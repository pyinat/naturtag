from logging import Handler, basicConfig

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTextEdit
from rich.logging import RichHandler


class QPlainTextEditLogger(RichHandler):
    """Logging handler that writes to a Qt widget"""

    def __init__(self):
        super().__init__()
        self.widget = QTextEdit()
        self.widget.setReadOnly(True)
        self.widget.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        # self.widget.setAutoFillBackground(True)
        # p = self.widget.palette()
        # p.setColor(self.widget.backgroundRole(), Qt.red)
        # self.widget.setPalette(p)
        self.widget.setAttribute(Qt.WA_StyledBackground, True)
        self.widget.setStyleSheet('background-color: #ceddf0;')

        self.console.record = True
        # self.console.width = self.widget.sizeHint().width() - 2
        self.console.width = 120

    def emit(self, record):
        # with self.console.capture() as capture:
        #     super().emit(record)
        # self.widget.setHtml(capture.get())
        super().emit(record)
        self.widget.append(self.console.export_html())


# getLogger('naturtag').addHandler(LOG_HANDLER)
# getLogger('pyinaturalist').addHandler(LOG_HANDLER)


def init_handler() -> Handler:
    log_handler = QPlainTextEditLogger()
    basicConfig(level='DEBUG', format='%(message)s', datefmt='[%X]', handlers=[log_handler])
    return log_handler
