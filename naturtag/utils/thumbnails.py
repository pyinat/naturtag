"""Utilities for generating and retrieving image thumbnails"""
from io import IOBase
from logging import getLogger

from PIL import Image
from PIL.ImageOps import exif_transpose, flip
from PIL.ImageQt import ImageQt
from PySide6.QtGui import QPixmap

from naturtag.constants import EXIF_ORIENTATION_ID, SIZE_DEFAULT, Dimensions, PathOrStr

logger = getLogger().getChild(__name__)


def generate_thumbnail(
    path: PathOrStr,
    target_size: Dimensions = SIZE_DEFAULT,
    default_flip: bool = True,
) -> QPixmap:
    """Generate a thumbnail from the source image

    Args:
        path: Image file path
        target_size: Max dimensions for thumbnail

    Returns:
        Thumbnail data as a pixmap
    """
    logger.debug(f'Thumbnails: Generating {target_size} thumbnail for {path}')

    # Resize if necessary, or just copy the image to the cache if it's already thumbnail size
    try:
        image = _get_orientated_image(path, default_flip=default_flip)
        image = _crop_square(image)
        if image.size[0] > target_size[0] or image.size[1] > target_size[1]:
            image.thumbnail(target_size)
        else:
            logger.debug(f'Thumbnails: Image is already thumbnail size: ({image.size})')

        return QPixmap.fromImage(ImageQt(image))

    # If we're unable to generate a thumbnail, just return the original image source
    except RuntimeError:
        logger.warning('Thumbnails: Failed to generate thumbnail')
        return None


def _get_orientated_image(source, default_flip: bool = True) -> Image:
    """
    Load and rotate/transpose image according to EXIF orientation, if any. If missing orientation
    and the image was fetched from iNat, it will be vertically mirrored. (?)
    """
    image = Image.open(source)
    exif = image.getexif()

    if exif.get(EXIF_ORIENTATION_ID):
        image = exif_transpose(image)
    # TODO: In the future there may be more cases than just local images and remote images from iNat
    elif default_flip and isinstance(source, IOBase):
        image = flip(image)

    return image


def _crop_square(image: Image) -> Image:
    """Crop an image into a square (retaining dimension of short edge)"""
    width, height = image.size
    short_edge = min(width, height)
    if width == height:
        return image

    return image.crop(
        (
            (width - short_edge) // 2,
            (height - short_edge) // 2,
            (width + short_edge) // 2,
            (height + short_edge) // 2,
        )
    )
