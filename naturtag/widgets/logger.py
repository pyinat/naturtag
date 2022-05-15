from logging import basicConfig, getLogger

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTextEdit
from rich.logging import RichHandler


def init_handler(root_level='INFO') -> 'QtRichHandler':
    """Initialize logging handler and attach to root logger"""
    log_handler = QtRichHandler()
    basicConfig(level=root_level, format='%(message)s', datefmt='[%X]', handlers=[log_handler])
    getLogger('naturtag').setLevel('DEBUG')
    return log_handler


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
