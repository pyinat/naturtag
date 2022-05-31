"""Generic image widgets"""
from logging import getLogger
from pathlib import Path
from typing import Union

from pyinaturalist import Photo
from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor, QFont, QIcon, QKeySequence, QPainter, QPixmap, QShortcut
from PySide6.QtWidgets import QLabel, QWidget

from naturtag.app.style import fa_icon
from naturtag.client import IMG_SESSION
from naturtag.widgets import VerticalLayout

logger = getLogger(__name__)


class IconLabel(QLabel):
    """A QLabel for displaying a FontAwesome icon"""

    def __init__(
        self,
        icon_str: str,
        parent: QWidget = None,
        size: int = 32,
        color: QColor = None,
    ):
        super().__init__(parent)
        self.icon = fa_icon(icon_str, color=color)
        self.icon_size = QSize(size, size)
        self.setPixmap(self.icon.pixmap(size, size, mode=QIcon.Mode.Normal))

    def set_enabled(self, enabled: bool = True):
        self.setPixmap(
            self.icon.pixmap(
                self.icon_size,
                mode=QIcon.Mode.Normal if enabled else QIcon.Mode.Disabled,
            ),
        )


class PixmapLabel(QLabel):
    """A QLabel containing a pixmap that preserves its aspect ratio when resizing, with optional
    description text
    """

    def __init__(
        self,
        parent: QWidget = None,
        pixmap: QPixmap = None,
        path: Union[str, Path] = None,
        url: str = None,
        description: str = None,
    ):
        super().__init__(parent)
        self.setMinimumSize(1, 1)
        self.setScaledContents(False)
        self._pixmap = None
        self.path = None
        self.description = description
        self.set_pixmap(pixmap, path, url)

    def set_pixmap(
        self,
        pixmap: QPixmap = None,
        path: Union[str, Path] = None,
        url: str = None,
    ):
        if path:
            pixmap = QPixmap(str(path))
        elif url:
            pixmap = IMG_SESSION.get_pixmap(Photo(url=url))
        if pixmap is not None:
            self._pixmap = pixmap
            super().setPixmap(self.scaledPixmap())

    def clear(self):
        self.set_pixmap(QPixmap())

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
        """Draw description text in the upper left corner of the image"""
        super().paintEvent(event)
        if not self.description:
            return

        font = QFont()
        font.setPixelSize(16)
        painter = QPainter(self)
        painter.setFont(font)

        # Get text dimensions
        lines = self.description.split('\n')
        longest_line = max(lines, key=len)
        metrics = painter.fontMetrics()
        text_width = painter.fontMetrics().horizontalAdvance(longest_line)
        text_height = metrics.height() * len(lines)

        # Draw text with a a semitransparent background
        bg_color = self.palette().dark().color()
        bg_color.setAlpha(128)
        painter.fillRect(0, 0, text_width + 2, text_height + 2, bg_color)
        painter.drawText(self.rect(), Qt.AlignTop | Qt.AlignLeft, self.description)


class HoverMixin:
    """Mixin that adds a transparent overlay to darken the image on hover"""

    def __init__(self, *args, hover_icon: bool = False, **kwargs):
        super().__init__(*args, **kwargs)
        self.overlay = IconLabel('mdi.open-in-new', self, size=64) if hover_icon else QLabel(self)
        self.overlay.setAlignment(Qt.AlignTop)
        self.overlay.setAutoFillBackground(True)
        self.overlay.setGeometry(self.geometry())
        self.overlay.setObjectName('hover_overlay')
        self.overlay.setVisible(False)
        self.enterEvent = lambda *x: self.overlay.setVisible(True)
        self.leaveEvent = lambda *x: self.overlay.setVisible(False)


class ImageWindow(QWidget):
    """Display local images in fullscreen as a separate window

    Keyboard shortcuts: Escape to close window, Left and Right to cycle through images
    """

    def __init__(self, image_class: type = PixmapLabel):
        super().__init__()
        self.image_paths: list[str] = []
        self.selected_path = None

        self.image = image_class()
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

    def display_image(self, selected_path: str, image_paths: list[str]):
        """Open window to a selected image, and save other available image paths for navigation"""
        self.selected_path = selected_path
        self.image_paths = image_paths
        self.set_pixmap(self.selected_path)
        self.showFullScreen()

    def select_image_idx(self, idx: int):
        """Select an image by index"""
        self.selected_path = self.image_paths[idx]
        self.set_pixmap(self.selected_path)

    def select_next_image(self):
        self.select_image_idx(self.wrap_idx(1))

    def select_prev_image(self):
        self.select_image_idx(self.wrap_idx(-1))

    def set_pixmap(self, path: str):
        self.image.set_pixmap(QPixmap(path))
        self.image.description = str(path)

    def wrap_idx(self, increment: int):
        """Increment and wrap the index around to the other side of the list"""
        idx = self.idx + increment
        if idx < 0:
            idx = len(self.image_paths) - 1
        elif idx >= len(self.image_paths):
            idx = 0
        return idx
