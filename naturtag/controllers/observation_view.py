"""Components for displaying taxon info"""

# TODO: code reuse with taxon_view
# TODO: nav history
import webbrowser
from collections import deque
from logging import getLogger

from pyinaturalist import Comment, Identification, Observation, Taxon
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import QGroupBox, QLabel, QPushButton, QScrollArea, QWidget

from naturtag.constants import SIZE_SM
from naturtag.widgets import (
    GEOPRIVACY_ICONS,
    QUALITY_GRADE_ICONS,
    FAIcon,
    HorizontalLayout,
    IconLabelList,
    ObservationImageWindow,
    ObservationPhoto,
    ScrollableGridArea,
    StylableWidget,
    VerticalLayout,
    fa_icon,
    set_pixmap_async,
)

logger = getLogger(__name__)


class ObservationInfoSection(StylableWidget):
    """Section to display selected observation photos and info"""

    on_select = Signal(Observation)  #: An observation was selected for tagging
    on_view_taxon = Signal(Taxon)  #: A taxon was selected for viewing (full object)
    on_view_taxon_by_id = Signal(int)  #: A taxon ID was selected for viewing (partial object)

    def __init__(self):
        super().__init__()
        self.hist_prev: deque[Observation] = deque()  # Viewing history for current session only
        self.hist_next: deque[Observation] = deque()  # Set when loading from history
        self.history_observation: Observation = None  # Set when loading from history, to avoid loop
        self.selected_observation: Observation = None

        self.group_box = QGroupBox('No observation selected')
        self.layout = HorizontalLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        root = VerticalLayout(self.group_box)

        # Scrollable area wrapping images and details
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll_content = QWidget()
        scroll_layout = VerticalLayout(scroll_content)
        scroll_area.setWidget(scroll_content)
        root.addWidget(scroll_area)

        images_container = QWidget()
        images_container.setMaximumHeight(316)
        images = HorizontalLayout(images_container)
        images.setContentsMargins(0, 0, 0, 0)
        images.setAlignment(Qt.AlignTop)
        scroll_layout.addWidget(images_container)
        self.layout.addWidget(self.group_box)

        # Medium default photo
        self.image = ObservationPhoto(hover_icon=True, hover_event=False)  # Disabled until 1st load
        self.image.setAlignment(Qt.AlignTop)
        images.addWidget(self.image)

        # Additional thumbnails
        self.thumbnails = ScrollableGridArea(n_columns=2, item_width=SIZE_SM[0])
        images.addWidget(self.thumbnails, alignment=Qt.AlignRight)

        # Selected observation details
        self.description = QLabel()
        self.description.setWordWrap(True)
        self.description.setMaximumWidth(500)
        self.details = IconLabelList()
        self.details_right = IconLabelList()
        details_columns = HorizontalLayout()
        details_columns.addWidget(self.details)
        details_columns.addWidget(self.details_right)
        details_container = VerticalLayout()
        details_container.addWidget(self.description)
        details_container.addLayout(details_columns)
        scroll_layout.addLayout(details_container)

        activity_header = QLabel('<h3>Activity</h3>')
        scroll_layout.addWidget(activity_header)
        self.id_comments_container = VerticalLayout()
        self.id_comments_container.setSpacing(6)
        scroll_layout.addLayout(self.id_comments_container)

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

        # Select button: Use observation for tagging
        self.select_button = QPushButton('Select')
        self.select_button.setIcon(fa_icon('fa5s.tag', primary=True))
        self.select_button.clicked.connect(lambda: self.on_select.emit(self.selected_observation))
        self.select_button.setEnabled(False)
        self.select_button.setToolTip('Select this observation for tagging')
        button_layout.addWidget(self.select_button)

        # View taxon button
        self.view_taxon_button = QPushButton('View Taxon')
        self.view_taxon_button.setIcon(fa_icon('fa5s.spider', primary=True))
        self.view_taxon_button.clicked.connect(
            lambda: self.on_view_taxon.emit(self.selected_observation.taxon)
        )
        self.view_taxon_button.setEnabled(False)
        button_layout.addWidget(self.view_taxon_button)

        # Link button: Open web browser to observation info page
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
        self.image.hover_event = True
        self.image.observation = obs
        set_pixmap_async(
            self.image,
            photo=obs.default_photo,
            size='medium',
            priority=QThread.HighPriority,
        )
        self._update_buttons()

        # Load additional thumbnails
        self.thumbnails.clear()
        for i, photo in enumerate(obs.photos[1:11] if obs.photos else []):
            thumb = ObservationPhoto(observation=obs, idx=i + 1, rounded=True)
            thumb.setFixedSize(*SIZE_SM)
            thumb.on_click.connect(self.image_window.display_observation_fullscreen)
            set_pixmap_async(thumb, photo=photo, size='thumbnail')
            self.thumbnails.addWidget(thumb)

        # Load observation details
        # TODO: code reuse with ObservationInfoCard
        # TODO: Format description in text box with border
        observed_date_str = (
            obs.observed_on.strftime('%Y-%m-%d %H:%M:%S') if obs.observed_on else 'unknown date'
        )
        created_date_str = (
            obs.created_at.strftime('%Y-%m-%d %H:%M:%S') if obs.created_at else 'unknown date'
        )
        num_ids = obs.identifications_count or 0
        quality_str = obs.quality_grade.replace('_', ' ').title().replace('Id', 'ID')
        self.description.setText(obs.description)

        # Left column: basic attributes
        self.details.clear()
        self.details.add_line('fa5.calendar-alt', f'<b>Observed on:</b> {observed_date_str}')
        self.details.add_line('fa5.calendar-alt', f'<b>Created on:</b> {created_date_str}')
        self.details.add_line('mdi.marker-check', f'<b>Identifications:</b> {num_ids}')

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
            f'<b>Coordinates:</b> {_format_location(obs)}',
        )
        self.details.add_line(
            'mdi.map-marker-radius',
            f'<b>Positional accuracy:</b> {obs.positional_accuracy or 0}m',
        )

        # Right column: annotations, ofvs, and tags
        self.details_right.clear()
        for a in obs.annotations or []:
            self.details_right.add_line('mdi.label', f'<b>{a.term}:</b> {a.value}')
        for ofv in obs.ofvs or []:
            self.details_right.add_line(
                'mdi.format-list-bulleted', f'<b>{ofv.name}:</b> {str(ofv.value)}'
            )
        if obs.tags:
            self.details_right.add_line('fa5s.tags', f'<b>Tags:</b> {", ".join(obs.tags)}')

        # Identifications and comments
        self.id_comments_container.clear()
        for item in _sort_id_comments(obs):
            if isinstance(item, Identification):
                card = IdentificationCard(item)
                card.on_view_taxon_by_id.connect(self.on_view_taxon_by_id.emit)
            else:
                card = CommentCard(item)
            self.id_comments_container.addWidget(card)

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

    def _update_buttons(self):
        """Update status and tooltip for nav and selection buttons"""
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
        self.view_taxon_button.setEnabled(True)
        self.view_taxon_button.setToolTip(
            f'See details for {self.selected_observation.taxon.full_name}'
        )
        self.select_button.setEnabled(True)


