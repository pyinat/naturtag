import re
import webbrowser
from logging import getLogger
from pathlib import Path
from typing import Callable, Iterable

from PySide6.QtCore import (
    QEasingCurve,
    QParallelAnimationGroup,
    QPropertyAnimation,
    Qt,
    QUrl,
    Signal,
    Slot,
)
from PySide6.QtGui import QAction, QDesktopServices, QDropEvent
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QGraphicsColorizeEffect,
    QGraphicsOpacityEffect,
    QLabel,
    QMenu,
    QScrollArea,
)

from naturtag.app.style import fa_icon
from naturtag.constants import IMAGE_FILETYPES, THUMBNAIL_SIZE_DEFAULT, PathOrStr
from naturtag.metadata import MetaMetadata
from naturtag.utils import generate_thumbnail, get_valid_image_paths
from naturtag.widgets import (
    FlowLayout,
    HorizontalLayout,
    HoverLabel,
    IconLabel,
    ImageWindow,
    StylableWidget,
    VerticalLayout,
)

logger = getLogger(__name__)


class ImageGallery(StylableWidget):
    """Container for displaying local image thumbnails & info"""

    on_message = Signal(str)  #: Forward a message to status bar
    on_select_taxon = Signal(int)  #: A taxon was selected from context menu

    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.images: dict[Path, LocalThumbnail] = {}
        self.image_window = ImageWindow()
        self.image_window.on_remove.connect(self.remove_image)
        root = VerticalLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        self.scroll_panel = StylableWidget()
        self.scroll_panel.setObjectName('gallery_scroll_panel')
        self.flow_layout = FlowLayout(self.scroll_panel)
        self.flow_layout.setSpacing(0)
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setWidget(self.scroll_panel)
        root.addLayout(self.flow_layout)
        root.addWidget(scroll_area)

    def clear(self):
        """Clear all images from the viewer"""
        self.images = {}
        self.flow_layout.clear()

    def load_file_dialog(self):
        """Show a file chooser dialog"""
        image_paths, _ = QFileDialog.getOpenFileNames(
            self,
            'Open image files:',
            filter=f'Image files ({" ".join(IMAGE_FILETYPES)})',
        )
        self.load_images(image_paths)

    def load_images(self, image_paths: Iterable[PathOrStr]):
        """Load multiple images, and ignore any duplicates"""
        images = get_valid_image_paths(image_paths, recursive=True)
        new_images = images - set(self.images.keys())
        if not new_images:
            return

        logger.info(f'Loading {len(new_images)} ({len(images) - len(new_images)} already loaded)')
        for image_path in sorted(list(new_images)):
            self.load_image(image_path)

    def load_image(self, image_path: Path):
        """Load an image"""
        if not image_path.is_file():
            logger.info(f'File does not exist: {image_path}')
            return
        elif image_path in self.images:
            logger.info(f'Image already loaded: {image_path}')
            return

        logger.info(f'Loading {image_path}')
        thumbnail = LocalThumbnail(image_path)
        thumbnail.on_remove.connect(self.remove_image)
        thumbnail.on_select.connect(self.select_image)
        thumbnail.on_copy.connect(self.on_message)
        thumbnail.context_menu.on_select_taxon.connect(self.on_select_taxon)
        self.flow_layout.addWidget(thumbnail)
        self.images[thumbnail.image_path] = thumbnail

    def dragEnterEvent(self, event):
        event.acceptProposedAction()

    def dragMoveEvent(self, event):
        event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        event.acceptProposedAction()
        self.load_images(event.mimeData().text().splitlines())

    @Slot(str)
    def remove_image(self, image_path: Path):
        logger.debug(f'Removing image {image_path}')
        thumbnail = self.images.pop(image_path)
        thumbnail.setParent(None)
        thumbnail.deleteLater()

    @Slot(str)
    def select_image(self, image_path: Path):
        self.image_window.display_image(image_path, list(self.images.keys()))


