from logging import getLogger
from typing import Iterable

from pyinaturalist import Taxon, TaxonCount, TaxonCounts
from PySide6.QtCore import QSize, Qt, QThread, QTimer, Signal, Slot
from PySide6.QtWidgets import QTabWidget, QWidget

from naturtag.app.style import fa_icon
from naturtag.app.threadpool import ThreadPool
from naturtag.client import INAT_CLIENT
from naturtag.constants import MAX_DISPLAY_OBSERVED
from naturtag.controllers import BaseController, TaxonInfoSection, TaxonomySection, TaxonSearch
from naturtag.metadata.inat_metadata import get_observed_taxa
from naturtag.settings import Settings, UserTaxa
from naturtag.widgets import HorizontalLayout, TaxonInfoCard, TaxonList, VerticalLayout

logger = getLogger(__name__)


class TaxonController(BaseController):
    """Controller for searching and viewing taxa"""

    on_select = Signal(Taxon)  #: A taxon was selected

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user_taxa = UserTaxa.read()

        self.root = HorizontalLayout(self)
        self.root.setAlignment(Qt.AlignLeft)
        self.selected_taxon: Taxon = None

        # Search inputs
        self.search = TaxonSearch(self.settings)
        self.search.autocomplete.on_select.connect(self.select_taxon)
        self.search.on_results.connect(self.set_search_results)
        self.on_select.connect(self.search.set_taxon)
        self.root.addLayout(self.search)

        # Search results & user taxa
        self.tabs = TaxonTabs(self.settings, self.threadpool, self.user_taxa)
        self.tabs.on_load.connect(self.bind_selection)
        self.root.addWidget(self.tabs)
        self.on_select.connect(self.tabs.update_history)
        self.search.on_reset.connect(self.tabs.results.clear)

        # Selected taxon info
        self.taxon_info = TaxonInfoSection(self.threadpool)
        self.taxon_info.on_select_id.connect(self.select_taxon)
        self.taxon_info.on_select.connect(self.display_taxon)
        self.taxonomy = TaxonomySection(self.threadpool, self.user_taxa)
        taxon_layout = VerticalLayout()
        taxon_layout.addLayout(self.taxon_info)
        taxon_layout.addLayout(self.taxonomy)
        self.root.addLayout(taxon_layout)

        # Navigation keyboard shortcuts
        self.add_shortcut('Alt+Left', self.taxon_info.prev)
        self.add_shortcut('Alt+Right', self.taxon_info.next)
        self.add_shortcut('Alt+Up', self.taxon_info.select_parent)
        self.add_shortcut('Ctrl+Shift+R', self.search.reset)
        self.add_shortcut('Ctrl+Shift+Enter', self.search.search)

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
        future = self.threadpool.schedule(
            lambda: INAT_CLIENT.taxa(taxon_id), priority=QThread.HighPriority
        )
        future.on_result.connect(lambda taxon: self.display_taxon(taxon))

    @Slot(Taxon)
    def display_taxon(self, taxon: Taxon, notify: bool = True):
        self.selected_taxon = taxon
        if notify:
            self.on_select.emit(taxon)
        self.taxon_info.load(taxon)
        self.taxonomy.load(taxon)
        self.bind_selection(self.taxonomy.ancestors_list.cards)
        self.bind_selection(self.taxonomy.children_list.cards)
        logger.debug(f'Loaded taxon {taxon.id}')

    def set_search_results(self, taxa: list[Taxon]):
        """Load search results into Results tab"""
        if not taxa:
            self.on_message.emit('No results found')
        self.tabs.results.set_taxa(taxa)
        self.tabs.setCurrentWidget(self.tabs.results)
        self.bind_selection(self.tabs.results.cards)

    def bind_selection(self, taxon_cards: Iterable[TaxonInfoCard]):
        """Connect click signal from each taxon card to select_taxon()"""
        for taxon_card in taxon_cards:
            taxon_card.on_click.connect(self.select_taxon)


