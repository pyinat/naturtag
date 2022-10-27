"""Tools to translate iNaturalist observations and taxa into image metadata"""
# TODO: Get separate keywords for species, binomial, and trinomial
# TODO: Get common names for specified locale (requires using different endpoints)
# TODO: Handle observation with no taxon ID?
# TODO: Include eol:dataObject info (metadata for an individual observation photo)
from logging import getLogger
from typing import Iterable, Optional
from urllib.parse import urlparse

from pyinaturalist import Observation, Taxon, TaxonCounts
from pyinaturalist_convert import to_dwc

from naturtag.client import INAT_CLIENT
from naturtag.constants import COMMON_NAME_IGNORE_TERMS, COMMON_RANKS, IntTuple, PathOrStr
from naturtag.metadata import MetaMetadata
from naturtag.settings import Settings
from naturtag.utils.image_glob import get_valid_image_paths

DWC_NAMESPACES = ['dcterms', 'dwc']
logger = getLogger().getChild(__name__)


def tag_images(
    image_paths: Iterable[PathOrStr],
    observation_id: int = None,
    taxon_id: int = None,
    recursive: bool = False,
    include_sidecars: bool = False,
    settings: Settings = None,
) -> list[MetaMetadata]:
    """
    Get taxonomy tags from an iNaturalist observation or taxon, and write them to local image
    metadata.

    Examples:

        >>> # Tag images with full observation metadata:
        >>> from naturtag import tag_images
        >>> tag_images(['img1.jpg', 'img2.jpg'], observation_id=1234)

        >>> # Tag images with taxonomy metadata only
        >>> tag_images(['img1.jpg', 'img2.jpg'], taxon_id=1234)

        >>> # Glob patterns are also supported
        >>> tag_images(['~/observations/*.jpg'], taxon_id=1234)

    Args:
        image_paths: Paths to images to tag
        observation_id: ID of an iNaturalist observation
        taxon_id: ID of an iNaturalist species or other taxon
        recursive: Recursively search subdirectories for valid image files
        include_sidecars: Allow loading a sidecar file without an associated image
        settings: Settings for metadata types to generate

    Returns:
        Updated image metadata for each image
    """
    settings = settings or Settings.read()
    inat_metadata = get_inat_metadata(
        observation_id=observation_id,
        taxon_id=taxon_id,
        common_names=settings.common_names,
        hierarchical=settings.hierarchical,
    )

    if not inat_metadata:
        return []
    elif not image_paths:
        return [inat_metadata]

    def _tag_image(
        image_path,
    ):
        img_metadata = MetaMetadata(image_path).merge(inat_metadata)
        img_metadata.write(
            write_exif=settings.exif,
            write_iptc=settings.iptc,
            write_xmp=settings.xmp,
            write_sidecar=settings.sidecar,
        )
        return img_metadata

    return [
        _tag_image(image_path)
        for image_path in get_valid_image_paths(
            image_paths,
            recursive=recursive,
            include_sidecars=include_sidecars,
        )
    ]


def get_inat_metadata(
    observation_id: int = None,
    taxon_id: int = None,
    common_names: bool = False,
    hierarchical: bool = False,
    metadata: MetaMetadata = None,
) -> Optional[MetaMetadata]:
    """Create or update image metadata based on an iNaturalist observation and/or taxon"""
    metadata = metadata or MetaMetadata()
    observation, taxon = None, None

    # Get observation and/or taxon records
    if observation_id:
        observation = INAT_CLIENT.observations(observation_id, refresh=True)
        taxon_id = observation.taxon.id

    # Observation.taxon doesn't include ancestors, so we always need to fetch the full taxon record
    taxon = INAT_CLIENT.taxa(taxon_id, refresh=True)
    if not taxon:
        logger.warning(f'No taxon found: {taxon_id}')
        return None

    # If there's a taxon only (no observation), check for any taxonomy changes
    if (
        not observation_id
        and not taxon.is_active
        and len(taxon.current_synonymous_taxon_ids or []) == 1
    ):
        taxon = INAT_CLIENT.taxa(taxon.current_synonymous_taxon_ids[0], refresh=True)

    # Get all specified keyword categories
    keywords = _get_taxonomy_keywords(taxon)
    if hierarchical:
        keywords.extend(_get_taxon_hierarchical_keywords(taxon))
    if common_names:
        common_keywords = _get_common_keywords(taxon)
        keywords.extend(common_keywords)
        if hierarchical:
            keywords.extend(_get_hierarchical_keywords(common_keywords))
    keywords.extend(_get_id_keywords(observation_id, taxon_id))

    logger.info(f'{len(keywords)} total keywords generated')
    metadata.update_keywords(keywords)

    # Convert and add coordinates
    if observation:
        metadata.update_coordinates(observation.location)

    # Convert and add DwC metadata
    metadata.update(_get_dwc_terms(observation, taxon))
    return metadata


def get_observed_taxa(username: str, include_casual: bool = False, **kwargs) -> TaxonCounts:
    """Get counts of taxa observed by the user, ordered by number of observations descending"""
    if not username:
        return {}
    taxon_counts = INAT_CLIENT.observations.species_counts(
        user_login=username,
        verifiable=None if include_casual else True,  # False will return *only* casual observations
        **kwargs,
    )
    logger.info(f'{len(taxon_counts)} user-observed taxa found')
    return sorted(taxon_counts, key=lambda x: x.count, reverse=True)


