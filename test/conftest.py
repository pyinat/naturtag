import os
import time
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import prettyprinter
import pytest
from pyinaturalist import Observation, Photo, Taxon
from PySide6.QtWidgets import QMenu, QWidget

from naturtag.app.threadpool import ProgressBar, ThreadPool, WorkerSignals
from naturtag.storage import Settings

prettyprinter.install_extras(exclude=['django'])

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

DEMO_IMAGES_DIR = Path(__file__).parent.parent / 'assets' / 'demo_images'
SAMPLE_DATA_DIR = Path(__file__).parent / 'sample_data'
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
    """Create a side_effect for threadpool.schedule that returns real WorkerSignals."""

    def side_effect(*args, **kwargs):
        signals = WorkerSignals()
        futures.append(signals)
        return signals

    return side_effect


@pytest.fixture
def mock_app(qapp, tmp_path):
    """Attach mock attributes to the real QApplication for MainWindow testing.

    Uses a real Settings object (with defaults) so that SettingsMenu can read
    all settings attributes correctly. Additional attributes needed by
    MainWindow (progress widget, log handler widget, user_dirs) are provided
    as real Qt objects or mocks.
    """
    futures: list[WorkerSignals] = []

    settings = Settings(path=tmp_path / 'settings.yml')
    settings.username = 'testuser'
    settings.debug = False
    qapp.settings = settings

    qapp.client = MagicMock()
    qapp.client.observations.count_db.return_value = 0

    qapp.state = MagicMock()
    qapp.state.window_size = (800, 600)
    qapp.state.display_ids = set()
    qapp.state.top_history = []
    qapp.state.top_frequent = []
    qapp.state.top_observed = []
    qapp.state.observed = {}
    qapp.state.starred = []

    qapp.threadpool = MagicMock()
    qapp.threadpool.progress = QWidget()
    qapp.threadpool.schedule.side_effect = _make_schedule_side_effect(futures)
    qapp.threadpool.schedule_paginator.side_effect = _make_schedule_side_effect(futures)

    qapp.log_handler = MagicMock()
    qapp.log_handler.widget = QWidget()

    qapp.img_session = MagicMock()

    qapp.user_dirs = MagicMock()
    qapp.user_dirs.on_dir_open = MagicMock()
    qapp.user_dirs.favorite_dirs_submenu = QMenu('Favorites')
    qapp.user_dirs.recent_dirs_submenu = QMenu('Recent')

    qapp._futures = futures

    yield qapp

    time.sleep(0.01)
    qapp.processEvents()

    for attr in (
        'settings',
        'client',
        'state',
        'threadpool',
        'log_handler',
        'img_session',
        'user_dirs',
        '_futures',
    ):
        try:
            delattr(qapp, attr)
        except AttributeError:
            pass


@pytest.fixture(autouse=True)
def _mock_set_pixmap(request):
    """Prevent sync and async pixmap loading in app tests."""
    with (
        patch('naturtag.widgets.images.set_pixmap_async'),
        patch('naturtag.widgets.images.set_pixmap'),
        patch('naturtag.widgets.taxon_images.set_pixmap'),
        patch('naturtag.widgets.observation_images.set_pixmap'),
    ):
        yield


@pytest.fixture
def progress_bar(qtbot):
    bar = ProgressBar()
    qtbot.addWidget(bar)
    yield bar
    bar.reset_timer.stop()


@pytest.fixture
def thread_pool(qtbot):
    pool = ThreadPool()
    qtbot.addWidget(pool.progress)
    yield pool
    pool.waitForDone(5000)
    qtbot.wait(10)  # Flush queued signals while pool is still alive
    pool.progress.reset_timer.stop()