class TaxonTabs(QTabWidget):
    """Tabbed view for search results and user taxa"""

    on_load = Signal(list)  #: New taxon cards were loaded

    def __init__(
        self,
        settings: Settings,
        threadpool: ThreadPool,
        user_taxa: UserTaxa,
        parent: QWidget = None,
    ):
        super().__init__(parent)
        self.setElideMode(Qt.ElideRight)
        self.setIconSize(QSize(32, 32))
        self.setMinimumWidth(240)
        self.setMaximumWidth(510)
        self.settings = settings
        self.threadpool = threadpool
        self.user_taxa = user_taxa
        self._init_complete = False

        self.results = self.add_tab(
            TaxonList(threadpool, user_taxa), 'mdi6.layers-search', 'Results', 'Search results'
        )
        self.recent = self.add_tab(
            TaxonList(threadpool, user_taxa), 'fa5s.history', 'Recent', 'Recently viewed taxa'
        )
        self.frequent = self.add_tab(
            TaxonList(threadpool, user_taxa),
            'ri.bar-chart-fill',
            'Frequent',
            'Frequently viewed taxa',
        )
        self.observed = self.add_tab(
            TaxonList(threadpool, user_taxa), 'fa5s.binoculars', 'Observed', 'Taxa observed by you'
        )

        # Add a delay before loading user taxa on startup
        QTimer.singleShot(2, self.load_user_taxa)

    def add_tab(self, taxon_list: TaxonList, icon_str: str, label: str, tooltip: str) -> TaxonList:
        idx = super().addTab(taxon_list.scroller, fa_icon(icon_str), label)
        self.setTabToolTip(idx, tooltip)
        return taxon_list

    def load_user_taxa(self):
        display_ids = self.user_taxa.display_ids

        def get_recent_taxa():
            logger.info(f'Loading {len(display_ids)} user taxa')
            return INAT_CLIENT.taxa.from_ids(*display_ids, accept_partial=True).all()

        future = self.threadpool.schedule(get_recent_taxa, priority=QThread.LowPriority)
        future.on_result.connect(self.display_recent)

        future = self.threadpool.schedule(
            lambda: get_observed_taxa(self.settings.username, self.settings.casual_observations),
            priority=QThread.LowPriority,
        )
        future.on_result.connect(self.display_observed)
        self._init_complete = True

    @Slot(list)
    def display_recent(self, taxa: list[Taxon]):
        """After fetching taxon records for recent and frequent, add info cards for them in the
        appropriate tabs
        """
        taxa_by_id = {t.id: t for t in taxa}
        self.recent.set_taxa([taxa_by_id.get(taxon_id) for taxon_id in self.user_taxa.top_history])
        self.on_load.emit(list(self.recent.cards))

        # Add counts to taxon cards in 'Frequent' tab, for sorting later
        def get_taxon_count(taxon_id: int) -> TaxonCount:
            taxon = TaxonCount.copy(taxa_by_id[taxon_id])
            taxon.count = self.user_taxa.view_count(taxon_id)
            return taxon

        self.frequent.set_taxa(
            [get_taxon_count(taxon_id) for taxon_id in self.user_taxa.top_frequent]
        )
        self.on_load.emit(list(self.frequent.cards))

    @Slot(list)
    def display_observed(self, taxon_counts: TaxonCounts):
        """After fetching observation taxon counts for the user, add info cards for them"""
        self.observed.set_taxa(list(taxon_counts)[:MAX_DISPLAY_OBSERVED])
        self.user_taxa.update_observed(taxon_counts)
        self.on_load.emit(list(self.observed.cards))

    @Slot(Taxon)
    def update_history(self, taxon: Taxon):
        """Update history and frequent lists with the selected taxon. If it was already in one or
        both lists, update its position in the list(s).
        """
        new_cards = []
        self.user_taxa.update_history(taxon.id)
        if card := self.recent.add_or_update_taxon(taxon):
            new_cards.append(card)

        idx = self.user_taxa.frequent_idx(taxon.id)
        if idx is not None:
            if card := self.frequent.add_or_update_taxon(taxon, idx):
                new_cards.append(card)

        if new_cards:
            self.on_load.emit(new_cards)

    def resizeEvent(self, event):
        """On resize, show tab labels if there is enough room for at least a couple characters each
        (plus '...'), otherwise collapse to icons only
        """
        super().resizeEvent(event)
        if self.width() > (90 * self.count()):
            self.setTabText(self.indexOf(self.results.scroller), 'Results')
            self.setTabText(self.indexOf(self.recent.scroller), 'Recent')
            self.setTabText(self.indexOf(self.frequent.scroller), 'Frequent')
            self.setTabText(self.indexOf(self.observed.scroller), 'Observed')
        else:
            for tab_idx in range(self.count()):
                self.setTabText(tab_idx, '')
