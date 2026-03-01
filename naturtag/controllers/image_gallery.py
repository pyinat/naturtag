# TODO: Placeholder "spinner" for loading images
import re
import webbrowser
from logging import getLogger
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Iterable, Optional

from PySide6.QtCore import (
    QEasingCurve,
    QParallelAnimationGroup,
    QPropertyAnimation,
    Qt,
    QUrl,
    Signal,
    Slot,
)
from PySide6.QtGui import QAction, QDesktopServices, QDropEvent, QImage, QPixmap
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
from shiboken6 import isValid

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
from naturtag.widgets.images import HoverMixin, PixmapLabel, SwappableIcon
from naturtag.widgets.style import RED, fa_icon

if TYPE_CHECKING:
    from naturtag.app.threadpool import ThreadPool

logger = getLogger(__name__)


class ImageGallery(BaseController):
    """Container for displaying local image thumbnails & info"""

    on_load_images = Signal(list)  #: New images have been loaded
    on_view_taxon_id = Signal(int)  #: A taxon was selected from context menu
    on_view_observation_id = Signal(int)  #: An observation was selected from context menu

    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.images: dict[Path, ThumbnailCard] = {}
        self._pending_signal = None
        self._current_pending: frozenset[str] = frozenset()
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
        root.addWidget(scroll_area)

        # Help text
        help = QWidget()
        help.setContentsMargins(5, 10, 5, 10)
        help_layout = HorizontalLayout(help)
        help_layout.setAlignment(Qt.AlignLeft)
        self.flow_layout.addWidget(help)
        help_msg = QLabel(
            'Select local photos to tag.\n'
            'Drag and drop files onto the window,\n'
            'or use the file browser (Ctrl+O).'
        )
        help_layout.addWidget(FAIcon('ei.info-circle'))
        help_layout.addWidget(help_msg)

    def clear(self):
        """Clear all images from the viewer"""
        self.images = {}
        self.flow_layout.clear()

    def load_file_dialog(self, start_dir: Optional[PathOrStr] = None):
        """Show a file chooser dialog"""
        image_paths, _ = QFileDialog.getOpenFileNames(
            self,
            caption='Open image files:',
            dir=str(start_dir or self.app.settings.start_image_dir),
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
            thumbnail_card.load_image_async(self.app.threadpool)

        self.on_load_images.emit(new_images)

    def load_image(self, image_path: Path, delayed_load: bool = False) -> Optional['ThumbnailCard']:
        """Load an image"""
        if not image_path.is_file():
            logger.debug(f'File does not exist: {image_path}')
            return None
        elif image_path in self.images:
            logger.debug(f'Image already loaded: {image_path}')
            return None

        # Clear initial help text if still present
        if not self.images:
            self.flow_layout.clear()

        logger.info(f'Loading {image_path}')
        thumbnail_card = ThumbnailCard(image_path)
        thumbnail_card.on_loaded.connect(self._bind_image_actions)
        thumbnail_card.on_load_error.connect(self.on_message)
        if self._pending_signal is not None:
            thumbnail_card.set_pending(bool(self._current_pending))
            thumbnail_card.set_pending_icons(self._current_pending)
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
        thumbnail.context_menu.on_view_taxon_id.connect(self.on_view_taxon_id)
        thumbnail.context_menu.on_view_observation_id.connect(self.on_view_observation_id)
        # Note: pending state is sent to all cards via _update_pending_state; no signal needed here

    def connect_pending_signal(self, signal: Signal):
        """Connect a signal for pending tag state updates to all current and future thumbnails."""
        self._pending_signal = signal
        signal.connect(self._update_pending_state)

    def _update_pending_state(self, pending: frozenset[str]):
        self._current_pending = pending
        for card in self.images.values():
            card.set_pending(bool(pending))
            card.set_pending_icons(pending)

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
    on_load_error = Signal(str)  #: Error message when image loading fails
    on_remove = Signal(Path)  #: Request for the image to be removed from the gallery
    on_select = Signal(Path)  #: The image was clicked

    def __init__(self, image_path: Path, size: Dimensions = SIZE_DEFAULT):
        super().__init__()
        self.image_path = image_path
        self.metadata: MetaMetadata = None  # type: ignore
        self.layout = VerticalLayout(self)

        # Image
        self.image = MetaThumbnail(self, size=size)
        self.layout.addWidget(self.image)

        self.context_menu = ThumbnailContextMenu(self)
        self.icons = ThumbnailMetaIcons(self)
        self.icons.setObjectName('metadata_icons')

        # Filename label
        text = re.sub('([_-])', '\\1\u200b', self.image_path.name)  # To allow word wrapping
        self.label = QLabel(text)
        self.label.setMaximumWidth(SIZE_DEFAULT[0])
        self.label.setMinimumHeight(40)
        self.label.setAlignment(Qt.AlignLeft)
        self.label.setWordWrap(True)
        self.layout.addWidget(self.label)

        # Icon shown when an image is tagged or updated
        self.check = FAIcon('fa5s.check', parent=self.image, secondary=True, size=SIZE_DEFAULT)
        self.check.setVisible(False)

    def load_image(self):
        """Load thumbnail + metadata in the main thread"""
        image, metadata, error = self.image.get_pixmap_meta(self.image_path)
        self.image.setPixmap(QPixmap.fromImage(image) if image else QPixmap())
        if error:
            self.set_load_error(error)
        self.set_metadata(metadata)

    def load_image_async(self, threadpool: 'ThreadPool'):
        """Load thumbnail + metadata in a separate thread"""
        self.image.set_pixmap_meta_async(threadpool, self.image_path)
        self.image.on_load_metadata.connect(self.set_metadata)
        self.image.on_load_error.connect(self.set_load_error)

    def set_load_error(self, error: str):
        """Show error icon on thumbnail when image loading fails."""
        self.icons.set_error(error)
        self.on_load_error.emit(error)

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
        if (
            hasattr(self, 'anim_group')
            and self.anim_group.state() == QParallelAnimationGroup.Running
        ):
            self.anim_group.stop()

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

    def set_pending(self, pending: bool):
        """Show or hide the pending tags icon."""
        self.icons.set_pending(pending)

    def set_pending_icons(self, pending: frozenset[str]):
        """Switch metadata icons to primary color for each pending type."""
        self.icons.set_pending_icons(pending)

    def update_metadata(self, metadata: MetaMetadata):
        """Update UI based on new metadata, and show a highlight animation"""
        self.icons.set_pending(False)
        self.pulse()
        self.set_metadata(metadata)


class MetaThumbnail(HoverMixin, PixmapLabel):
    """Thumbnail for a local image plus metadata"""

    on_load_metadata = Signal(MetaMetadata)  #: Finished reading image metadata
    on_load_error = Signal(str)  #: Error message when image loading fails

    def __init__(self, parent: QWidget, size: Dimensions = SIZE_DEFAULT):
        # We will generate a thumbnail of final size; no scaling needed
        super().__init__(parent, rounded=True, scale=False)
        self.thumbnail_size = size
        self.setFixedSize(*size)

    def get_pixmap_meta(self, path: PathOrStr) -> tuple[QImage | None, MetaMetadata, str | None]:
        """All I/O for loading an image preview (reading metadata, generating thumbnail),
        to be run from a separate thread. Returns QImage (thread-safe) instead of QPixmap.
        """
        error = None
        try:
            image = generate_thumbnail(path, self.thumbnail_size)
        except Exception as e:
            logger.warning(f'Error generating thumbnail for {path}:', exc_info=True)
            image = None
            error = str(e)
        return image, MetaMetadata(path), error

    def set_pixmap_meta_async(self, threadpool: 'ThreadPool', path: Optional[PathOrStr] = None):
        """Generate a photo thumbnail and read its metadata from a separate thread, and render it
        in the main thread when complete
        """
        future = threadpool.schedule(self.get_pixmap_meta, path=path)
        future.on_result.connect(self.set_pixmap_meta)

    def set_pixmap_meta(self, image_meta: tuple[QImage | None, MetaMetadata, str | None]):
        if not isValid(self):
            return
        image, metadata, error = image_meta
        self.setPixmap(QPixmap.fromImage(image) if image else QPixmap())
        if error:
            self.on_load_error.emit(error)
        self.on_load_metadata.emit(metadata)


class ThumbnailContextMenu(QMenu):
    """Context menu for local image thumbnails"""

    on_view_taxon_id = Signal(int)  #: A taxon was selected from context menu
    on_view_observation_id = Signal(int)  #: An observation was selected from context menu

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
            callback=lambda: self.on_view_taxon_id.emit(meta.taxon_id),
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
            icon='fa6s.binoculars',
            text='View Observation',
            tooltip=f'View observation {meta.observation_id} in naturtag',
            enabled=meta.has_observation,
            callback=lambda: self.on_view_observation_id.emit(meta.observation_id),
        )
        self._add_action(
            parent=thumbnail_card,
            icon='fa6s.binoculars',
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
            icon='ei.remove',
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
        callback: Optional[Callable] = None,
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
        self.setGeometry(9, img_size[0] - 11, 130, 20)

        # Main metadata icons
        self.taxon_icon = SwappableIcon('mdi.bird', secondary=True, size=20)
        self.observation_icon = SwappableIcon('fa6s.binoculars', secondary=True, size=20)
        self.geo_icon = SwappableIcon('mdi.map-marker', secondary=True, size=20)
        self.tag_icon = SwappableIcon('fa6s.tags', secondary=True, size=20)
        self.sidecar_icon = SwappableIcon('mdi.xml', secondary=True, size=20)
        self.icon_layout.addWidget(self.taxon_icon)
        self.icon_layout.addWidget(self.observation_icon)
        self.icon_layout.addWidget(self.geo_icon)
        self.icon_layout.addWidget(self.tag_icon)
        self.icon_layout.addWidget(self.sidecar_icon)

        # Pending tags indicator — parented to the image widget so coordinates are image-relative
        self.pending_container, self.pending_icon = self._create_icon_container(
            parent.image, 'fa6s.floppy-disk', img_size[0] - 40, img_size[1] - 40
        )
        self.pending_icon.setToolTip('Pending tags: click Run (Ctrl+R) to apply')

        # Error indicator — centered in the thumbnail
        icon_size = 128
        x = (img_size[0] - icon_size) // 2
        y = (img_size[1] - icon_size) // 2
        self.error_container, self.error_icon = self._create_icon_container(
            parent.image, 'fa6s.triangle-exclamation', x, y, size=icon_size, color=RED
        )

    def _create_icon_container(
        self,
        parent_image: QLabel,
        icon_name: str,
        x: int,
        y: int,
        size: int = 40,
        color: str | None = None,
    ) -> tuple[QLabel, FAIcon]:
        container = QLabel(parent_image)
        container.setObjectName('metadata_icons')
        layout = HorizontalLayout(container)
        layout.setAlignment(Qt.AlignCenter)
        layout.setContentsMargins(0, 0, 0, 0)
        container.setGeometry(x, y, size, size)
        container.setVisible(False)
        icon = FAIcon(icon_name, size=size, color=color)
        layout.addWidget(icon)
        return container, icon

    def set_error(self, error: str | None):
        """Show or hide the error icon, with error message as tooltip."""
        self.error_container.setVisible(bool(error))
        self.error_icon.setToolTip(f'Error loading image: {error}' if error else '')

    def set_pending(self, pending: bool):
        """Show or hide the pending tags indicator."""
        self.pending_container.setVisible(pending)

    def set_pending_icons(self, pending: frozenset[str]):
        """Switch icons to primary color for each pending metadata type."""
        self.taxon_icon.set_primary('taxon' in pending)
        self.observation_icon.set_primary('observation' in pending)
        self.geo_icon.set_primary('geo' in pending)
        self.tag_icon.set_primary('tags' in pending)
        self.sidecar_icon.set_primary('sidecar' in pending)

    def refresh_icons(self, metadata: MetaMetadata):
        """Update icons based on the available metadata"""
        # Reset any pending primary highlighting first
        self.set_pending_icons(frozenset())
        self.taxon_icon.set_enabled(metadata.has_taxon)
        self.observation_icon.set_enabled(metadata.has_observation)
        self.geo_icon.set_enabled(metadata.has_coordinates)
        self.tag_icon.set_enabled(metadata.has_any_tags)
        self.sidecar_icon.set_enabled(metadata.has_sidecar)
