import re
import webbrowser
from logging import getLogger
from os.path import isfile
from pathlib import Path
from typing import Callable, Iterable
from urllib.parse import unquote, urlparse

from PySide6.QtCore import Qt, QUrl, Signal, Slot
from PySide6.QtGui import QAction, QDesktopServices, QDropEvent, QKeySequence, QPixmap, QShortcut
from PySide6.QtWidgets import QApplication, QFileDialog, QLabel, QMenu, QScrollArea, QWidget

from naturtag.app.style import fa_icon
from naturtag.constants import IMAGE_FILETYPES, THUMBNAIL_SIZE_DEFAULT
from naturtag.image_glob import get_valid_image_paths
from naturtag.metadata import MetaMetadata
from naturtag.thumbnails import get_thumbnail
from naturtag.widgets import (
    FlowLayout,
    HorizontalLayout,
    IconLabel,
    PixmapLabel,
    StylableWidget,
    VerticalLayout,
)

logger = getLogger(__name__)


class ImageGallery(StylableWidget):
    """Container for displaying local image thumbnails & info"""

    message = Signal(str)
    selected_taxon: Signal = Signal(int)

    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.images: dict[str, LocalThumbnail] = {}
        self.image_window = ImageWindow()
        root = VerticalLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        self.scroll_panel = StylableWidget()
        self.scroll_panel.setObjectName('gallery_scroll_panel')
        self.flow_layout = FlowLayout(self.scroll_panel)
        self.flow_layout.setSpacing(0)
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setWidget(self.scroll_panel)
        root.addLayout(self.flow_layout)
        root.addWidget(scroll_area)

    def clear(self):
        """Clear all images from the viewer"""
        self.images = {}
        self.flow_layout.clear()

    def load_file_dialog(self):
        """Show a file chooser dialog"""
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            'Open image files:',
            filter=f'Image files ({" ".join(IMAGE_FILETYPES)})',
        )
        self.load_images(file_paths)

    def load_images(self, paths: Iterable[str]):
        """Load multiple images, and ignore any duplicates"""
        images = get_valid_image_paths(paths, recursive=True)
        new_images = [i for i in set(images) - set(self.images.keys()) if i]
        if not new_images:
            return

        logger.info(f'Loading {len(new_images)} ({len(images) - len(new_images)} already loaded)')
        for file_path in sorted(new_images):
            self.load_image(file_path)

    def load_image(self, file_path: str):
        """Load an image from a file path or URI"""
        # TODO: Support Windows file URIs
        file_path = unquote(urlparse(str(file_path)).path)
        if not isfile(file_path):
            logger.info(f'File does not exist: {file_path}')
            return
        elif file_path in self.images:
            logger.info(f'Image already loaded: {file_path}')
            return

        logger.info(f'Loading {file_path}')
        thumbnail = LocalThumbnail(file_path)
        thumbnail.removed.connect(self.remove_image)
        thumbnail.selected.connect(self.select_image)
        thumbnail.copied.connect(self.message.emit)
        thumbnail.context_menu.selected_taxon.connect(self.selected_taxon.emit)
        self.flow_layout.addWidget(thumbnail)
        self.images[file_path] = thumbnail

    def dragEnterEvent(self, event):
        event.acceptProposedAction()

    def dragMoveEvent(self, event):
        event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        event.acceptProposedAction()
        for file_path in event.mimeData().text().splitlines():
            self.load_image(file_path)

    @Slot(str)
    def remove_image(self, file_path: str):
        del self.images[file_path]

    @Slot(str)
    def select_image(self, file_path: str):
        self.image_window.select_image(file_path, list(self.images.keys()))


