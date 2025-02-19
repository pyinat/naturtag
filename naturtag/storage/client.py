from datetime import datetime
from itertools import chain
from logging import getLogger
from pathlib import Path
from time import time
from typing import Optional

from pyinaturalist import Observation, Taxon, WrapperPaginator, iNatClient
from pyinaturalist.constants import MultiInt
from pyinaturalist.controllers import ObservationController, TaxonController
from pyinaturalist.converters import ensure_list
from pyinaturalist_convert import index_observation_text
from pyinaturalist_convert.db import get_db_observations, get_db_taxa, save_observations, save_taxa

from naturtag.constants import DB_PATH, DEFAULT_PAGE_SIZE, ROOT_TAXON_ID

logger = getLogger(__name__)


class iNatDbClient(iNatClient):
    """API client class that uses a local SQLite database to cache observations and taxa (when searched by ID)"""

    def __init__(self, db_path: Path = DB_PATH, **kwargs):
        kwargs.setdefault('cache_control', False)
        super().__init__(**kwargs)
        self.db_path = db_path
        self.taxa = TaxonDbController(self)
        self.observations = ObservationDbController(self, taxon_controller=self.taxa)

    def from_id(
        self, observation_id: Optional[int] = None, taxon_id: Optional[int] = None
    ) -> Optional[Observation]:
        """Get an iNaturalist observation and/or taxon matching the specified ID(s). If only a taxon ID
        is provided, the observation will be a placeholder with only the taxon field populated.
        """
        # Get observation record, if available
        if observation_id:
            observation = self.observations(observation_id, refresh=True)
            if not observation:
                return None
            taxon_id = observation.taxon.id if observation.taxon else None
        # Otherwise, use an empty placeholder observation
        else:
            observation = Observation()

        # Observation.taxon doesn't include ancestors, so we always need to fetch the full taxon record
        observation.taxon = self.taxa(taxon_id)
        if not observation.taxon:
            logger.warning(f'No taxon found: {taxon_id}')
            return None

        # If there's a taxon only (no observation), check for any taxonomy changes
        # TODO: Add this to pyinat: https://github.com/pyinat/pyinaturalist/issues/444
        synonyms = observation.taxon.current_synonymous_taxon_ids
        if not observation_id and not observation.taxon.is_active and len(synonyms or []) == 1:
            observation.taxon = self.taxa(synonyms[0], refresh=True)

        return observation


# TODO: Expiration?
class ObservationDbController(ObservationController):
    def __init__(self, *args, taxon_controller: 'TaxonDbController', **kwargs):
        """Need a reference to taxon controller to get full taxon ancestry"""
        super().__init__(*args, **kwargs)
        self.taxon_controller = taxon_controller

    def from_ids(
        self,
        observation_ids: MultiInt,
        refresh: bool = False,
        taxonomy: bool = False,
        **params,
    ) -> WrapperPaginator[Observation]:
        """Get observations by ID; first from the database, then from the API"""
        # Get any observations saved in the database (unless refreshing)
        start = time()
        observation_ids = ensure_list(observation_ids)
        if refresh:
            observations = []
        else:
            observations = list(get_db_observations(self.client.db_path, ids=observation_ids))
        logger.debug(f'{len(observations)} observations found in database')

        # Get remaining observations from the API and save to the database
        remaining_ids = set(observation_ids) - {obs.id for obs in observations}
        if remaining_ids:
            logger.debug(f'Fetching remaining {len(remaining_ids)} observations from API')
            api_results = super().from_ids(remaining_ids, **params).all()
            observations.extend(api_results)
            self.save(api_results)

        # Add full taxonomy to observations, if specified
        if taxonomy:
            self.taxon_controller._add_taxonomy([obs.taxon for obs in observations])

        logger.debug(f'Finished in {time() - start:.2f} seconds')
        return WrapperPaginator(observations)

    def count(self, username: str, **params) -> int:
        """Get the total number of observations matching the specified criteria"""
        return super().search(user_login=username, refresh=True, **params).count()

    # TODO: Save one page at a time
    def search(self, **params) -> WrapperPaginator[Observation]:
        """Search observations, and save results to the database (for future reference by ID)"""
        results = super().search(**params).all()
        if results:
            self.save(results)
        return WrapperPaginator(results)

    def get_user_observations(
        self,
        username: str,
        updated_since: Optional[datetime] = None,
        limit: int = DEFAULT_PAGE_SIZE,
        page: int = 1,
    ) -> list[Observation]:
        """Fetch any new user observations from the API since last search, save them to the db,
        and then return up to ``limit`` most recent observations from the db
        """
        # TODO: Initial load should be done in a separate thread
        logger.debug(f'Fetching new user observations since {updated_since}')
        new_observations = []
        if page == 1:
            new_observations = self.search(
                user_login=username,
                updated_since=updated_since,
                refresh=True,
            ).all()
        if new_observations:
            logger.info(f'{len(new_observations)} new observations found since {updated_since}')
        else:
            logger.info(f'No new observations found since {updated_since}')

        if not limit:
            return []

        # If there are enough new results to fill first page, return them directly
        if len(new_observations) >= limit:
            new_observations = sorted(
                new_observations, key=lambda obs: obs.created_at, reverse=True
            )
            return new_observations[:limit]

        # Otherwise get up to `limit` most recent saved observations from the db.
        # This includes obs we just fetched and saved; a minor inefficiency, but we can't accurately
        # sort a mix of API results and db results by created date within a single query.
        obs = get_db_observations(
            self.client.db_path,
            username=username,
            limit=limit,
            page=page,
            order_by_created=True,
        )
        return list(obs)

    def save(self, observations: list[Observation]):
        """Save observations to the database (full records + text search index)"""
        save_observations(observations, self.client.db_path)
        index_observation_text(observations, self.client.db_path)


