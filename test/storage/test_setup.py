"""Tests for naturtag/storage/setup.py"""

import sqlite3
import tarfile
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest
import requests

from naturtag.constants import TAXON_DB_URL
from naturtag.storage.setup import _download_taxon_db, _load_taxon_db, _taxon_table_populated, setup


@pytest.fixture
def db_path(tmp_path) -> Path:
    return tmp_path / 'naturtag.db'


@pytest.fixture
def mock_setup_deps():
    """Patch all external dependencies of setup() and return a pre-configured mock AppState."""
    mock_state = MagicMock()
    mock_state.setup_complete = False

    with (
        patch('naturtag.storage.setup.create_tables') as mock_create_tables,
        patch('naturtag.storage.setup.create_taxon_fts_table') as mock_create_taxon_fts,
        patch('naturtag.storage.setup.create_observation_fts_table') as mock_create_obs_fts,
        patch('naturtag.storage.setup._load_taxon_db') as mock_load_taxon_db,
        patch(
            'naturtag.storage.setup._taxon_table_populated', return_value=False
        ) as mock_populated,
        patch('naturtag.storage.setup.AppState') as mock_app_state_cls,
    ):
        mock_app_state_cls.read.return_value = mock_state
        yield {
            'state': mock_state,
            'create_tables': mock_create_tables,
            'create_taxon_fts': mock_create_taxon_fts,
            'create_obs_fts': mock_create_obs_fts,
            'load_taxon_db': mock_load_taxon_db,
            'taxon_table_populated': mock_populated,
        }


@pytest.fixture
def mock_load_taxon_db_deps():
    """Patch external dependencies shared by multiple _load_taxon_db() tests."""
    mock_tar = MagicMock()
    mock_conn = MagicMock()

    with (
        patch('naturtag.storage.setup.load_table'),
        patch('naturtag.storage.setup.vacuum_analyze'),
        patch('naturtag.storage.setup.TarFile') as mock_tarfile_cls,
        patch('naturtag.storage.setup.sqlite3.connect') as mock_connect,
    ):
        mock_tarfile_cls.open.return_value.__enter__.return_value = mock_tar
        mock_connect.return_value.__enter__.return_value = mock_conn
        yield {'tar': mock_tar, 'conn': mock_conn}


def test_setup__creates_tables_on_first_run(mock_setup_deps, db_path):
    setup(db_path=db_path)

    mock_setup_deps['create_tables'].assert_called_once_with(db_path)
    mock_setup_deps['create_taxon_fts'].assert_called_once_with(db_path)
    mock_setup_deps['create_obs_fts'].assert_called_once_with(db_path)
    mock_setup_deps['load_taxon_db'].assert_called_once_with(db_path, False)

    state = mock_setup_deps['state']
    assert state.setup_complete is True
    assert state.last_obs_check is None
    state.write.assert_called_once()


def test_setup__skips_if_already_complete(mock_setup_deps, db_path):
    mock_setup_deps['state'].setup_complete = True

    result = setup(db_path=db_path)

    mock_setup_deps['create_tables'].assert_not_called()
    mock_setup_deps['load_taxon_db'].assert_not_called()
    assert result is mock_setup_deps['state']


def test_setup__overwrite_drops_correct_tables_and_recreates(mock_setup_deps, db_path):
    """With overwrite=True, all known tables are dropped in order, then recreated."""
    mock_setup_deps['state'].setup_complete = True
    db_path.touch()

    with patch('naturtag.storage.setup.sqlite3.connect') as mock_connect:
        mock_conn = MagicMock()
        mock_connect.return_value.__enter__.return_value = mock_conn

        setup(db_path=db_path, overwrite=True)

    expected_drops = [
        call('DROP TABLE IF EXISTS observation'),
        call('DROP TABLE IF EXISTS observation_fts'),
        call('DROP TABLE IF EXISTS taxon'),
        call('DROP TABLE IF EXISTS taxon_fts'),
        call('DROP TABLE IF EXISTS photo'),
        call('DROP TABLE IF EXISTS user'),
    ]
    mock_conn.execute.assert_has_calls(expected_drops, any_order=False)
    mock_setup_deps['create_tables'].assert_called_once_with(db_path)
    mock_setup_deps['load_taxon_db'].assert_called_once_with(db_path, False)


def test_setup__creates_parent_dirs(mock_setup_deps, tmp_path):
    nested_db = tmp_path / 'a' / 'b' / 'naturtag.db'
    assert not nested_db.parent.exists()

    setup(db_path=nested_db)

    assert nested_db.parent.exists()


@pytest.mark.parametrize('download', [False, True])
def test_setup__passes_download_flag_to_load(mock_setup_deps, db_path, download):
    setup(db_path=db_path, download=download)
    mock_setup_deps['load_taxon_db'].assert_called_once_with(db_path, download)


