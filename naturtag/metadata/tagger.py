"""Tools to translate + write iNaturalist observation and taxonomy data into image metadata"""

# TODO: Get separate keywords for species, binomial, and trinomial
# TODO: Get common names for specified locale (requires using different endpoints)
# TODO: Handle observation with no taxon ID?
# TODO: Include eol:dataObject info (metadata for an individual observation photo)
from collections.abc import Iterator
from logging import getLogger
from typing import Iterable, Optional

from pyinaturalist import Observation

from naturtag.constants import PathOrStr
from naturtag.metadata import DerivedMetadata
from naturtag.storage import Settings, iNatDbClient
from naturtag.utils import get_valid_image_paths

logger = getLogger().getChild(__name__)


def tag_images(
    image_paths: Iterable[PathOrStr],
    observation_id: Optional[int] = None,
    taxon_id: Optional[int] = None,
    recursive: bool = False,
    include_sidecars: bool = False,
    client: Optional[iNatDbClient] = None,
    settings: Optional[Settings] = None,
) -> list[DerivedMetadata]:
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
    return list(
        _tag_images_iter(
            image_paths, observation_id, taxon_id, recursive, include_sidecars, client, settings
        )
    )


def _tag_images_iter(
    image_paths: Iterable[PathOrStr],
    observation_id: Optional[int] = None,
    taxon_id: Optional[int] = None,
    recursive: bool = False,
    include_sidecars: bool = False,
    client: Optional[iNatDbClient] = None,
    settings: Optional[Settings] = None,
) -> Iterator[DerivedMetadata]:
    """Same as :py:func:`tag_images`, but returns an iterator"""
    settings = settings or Settings.read()
    client = client or iNatDbClient(settings.db_path)

    observation = client.from_id(observation_id, taxon_id)
    if not observation:
        return

    inat_metadata = DerivedMetadata().from_observation(
        observation,
        common_names=settings.common_names,
        hierarchical=settings.hierarchical,
    )
    if not image_paths:
        yield inat_metadata
        return

    def _tag_image(
        image_path,
    ):
        img_metadata = DerivedMetadata(image_path).merge(inat_metadata)
        img_metadata.write(
            write_exif=settings.exif,
            write_iptc=settings.iptc,
            write_xmp=settings.xmp,
            write_sidecar=settings.sidecar,
        )
        return img_metadata

    for image_path in get_valid_image_paths(
        image_paths,
        recursive=recursive,
        include_sidecars=include_sidecars,
        create_sidecars=settings.sidecar,
        include_raw=True,
    ):
        yield _tag_image(image_path)


def refresh_tags(
    image_paths: Iterable[PathOrStr],
    recursive: bool = False,
    client: Optional[iNatDbClient] = None,
    settings: Optional[Settings] = None,
) -> list[DerivedMetadata]:
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
        Updated metadata for each image that was successfully refreshed
    """
    return [i for i in _refresh_tags_iter(image_paths, recursive, client, settings) if i]


def _refresh_tags_iter(
    image_paths: Iterable[PathOrStr],
    recursive: bool = False,
    client: Optional[iNatDbClient] = None,
    settings: Optional[Settings] = None,
) -> Iterator[DerivedMetadata | None]:
    """Same as :py:func:`refresh_tags`, but returns an iterator"""
    settings = settings or Settings.read()
    client = client or iNatDbClient(settings.db_path)
    for image_path in get_valid_image_paths(
        image_paths, recursive, create_sidecars=settings.sidecar, include_raw=True
    ):
        yield _refresh_tags(DerivedMetadata(image_path), client, settings)


def _refresh_tags(
    metadata: DerivedMetadata, client: iNatDbClient, settings: Settings
) -> Optional[DerivedMetadata]:
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
    metadata.from_observation(
        observation,
        common_names=settings.common_names,
        hierarchical=settings.hierarchical,
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
    metadata: Optional[DerivedMetadata] = None,
    common_names: bool = False,
    hierarchical: bool = False,
) -> DerivedMetadata:
    """Get image metadata from an Observation object"""
    metadata = metadata or DerivedMetadata()
    return metadata.from_observation(
        observation, common_names=common_names, hierarchical=hierarchical
    )
