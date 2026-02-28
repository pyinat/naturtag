"""Tests for naturtag/storage/app_state.py"""

from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from naturtag.constants import MAX_DISPLAY_HISTORY, MAX_DISPLAY_OBSERVED
from naturtag.storage.app_state import AppState, _top_unique_ids


@pytest.fixture
def db_path(tmp_path) -> Path:
    return tmp_path / 'naturtag.db'


@pytest.fixture
def state(db_path) -> AppState:
    s = AppState()
    s.db_path = db_path
    return s


@pytest.mark.parametrize(
    'ids, n, expected',
    [
        ([1, 2, 3, 1, 2], 10, [1, 2, 3]),
        ([3, 1, 2, 1, 3], 2, [3, 1]),
        ([], 5, []),
        ([1, 1, 1], 5, [1]),
    ],
)
def test_top_unique_ids(ids, n, expected):
    assert _top_unique_ids(ids, n) == expected


def test_app_state__frequent_initialized_from_history():
    s = AppState(history=[1, 2, 1, 3, 1])
    assert s.frequent == Counter({1: 3, 2: 1, 3: 1})


def test_update_history__appends_and_counts(state):
    state.update_history(10)
    state.update_history(20)
    state.update_history(10)

    assert state.history == [10, 20, 10]
    assert state.frequent[10] == 2
    assert state.frequent[20] == 1


def test_update_observed(state):
    state.observed = {99: 100}
    state.update_observed([MagicMock(id=1, count=5), MagicMock(id=2, count=3)])
    assert state.observed == {1: 5, 2: 3}


@pytest.mark.parametrize(
    'history, taxon_id, expected',
    [
        ([], 999, 0),
        ([5, 5], 5, 2),
    ],
)
def test_view_count(state, history, taxon_id, expected):
    for t in history:
        state.update_history(t)
    assert state.view_count(taxon_id) == expected


@pytest.mark.parametrize(
    'prop, setup',
    [
        (
            'top_history',
            lambda s: setattr(s, 'history', list(range(MAX_DISPLAY_HISTORY + 10))),
        ),
        (
            'top_frequent',
            lambda s: setattr(
                s, 'frequent', Counter({i: i for i in range(MAX_DISPLAY_HISTORY + 10)})
            ),
        ),
        (
            'top_observed',
            lambda s: setattr(s, 'observed', {i: i for i in range(MAX_DISPLAY_OBSERVED + 10)}),
        ),
    ],
)
def test_top_list(state, prop, setup):
    setup(state)
    result = getattr(state, prop)
    expected_max = MAX_DISPLAY_OBSERVED if prop == 'top_observed' else MAX_DISPLAY_HISTORY
    assert len(result) == expected_max


def test_top_history(state):
    # 1 viewed first, 2 viewed second, 1 viewed again → most recent unique order is [1, 2]
    state.history = [1, 2, 1]
    assert state.top_history == [1, 2]


def test_top_frequent():
    s = AppState(history=[1, 2, 1, 3, 1, 2])
    assert s.top_frequent[0] == 1
    assert s.top_frequent[1] == 2


@pytest.mark.parametrize(
    'taxon_id, expected',
    [
        (1, 0),
        (2, 1),
        (999, None),
    ],
)
def test_frequent_idx(state, taxon_id, expected):
    state.frequent = Counter({1: 10, 2: 5, 3: 1})
    assert state.frequent_idx(taxon_id) == expected


def test_top_observed(state):
    state.observed = {10: 5, 20: 3, 30: 1}
    assert state.top_observed == [10, 20, 30]


def test_display_ids__combines_all_sources_as_set(state):
    state.history = [1, 1, 2]
    state.frequent = Counter(state.history)
    state.observed = {3: 1}
    state.starred = [4]
    assert state.display_ids == {1, 2, 3, 4}


@pytest.mark.parametrize(
    'prev, current, expected_setup_complete, expected_prev',
    [
        ('0.0.1', '0.0.2', False, '0.0.2'),  # version bump resets setup
        ('1.0.0', '1.0.0', True, '1.0.0'),  # same version is a no-op
    ],
)
def test_check_version_change(state, prev, current, expected_setup_complete, expected_prev):
    state.setup_complete = True
    state.prev_version = prev
    state._version = None
    with patch('naturtag.storage.app_state.pkg_version', return_value=current):
        state.check_version_change()
    assert state.setup_complete is expected_setup_complete
    assert state.prev_version == expected_prev


def test_set_obs_checkpoint__sets_utc_time_and_writes(state):
    before = datetime.now(timezone.utc).replace(microsecond=0)

    with patch.object(state, 'write') as mock_write:
        state.set_obs_checkpoint()

    after = datetime.now(timezone.utc).replace(microsecond=0)
    assert before <= state.last_obs_check <= after
    mock_write.assert_called_once()


def test_read__db_missing(db_path):
    missing_db = db_path.parent / 'nonexistent.db'
    loaded = AppState.read(missing_db)
    assert loaded.history == []
    assert loaded.setup_complete is False
    assert loaded.db_path == missing_db


def test_write(state, db_path):
    state.history = [1, 2]
    state.write()

    state.history = [3, 4]
    state.write()

    loaded = AppState.read(db_path)
    assert loaded.history == [3, 4]


def test_read_write_round_trip(state):
    state.history = [1, 2, 3]
    state.starred = [10, 20]
    state.observed = {5: 3}
    state.setup_complete = True
    state.write()

    loaded = AppState.read(state.db_path)
    assert loaded.history == [1, 2, 3]
    assert loaded.starred == [10, 20]
    assert loaded.observed == {5: 3}
    assert loaded.setup_complete is True


def test_str(state):
    state.history = [1, 2]
    state.starred = [3]
    state.observed = {4: 1}
    state.frequent = Counter(state.history)
    result = str(state)
    assert 'History: 2' in result
    assert 'Starred: 1' in result
    assert 'Observed: 1' in result
