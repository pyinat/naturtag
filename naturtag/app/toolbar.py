"""Configuration for toolbar, menu bar, and main keyboard shortcuts"""
from logging import getLogger
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import QMenu, QSizePolicy, QToolBar, QWidget

from naturtag.app.style import fa_icon

HOME_DIR = str(Path.home())
logger = getLogger(__name__)


class Toolbar(QToolBar):
    def __init__(self, parent: QWidget):
        super(Toolbar, self).__init__(parent)
        self.setIconSize(QSize(24, 24))
        self.recent_dirs: list[Path] = []
        self.recent_dirs_submenu = QMenu('Open Recent')

        self.run_button = self.add_button(
            '&Run', tooltip='Apply tags to images', icon='fa.play', shortcut='Ctrl+R'
        )
        self.addSeparator()
        self.open_button = self.add_button(
            '&Open', tooltip='Open images', icon='ri.image-add-fill', shortcut='Ctrl+O'
        )
        self.paste_button = self.add_button(
            '&Paste',
            tooltip='Paste photos or iNaturalist URLs',
            icon='fa5s.paste',
            shortcut='Ctrl+V',
        )
        self.clear_button = self.add_button(
            '&Clear', tooltip='Clear open images', icon='fa.remove', shortcut='Ctrl+Shift+X'
        )
        self.refresh_button = self.add_button(
            '&Refresh',
            tooltip='Refresh previously tagged images with latest observation/taxon data',
            icon='fa.refresh',
            shortcut='F5',
        )

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.addWidget(spacer)
        self.fullscreen_button = self.add_button(
            '&Fullscreen',
            tooltip='Toggle fullscreen mode',
            icon='mdi.fullscreen',
            shortcut=Qt.Key_F11,
        )

        # Extra actions not added to the toolbar, but used by the menu
        self.settings_button = self.add_button(
            '&Settings',
            tooltip='Settings',
            icon='fa.gear',
            shortcut='Ctrl+Shift+S',
            visible=False,
        )
        self.exit_button = self.add_button(
            '&Exit',
            tooltip='Exit to desktop',
            icon='mdi.exit-run',
            shortcut='Ctrl+Q',
            visible=False,
        )
        self.docs_button = self.add_button(
            '&Docs',
            tooltip='Open documentation',
            icon='fa.question-circle',
            shortcut='F1',
            visible=False,
        )
        self.about_button = self.add_button(
            '&About',
            tooltip='Application information',
            icon='fa.info-circle',
            shortcut='Ctrl+F1',
            visible=False,
        )

    def add_button(
        self,
        name: str,
        tooltip: str,
        icon: str,
        shortcut: str = None,
        visible: bool = True,
    ) -> QAction:
        action = QAction(fa_icon(icon), name, self)
        if tooltip:
            action.setStatusTip(tooltip)
        if shortcut:
            action.setShortcut(QKeySequence(shortcut))
        if visible:
            self.addAction(action)
        return action

    def _placeholder(self, s):
        logger.info(f'Click; checked: {s}')

    def populate_menu(self, menu: QMenu):
        """Populate the application menu using actions defined on the toolbar"""
        file_menu = menu.addMenu('&File')
        file_menu.addAction(self.run_button)
        file_menu.addAction(self.open_button)

        self.recent_dirs_submenu.setIcon(fa_icon('fa.history'))
        file_menu.addMenu(self.recent_dirs_submenu)

        file_menu.addAction(self.paste_button)
        file_menu.addAction(self.clear_button)
        file_menu.addAction(self.refresh_button)
        file_menu.addAction(self.exit_button)

        view_menu = menu.addMenu('&View')
        view_menu.addAction(self.fullscreen_button)

        settings_menu = menu.addMenu('&Settings')
        settings_menu.addAction(self.settings_button)

        help_menu = menu.addMenu('&Help')
        help_menu.addAction(self.docs_button)
        help_menu.addAction(self.about_button)

    def add_recent_image_dir(self, image_dir: Path) -> Optional[QAction]:
        """Populate the recent image directories menu"""
        if image_dir in self.recent_dirs:
            return None

        self.recent_dirs.append(image_dir)
        action = self.recent_dirs_submenu.addAction(
            fa_icon('fa5s.folder-open'),
            str(image_dir).replace(HOME_DIR, '~'),
        )
        action.setStatusTip(f'Open images from {image_dir}')
        return action
