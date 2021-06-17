from logging import basicConfig
from re import DOTALL, MULTILINE, compile
from typing import Optional

import click
from click_help_colors import HelpColorsCommand
from pyinaturalist.node_api import get_taxa_autocomplete
from rich import print as rprint
from rich.box import SIMPLE_HEAVY
from rich.table import Column, Table

from naturtag.constants import ICONIC_EMOJI
from naturtag.image_glob import glob_paths
from naturtag.inat_metadata import strip_url
from naturtag.tagger import tag_images

CODE_BLOCK = compile(r'```\n(.+?)```\s*\n', DOTALL)
CODE_INLINE = compile(r'`([^`]+?)`')
HEADER = compile(r'^#+\s*(.*)$', MULTILINE)


def colorize_help_text(text):
    """An ugly hack to make help text prettier"""
    text = HEADER.sub(click.style(r'\1:', 'blue'), text)
    text = CODE_BLOCK.sub(click.style(r'\1', 'cyan'), text)
    text = CODE_INLINE.sub(click.style(r'\1', 'cyan'), text)
    return text


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
@click.option('-o', '--observation', help='Observation ID or URL', callback=_strip_url)
@click.option('-t', '--taxon', help='Taxon name, ID, or URL', callback=_strip_url_or_name)
@click.option(
    '-x', '--create-xmp', is_flag=True, help="Create XMP sidecar file if it doesn't already exist"
)
@click.option('-v', '--verbose', is_flag=True, help='Show additional information')
@click.argument('image_paths', nargs=-1)
def tag(
    ctx,
    common_names,
    create_xmp,
    darwin_core,
    flickr_format,
    hierarchical,
    image_paths,
    observation,
    taxon,
    verbose,
):
    """
    Get taxonomy tags from an iNaturalist observation or taxon, and write them
    either to the console or to local image metadata.

    \b
    ### Species & Observation IDs
    Either a species or observation may be specified, either by ID or URL.
    For example, all of the following options will fetch the same taxonomy
    metadata:
    ```
    naturtag -t 48978
    naturtag -t https://www.inaturalist.org/taxa/48978-Dirona-picta
    naturtag -o 45524803
    naturtag -o https://www.inaturalist.org/observations/45524803
    ```

    \b
    The difference is that specifying a species (`-t, --taxon`) will fetch only
    taxonomy metadata, while specifying an observation (`-o, --observation`)
    will fetch taxonomy plus observation metadata.

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
    ### DarwinCore
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
    """
    if not any([observation, taxon]):
        click.echo(ctx.get_help())
        ctx.exit()
    if all([observation, taxon]):
        click.secho('Provide either a taxon or an observation', fg='red')
        ctx.exit()
    if isinstance(taxon, str):
        taxon = search_taxa_by_name(taxon, verbose)
        if not taxon:
            ctx.exit()

    if verbose:
        basicConfig(level='DEBUG')

    _, keywords, metadata = tag_images(
        observation,
        taxon,
        common_names,
        darwin_core,
        hierarchical,
        create_xmp,
        glob_paths(image_paths),
    )

    # Print keywords and/or DWC tags, if appropriate
    if flickr_format:
        print(' '.join(keywords))
    elif not image_paths or verbose:
        rprint('\n'.join([kw.replace('"', '') for kw in keywords]))
        if darwin_core and metadata:
            rprint(metadata)


def search_taxa_by_name(taxon: str, verbose: bool = False) -> Optional[int]:
    """Search for a taxon by name.
    If there's a single unambiguous result, return its ID; otherwise prompt with choices.
    """
    response = get_taxa_autocomplete(q=taxon)
    results = response.get('results', [])[:10]

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


# Main CLI entry point
main = tag
tag.help = colorize_help_text(tag.help)
