"""Image widgets specifically for observation photos"""
from logging import getLogger
from string import capwords
from typing import Iterable, Optional

from pyinaturalist import Observation, Photo
from PySide6.QtCore import Qt

from naturtag.constants import SIZE_ICON_SM
from naturtag.widgets.images import HoverPhoto, IconLabel, ImageWindow, InfoCard, InfoCardList
from naturtag.widgets.layouts import HorizontalLayout

logger = getLogger(__name__)

GEOPRIVACY_ICONS = {
    'open': 'mdi.map-marker-check',
    'obscured': 'mdi.map-marker-question',
    'private': 'mdi.map-marker-remove-variant',
}
QUALITY_GRADE_ICONS = {
    'casual': 'mdi.chevron-up',
    'needs_id': 'mdi.chevron-double-up',
    'research': 'mdi.chevron-triple-up',
}


class ObservationPhoto(HoverPhoto):
    """A photo with an observation reference and hover effect"""

    def __init__(self, observation: Optional[Observation] = None, **kwargs):
        super().__init__(**kwargs)
        self.observation = observation


class ObservationInfoCard(InfoCard):
    """Card containing an observation thumbnail and basic info"""

    def __init__(self, obs: Observation, delayed_load: bool = True):
        super().__init__(card_id=obs.id)
        self.setFixedHeight(100)
        self.observation = obs

        if not delayed_load:
            pixmap = self.thumbnail.get_pixmap(url=obs.default_photo.thumbnail_url)
            self.thumbnail.setPixmap(pixmap)

        # Title: Taxon name
        if obs.taxon:
            t = obs.taxon
            common_name = (
                f' ({capwords(t.preferred_common_name)})' if t.preferred_common_name else ''
            )
            self.title.setText(f'{t.rank.title()}: <i>{t.name}</i>{common_name}')
        else:
            self.title.setText('Unknown Taxon')

        # Details: Date, place guess, number of ids and photos, quality grade
        date_str = obs.observed_on.strftime('%Y-%m-%d') if obs.observed_on else 'unknown date'
        num_ids = obs.identifications_count or 0
        num_photos = len(obs.photos)
        icon_size = SIZE_ICON_SM[0]
        layout = HorizontalLayout()
        layout.setSpacing(0)
        layout.setAlignment(Qt.AlignLeft)
        layout.addWidget(IconLabel('fa5.calendar-alt', date_str, size=icon_size))
        layout.addWidget(IconLabel('mdi.marker-check', num_ids, size=icon_size))
        layout.addWidget(
            IconLabel(
                'fa5.images' if num_photos > 1 else 'fa5.image',
                num_photos,
                size=icon_size,
            )
        )
        if obs.sounds:
            layout.addWidget(
                IconLabel(
                    'ri.volume-up-fill',
                    len(obs.sounds),
                    size=icon_size,
                )
            )
        layout.addWidget(
            IconLabel(
                QUALITY_GRADE_ICONS.get(obs.quality_grade, 'mdi.chevron-up'),
                obs.quality_grade.replace('_', ' ').title(),
                size=icon_size,
            )
        )
        self.add_row(layout)
        self.add_row(IconLabel('fa.map-marker', obs.place_guess or obs.location, size=icon_size))

        # Add more verbose details in tooltip
        tooltip_lines = [
            f'Observed on: {obs.observed_on}',
            f'Submitted on: {obs.created_at}',
            f'Taxon: {obs.taxon.full_name}',
            f'Location: {obs.place_guess}',
            f'Coordinates: {obs.location}',
            f'Positional accuracy: {obs.positional_accuracy or 0}m',
            f'Identifications: {num_ids} ({obs.num_identification_agreements or 0} agree)',
            f'Photos: {num_photos}',
            f'Sounds: {len(obs.sounds)}',
            f'Quality grade: {obs.quality_grade}',
        ]
        self.setToolTip('\n'.join(tooltip_lines))


class ObservationList(InfoCardList):
    """A scrollable list of ObservationInfoCards"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def add_observation(
        self, observation: Observation, idx: Optional[int] = None
    ) -> ObservationInfoCard:
        """Add a card immediately, and load its thumbnail from a separate thread"""
        card = ObservationInfoCard(observation)
        super().add_card(card, observation.default_photo.thumbnail_url, idx=idx)
        return card

    def add_or_update_observation(
        self, observation: Observation, idx: int = 0
    ) -> Optional[ObservationInfoCard]:
        """Move a card to the specified position, and add a new one if it doesn't exist.
        Return True if a new card was added.
        """
        if not self.move_card(observation.id, idx):
            return self.add_observation(observation, idx)
        return None

    def set_observations(self, observations: Iterable[Observation]):
        """Replace all existing cards with new ones for the specified observations"""
        self.clear()
        for observation in observations:
            if observation is not None:
                self.add_observation(observation)


class ObservationImageWindow(ImageWindow):
    """Display observation images in fullscreen as a separate window.
    Uses URLs instead of local file paths.
    """

    def __init__(self):
        super().__init__()
        self.observation: Observation = None
        self.photos: list[Photo] = None
        self.selected_photo: Photo = None

    @property
    def idx(self) -> int:
        """The index of the currently selected image"""
        return self.photos.index(self.selected_photo)

    def display_observation_fullscreen(self, observation_photo: ObservationPhoto):
        """Open window to a selected observation image, and save other image URLs for navigation"""
        idx = observation_photo.idx
        obs = observation_photo.observation
        if not obs:
            return

        self.observation = obs
        self.selected_photo = obs.photos[idx] if obs.photos else Photo()  # TODO
        self.photos = obs.photos
        self.image_paths = [photo.original_url for photo in self.photos]
        self.set_photo(self.selected_photo)
        self.showFullScreen()

    def select_image_idx(self, idx: int):
        """Select an image by index"""
        self.selected_photo = self.photos[idx]
        self.set_photo(self.selected_photo)

    def set_photo(self, photo: Photo):
        self.image.setPixmap(self.image.get_pixmap(url=photo.original_url))

    def remove_image(self):
        pass
