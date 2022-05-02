import sys
from logging import getLogger

from PySide6.QtGui import QAction, QIntValidator, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QStatusBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
from qtawesome import icon as fa_icon
from qtmodern import styles
from qtmodern.windows import ModernWindow

from naturtag.constants import APP_ICONS_DIR
from naturtag.inat_metadata import get_ids_from_url
from naturtag.qt_app.images import ImageViewer
from naturtag.qt_app.logger import init_handler
from naturtag.qt_app.toolbar import Toolbar
from naturtag.tagger import tag_images

logger = getLogger(__name__)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.resize(1024, 768)
        self.setWindowTitle('QT Image Viewer Demo')

        # Tabbed layout
        tabs = QTabWidget()
        self.setCentralWidget(tabs)

        photo_layout = QVBoxLayout()
        photo_root = QWidget()
        photo_root.setLayout(photo_layout)
        tabs.addTab(photo_root, fa_icon('fa.camera'), 'Photos')
        tabs.addTab(QWidget(), fa_icon('fa.binoculars'), 'Observation')
        tabs.addTab(QWidget(), fa_icon('fa5s.spider'), 'Taxon')
        log_tab_idx = tabs.addTab(init_handler().widget, fa_icon('fa.file-text-o'), 'Logs')
        tabs.setTabVisible(log_tab_idx, False)

        # Input group
        input_layout = QHBoxLayout()
        groupBox = QGroupBox('Input')
        groupBox.setLayout(input_layout)
        photo_layout.addWidget(groupBox)

        # Viewer
        self.viewer = ImageViewer()
        photo_layout.addWidget(self.viewer)

        # Toolbar + status bar
        self.toolbar = Toolbar(
            'My main toolbar',
            load_file_callback=self.viewer.load_file_dialog,
            run_callback=self.run,
            clear_callback=self.clear,
            paste_callback=self.paste,
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
        shortcut = QShortcut(QKeySequence('Ctrl+O'), self)
        shortcut.activated.connect(self.viewer.load_file_dialog)
        shortcut2 = QShortcut(QKeySequence('Ctrl+Q'), self)
        shortcut2.activated.connect(QApplication.instance().quit)
        shortcut2 = QShortcut(QKeySequence('Ctrl+V'), self)
        shortcut2.activated.connect(self.paste)

        # Input fields
        self.input_obs_id = QLineEdit()
        self.input_obs_id.setClearButtonEnabled(True)
        self.input_obs_id.setValidator(QIntValidator())
        input_layout.addWidget(QLabel('Observation ID:'))
        input_layout.addWidget(self.input_obs_id)

        self.input_taxon_id = QLineEdit()
        self.input_taxon_id.setClearButtonEnabled(True)
        self.input_taxon_id.setValidator(QIntValidator())
        input_layout.addWidget(QLabel('Taxon ID:'))
        input_layout.addWidget(self.input_taxon_id)

        # Load test images
        filenames = [
            'amphibia.png',
            'animalia.png',
            'arachnida.png',
            'aves.png',
            'fungi.png',
            'insecta.png',
        ]
        self.viewer.load_images([APP_ICONS_DIR / filename for filename in filenames])

    def run(self):
        """Run image tagging for selected images and input"""
        obs_id, taxon_id = self.input_obs_id.text(), self.input_taxon_id.text()
        files = list(self.viewer.images.keys())

        if not files:
            self.info('Select images to tag')
            return
        if not (obs_id or taxon_id):
            self.info('Select either an observation or an organism to tag images with')
            return

        selected_id = f'Observation ID: {obs_id}' if obs_id else f'Taxon ID: {taxon_id}'
        logger.info(f'Tagging {len(files)} images with metadata for {selected_id}')

        # TODO: Handle write errors (like file locked) and show dialog
        # TODO: Application settings
        # metadata_settings = get_app().settings_controller.metadata
        all_metadata, _, _ = tag_images(
            obs_id,
            taxon_id,
            # metadata_settings['common_names'],
            # metadata_settings['darwin_core'],
            # metadata_settings['hierarchical_keywords'],
            # metadata_settings['create_xmp'],
            images=files,
        )
        self.info(f'{len(files)} images tagged with metadata for {selected_id}')

        # Update image previews with new metadata
        # previews = {img.metadata.image_path: img for img in self.image_previews.children}
        # for metadata in all_metadata:
        #     previews[metadata.image_path].metadata = metadata

    def clear(self):
        """Clear all images and input"""
        self.viewer.clear()
        self.input_obs_id.setText('')
        self.input_taxon_id.setText('')

    def info(self, message: str):
        """Show a message both in the status bar and in the logs"""
        self.statusbar.showMessage(message)
        logger.info(message)

    def paste(self):
        """Paste either image paths or taxon/observation URLs"""
        text = QApplication.clipboard().text()
        logger.debug(f'Pasted: {text}')

        taxon_id, observation_id = get_ids_from_url(text)
        if observation_id:
            self.input_obs_id.setText(str(observation_id))
            self.info(f'Observation {observation_id} selected')
        elif taxon_id:
            self.input_taxon_id.setText(str(taxon_id))
            self.info(f'Taxon {taxon_id} selected')
        else:
            self.viewer.load_images(text.splitlines())


if __name__ == '__main__':
    app = QApplication(sys.argv)
    styles.dark(app)
    # styles.light(app)
    window = ModernWindow(MainWindow())
    window.show()
    sys.exit(app.exec())
