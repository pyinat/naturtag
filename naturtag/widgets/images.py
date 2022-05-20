from logging import getLogger
from pathlib import Path
from typing import Union

from pyinaturalist import Photo, Taxon
from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QLabel, QWidget

from naturtag.app.style import fa_icon
from naturtag.client import IMG_SESSION

logger = getLogger(__name__)


class IconLabel(QLabel):
    """A QLabel for displaying a FontAwesome icon"""

    def __init__(self, icon_str: str, parent: QWidget = None, size: int = 20, active: bool = True):
        super().__init__(parent)

        # TODO: Use palette, figure out setting icon state
        icon = fa_icon(icon_str, color='yellowgreen' if active else 'gray')
        self.setPixmap(icon.pixmap(size, size))


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
            pixmap = fetch_image(taxon.default_photo)
        elif url:
            pixmap = fetch_image(Photo(url=url))
        if pixmap is not None:
            self._pixmap = pixmap
            super().setPixmap(self.scaledPixmap())

    def clear(self):
        self.setPixmap(QPixmap())

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


def fetch_image(photo: Photo) -> QPixmap:
    data = IMG_SESSION.get(photo.url, stream=True).content
    pixmap = QPixmap()
    pixmap.loadFromData(data, format=photo.ext)
    return pixmap