# TODO: Small overlay with photo info
class ImageWindow(QWidget):
    """Display a single full-size image at a time as a separate window

    Keyboard shortcuts: Escape to close window, Left and Right to cycle through images
    """

    def __init__(self):
        super().__init__()
        self.image_paths: list[str] = []
        self.selected_path = None

        self.image = PixmapLabel()
        self.image.setFixedSize(QApplication.primaryScreen().availableSize())
        self.image.setAlignment(Qt.AlignCenter)
        self.image_layout = VerticalLayout(self)
        self.image_layout.addWidget(self.image)
        self.image_layout.setContentsMargins(0, 0, 0, 0)

        # Keyboard shortcuts
        shortcut = QShortcut(QKeySequence(Qt.Key_Escape), self)
        shortcut.activated.connect(self.close)
        shortcut = QShortcut(QKeySequence(Qt.Key_Right), self)
        shortcut.activated.connect(self.select_next_image)
        shortcut = QShortcut(QKeySequence(Qt.Key_Left), self)
        shortcut.activated.connect(self.select_prev_image)

    def select_image(self, selected_path: str, image_paths: list[str]):
        """Open window to a selected image, and save other available image paths for navigation"""
        self.selected_path = selected_path
        self.image_paths = image_paths
        self.set_pixmap(self.selected_path)
        self.showFullScreen()

    def select_image_idx(self, idx: int):
        """Select an image by index, with wraparound"""
        if idx < 0:
            idx = len(self.image_paths) - 1
        elif idx >= len(self.image_paths):
            idx = 0

        logger.debug(f'Selecting image {idx}: {self.selected_path}')
        self.selected_path = self.image_paths[idx]
        self.set_pixmap(self.selected_path)

    def select_next_image(self):
        self.select_image_idx(self.image_paths.index(self.selected_path) + 1)

    def select_prev_image(self):
        self.select_image_idx(self.image_paths.index(self.selected_path) - 1)

    def set_pixmap(self, path: str):
        self.image.setPixmap(QPixmap(path))


class LocalThumbnail(StylableWidget):
    """A tile that generates, caches, and displays a thumbnail for a local image file.
    Contains icons representing its metadata types, and the following mouse actions:

    * Left click: Show full image
    * Middle click: Remove image
    * Right click: Show context menu
    """

    copied = Signal(str)
    removed = Signal(str)
    selected = Signal(str)

    def __init__(self, file_path: str):
        super().__init__()
        self.metadata = MetaMetadata(file_path)
        self.file_path = Path(file_path)
        self.window = None
        self.setToolTip(f'{file_path}\n{self.metadata.summary}')
        self.setContentsMargins(2, 2, 2, 2)
        self.observation = None

        layout = VerticalLayout(self)
        layout.setSpacing(0)
        self.context_menu = ThumbnailContextMenu(self)

        # Image
        self.image = QLabel(self)
        self.image.setPixmap(QPixmap(get_thumbnail(file_path)))
        self.image.setAlignment(Qt.AlignCenter)
        self.image.setMaximumWidth(THUMBNAIL_SIZE_DEFAULT[0])
        self.image.setMaximumHeight(THUMBNAIL_SIZE_DEFAULT[1])
        layout.addWidget(self.image)

        # Metadata icons
        self.icons = ThumbnailMetaIcons(self)
        self.icons.setObjectName('metadata-icons')

        # Filename
        text = re.sub('([_-])', '\\1\u200b', self.file_path.name)  # To allow word wrapping
        self.label = QLabel(text)
        self.label.setMaximumWidth(THUMBNAIL_SIZE_DEFAULT[0])
        self.label.setMinimumHeight(40)
        self.label.setAlignment(Qt.AlignLeft)
        self.label.setWordWrap(True)
        layout.addWidget(self.label)

    def contextMenuEvent(self, e):
        self.context_menu.exec(e.globalPos())

    def mousePressEvent(self, _):
        """Placeholder to accept mouse press events"""

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.select()
        elif event.button() == Qt.MiddleButton:
            self.remove()

    def copy_flickr_tags(self):
        QApplication.clipboard().setText(self.metadata.keyword_meta.flickr_tags)
        id_str = (
            f'observation {self.metadata.observation_id}'
            if self.metadata.has_observation
            else f'taxon {self.metadata.taxon_id}'
        )
        self.copied.emit(f'Tags for {id_str} copied to clipboard')

    def remove(self):
        logger.debug(f'Removing image {self.file_path}')
        self.removed.emit(str(self.file_path))
        self.setParent(None)
        self.deleteLater()

    def select(self):
        logger.debug(f'Selecting image {self.file_path}')
        self.selected.emit(str(self.file_path))

    def update_metadata(self, metadata: MetaMetadata):
        self.metadata = metadata
        self.icons.refresh_icons(metadata)
        self.setToolTip(f'{self.file_path}\n{self.metadata.summary}')

    def open_directory(self):
        QDesktopServices.openUrl(QUrl(self.file_path.parent.as_uri()))


