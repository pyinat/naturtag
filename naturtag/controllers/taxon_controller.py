from logging import getLogger
from time import time
from typing import Union

from pyinaturalist import Taxon
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QWidget

from naturtag.controllers.taxon_search import TaxonSearch
from naturtag.controllers.taxon_view import TaxonInfoSection, TaxonList, TaxonomySection
from naturtag.metadata import INAT_CLIENT
from naturtag.settings import Settings
from naturtag.widgets import HorizontalLayout, VerticalLayout

logger = getLogger(__name__)


class TaxonController(QWidget):
    """Controller for searching and viewing taxa"""

    message = Signal(str)
    selection = Signal(Taxon)

    def __init__(self, settings: Settings):
        super().__init__()
        self.settings = settings
        root_layout = HorizontalLayout()
        root_layout.setAlignment(Qt.AlignLeft)
        self.setLayout(root_layout)
        self.selected_taxon: Taxon = None

        # Search inputs
        self.search = TaxonSearch(settings)
        self.search.autocomplete.selection.connect(self.select_taxon)
        self.search.new_results.connect(self.bind_selection)
        root_layout.addLayout(self.search)

        # Debug
        shortcut = QShortcut(QKeySequence('F9'), self)
        shortcut.activated.connect(
            lambda: logger.info(self.search.category_filters.selected_iconic_taxa)
        )

        # Selected taxon info
        self.taxon_info = TaxonInfoSection()
        self.taxonomy = TaxonomySection()
        taxon_layout = VerticalLayout()
        taxon_layout.addLayout(self.taxon_info)
        taxon_layout.addLayout(self.taxonomy)
        root_layout.addLayout(taxon_layout)

        self.select_taxon(47792)

    def info(self, message: str):
        self.message.emit(message)

    def select_taxon(self, taxon_id: int = None, taxon: Taxon = None):
        """Update taxon info display"""
        # Don't need to do anything if this taxon is already selected
        id = taxon_id or getattr(taxon, 'id', None)
        if self.selected_taxon and self.selected_taxon.id == id:
            return

        # Fetch taxon record if not already done
        logger.info(f'Selecting taxon {id}')
        start = time()
        if taxon_id and not taxon:
            taxon = INAT_CLIENT.taxa(taxon_id)
        assert taxon is not None
        self.selected_taxon = taxon
        self.selection.emit(taxon)

        self.taxon_info.load(taxon)
        self.taxonomy.load(taxon)
        self.bind_selection(self.taxonomy)
        logger.debug(f'Loaded taxon {taxon.id} in {time() - start:.2f}s')

    def bind_selection(self, taxon_list: Union[TaxonomySection, TaxonList]):
        """Connect click signal from each taxon in a list to select_taxon()"""
        for taxon_card in taxon_list.taxa:
            taxon_card.clicked.connect(self.select_taxon)
