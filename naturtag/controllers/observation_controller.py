import math
from logging import getLogger
from typing import Iterable, Iterator

from pyinaturalist import Observation, Taxon
from PySide6.QtCore import Qt, QThread, QTimer, Signal, Slot
from PySide6.QtWidgets import QLabel, QPushButton

from naturtag.constants import DEFAULT_PAGE_SIZE
from naturtag.controllers import BaseController, ObservationInfoSection
from naturtag.widgets import HorizontalLayout, ObservationInfoCard, ObservationList, VerticalLayout
from naturtag.widgets.style import fa_icon

logger = getLogger(__name__)


class ObservationController(BaseController):
    on_view_taxon = Signal(Taxon)  #: Request to switch to taxon tab

    def __init__(self):
        super().__init__()
        self.root = HorizontalLayout(self)
        self.root.setAlignment(Qt.AlignLeft)
        self.displayed_observation: Observation = None

        # Search inputs
        # self.search = ObservationSearch(self.app.settings)
        # self.search.autocomplete.on_select.connect(self.select_taxon)
        # self.search.on_results.connect(self.set_search_results)
        # self.on_select.connect(self.search.set_taxon)
        # self.root.addLayout(self.search)

        # Pagination
        self.page = 1
        self.total_pages = 0
        self.total_results = 0
        self.loaded_pages = 0
        # TODO: Cache pages while navigating back and forth?
        # self.pages: dict[int, list[ObservationInfoCard]] = {}

        # User observations
        self.user_observations = ObservationList()
        self.user_obs_group_box = self.add_group(
            'My Observations',
            self.root,
            min_width=500,
            max_width=800,
            policy_min_height=False,
        )
        self.user_obs_group_box.addWidget(self.user_observations.scroller)

        # Pagination buttons + label
        button_layout = HorizontalLayout()
        self.user_obs_group_box.addLayout(button_layout)
        self.prev_button = QPushButton('Prev')
        self.prev_button.setIcon(fa_icon('ei.chevron-left'))
        self.prev_button.clicked.connect(self.prev_page)
        self.prev_button.setEnabled(False)
        button_layout.addWidget(self.prev_button)

        self.page_label = QLabel('Page 1  / ?')
        self.page_label.setAlignment(Qt.AlignCenter)
        button_layout.addWidget(self.page_label)

        self.next_button = QPushButton('Next')
        self.next_button.setIcon(fa_icon('ei.chevron-right'))
        self.next_button.clicked.connect(self.next_page)
        self.next_button.setEnabled(False)
        button_layout.addWidget(self.next_button)

        # Full observation info viewer
        self.obs_info = ObservationInfoSection()
        obs_layout = VerticalLayout()
        obs_layout.addLayout(self.obs_info)
        self.root.addLayout(obs_layout)

        # Navigation keyboard shortcuts
        self.add_shortcut('Ctrl+Left', self.prev_page)
        self.add_shortcut('Ctrl+Right', self.next_page)

        # On startup: display from DB first, then sync in background
        self._is_cold_start = False
        QTimer.singleShot(1, self._startup)

    def _startup(self):
        """Two-phase startup: display cached DB data, then sync from API"""
        if not self.app.settings.username:
            logger.info('Unknown user; skipping observation load')
            return
        self.load_observations_from_db()
        self.start_background_sync()

    # Actions triggered directly by UI
    # ----------------------------------------

    def display_observation_by_id(self, observation_id: int):
        """Display full observation details"""
        # Don't need to do anything if this observation is already displayed
        if self.displayed_observation and self.displayed_observation.id == observation_id:
            return

        logger.info(f'Loading observation {observation_id}')
        future = self.app.threadpool.schedule(
            lambda: self.app.client.observations(observation_id, taxonomy=True),
            priority=QThread.HighPriority,
        )
        future.on_result.connect(self.display_observation)

    def load_observations_from_db(self):
        """Read the current page of observations from the local DB and display them"""
        logger.info(f'Loading observations from DB (page {self.page})')
        future = self.app.threadpool.schedule(self._get_db_page, priority=QThread.NormalPriority)
        future.on_result.connect(self.display_user_observations)

    def start_background_sync(self):
        """Kick off a background worker to fetch all new/updated observations from the API"""
        logger.info('Starting background observation sync')
        future = self.app.threadpool.schedule_paginator(
            self._sync_observations,
            priority=QThread.LowPriority,
        )
        future.on_result.connect(self.on_sync_page_received)
        future.on_complete.connect(self.on_sync_complete)

    def next_page(self):
        if self.page < min(self.total_pages, self.loaded_pages):
            self.page += 1
            self.load_observations_from_db()

    def prev_page(self):
        if self.page > 1:
            self.page -= 1
            self.load_observations_from_db()

    def refresh(self):
        self.page = 1
        self.load_observations_from_db()
        self.start_background_sync()

    # UI helper functions (slots triggered after worker threads complete)
    # ----------------------------------------

    @Slot(Observation)
    def display_observation(self, observation: Observation):
        """Display full details for a single observation"""
        self.displayed_observation = observation
        self.obs_info.load(observation)
        logger.debug(f'Loaded observation {observation.id}')

    @Slot(list)
    def display_user_observations(self, observations: list[Observation]):
        """Display a page of observations"""
        self.user_observations.set_observations(observations)
        self.bind_selection(self.user_observations.cards)
        self.update_pagination_buttons()
        if self.total_results:
            self.user_obs_group_box.set_title(f'My Observations ({self.total_results})')
        self.info('')

    @Slot(object)
    def on_sync_page_received(self, observations: list[Observation]):
        """Called each time the background sync saves a page to the DB"""
        self.loaded_pages += 1
        logger.debug(f'Sync page {self.loaded_pages} received ({len(observations)} observations)')
        self.update_pagination_buttons()

        # On cold start, auto-display page 1 once the first sync page arrives
        if self._is_cold_start and self.loaded_pages == 1:
            self._update_db_counts()
            self.load_observations_from_db()

    @Slot()
    def on_sync_complete(self):
        """Called when the background sync finishes"""
        logger.info('Background observation sync complete')
        self.app.state.set_obs_checkpoint()
        self._update_db_counts()
        self.update_pagination_buttons()

    def bind_selection(self, obs_cards: Iterable[ObservationInfoCard]):
        """Connect click signal from each observation card"""
        for obs_card in obs_cards:
            obs_card.on_click.connect(self.display_observation_by_id)

    def update_pagination_buttons(self):
        """Update pagination buttons, gating 'next' on pages that have been loaded"""
        self.prev_button.setEnabled(self.page > 1)
        self.next_button.setEnabled(self.page < min(self.total_pages, self.loaded_pages))
        self.page_label.setText(f'Page {self.page} / {self.total_pages}')

    # I/O bound functions run from worker threads
    # ----------------------------------------

    # TODO: Handle casual_observations setting?
    def _get_db_page(self) -> list[Observation]:
        """Read a single page of observations from the local DB"""
        self._update_db_counts()

        if self.total_results == 0:
            self._is_cold_start = True
            self.user_obs_group_box.set_title('My Observations (loading...)')
            return []

        self._is_cold_start = False
        self.loaded_pages = self.total_pages
        return self.app.client.observations.search_user_db(
            username=self.app.settings.username,
            page=self.page,
        )

    def _update_db_counts(self):
        """Update total_results and total_pages from the DB"""
        self.total_results = self.app.client.observations.count_db()
        self.total_pages = (
            math.ceil(self.total_results / DEFAULT_PAGE_SIZE) if self.total_results else 0
        )

    def _sync_observations(self) -> Iterator[list[Observation]]:
        """Fetch all new/updated observations from the API, yielding one page at a time"""
        yield from self.app.client.observations.search_user_paginated(
            username=self.app.settings.username,
            updated_since=self.app.state.last_obs_check,
        )
