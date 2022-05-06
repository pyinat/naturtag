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

from naturtag.inat_metadata import get_ids_from_url
from naturtag.qt_app.images import ImageViewer
from naturtag.tagger import tag_images

logger = getLogger(__name__)


class PhotoController(QWidget):
    """Controller for selecting and tagging local image files"""

    def __init__(self, info_callback: Callable):
        super().__init__()
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
        self.viewer = ImageViewer()
        photo_layout.addWidget(self.viewer)

        # TODO: Deselect input fields after clicking anywhere else
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
        files = list(self.viewer.images.keys())

        if not files:
            self.info('Select images to tag')
            return
        if not (obs_id or taxon_id):
            self.info('Select either an observation or an organism to tag images with')
            return

        selected_id = f'Observation ID: {obs_id}' if obs_id else f'Taxon ID: {taxon_id}'
        logger.info(f'Tagging {len(files)} images with metadata for {selected_id}')

        # TODO: Handle write errors (like file locked) and show dialog
        # TODO: Application settings
        # metadata_settings = get_app().settings_controller.metadata
        all_metadata, _, _ = tag_images(
            obs_id,
            taxon_id,
            # metadata_settings['common_names'],
            # metadata_settings['darwin_core'],
            # metadata_settings['hierarchical_keywords'],
            # metadata_settings['create_xmp'],
            images=files,
        )
        self.info(f'{len(files)} images tagged with metadata for {selected_id}')
        logger.info(sorted(list(self.viewer.images.keys())))
        logger.info(sorted([metadata.image_path for metadata in all_metadata]))

        for metadata in all_metadata:
            image = self.viewer.images[metadata.image_path]
            image.update_metadata(metadata)

    def clear(self):
        """Clear all images and input"""
        self.viewer.clear()
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
            self.viewer.load_images(text.splitlines())