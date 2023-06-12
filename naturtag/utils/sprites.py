import sqlite3
from logging import basicConfig, getLogger

from attr import define, field
from pyinaturalist import Taxon
from requests_cache.backends import SQLiteDict

from naturtag.constants import ASSETS_DIR

SPRITE_DB_PATH = ASSETS_DIR / 'sprites.db'


logger = getLogger(__name__)
basicConfig(level='INFO')


@define
class TaxonSprite:
    id: int = field()
    name: str = field()
    sprite: bytes = field(default=None)


# Option 1
def read_sprite_db():
    """Load sprite database into memory"""
    source = sqlite3.connect(SPRITE_DB_PATH)
    dest = sqlite3.connect('file::memory:?cache=shared')
    source.backup(dest)
    return dest


# Option 2
def get_sprite_dict() -> dict[int, bytes]:
    """Load sprite database into memory"""
    sprite_db = SQLiteDict(SPRITE_DB_PATH, table_name='taxon_sprite', serializer=None)
    return {int(k): v for k, v in sprite_db.items()}


def get_sprite(taxon: Taxon) -> bytes:
    """Get sprite for a taxon. If there is no exact match by taxon ID, use the closest ancestor that
    has a sprite.
    """
    for taxon_id in [taxon.id] + list(reversed(taxon.ancestor_ids)):
        if taxon_id in TAXON_SPRITES:
            return TAXON_SPRITES[taxon_id]
    return b''  # unknown/placeholder


TAXON_SPRITES = get_sprite_dict()
