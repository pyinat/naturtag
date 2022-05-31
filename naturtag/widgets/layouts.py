"""Source:
* https://doc.qt.io/qtforpython/examples/example_widgets_layouts_flowlayout.html
* Many hours of frustration
"""
from logging import getLogger
from typing import TYPE_CHECKING, Iterator, Optional, TypeAlias

from PySide6.QtCore import QPoint, QRect, QSize, Qt
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import (
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLayout,
    QSizePolicy,
    QStyle,
    QStyleOption,
    QVBoxLayout,
    QWidget,
)

logger = getLogger(__name__)

if TYPE_CHECKING:
    MIXIN_BASE: TypeAlias = QLayout
else:
    MIXIN_BASE = object


class LayoutMixin(MIXIN_BASE):
    """Layout mixin with some extra convenience methods"""

    def __del__(self):
        try:
            self.clear()
        except RuntimeError:
            pass

    def clear(self):
        for i in reversed(range(self.count())):
            child = self.takeAt(i)
            if child.widget():
                child.widget().deleteLater()

    @property
    def widgets(self) -> Iterator[QWidget]:
        for i in range(self.count()):
            item = self.itemAt(i)
            if item and (widget := item.widget()):
                yield widget


class GroupMixin(MIXIN_BASE):
    def add_group(self, name: str, parent: QLayout = None, width: int = None) -> 'VerticalLayout':
        """Add a new groupbox with a vertical layout"""
        group_box = QGroupBox(name)
        group_layout = VerticalLayout(group_box)
        parent = parent or self
        parent.addWidget(group_box)
        if width:
            group_box.setFixedWidth(width)
            group_box.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        return group_layout


class StyleMixin:
    def paintEvent(self, event):
        """Allow custom widgets to be styled with QSS"""
        super().paintEvent(event)
        opt = QStyleOption()
        opt.initFrom(self)
        painter = QPainter(self)
        style = self.style()
        style.drawPrimitive(QStyle.PE_Widget, opt, painter, self)


class FlowLayout(LayoutMixin, QLayout):
    def __init__(self, parent=None, spacing: float = None):
        super().__init__(parent)
        if parent is not None:
            self.setContentsMargins(0, 0, 0, 0)
        self._items: list[QWidget] = []
        self._spacing = spacing or 0

    def addItem(self, item: QWidget):
        self._items.append(item)
        self.invalidate()

    def count(self):
        return len(self._items)

    def itemAt(self, index: int) -> Optional[QWidget]:
        if 0 <= index < len(self._items):
            return self._items[index]
        return None

    def takeAt(self, index: int) -> Optional[QWidget]:
        if 0 <= index < len(self._items):
            item = self._items.pop(index)
            return item
        return None

    def expandingDirections(self):
        return Qt.Orientation(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width: int):
        return self._do_layout(QRect(0, 0, width, 0), apply_geom=False)

    def setGeometry(self, rect: QRect):
        super().setGeometry(rect)
        self._do_layout(rect)

    def sizeHint(self, which: Qt.SizeHint = None, constraint: QSize = None):
        which = which or Qt.MinimumSize
        if which == Qt.SizeHint.MinimumSize:
            return self.minimumSize()
        elif which == Qt.SizeHint.MaximumSize:
            return self.maximumSize()
        elif which == Qt.SizeHint.PreferredSize:
            return self.preferredSize(constraint)
        else:
            raise NotImplementedError(f'{which}, {constraint}')

    def minimumSize(self):
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())

        top = self.getContentsMargins()[1]  # Returns left, top, right, bottom
        return size + QSize(2 * top, 2 * top)

    def maximumSize(self):
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.maximumSize())

        top = self.getContentsMargins()[1]
        return size + QSize(2 * top, 2 * top)

    def preferredSize(self, constraint: QSize = None):
        max_width = constraint.width() if constraint and constraint.width() >= 0 else 1440
        max_height = self.heightForWidth(max_width)
        size = QSize(max_width, max_height)
        for item in self._items:
            size = size.expandedTo(item.preferredSize())

        top = self.getContentsMargins()[1]
        return size + QSize(2 * top, 2 * top)

    def spacing(self) -> float:
        return self._spacing

    def setSpacing(self, value: float):
        self._spacing = value

    def _do_layout(self, rect, apply_geom=True):
        x = rect.x()
        y = rect.y()
        line_height = 0
        spacing = self.spacing()

        for item in self._items:
            size = item.sizeHint()
            next_x = x + size.width() + spacing

            # Overflow to next line
            if next_x - spacing > rect.right() and line_height > 0:
                x = rect.x()
                y += line_height + spacing
                next_x = x + size.width() + spacing
                line_height = 0

            if apply_geom:
                item.setGeometry(QRect(QPoint(x, y), size))

            x = next_x
            line_height = max(line_height, size.height())

        return y + line_height - rect.y()


class GridLayout(LayoutMixin, GroupMixin, QGridLayout):
    def __init__(self, parent=None, n_columns: int = None):
        super().__init__(parent)
        self._n_columns = n_columns
        self._col = 0
        self._row = 0

    def add_widget(self, item):
        self.addWidget(item, self._row, self._col)
        self._col += 1
        if self._n_columns and self._col >= self._n_columns:
            self._col = 0
            self._row += 1

    def clear(self):
        super().clear()
        self._col = 0
        self._row = 0


class HorizontalLayout(LayoutMixin, GroupMixin, QHBoxLayout):
    pass


class VerticalLayout(LayoutMixin, GroupMixin, QVBoxLayout):
    pass


class StylableWidget(StyleMixin, GroupMixin, QWidget):
    pass
