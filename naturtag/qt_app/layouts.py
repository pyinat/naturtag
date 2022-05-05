"""Source:
* https://doc.qt.io/qtforpython/examples/example_widgets_layouts_flowlayout.html
* Many hours of frustration
"""
from logging import getLogger

from PySide6.QtCore import QPoint, QRect, QSize, Qt
from PySide6.QtWidgets import QLayout

logger = getLogger(__name__)


class FlowLayout(QLayout):
    def __init__(self, parent=None):
        super().__init__(parent)
        if parent is not None:
            self.setContentsMargins(0, 0, 0, 0)
        self._spacing = 4.0
        self._items = []

    def __del__(self):
        self.clear()

    def clear(self):
        while item := self.takeAt(0):
            if item.widget():
                item.widget().setParent(None)

    def addItem(self, item):
        self._items.append(item)
        self.invalidate()

    def count(self):
        return len(self._items)

    def itemAt(self, index):
        if 0 <= index < len(self._items):
            return self._items[index]
        return None

    def takeAt(self, index):
        if 0 <= index < len(self._items):
            item = self._items.pop(index)
            return item
        return None

    def expandingDirections(self):
        return Qt.Orientation(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self._do_layout(QRect(0, 0, width, 0), apply_geom=False)

    def setGeometry(self, rect):
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
