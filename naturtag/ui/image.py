""" Classes to extend image container functionality for caching, metadata, etc. """
from kivy.properties import ObjectProperty
from kivy.uix.image import AsyncImage
from kivymd.uix.imagelist import SmartTile
from kivymd.uix.imagelist import SmartTileWithLabel

from naturtag.ui.thumbnails import get_thumbnail_if_exists, cache_async_thumbnail


class IconicTaxaIcon(SmartTile):
    box_color = (0, 0, 0, 0)


class CachedAsyncImage(AsyncImage):
    """ AsyncImage which, once loaded, caches the image for future use """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.has_thumbnail = False

    def _load_source(self, *args):
        # Before downloading remote image, first check for existing thumbnail
        thumbnail_path = get_thumbnail_if_exists(self.source)
        if thumbnail_path:
            self.has_thumbnail = True
            self.source = thumbnail_path
        super()._load_source(*args)

    def on_load(self, *args):
        """ After loading, cache the downloaded image for future use, if not previously done """
        if self._coreimage.image.texture and not self.has_thumbnail:
            cache_async_thumbnail(self, large=True)


class ImageMetaTile(SmartTileWithLabel):
    """ Class that contains an image thumbnail to display plus its associated metadata """
    metadata = ObjectProperty()
    allow_stretch = False
    box_color = [0, 0, 0, 0.4]

    def __init__(self, metadata, **kwargs):
        super().__init__(**kwargs)
        self.metadata = metadata
