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

TEST_IMAGES = [
    APP_ICONS_DIR / 'amphibia.png',
    APP_ICONS_DIR / 'animalia.png',
    APP_ICONS_DIR / 'arachnida.png',
    APP_ICONS_DIR / 'aves.png',
    APP_ICONS_DIR / 'fungi.png',
    APP_ICONS_DIR / 'insecta.png',
]

logger = getLogger(__name__)
basicConfig(level='DEBUG')


class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        # self.resize(1600, 1000)
        self.resize(1000, 700)
        self.setWindowTitle('QT Material Demo')
        self.setAcceptDrops(True)

        pagelayout = QVBoxLayout()
        # toolbar_layout = QHBoxLayout()

        label = QLabel('Hello!\nThis is a demo!')
        label.setAlignment(Qt.AlignCenter)
        pagelayout.addWidget(label)
        self.viewer = ImageViewer()
        pagelayout.addWidget(self.viewer)

        widget = QWidget()
        widget.setLayout(pagelayout)
        self.setCentralWidget(widget)

        # Toolbar
        self.toolbar = Toolbar('My main toolbar', self.viewer)
        self.addToolBar(self.toolbar)

        # Menu bar
        menu = self.menuBar()
        file_menu = menu.addMenu('&File')
        file_menu.addAction(self.toolbar.run_button)
        file_menu.addAction(self.toolbar.open_button)
        file_submenu = file_menu.addMenu('Submenu')
        file_submenu.addAction(self.toolbar.paste_button)
        file_submenu.addAction(self.toolbar.history_button)

        # Status bar
        self.setStatusBar(QStatusBar(self))

        # Keyboard shortcuts
        shortcut = QShortcut(QKeySequence('Ctrl+O'), self)
        shortcut.activated.connect(self.viewer.load_file_dialog)
        shortcut2 = QShortcut(QKeySequence('Ctrl+Q'), self)
        shortcut2.activated.connect(QApplication.instance().quit)

        # Load test images
        for file_path in TEST_IMAGES:
            self.viewer.load_file(file_path)

    def dragEnterEvent(self, event):
        event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        self.viewer.load_file(event.mimeData().text())
        event.acceptProposedAction()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    apply_stylesheet(app, theme='dark_lightgreen.xml')
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
