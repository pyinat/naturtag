"""Components for displaying taxon info"""
from logging import getLogger
from typing import Iterator

from pyinaturalist import Taxon
from PySide6.QtCore import QEvent, Qt
from PySide6.QtWidgets import QGroupBox

from naturtag.app.threadpool import ThreadPool
from naturtag.widgets import (
    GridLayout,
    HorizontalLayout,
    TaxonImageWindow,
    TaxonInfoCard,
    TaxonList,
)
from naturtag.widgets.taxon_images import HoverTaxonPhoto

logger = getLogger(__name__)


# thumbnail.selected.connect(self.select_image)
class TaxonInfoSection(HorizontalLayout):
    """Section to display selected taxon photo and basic info"""

    def __init__(self, threadpool: ThreadPool):
        super().__init__()
        self.threadpool = threadpool
        self.group_box = QGroupBox('Selected Taxon')
        root = HorizontalLayout(self.group_box)
        self.addWidget(self.group_box)
        self.setAlignment(Qt.AlignTop)

        # Medium taxon default photo
        self.image = HoverTaxonPhoto(hover_icon=True)
        self.image.setObjectName('selected_taxon')
        self.image.setFixedHeight(395)  # Height of 5 thumbnails + spacing
        self.image.setAlignment(Qt.AlignTop)
        root.addWidget(self.image)

        # Additional taxon photos
        self.taxon_thumbnails = GridLayout(n_columns=2)
        self.taxon_thumbnails.setSpacing(5)
        root.addLayout(self.taxon_thumbnails)

        # Fullscreen image viewer
        self.image_window = TaxonImageWindow()
        self.image.on_click.connect(self.image_window.display_taxon)

    def load(self, taxon: Taxon):
        """Load default photo + additional thumbnails"""
        self.group_box.setTitle(taxon.full_name)
        self.threadpool.schedule(self.image.set_taxon, taxon=taxon)

        self.taxon_thumbnails.clear()
        for i, photo in enumerate(taxon.taxon_photos[1:] if taxon.taxon_photos else []):
            thumb = HoverTaxonPhoto(taxon=taxon, idx=i + 1)
            thumb.setFixedSize(75, 75)
            thumb.on_click.connect(self.image_window.display_taxon)
            self.taxon_thumbnails.add_widget(thumb)
            self.threadpool.schedule(thumb.set_pixmap, url=photo.thumbnail_url)

    def enterEvent(self, event: QEvent):
        logger.warning('Enter')
        self.open_overlay.setVisible(True)
        return super().enterEvent(event)

    def leaveEvent(self, event: QEvent) -> None:
        logger.warning('Leave')
        self.open_overlay.setVisible(False)
        return super().leaveEvent(event)


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
