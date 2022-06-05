from logging import getLogger

from PySide6.QtCore import QEvent, Signal
from PySide6.QtGui import QAction, QIntValidator
from PySide6.QtWidgets import QLineEdit, QToolButton

from naturtag.app.style import fa_icon

logger = getLogger(__name__)


class IdInput(QLineEdit):
    """Pressing return or losing focus will send an 'on_select' signal"""

    on_clear = Signal()  #: Wrapper for 'clear' button signal
    on_select = Signal(int)  #: An ID was selected

    def __init__(self):
        super().__init__()
        self.setValidator(QIntValidator())
        self.setMaximumWidth(200)
        self.setClearButtonEnabled(True)
        self.findChild(QToolButton).setIcon(fa_icon('mdi.backspace'))
        self.findChild(QAction).triggered.connect(self.on_clear)
        self.returnPressed.connect(self.select)

    def focusOutEvent(self, event: QEvent = None):
        self.select()
        return super().focusOutEvent(event)

    def select(self):
        if self.text():
            self.on_select.emit(int(self.text()))

    def set_id(self, id: int):
        self.setText(str(id))
        self.select()
