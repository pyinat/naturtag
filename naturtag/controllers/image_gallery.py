# TODO: Placeholder "spinner" for loading images
import re
import webbrowser
from logging import getLogger
from pathlib import Path
from typing import Callable, Iterable, Optional

from PySide6.QtCore import (
    QEasingCurve,
    QParallelAnimationGroup,
    QPropertyAnimation,
    Qt,
    QUrl,
    Signal,
    Slot,
)
from PySide6.QtGui import QAction, QDesktopServices, QDropEvent, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QGraphicsColorizeEffect,
    QGraphicsOpacityEffect,
    QLabel,
    QMenu,
    QScrollArea,
    QWidget,
)

from naturtag.app.style import fa_icon
from naturtag.app.threadpool import ThreadPool
from naturtag.constants import IMAGE_FILETYPES, SIZE_DEFAULT, Dimensions, PathOrStr
from naturtag.controllers import BaseController
from naturtag.metadata import MetaMetadata
from naturtag.utils import generate_thumbnail, get_valid_image_paths
from naturtag.widgets import (
    FAIcon,
    FlowLayout,
    HorizontalLayout,
    ImageWindow,
    StylableWidget,
    VerticalLayout,
)
from naturtag.widgets.images import HoverMixin, PixmapLabel

logger = getLogger(__name__)


class ImageGallery(BaseController):
    """Container for displaying local image thumbnails & info"""

    on_load_images = Signal(list)  #: New images have been loaded
    on_select_taxon = Signal(int)  #: A taxon was selected from context menu
    on_select_observation = Signal(int)  #: An observation was selected from context menu

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setAcceptDrops(True)
        self.images: dict[Path, ThumbnailCard] = {}
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

    def load_file_dialog(self, start_dir: PathOrStr = None):
        """Show a file chooser dialog"""
        image_paths, _ = QFileDialog.getOpenFileNames(
            self,
            caption='Open image files:',
            dir=str(start_dir or self.settings.start_image_dir),
            filter=f'Image files ({" ".join(IMAGE_FILETYPES)})',
        )
        self.load_images(image_paths)

    def load_images(self, image_paths: Iterable[PathOrStr]):
        """Load multiple images, and ignore any duplicates"""
        images = get_valid_image_paths(image_paths, recursive=True)
        new_images = sorted(images - set(self.images.keys()))
        if not new_images:
            return

        # Load blank placeholder cards first
        logger.info(f'Loading {len(new_images)} ({len(images) - len(new_images)} already loaded)')
        cards = [self.load_image(image_path, delayed_load=True) for image_path in new_images]

        # Then load actual images
        for thumbnail_card in filter(None, cards):
            thumbnail_card.load_image_async(self.threadpool)

        self.on_load_images.emit(new_images)

    def load_image(self, image_path: Path, delayed_load: bool = False) -> Optional['ThumbnailCard']:
        """Load an image"""
        if not image_path.is_file():
            logger.info(f'File does not exist: {image_path}')
            return None
        elif image_path in self.images:
            logger.info(f'Image already loaded: {image_path}')
            return None

        logger.info(f'Loading {image_path}')
        thumbnail_card = ThumbnailCard(image_path)
        thumbnail_card.on_loaded.connect(self._bind_image_actions)
        self.flow_layout.addWidget(thumbnail_card)
        self.images[thumbnail_card.image_path] = thumbnail_card

        if not delayed_load:
            thumbnail_card.load_image()
        return thumbnail_card

    def _bind_image_actions(self, thumbnail: 'ThumbnailCard'):
        """Bind actions to an image"""
        thumbnail.on_remove.connect(self.remove_image)
        thumbnail.on_select.connect(self.select_image)
        thumbnail.on_copy.connect(self.on_message)
        thumbnail.context_menu.on_select_taxon.connect(self.on_select_taxon)
        thumbnail.context_menu.on_select_observation.connect(self.on_select_observation)

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
        self.image_window.display_image_fullscreen(image_path, list(self.images.keys()))


