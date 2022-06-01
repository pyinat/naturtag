from logging import getLogger
from typing import TYPE_CHECKING

from pyinaturalist import Taxon
from PySide6.QtCore import Signal, Slot
from PySide6.QtWidgets import QApplication, QGroupBox, QLabel, QWidget

from naturtag.app.threadpool import ThreadPool
from naturtag.controllers import ImageGallery
from naturtag.metadata import get_ids_from_url, refresh_image, tag_images
from naturtag.metadata.meta_metadata import MetaMetadata
from naturtag.settings import Settings
from naturtag.widgets import HorizontalLayout, IdInput, TaxonInfoCard, VerticalLayout

logger = getLogger(__name__)


# TODO: Handle write errors (like file locked) and show dialog
class ImageController(QWidget):
    """Controller for selecting and tagging local image files"""

    on_message = Signal(str)
    on_new_metadata = Signal(MetaMetadata)

    def __init__(self, settings: Settings, threadpool: ThreadPool):
        super().__init__()
        self.settings = settings
        self.threadpool = threadpool
        photo_layout = VerticalLayout(self)
        self.on_new_metadata.connect(self.update_metadata)

        # Input group
        group_box = QGroupBox('Metadata source (observation and/or taxon)')
        group_box.setFixedHeight(150)
        group_box.setFixedWidth(600)
        data_source_layout = HorizontalLayout(group_box)
        photo_layout.addWidget(group_box)

        # Input fields
        inputs_layout = VerticalLayout()
        data_source_layout.addLayout(inputs_layout)
        self.input_obs_id = IdInput()
        inputs_layout.addWidget(QLabel('Observation ID:'))
        inputs_layout.addWidget(self.input_obs_id)
        self.input_taxon_id = IdInput()
        inputs_layout.addWidget(QLabel('Taxon ID:'))
        inputs_layout.addWidget(self.input_taxon_id)

        # Selected taxon/observation info
        data_source_layout.addStretch()
        self.data_source_card = HorizontalLayout()
        data_source_layout.addLayout(self.data_source_card)

        # Viewer
        self.gallery = ImageGallery()
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
            return tag_images(
                [image_path],
                obs_id,
                taxon_id,
                common_names=self.settings.common_names,
                hierarchical=self.settings.hierarchical_keywords,
                create_sidecar=self.settings.create_sidecar,
            )[0]

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

        def _refresh_image(image):
            return refresh_image(
                image.metadata,
                common_names=self.settings.common_names,
                hierarchical=self.settings.hierarchical_keywords,
                create_sidecar=self.settings.create_sidecar,
            )

        for image in images:
            future = self.threadpool.schedule(_refresh_image, image=image)
            future.on_result.connect(self.update_metadata)
        self.info(f'{len(images)} images updated')

    def clear(self):
        """Clear all images and input"""
        self.gallery.clear()
        self.input_obs_id.setText('')
        self.input_taxon_id.setText('')
        self.data_source_card.clear()
        self.info('Images cleared')

    # TODO: Cleaner way to do this. move paste to MainWindow?
    def paste(self):
        """Paste either image paths or taxon/observation URLs"""
        text = QApplication.clipboard().text()
        logger.debug(f'Pasted: {text}')

        observation_id, taxon_id = get_ids_from_url(text)
        if observation_id:
            self.input_obs_id.setText(str(observation_id))
            # self.input_obs_id.select_taxon()
            self.info(f'Observation {observation_id} selected')
        elif taxon_id:
            self.input_taxon_id.setText(str(taxon_id))
            # self.input_taxon_id.select_taxon()
            self.info(f'Taxon {taxon_id} selected')
        else:
            self.gallery.load_images(text.splitlines())

    def select_taxon(self, taxon: Taxon):
        self.input_taxon_id.setText(str(taxon.id))
        self.data_source_card.clear()
        self.data_source_card.addWidget(TaxonInfoCard(taxon=taxon, delayed_load=False))

    def info(self, message: str):
        self.on_message.emit(message)
