from fnmatch import fnmatch
from glob import glob
from itertools import chain
from logging import getLogger
from os.path import expanduser, isdir, isfile, join
from pathlib import Path
from typing import Union

from naturtag.constants import IMAGE_FILETYPES

logger = getLogger().getChild(__name__)


def glob_paths(path_patterns: list[str]) -> list[str]:
    """
    Given one to many glob patterns, expand all into a list of matching files

    Args:
        path_patterns: Glob patterns

    Returns:
        Expanded list of file paths
    """
    return list(
        chain.from_iterable(
            [expanduser(path) for path in glob(pattern, recursive=True)] for pattern in path_patterns
        )
    )


def get_images_from_dir(dir: str, recursive: bool = False) -> list[str]:
    """
    Get all images of supported filetypes from the selected directory.

    Args:
        dir: Path to image directory
        recursive: Recursively get images from subdirectories

    Returns:
        Paths of supported image files in the directory
    """
    patterns = {f'**/{ext}' for ext in IMAGE_FILETYPES} if recursive else IMAGE_FILETYPES
    paths = glob_paths([join(dir, pattern) for pattern in patterns])
    logger.info(f'{len(paths)} images found in directory: {dir}')
    return paths


def get_images_from_paths(paths: Union[str, bytes, Path], recursive: bool = False) -> list[str]:
    """
    Get all images of supported filetypes from one or more dirs and/or image paths

    Args:
        paths: Paths to images and/or image directories
        recursive: Recursively get images from subdirectories

    Returns:
         Combined list of image file paths
    """
    image_paths = []
    logger.info(f'Getting images from paths: {paths}')

    for path in paths:
        path = path.decode('utf-8') if isinstance(path, bytes) else str(path)
        if isdir(path):
            image_paths.extend(get_images_from_dir(path, recursive=recursive))
        elif is_image_path(path):
            image_paths.append(path)
        else:
            logger.warning(f'Not a valid path: {path}')

    logger.info(f'{len(image_paths)} total images found in paths')
    return image_paths


def is_image_path(path: str) -> bool:
    """Determine if a path points to a valid image of a supported type"""
    return isfile(path) and any(fnmatch(path.lower(), pattern) for pattern in IMAGE_FILETYPES)
