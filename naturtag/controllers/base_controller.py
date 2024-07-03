from typing import TYPE_CHECKING

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QApplication

from naturtag.widgets.layouts import StylableWidget

if TYPE_CHECKING:
    from naturtag.app import NaturtagApp


class BaseController(StylableWidget):
    """Base class for controllers, typically in charge of a single tab/screen"""

    on_message = Signal(str)  #: Forward a message to status bar

    @property
    def app(self) -> 'NaturtagApp':
        return QApplication.instance()

    def info(self, message: str):
        self.on_message.emit(message)
