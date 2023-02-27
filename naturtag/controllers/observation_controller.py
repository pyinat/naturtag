from logging import getLogger
from typing import Iterable

from pyinaturalist import Observation
from PySide6.QtCore import Qt, QThread, QTimer, Signal, Slot

from naturtag.client import INAT_CLIENT
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

        # Selected observation info
        self.obs_info = ObservationInfoSection(self.threadpool)
        self.obs_info.on_select.connect(self.display_observation)
        obs_layout = VerticalLayout()
        obs_layout.addLayout(self.obs_info)
        self.root.addLayout(obs_layout)

        # Add a delay before loading user observations on startup
        QTimer.singleShot(1, self.load_user_observations)

    def select_observation(self, observation_id: int):
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

    def load_user_observations(self):
        logger.info('Fetching user observations')
        future = self.threadpool.schedule(self.get_user_observations, priority=QThread.LowPriority)
        future.on_result.connect(self.display_user_observations)

    # TODO: Paginate results
    def get_user_observations(self) -> list[Observation]:
        if not self.settings.username:
            return []
        observations = INAT_CLIENT.observations.get_user_observations(
            username=self.settings.username,
            updated_since=self.settings.last_obs_check,
            limit=50,
        )
        self.settings.set_obs_checkpoint()
        return observations

    @Slot(list)
    def display_user_observations(self, observations: list[Observation]):
        self.user_observations.set_observations(observations)
        self.bind_selection(self.user_observations.cards)

    def bind_selection(self, obs_cards: Iterable[ObservationInfoCard]):
        """Connect click signal from each observation card"""
        for obs_card in obs_cards:
            obs_card.on_click.connect(self.select_observation)
