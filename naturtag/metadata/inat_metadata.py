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
from naturtag.constants import COMMON_NAME_IGNORE_TERMS, IntTuple, PathOrStr
from naturtag.image_glob import glob_paths
from naturtag.metadata import MetaMetadata

DWC_NAMESPACES = ['dcterms', 'dwc']
logger = getLogger().getChild(__name__)


def tag_images(
    observation_id: int,
    taxon_id: int,
    common_names: bool = False,
    darwin_core: bool = False,
    hierarchical: bool = False,
    create_sidecar: bool = False,
    images: list[str] = None,
) -> list[MetaMetadata]:
    """
    Get taxonomy tags from an iNaturalist observation or taxon, and write them to local image
    metadata. See :py:func:`~naturtag.cli.tag` for details.
    """
    inat_metadata = get_inat_metadata(
        observation_id=observation_id,
        taxon_id=taxon_id,
        common_names=common_names,
        darwin_core=darwin_core,
        hierarchical=hierarchical,
    )

    if not inat_metadata:
        return []
    elif not images:
        return [inat_metadata]
    return [tag_image(image_path, inat_metadata, create_sidecar) for image_path in glob_paths(images)]


def tag_image(
    image_path: str, inat_metadata: MetaMetadata, create_sidecar: bool = False
) -> MetaMetadata:
    img_metadata = MetaMetadata(image_path).merge(inat_metadata)
    img_metadata.write(create_sidecar=create_sidecar)
    return img_metadata


def get_inat_metadata(
    observation_id: int = None,
    taxon_id: int = None,
    common_names: bool = False,
    darwin_core: bool = False,
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
    taxon = INAT_CLIENT.taxa(taxon_id)
    if not taxon:
        logger.warning(f'No taxon found: {taxon_id}')
        return None

    # Get all specified keyword categories
    keywords = get_taxonomy_keywords(taxon)
    if hierarchical:
        keywords.extend(get_hierarchical_keywords(keywords))
    if common_names:
        keywords.extend(get_common_keywords(taxon))
    keywords.extend(get_id_keywords(observation_id, taxon_id))

    logger.info(f'{len(keywords)} total keywords generated')
    metadata.update_keywords(keywords)

    # Convert and add coordinates
    if observation:
        metadata.update_coordinates(observation.location)

    # Convert and add DwC metadata, if specified
    if darwin_core:
        metadata.update(get_dwc_terms(observation, taxon))

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


def get_records_from_metadata(metadata: 'MetaMetadata') -> tuple[Taxon, Observation]:
    """Get observation and/or taxon records based on image metadata"""
    logger.info(f'Searching for matching taxon and/or observation for {metadata.image_path}')
    taxon, observation = None, None

    if metadata.has_observation:
        observation = INAT_CLIENT.observations(metadata.observation_id)
        taxon = observation.taxon
    elif metadata.has_taxon:
        taxon = INAT_CLIENT.taxa(metadata.taxon_id)

    return taxon, observation


def get_taxonomy_keywords(taxon: Taxon) -> list[str]:
    """Format a list of taxa into rank keywords"""
    return [_quote(f'taxonomy:{t.rank}={t.name}') for t in [taxon, *taxon.ancestors]]


def get_id_keywords(observation_id: int = None, taxon_id: int = None) -> list[str]:
    keywords = []
    if taxon_id:
        keywords.append(f'inat:taxon_id={taxon_id}')
        keywords.append(f'dwc:taxonID={taxon_id}')
    if observation_id:
        keywords.append(f'inat:observation_id={observation_id}')
        keywords.append(f'dwc:catalogNumber={observation_id}')
    return keywords


def get_common_keywords(taxon: Taxon) -> list[str]:
    """Format a list of taxa into common name keywords.
    Filters out terms that aren't useful to keep as tags
    """
    keywords = [t.preferred_common_name for t in [taxon, *taxon.ancestors]]

    def is_ignored(kw):
        return any([ignore_term in kw.lower() for ignore_term in COMMON_NAME_IGNORE_TERMS])

    return [_quote(kw) for kw in keywords if kw and not is_ignored(kw)]


def get_hierarchical_keywords(keywords: list) -> list[str]:
    """Translate sorted taxonomy keywords into pipe-delimited hierarchical keywords"""
    hier_keywords = [keywords[0]]
    for rank_name in keywords[1:]:
        hier_keywords.append(f'{hier_keywords[-1]}|{rank_name}')
    return hier_keywords


def get_dwc_terms(observation: Observation = None, taxon: Taxon = None) -> dict[str, str]:
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


def refresh_all(
    file_paths: Iterable[PathOrStr],
    common_names: bool = False,
    darwin_core: bool = False,
    hierarchical: bool = False,
    create_sidecar: bool = False,
):
    """Refresh metadata for all specified images"""
    for file_path in file_paths:
        refresh_metadata(
            MetaMetadata(file_path), common_names, darwin_core, hierarchical, create_sidecar
        )


def refresh_metadata(
    metadata: MetaMetadata,
    common_names: bool = False,
    darwin_core: bool = False,
    hierarchical: bool = False,
    create_sidecar: bool = False,
) -> MetaMetadata:
    """Refresh existing image metadata with latest observation and/or taxon data"""
    if not metadata.has_observation and not metadata.has_taxon:
        return metadata

    logger.info(f'Refreshing metadata for {metadata.image_path}')
    metadata = get_inat_metadata(  # type: ignore
        observation_id=metadata.observation_id,
        taxon_id=metadata.taxon_id,
        common_names=common_names,
        darwin_core=darwin_core,
        hierarchical=hierarchical,
        metadata=metadata,
    )
    metadata.write(create_sidecar=create_sidecar)
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
