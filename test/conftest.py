from pathlib import Path

import prettyprinter
import pytest

from naturtag.app.threadpool import ProgressBar, ThreadPool

prettyprinter.install_extras(exclude=['django'])

DEMO_IMAGES_DIR = Path(__file__).parent.parent / 'assets' / 'demo_images'
SAMPLE_DATA_DIR = Path(__file__).parent / 'sample_data'


@pytest.fixture
def progress_bar(qtbot):
    bar = ProgressBar()
    qtbot.addWidget(bar)
    return bar


@pytest.fixture
def thread_pool(qtbot):
    pool = ThreadPool()
    qtbot.addWidget(pool.progress)
    yield pool
    pool.waitForDone(5000)
