from logging import getLogger
from typing import TYPE_CHECKING

from pyinaturalist import Observation, Taxon
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtWidgets import QApplication, QGroupBox, QLabel, QSizePolicy

from naturtag.controllers import BaseController, ImageGallery
from naturtag.metadata import MetaMetadata, _refresh_tags, get_ids_from_url, tag_images
from naturtag.widgets import (
    HorizontalLayout,
    IdInput,
    ObservationInfoCard,
    TaxonInfoCard,
    VerticalLayout,
)

logger = getLogger(__name__)


# TODO: Handle write errors (like file locked) and show dialog
class ImageController(BaseController):
    """Controller for selecting and tagging local image files"""

    on_new_metadata = Signal(MetaMetadata)  #: Metadata for an image was updated
    on_select_taxon_id = Signal(int)  #: A taxon ID was entered
    on_select_taxon_tab = Signal()  #: Request to switch to taxon tab
    on_select_observation_id = Signal(int)  #: An observation ID was entered
    on_select_observation_tab = Signal()  #: Request to switch to observation tab

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        photo_layout = VerticalLayout(self)
        top_section_layout = HorizontalLayout()
        top_section_layout.setAlignment(Qt.AlignLeft)
        photo_layout.addLayout(top_section_layout)
        self.on_new_metadata.connect(self.update_metadata)

        # Input group
        group_box = QGroupBox('Quick entry')
        group_box.setFixedHeight(150)
        group_box.setFixedWidth(200)
        top_section_layout.addWidget(group_box)

        # Input fields
        inputs_layout = VerticalLayout(group_box)
        self.input_obs_id = IdInput()
        inputs_layout.addWidget(QLabel('Observation ID:'))
        inputs_layout.addWidget(self.input_obs_id)
        self.input_taxon_id = IdInput()
        inputs_layout.addWidget(QLabel('Taxon ID:'))
        inputs_layout.addWidget(self.input_taxon_id)

        # Notify other controllers when an ID is selected from input text
        self.input_obs_id.on_select.connect(self.on_select_observation_id)
        self.input_taxon_id.on_select.connect(self.on_select_taxon_id)

        # Selected taxon/observation info
        group_box = QGroupBox('Metadata source')
        group_box.setFixedHeight(150)
        group_box.setMinimumWidth(400)
        group_box.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Minimum)
        top_section_layout.addWidget(group_box)
        self.data_source_card = HorizontalLayout(group_box)

        # Clear info when clearing an input field
        self.input_obs_id.on_clear.connect(self.data_source_card.clear)
        self.input_taxon_id.on_clear.connect(self.data_source_card.clear)

        # Image gallery
        self.gallery = ImageGallery(self.settings, self.threadpool)
        self.gallery.on_select_observation.connect(self.on_select_observation_tab)
        self.gallery.on_select_taxon.connect(self.on_select_taxon_tab)
        photo_layout.addWidget(self.gallery)

    def run(self):
        """Run image tagging for selected images and input"""
        image_paths = list(self.gallery.images.keys())
        if not image_paths:
            self.info('Select images to tag')
            return

        obs_id, taxon_id = self.input_obs_id.text(), self.input_taxon_id.text()
        if not (obs_id or taxon_id):
            self.info('Select either an observation or an organism to tag images with')
            return

        selected_id = f'Observation ID: {obs_id}' if obs_id else f'Taxon ID: {taxon_id}'
        logger.info(f'Tagging {len(image_paths)} images with metadata for {selected_id}')

        def tag_image(image_path):
            return tag_images([image_path], obs_id, taxon_id, settings=self.settings)[0]

        for image_path in image_paths:
            future = self.threadpool.schedule(tag_image, image_path=image_path)
            future.on_result.connect(self.update_metadata)
        self.info(f'{len(image_paths)} images tagged with metadata for {selected_id}')

    @Slot(MetaMetadata)
    def update_metadata(self, metadata: MetaMetadata):
        if TYPE_CHECKING:
            assert metadata.image_path is not None
        image = self.gallery.images[metadata.image_path]
        image.update_metadata(metadata)

    def refresh(self):
        """Refresh metadata for any previously tagged images"""
        images = list(self.gallery.images.values())
        if not images:
            self.info('Select images to tag')
            return

        for image in images:
            future = self.threadpool.schedule(
                lambda: _refresh_tags(image.metadata, self.settings),
            )
            future.on_result.connect(self.update_metadata)
        self.info(f'{len(images)} images updated')

    def clear(self):
        """Clear all images and input"""
        self.gallery.clear()
        self.input_obs_id.clear()
        self.input_taxon_id.clear()
        self.data_source_card.clear()
        self.info('Images cleared')

    def paste(self):
        """Paste either image paths or taxon/observation URLs"""
        text = QApplication.clipboard().text()
        logger.debug(f'Pasted: {text}')

        # Check for IDs if an iNat URL was pasted
        observation_id, taxon_id = get_ids_from_url(text)
        if observation_id:
            self.on_select_observation_id.emit(observation_id)
        elif taxon_id:
            self.on_select_taxon_id.emit(taxon_id)
        # If not an iNat URL, check for valid image paths
        else:
            self.gallery.load_images(text.splitlines())

    @Slot(Taxon)
    def select_taxon(self, taxon: Taxon):
        """Update input info from a taxon object (loaded from Species tab)"""
        if self.input_taxon_id.text() == str(taxon.id):
            return

        self.input_taxon_id.set_id(taxon.id)
        self.data_source_card.clear()
        card = TaxonInfoCard(taxon=taxon, delayed_load=False)
        card.on_click.connect(self.on_select_taxon_tab)
        self.data_source_card.addWidget(card)

    @Slot(Observation)
    def select_observation(self, observation: Observation):
        """Update input info from an observation object (loaded from Observations tab)"""
        if self.input_obs_id.text() == str(observation.id):
            return

        self.input_obs_id.set_id(observation.id)
        self.input_taxon_id.set_id(observation.taxon.id)
        self.data_source_card.clear()
        card = ObservationInfoCard(obs=observation, delayed_load=False)
        card.on_click.connect(self.on_select_observation_tab)
        self.data_source_card.addWidget(card)

    def info(self, message: str):
        self.on_message.emit(message)
