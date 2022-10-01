"""Components for searching for observations"""
from logging import getLogger

from pyinaturalist import Observation
from PySide6.QtCore import Qt

from naturtag.settings import Settings
from naturtag.widgets import VerticalLayout

logger = getLogger(__name__)


class ObservationSearch(VerticalLayout):
    def __init__(self, settings: Settings):
        super().__init__()
        self.selected_observation: Observation = None
        self.settings = settings
        self.setAlignment(Qt.AlignTop)
