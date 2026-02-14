"""Tests for ObservationController."""

from unittest.mock import MagicMock, patch

import pytest

from naturtag.controllers.observation_controller import DbPageResult, ObservationController
from test.conftest import _make_obs


@pytest.fixture
def controller(qtbot, mock_app):
    ctrl = ObservationController()
    qtbot.addWidget(ctrl)
    return ctrl


def test_init(controller):
    assert controller.page == 1
    assert controller.total_pages == 0
    assert controller.total_results == 0
    assert controller.displayed_observation is None


def test_display_observation_by_id(controller, mock_app):
    mock_app._futures.clear()
    controller.display_observation_by_id(42)

    mock_app.threadpool.schedule.assert_called()
    assert len(mock_app._futures) >= 1


def test_display_observation_by_id__same_id_skipped(controller, mock_app):
    """No work scheduled when the same observation is already displayed."""
    controller.displayed_observation = _make_obs(id=42)
    mock_app._futures.clear()
    mock_app.threadpool.schedule.reset_mock()

    controller.display_observation_by_id(42)

    mock_app.threadpool.schedule.assert_not_called()


def test_display_observation(controller):
    obs = _make_obs(id=99)
    with patch.object(controller.obs_info, 'load') as mock_load:
        controller.display_observation(obs)

    assert controller.displayed_observation is obs
    mock_load.assert_called_once_with(obs)


def test_display_user_observations(controller):
    observations = [_make_obs(id=i) for i in range(3)]
    controller.total_results = 15

    controller.display_user_observations(observations)

    assert len(list(controller.user_observations.cards)) == 3
    assert 'My Observations (15)' in controller.user_obs_group_box.box.title()


@pytest.mark.parametrize(
    'page, total_pages, loaded_pages, action, expected_page',
    [
        (2, 5, 5, 'next', 3),
        (3, 3, 3, 'next', 3),  # at limit
        (2, 10, 2, 'next', 2),  # limited by loaded_pages
        (3, 5, 5, 'prev', 2),
        (1, 5, 5, 'prev', 1),  # at start
    ],
    ids=['next', 'next__at_limit', 'next__limited_by_loaded_pages', 'prev', 'prev__at_start'],
)
def test_pagination(controller, mock_app, page, total_pages, loaded_pages, action, expected_page):
    controller.page = page
    controller.total_pages = total_pages
    controller.loaded_pages = loaded_pages
    mock_app._futures.clear()

    getattr(controller, f'{action}_page')()

    assert controller.page == expected_page


@pytest.mark.parametrize(
    'page, total_pages, loaded_pages, prev_enabled, next_enabled, label',
    [
        (2, 5, 5, True, True, 'Page 2 / 5'),
        (1, 3, 3, False, True, 'Page 1 / 3'),
        (3, 3, 3, True, False, 'Page 3 / 3'),
    ],
    ids=['middle', 'first', 'last'],
)
def test_update_pagination_buttons(
    controller, page, total_pages, loaded_pages, prev_enabled, next_enabled, label
):
    controller.page = page
    controller.total_pages = total_pages
    controller.loaded_pages = loaded_pages

    controller.update_pagination_buttons()

    assert controller.prev_button.isEnabled() == prev_enabled
    assert controller.next_button.isEnabled() == next_enabled
    assert controller.page_label.text() == label


def test_cold_start(controller, mock_app):
    """When DB count is 0: _is_cold_start=True, returns empty list, title shows 'loading...'."""
    mock_app.client.observations.count_db.return_value = 0

    result = controller._get_db_page()

    assert result.is_empty is True
    assert result.observations == []
    assert result.total_results == 0

    # State mutation happens in on_db_page_loaded (main thread)
    controller.on_db_page_loaded(result)
    assert controller._is_cold_start is True
    assert 'loading...' in controller.user_obs_group_box.box.title()


def test_warm_start(controller, mock_app):
    """When DB has data: _is_cold_start=False, loaded_pages=total_pages."""
    mock_app.client.observations.count_db.return_value = 75
    mock_app.client.observations.search_user_db.return_value = [_make_obs(id=i) for i in range(50)]

    result = controller._get_db_page()

    assert result.is_empty is False
    assert result.total_results == 75
    assert len(result.observations) == 50

    # State mutation happens in on_db_page_loaded (main thread)
    controller.on_db_page_loaded(result)
    assert controller._is_cold_start is False
    assert controller.total_results == 75
    assert controller.total_pages == 2  # ceil(75/50)
    assert controller.loaded_pages == controller.total_pages


def test_on_sync_page_received(controller, mock_app):
    controller.loaded_pages = 0

    controller.on_sync_page_received([_make_obs(id=i) for i in range(10)])

    assert controller.loaded_pages == 1


