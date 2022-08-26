"""Image widgets specifically for observation photos"""
from logging import getLogger
from typing import Iterable

from pyinaturalist import Observation
from PySide6.QtCore import Qt

from naturtag.widgets.images import HoverPhoto, IconLabel, InfoCard, InfoCardList
from naturtag.widgets.layouts import HorizontalLayout

logger = getLogger(__name__)

QUALITY_GRADE_ICONS = {
    'casual': 'mdi.chevron-up',
    'needs_id': 'mdi.chevron-double-up',
    'research': 'mdi.chevron-triple-up',
}


class ObservationPhoto(HoverPhoto):
    """A photo with an observation reference and hover effect"""

    def __init__(self, observation: Observation = None, **kwargs):
        super().__init__(**kwargs)
        self.observation = observation


class ObservationInfoCard(InfoCard):
    """Card containing an observation thumbnail and basic info"""

    def __init__(self, observation: Observation, delayed_load: bool = True):
        super().__init__(card_id=observation.id)
        self.setFixedHeight(100)
        self.observation = observation

        if not delayed_load:
            pixmap = self.thumbnail.get_pixmap(url=observation.thumbnail_url)
            self.thumbnail.setPixmap(pixmap)

        # Title: Taxon name
        if observation.taxon:
            t = observation.taxon
            common_name = f' ({t.preferred_common_name.title()})' if t.preferred_common_name else ''
            self.title.setText(f'{t.rank.title()}: <i>{t.name}</i>{common_name}')
        else:
            self.title.setText('Unknown Taxon')

        # Details: Date, place guess, number of ids and photos, quality grade
        date_str = (
            observation.observed_on.strftime('%Y-%m-%d')
            if observation.observed_on
            else 'unknown date'
        )
        quality_icon = QUALITY_GRADE_ICONS.get(observation.quality_grade, 'mdi.chevron-up')
        num_ids = observation.identifications_count or len(observation.identifications)
        num_photos = len(observation.photos)
        photos_icon = 'fa5.images' if num_photos > 1 else 'fa5.image'
        quality_str = observation.quality_grade.replace('_', ' ').title()

        layout = HorizontalLayout()
        layout.setSpacing(0)
        layout.setAlignment(Qt.AlignLeft)
        layout.addWidget(IconLabel('fa5.calendar-alt', date_str, size=20))
        layout.addWidget(IconLabel('mdi.marker-check', str(num_ids), size=20))
        layout.addWidget(IconLabel(photos_icon, str(num_photos), size=20))
        layout.addWidget(IconLabel(quality_icon, quality_str, size=20))
        self.details_layout.addLayout(layout)
        self.details_layout.addWidget(
            IconLabel('fa.map-marker', observation.place_guess or observation.location, size=20)
        )

        # Add more verbose details in tooltip
        tooltip_lines = [
            f'Observed on: {observation.observed_on}',
            f'Submitted on: {observation.created_at}',
            f'Taxon: {observation.taxon.full_name}',
            f'Location: {observation.place_guess}',
            f'Coordinates: {observation.location}',
            f'Positional accuracy: {observation.positional_accuracy or 0}m',
            f'Identifications: {num_ids}',
            f'Photos: {num_photos}',
            f'Quality grade: {observation.quality_grade}',
        ]
        self.setToolTip('\n'.join(tooltip_lines))


class ObservationList(InfoCardList):
    """A scrollable list of TaxonInfoCards"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def add_observation(self, observation: Observation, idx: int = None):
        """Add a card immediately, and load its thumbnail from a separate thread"""
        card = ObservationInfoCard(observation)
        super().add_card(card, observation.thumbnail_url, idx=idx)

    def add_or_update_observation(self, observation: Observation, idx: int = 0):
        """Move a card to the specified position, and add a new one if it doesn't exist"""
        if not self.move_card(observation.id, idx):
            self.add_observation(observation, idx)

    def set_observations(self, observations: Iterable[Observation]):
        """Replace all existing cards with new ones for the specified observations"""
        self.clear()
        for observation in observations:
            if observation is not None:
                self.add_observation(observation)
