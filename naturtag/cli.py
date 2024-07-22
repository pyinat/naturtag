# TODO: Show all matched taxon names if more than one match per taxon ID
# TODO: Bash doesn't support completion help text, so currently only shows IDs
# TODO: Use table formatting from pyinaturalist if format_taxa
import os
import re
from collections import defaultdict
from importlib.metadata import version as pkg_version
from logging import basicConfig, getLogger
from pathlib import Path
from shutil import copyfile
from typing import Optional

import click
from click.shell_completion import CompletionItem
from click_help_colors import HelpColorsGroup
from pyinaturalist import ICONIC_EMOJI, get_taxa_autocomplete
from pyinaturalist_convert.fts import TaxonAutocompleter
from rich import print as rprint
from rich.box import SIMPLE_HEAVY
from rich.logging import RichHandler
from rich.table import Column, Table

from naturtag.constants import CLI_COMPLETE_DIR
from naturtag.metadata import KeywordMetadata, MetaMetadata, refresh_tags, tag_images
from naturtag.storage import Settings, setup
from naturtag.utils import get_valid_image_paths, strip_url

CODE_BLOCK = re.compile(r'```\n\s*(.+?)```\n', re.DOTALL)
CODE_INLINE = re.compile(r'`([^`]+?)`')
HEADER = re.compile(r'^\s*#+\s*(.*)$', re.MULTILINE)


class TaxonParam(click.ParamType):
    """Custom parameter with taxon name autocompletion"""

    name = 'taxon'

    def shell_complete(self, ctx, param, incomplete):
        db_path = Settings.read().db_path
        results = TaxonAutocompleter(db_path).search(incomplete)
        grouped_results = defaultdict(list)
        for taxon in results:
            grouped_results[taxon.id].append(taxon.name)

        # return [CompletionItem(taxon.id, help=taxon.name) for taxon in results]
        return [CompletionItem(id, help=' | '.join(names)) for id, names in grouped_results.items()]


def _strip_url(ctx, param, value):
    return strip_url(value)


def _strip_url_or_name(ctx, param, value):
    return strip_url(value) or value


@click.group(
    cls=HelpColorsGroup,
    invoke_without_command=True,
    help_headers_color='blue',
    help_options_color='cyan',
)
@click.pass_context
@click.option('-v', '--verbose', count=True, help='Show verbose output (up to 3 times)')
@click.option('--version', is_flag=True, help='Show version')
def main(ctx, verbose, version):
    ctx.meta['verbose'] = verbose
    if verbose == 0:
        enable_logging(level='WARNING', external_level='ERROR')
    if verbose == 1:
        enable_logging(level='INFO', external_level='WARNING')
    elif verbose == 2:
        enable_logging(level='DEBUG', external_level='INFO')
    elif verbose >= 3:
        enable_logging(level='DEBUG', external_level='DEBUG')

    if version:
        v = pkg_version('naturtag')
        click.echo(f'naturtag v{v}')
        click.echo(f'User data directory: {Settings.read().data_dir}')
        ctx.exit()
    elif not ctx.invoked_subcommand:
        click.echo(ctx.get_help())


