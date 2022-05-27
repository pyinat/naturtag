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
### Keywords
Keywords will be generated in the format:
`taxonomy:{rank}={name}`

\b
### Darwin Core
If an observation is specified, DwC metadata will also be generated, in the
form of XMP tags. Among other things, this includes taxonomy tags in the
format:
`dwc:{rank}="{name}"`

\b
### Sidecar Files
By default, XMP tags will be written to a sidecar file if it already exists.
Use the `-x` option to create a new one if it doesn't exist.

\b
### Hierarchical Keywords
If specified (`-h`), hierarchical keywords will be generated. These will be
interpreted as a tree structure by image viewers that support them.

\b
For example, the following keywords:
```
Animalia
Animalia|Arthropoda
Animalia|Arthropoda|Chelicerata
Animalia|Arthropoda|Hexapoda
```

\b
Will translate into the following tree structure:
```
Animalia
    ┗━Arthropoda
        ┣━Chelicerata
        ┗━Hexapoda
```

\b
### Shell Completion
Shell tab-completion is available for bash and fish shells. To install, run:
```
naturtag --install-completion [shell name]
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

from naturtag.constants import AUTOCOMPLETE_DIR
from naturtag.metadata import refresh_all, strip_url, tag_images
from naturtag.metadata.keyword_metadata import KeywordMetadata

CODE_BLOCK = compile(r'```\n\s*(.+?)```\s*\n', DOTALL)
CODE_INLINE = compile(r'`([^`]+?)`')
HEADER = compile(r'^\s*#+\s*(.*)$', MULTILINE)


class TaxonParam(click.ParamType):
    """Custom parameter with taxon name autocompletion"""

    name = 'taxon'

    def shell_complete(self, ctx, param, incomplete):
        results = TaxonAutocompleter().search(incomplete)
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
    '-c', '--common-names', is_flag=True, help='Include common names for all ranks that have them'
)
@click.option('-d', '--darwin-core', is_flag=True, help='Generate Darwin Core metadata')
@click.option('-f', '--flickr-format', is_flag=True, help='Output tags in a Flickr-compatible format')
@click.option('-h', '--hierarchical', is_flag=True, help='Generate pipe-delimited hierarchical keywords')
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
    '-x', '--create-sidecar', is_flag=True, help="Create XMP sidecar file if it doesn't already exist"
)
@click.option('-v', '--verbose', is_flag=True, help='Show debug logs')
@click.option(
    '--install-completion',
    type=click.Choice(['all', 'bash', 'fish']),
    help='Install shell completion scripts',
)
@click.argument('image_paths', nargs=-1)
def tag(
    ctx,
    common_names,
    create_sidecar,
    darwin_core,
    flickr_format,
    hierarchical,
    image_paths,
    refresh,
    observation,
    taxon,
    verbose,
    install_completion,
):
    if install_completion:
        install_shell_completion(install_completion)
        ctx.exit()
    n_action_args = sum([1 for arg in [observation, taxon, refresh] if arg is True])
    if n_action_args != 1:
        click.secho('Specify either a taxon, observation, or refresh', fg='red')
        click.echo(ctx.get_help())
        ctx.exit()
    if isinstance(taxon, str):
        taxon = search_taxa_by_name(taxon, verbose)
        if not taxon:
            ctx.exit()

    if verbose:
        enable_logging(level='DEBUG')

    if refresh:
        refresh_all(
            image_paths,
            common_names=common_names,
            darwin_core=darwin_core,
            hierarchical=hierarchical,
            create_sidecar=create_sidecar,
        )
        click.echo('Images refreshed')
        ctx.exit()

    metadata_list = tag_images(
        observation,
        taxon,
        common_names=common_names,
        darwin_core=darwin_core,
        hierarchical=hierarchical,
        create_sidecar=create_sidecar,
        images=image_paths,
    )
    if not metadata_list:
        return

    # Print keywords if specified
    keyword_meta = metadata_list[0].keyword_meta
    if flickr_format:
        print(' '.join(keyword_meta.flickr_tags))
    elif not image_paths or verbose:
        print_metadata(keyword_meta, hierarchical)


def print_metadata(keyword_meta: KeywordMetadata, hierarchical: bool = True):
    rprint('\n'.join(keyword_meta.normal_keywords))
    if hierarchical:
        rprint(keyword_meta.hier_keyword_tree_str)
    else:
        rprint('\n'.join([kw.replace('"', '') for kw in keyword_meta.kv_keyword_list]))


def search_taxa_by_name(taxon: str, verbose: bool = False) -> Optional[int]:
    """Search for a taxon by name.
    If there's a single unambiguous result, return its ID; otherwise prompt with choices.
    """
    response = get_taxa_autocomplete(q=taxon)
    results = response.get('results', [])[:10]
    # results = TaxonAutocompleter().search(taxon)

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

    for script in AUTOCOMPLETE_DIR.glob('*.fish'):
        copyfile(script, completion_dir / script.name)
    print(f'Installed fish completion scripts to {completion_dir}')


def _install_bash_completion():
    """Copy packaged completion scripts for bash"""
    config_dir = Path(os.environ.get('XDG_CONFIG_HOME', '~/.config')).expanduser()
    completion_dir = config_dir / 'bash' / 'completions'
    completion_dir.mkdir(exist_ok=True, parents=True)

    for script in AUTOCOMPLETE_DIR.glob('*.bash'):
        copyfile(script, completion_dir / script.name)
    print('Installed bash completion scripts.')
    print('Add the following to your ~/.bashrc, and restart your shell:')
    print(f'source {completion_dir}/*.bash\n')


# Main CLI entry point
main = tag
tag.help = colorize_help_text(CLI_HELP)
