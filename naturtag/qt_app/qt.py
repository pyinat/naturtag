import sys
from logging import basicConfig, getLogger
from os.path import isfile
from typing import Callable
from urllib.parse import unquote, urlparse

from PySide6.QtCore import QRectF, QSize, Qt, Signal
from PySide6.QtGui import QAction, QDropEvent, QIcon, QImage, QKeySequence, QPixmap, QShortcut
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QFrame,
    QGraphicsGridLayout,
    QGraphicsLinearLayout,
    QGraphicsPixmapItem,
    QGraphicsScene,
    QGraphicsView,
    QGraphicsWidget,
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
    QToolBar,
    QToolTip,
    QVBoxLayout,
    QWidget,
)
from qt_material import apply_stylesheet

from naturtag.constants import APP_ICONS_DIR, ASSETS_DIR, IMAGE_FILETYPES
from naturtag.models import MetaMetadata
from naturtag.thumbnails import get_thumbnail

ICONS_DIR = ASSETS_DIR / 'material_icons'
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


class QtImageViewer(QGraphicsView):
    file_changed = Signal(str)

    def __init__(self):
        super().__init__()

        self.setAcceptDrops(True)
        self.scene = QGraphicsScene()
        self.setScene(self.scene)
        self.layout = QGraphicsGridLayout()
        self.img_row = 0
        self.img_col = 0
        self.images = {}

        self.aspectRatioMode = Qt.KeepAspectRatio
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        form = QGraphicsWidget()
        form.setLayout(self.layout)
        self.scene.addItem(form)

    def load_file_dialog(self):
        file_names, _ = QFileDialog.getOpenFileNames(
            self,
            'Open image files:',
            filter=f'Image files ({" ".join(IMAGE_FILETYPES)})',
        )
        for file_name in file_names:
            self.load_file(file_name)

    def load_file(self, file_path: str):
        '''Load an image from a file path or URI'''
        # TODO: Support Windows file URIs
        file_path = unquote(urlparse(str(file_path)).path)
        if not isfile(file_path):
            logger.info(f'File does not exist: {file_path}')
            return
        elif file_path in self.images:
            logger.info(f'Image already loaded: {file_path}')
            return

        logger.info(f'Loading {file_path} at ({self.img_row}, {self.img_col})')
        thumbnail = self.scene.addWidget(LocalThumbnail(file_path))
        self.layout.addItem(thumbnail, self.img_row, self.img_col)
        self.images[file_path] = thumbnail

        # I need to manually manage a grid layout? Oh joy
        self.img_col += 1
        if self.img_col == 4:
            self.img_col = 0
            self.img_row += 1

    def dragEnterEvent(self, event):
        event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        event.acceptProposedAction()
        self.load_file(event.mimeData().text())


class LocalThumbnail(QLabel):
    """Displays a thumbnail of a local image and contains associated metadata"""

    def __init__(self, file_path: str):
        super().__init__()
        self.metadata = MetaMetadata(file_path)
        self.setPixmap(QPixmap(get_thumbnail(file_path)))
        self.setToolTip(f'{file_path}\n{self.metadata.summary}')

        # Can't be used with pixmap?
        # self.setFrameShape(QFrame.StyledPanel)
        # self.setFrameShadow(QFrame.Raised)


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
        self.viewer = QtImageViewer()
        pagelayout.addWidget(self.viewer)

        widget = QWidget()
        widget.setLayout(pagelayout)
        self.setCentralWidget(widget)

        # Toolbar
        toolbar = QToolBar('My main toolbar')
        toolbar.setIconSize(QSize(24, 24))
        self.addToolBar(toolbar)

        # get_button('&Run', 'control.png', self.on_toolbar_click, self)
        button_action_1 = get_button(
            '&Run', 'ic_play_arrow_black_24dp.png', 'Run a thing', self.on_toolbar_click, self
        )
        toolbar.addAction(button_action_1)
        toolbar.addSeparator()

        button_action_2 = get_button(
            '&Open', 'ic_insert_photo_black_24dp.png', 'Open images', self.viewer.load_file_dialog, self
        )
        toolbar.addAction(button_action_2)
        toolbar.addSeparator()

        button_action_3 = get_button(
            '&Paste', 'ic_content_paste_black_24dp.png', 'Paste a thing', self.on_toolbar_click, self
        )
        button_action_3.setCheckable(True)
        toolbar.addAction(button_action_3)
        toolbar.addSeparator()

        button_action_4 = get_button(
            '&History', 'ic_history_black_24dp.png', 'View history', self.on_toolbar_click, self
        )
        button_action_4.setCheckable(True)
        toolbar.addAction(button_action_4)

        # Menu bar
        menu = self.menuBar()
        file_menu = menu.addMenu('&File')
        file_menu.addAction(button_action_1)
        file_menu.addAction(button_action_2)
        file_submenu = file_menu.addMenu('Submenu')
        file_submenu.addAction(button_action_3)
        file_submenu.addAction(button_action_4)

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

    def on_toolbar_click(self, s):
        logger.info(f'Click; checked: {s}')


def get_button(name: str, icon: str, tooltip: str, callback: Callable, parent: QWidget) -> QAction:
    button_action = QAction(QIcon(str(ICONS_DIR / icon)), name, parent)
    button_action.setStatusTip(tooltip)
    button_action.triggered.connect(callback)
    return button_action


if __name__ == '__main__':
    app = QApplication(sys.argv)
    apply_stylesheet(app, theme='dark_lightgreen.xml')
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
