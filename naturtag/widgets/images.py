"""Generic image widgets"""
from logging import getLogger
from pathlib import Path
from typing import Union

from pyinaturalist import Photo, Taxon
from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QFont, QKeySequence, QPainter, QPixmap, QShortcut
from PySide6.QtWidgets import QApplication, QLabel, QWidget

from naturtag.app.style import fa_icon
from naturtag.client import IMG_SESSION
from naturtag.widgets import VerticalLayout

logger = getLogger(__name__)


class IconLabel(QLabel):
    """A QLabel for displaying a FontAwesome icon"""

    def __init__(self, icon_str: str, parent: QWidget = None, size: int = 20, active: bool = True):
        super().__init__(parent)

        # TODO: Use palette, figure out setting icon state
        icon = fa_icon(icon_str, color='yellowgreen' if active else 'gray')
        self.setPixmap(icon.pixmap(size, size))


class PixmapLabel(QLabel):
    """A QLabel containing a pixmap that preserves its aspect ratio when resizing"""

    def __init__(
        self,
        parent: QWidget = None,
        pixmap: QPixmap = None,
        path: Union[str, Path] = None,
        taxon: Taxon = None,
        url: str = None,
        text: str = None,
    ):
        super().__init__(parent)
        self.setMinimumSize(1, 1)
        self.setScaledContents(False)
        self._pixmap = None
        self.path = None
        self.text = text
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
            pixmap = fetch_image(taxon.default_photo)
        elif url:
            pixmap = fetch_image(Photo(url=url))
        if pixmap is not None:
            self._pixmap = pixmap
            super().setPixmap(self.scaledPixmap())

    def clear(self):
        self.setPixmap(QPixmap())

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

    def paintEvent(self, event):
        """Draw a text overlay on the image"""
        super().paintEvent(event)
        if not self.text:
            return

        font = QFont()
        font.setPixelSize(16)
        painter = QPainter(self)
        painter.setFont(font)

        # Draw a semitransparent background for the text
        metrics = painter.fontMetrics()
        text_width = painter.fontMetrics().horizontalAdvance(self.text)
        bg_color = self.palette().dark().color()
        bg_color.setAlpha(128)
        painter.fillRect(0, 0, text_width + 2, metrics.height() + 2, bg_color)

        painter.drawText(self.rect(), Qt.AlignTop | Qt.AlignLeft, self.text)


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
        shortcut = QShortcut(QKeySequence('Q'), self)
        shortcut.activated.connect(self.close)
        shortcut = QShortcut(QKeySequence(Qt.Key_Right), self)
        shortcut.activated.connect(self.select_next_image)
        shortcut = QShortcut(QKeySequence(Qt.Key_Left), self)
        shortcut.activated.connect(self.select_prev_image)

    @property
    def idx(self) -> int:
        """The index of the currently selected image"""
        return self.image_paths.index(self.selected_path)

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
        self.selected_path = self.image_paths[idx]
        self.set_pixmap(self.selected_path)

    def select_next_image(self):
        self.select_image_idx(self.idx + 1)

    def select_prev_image(self):
        self.select_image_idx(self.idx - 1)

    def set_pixmap(self, path: str):
        self.image.setPixmap(QPixmap(path))
        self.image.text = path


def fetch_image(photo: Photo, size: str = None) -> QPixmap:
    url = photo.url_size(size) if size else photo.url
    data = IMG_SESSION.get(url, stream=True).content
    pixmap = QPixmap()
    pixmap.loadFromData(data, format=photo.ext)
    return pixmap
