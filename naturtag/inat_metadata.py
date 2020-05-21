""" Tools to get keyword tags (e.g., for XMP metadata) from iNaturalist observations """
from logging import getLogger
import xmltodict

from pyinaturalist.constants import RANKS
from pyinaturalist.node_api import (
    get_observation,
    get_taxa,
    get_taxa_by_id,
    get_taxa_autocomplete as _get_taxa_autocomplete,
)
from pyinaturalist.rest_api import get_observations  # TODO: Currently only in dev branch
from naturtag.constants import DWC_NAMESPACES, TAXON_KEYS, OBSERVATION_KEYS

logger = getLogger().getChild(__name__)


def get_observation_taxon(observation_id):
    """ Get the current taxon ID for the given observation """
    logger.info(f'Fetching observation {observation_id}')
    obs = get_observation(observation_id)
    if obs.get('community_tax_id') and obs['community_tax_id'] != obs['taxon']['id']:
        logger.warning('Community ID does not match selected taxon')
    return obs['taxon']['id']


def get_observation_dwc_terms(observation_id):
    """ Get all DWC terms from an iNaturalist observation """
    logger.info(f'Getting darwincore terms for observation {observation_id}')
    obs_dwc = get_observations(id=observation_id, response_format='dwc')
    return convert_dwc_to_xmp(obs_dwc)


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


def get_child_taxa(taxon_id):
    """ Get a taxon's children' """
    logger.info(f'Fetching children of taxon {taxon_id}')
    r = get_taxa(parent_id=taxon_id)
    logger.info(f'{len(r["results"])} child taxa found')
    return r['results']


def get_parent_taxa(taxon_id):
    """ Get a taxon with all its parents """
    logger.info(f'Fetching parents of taxon {taxon_id}')
    r = get_taxa_by_id(taxon_id)
    taxon = r['results'][0]
    logger.info(f'{len(taxon["ancestors"])} parent taxa found')
    return taxon['ancestors'] + [taxon]


def get_taxa_by_best_info(id=None, rank=None, name=None):
    """ Get taxon info by ID if provided, otherwise rank + name """
    params = {'id': id} if id else {'rank': rank, 'q': name}
    return get_taxa(**params)['results']

def get_taxa_autocomplete(search_str):
    """ Get taxa autocomplete search results, both with the matched term plus extra info """
    results = _get_taxa_autocomplete(q=search_str).get('results', [])
    return [_get_taxon_labels(taxon) for taxon in results]


def _get_taxon_labels(taxon):
    # Padding in format strings is to visually align taxon IDs (< 7 chars) and ranks (< 11 chars)
    display_text = "{:<8} {:>12} {}".format(taxon["id"], taxon["rank"].title(), taxon["name"])
    if 'preferred_common_name' in taxon:
        display_text += f' ({taxon["preferred_common_name"]})'
    return display_text, taxon['matched_term']


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


def sort_taxonomy_keywords(keywords):
    """ Sort keywords by taxonomic rank, where applicable """
    def get_rank_idx(tag):
        base_tag = tag.split(':')[-1].split('=')[0]
        return RANKS.index(base_tag) if base_tag in RANKS else 0
    return sorted(keywords, key=get_rank_idx, reverse=True)


def get_inaturalist_ids(metadata):
    """ Look for taxon and/or observation IDs from metadata if available """
    # Get first non-None value from specified keys, if any; otherwise return None
    def _first_match(d, keys):
        return next(filter(None, map(d.get, keys)), None)

    # Check all possible keys for valid taxon and observation IDs
    taxon_id = _first_match(metadata, TAXON_KEYS)
    observation_id = _first_match(metadata, OBSERVATION_KEYS)
    logger.info(f'Taxon ID: {taxon_id} | Observation ID: {observation_id}')
    return taxon_id, observation_id


def get_min_rank(metadata):
    """ Get the lowest (most specific) taxonomic rank from tags, if any """
    for rank in RANKS[::-1]:
        if rank in metadata:
            logger.info(f'Found minimum rank: {rank} = {metadata[rank]}')
            return (rank, metadata)
    return None


def quote(s):
    """ Surround keyword in quotes if it contains whitespace """
    return f'"{s}"' if ' ' in s else s


def convert_dwc_to_xmp(dwc):
    """
    Get all DWC terms from XML content containing a SimpleDarwinRecordSet, and format them as
    XMP tags. For example: ``'dwc:species' -> 'Xmp.dwc.species'``

    Aside: This is a fun project. If it involved manual XML processsing, it would no longer
    be a fun project. Thanks, xmltodict!
    """
    # Get inner record as a dict, if it exists
    xml_dict = xmltodict.parse(dwc)
    dwr = xml_dict.get("dwr:SimpleDarwinRecordSet", {}).get("dwr:SimpleDarwinRecord")
    if not dwr:
        logger.warning('No SimpleDarwinRecord found')
        return {}

    # iNat sometimes includes duplicate occurence IDs
    if isinstance(dwr["dwc:occurrenceID"], list):
        dwr["dwc:occurrenceID"] = dwr["dwc:occurrenceID"][0]

    def _format_term(k):
        ns, term = k.split(':')
        return f'Xmp.{ns}.{term}'

    def _include_term(k):
        ns = k.split(':')[0]
        return ns in DWC_NAMESPACES

    # Format as XMP tags
    return {_format_term(k): v for k, v in dwr.items() if _include_term(k)}

