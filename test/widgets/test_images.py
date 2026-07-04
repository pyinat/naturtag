from unittest.mock import MagicMock, patch

import pytest
from PIL import Image
from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QLabel

from naturtag.widgets.images import (
    ImageWindow,
    InfoCard,
    InfoCardList,
    PixmapLabel,
    SwappableIcon,
    format_int,
)
from test.conftest import SAMPLE_DATA_DIR


@pytest.fixture
def pixmap_label(qtbot):
    label = PixmapLabel()
    qtbot.addWidget(label)
    return label


@pytest.fixture
def sample_pixmap():
    """A small non-null pixmap for testing"""
    return QPixmap(200, 100)


@pytest.fixture
def info_card(qtbot):
    card = InfoCard(card_id=42)
    qtbot.addWidget(card)
    return card


@pytest.fixture
def image_window(qtbot, mock_app):
    window = ImageWindow()
    qtbot.addWidget(window)
    return window


@pytest.fixture
def info_card_list(qtbot):
    card_list = InfoCardList()
    qtbot.addWidget(card_list)
    return card_list


@pytest.mark.parametrize(
    'value, expected',
    [
        (0, '0'),
        (999, '999'),
        (1000, '1000'),
        (9999, '9999'),
        (10000, '10K'),
        (50000, '50K'),
        (999999, '999K'),
        (1000000, '1M'),
        (5000000, '5M'),
    ],
)
def test_format_int(value, expected):
    assert format_int(value) == expected


# --- SwappableIcon ---


@pytest.fixture
def swappable_icon(qtbot, mock_app):
    icon = SwappableIcon('mdi.bird', secondary=True, size=20)
    qtbot.addWidget(icon)
    return icon


def test_swappable_fa_icon__set_primary__changes_pixmap(swappable_icon):
    """set_primary() swaps between primary and secondary pixmaps."""
    secondary_pixmap = swappable_icon.pixmap().toImage()

    swappable_icon.set_primary(True)
    primary_pixmap = swappable_icon.pixmap().toImage()

    swappable_icon.set_primary(False)
    restored_pixmap = swappable_icon.pixmap().toImage()

    assert primary_pixmap != secondary_pixmap
    assert restored_pixmap == secondary_pixmap


# --- PixmapLabel ---


def test_pixmap_label__default_state(pixmap_label):
    assert pixmap_label._pixmap is not None
    assert pixmap_label._pixmap.isNull()
    assert pixmap_label.path is None
    assert pixmap_label.description is None
    assert pixmap_label.rounded is False
    assert pixmap_label.scale is True
    assert pixmap_label.idx == 0


def test_pixmap_label__init_with_pixmap(qtbot, sample_pixmap):
    label = PixmapLabel(pixmap=sample_pixmap)
    qtbot.addWidget(label)
    assert not label._pixmap.isNull()
    assert label._pixmap.width() == 200
    assert label._pixmap.height() == 100


def test_pixmap_label__init_with_options(qtbot):
    label = PixmapLabel(description='test desc', rounded=True, scale=False, idx=5)
    qtbot.addWidget(label)
    assert label.description == 'test desc'
    assert label.rounded is True
    assert label.scale is False
    assert label.idx == 5


def test_pixmap_label__set_pixmap(pixmap_label, sample_pixmap):
    pixmap_label.setPixmap(sample_pixmap)
    assert not pixmap_label._pixmap.isNull()
    assert pixmap_label._pixmap.width() == 200
    assert pixmap_label._pixmap.height() == 100


def test_pixmap_label__clear(pixmap_label, sample_pixmap):
    pixmap_label.setPixmap(sample_pixmap)
    assert not pixmap_label._pixmap.isNull()
    pixmap_label.clear()
    assert pixmap_label._pixmap.isNull()


def test_pixmap_label__height_for_width(pixmap_label, sample_pixmap):
    """heightForWidth should preserve the original aspect ratio (200:100 = 2:1)"""
    pixmap_label.setPixmap(sample_pixmap)
    assert pixmap_label.heightForWidth(400) == 200
    assert pixmap_label.heightForWidth(100) == 50


def test_pixmap_label__height_for_width__no_pixmap(pixmap_label):
    """Without a pixmap, heightForWidth falls back to current widget height"""
    pixmap_label.resize(300, 150)
    assert pixmap_label.heightForWidth(999) == 150


def test_pixmap_label__scaled_pixmap__null(pixmap_label):
    """Null pixmap is returned as-is"""
    result = pixmap_label.scaledPixmap()
    assert result.isNull()


