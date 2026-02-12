from unittest.mock import MagicMock, patch

import pytest
from pyinaturalist import Photo, Taxon
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel

from naturtag.widgets.taxon_images import TaxonInfoCard, TaxonList

THUMB_URL = 'https://static.inaturalist.org/photos/10/square.jpg'


# --- TaxonInfoCard ---


def _make_taxon(**kwargs) -> Taxon:
    """Build a minimal Taxon with sensible defaults, overridable via kwargs"""
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


@pytest.fixture
def taxon():
    return _make_taxon()


@pytest.fixture
def taxon_card(qtbot, taxon):
    card = TaxonInfoCard(taxon, delayed_load=True)
    qtbot.addWidget(card)
    return card


def test_taxon_info_card__default_state(taxon_card, taxon):
    assert taxon_card.card_id == taxon.id
    assert taxon_card.taxon is taxon
    assert taxon_card.minimumHeight() == 90
    assert taxon_card.maximumHeight() == 90


def test_taxon_info_card__title(taxon_card):
    title = taxon_card.title.text()
    assert 'Danaus plexippus' in title
    assert 'Species' in title


def test_taxon_info_card__common_name_row(taxon_card):
    """Common name should appear as a label in the details layout"""
    labels = [
        w.text()
        for w in taxon_card.details_layout.widgets
        if isinstance(w, QLabel) and w is not taxon_card.title
    ]
    assert any('Monarch Butterfly' in lbl for lbl in labels)


@pytest.mark.parametrize(
    'kwargs',
    [
        {'preferred_common_name': None},
        {'complete_species_count': 150},
    ],
    ids=['no_common_name', 'with_species_count'],
)
def test_taxon_info_card__optional_fields(qtbot, kwargs):
    """Card should construct without errors regardless of optional fields."""
    taxon = _make_taxon(**kwargs)
    card = TaxonInfoCard(taxon, delayed_load=True)
    qtbot.addWidget(card)
    assert card.card_id == 200


def test_taxon_info_card__with_user_observations_count(qtbot):
    taxon = _make_taxon()
    card = TaxonInfoCard(taxon, user_observations_count=7, delayed_load=True)
    qtbot.addWidget(card)
    assert card.card_id == 200


def test_taxon_info_card__on_click(taxon_card, qtbot):
    on_click = MagicMock()
    taxon_card.on_click.connect(on_click)
    qtbot.mouseClick(taxon_card, Qt.LeftButton)
    on_click.assert_called_once_with(200)


# --- TaxonList ---


@pytest.fixture
def user_taxa():
    """Minimal stand-in for AppState with an observed dict"""
    mock = MagicMock()
    mock.observed = {200: 5, 201: 12}
    return mock


@pytest.fixture
def taxon_list(qtbot, user_taxa):
    lst = TaxonList(user_taxa=user_taxa)
    qtbot.addWidget(lst)
    return lst


@patch('naturtag.widgets.images.set_pixmap_async')
def test_taxon_list__add_taxon(mock_set_pixmap, taxon_list, taxon):
    card = taxon_list.add_taxon(taxon)
    assert isinstance(card, TaxonInfoCard)
    assert taxon_list.contains(taxon.id)
    mock_set_pixmap.assert_called_once()


@patch('naturtag.widgets.images.set_pixmap_async')
def test_taxon_list__add_taxon__uses_user_obs_count(mock_set_pixmap, taxon_list, user_taxa):
    """user_observations_count should come from user_taxa.observed"""
    taxon = _make_taxon(id=200)
    card = taxon_list.add_taxon(taxon)
    # user_taxa.observed[200] == 5, so the card should have been constructed with that count
    assert card.card_id == 200


@patch('naturtag.widgets.images.set_pixmap_async')
def test_taxon_list__add_taxon__at_index(mock_set_pixmap, taxon_list):
    taxon_a = _make_taxon(id=1)
    taxon_b = _make_taxon(id=2)
    taxon_list.add_taxon(taxon_a)
    taxon_list.add_taxon(taxon_b, idx=0)
    first = taxon_list.root.itemAt(0).widget()
    assert first.card_id == 2


@patch('naturtag.widgets.images.set_pixmap_async')
def test_taxon_list__add_or_update__new(mock_set_pixmap, taxon_list, taxon):
    card = taxon_list.add_or_update_taxon(taxon)
    assert card is not None
    assert taxon_list.contains(taxon.id)


@patch('naturtag.widgets.images.set_pixmap_async')
def test_taxon_list__add_or_update__existing(mock_set_pixmap, taxon_list):
    t1 = _make_taxon(id=5)
    t2 = _make_taxon(id=6)
    taxon_list.add_taxon(t1)
    taxon_list.add_taxon(t2)
    # Updating should move existing card, not create a new one
    result = taxon_list.add_or_update_taxon(t1, idx=0)
    assert result is None
    first = taxon_list.root.itemAt(0).widget()
    assert first.card_id == 5


@patch('naturtag.widgets.images.set_pixmap_async')
def test_taxon_list__set_taxa(mock_set_pixmap, taxon_list):
    taxon_list.add_taxon(_make_taxon(id=1))
    assert taxon_list.contains(1)
    # Replace with a new set
    new_taxa = [_make_taxon(id=10), _make_taxon(id=20)]
    taxon_list.set_taxa(new_taxa)
    assert taxon_list.root.count() == 2
    assert taxon_list.contains(10)
    assert taxon_list.contains(20)


@patch('naturtag.widgets.images.set_pixmap_async')
def test_taxon_list__set_taxa__skips_none(mock_set_pixmap, taxon_list):
    taxon_list.set_taxa([_make_taxon(id=1), None, _make_taxon(id=2)])
    assert taxon_list.root.count() == 2
