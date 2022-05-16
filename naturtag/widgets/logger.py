from logging import FileHandler, Handler, basicConfig, getLogger

from pyinaturalist_convert import PathOrStr
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTextEdit
from rich.logging import RichHandler

from naturtag.constants import LOGFILE


def init_handler(
    level: str = 'DEBUG', root_level: str = 'INFO', logfile: PathOrStr = LOGFILE
) -> 'QtRichHandler':
    """Initialize logging handler and attach to root logger

    Args:
        level: Logging level for naturtag
        root_level: Logging level for root logger (applies to other libraries)
        logfile: Optional log file to write to
    """
    qt_handler = QtRichHandler()
    handlers: list[Handler] = [qt_handler]
    if logfile:
        handlers.append(FileHandler(filename=str(logfile)))

    basicConfig(level=root_level, format='%(message)s', datefmt='[%X]', handlers=handlers)
    getLogger('naturtag').setLevel(level)
    return qt_handler


class QtRichHandler(RichHandler):
    """Logging handler that writes to a Qt widget"""

    def __init__(self):
        super().__init__()
        self.widget = QTextEdit()
        self.widget.setReadOnly(True)
        self.widget.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.widget.setAttribute(Qt.WA_StyledBackground, True)
        self.widget.setObjectName('log_container')

        self.console.record = True
        self.console.width = 120

    def emit(self, record):
        super().emit(record)
        self.widget.append(self.console.export_html())
