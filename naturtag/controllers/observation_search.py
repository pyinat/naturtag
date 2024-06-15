"""Components for searching for observations"""

from logging import getLogger

from pyinaturalist import Observation
from PySide6.QtCore import Qt

from naturtag.widgets import VerticalLayout

logger = getLogger(__name__)


class ObservationSearch(VerticalLayout):
    def __init__(self):
        super().__init__()
        self.selected_observation: Observation = None
        self.setAlignment(Qt.AlignTop)
