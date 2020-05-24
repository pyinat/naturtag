from hashlib import md5
from PIL import Image
from os import makedirs
from os.path import isfile, join, splitext
from logging import getLogger
from naturtag.constants import THUMBNAILS_DIR, THUMBNAIL_SIZE

logger = getLogger().getChild(__name__)


def get_thumbnail(image_path):
    """
    Get a cached thumbnail for an image, if one already exists; otherwise, generate a new one.
    """
    thumbnail_path = get_thumbnail_path(image_path)
    if isfile(thumbnail_path):
        logger.info(f'Found existing thumbnail for {image_path}')
        return thumbnail_path
    else:
        return generate_thumbnail(image_path, thumbnail_path)


def get_thumbnail_path(image_path):
    """ Determine the thumbnail filename based on a hash of the original file path """
    makedirs(THUMBNAILS_DIR, exist_ok=True)
    thumbnail_hash = md5(image_path.encode()).hexdigest()
    return join(THUMBNAILS_DIR, f'{thumbnail_hash}{splitext(image_path)[-1]}')


def generate_thumbnail(image_path, thumbnail_path):
    logger.info(f'Generating new thumbnail for {image_path}:\n  {thumbnail_path}')
    try:
        image = Image.open(image_path)
        image.thumbnail(THUMBNAIL_SIZE)
        image.save(thumbnail_path)
        return thumbnail_path
    # If we're unable to generate a thumbnail, just use the original image
    except RuntimeError as e:
        logger.error('Failed to generate thumbnail:')
        logger.exception(e)
        return image_path
