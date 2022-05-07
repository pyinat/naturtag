import webbrowser
from logging import getLogger
from os.path import isfile
from pathlib import Path
from urllib.parse import unquote, urlparse

# from pyinaturalist.models import Observation, Taxon
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QAction, QDropEvent, QPixmap
from PySide6.QtWidgets import QApplication, QFileDialog, QHBoxLayout, QLabel, QMenu, QVBoxLayout, QWidget
from qtawesome import icon as fa_icon

from naturtag.app.image_window import ImageWindow
from naturtag.app.layouts import FlowLayout
from naturtag.constants import IMAGE_FILETYPES, THUMBNAIL_SIZE_DEFAULT
from naturtag.image_glob import get_images_from_paths
from naturtag.models import MetaMetadata
from naturtag.thumbnails import get_thumbnail

logger = getLogger(__name__)


class ImageGallery(QWidget):
    """Container for displaying local image thumbnails & info"""

    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.images: dict[str, LocalThumbnail] = {}
        self.image_window = ImageWindow()
        self.flow_layout = FlowLayout()
        self.flow_layout.setSpacing(4)
        self.setLayout(self.flow_layout)

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

    def load_images(self, paths: list[str]):
        """Load multiple images, and ignore any duplicates"""
        images = get_images_from_paths(paths, recursive=True)
        new_images = list(set(images) - set(self.images.keys()))
        logger.info(f'Loading {len(new_images)} ({len(images) - len(new_images)} already loaded)')
        if not new_images:
            return

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


class LocalThumbnail(QWidget):
    """A tile that generates, caches, and displays a thumbnail for a local image file.
    Contains icons representing its metadata types, and the following mouse actions:

    * Left click: Show full image
    * Middle click: Remove image
    * Right click: Show context menu
    """

    removed = Signal(str)
    selected = Signal(str)

    def __init__(self, file_path: str):
        super().__init__()
        self.metadata = MetaMetadata(file_path)
        self.file_path = Path(file_path)
        self.window = None
        self.setToolTip(f'{file_path}\n{self.metadata.summary}')
        self.taxon = None
        self.observation = None

        layout = QVBoxLayout(self)
        layout.setSpacing(0)

        # Image
        self.image = QLabel(self)
        self.image.setPixmap(QPixmap(get_thumbnail(file_path)))
        self.image.setAlignment(Qt.AlignCenter)
        self.image.setMaximumWidth(THUMBNAIL_SIZE_DEFAULT[0])
        self.image.setMaximumHeight(THUMBNAIL_SIZE_DEFAULT[1])
        layout.addWidget(self.image)

        # Metadata icons
        self.icons = ThumbnailMetaIcons(self)
        self.icons.setStyleSheet('background-color: rgba(0, 0, 0, 0.5);')

        # Filename
        self.label = QLabel(self.file_path.name)
        self.label.setMaximumWidth(THUMBNAIL_SIZE_DEFAULT[0])
        self.label.setAlignment(Qt.AlignLeft)
        self.label.setStyleSheet('background-color: rgba(0, 0, 0, 0.5);font-size: 10pt;')
        layout.addWidget(self.label)

    def contextMenuEvent(self, e):
        context_menu = ThumbnailContextMenu(self)
        context_menu.exec(e.globalPos())

    def mousePressEvent(self, _):
        """Placeholder to accept mouse press events"""

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.select()
        elif event.button() == Qt.MiddleButton:
            self.remove()

    def copy_flickr_tags(self):
        QApplication.clipboard().setText(self.metadata.keyword_meta.flickr_tags)
        # alert('Tags copied to clipboard')

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


class ThumbnailContextMenu(QMenu):
    """Context menu for local image thumbnails"""

    def __init__(self, thumbnail: LocalThumbnail):
        super().__init__()
        meta = thumbnail.metadata

        action = QAction(fa_icon('fa.binoculars'), 'View Observation', thumbnail)
        action.setStatusTip(f'View observation {meta.observation_id} on inaturalist.org')
        action.setEnabled(meta.has_observation)
        action.triggered.connect(lambda: webbrowser.open(meta.observation_url))
        self.addAction(action)

        action = QAction(fa_icon('fa5s.spider'), 'View Taxon', thumbnail)
        action.setStatusTip(f'View taxon {meta.taxon_id} on inaturalist.org')
        action.setEnabled(meta.has_taxon)
        action.triggered.connect(lambda: webbrowser.open(meta.taxon_url))
        self.addAction(action)

        action = QAction(fa_icon('fa5.copy'), 'Copy Flickr tags', thumbnail)
        action.setStatusTip('Copy Flickr-compatible taxon tags to clipboard')
        action.setEnabled(meta.has_taxon)
        action.triggered.connect(thumbnail.copy_flickr_tags)
        self.addAction(action)

        action = QAction(fa_icon('fa.remove'), 'Remove image', thumbnail)
        action.setStatusTip('Remove this image from the selection')
        action.triggered.connect(thumbnail.remove)
        self.addAction(action)


class ThumbnailMetaIcons(QLabel):
    """Icons overlayed on top of a thumbnail to indicate what types of metadata are available"""

    def __init__(self, parent: LocalThumbnail):
        super().__init__(parent)
        img_size = parent.image.sizeHint()

        self.icon_layout = QHBoxLayout(self)
        self.icon_layout.setAlignment(Qt.AlignLeft)
        self.icon_layout.setContentsMargins(0, 0, 0, 0)
        self.setGeometry(9, img_size.height() - 10, 100, 20)

        self.refresh_icons(parent.metadata)

    def refresh_icons(self, metadata: MetaMetadata):
        while (child := self.icon_layout.takeAt(0)) is not None:
            child.widget().deleteLater()

        self._add_icon('mdi.bird', active=metadata.has_taxon)
        self._add_icon('fa.binoculars', active=metadata.has_observation)
        self._add_icon('fa.map-marker', active=metadata.has_coordinates)
        self._add_icon('fa.tags', active=metadata.has_any_tags)
        self._add_icon('mdi.xml', active=metadata.has_sidecar)

    def _add_icon(self, icon_str: str, active: bool = False):
        icon = fa_icon(icon_str, color='yellowgreen' if active else 'gray')
        icon_label = QLabel(self)
        icon_label.setPixmap(icon.pixmap(16, 16))
        icon_label.setStyleSheet('background-color: rgba(0, 0, 0, 0);')
        self.icon_layout.addWidget(icon_label)
