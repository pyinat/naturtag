"""Main Qt app window and entry point"""
import sys
import webbrowser
from datetime import datetime
from importlib.metadata import version as pkg_version
from logging import getLogger

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon, QKeySequence, QPixmap, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QSplashScreen,
    QStatusBar,
    QTabWidget,
    QWidget,
)
from qtmodern.windows import ModernWindow

from naturtag.app.controls import Toolbar, UserDirs
from naturtag.app.settings_menu import SettingsMenu
from naturtag.app.style import fa_icon, set_stylesheet, set_theme
from naturtag.app.threadpool import ThreadPool
from naturtag.constants import APP_DIR, APP_ICON, APP_LOGO, ASSETS_DIR, DOCS_URL, REPO_URL
from naturtag.controllers import ImageController, ObservationController, TaxonController
from naturtag.settings import Settings, setup
from naturtag.widgets import VerticalLayout, init_handler

# Provide an application group so Windows doesn't use the default 'python' icon
try:
    from ctypes import windll  # type: ignore

    windll.shell32.SetCurrentProcessExplicitAppUserModelID('pyinat.naturtag.app.1.0')
except ImportError:
    pass

logger = getLogger(__name__)


# TODO: Global access to Settings object instead of passing it around everywhere?
class MainWindow(QMainWindow):
    def __init__(self, settings: Settings):
        super().__init__()
        self.setWindowTitle('Naturtag')
        self.resize(*settings.window_size)
        self.threadpool = ThreadPool()
        log_handler = init_handler(
            settings.log_level, root_level=settings.log_level_external, logfile=settings.logfile
        )

        # Run any first-time setup steps, if needed
        self.settings = settings
        self.user_dirs = UserDirs(settings)
        setup(settings)

        # Controllers
        self.settings_menu = SettingsMenu(self.settings)
        self.image_controller = ImageController(self.settings, self.threadpool)
        self.taxon_controller = TaxonController(self.settings, self.threadpool)
        self.observation_controller = ObservationController(self.settings, self.threadpool)

        # Connect controllers and their widgets to statusbar info
        self.settings_menu.on_message.connect(self.info)
        self.image_controller.on_message.connect(self.info)
        self.image_controller.gallery.on_message.connect(self.info)
        self.taxon_controller.on_message.connect(self.info)
        self.observation_controller.on_message.connect(self.info)

        # Select observation/taxon from image context menu, ID input fields, and iconic taxa filters
        self.image_controller.gallery.on_select_taxon.connect(self.taxon_controller.select_taxon)
        self.image_controller.gallery.on_select_observation.connect(
            self.observation_controller.select_observation
        )
        self.image_controller.on_select_observation_id.connect(
            self.observation_controller.select_observation
        )
        self.image_controller.on_select_taxon_id.connect(self.taxon_controller.select_taxon)
        self.taxon_controller.search.iconic_taxon_filters.on_select.connect(
            self.taxon_controller.select_taxon
        )

        # Update photo tab when a taxon is selected
        self.taxon_controller.on_select.connect(self.image_controller.select_taxon)

        # Update photo and taxon tabs when an observation is selected
        self.observation_controller.on_select.connect(self.image_controller.select_observation)
        self.observation_controller.on_select.connect(
            lambda obs: self.taxon_controller.display_taxon(obs.taxon, notify=False)
        )

        # Settings that take effect immediately
        self.settings_menu.all_ranks.on_click.connect(self.taxon_controller.search.reset_ranks)
        self.settings_menu.dark_mode.on_click.connect(set_theme)
        self.settings_menu.show_logs.on_click.connect(self.toggle_log_tab)

        # Tabs
        self.tabs = QTabWidget()
        self.tabs.setIconSize(QSize(32, 32))
        self.tabs.addTab(self.image_controller, fa_icon('fa.camera'), 'Photos')
        self.tabs.addTab(self.taxon_controller, fa_icon('fa5s.spider'), 'Species')
        self.tabs.addTab(self.observation_controller, fa_icon('fa5s.binoculars'), 'Observation')

        # Root layout: tabs + progress bar
        self.root_widget = QWidget()
        self.root = VerticalLayout(self.root_widget)
        self.root.addWidget(self.tabs)
        self.root.addWidget(self.threadpool.progress)
        self.setCentralWidget(self.root_widget)

        # Optionally show Logs tab
        self.log_tab_idx = self.tabs.addTab(log_handler.widget, fa_icon('fa.file-text-o'), 'Logs')
        self.tabs.setTabVisible(self.log_tab_idx, self.settings.show_logs)

        # Switch to differet tab if requested from Photos tab
        self.image_controller.on_select_taxon_tab.connect(
            lambda: self.tabs.setCurrentWidget(self.taxon_controller)
        )
        self.image_controller.on_select_observation_tab.connect(
            lambda: self.tabs.setCurrentWidget(self.observation_controller)
        )

        # Connect file picker <--> recent/favorite dirs
        self.image_controller.gallery.on_load_images.connect(self.user_dirs.add_recent_dirs)
        self.user_dirs.on_dir_open.connect(self.image_controller.gallery.load_file_dialog)

        # Toolbar actions
        self.toolbar = Toolbar(self, self.user_dirs)
        self.toolbar.run_button.triggered.connect(self.image_controller.run)
        self.toolbar.open_button.triggered.connect(self.image_controller.gallery.load_file_dialog)
        self.toolbar.paste_button.triggered.connect(self.image_controller.paste)
        self.toolbar.clear_button.triggered.connect(self.image_controller.clear)
        self.toolbar.refresh_button.triggered.connect(self.image_controller.refresh)
        self.toolbar.fullscreen_button.triggered.connect(self.toggle_fullscreen)
        self.toolbar.settings_button.triggered.connect(self.show_settings)
        self.toolbar.exit_button.triggered.connect(QApplication.instance().quit)
        self.toolbar.docs_button.triggered.connect(self.open_docs)
        self.toolbar.about_button.triggered.connect(self.open_about)

        # Menu bar and status bar
        self.toolbar.populate_menu(self.menuBar())
        self.addToolBar(self.toolbar)
        self.statusbar = QStatusBar(self)
        self.setStatusBar(self.statusbar)

        # Load any valid image paths provided on command line (or from drag & drop)
        self.image_controller.gallery.load_images(
            [a for a in sys.argv if not (a == __file__ or a.endswith('.exe'))]
        )

        # Debug
        if settings.debug:
            QShortcut(QKeySequence('F9'), self).activated.connect(self.reload_qss)
            demo_images = list((ASSETS_DIR / 'demo_images').glob('*.jpg'))
            self.image_controller.gallery.load_images(demo_images)  # type: ignore
            self.observation_controller.select_observation(56830941)

    def closeEvent(self, _):
        """Save settings before closing the app"""
        self.settings.write()
        self.taxon_controller.user_taxa.write()

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

    def open_docs(self):
        """Open the documentation in a web browser"""
        webbrowser.open(DOCS_URL)

    def open_about(self):
        """Show an About dialog with basic app information"""
        about = QMessageBox()
        about.setIconPixmap(QPixmap(str(APP_ICON)))
        about.setTextFormat(Qt.RichText)

        version = pkg_version('naturtag')
        repo_link = f"<a href='{REPO_URL}'>{REPO_URL}</a>"
        license_link = f"<a href='{REPO_URL}/LICENSE'>MIT License</a>"
        attribution = f'Ⓒ {datetime.now().year} Jordan Cook, {license_link}'
        app_dir_link = f"<a href='{APP_DIR}'>{APP_DIR}</a>"

        about.setText(
            f'<b>Naturtag v{version}</b><br/>'
            f'{attribution}'
            f'<br/>Source: {repo_link}'
            f'<br/>User data directory: {app_dir_link}'
        )
        about.exec()

    def reload_qss(self):
        """Reload Qt stylesheet"""
        set_stylesheet(self)

    def show_settings(self):
        """Show the settings menu"""
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

    def toggle_log_tab(self, checked: bool = True):
        self.tabs.setTabVisible(self.log_tab_idx, checked)


def main():
    app = QApplication(sys.argv)
    splash = QSplashScreen(QPixmap(str(APP_LOGO)).scaledToHeight(512))
    splash.show()
    settings = Settings.read()

    app.setWindowIcon(QIcon(QPixmap(str(APP_ICON))))
    set_theme(dark_mode=settings.dark_mode)
    window = ModernWindow(MainWindow(settings))
    window.show()
    splash.finish(window)
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
