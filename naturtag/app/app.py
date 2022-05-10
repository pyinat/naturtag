import sys
from logging import getLogger

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QLineEdit, QMainWindow, QPushButton, QStatusBar, QTabWidget
from qtmodern.windows import ModernWindow

from naturtag.app.image_controller import ImageController
from naturtag.app.logger import init_handler
from naturtag.app.settings_menu import SettingsMenu
from naturtag.app.style import fa_icon, set_stylesheet, set_theme
from naturtag.app.taxon_controller import TaxonController
from naturtag.app.toolbar import Toolbar
from naturtag.constants import ASSETS_DIR
from naturtag.settings import Settings

logger = getLogger(__name__)


class MainWindow(QMainWindow):
    def __init__(self, settings: Settings):
        super().__init__()
        self.resize(1024, 1024)
        self.setWindowTitle('Naturtag')
        log_handler = init_handler()

        # Controllers & Settings
        self.settings = settings
        self.image_controller = ImageController(self.settings, self.info)
        self.taxon_controller = TaxonController(self.settings, self.info)

        # Tabbed layout
        self.tabs = QTabWidget()
        self.tabs.addTab(self.image_controller, fa_icon('fa.camera'), 'Photos')
        # self.tabs.addTab(QWidget(), fa_icon('fa.binoculars'), 'Observations')
        self.tabs.addTab(self.taxon_controller, fa_icon('fa5s.spider'), 'Species')
        self.log_tab_idx = self.tabs.addTab(log_handler.widget, fa_icon('fa.file-text-o'), 'Logs')
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

        # Debug
        button = QPushButton('Reload QSS')
        button.clicked.connect(self.reload_qss)
        self.taxon_controller.input_layout.addWidget(button)

        # Load demo images
        demo_images = (ASSETS_DIR / 'demo_images').glob('*.jpg')
        self.image_controller.gallery.load_images(demo_images)  # type: ignore

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

    def reload_qss(self):
        set_stylesheet(self)


def main():
    app = QApplication(sys.argv)
    settings = Settings.read()
    set_theme(dark_mode=settings.dark_mode)

    window = ModernWindow(MainWindow(settings))
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
