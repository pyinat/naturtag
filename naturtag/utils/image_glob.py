"""Utilities for finding and resolving image paths from directories, URIs, and/or glob patterns"""
from fnmatch import fnmatch
from glob import glob
from itertools import chain
from logging import getLogger
from pathlib import Path, PosixPath, PureWindowsPath
from urllib.parse import unquote_plus, urlparse

from pyinaturalist import Iterable

from naturtag.constants import IMAGE_FILETYPES, PathOrStr

logger = getLogger().getChild(__name__)


def get_valid_image_paths(
    paths_or_uris: Iterable[PathOrStr],
    recursive: bool = False,
    include_sidecars: bool = False,
) -> set[Path]:
    """
    Get all images of supported filetypes from one or more dirs and/or image paths, including URIs.

    Args:
        paths: Paths or file URIs to images and/or image directories
        recursive: Recursively get images from subdirectories
        include_sidecars: Allow loading a sidecar file without an associated image

    Returns:
         Combined list of image file paths
    """
    if not paths_or_uris:
        return set()

    image_paths = []
    logger.info(f'Getting images from paths: {paths_or_uris}')

    for path in paths_or_uris:
        if not path:
            continue
        path = uri_to_path(path)
        if path.is_dir():
            image_paths.extend(get_images_from_dir(path, recursive=recursive))
        elif is_image_path(path, include_sidecars=include_sidecars):
            image_paths.append(path)
        else:
            logger.warning(f'Not a valid path: {path}')

    logger.info(f'{len(image_paths)} total images found in paths')
    return set(image_paths)


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


def is_image_path(path: Path, include_sidecars: bool = False) -> bool:
    """Determine if a path points to a valid image of a supported type"""
    valid_exts = IMAGE_FILETYPES
    if include_sidecars:
        valid_exts.append('*.xmp')
    return path.is_file() and any(fnmatch(path.suffix.lower(), ext) for ext in valid_exts)


def uri_to_path(path_or_uri) -> Path:
    """Translate a Path, string, or file URI to a Path. Handles urlencoded and Windows paths"""
    if isinstance(path_or_uri, Path):
        path = path_or_uri
    elif str(path_or_uri).startswith('file://'):
        path = Path(unquote_plus(urlparse(str(path_or_uri)).path))
    else:
        path = Path(path_or_uri)

    if isinstance(path, PureWindowsPath):
        path = Path(str(path).lstrip('\\'))
    elif isinstance(path, PosixPath):
        path = path.expanduser().absolute()

    return path
