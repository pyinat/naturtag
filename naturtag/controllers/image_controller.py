from logging import getLogger

from pyinaturalist import Taxon
from PySide6.QtCore import QEvent, Signal
from PySide6.QtGui import QIntValidator
from PySide6.QtWidgets import QApplication, QGroupBox, QLabel, QLineEdit, QToolButton, QWidget

from naturtag.app.style import fa_icon
from naturtag.controllers import ImageGallery
from naturtag.metadata import get_ids_from_url, refresh_metadata, tag_images
from naturtag.settings import Settings
from naturtag.widgets import HorizontalLayout, TaxonInfoCard, VerticalLayout

logger = getLogger(__name__)


class ImageController(QWidget):
    """Controller for selecting and tagging local image files"""

    message = Signal(str)

    def __init__(self, settings: Settings):
        super().__init__()
        self.settings = settings
        photo_layout = VerticalLayout()
        self.setLayout(photo_layout)

        # Input group
        data_source_layout = HorizontalLayout()
        group_box = QGroupBox('Metadata source (observation and/or taxon)')
        group_box.setFixedHeight(150)
        group_box.setFixedWidth(600)
        group_box.setLayout(data_source_layout)
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
        files = list(self.gallery.images.keys())
        if not files:
            self.info('Select images to tag')
            return

        obs_id, taxon_id = self.input_obs_id.text(), self.input_taxon_id.text()
        if not (obs_id or taxon_id):
            self.info('Select either an observation or an organism to tag images with')
            return

        selected_id = f'Observation ID: {obs_id}' if obs_id else f'Taxon ID: {taxon_id}'
        logger.info(f'Tagging {len(files)} images with metadata for {selected_id}')

        # TODO: Handle write errors (like file locked) and show dialog
        all_metadata = tag_images(
            obs_id,
            taxon_id,
            common_names=self.settings.common_names,
            hierarchical=self.settings.hierarchical_keywords,
            create_sidecar=self.settings.create_sidecar,
            images=files,
        )
        self.info(f'{len(files)} images tagged with metadata for {selected_id}')

        for metadata in all_metadata:
            image = self.gallery.images[metadata.image_path]
            image.update_metadata(metadata)

    def refresh(self):
        """Refresh metadata for any previously tagged images"""
        images = list(self.gallery.images.values())
        if not images:
            self.info('Select images to tag')
            return

        for image in images:
            metadata = refresh_metadata(
                image.metadata,
                common_names=self.settings.common_names,
                hierarchical=self.settings.hierarchical_keywords,
                create_sidecar=self.settings.create_sidecar,
            )
            image.update_metadata(metadata)
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
        self.message.emit(message)


class IdInput(QLineEdit):
    """Pressing return or losing focus will send a 'selection' signal"""

    selection = Signal(int)

    def __init__(self):
        super().__init__()
        self.setClearButtonEnabled(True)
        self.setValidator(QIntValidator())
        self.setMaximumWidth(200)
        self.findChild(QToolButton).setIcon(fa_icon('mdi.backspace'))
        self.returnPressed.connect(self.select_taxon)

    def focusOutEvent(self, event: QEvent = None):
        self.select_taxon()
        return super().focusOutEvent(event)

    def select_taxon(self):
        if self.text():
            self.selection.emit(int(self.text()))
