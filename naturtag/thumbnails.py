from hashlib import md5
from io import BytesIO, IOBase
from os import makedirs
from os.path import isfile, join, splitext
from logging import getLogger

from PIL import Image
from PIL.ImageOps import exif_transpose, flip
from naturtag.constants import (
    THUMBNAILS_DIR,
    THUMBNAIL_SIZE_DEFAULT,
    THUMBNAIL_SIZE_SM,
    THUMBNAIL_SIZE_LG,
    THUMBNAIL_DEFAULT_FORMAT,
)

EXIF_ORIENTATION_ID = '0x0112'
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
    else:
        return None


def get_thumbnail_path(source):
    """
    Determine the thumbnail filename based on a hash of the original file path

    Args:
        source (str): File path or URI for image source
    """
    makedirs(THUMBNAILS_DIR, exist_ok=True)
    thumbnail_hash = md5(source.encode()).hexdigest()
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


def cache_async_thumbnail(async_image, **kwargs):
    """
    Get raw image data from an AsyncImage and cache a thumbnail for future usage.
    See :py:func:`.generate_thumbnail` for size options.

    Args:
        async_image (:py:class:`~kivy.uix.image.AsyncImage`): Image object

    Returns:
        str: The path of the new thumbnail
    """
    thumbnail_path = get_thumbnail_path(async_image.source)
    ext = get_format(thumbnail_path)
    logger.debug(f'Getting image data downloaded from {async_image.source}; format {ext}')

    # Load inner 'texture' bytes into a file-like object that PIL can read
    image_bytes = BytesIO()
    async_image._coreimage.image.texture.save(image_bytes, fmt=ext)
    image_bytes.seek(0)

    if len(image_bytes.getvalue()) > 0:
        return generate_thumbnail(image_bytes, thumbnail_path, fmt=ext, **kwargs)
    else:
        logger.error(f'Failed to save texture to thumbnail: {async_image.source}')
        return None


# TODO: pass in small=True to correctly resize icon-sized taxon thumbs; some are, e.g., 75x79
def generate_thumbnail(source, thumbnail_path, fmt=None, small=False, large=False):
    """
    Generate and store a thumbnail from the source image, in one of 3 sizea; default is 200x200

    Args:
        source (str): File path or URI for image source
        thumbnail_path (str): Destination path for thumbnail
        fmt (str): Image format to specify to PIL, if it can't be auto-detected
        small (bool): Store a smaller thumbnail
        large (bool): Store a larger thumbnail

    Returns:
        str: The path of the new thumbnail
    """
    logger.info(f'Generating new thumbnail for {source}:\n  {thumbnail_path}')

    target_size = THUMBNAIL_SIZE_DEFAULT
    if small:
        target_size = THUMBNAIL_SIZE_SM
    elif large:
        target_size = THUMBNAIL_SIZE_LG

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
