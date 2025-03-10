"""Generic image widgets and base classes for other page-specific widgets.
Includes plain images, cards, scrollable lists, and fullscreen image views.
"""

from logging import getLogger
from pathlib import Path
from typing import TYPE_CHECKING, Iterator, Optional, TypeAlias, Union

from PySide6.QtCore import QSize, Qt, QThread, Signal
from PySide6.QtGui import QBrush, QFont, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QLabel, QLayout, QScrollArea, QSizePolicy, QWidget

from naturtag.constants import SIZE_ICON, SIZE_ICON_SM, SIZE_SM, IconDimensions, IntOrStr, PathOrStr
from naturtag.widgets import StylableWidget, VerticalLayout
from naturtag.widgets.layouts import GridLayout, HorizontalLayout
from naturtag.widgets.style import fa_icon

if TYPE_CHECKING:
    MIXIN_BASE: TypeAlias = QWidget
else:
    MIXIN_BASE = object

logger = getLogger(__name__)


def set_pixmap_async(
    pixmap_label: QLabel,
    priority: QThread.Priority = QThread.NormalPriority,
    **kwargs,
):
    """Fetch an image from a separate thread, and render it in the main thread when complete"""
    from naturtag.controllers import get_app

    app = get_app()
    future = app.threadpool.schedule(app.img_session.get_pixmap, priority=priority, **kwargs)
    future.on_result.connect(pixmap_label.setPixmap)


def set_pixmap(pixmap_label: QLabel, *args, **kwargs):
    """Fetch an image from either a local path or remote URL."""
    from naturtag.controllers import get_app

    app = get_app()
    pixmap = app.img_session.get_pixmap(*args, **kwargs)
    pixmap_label.setPixmap(pixmap)


class FAIcon(QLabel):
    """A QLabel for displaying a FontAwesome icon"""

    def __init__(
        self,
        icon_str: str,
        parent: Optional[QWidget] = None,
        secondary: bool = False,
        size: IconDimensions = SIZE_ICON,
    ):
        super().__init__(parent)
        x = size if isinstance(size, int) else size[0]
        y = size if isinstance(size, int) else size[1]
        self.icon = fa_icon(icon_str, secondary=secondary)
        self.icon_size = QSize(x, y)
        self.setPixmap(self.icon.pixmap(x, y, mode=QIcon.Mode.Normal))

    def set_enabled(self, enabled: bool = True):
        self.setPixmap(
            self.icon.pixmap(
                self.icon_size,
                mode=QIcon.Mode.Normal if enabled else QIcon.Mode.Disabled,
            ),
        )


class IconLabel(QWidget):
    def __init__(
        self,
        icon_str: str,
        text: IntOrStr,
        size: IconDimensions = SIZE_ICON,
        parent: Optional[QWidget] = None,
        **kwargs,
    ):
        super().__init__(parent)
        y = size if isinstance(size, int) else size[1]
        self.setFixedHeight(y + 15)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)

        self.icon = FAIcon(icon_str, size=size, **kwargs)
        self.label = QLabel()
        self.label.setTextFormat(Qt.RichText)
        self.set_text(text)
        root = HorizontalLayout(self)
        root.addWidget(self.icon)
        root.addWidget(self.label)
        root.setAlignment(Qt.AlignLeft)

    def set_text(self, text: IntOrStr):
        if isinstance(text, int):
            text = format_int(text)
        self.label.setText(text)


class IconLabelList(QWidget):
    """Widget that uses a grid to display a list of icons with labels"""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.grid = GridLayout(self, n_columns=2)
        self.grid.setAlignment(Qt.AlignTop | Qt.AlignLeft)

    def add_line(self, icon_str: str, text: IntOrStr, size: int = SIZE_ICON_SM[0], **kwargs):
        icon = FAIcon(icon_str, size=size, **kwargs)
        self.grid.addWidget(icon)

        text = format_int(text) if isinstance(text, int) else text
        label = QLabel(text)
        label.setTextFormat(Qt.RichText)
        self.grid.addWidget(label)

    def clear(self):
        self.grid.clear()


class PixmapLabel(QLabel):
    """A QLabel containing a pixmap that preserves its aspect ratio when resizing, with optional
    description text
    """

    on_click = Signal(QLabel)

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        pixmap: Optional[QPixmap] = None,
        path: Optional[PathOrStr] = None,
        url: Optional[str] = None,
        description: Optional[str] = None,
        resample: bool = True,
        rounded: bool = False,
        scale: bool = True,
        idx: int = 0,
    ):
        super().__init__(parent)
        self.setMinimumSize(1, 1)
        self.setScaledContents(False)
        self._pixmap = None
        self.idx = idx
        self.path = None
        self.description = description
        self.rounded = rounded
        self.scale = scale
        self.xform = Qt.SmoothTransformation if resample else Qt.FastTransformation
        self.setPixmap(pixmap)
        if path or url:
            set_pixmap(self, path=path, url=url)

    def setPixmap(self, pixmap: QPixmap):
        self._pixmap = pixmap
        super().setPixmap(self.scaledPixmap())

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
        super().mouseReleaseEvent(event)

    def paintEvent(self, event):
        """Optionally draw rounded corners and/or image description text"""
        super().paintEvent(event)
        if self.rounded:
            self._draw_rounded_corners()
        if self.description:
            self._draw_description_text()

    def _draw_rounded_corners(self):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        brush = QBrush(self._pixmap)
        painter.setBrush(brush)
        painter.drawRoundedRect(self._pixmap.rect(), 6, 6)

    def _draw_description_text(self):
        painter = QPainter(self)
        font = QFont()
        font.setPixelSize(16)
        painter.setFont(font)

        # Get text dimensions
        lines = self.description.split('\n')
        longest_line = max(lines, key=len)
        metrics = painter.fontMetrics()
        text_width = painter.fontMetrics().horizontalAdvance(longest_line)
        text_height = metrics.height() * len(lines)

        # Draw text with a semitransparent background
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
            return self._pixmap
        elif self._pixmap.isNull() or not self.scale:
            return self._pixmap
        return self._pixmap.scaled(self.size(), Qt.KeepAspectRatio, self.xform)

    def sizeHint(self) -> QSize:
        return QSize(self.width(), self.heightForWidth(self.width()))


