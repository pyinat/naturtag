"""Basic utilities for reading and writing settings from config files"""
import sqlite3
from collections import Counter, OrderedDict
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
from pyinaturalist_convert.fts import create_fts5_table, vacuum_analyze

from naturtag.constants import (
    CONFIG_PATH,
    DB_PATH,
    DEFAULT_WINDOW_SIZE,
    LOGFILE,
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
    converter.register_unstructure_hook(Path, str)
    converter.register_structure_hook(Path, lambda obj, cls: Path(obj))
    return converter


YamlConverter = make_converter()


class YamlMixin:
    """Attrs class mixin that converts to and from a YAML file"""

    path: Path

    @classmethod
    def read(cls) -> 'YamlMixin':
        """Read settings from config file"""
        if not cls.path.is_file():
            return cls()

        logger.info(f'Reading {cls.__name__} from {cls.path}')
        with open(cls.path) as f:
            attrs_dict = yaml.safe_load(f)
            return YamlConverter.structure(attrs_dict, cl=cls)

    def write(self):
        """Write settings to config file"""
        logger.info(f'Writing {self.__class__.__name__} to {self.path}')
        logger.debug(str(self))
        self.path.parent.mkdir(parents=True, exist_ok=True)

        attrs_dict = YamlConverter.unstructure(self)
        with open(self.path, 'w') as f:
            yaml.safe_dump(attrs_dict, f)

    @classmethod
    def reset_defaults(cls) -> 'YamlMixin':
        cls().write()
        return cls.read()


def doc_field(doc: str = '', **kwargs):
    """
    Create a field for an attrs class that is documented in the class docstring.
    """
    return field(metadata={'doc': doc}, **kwargs)


@define
class Settings(YamlMixin):
    path = CONFIG_PATH

    # Display settings
    dark_mode: bool = field(default=False)
    window_size: tuple[int, int] = field(default=DEFAULT_WINDOW_SIZE)

    # Logging settings
    log_level: str = doc_field(default='INFO', doc='Logging level')
    log_level_external: str = field(default='INFO')
    logfile: Path = field(default=LOGFILE, converter=Path)
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
    # data_dir: Path = field(default=DATA_DIR, converter=Path)

    debug: bool = field(default=False)
    setup_complete: bool = field(default=False)

    @classmethod
    def read(cls) -> 'Settings':
        return super(Settings, cls).read()  # type: ignore

    @property
    def start_image_dir(self) -> Path:
        """Get the starting directory for image selection, depeding on settings"""
        if self.use_last_dir and self.recent_image_dirs:
            return self.recent_image_dirs[0]
        else:
            return self.default_image_dir

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

    def remove_recent_dir(self, image_dir: Path):
        if image_dir in self.recent_image_dirs:
            self.recent_image_dirs.remove(image_dir)


@define(auto_attribs=False)
class UserTaxa(YamlMixin):
    """Relevant taxon IDs stored for the current user"""

    path = USER_TAXA_PATH

    history: list[int] = field(factory=list)
    starred: list[int] = field(factory=list)
    observed: dict[int, int] = field(factory=dict)
    frequent: Counter[int] = None  # type: ignore

    def __attrs_post_init__(self):
        """Initialize frequent taxa counter"""
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

    @classmethod
    def read(cls) -> 'UserTaxa':
        return super(UserTaxa, cls).read()  # type: ignore


def setup(settings: Settings = None, overwrite: bool = False, download: bool = False):
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
    if settings.setup_complete and not overwrite:
        logger.debug('First-time setup already done')
        return

    logger.info('Running first-time setup')
    if DB_PATH.is_file():
        logger.warning('Taxon database already exists; attempting to update')
        if overwrite:
            with sqlite3.connect(DB_PATH) as conn:
                conn.execute('DROP TABLE taxon')
                conn.execute('DROP TABLE taxon_fts')

    # Create SQLite file with tables if they don't already exist
    create_tables(DB_PATH)
    create_fts5_table(DB_PATH)
    _load_taxon_db(download)

    # Indicate some columns are missing and need to be filled in from API
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute('UPDATE taxon SET partial=1')

    vacuum_analyze(['taxon', 'taxon_fts'], DB_PATH)

    logger.info('Setup complete')
    settings.setup_complete = True
    settings.write()


# TODO: Currently this isn't exposed through the UI or CLI; requires calling `setup(download=True)`.
#   Not sure yet if this is a good idea to include.
def _download_taxon_db():
    logger.info(f'Downloading {TAXON_DB_URL} to {PACKAGED_TAXON_DB}')
    r = requests.get(TAXON_DB_URL, stream=True)
    with open(PACKAGED_TAXON_DB, 'wb') as f:
        f.write(r.content)


def _load_taxon_db(download: bool = False):
    """Load taxon tables from packaged data, if available"""
    # Optionally download data if it doesn't exist locally
    if not PACKAGED_TAXON_DB.is_file():
        if download:
            _download_taxon_db()
            _load_taxon_db()
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

        load_table(tmp_dir / 'taxon.csv', DB_PATH, table_name='taxon')
        load_table(tmp_dir / 'taxon_fts.csv', DB_PATH, table_name='taxon_fts')


def _top_unique_ids(ids: Iterable[int], n: int = MAX_DISPLAY_HISTORY) -> list[int]:
    """Get the top unique IDs from a list, preserving order"""
    return list(OrderedDict.fromkeys(ids))[:n]