class TaxonDbController(TaxonController):
    def from_ids(
        self,
        taxon_ids: MultiInt,
        accept_partial: bool = False,
        refresh: bool = False,
        **params,
    ) -> WrapperPaginator[Taxon]:
        """Get taxa by ID; first from the database, then from the API"""
        # Get any taxa saved in the database (unless refreshing)
        start = time()
        taxon_ids = ensure_list(taxon_ids)
        taxa = [] if refresh else self._get_db_taxa(taxon_ids, accept_partial)
        logger.debug(f'{len(taxa)} taxa found in database')

        # Get remaining taxa from the API and save to the database
        remaining_ids = set(taxon_ids) - {taxon.id for taxon in taxa}
        if remaining_ids:
            logger.debug(f'Fetching remaining {len(remaining_ids)} taxa from API')
            api_results = super().from_ids(remaining_ids, **params).all() if remaining_ids else []
            taxa.extend(api_results)
            save_taxa(api_results, self.client.db_path)
            api_results = self._add_db_taxonomy(api_results)

        logger.debug(f'Finished in {time() - start:.2f} seconds')
        return WrapperPaginator(taxa)

    def _get_db_taxa(self, taxon_ids: list[int], accept_partial: bool = False):
        db_results = list(
            get_db_taxa(self.client.db_path, ids=taxon_ids, accept_partial=accept_partial)
        )
        if not accept_partial:
            db_results = self._add_taxonomy(db_results)
        return db_results

    def _add_taxonomy(self, taxa: list[Taxon]) -> list[Taxon]:
        """Add ancestor and descendant records to all the specified taxa.

        DB records only contain ancestor/child IDs, so we need another query to fetch full records.
        This could be done in SQL, but a many-to-many relationship with ancestors would get messy.
        Besides, some may be missing and need to be fetched from the API.
        """
        fetch_ids = chain.from_iterable([t.ancestor_ids + t.child_ids for t in taxa])
        extended_taxa = {t.id: t for t in self.from_ids(set(fetch_ids), accept_partial=True)}

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

    def _add_db_taxonomy(self, taxa: list[Taxon]) -> list[Taxon]:
        """Given new taxon records from the API, replace partial ancestors and children with any
        that are stored locally. This is mainly for displaying aggregate values in the taxonomy
        browser.
        """
        api_taxa = chain.from_iterable([t.ancestors + t.children for t in taxa])
        partial_taxa = {t.id: t for t in api_taxa}
        full_taxa = {
            t.id: t
            for t in get_db_taxa(
                self.client.db_path, ids=list(partial_taxa.keys()), accept_partial=True
            )
        }
        for taxon in taxa:
            taxon.ancestors = [
                full_taxa.get(id) or partial_taxa[id]
                for id in taxon.ancestor_ids
                if id not in [ROOT_TAXON_ID, taxon.id]
            ]
            taxon.children = [full_taxa.get(id) or partial_taxa[id] for id in taxon.child_ids]
        return taxa

    # TODO: Save one page at a time
    def search(self, **params) -> WrapperPaginator[Taxon]:
        """Search taxa, and save results to the database (for future reference by ID)"""
        results = super().search(**params).all()
        save_taxa(results)
        return WrapperPaginator(results)
