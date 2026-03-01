"""Tests for ImageGallery, ThumbnailCard, ThumbnailContextMenu, and ThumbnailMetaIcons."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtCore import QObject, Qt, Signal

from naturtag.controllers.image_gallery import (
    ImageGallery,
    ThumbnailCard,
)


@pytest.fixture
def gallery(qtbot, mock_app):
    gallery = ImageGallery()
    qtbot.addWidget(gallery)
    return gallery


@pytest.fixture
def image_files(tmp_path):
    """Create temporary image files for testing."""
    paths = []
    for name in ['photo1.jpg', 'photo2.jpg', 'photo3.jpg']:
        p = tmp_path / name
        p.write_bytes(b'\xff\xd8\xff\xe0')
        paths.append(p)
    return paths


@pytest.fixture
def thumbnail_card(qtbot):
    card = ThumbnailCard(Path('/tmp/test_image.jpg'))
    qtbot.addWidget(card)
    return card


@pytest.fixture
def mock_metadata():
    meta = MagicMock()
    meta.has_taxon = True
    meta.has_observation = True
    meta.has_coordinates = True
    meta.has_any_tags = True
    meta.has_sidecar = False
    meta.taxon_id = 42
    meta.observation_id = 99
    meta.taxon_url = 'https://inaturalist.org/taxa/42'
    meta.observation_url = 'https://inaturalist.org/observations/99'
    meta.summary = 'Test summary'
    meta.keyword_meta.flickr_tags = 'tag1 tag2'
    return meta


# --- ImageGallery ---


def test_init(gallery):
    assert gallery.images == {}


def test_clear(gallery, image_files):
    """clear() removes all images and clears the flow layout."""
    with patch.object(ThumbnailCard, 'load_image_async'):
        gallery.load_images(image_files)
    assert len(gallery.images) > 0

    gallery.clear()

    assert gallery.images == {}
    assert gallery.flow_layout.count() == 0


def test_load_images(gallery, image_files):
    """load_images() creates thumbnail cards and emits on_load_images."""
    on_load = MagicMock()
    gallery.on_load_images.connect(on_load)

    with patch.object(ThumbnailCard, 'load_image_async'):
        gallery.load_images(image_files)

    assert len(gallery.images) == 3
    on_load.assert_called_once()
    assert len(on_load.call_args[0][0]) == 3


def test_load_images__deduplicates(gallery, image_files):
    """Loading the same images twice doesn't create duplicates."""
    with patch.object(ThumbnailCard, 'load_image_async'):
        gallery.load_images(image_files)
        gallery.load_images(image_files)

    assert len(gallery.images) == 3


def test_load_images__empty(gallery):
    """Loading empty list is a no-op."""
    on_load = MagicMock()
    gallery.on_load_images.connect(on_load)
    gallery.load_images([])

    assert len(gallery.images) == 0
    on_load.assert_not_called()


def test_load_image__nonexistent_file(gallery):
    result = gallery.load_image(Path('/nonexistent/image.jpg'))
    assert result is None


def test_load_image__duplicate(gallery, image_files):
    """load_image returns None if the image is already loaded."""
    gallery.load_image(image_files[0], delayed_load=True)
    result = gallery.load_image(image_files[0])
    assert result is None


def test_load_image__creates_card(gallery, image_files):
    result = gallery.load_image(image_files[0], delayed_load=True)

    assert isinstance(result, ThumbnailCard)
    assert image_files[0] in gallery.images


def test_load_image__clears_help_text(gallery, image_files):
    """Loading the first image removes the initial help text."""
    initial_count = gallery.flow_layout.count()
    assert initial_count > 0  # Help text widget is present

    gallery.load_image(image_files[0], delayed_load=True)

    # Help text was cleared, then the new card was added
    assert gallery.flow_layout.count() == 1


def test_remove_image(gallery, image_files):
    with patch.object(ThumbnailCard, 'load_image_async'):
        gallery.load_images(image_files)

    gallery.remove_image(image_files[0])

    assert image_files[0] not in gallery.images
    assert len(gallery.images) == 2


def test_select_image(gallery, image_files):
    """select_image delegates to the fullscreen image viewer."""
    with patch.object(ThumbnailCard, 'load_image_async'):
        gallery.load_images(image_files)

    with patch.object(gallery.image_window, 'display_image_fullscreen') as mock_display:
        gallery.select_image(image_files[0])

    mock_display.assert_called_once_with(image_files[0], list(gallery.images.keys()))


@pytest.mark.parametrize(
    'handler',
    ['dragEnterEvent', 'dragMoveEvent'],
    ids=['drag_enter', 'drag_move'],
)
def test_drag_event_accepted(gallery, handler):
    """Drag enter and move events accept the proposed action."""
    event = MagicMock()
    getattr(gallery, handler)(event)
    event.acceptProposedAction.assert_called_once()


def test_drop_event(gallery, image_files):
    """dropEvent loads images from the dropped mime data."""
    event = MagicMock()
    event.mimeData.return_value.text.return_value = '\n'.join(str(p) for p in image_files)

    with patch.object(ThumbnailCard, 'load_image_async'):
        gallery.dropEvent(event)

    event.acceptProposedAction.assert_called_once()
    assert len(gallery.images) == 3


class _PendingSignalEmitter(QObject):
    """Minimal helper to emit a boolean signal in tests."""

    signal = Signal(bool)


@pytest.mark.parametrize('pending', [True, False], ids=['show', 'hide'])
def test_image_gallery__connect_pending_signal(gallery, image_files, pending):
    """When the pending signal fires, all loaded cards reflect the new state."""
    with patch.object(ThumbnailCard, 'load_image_async'):
        gallery.load_images(image_files)

    emitter = _PendingSignalEmitter()
    gallery.connect_pending_signal(emitter.signal)

    emitter.signal.emit(pending)

    for card in gallery.images.values():
        assert card.icons.pending_container.isHidden() == (not pending)


