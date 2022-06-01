from fnmatch import fnmatch
from glob import glob
from itertools import chain
from logging import getLogger
from pathlib import Path

from pyinaturalist import Iterable

from naturtag.constants import IMAGE_FILETYPES, PathOrStr

logger = getLogger().getChild(__name__)


def glob_paths(path_patterns: Iterable[PathOrStr]) -> list[Path]:
    """
    Given one to many glob patterns, expand all into a list of matching files

    Args:
        path_patterns: Glob patterns

    Returns:
        Expanded list of file paths
    """
    return [
        Path(path).expanduser()
        for path in chain.from_iterable(
            glob(str(pattern), recursive=True) for pattern in path_patterns
        )
    ]


def get_images_from_dir(path: Path, recursive: bool = False) -> list[Path]:
    """
    Get all images of supported filetypes from the selected directory.

    Args:
        dir: Path to image directory
        recursive: Recursively get images from subdirectories

    Returns:
        Paths of supported image files in the directory
    """
    patterns = {f'**/{ext}' for ext in IMAGE_FILETYPES} if recursive else IMAGE_FILETYPES
    paths = glob_paths([path / pattern for pattern in patterns])
    logger.info(f'{len(paths)} images found in directory: {path}')
    return paths


def get_valid_image_paths(paths: Iterable[PathOrStr], recursive: bool = False) -> list[Path]:
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
        path = Path(path)
        if path.is_dir():
            image_paths.extend(get_images_from_dir(path, recursive=recursive))
        elif is_image_path(path):
            image_paths.append(path)
        else:
            logger.warning(f'Not a valid path: {path}')

    logger.info(f'{len(image_paths)} total images found in paths')
    return image_paths


def is_image_path(path: Path) -> bool:
    """Determine if a path points to a valid image of a supported type"""
    return path.is_file() and any(fnmatch(path.suffix.lower(), ext) for ext in IMAGE_FILETYPES)
