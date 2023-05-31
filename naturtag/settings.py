"""Basic utilities for reading and writing settings from config files"""
# TODO: use user data dir for logfile
import sqlite3
from collections import Counter, OrderedDict
from datetime import datetime
from itertools import chain
from logging import getLogger
from pathlib import Path
from tarfile import TarFile
from tempfile import TemporaryDirectory
from typing import Iterable, Optional

import requests
import yaml
from attr import define, field
from cattr import Converter
from cattr.preconf import pyyaml
from pyinaturalist import TaxonCounts
from pyinaturalist_convert import create_tables, load_table
from pyinaturalist_convert.fts import (
    create_observation_fts_table,
    create_taxon_fts_table,
    vacuum_analyze,
)

from naturtag.constants import (
    APP_DIR,
    CONFIG_PATH,
    DEFAULT_WINDOW_SIZE,
    MAX_DIR_HISTORY,
    MAX_DISPLAY_HISTORY,
    MAX_DISPLAY_OBSERVED,
    PACKAGED_TAXON_DB,
    TAXON_DB_URL,
    USER_TAXA_PATH,
    PathOrStr,
)

logger = getLogger().getChild(__name__)


def make_converter() -> Converter:
    converter = pyyaml.make_converter()
    converter.register_unstructure_hook(Path, lambda obj: str(obj) if obj else None)
    converter.register_structure_hook(
        Path, lambda obj, cls: Path(obj).expanduser() if obj else None
    )
    converter.register_unstructure_hook(datetime, lambda obj: obj.isoformat() if obj else None)
    converter.register_structure_hook(
        datetime, lambda obj, cls: datetime.fromisoformat(obj) if obj else None
    )
    return converter


YamlConverter = make_converter()


@define
class YamlMixin:
    """Attrs class mixin that converts to and from a YAML file"""

    path: Optional[Path] = field(default=None)

    @classmethod
    def read(cls, path: Optional[Path]) -> 'YamlMixin':
        """Read settings from config file"""
        path = path or cls.path

        # New file; no contents to read
        if not path or not path.is_file():
            return cls(path=path)

        logger.debug(f'Reading {cls.__name__} from {path}')
        with open(path) as f:
            attrs_dict = yaml.safe_load(f)
        obj = YamlConverter.structure(attrs_dict, cl=cls)

        # Config file may be a stub that specifies an alternate path; if so, read from that path
        if obj.path and obj.path != path:
            return cls.read(obj.path)

        obj.path = path
        return obj

    def write(self):
        """Write settings to config file"""
        logger.info(f'Writing {self.__class__.__name__} to {self.path}')
        logger.debug(str(self))
        attrs_dict = YamlConverter.unstructure(self)

        # Only keep 'path' if it's not the default
        if self.path.parent == APP_DIR:
            attrs_dict.pop('path')

        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, 'w') as f:
            yaml.safe_dump(attrs_dict, f)

    def reset_defaults(self):
        self.__class__(path=self.path).write()
        self = self.__class__.read(path=self.path)


def doc_field(doc: str = '', **kwargs):
    """
    Create a field for an attrs class that is documented in the class docstring.
    """
    return field(metadata={'doc': doc}, **kwargs)


@define
class Settings(YamlMixin):
    # Display settings
    dark_mode: bool = field(default=False)
    window_size: tuple[int, int] = field(default=DEFAULT_WINDOW_SIZE)

    # Logging settings
    log_level: str = doc_field(default='INFO', doc='Logging level')
    log_level_external: str = field(default='INFO')
    show_logs: bool = doc_field(default=False, doc='Show a tab with application logs')

    # iNaturalist
    all_ranks: bool = doc_field(
        default=False, doc='Show all available taxonomic rank filters on taxon search page'
    )
    casual_observations: bool = doc_field(
        default=True, doc='Include casual observations in searches'
    )
    locale: str = doc_field(default='en', doc='Locale preference for species common names')
    preferred_place_id: int = doc_field(
        default=1, converter=int, doc='Place preference for regional species common names'
    )
    search_locale: bool = doc_field(
        default=True, doc='Search common names for only your selected locale'
    )
    username: str = doc_field(default='', doc='Your iNaturalist username')

    # Metadata
    common_names: bool = doc_field(default=True, doc='Include common names in taxonomy keywords')
    hierarchical: bool = doc_field(default=True, doc='Generate hierarchical keywords')
    sidecar: bool = doc_field(default=True, doc='Write XMP metadata to sidecar (separate file)')
    exif: bool = doc_field(default=True, doc='Write EXIF metadata to image (embedded)')
    iptc: bool = doc_field(default=True, doc='Write IPTC metadata to image (embedded)')
    xmp: bool = doc_field(default=True, doc='Write XMP metadata to image (embedded)')

    # User data directories
    default_image_dir: Path = doc_field(
        default=Path('~').expanduser(), doc='Open file chooser in a specific directory'
    )
    use_last_dir: bool = doc_field(
        default=True, doc='Open file chooser in the previously used directory'
    )
    recent_image_dirs: list[Path] = field(factory=list)
    favorite_image_dirs: list[Path] = field(factory=list)

    debug: bool = field(default=False)
    setup_complete: bool = field(default=False)
    last_obs_check: Optional[datetime] = field(default=None)

    @classmethod
    def read(cls, path: Path = CONFIG_PATH) -> 'Settings':  # type: ignore
        return super(Settings, cls).read(path)  # type: ignore

    # Shortcuts for application files within the user data dir
    @property
    def data_dir(self) -> Path:
        return self.path.parent  # type: ignore

    @property
    def db_path(self) -> Path:
        return self.data_dir / 'naturtag.db'

    @property
    def image_cache_path(self) -> Path:
        return self.data_dir / 'images.db'

    @property
    def logfile(self) -> Path:
        return self.data_dir / 'naturtag.log'

    @property
    def user_taxa_path(self) -> Path:
        return self.data_dir / 'user_taxa.yml'

    @property
    def start_image_dir(self) -> Path:
        """Get the starting directory for image selection, depeding on settings"""
        if self.use_last_dir and self.recent_image_dirs:
            return self.recent_image_dirs[0]
        else:
            return self.default_image_dir

    def set_obs_checkpoint(self):
        self.last_obs_check = datetime.utcnow().replace(microsecond=0)
        self.write()

    def add_favorite_dir(self, image_dir: Path):
        if image_dir not in self.favorite_image_dirs:
            self.favorite_image_dirs.append(image_dir)

    def add_recent_dir(self, path: PathOrStr):
        """Add a directory to the list of recent image directories"""
        path = Path(path)
        if path in self.recent_image_dirs:
            self.recent_image_dirs.remove(path)
        self.recent_image_dirs = [path] + self.recent_image_dirs[:MAX_DIR_HISTORY]

    def remove_favorite_dir(self, image_dir: Path):
        if image_dir in self.favorite_image_dirs:
            self.favorite_image_dirs.remove(image_dir)
        self.write()

    def remove_recent_dir(self, image_dir: Path):
        if image_dir in self.recent_image_dirs:
            self.recent_image_dirs.remove(image_dir)


