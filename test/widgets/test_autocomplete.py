"""Tests for TaxonAutocomplete widget."""

from types import SimpleNamespace
from unittest.mock import patch

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent

from naturtag.widgets.autocomplete import TaxonAutocomplete


def _make_result(name: str, taxon_id: int) -> SimpleNamespace:
    return SimpleNamespace(name=name, id=taxon_id)


@pytest.fixture
def autocomplete(qtbot, mock_app):
    mock_app.settings.search_locale = False

    with patch('naturtag.widgets.autocomplete.TaxonAutocompleter'):
        widget = TaxonAutocomplete()

    qtbot.addWidget(widget)
    return widget


def test_initial_state(autocomplete):
    assert autocomplete.taxa == {}
    assert autocomplete._last_query == ''
    assert autocomplete.model.stringList() == []


@pytest.mark.parametrize(
    'query,expect_search',
    [
        ('c', False),
        ('ca', True),
    ],
    ids=['single-char', 'two-chars'],
)
def test_do_search__length_threshold(autocomplete, query, expect_search):
    autocomplete.taxon_completer.search.return_value = [_make_result('cat', 1)]
    autocomplete._pending_query = query
    autocomplete._do_search()
    if expect_search:
        autocomplete.taxon_completer.search.assert_called_once_with(query, language=None)
        assert autocomplete._last_query == query
        assert autocomplete.taxa == {'cat': 1}
    else:
        autocomplete.taxon_completer.search.assert_not_called()


def test_do_search__duplicate(autocomplete):
    autocomplete.taxon_completer.search.return_value = [_make_result('cat', 1)]
    autocomplete._pending_query = 'ca'
    autocomplete._do_search()
    autocomplete._do_search()
    autocomplete.taxon_completer.search.assert_called_once()


@pytest.mark.parametrize(
    'raw_query,expected_query',
    [
        ('"acer"', 'acer'),
        ('Ca(t', 'Cat'),
        ('Quercus robur', 'Quercus robur'),
        ('some^query', 'somequery'),
    ],
    ids=['quotes', 'parens', 'valid-name', 'caret'],
)
def test_do_search__sanitize_input(autocomplete, raw_query, expected_query):
    autocomplete.taxon_completer.search.return_value = []
    autocomplete._pending_query = raw_query
    autocomplete._do_search()
    autocomplete.taxon_completer.search.assert_called_once_with(expected_query, language=None)


def test_do_search__sanitize_input__empty(autocomplete):
    """A query that strips down to <=1 char should not trigger a search"""
    autocomplete._pending_query = '\\'
    autocomplete._do_search()
    autocomplete.taxon_completer.search.assert_not_called()


@pytest.mark.parametrize(
    'name,expected',
    [
        ('Catfish', [42]),
        ('Unknown', []),
    ],
    ids=['known-name', 'unknown-name'],
)
def test_select_taxon(autocomplete, name, expected):
    autocomplete.taxa = {'Catfish': 42}
    received = []
    autocomplete.on_select.connect(received.append)
    autocomplete.select_taxon(name)
    assert received == expected


def test_do_search__passes_language_when_search_locale_enabled(autocomplete, mock_app):
    """When search_locale is True, the settings locale is forwarded to the completer."""
    mock_app.settings.search_locale = True
    mock_app.settings.locale = 'fr'
    autocomplete.taxon_completer.search.return_value = []
    autocomplete._pending_query = 'qu'
    autocomplete._do_search()
    autocomplete.taxon_completer.search.assert_called_once_with('qu', language='fr')


def test_do_search__model_string_list(autocomplete):
    autocomplete.taxon_completer.search.return_value = [
        _make_result('Quercus robur', 10),
        _make_result('Quercus alba', 11),
    ]
    autocomplete._pending_query = 'qu'
    autocomplete._do_search()
    assert set(autocomplete.model.stringList()) == {'Quercus robur', 'Quercus alba'}


def test_do_search__clear(autocomplete):
    """An empty result set clears any previously shown completions"""
    autocomplete.taxon_completer.search.return_value = [_make_result('Quercus', 10)]
    autocomplete._pending_query = 'qu'
    autocomplete._do_search()

    autocomplete.taxon_completer.search.return_value = []
    autocomplete._pending_query = 'qx'
    autocomplete._do_search()
    assert autocomplete.model.stringList() == []


def test_schedule_search__debounce(autocomplete):
    """Each call stores the latest query and (re)starts the debounce timer"""
    autocomplete._schedule_search('ab')
    autocomplete._schedule_search('abc')
    assert autocomplete._pending_query == 'abc'
    assert autocomplete._search_timer.isActive()
    autocomplete._search_timer.stop()


@pytest.mark.parametrize(
    'key,expect_emit',
    [
        (Qt.Key_Tab, True),
        (Qt.Key_A, False),
    ],
    ids=['tab', 'non-tab'],
)
def test_key_event(autocomplete, key, expect_emit):
    """Tab key emits on_tab and is consumed; other keys do not emit on_tab"""
    emitted = []
    autocomplete.on_tab.connect(lambda: emitted.append(True))
    key_event = QKeyEvent(QKeyEvent.Type.KeyPress, key, Qt.NoModifier)
    consumed = autocomplete.event(key_event)
    assert bool(emitted) is expect_emit
    if expect_emit:
        assert consumed is True
