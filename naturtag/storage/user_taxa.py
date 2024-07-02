from collections import Counter, OrderedDict
from dataclasses import dataclass
from itertools import chain
from logging import getLogger
from pathlib import Path
from typing import Iterable, Optional

from pyinaturalist import TaxonCounts
from pyinaturalist_convert._models import Base, sa_field
from pyinaturalist_convert.db import get_session
from sqlalchemy import Integer, select, types
from sqlalchemy.orm import reconstructor

from naturtag.constants import DB_PATH, MAX_DISPLAY_HISTORY, MAX_DISPLAY_OBSERVED

logger = getLogger(__name__)


def _top_unique_ids(ids: Iterable[int], n: int = MAX_DISPLAY_HISTORY) -> list[int]:
    """Get the top unique IDs from a list, preserving order"""
    return list(OrderedDict.fromkeys(ids))[:n]


@Base.mapped
@dataclass
class UserTaxa:
    """Relevant taxon IDs stored for the current user, mainly used by taxonomy browser"""

    __tablename__ = 'user_taxa'
    __sa_dataclass_metadata_key__ = 'sa'

    id: int = sa_field(Integer, primary_key=True)
    history: list[int] = sa_field(types.JSON, default=None)
    starred: list[int] = sa_field(types.JSON, default=None)
    observed: dict[int, int] = sa_field(types.JSON, default=None)
    frequent: Counter[int] = None  # type: ignore

    # @property
    # def frequent(self) -> Counter[int]:
    #     if not self._frequent:
    #         self.frequent = Counter(self.history)
    #     return self._frequent

    @property
    def display_ids(self) -> set[int]:
        """Return top history, frequent, observed, and starred taxa combined.
        Returns only unique IDs, since a given taxon may appear in more than one list.
        """
        top_ids = [self.top_history, self.top_frequent, self.top_observed, self.starred]
        return set(chain.from_iterable(top_ids))

    @reconstructor
    def post_init(self):
        self.history = self.history or []
        self.starred = self.starred or []
        self.observed = self.observed or {}
        self.frequent = Counter(self.history)

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

    def frequent_idx(self, taxon_id: int) -> Optional[int]:
        """Return the position of a taxon in the frequent list, if it's in the top
        ``MAX_DISPLAY_HISTORY`` taxa.
        """
        try:
            return self.top_frequent.index(taxon_id)
        except ValueError:
            return None

    def view_count(self, taxon_id: int) -> int:
        """Return the number of times this taxon has been viewed"""
        return self.frequent.get(taxon_id, 0)

    def update_history(self, taxon_id: int):
        """Update history and frequent with a new or existing taxon ID"""
        self.history.append(taxon_id)
        self.frequent.update([taxon_id])

    def update_observed(self, taxon_counts: TaxonCounts):
        self.observed = {t.id: t.count for t in taxon_counts}
        self.write()

    def __str__(self):
        sizes = [
            f'History: {len(self.history)}',
            f'Starred: {len(self.starred)}',
            f'Frequent: {len(self.frequent)}',
            f'Observed: {len(self.observed)}',
        ]
        return '\n'.join(sizes)

    # Unconventional for a SQLAlchemy model, but convenient for consistency with Settings class
    @classmethod
    def read(cls, db_path: Path = DB_PATH) -> 'UserTaxa':
        logger.info(f'Reading user taxa from {db_path}')
        with get_session(db_path) as session:
            user_taxa = session.execute(select(UserTaxa)).first()
        if not user_taxa:
            user_taxa = UserTaxa(id=0)
            user_taxa.post_init()
        return user_taxa

    def write(self, db_path: Path = DB_PATH):
        logger.info(f'Writing user taxa to {db_path}')
        with get_session(db_path) as session:
            session.add(self)
            session.commit()
