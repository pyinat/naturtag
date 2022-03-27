""" Classes to extend image container functionality for caching, metadata, etc. """
from io import BytesIO
from logging import getLogger

import requests
from kivy.core.clipboard import Clipboard
from kivy.core.image import Image as CoreImage
from kivy.properties import BooleanProperty, ObjectProperty
from kivy.uix.image import AsyncImage
from kivymd.uix.imagelist import SmartTile, SmartTileWithLabel

from naturtag.app import alert
from naturtag.models import MetaMetadata, get_icon_path
from naturtag.thumbnails import (
    generate_thumbnail_from_bytes,
    get_format,
    get_thumbnail,
    get_thumbnail_if_exists,
)

logger = getLogger().getChild(__name__)

DESELECTED_COLOR = (0, 0, 0, 0)
SELECTED_COLOR = (0.2, 0.6, 0.6, 0.4)


# TODO: Caching
# TODO: Run in background thread
# TODO: Placeholder image or spinner
class CustomImage(AsyncImage):
    def __init__(self, source: str = None, **kwargs):
        super().__init__(source='', **kwargs)
        response = requests.get(source)
        ext = source.split('.')[-1]
        img_data = BytesIO(response.content)

        self.texture = CoreImage(img_data, ext=ext).texture
        self.reload()


class CachedAsyncImage(AsyncImage):
    """AsyncImage which, once loaded, caches the image for future use"""

    def __init__(self, thumbnail_size: str = 'large', source: str = None, **kwargs):
        """
        Args:
            size : Size of thumbnail to cache
        """
        self.thumbnail_size = thumbnail_size
        self.thumbnail_path = None
        logger.debug(f'CachedAsyncImage: Loading image: {source}')
        super().__init__(source=source, **kwargs)

    def _load_source(self, *args):
        """Before downloading remote image, first check for existing thumbnail"""
        # Differentiating between None and '' here to handle on_load being triggered multiple times
        if self.thumbnail_path is None:
            self.thumbnail_path = get_thumbnail_if_exists(self.source) or ''
            if self.thumbnail_path:
                logger.debug(f'CachedAsyncImage: Found {self.source} in cache: {self.thumbnail_path}')
                self.source = self.thumbnail_path
        super()._load_source(*args)

    def on_load(self, *args):
        """After loading, cache the downloaded image for future use, if not previously done"""
        if not get_thumbnail_if_exists(self.source):
            image_bytes, _ = self.get_image_bytes()
            generate_thumbnail_from_bytes(image_bytes, self.source, size=self.thumbnail_size)

    def get_image_bytes(self):
        if not (self._coreimage.image and self._coreimage.image.texture):
            logger.warning(f'CachedAsyncImage: Texture for {self.source} not loaded')
            return None

        # thumbnail_path = get_thumbnail_path(self.source)
        ext = get_format(self.source)
        logger.debug(f'CachedAsyncImage: Getting image data from {self.source}; format {ext}')

        # Load inner 'texture' bytes into a file-like object that PIL can read
        image_bytes = BytesIO()
        self._coreimage.image.texture.save(image_bytes, fmt=ext)
        return image_bytes, ext


class IconicTaxaIcon(SmartTile):
    """Icon for an iconic taxon"""

    is_selected = BooleanProperty()

    def __init__(self, taxon_id, **kwargs):
        super().__init__(source=get_icon_path(taxon_id), **kwargs)
        self.is_selected = False
        self.box_color = DESELECTED_COLOR
        self.taxon_id = taxon_id
        self.bind(on_release=self.toggle_selection)

    def toggle_selection(self, *args):
        """Toggle between selected and deselected when clicked. The SmartTile overlay can be
        conveniently repurposed as a background, since the icon is so small the overlay covers it
        """
        if self.is_selected:
            self.box_color = DESELECTED_COLOR
            self.is_selected = False
        else:
            self.box_color = SELECTED_COLOR
            self.is_selected = True


class ImageMetaTile(SmartTileWithLabel):
    """Class that contains an image thumbnail to display plus its associated metadata"""

    metadata = ObjectProperty()

    def __init__(self, source, **kwargs):
        super().__init__(source=get_thumbnail(source), **kwargs)
        self.original_source = source
        self.metadata = MetaMetadata(source)

    def copy_flickr_tags(self, *args):
        Clipboard.copy(self.metadata.keyword_meta.flickr_tags)
        alert('Tags copied to clipboard')

    def on_metadata(self, *args):
        """Triggered whenever metadata changes"""
        self.text = self.metadata.summary
        self.set_box_color()

    def set_box_color(self):
        """Set the color of the image overlay box based on its metadata"""

        def set_alpha(rgba, alpha):
            return rgba[:3] + [alpha]

        if self.metadata.observation_id:
            self.box_color = set_alpha(self.theme_cls.accent_color, 0.6)
        elif self.metadata.has_taxon:
            self.box_color = set_alpha(self.theme_cls.primary_color, 0.5)
        else:
            self.box_color = (0, 0, 0, 0.5)
