import sys
from logging import getLogger
from typing import Callable

from PySide6.QtGui import QAction, QKeySequence, QShortcut
from PySide6.QtWidgets import QApplication, QLineEdit, QMainWindow, QStatusBar, QTabWidget, QWidget
from qtawesome import icon as fa_icon
from qtmodern import styles
from qtmodern.windows import ModernWindow

from naturtag.constants import ASSETS_DIR
from naturtag.qt_app.logger import init_handler
from naturtag.qt_app.photo_controller import PhotoController
from naturtag.qt_app.toolbar import Toolbar
from naturtag.settings import Settings

DEMO_IMAGES = ASSETS_DIR / 'demo_images'
logger = getLogger(__name__)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.resize(1024, 1024)
        self.setWindowTitle('Naturtag')

        # Controllers & Settings
        self.settings = Settings.read()
        self.photo_controller = PhotoController(self.settings, self.info)

        # Tabbed layout
        tabs = QTabWidget()
        tabs.addTab(self.photo_controller, fa_icon('fa.camera'), 'Photos')
        tabs.addTab(QWidget(), fa_icon('fa.binoculars'), 'Observation')
        tabs.addTab(QWidget(), fa_icon('fa5s.spider'), 'Taxon')
        log_tab_idx = tabs.addTab(init_handler().widget, fa_icon('fa.file-text-o'), 'Logs')
        tabs.setTabVisible(log_tab_idx, False)
        self.setCentralWidget(tabs)

        # Toolbar + status bar
        self.toolbar = Toolbar(
            'My main toolbar',
            load_file_callback=self.photo_controller.viewer.load_file_dialog,
            run_callback=self.photo_controller.run,
            clear_callback=self.photo_controller.clear,
            paste_callback=self.photo_controller.paste,
        )
        self.addToolBar(self.toolbar)
        self.statusbar = QStatusBar(self)
        self.setStatusBar(self.statusbar)

        # Menu bar
        menu = self.menuBar()
        file_menu = menu.addMenu('&File')
        file_menu.addAction(self.toolbar.run_button)
        file_menu.addAction(self.toolbar.open_button)
        file_menu.addAction(self.toolbar.clear_button)
        settings_menu = menu.addMenu('&Settings')
        settings_menu.addAction(self.toolbar.settings_button)
        # file_submenu = file_menu.addMenu('Submenu')
        # file_submenu.addAction(self.toolbar.paste_button)
        # file_submenu.addAction(self.toolbar.history_button)

        def toggle_tab(idx):
            tabs.setTabVisible(idx, not tabs.isTabVisible(idx))

        # Button to enable log tab
        button_action = QAction(fa_icon('fa.file-text-o'), '&View Logs', self)
        button_action.setStatusTip('View Logs')
        button_action.setCheckable(True)
        button_action.triggered.connect(lambda: toggle_tab(log_tab_idx))
        settings_menu.addAction(button_action)

        # Keyboard shortcuts
        self._add_shortcut('Ctrl+O', self.photo_controller.viewer.load_file_dialog)
        self._add_shortcut('Ctrl+Q', QApplication.instance().quit)
        self._add_shortcut('Ctrl+R', self.photo_controller.run)
        self._add_shortcut('Ctrl+V', self.photo_controller.paste)
        self._add_shortcut('Ctrl+Shift+X', self.photo_controller.clear)

        # Load demo images
        self.photo_controller.viewer.load_images(sorted(DEMO_IMAGES.glob('*.jpg')))

    def _add_shortcut(self, keys: str, callback: Callable):
        shortcut = QShortcut(QKeySequence(keys), self)
        shortcut.activated.connect(callback)

    def info(self, message: str):
        """Show a message both in the status bar and in the logs"""
        self.statusbar.showMessage(message)
        logger.info(message)

    def mousePressEvent(self, event):
        """Deselect focus from text edit fields when clicking anywhere else on the window"""
        focused_widget = QApplication.focusWidget()
        if isinstance(focused_widget, QLineEdit):
            focused_widget.clearFocus()
        super().mousePressEvent(event)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    styles.dark(app)
    # styles.light(app)
    window = ModernWindow(MainWindow())
    window.show()
    sys.exit(app.exec())
