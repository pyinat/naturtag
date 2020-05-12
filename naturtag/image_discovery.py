from itertools import chain
from logging import getLogger
from os.path import isfile, splitext

from pyexiv2 import Image
from naturtag.image_metadata import KEYWORD_TAGS

TAXON_KEYS = ['taxonid', 'dwc:taxonid']
OBSERVATION_KEYS = ['observationid', 'catalognumber', 'dwc:catalognumber']

logger = getLogger(__name__)


def find_tagged_images(paths):
    image_ids = {path: get_taxon_obs_ids(path) for path in paths}
    return {path: ids for path, ids in image_ids.items() if any(ids)}


def get_taxon_obs_ids(path):
    """ Look for taxon and/or observation IDs from the specified image + sidecar, if any """

    # Reduce variations in similarly-named keys
    def _simplify_key(s):
        return s.lower().replace('_', '').split(':')[-1]

    # Get first non-None value from specified keys, if any; otherwise return None
    def _first_match(metadata, keys):
        return next(filter(None, map(metadata.get, keys)), None)

    # Extract and key-value pairs from keywords and combine with other metadata
    metadata = read_combined_metadata(path)
    kw_metadata = get_combined_keyword_attrs(metadata)
    metadata.update({_simplify_key(k): v for k, v in kw_metadata.items()})

    # Check all possible keys for valid taxon and observation IDs
    return _first_match(metadata, TAXON_KEYS), _first_match(metadata, OBSERVATION_KEYS)


def read_combined_metadata(path):
    """
    Get a single dict containing all EXIF, IPTC, and XMP metadata, including sidecar if present
    """
    metadata = {}
    img = Image(path)
    metadata.update(img.read_exif())
    metadata.update(img.read_iptc())
    metadata.update(img.read_xmp())

    xmp_path = splitext(path)[0] + '.xmp'
    if isfile(xmp_path):
        sidecar = Image(xmp_path)
        metadata.update(sidecar.read_xmp())
        metadata.update(sidecar.read_iptc())

    logger.debug(
        f'{len(metadata)} total tags found in {path}'
        f' + {xmp_path}' if xmp_path else ''
    )
    return metadata


def get_combined_keyword_attrs(metadata):
    """ Get all keywords that contain key-value pairs"""
    keywords = [_get_keyword_list(metadata.get(tag, [])) for tag in KEYWORD_TAGS]
    keywords = set(chain.from_iterable(keywords))
    logger.debug(f'{len(keywords)} unique keywords found')
    keyword_pairs = [
        kw.split('=') for kw in keywords
        if kw.count('=') == 1 and kw.split('=')[1]
    ]
    logger.debug(f'{len(keyword_pairs)} unique key-value pairs found in keywords')
    return dict(keyword_pairs)


def _get_keyword_list(keywords):
    """ Split comma-separated keywords into a list, if not already a list """
    if isinstance(keywords, list):
        return keywords
    elif ',' in keywords:
        return [kw.strip() for kw in ','.split(keywords)]
    else:
        return [keywords.strip()] if keywords.strip() else []
