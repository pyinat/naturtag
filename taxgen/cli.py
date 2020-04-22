import click
import sys

from taxgen.inat_keywords import get_keywords


@click.group()
def main():
    """ Main CLI entry point """


@main.command()
@click.option('-c', '--common-names', is_flag=True,
              help='Include common names for all ranks (if availalable)')
@click.option('-h', '--hierarchical', is_flag=True,
              help='Generate pipe-delimited hierarchical keywords')
@click.option('-o', '--observation', help='Observation ID')
@click.option('-t', '--taxon', help='Taxon ID')
def tags(observation, taxon, common_names, hierarchical):
    """
    Get Keyword tags from iNat observations or taxa.
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
    print('\n'.join(keywords))
