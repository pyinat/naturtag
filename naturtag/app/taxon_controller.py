from logging import getLogger
from time import time
from typing import Callable, Iterator

from pyinaturalist import Taxon
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLayout,
    QLineEdit,
    QListWidget,
    QVBoxLayout,
    QWidget,
)

from naturtag.app.image_window import PixmapLabel
from naturtag.metadata.inat_metadata import INAT_CLIENT
from naturtag.settings import Settings

# from naturtag.thumbnails import get_thumbnail

logger = getLogger(__name__)


H1_FONT = QFont()
H1_FONT.setWeight(QFont.Bold)
H1_FONT.setPointSize(20)
H2_FONT = QFont()
H2_FONT.setWeight(QFont.Bold)
H2_FONT.setPointSize(16)


ancestors = [
    Taxon(name='Animalia', id=1, rank='kingdom', preferred_common_name='Animals'),
    Taxon(name='Arthropoda', id=1, rank='phylum', preferred_common_name='Arthropods'),
    Taxon(name='Hexapoda', id=1, rank='subphylum', preferred_common_name='Hexapods'),
    Taxon(name='Insecta', id=1, rank='class', preferred_common_name='Insects'),
    Taxon(name='Pterygota', id=1, rank='subclass', preferred_common_name='Winged insects'),
]
children = [
    Taxon(name='Anisoptera', id=12345, rank='suborder', preferred_common_name='Dragonflies'),
    Taxon(name='Zygoptera', id=12345, rank='suborder', preferred_common_name='Damselflies'),
]


class TaxonController(QWidget):
    """Controller for searching taxa"""

    def __init__(self, settings: Settings, info_callback: Callable):
        super().__init__()
        self.settings = settings
        root_layout = QHBoxLayout()
        self.setLayout(root_layout)
        self.selected_taxon: Taxon = None
        self.info = info_callback

        input_layout = QVBoxLayout()
        root_layout.addLayout(input_layout)

        # Taxon name autocomplete
        autocomplete_layout = QVBoxLayout()
        autocomplete_layout.setAlignment(Qt.AlignTop)
        group_box = QGroupBox('Search')
        group_box.setFixedWidth(400)
        group_box.setFont(H2_FONT)
        group_box.setLayout(autocomplete_layout)
        input_layout.addWidget(group_box)

        self.input_taxon_search = QLineEdit()
        self.input_taxon_search.setClearButtonEnabled(True)
        autocomplete_layout.addWidget(self.input_taxon_search)

        autocomplete_results = QListWidget()
        autocomplete_results.addItems([f'result {i+1}' for i in range(10)])
        # autocomplete_results.setVisible(False)
        autocomplete_results.setFixedHeight(300)
        autocomplete_layout.addWidget(autocomplete_results)

        # Iconic taxa (category) inputs
        categories_layout = QVBoxLayout()
        group_box = QGroupBox('Categories')
        group_box.setFixedWidth(400)
        group_box.setFont(H2_FONT)
        group_box.setLayout(categories_layout)
        input_layout.addWidget(group_box)

        categories_layout.addWidget(QLabel('1'))
        categories_layout.addWidget(QLabel('2'))
        categories_layout.addWidget(QLabel('3'))

        # Rank inputs
        rank_layout = QVBoxLayout()
        group_box = QGroupBox('Rank')
        group_box.setFixedWidth(400)
        group_box.setFont(H2_FONT)
        group_box.setLayout(rank_layout)
        input_layout.addWidget(group_box)

        rank_layout.addWidget(QLabel('1'))
        rank_layout.addWidget(QLabel('2'))
        rank_layout.addWidget(QLabel('3'))

        # -----------------

        # Selected taxon
        results_layout = QVBoxLayout()
        root_layout.addLayout(results_layout)

        self.selected_taxon_title = QLabel('Selected Taxon')
        self.selected_taxon_title.setFont(H2_FONT)
        results_layout.addWidget(self.selected_taxon_title)

        self.taxon_info = TaxonInfoSection()
        results_layout.addLayout(self.taxon_info)

        self.taxonomy = TaxonomySection()
        results_layout.addLayout(self.taxonomy)

        self.select_taxon(47792)

    def select_taxon(self, taxon_id: int = None, taxon: Taxon = None):
        """Update taxon info display"""
        # Don't need to do anything if this taxon is already selected
        id = taxon_id or taxon.id
        if self.selected_taxon is not None and id == self.selected_taxon.id:
            return

        logger.info(f'Selecting taxon {id}')
        start = time()
        if taxon_id and not taxon:
            taxon = INAT_CLIENT.taxa.from_id(taxon_id).one()
        self.selected_taxon = taxon

        common_name = f' ({taxon.preferred_common_name}) ' if taxon.preferred_common_name else ''
        self.selected_taxon_title.setText(f'{taxon.name}{common_name}')

        self.taxon_info.load(taxon)
        self.taxonomy.load(taxon)

        # Clicking on a taxon card will select it
        for card in self.taxonomy.taxon_cards:
            card.clicked.connect(self.select_taxon)
        logger.info(f'Loaded taxon {taxon.id} {time() - start:.2f}s')


