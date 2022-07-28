"""Generic image widgets"""
from logging import getLogger
from pathlib import Path
from typing import TYPE_CHECKING, Type, TypeAlias

from pyinaturalist import Photo
from PySide6.QtCore import QSize, Qt, QThread, Signal
from PySide6.QtGui import QFont, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QLabel, QWidget

from naturtag.app.style import fa_icon
from naturtag.app.threadpool import ThreadPool
from naturtag.client import IMG_SESSION
from naturtag.constants import SIZE_ICON, PathOrStr
from naturtag.widgets import StylableWidget, VerticalLayout

if TYPE_CHECKING:
    MIXIN_BASE: TypeAlias = QWidget
else:
    MIXIN_BASE = object

logger = getLogger(__name__)


class IconLabel(QLabel):
    """A QLabel for displaying a FontAwesome icon"""

    def __init__(
        self,
        icon_str: str,
        parent: QWidget = None,
        secondary: bool = False,
        size: int = SIZE_ICON[0],
    ):
        super().__init__(parent)
        self.icon = fa_icon(icon_str, secondary=secondary)
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

    on_click = Signal(QLabel)

    def __init__(
        self,
        parent: QWidget = None,
        pixmap: QPixmap = None,
        path: PathOrStr = None,
        url: str = None,
        description: str = None,
        resample: bool = True,
        scale: bool = True,
    ):
        super().__init__(parent)
        self.setMinimumSize(1, 1)
        self.setScaledContents(False)
        self._pixmap = None
        self.path = None
        self.description = description
        self.scale = scale
        self.xform = Qt.SmoothTransformation if resample else Qt.FastTransformation
        if path or url:
            pixmap = self.get_pixmap(path=path, url=url)
        self.setPixmap(pixmap)

    def get_pixmap(
        self,
        path: PathOrStr = None,
        photo: Photo = None,
        size: str = None,
        url: str = None,
    ) -> QPixmap:
        """Fetch a pixmap from either a local path or remote URL.
        This does not render the image, so it is safe to run from any thread.
        """
        if path:
            self._pixmap = QPixmap(str(path))
        elif photo or url:
            self._pixmap = IMG_SESSION.get_pixmap(photo, url, size)
        return self._pixmap

    def setPixmap(self, pixmap: QPixmap):
        self._pixmap = pixmap
        super().setPixmap(self.scaledPixmap())

    def set_pixmap_async(
        self,
        threadpool: ThreadPool,
        priority: QThread.Priority = QThread.NormalPriority,
        path: PathOrStr = None,
        photo: Photo = None,
        size: str = 'medium',
        url: str = None,
    ):
        """Fetch a photo from a separate thread, and render it in the main thread when complete"""
        future = threadpool.schedule(
            self.get_pixmap,
            priority=priority,
            path=path,
            photo=photo,
            url=url,
            size=size,
        )
        future.on_result.connect(self.setPixmap)

    def clear(self):
        self.setPixmap(QPixmap())

    def heightForWidth(self, width: int) -> int:
        if self._pixmap:
            return (self._pixmap.height() * width) / self._pixmap.width()
        else:
            return self.height()

    def mousePressEvent(self, _):
        """Placeholder to accept mouse press events"""

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.on_click.emit(self)

    def paintEvent(self, event):
        """Draw optional description text in the upper left corner of the image"""
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

    def resizeEvent(self, _):
        if self._pixmap:
            super().setPixmap(self.scaledPixmap())

    def scaledPixmap(self) -> QPixmap:
        if self._pixmap is None:
            self._pixmap = QPixmap()
        if not self.scale:
            return self._pixmap
        if TYPE_CHECKING:
            assert self._pixmap is not None
        return self._pixmap.scaled(self.size(), Qt.KeepAspectRatio, self.xform)

    def sizeHint(self) -> QSize:
        return QSize(self.width(), self.heightForWidth(self.width()))


class HoverMixinBase(MIXIN_BASE):
    """Base class for HoverMixin, to allow activating overlay on parent hover"""

    def __init__(self, *args, hover_icon: bool = False, **kwargs):
        super().__init__(*args, **kwargs)
        self.overlay = IconLabel('mdi.open-in-new', self, size=64) if hover_icon else QLabel(self)
        self.overlay.setAlignment(Qt.AlignTop)
        self.overlay.setAutoFillBackground(True)
        self.overlay.setGeometry(self.geometry())
        self.overlay.setObjectName('hover_overlay')
        self.overlay.setVisible(False)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.overlay.setFixedSize(self.size())


