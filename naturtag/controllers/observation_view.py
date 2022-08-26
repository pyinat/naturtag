"""Components for displaying taxon info"""
# TODO: code reuse with taxon_view
import webbrowser
from collections import deque
from logging import getLogger
from typing import Iterator

from pyinaturalist import Observation, Taxon
from PySide6.QtCore import QEvent, Qt, QThread, Signal
from PySide6.QtWidgets import QGroupBox, QPushButton

from naturtag.app.style import fa_icon
from naturtag.app.threadpool import ThreadPool
from naturtag.constants import SIZE_SM
from naturtag.widgets import (
    GridLayout,
    HorizontalLayout,
    ObservationImageWindow,
    ObservationPhoto,
    VerticalLayout,
)

logger = getLogger(__name__)


class ObservationInfoSection(HorizontalLayout):
    """Section to display selected observation photos and info"""

    on_select_obj = Signal(Observation)  #: An observation was selected

    def __init__(self, threadpool: ThreadPool):
        super().__init__()
        self.threadpool = threadpool
        # self.hist_prev: deque[Taxon] = deque()  # Viewing history for current session only
        # self.hist_next: deque[Taxon] = deque()  # Set when loading from history
        # self.history_taxon: Taxon = None  # Set when loading from history, to avoid loops
        self.selected_observation: Observation = None

        self.group_box = QGroupBox('No observation selected')
        root = VerticalLayout(self.group_box)
        images = HorizontalLayout()
        root.addLayout(images)
        self.addWidget(self.group_box)
        self.setAlignment(Qt.AlignTop)

        # Medium default photo
        self.image = ObservationPhoto(hover_icon=True)
        self.image.setFixedHeight(395)  # Height of 5 thumbnails + spacing
        self.image.setAlignment(Qt.AlignTop)
        images.addWidget(self.image)

        # Additional thumbnails
        self.observation_thumbnails = GridLayout(n_columns=2)
        self.observation_thumbnails.setSpacing(5)
        self.observation_thumbnails.setAlignment(Qt.AlignTop)
        images.addLayout(self.observation_thumbnails)

        # Back and Forward buttons: We already have the full Observation object
        # button_layout = HorizontalLayout()
        # root.addLayout(button_layout)
        # self.prev_button = QPushButton('Back')
        # self.prev_button.setIcon(fa_icon('ei.chevron-left'))
        # self.prev_button.clicked.connect(self.prev)
        # self.prev_button.setEnabled(False)
        # button_layout.addWidget(self.prev_button)

        # self.next_button = QPushButton('Forward')
        # self.next_button.setIcon(fa_icon('ei.chevron-right'))
        # self.next_button.clicked.connect(self.next)
        # self.next_button.setEnabled(False)
        # button_layout.addWidget(self.next_button)

        # # Parent button: We need to fetch the full Taxon object, so just pass the ID
        # self.parent_button = QPushButton('Parent')
        # self.parent_button.setIcon(fa_icon('ei.chevron-up'))
        # self.parent_button.clicked.connect(self.select_parent)
        # button_layout.addWidget(self.parent_button)

        # # Link button: Open web browser to taxon info page
        # self.link_button = QPushButton('View on iNaturalist')
        # self.link_button.setIcon(fa_icon('mdi.web', primary=True))
        # self.link_button.clicked.connect(lambda: webbrowser.open(self.selected_observation.url))
        # button_layout.addWidget(self.link_button)

        # Fullscreen image viewer
        self.image_window = ObservationImageWindow()
        self.image.on_click.connect(self.image_window.display_observation_fullscreen)

    def load(self, observation: Observation):
        """Load default photo + additional thumbnails"""
        if self.selected_observation and observation.id == self.selected_observation.id:
            return

        # Append to history, unless we just loaded a taxon from history
        # if self.selected_observation and taxon.id != getattr(self.history_taxon, 'id', None):
        #     self.hist_prev.append(self.selected_observation)
        #     self.hist_next.clear()
        # logger.debug(
        #     f'Navigation: {" ".join([t.name for t in self.hist_prev])} [{taxon.name}] '
        #     f'{" ".join([t.name for t in self.hist_next])}'
        # )

        # Set title and main photo
        self.history_taxon = None
        self.selected_observation = observation
        self.group_box.setTitle(observation.taxon.full_name)
        self.image.observation = observation
        self.image.set_pixmap_async(
            self.threadpool,
            photo=observation.photos[0],  # TODO: add Observation.default_photo in pyinat
            priority=QThread.HighPriority,
        )
        # self._update_nav_buttons()

        # Load additional thumbnails
        self.observation_thumbnails.clear()
        for i, photo in enumerate(observation.photos[1:11] if observation.photos else []):
            thumb = ObservationPhoto(observation=observation, idx=i + 1)
            thumb.setFixedSize(*SIZE_SM)
            thumb.on_click.connect(self.image_window.display_observation_fullscreen)
            thumb.set_pixmap_async(self.threadpool, photo=photo, size='thumbnail')
            self.observation_thumbnails.add_widget(thumb)

    # def prev(self):
    #     if not self.hist_prev:
    #         return
    #     self.history_taxon = self.hist_prev.pop()
    #     self.hist_next.appendleft(self.selected_observation)
    #     self.on_select_obj.emit(self.history_taxon)

    # def next(self):
    #     if not self.hist_next:
    #         return
    #     self.history_taxon = self.hist_next.popleft()
    #     self.hist_prev.append(self.selected_observation)
    #     self.on_select_obj.emit(self.history_taxon)

    def enterEvent(self, event: QEvent):
        self.open_overlay.setVisible(True)
        return super().enterEvent(event)

    def leaveEvent(self, event: QEvent) -> None:
        self.open_overlay.setVisible(False)
        return super().leaveEvent(event)

    def select_observation(self, observation: Observation):
        self.load(observation)
        self.on_select_obj.emit(observation)

    # def _update_nav_buttons(self):
    #     """Update status and tooltip for 'back', 'forward', 'parent', and 'view on iNat' buttons"""
    #     self.prev_button.setEnabled(bool(self.hist_prev))
    #     self.prev_button.setToolTip(self.hist_prev[-1].full_name if self.hist_prev else None)
    #     self.next_button.setEnabled(bool(self.hist_next))
    #     self.next_button.setToolTip(self.hist_next[0].full_name if self.hist_next else None)
    #     self.parent_button.setEnabled(bool(self.selected_observation.parent))
    #     self.parent_button.setToolTip(
    #         self.selected_observation.parent.full_name if self.selected_observation.parent else None
    #     )
    #     self.link_button.setToolTip(self.selected_observation.url)