class TaxonInfoSection(QHBoxLayout):
    """Section to display selected taxon photo and basic info"""

    def __init__(self):
        super().__init__()

        self.setAlignment(Qt.AlignTop)

        self.image = PixmapLabel()
        self.image.setMinimumWidth(200)
        self.image.setMaximumWidth(400)
        self.addWidget(self.image)

        self.icon = PixmapLabel()
        self.icon.setFixedSize(75, 75)

        self.details = QVBoxLayout()
        self.details.setAlignment(Qt.AlignTop)
        self.details.addWidget(self.icon)
        self.addLayout(self.details)

    def load(self, taxon: Taxon):
        # Photo and iconic taxon icon
        self.image.setPixmap(taxon=taxon)
        self.icon.setPixmap(url=taxon.icon_url)

        # Other attributes
        self.details.addWidget(QLabel(f'ID: {taxon.id}'))
        self.details.addWidget(QLabel(f'Rank: {taxon.rank}'))
        self.details.addWidget(QLabel(f'Observations: {taxon.observations_count}'))
        self.details.addWidget(QLabel(f'Child species: {taxon.complete_species_count}'))


class TaxonomySection(QHBoxLayout):
    """Section to display ancestors and children of selected taxon"""

    def __init__(self):
        super().__init__()

        # Ancestors
        self.ancestors_layout = QVBoxLayout()
        self.ancestors_layout.setAlignment(Qt.AlignTop)
        self.ancestors_group = QGroupBox('Ancestors')
        self.ancestors_group.setFixedWidth(400)
        self.ancestors_group.setFont(H2_FONT)
        self.ancestors_group.setLayout(self.ancestors_layout)
        self.addWidget(self.ancestors_group)

        # Children
        self.children_layout = QVBoxLayout()
        self.children_layout.setAlignment(Qt.AlignTop)
        self.children_group = QGroupBox('Children')
        self.children_group.setFixedWidth(400)
        self.children_group.setFont(H2_FONT)
        self.children_group.setLayout(self.children_layout)
        self.addWidget(self.children_group)

    def load(self, taxon: Taxon):
        """Populate taxon ancestors and children"""
        logger.info(f'Loading {len(taxon.ancestors)} ancestors and {len(taxon.children)} children')

        def get_label(text: str, items: list) -> str:
            return text + (f' ({len(items)})' if items else '')

        # Load ancestors
        self.ancestors_group.setTitle(get_label('Ancestors', taxon.ancestors))
        clear_layout(self.ancestors_layout)
        for t in taxon.ancestors:
            self.ancestors_layout.addWidget(TaxonInfoCard(taxon=t))

        # Load children
        self.children_group.setTitle(get_label('Children', taxon.children))
        clear_layout(self.children_layout)
        for t in taxon.children:
            self.children_layout.addWidget(TaxonInfoCard(taxon=t))

    @property
    def taxon_cards(self) -> Iterator['TaxonInfoCard']:
        for item in self.ancestors_group.children():
            if isinstance(item, TaxonInfoCard):
                yield item
        for item in self.children_group.children():
            if isinstance(item, TaxonInfoCard):
                yield item


class TaxonInfoCard(QWidget):
    clicked = Signal(int)

    def __init__(self, taxon: Taxon):
        super().__init__()
        card_layout = QHBoxLayout()
        self.setLayout(card_layout)
        self.taxon_id = taxon.id
        print('Taxon ID:', self.taxon_id)

        # Image
        img = PixmapLabel(taxon=taxon)
        img.setFixedWidth(75)
        card_layout.addWidget(img)

        # Details
        title = QLabel(taxon.name)
        title.setFont(H2_FONT)
        details_layout = QVBoxLayout()
        card_layout.addLayout(details_layout)
        details_layout.addWidget(title)
        details_layout.addWidget(QLabel(taxon.rank))
        details_layout.addWidget(QLabel(taxon.preferred_common_name))

    def mousePressEvent(self, _):
        """Placeholder to accept mouse press events"""

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.taxon_id)


def clear_layout(layout: QLayout):
    """Why is this not built-in???"""
    if not layout:
        return
    for i in reversed(range(layout.count())):
        child = layout.takeAt(i)
        if child.widget():
            child.widget().deleteLater()