class ActivityCard(StylableWidget):
    """Base card widget for activity items (identifications and comments)"""

    on_view_taxon_by_id = Signal(int)

    def __init__(self, item: Identification | Comment, icon_name: str):
        super().__init__()
        layout = HorizontalLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignTop)

        icon_label = FAIcon(icon_name, size=16, align=Qt.AlignTop)
        layout.addWidget(icon_label)

        self.content = VerticalLayout()
        self.content.setContentsMargins(0, 0, 0, 0)
        self.content.setSpacing(2)
        layout.addLayout(self.content, stretch=1)

        date_str = item.created_at.strftime('%Y-%m-%d %H:%M') if item.created_at else ''
        header = QLabel(f'<b>{item.username}</b> · {date_str}')
        header.setTextFormat(Qt.RichText)
        header.setAlignment(Qt.AlignLeft)
        self.content.addWidget(header)

        # Add taxon, if one exists
        if taxon := getattr(item, 'taxon', None):
            taxon_label = QLabel(f'<a href="#"><i>{taxon.full_name}</i></a>')
            taxon_label.setTextFormat(Qt.RichText)
            taxon_label.setAlignment(Qt.AlignLeft)
            taxon_label.setOpenExternalLinks(False)
            taxon_label.linkActivated.connect(lambda _: self.on_view_taxon_by_id.emit(taxon.id))
            self.content.addWidget(taxon_label)

        if item.body:
            body = QLabel(item.body)
            body.setWordWrap(True)
            body.setAlignment(Qt.AlignLeft)
            self.content.addWidget(body)


class CommentCard(ActivityCard):
    """Card widget for a single comment"""

    def __init__(self, item: Comment):
        super().__init__(item, 'fa5s.comment')


class IdentificationCard(ActivityCard):
    """Card widget for a single identification"""

    def __init__(self, item: Identification):
        super().__init__(item, 'mdi.marker-check')


# TODO: move to pyinaturalist.Observation
def _format_location(obs: Observation) -> str:
    """Format the observation coordinates + geoprivacy, if available"""
    coords = obs.private_location or obs.location
    if not coords or len(coords) < 2:
        return 'N/A'
    geoprivacy = f' ({obs.geoprivacy})' if obs.geoprivacy else ''
    return f'({coords[0]:.4f}, {coords[1]:.4f}){geoprivacy}'


def _sort_id_comments(obs: Observation) -> list[Identification | Comment]:
    """Sort identifications and comments chronologically, with identifications first if timestamps are equal"""
    return sorted(
        (obs.identifications or []) + (obs.comments or []),
        key=lambda c: c.created_at,
    )