def test_setup__skips_load_if_taxon_table_populated(mock_setup_deps, db_path):
    """After a version bump, setup_complete is reset but _load_taxon_db should not run if the
    taxon table is already populated — prevents UNIQUE constraint errors on second tag invocation.
    """
    mock_setup_deps['taxon_table_populated'].return_value = True

    setup(db_path=db_path)

    mock_setup_deps['load_taxon_db'].assert_not_called()
    assert mock_setup_deps['state'].setup_complete is True


@pytest.mark.parametrize(
    'rows, expected',
    [
        ([(1,)], True),
        ([(0,)], False),
    ],
)
def test_taxon_table_populated(tmp_path, rows, expected):
    db_path = tmp_path / 'naturtag.db'
    with patch('naturtag.storage.setup.sqlite3.connect') as mock_connect:
        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchone.return_value = rows[0]
        mock_connect.return_value.__enter__.return_value = mock_conn
        assert _taxon_table_populated(db_path) is expected


def test_taxon_table_populated__missing_table(tmp_path):
    db_path = tmp_path / 'naturtag.db'
    with patch('naturtag.storage.setup.sqlite3.connect') as mock_connect:
        mock_conn = MagicMock()
        mock_conn.execute.side_effect = sqlite3.OperationalError('no such table: taxon')
        mock_connect.return_value.__enter__.return_value = mock_conn
        assert _taxon_table_populated(db_path) is False


def test_load_taxon_db__download(db_path, mock_load_taxon_db_deps):
    with (
        patch('naturtag.storage.setup.PACKAGED_TAXON_DB') as mock_packaged_db,
        patch('naturtag.storage.setup._download_taxon_db') as mock_download,
    ):
        # File is missing before download, present after
        mock_packaged_db.is_file.side_effect = [False, True]
        _load_taxon_db(db_path, download=True)

    mock_download.assert_called_once()


def test_load_taxon_db__no_download(db_path, mock_load_taxon_db_deps):
    with (
        patch('naturtag.storage.setup.PACKAGED_TAXON_DB') as mock_packaged_db,
        patch('naturtag.storage.setup._download_taxon_db') as mock_download,
    ):
        mock_packaged_db.is_file.return_value = False
        _load_taxon_db(db_path, download=False)

    mock_download.assert_not_called()


def test_load_taxon_db(db_path, mock_load_taxon_db_deps):
    with (
        patch('naturtag.storage.setup.PACKAGED_TAXON_DB') as mock_packaged_db,
        patch('naturtag.storage.setup.load_table') as mock_load_table,
        patch('naturtag.storage.setup.vacuum_analyze') as mock_vacuum,
    ):
        mock_packaged_db.is_file.return_value = True

        _load_taxon_db(db_path, download=False)

    table_names = [c.kwargs.get('table_name') or c.args[2] for c in mock_load_table.call_args_list]
    assert table_names == ['taxon', 'taxon_fts']
    mock_load_taxon_db_deps['conn'].execute.assert_any_call('DELETE FROM taxon')
    mock_load_taxon_db_deps['conn'].execute.assert_any_call('DELETE FROM taxon_fts')
    mock_vacuum.assert_called_once_with(['taxon', 'taxon_fts'], db_path)


def test_load_taxon_db__corrupt_tar(db_path, mock_load_taxon_db_deps, tmp_path):
    """A corrupt tar file is deleted so the next run with download=True can refetch it."""
    corrupt_tar = tmp_path / 'taxonomy.tar.gz'
    corrupt_tar.touch()

    with (
        patch('naturtag.storage.setup.PACKAGED_TAXON_DB', corrupt_tar),
        patch('naturtag.storage.setup.TarFile') as mock_tarfile_cls,
    ):
        mock_tarfile_cls.open.return_value.__enter__.side_effect = tarfile.TarError('bad file')

        with pytest.raises(tarfile.TarError):
            _load_taxon_db(db_path, download=False)

    assert not corrupt_tar.exists()


def test_download_taxon_db(tmp_path, requests_mock):
    dest = tmp_path / 'taxonomy.tar.gz'
    content = b'x' * (1024 * 1024)
    requests_mock.get(TAXON_DB_URL, content=content)

    with patch('naturtag.storage.setup.PACKAGED_TAXON_DB', dest):
        _download_taxon_db()

    assert dest.stat().st_size == len(content)


def test_download_taxon_db__error(tmp_path):
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = requests.HTTPError('404 Not Found')

    with (
        patch('naturtag.storage.setup.PACKAGED_TAXON_DB', tmp_path / 'taxonomy.tar.gz'),
        patch('naturtag.storage.setup.requests.get') as mock_get,
        patch('builtins.open', create=True),
    ):
        mock_get.return_value.__enter__.return_value = mock_response

        with pytest.raises(requests.HTTPError):
            _download_taxon_db()
