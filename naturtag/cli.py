import click
import sys

from naturtag.image_metadata import get_keyword_metadata, write_metadata
from naturtag.inat_darwincore import get_observation_dwc_terms
from naturtag.inat_keywords import get_keywords


def strip_url(ctx, param, value):
    """ If a URL is provided containing an ID, return just the ID """
    return int(value.split('/')[-1].split('-')[0]) if value else None


@click.command()
@click.option('-c', '--common-names', is_flag=True,
              help='Include common names for all ranks (if availalable)')
@click.option('-h', '--hierarchical', is_flag=True,
              help='Generate pipe-delimited hierarchical keywords')
@click.option('-o', '--observation', help='Observation ID or URL', callback=strip_url)
@click.option('-t', '--taxon', help='Taxon ID or URL', callback=strip_url)
@click.option('-x', '--create-xmp', is_flag=True,
              help="Create XMP sidecar file if it doesn't already exist")
@click.argument('images', nargs=-1, type=click.Path(dir_okay=False, exists=True, writable=True))
def tag(observation, taxon, common_names, hierarchical, create_xmp, images):
    """
    Get Keyword tags from an iNaturalist observation or taxon, and write them to local image
    metadata
    """
    if all([observation, taxon]) or not any([observation, taxon]):
        click.secho('One of either observation or taxon is required', fg='red')
        sys.exit()

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


# Main CLI entry point
main = tag
