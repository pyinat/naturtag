import math
from collections import OrderedDict
from logging import getLogger
from typing import Iterable, Iterator

from attr import define
from pyinaturalist import Observation, Taxon
from PySide6.QtCore import Qt, QThread, QTimer, Signal, Slot
from PySide6.QtWidgets import QLabel, QPushButton

from naturtag.constants import DEFAULT_DISPLAY_PAGE_SIZE, N_DISPLAY_TAXON_THUMBNAILS, PAGE_CACHE_MAX
from naturtag.controllers import BaseController, ObservationInfoSection
from naturtag.widgets import HorizontalLayout, ObservationInfoCard, ObservationList
from naturtag.widgets.style import fa_icon

logger = getLogger(__name__)


@define
class DbPageResult:
    """Container to pass results from a worker thread to UI thread"""

    observations: list[Observation]
    total_results: int
    is_empty: bool


class ObservationController(BaseController):
    on_view_taxon = Signal(Taxon)  #: Request to switch to taxon tab
    on_sync_progress = Signal(int, int)  #: (loaded_count, total_count) as pages arrive
    on_sync_finished = Signal()  #: Emitted when the background sync completes

    def __init__(self):
        super().__init__()
        self.root = HorizontalLayout(self)
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
        self.loaded_obs = 0  # running count of observations received from API during sync
        self._page_cache: OrderedDict[int, list[Observation]] = OrderedDict()
        self._sync_in_progress: bool = False
        self._precache_in_progress: bool = False

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
        self.root.addWidget(self.obs_info)

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
            lambda: self.app.client.observations(observation_id, taxonomy=True, ident_taxa=True),
            priority=QThread.HighPriority,
        )
        future.on_result.connect(self.display_observation)

    def load_observations_from_db(self):
        """Read the current page of observations from the local DB and display them"""
        cached = self._page_cache.get(self.page)
        if cached is not None:
            self._page_cache.move_to_end(self.page)
            self.display_user_observations(cached)
            return
        logger.debug(f'Loading observations from DB (page {self.page})')
        future = self.app.threadpool.schedule(self._get_db_page, priority=QThread.NormalPriority)
        future.on_result.connect(self.on_db_page_loaded)

    def start_background_sync(self):
        """Kick off a background worker to fetch all new/updated observations from the API"""
        self._sync_in_progress = True
        logger.info('Starting background observation sync')
        future = self.app.threadpool.schedule_paginator(
            self._sync_observations,
            priority=QThread.LowPriority,
            total_results=self.total_results or None,
        )
        future.on_result.connect(self.on_sync_page_received)
        future.on_complete.connect(self.on_sync_complete)
        future.on_error.connect(self.on_sync_error_received)

    def next_page(self):
        if self.page < min(self.total_pages, self.loaded_pages):
            self.page += 1
            self.load_observations_from_db()

    def prev_page(self):
        if self.page > 1:
            self.page -= 1
            self.load_observations_from_db()

    def refresh(self):
        if self._sync_in_progress:
            self.info('Refresh already in progress')
            return
        self.page = 1
        self.loaded_pages = 0
        self.loaded_obs = 0
        self._page_cache.clear()
        self.app.state.sync_resume_id = None
        self.load_observations_from_db()
        self.start_background_sync()

    def _start_precache_thumbnails(self, observations: list[Observation]):
        """Schedule thumbnail pre-caching for a single sync page as a low-priority worker."""
        urls = [url for obs in observations for url in self._get_obs_image_urls(obs)]
        if urls:
            self.app.threadpool.schedule(
                lambda: self.app.img_fetcher.precache_image(urls),
                priority=QThread.LowPriority,
            )

    def _start_precache_all_thumbnails(self):
        """Start background pre-caching of all observation thumbnails.
        Used to backfill previously downloaded observations, after selecting the option for the
        first time.
        """
        if self._precache_in_progress:
            logger.debug('Thumbnail pre-cache already in progress; skipping')
            return
        self._precache_in_progress = True
        total = self.total_results or self.app.client.observations.count_db()
        logger.info(f'Starting thumbnail pre-cache for {total} observations')
        future = self.app.threadpool.schedule_paginator(
            self._precache_thumbnails,
            priority=QThread.LowPriority,
            total_results=total or None,
        )
        future.on_finished.connect(self._on_precache_finished)

    def start_precache_when_ready(self):
        """Start thumbnail pre-caching, or defer until sync completes if one is in progress."""
        if self._sync_in_progress:
            logger.debug('Sync in progress; deferring thumbnail pre-cache until sync completes')
            self.on_sync_finished.connect(
                self._start_precache_all_thumbnails,
                Qt.SingleShotConnection,
            )
        else:
            self._start_precache_all_thumbnails()

    # UI helper functions (slots triggered in main thread after workers complete)
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
    def on_db_page_loaded(self, result: DbPageResult):
        """Handle DB page result on the main thread"""
        self._page_cache[self.page] = result.observations
        if len(self._page_cache) > PAGE_CACHE_MAX:
            self._page_cache.popitem(last=False)
        # Use the DB count only if it's higher than previous count; the DB count grows during
        # download and must not overwrite the API-fetched total.
        if result.total_results > self.total_results:
            self.total_results = result.total_results
        self.total_pages = (
            math.ceil(self.total_results / DEFAULT_DISPLAY_PAGE_SIZE) if self.total_results else 0
        )

        if result.is_empty:
            self._is_cold_start = True
            self.user_obs_group_box.set_title('My Observations (loading...)')
        else:
            self._is_cold_start = False
            self.loaded_pages = self.total_pages

        self.display_user_observations(result.observations)

    @Slot(object)
    def on_sync_page_received(self, observations: list[Observation]):
        """Called each time the background sync saves a page to the DB"""
        self.loaded_pages += 1
        logger.debug(f'Sync page {self.loaded_pages} received ({len(observations)} observations)')
        if observations:
            max_id = max(obs.id for obs in observations)
            self.app.state.sync_resume_id = max_id
            self.app.state.write()
        self.loaded_obs += len(observations)
        self.update_pagination_buttons()
        self.on_sync_progress.emit(min(self.loaded_obs, self.total_results), self.total_results)
        if observations and self.app.settings.precache_thumbnails:
            self._start_precache_thumbnails(observations)

        # On cold start, display page 1 once the first sync page arrives.
        # Delay _update_db_counts() until after sync, since DB count is not yet accurate.
        if self._is_cold_start and self.loaded_pages == 1:
            self.load_observations_from_db()

    @Slot(Exception)
    def on_sync_error_received(self, exc: Exception):
        """Called when the background sync fails"""
        logger.warning('Background observation sync failed:', exc_info=exc)
        self._sync_in_progress = False
        if self._is_cold_start:
            self.user_obs_group_box.set_title('My Observations')
        self.info(f'Observation sync failed: {exc}')
        # Remove unfinished progress bar units
        unfinished = max(0, (self.total_results or 1) - self.loaded_obs - 1)
        if unfinished > 0:
            self.app.threadpool.progress.remove(unfinished)

    @Slot()
    def on_sync_complete(self):
        """Called when the background sync finishes"""
        logger.info('Background observation sync complete')
        self._sync_in_progress = False
        self._page_cache.clear()
        self.app.state.sync_resume_id = None
        self.app.state.set_obs_checkpoint()
        self._update_db_counts()
        self.update_pagination_buttons()
        self.load_observations_from_db()
        self.on_sync_finished.emit()

    @Slot()
    def _on_precache_finished(self):
        """Handle completion of thumbnail pre-caching"""
        self._precache_in_progress = False
        logger.info('Thumbnail pre-cache complete')

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
    def _get_db_page(self) -> DbPageResult:
        """Read a single page of observations from the local DB"""
        total_results = self.app.client.observations.count_db()
        if total_results == 0:
            return DbPageResult([], total_results=0, is_empty=True)
        obs = self.app.client.observations.search_user_db(
            username=self.app.settings.username,
            page=self.page,
        )
        return DbPageResult(obs, total_results=total_results, is_empty=False)

    def _update_db_counts(self):
        """Update total_results and total_pages from the DB"""
        self.total_results = self.app.client.observations.count_db()
        self.total_pages = (
            math.ceil(self.total_results / DEFAULT_DISPLAY_PAGE_SIZE) if self.total_results else 0
        )

    def _sync_observations(self) -> Iterator[list[Observation]]:
        """Fetch all new/updated observations from the API, yielding one page at a time"""
        yield from self.app.client.observations.search_user_paginated(
            username=self.app.settings.username,
            updated_since=self.app.state.last_obs_check,
            id_above=self.app.state.sync_resume_id,
        )

    def _get_obs_image_urls(self, obs: Observation) -> list[str]:
        """Return all thumbnail URLs to precache for a single observation.

        Includes the observation default photo at medium size, all observation photos at square
        size, the taxon default photo at medium size, and taxon grid photos at square size.
        """
        urls = []
        if obs.photos:
            urls.append(obs.default_photo.url_size('medium'))
            for photo in obs.photos:
                urls.append(photo.url_size('square'))
        if obs.taxon and obs.taxon.taxon_photos:
            urls.append(obs.taxon.default_photo.url_size('medium'))
            for photo in obs.taxon.taxon_photos[: N_DISPLAY_TAXON_THUMBNAILS + 1]:
                urls.append(photo.url_size('square'))
        return urls

    def _precache_thumbnails(self):
        """Fetch and cache thumbnails for all observations in the DB. Yields after each page.

        Yields the count of observations processed on each page. This allows the PaginatedWorker
        to check for cancellation between pages, providing graceful shutdown during pre-cache.
        """
        username = self.app.settings.username
        for obs_page in self.app.client.observations.search_user_db_paginated(username=username):
            urls = [url for obs in obs_page for url in self._get_obs_image_urls(obs)]
            self.app.img_fetcher.precache_image(urls)
            # Yield after each page to allow cancellation checks in worker
            yield obs_page
