from logging import getLogger
from typing import Iterable

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

        # Add a delay before loading user observations on startup
        QTimer.singleShot(1, self.load_user_observations)

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

    def load_user_observations(self):
        """Fetch and display a single page of user observations"""
        if not self.app.settings.username:
            logger.info('Unknown user; skipping observation load')
            return

        self.info('Fetching user observations')
        future = self.app.threadpool.schedule(
            self.get_user_observations, priority=QThread.LowPriority
        )
        future.on_result.connect(self.display_user_observations)

    def next_page(self):
        if self.page < self.total_pages:
            self.page += 1
            self.load_user_observations()

    def prev_page(self):
        if self.page > 1:
            self.page -= 1
            self.load_user_observations()

    def refresh(self):
        self.page = 1
        self.load_user_observations()

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

    def bind_selection(self, obs_cards: Iterable[ObservationInfoCard]):
        """Connect click signal from each observation card"""
        for obs_card in obs_cards:
            obs_card.on_click.connect(self.display_observation_by_id)

    def update_pagination_buttons(self):
        """Update pagination buttons based on current page"""
        self.prev_button.setEnabled(self.page > 1)
        self.next_button.setEnabled(self.page < self.total_pages)
        self.page_label.setText(f'Page {self.page} / {self.total_pages}')

    # I/O bound functions run from worker threads
    # ----------------------------------------

    # TODO: Handle casual_observations setting?
    # TODO: Store a Paginator object instead of page number?
    def get_user_observations(self) -> list[Observation]:
        """Fetch a single page of user observations"""
        # TODO: Depending on order of operations, this could be counted from the db instead of API.
        # Maybe do that except on initial observation load?
        self.total_results = self.app.client.observations.count(username=self.app.settings.username)
        self.total_pages = (self.total_results // DEFAULT_PAGE_SIZE) + 1
        logger.debug(
            'Total user observations: %s (%s pages)',
            self.total_results,
            self.total_pages,
        )

        observations = self.app.client.observations.get_user_observations(
            username=self.app.settings.username,
            updated_since=self.app.state.last_obs_check,
            limit=DEFAULT_PAGE_SIZE,
            page=self.page,
        )
        self.app.state.set_obs_checkpoint()
        return observations
