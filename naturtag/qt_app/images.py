from logging import getLogger
from os.path import isfile
from pathlib import Path
from urllib.parse import unquote, urlparse

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QDropEvent, QPixmap
from PySide6.QtWidgets import QFileDialog, QLabel, QVBoxLayout, QWidget

from naturtag.constants import IMAGE_FILETYPES, THUMBNAIL_SIZE_DEFAULT
from naturtag.image_glob import get_images_from_paths
from naturtag.models import MetaMetadata
from naturtag.qt_app.layouts import FlowLayout
from naturtag.thumbnails import get_thumbnail

# from qtawesome import icon as fa_icon


logger = getLogger(__name__)


class ImageViewer(QWidget):
    file_changed = Signal(str)

    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.images: dict[str, LocalThumbnail] = {}
        self.flow_layout = FlowLayout()
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
        self.setStyleSheet('background-color: rgba(0, 0, 0, 0.2);')
        layout = QVBoxLayout(self)
        layout.setSpacing(0)

        self.image = QLabel(self)
        self.image.setPixmap(QPixmap(get_thumbnail(file_path)))
        self.image.setAlignment(Qt.AlignCenter)
        self.image.setMaximumWidth(THUMBNAIL_SIZE_DEFAULT[0])
        self.image.setMaximumHeight(THUMBNAIL_SIZE_DEFAULT[1])
        self.image.setStyleSheet('background-color: rgba(0, 0, 0, 0.2);')
        layout.addWidget(self.image)

        # self.info = QLabel(fa_icon("fa.play"))
        self.info = QLabel(self.metadata.summary)
        self.info.setMaximumWidth(THUMBNAIL_SIZE_DEFAULT[0])
        self.info.setAlignment(Qt.AlignRight)
        self.info.setStyleSheet('background-color: rgba(0, 0.5, 0.5, 0.5);\ncolor: white;')
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
