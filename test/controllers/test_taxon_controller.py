"""Tests for TaxonController and TaxonTabs."""

from unittest.mock import MagicMock, patch

import pytest
from pyinaturalist import TaxonCount
from PySide6.QtCore import QSize
from PySide6.QtGui import QResizeEvent

from naturtag.controllers.taxon_controller import TaxonController, TaxonTabs
from test.controllers.conftest import _make_taxon


@pytest.fixture
def controller(qtbot, mock_app):
    with (
        patch('naturtag.controllers.taxon_controller.get_app', return_value=mock_app),
        patch('naturtag.controllers.taxon_search.get_app', return_value=mock_app),
    ):
        ctrl = TaxonController()
    qtbot.addWidget(ctrl)
    return ctrl


@pytest.fixture
def taxon_tabs(qtbot, mock_app):
    with patch('naturtag.controllers.taxon_controller.get_app', return_value=mock_app):
        tabs = TaxonTabs(mock_app.state)
    qtbot.addWidget(tabs)
    return tabs


# --- TaxonController ---


def test_init(controller):
    assert controller.selected_taxon is None


def test_display_taxon_by_id(controller, mock_app):
    mock_app._futures.clear()
    mock_app.threadpool.schedule.reset_mock()

    controller.display_taxon_by_id(42)

    mock_app.threadpool.schedule.assert_called_once()
    assert len(mock_app._futures) == 1


def test_display_taxon_by_id__same_id_skipped(controller, mock_app):
    """No work when same taxon already selected."""
    controller.selected_taxon = _make_taxon(id=42)
    mock_app._futures.clear()
    mock_app.threadpool.schedule.reset_mock()

    controller.display_taxon_by_id(42)

    mock_app.threadpool.schedule.assert_not_called()


@pytest.mark.parametrize(
    'notify, expected_signal_count',
    [(True, 1), (False, 0)],
    ids=['notify', 'no_notify'],
)
def test_display_taxon(controller, notify, expected_signal_count):
    taxon = _make_taxon(id=50)
    on_select = MagicMock()
    controller.on_select.connect(on_select)

    with patch.object(controller.taxon_info, 'load'), patch.object(controller.taxonomy, 'load'):
        controller.display_taxon(taxon, notify=notify)

    assert controller.selected_taxon is taxon
    assert on_select.call_count == expected_signal_count


def test_set_search_results(controller):
    taxa = [_make_taxon(id=i) for i in range(3)]

    controller.set_search_results(taxa)

    assert len(list(controller.tabs.results.cards)) == 3
    assert controller.tabs.currentWidget() is controller.tabs.results.scroller


def test_set_search_results__empty(controller):
    on_message = MagicMock()
    controller.on_message.connect(on_message)

    controller.set_search_results([])

    on_message.assert_any_call('No results found')


def test_bind_selection(controller):
    """bind_selection connects card on_click to display_taxon_by_id."""
    taxa = [_make_taxon(id=i) for i in range(3)]

    on_display = MagicMock()
    controller.display_taxon_by_id = on_display
    controller.set_search_results(taxa)
    cards = list(controller.tabs.results.cards)

    cards[0].on_click.emit(cards[0].card_id)
    on_display.assert_called_once_with(cards[0].card_id)


# --- TaxonTabs ---


def test_tabs_init(taxon_tabs):
    assert taxon_tabs.count() == 4


def test_display_recent(taxon_tabs, mock_app):
    """Populates recent and frequent tabs from taxa list."""
    t1 = _make_taxon(id=10)
    t2 = _make_taxon(id=20)
    mock_app.state.top_history = [10, 20]
    mock_app.state.top_frequent = [20]
    mock_app.state.view_count.return_value = 5

    taxon_tabs.display_recent([t1, t2])

    assert len(list(taxon_tabs.recent.cards)) == 2
    assert len(list(taxon_tabs.frequent.cards)) == 1


def test_display_observed(taxon_tabs, mock_app):
    """Populates observed tab, calls update_observed and write on AppState."""
    tc = TaxonCount(id=10, name='Species A', rank='species', count=5)

    taxon_tabs.display_observed([tc])

    assert len(list(taxon_tabs.observed.cards)) == 1
    mock_app.state.update_observed.assert_called_once()
    mock_app.state.write.assert_called_once()


@pytest.mark.parametrize(
    'frequent_idx, expect_in_frequent',
    [(None, False), (0, True)],
    ids=['new_taxon', 'frequent_taxon'],
)
def test_update_history(taxon_tabs, mock_app, frequent_idx, expect_in_frequent):
    taxon = _make_taxon(id=300)
    mock_app.state.frequent_idx.return_value = frequent_idx
    on_load = MagicMock()
    taxon_tabs.on_load.connect(on_load)

    taxon_tabs.update_history(taxon)

    mock_app.state.update_history.assert_called_once_with(300)
    assert taxon_tabs.recent.contains(300)
    assert taxon_tabs.frequent.contains(300) == expect_in_frequent
    on_load.assert_called()


def test_resize__wide(taxon_tabs):
    """Tab labels shown when width > 90*count."""
    taxon_tabs.resize(500, 400)

    assert taxon_tabs.tabText(0) == 'Results'
    assert taxon_tabs.tabText(1) == 'Recent'


def test_resize__narrow(taxon_tabs):
    """Tab labels hidden when width <= 90*count."""
    taxon_tabs.setMinimumWidth(0)
    taxon_tabs.setFixedWidth(100)
    taxon_tabs.resizeEvent(QResizeEvent(QSize(100, 400), QSize(500, 400)))

    for i in range(taxon_tabs.count()):
        assert taxon_tabs.tabText(i) == ''
