from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from naturtag.cli import (
    main,
    search_taxa_by_name,
)

SAMPLE_TAXON_RESULTS = [
    {
        'id': 1,
        'rank': 'species',
        'name': 'Foo bar',
        'iconic_taxon_id': 1,
        'matched_term': 'Foo',
        'preferred_common_name': 'Common Foo',
    },
    {
        'id': 2,
        'rank': 'genus',
        'name': 'Foo baz',
        'iconic_taxon_id': 3,
        'matched_term': 'Baz',
        'preferred_common_name': 'Common Baz',
    },
]


@pytest.fixture
def runner():
    return CliRunner()


def test_version(runner):
    result = runner.invoke(main, ['--version'], catch_exceptions=False)
    assert result.exit_code == 0
    assert 'naturtag v' in result.output
    assert 'User data directory:' in result.output


def test_no_subcommand__prints_usage(runner):
    result = runner.invoke(main, [], catch_exceptions=False)
    assert result.exit_code == 0
    assert 'Usage:' in result.output


# -- tag command


@pytest.mark.parametrize(
    'args, expected_message',
    [
        (['tag'], 'Specify either a taxon, observation, or refresh'),
        (['tag', '-t', '12345', '-o', '67890'], 'Specify either a taxon, observation, or refresh'),
        (['tag', '--print'], 'Specify images'),
    ],
    ids=['no-options', 'mutually-exclusive', 'print-without-images'],
)
def test_tag__validation_errors(runner, args, expected_message):
    result = runner.invoke(main, args)
    assert expected_message in result.output


@pytest.mark.parametrize(
    'flag, value, expected_taxon_id, expected_observation_id',
    [
        ('-t', '48978', 48978, None),
        ('-t', 'https://www.inaturalist.org/taxa/48978-Dirona-picta', 48978, None),
        ('-o', '45524803', None, 45524803),
        ('-o', 'https://www.inaturalist.org/observations/45524803', None, 45524803),
    ],
    ids=['taxon-id', 'taxon-url', 'observation-id', 'observation-url'],
)
@patch('naturtag.cli.tag_images')
@patch('naturtag.cli.setup')
def test_tag__with_id_or_url(
    mock_setup, mock_tag_images, runner, flag, value, expected_taxon_id, expected_observation_id
):
    mock_tag_images.return_value = [MagicMock()]
    result = runner.invoke(main, ['tag', flag, value, 'image.jpg'], catch_exceptions=False)
    assert result.exit_code == 0
    assert '1 images tagged' in result.output
    mock_tag_images.assert_called_once_with(
        ('image.jpg',),
        observation_id=expected_observation_id,
        taxon_id=expected_taxon_id,
        include_sidecars=True,
    )
    mock_setup.assert_called_once()


@patch('naturtag.cli.tag_images')
@patch('naturtag.cli.setup')
def test_tag__no_results(mock_setup, mock_tag_images, runner):
    mock_tag_images.return_value = []
    result = runner.invoke(main, ['tag', '-t', '48978', 'image.jpg'], catch_exceptions=False)
    assert 'No search results found' in result.output


@patch('naturtag.cli.tag_images')
@patch('naturtag.cli.setup')
def test_tag__multiple_images(mock_setup, mock_tag_images, runner):
    mock_tag_images.return_value = [MagicMock(), MagicMock(), MagicMock()]
    result = runner.invoke(
        main, ['tag', '-t', '48978', 'a.jpg', 'b.jpg', 'c.jpg'], catch_exceptions=False
    )
    assert result.exit_code == 0
    assert '3 images tagged' in result.output


@pytest.mark.parametrize(
    'extra_flags, expected_flickr',
    [
        ([], False),
        (['--flickr'], True),
    ],
    ids=['default', 'flickr'],
)
@patch('naturtag.cli.print_all_metadata')
def test_tag__print(mock_print_all, runner, extra_flags, expected_flickr):
    result = runner.invoke(
        main, ['tag', '--print', *extra_flags, 'image.jpg'], catch_exceptions=False
    )
    assert result.exit_code == 0
    mock_print_all.assert_called_once_with(('image.jpg',), expected_flickr)


# -- tag command: taxon name search --


@patch('naturtag.cli.search_taxa_by_name', return_value=None)
def test_tag__taxon_name_no_match(mock_search, runner):
    result = runner.invoke(main, ['tag', '-t', 'nonexistent species'], catch_exceptions=False)
    assert result.exit_code == 0
    mock_search.assert_called_once()


