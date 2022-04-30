import sys
from logging import basicConfig, getLogger

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QDropEvent, QKeySequence, QShortcut
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPlainTextEdit,
    QPushButton,
    QStackedLayout,
    QStatusBar,
    QTextEdit,
    QToolTip,
    QVBoxLayout,
    QWidget,
)
from qt_material import apply_stylesheet

from naturtag.constants import APP_ICONS_DIR
from naturtag.qt_app.images import ImageViewer
from naturtag.qt_app.toolbar import Toolbar
from naturtag.tagger import tag_images

logger = getLogger(__name__)
basicConfig(level='DEBUG')


class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.resize(1000, 700)
        self.setWindowTitle('QT Image Viewer Demo')

        # Layout
        page_layout = QVBoxLayout()
        widget = QWidget()
        widget.setLayout(page_layout)
        self.setCentralWidget(widget)
        input_layout = QHBoxLayout()
        page_layout.addLayout(input_layout)
        self.viewer = ImageViewer()
        page_layout.addWidget(self.viewer)

        # Toolbar + status bar
        self.toolbar = Toolbar(
            'My main toolbar',
            load_file_callback=self.viewer.load_file_dialog,
            run_callback=self.run,
            clear_callback=self.clear,
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
        file_submenu = file_menu.addMenu('Submenu')
        file_submenu.addAction(self.toolbar.paste_button)
        file_submenu.addAction(self.toolbar.history_button)

        settings_menu = menu.addMenu('&Settings')
        settings_menu.addAction(self.toolbar.settings_button)

        # Keyboard shortcuts
        shortcut = QShortcut(QKeySequence('Ctrl+O'), self)
        shortcut.activated.connect(self.viewer.load_file_dialog)
        shortcut2 = QShortcut(QKeySequence('Ctrl+Q'), self)
        shortcut2.activated.connect(QApplication.instance().quit)

        # Input
        self.input_obs_id = QLineEdit()
        self.input_taxon_id = QLineEdit()
        input_layout.addWidget(QLabel('Observation ID:'))
        input_layout.addWidget(self.input_obs_id)
        input_layout.addWidget(QLabel('Taxon ID:'))
        input_layout.addWidget(self.input_taxon_id)

        # Load test images
        for file_path in [
            'amphibia.png',
            'animalia.png',
            'arachnida.png',
            'aves.png',
            'fungi.png',
            'insecta.png',
        ]:
            self.viewer.load_file(APP_ICONS_DIR / file_path)

    def run(self, *args):
        """Run image tagging for selected images and input"""
        obs_id, taxon_id = self.input_obs_id.text(), self.input_taxon_id.text()
        files = list(self.viewer.images.keys())

        if not files:
            self.statusbar.showMessage('Select images to tag')
            return
        if not (obs_id or taxon_id):
            self.statusbar.showMessage('Select either an observation or an organism to tag images with')
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
        self.statusbar.showMessage(f'{len(files)} images tagged with metadata for {selected_id}')

        # Update image previews with new metadata
        # previews = {img.metadata.image_path: img for img in self.image_previews.children}
        # for metadata in all_metadata:
        #     previews[metadata.image_path].metadata = metadata

    def clear(self):
        """Clear all images and input"""
        self.viewer.clear()
        self.input_obs_id.setText('')
        self.input_taxon_id.setText('')


if __name__ == '__main__':
    app = QApplication(sys.argv)
    apply_stylesheet(app, theme='dark_lightgreen.xml')
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
