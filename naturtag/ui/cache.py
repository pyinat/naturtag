""" Utilities for UI-specific caching """
from logging import getLogger
from io import BytesIO

from naturtag.thumbnails import (
    get_thumbnail_hash,
    get_format,
    get_thumbnail,
    get_thumbnail_if_exists,
    generate_thumbnail_from_bytes,
)
from naturtag.atlas import get_resource_path_if_exists

logger = getLogger().getChild(__name__)


def get_any_thumbnail(source, size='small'):
    """ Get the path of a thumbnail stored inside either an atlas or the thumbnail cache """
    return get_atlas_thumbnail_if_exists(source, size) or get_thumbnail(source)


def get_any_thumbnail_if_exists(source, size='small'):
    """ Get the path of a thumbnail stored inside either an atlas or the thumbnail cache """
    return get_atlas_thumbnail_if_exists(source, size) or get_thumbnail_if_exists(source)


def get_atlas_thumbnail_if_exists(source, size):
    """ Get the path of a thumbnail stored inside an atlas, if available

    Args:
        source (str): File path or URI for image source

    Returns:
        str: `atlas://` path, if found; otherwise ``None``
    """
    return get_resource_path_if_exists(size, get_thumbnail_hash(source))


def cache_async_thumbnail(async_image, **kwargs):
    """
    Get raw image data from an AsyncImage and cache a thumbnail for future usage.
    See :py:func:`.generate_thumbnail` for size options.

    Args:
        async_image (:py:class:`~kivy.uix.image.AsyncImage`): Image object

    Returns:
        str: The path of the new thumbnail
    """
    if not (async_image._coreimage.image and async_image._coreimage.image.texture):
        logger.warning(f'Texture for {async_image.source} not loaded')
        return None

    # thumbnail_path = get_thumbnail_path(async_image.source)
    ext = get_format(async_image.source)
    logger.debug(f'Getting image data downloaded from {async_image.source}; format {ext}')

    # Load inner 'texture' bytes into a file-like object that PIL can read
    image_bytes = BytesIO()
    async_image._coreimage.image.texture.save(image_bytes, fmt=ext)
    generate_thumbnail_from_bytes(image_bytes, async_image.source, **kwargs)
