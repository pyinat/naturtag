from PySide6.QtCore import Signal

from naturtag.app.threadpool import ThreadPool
from naturtag.settings import Settings
from naturtag.widgets.layouts import StylableWidget


class BaseController(StylableWidget):
    """Base class for controllers, typically in charge of a single tab/screen"""

    on_message = Signal(str)  #: Forward a message to status bar

    def __init__(self, settings: Settings, threadpool: ThreadPool = None):
        super().__init__()
        self.settings = settings
        self.threadpool: ThreadPool = threadpool  # type: ignore
