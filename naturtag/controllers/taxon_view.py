"""Components for displaying taxon info"""
from logging import getLogger
from typing import Iterator

from pyinaturalist import Taxon
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGroupBox, QLabel

from naturtag.app.threadpool import ThreadPool
from naturtag.widgets import (
    HorizontalLayout,
    PixmapLabel,
    TaxonImageWindow,
    TaxonInfoCard,
    TaxonList,
    TaxonPixmapLabel,
    VerticalLayout,
)

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
        self.image.on_click.connect(self.image_window.display_taxon)

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
