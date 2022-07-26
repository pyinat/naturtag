"""This module contains utilities for the main UI controls:

* Toolbar
* Menu bar
* Global keyboard shortcuts
"""
from functools import partial
from logging import getLogger
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject, QSize, Qt, Signal, Slot
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import QApplication, QFileDialog, QMenu, QSizePolicy, QToolBar, QWidget

from naturtag.app.style import fa_icon
from naturtag.settings import Settings

HOME_DIR = str(Path.home())
logger = getLogger(__name__)


class Toolbar(QToolBar):
    """Contains all actions used by toolbar and menu bar.
    Action signals are connected in `app.py`.
    """

    def __init__(self, parent: QWidget, user_dirs: 'UserDirs'):
        super(Toolbar, self).__init__(parent)
        self.setIconSize(QSize(24, 24))
        self.user_dirs = user_dirs

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

        # Add action to toggle toolbar visibility
        self.show_toolbar_button = self.toggleViewAction()
        self.show_toolbar_button.setText('Show &toolbar')
        self.show_toolbar_button.setShortcut('Ctrl+Shift+T')
        self.show_toolbar_button.setStatusTip('Show or hide the toolbar')

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

    # TODO: Merge into init?
    def populate_menu(self, menu: QMenu):
        """Populate the application menu using actions defined on the toolbar"""
        file_menu = menu.addMenu('&File')
        file_menu.addAction(self.run_button)
        file_menu.addAction(self.open_button)

        file_menu.addMenu(self.user_dirs.favorite_dirs_submenu)
        file_menu.addMenu(self.user_dirs.recent_dirs_submenu)

        file_menu.addAction(self.paste_button)
        file_menu.addAction(self.clear_button)
        file_menu.addAction(self.refresh_button)
        file_menu.addAction(self.exit_button)

        view_menu = menu.addMenu('&View')
        view_menu.addAction(self.fullscreen_button)
        view_menu.addAction(self.show_toolbar_button)

        settings_menu = menu.addMenu('&Settings')
        settings_menu.addAction(self.settings_button)

        help_menu = menu.addMenu('&Help')
        help_menu.addAction(self.docs_button)
        help_menu.addAction(self.about_button)


