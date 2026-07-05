"""Tests for ImageController."""

from pathlib import Path
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
    assert controller.selected_observation is None


def test_run__no_images(controller):
    on_message = MagicMock()
    controller.on_message.connect(on_message)

    controller.run()

    on_message.assert_any_call('Select images to tag')


def test_run__no_selection(controller):
    """Has images but no taxon/observation selected."""
    controller.gallery._cards = [MagicMock(image_path='/tmp/img.jpg', raw_path=None)]
    on_message = MagicMock()
    controller.on_message.connect(on_message)

    controller.run()

    on_message.assert_any_call('Select either an observation or an organism to tag images with')


def _run_and_invoke_scheduled_task(controller, mock_app, result_metadata=None, side_effect=None):
    """Call controller.run(), then extract and invoke the scheduled per-card callable."""
    mock_kwargs = (
        {'side_effect': side_effect} if side_effect else {'return_value': [result_metadata]}
    )
    with patch('naturtag.controllers.image_controller.tag_images', **mock_kwargs) as mock_tag:
        controller.run()
        scheduled_fn = mock_app.threadpool.schedule.call_args[0][0]
        scheduled_card = mock_app.threadpool.schedule.call_args[1]['card']
        result = scheduled_fn(scheduled_card)
    return result, mock_tag


@pytest.mark.parametrize(
    'taxon_id, obs_id',
    [(42, None), (None, 99)],
    ids=['with_taxon', 'with_observation'],
)
def test_run__schedules_tagging(controller, mock_app, taxon_id, obs_id):
    card = MagicMock(image_path='/tmp/img.jpg', raw_path=None)
    controller.gallery._cards = [card]
    controller.selected_taxon_id = taxon_id
    controller.selected_observation_id = obs_id
    mock_app._futures.clear()
    mock_app.threadpool.schedule.reset_mock()

    result_metadata = MagicMock(image_path='/tmp/img.jpg')
    result, mock_tag = _run_and_invoke_scheduled_task(controller, mock_app, result_metadata)

    mock_app.threadpool.schedule.assert_called_once()
    mock_tag.assert_called_once()
    assert result is result_metadata


def test_run__batches_paired_paths_into_one_task(controller, mock_app):
    """A RAW+JPG pair (same card under two dict keys) is tagged in a single threadpool task,
    not two, to avoid two threads racing to write the same shared sidecar file."""
    card = MagicMock(image_path='/tmp/photo.jpg', raw_path='/tmp/photo.CR2')
    controller.gallery._cards = [card]
    controller.selected_taxon_id = 42
    mock_app._futures.clear()
    mock_app.threadpool.schedule.reset_mock()

    result_metadata = MagicMock(image_path='/tmp/photo.jpg')
    result, mock_tag = _run_and_invoke_scheduled_task(controller, mock_app, result_metadata)

    mock_app.threadpool.schedule.assert_called_once()
    assert mock_tag.call_args[0][0] == ['/tmp/photo.jpg', '/tmp/photo.CR2']
    assert result is result_metadata


def test_run__reports_failed_tagging_via_info_message(controller, mock_app):
    """When the companion (JPG) path's write fails but the paired RAW's write succeeds, tag_card
    surfaces the failure via self.info() instead of silently leaving the card 'pending' with no
    explanation."""
    card = MagicMock(image_path='/tmp/photo.jpg', raw_path='/tmp/photo.CR2')
    controller.gallery._cards = [card]
    controller.selected_taxon_id = 42
    mock_app._futures.clear()
    mock_app.threadpool.schedule.reset_mock()
    on_message = MagicMock()
    controller.on_message.connect(on_message)

    def fake_tag_images(
        paths, obs_id=None, taxon_id=None, client=None, settings=None, failed_paths=None
    ):
        # Simulates the JPG's write failing while the paired RAW's write succeeds.
        failed_paths.append(Path('/tmp/photo.jpg'))
        return [MagicMock(image_path='/tmp/photo.CR2')]

    result, _ = _run_and_invoke_scheduled_task(controller, mock_app, side_effect=fake_tag_images)

    assert result is None
    on_message.assert_any_call('Failed to tag: photo.jpg')


