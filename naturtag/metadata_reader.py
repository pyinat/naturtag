# TODO: Is this module better organized as static functions or as a class?
from collections import namedtuple
from itertools import chain
from logging import getLogger
from os.path import isfile, splitext

from pyexiv2 import Image
from pyinaturalist.constants import RANKS
from naturtag.metadata_writer import KEYWORD_TAGS

# Simplified tags without formatting variations
TAXON_KEYS = ['taxonid', 'dwc:taxonid']
OBSERVATION_KEYS = ['observationid', 'catalognumber', 'dwc:catalognumber']

MetaMetaData = namedtuple(
    'MetaMetaData',
    ['exif', 'iptc', 'xmp', 'combined', 'keywords', 'hier_keywords', 'taxon_id', 'observation_id', 'has_gps'])
logger = getLogger(__name__)


def get_tagged_image_metadata(paths):
    all_image_metadata = get_all_image_metadata(paths)
    return {path: m for path, m in all_image_metadata.items() if m.taxon_id or m.observation_id}


def get_all_image_metadata(paths):
    return [get_image_metadata(path) for path in paths]


def get_image_metadata(path):
    """
    Get aggregate info about image metadata.
    Look for taxon and/or observation IDs from the specified image + sidecar, if any.
    """
    # Reduce variations in similarly-named keys
    def _simplify_key(s):
        return s.lower().replace('_', '').split(':')[-1]

    # Get first non-None value from specified keys, if any; otherwise return None
    def _first_match(metadata, keys):
        return next(filter(None, map(metadata.get, keys)), None)

    metadata = read_combined_metadata(path)
    keywords = get_combined_keywords(metadata)

    # Extract any key-value pairs from keywords and combine with other metadata
    kv_keywords = get_kv_keywords(keywords)
    hier_keywords = get_hierarchical_keywords(keywords)
    simplified_metadata = {_simplify_key(k): v for k, v in {**metadata, **kv_keywords}.items()}

    # Check all possible keys for valid taxon and observation IDs
    taxon_id = _first_match(simplified_metadata, TAXON_KEYS)
    observation_id = _first_match(simplified_metadata, OBSERVATION_KEYS)
    return MetaMetaData(None, None, None, metadata, keywords, hier_keywords, taxon_id, observation_id, False)


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


def get_combined_keywords(metadata):
    """ Get keywords from all metadata formats """
    keywords = [_get_keyword_list(metadata.get(tag, [])) for tag in KEYWORD_TAGS]
    keywords = set(chain.from_iterable(keywords))
    logger.debug(f'{len(keywords)} unique keywords found')
    return _sort_taxonomy_keywords(keywords)


def _get_keyword_list(keywords):
    """ Split comma-separated keywords into a list, if not already a list """
    if isinstance(keywords, list):
        return keywords
    elif ',' in keywords:
        return [kw.strip() for kw in ','.split(keywords)]
    else:
        return [keywords.strip()] if keywords.strip() else []


def _sort_taxonomy_keywords(keywords):
    """
    Sort keywords by taxonomic rank, where applicable; non-taxonomic tags will be sorted by name
    """
    def get_rank_idx(tag):
        base_tag = tag.split(':')[-1].split('=')[0]
        return RANKS.index(base_tag) if base_tag in RANKS else 0

    return sorted(keywords, key=get_rank_idx, reverse=True)


def get_kv_keywords(keywords):
    """ Get all keywords that contain key-value pairs"""
    keyword_pairs = [
        kw.replace('"', '').split('=') for kw in keywords
        if kw.count('=') == 1 and kw.split('=')[1]
    ]
    logger.debug(f'{len(keyword_pairs)} unique key-value pairs found in keywords')
    return dict(keyword_pairs)


def get_hierarchical_keywords(keywords):
    hier_keywords = [kw.split('|') for kw in keywords if '|' in kw]
    kw_tree = {}
    for kw_ranks in hier_keywords:
        kw_tree = _append_nodes(kw_tree, kw_ranks)
    return kw_tree


def _append_nodes(tree, kw_tokens):
    tree_node = tree
    for token in kw_tokens:
        tree_node = tree_node.setdefault(token, {})
    return tree
