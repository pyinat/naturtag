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
    QInputDialog,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QSplashScreen,
    QStatusBar,
    QTabWidget,
    QWidget,
)

from naturtag.app.controls import Toolbar, UserDirs
from naturtag.app.settings_menu import SettingsMenu
from naturtag.app.threadpool import ThreadPool
from naturtag.constants import APP_ICON, APP_LOGO, ASSETS_DIR, DOCS_URL, REPO_URL
from naturtag.controllers import ImageController, ObservationController, TaxonController
from naturtag.storage import ImageSession, Settings, iNatDbClient, setup
from naturtag.widgets import VerticalLayout, fa_icon, init_handler, set_theme

# Provide an application group so Windows doesn't use the default 'python' icon
try:
    from ctypes import windll  # type: ignore

    windll.shell32.SetCurrentProcessExplicitAppUserModelID('pyinat.naturtag.app.1.0')
except ImportError:
    pass

logger = getLogger(__name__)


class NaturtagApp(QApplication):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setApplicationName('Naturtag')
        self.setApplicationVersion(pkg_version('naturtag'))
        self.setOrganizationName('pyinat')
        self.setWindowIcon(QIcon(QPixmap(str(APP_ICON))))

    def post_init(self):
        self.settings = Settings.read()
        self.log_handler = init_handler(
            self.settings.log_level,
            root_level=self.settings.log_level_external,
            logfile=self.settings.logfile,
        )

        # Run initial/post-update setup steps, if needed
        self.state = setup(self.settings.db_path)

        # Globally available application objects
        self.client = iNatDbClient(self.settings.db_path)
        self.img_session = ImageSession(self.settings.image_cache_path)
        self.threadpool = ThreadPool(n_worker_threads=self.settings.n_worker_threads)
        self.user_dirs = UserDirs(self.settings)


