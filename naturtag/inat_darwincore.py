from logging import getLogger
from pyinaturalist.rest_api import get_observations  # TODO: Currently only in dev branch
import xmltodict

from naturtag.constants import DWC_NAMESPACES

logger = getLogger(__name__)


def get_observation_dwc_terms(observation_id):
    """ Get all DWC terms from an iNaturalist observation """
    logger.info(f'Getting darwincore terms for observation {observation_id}')
    obs_dwc = get_observations(id=observation_id, response_format='dwc')
    return convert_dwc_to_xmp(obs_dwc)


def convert_dwc_to_xmp(dwc):
    """
    Get all DWC terms from XML content containing a SimpleDarwinRecordSet, and format them as
    XMP tags. For example: ``'dwc:species' -> 'Xmp.dwc.species'``

    Aside: This is a fun project. If it involved manual XML processsing, it would no longer
    be a fun project. Thanks, xmltodict.
    """
    # Get inner record as a dict, if it exists
    xml_dict = xmltodict.parse(dwc)
    dwr = xml_dict.get("dwr:SimpleDarwinRecordSet", {}).get("dwr:SimpleDarwinRecord")
    if not dwr:
        logger.warn('No SimpleDarwinRecord found')
        return {}

    # iNat sometimes includes duplicate occurence IDs
    if isinstance(dwr["dwc:occurrenceID"], list):
        dwr["dwc:occurrenceID"] = dwr["dwc:occurrenceID"][0]

    # Format as XMP tags
    return {_format_term(k): v for k, v in dwr.items() if _include_term(k)}


def _format_term(k):
    ns, term = k.split(':')
    return f'Xmp.{ns}.{term}'


def _include_term(k):
    ns = k.split(':')[0]
    return ns in DWC_NAMESPACES
