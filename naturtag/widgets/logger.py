from logging import FileHandler, Formatter, LogRecord, getLogger

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTextEdit
from rich.logging import RichHandler

from naturtag.constants import PathOrStr


def init_handler(
    level: str = 'DEBUG', root_level: str = 'INFO', logfile: PathOrStr = 'log.log'
) -> 'QtRichHandler':
    """Initialize logging handler and attach to root logger

    Args:
        level: Logging level for naturtag
        root_level: Logging level for root logger (applies to other libraries)
        logfile: Optional log file to write to
    """
    qt_handler = QtRichHandler()
    root = getLogger()
    root.setLevel(root_level)
    root.addHandler(qt_handler)

    # iI a logfile is specified, add a FileHandler with a separate formatter
    if logfile:
        handler = FileHandler(filename=str(logfile))
        handler.setFormatter(
            Formatter(
                '%(asctime)s [%(levelname)8s] [%(threadName)10s:%(name)s] %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S',
            ),
        )
        root.addHandler(handler)

    getLogger('naturtag').setLevel(level)
    return qt_handler


class QtRichHandler(RichHandler):
    """Logging handler that writes to a Qt widget"""

    def __init__(self):
        super().__init__()
        self.widget = None
        self.widget = QTextEdit()
        self.widget.setReadOnly(True)
        self.widget.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.widget.setAttribute(Qt.WA_StyledBackground, True)
        self.widget.setObjectName('log_container')

        self.console.record = True
        self.console.width = 120

    def emit(self, record: LogRecord):
        super().emit(record)
        if self.widget:
            self.widget.append(self.console.export_html())
