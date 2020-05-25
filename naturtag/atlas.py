""" Utilities for intelligently combining thumbnail images into a Kivy Atlas """
from logging import getLogger
from math import ceil
from PIL import Image

from naturtag.constants import (
    ATLAS_MAX_SIZE, THUMBNAILS_DIR, THUMBNAIL_SIZE_DEFAULT, THUMBNAIL_SIZE_SM, THUMBNAIL_SIZE_LG)
from naturtag.glob import get_images_from_paths

logger = getLogger().getChild(__name__)


def build_taxon_icon_atlas():
    build_atlas(THUMBNAILS_DIR, *THUMBNAIL_SIZE_SM, 'taxon_icons', max_size=ATLAS_MAX_SIZE)


def build_taxon_photo_atlas():
    build_atlas(THUMBNAILS_DIR, *THUMBNAIL_SIZE_LG, 'taxon_photos', max_size=ATLAS_MAX_SIZE)


def build_local_photo_atlas():
    build_atlas(THUMBNAILS_DIR, *THUMBNAIL_SIZE_DEFAULT, 'local_photos', max_size=ATLAS_MAX_SIZE)


def build_atlas(image_paths, src_x, src_y, atlas_name, padding=2, **limit_kwarg):
    """ Build a Kivy  Kivy :py:class:`~kivy.atlas.Atlas`

    Args:
        image_paths (list): Paths to images and/or image directories
        src_x: Max width of source images
        src_y: Max height of source images
        atlas_name: Name of atlas file to create
        \\*\\*limit_kwarg: At most one limit to provide to :py:func:`.get_atlas_dimensions`
    """
    from kivy.atlas import Atlas

    # Allow smallest dimension to be as low as half the max. This this works because each thumbnail
    # size category is over twice the size of the next smallest one
    min_x = ceil(src_x / 2)
    min_y = ceil(src_y / 2)
    logger.info(f'Searching for images of dimensions ({min_x}-{src_x}) x ({min_y}-{src_y})...')
    image_paths = list(filter_images_by_size(image_paths, src_x, src_y, min_x, min_y))
    logger.info(f'{len(image_paths)} images found')

    atlas_size = get_atlas_dimensions(len(image_paths), src_x, src_y, padding=padding, **limit_kwarg)
    logger.info(f'Calculated atlas size: {atlas_size}')
    Atlas.create(atlas_name, image_paths, atlas_size, padding=padding)


def filter_images_by_size(image_paths, max_x, max_y, min_x, min_y):
    """ Get all images from the specified paths that are within specified dimensions.
    See also :py:func:`.get_images_from_paths`

    Args:
        image_paths (list): Paths to images and/or image directories
        max_x (int): Return only images this width or smaller
        max_y (int): Return only images this height or smaller
        min_x (int): Return only images this width or larger
        min_y (int): Return only images this height or larger

    Returns:
        list: Filtered list of image file paths
    """
    for image_path in get_images_from_paths(image_paths):
        img = Image.open(image_path)
        img_x, img_y = img.size
        img.close()
        if min_x <= img_x <= max_x and min_y< img_y <= max_y:
            yield image_path


def get_atlas_dimensions(n_images, x, y, padding=2, max_size=None, max_bins=None, max_per_bin=None):
    """ Get the ideal dimensions of a Kivy :py:class:`~kivy.atlas.Atlas` in which to store images
    of mostly uniform size.
    'Ideal' in this case means the smallest rectangle, with minimal wasted space, with closest to
    square x and y dimensions, and within specified limit of dimensions, # of bins, or
    # of images per bin. Only one of these limit parameters (``max_*``) may be provided.

    Args:
        n_images (str): Number of images to combine
        x (int): Horizontal dimension of images
        y (int): Vertical dimension of images
        padding (int): Amount of padding per image, in pixels
        max_size (int): Maximum dimension (x or y) of combined atlas image; beyond that multiple
            atlas images will be created
        max_bins (int): The maximum number of atlas images to produce
        max_per_bin (int): Maximum number of images per bin

    Returns:
        ``int, int``: Ideal atlas dimensions
    """
    if len(list(filter(None, [max_size, max_bins, max_per_bin]))) > 1:
        raise ValueError('Only one max limit may be provided')
    if n_images == 0:
        return 0, 0

    # Apply limit (if any) round up to nearest even int; a small amount of wasted space is okay
    if max_bins:
        n_images = ceil(n_images / max_bins)
    if max_per_bin:
        n_images = min(n_images, max_per_bin)
    if n_images % 2 == 1:
        n_images += 1

    # Get total atlas dimensions that will fit all the thumbnails
    x += padding; y += padding
    factors = _largest_factor_pair(n_images)
    factor_x = _max_factor(x, factors[0], max_size)
    factor_y = _max_factor(y, factors[1], max_size)
    return x * factor_x, y * factor_y


def _max_factor(n, factor, max_size):
    """ Return the largest factor that will fit within the provided max """
    if not max_size or n * factor <= max_size:
        return factor
    else:
        return _max_factor(n, factor-1, max_size)


def _largest_factor_pair(n):
    """ Get the largest pair of factors for the given number """
    for i in reversed(range(1, int(n**0.5) + 1)):
        if n % i == 0:
            return i, int(n/i)
    return n, 1