def test_image_gallery__new_card_inherits_pending_state(gallery, image_files):
    """A card loaded after connect_pending_signal() inherits the current pending state."""
    emitter = _PendingSignalEmitter()
    gallery.connect_pending_signal(emitter.signal)
    emitter.signal.emit(True)

    card = gallery.load_image(image_files[0], delayed_load=True)

    assert not card.icons.pending_container.isHidden()


# --- ThumbnailCard ---


def test_thumbnail_card__init(thumbnail_card):
    assert thumbnail_card.image_path == Path('/tmp/test_image.jpg')
    assert thumbnail_card.metadata is None
    assert 'test' in thumbnail_card.label.text()
    assert 'image' in thumbnail_card.label.text()


def test_thumbnail_card__set_metadata(thumbnail_card, mock_metadata):
    """set_metadata updates metadata, tooltip, and emits on_loaded."""
    on_loaded = MagicMock()
    thumbnail_card.on_loaded.connect(on_loaded)
    thumbnail_card.set_metadata(mock_metadata)
    assert thumbnail_card.metadata is mock_metadata
    assert thumbnail_card.toolTip() == 'Test summary'
    on_loaded.assert_called_once_with(thumbnail_card)


@pytest.mark.parametrize(
    'button, signal_name',
    [(Qt.LeftButton, 'on_select'), (Qt.MiddleButton, 'on_remove')],
    ids=['left_click_selects', 'middle_click_removes'],
)
def test_thumbnail_card__mouse_click(thumbnail_card, qtbot, button, signal_name):
    handler = MagicMock()
    getattr(thumbnail_card, signal_name).connect(handler)
    qtbot.mouseClick(thumbnail_card, button)
    handler.assert_called_once_with(thumbnail_card.image_path)


@pytest.mark.parametrize(
    'method, signal_name',
    [('remove', 'on_remove'), ('select', 'on_select')],
    ids=['remove', 'select'],
)
def test_thumbnail_card__signal(thumbnail_card, method, signal_name):
    handler = MagicMock()
    getattr(thumbnail_card, signal_name).connect(handler)
    getattr(thumbnail_card, method)()
    handler.assert_called_once_with(thumbnail_card.image_path)


@pytest.mark.parametrize(
    'has_observation, expected_prefix',
    [(True, 'observation'), (False, 'taxon')],
    ids=['observation', 'taxon'],
)
def test_thumbnail_card__copy_flickr_tags(
    thumbnail_card, mock_metadata, has_observation, expected_prefix
):
    """copy_flickr_tags copies tags to clipboard and emits message based on metadata."""
    mock_metadata.has_observation = has_observation
    thumbnail_card.metadata = mock_metadata
    on_copy = MagicMock()
    thumbnail_card.on_copy.connect(on_copy)

    with patch('naturtag.controllers.image_gallery.QApplication.clipboard') as mock_clipboard:
        thumbnail_card.copy_flickr_tags()

    mock_clipboard.return_value.setText.assert_called_once_with('tag1 tag2')
    on_copy.assert_called_once()
    message = on_copy.call_args[0][0]
    assert expected_prefix in message
    assert 'copied to clipboard' in message


def test_thumbnail_card__update_metadata(thumbnail_card, mock_metadata):
    """update_metadata sets metadata and triggers the pulse animation."""
    with patch.object(thumbnail_card, 'pulse') as mock_pulse:
        thumbnail_card.update_metadata(mock_metadata)

    assert thumbnail_card.metadata is mock_metadata
    mock_pulse.assert_called_once()


@pytest.mark.parametrize('pending', [True, False], ids=['show', 'hide'])
def test_thumbnail_card__set_pending(thumbnail_card, pending):
    """set_pending() on ThumbnailCard delegates to its icons."""
    thumbnail_card.set_pending(pending)
    assert thumbnail_card.icons.pending_container.isHidden() == (not pending)


def test_thumbnail_card__update_metadata_clears_pending(thumbnail_card, mock_metadata):
    """update_metadata() clears the pending icon regardless of prior state."""
    thumbnail_card.set_pending(True)

    with patch.object(thumbnail_card, 'pulse'):
        thumbnail_card.update_metadata(mock_metadata)

    assert thumbnail_card.icons.pending_container.isHidden()


# --- ThumbnailContextMenu ---


@pytest.mark.parametrize(
    'has_taxon, has_observation, expected_enabled_count',
    [
        (True, True, 7),
        (False, False, 2),
        (True, False, 5),
        (False, True, 4),
    ],
    ids=['all_metadata', 'no_metadata', 'taxon_only', 'observation_only'],
)
def test_context_menu__actions_enabled(
    thumbnail_card, mock_metadata, has_taxon, has_observation, expected_enabled_count
):
    """Correct number of actions are enabled based on available metadata."""
    mock_metadata.has_taxon = has_taxon
    mock_metadata.has_observation = has_observation
    thumbnail_card.metadata = mock_metadata

    thumbnail_card.context_menu.refresh_actions(thumbnail_card)

    actions = thumbnail_card.context_menu.actions()
    assert len(actions) == 7  # Always 7 actions total
    enabled = [a for a in actions if a.isEnabled()]
    assert len(enabled) == expected_enabled_count


# --- ThumbnailMetaIcons ---


@pytest.mark.parametrize('pending', [True, False], ids=['show', 'hide'])
def test_thumbnail_meta_icons__set_pending(thumbnail_card, pending):
    """set_pending() controls hidden state of the pending container."""
    thumbnail_card.icons.set_pending(pending)
    assert thumbnail_card.icons.pending_container.isHidden() == (not pending)
