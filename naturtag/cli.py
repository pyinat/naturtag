import re

import click
from click_help_colors import HelpColorsCommand

from naturtag.image_metadata import get_keyword_metadata, write_metadata
from naturtag.inat_darwincore import get_observation_dwc_terms
from naturtag.inat_keywords import get_keywords


def strip_url(ctx, param, value):
    """ If a URL is provided containing an ID, return just the ID """
    return int(value.split('/')[-1].split('-')[0]) if value else None


@click.command(cls=HelpColorsCommand, help_headers_color='blue', help_options_color='cyan')
@click.pass_context
@click.option('-c', '--common-names', is_flag=True,
              help='Include common names for all ranks that have them')
@click.option('-h', '--hierarchical', is_flag=True,
              help='Generate pipe-delimited hierarchical keywords')
@click.option('-o', '--observation', help='Observation ID or URL', callback=strip_url)
@click.option('-t', '--taxon', help='Taxon ID or URL', callback=strip_url)
@click.option('-x', '--create-xmp', is_flag=True,
              help="Create XMP sidecar file if it doesn't already exist")
@click.argument('images', nargs=-1, type=click.Path(dir_okay=False, exists=True, writable=True))
def tag(ctx, observation, taxon, common_names, hierarchical, create_xmp, images):
    """
    Get taxonomy tags from an iNaturalist observation or taxon, and write them to local image
    metadata.

    \b
    Keywords Only:
    If no images are specified, this command will just print the generated keywords.

    \b
    Keywords:
    Keywords will be generated in the format `taxonomy:{rank}={name}`.

    \b
    Hierarchical Keywords:
    If specified, hierarchical keywords will be generated

    \b
    DarwinCore:
    If an observation is specified, DwC metadata will also be generated, in the form of
    XMP tags. Among other things, this includes taxonomy tags in the format
    `dwc:{rank}="{name}"`.

    \b
    Sidecar Files:
    By default, XMP tags will be written to a sidecar file if it already exists.
    Use the `-x` / `--create-xmp` option to create a new one if it doesn't exist.
    """
    if not any([observation, taxon]):
        # print_help()
        click.echo(ctx.get_help())
        ctx.exit()
    if all([observation, taxon]):
        click.secho('Provide either a taxon or an observation', fg='red')
        ctx.exit()

    keywords = get_keywords(
        observation_id=observation,
        taxon_id=taxon,
        common=common_names,
        hierarchical=hierarchical,
    )
    metadata = get_keyword_metadata(keywords)

    if observation and images:
        metadata.update(get_observation_dwc_terms(observation))
    for image in images:
        write_metadata(image, metadata, create_xmp=create_xmp)

    # If no images were specified, just print keywords
    if not images:
        click.echo('\n'.join(keywords))


def colorize_help_text(text):
    """ An ugly hack to make help text prettier """
    headers = ['Keywords Only:', 'Hierarchical Keywords:', 'Keywords:', 'DarwinCore:',
               'Sidecar Files:']
    for h in headers:
        text = text.replace(h, click.style(h, 'blue'))

    return re.sub(r'`([^`]+)`', click.style(r'\1', 'cyan'), text)


tag.help = colorize_help_text(tag.help)


# Main CLI entry point
main = tag
