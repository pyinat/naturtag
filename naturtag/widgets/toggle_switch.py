"""Material-style toggle switch.
Source: https://stackoverflow.com/a/51825815/15592055
"""
from PySide6.QtCore import Property, QPropertyAnimation, QRectF, QSize, Qt
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QAbstractButton, QSizePolicy


class ToggleSwitch(QAbstractButton):
    def __init__(self, parent=None, track_radius=10, thumb_radius=8):
        super().__init__(parent=parent)
        self.setCheckable(True)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        self._thumb_radius = thumb_radius
        self._track_radius = track_radius
        self._track_opacity = 1

        self._margin = max(0, self._thumb_radius - self._track_radius)
        self._base_offset = max(self._thumb_radius, self._track_radius)
        self._end_offset = {
            True: lambda: self.width() - self._base_offset,
            False: lambda: self._base_offset,
        }
        self._offset = self._base_offset

        palette = self.palette()
        self._thumb_color = {
            True: palette.highlightedText(),
            False: palette.midlight(),
            None: palette.mid(),
        }
        self._track_color = {
            True: palette.highlight(),
            False: palette.dark(),
            None: palette.shadow(),
        }
        self._text_color = {
            True: palette.highlight().color(),
            False: palette.dark().color(),
            None: palette.shadow().color(),
        }
        self._thumb_text = {True: '✔', False: '✕'}

    def get_offset(self):
        return self._offset

    def set_offset(self, value):
        self._offset = value
        self.update()

    offset = Property(int, get_offset, set_offset)

    def sizeHint(self):
        return QSize(
            4 * self._track_radius + 2 * self._margin,
            2 * self._track_radius + 2 * self._margin,
        )

    def setChecked(self, checked):
        super().setChecked(checked)
        self.offset = self._end_offset[checked]()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.offset = self._end_offset[self.isChecked()]()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setPen(Qt.NoPen)
        thumb_opacity = 1.0
        text_opacity = 1.0
        track_opacity = self._track_opacity
        if not self.isEnabled():
            track_opacity *= 0.8

        state = self.isChecked() if self.isEnabled() else None
        track_brush = self._track_color[state]
        thumb_brush = self._thumb_color[state]
        text_color = self._text_color[state]

        p.setBrush(track_brush)
        p.setOpacity(track_opacity)
        p.drawRoundedRect(
            self._margin,
            self._margin,
            self.width() - 2 * self._margin,
            self.height() - 2 * self._margin,
            self._track_radius,
            self._track_radius,
        )
        p.setBrush(thumb_brush)
        p.setOpacity(thumb_opacity)
        p.drawEllipse(
            self.offset - self._thumb_radius,
            self._base_offset - self._thumb_radius,
            2 * self._thumb_radius,
            2 * self._thumb_radius,
        )
        p.setPen(text_color)
        p.setOpacity(text_opacity)
        font = p.font()
        font.setPixelSize(1.5 * self._thumb_radius)
        p.setFont(font)
        p.drawText(
            QRectF(
                self.offset - self._thumb_radius,
                self._base_offset - self._thumb_radius,
                2 * self._thumb_radius,
                2 * self._thumb_radius,
            ),
            Qt.AlignCenter,
            self._thumb_text[self.isChecked()],
        )

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        if event.button() == Qt.LeftButton:
            anim = QPropertyAnimation(self, b'offset', self)
            anim.setDuration(120)
            anim.setStartValue(self.offset)
            anim.setEndValue(self._end_offset[self.isChecked()]())
            anim.start()

    def enterEvent(self, event):
        self.setCursor(Qt.PointingHandCursor)
        super().enterEvent(event)
