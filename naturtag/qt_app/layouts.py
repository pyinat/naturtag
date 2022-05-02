"""Source: https://doc.qt.io/qtforpython/examples/example_widgets_layouts_flowlayout.html"""
from functools import reduce
from logging import getLogger
from typing import Union

from PySide6.QtCore import QMargins, QPoint, QRect, QRectF, QSize, QSizeF, Qt
from PySide6.QtWidgets import QGraphicsLayout, QSizePolicy

logger = getLogger(__name__)


class FlowLayout(QGraphicsLayout):
    def __init__(self, parent=None):
        super().__init__(parent)
        if parent is not None:
            self.setContentsMargins(0, 0, 0, 0)
        self._spacing = 5.0
        self._item_list = []

    def __del__(self):
        item = self.takeAt(0)
        while item:
            item = self.takeAt(0)

    def addItem(self, item):
        self._item_list.append(item)
        self.invalidate()

    def count(self):
        return len(self._item_list)

    def itemAt(self, index):
        if 0 <= index < len(self._item_list):
            return self._item_list[index]
        return None

    def takeAt(self, index):
        if 0 <= index < len(self._item_list):
            self.invalidate()
            return self._item_list.pop(index)
        return None

    def expandingDirections(self):
        return Qt.Orientation(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self._do_layout(QRectF(0, 0, width, 0), apply_geom=False)

    def invalidate(self) -> None:
        self.updateGeometry()
        super().invalidate()

    def setGeometry(self, rect):
        # breakpoint()
        super().setGeometry(rect)
        self._do_layout(rect)

    def sizeHint(self, which: Qt.SizeHint, constraint: QSizeF = None):
        if which == Qt.SizeHint.MinimumSize:
            if constraint:
                logger.warning("Const:" + str(constraint))
            return self.minimumSize()
        elif which == Qt.SizeHint.MaximumSize:
            if constraint:
                logger.warning("Const:" + str(constraint))
            return self.maximumSize()
        elif which == Qt.SizeHint.PreferredSize:
            return self.preferredSize(constraint)
        else:
            raise NotImplementedError(f'{which}, {constraint}')

    def minimumSize(self):
        size = QSizeF()
        for item in self._item_list:
            size = size.expandedTo(item.minimumSize())

        top = self.getContentsMargins()[1]  # Returns left, top, right, bottom
        return size + QSizeF(2 * top, 2 * top)

    def maximumSize(self):
        size = QSizeF()
        for item in self._item_list:
            size = size.expandedTo(item.maximumSize())

        top = self.getContentsMargins()[1]  # Returns left, top, right, bottom
        return size + QSizeF(2 * top, 2 * top)

    def preferredSize(self, constraint: QSizeF = None):
        max_width = constraint.width() if constraint and constraint.width() >= 0 else 16777215
        max_height = self.heightForWidth(max_width)
        # h = reduce(QRectF.united, res, QRectF()).size()
        size = QSizeF(max_width, max_height)
        # for item in self._item_list:
        #     size = size.expandedTo(item.preferredSize())

        top = self.getContentsMargins()[1]  # Returns left, top, right, bottom
        return size + QSizeF(2 * top, 2 * top)

    def spacing(self) -> float:
        return self._spacing

    def setSpacing(self, value: float):
        self._spacing = value

    def _do_layout(self, rect, apply_geom=True):
        x = rect.x()
        y = rect.y()
        line_height = 0
        spacing = self.spacing()

        logger.warning(rect)
        for i, item in enumerate(self._item_list):
            size = item.sizeHint(Qt.SizeHint.PreferredSize)
            style = item.widget().style()
            button = QSizePolicy.PushButton
            space_x = spacing  # + style.layoutSpacing(button, button, Qt.Horizontal)
            space_y = spacing  # + style.layoutSpacing(button, button, Qt.Vertical)
            next_x = x + size.width() + space_x

            # Overflow to next line
            logger.debug(
                f'Checking: {next_x}, {space_x}, {rect.right()}, {line_height}, {next_x - space_x > rect.right() and line_height > 0}'
            )
            if next_x - space_x > rect.right() and line_height > 0:
                x = rect.x()
                y = y + line_height + space_y
                next_x = x + size.width() + space_x
                line_height = 0

            if apply_geom:
                logger.info(f'Setting item {i} to {x}, {y}, {size}')
                item.setGeometry(QRectF(QPoint(x, y), size))

            x = next_x
            line_height = max(line_height, size.height())

        return y + line_height - rect.y()