class LocalThumbnail(StylableWidget):
    """A tile that displays a thumbnail for a local image file. Contains icons representing its
    metadata types, and the following mouse actions:

    * Left click: Show full image
    * Middle click: Remove image
    * Right click: Show context menu
    """

    on_copy = Signal(str)  #: Tags were copied to the clipboard
    on_remove = Signal(Path)  #: Request for the image to be removed from the gallery
    on_select = Signal(Path)  #: The image was clicked

    def __init__(self, image_path: Path):
        super().__init__()
        self.image_path = image_path
        self.metadata = MetaMetadata(self.image_path)
        self.setToolTip(self.metadata.summary)
        layout = VerticalLayout(self)

        # Image
        self.image = HoverLabel(self)
        self.image.setPixmap(generate_thumbnail(self.image_path))
        layout.addWidget(self.image)

        # Context menu and metadata icons
        self.context_menu = ThumbnailContextMenu(self)
        self.icons = ThumbnailMetaIcons(self)
        self.icons.setObjectName('metadata-icons')

        # Filename label
        text = re.sub('([_-])', '\\1\u200b', self.image_path.name)  # To allow word wrapping
        self.label = QLabel(text)
        self.label.setMaximumWidth(THUMBNAIL_SIZE_DEFAULT[0])
        self.label.setMinimumHeight(40)
        self.label.setAlignment(Qt.AlignLeft)
        self.label.setWordWrap(True)
        layout.addWidget(self.label)

        # Icon shown when an image is tagged or updated
        self.check = IconLabel(
            'fa5s.check', self.image, primary=True, size=THUMBNAIL_SIZE_DEFAULT[0]
        )
        self.check.setVisible(False)

    def contextMenuEvent(self, e):
        self.context_menu.exec(e.globalPos())

    def mousePressEvent(self, _):
        """Placeholder to accept mouse press events"""

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.select()
        elif event.button() == Qt.MiddleButton:
            self.remove()

    def copy_flickr_tags(self):
        QApplication.clipboard().setText(self.metadata.keyword_meta.flickr_tags)
        id_str = (
            f'observation {self.metadata.observation_id}'
            if self.metadata.has_observation
            else f'taxon {self.metadata.taxon_id}'
        )
        self.pulse()
        self.on_copy.emit(f'Tags for {id_str} copied to clipboard')

    def pulse(self):
        """Show a highlight animation to indicate the image has been updated"""
        # Color pulse
        self.color_effect = QGraphicsColorizeEffect()
        self.color_effect.setColor(self.palette().highlight().color())
        self.label.setGraphicsEffect(self.color_effect)
        color_anim = QPropertyAnimation(self.color_effect, b'strength')
        color_anim.setStartValue(1)
        color_anim.setEndValue(0)
        color_anim.setDuration(1000)
        color_anim.setEasingCurve(QEasingCurve.OutQuad)

        # Check mark icon
        self.op_effect = QGraphicsOpacityEffect()
        self.check.setGraphicsEffect(self.op_effect)
        self.check.setVisible(True)
        op_anim = QPropertyAnimation(self.op_effect, b'opacity')
        op_anim.setStartValue(1)
        op_anim.setEndValue(0)
        op_anim.setDuration(1000)
        op_anim.setEasingCurve(QEasingCurve.InQuad)

        # Group animations and start all
        self.anim_group = QParallelAnimationGroup()
        self.anim_group.addAnimation(color_anim)
        self.anim_group.addAnimation(op_anim)
        self.anim_group.finished.connect(lambda: self.label.setGraphicsEffect(None))
        self.anim_group.start()

    def remove(self):
        self.on_remove.emit(self.image_path)

    def select(self):
        logger.debug(f'Selecting image {self.image_path}')
        self.on_select.emit(self.image_path)

    def update_metadata(self, metadata: MetaMetadata):
        self.pulse()
        self.metadata = metadata
        self.icons.refresh_icons(metadata)
        self.setToolTip(f'{self.image_path}\n{self.metadata.summary}')
        self.context_menu.refresh_actions(metadata)

    def open_directory(self):
        QDesktopServices.openUrl(QUrl(self.image_path.parent.as_uri()))