def test_update_metadata__skips_visual_update_for_raw_path(controller):
    """update_metadata only applies the visual update when metadata is for the card's companion
    path, so a paired RAW file's tagging result doesn't double-pulse the card."""
    card = MagicMock(image_path='/tmp/photo.jpg', raw_path='/tmp/photo.CR2')
    controller.gallery._cards = [card]

    controller.update_metadata(MagicMock(image_path='/tmp/photo.CR2'))
    card.update_metadata.assert_not_called()

    controller.update_metadata(MagicMock(image_path='/tmp/photo.jpg'))
    card.update_metadata.assert_called_once()


def test_update_metadata__no_raise_when_card_already_removed(controller):
    """A tagging result arriving after its card was removed mid-flight is silently
    ignored instead of raising KeyError, and doesn't touch unrelated loaded cards."""
    other_card = MagicMock(image_path='/tmp/other.jpg', raw_path=None)
    controller.gallery._cards = [other_card]

    controller.update_metadata(MagicMock(image_path='/tmp/removed.jpg'))

    other_card.update_metadata.assert_not_called()


def test_select_taxon(controller):
    controller.select_taxon(_make_taxon(id=42))

    assert controller.selected_taxon_id == 42
    assert controller.selected_observation_id is None
    assert controller.selected_observation is None


def test_select_taxon__clears_selected_observation(controller):
    """Selecting a taxon clears a previously stored observation object."""
    controller.selected_observation = _make_obs(id=99)

    controller.select_taxon(_make_taxon(id=42))

    assert controller.selected_observation is None


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
    controller.selected_observation = _make_obs(id=99)

    controller.clear()

    assert controller.selected_taxon_id is None
    assert controller.selected_observation_id is None
    assert controller.selected_observation is None


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


def test_refresh__deduplicates_paired_cards(controller, mock_app):
    """refresh() schedules exactly one task per unique card, even when paired with a RAW file."""
    card = MagicMock(image_path='/tmp/photo.jpg', raw_path='/tmp/photo.CR2')
    controller.gallery._cards = [card]
    mock_app.threadpool.schedule.reset_mock()

    controller.refresh()

    mock_app.threadpool.schedule.assert_called_once()


def test_refresh__passes_paired_raw_path(controller, mock_app):
    """refresh() forwards a card's raw_path to _refresh_tags, so a paired RAW file's metadata
    is refreshed alongside its companion instead of being silently skipped."""
    card = MagicMock(image_path='/tmp/photo.jpg', raw_path='/tmp/photo.CR2')
    controller.gallery._cards = [card]
    mock_app.threadpool.schedule.reset_mock()

    controller.refresh()

    scheduled_fn = mock_app.threadpool.schedule.call_args[0][0]
    assert scheduled_fn.args[0] is card.metadata
    assert scheduled_fn.keywords['raw_path'] == '/tmp/photo.CR2'


@pytest.mark.parametrize(
    'method, arg, expected_pending',
    [
        ('select_taxon', _make_taxon(id=42), frozenset({'taxon', 'tags', 'sidecar'})),
        (
            'select_observation',
            _make_obs(id=99, location=(45.5, -122.6)),
            frozenset({'taxon', 'observation', 'tags', 'geo', 'sidecar'}),
        ),
        (
            'select_observation',
            _make_obs(id=99, location=None),
            frozenset({'taxon', 'observation', 'tags', 'sidecar'}),
        ),
    ],
    ids=['taxon', 'observation_with_geo', 'observation_without_geo'],
)
def test_selection_changed_signal__emits_pending_frozenset(
    controller, method, arg, expected_pending
):
    """select_taxon and select_observation emit the correct frozenset of pending icon keys.

    settings.sidecar defaults to True in tests, so 'sidecar' is always included.
    """
    handler = MagicMock()
    controller.on_selection_changed.connect(handler)

    getattr(controller, method)(arg)

    handler.assert_called_once()
    assert handler.call_args[0][0] == expected_pending


def test_selection_changed_signal__no_sidecar_when_disabled(controller):
    """'sidecar' is excluded from the pending set when settings.sidecar is False."""
    controller.app.settings.sidecar = False
    handler = MagicMock()
    controller.on_selection_changed.connect(handler)

    controller.select_taxon(_make_taxon(id=42))

    emitted = handler.call_args[0][0]
    assert 'sidecar' not in emitted


def test_selection_changed_signal__clear_emits_empty_frozenset(controller):
    """clear() emits on_selection_changed with an empty frozenset."""
    handler = MagicMock()
    controller.on_selection_changed.connect(handler)

    controller.clear()

    handler.assert_called_once()
    assert handler.call_args[0][0] == frozenset()
