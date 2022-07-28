"""Image widgets specifically for taxon photos"""
import re
from logging import getLogger
from typing import TYPE_CHECKING, Iterable, Iterator, Optional

from pyinaturalist import Photo, Taxon, TaxonCount
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QLabel, QScrollArea, QSizePolicy, QWidget

from naturtag.constants import SIZE_SM
from naturtag.widgets.images import (
    HoverMixin,
    HoverMixinBase,
    ImageWindow,
    NavButtonsMixin,
    PixmapLabel,
)
from naturtag.widgets.layouts import HorizontalLayout, StylableWidget, VerticalLayout

if TYPE_CHECKING:
    from naturtag.app.threadpool import ThreadPool

ATTRIBUTION_STRIP_PATTERN = re.compile(r',?\s+uploaded by.*')

logger = getLogger(__name__)


# Note: This doesn't inherit from HoverMixin because overlay is shown when TaxonInfoCard is hovered
class TaxonPhoto(HoverMixinBase, PixmapLabel):
    """A taxon photo widget with a Taxon reference and a click event

    Args:
        taxon: The taxon associated with this photo
        idx: The index of this photo within Taxon.taxon_photos
    """

    def __init__(self, *args, taxon: Taxon = None, idx: int = 0, **kwargs):
        super().__init__(*args, **kwargs)
        self.idx = idx
        self.taxon = taxon


class FullscreenTaxonPhoto(NavButtonsMixin, TaxonPhoto):
    """A fullscreen taxon photo widget with nav buttons"""


class HoverTaxonPhoto(HoverMixin, TaxonPhoto):
    """A taxon photo widget with hover effect"""


class TaxonImageWindow(ImageWindow):
    """Display taxon images in fullscreen as a separate window. Uses URLs instead of local file paths."""

    def __init__(self):
        super().__init__(image_class=FullscreenTaxonPhoto)
        self.taxon: Taxon = None
        self.photos: list[Photo] = None
        self.selected_photo: Photo = None

    @property
    def idx(self) -> int:
        """The index of the currently selected image"""
        return self.photos.index(self.selected_photo)

    def display_taxon(self, taxon_image: FullscreenTaxonPhoto):
        """Open window to a selected taxon image, and save other taxon image URLs for navigation"""
        idx = taxon_image.idx
        taxon = taxon_image.taxon
        if TYPE_CHECKING:
            assert taxon is not None

        self.taxon = taxon_image.taxon
        self.selected_photo = taxon.taxon_photos[idx] if taxon.taxon_photos else taxon.default_photo
        self.photos = taxon.taxon_photos
        self.image_paths = [photo.original_url for photo in self.photos]
        self.set_photo(self.selected_photo)
        self.showFullScreen()

    def select_image_idx(self, idx: int):
        """Select an image by index"""
        self.selected_photo = self.photos[idx]
        self.set_photo(self.selected_photo)

    def set_photo(self, photo: Photo):
        self.image.setPixmap(self.image.get_pixmap(url=photo.original_url))
        attribution = (
            ATTRIBUTION_STRIP_PATTERN.sub('', photo.attribution or '')
            .replace('(c)', '©')
            .replace('CC ', 'CC-')
        )
        self.image.description = f'{self.taxon.full_name}\n{attribution}'

    def remove_image(self):
        pass


class TaxonList(StylableWidget):
    """A scrollable list of TaxonInfoCards"""

    def __init__(self, threadpool: 'ThreadPool', parent: QWidget = None):
        super().__init__(parent)
        self.threadpool = threadpool
        self.root = VerticalLayout(self)
        self.root.setAlignment(Qt.AlignTop)
        self.root.setContentsMargins(0, 5, 5, 0)

        self.scroller = QScrollArea()
        self.scroller.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroller.setWidgetResizable(True)
        self.scroller.setWidget(self)

    @property
    def taxa(self) -> Iterator['TaxonInfoCard']:
        for item in self.children():
            if isinstance(item, TaxonInfoCard):
                yield item

    def add_taxon(self, taxon: Taxon, idx: int = None):
        """Add a taxon card immediately, and load its thumbnail from a separate thread"""
        card = TaxonInfoCard(taxon=taxon)
        if idx is not None:
            self.root.insertWidget(idx, card)
        else:
            self.root.addWidget(card)
        card.thumbnail.set_pixmap_async(
            self.threadpool, photo=taxon.default_photo, size='thumbnail'
        )

    def add_or_update(self, taxon: Taxon, idx: int = 0):
        """Move a taxon card to the specified position, and add a new one if it doesn't exist"""
        if not self.move_card(taxon.id, idx):
            self.add_taxon(taxon, idx)

    def clear(self):
        self.root.clear()

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
            self.root.removeWidget(card)
            self.root.insertWidget(idx, card)
            return True
        return False

    def set_taxa(self, taxa: Iterable[Taxon]):
        self.clear()
        for taxon in taxa:
            if taxon is not None:
                self.add_taxon(taxon)


class TaxonInfoCard(StylableWidget):
    """Card containing a taxon thumbnail, name, common name, and rank"""

    on_click = Signal(int)

    def __init__(self, taxon: Taxon, delayed_load: bool = True):
        super().__init__()
        card_layout = HorizontalLayout(self)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setFixedHeight(90)

        self.taxon = taxon
        if isinstance(taxon, TaxonCount):
            self.setToolTip(f'Count: {taxon.count}')

        # Image
        self.thumbnail = TaxonPhoto(taxon=self.taxon)
        self.thumbnail.setFixedSize(*SIZE_SM)
        card_layout.addWidget(self.thumbnail)
        if not delayed_load:
            pixmap = self.thubmnail.get_pixmap(url=taxon.default_photo.thumbnail_url)
            self.thumbnail.setPixmap(pixmap)

        # Details
        self.title = QLabel(taxon.name)
        self.title.setObjectName('h1_italic')
        self.line_1 = QLabel(taxon.rank)
        self.line_2 = QLabel(taxon.preferred_common_name)

        details_layout = VerticalLayout()
        details_layout.addWidget(self.title)
        details_layout.addWidget(self.line_1)
        details_layout.addWidget(self.line_2)
        card_layout.addLayout(details_layout)

    # Darken thumbnail when hovering over card. Background hover is handled in QSS.
    def enterEvent(self, event):
        self.thumbnail.overlay.setVisible(True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.thumbnail.overlay.setVisible(False)
        super().leaveEvent(event)

    def mousePressEvent(self, _):
        """Placeholder to accept mouse press events"""

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.on_click.emit(self.taxon.id)
