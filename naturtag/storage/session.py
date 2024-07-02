from hashlib import md5
from logging import getLogger
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from pyinaturalist import ClientSession, Photo
from pyinaturalist.converters import format_file_size
from requests_cache import SQLiteDict

from naturtag.constants import IMAGE_CACHE, PathOrStr

if TYPE_CHECKING:
    from PySide6.QtGui import QPixmap

logger = getLogger(__name__)


# TODO: Set expiration on 'original' and 'large' size images using URL patterns
class ImageSession(ClientSession):
    def __init__(self, *args, cache_path: Path = IMAGE_CACHE, **kwargs):
        super().__init__(*args, per_second=5, per_minute=400, **kwargs)
        self.image_cache = SQLiteDict(cache_path, 'images', serializer=None)

    def get_image(
        self, photo: Photo, url: Optional[str] = None, size: Optional[str] = None
    ) -> bytes:
        """Get an image from the cache, if it exists; otherwise, download and cache a new one"""
        if not url:
            url = photo.url_size(size) if size else photo.url
        if not url:
            raise ValueError('No URL or photo object specified')
        image_hash = f'{get_url_hash(url)}.{photo.ext}'
        try:
            return self.image_cache[image_hash]
        except KeyError:
            pass

        data = self.get(url).content
        self.image_cache[image_hash] = data
        return data

    def get_pixmap(
        self,
        path: Optional[PathOrStr] = None,
        photo: Optional[Photo] = None,
        url: Optional[str] = None,
        size: Optional[str] = None,
    ) -> 'QPixmap':
        """Fetch a pixmap from either a local path or remote URL.
        This does not render the image, so it is safe to run from any thread.
        """
        from PySide6.QtGui import QPixmap

        if path:
            return QPixmap(str(path))

        if url and not photo:
            photo = Photo(url=url)
        pixmap = QPixmap()
        pixmap.loadFromData(self.get_image(photo, url, size), format=photo.ext)  # type: ignore
        return pixmap

    def cache_size(self) -> str:
        """Get the total cache size in bytes, and the number of cached files"""
        size = format_file_size(self.image_cache.size)
        return f'{size} ({len(self.image_cache)} files)'


def get_url_hash(url: str) -> str:
    """Generate a hash to use as a cache key from an image URL, appended with the file extension

    Args:
        source: File path or URI for image source
    """
    thumbnail_hash = md5(url.encode()).hexdigest()
    ext = Photo(url=url).ext
    return f'{thumbnail_hash}.{ext}'
