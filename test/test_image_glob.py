from pathlib import Path, PosixPath, PureWindowsPath
from unittest.mock import patch

import pytest

from naturtag.constants import APP_LOGO, ASSETS_DIR, ICONS_DIR
from naturtag.utils.image_glob import get_valid_image_paths, uri_to_path


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


def test_get_valid_image_paths__recursive():
    assert len(get_valid_image_paths([ASSETS_DIR], recursive=True)) == 28


def test_get_valid_image_paths__uri():
    assert get_valid_image_paths([f'file://{APP_LOGO.absolute()}']) == {APP_LOGO}


def test_get_valid_image_paths__removes_duplicates():
    assert len(get_valid_image_paths([APP_LOGO, f'file://{APP_LOGO.absolute()}'])) == 1


def test_get_valid_image_paths__nonexistent():
    assert len(get_valid_image_paths(['file://nonexistent', Path('nonexistent')])) == 0


def test_get_valid_image_paths__unsupported_type():
    assert len(get_valid_image_paths([ASSETS_DIR / 'style.qss'])) == 0