# TODO: Support tab-completion for files (while also supporting glob patterns)
@main.command()
@click.pass_context
@click.option('-f', '--flickr', is_flag=True, help='Output tags in a Flickr-compatible format')
@click.option(
    '-p',
    '--print',
    'print_tags',
    is_flag=True,
    help='Print existing tags for previously tagged images',
)
@click.option('-o', '--observation', help='Observation ID or URL', callback=_strip_url)
@click.option(
    '-t',
    '--taxon',
    help='Taxon name, ID, or URL',
    type=TaxonParam(),
    callback=_strip_url_or_name,
)
@click.argument('image_paths', nargs=-1)
def tag(
    ctx,
    image_paths,
    flickr,
    print_tags,
    observation,
    taxon,
):
    """Write iNaturalist metadata to the console or to image files.

    \b
    ### Image Paths
    Multiple paths are supported, as well as directories and glob patterns,
    for example:
    ```
    0001.jpg IMG*.jpg ~/observations/**.jpg
    ```

    If no images are specified, the generated keywords will be printed.

    \b
    ### Species & Observation IDs
    Either a species or observation may be specified, either by ID or URL.
    For example, all of the following options will fetch the same taxonomy
    metadata:
    ```
    nt tag -t 48978 image.jpg
    nt tag -t https://www.inaturalist.org/taxa/48978-Dirona-picta image.jpg
    nt tag -o 45524803 image.jpg
    nt tag -o https://www.inaturalist.org/observations/45524803 image.jpg
    ```

    The difference is that specifying a species (`-t, --taxon`) will fetch only
    taxonomy metadata, while specifying an observation (`-o, --observation`)
    will fetch taxonomy plus observation metadata.

    \b
    ### Species Search
    You may also search for species by name. If there are multiple results, you
    will be prompted to choose from the top 10 search results:
    ```
    nt tag -t 'indigo bunting'
    ```
    """
    if sum([1 for arg in [observation, taxon, print_tags] if arg]) != 1:
        click.secho('Specify either a taxon, observation, or refresh\n', fg='red')
        click.echo(ctx.get_help())
        ctx.exit()
    elif print_tags and not image_paths:
        click.secho('Specify images', fg='red')
        ctx.exit()
    elif isinstance(taxon, str):
        taxon = search_taxa_by_name(taxon, verbose=ctx.meta['verbose'])
        if not taxon:
            ctx.exit()

    # Print or refresh images instead of tagging with new IDs
    if print_tags:
        print_all_metadata(image_paths, flickr)
        ctx.exit()

    # Run first-time setup if necessary
    setup()

    metadata_objs = tag_images(
        image_paths,
        observation_id=observation,
        taxon_id=taxon,
        include_sidecars=True,
    )
    if not metadata_objs:
        click.secho('No search results found', fg='red')
        return
    click.echo(f'{len(metadata_objs)} images tagged')

    # Print keywords if specified
    if not image_paths or ctx.meta['verbose'] or flickr:
        print_metadata(list(metadata_objs)[0].keyword_meta, flickr)


@main.command()
@click.option('-r', '--recursive', is_flag=True, help='Recursively search subdirectories')
@click.argument('image_paths', nargs=-1)
def refresh(recursive, image_paths):
    """Refresh metadata for previously tagged images.

    Use this command for images that have been previously tagged images with at least a taxon or
    observation ID. This will download the latest metadata for those images and update their tags.
    This is useful, for example, when you update observations on iNaturalist, or when someone else
    identifies your observations for you.

    Like the `tag` command, image files, directories, and glob patterns are supported.

    \b
    ### Examples
    ```
    nt refresh image_1.jpg image_2.jpg
    nt refresh -r image_directory
    ```
    """
    # Run first-time setup if necessary
    setup()

    metadata_objs = refresh_tags(image_paths, recursive=recursive)
    click.echo(f'{len(metadata_objs)} Images refreshed')


@main.group(name='setup')
def setup_group():
    """Setup commands"""


@setup_group.command()
@click.option(
    '-d',
    '--download',
    is_flag=True,
    help='Download taxonomy data if it does not exist locally',
)
@click.option(
    '-f',
    '--force',
    is_flag=True,
    help='Reset database if it already exists',
)
def db(download, force):
    """Set up Naturtag's local database.

    Naturtag uses a SQLite database to store observation and taxonomy data. This command can
    initialize it for the first time, reset it, or download missing data for taxon text search.

    \b
    Example: Full reset and download, with debug logs:
    ```
    nt -vv setup db -f -d
    ```
    """
    click.echo('Initializing database...')
    setup(overwrite=force, download=download)


@setup_group.command()
@click.option(
    '-s',
    '--shell',
    type=click.Choice(['bash', 'fish']),
    help='Install completion script for a specific shell only',
)
def shell(shell):
    """Install shell tab-completion for naturtag.

    \b
    Completion is available for bash and fish shells. To install, run:
    ```
    nt setup shell
    ```

    Or for a specific shell only:
    ```
    nt setup shell -s [shell name]
    ```

    \b
    This will provide tab-completion for CLI options as well as taxon names, for example:
    ```
    nt tag -t corm<TAB>
    ```
    """
    install_shell_completion(shell or 'all')


def enable_logging(level: str = 'INFO', external_level: str = 'WARNING'):
    """Configure logging to standard output with prettier tracebacks, formatting, and terminal
    colors (if supported).

    Args:
        level: Logging level to use for naturtag
        external_level: Logging level to use for other libraries
    """

    basicConfig(
        format='%(message)s',
        datefmt='[%m-%d %H:%M:%S]',
        handlers=[RichHandler(rich_tracebacks=True, markup=True)],
        level=external_level,
    )
    getLogger('naturtag').setLevel(level)
    getLogger('pyinaturalist').setLevel(external_level)
    getLogger('pyinaturalist_convert').setLevel(external_level)