class UserDirs(QObject):
    """Manages Recent and Favorite image directories (settings + menus)"""

    on_dir_open = Signal(Path)  # Request to open file chooser at a specific directory

    def __init__(self, settings: Settings):
        super().__init__()
        self.favorite_dirs: dict[Path, QAction] = {}
        self.favorite_dirs_submenu = QMenu('Open Favorites')
        self.favorite_dirs_submenu.setIcon(fa_icon('fa.star'))

        self.recent_dirs: dict[Path, QAction] = {}
        self.recent_dirs_submenu = QMenu('Open Recent')
        self.recent_dirs_submenu.setIcon(fa_icon('mdi6.history'))

        # insertAction() requires a reference to another action to insert before
        self.last_opened_action = QAction()

        # Add action to top of favorites submenu to add a new favorite
        action = self.favorite_dirs_submenu.addAction(fa_icon('fa.star'), 'Add a favorite')
        action.triggered.connect(self.choose_favorite_dir)
        action.setStatusTip('Add a new image directory to Favorites')
        action.setShortcut(QKeySequence('Ctrl+Shift+F'))
        self.favorite_dirs_submenu.addSeparator()

        # Populate directory submenus from settings
        self.settings = settings
        for image_dir in settings.favorite_image_dirs:
            self.add_favorite_dir(image_dir, save=False)
        for image_dir in settings.recent_image_dirs[::-1]:
            self.add_recent_dir(image_dir, save=False)

    def add_favorite_dir(self, image_dir: Path, save: bool = True) -> Optional[QAction]:
        """Add an image directory to Favorites (if not already added)"""
        if image_dir in self.favorite_dirs:
            return None
        if save:
            self.settings.add_favorite_dir(image_dir)

        logger.debug(f'Adding favorite: {image_dir}')
        action = self.favorite_dirs_submenu.addAction(
            fa_icon('mdi.folder-star'),
            str(image_dir).replace(HOME_DIR, '~'),
        )
        action.triggered.connect(partial(self.open_or_remove_favorite_dir, image_dir))
        action.setStatusTip(f'Open images from {image_dir} (Ctrl-click to remove from favorites)')

        self.favorite_dirs[image_dir] = action
        return action

    def add_recent_dirs(self, paths: list[Path], save: bool = True):
        """Update recently used image directories in the menu and (optionally) settings

        Args:
            paths: Image or image directory paths
            save: Save directories to settings
        """
        unique_image_dirs = {p.parent if p.is_file() else p for p in paths}
        for image_dir in unique_image_dirs:
            self.add_recent_dir(image_dir, save=save)
        if save:
            self.settings.write()

    def add_recent_dir(self, image_dir: Path, save: bool = True) -> Optional[QAction]:
        """Add an image directory to Recent (if not already added)"""
        if save:
            self.settings.add_recent_dir(image_dir)

        # Move existing item to top of Recent submenu
        if image_dir in self.recent_dirs:
            self._move_to_top(image_dir)
            return None

        # Add new item to top of Recent submenu
        action = QAction(
            fa_icon('mdi6.folder-clock'),
            str(image_dir).replace(HOME_DIR, '~'),
        )
        if self.last_opened_action:
            self.recent_dirs_submenu.insertAction(self.last_opened_action, action)
        else:
            self.recent_dirs_submenu.addAction(action)
        action.setStatusTip(f'Open images from {image_dir} (Ctrl-click to add to favorites)')
        action.triggered.connect(partial(self.open_or_add_favorite_dir, image_dir))

        self.recent_dirs[image_dir] = action
        self.last_opened_action = action
        return action

    def choose_favorite_dir(self):
        """Open a file chooser to select a new favorite directory"""
        path = QFileDialog.getExistingDirectory(
            caption='Choose a directory to add:', dir=str(self.settings.start_image_dir)
        )
        if path:
            self.add_favorite_dir(Path(path))

    def _move_to_top(self, image_dir: Path):
        """Move an existing directory in history to the top of the submenu"""
        action = self.recent_dirs[image_dir]
        self.recent_dirs_submenu.removeAction(action)
        self.recent_dirs_submenu.insertAction(self.last_opened_action, action)
        self.last_opened_action = action

    def remove_favorite_dir(self, image_dir: Path):
        """Remove an image directory from Favorites menu"""
        logger.debug(f'Removing favorite: {image_dir}')
        self.settings.remove_favorite_dir(image_dir)
        self.settings.write()
        if action := self.favorite_dirs.pop(image_dir, None):
            self.favorite_dirs_submenu.removeAction(action)

    def remove_recent_dir(self, image_dir: Path):
        """Remove an image directory from Recent menu"""
        self.settings.remove_recent_dir(image_dir)
        if action := self.recent_dirs.pop(image_dir, None):
            self.recent_dirs_submenu.removeAction(action)

    @Slot(Path)
    def open_or_add_favorite_dir(self, image_dir: Path):
        """Open a directory from the 'Open Recent' submenu, or Ctrl-click to add it as a favorite"""
        if QApplication.keyboardModifiers() == Qt.ControlModifier:
            self.add_favorite_dir(image_dir)
            self.remove_recent_dir(image_dir)
        else:
            self.on_dir_open.emit(image_dir)

    @Slot(Path)
    def open_or_remove_favorite_dir(self, image_dir: Path):
        """Open a directory from the 'Open Favorites' submenu, or Ctrl-click to add it as a
        favorite"""
        if QApplication.keyboardModifiers() == Qt.ControlModifier:
            self.remove_favorite_dir(image_dir)
            self.add_recent_dir(image_dir)
        else:
            self.on_dir_open.emit(image_dir)
