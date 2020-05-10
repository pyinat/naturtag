import click
import sys

from taxgen.image_metadata import get_keyword_metadata, write_metadata
from taxgen.inat_darwincore import get_observation_dwc_terms
from taxgen.inat_export import generate_tree as inat_generate_tree
from taxgen.inat_keywords import get_keywords
from taxgen.ncbi_import import prepare_ncbi_taxdump
from taxgen.ncbi_export import generate_trees as ncbi_generate_trees
from taxgen.constants import DATA_DIR, EUKARYOTA_TAX_ID, INAT_OBSERVATION_FILE


def strip_url(ctx, param, value):
    """ If a URL is provided containing an ID, return just the ID """
    return value.split('/')[-1].split('-')[0] if value else None


@click.group()
def main():
    """ Main CLI entry point """


@main.group()
def inat():
    """ Commands for interacting with iNaturalist data """


@inat.command()
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


@inat.command(name='export')
@click.option(
    '-i', '--input-file',
    default=INAT_OBSERVATION_FILE,
    show_default=True,
    type=click.Path(exists=True),
    help='CSV export file to read',
)
@click.option(
    '-o', '--output-dir',
    default=DATA_DIR,
    show_default=True,
    type=click.Path(),
    help='Directory to write output files to',
)
def inat_export(input_file, output_dir):
    """
    Read a CSV-formatted data export from iNaturalist and ouptut as a tree of keywords.
    A data export can be generated from the web UI here: https://www.inaturalist.org/observations/export
    """
    inat_generate_tree(input_file, output_dir)


@main.group()
def ncbi():
    """ Commands for interacting with NCBI data """


@ncbi.command(name='export')
@click.option(
    '-o', '--output-dir',
    default=DATA_DIR,
    show_default=True,
    type=click.Path(),
    help='Directory to write output files to',
)
@click.argument('root_nodes', nargs=-1)
def ncbi_export(output_dir, root_nodes):
    """
    Download and read NCBI taxonomy data and output as a tree of keywords.
    Optionally specify one or more taxon IDs to process only those taxa and their
    descendants. Defaults to Eukaryotes.
    """
    df = prepare_ncbi_taxdump()
    ncbi_generate_trees(df, output_dir, root_nodes or [EUKARYOTA_TAX_ID])
    # ncbi_generate_trees(df, [ANIMALIA_TAX_ID, PLANT_TAX_ID, FUNGI_TAX_ID])
