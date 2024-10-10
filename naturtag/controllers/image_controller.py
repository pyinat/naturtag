from logging import getLogger
from typing import Optional

from pyinaturalist import Observation, Taxon
from PySide6.QtCore import Qt, QThread, Signal, Slot
from PySide6.QtWidgets import QApplication, QGroupBox, QLabel, QSizePolicy

from naturtag.controllers import BaseController, ImageGallery, get_app
from naturtag.metadata import MetaMetadata, _refresh_tags, tag_images
from naturtag.utils import get_ids_from_url
from naturtag.widgets import (
    HorizontalLayout,
    IdInput,
    ObservationInfoCard,
    TaxonInfoCard,
    VerticalLayout,
)
from naturtag.widgets.images import FAIcon

logger = getLogger(__name__)


# TODO: Handle write errors (like file locked) and show dialog
class ImageController(BaseController):
    """Controller for selecting and tagging local image files"""

    on_new_metadata = Signal(MetaMetadata)  #: Metadata for an image was updated
    on_view_taxon_id = Signal(int)  #: Request to switch to taxon tab
    on_view_observation_id = Signal(int)  #: Request to switch to observation tab

    def __init__(self):
        super().__init__()
        photo_layout = VerticalLayout(self)
        top_section_layout = HorizontalLayout()
        top_section_layout.setAlignment(Qt.AlignLeft)
        photo_layout.addLayout(top_section_layout)
        self.on_new_metadata.connect(self.update_metadata)
        self.selected_taxon_id: Optional[int] = None
        self.selected_observation_id: Optional[int] = None

        # Selected taxon/observation info
        group_box = QGroupBox('Metadata source')
        group_box.setFixedHeight(150)
        group_box.setMinimumWidth(400)
        group_box.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Minimum)
        top_section_layout.addWidget(group_box)
        self.data_source_card = HorizontalLayout(group_box)
        self.data_source_card.setAlignment(Qt.AlignLeft)

        # Help text
        help_msg = QLabel(
            'Select a source of metadata to tag photos with.\n'
            'Browse the Species or Observations tabs,\n'
            'paste an iNaturalist URL, or enter an ID to the right.'
        )
        self.data_source_card.addWidget(FAIcon('ei.info-circle'))
        self.data_source_card.addWidget(help_msg)

        # Input group
        group_box = QGroupBox('Quick entry')
        group_box.setFixedHeight(150)
        group_box.setFixedWidth(200)
        top_section_layout.addWidget(group_box)

        # Input fields
        inputs_layout = VerticalLayout(group_box)
        self.input_taxon_id = IdInput()
        self.input_taxon_id.on_select.connect(self.select_taxon_by_id)
        inputs_layout.addWidget(QLabel('Taxon ID:'))
        inputs_layout.addWidget(self.input_taxon_id)
        self.input_obs_id = IdInput()
        self.input_obs_id.on_select.connect(self.select_observation_by_id)
        inputs_layout.addWidget(QLabel('Observation ID:'))
        inputs_layout.addWidget(self.input_obs_id)

        # Image gallery
        self.gallery = ImageGallery()
        photo_layout.addWidget(self.gallery)

    def run(self):
        """Run image tagging for selected images and input"""
        image_paths = list(self.gallery.images.keys())
        if not image_paths:
            self.info('Select images to tag')
            return

        obs_id, taxon_id = self.selected_observation_id, self.selected_taxon_id
        if not (obs_id or taxon_id):
            self.info('Select either an observation or an organism to tag images with')
            return

        selected_id = f'Observation ID: {obs_id}' if obs_id else f'Taxon ID: {taxon_id}'
        logger.info(f'Tagging {len(image_paths)} images with metadata for {selected_id}')

        def tag_image(image_path):
            return tag_images(
                [image_path],
                obs_id,
                taxon_id,
                client=self.app.client,
                settings=self.app.settings,
            )[0]

        for image_path in image_paths:
            future = self.app.threadpool.schedule(tag_image, image_path=image_path)
            future.on_result.connect(self.update_metadata)
        self.info(f'{len(image_paths)} images tagged with metadata for {selected_id}')

    @Slot(MetaMetadata)
    def update_metadata(self, metadata: Optional[MetaMetadata]):
        if metadata and metadata.image_path:
            image = self.gallery.images[metadata.image_path]
            image.update_metadata(metadata)

    def refresh(self):
        """Refresh metadata for any previously tagged images"""
        images = list(self.gallery.images.values())
        if not images:
            self.info('Select images to tag')
            return

        self.info(f'Refreshing tags for {len(images)} images')
        for image in images:
            future = self.app.threadpool.schedule(
                lambda: _refresh_tags(image.metadata, self.app.client, self.app.settings),
            )
            future.on_result.connect(self.update_metadata)

    def clear(self):
        """Clear all images and input"""
        self.selected_taxon_id = None
        self.selected_observation_id = None
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
            self.select_observation_by_id(observation_id)
        elif taxon_id:
            self.select_taxon_by_id(taxon_id)
        # If not an iNat URL, check for valid image paths
        else:
            self.gallery.load_images(text.splitlines())

    # Note: These methods duplicate "display_x_by_id" controller methods, but attempts at code reuse
    #   added too much spaghetti
    def select_taxon_by_id(self, taxon_id: int):
        """Load a taxon by ID (pasted or directly entered)"""
        if self.selected_taxon_id == taxon_id:
            return

        app = get_app()
        logger.info(f'Loading taxon {taxon_id}')
        future = app.threadpool.schedule(
            lambda: app.client.taxa(taxon_id, locale=app.settings.locale),
            priority=QThread.HighPriority,
        )
        future.on_result.connect(self.select_taxon)

    def select_observation_by_id(self, observation_id: int):
        """Load an observation by ID (pasted or directly entered)"""
        if self.selected_observation_id == observation_id:
            return

        app = get_app()
        logger.info(f'Loading observation {observation_id}')
        future = app.threadpool.schedule(
            lambda: app.client.observations(observation_id, taxonomy=True),
            priority=QThread.HighPriority,
        )
        future.on_result.connect(self.select_observation)

    @Slot(Taxon)
    def select_taxon(self, taxon: Taxon):
        """Update metadata info from a taxon object"""
        if self.selected_taxon_id == taxon.id:
            return

        self.selected_taxon_id = taxon.id
        self.selected_observation_id = None
        self.input_obs_id.clear()
        self.input_taxon_id.clear()
        self.data_source_card.clear()

        card = TaxonInfoCard(taxon=taxon, delayed_load=False)
        card.on_click.connect(self.on_view_taxon_id)
        self.data_source_card.addWidget(card)

    @Slot(Observation)
    def select_observation(self, observation: Observation):
        """Update input info from an observation object"""
        if self.selected_observation_id == observation.id:
            return

        self.selected_taxon_id = None
        self.selected_observation_id = observation.id
        self.input_obs_id.clear()
        self.input_taxon_id.clear()
        self.data_source_card.clear()

        card = ObservationInfoCard(obs=observation, delayed_load=False)
        card.on_click.connect(self.on_view_observation_id)
        self.data_source_card.addWidget(card)
