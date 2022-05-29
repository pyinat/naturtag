from logging import getLogger
from typing import Iterable

from pyinaturalist import Taxon, TaxonCount, TaxonCounts
from PySide6.QtCore import QSize, Qt, QTimer, Signal, Slot
from PySide6.QtWidgets import QLayout, QTabWidget, QWidget

from naturtag.app.style import fa_icon
from naturtag.app.threadpool import ThreadPool
from naturtag.client import INAT_CLIENT
from naturtag.constants import MAX_DISPLAY_OBSERVED
from naturtag.controllers import TaxonInfoSection, TaxonomySection, TaxonSearch
from naturtag.metadata.inat_metadata import get_observed_taxa
from naturtag.settings import Settings, UserTaxa
from naturtag.widgets import HorizontalLayout, TaxonInfoCard, TaxonList, VerticalLayout

logger = getLogger(__name__)


# TODO: Store Taxon.taxon_photos in DB; currently need to fetch this from API each time
# TODO: Collapse tab titles to icons only if not all titles fit
class TaxonController(QWidget):
    """Controller for searching and viewing taxa"""

    on_message = Signal(str)
    on_select = Signal(Taxon)

    def __init__(self, settings: Settings, threadpool: ThreadPool):
        super().__init__()
        self.settings = settings
        self.threadpool = threadpool
        self.user_taxa = UserTaxa.read()

        self.root = HorizontalLayout()
        self.root.setAlignment(Qt.AlignLeft)
        self.setLayout(self.root)
        self.selected_taxon: Taxon = None

        # Search inputs
        self.search = TaxonSearch(settings)
        self.search.autocomplete.on_select.connect(self.select_taxon)
        self.search.on_results.connect(self.set_search_results)
        self.root.addLayout(self.search)

        # Search results & User taxa
        self.tabs = TaxonTabs(threadpool, self.settings, self.user_taxa)
        self.tabs.on_load.connect(self.bind_selection)
        self.root.addWidget(self.tabs)
        self.on_select.connect(self.tabs.update_history)
        self.search.on_reset.connect(self.tabs.results.clear)

        # Selected taxon info
        self.taxon_info = TaxonInfoSection(threadpool)
        self.taxonomy = TaxonomySection(threadpool)
        taxon_layout = VerticalLayout()
        taxon_layout.addLayout(self.taxon_info)
        taxon_layout.addLayout(self.taxonomy)
        self.root.addLayout(taxon_layout)

    def info(self, message: str):
        self.on_message.emit(message)

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
        if self.tabs._init_complete:
            self.threadpool.cancel()
        future = self.threadpool.schedule(lambda: INAT_CLIENT.taxa(taxon_id, refresh=True))
        future.on_result.connect(self.display_taxon)

    def select_observation_taxon(self, observation_id: int):
        """Load a taxon from an observation ID"""
        logger.info(f'Selecting observation {observation_id}')
        self.threadpool.cancel()
        future = self.threadpool.schedule(lambda: INAT_CLIENT.observations(observation_id).taxon)
        future.on_result.connect(self.display_taxon)

    @Slot(Taxon)
    def display_taxon(self, taxon: Taxon):
        self.selected_taxon = taxon
        self.on_select.emit(taxon)
        self.taxon_info.load(self.selected_taxon)
        self.taxonomy.load(self.selected_taxon)
        self.bind_selection(self.taxonomy.ancestors_list.taxa)
        self.bind_selection(self.taxonomy.children_list.taxa)
        logger.debug(f'Loaded taxon {self.selected_taxon.id}')

    def set_search_results(self, taxa: list[Taxon]):
        """Load search results into Results tab"""
        self.tabs.results.set_taxa(taxa)
        self.tabs.setCurrentWidget(self.tabs.results_tab)
        self.bind_selection(self.tabs.results.taxa)

    def bind_selection(self, taxon_cards: Iterable[TaxonInfoCard]):
        """Connect click signal from each taxon card to select_taxon()"""
        for taxon_card in taxon_cards:
            taxon_card.on_click.connect(self.select_taxon)


