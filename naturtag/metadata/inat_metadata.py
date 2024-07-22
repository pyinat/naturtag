"""Tools to translate iNaturalist observations and taxa into image metadata"""

# TODO: Get separate keywords for species, binomial, and trinomial
# TODO: Get common names for specified locale (requires using different endpoints)
# TODO: Handle observation with no taxon ID?
# TODO: Include eol:dataObject info (metadata for an individual observation photo)
from logging import getLogger
from typing import Iterable, Optional

from pyinaturalist import Observation, Taxon
from pyinaturalist_convert import to_dwc

from naturtag.constants import COMMON_NAME_IGNORE_TERMS, COMMON_RANKS, PathOrStr
from naturtag.metadata import MetaMetadata
from naturtag.storage import Settings, iNatDbClient
from naturtag.utils import get_valid_image_paths, quote

DWC_NAMESPACES = ['dcterms', 'dwc']
logger = getLogger().getChild(__name__)


def tag_images(
    image_paths: Iterable[PathOrStr],
    observation_id: Optional[int] = None,
    taxon_id: Optional[int] = None,
    recursive: bool = False,
    include_sidecars: bool = False,
    client: Optional[iNatDbClient] = None,
    settings: Optional[Settings] = None,
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
    client = client or iNatDbClient(settings.db_path)

    observation = client.from_id(observation_id, taxon_id)
    if not observation:
        return []

    inat_metadata = observation_to_metadata(
        observation,
        common_names=settings.common_names,
        hierarchical=settings.hierarchical,
    )
    if not image_paths:
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
            create_sidecars=settings.sidecar,
        )
    ]


def refresh_tags(
    image_paths: Iterable[PathOrStr],
    recursive: bool = False,
    client: Optional[iNatDbClient] = None,
    settings: Optional[Settings] = None,
) -> list[MetaMetadata]:
    """Refresh metadata for previously tagged images with latest observation and/or taxon data.

    Example:

        >>> # Refresh previously tagged images with latest observation and taxonomy metadata
        >>> from naturtag import refresh_tags
        >>> refresh_tags(['~/observations/'], recursive=True)

    Args:
        image_paths: Paths to images to tag
        recursive: Recursively search subdirectories for valid image files
        settings: Settings for metadata types to generate

    Returns:
        Updated metadata objects for updated images only
    """
    settings = settings or Settings.read()
    client = client or iNatDbClient(settings.db_path)
    metadata_objs = [
        _refresh_tags(MetaMetadata(image_path), client, settings)
        for image_path in get_valid_image_paths(
            image_paths, recursive, create_sidecars=settings.sidecar
        )
    ]
    return [m for m in metadata_objs if m]


def _refresh_tags(
    metadata: MetaMetadata, client: iNatDbClient, settings: Settings
) -> Optional[MetaMetadata]:
    """Refresh existing metadata for a single image

    Returns:
        Updated metadata if existing IDs were found, otherwise ``None``
    """
    if not metadata.has_observation and not metadata.has_taxon:
        logger.debug(f'No IDs found in {metadata.image_path}')
        return None

    logger.debug(f'Refreshing tags for {metadata.image_path}')
    settings = settings or Settings.read()
    observation = client.from_id(metadata.observation_id, metadata.taxon_id)
    metadata = observation_to_metadata(
        observation,
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


def observation_to_metadata(
    observation: Observation,
    metadata: Optional[MetaMetadata] = None,
    common_names: bool = False,
    hierarchical: bool = False,
) -> MetaMetadata:
    """Get image metadata from an Observation object"""
    metadata = metadata or MetaMetadata()

    # Get all specified keyword categories
    keywords = _get_taxonomy_keywords(observation.taxon)
    if hierarchical:
        keywords.extend(_get_taxon_hierarchical_keywords(observation.taxon))
    if common_names:
        common_keywords = _get_common_keywords(observation.taxon)
        keywords.extend(common_keywords)
        if hierarchical:
            keywords.extend(_get_hierarchical_keywords(common_keywords))
    keywords.extend(_get_id_keywords(observation.id, observation.taxon.id))

    logger.debug(f'{len(keywords)} total keywords generated')
    metadata.update_keywords(keywords)

    # Convert and add coordinates
    # TODO: Add other metadata like title, description, tags, etc.
    if observation:
        metadata.update_coordinates(observation.location, observation.positional_accuracy)

    def _format_key(k):
        """Get DwC terms as XMP tags.
        Note: exiv2 will automatically add recognized XML namespace URLs when adding properties
        """
        namespace, term = k.split(':')
        return f'Xmp.{namespace}.{term}' if namespace in DWC_NAMESPACES else None

    # Convert and add DwC metadata
    tag_observations = [observation] if observation.id else None
    dwc = to_dwc(observations=tag_observations, taxa=[observation.taxon])[0]
    dwc_xmp = {_format_key(k): v for k, v in dwc.items() if _format_key(k)}
    metadata.update(dwc_xmp)

    return metadata


def _get_taxonomy_keywords(taxon: Taxon) -> list[str]:
    """Format a list of taxa into rank keywords"""
    return [quote(f'taxonomy:{t.rank}={t.name}') for t in taxon.ancestors + [taxon]]


def _get_id_keywords(
    observation_id: Optional[int] = None, taxon_id: Optional[int] = None
) -> list[str]:
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
        return any(ignore_term in kw.lower() for ignore_term in COMMON_NAME_IGNORE_TERMS)

    return [quote(kw) for kw in keywords if kw and not is_ignored(kw)]


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
