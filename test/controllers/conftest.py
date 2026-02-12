"""Shared fixtures for controller tests."""

import time
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from pyinaturalist import Observation, Photo, Taxon

from naturtag.app.threadpool import WorkerSignals

THUMB_URL = 'https://static.inaturalist.org/photos/10/square.jpg'


def _make_taxon(**kwargs) -> Taxon:
    """Build a minimal Taxon with sensible defaults, overridable via kwargs."""
    defaults = {
        'id': 200,
        'name': 'Danaus plexippus',
        'rank': 'species',
        'preferred_common_name': 'Monarch Butterfly',
        'observations_count': 50000,
        'complete_species_count': None,
        'default_photo': Photo(id=10, url=THUMB_URL),
    }
    defaults.update(kwargs)
    return Taxon(**defaults)


def _make_obs(**kwargs) -> Observation:
    """Build a minimal Observation with sensible defaults, overridable via kwargs."""
    defaults = {
        'id': 100,
        'taxon': Taxon(
            id=1,
            name='Danaus plexippus',
            rank='species',
            preferred_common_name='Monarch Butterfly',
        ),
        'photos': [Photo(id=10, url=THUMB_URL)],
        'observed_on': datetime(2024, 6, 15),
        'created_at': datetime(2024, 6, 16),
        'place_guess': 'Portland, OR',
        'location': (45.5, -122.6),
        'quality_grade': 'research',
        'identifications_count': 3,
        'num_identification_agreements': 2,
        'positional_accuracy': 10,
        'sounds': [],
    }
    defaults.update(kwargs)
    return Observation(**defaults)


def _make_schedule_side_effect(futures: list[WorkerSignals]):
    """Create a side_effect for threadpool.schedule that returns real WorkerSignals.

    Appends each created WorkerSignals instance to ``futures`` so tests can
    inspect or emit on them.
    """

    def side_effect(*args, **kwargs):
        signals = WorkerSignals()
        futures.append(signals)
        return signals

    return side_effect


@pytest.fixture
def mock_app(qapp):
    """Attach mock attributes to the real QApplication for controller testing.

    Controllers access the app via ``QApplication.instance()`` (through
    ``BaseController.app``), so attaching mocks directly to ``qapp`` avoids
    the need to patch that property.
    """
    futures: list[WorkerSignals] = []

    qapp.settings = MagicMock()
    qapp.settings.username = 'testuser'
    qapp.settings.locale = 'en'
    qapp.settings.casual_observations = False
    qapp.settings.preferred_place_id = None
    qapp.settings.all_ranks = False
    qapp.settings.db_path = '/tmp/test.db'

    qapp.client = MagicMock()
    qapp.client.observations.count_db.return_value = 0

    qapp.state = MagicMock()
    qapp.state.display_ids = set()
    qapp.state.top_history = []
    qapp.state.top_frequent = []
    qapp.state.top_observed = []
    qapp.state.observed = {}
    qapp.state.starred = []

    qapp.threadpool = MagicMock()
    qapp.threadpool.schedule.side_effect = _make_schedule_side_effect(futures)
    qapp.threadpool.schedule_paginator.side_effect = _make_schedule_side_effect(futures)

    qapp.img_session = MagicMock()

    # Expose futures list so tests can inspect signals returned by schedule()
    qapp._futures = futures

    yield qapp

    # Flush pending QTimer.singleShot callbacks (e.g. TaxonTabs.load_user_taxa at 2ms)
    # before removing mock attrs, so they don't crash against a bare QApplication.
    time.sleep(0.01)
    qapp.processEvents()

    # Cleanup: remove mock attributes so they don't leak into non-controller tests
    for attr in (
        'settings',
        'client',
        'state',
        'threadpool',
        'img_session',
        '_futures',
    ):
        try:
            delattr(qapp, attr)
        except AttributeError:
            pass


@pytest.fixture(autouse=True)
def _mock_set_pixmap(request):
    """Autouse fixture to prevent sync and async pixmap loading in controller tests."""
    with (
        patch('naturtag.widgets.images.set_pixmap_async'),
        patch('naturtag.widgets.images.set_pixmap'),
        patch('naturtag.widgets.taxon_images.set_pixmap'),
        patch('naturtag.widgets.observation_images.set_pixmap'),
    ):
        yield
