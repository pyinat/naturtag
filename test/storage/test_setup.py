"""Tests for naturtag/storage/setup.py"""

from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest
import requests

from naturtag.storage.setup import _download_taxon_db, _load_taxon_db, setup


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
        patch('naturtag.storage.setup.AppState') as mock_app_state_cls,
    ):
        mock_app_state_cls.read.return_value = mock_state
        yield {
            'state': mock_state,
            'create_tables': mock_create_tables,
            'create_taxon_fts': mock_create_taxon_fts,
            'create_obs_fts': mock_create_obs_fts,
            'load_taxon_db': mock_load_taxon_db,
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


def test_load_taxon_db__loads_both_taxon_tables(db_path, mock_load_taxon_db_deps):
    with (
        patch('naturtag.storage.setup.PACKAGED_TAXON_DB') as mock_packaged_db,
        patch('naturtag.storage.setup.load_table') as mock_load_table,
    ):
        mock_packaged_db.is_file.return_value = True

        _load_taxon_db(db_path, download=False)

    table_names = [c.kwargs.get('table_name') or c.args[2] for c in mock_load_table.call_args_list]
    assert table_names == ['taxon', 'taxon_fts']


def test_load_taxon_db__marks_taxa_partial_and_runs_vacuum(db_path, mock_load_taxon_db_deps):
    with (
        patch('naturtag.storage.setup.PACKAGED_TAXON_DB') as mock_packaged_db,
        patch('naturtag.storage.setup.vacuum_analyze') as mock_vacuum,
    ):
        mock_packaged_db.is_file.return_value = True

        _load_taxon_db(db_path, download=False)

    mock_load_taxon_db_deps['conn'].execute.assert_called_once_with('UPDATE taxon SET partial=1')
    mock_vacuum.assert_called_once_with(['taxon', 'taxon_fts'], db_path)


@patch('naturtag.storage.setup.TAXON_DB_URL', 'https://example.com/taxonomy.tar.gz')
def test_download_taxon_db__streams_chunks_to_file(tmp_path):
    chunks = [b'chunk1_data', b'chunk2_data']
    mock_response = MagicMock()
    mock_response.iter_content.return_value = iter(chunks)

    with (
        patch('naturtag.storage.setup.PACKAGED_TAXON_DB', tmp_path / 'taxonomy.tar.gz'),
        patch('naturtag.storage.setup.requests.get') as mock_get,
        patch('builtins.open', create=True) as mock_open,
    ):
        mock_get.return_value.__enter__.return_value = mock_response
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file

        _download_taxon_db()

    mock_response.raise_for_status.assert_called_once()
    mock_file.write.assert_has_calls([call(c) for c in chunks])


@patch('naturtag.storage.setup.TAXON_DB_URL', 'https://example.com/taxonomy.tar.gz')
def test_download_taxon_db__raises_on_http_error(tmp_path):
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
