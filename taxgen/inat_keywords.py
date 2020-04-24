#!/usr/bin/env python3
# TODO: Hierarchical tags
"""
Tools to get keyword tags (e.g., for XMP metadata) from iNaturalist observations
"""
from logging import getLogger

from pyinaturalist.node_api import get_observation, get_taxa_by_id

logger = getLogger(__name__)


def get_observation_taxon(observation_id):
    """ Get the current taxon ID for the given observation """
    obs = get_observation(observation_id)
    if obs.get('community_tax_id') and obs['community_tax_id'] != obs['taxon']['id']:
        logger.warn('Community ID does not match selected taxon')
    return obs['taxon']['id']


def get_keywords(observation_id=None, taxon_id=None, common=False, hierarchical=False):
    """ Get all taxonomic keywords for a given observation or taxon """
    min_tax_id = taxon_id or get_observation_taxon(observation_id)
    taxa = get_taxonomy(min_tax_id)

    keywords = get_taxonomy_keywords(taxa)
    if common:
        keywords.extend(get_common_keywords(taxa))
    if hierarchical:
        keywords.extend(get_hierarchical_keywords(taxa))

    keywords.append(f'inat:taxon_id={min_tax_id}')
    if observation_id:
        keywords.append(f'inat:observation_id={observation_id}')

    return keywords


def get_taxonomy(taxon_id):
    """ Get a taxon with all its parents """
    r = get_taxa_by_id(taxon_id)
    taxon = r['results'][0]
    return taxon['ancestors'] + [taxon]


def get_taxonomy_keywords(taxa):
    """ Format a list of taxa into rank keywords """
    return [quote(f'taxonomy:{t["rank"]}={t["name"]}') for t in taxa]


def get_common_keywords(taxa):
    """ Format a list of taxa into common name keywords """
    keywords = [quote(t.get('preferred_common_name', '')) for t in taxa]
    return list(filter(None, keywords))


def get_hierarchical_keywords(taxa):
    raise NotImplementedError


def quote(s):
    """ Surround keyword in quotes if it contains whitespace """
    return f'"{s}"' if ' ' in s else s
