from hashlib import md5
from io import BytesIO
from os import makedirs
from os.path import isfile, join, splitext
from logging import getLogger

from PIL import Image
from naturtag.constants import (
    THUMBNAILS_DIR,
    THUMBNAIL_SIZE,
    LG_THUMBNAIL_SIZE,
    THUMBNAIL_DEFAULT_FORMAT,
)

logger = getLogger().getChild(__name__)


def get_thumbnail(image_path, large=False):
    """
    Get a cached thumbnail for an image, if one already exists; otherwise, generate a new one.

    Args:
        image_path (str): Path to source image
        large (bool): Make it a 'larger' thumbnail

    Returns:
        str: Path to thumbnail image
    """
    thumbnail_path = get_thumbnail_path(image_path)
    if isfile(thumbnail_path):
        return thumbnail_path
    else:
        return generate_thumbnail(image_path, thumbnail_path, large)


def get_thumbnail_if_exists(image_path):
    """
    Get a cached thumbnail for an image, if one already exists, but if not, don't generate a new one
    """
    thumbnail_path = get_thumbnail_path(image_path)
    if isfile(thumbnail_path):
        logger.debug(f'Found existing thumbnail for {image_path}')
        return thumbnail_path
    else:
        return None


def get_thumbnail_path(image_path):
    """ Determine the thumbnail filename based on a hash of the original file path """
    makedirs(THUMBNAILS_DIR, exist_ok=True)
    thumbnail_hash = md5(image_path.encode()).hexdigest()
    ext = _get_format(image_path)
    return join(THUMBNAILS_DIR, f'{thumbnail_hash}.{ext}')


def _get_format(image_path):
    """ Account for various edge cases when getting an image format based on a file extension """
    if isinstance(image_path, bytes):
        image_path = image_path.decode('utf-8')
    # Strip off request params if path is a URL
    image_path = image_path.split('?')[0]
    ext = splitext(image_path)[-1] or THUMBNAIL_DEFAULT_FORMAT
    return ext.lower().replace('.', '')


def cache_async_thumbnail(async_image, large=False):
    """ Get raw image data from an AsyncImage and cache a thumbnail for future usage """
    thumbnail_path = get_thumbnail_path(async_image.source)
    ext = _get_format(thumbnail_path)
    logger.debug(f'Getting image data downloaded from {async_image.source}; format {ext}')

    # Load inner 'texture' bytes into a file-like object that PIL can read
    image_bytes = BytesIO()
    async_image._coreimage.image.texture.save(image_bytes, fmt=ext)
    image_bytes.seek(0)
    # TODO: Unsure why some images fail
    if len(image_bytes.getvalue()) > 0:
        return generate_thumbnail(image_bytes, thumbnail_path, large=True, fmt=ext)
    else:
        logger.error(f'Failed to save texture to thumbnail: {async_image.source}')


def generate_thumbnail(source, thumbnail_path, large=False, fmt=None):
    """
    Generate a new thumbnail from the source image, or just copy the image to the cache if it's
    already thumbnail size
    """
    logger.info(f'Generating new thumbnail for {source}:\n  {thumbnail_path}')
    target_size = LG_THUMBNAIL_SIZE if large else THUMBNAIL_SIZE
    try:
        image = Image.open(source)
        if image.size[0] > target_size[0] or image.size[1] > target_size[1]:
            image.thumbnail(target_size)
        else:
            logger.debug(f'Image is already thumbnail size! ({image.size})')
        image.save(thumbnail_path, fmt=fmt.replace('jpg', 'jpeg'))
        return thumbnail_path
    # If we're unable to generate a thumbnail, just use the original image
    except RuntimeError as e:
        logger.error('Failed to generate thumbnail:')
        logger.exception(e)
        return source