class TaxonTabs(QTabWidget):
    """Tabbed view for search results and user taxa"""

    on_load = Signal(list)

    def __init__(
        self,
        threadpool: ThreadPool,
        settings: Settings,
        user_taxa: UserTaxa,
        parent: QWidget = None,
    ):
        super().__init__(parent)
        self.setMinimumWidth(200)
        self.setMaximumWidth(510)
        self.setIconSize(QSize(32, 32))
        self.settings = settings
        self.threadpool = threadpool
        self.user_taxa = user_taxa
        self._init_complete = False

        self.results = TaxonList(threadpool)
        self.results_tab = self.add_tab(
            self.results, 'mdi6.layers-search', 'Results', 'Search results'
        )

        self.history = TaxonList(threadpool)
        self.add_tab(self.history, 'fa5s.history', 'History', 'Recently viewed taxa')

        self.frequent = TaxonList(threadpool)
        self.add_tab(self.frequent, 'ri.bar-chart-fill', 'Frequent', 'Frequently viewed taxa')

        self.observed = TaxonList(threadpool)
        self.add_tab(self.observed, 'fa5s.binoculars', 'Observed', 'Taxa observed by you')

        # self.starred = TaxonList(threadpool)
        # self.add_tab(self.starred, 'fa.star', 'Starred', 'Starred taxa')

        # Add a delay before loading user taxa on startup
        QTimer.singleShot(2, self.load_user_taxa)

    def add_tab(self, tab_layout: QLayout, icon_str: str, label: str, tooltip: str) -> QWidget:
        tab = QWidget()
        tab.setLayout(tab_layout)
        idx = super().addTab(tab, fa_icon(icon_str), label)
        self.setTabToolTip(idx, tooltip)
        return tab

    def load_user_taxa(self):
        display_ids = self.user_taxa.display_ids

        def get_history_taxa():
            logger.info(f'Loading {len(display_ids)} user taxa')
            return INAT_CLIENT.taxa.from_ids(*display_ids, accept_partial=True).all()

        future = self.threadpool.schedule(get_history_taxa)
        future.on_result.connect(self.display_history)

        future = self.threadpool.schedule(
            lambda: get_observed_taxa(self.settings.username, self.settings.casual_observations)
        )
        future.on_result.connect(self.display_observed)
        self._init_complete = True

    @Slot(list)
    def display_history(self, taxa: list[Taxon]):
        """After fetching taxon records for history/frequent, add info cards for them in the
        appropriate tabs
        """
        taxa_by_id = {t.id: t for t in taxa}
        self.history.set_taxa([taxa_by_id.get(taxon_id) for taxon_id in self.user_taxa.top_history])
        self.on_load.emit(list(self.history.taxa))

        # Add counts to taxon cards in 'Frequent' tab, for sorting later
        def get_taxon_count(taxon_id: int) -> TaxonCount:
            taxon = TaxonCount.copy(taxa_by_id[taxon_id])
            taxon.count = self.user_taxa.view_count(taxon_id)
            return taxon

        self.frequent.set_taxa(
            [get_taxon_count(taxon_id) for taxon_id in self.user_taxa.top_frequent]
        )
        self.on_load.emit(list(self.frequent.taxa))

    @Slot(list)
    def display_observed(self, taxon_counts: TaxonCounts):
        """After fetching observation taxon counts for the user, add info cards for them"""
        self.observed.set_taxa(list(taxon_counts)[:MAX_DISPLAY_OBSERVED])
        self.user_taxa.update_observed(taxon_counts)
        self.on_load.emit(list(self.observed.taxa))

    @Slot(Taxon)
    def update_history(self, taxon: Taxon):
        """Update history and frequent lists with the selected taxon. If it was already in one or
        both lists, update its position in the list(s).
        """
        self.history.add_or_update(taxon)
        self.user_taxa.update_history(taxon.id)

        idx = self.user_taxa.frequent_idx(taxon.id)
        if idx is not None:
            self.frequent.add_or_update(taxon, idx)