def test_pixmap_label__scaled_pixmap__no_scale(qtbot, sample_pixmap):
    """With scale=False, the original pixmap is returned unmodified"""
    label = PixmapLabel(pixmap=sample_pixmap, scale=False)
    qtbot.addWidget(label)
    label.resize(50, 50)
    result = label.scaledPixmap()
    assert result.width() == 200
    assert result.height() == 100


def test_pixmap_label__scaled_pixmap__with_scale(pixmap_label, sample_pixmap):
    """With scale=True (default), the pixmap is scaled to fit the widget"""
    pixmap_label.resize(100, 100)
    pixmap_label.setPixmap(sample_pixmap)
    result = pixmap_label.scaledPixmap()
    # Scaled to fit 100x100 while keeping 2:1 aspect ratio → 100x50
    assert result.width() == 100
    assert result.height() == 50


def test_pixmap_label__size_hint(pixmap_label, sample_pixmap):
    pixmap_label.resize(100, 100)
    pixmap_label.setPixmap(sample_pixmap)
    hint = pixmap_label.sizeHint()
    assert hint == QSize(100, 50)


@pytest.mark.parametrize(
    'button, expect_called',
    [(Qt.LeftButton, True), (Qt.RightButton, False)],
    ids=['left_click', 'right_click_ignored'],
)
def test_pixmap_label__on_click(pixmap_label, qtbot, button, expect_called):
    on_click = MagicMock()
    pixmap_label.on_click.connect(on_click)
    qtbot.mouseClick(pixmap_label, button)
    assert on_click.called == expect_called


# --- ImageWindow ---


def test_image_window__display_image_fullscreen__non_raw(image_window, tmp_path):
    img_path = tmp_path / 'test.jpg'
    Image.new('RGB', (50, 50), color='red').save(img_path)

    image_window.display_image_fullscreen(img_path, [img_path])

    assert image_window.image._pixmap.size() == QSize(50, 50)
    assert image_window.image.description == str(img_path)


def test_image_window__display_image_fullscreen__raw_shows_placeholder_and_schedules(
    image_window, mock_app
):
    """A RAW file should show a placeholder immediately and decode in the background,
    rather than blocking the GUI thread"""
    raw_path = SAMPLE_DATA_DIR / 'raw_without_sidecar.ORF'

    image_window.display_image_fullscreen(raw_path, [raw_path])

    # Real decode is scheduled rather than run synchronously, so the only pixmap that could be
    # showing at this point is the immediate placeholder
    assert not image_window.image._pixmap.isNull()
    assert len(mock_app._futures) == 1


def test_image_window__display_image_fullscreen__raw_applies_result_on_completion(
    image_window, mock_app
):
    raw_path = SAMPLE_DATA_DIR / 'raw_without_sidecar.ORF'
    image_window.display_image_fullscreen(raw_path, [raw_path])

    mock_app._futures[-1].on_result.emit(QPixmap(30, 20))

    assert image_window.image._pixmap.size() == QSize(30, 20)


def test_image_window__display_image_fullscreen__raw_decode_failure_shows_placeholder(
    image_window, mock_app
):
    """A null pixmap result (e.g. RAW decode failure) should fall back to a newly-generated
    placeholder, not just leave the initial pre-decode placeholder in place"""
    raw_path = SAMPLE_DATA_DIR / 'raw_without_sidecar.ORF'
    image_window.display_image_fullscreen(raw_path, [raw_path])
    initial_placeholder = image_window.image._pixmap

    mock_app._futures[-1].on_result.emit(QPixmap())

    assert image_window.image._pixmap is not initial_placeholder
    assert not image_window.image._pixmap.isNull()


def test_image_window__select_image_idx__stale_raw_result_ignored(image_window, mock_app):
    """A late-arriving decode for a since-navigated-away-from image should be ignored"""
    raw_path_1 = SAMPLE_DATA_DIR / 'raw_without_sidecar.ORF'
    raw_path_2 = SAMPLE_DATA_DIR / 'IMG20210310_120958.ORF'

    image_window.display_image_fullscreen(raw_path_1, [raw_path_1, raw_path_2])
    stale_future = mock_app._futures[-1]

    image_window.select_image_idx(1)
    assert image_window.selected_path == raw_path_2
    pixmap_before_stale_result = image_window.image._pixmap

    stale_future.on_result.emit(QPixmap(30, 20))

    assert image_window.image._pixmap is pixmap_before_stale_result


# --- InfoCard ---


def test_info_card__default_state(info_card):
    assert info_card.card_id == 42
    assert info_card.title.text() == ''
    assert info_card.thumbnail is not None


def test_info_card__init_without_id(qtbot):
    card = InfoCard()
    qtbot.addWidget(card)
    assert card.card_id is None


