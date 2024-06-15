"""Utilities for finding and resolving image paths from directories, URIs, and/or glob patterns"""

from fnmatch import fnmatch
from glob import glob
from itertools import chain
from logging import getLogger
from pathlib import Path, PosixPath, PureWindowsPath
from typing import Iterator
from urllib.parse import unquote_plus, urlparse

from pyinaturalist import Iterable

from naturtag.constants import IMAGE_FILETYPES, PathOrStr

logger = getLogger().getChild(__name__)


def get_valid_image_paths(
    paths_or_uris: Iterable[PathOrStr],
    recursive: bool = False,
    include_sidecars: bool = False,
    create_sidecars: bool = False,
) -> set[Path]:
    """
    Get all images of supported filetypes from one or more dirs and/or image paths, including URIs.

    Notes on sidecar files:

    * Directly passing a path to a sidecar file is allowed
    * When passing a path to a file that is not writeable (e.g., RAW images), a sidecar file will be
      created or updated for it

    Args:
        paths: Paths or file URIs to images and/or image directories
        recursive: Recursively get images from subdirectories
        include_sidecars: Allow loading a sidecar file without an associated image
        create_sidecars: Create a new sidecar file if a non-writeable file path is provided

    Returns:
         Combined list of image file paths
    """
    if not paths_or_uris:
        return set()

    image_paths = []
    logger.debug(f'Getting images from paths: {paths_or_uris}')

    for path in _expand_globs(paths_or_uris):
        if not path:
            continue

        path = uri_to_path(path)
        sidecar_path = get_sidecar_path(path)
        if path.is_dir():
            image_paths.extend(get_images_from_dir(path, recursive=recursive))
        elif '*' in str(path):
            image_paths.extend(glob_paths([path]))
        elif is_image_path(path, include_sidecars=include_sidecars):
            image_paths.append(path)
        elif include_sidecars and sidecar_path.is_file():
            logger.debug(f'{path} is not writable; using existing sidecar: {sidecar_path}')
            image_paths.append(sidecar_path)
        elif path.is_file() and create_sidecars:
            logger.debug(f'{path} is not writable; creating sidecar: {sidecar_path}')
            image_paths.append(sidecar_path)
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
    logger.debug(f'{len(paths)} images found in directory: {path}')
    return paths


def _expand_globs(paths: Iterable[PathOrStr]) -> Iterator[PathOrStr]:
    """Expand any glob patterns in a list of paths"""
    for path in paths:
        if '*' in str(path):
            yield from glob_paths([path])
        else:
            yield path


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


def get_sidecar_path(path: Path) -> Path:
    default_path = path.with_suffix('.xmp')
    alt_path = path.with_suffix(f'{path.suffix}.xmp')
    return alt_path if alt_path.is_file() else default_path


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
