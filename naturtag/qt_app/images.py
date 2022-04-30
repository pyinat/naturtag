from logging import basicConfig, getLogger
from os.path import isfile
from urllib.parse import unquote, urlparse

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDropEvent, QPixmap
from PySide6.QtWidgets import (
    QFileDialog,
    QGraphicsGridLayout,
    QGraphicsScene,
    QGraphicsView,
    QGraphicsWidget,
    QLabel,
)

from naturtag.constants import IMAGE_FILETYPES
from naturtag.models import MetaMetadata
from naturtag.thumbnails import get_thumbnail

logger = getLogger(__name__)


class ImageViewer(QGraphicsView):
    file_changed = Signal(str)

    def __init__(self):
        super().__init__()
        self.scene = QGraphicsScene()
        self.setScene(self.scene)
        self.setAcceptDrops(True)
        self.clear()

        self.aspectRatioMode = Qt.KeepAspectRatio
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

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

    # TODO: Do previously added widgets get garbage collected?
    def clear(self):
        """Clear all images from the viewer"""
        self.scene.clear()
        self.layout = QGraphicsGridLayout()
        form = QGraphicsWidget()
        form.setLayout(self.layout)
        self.scene.addItem(form)

        self.img_row = 0
        self.img_col = 0
        self.images = {}

    def dragEnterEvent(self, event):
        event.acceptProposedAction()

    def dragMoveEvent(self, event):
        event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        event.acceptProposedAction()
        for file_path in event.mimeData().text().splitlines():
            self.load_file(file_path)


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
