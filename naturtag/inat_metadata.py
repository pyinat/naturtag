"""Tools to get keyword tags from iNaturalist observations"""
# TODO: Get separate keywords for species, binomial, and trinomial
from logging import getLogger
from typing import Optional
from urllib.parse import urlparse

import xmltodict
from pyinaturalist import Observation, Taxon, iNatClient
from pyinaturalist.v0 import get_observations
from pyinaturalist.v1 import get_observation

from naturtag.constants import COMMON_NAME_IGNORE_TERMS, DWC_NAMESPACES, DWC_TAXON_TERMS, IntTuple
from naturtag.models import MetaMetadata

inat_client = iNatClient()
logger = getLogger().getChild(__name__)


# TODO : get common names for specified locale
def get_inat_metadata(
    observation_id: int,
    taxon_id: int,
    common_names: bool = False,
    darwin_core: bool = False,
    hierarchical: bool = False,
    locale: str = None,
) -> Optional[MetaMetadata]:
    """Get image metadata based on an iNaturalist observation and/or taxon"""
    inat_metadata = MetaMetadata()
    observation, taxon = None, None

    # Get observation and/or taxon records
    if observation_id:
        observation = inat_client.observations.from_id(observation_id).one()
        taxon_id = observation.taxon.id

    # Observation.taxon doesn't include ancestors, so we always need to fetch the full taxon record
    taxon = inat_client.taxa.from_id(taxon_id).one()
    if not taxon:
        logger.warning(f'No taxon found: {taxon_id}')
        return None

    # Get all specified keyword categories
    keywords = get_taxonomy_keywords(taxon)
    if hierarchical:
        keywords.extend(get_hierarchical_keywords(keywords))
    if common_names:
        keywords.extend(get_common_keywords(taxon))
    keywords.extend(get_id_keywords(taxon_id, observation_id))

    logger.info(f'{len(keywords)} total keywords generated')
    inat_metadata.update_keywords(keywords)

    # Convert and add coordinates
    if observation:
        inat_metadata.update_coordinates(observation.location)

    # Get DwC metadata, if specified
    dwc_metadata = {}
    if darwin_core:
        if observation:
            dwc_metadata = get_observation_dwc_terms(observation_id)
        elif taxon:
            dwc_metadata = get_taxon_dwc_terms(taxon_id)
        inat_metadata.update(dwc_metadata)

    return inat_metadata


def get_keywords(
    observation_id: int = None,
    taxon_id: int = None,
    common: bool = False,
    hierarchical: bool = False,
    locale: str = None,
) -> list[str]:
    """Get all taxonomic keywords for a given observation or taxon"""
    observation, taxon = None, None
    if observation_id:
        observation = inat_client.observations.from_id(observation_id).one()
        taxon_id = observation.taxon.id  # Doesn't include full ancestry, so need to fetch by ID
    taxon = inat_client.taxa.from_id(taxon_id).one()
    if not taxon:
        logger.warning(f'No taxon found: {taxon_id}')
        return []

    # Get all specified keyword categories
    keywords = []  # get_id_keywords(taxon_id, observation_id)
    keywords.extend(get_taxonomy_keywords(taxon))
    if hierarchical:
        keywords.extend(get_hierarchical_keywords(keywords))
    if common:
        keywords.extend(get_common_keywords(taxon))

    logger.info(f'{len(keywords)} total keywords generated')
    return keywords


def get_observed_taxa(username: str, include_casual: bool = False, **kwargs) -> dict[int, int]:
    """Get counts of taxa observed by the user, ordered by number of observations descending"""
    if not username:
        return {}
    taxon_counts = inat_client.observations.species_counts(
        user_login=username,
        verifiable=None if include_casual else True,  # False will return *only* casual observations
        **kwargs,
    )
    logger.info(f'{len(taxon_counts)} user-observed taxa found')
    taxon_counts = sorted(taxon_counts, key=lambda x: x.count, reverse=True)
    return {t.id: t.count for t in taxon_counts}


def get_records_from_metadata(metadata: 'MetaMetadata') -> tuple[Taxon, Observation]:
    """Get observation and/or taxon records based on image metadata"""
    logger.info(f'Searching for matching taxon and/or observation for {metadata.image_path}')
    taxon, observation = None, None

    # Handle observation with no taxon ID?
    if metadata.has_observation:
        observation = inat_client.observations.from_id(metadata.observation_id).one()
        taxon = observation.taxon
    elif metadata.has_taxon:
        taxon = inat_client.taxa.from_id(metadata.taxon_id)

    return taxon, observation


#  Keyword categories
# -------------------


