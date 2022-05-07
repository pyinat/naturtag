from logging import getLogger
from typing import Callable

from PySide6.QtGui import QIntValidator
from PySide6.QtWidgets import (
    QApplication,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from naturtag.app.image_gallery import ImageGallery
from naturtag.inat_metadata import get_ids_from_url
from naturtag.settings import Settings
from naturtag.tagger import tag_images

logger = getLogger(__name__)


class ImageController(QWidget):
    """Controller for selecting and tagging local image files"""

    def __init__(self, settings: Settings, info_callback: Callable):
        super().__init__()
        self.settings = settings
        photo_layout = QVBoxLayout()
        self.setLayout(photo_layout)
        self.info = info_callback

        # Input group
        input_layout = QHBoxLayout()
        group_box = QGroupBox('Input')
        group_box.setFixedHeight(80)
        group_box.setLayout(input_layout)
        photo_layout.addWidget(group_box)

        # Viewer
        self.gallery = ImageGallery()
        photo_layout.addWidget(self.gallery)

        # Input fields
        self.input_obs_id = QLineEdit()
        self.input_obs_id.setClearButtonEnabled(True)
        self.input_obs_id.setValidator(QIntValidator())
        input_layout.addWidget(QLabel('Observation ID:'))
        input_layout.addWidget(self.input_obs_id)

        self.input_taxon_id = QLineEdit()
        self.input_taxon_id.setClearButtonEnabled(True)
        self.input_taxon_id.setValidator(QIntValidator())
        input_layout.addWidget(QLabel('Taxon ID:'))
        input_layout.addWidget(self.input_taxon_id)

    def run(self):
        """Run image tagging for selected images and input"""
        obs_id, taxon_id = self.input_obs_id.text(), self.input_taxon_id.text()
        files = list(self.gallery.images.keys())

        if not files:
            self.info('Select images to tag')
            return
        if not (obs_id or taxon_id):
            self.info('Select either an observation or an organism to tag images with')
            return

        selected_id = f'Observation ID: {obs_id}' if obs_id else f'Taxon ID: {taxon_id}'
        logger.info(f'Tagging {len(files)} images with metadata for {selected_id}')

        # TODO: Handle write errors (like file locked) and show dialog
        all_metadata = tag_images(
            obs_id,
            taxon_id,
            self.settings.common_names,
            self.settings.darwin_core,
            self.settings.hierarchical_keywords,
            self.settings.create_xmp,
            images=files,
        )
        self.info(f'{len(files)} images tagged with metadata for {selected_id}')

        for metadata in all_metadata:
            image = self.gallery.images[metadata.image_path]
            image.update_metadata(metadata)

    def clear(self):
        """Clear all images and input"""
        self.gallery.clear()
        self.input_obs_id.setText('')
        self.input_taxon_id.setText('')
        self.info('Images cleared')

    def paste(self):
        """Paste either image paths or taxon/observation URLs"""
        text = QApplication.clipboard().text()
        logger.debug(f'Pasted: {text}')

        taxon_id, observation_id = get_ids_from_url(text)
        if observation_id:
            self.input_obs_id.setText(str(observation_id))
            self.info(f'Observation {observation_id} selected')
        elif taxon_id:
            self.input_taxon_id.setText(str(taxon_id))
            self.info(f'Taxon {taxon_id} selected')
        else:
            self.gallery.load_images(text.splitlines())
