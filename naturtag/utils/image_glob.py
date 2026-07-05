"""Utilities for finding and resolving image paths from directories, URIs, and/or glob patterns"""

from collections import defaultdict
from dataclasses import dataclass
from fnmatch import fnmatch
from glob import glob
from itertools import chain
from logging import getLogger
from pathlib import Path, PosixPath, PureWindowsPath
from typing import Iterator, Optional
from urllib.parse import unquote_plus, urlparse

from pyinaturalist import Iterable

from naturtag.constants import ALL_IMAGE_FILETYPES, IMAGE_FILETYPES, RAW_FILETYPES, PathOrStr

logger = getLogger().getChild(__name__)

# Non-raw extensions that may be paired with a RAW file sharing the same basename.
# Narrower than IMAGE_FILETYPES since gif/webp pairing isn't a real camera workflow.
_PAIRABLE_EXTS = frozenset(('.jpg', '.jpeg', '.png'))


@dataclass(frozen=True)
class ImagePair:
    """A logical image unit: a displayable image file optionally paired with a RAW file sharing
    the same basename. ``image_path`` may itself be a standalone RAW when there is no companion.
    """

    image_path: Path
    raw_path: Optional[Path] = None

    @property
    def all_paths(self) -> list[Path]:
        return [p for p in (self.image_path, self.raw_path) if p is not None]


def get_image_pairs(paths: Iterable[Path]) -> list['ImagePair']:
    """Convert a flat list of image paths into logical :class:`ImagePair` units.

    Paths sharing a basename that form an unambiguous RAW+JPG/PNG pair are grouped into a single
    :class:`ImagePair`. All other paths become standalone pairs with ``raw_path=None``.
    """
    paths = list(paths)
    pairs_dict = find_raw_pairs(paths)
    paired = pairs_dict.keys() | pairs_dict.values()
    result = [ImagePair(companion, raw) for companion, raw in pairs_dict.items()]
    result += [ImagePair(p) for p in paths if p not in paired]
    return result


def get_valid_image_paths(
    paths_or_uris: Iterable[PathOrStr],
    recursive: bool = False,
    include_sidecars: bool = False,
    create_sidecars: bool = False,
    include_raw: bool = False,
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
            image_paths.extend(
                get_images_from_dir(path, recursive=recursive, include_raw=include_raw)
            )
        elif is_image_path(path, include_sidecars=include_sidecars, include_raw=include_raw):
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


def get_images_from_dir(
    path: Path, recursive: bool = False, include_raw: bool = False
) -> list[Path]:
    """
    Get all images of supported filetypes from the selected directory.

    Args:
        dir: Path to image directory
        recursive: Recursively get images from subdirectories
        include_raw: Include RAW image files

    Returns:
        Paths of supported image files in the directory
    """
    filetypes = ALL_IMAGE_FILETYPES if include_raw else IMAGE_FILETYPES
    patterns = [f'**/{ext}' for ext in filetypes] if recursive else filetypes
    paths = [p for pattern in patterns for p in path.glob(pattern, case_sensitive=False)]
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


def is_image_path(path: Path, include_sidecars: bool = False, include_raw: bool = False) -> bool:
    """Determine if a path points to a valid image of a supported type"""
    valid_exts = list(ALL_IMAGE_FILETYPES if include_raw else IMAGE_FILETYPES)
    if include_sidecars:
        valid_exts.append('*.xmp')
    return path.is_file() and any(fnmatch(path.suffix.lower(), ext) for ext in valid_exts)


def is_raw_path(path: Path) -> bool:
    """Determine if a path points to a RAW image file"""
    return any(fnmatch(path.suffix.lower(), ext) for ext in RAW_FILETYPES)


def find_raw_pairs(paths: Iterable[Path]) -> dict[Path, Path]:
    """Find RAW+JPG/PNG pairs sharing a directory and basename (stem, case-insensitive).

    A stem-group is only paired when it contains exactly one RAW file and exactly one
    jpg/jpeg/png; any other combination (2 raw + 1 jpg, 1 raw + 2 jpg, raw + gif, etc.) is left
    ungrouped, since there's no unambiguous partner to pick.

    Returns:
        ``{companion_path: raw_path}``, one entry per confirmed pair, where ``companion_path`` is
        the jpg/png file.
    """
    groups: dict[tuple[Path, str], list[Path]] = defaultdict(list)
    for path in paths:
        groups[(path.parent, path.stem.lower())].append(path)

    pairs = {}
    for group in groups.values():
        raw_paths = [p for p in group if is_raw_path(p)]
        companion_paths = [p for p in group if p.suffix.lower() in _PAIRABLE_EXTS]
        if len(raw_paths) == 1 and len(companion_paths) == 1:
            pairs[companion_paths[0]] = raw_paths[0]
    return pairs


def uri_to_path(path_or_uri) -> Path:
    """Translate a Path, string, or file URI to a Path. Handles urlencoded and Windows paths"""
    if isinstance(path_or_uri, Path):
        path = path_or_uri
    elif str(path_or_uri).startswith('file://'):
        parsed = urlparse(str(path_or_uri))
        path = Path(unquote_plus(parsed.path or parsed.netloc))
    else:
        path = Path(path_or_uri)

    if isinstance(path, PureWindowsPath):
        path = Path(str(path).lstrip('\\'))
    elif isinstance(path, PosixPath):
        path = path.expanduser().absolute()

    return path