def test_info_card__title(info_card):
    info_card.title.setText('Species Name')
    assert info_card.title.text() == 'Species Name'


def test_info_card__add_row__widget(info_card):
    label = QLabel('extra info')
    info_card.add_row(label)
    assert label.parent() is not None


def test_info_card__add_row__layout(info_card):
    from naturtag.widgets.layouts import HorizontalLayout

    layout = HorizontalLayout()
    layout.addWidget(QLabel('a'))
    info_card.add_row(layout)
    assert info_card.details_layout.count() > 1


@pytest.mark.parametrize(
    'button, expect_called',
    [(Qt.LeftButton, True), (Qt.RightButton, False)],
    ids=['left_click', 'right_click_ignored'],
)
def test_info_card__on_click(info_card, qtbot, button, expect_called):
    on_click = MagicMock()
    info_card.on_click.connect(on_click)
    qtbot.mouseClick(info_card, button)
    assert on_click.called == expect_called


def test_info_card__hover__shows_overlay(info_card, qtbot):
    # Use isHidden() since isVisible() requires all ancestors to be shown
    assert info_card.thumbnail.overlay.isHidden()
    info_card.enterEvent(None)
    assert not info_card.thumbnail.overlay.isHidden()
    info_card.leaveEvent(None)
    assert info_card.thumbnail.overlay.isHidden()


# --- InfoCardList ---


def _make_card(qtbot, card_id):
    card = InfoCard(card_id=card_id)
    qtbot.addWidget(card)
    return card


@patch('naturtag.widgets.images.set_pixmap_async')
def test_info_card_list__add_card(mock_set_pixmap, info_card_list, qtbot):
    card = _make_card(qtbot, 1)
    info_card_list.add_card(card, thumbnail_url='https://example.com/img.jpg')
    assert info_card_list.contains(1)
    mock_set_pixmap.assert_called_once()


@patch('naturtag.widgets.images.set_pixmap_async')
def test_info_card_list__add_card__at_index(mock_set_pixmap, info_card_list, qtbot):
    card_a = _make_card(qtbot, 1)
    card_b = _make_card(qtbot, 2)
    info_card_list.add_card(card_a, thumbnail_url='https://example.com/a.jpg')
    info_card_list.add_card(card_b, thumbnail_url='https://example.com/b.jpg', idx=0)
    # card_b was inserted at index 0, so it should be the first widget
    first = info_card_list.root.itemAt(0).widget()
    assert first.card_id == 2


@patch('naturtag.widgets.images.set_pixmap_async')
def test_info_card_list__get_card_by_id(mock_set_pixmap, info_card_list, qtbot):
    card = _make_card(qtbot, 7)
    info_card_list.add_card(card, thumbnail_url='https://example.com/img.jpg')
    assert info_card_list.get_card_by_id(7) is card
    assert info_card_list.get_card_by_id(999) is None


@patch('naturtag.widgets.images.set_pixmap_async')
def test_info_card_list__contains(mock_set_pixmap, info_card_list, qtbot):
    card = _make_card(qtbot, 3)
    info_card_list.add_card(card, thumbnail_url='https://example.com/img.jpg')
    assert info_card_list.contains(3)
    assert not info_card_list.contains(99)


@patch('naturtag.widgets.images.set_pixmap_async')
def test_info_card_list__clear(mock_set_pixmap, info_card_list, qtbot):
    for i in range(3):
        info_card_list.add_card(_make_card(qtbot, i), thumbnail_url='https://example.com/img.jpg')
    assert info_card_list.root.count() == 3
    info_card_list.clear()
    assert info_card_list.root.count() == 0


@patch('naturtag.widgets.images.set_pixmap_async')
def test_info_card_list__move_card(mock_set_pixmap, info_card_list, qtbot):
    for i in range(3):
        info_card_list.add_card(_make_card(qtbot, i), thumbnail_url='https://example.com/img.jpg')
    # Move card 2 to position 0
    assert info_card_list.move_card(2, idx=0)
    first = info_card_list.root.itemAt(0).widget()
    assert first.card_id == 2


@patch('naturtag.widgets.images.set_pixmap_async')
def test_info_card_list__move_card__not_found(mock_set_pixmap, info_card_list):
    assert not info_card_list.move_card(999)


@patch('naturtag.widgets.images.set_pixmap_async')
def test_info_card_list__cards_iterator(mock_set_pixmap, info_card_list, qtbot):
    for i in range(3):
        info_card_list.add_card(_make_card(qtbot, i), thumbnail_url='https://example.com/img.jpg')
    card_ids = [c.card_id for c in info_card_list.cards]
    assert card_ids == [0, 1, 2]