class ThumbnailContextMenu(QMenu):
    """Context menu for local image thumbnails"""

    selected_taxon: Signal = Signal(int)

    def __init__(self, thumbnail: LocalThumbnail):
        super().__init__()
        self.thumbnail = thumbnail
        meta = thumbnail.metadata

        self._add_action(
            icon='fa5s.spider',
            text='View Taxon',
            tooltip=f'View taxon {meta.taxon_id} in naturtag',
            enabled=meta.has_taxon,
            callback=lambda: self.selected_taxon.emit(meta.taxon_id),
        )
        self._add_action(
            icon='fa5s.spider',
            text='View Taxon on iNat',
            tooltip=f'View taxon {meta.taxon_id} on inaturalist.org',
            enabled=meta.has_taxon,
            callback=lambda: webbrowser.open(meta.taxon_url),
        )
        self._add_action(
            icon='fa.binoculars',
            text='View Observation on iNat',
            tooltip=f'View observation {meta.observation_id} on inaturalist.org',
            enabled=meta.has_observation,
            callback=lambda: webbrowser.open(meta.observation_url),
        )
        self._add_action(
            icon='fa5.copy',
            text='Copy Flickr tags',
            tooltip='Copy Flickr-compatible taxon tags to clipboard',
            enabled=meta.has_taxon,
            callback=thumbnail.copy_flickr_tags,
        )
        self._add_action(
            icon='fa5s.folder-open',
            text='Open containing folder',
            tooltip=f'Open containing folder: {thumbnail.file_path.parent}',
            callback=thumbnail.open_directory,
        )
        self._add_action(
            icon='fa.remove',
            text='Remove image',
            tooltip='Remove this image from the selection',
            callback=thumbnail.remove,
        )

    def _add_action(
        self, icon: str, text: str, tooltip: str, enabled: bool = True, callback: Callable = None
    ):
        action = QAction(fa_icon(icon), text, self.thumbnail)
        action.setStatusTip(tooltip)
        action.setEnabled(enabled)
        if callback:
            action.triggered.connect(callback)
        self.addAction(action)


class ThumbnailMetaIcons(QLabel):
    """Icons overlayed on top of a thumbnail to indicate what types of metadata are available"""

    def __init__(self, parent: LocalThumbnail):
        super().__init__(parent)
        img_size = parent.image.sizeHint()

        self.icon_layout = HorizontalLayout(self)
        self.icon_layout.setAlignment(Qt.AlignLeft)
        self.icon_layout.setContentsMargins(0, 0, 0, 0)
        self.setGeometry(11, img_size.height() - 9, 116, 20)

        self.refresh_icons(parent.metadata)

    def refresh_icons(self, metadata: MetaMetadata):
        """Update icons based on types of metadata available"""
        self.icon_layout.clear()
        self.icon_layout.addWidget(IconLabel('mdi.bird', active=metadata.has_taxon))
        self.icon_layout.addWidget(IconLabel('fa.binoculars', active=metadata.has_observation))
        self.icon_layout.addWidget(IconLabel('fa.map-marker', active=metadata.has_coordinates))
        self.icon_layout.addWidget(IconLabel('fa.tags', active=metadata.has_any_tags))
        self.icon_layout.addWidget(IconLabel('mdi.xml', active=metadata.has_sidecar))
