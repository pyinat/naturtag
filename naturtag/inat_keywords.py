""" Tools to get keyword tags (e.g., for XMP metadata) from iNaturalist observations """
from logging import getLogger

from pyinaturalist.node_api import get_observation, get_taxa_by_id

logger = getLogger().getChild(__name__)


def get_observation_taxon(observation_id):
    """ Get the current taxon ID for the given observation """
    logger.info(f'Fetching observation {observation_id}')
    obs = get_observation(observation_id)
    if obs.get('community_tax_id') and obs['community_tax_id'] != obs['taxon']['id']:
        logger.warning('Community ID does not match selected taxon')
    return obs['taxon']['id']


# TODO: separate species, binomial, trinomial
def get_keywords(observation_id=None, taxon_id=None, common=False, hierarchical=False):
    """ Get all taxonomic keywords for a given observation or taxon """
    min_tax_id = taxon_id or get_observation_taxon(observation_id)
    taxa = get_parent_taxa(min_tax_id)

    keywords = get_taxonomy_keywords(taxa)
    if hierarchical:
        keywords.extend(get_hierarchical_keywords(keywords))
    if common:
        keywords.extend(get_common_keywords(taxa))

    keywords.append(f'inat:taxon_id={min_tax_id}')
    keywords.append(f'dwc:taxonID={min_tax_id}')
    if observation_id:
        keywords.append(f'inat:observation_id={observation_id}')
        keywords.append(f'dwc:catalogNumber={observation_id}')

    logger.info(f'{len(keywords)} keywords generated')
    return keywords


def get_parent_taxa(taxon_id):
    """ Get a taxon with all its parents """
    logger.info(f'Fetching taxon {taxon_id}')
    r = get_taxa_by_id(taxon_id)
    taxon = r['results'][0]
    logger.info(f'{len(taxon["ancestors"])} parent taxa found')
    return taxon['ancestors'] + [taxon]


def get_taxonomy_keywords(taxa):
    """ Format a list of taxa into rank keywords """
    return [quote(f'taxonomy:{t["rank"]}={t["name"]}') for t in taxa]


def get_common_keywords(taxa):
    """ Format a list of taxa into common name keywords """
    # TODO: Split comma-delimited lists, deduplicate, remove some descriptors, e.g.:
    # ['Velvet Mites', 'Velvet Mites, Chiggers, and Relatives']
    # -> ['Velvet Mites', 'Chiggers']
    # [s.strip() for s in re.split(',|and', "Velvet Mites, Chiggers, and Relatives")]
    keywords = [quote(t.get('preferred_common_name', '')) for t in taxa]
    return list(filter(None, keywords))


# TODO: Also include common names in hierarchy?
def get_hierarchical_keywords(keywords):
    hier_keywords = [keywords[0]]
    for rank_name in keywords[1:]:
        hier_keywords.append(f'{hier_keywords[-1]}|{rank_name}')
    return hier_keywords


def quote(s):
    """ Surround keyword in quotes if it contains whitespace """
    return f'"{s}"' if ' ' in s else s
