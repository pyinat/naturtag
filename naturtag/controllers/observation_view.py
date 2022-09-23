"""Components for displaying taxon info"""
# TODO: code reuse with taxon_view
# TODO: nav history
import webbrowser
from collections import deque
from logging import getLogger

from pyinaturalist import Observation
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import QGroupBox, QLabel, QPushButton

from naturtag.app.style import fa_icon
from naturtag.app.threadpool import ThreadPool
from naturtag.constants import SIZE_SM
from naturtag.widgets import (
    GridLayout,
    HorizontalLayout,
    IconLabelList,
    ObservationImageWindow,
    ObservationPhoto,
    VerticalLayout,
)
from naturtag.widgets.observation_images import GEOPRIVACY_ICONS, QUALITY_GRADE_ICONS

logger = getLogger(__name__)


class ObservationInfoSection(HorizontalLayout):
    """Section to display selected observation photos and info"""

    on_select = Signal(Observation)  #: An observation was selected

    def __init__(self, threadpool: ThreadPool):
        super().__init__()
        self.threadpool = threadpool
        self.hist_prev: deque[Observation] = deque()  # Viewing history for current session only
        self.hist_next: deque[Observation] = deque()  # Set when loading from history
        self.history_observation: Observation = None  # Set when loading from history, to avoid loop
        self.selected_observation: Observation = None

        self.group_box = QGroupBox('No observation selected')
        self.setAlignment(Qt.AlignTop)
        root = VerticalLayout(self.group_box)
        root.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        images = HorizontalLayout()
        images.setAlignment(Qt.AlignTop)
        root.addLayout(images)
        self.addWidget(self.group_box)

        # Medium default photo
        self.image = ObservationPhoto(hover_icon=True)
        self.image.setMaximumHeight(395)  # Height of 5 thumbnails + spacing
        self.image.setAlignment(Qt.AlignTop)
        images.addWidget(self.image)

        # Additional thumbnails
        self.thumbnails = GridLayout(n_columns=2)
        self.thumbnails.setSpacing(5)
        self.thumbnails.setAlignment(Qt.AlignTop)
        images.addLayout(self.thumbnails)

        # Selected observation details
        self.description = QLabel()
        self.description.setWordWrap(True)
        self.description.setMaximumWidth(500)
        self.details = IconLabelList()
        details_container = VerticalLayout()
        details_container.addWidget(self.description)
        details_container.addWidget(self.details)
        root.addLayout(details_container)

        # Back and Forward buttons: We already have the full Observation object
        button_layout = HorizontalLayout()
        root.addLayout(button_layout)
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
        self.link_button = QPushButton('View on iNaturalist')
        self.link_button.setIcon(fa_icon('mdi.web', primary=True))
        self.link_button.clicked.connect(lambda: webbrowser.open(self.selected_observation.uri))
        self.link_button.setEnabled(False)
        button_layout.addWidget(self.link_button)

        # Fullscreen image viewer
        self.image_window = ObservationImageWindow()
        self.image.on_click.connect(self.image_window.display_observation_fullscreen)

    def load(self, obs: Observation):
        """Load default photo + additional thumbnails"""
        if self.selected_observation and obs.id == self.selected_observation.id:
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
        self.selected_observation = obs
        self.group_box.setTitle(obs.taxon.full_name)
        self.image.observation = obs
        self.image.set_pixmap_async(
            self.threadpool,
            photo=obs.photos[0],  # TODO: add Observation.default_photo in pyinat
            priority=QThread.HighPriority,
        )
        self._update_nav_buttons()

        # Load additional thumbnails
        self.thumbnails.clear()
        for i, photo in enumerate(obs.photos[1:11] if obs.photos else []):
            thumb = ObservationPhoto(observation=obs, idx=i + 1)
            thumb.setFixedSize(*SIZE_SM)
            thumb.on_click.connect(self.image_window.display_observation_fullscreen)
            thumb.set_pixmap_async(self.threadpool, photo=photo, size='thumbnail')
            self.thumbnails.addWidget(thumb)

        # Load observation details
        # TODO: code reuse with ObservationInfoCard
        # TODO: Format description in text box with border
        observed_date_str = (
            obs.observed_on.strftime('%Y-%m-%d %H:%M:%S') if obs.observed_on else 'unknown date'
        )
        created_date_str = (
            obs.created_at.strftime('%Y-%m-%d %H:%M:%S') if obs.observed_on else 'unknown date'
        )
        num_ids = obs.identifications_count or len(obs.identifications)
        quality_str = obs.quality_grade.replace('_', ' ').title()
        self.description.setText(obs.description)

        self.details.clear()
        self.details.add_line('fa5.calendar-alt', f'<b>Observed on:</b> {observed_date_str}')
        self.details.add_line('fa5.calendar-alt', f'<b>Submitted on:</b> {created_date_str}')
        self.details.add_line(
            'mdi.marker-check',
            f'<b>Identifications:</b> {num_ids} ({obs.num_identification_agreements or 0} agree)',
        )

        self.details.add_line(
            QUALITY_GRADE_ICONS.get(obs.quality_grade, 'mdi.chevron-up'),
            f'<b>Quality grade:</b> {quality_str}',
        )
        self.details.add_line(
            'mdi.map-marker',
            f'<b>Location:</b> {obs.private_place_guess or obs.place_guess}',
        )
        self.details.add_line(
            GEOPRIVACY_ICONS.get(obs.geoprivacy, 'mdi.map-marker'),
            f'<b>Coordinates:</b> {obs.private_location or obs.location} '
            f'({obs.geoprivacy or "Unknown geoprivacy"})',
        )
        self.details.add_line(
            'mdi.map-marker-radius',
            f'<b>Positional accuracy:</b> {obs.positional_accuracy or 0}m',
        )

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

    def select_observation(self, observation: Observation):
        self.load(observation)
        self.on_select.emit(observation)

    def _update_nav_buttons(self):
        """Update status and tooltip for 'back', 'forward', 'parent', and 'view on iNat' buttons"""
        # self.prev_button.setEnabled(bool(self.hist_prev))
        # self.prev_button.setToolTip(self.hist_prev[-1].full_name if self.hist_prev else None)
        # self.next_button.setEnabled(bool(self.hist_next))
        # self.next_button.setToolTip(self.hist_next[0].full_name if self.hist_next else None)
        # self.parent_button.setEnabled(bool(self.selected_observation.parent))
        # self.parent_button.setToolTip(
        #     self.selected_observation.parent.full_name if self.selected_observation.parent else None
        # )
        self.link_button.setEnabled(True)
        self.link_button.setToolTip(self.selected_observation.uri)
