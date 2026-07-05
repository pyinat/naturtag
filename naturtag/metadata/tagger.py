"""Tools to translate + write iNaturalist observation and taxonomy data into image metadata"""

# TODO: Get separate keywords for species, binomial, and trinomial
# TODO: Get common names for specified locale (requires using different endpoints)
# TODO: Handle observation with no taxon ID?
# TODO: Include eol:dataObject info (metadata for an individual observation photo)
from collections.abc import Iterator
from logging import getLogger
from pathlib import Path
from typing import Iterable, Optional

from pyinaturalist import Observation

from naturtag.constants import PathOrStr
from naturtag.metadata import DerivedMetadata
from naturtag.storage import Settings, iNatDbClient
from naturtag.utils import ImagePair, get_image_pairs, get_valid_image_paths

logger = getLogger().getChild(__name__)


def tag_images(
    image_paths: Iterable[PathOrStr],
    observation_id: Optional[int] = None,
    taxon_id: Optional[int] = None,
    recursive: bool = False,
    include_sidecars: bool = False,
    client: Optional[iNatDbClient] = None,
    settings: Optional[Settings] = None,
    *,
    failed_paths: Optional[list[Path]] = None,
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
        failed_paths: Optional list to populate with any paths that failed to write

    Returns:
        Updated image metadata for each image
    """
    return list(
        _tag_images_iter(
            image_paths,
            observation_id,
            taxon_id,
            recursive,
            include_sidecars,
            client,
            settings,
            failed_paths=failed_paths,
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
    *,
    failed_paths: Optional[list[Path]] = None,
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

    paths = get_valid_image_paths(
        image_paths,
        recursive=recursive,
        include_sidecars=include_sidecars,
        create_sidecars=settings.sidecar,
        include_raw=True,
    )

    for pair in get_image_pairs(paths):
        yield from _tag_pair(pair, inat_metadata, settings, failed_paths)


def _tag_pair(
    pair: ImagePair,
    inat_metadata: DerivedMetadata,
    settings: Settings,
    failed_paths: Optional[list[Path]],
) -> Iterator[DerivedMetadata]:
    """Tag a companion image and its optional paired RAW file, tracking any failed paths"""
    try:
        companion_meta = DerivedMetadata(pair.image_path).merge(inat_metadata)
        raw_path = pair.raw_path
        raw_meta = DerivedMetadata(raw_path).merge(inat_metadata) if raw_path else None
        companion_ok, raw_ok = _write_pair(companion_meta, raw_meta, settings)
        if companion_ok:
            yield companion_meta
        elif failed_paths is not None:
            failed_paths.append(pair.image_path)
        if raw_path is not None:
            if raw_ok:
                assert raw_meta is not None  # set together with raw_path above
                yield raw_meta
            elif failed_paths is not None:
                failed_paths.append(raw_path)
    except (RuntimeError, OSError):
        # Pre-write failure (e.g. metadata construction or sidecar I/O)
        # Ensure one file's failure doesn't discard results already produced for other files
        logger.exception(f'Failed to tag {pair.image_path}')
        if failed_paths is not None:
            failed_paths.append(pair.image_path)


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
    paths = get_valid_image_paths(
        image_paths, recursive, create_sidecars=settings.sidecar, include_raw=True
    )
    for pair in get_image_pairs(paths):
        try:
            companion_result, raw_result = _refresh_pair(
                DerivedMetadata(pair.image_path), client, settings, raw_path=pair.raw_path
            )
            yield companion_result
            if raw_result is not None:
                yield raw_result
        except (RuntimeError, OSError):
            # RuntimeError: exiv2 write failure; OSError: sidecar I/O failure
            logger.exception(f'Failed to refresh {pair.image_path}')
            yield None


def _refresh_tags(
    metadata: DerivedMetadata,
    client: iNatDbClient,
    settings: Settings,
    *,
    raw_path: Optional[Path] = None,
) -> Optional[DerivedMetadata]:
    """Refresh existing metadata for a single image, and its paired RAW file, if any.

    Returns the companion's result only; used by the GUI, which tracks each card by its
    displayed/companion path.

    Args:
        metadata: Previously loaded metadata for the companion (displayed) image path
        raw_path: A RAW file sharing a basename with ``metadata``'s image, to refresh alongside it

    Returns:
        Updated metadata for the companion image if existing IDs were found and its write
        succeeded, otherwise ``None``
    """
    companion_result, _ = _refresh_pair(metadata, client, settings, raw_path=raw_path)
    return companion_result


def _refresh_pair(
    metadata: DerivedMetadata,
    client: iNatDbClient,
    settings: Settings,
    *,
    raw_path: Optional[Path] = None,
) -> tuple[Optional[DerivedMetadata], Optional[DerivedMetadata]]:
    """Refresh a companion image's metadata and its paired RAW file's, if any.

    Returns:
        ``(companion_result, raw_result)``. Both are ``None`` if no existing IDs were found or
        the pair's write failed; ``raw_result`` is ``None`` whenever there's no paired RAW file.
    """
    if not metadata.has_observation and not metadata.has_taxon:
        logger.debug(f'No IDs found in {metadata.image_path}')
        return None, None

    logger.debug(f'Refreshing tags for {metadata.image_path}')
    observation = client.from_id(metadata.observation_id, metadata.taxon_id)
    inat_metadata = DerivedMetadata().from_observation(
        observation,
        common_names=settings.common_names,
        hierarchical=settings.hierarchical,
    )
    metadata.merge(inat_metadata)
    raw_meta = DerivedMetadata(raw_path).merge(inat_metadata) if raw_path else None
    companion_ok, raw_ok = _write_pair(metadata, raw_meta, settings)
    if not companion_ok:
        return None, None
    return metadata, (raw_meta if raw_ok else None)


def _write_pair(
    companion_meta: DerivedMetadata,
    raw_meta: Optional[DerivedMetadata],
    settings: Settings,
) -> tuple[bool, bool]:
    """Write metadata to a companion image and its optional paired RAW file.

    A RAW file sharing a basename with its companion shares one physical sidecar file. Whichever
    of the two resolves to that shared ``sidecar_path`` is the sidecar's owner and writes it as
    part of its normal write; if the owner's write fails, the sidecar is recovered from the other
    side's already-merged metadata, since both were merged from the same source data.

    Returns:
        ``(companion_ok, raw_ok)``. ``raw_ok`` is always ``False`` when there is no RAW file.
    """
    raw_owns_sidecar = bool(
        raw_meta is not None
        and settings.sidecar
        and companion_meta.sidecar_path == raw_meta.sidecar_path
    )
    companion_ok = _write_one(companion_meta, settings, settings.sidecar and not raw_owns_sidecar)
    if not companion_ok or raw_meta is None:
        return companion_ok, False

    raw_ok = _write_one(raw_meta, settings, settings.sidecar)
    if not raw_ok and raw_owns_sidecar:
        # RAW owned the shared sidecar and failed before writing it; recover it from the
        # companion's merged metadata instead of leaving it stale/missing.
        try:
            companion_meta.write(
                write_exif=False, write_iptc=False, write_xmp=False, write_sidecar=True
            )
        except (RuntimeError, OSError):
            logger.exception(f'Also failed sidecar fallback for {companion_meta.image_path}')
    return companion_ok, raw_ok


def _write_one(metadata: DerivedMetadata, settings: Settings, write_sidecar: bool) -> bool:
    """Write metadata to a single file.

    Returns:
        True if the write succeeded.
    """
    try:
        metadata.write(
            write_exif=settings.exif,
            write_iptc=settings.iptc,
            write_xmp=settings.xmp,
            write_sidecar=write_sidecar,
        )
        return True
    except (RuntimeError, OSError):
        # RuntimeError: exiv2 write failure (locked/corrupted file)
        # OSError: sidecar-stub file I/O failure (permissions, disk full)
        logger.exception(f'Failed to write {metadata.image_path}')
        return False


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
