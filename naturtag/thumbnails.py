""" Utilities for generating and retrieving image thumbnails """
from hashlib import md5
from io import IOBase
from os import makedirs
from os.path import dirname, isfile, join, normpath, splitext
from logging import getLogger

from PIL import Image
from PIL.ImageOps import exif_transpose, flip
from naturtag.constants import (
    EXIF_ORIENTATION_ID,
    THUMBNAILS_DIR,
    THUMBNAIL_SIZE_DEFAULT,
    THUMBNAIL_SIZES,
    THUMBNAIL_DEFAULT_FORMAT,
)

logger = getLogger().getChild(__name__)


def get_thumbnail(source, **kwargs):
    """
    Get a cached thumbnail for an image, if one already exists; otherwise, generate a new one.
    See :py:func:`.generate_thumbnail` for size options.

    Args:
        source (str): File path or URI for image source

    Returns:
        str: Path to thumbnail image
    """
    thumbnail_path = get_thumbnail_path(source)
    if isfile(thumbnail_path):
        return thumbnail_path
    else:
        return generate_thumbnail(source, thumbnail_path, **kwargs)


def get_thumbnail_if_exists(source):
    """
    Get a cached thumbnail for an image, if one already exists, but if not, don't generate a new one

    Args:
        source (str): File path or URI for image source

    Returns:
        str: The path of the new thumbnail, if found; otherwise ``None``
    """
    thumbnail_path = get_thumbnail_path(source)
    if isfile(thumbnail_path):
        logger.debug(f'Found existing thumbnail for {source}')
        return thumbnail_path
    elif normpath(dirname(source)) == normpath(THUMBNAILS_DIR) or source.startswith('atlas://'):
        logger.debug(f'Image is already a thumbnail: {source}')
        return source
    else:
        return None


def get_thumbnail_hash(source):
    """ Get a unique string based on the source to use as a filename or atlas resource ID """
    return md5(source.encode()).hexdigest()


def get_thumbnail_size(size):
    """ Get one of the predefined thumbnail dimensions from a size string

    Args:
        size (str): One of: 'small', 'medium', 'large'

    Returns:
        ``int, int``: X and Y dimensions of thumbnail size
    """
    return THUMBNAIL_SIZES.get(size, THUMBNAIL_SIZE_DEFAULT)


def get_thumbnail_path(source):
    """
    Determine the thumbnail filename based on a hash of the original file path

    Args:
        source (str): File path or URI for image source
    """
    makedirs(THUMBNAILS_DIR, exist_ok=True)
    thumbnail_hash = get_thumbnail_hash(source)
    ext = get_format(source)
    return join(THUMBNAILS_DIR, f'{thumbnail_hash}.{ext}')


def get_format(source):
    """
    Account for various edge cases when getting an image format based on a file extension

    Args:
        source (str): File path or URI for image source

    Returns:
        str: Format, if found; otherwise, defaults to ``jpg``
    """
    if isinstance(source, bytes):
        source = source.decode('utf-8')
    # Strip off request params if path is a URL
    source = source.split('?')[0]
    ext = splitext(source)[-1] or THUMBNAIL_DEFAULT_FORMAT
    # Note: PIL only accepts 'jpeg' (not 'jpg'), and Kivy is the opposite
    return ext.lower().replace('.', '').replace('jpeg', 'jpg') or 'jpg'


def generate_thumbnail_from_bytes(image_bytes, source, **kwargs):
    """ Like :py:func:`.generate_thumbnail`, but takes raw image bytes instead of a path """
    image_bytes.seek(0)
    fmt = get_format(source)
    thumbnail_path = get_thumbnail_path(source)

    if len(image_bytes.getvalue()) > 0:
        return generate_thumbnail(image_bytes, thumbnail_path, fmt=fmt, **kwargs)
    else:
        logger.error(f'Failed to save image bytes to thumbnail for {source}')
        return None


def generate_thumbnail(source, thumbnail_path, fmt=None, size='medium'):
    """
    Generate and store a thumbnail from the source image

    Args:
        source (str): File path or URI for image source
        thumbnail_path (str): Destination path for thumbnail
        fmt (str): Image format to specify to PIL, if it can't be auto-detected
        size (str): One of: 'small', 'medium', 'large'

    Returns:
        str: The path of the new thumbnail
    """
    target_size = get_thumbnail_size(size)
    logger.info(f'Generating {target_size} thumbnail for {source}:\n  {thumbnail_path}')

    # Resize if necessary, or just copy the image to the cache if it's already thumbnail size
    try:
        image = get_orientated_image(source)
        if image.size[0] > target_size[0] or image.size[1] > target_size[1]:
            image.thumbnail(target_size)
        else:
            logger.debug(f'Image is already thumbnail size: ({image.size})')
        image.save(thumbnail_path, fmt=fmt.replace('jpg', 'jpeg') if fmt else None)
        return thumbnail_path

    # If we're unable to generate a thumbnail, just return the original image source
    except RuntimeError as e:
        logger.error('Failed to generate thumbnail:')
        logger.exception(e)
        return source


def get_orientated_image(source):
    """
    Load and rotate/transpose image according to EXIF orientation, if any. If missing orientation
    and the image was fetched from iNat, it will be vertically mirrored. (?)
    """
    image = Image.open(source)
    exif = image.getexif()

    if exif.get(EXIF_ORIENTATION_ID):
        image = exif_transpose(image)
    # TODO: In the future there may be more cases than just local images and remote images from iNat
    elif isinstance(source, IOBase):
        image = flip(image)

    return image