def _get_records_from_metadata(metadata: 'MetaMetadata') -> tuple[Taxon, Observation]:
    """Get observation and/or taxon records based on image metadata"""
    logger.info(f'Searching for matching taxon and/or observation for {metadata.image_path}')
    taxon, observation = None, None

    if metadata.has_observation:
        observation = INAT_CLIENT.observations(metadata.observation_id)
        taxon = observation.taxon
    elif metadata.has_taxon:
        taxon = INAT_CLIENT.taxa(metadata.taxon_id)

    return taxon, observation


def _get_taxonomy_keywords(taxon: Taxon) -> list[str]:
    """Format a list of taxa into rank keywords"""
    return [_quote(f'taxonomy:{t.rank}={t.name}') for t in taxon.ancestors + [taxon]]


def _get_id_keywords(observation_id: int = None, taxon_id: int = None) -> list[str]:
    keywords = []
    if taxon_id:
        keywords.append(f'inat:taxon_id={taxon_id}')
        keywords.append(f'dwc:taxonID={taxon_id}')
    if observation_id:
        keywords.append(f'inat:observation_id={observation_id}')
        keywords.append(f'dwc:catalogNumber={observation_id}')
    return keywords


def _get_common_keywords(taxon: Taxon) -> list[str]:
    """Format a list of taxa into common name keywords.
    Filters out terms that aren't useful to keep as tags.
    """
    keywords = [
        t.preferred_common_name for t in taxon.ancestors + [taxon] if t.rank in COMMON_RANKS
    ]

    def is_ignored(kw):
        return any([ignore_term in kw.lower() for ignore_term in COMMON_NAME_IGNORE_TERMS])

    return [_quote(kw) for kw in keywords if kw and not is_ignored(kw)]


def _get_taxon_hierarchical_keywords(taxon: Taxon) -> list[str]:
    """Get hierarchical keywords for a taxon"""
    keywords = [t.name for t in taxon.ancestors + [taxon] if t.rank in COMMON_RANKS]
    return _get_hierarchical_keywords(keywords)


def _get_hierarchical_keywords(keywords: list[str]) -> list[str]:
    """Translate a sorted list of flat keywords into pipe-delimited hierarchical keywords"""
    hier_keywords = [keywords[0]]
    for k in keywords[1:]:
        hier_keywords.append(f'{hier_keywords[-1]}|{k}')
    return hier_keywords


def _get_dwc_terms(observation: Observation = None, taxon: Taxon = None) -> dict[str, str]:
    """Convert either an observation or taxon into XMP-formatted Darwin Core terms"""

    # Get terms only for specific namespaces
    # Note: exiv2 will automatically add recognized XML namespace URLs when adding properties
    def format_key(k):
        namespace, term = k.split(':')
        return f'Xmp.{namespace}.{term}' if namespace in DWC_NAMESPACES else None

    # Convert to DwC, then to XMP tags
    dwc = to_dwc(observations=observation, taxa=taxon)[0]
    return {format_key(k): v for k, v in dwc.items() if format_key(k)}


def get_ids_from_url(url: str) -> IntTuple:
    """If a URL is provided containing an ID, return the taxon or observation ID.

    Returns:
        ``(observation_id, taxon_id)``
    """
    observation_id, taxon_id = None, None
    id = strip_url(url)

    if 'observation' in url:
        observation_id = id
    elif 'taxa' in url:
        taxon_id = id

    return observation_id, taxon_id


def refresh_tags(
    image_paths: Iterable[PathOrStr],
    recursive: bool = False,
    settings: Settings = None,
):
    """Refresh metadata for previously tagged images

    Example:

        >>> # Refresh previously tagged images with latest observation and taxonomy metadata
        >>> from naturtag import refresh_tags
        >>> refresh_tags(['~/observations/'], recursive=True)

    Args:
        image_paths: Paths to images to tag
        recursive: Recursively search subdirectories for valid image files
        settings: Settings for metadata types to generate
    """
    for image_path in get_valid_image_paths(image_paths, recursive):
        _refresh_tags(MetaMetadata(image_path), settings)


def _refresh_tags(metadata: MetaMetadata, settings: Settings = None) -> MetaMetadata:
    """Refresh existing metadata for a single image with latest observation and/or taxon data"""
    if not metadata.has_observation and not metadata.has_taxon:
        return metadata

    logger.info(f'Refreshing tags for {metadata.image_path}')
    settings = settings or Settings.read()
    metadata = get_inat_metadata(  # type: ignore
        observation_id=metadata.observation_id,
        taxon_id=metadata.taxon_id,
        common_names=settings.common_names,
        hierarchical=settings.hierarchical,
        metadata=metadata,
    )
    metadata.write(
        write_exif=settings.exif,
        write_iptc=settings.iptc,
        write_xmp=settings.xmp,
        write_sidecar=settings.sidecar,
    )
    return metadata


def strip_url(value: str) -> Optional[int]:
    """If a URL is provided containing an ID, return just the ID"""
    try:
        path = urlparse(value).path
        return int(path.split('/')[-1].split('-')[0])
    except (TypeError, ValueError):
        return None


def _quote(s: str) -> str:
    """Surround keyword in quotes if it contains whitespace"""
    return f'"{s}"' if ' ' in s else s
