"""Image widgets specifically for taxon photos"""
import re
from logging import getLogger
from typing import TYPE_CHECKING, Iterable

from pyinaturalist import Photo, Taxon, TaxonCount

from naturtag.widgets.images import HoverPhoto, ImageWindow, InfoCard, InfoCardList

ATTRIBUTION_STRIP_PATTERN = re.compile(r',?\s+uploaded by.*')

logger = getLogger(__name__)


class TaxonPhoto(HoverPhoto):
    """A photo with a taxon reference and hover effect"""

    def __init__(self, taxon: Taxon = None, **kwargs):
        super().__init__(**kwargs)
        self.taxon = taxon


class TaxonInfoCard(InfoCard):
    """Card containing a taxon thumbnail, name, common name, and rank"""

    def __init__(self, taxon: Taxon, delayed_load: bool = True):
        super().__init__(card_id=taxon.id)
        self.setFixedHeight(90)
        self.taxon = taxon
        if isinstance(taxon, TaxonCount):
            self.setToolTip(f'Count: {taxon.count}')

        # Image
        if not delayed_load:
            pixmap = self.thumbnail.get_pixmap(url=taxon.default_photo.thumbnail_url)
            self.thumbnail.setPixmap(pixmap)

        # Details
        self.title.setText(taxon.name)
        self.title.setObjectName('h1_italic')
        self.line_1.setText(taxon.rank)
        self.line_2.setText(taxon.preferred_common_name)


class TaxonList(InfoCardList):
    """A scrollable list of TaxonInfoCards"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def add_taxon(self, taxon: Taxon, idx: int = None):
        """Add a card immediately, and load its thumbnail from a separate thread"""
        card = TaxonInfoCard(taxon)
        super().add_card(card, taxon.default_photo.thumbnail_url, idx=idx)

    def add_or_update_taxon(self, taxon: Taxon, idx: int = 0):
        """Move a card to the specified position, and add a new one if it doesn't exist"""
        if not self.move_card(taxon.id, idx):
            self.add_taxon(taxon, idx)

    def set_taxa(self, taxa: Iterable[Taxon]):
        """Replace all existing cards with new ones for the specified taxa"""
        self.clear()
        for taxon in taxa:
            if taxon is not None:
                self.add_taxon(taxon)


class TaxonImageWindow(ImageWindow):
    """Display taxon images in fullscreen as a separate window. Uses URLs instead of local file paths."""

    def __init__(self):
        super().__init__()
        self.taxon: Taxon = None
        self.photos: list[Photo] = None
        self.selected_photo: Photo = None

    @property
    def idx(self) -> int:
        """The index of the currently selected image"""
        return self.photos.index(self.selected_photo)

    def display_taxon_fullscreen(self, taxon_photo: TaxonPhoto):
        """Open window to a selected taxon image, and save other taxon image URLs for navigation"""
        idx = taxon_photo.idx
        taxon = taxon_photo.taxon
        if TYPE_CHECKING:
            assert taxon is not None

        self.taxon = taxon_photo.taxon
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