class ThumbnailCard(StylableWidget):
    """A card that displays a thumbnail for a local image file, along with a title and icons
    representing its metadata contents. Also adds the following mouse actions:

    * Left click: Show full image
    * Middle click: Remove image
    * Right click: Show context menu
    """

    on_loaded = Signal(object)  #: Image and metadata have been loaded
    on_copy = Signal(str)  #: Tags were copied to the clipboard
    on_remove = Signal(Path)  #: Request for the image to be removed from the gallery
    on_select = Signal(Path)  #: The image was clicked

    def __init__(self, image_path: Path, size: Dimensions = SIZE_DEFAULT):
        super().__init__()
        self.image_path = image_path
        self.metadata: MetaMetadata = None  # type: ignore
        layout = VerticalLayout(self)

        # Image
        self.image = MetaThumbnail(self, size=size)
        layout.addWidget(self.image)

        self.context_menu = ThumbnailContextMenu(self)
        self.icons = ThumbnailMetaIcons(self)
        self.icons.setObjectName('metadata-icons')

        # Filename label
        text = re.sub('([_-])', '\\1\u200b', self.image_path.name)  # To allow word wrapping
        self.label = QLabel(text)
        self.label.setMaximumWidth(SIZE_DEFAULT[0])
        self.label.setMinimumHeight(40)
        self.label.setAlignment(Qt.AlignLeft)
        self.label.setWordWrap(True)
        layout.addWidget(self.label)

        # Icon shown when an image is tagged or updated
        self.check = FAIcon('fa5s.check', self.image, secondary=True, size=SIZE_DEFAULT[0])
        self.check.setVisible(False)

    def load_image(self):
        """Load thumbnail + metadata in the main thread"""
        pixmap, metadata = self.image.get_pixmap_meta()
        self.image.setPixmap(pixmap)
        self.set_metadata(metadata)

    def load_image_async(self, threadpool: ThreadPool):
        """Load thumbnail + metadata in a separate thread"""
        self.image.set_pixmap_meta_async(threadpool, self.image_path)
        self.image.on_load_metadata.connect(self.set_metadata)

    def set_metadata(self, metadata: MetaMetadata):
        """Update UI based on new metadata"""
        logger.debug(f'New metadata: {metadata}')
        self.metadata = metadata
        self.context_menu.refresh_actions(self)
        self.icons.refresh_icons(metadata)
        self.setToolTip(metadata.summary)
        self.on_loaded.emit(self)

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

    def open_directory(self):
        QDesktopServices.openUrl(QUrl(self.image_path.parent.as_uri()))

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
        """Update UI based on new metadata, and show a highlight animation"""
        self.pulse()
        self.set_metadata(metadata)


class MetaThumbnail(HoverMixin, PixmapLabel):
    """Thumbnail for a local image plus metadata"""

    on_load_metadata = Signal(MetaMetadata)  #: Finished reading image metadata

    def __init__(self, parent: QWidget, size: Dimensions = SIZE_DEFAULT):
        # We will generate a thumbnail of final size; no scaling needed
        super().__init__(parent, scale=False)
        self.thumbnail_size = size
        self.setFixedSize(*size)

    def get_pixmap_meta(self, path: PathOrStr) -> tuple[QPixmap, MetaMetadata]:
        """All I/O for loading an image preview (reading metadata, generating thumbnail),
        to be run from a separate thread
        """
        return generate_thumbnail(path, self.thumbnail_size), MetaMetadata(path)

    def set_pixmap_meta_async(self, threadpool: ThreadPool, path: PathOrStr = None):
        """Generate a photo thumbnail and read its metadata from a separate thread, and render it
        in the main thread when complete
        """
        future = threadpool.schedule(self.get_pixmap_meta, path=path)
        future.on_result.connect(self.set_pixmap_meta)

    def set_pixmap_meta(self, pixmap_meta: tuple[QPixmap, MetaMetadata]):
        pixmap, metadata = pixmap_meta
        self.setPixmap(pixmap)
        self.on_load_metadata.emit(metadata)


