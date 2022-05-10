from logging import getLogger
from pathlib import Path
from typing import Union

from pyinaturalist import Photo, Taxon
from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QLabel, QWidget

from naturtag.metadata.inat_metadata import INAT_CLIENT

logger = getLogger(__name__)


class PixmapLabel(QLabel):
    """A QLabel containing a pixmap that preserves its aspect ratio when resizing"""

    def __init__(
        self,
        parent: QWidget = None,
        pixmap: QPixmap = None,
        path: Union[str, Path] = None,
        taxon: Taxon = None,
        url: str = None,
    ):
        super().__init__(parent)
        self.setMinimumSize(1, 1)
        self.setScaledContents(False)
        self._pixmap = None
        self.setPixmap(pixmap, path, taxon, url)

    def setPixmap(
        self,
        pixmap: QPixmap = None,
        path: Union[str, Path] = None,
        taxon: Taxon = None,
        url: str = None,
    ):
        if path:
            pixmap = QPixmap(str(path))
        elif taxon:
            pixmap = _get_image(taxon.default_photo or Photo(url=taxon.icon_url))
        elif url:
            pixmap = _get_image(Photo(url=url))
        if pixmap:
            self._pixmap = pixmap
            super().setPixmap(self.scaledPixmap())

    def heightForWidth(self, width: int) -> int:
        if self._pixmap:
            return (self._pixmap.height() * width) / self._pixmap.width()
        else:
            return self.height()

    def sizeHint(self) -> QSize:
        return QSize(self.width(), self.heightForWidth(self.width()))

    def scaledPixmap(self) -> QPixmap:
        assert self._pixmap is not None
        return self._pixmap.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)

    def resizeEvent(self, _):
        if self._pixmap:
            super().setPixmap(self.scaledPixmap())


# TODO: Simplify this with changes to Photo model
def _get_image(photo: Photo) -> QPixmap:
    data = INAT_CLIENT.session.get(photo.url, stream=True).content
    pixmap = QPixmap()
    pixmap.loadFromData(data, format=photo.mimetype.replace('image/', ''))
    return pixmap
