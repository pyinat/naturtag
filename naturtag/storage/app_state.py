from collections import Counter, OrderedDict
from datetime import datetime, timezone
from importlib.metadata import version as pkg_version
from itertools import chain
from logging import getLogger
from pathlib import Path
from typing import Iterable, Optional

from attr import define, field
from cattrs.preconf import json
from pyinaturalist import TaxonCounts
from pyinaturalist_convert._models import Base
from pyinaturalist_convert.db import create_table, get_session
from sqlalchemy import Column, Integer, delete, select, types
from sqlalchemy.exc import OperationalError

from naturtag.constants import (
    DB_PATH,
    DEFAULT_WINDOW_SIZE,
    MAX_DISPLAY_HISTORY,
    MAX_DISPLAY_OBSERVED,
)

JsonConverter = json.make_converter()
logger = getLogger(__name__)


@define(auto_attribs=False, slots=False)
class AppState:
    """Container for persistent application state info. This includes values that don't need to be
    human-readable/editable, so they are persisted in SQLite instead of ``settings.yml``.
    """

    db_path: Path = None  # type: ignore

    # Taxonomy browser data
    history: list[int] = field(factory=list)
    starred: list[int] = field(factory=list)
    observed: dict[int, int] = field(factory=dict)
    frequent: Counter[int] = None  # type: ignore

    # Misc state info
    setup_complete: bool = field(default=False)
    last_obs_check: Optional[datetime] = field(default=None)
    last_version: str = field(default='N/A')
    window_size: tuple[int, int] = field(default=DEFAULT_WINDOW_SIZE)

    def __attrs_post_init__(self):
        self.frequent = Counter(self.history)

    @property
    def display_ids(self) -> set[int]:
        """Return top history, frequent, observed, and starred taxa combined.
        Returns only unique IDs, since a given taxon may appear in more than one list.
        """
        top_ids = [self.top_history, self.top_frequent, self.top_observed, self.starred]
        return set(chain.from_iterable(top_ids))

    @property
    def top_history(self) -> list[int]:
        """Get the most recently viewed unique taxa"""
        return _top_unique_ids(self.history[::-1])

    @property
    def top_frequent(self) -> list[int]:
        """Get the most frequently viewed taxa"""
        return [t[0] for t in self.frequent.most_common(MAX_DISPLAY_HISTORY)]

    @property
    def top_observed(self) -> list[int]:
        """Get the most commonly observed taxa"""
        return _top_unique_ids(self.observed.keys(), MAX_DISPLAY_OBSERVED)

    def check_version_change(self):
        """Check if the app version has changed since the last run"""
        current_version = pkg_version('naturtag')
        if self.last_version != current_version:
            logger.info(f'Updated from {self.last_version} to {current_version}')
            self.last_version = current_version
            self.setup_complete = False

    def frequent_idx(self, taxon_id: int) -> Optional[int]:
        """Return the position of a taxon in the frequent list, if it's in the top
        ``MAX_DISPLAY_HISTORY`` taxa.
        """
        try:
            return self.top_frequent.index(taxon_id)
        except ValueError:
            return None

    def set_obs_checkpoint(self):
        self.last_obs_check = datetime.now(timezone.utc).replace(microsecond=0)
        self.write()

    def update_history(self, taxon_id: int):
        """Update history and frequent with a new or existing taxon ID"""
        self.history.append(taxon_id)
        self.frequent.update([taxon_id])

    def update_observed(self, taxon_counts: TaxonCounts):
        self.observed = {t.id: t.count for t in taxon_counts}

    def view_count(self, taxon_id: int) -> int:
        """Return the number of times this taxon has been viewed"""
        return self.frequent.get(taxon_id, 0)

    def __str__(self):
        sizes = [
            f'History: {len(self.history)}',
            f'Starred: {len(self.starred)}',
            f'Frequent: {len(self.frequent)}',
            f'Observed: {len(self.observed)}',
        ]
        return '\n'.join(sizes)

    @classmethod
    def read(cls, db_path: Path = DB_PATH) -> 'AppState':
        """Read app state from SQLite database, or return a new instance if no state is found"""
        logger.debug(f'Reading app state from {db_path}')

        try:
            with get_session(db_path) as session:
                state_json = session.execute(select(DbAppState)).first()[0].content
        except (TypeError, OperationalError):
            new_state = AppState()
            new_state.db_path = db_path
            return new_state

        obj = JsonConverter.structure(state_json, cl=cls)
        obj.db_path = db_path
        return obj

    def write(self):
        """Write app state to SQLite database. Table will be created if it doesn't exist."""
        logger.info(f'Writing app state to {self.db_path}')
        create_table(DbAppState, self.db_path)
        state_json = JsonConverter.unstructure(self)
        with get_session(self.db_path) as session:
            session.execute(delete(DbAppState))
            session.add(DbAppState(content=state_json))
            session.commit()


@Base.mapped
class DbAppState:
    """Application state persisted in SQLite, stored in a single JSON field"""

    __tablename__ = 'app_state'

    id = Column(Integer, default=0, primary_key=True)
    content = Column(types.JSON)


def _top_unique_ids(ids: Iterable[int], n: int = MAX_DISPLAY_HISTORY) -> list[int]:
    """Get the top unique IDs from a list, preserving order"""
    return list(OrderedDict.fromkeys(ids))[:n]
