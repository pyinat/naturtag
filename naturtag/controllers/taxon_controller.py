from logging import getLogger
from typing import Union

from pyinaturalist import Taxon
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtWidgets import QWidget

from naturtag.app.threadpool import ThreadPool
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

    def __init__(self, settings: Settings, threadpool: ThreadPool):
        super().__init__()
        self.settings = settings
        self.threadpool = threadpool
        self.root_plus_progress = VerticalLayout()
        self.root = HorizontalLayout()
        self.root.setAlignment(Qt.AlignLeft)
        self.root_plus_progress.addLayout(self.root)
        self.root_plus_progress.addWidget(self.threadpool.progress)
        self.setLayout(self.root_plus_progress)
        self.selected_taxon: Taxon = None

        # Search inputs
        self.search = TaxonSearch(settings, threadpool)
        self.search.autocomplete.selection.connect(self.select_taxon)
        self.search.new_results.connect(self.bind_selection)
        self.root.addLayout(self.search)

        # Selected taxon info
        self.taxon_info = TaxonInfoSection(threadpool)
        self.taxonomy = TaxonomySection(threadpool)
        taxon_layout = VerticalLayout()
        taxon_layout.addLayout(self.taxon_info)
        taxon_layout.addLayout(self.taxonomy)
        self.root.addLayout(taxon_layout)

        # Testing
        self.select_taxon(47792)

    def info(self, message: str):
        self.message.emit(message)

    def select_taxon(self, taxon_id: int):
        """Load a taxon by ID and update info display. Taxon API request will be sent from a
        separate thread, return to main thread, and then display info will be loaded from a separate
        thread.
        """
        # Don't need to do anything if this taxon is already selected
        if self.selected_taxon and self.selected_taxon.id == taxon_id:
            return

        # Fetch taxon record
        logger.info(f'Selecting taxon {taxon_id}')
        self.threadpool.cancel()
        future = self.threadpool.schedule(lambda: INAT_CLIENT.taxa(taxon_id))
        future.result.connect(self.display_taxon)

    @Slot(Taxon)
    def display_taxon(self, taxon: Taxon):
        self.selected_taxon = taxon
        self.selection.emit(taxon)
        self.taxon_info.load(self.selected_taxon)
        self.taxonomy.load(self.selected_taxon)
        self.bind_selection(self.taxonomy)
        logger.debug(f'Loaded taxon {self.selected_taxon.id}')

    def bind_selection(self, taxon_list: Union[TaxonomySection, TaxonList]):
        """Connect click signal from each taxon in a list to select_taxon()"""
        for taxon_card in taxon_list.taxa:
            taxon_card.clicked.connect(self.select_taxon)