class MainWindow(QMainWindow):
    def __init__(self, app: NaturtagApp):
        super().__init__()
        self.setWindowTitle('Naturtag')
        self.resize(*app.state.window_size)
        self.app = app

        # Controllers
        self.settings_menu = SettingsMenu()
        self.image_controller = ImageController()
        self.taxon_controller = TaxonController()
        self.observation_controller = ObservationController()

        # Connect controllers and their widgets to statusbar info
        self.settings_menu.on_message.connect(self.info)
        self.image_controller.on_message.connect(self.info)
        self.image_controller.gallery.on_message.connect(self.info)
        self.taxon_controller.on_message.connect(self.info)
        self.observation_controller.on_message.connect(self.info)

        # Settings that take effect immediately
        self.settings_menu.all_ranks.on_click.connect(self.taxon_controller.search.reset_ranks)
        self.settings_menu.dark_mode.on_click.connect(set_theme)
        self.settings_menu.show_logs.on_click.connect(self.toggle_log_tab)

        # Tabs
        self.tabs = QTabWidget()
        self.tabs.setIconSize(QSize(32, 32))
        idx = self.tabs.addTab(self.image_controller, fa_icon('fa.camera'), 'Photos')
        self.tabs.setTabToolTip(idx, 'Add and tag local photos')
        idx = self.tabs.addTab(self.taxon_controller, fa_icon('fa5s.spider'), 'Species')
        self.tabs.setTabToolTip(idx, 'Browse and search taxonomy')
        idx = self.tabs.addTab(
            self.observation_controller, fa_icon('fa5s.binoculars'), 'Observations'
        )
        self.tabs.setTabToolTip(idx, 'Browse your recent observations')

        # Root layout: tabs + progress bar
        self.root_widget = QWidget()
        self.root = VerticalLayout(self.root_widget)
        self.root.addWidget(self.tabs)
        self.root.addWidget(self.app.threadpool.progress)
        self.setCentralWidget(self.root_widget)

        # Optionally show Logs tab
        self.log_tab_idx = self.tabs.addTab(
            self.app.log_handler.widget, fa_icon('fa.file-text-o'), 'Logs'
        )
        self.tabs.setTabVisible(self.log_tab_idx, self.app.settings.show_logs)
        self.tabs.setTabToolTip(self.log_tab_idx, 'View application logs')

        # Photos tab: view taxon and switch tab
        self.image_controller.gallery.on_view_taxon_id.connect(
            self.taxon_controller.display_taxon_by_id
        )
        self.image_controller.gallery.on_view_taxon_id.connect(self.switch_tab_taxa)
        self.image_controller.on_view_taxon_id.connect(self.taxon_controller.display_taxon_by_id)
        self.image_controller.on_view_taxon_id.connect(self.switch_tab_taxa)

        # Photos tab: view observation and switch tab
        self.image_controller.gallery.on_view_observation_id.connect(
            self.observation_controller.display_observation_by_id
        )
        self.image_controller.gallery.on_view_observation_id.connect(self.switch_tab_observations)
        self.image_controller.on_view_observation_id.connect(
            self.observation_controller.display_observation_by_id
        )
        self.image_controller.on_view_observation_id.connect(self.switch_tab_observations)

        # Species tab: View observation and switch tab
        # self.taxon_controller.taxon_info.on_view_observations.connect(
        #     lambda obs: self.observation_controller.display_observation(obs, notify=False)
        # )
        # self.taxon_controller.taxon_info.on_view_observations.connect(self.switch_tab_observations)

        # Species tab: Select taxon for tagging and switch to Photos tab
        self.taxon_controller.taxon_info.on_select.connect(self.image_controller.select_taxon)
        self.taxon_controller.taxon_info.on_select.connect(
            lambda: self.tabs.setCurrentWidget(self.image_controller)
        )

        # Observations tab: View taxon and switch tab
        self.observation_controller.obs_info.on_view_taxon.connect(
            lambda taxon: self.taxon_controller.display_taxon(taxon, notify=False)
        )
        self.observation_controller.obs_info.on_view_taxon.connect(self.switch_tab_taxa)

        # Observations tab: Select observation for tagging and switch to Photos tab
        self.observation_controller.obs_info.on_select.connect(
            self.image_controller.select_observation
        )
        self.observation_controller.obs_info.on_select.connect(
            lambda: self.tabs.setCurrentWidget(self.image_controller)
        )

        # Connect file picker <--> recent/favorite dirs
        self.image_controller.gallery.on_load_images.connect(self.app.user_dirs.add_recent_dirs)
        self.app.user_dirs.on_dir_open.connect(self.image_controller.gallery.load_file_dialog)

        # Toolbar actions
        self.toolbar = Toolbar(self, self.app.user_dirs)
        self.toolbar.run_button.triggered.connect(self.image_controller.run)
        self.toolbar.refresh_tags_button.triggered.connect(self.image_controller.refresh)
        self.toolbar.open_button.triggered.connect(self.image_controller.gallery.load_file_dialog)
        self.toolbar.paste_button.triggered.connect(self.image_controller.paste)
        self.toolbar.clear_button.triggered.connect(self.image_controller.clear)
        self.toolbar.refresh_obs_button.triggered.connect(self.observation_controller.refresh)
        self.toolbar.fullscreen_button.triggered.connect(self.toggle_fullscreen)
        self.toolbar.reset_db_button.triggered.connect(self.reset_db)
        self.toolbar.settings_button.triggered.connect(self.show_settings)
        self.toolbar.exit_button.triggered.connect(QApplication.instance().quit)
        self.toolbar.docs_button.triggered.connect(self.open_docs)
        self.toolbar.about_button.triggered.connect(self.open_about)

        # Menu bar and status bar
        self.toolbar.populate_menu(self.menuBar())
        self.addToolBar(self.toolbar)
        self.statusbar = QStatusBar(self)
        self.setStatusBar(self.statusbar)
        # self.status_widget = QLabel('This is a status widget')
        # self.statusbar.addWidget(self.status_widget)
        # self.status_widget.setAttribute(Qt.WA_TransparentForMouseEvents)

        # Load any valid image paths provided on command line (or from drag & drop)
        self.image_controller.gallery.load_images(
            [a for a in sys.argv if not (a == __file__ or a.endswith('.exe'))]
        )

        # Debug
        if self.app.settings.debug:
            QShortcut(QKeySequence('F9'), self).activated.connect(self.reload_qss)
            demo_images = list((ASSETS_DIR / 'demo_images').glob('*.jpg'))
            self.image_controller.gallery.load_images(demo_images)  # type: ignore
            self.observation_controller.display_observation_by_id(56830941)

    def check_username(self):
        """If username isn't saved, show popup dialog to prompt user to enter it"""
        if self.app.settings.username:
            return

        username, ok = QInputDialog.getText(
            self,
            'iNaturalist username',
            'Enter your iNaturalist username to fetch your observations',
        )
        if ok:
            self.app.settings.username = username
            self.app.settings.write()
            self.observation_controller.load_user_observations()

    def closeEvent(self, _):
        """Save settings before closing the app"""
        self.app.settings.write()
        self.app.state.write()

    def info(self, message: str, timeout: int = 3000):
        """Show a message both in the status bar and in the logs"""
        self.statusbar.showMessage(message, timeout)
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
        data_dir = self.app.settings.data_dir
        app_dir_link = f"<a href='file://{data_dir}'>{data_dir}</a>"

        about.setText(
            f'<b>Naturtag v{version}</b><br/>'
            f'{attribution}'
            f'<br/>Source: {repo_link}'
            f'<br/>User data directory: {app_dir_link}'
        )
        about.exec()

    def reload_qss(self):
        """Reload Qt stylesheet"""
        set_theme(dark_mode=self.app.settings.dark_mode)

    # TODO: progress spinner
    def reset_db(self):
        """Reset the database"""
        response = QMessageBox.question(
            self,
            'Reset database?',
            'This will delete all observation and taxonomy data saved in the local database. Continue?',
        )
        if response == QMessageBox.Yes:
            self.info('Resetting database...')
            setup(self.app.settings, overwrite=True)
            self.info('Database reset complete')

    def show_settings(self):
        """Show the settings menu"""
        self.settings_menu.show()

    def switch_tab_observations(self):
        self.tabs.setCurrentWidget(self.observation_controller)

    def switch_tab_taxa(self):
        self.tabs.setCurrentWidget(self.taxon_controller)

    def switch_tab_photos(self):
        self.tabs.setCurrentWidget(self.image_controller)

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
    app = NaturtagApp(sys.argv)
    splash = QSplashScreen(QPixmap(str(APP_LOGO)).scaledToHeight(512))
    splash.show()
    app.post_init()

    set_theme(dark_mode=app.settings.dark_mode)
    window = MainWindow(app)
    window.show()
    splash.finish(window)
    window.check_username()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
