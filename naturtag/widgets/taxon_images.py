"""Image widgets specifically for taxon photos"""
from typing import TYPE_CHECKING, Iterable, Iterator, Optional

from pyinaturalist import Taxon, TaxonCount
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QLabel, QScrollArea, QSizePolicy, QWidget

from naturtag.widgets.images import ImageWindow, PixmapLabel, fetch_image
from naturtag.widgets.layouts import HorizontalLayout, StylableWidget, VerticalLayout

if TYPE_CHECKING:
    from naturtag.app.threadpool import ThreadPool


class TaxonPixmapLabel(PixmapLabel):
    """A PixmapLabel for a taxon photo that adds a click event"""

    clicked = Signal(Taxon)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.taxon = None

    def set_taxon(self, taxon: Taxon, size: str = 'medium'):
        self.taxon = taxon
        self._pixmap = fetch_image(taxon.default_photo, size=size)
        QLabel.setPixmap(self, self.scaledPixmap())

    def mousePressEvent(self, _):
        """Placeholder to accept mouse press events"""

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.taxon)


class TaxonList(VerticalLayout):
    """A scrollable list of TaxonInfoCards"""

    def __init__(self, threadpool: 'ThreadPool', parent: QWidget = None):
        super().__init__(parent)
        self.threadpool = threadpool

        self.scroll_panel = QWidget()
        self.scroll_layout = VerticalLayout(self.scroll_panel)
        self.scroll_layout.setAlignment(Qt.AlignTop)
        self.scroll_layout.setContentsMargins(0, 0, 0, 0)
        self.addLayout(self.scroll_layout)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setWidget(self.scroll_panel)
        self.addWidget(scroll_area)

    @property
    def taxa(self) -> Iterator['TaxonInfoCard']:
        for item in self.scroll_panel.children():
            if isinstance(item, TaxonInfoCard):
                yield item

    def add_taxon(self, taxon: Taxon, idx: int = None):
        """Add a taxon card immediately, and load its thumbnail from a separate thread"""
        card = TaxonInfoCard(taxon=taxon)
        if idx is not None:
            self.scroll_layout.insertWidget(idx, card)
        else:
            self.scroll_layout.addWidget(card)
        self.threadpool.schedule(card.thumbnail.setPixmap, taxon=taxon)

    def add_or_update(self, taxon: Taxon, idx: int = 0):
        """Move a taxon card to the specified position, and add a new one if it doesn't exist"""
        if not self.move_card(taxon.id, idx):
            self.add_taxon(taxon, idx)

    def clear(self):
        self.scroll_layout.clear()

    def contains(self, taxon_id: int) -> bool:
        return self.get_card_by_id(taxon_id) is not None

    def get_card_by_id(self, taxon_id: int) -> Optional['TaxonInfoCard']:
        for card in self.taxa:
            if card.taxon.id == taxon_id:
                return card
        return None

    def move_card(self, taxon_id: int, idx: int = 0) -> bool:
        """Move a card to the specified position, if found; return False otherwise"""
        card = self.get_card_by_id(taxon_id)
        if card:
            self.scroll_layout.removeWidget(card)
            self.scroll_layout.insertWidget(idx, card)
            return True
        return False

    def set_taxa(self, taxa: Iterable[Taxon]):
        self.clear()
        for taxon in taxa:
            if taxon is not None:
                self.add_taxon(taxon)


class TaxonInfoCard(StylableWidget):
    """Card containing a taxon thumbnail, name, common name, and rank"""

    clicked = Signal(int)

    def __init__(self, taxon: Taxon, delayed_load: bool = True):
        super().__init__()
        card_layout = HorizontalLayout()
        self.setLayout(card_layout)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        if isinstance(taxon, TaxonCount):
            self.setToolTip(f'Count: {taxon.count}')
        self.setFixedHeight(90)
        self.taxon = taxon
        self.taxon_id = taxon.id

        # Image
        self.thumbnail = TaxonPixmapLabel()
        self.thumbnail.setFixedWidth(75)
        card_layout.addWidget(self.thumbnail)
        if not delayed_load:
            self.thumbnail.set_taxon(taxon, size='thumbnail')

        # Details
        # TODO: Style with QSS
        title = QLabel(taxon.name)
        font = QFont()
        font.setPixelSize(16)
        font.setBold(True)
        font.setItalic(True)
        title.setFont(font)
        details_layout = VerticalLayout()
        card_layout.addLayout(details_layout)
        details_layout.addWidget(title)
        details_layout.addWidget(QLabel(taxon.rank))
        details_layout.addWidget(QLabel(taxon.preferred_common_name))

    def mousePressEvent(self, _):
        """Placeholder to accept mouse press events"""

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.taxon.id)


class TaxonImageWindow(ImageWindow):
    """Full-size image viewer that displays photos from URLs instead of local files"""

    def display_taxon(self, taxon: Taxon):
        """Open window to a selected taxon image, and save other taxon image URLs for navigation"""
        self.selected_path = taxon.default_photo.original_url
        self.image_paths = [p.original_url for p in taxon.taxon_photos]
        self.image.setPixmap(url=self.selected_path)
        self.showFullScreen()

    def set_pixmap(self, url: str):
        self.image.setPixmap(url=url)