def get_taxonomy_keywords(taxon: Taxon) -> list[str]:
    """Format a list of taxa into rank keywords"""
    return [_quote(f'taxonomy:{t.rank}={t.name}') for t in [taxon, *taxon.ancestors]]


def get_id_keywords(taxon_id: int, observation_id: int = None) -> list[str]:
    keywords = [f'inaturalist:taxon_id={taxon_id}', f'dwc:taxonID={taxon_id}']
    if observation_id:
        keywords.append(f'inaturalist:observation_id={observation_id}')
        keywords.append(f'dwc:catalogNumber={observation_id}')
    return keywords


def get_common_keywords(taxon: Taxon) -> list[str]:
    """Format a list of taxa into common name keywords.
    Filters out terms that aren't useful to keep as tags
    """
    keywords = [t.preferred_common_name for t in [taxon, *taxon.ancestors]]

    def is_ignored(kw):
        return any([ignore_term in kw.lower() for ignore_term in COMMON_NAME_IGNORE_TERMS])

    return [_quote(kw) for kw in keywords if kw and not is_ignored(kw)]


def get_hierarchical_keywords(keywords: list) -> list[str]:
    """Translate sorted taxonomy keywords into pipe-delimited hierarchical keywords"""
    hier_keywords = [keywords[0]]
    for rank_name in keywords[1:]:
        hier_keywords.append(f'{hier_keywords[-1]}|{rank_name}')
    return hier_keywords


# Darwin Core stuff
# -----------------
# TODO: Use pyinaturalist_convert.dwc for this


def get_observation_dwc_terms(observation_id: int) -> dict[str, str]:
    """Get all DWC terms for an iNaturalist observation"""
    logger.info(f'Getting Darwin Core terms for observation {observation_id}')
    obs_dwc = get_observations(id=observation_id, response_format='dwc')
    return convert_dwc_to_xmp(obs_dwc)


def get_taxon_dwc_terms(taxon_id: int) -> dict[str, str]:
    """Get all DWC terms for an iNaturalist taxon.
    Since there is no DWC format for ``GET /taxa``, we'll just search for a random observation
    with this taxon ID, strip off the observation metadata, and keep only the taxon metadata.
    """
    logger.info(f'Getting Darwin Core terms for taxon {taxon_id}')
    obs_dwc = get_observations(taxon_id=taxon_id, per_page=1, response_format='dwc')
    dwc_xmp = convert_dwc_to_xmp(obs_dwc)
    return {k: v for k, v in dwc_xmp.items() if k in DWC_TAXON_TERMS}


def convert_dwc_to_xmp(dwc: str) -> dict[str, str]:
    """
    Get all DWC terms from XML content containing a SimpleDarwinRecordSet, and format them as
    XMP tags. For example: ``'dwc:species' -> 'Xmp.dwc.species'``
    """
    # Get inner record as a dict, if it exists
    xml_dict = xmltodict.parse(dwc)
    dwr = xml_dict.get('dwr:SimpleDarwinRecordSet', {}).get('dwr:SimpleDarwinRecord')
    if not dwr:
        logger.warning('No SimpleDarwinRecord found')
        return {}

    # iNat sometimes includes duplicate occurrence IDs
    if isinstance(dwr['dwc:occurrenceID'], list):
        dwr['dwc:occurrenceID'] = dwr['dwc:occurrenceID'][0]

    def _format_term(k):
        namespace, term = k.split(':')
        return f'Xmp.{namespace}.{term}'

    def _include_term(k):
        return k.split(':')[0] in DWC_NAMESPACES

    # Format as XMP tags
    return {_format_term(k): v for k, v in dwr.items() if _include_term(k)}


# Other utilities
# ---------------


# TODO: Refactor so this doesn't require an extra query (even though it's cached)
def get_ids_from_url(value: str) -> IntTuple:
    """If a URL is provided containing an ID, return the taxon and/or observation ID.
    If it's an observation, fetch its taxon ID as well.

    Returns:
        taxon_id, observation_id
    """
    taxon_id, observation_id = None, None
    id = strip_url(value)

    if 'observation' in value:
        observation_id = id
        json = get_observation(id)
        taxon_id = json.get('taxon', {}).get('id')
    elif 'taxa' in value:
        taxon_id = id

    return taxon_id, observation_id


def strip_url(value: str) -> Optional[int]:
    """If a URL is provided containing an ID, return just the ID"""
    try:
        path = urlparse(value).path
        return int(path.split('/')[-1].split('-')[0])
    except (TypeError, ValueError):
        return None


def _quote(s: str) -> str:
    """Surround keyword in quotes if it contains whitespace"""
    return f'"{s}"' if ' ' in s else s
