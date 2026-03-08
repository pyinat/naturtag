"""Tests for naturtag/storage/client.py"""

from unittest.mock import MagicMock

import pytest
from pyinaturalist import Observation, Photo

from naturtag.storage.client import ObservationDbController

THUMB_URL = 'https://static.inaturalist.org/photos/10/square.jpg'


@pytest.fixture
def obs_controller() -> ObservationDbController:
    mock_client = MagicMock()
    mock_taxon_controller = MagicMock()
    controller = ObservationDbController(mock_client, taxon_controller=mock_taxon_controller)
    return controller


def _make_obs_page(ids: list[int]) -> list[Observation]:
    return [Observation(id=i, photos=[Photo(id=i, url=THUMB_URL)]) for i in ids]


def test_search_user_db_paginated__yields_pages(obs_controller):
    """Yields each non-empty page in order."""
    page1 = _make_obs_page([1, 2, 3])
    page2 = _make_obs_page([4, 5, 6])
    obs_controller.search_user_db = MagicMock(side_effect=[page1, page2, []])

    pages = list(obs_controller.search_user_db_paginated(username='testuser'))

    assert pages == [page1, page2]


def test_search_user_db_paginated__empty_db(obs_controller):
    """Yields nothing when the DB is empty."""
    obs_controller.search_user_db = MagicMock(return_value=[])

    pages = list(obs_controller.search_user_db_paginated(username='testuser'))

    assert pages == []


def test_search_user_db_paginated__calls_each_page(obs_controller):
    """Calls search_user_db with incrementing page numbers."""
    obs_controller.search_user_db = MagicMock(side_effect=[_make_obs_page([1]), []])

    list(obs_controller.search_user_db_paginated(username='testuser'))

    calls = obs_controller.search_user_db.call_args_list
    assert calls[0].kwargs['page'] == 1
    assert calls[1].kwargs['page'] == 2
