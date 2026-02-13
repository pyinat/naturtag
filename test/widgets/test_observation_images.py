from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from pyinaturalist import Observation, Photo, Taxon
from PySide6.QtCore import Qt

from naturtag.widgets.observation_images import ObservationInfoCard, ObservationList

THUMB_URL = 'https://static.inaturalist.org/photos/10/square.jpg'


def _make_obs(**kwargs) -> Observation:
    """Build a minimal Observation with sensible defaults, overridable via kwargs"""
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


@pytest.fixture
def observation():
    return _make_obs()


@pytest.fixture
def obs_card(qtbot, observation):
    card = ObservationInfoCard(observation, delayed_load=True)
    qtbot.addWidget(card)
    return card


# --- ObservationInfoCard ---


def test_obs_info_card__default_state(obs_card, observation):
    assert obs_card.card_id == observation.id
    assert obs_card.observation is observation
    assert obs_card.minimumHeight() == 100
    assert obs_card.maximumHeight() == 100


def test_obs_info_card__title__with_taxon(obs_card):
    title = obs_card.title.text()
    assert 'Danaus plexippus' in title
    assert 'Monarch Butterfly' in title
    assert 'Species' in title


def test_obs_info_card__title__without_common_name(qtbot):
    obs = _make_obs(
        taxon=Taxon(id=2, name='Fungus sp.', rank='genus', preferred_common_name=None),
    )
    card = ObservationInfoCard(obs, delayed_load=True)
    qtbot.addWidget(card)
    title = card.title.text()
    assert 'Fungus sp.' in title
    # No parenthesized common name
    assert '(' not in title


def test_obs_info_card__tooltip(obs_card):
    tip = obs_card.toolTip()
    assert 'Portland, OR' in tip
    assert 'research' in tip
    assert 'Danaus plexippus' in tip
    assert '2024-06-15' in tip


@pytest.mark.parametrize('grade', ['casual', 'needs_id', 'research'])
def test_obs_info_card__details__quality_grade_icons(grade):
    """Different quality grades should produce cards without errors"""
    obs = _make_obs(quality_grade=grade)
    card = ObservationInfoCard(obs, delayed_load=True)
    assert card.card_id == 100


def test_obs_info_card__details__with_sounds(qtbot):
    obs = _make_obs(sounds=[{'id': 1}])
    card = ObservationInfoCard(obs, delayed_load=True)
    qtbot.addWidget(card)
    # Should have a sound icon row; card should construct without errors
    assert card.card_id == 100


def test_obs_info_card__on_click(obs_card, qtbot):
    on_click = MagicMock()
    obs_card.on_click.connect(on_click)
    qtbot.mouseClick(obs_card, Qt.LeftButton)
    on_click.assert_called_once_with(100)


# --- ObservationList ---


@pytest.fixture
def obs_list(qtbot):
    lst = ObservationList()
    qtbot.addWidget(lst)
    return lst


@patch('naturtag.widgets.images.set_pixmap_async')
def test_obs_list__add_observation(mock_set_pixmap, obs_list, observation):
    card = obs_list.add_observation(observation)
    assert isinstance(card, ObservationInfoCard)
    assert obs_list.contains(observation.id)
    mock_set_pixmap.assert_called_once()


@patch('naturtag.widgets.images.set_pixmap_async')
def test_obs_list__add_observation__at_index(mock_set_pixmap, obs_list):
    obs_a = _make_obs(id=1)
    obs_b = _make_obs(id=2)
    obs_list.add_observation(obs_a)
    obs_list.add_observation(obs_b, idx=0)
    first = obs_list.root.itemAt(0).widget()
    assert first.card_id == 2


@patch('naturtag.widgets.images.set_pixmap_async')
def test_obs_list__add_or_update__new(mock_set_pixmap, obs_list, observation):
    card = obs_list.add_or_update_observation(observation)
    assert card is not None
    assert obs_list.contains(observation.id)


@patch('naturtag.widgets.images.set_pixmap_async')
def test_obs_list__add_or_update__existing(mock_set_pixmap, obs_list):
    obs = _make_obs(id=5)
    obs_list.add_observation(obs)
    obs_list.add_observation(_make_obs(id=6))
    # Updating should move existing card to idx=0, not create a new one
    result = obs_list.add_or_update_observation(obs, idx=0)
    assert result is None
    first = obs_list.root.itemAt(0).widget()
    assert first.card_id == 5


@patch('naturtag.widgets.images.set_pixmap_async')
def test_obs_list__set_observations(mock_set_pixmap, obs_list):
    # Start with one observation
    obs_list.add_observation(_make_obs(id=1))
    assert obs_list.contains(1)
    # Replace with a new set
    new_obs = [_make_obs(id=10), _make_obs(id=20)]
    obs_list.set_observations(new_obs)
    assert obs_list.root.count() == 2
    assert obs_list.contains(10)
    assert obs_list.contains(20)


@patch('naturtag.widgets.images.set_pixmap_async')
def test_obs_list__set_observations__skips_none(mock_set_pixmap, obs_list):
    obs_list.set_observations([_make_obs(id=1), None, _make_obs(id=2)])
    assert obs_list.root.count() == 2
