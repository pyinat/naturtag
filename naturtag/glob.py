from glob import glob
from logging import getLogger
from os.path import expanduser, isdir, isfile, join

from naturtag.constants import IMAGE_FILETYPES

logger = getLogger().getChild(__name__)


def glob_paths(path_patterns):
    """ Given one to many glob patterns, expand all into a list of files """
    expanded_paths = []
    for pattern in path_patterns:
        expanded_paths.extend([expanduser(path) for path in glob(pattern)])
    return expanded_paths


def get_images_from_dir(dir):
    """ Get all images of supported filetypes from the selected directory """
    paths = glob_paths([join(dir, pattern) for pattern in IMAGE_FILETYPES])
    logger.info(f'{len(paths)} images found in directory: {dir}')
    return paths


def get_images_from_paths(paths):
    """  Get all images of supported filetypes from one or more dirs and/or image paths """
    image_paths = []
    paths = [paths] if isinstance(paths, (str, bytes)) else paths
    logger.info('Getting images from paths: {paths}')

    for path in paths:
        if isinstance(path, bytes):
            path = path.decode('utf-8')
        print('Getting: ', path)
        if isdir(path):
            image_paths.extend(get_images_from_dir(path))
        elif isfile(path):
            image_paths.append(path)
        else:
            logger.warning(f'Not a valid path: {path}')

    logger.info(f'{len(image_paths)} total images found in paths')
    return image_paths
