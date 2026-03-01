"""Tests for ImageController."""

from unittest.mock import MagicMock, patch

import pytest

from naturtag.controllers.image_controller import ImageController
from test.conftest import _make_obs, _make_taxon


@pytest.fixture
def controller(qtbot, mock_app):
    with patch('naturtag.controllers.image_controller.get_app', return_value=mock_app):
        ctrl = ImageController()
    qtbot.addWidget(ctrl)
    return ctrl


def test_init(controller):
    assert controller.selected_taxon_id is None
    assert controller.selected_observation_id is None


def test_run__no_images(controller):
    on_message = MagicMock()
    controller.on_message.connect(on_message)

    controller.run()

    on_message.assert_any_call('Select images to tag')


def test_run__no_selection(controller):
    """Has images but no taxon/observation selected."""
    controller.gallery.images = {'/tmp/img.jpg': MagicMock()}
    on_message = MagicMock()
    controller.on_message.connect(on_message)

    controller.run()

    on_message.assert_any_call('Select either an observation or an organism to tag images with')


@pytest.mark.parametrize(
    'taxon_id, obs_id',
    [(42, None), (None, 99)],
    ids=['with_taxon', 'with_observation'],
)
def test_run__schedules_tagging(controller, mock_app, taxon_id, obs_id):
    controller.gallery.images = {'/tmp/img.jpg': MagicMock()}
    controller.selected_taxon_id = taxon_id
    controller.selected_observation_id = obs_id
    mock_app._futures.clear()
    mock_app.threadpool.schedule.reset_mock()

    controller.run()

    mock_app.threadpool.schedule.assert_called_once()


@pytest.mark.parametrize(
    'taxon_id, obs_id',
    [(42, None), (None, 99)],
    ids=['with_taxon', 'with_observation'],
)
def test_run__calls_tag_images(controller, mock_app, taxon_id, obs_id):
    controller.gallery.images = {'/tmp/img.jpg': MagicMock()}
    controller.selected_taxon_id = taxon_id
    controller.selected_observation_id = obs_id
    mock_app._futures.clear()
    mock_app.threadpool.schedule.reset_mock()

    with patch(
        'naturtag.controllers.image_controller.tag_images', return_value=[MagicMock()]
    ) as mock_tag:
        controller.run()
        # Extract and invoke the callable that was scheduled
        scheduled_fn = mock_app.threadpool.schedule.call_args[0][0]
        scheduled_fn(image_path='/tmp/img.jpg')

    mock_tag.assert_called_once()


def test_select_taxon(controller):
    controller.select_taxon(_make_taxon(id=42))

    assert controller.selected_taxon_id == 42
    assert controller.selected_observation_id is None


def test_select_taxon__same_id_skipped(controller):
    """No update when same taxon already selected."""
    controller.selected_taxon_id = 42

    controller.select_taxon(_make_taxon(id=42))

    assert controller.selected_taxon_id == 42


def test_select_observation(controller):
    controller.select_observation(_make_obs(id=99))

    assert controller.selected_observation_id == 99
    assert controller.selected_taxon_id is None


def test_select_observation__same_id_skipped(controller):
    """No update when same observation already selected."""
    controller.selected_observation_id = 99

    controller.select_observation(_make_obs(id=99))

    assert controller.selected_observation_id == 99


@pytest.mark.parametrize(
    'method, id_attr, value',
    [
        ('select_taxon_by_id', 'selected_taxon_id', 42),
        ('select_observation_by_id', 'selected_observation_id', 99),
    ],
    ids=['taxon', 'observation'],
)
def test_select_by_id(controller, mock_app, method, id_attr, value):
    mock_app._futures.clear()
    mock_app.threadpool.schedule.reset_mock()

    with patch('naturtag.controllers.image_controller.get_app', return_value=mock_app):
        getattr(controller, method)(value)

    mock_app.threadpool.schedule.assert_called_once()


@pytest.mark.parametrize(
    'method, id_attr, value',
    [
        ('select_taxon_by_id', 'selected_taxon_id', 42),
        ('select_observation_by_id', 'selected_observation_id', 99),
    ],
    ids=['taxon', 'observation'],
)
def test_select_by_id__same_id_skipped(controller, mock_app, method, id_attr, value):
    setattr(controller, id_attr, value)
    mock_app.threadpool.schedule.reset_mock()

    with patch('naturtag.controllers.image_controller.get_app', return_value=mock_app):
        getattr(controller, method)(value)

    mock_app.threadpool.schedule.assert_not_called()


def test_clear(controller):
    controller.selected_taxon_id = 42
    controller.selected_observation_id = 99

    controller.clear()

    assert controller.selected_taxon_id is None
    assert controller.selected_observation_id is None


@pytest.mark.parametrize(
    'url, expected_method',
    [
        ('https://www.inaturalist.org/observations/12345', 'select_observation_by_id'),
        ('https://www.inaturalist.org/taxa/48978', 'select_taxon_by_id'),
    ],
    ids=['observation_url', 'taxon_url'],
)
def test_paste__url(controller, mock_app, url, expected_method):
    mock_app.threadpool.schedule.reset_mock()

    with (
        patch('naturtag.controllers.image_controller.QApplication.clipboard') as mock_clipboard,
        patch('naturtag.controllers.image_controller.get_app', return_value=mock_app),
    ):
        mock_clipboard.return_value.text.return_value = url
        controller.paste()

    mock_app.threadpool.schedule.assert_called_once()


def test_paste__image_paths(controller):
    with patch('naturtag.controllers.image_controller.QApplication.clipboard') as mock_clipboard:
        mock_clipboard.return_value.text.return_value = '/tmp/photo1.jpg\n/tmp/photo2.jpg'
        with patch.object(controller.gallery, 'load_images') as mock_load:
            controller.paste()

    mock_load.assert_called_once_with(['/tmp/photo1.jpg', '/tmp/photo2.jpg'])


def test_refresh__no_images(controller):
    on_message = MagicMock()
    controller.on_message.connect(on_message)

    controller.refresh()

    on_message.assert_any_call('Select images to tag')
