from logging import getLogger
from typing import Iterable

from pyinaturalist import Observation
from PySide6.QtCore import Qt, QThread, QTimer, Signal, Slot
from PySide6.QtWidgets import QLabel, QPushButton

from naturtag.app.style import fa_icon
from naturtag.client import INAT_CLIENT
from naturtag.constants import DEFAULT_PAGE_SIZE
from naturtag.controllers import BaseController, ObservationInfoSection
from naturtag.widgets import HorizontalLayout, ObservationInfoCard, ObservationList, VerticalLayout

logger = getLogger(__name__)


class ObservationController(BaseController):
    on_select = Signal(Observation)  #: An observation was selected

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.root = HorizontalLayout(self)
        self.root.setAlignment(Qt.AlignLeft)
        self.selected_observation: Observation = None

        # Search inputs
        # self.search = ObservationSearch(self.settings)
        # self.search.autocomplete.on_select.connect(self.select_taxon)
        # self.search.on_results.connect(self.set_search_results)
        # self.on_select.connect(self.search.set_taxon)
        # self.root.addLayout(self.search)

        # Pagination
        self.page = 1
        self.total_pages = 0
        # TODO: Cache pages while navigating back and forth?
        # self.pages: dict[int, list[ObservationInfoCard]] = {}

        # User observations
        self.user_observations = ObservationList(self.threadpool)
        user_obs_group_box = self.add_group(
            'My Observations',
            self.root,
            min_width=500,
            max_width=800,
            policy_min_height=False,
        )
        user_obs_group_box.addWidget(self.user_observations.scroller)

        # Pagination buttons + label
        button_layout = HorizontalLayout()
        user_obs_group_box.addLayout(button_layout)
        self.prev_button = QPushButton('Prev')
        self.prev_button.setIcon(fa_icon('ei.chevron-left'))
        self.prev_button.clicked.connect(self.get_prev_page)
        self.prev_button.setEnabled(False)
        button_layout.addWidget(self.prev_button)

        self.page_label = QLabel('Page 1  / ?')
        self.page_label.setAlignment(Qt.AlignCenter)
        button_layout.addWidget(self.page_label)

        self.next_button = QPushButton('Next')
        self.next_button.setIcon(fa_icon('ei.chevron-right'))
        self.next_button.clicked.connect(self.get_next_page)
        self.next_button.setEnabled(False)
        button_layout.addWidget(self.next_button)

        # Selected observation info
        self.obs_info = ObservationInfoSection(self.threadpool)
        self.obs_info.on_select.connect(self.display_observation)
        obs_layout = VerticalLayout()
        obs_layout.addLayout(self.obs_info)
        self.root.addLayout(obs_layout)

        # Add a delay before loading user observations on startup
        QTimer.singleShot(1, self.load_user_observations)

    def select_observation(self, observation_id: int):
        """Select an observation to display full details"""
        # Don't need to do anything if this observation is already selected
        if self.selected_observation and self.selected_observation.id == observation_id:
            return

        logger.info(f'Selecting observation {observation_id}')
        future = self.threadpool.schedule(
            lambda: INAT_CLIENT.observations(observation_id, taxonomy=True),
            priority=QThread.HighPriority,
        )
        future.on_result.connect(self.display_observation)

    @Slot(Observation)
    def display_observation(self, observation: Observation):
        self.selected_observation = observation
        self.on_select.emit(observation)
        self.obs_info.load(observation)
        logger.debug(f'Loaded observation {observation.id}')

    @Slot(list)
    def display_user_observations(self, observations: list[Observation]):
        # Update observation list
        self.user_observations.set_observations(observations)
        self.bind_selection(self.user_observations.cards)

        # Update pagination buttons based on current page
        self.prev_button.setEnabled(self.page > 1)
        self.next_button.setEnabled(self.page < self.total_pages)
        self.page_label.setText(f'Page {self.page} / {self.total_pages}')

    def load_user_observations(self):
        logger.info('Fetching user observations')
        future = self.threadpool.schedule(self.get_user_observations, priority=QThread.LowPriority)
        future.on_result.connect(self.display_user_observations)

    # TODO: Handle casual_observations setting
    # TODO: Store a Paginator object instead of page number?
    def get_user_observations(self) -> list[Observation]:
        if not self.settings.username:
            return []

        updated_since = self.settings.last_obs_check
        self.settings.set_obs_checkpoint()

        # TODO: Depending on order of operations, this could be counted from the db instead of API.
        # Maybe do that except on initial observation load?
        if not self.total_pages:
            total_results = INAT_CLIENT.observations.count(username=self.settings.username)
            self.total_pages = (total_results // DEFAULT_PAGE_SIZE) + 1
            logger.info('Total user observations: %s (%s pages)', total_results, self.total_pages)

        observations = INAT_CLIENT.observations.get_user_observations(
            username=self.settings.username,
            updated_since=updated_since,
            limit=DEFAULT_PAGE_SIZE,
            page=self.page,
        )
        return observations

    def get_next_page(self):
        if self.page < self.total_pages:
            self.page += 1
            self.load_user_observations()

    def get_prev_page(self):
        if self.page > 1:
            self.page -= 1
            self.load_user_observations()

    def refresh(self):
        self.page = 1
        self.total_pages = 1
        self.load_user_observations()

    def bind_selection(self, obs_cards: Iterable[ObservationInfoCard]):
        """Connect click signal from each observation card"""
        for obs_card in obs_cards:
            obs_card.on_click.connect(self.select_observation)
