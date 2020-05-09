# TODO: hacked this together quickly; needs lots of cleanup
from logging import getLogger
from pyinaturalist.rest_api import get_observations  # TODO: Currently only in dev branch
import xmltodict

from taxgen.constants import DWC_NAMESPACES

logger = getLogger(__name__)


def get_observation_dwc_terms(observation_id):
    """ Get all DWC terms from an iNaturalist observation """
    logger.info(f'Getting darwincore terms for observation {observation_id}')
    obs_dwc = get_observations(id=strip_url(observation_id), response_format='dwc')
    return get_dwc_terms(obs_dwc)


def get_dwc_terms(dwc):
    """ Get all DWC terms as XMP metadata from XML content containing a SimpleDarwinRecordSet """
    # Get inner SimpleDarwinRecord as a dict
    xml_dict = xmltodict.parse(dwc)
    dwr = xml_dict["dwr:SimpleDarwinRecordSet"]["dwr:SimpleDarwinRecord"]
    if isinstance(dwr["dwc:occurrenceID"], list):
        dwr["dwc:occurrenceID"] = dwr["dwc:occurrenceID"][0]

    # Format DWC properties as XMP properties (e.g.: 'dwc:species' -> 'Xmp.dwc.species')
    dwc_xmp = {}
    for k, v in dwr.items():
        ns, term = k.split(':')
        if ns in DWC_NAMESPACES:
            dwc_xmp[f'Xmp.{ns}.{term}'] = v

    return dwc_xmp


def strip_url(s):
    """ If a URL is provided containing an ID, return just the ID """
    return s.split('/')[-1].split('-')[0] if s else None
