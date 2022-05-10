from logging import getLogger
from pathlib import Path
from typing import Union

from pyinaturalist import Photo, Taxon
from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QKeySequence, QPixmap, QShortcut
from PySide6.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget

from naturtag.metadata.inat_metadata import INAT_CLIENT

logger = getLogger(__name__)


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
        self.image_layout = QVBoxLayout(self)
        self.image_layout.addWidget(self.image)
        self.image_layout.setContentsMargins(0, 0, 0, 0)

        # Keyboard shortcuts
        shortcut = QShortcut(QKeySequence(Qt.Key_Escape), self)
        shortcut.activated.connect(self.close)
        shortcut = QShortcut(QKeySequence(Qt.Key_Right), self)
        shortcut.activated.connect(self.select_next_image)
        shortcut = QShortcut(QKeySequence(Qt.Key_Left), self)
        shortcut.activated.connect(self.select_prev_image)

    def select_image(self, file_path: str, image_paths: list[str]):
        """Open window to a selected image, and save other available image paths for navigation"""
        self.selected_path = file_path
        self.image_paths = image_paths
        self.image.setPixmap(QPixmap(file_path))
        self.showFullScreen()

    def select_image_idx(self, idx: int):
        """Select an image by index, with wraparound"""
        if idx < 0:
            idx = len(self.image_paths) - 1
        elif idx >= len(self.image_paths):
            idx = 0

        logger.debug(f'Selecting image {idx}: {self.selected_path}')
        self.selected_path = self.image_paths[idx]
        self.image.setPixmap(QPixmap(self.selected_path))

    def select_next_image(self):
        self.select_image_idx(self.image_paths.index(self.selected_path) + 1)

    def select_prev_image(self):
        self.select_image_idx(self.image_paths.index(self.selected_path) - 1)


class PixmapLabel(QLabel):
    """A QLabel containing a pixmap that preserves its aspect ratio when resizing"""

    def __init__(
        self,
        parent: QWidget = None,
        pixmap: QPixmap = None,
        path: Union[str, Path] = None,
        taxon: Taxon = None,
        url: str = None,
    ):
        super().__init__(parent)
        self.setMinimumSize(1, 1)
        self.setScaledContents(False)
        self._pixmap = None
        self.setPixmap(pixmap, path, taxon, url)

    def setPixmap(
        self,
        pixmap: QPixmap = None,
        path: Union[str, Path] = None,
        taxon: Taxon = None,
        url: str = None,
    ):
        if path:
            pixmap = QPixmap(str(path))
        elif taxon:
            pixmap = _get_image(taxon.default_photo or Photo(url=taxon.icon_url))
        elif url:
            pixmap = _get_image(Photo(url=url))
        if pixmap:
            self._pixmap = pixmap
            super().setPixmap(self.scaledPixmap())

    def heightForWidth(self, width: int) -> int:
        if self._pixmap:
            return (self._pixmap.height() * width) / self._pixmap.width()
        else:
            return self.height()

    def sizeHint(self) -> QSize:
        return QSize(self.width(), self.heightForWidth(self.width()))

    def scaledPixmap(self) -> QPixmap:
        assert self._pixmap is not None
        return self._pixmap.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)

    def resizeEvent(self, _):
        if self._pixmap:
            super().setPixmap(self.scaledPixmap())


# TODO: Simplify this with changes to Photo model
def _get_image(photo: Photo) -> QPixmap:
    data = INAT_CLIENT.session.get(photo.url, stream=True).content
    pixmap = QPixmap()
    pixmap.loadFromData(data, format=photo.mimetype.replace('image/', ''))
    return pixmap