@patch('naturtag.cli.tag_images')
@patch('naturtag.cli.setup')
@patch('naturtag.cli.search_taxa_by_name', return_value=12345)
def test_tag__taxon_name_with_match(mock_search, mock_setup, mock_tag_images, runner):
    mock_tag_images.return_value = [MagicMock()]
    result = runner.invoke(
        main, ['tag', '-t', 'indigo bunting', 'image.jpg'], catch_exceptions=False
    )
    assert result.exit_code == 0
    mock_search.assert_called_once_with('indigo bunting', verbose=0)
    mock_tag_images.assert_called_once_with(
        ('image.jpg',),
        observation_id=None,
        taxon_id=12345,
        include_sidecars=True,
    )


# -- refresh command --


@pytest.mark.parametrize(
    'flags, images, expected_recursive',
    [
        ([], ['a.jpg', 'b.jpg'], False),
        (['-r'], ['some_dir'], True),
    ],
    ids=['default', 'recursive'],
)
@patch('naturtag.cli.refresh_tags')
@patch('naturtag.cli.setup')
def test_refresh(mock_setup, mock_refresh_tags, runner, flags, images, expected_recursive):
    mock_refresh_tags.return_value = [MagicMock()] * len(images)
    result = runner.invoke(main, ['refresh', *flags, *images], catch_exceptions=False)
    assert result.exit_code == 0
    assert f'{len(images)} Images refreshed' in result.output
    mock_refresh_tags.assert_called_once_with(tuple(images), recursive=expected_recursive)


# -- setup db command --


@pytest.mark.parametrize(
    'flags, expected_kwargs',
    [
        ([], {'overwrite': False, 'download': False}),
        (['-f', '-d'], {'overwrite': True, 'download': True}),
    ],
    ids=['defaults', 'force-download'],
)
@patch('naturtag.cli.setup')
def test_setup_db(mock_setup, runner, flags, expected_kwargs):
    result = runner.invoke(main, ['setup', 'db', *flags], catch_exceptions=False)
    assert result.exit_code == 0
    assert 'Initializing database' in result.output
    mock_setup.assert_called_once_with(**expected_kwargs)


# -- setup shell command --


@patch('naturtag.cli.install_shell_completion')
def test_setup_shell(mock_install, runner):
    result = runner.invoke(main, ['setup', 'shell'], catch_exceptions=False)
    assert result.exit_code == 0
    mock_install.assert_called_once_with('all')


@pytest.mark.parametrize('shell_name', ['bash', 'fish'])
@patch('naturtag.cli.install_shell_completion')
def test_setup_shell__specific(mock_install, runner, shell_name):
    result = runner.invoke(main, ['setup', 'shell', '-s', shell_name], catch_exceptions=False)
    assert result.exit_code == 0
    mock_install.assert_called_once_with(shell_name)


# -- shell completion install --


@pytest.mark.parametrize('shell_name', ['fish', 'bash'])
def test_install_completion(runner, tmp_path, shell_name):
    with (
        patch('naturtag.cli.copyfile'),
        patch.dict('os.environ', {'XDG_CONFIG_HOME': str(tmp_path)}),
    ):
        result = runner.invoke(main, ['setup', 'shell', '-s', shell_name], catch_exceptions=False)
    assert result.exit_code == 0
    assert (tmp_path / shell_name / 'completions').is_dir()


# -- search_taxa_by_name --


@patch('naturtag.cli.get_taxa_autocomplete')
def test_search_taxa_by_name__no_results(mock_autocomplete):
    mock_autocomplete.return_value = {'results': []}
    assert search_taxa_by_name('nonexistent') is None


@patch('naturtag.cli.get_taxa_autocomplete')
def test_search_taxa_by_name__single_result(mock_autocomplete):
    mock_autocomplete.return_value = {'results': [{'id': 12345}]}
    assert search_taxa_by_name('indigo bunting') == 12345


@pytest.mark.parametrize(
    'choice, expected_id',
    [('0', 1), ('1', 2)],
    ids=['first-choice', 'second-choice'],
)
@patch('naturtag.cli.get_taxa_autocomplete')
def test_search_taxa_by_name__multiple_results(mock_autocomplete, choice, expected_id):
    mock_autocomplete.return_value = {'results': SAMPLE_TAXON_RESULTS}
    with patch('naturtag.cli.click.prompt', return_value=choice):
        assert search_taxa_by_name('foo') == expected_id
