import sys
from logging import getLogger

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QLineEdit, QMainWindow, QStatusBar, QTabWidget, QWidget
from qtawesome import icon as fa_icon
from qtmodern import styles
from qtmodern.windows import ModernWindow

from naturtag.constants import ASSETS_DIR
from naturtag.qt_app.image_controller import ImageController
from naturtag.qt_app.logger import init_handler
from naturtag.qt_app.settings_menu import SettingsMenu
from naturtag.qt_app.toolbar import Toolbar
from naturtag.settings import Settings

logger = getLogger(__name__)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.resize(1024, 1024)
        self.setWindowTitle('Naturtag')

        # Controllers & Settings
        self.settings = Settings.read()
        self.image_controller = ImageController(self.settings, self.info)

        # Tabbed layout
        self.tabs = QTabWidget()
        self.tabs.addTab(self.image_controller, fa_icon('fa.camera'), 'Photos')
        self.tabs.addTab(QWidget(), fa_icon('fa.binoculars'), 'Observation')
        self.tabs.addTab(QWidget(), fa_icon('fa5s.spider'), 'Taxon')
        self.log_tab_idx = self.tabs.addTab(init_handler().widget, fa_icon('fa.file-text-o'), 'Logs')
        self.tabs.setTabVisible(self.log_tab_idx, self.settings.show_logs)
        self.setCentralWidget(self.tabs)

        # Toolbar
        self.toolbar = Toolbar(
            self,
            load_file_callback=self.image_controller.gallery.load_file_dialog,
            run_callback=self.image_controller.run,
            clear_callback=self.image_controller.clear,
            paste_callback=self.image_controller.paste,
            fullscreen_callback=self.toggle_fullscreen,
            log_callback=self.toggle_log_tab,
            settings_callback=self.show_settings,
        )

        # Menu bar and status bar
        self.toolbar.populate_menu(self.menuBar(), self.settings)
        self.addToolBar(self.toolbar)
        self.statusbar = QStatusBar(self)
        self.setStatusBar(self.statusbar)

        # Load demo images
        self.image_controller.gallery.load_images((ASSETS_DIR / 'demo_images').glob('*.jpg'))

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

    def show_settings(self):
        self.settings_menu = SettingsMenu(self.settings)
        self.settings_menu.show()

    def toggle_fullscreen(self) -> bool:
        """Toggle fullscreen, and change icon for toolbar fullscreen button"""
        if not self.isFullScreen():
            self._flags = self.windowFlags()
            self.setWindowFlags(Qt.WindowCloseButtonHint | Qt.WindowType_Mask)
            self.showFullScreen()
            self.toolbar.fullscreen_button.setIcon(fa_icon('mdi.fullscreen-exit'))
        else:
            self.setWindowFlags(self._flags)
            self.showNormal()
            self.toolbar.fullscreen_button.setIcon(fa_icon('mdi.fullscreen'))
        return self.isFullScreen()

    def toggle_log_tab(self):
        tab_visible = not self.tabs.isTabVisible(self.log_tab_idx)
        self.tabs.setTabVisible(self.log_tab_idx, tab_visible)
        self.settings.show_logs = tab_visible
        self.settings.write()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    styles.dark(app)
    # styles.light(app)
    window = ModernWindow(MainWindow())
    window.show()
    sys.exit(app.exec())
