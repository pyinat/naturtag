from PySide6.QtCore import QEvent, Signal
from PySide6.QtGui import QIntValidator
from PySide6.QtWidgets import QLineEdit, QToolButton

from naturtag.app.style import fa_icon


class IdInput(QLineEdit):
    """Pressing return or losing focus will send an 'on_select' signal"""

    on_select = Signal(int)

    def __init__(self):
        super().__init__()
        self.setClearButtonEnabled(True)
        self.setValidator(QIntValidator())
        self.setMaximumWidth(200)
        self.findChild(QToolButton).setIcon(fa_icon('mdi.backspace'))
        self.returnPressed.connect(self.select)

    def focusOutEvent(self, event: QEvent = None):
        self.select()
        return super().focusOutEvent(event)

    def select(self):
        if self.text():
            self.on_select.emit(int(self.text()))
