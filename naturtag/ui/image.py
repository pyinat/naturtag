""" Classes to extend image container functionality for caching, metadata, etc. """
from io import BytesIO
from logging import getLogger

from kivy.properties import ObjectProperty
from kivy.uix.image import AsyncImage
from kivymd.uix.imagelist import SmartTile, SmartTileWithLabel
from kivymd.uix.list import ThreeLineAvatarIconListItem, ILeftBody
from kivymd.uix.tooltip import MDTooltip

from naturtag.models import Taxon, get_icon_path
from naturtag.thumbnails import get_thumbnail_if_exists, get_format
from naturtag.ui.cache import cache_async_thumbnail

logger = getLogger().getChild(__name__)


class CachedAsyncImage(AsyncImage):
    """ AsyncImage which, once loaded, caches the image for future use """
    def __init__(self, thumbnail_size='large', **kwargs):
        """
        Args:
            size (str) : Size of thumbnail to cache
        """
        self.thumbnail_size = thumbnail_size
        self.thumbnail_path = None
        super().__init__(**kwargs)

    def _load_source(self, *args):
        """ Before downloading remote image, first check for existing thumbnail """
        # Differentiating between None and '' here to handle on_load being triggered multiple times
        if self.thumbnail_path is None:
            self.thumbnail_path = get_thumbnail_if_exists(self.source) or ''
            if self.thumbnail_path:
                logger.debug(f'Found {self.source} in cache: {self.thumbnail_path}')
                self.source = self.thumbnail_path
        super()._load_source(*args)

    def on_load(self, *args):
        """ After loading, cache the downloaded image for future use, if not previously done """
        if not get_thumbnail_if_exists(self.source):
            cache_async_thumbnail(self, size=self.thumbnail_size)

    def get_image_bytes(self):
        if not (self._coreimage.image and self._coreimage.image.texture):
            logger.warning(f'Texture for {self.source} not loaded')
            return None

        # thumbnail_path = get_thumbnail_path(self.source)
        ext = get_format(self.source)
        logger.debug(f'Getting image data downloaded from {self.source}; format {ext}')

        # Load inner 'texture' bytes into a file-like object that PIL can read
        image_bytes = BytesIO()
        self._coreimage.image.texture.save(image_bytes, fmt=ext)
        return image_bytes, ext


class IconicTaxaIcon(SmartTile):
    box_color = (0, 0, 0, 0)

    def __init__(self, taxon_id, **kwargs):
        self.taxon_id = taxon_id
        super().__init__(source=get_icon_path(taxon_id), **kwargs)


class ImageMetaTile(SmartTileWithLabel):
    """ Class that contains an image thumbnail to display plus its associated metadata """
    metadata = ObjectProperty()
    allow_stretch = False
    box_color = [0, 0, 0, 0.4]

    def __init__(self, metadata, **kwargs):
        super().__init__(**kwargs)
        self.metadata = metadata


class TaxonListItem(ThreeLineAvatarIconListItem, MDTooltip):
    """ Class that displays condensed taxon info as a list item """
    def __init__(self, taxon=None, taxon_id=None, button_callback=None, **kwargs):
        if not taxon and not taxon_id:
            raise ValueError('Must provide either a taxon object or ID')
        taxon = taxon or Taxon.from_id(taxon_id)

        super().__init__(
            font_style='H6',
            text=taxon.name,
            secondary_text=taxon.rank,
            tertiary_text=taxon.preferred_common_name,
            tooltip_text=f'ID: {taxon.id}\nAncestry: {taxon.ancestry_str}\nChildren: {len(taxon.child_taxa)}',
            **kwargs,
        )
        self.taxon = taxon
        if button_callback:
            self.bind(on_release=button_callback)
        self.add_widget(TaxonThumbnail(source=taxon.thumbnail_url or taxon.icon_path))


class TaxonThumbnail(CachedAsyncImage, ILeftBody):
    """ Class that contains a taxon thumbnail to be used in a list item """
    def __init__(self, **kwargs):
        super().__init__(thumbnail_size='small', **kwargs)