def print_all_metadata(
    image_paths: list[str],
    flickr: bool = False,
    hierarchical: bool = False,
):
    """Print keyword metadata for all specified files"""
    for image_path in get_valid_image_paths(image_paths):
        metadata = MetaMetadata(image_path)
        click.secho(f'\n{image_path}', fg='white')
        print_metadata(metadata.keyword_meta, flickr, hierarchical)


def print_metadata(
    keyword_meta: KeywordMetadata,
    flickr: bool = False,
    hierarchical: bool = False,
):
    """Print keyword metadata for a single observation/taxa"""
    if flickr:
        print(keyword_meta.flickr_tags)
        return

    rprint('\n'.join(keyword_meta.normal_keywords))
    if hierarchical:
        rprint(keyword_meta.hier_keyword_tree_str)
    else:
        for kw in keyword_meta.kv_keyword_list:
            rprint(kw.replace('"', ''))


def search_taxa_by_name(taxon: str, verbose: bool = False) -> Optional[int]:
    """Search for a taxon by name.
    If there's a single unambiguous result, return its ID; otherwise prompt with choices.
    """
    response = get_taxa_autocomplete(q=taxon)
    results = response.get('results', [])[:10]
    # results = TaxonAutocompleter(DB_PATH).search(taxon)

    # No results
    if not results:
        click.echo(f'No matches found for "{taxon}"')
        return None
    # Single results
    if len(results) == 1:
        return results[0]['id']

    # Multiple results
    taxon_table = format_taxa(results, verbose)
    choices = click.Choice([str(t) for t in range(len(results))])

    click.echo(f'Multiple matches found for "{taxon}"; please choose one:')
    rprint(taxon_table)
    taxon_index = click.prompt('Choice', type=choices, show_choices=False)
    return results[int(taxon_index)]['id']


def format_taxa(results, verbose: bool = False) -> Table:
    """Format taxon autocomplete results into a table"""
    table = Table(
        Column('#', style='bold white'),
        'Rank',
        'Name',
        'Common name',
        box=SIMPLE_HEAVY,
        header_style='bold cyan',
    )
    if verbose:
        table.add_column('Matched term')
        table.add_column('ID')

    for i, t in enumerate(results):
        icon = ICONIC_EMOJI.get(t['iconic_taxon_id'], ' ')
        row = [str(i), t['rank'], f'{icon} {t["name"]}', t.get('preferred_common_name')]
        if verbose:
            row += [t['matched_term'], str(t['id'])]
        table.add_row(*row)

    return table


def colorize_help_text(text):
    """Colorize code blocks and headers in CLI help text"""
    text = re.sub(r'^    ', '', text, flags=re.MULTILINE)
    text = HEADER.sub(click.style(r'\1:', 'blue', bold=True), text)
    text = CODE_BLOCK.sub(click.style(r'\1', 'cyan'), text)
    text = CODE_INLINE.sub(click.style(r'\1', 'cyan'), text)
    return text


def install_shell_completion(shell: str):
    """Copy packaged completion scripts for the specified shell(s)"""
    if shell in ['all', 'bash']:
        _install_bash_completion()
    if shell in ['all', 'fish']:
        _install_fish_completion()


def _install_fish_completion():
    """Copy packaged completion scripts for fish shell"""
    config_dir = Path(os.environ.get('XDG_CONFIG_HOME', '~/.config')).expanduser()
    completion_dir = config_dir / 'fish' / 'completions'
    completion_dir.mkdir(exist_ok=True, parents=True)

    for script in CLI_COMPLETE_DIR.glob('*.fish'):
        copyfile(script, completion_dir / script.name)
    print(f'Installed fish completion scripts to {completion_dir}')


def _install_bash_completion():
    """Copy packaged completion scripts for bash"""
    config_dir = Path(os.environ.get('XDG_CONFIG_HOME', '~/.config')).expanduser()
    completion_dir = config_dir / 'bash' / 'completions'
    completion_dir.mkdir(exist_ok=True, parents=True)

    for script in CLI_COMPLETE_DIR.glob('*.bash'):
        copyfile(script, completion_dir / script.name)
    print('Installed bash completion scripts.')
    print('Add the following to your ~/.bashrc, and restart your shell:')
    print(f'source {completion_dir}/*.bash\n')


for cmd in [tag, refresh, db, shell]:
    cmd.help = colorize_help_text(cmd.help)
