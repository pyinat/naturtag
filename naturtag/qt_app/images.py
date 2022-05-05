from logging import getLogger
from os.path import isfile
from pathlib import Path
from urllib.parse import unquote, urlparse

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QDropEvent, QPixmap
from PySide6.QtWidgets import QFileDialog, QHBoxLayout, QLabel, QVBoxLayout, QWidget
from qtawesome import icon as fa_icon

from naturtag.constants import IMAGE_FILETYPES, THUMBNAIL_SIZE_DEFAULT
from naturtag.image_glob import get_images_from_paths
from naturtag.models import MetaMetadata
from naturtag.qt_app.layouts import FlowLayout
from naturtag.thumbnails import get_thumbnail

logger = getLogger(__name__)


class ImageViewer(QWidget):
    file_changed = Signal(str)

    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.images: dict[str, LocalThumbnail] = {}
        self.flow_layout = FlowLayout()
        self.flow_layout.setSpacing(4)
        self.setLayout(self.flow_layout)

    def clear(self):
        """Clear all images from the viewer"""
        del self.images
        self.images = {}
        self.flow_layout.clear()

    def load_file_dialog(self):
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            'Open image files:',
            filter=f'Image files ({" ".join(IMAGE_FILETYPES)})',
        )
        self.load_images(file_paths)

    def load_images(self, paths: list[str]):
        # Determine images to load, ignoring duplicates
        images = get_images_from_paths(paths, recursive=True)
        new_images = list(set(images) - set(self.images.keys()))
        logger.info(f'Loading {len(new_images)} ({len(images) - len(new_images)} already loaded)')
        if not new_images:
            return

        for file_path in new_images:
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
        thumbnail.removed.connect(self.on_image_removed)
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
    def on_image_removed(self, file_path: str):
        logger.debug(f'Removing {file_path}')
        del self.images[file_path]


class LocalThumbnail(QWidget):
    removed = Signal(str)

    def __init__(self, file_path: str):
        super().__init__()
        self.metadata = MetaMetadata(file_path)
        self.file_path = Path(file_path)
        self.setToolTip(f'{file_path}\n{self.metadata.summary}')
        layout = QVBoxLayout(self)
        layout.setSpacing(0)

        logger.info(self.metadata.exif.get('Exif.GPSInfo'))
        logger.info(self.metadata.exif.get('Exif.GPSInfo.GPSLatitude'))
        logger.info(type(self.metadata.exif.get('Exif.GPSInfo.GPSLatitude')))

        # Image
        self.image = QLabel(self)
        self.image.setPixmap(QPixmap(get_thumbnail(file_path)))
        self.image.setAlignment(Qt.AlignCenter)
        self.image.setMaximumWidth(THUMBNAIL_SIZE_DEFAULT[0])
        self.image.setMaximumHeight(THUMBNAIL_SIZE_DEFAULT[1])
        layout.addWidget(self.image)

        # Metadata icons
        icons = ThumbnailMetaIcons(self)
        icons.setStyleSheet('background-color: rgba(0, 0, 0, 0.5);')

        # Filename
        self.info = QLabel(self.file_path.name)
        self.info.setMaximumWidth(THUMBNAIL_SIZE_DEFAULT[0])
        self.info.setAlignment(Qt.AlignRight)
        self.info.setStyleSheet('background-color: rgba(0, 0, 0, 0.5);')
        layout.addWidget(self.info)

    def mouseReleaseEvent(self, event):
        # TODO: Left click: expand
        if event.button() == Qt.LeftButton:
            logger.info("mouseReleaseEvent LEFT")
        # Middle click: Remove image
        elif event.button() == Qt.MiddleButton:
            self.removed.emit(str(self.file_path))
            self.setParent(None)
            self.deleteLater()
        # TODO: Right click: context menu
        elif event.button() == Qt.RightButton:
            logger.info("mouseReleaseEvent RIGHT")

    def mousePressEvent(self, _):
        pass


class ThumbnailMetaIcons(QLabel):
    """Icons overlayed on top of a thumbnail to indicate what types of metadata are available"""

    def __init__(self, parent: LocalThumbnail):
        super().__init__(parent)
        img_size = parent.image.sizeHint()

        self.icon_layout = QHBoxLayout(self)
        self.icon_layout.setAlignment(Qt.AlignLeft)
        self.icon_layout.setContentsMargins(0, 0, 0, 0)
        self.setGeometry(9, img_size.height() - 10, 100, 20)

        self._add_icon('mdi.bird', active=parent.metadata.has_taxon)
        self._add_icon('fa.binoculars', active=parent.metadata.has_observation)
        self._add_icon('fa.map-marker', active=parent.metadata.has_coordinates)
        self._add_icon('fa.tags', active=parent.metadata.has_any_tags)
        self._add_icon('mdi.xml', active=parent.metadata.has_sidecar)

    def _add_icon(self, icon_str: str, active: bool = False):
        icon = fa_icon(icon_str, color='yellowgreen' if active else 'gray')
        icon_label = QLabel(self)
        icon_label.setPixmap(icon.pixmap(16, 16))
        icon_label.setStyleSheet('background-color: rgba(0, 0, 0, 0);')
        self.icon_layout.addWidget(icon_label)