class HoverMixin(MIXIN_BASE):
    """Mixin that adds a transparent overlay to darken the image on hover (handled in QSS)

    Args:
        hover_icon: Add an 'open' icon on hover
        hover_event: Set to ``False`` to disable overlay on hover
            (e.g., to use parent widget hover event instead)
    """

    def __init__(self, *args, hover_icon: bool = False, hover_event: bool = True, **kwargs):
        super().__init__(*args, **kwargs)
        self.overlay = FAIcon('mdi.open-in-new', self, size=64) if hover_icon else QLabel(self)
        self.overlay.setAlignment(Qt.AlignTop)
        self.overlay.setAutoFillBackground(True)
        self.overlay.setGeometry(self.geometry())
        self.overlay.setObjectName('hover_overlay')
        self.overlay.setVisible(False)
        self.hover_event = hover_event

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.overlay.setFixedSize(self.size())

    def enterEvent(self, event):
        if self.hover_event:
            self.overlay.setVisible(True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        if self.hover_event:
            self.overlay.setVisible(False)
        super().leaveEvent(event)


class HoverPhoto(HoverMixin, PixmapLabel):
    """PixmapLabel with a hover effect"""


class HoverIcon(FAIcon):
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
        super().mouseReleaseEvent(event)


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


class InfoCard(StylableWidget):
    """Card containing a thumbnail and additional details"""

    on_click = Signal(int)

    def __init__(self, card_id: Optional[int] = None):
        super().__init__()
        card_layout = HorizontalLayout(self)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.card_id = card_id

        # Image
        self.thumbnail = HoverPhoto(rounded=True, hover_event=False)  # Use card hover event
        self.thumbnail.setFixedSize(*SIZE_SM)
        self.thumbnail.setObjectName('thumbnail')
        card_layout.addWidget(self.thumbnail)

        # Details
        self.title = QLabel()
        self.title.setTextFormat(Qt.RichText)
        self.title.setObjectName('h2')
        # Don't let text steal mouse focus; pass click events to the card
        self.title.mouseReleaseEvent = self.mouseReleaseEvent

        self.details_layout = VerticalLayout()
        self.details_layout.setAlignment(Qt.AlignLeft)
        self.details_layout.addWidget(self.title)
        card_layout.addLayout(self.details_layout)

    def add_row(self, item: Union[QLayout, QWidget]):
        """Add a layout or widget as a row of info to the card"""
        if isinstance(item, QLayout):
            self.details_layout.addLayout(item)
        else:
            self.details_layout.addWidget(item)

    def enterEvent(self, event):
        """Note on hover effect:
        * Thumbnail: this method triggers overlay
        * Card background: Handled in QSS
        """
        self.thumbnail.overlay.setVisible(True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.thumbnail.overlay.setVisible(False)
        super().leaveEvent(event)

    def mousePressEvent(self, _):
        """Placeholder to accept mouse press events"""

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.on_click.emit(self.card_id)


class InfoCardList(StylableWidget):
    """A scrollable list of InfoCards"""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.root = VerticalLayout(self)
        self.root.setAlignment(Qt.AlignTop)
        self.root.setContentsMargins(0, 5, 5, 0)

        self.scroller = QScrollArea()
        self.scroller.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroller.setWidgetResizable(True)
        self.scroller.setWidget(self)

    @property
    def cards(self) -> Iterator[InfoCard]:
        for item in self.children():
            if isinstance(item, InfoCard):
                yield item

    def add_card(self, card: InfoCard, thumbnail_url: str, idx: Optional[int] = None):
        """Add a card immediately, and load its thumbnail from a separate thread"""
        if idx is not None:
            self.root.insertWidget(idx, card)
        else:
            self.root.addWidget(card)
        set_pixmap_async(card.thumbnail, url=thumbnail_url)

    def clear(self):
        self.root.clear()

    def contains(self, card_id: int) -> bool:
        return self.get_card_by_id(card_id) is not None

    def get_card_by_id(self, card_id: int) -> Optional[InfoCard]:
        for card in self.cards:
            if card.card_id == card_id:
                return card
        return None

    def move_card(self, card_id: int, idx: int = 0) -> bool:
        """Move a card to the specified position, if found; return ``False`` otherwise"""
        card = self.get_card_by_id(card_id)
        if card:
            self.root.removeWidget(card)
            self.root.insertWidget(idx, card)
            return True
        return False


class ImageWindow(StylableWidget):
    """Display local images in fullscreen as a separate window

    Keyboard shortcuts: Escape to close window, Left and Right to cycle through images
    """

    on_remove = Signal(Path)  #: Request for image to be removed from list

    def __init__(self):
        super().__init__()
        self.image_paths: list[Path] = []
        self.selected_path = Path('.')
        self.setWindowTitle('Naturtag')

        self.image = FullscreenPhoto()
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

    def display_image_fullscreen(self, selected_path: Path, image_paths: list[Path]):
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


def format_int(value: int) -> str:
    if value >= 1000000:
        return f'{int(value / 1000000)}M'
    elif value >= 10000:
        return f'{int(value / 1000)}K'
    else:
        return str(value)