class HoverMixin(HoverMixinBase):
    """Mixin that adds a transparent overlay to darken the image on hover (handled in QSS)"""

    def enterEvent(self, event):
        self.overlay.setVisible(True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.overlay.setVisible(False)
        super().leaveEvent(event)


class HoverIcon(IconLabel):
    """IconLabel with a hover effect and click event"""

    on_click = Signal(object)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_enabled(False)
        self.enterEvent = lambda *x: self.set_enabled(True)
        self.leaveEvent = lambda *x: self.set_enabled(False)

    def mousePressEvent(self, _):
        """Placeholder to accept mouse press events"""

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.on_click.emit(self)


class NavButtonsMixin(MIXIN_BASE):
    """Mixin for fullscreen images that adds left and right navigation buttons"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.left_arrow = HoverIcon('ph.caret-left', self, size=128)
        self.right_arrow = HoverIcon('ph.caret-right', self, size=128)

    def resizeEvent(self, event):
        """Position nav buttons on left/right center"""
        self.left_arrow.setGeometry(0, (self.height() - 128) / 2, 128, 128)
        self.right_arrow.setGeometry(self.width() - 128, (self.height() - 128) / 2, 128, 128)
        super().resizeEvent(event)


class FullscreenPhoto(NavButtonsMixin, PixmapLabel):
    """A fullscreen photo widget with nav buttons"""


class ImageWindow(StylableWidget):
    """Display local images in fullscreen as a separate window

    Keyboard shortcuts: Escape to close window, Left and Right to cycle through images
    """

    on_remove = Signal(Path)  #: Request for image to be removed from list

    def __init__(self, image_class: Type[FullscreenPhoto] = FullscreenPhoto):
        super().__init__()
        self.image_paths: list[Path] = []
        self.selected_path = Path('.')
        self.setWindowTitle('Naturtag')

        self.image = image_class()
        self.image.setAlignment(Qt.AlignCenter)
        self.image_layout = VerticalLayout(self)
        self.image_layout.addWidget(self.image)
        self.image_layout.setContentsMargins(0, 0, 0, 0)

        # Nav button actions
        self.image.left_arrow.on_click.connect(self.select_prev_image)
        self.image.right_arrow.on_click.connect(self.select_next_image)

        # Keyboard shortcuts
        self.add_shortcut(Qt.Key_Escape, self.close)
        self.add_shortcut('Q', self.close)
        self.add_shortcut(Qt.Key_Right, self.select_next_image)
        self.add_shortcut(Qt.Key_Left, self.select_prev_image)
        self.add_shortcut(Qt.Key_Delete, self.remove_image)

    @property
    def idx(self) -> int:
        """The index of the currently selected image"""
        return self.image_paths.index(self.selected_path)

    def display_image(self, selected_path: Path, image_paths: list[Path]):
        """Open window to a selected image, and save other available image paths for navigation"""
        self.selected_path = selected_path
        self.image_paths = image_paths
        self.set_pixmap_path(self.selected_path)
        self.showFullScreen()

    def select_image_idx(self, idx: int):
        """Select an image by index"""
        self.selected_path = self.image_paths[idx]
        self.set_pixmap_path(self.selected_path)

    def select_next_image(self):
        self.select_image_idx(self.wrap_idx(1))

    def select_prev_image(self):
        self.select_image_idx(self.wrap_idx(-1))

    def set_pixmap_path(self, path: PathOrStr):
        self.image.setPixmap(QPixmap(str(path)))
        self.image.description = str(path)

    def remove_image(self):
        """Remove the current image from the list"""
        remove_path = self.selected_path
        if len(self.image_paths) > 1:
            self.select_next_image()
            self.image_paths.remove(remove_path)
        # If the last image was removed, close the window
        else:
            self.close()
        self.on_remove.emit(remove_path)

    def wrap_idx(self, increment: int):
        """Increment and wrap the index around to the other side of the list"""
        idx = self.idx + increment
        if idx < 0:
            idx = len(self.image_paths) - 1
        elif idx >= len(self.image_paths):
            idx = 0
        return idx
