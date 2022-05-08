from typing import Callable

from pyinaturalist import Taxon
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QVBoxLayout,
    QWidget,
)

from naturtag.app.image_window import PixmapLabel
from naturtag.constants import ASSETS_DIR
from naturtag.settings import Settings
from naturtag.thumbnails import get_thumbnail

PLACEHOLDER_IMG_PATH = str(ASSETS_DIR / 'demo_images' / '78513963.jpg')

header_font = QFont()
header_font.setWeight(QFont.Bold)
header_font.setPointSize(20)


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
        self.info = info_callback

        input_layout = QVBoxLayout()
        root_layout.addLayout(input_layout)
        # root_layout.setAlignment(Qt.AlignTop)

        # Taxon name autocomplete
        autocomplete_layout = QVBoxLayout()
        autocomplete_layout.setAlignment(Qt.AlignTop)
        group_box = QGroupBox('Taxon search')
        group_box.setFixedWidth(400)
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
        group_box.setLayout(categories_layout)
        input_layout.addWidget(group_box)

        categories_layout.addWidget(QLabel('1'))
        categories_layout.addWidget(QLabel('2'))
        categories_layout.addWidget(QLabel('3'))

        # Rank inputs
        rank_layout = QVBoxLayout()
        group_box = QGroupBox('Rank')
        group_box.setFixedWidth(400)
        group_box.setLayout(rank_layout)
        input_layout.addWidget(group_box)

        rank_layout.addWidget(QLabel('1'))
        rank_layout.addWidget(QLabel('2'))
        rank_layout.addWidget(QLabel('3'))

        # -----------------

        # Search results
        results_layout = QVBoxLayout()
        root_layout.addLayout(results_layout)

        selected_taxon_layout = QHBoxLayout()
        selected_taxon_layout.setAlignment(Qt.AlignTop)
        results_layout.addLayout(selected_taxon_layout)
        img = PixmapLabel(path=PLACEHOLDER_IMG_PATH)
        img.setMinimumWidth(200)
        img.setMaximumWidth(400)
        selected_taxon_layout.addWidget(img)

        taxon_details_layout = QVBoxLayout()
        taxon_details_layout.setAlignment(Qt.AlignTop)
        selected_taxon_layout.addLayout(taxon_details_layout)
        taxon_details_layout.addWidget(QLabel('Taxon details'))
        taxon_details_layout.addWidget(QLabel('ID: 47792'))
        taxon_details_layout.addWidget(QLabel('Observations: 730000'))
        taxon_details_layout.addWidget(QLabel('Child species: 6323'))

        taxonomy_layout = QHBoxLayout()
        results_layout.addLayout(taxonomy_layout)

        ancestors_layout = QVBoxLayout()
        ancestors_layout.setAlignment(Qt.AlignTop)
        taxonomy_layout.addLayout(ancestors_layout)
        header = QLabel('Ancestors')
        header.setFont(header_font)
        ancestors_layout.addWidget(header)
        for taxon in ancestors:
            ancestors_layout.addWidget(TaxonInfoCard(taxon=taxon))

        children_layout = QVBoxLayout()
        children_layout.setAlignment(Qt.AlignTop)
        taxonomy_layout.addLayout(children_layout)
        header = QLabel('Children')
        header.setFont(header_font)
        children_layout.addWidget(header)

        for taxon in children:
            children_layout.addWidget(TaxonInfoCard(taxon=taxon))


class TaxonInfoCard(QWidget):
    def __init__(self, taxon: Taxon):
        super().__init__()
        card_layout = QHBoxLayout()
        self.setLayout(card_layout)

        # img = PixmapLabel(path=get_thumbnail(taxon.default_photo.thumbnail_url))
        img = PixmapLabel(path=get_thumbnail(PLACEHOLDER_IMG_PATH))
        img.setFixedWidth(75)
        card_layout.addWidget(img)

        details_layout = QVBoxLayout()
        card_layout.addLayout(details_layout)

        custom_font = QFont()
        custom_font.setWeight(QFont.Bold)
        custom_font.setPointSize(16)
        title = QLabel(taxon.name)
        title.setFont(custom_font)

        details_layout.addWidget(title)
        details_layout.addWidget(QLabel(taxon.rank))
        details_layout.addWidget(QLabel(taxon.preferred_common_name))
