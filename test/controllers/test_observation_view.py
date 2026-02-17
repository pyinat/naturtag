"""Tests for ObservationInfoSection, ActivityCard, and related helpers."""

from datetime import datetime
from unittest.mock import patch

import pytest
from pyinaturalist import Comment, Identification, Taxon, User

from naturtag.controllers.observation_view import (
    CommentCard,
    IdentificationCard,
    ObservationInfoSection,
    _format_location,
    _sort_id_comments,
)
from test.conftest import _make_obs

_USER = User(id=1, login='testuser')
_TAXON = Taxon(id=200, name='Danaus plexippus', rank='species')


def _make_identification(**kwargs) -> Identification:
    defaults = {
        'id': 10,
        'user': _USER,
        'taxon': _TAXON,
        'created_at': datetime(2024, 1, 1, 12, 0),
        'current': True,
    }
    defaults.update(kwargs)
    return Identification(**defaults)


def _make_comment(**kwargs) -> Comment:
    defaults = {
        'id': 20,
        'user': _USER,
        'body': 'Nice find!',
        'created_at': datetime(2024, 1, 2, 12, 0),
    }
    defaults.update(kwargs)
    return Comment(**defaults)


@pytest.fixture
def obs_info(qtbot, mock_app):
    with patch('naturtag.controllers.observation_view.set_pixmap_async'):
        widget = ObservationInfoSection()
        qtbot.addWidget(widget)
        yield widget


@pytest.mark.parametrize(
    'obs_kwargs, expected',
    [
        ({'location': (45.1234, -122.5678)}, '(45.1234, -122.5678)'),
        (
            {'location': (45.1234, -122.5678), 'geoprivacy': 'obscured'},
            '(45.1234, -122.5678) (obscured)',
        ),
        ({'location': None}, 'N/A'),
    ],
)
def test_format_location(obs_kwargs, expected):
    assert _format_location(_make_obs(**obs_kwargs)) == expected


def test_sort_id_comments__chronological():
    """Items are sorted by created_at regardless of type."""
    id1 = _make_identification(id=10, created_at=datetime(2024, 1, 1))
    comment = _make_comment(id=20, created_at=datetime(2024, 1, 3))
    id2 = _make_identification(id=11, created_at=datetime(2024, 1, 2))
    obs = _make_obs(identifications=[id1, id2], comments=[comment])

    result = _sort_id_comments(obs)

    assert result == [id1, id2, comment]


def test_sort_id_comments__empty():
    obs = _make_obs(identifications=[], comments=[])
    assert _sort_id_comments(obs) == []


def test_identification_card__content(qtbot, mock_app):
    """Header contains username, second label contains taxon link."""
    item = _make_identification(body='Agreed!')
    card = IdentificationCard(item)
    qtbot.addWidget(card)
    labels = [w.text() for w in card.content.widgets]

    assert any('testuser' in t for t in labels)
    assert any('Danaus plexippus' in t for t in labels)
    assert any('Agreed!' in t for t in labels)


def test_identification_card__no_body(qtbot, mock_app):
    """An identification with no body shows header and taxon label only."""
    item = _make_identification(body='')
    card = IdentificationCard(item)
    qtbot.addWidget(card)
    assert len(list(card.content.widgets)) == 2  # header + taxon


def test_identification_card__no_taxon(qtbot, mock_app):
    """An identification without a taxon shows header and body only."""
    item = _make_identification(taxon=None, body='test body')
    card = IdentificationCard(item)
    qtbot.addWidget(card)
    labels = [w.text() for w in card.content.widgets]
    assert len(labels) == 2  # header + body, no taxon label
    assert any('test body' in t for t in labels)


def test_identification_card__emits_taxon_id(qtbot, mock_app):
    """Activating the taxon link emits on_view_taxon_by_id with the taxon's id."""
    item = _make_identification()
    card = IdentificationCard(item)
    qtbot.addWidget(card)

    labels = list(card.content.widgets)
    taxon_label = labels[1]  # header is [0], taxon link is [1]

    with qtbot.waitSignal(card.on_view_taxon_by_id) as blocker:
        taxon_label.linkActivated.emit('#')

    assert blocker.args == [200]


def test_comment_card__content(qtbot, mock_app):
    """Header contains username, body label contains comment text."""
    item = _make_comment(body='Nice find!')
    card = CommentCard(item)
    qtbot.addWidget(card)
    labels = [w.text() for w in card.content.widgets]

    assert any('testuser' in t for t in labels)
    assert any('Nice find!' in t for t in labels)


def test_obs_info_load__same_id_is_noop(obs_info):
    """Calling load() with the same observation ID does not re-render."""
    obs = _make_obs(id=42)
    obs_info.load(obs)
    obs_info.group_box.setTitle('init')

    obs_info.load(obs)
    assert obs_info.group_box.title() == 'init'


def test_obs_info_load__populates_activity(obs_info):
    """load() creates one card per identification/comment in chronological order."""
    id1 = _make_identification()
    comment = _make_comment()
    obs = _make_obs(identifications=[id1], comments=[comment])

    obs_info.load(obs)
    cards = list(obs_info.id_comments_container.widgets)
    assert len(cards) == 2
    assert isinstance(cards[0], IdentificationCard)
    assert isinstance(cards[1], CommentCard)


def test_obs_info_load__clears_previous_activity(obs_info):
    """Loading a new observation replaces, not appends to, the activity cards."""
    obs_info.load(_make_obs(id=1, identifications=[_make_identification()], comments=[]))
    obs_info.load(_make_obs(id=2, identifications=[], comments=[_make_comment()]))

    cards = list(obs_info.id_comments_container.widgets)
    assert len(cards) == 1
    assert isinstance(cards[0], CommentCard)


def test_obs_info_on_view_taxon_by_id(qtbot, obs_info):
    """Activating an identification taxon link propagates on_view_taxon_by_id."""
    id1 = _make_identification()
    obs = _make_obs(identifications=[id1], comments=[])
    obs_info.load(obs)

    card = list(obs_info.id_comments_container.widgets)[0]
    taxon_label = list(card.content.widgets)[1]

    with qtbot.waitSignal(obs_info.on_view_taxon_by_id) as blocker:
        taxon_label.linkActivated.emit('#')

    assert blocker.args == [200]
