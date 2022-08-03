from hashlib import md5
from itertools import chain
from logging import getLogger
from time import time
from typing import TYPE_CHECKING

from pyinaturalist import ClientSession, Observation, Photo, Taxon, WrapperPaginator, iNatClient
from pyinaturalist.controllers import ObservationController, TaxonController
from pyinaturalist.converters import format_file_size
from pyinaturalist_convert.db import get_db_observations, get_db_taxa, save_observations, save_taxa
from requests_cache import SQLiteDict

from naturtag.constants import DB_PATH, IMAGE_CACHE, ROOT_TAXON_ID

if TYPE_CHECKING:
    from PySide6.QtGui import QPixmap

logger = getLogger(__name__)


class iNatDbClient(iNatClient):
    """API client class that uses a local SQLite database to cache observations and taxa (when searched by ID)"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.taxa = TaxonDbController(self)
        self.observations = ObservationDbController(self, taxon_controller=self.taxa)


# TODO: Expiration?
class ObservationDbController(ObservationController):
    def __init__(self, *args, taxon_controller: 'TaxonDbController', **kwargs):
        """Need a reference to taxon controller to get full taxon ancestry"""
        super().__init__(*args, **kwargs)
        self.taxon_controller = taxon_controller

    def from_ids(
        self, *observation_ids, refresh: bool = False, taxonomy: bool = False, **params
    ) -> WrapperPaginator[Observation]:
        """Get observations by ID; first from the database, then from the API"""
        # Get any observations saved in the database (unless refreshing)
        start = time()
        observations = [] if refresh else list(get_db_observations(DB_PATH, ids=observation_ids))
        logger.debug(f'{len(observations)} observations found in database')

        # Get remaining observations from the API and save to the database
        remaining_ids = set(observation_ids) - {obs.id for obs in observations}
        if remaining_ids:
            logger.debug(f'Fetching remaining {len(remaining_ids)} observations from API')
            api_results = super().from_ids(*remaining_ids, **params).all()
            observations.extend(api_results)
            save_observations(api_results, DB_PATH)

        # Add full taxonomy to observations, if specified
        if taxonomy:
            self.taxon_controller._get_taxonomy([obs.taxon for obs in observations])

        logger.debug(f'Finished in {time()-start:.2f} seconds')
        return WrapperPaginator(observations)

    def search(self, **params) -> WrapperPaginator[Observation]:
        """Search observations, and save results to the database (for future reference by ID)"""
        results = super().search(**params).all()
        save_observations(results, DB_PATH)
        return WrapperPaginator(results)


class TaxonDbController(TaxonController):
    def from_ids(
        self,
        *taxon_ids: int,
        accept_partial: bool = False,
        refresh: bool = False,
        **params,
    ) -> WrapperPaginator[Taxon]:
        """Get taxa by ID; first from the database, then from the API"""
        # Get any taxa saved in the database (unless refreshing)
        start = time()
        taxa = [] if refresh else self._get_db_taxa(list(taxon_ids), accept_partial)
        logger.debug(f'{len(taxa)} taxa found in database')

        # Get remaining taxa from the API and save to the database
        remaining_ids = set(taxon_ids) - {taxon.id for taxon in taxa}
        if remaining_ids:
            logger.debug(f'Fetching remaining {len(remaining_ids)} taxa from API')
            api_results = super().from_ids(*remaining_ids, **params).all() if remaining_ids else []
            taxa.extend(api_results)
            save_taxa(api_results, DB_PATH)

        logger.debug(f'Finished in {time()-start:.2f} seconds')
        return WrapperPaginator(taxa)

    def _get_db_taxa(self, taxon_ids: list[int], accept_partial: bool = False):
        db_results = list(get_db_taxa(DB_PATH, ids=taxon_ids, accept_partial=accept_partial))
        if not accept_partial:
            db_results = self._get_taxonomy(db_results)
        return db_results

    def _get_taxonomy(self, taxa: list[Taxon]) -> list[Taxon]:
        """Add ancestor and descendant records to all the specified taxa.

        DB records only contain ancestor/child IDs, so we need another query to fetch full records
        This could be done in SQL, but a many-to-many relationship with ancestors would get messy.
        Besides, some may be missing and need to be fetched from the API.
        """
        fetch_ids = chain.from_iterable([t.ancestor_ids + t.child_ids for t in taxa])
        extended_taxa = {t.id: t for t in self.from_ids(*set(fetch_ids), accept_partial=True)}

        for taxon in taxa:
            # Depending on data source, the taxon itself may have already been added to ancestry
            # TODO: Fix in pyinaturalist.Taxon and/or pyinaturalist_convert.db
            taxon.ancestors = [
                extended_taxa[id]
                for id in taxon.ancestor_ids
                if id not in [ROOT_TAXON_ID, taxon.id]
            ]
            taxon.children = [extended_taxa[id] for id in taxon.child_ids]
        return taxa

    # TODO: Don't use all
    def search(self, **params) -> WrapperPaginator[Taxon]:
        """Search taxa, and save results to the database (for future reference by ID)"""
        results = super().search(**params).all()
        save_taxa(results)
        return WrapperPaginator(results)


# TODO: Set expiration on 'original' and 'large' size images using URL patterns
#   Requires changes in ClientSession to update urls_expire_after param for requests-cache
class ImageSession(ClientSession):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.image_cache = SQLiteDict(IMAGE_CACHE, 'images', no_serializer=True)

    def get_image(self, photo: Photo, url: str = None, size: str = None) -> bytes:
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

    def get_pixmap(self, photo: Photo = None, url: str = None, size: str = None) -> 'QPixmap':
        from PySide6.QtGui import QPixmap

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


INAT_CLIENT = iNatDbClient(cache_control=False)
IMG_SESSION = ImageSession(expire_after=-1, per_second=5, per_minute=400)
