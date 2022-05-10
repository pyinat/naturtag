from logging import getLogger
from time import time
from typing import Callable, Iterable, Iterator

from pyinaturalist import Taxon
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QGroupBox, QLabel, QLineEdit, QListWidget, QScrollArea, QWidget

from naturtag.app.images import PixmapLabel
from naturtag.app.layouts import HorizontalLayout, VerticalLayout
from naturtag.metadata.inat_metadata import INAT_CLIENT
from naturtag.settings import Settings

logger = getLogger(__name__)


class TaxonController(QWidget):
    """Controller for searching taxa"""

    def __init__(self, settings: Settings, info_callback: Callable):
        super().__init__()
        self.settings = settings
        root_layout = HorizontalLayout()
        self.setLayout(root_layout)
        self.selected_taxon: Taxon = None
        self.info = info_callback

        self.input_layout = VerticalLayout()
        root_layout.addLayout(self.input_layout)

        # Taxon name autocomplete
        autocomplete_layout = VerticalLayout()
        autocomplete_layout.setAlignment(Qt.AlignTop)
        group_box = QGroupBox('Search')
        group_box.setFixedWidth(400)
        group_box.setLayout(autocomplete_layout)
        self.input_layout.addWidget(group_box)

        self.input_taxon_search = QLineEdit()
        self.input_taxon_search.setClearButtonEnabled(True)
        autocomplete_layout.addWidget(self.input_taxon_search)

        autocomplete_results = QListWidget()
        autocomplete_results.addItems([f'result {i+1}' for i in range(10)])
        # autocomplete_results.setVisible(False)
        autocomplete_results.setFixedHeight(300)
        autocomplete_layout.addWidget(autocomplete_results)

        # Category inputs
        categories_layout = VerticalLayout()
        group_box = QGroupBox('Categories')
        group_box.setFixedWidth(400)
        group_box.setLayout(categories_layout)
        self.input_layout.addWidget(group_box)
        categories_layout.addWidget(QLabel('1'))
        categories_layout.addWidget(QLabel('2'))
        categories_layout.addWidget(QLabel('3'))

        # Rank inputs
        rank_layout = VerticalLayout()
        group_box = QGroupBox('Rank')
        group_box.setFixedWidth(400)
        group_box.setLayout(rank_layout)
        self.input_layout.addWidget(group_box)
        rank_layout.addWidget(QLabel('1'))
        rank_layout.addWidget(QLabel('2'))
        rank_layout.addWidget(QLabel('3'))

        # Selected taxon
        results_layout = VerticalLayout()
        root_layout.addLayout(results_layout)
        self.taxon_info = TaxonInfoSection()
        results_layout.addLayout(self.taxon_info)
        self.taxonomy = TaxonomySection()
        results_layout.addLayout(self.taxonomy)

        self.select_taxon(47792)

    def select_taxon(self, taxon_id: int = None, taxon: Taxon = None):
        """Update taxon info display"""
        # Don't need to do anything if this taxon is already selected
        id = taxon_id or getattr(taxon, 'id', None)
        if self.selected_taxon and self.selected_taxon.id == id:
            return

        logger.info(f'Selecting taxon {id}')
        start = time()
        if taxon_id and not taxon:
            taxon = INAT_CLIENT.taxa.from_id(taxon_id).one()
        assert taxon is not None
        self.selected_taxon = taxon

        self.taxon_info.load(taxon)
        self.taxonomy.load(taxon)

        # Clicking on a taxon card will select it
        for card in self.taxonomy.taxa:
            card.clicked.connect(self.select_taxon)
        logger.info(f'Loaded taxon {taxon.id} in {time() - start:.2f}s')


class TaxonInfoSection(HorizontalLayout):
    """Section to display selected taxon photo and basic info"""

    def __init__(self):
        super().__init__()

        self.group = QGroupBox('Selected Taxon')
        inner_layout = HorizontalLayout(self.group)
        self.addWidget(self.group)
        self.setAlignment(Qt.AlignTop)

        self.image = PixmapLabel()
        self.image.setMinimumWidth(200)
        self.image.setMaximumWidth(400)
        inner_layout.addWidget(self.image)

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
        # Label, photo ,and iconic taxon icon
        common_name = f' ({taxon.preferred_common_name}) ' if taxon.preferred_common_name else ''
        self.group.setTitle(f'{taxon.name}{common_name}')
        self.image.setPixmap(taxon=taxon)
        self.icon.setPixmap(url=taxon.icon_url)

        # Other attributes
        self.details.clear()
        self.details.addWidget(QLabel(f'ID: {taxon.id}'))
        self.details.addWidget(QLabel(f'Rank: {taxon.rank}'))
        self.details.addWidget(QLabel(f'Observations: {taxon.observations_count}'))
        self.details.addWidget(QLabel(f'Child species: {taxon.complete_species_count}'))


class TaxonomySection(HorizontalLayout):
    """Section to display ancestors and children of selected taxon"""

    def __init__(self):
        super().__init__()

        self.ancestors_group = QGroupBox('Ancestors')
        self.ancestors_group.setFixedWidth(400)
        self.ancestors_layout = TaxonList(self.ancestors_group)
        self.addWidget(self.ancestors_group)

        self.children_group = QGroupBox('Children')
        self.children_group.setFixedWidth(400)
        self.children_layout = TaxonList(self.children_group)
        self.addWidget(self.children_group)

    def load(self, taxon: Taxon):
        """Populate taxon ancestors and children"""
        logger.info(f'Loading {len(taxon.ancestors)} ancestors and {len(taxon.children)} children')

        def get_label(text: str, items: list) -> str:
            return text + (f' ({len(items)})' if items else '')

        self.ancestors_group.setTitle(get_label('Ancestors', taxon.ancestors))
        self.ancestors_layout.set_taxa(taxon.ancestors)
        self.children_group.setTitle(get_label('Children', taxon.children))
        self.children_layout.set_taxa(taxon.children)

    @property
    def taxa(self) -> Iterator['TaxonInfoCard']:
        yield from self.ancestors_layout.taxa
        yield from self.children_layout.taxa


class TaxonList(VerticalLayout):
    """A scrollable list of TaxonInfoCards"""

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)

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

    def add_taxon(self, taxon: Taxon):
        self.scroll_layout.addWidget(TaxonInfoCard(taxon=taxon))

    def clear(self):
        self.scroll_layout.clear()

    def set_taxa(self, taxa: Iterable[Taxon]):
        self.clear()
        for taxon in taxa:
            self.add_taxon(taxon)


class TaxonInfoCard(QWidget):
    clicked = Signal(int)

    def __init__(self, taxon: Taxon):
        super().__init__()
        card_layout = HorizontalLayout()
        self.setLayout(card_layout)
        self.taxon_id = taxon.id

        # Image
        img = PixmapLabel(taxon=taxon)
        img.setFixedWidth(75)
        card_layout.addWidget(img)

        # Details
        title = QLabel(taxon.name)
        details_layout = VerticalLayout()
        card_layout.addLayout(details_layout)
        details_layout.addWidget(title)
        details_layout.addWidget(QLabel(taxon.rank))
        details_layout.addWidget(QLabel(taxon.preferred_common_name))

    def mousePressEvent(self, _):
        """Placeholder to accept mouse press events"""

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.taxon_id)