class ThumbnailContextMenu(QMenu):
    """Context menu for local image thumbnails"""

    on_select_taxon = Signal(int)  #: A taxon was selected from context menu
    on_select_observation = Signal(int)  #: An observation was selected from context menu

    def refresh_actions(self, thumbnail_card: ThumbnailCard):
        """Update menu actions based on the available metadata"""
        self.clear()
        meta = thumbnail_card.metadata

        self._add_action(
            parent=thumbnail_card,
            icon='fa5s.spider',
            text='View Taxon',
            tooltip=f'View taxon {meta.taxon_id} in naturtag',
            enabled=meta.has_taxon,
            callback=lambda: self.on_select_taxon.emit(meta.taxon_id),
        )
        self._add_action(
            parent=thumbnail_card,
            icon='fa5s.spider',
            text='View Taxon on iNat',
            tooltip=f'View taxon {meta.taxon_id} on inaturalist.org',
            enabled=meta.has_taxon,
            callback=lambda: webbrowser.open(meta.taxon_url),
        )
        self._add_action(
            parent=thumbnail_card,
            icon='fa.binoculars',
            text='View Observation',
            tooltip=f'View observation {meta.observation_id} in naturtag',
            enabled=meta.has_observation,
            callback=lambda: self.on_select_observation.emit(meta.observation_id),
        )
        self._add_action(
            parent=thumbnail_card,
            icon='fa.binoculars',
            text='View Observation on iNat',
            tooltip=f'View observation {meta.observation_id} on inaturalist.org',
            enabled=meta.has_observation,
            callback=lambda: webbrowser.open(meta.observation_url),
        )
        self._add_action(
            parent=thumbnail_card,
            icon='fa5.copy',
            text='Copy Flickr tags',
            tooltip='Copy Flickr-compatible taxon tags to clipboard',
            enabled=meta.has_taxon,
            callback=thumbnail_card.copy_flickr_tags,
        )
        self._add_action(
            parent=thumbnail_card,
            icon='fa5s.folder-open',
            text='Open containing folder',
            tooltip=f'Open containing folder: {thumbnail_card.image_path.parent}',
            callback=thumbnail_card.open_directory,
        )
        self._add_action(
            parent=thumbnail_card,
            icon='fa.remove',
            text='Remove image',
            tooltip='Remove this image from the selection',
            callback=thumbnail_card.remove,
        )

    def _add_action(
        self,
        parent: QWidget,
        icon: str,
        text: str,
        tooltip: str,
        enabled: bool = True,
        callback: Callable = None,
    ):
        action = QAction(fa_icon(icon), text, parent)
        action.setStatusTip(tooltip)
        action.setEnabled(enabled)
        if callback:
            action.triggered.connect(callback)
        self.addAction(action)


class ThumbnailMetaIcons(QLabel):
    """Icons overlaid on top of a thumbnail to indicate what types of metadata are available"""

    def __init__(self, parent: ThumbnailCard):
        super().__init__(parent)
        img_size = SIZE_DEFAULT

        self.icon_layout = HorizontalLayout(self)
        self.icon_layout.setAlignment(Qt.AlignLeft)
        self.icon_layout.setContentsMargins(0, 0, 0, 0)
        self.setGeometry(9, img_size[0] - 11, 116, 20)

        self.taxon_icon = FAIcon('mdi.bird', secondary=True, size=20)
        self.observation_icon = FAIcon('fa.binoculars', secondary=True, size=20)
        self.geo_icon = FAIcon('mdi.map-marker', secondary=True, size=20)
        self.tag_icon = FAIcon('fa.tags', secondary=True, size=20)
        self.sidecar_icon = FAIcon('mdi.xml', secondary=True, size=20)
        self.icon_layout.addWidget(self.taxon_icon)
        self.icon_layout.addWidget(self.observation_icon)
        self.icon_layout.addWidget(self.geo_icon)
        self.icon_layout.addWidget(self.tag_icon)
        self.icon_layout.addWidget(self.sidecar_icon)

    def refresh_icons(self, metadata: MetaMetadata):
        """Update icons based on the available metadata"""
        self.taxon_icon.set_enabled(metadata.has_taxon)
        self.observation_icon.set_enabled(metadata.has_observation)
        self.geo_icon.set_enabled(metadata.has_coordinates)
        self.tag_icon.set_enabled(metadata.has_any_tags)
        self.sidecar_icon.set_enabled(metadata.has_sidecar)
