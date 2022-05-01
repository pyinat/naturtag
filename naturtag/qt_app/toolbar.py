from logging import getLogger
from typing import Callable

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QToolBar, QWidget
from qtawesome import icon as fa_icon

logger = getLogger(__name__)


# TODO: Is there a better way to connect these buttons to callbacks (slots)?
class Toolbar(QToolBar):
    def __init__(
        self,
        parent: QWidget,
        load_file_callback: Callable,
        run_callback: Callable,
        clear_callback: Callable,
        paste_callback: Callable,
    ):
        super(Toolbar, self).__init__(parent)
        self.setIconSize(QSize(24, 24))
        self.setMovable(False)
        self.setFloatable(False)
        self.setAllowedAreas(Qt.TopToolBarArea)
        self.setStyleSheet('#toolbar { border: none; background-color: transparent; }')

        # get_button('&Run', 'control.png', self.on_toolbar_click, self)
        self.run_button = self.add_button('&Run', 'fa.play', 'Run a thing', run_callback)
        self.addSeparator()

        self.open_button = self.add_button('&Open', 'fa.photo', 'Open images', load_file_callback)
        self.paste_button = self.add_button(
            '&Paste', 'fa5s.paste', 'Paste photos or iNaturalist URLs', paste_callback
        )
        self.clear_button = self.add_button('&Clear', 'fa.remove', 'Clear open images', clear_callback)
        self.addSeparator()

        self.history_button = self.add_button(
            '&History', 'fa5s.history', 'View history', self.on_toolbar_click
        )
        self.history_button.setCheckable(True)
        self.addSeparator()

        self.settings_button = self.add_button('&Settings', 'fa.gear', 'Settings', self.on_toolbar_click)

    def add_button(self, name: str, icon: str, tooltip: str, callback: Callable) -> QAction:
        button_action = QAction(fa_icon(icon), name, self)
        button_action.setStatusTip(tooltip)
        button_action.triggered.connect(callback)
        self.addAction(button_action)
        return button_action

    def on_toolbar_click(self, s):
        """Placeholder"""
        logger.info(f'Click; checked: {s}')
