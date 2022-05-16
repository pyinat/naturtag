"""Main Qt app window and entry point"""
import sys
from logging import getLogger

from PySide6.QtCore import Qt
from PySide6.QtGui import QCloseEvent, QKeySequence, QShortcut
from PySide6.QtWidgets import QApplication, QLineEdit, QMainWindow, QStatusBar, QTabWidget
from qtmodern.windows import ModernWindow

from naturtag.app.settings_menu import SettingsMenu
from naturtag.app.style import fa_icon, set_stylesheet, set_theme
from naturtag.app.threadpool import ThreadPool
from naturtag.app.toolbar import Toolbar
from naturtag.constants import ASSETS_DIR
from naturtag.controllers import ImageController, TaxonController
from naturtag.settings import Settings
from naturtag.widgets import init_handler

logger = getLogger(__name__)


# TODO: Global access to Settings object instead of passing it around everywhere?
# TODO: Rember last selected taxon
class MainWindow(QMainWindow):
    def __init__(self, settings: Settings):
        super().__init__()
        self.setWindowTitle('Naturtag')
        self.resize(*settings.window_size)
        self.threadpool = ThreadPool()
        log_handler = init_handler(
            settings.log_level, root_level=settings.log_level_external, logfile=settings.logfile
        )

        # Controllers & Settings
        self.settings = settings
        self.settings_menu = SettingsMenu(self.settings)
        self.image_controller = ImageController(self.settings)
        self.taxon_controller = TaxonController(self.settings, self.threadpool)

        # Connect controllers and their widgets to statusbar info
        self.settings_menu.message.connect(self.info)
        self.image_controller.message.connect(self.info)
        self.image_controller.gallery.message.connect(self.info)
        self.taxon_controller.message.connect(self.info)

        # Select taxon from image context menu
        self.image_controller.gallery.selected_taxon.connect(self.taxon_controller.select_taxon)
        # Select taxon from iconic taxa filters
        self.taxon_controller.search.iconic_taxa_filters.selected_taxon.connect(
            self.taxon_controller.select_taxon
        )
        # Update taxon ID on main page when a taxon is selected
        self.taxon_controller.selection.connect(self.image_controller.select_taxon)

        # Settings that take effect immediately
        self.settings_menu.dark_mode.clicked.connect(lambda checked: set_theme(dark_mode=checked))
        self.settings_menu.all_ranks.clicked.connect(self.taxon_controller.search.reset_ranks)

        # Tabbed layout
        self.tabs = QTabWidget()
        self.tabs.addTab(self.image_controller, fa_icon('fa.camera'), 'Photos')
        # self.tabs.addTab(QWidget(), fa_icon('fa.binoculars'), 'Observations')
        self.tabs.addTab(self.taxon_controller, fa_icon('fa5s.spider'), 'Species')
        self.setCentralWidget(self.tabs)

        # Optionally show Logs tab
        self.log_tab_idx = self.tabs.addTab(log_handler.widget, fa_icon('fa.file-text-o'), 'Logs')
        self.tabs.setTabVisible(self.log_tab_idx, self.settings.show_logs)

        # Switch to Taxon tab from image context menu -> View Taxon
        self.image_controller.gallery.selected_taxon.connect(
            lambda: self.tabs.setCurrentWidget(self.taxon_controller)
        )

        # Toolbar
        self.toolbar = Toolbar(self)
        self.toolbar.run_button.triggered.connect(self.image_controller.run)
        self.toolbar.open_button.triggered.connect(self.image_controller.gallery.load_file_dialog)
        self.toolbar.paste_button.triggered.connect(self.image_controller.paste)
        self.toolbar.clear_button.triggered.connect(self.image_controller.clear)
        self.toolbar.fullscreen_button.triggered.connect(self.toggle_fullscreen)
        self.toolbar.settings_button.triggered.connect(self.show_settings)
        self.toolbar.logs_button.triggered.connect(self.toggle_log_tab)
        self.toolbar.exit_button.triggered.connect(QApplication.instance().quit)

        # Menu bar and status bar
        self.toolbar.populate_menu(self.menuBar(), self.settings)
        self.addToolBar(self.toolbar)
        self.statusbar = QStatusBar(self)
        self.setStatusBar(self.statusbar)

        # Debug
        shortcut = QShortcut(QKeySequence('F5'), self)
        shortcut.activated.connect(self.reload_qss)

        # Load demo images
        demo_images = (ASSETS_DIR / 'demo_images').glob('*.jpg')
        self.image_controller.gallery.load_images(demo_images)  # type: ignore

    def closeEvent(self, event: QCloseEvent):
        self.settings.window_size = self.size().toTuple()
        self.settings.write()

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
