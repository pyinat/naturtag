from logging import getLogger
from typing import Callable

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import QApplication, QMenu, QSizePolicy, QToolBar, QWidget

from naturtag.app.style import fa_icon
from naturtag.settings import Settings

logger = getLogger(__name__)


# TODO: Is there a better way to connect these buttons to callbacks (slots)?
class Toolbar(QToolBar):
    """Main toolbar and keyboard shortcut definitions. Actions are reused by app menu."""

    def __init__(
        self,
        parent: QWidget,
        load_file_callback: Callable,
        run_callback: Callable,
        clear_callback: Callable,
        paste_callback: Callable,
        fullscreen_callback: Callable,
        log_callback: Callable,
        settings_callback: Callable,
    ):
        super(Toolbar, self).__init__(parent)
        self.setIconSize(QSize(24, 24))
        self.setMovable(False)
        self.setFloatable(False)
        self.setAllowedAreas(Qt.TopToolBarArea)
        self.setStyleSheet('#toolbar { border: none; background-color: transparent; }')

        self.run_button = self.add_button(
            '&Run',
            tooltip='Apply tags to images',
            icon='fa.play',
            shortcut='Ctrl+R',
            callback=run_callback,
        )
        self.addSeparator()
        self.open_button = self.add_button(
            '&Open',
            tooltip='Open images',
            icon='ri.image-add-fill',
            shortcut='Ctrl+O',
            callback=load_file_callback,
        )
        self.paste_button = self.add_button(
            '&Paste',
            tooltip='Paste photos or iNaturalist URLs',
            icon='fa5s.paste',
            shortcut='Ctrl+V',
            callback=paste_callback,
        )
        self.clear_button = self.add_button(
            '&Clear',
            tooltip='Clear open images',
            icon='fa.remove',
            shortcut='Ctrl+Shift+X',
            callback=clear_callback,
        )
        self.addSeparator()
        self.settings_button = self.add_button(
            '&Settings',
            tooltip='Settings',
            icon='fa.gear',
            callback=settings_callback,
        )

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.addWidget(spacer)

        self.fullscreen_button = self.add_button(
            '&Fullscreen',
            tooltip='Toggle fullscreen mode',
            icon='mdi.fullscreen',
            shortcut=Qt.Key_F11,
            callback=fullscreen_callback,
        )

        # Extra actions not added to the toolbar, but used by the menu
        self.exit_button = self.add_button(
            '&Exit',
            tooltip='Exit to desktop',
            icon='mdi.exit-run',
            shortcut='Ctrl+Q',
            callback=QApplication.instance().quit,
            visible=False,
        )
        self.logs_button = self.add_button(
            'Show &Logs',
            tooltip='Show tab with debug logs',
            icon='fa.file-text-o',
            callback=log_callback,
            visible=False,
        )
        self.logs_button.setCheckable(True)

    def add_button(
        self,
        name: str,
        tooltip: str,
        icon: str,
        shortcut: str = None,
        callback: Callable = None,
        visible: bool = True,
    ) -> QAction:
        action = QAction(fa_icon(icon), name, self)
        if tooltip:
            action.setStatusTip(tooltip)
        if shortcut:
            action.setShortcut(QKeySequence(shortcut))
        if callback:
            action.triggered.connect(callback)
        if visible:
            self.addAction(action)
        return action

    def _placeholder(self, s):
        logger.info(f'Click; checked: {s}')

    def populate_menu(self, menu: QMenu, settings: Settings):
        """Populate the application menu using actions defined on the toolbar"""
        file_menu = menu.addMenu('&File')
        file_menu.addAction(self.run_button)
        file_menu.addAction(self.open_button)
        file_menu.addAction(self.paste_button)
        file_menu.addAction(self.clear_button)
        file_menu.addAction(self.exit_button)

        view_menu = menu.addMenu('&View')
        view_menu.addAction(self.fullscreen_button)
        view_menu.addAction(self.logs_button)
        self.logs_button.setChecked(settings.show_logs)

        settings_menu = menu.addMenu('&Settings')
        settings_menu.addAction(self.settings_button)
