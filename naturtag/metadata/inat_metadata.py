"""Tools to get keyword tags from iNaturalist observations"""
# TODO: Get separate keywords for species, binomial, and trinomial
# TODO: Get common names for specified locale (requires using different endpoints)
# TODO: Handle observation with no taxon ID?
# TODO: Include eol:dataObject info (metadata for an individual observation photo)
# TODO: Refactor usage of get_ids_from_url() it doesn't require an extra query
from logging import getLogger
from typing import Optional
from urllib.parse import urlparse

from pyinaturalist import Observation, Taxon, iNatClient
from pyinaturalist_convert import to_dwc

from naturtag.constants import COMMON_NAME_IGNORE_TERMS, DWC_NAMESPACES, IntTuple
from naturtag.metadata import MetaMetadata

inat_client = iNatClient()
logger = getLogger().getChild(__name__)


def tag_images(
    observation_id: int,
    taxon_id: int,
    common_names: bool = False,
    darwin_core: bool = False,
    hierarchical: bool = False,
    create_sidecar: bool = False,
    images: list[str] = None,
) -> list[MetaMetadata]:
    """
    Get taxonomy tags from an iNaturalist observation or taxon, and write them to local image
    metadata. See :py:func:`~naturtag.cli.tag` for details.
    """
    inat_metadata = get_inat_metadata(
        observation_id=observation_id,
        taxon_id=taxon_id,
        common_names=common_names,
        darwin_core=darwin_core,
        hierarchical=hierarchical,
    )

    if not images:
        return [inat_metadata]
    return [tag_image(image_path, inat_metadata, create_sidecar) for image_path in images]


def tag_image(
    image_path: str, inat_metadata: MetaMetadata, create_sidecar: bool = False
) -> MetaMetadata:
    img_metadata = MetaMetadata(image_path).merge(inat_metadata)
    img_metadata.write(create_sidecar=create_sidecar)
    return img_metadata


def get_inat_metadata(
    observation_id: int,
    taxon_id: int,
    common_names: bool = False,
    darwin_core: bool = False,
    hierarchical: bool = False,
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
    keywords.extend(get_id_keywords(observation_id, taxon_id))

    logger.info(f'{len(keywords)} total keywords generated')
    inat_metadata.update_keywords(keywords)

    # Convert and add coordinates
    if observation:
        inat_metadata.update_coordinates(observation.location)

    # Convert and add DwC metadata, if specified
    if darwin_core:
        inat_metadata.update(get_dwc_terms(observation, taxon))

    return inat_metadata


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

    if metadata.has_observation:
        observation = inat_client.observations.from_id(metadata.observation_id).one()
        taxon = observation.taxon
    elif metadata.has_taxon:
        taxon = inat_client.taxa.from_id(metadata.taxon_id)

    return taxon, observation


def get_taxonomy_keywords(taxon: Taxon) -> list[str]:
    """Format a list of taxa into rank keywords"""
    return [_quote(f'taxonomy:{t.rank}={t.name}') for t in [taxon, *taxon.ancestors]]


def get_id_keywords(observation_id: int, taxon_id: int) -> list[str]:
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


def get_dwc_terms(observation: Observation = None, taxon: Taxon = None) -> dict[str, str]:
    """Convert either an observation or taxon into XMP-formatted Darwin Core terms"""

    def format_key(k):
        namespace, term = k.split(':')
        return f'Xmp.{namespace}.{term}' if namespace in DWC_NAMESPACES else None

    # Convert to DwC, then to XMP tags
    dwc = to_dwc(observations=observation, taxa=taxon)[0]
    return {format_key(k): v for k, v in dwc.items() if format_key(k)}


def get_ids_from_url(value: str) -> IntTuple:
    """If a URL is provided containing an ID, return the taxon and/or observation ID.
    If it's an observation, fetch its taxon ID as well.

    Returns:
        taxon_id, observation_id
    """
    observation_id, taxon_id = None, None
    id = strip_url(value)

    if 'observation' in value:
        obs = inat_client.observations.from_id(id).one()
        observation_id, taxon_id = id, obs.taxon.id
    elif 'taxa' in value:
        taxon_id = id

    return observation_id, taxon_id


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
