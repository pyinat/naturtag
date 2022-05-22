from itertools import chain
from logging import getLogger
from time import time

from pyinaturalist import ClientSession, Observation, Taxon, WrapperPaginator, iNatClient
from pyinaturalist.controllers import ObservationController, TaxonController
from pyinaturalist_convert.db import get_db_observations, get_db_taxa, save_observations, save_taxa

logger = getLogger(__name__)


class iNatDbClient(iNatClient):
    """API client class that uses a local SQLite database to cache observations and taxa (when searched by ID)"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.observations = ObservationDbController(self)
        self.taxa = TaxonDbController(self)


# TODO: Expiration?
class ObservationDbController(ObservationController):
    def from_ids(
        self, *observation_ids, refresh: bool = False, **params
    ) -> WrapperPaginator[Observation]:
        """Get observations by ID; first from the database, then from the API"""
        # Get any observations saved in the database (unless refreshing)
        db_results = list(get_db_observations(ids=observation_ids)) if not refresh else []
        logger.debug(f'{len(db_results)} observations found in database')

        # Get remaining observations from the API and save to the database
        remaining_ids = set(observation_ids) - {obs.id for obs in db_results}
        if remaining_ids:
            logger.debug(f'Fetching remaining {len(remaining_ids)} observations from API')
            results = super().from_ids(*remaining_ids, **params).all()
            save_observations(results)
        else:
            results = []

        return WrapperPaginator(db_results + results)

    def search(self, **params) -> list[Observation]:
        """Search observations, and save results to the database (for future reference by ID)"""
        results = super().search(**params).all()
        save_observations(results)
        return results


class TaxonDbController(TaxonController):
    def from_ids(
        self,
        *taxon_ids: int,
        accept_partial: bool = False,
        refresh: bool = False,
        **params,
    ) -> WrapperPaginator[Taxon]:
        """Get taxa by ID; first from the database, then from the API"""
        start = time()
        # Get any taxa saved in the database (unless refreshing)
        if not refresh:
            db_results = self._get_db_taxa(list(taxon_ids), accept_partial)
        else:
            db_results = []
        logger.debug(f'{len(db_results)} taxa found in database')

        # Get remaining taxa from the API and save to the database
        remaining_ids = set(taxon_ids) - {taxon.id for taxon in db_results}
        if remaining_ids:
            logger.debug(f'Fetching remaining {len(remaining_ids)} taxa from API')
            results = super().from_ids(*remaining_ids, **params).all() if remaining_ids else []
            save_taxa(results)
        else:
            results = []

        logger.debug(f'Finished in {time()-start:.2f} seconds')
        return WrapperPaginator(db_results + results)

    def _get_db_taxa(self, taxon_ids: list[int], accept_partial: bool = False):
        db_results = list(get_db_taxa(ids=taxon_ids, accept_partial=accept_partial))

        # DB records only contain ancestor/child IDs, so we need another query to fetch full records
        # This could be done in SQL, but a many-to-many relationship with ancestors would get messy
        if not accept_partial:
            fetch_ids = chain.from_iterable([t.ancestor_ids + t.child_ids for t in db_results])
            taxa = {t.id: t for t in self.from_ids(*set(fetch_ids), accept_partial=True)}
            for taxon in db_results:
                taxon.ancestors = [taxa[id] for id in taxon.ancestor_ids]
                taxon.children = [taxa[id] for id in taxon.child_ids]

        return db_results

    def search(self, **params) -> list[Taxon]:
        """Search taxa, and save results to the database (for future reference by ID)"""
        results = super().search(**params).all()
        save_taxa(results)
        return results


INAT_CLIENT = iNatDbClient(cache_control=False)

# A second session to use for fetching images, to set a higher rate limit
# Changes could be made in requests-ratelimiter to more easily set different limits per host
IMG_SESSION = ClientSession(expire_after=-1, per_second=5, per_minute=400)
