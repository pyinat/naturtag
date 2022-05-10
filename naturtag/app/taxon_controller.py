from logging import getLogger
from time import time
from typing import Callable

from pyinaturalist import Taxon
from PySide6.QtCore import Qt
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
from naturtag.constants import ASSETS_DIR
from naturtag.metadata.inat_metadata import INAT_CLIENT
from naturtag.settings import Settings

# from naturtag.thumbnails import get_thumbnail

logger = getLogger(__name__)

PLACEHOLDER_IMG_PATH = str(ASSETS_DIR / 'demo_images' / '78513963.jpg')

HEADER_FONT = QFont()
HEADER_FONT.setWeight(QFont.Bold)
HEADER_FONT.setPointSize(16)


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
        start = time()

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
        group_box.setFont(HEADER_FONT)
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
        group_box.setFont(HEADER_FONT)
        group_box.setLayout(categories_layout)
        input_layout.addWidget(group_box)

        categories_layout.addWidget(QLabel('1'))
        categories_layout.addWidget(QLabel('2'))
        categories_layout.addWidget(QLabel('3'))

        # Rank inputs
        rank_layout = QVBoxLayout()
        group_box = QGroupBox('Rank')
        group_box.setFixedWidth(400)
        group_box.setFont(HEADER_FONT)
        group_box.setLayout(rank_layout)
        input_layout.addWidget(group_box)

        rank_layout.addWidget(QLabel('1'))
        rank_layout.addWidget(QLabel('2'))
        rank_layout.addWidget(QLabel('3'))

        # -----------------

        # Search results
        results_layout = QVBoxLayout()
        root_layout.addLayout(results_layout)

        self.selected_taxon_layout = QHBoxLayout()
        self.selected_taxon_layout.setAlignment(Qt.AlignTop)
        results_layout.addLayout(self.selected_taxon_layout)

        self.selected_taxon_image = PixmapLabel()
        self.selected_taxon_image.setMinimumWidth(200)
        self.selected_taxon_image.setMaximumWidth(400)
        self.selected_taxon_layout.addWidget(self.selected_taxon_image)

        self.taxon_details_layout = QVBoxLayout()
        self.taxon_details_layout.setAlignment(Qt.AlignTop)
        self.selected_taxon_layout.addLayout(self.taxon_details_layout)

        taxonomy_layout = QHBoxLayout()
        results_layout.addLayout(taxonomy_layout)

        # Ancestors
        self.ancestors_layout = QVBoxLayout()
        self.ancestors_layout.setAlignment(Qt.AlignTop)
        self.ancestors_group = QGroupBox('Ancestors')
        self.ancestors_group.setFixedWidth(400)
        self.ancestors_group.setFont(HEADER_FONT)
        self.ancestors_group.setLayout(self.ancestors_layout)
        taxonomy_layout.addWidget(self.ancestors_group)

        # Children
        self.children_layout = QVBoxLayout()
        self.children_layout.setAlignment(Qt.AlignTop)
        self.children_group = QGroupBox('Children')
        self.children_group.setFixedWidth(400)
        self.children_group.setFont(HEADER_FONT)
        self.children_group.setLayout(self.children_layout)
        taxonomy_layout.addWidget(self.children_group)

        test_taxon = INAT_CLIENT.taxa.from_id(47792).one()
        self.select_taxon(test_taxon)
        logger.info(f'Initialized taxon page in {time() - start:.2f}s')

    def select_taxon(self, taxon: Taxon):
        """Update taxon info display"""
        # Don't need to do anything if this taxon is already selected
        if self.selected_taxon is not None and taxon.id == self.selected_taxon.id:
            return

        logger.info(f'Selecting taxon {taxon.id}')
        self.selected_taxon = taxon

        self.load_basic_info()
        self.load_taxonomy()

    def load_basic_info(self):
        """Load taxon photo + basic info"""
        self.selected_taxon_image.setPixmap(taxon=self.selected_taxon)

        # Name, rank
        # item = ThreeLineAvatarIconListItem(
        #     text=self.selected_taxon.name,
        #     secondary_text=self.selected_taxon.rank.title(),
        #     tertiary_text=self.selected_taxon.preferred_common_name,
        # )

        # Icon (if available)
        # icon_path = get_icon_path(self.selected_taxon.iconic_taxon_id)
        # if icon_path:
        #     item.add_widget(ImageLeftWidget(source=icon_path))
        # self.basic_info.add_widget(item)

        # Other attributes
        clear_layout(self.taxon_details_layout)
        self.taxon_details_layout.addWidget(QLabel('Taxon details'))
        self.taxon_details_layout.addWidget(QLabel(f'ID: {self.selected_taxon.id}'))
        self.taxon_details_layout.addWidget(
            QLabel(f'Observations: {self.selected_taxon.observations_count}')
        )
        self.taxon_details_layout.addWidget(
            QLabel(f'Child species: {self.selected_taxon.complete_species_count}')
        )

    def load_taxonomy(self):
        """Populate taxon ancestors and children"""
        logger.info(
            f'Loading {len(self.selected_taxon.ancestors)} ancestors '
            f'and {len(self.selected_taxon.children)} children'
        )

        def get_label(text: str, items: list) -> str:
            return text + (f' ({len(items)})' if items else '')

        # Load ancestors
        self.ancestors_group.setTitle(get_label('Ancestors', self.selected_taxon.ancestors))
        clear_layout(self.ancestors_layout)
        for taxon in self.selected_taxon.ancestors:
            self.ancestors_layout.addWidget(TaxonInfoCard(taxon=taxon))

        # Load children
        self.children_group.setTitle(get_label('Children', self.selected_taxon.children))
        clear_layout(self.children_layout)
        for taxon in self.selected_taxon.children:
            self.children_layout.addWidget(TaxonInfoCard(taxon=taxon))


class TaxonInfoCard(QWidget):
    def __init__(self, taxon: Taxon):
        super().__init__()
        card_layout = QHBoxLayout()
        self.setLayout(card_layout)

        img = PixmapLabel(taxon=taxon)
        img.setFixedWidth(75)
        card_layout.addWidget(img)

        details_layout = QVBoxLayout()
        card_layout.addLayout(details_layout)

        title = QLabel(taxon.name)
        title.setFont(HEADER_FONT)
        details_layout.addWidget(title)
        details_layout.addWidget(QLabel(taxon.rank))
        details_layout.addWidget(QLabel(taxon.preferred_common_name))


def clear_layout(layout: QLayout):
    """Why is this not built-in???"""
    if not layout:
        return
    for i in reversed(range(layout.count())):
        child = layout.takeAt(i)
        if child.widget():
            child.widget().deleteLater()
