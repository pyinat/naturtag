from pathlib import Path, PosixPath, PureWindowsPath
from unittest.mock import patch

import pytest

from naturtag.constants import APP_LOGO, ASSETS_DIR, ICONS_DIR
from naturtag.utils.image_glob import get_valid_image_paths, is_raw_path, uri_to_path
from test.conftest import SAMPLE_DATA_DIR


@pytest.mark.parametrize(
    'input, expected',
    [
        ('file:///home/user/img.jpg', '/home/user/img.jpg'),
        ('file:///home/user', '/home/user'),
        ('/home/user/img.jpg', '/home/user/img.jpg'),
    ],
)
@patch('naturtag.utils.image_glob.Path', PosixPath)
def test_uri_to_path__posix(input, expected):
    assert str(uri_to_path(input)) == expected


@pytest.mark.parametrize(
    'input, expected',
    [
        (
            'file:///C:/My%20Pictures/My+Observations/img.jpg',
            'C:\\My Pictures\\My Observations\\img.jpg',
        ),
        (
            'file:///C:/My%20Pictures/My+Observations',
            'C:\\My Pictures\\My Observations',
        ),
        ('C:\\My Pictures\\My Observations\\img.jpg', 'C:\\My Pictures\\My Observations\\img.jpg'),
    ],
)
@patch('naturtag.utils.image_glob.Path', PureWindowsPath)
def test_uri_to_path__windows(input, expected):
    assert str(uri_to_path(input)) == expected


def test_get_valid_image_paths__dir():
    assert len(get_valid_image_paths([ICONS_DIR])) == 6


def test_get_valid_image_paths__glob():
    expected = SAMPLE_DATA_DIR / 'raw_with_sidecar.jpg'
    result_path = list(get_valid_image_paths([f'{SAMPLE_DATA_DIR}/*.jpg']))[0]
    assert result_path == expected

    result_path = list(get_valid_image_paths([SAMPLE_DATA_DIR / '*.jpg']))[0]
    assert result_path == expected


def test_get_valid_image_paths__recursive():
    assert len(get_valid_image_paths([ASSETS_DIR], recursive=True)) == 30


def test_get_valid_image_paths__uri():
    assert get_valid_image_paths([f'file://{APP_LOGO.absolute()}']) == {APP_LOGO}


def test_get_valid_image_paths__sidecar():
    sidecar_path = SAMPLE_DATA_DIR / 'raw_with_sidecar.xmp'
    assert len(get_valid_image_paths([sidecar_path])) == 0
    assert len(get_valid_image_paths([sidecar_path], include_sidecars=True)) == 1


def test_get_valid_image_paths__raw_with_sidecar():
    raw_path = SAMPLE_DATA_DIR / 'raw_with_sidecar.ORF'
    sidecar_path = SAMPLE_DATA_DIR / 'raw_with_sidecar.xmp'
    assert len(get_valid_image_paths([raw_path])) == 0

    # Passing a raw image (or other non-writable file) path should use its sidecar if it exists
    result_path = list(get_valid_image_paths([raw_path], include_sidecars=True))[0]
    assert result_path == sidecar_path


def test_get_valid_image_paths__raw_without_sidecar():
    raw_path = SAMPLE_DATA_DIR / 'raw_without_sidecar.ORF'
    sidecar_path = SAMPLE_DATA_DIR / 'raw_without_sidecar.xmp'  # Doesn't exist
    assert len(get_valid_image_paths([raw_path])) == 0

    # Passing a raw image path should create a sidecar if it doesn't exist
    result_path = list(get_valid_image_paths([raw_path], create_sidecars=True))[0]
    assert result_path == sidecar_path


def test_get_valid_image_paths__glob_raw_with_sidecar():
    raw_glob = SAMPLE_DATA_DIR / '*.ORF'
    sidecar_path = SAMPLE_DATA_DIR / 'raw_with_sidecar.xmp'
    assert len(get_valid_image_paths([raw_glob])) == 0

    result_path = list(get_valid_image_paths([raw_glob], include_sidecars=True))[0]
    assert result_path == sidecar_path


def test_get_valid_image_paths__glob_raw_without_sidecar():
    raw_glob = SAMPLE_DATA_DIR / '*.ORF'
    sidecar_path_1 = SAMPLE_DATA_DIR / 'raw_with_sidecar.xmp'  # exists
    sidecar_path_2 = SAMPLE_DATA_DIR / 'raw_without_sidecar.xmp'  # Doesn't exist
    assert len(get_valid_image_paths([raw_glob])) == 0

    results = list(get_valid_image_paths([raw_glob], include_sidecars=True, create_sidecars=True))
    assert sidecar_path_1 in results
    assert sidecar_path_2 in results


def test_get_valid_image_paths__removes_duplicates():
    assert len(get_valid_image_paths([APP_LOGO, f'file://{APP_LOGO.absolute()}'])) == 1


def test_get_valid_image_paths__nonexistent():
    assert len(get_valid_image_paths(['file://nonexistent', Path('nonexistent')])) == 0


def test_get_valid_image_paths__unsupported_type():
    assert len(get_valid_image_paths([ASSETS_DIR / 'style.qss'])) == 0


@pytest.mark.parametrize(
    'filename, expected',
    [
        ('photo.ORF', True),
        ('photo.orf', True),
        ('photo.cr2', True),
        ('photo.jpg', False),
        ('photo.png', False),
        ('photo.xmp', False),
    ],
)
def test_is_raw_path(filename, expected):
    assert is_raw_path(Path(filename)) == expected


def test_get_valid_image_paths__include_raw_file():
    raw_path = SAMPLE_DATA_DIR / 'raw_with_sidecar.ORF'
    assert len(get_valid_image_paths([raw_path])) == 0
    results = get_valid_image_paths([raw_path], include_raw=True)
    assert raw_path in results


def test_get_valid_image_paths__include_raw_dir():
    results_without = get_valid_image_paths([SAMPLE_DATA_DIR], include_raw=False)
    results_with = get_valid_image_paths([SAMPLE_DATA_DIR], include_raw=True)
    assert len(results_with) > len(results_without)

    raw_paths = results_with - results_without
    assert all(is_raw_path(p) for p in raw_paths)


def test_get_valid_image_paths__include_raw_without_sidecar():
    """RAW files without sidecars are accepted directly when include_raw=True"""
    raw_path = SAMPLE_DATA_DIR / 'raw_without_sidecar.ORF'
    assert len(get_valid_image_paths([raw_path])) == 0
    results = get_valid_image_paths([raw_path], include_raw=True)
    assert raw_path in results