# TODO: This doesn't necessarily need to be human-readable/editable;
#   maybe it could go in SQLite instead?
@define(auto_attribs=False, slots=False)
class UserTaxa(YamlMixin):
    """Relevant taxon IDs stored for the current user"""

    history: list[int] = field(factory=list)
    starred: list[int] = field(factory=list)
    observed: dict[int, int] = field(factory=dict)
    frequent: Counter[int] = None  # type: ignore

    def __attrs_post_init__(self):
        """Initialize frequent taxa counter"""
        self.frequent = Counter(self.history)

    @classmethod
    def read(cls, path: Path = USER_TAXA_PATH) -> 'UserTaxa':  # type: ignore
        return super(UserTaxa, cls).read(path)  # type: ignore

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


def setup(
    settings: Optional[Settings] = None,
    overwrite: bool = False,
    download: bool = False,
):
    """Run any first-time setup steps, if needed:
    * Create database tables
    * Extract packaged taxonomy data and load into SQLite

    Note: taxonomy data is included with PyInstaller packages and platform-specific installers,
    but not with plain python package on PyPI (to keep package size small).
    Use `download=True` to fetch the missing data.

    Args:
        settings: Existing settings object
        overwrite: Overwrite an existing taxon database, if it already exists
        download: Download taxon data (full text search + basic taxon details)
    """
    settings = settings or Settings.read()
    db_path = settings.db_path
    if settings.setup_complete and not overwrite:
        logger.debug('First-time setup already done')
        return

    logger.info('Running first-time setup')
    if overwrite:
        logger.info('Overwriting exiting tables')
        with sqlite3.connect(db_path) as conn:
            conn.execute('DROP TABLE IF EXISTS observation')
            conn.execute('DROP TABLE IF EXISTS observation_fts')
            conn.execute('DROP TABLE IF EXISTS taxon')
            conn.execute('DROP TABLE IF EXISTS taxon_fts')
            conn.execute('DROP TABLE IF EXISTS photo')
            conn.execute('DROP TABLE IF EXISTS user')
    elif db_path.is_file():
        logger.warning('Database already exists; attempting to update')

    # Create SQLite file with tables if they don't already exist
    create_tables(db_path)
    create_taxon_fts_table(db_path)
    create_observation_fts_table(db_path)
    _load_taxon_db(db_path, download)

    # Indicate some columns are missing and need to be filled in from the API (mainly photo URLs)
    with sqlite3.connect(db_path) as conn:
        conn.execute('UPDATE taxon SET partial=1')

    vacuum_analyze(['taxon', 'taxon_fts'], db_path)

    logger.info('Setup complete')
    settings.setup_complete = True
    settings.last_obs_check = None
    settings.write()


# TODO: Currently this isn't exposed through the UI or CLI; requires calling `setup(download=True)`.
#   Not sure yet if this is a good idea to include.
def _download_taxon_db():
    logger.info(f'Downloading {TAXON_DB_URL} to {PACKAGED_TAXON_DB}')
    r = requests.get(TAXON_DB_URL, stream=True)
    with open(PACKAGED_TAXON_DB, 'wb') as f:
        f.write(r.content)


def _load_taxon_db(db_path: Path, download: bool = False):
    """Load taxon tables from packaged data, if available"""
    # Optionally download data if it doesn't exist locally
    if not PACKAGED_TAXON_DB.is_file():
        if download:
            _download_taxon_db()
        else:
            logger.warning(
                'Pre-packaged taxon FTS database does not exist; '
                'taxon text search and autocomplete will not be available'
            )
            return

    with TemporaryDirectory() as tmp_dir_name:
        tmp_dir = Path(tmp_dir_name)
        with TarFile.open(PACKAGED_TAXON_DB) as tar:
            tar.extractall(path=tmp_dir)

        load_table(tmp_dir / 'taxon.csv', db_path, table_name='taxon')
        load_table(tmp_dir / 'taxon_fts.csv', db_path, table_name='taxon_fts')


def _top_unique_ids(ids: Iterable[int], n: int = MAX_DISPLAY_HISTORY) -> list[int]:
    """Get the top unique IDs from a list, preserving order"""
    return list(OrderedDict.fromkeys(ids))[:n]
