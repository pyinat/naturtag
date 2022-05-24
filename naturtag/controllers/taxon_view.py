"""Components for displaying taxon info"""
from logging import getLogger
from typing import Iterable, Iterator, Optional

from pyinaturalist import Taxon, TaxonCount
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QGroupBox, QLabel, QScrollArea, QSizePolicy, QWidget

from naturtag.app.threadpool import ThreadPool
from naturtag.controllers import ImageWindow
from naturtag.widgets import HorizontalLayout, PixmapLabel, StylableWidget, VerticalLayout
from naturtag.widgets.images import fetch_image

logger = getLogger(__name__)


# thumbnail.selected.connect(self.select_image)
class TaxonInfoSection(HorizontalLayout):
    """Section to display selected taxon photo and basic info"""

    def __init__(self, threadpool: ThreadPool):
        super().__init__()
        self.threadpool = threadpool

        self.group = QGroupBox('Selected Taxon')
        inner_layout = HorizontalLayout(self.group)
        self.addWidget(self.group)
        self.setAlignment(Qt.AlignTop)

        # Medium taxon default photo
        self.image = TaxonPixmapLabel()
        self.image.setMinimumWidth(200)
        self.image.setMaximumWidth(600)
        self.image.setMaximumHeight(400)
        inner_layout.addWidget(self.image)

        self.image_window = TaxonImageWindow()
        self.image.clicked.connect(self.image_window.display_taxon)

        self.icon = PixmapLabel()
        self.icon.setFixedSize(75, 75)
        icon_layout = HorizontalLayout()
        icon_layout.setAlignment(Qt.AlignTop)
        icon_layout.addWidget(self.icon)
        inner_layout.addLayout(icon_layout)

        self.details = VerticalLayout()
        self.details.setAlignment(Qt.AlignTop)
        inner_layout.addLayout(self.details)

    def load(self, taxon: Taxon):
        # Label, photo, and iconic taxon icon
        common_name = f' ({taxon.preferred_common_name}) ' if taxon.preferred_common_name else ''
        self.group.setTitle(f'{taxon.name}{common_name}')
        self.threadpool.schedule(self.image.set_taxon, taxon=taxon)
        self.threadpool.schedule(self.icon.setPixmap, url=taxon.icon_url)

        # Other attributes
        self.details.clear()
        self.details.addWidget(QLabel(f'ID: {taxon.id}'))
        self.details.addWidget(QLabel(f'Rank: {taxon.rank}'))
        self.details.addWidget(QLabel(f'Observations: {taxon.observations_count}'))
        self.details.addWidget(QLabel(f'Child species: {taxon.complete_species_count}'))


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


class TaxonomySection(HorizontalLayout):
    """Section to display ancestors and children of selected taxon"""

    def __init__(self, threadpool: ThreadPool):
        super().__init__()

        self.ancestors_group = QGroupBox('Ancestors')
        self.ancestors_group.setFixedWidth(400)
        self.ancestors_list = TaxonList(threadpool, self.ancestors_group)
        self.addWidget(self.ancestors_group)

        self.children_group = QGroupBox('Children')
        self.children_group.setFixedWidth(400)
        self.children_list = TaxonList(threadpool, self.children_group)
        self.addWidget(self.children_group)

    def load(self, taxon: Taxon):
        """Populate taxon ancestors and children"""
        logger.info(f'Loading {len(taxon.ancestors)} ancestors and {len(taxon.children)} children')

        def get_label(text: str, items: list) -> str:
            return text + (f' ({len(items)})' if items else '')

        self.ancestors_group.setTitle(get_label('Ancestors', taxon.ancestors))
        self.ancestors_list.set_taxa(taxon.ancestors)
        self.children_group.setTitle(get_label('Children', taxon.children))
        self.children_list.set_taxa(taxon.children)

    @property
    def taxa(self) -> Iterator['TaxonInfoCard']:
        yield from self.ancestors_list.taxa
        yield from self.children_list.taxa


class TaxonList(VerticalLayout):
    """A scrollable list of TaxonInfoCards"""

    def __init__(self, threadpool: ThreadPool, parent: QWidget = None):
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
        logger.info(f'Next taxon photo URL: {url}')
        self.image.setPixmap(url=url)