class ThumbnailContextMenu(QMenu):
    """Context menu for local image thumbnails"""

    on_select_taxon = Signal(int)  #: A taxon was selected from context menu

    def __init__(self, thumbnail: LocalThumbnail):
        super().__init__()
        self.thumbnail = thumbnail
        self.refresh_actions(thumbnail.metadata)

    def refresh_actions(self, meta: MetaMetadata):
        """Update menu actions based on the available metadata"""
        self.clear()

        self._add_action(
            icon='fa5s.spider',
            text='View Taxon',
            tooltip=f'View taxon {meta.taxon_id} in naturtag',
            enabled=meta.has_taxon,
            callback=lambda: self.on_select_taxon.emit(meta.taxon_id),
        )
        self._add_action(
            icon='fa5s.spider',
            text='View Taxon on iNat',
            tooltip=f'View taxon {meta.taxon_id} on inaturalist.org',
            enabled=meta.has_taxon,
            callback=lambda: webbrowser.open(meta.taxon_url),
        )
        self._add_action(
            icon='fa.binoculars',
            text='View Observation on iNat',
            tooltip=f'View observation {meta.observation_id} on inaturalist.org',
            enabled=meta.has_observation,
            callback=lambda: webbrowser.open(meta.observation_url),
        )
        self._add_action(
            icon='fa5.copy',
            text='Copy Flickr tags',
            tooltip='Copy Flickr-compatible taxon tags to clipboard',
            enabled=meta.has_taxon,
            callback=self.thumbnail.copy_flickr_tags,
        )
        self._add_action(
            icon='fa5s.folder-open',
            text='Open containing folder',
            tooltip=f'Open containing folder: {self.thumbnail.image_path.parent}',
            callback=self.thumbnail.open_directory,
        )
        self._add_action(
            icon='fa.remove',
            text='Remove image',
            tooltip='Remove this image from the selection',
            callback=self.thumbnail.remove,
        )

    def _add_action(
        self, icon: str, text: str, tooltip: str, enabled: bool = True, callback: Callable = None
    ):
        action = QAction(fa_icon(icon), text, self.thumbnail)
        action.setStatusTip(tooltip)
        action.setEnabled(enabled)
        if callback:
            action.triggered.connect(callback)
        self.addAction(action)


class ThumbnailMetaIcons(QLabel):
    """Icons overlaid on top of a thumbnail to indicate what types of metadata are available"""

    def __init__(self, parent: LocalThumbnail):
        super().__init__(parent)
        img_size = parent.image.sizeHint()

        self.icon_layout = HorizontalLayout(self)
        self.icon_layout.setAlignment(Qt.AlignLeft)
        self.icon_layout.setContentsMargins(0, 0, 0, 0)
        self.setGeometry(9, img_size.height() - 11, 116, 20)

        self.taxon_icon = IconLabel('mdi.bird', primary=True, size=20)
        self.observation_icon = IconLabel('fa.binoculars', primary=True, size=20)
        self.geo_icon = IconLabel('fa.map-marker', primary=True, size=20)
        self.tag_icon = IconLabel('fa.tags', primary=True, size=20)
        self.sidecar_icon = IconLabel('mdi.xml', primary=True, size=20)
        self.icon_layout.addWidget(self.taxon_icon)
        self.icon_layout.addWidget(self.observation_icon)
        self.icon_layout.addWidget(self.geo_icon)
        self.icon_layout.addWidget(self.tag_icon)
        self.icon_layout.addWidget(self.sidecar_icon)

        self.refresh_icons(parent.metadata)

    def refresh_icons(self, meta: MetaMetadata):
        """Update icons based on the available metadata"""
        logger.debug(f'Refreshing: {meta}')
        self.taxon_icon.set_enabled(meta.has_taxon)
        self.observation_icon.set_enabled(meta.has_observation)
        self.geo_icon.set_enabled(meta.has_coordinates)
        self.tag_icon.set_enabled(meta.has_any_tags)
        self.sidecar_icon.set_enabled(meta.has_sidecar)
