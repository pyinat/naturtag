#!/usr/bin/env python3
"""
Tools to get keyword tags (e.g., for XMP metadata) from iNaturalist observations
"""
import sys
from logging import getLogger

from pyinaturalist.node_api import get_observation, get_taxa_by_id

logger = getLogger(__name__)


def get_observation_taxon(observation_id):
    """ Get the current taxon ID for the given observation """
    obs = get_observation(observation_id)
    if obs.get('community_tax_id') and obs['community_tax_id'] != obs['taxon']['id']:
        logger.warn('Community ID does not match selected taxon')
    return obs['taxon']['id']


def get_taxonomy(taxon_id):
    """ Get taxon with all its parents """
    r = get_taxa_by_id(taxon_id)
    taxon = r['results'][0]
    return taxon['ancestors'] + [taxon]


def get_keywords_from_taxa(taxa):
    """ Format a list of taxa into rank keywords """
    keywords = []

    for t in taxa:
        keywords.append(_quote(f'taxonomy:{t["rank"]}={t["name"]}'))
    for t in taxa:
        if t.get('preferred_common_name'):
            keywords.append(_quote(t['preferred_common_name']))

    return keywords


def _quote(s):
    """ Surround keyword in quotes if it contains whitespace """
    return f'"{s}"' if ' ' in s else s


if __name__ == '__main__':
    # tax_id = sys.argv[1]
    obs_id = sys.argv[1]
    tax_id = get_observation_taxon(obs_id)
    taxonomy = get_taxonomy(tax_id)
    keywords = get_keywords_from_taxa(taxonomy)
    keywords.append(f'inat:observation_id=obs_id')
    print('\n'.join(keywords))
