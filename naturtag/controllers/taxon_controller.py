from logging import getLogger
from typing import Iterable

from pyinaturalist import Taxon
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtWidgets import QTabWidget, QWidget

from naturtag.app.style import fa_icon
from naturtag.app.threadpool import ThreadPool
from naturtag.controllers.taxon_search import TaxonSearch
from naturtag.controllers.taxon_view import TaxonInfoCard, TaxonInfoSection, TaxonList, TaxonomySection
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
        self.search = TaxonSearch(settings)
        self.search.autocomplete.selection.connect(self.select_taxon)
        self.search.new_results.connect(self.set_search_results)
        self.root.addLayout(self.search)

        # Search results & User taxa
        self.tabs = TaxonTabs(threadpool)
        self.root.addWidget(self.tabs)
        self.search.reset_results.connect(self.tabs.results.clear)

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

    def select_observation_taxon(self, observation_id: int):
        """Load a taxon from an observation ID"""
        logger.info(f'Selecting observation {observation_id}')
        self.threadpool.cancel()
        future = self.threadpool.schedule(lambda: INAT_CLIENT.observations(observation_id).taxon)
        future.result.connect(self.display_taxon)

    @Slot(Taxon)
    def display_taxon(self, taxon: Taxon):
        self.selected_taxon = taxon
        self.selection.emit(taxon)
        self.taxon_info.load(self.selected_taxon)
        self.taxonomy.load(self.selected_taxon)
        self.bind_selection(self.taxonomy.ancestors_list.taxa)
        self.bind_selection(self.taxonomy.children_list.taxa)
        logger.debug(f'Loaded taxon {self.selected_taxon.id}')

    def set_search_results(self, taxa: list[Taxon]):
        """Load search results into Results tab"""
        self.tabs.results.set_taxa(taxa)
        self.bind_selection(self.tabs.results.taxa)
        self.tabs.setCurrentWidget(self.tabs.results_tab)

    def bind_selection(self, taxon_cards: Iterable[TaxonInfoCard]):
        """Connect click signal from each taxon card to select_taxon()"""
        for taxon_card in taxon_cards:
            taxon_card.clicked.connect(self.select_taxon)


class TaxonTabs(QTabWidget):
    """Tabbed view for search results and user taxa"""

    def __init__(self, threadpool: ThreadPool, parent: QWidget = None):
        super().__init__(parent)

        self.setMinimumWidth(200)
        self.setMaximumWidth(410)

        self.results_tab = QWidget()
        self.results = TaxonList(threadpool, self.results_tab)
        self.results.add_taxon(INAT_CLIENT.taxa(1))
        self.addTab(self.results_tab, fa_icon('mdi6.layers-search'), 'Results')
