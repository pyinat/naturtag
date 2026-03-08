"""Tests for naturtag/storage/remote_images.py"""

from unittest.mock import create_autospec, patch

import pytest

from naturtag.storage.remote_images import ImageFetcher

THUMB_URL = 'https://static.inaturalist.org/photos/10/square.jpg'


@pytest.fixture
def fetcher(tmp_path) -> ImageFetcher:
    with patch('naturtag.storage.remote_images.ClientSession'):
        f = ImageFetcher(cache_path=tmp_path / 'images.db')
    f.get_image = create_autospec(f.get_image)  # type: ignore[method-assign]
    return f


def test_precache_image(fetcher):
    """precache_image calls get_image once per URL."""
    url1 = THUMB_URL
    url2 = 'https://static.inaturalist.org/photos/10/medium.jpg'
    fetcher.precache_image([url1, url2])

    assert fetcher.get_image.call_count == 2


def test_precache_image__empty(fetcher):
    """precache_image does nothing for an empty URL list."""
    fetcher.precache_image([])

    fetcher.get_image.assert_not_called()


def test_precache_image__suppresses_errors(fetcher):
    """precache_image suppresses exceptions and continues processing remaining URLs."""
    url1 = THUMB_URL
    url2 = 'https://static.inaturalist.org/photos/10/medium.jpg'
    fetcher.get_image.side_effect = [Exception('Network error'), b'data']

    fetcher.precache_image([url1, url2])

    assert fetcher.get_image.call_count == 2