def test_on_sync_page_received__persists_resume_id(controller, mock_app):
    """After receiving a sync page, sync_resume_id is set to the max observation ID."""
    controller.loaded_pages = 0
    observations = [_make_obs(id=5), _make_obs(id=20), _make_obs(id=12)]

    controller.on_sync_page_received(observations)

    assert mock_app.state.sync_resume_id == 20
    mock_app.state.write.assert_called()


def test_on_sync_page_received__cold_start_trigger(controller, mock_app):
    """When _is_cold_start and loaded_pages==1, triggers load_observations_from_db."""
    controller._is_cold_start = True
    controller.loaded_pages = 0
    mock_app._futures.clear()

    controller.on_sync_page_received([_make_obs(id=i) for i in range(10)])

    assert controller.loaded_pages == 1
    assert len(mock_app._futures) >= 1


def test_on_sync_complete(controller, mock_app):
    mock_app._futures.clear()
    controller._sync_in_progress = True
    controller.on_sync_complete()

    assert controller._sync_in_progress is False
    assert mock_app.state.sync_resume_id is None
    mock_app.state.set_obs_checkpoint.assert_called_once()
    assert len(mock_app._futures) >= 1  # load_observations_from_db was called


def test_refresh(controller, mock_app):
    controller._page_cache[1] = [_make_obs(id=1)]
    controller._page_cache[2] = [_make_obs(id=2)]
    controller.page = 3
    mock_app._futures.clear()

    controller.refresh()

    assert controller.page == 1
    assert controller.loaded_pages == 0
    assert len(controller._page_cache) == 0
    assert mock_app.state.sync_resume_id is None
    assert controller._sync_in_progress is True
    assert mock_app.threadpool.schedule.called
    assert mock_app.threadpool.schedule_paginator.called


def test_refresh__blocked_while_sync_in_progress(controller, mock_app):
    """Refresh is a no-op (with status message) when a sync is already running."""
    controller._sync_in_progress = True
    controller.page = 3
    mock_app._futures.clear()
    mock_app.threadpool.schedule_paginator.reset_mock()

    with patch.object(controller, 'info') as mock_info:
        controller.refresh()

    mock_info.assert_called_once_with('Refresh already in progress')
    assert controller.page == 3  # unchanged
    mock_app.threadpool.schedule_paginator.assert_not_called()


def test_load_observations__cache_hit(controller, mock_app):
    observations = [_make_obs(id=i) for i in range(3)]
    controller._page_cache[1] = observations
    controller.total_results = 10
    mock_app._futures.clear()
    mock_app.threadpool.schedule.reset_mock()

    controller.load_observations_from_db()

    mock_app.threadpool.schedule.assert_not_called()
    assert len(list(controller.user_observations.cards)) == 3


def test_page_cache__lru_eviction(controller, mock_app):
    """Page cache evicts least-recently-used pages when exceeding max size."""
    for p in range(1, 21):
        controller.page = p
        result = DbPageResult([_make_obs(id=p)], total_results=100, is_empty=False)
        controller.on_db_page_loaded(result)

    # Access page 1 to make it recently used
    controller.page = 1
    controller.load_observations_from_db()

    # Add page 21 — should evict page 2
    controller.page = 21
    result = DbPageResult([_make_obs(id=21)], total_results=100, is_empty=False)
    controller.on_db_page_loaded(result)

    assert 2 not in controller._page_cache
    assert set(controller._page_cache.keys()) == set(range(1, 22)) - {2}


def test_on_sync_complete__clears_cache(controller, mock_app):
    controller._page_cache[1] = [_make_obs(id=1)]
    controller.on_sync_complete()
    assert len(controller._page_cache) == 0


def test_bind_selection(controller):
    observations = [_make_obs(id=i) for i in range(3)]
    controller.user_observations.set_observations(observations)
    cards = list(controller.user_observations.cards)

    on_click = MagicMock()
    controller.display_observation_by_id = on_click
    controller.bind_selection(cards)

    cards[0].on_click.emit(cards[0].card_id)
    on_click.assert_called_once_with(cards[0].card_id)


def test_sync_observations__passes_resume_id(controller, mock_app):
    """_sync_observations passes sync_resume_id as id_above to the client."""
    mock_app.state.last_obs_check = None
    mock_app.state.sync_resume_id = 42
    mock_app.client.observations.search_user_paginated.return_value = iter([])

    list(controller._sync_observations())

    mock_app.client.observations.search_user_paginated.assert_called_once_with(
        username='testuser',
        updated_since=None,
        id_above=42,
    )
