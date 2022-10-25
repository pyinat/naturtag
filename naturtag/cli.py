CLI_HELP = """
Get taxonomy tags from an iNaturalist observation or taxon, and write them
either to the console or to local image metadata.

\b
### Species & Observation IDs
Either a species or observation may be specified, either by ID or URL.
For example, all of the following options will fetch the same taxonomy
metadata:
```
naturtag -t 48978 image.jpg
naturtag -t https://www.inaturalist.org/taxa/48978-Dirona-picta image.jpg
naturtag -o 45524803 image.jpg
naturtag -o https://www.inaturalist.org/observations/45524803 image.jpg
```

\b
The difference is that specifying a species (`-t, --taxon`) will fetch only
taxonomy metadata, while specifying an observation (`-o, --observation`)
will fetch taxonomy plus observation metadata.

\b
### Refresh
If you previously tagged images with at least a taxon or observation ID, you
can use (`-r, --refresh`) to re-fetch the latest metadata for those images.
This is useful, for example, if you update an observation on iNaturalist or
someone else identifies it for you.
```
naturtag -r image.jpg
```

\b
### Species Search
You may also search for species by name. If there are multiple results, you
will be prompted to choose from the top 10 search results:
```
naturtag -t 'indigo bunting'
```

\b
### Images
Multiple paths are supported, as well as glob patterns, for example:
`0001.jpg IMG*.jpg ~/observations/**.jpg`

If no images are specified, the generated keywords will be printed.

\b
### Shell Completion
Shell tab-completion is available for bash and fish shells. To install, run:
```
naturtag --install [shell name]
```

\b
This will provide tab-completion for options as well as taxon names, for example:
```
naturtag -t corm<TAB>
```
"""
# TODO: Show all matched taxon names if more than one match per taxon ID
# TODO: Bash doesn't support completion help text, so currently only shows IDs
# TODO: Use table formatting from pyinaturalist if format_taxa
import os
from collections import defaultdict
from importlib.metadata import version as pkg_version
from pathlib import Path
from re import DOTALL, MULTILINE, compile
from shutil import copyfile
from typing import Optional

import click
from click.shell_completion import CompletionItem
from click_help_colors import HelpColorsCommand
from pyinaturalist import ICONIC_EMOJI, enable_logging, get_taxa_autocomplete
from pyinaturalist_convert.fts import TaxonAutocompleter
from rich import print as rprint
from rich.box import SIMPLE_HEAVY
from rich.table import Column, Table

from naturtag.constants import APP_DIR, CLI_COMPLETE_DIR, DB_PATH
from naturtag.metadata import refresh_tags, strip_url, tag_images
from naturtag.metadata.keyword_metadata import KeywordMetadata
from naturtag.metadata.meta_metadata import MetaMetadata
from naturtag.settings import Settings, setup

CODE_BLOCK = compile(r'```\n\s*(.+?)```\s*\n', DOTALL)
CODE_INLINE = compile(r'`([^`]+?)`')
HEADER = compile(r'^\s*#+\s*(.*)$', MULTILINE)


class TaxonParam(click.ParamType):
    """Custom parameter with taxon name autocompletion"""

    name = 'taxon'

    def shell_complete(self, ctx, param, incomplete):
        results = TaxonAutocompleter(DB_PATH).search(incomplete)
        grouped_results = defaultdict(list)
        for taxon in results:
            grouped_results[taxon.id].append(taxon.name)

        # return [CompletionItem(taxon.id, help=taxon.name) for taxon in results]
        return [CompletionItem(id, help=' | '.join(names)) for id, names in grouped_results.items()]


def _strip_url(ctx, param, value):
    return strip_url(value)


def _strip_url_or_name(ctx, param, value):
    return strip_url(value) or value


@click.command(cls=HelpColorsCommand, help_headers_color='blue', help_options_color='cyan')
@click.pass_context
@click.option(
    '-f', '--flickr-format', is_flag=True, help='Output tags in a Flickr-compatible format'
)
@click.option(
    '-p',
    '--print',
    'print_tags',
    is_flag=True,
    help='Print existing tags for previously tagged images',
)
@click.option('-r', '--refresh', is_flag=True, help='Refresh metadata for previously tagged images')
@click.option('-o', '--observation', help='Observation ID or URL', callback=_strip_url)
@click.option(
    '-t',
    '--taxon',
    help='Taxon name, ID, or URL',
    type=TaxonParam(),
    callback=_strip_url_or_name,
)
@click.option(
    '--install',
    type=click.Choice(['all', 'bash', 'fish']),
    help='Install shell completion scripts',
)
@click.option('-v', '--verbose', is_flag=True, help='Show debug logs')
@click.option('--version', is_flag=True, help='Show version')
@click.argument('image_paths', nargs=-1)
def tag(
    ctx,
    image_paths,
    flickr_format,
    print_tags,
    refresh,
    observation,
    taxon,
    install,
    verbose,
    version,
):
    if install:
        install_shell_completion(install)
        setup(Settings.read())
        ctx.exit()
    elif version:
        v = pkg_version('naturtag')
        click.echo(f'naturtag v{v}')
        click.echo(f'User data directory: {APP_DIR}')
        ctx.exit()
    elif sum([1 for arg in [observation, taxon, print_tags, refresh] if arg]) != 1:
        click.secho('Specify either a taxon, observation, or refresh', fg='red')
        click.echo(ctx.get_help())
        ctx.exit()
    elif (print_tags or refresh) and not image_paths:
        click.secho('Specify images', fg='red')
        ctx.exit()
    elif isinstance(taxon, str):
        taxon = search_taxa_by_name(taxon, verbose)
        if not taxon:
            ctx.exit()
    if verbose:
        enable_logging(level='DEBUG')

    # Print or refresh images instead of tagging with new IDs
    if print_tags:
        print_all_metadata(image_paths, flickr_format)
        ctx.exit()
    if refresh:
        refresh_tags(image_paths, recursive=True)
        click.echo('Images refreshed')
        ctx.exit()

    metadata_objs = tag_images(
        image_paths,
        observation_id=observation,
        taxon_id=taxon,
        include_sidecars=True,
    )
    if not metadata_objs:
        return

    # Print keywords if specified
    if not image_paths or verbose or flickr_format:
        print_metadata(list(metadata_objs)[0].keyword_meta, flickr_format)


def print_all_metadata(
    image_paths: list[str],
    flickr_format: bool = False,
    hierarchical: bool = False,
):
    """Print keyword metadata for all specified files"""
    for image_path in image_paths:
        metadata = MetaMetadata(image_path)
        click.secho(f'\n{image_path}', fg='white')
        print_metadata(metadata.keyword_meta, flickr_format, hierarchical)


def print_metadata(
    keyword_meta: KeywordMetadata,
    flickr_format: bool = False,
    hierarchical: bool = False,
):
    """Print keyword metadata for a single observation/taxa"""
    if flickr_format:
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


# Main CLI entry point
main = tag
tag.help = colorize_help_text(CLI_HELP)
