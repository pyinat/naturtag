"""Setup functions for creating and updating the SQLite database"""

import sqlite3
from logging import getLogger
from pathlib import Path
from tarfile import TarFile
from tempfile import TemporaryDirectory

import requests
from pyinaturalist_convert import create_tables, load_table
from pyinaturalist_convert.fts import (
    create_observation_fts_table,
    create_taxon_fts_table,
    vacuum_analyze,
)

from naturtag.constants import DB_PATH, PACKAGED_TAXON_DB, TAXON_DB_URL
from naturtag.storage import AppState

logger = getLogger().getChild(__name__)


def setup(
    db_path: Path = DB_PATH,
    overwrite: bool = False,
    download: bool = False,
) -> AppState:
    """Run any first-time setup steps, if needed:
    * Create database tables
    * Extract packaged taxonomy data and load into SQLite

    Note: taxonomy data is included with PyInstaller packages and platform-specific installers,
    but not with plain python package on PyPI (to keep package size small).
    Use `download=True` to fetch the missing data.

    Args:
        db_path: SQLite database path
        overwrite: Overwrite an existing taxon database, if it already exists
        download: Download taxon data (full text search + basic taxon details)
    """
    # Check if setup is needed
    app_state = AppState.read(db_path)
    app_state.check_version_change()
    if app_state.setup_complete and not overwrite:
        logger.debug('Database setup already done')
        return app_state

    logger.info('Running database setup')
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

    app_state.setup_complete = True
    app_state.last_obs_check = None
    app_state.write()
    logger.info('Setup complete')
    return app_state


# TODO: Currently this isn't exposed through the UI; requires calling `setup(download=True)` or
#  `nt setup db --download``. Not sure yet if this is a good idea to include.
# TODO: Option to download full taxon db (all languages)
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
        logger.info('Loading packaged taxon data and text search index')
        tmp_dir = Path(tmp_dir_name)
        with TarFile.open(PACKAGED_TAXON_DB) as tar:
            tar.extractall(path=tmp_dir)

        load_table(tmp_dir / 'taxon.csv', db_path, table_name='taxon')
        load_table(tmp_dir / 'taxon_fts.csv', db_path, table_name='taxon_fts')

    # Indicate some columns are missing and need to be filled in from the API (mainly photo URLs)
    with sqlite3.connect(db_path) as conn:
        conn.execute('UPDATE taxon SET partial=1')

    vacuum_analyze(['taxon', 'taxon_fts'], db_path)
