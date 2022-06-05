from pathlib import Path, PosixPath, PureWindowsPath
from unittest.mock import patch

import pytest

from naturtag.constants import ASSETS_DIR
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
    assert len(get_valid_image_paths([ASSETS_DIR])) == 2


def test_get_valid_image_paths__recursive():
    assert len(get_valid_image_paths([ASSETS_DIR], recursive=True)) == 22


def test_get_valid_image_paths__uri():
    logo = ASSETS_DIR / 'logo.png'
    assert get_valid_image_paths([f'file://{logo.absolute()}']) == {logo}


def test_get_valid_image_paths__removes_duplicates():
    logo = ASSETS_DIR / 'logo.png'
    assert len(get_valid_image_paths([ASSETS_DIR, logo, f'file://{logo.absolute()}'])) == 2


def test_get_valid_image_paths__nonexistent():
    assert len(get_valid_image_paths(['file://nonexistent', Path('nonexistent')])) == 0


def test_get_valid_image_paths__unsupported_type():
    assert len(get_valid_image_paths([ASSETS_DIR / 'style.qss'])) == 0
