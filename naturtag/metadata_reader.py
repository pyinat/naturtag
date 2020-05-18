from itertools import chain
from logging import getLogger
from os.path import isfile, splitext

from pyexiv2 import Image
from pyinaturalist.constants import RANKS
from naturtag.metadata_writer import KEYWORD_TAGS

# Simplified tags without formatting variations
TAXON_KEYS = ['taxonid', 'dwc:taxonid']
OBSERVATION_KEYS = ['observationid', 'catalognumber', 'dwc:catalognumber']
logger = getLogger(__name__)


def get_tagged_image_metadata(paths):
    all_image_metadata = (MetaMetadata(path) for path in paths)
    return {path: m for path, m in all_image_metadata.items() if m.taxon_id or m.observation_id}


# TODO: Extract GPS info
class MetaMetadata:
    """
    Container for combining, parsing, and organizing image metadata into relevant categories
    """
    def __init__(self, image_path):
        self.image_path = image_path
        self.xmp_path = ''
        self.exif, self.iptc, self.xmp = self.read_metadata()
        self.combined = {**self.exif, **self.iptc, **self.xmp}
        self.keyword_meta = KeywordMetadata(self.combined)
        self.taxon_id, self.observation_id = self.get_inaturalist_ids()

    def read_metadata(self):
        """ Read all formats of metadata from image + sidecar file """
        exif, iptc, xmp = self._safe_read_metadata(self.image_path)
        self.xmp_path = splitext(self.image_path)[0] + '.xmp'
        if isfile(self.xmp_path):
            s_exif, s_iptc, s_xmp = self._safe_read_metadata(self.xmp_path)
            exif.update(s_exif)
            iptc.update(s_iptc)
            xmp.update(s_xmp)
        else:
            self.xmp_path = ''

        paths = self.image_path + (f' + {self.xmp_path}' if self.xmp_path else '')
        counts = ' | '.join([f'EXIF: {len(exif)}', f'IPTC: {len(iptc)}', f'XMP: {len(xmp)}'])
        logger.info(f'Total tags found in {paths}: {counts}')

        return exif, iptc, xmp

    def _safe_read_metadata(self, path, encoding='utf-8'):
        """ Attempt to read metadata, with error handling """
        logger.debug(f'Reading metadata from: {path} ({encoding})')

        # Exiv2 RuntimeError usually means corrupted metadata; see https://dev.exiv2.org/issues/637#note-1
        try:
            img = Image(path)
        except RuntimeError as exc:
            logger.error(f'Failed to read corrupted metadata from {path}')
            logger.exception(exc)
            return {}, {}, {}

        try:
            exif = img.read_exif(encoding=encoding)
            iptc = img.read_iptc(encoding=encoding)
            xmp = img.read_xmp(encoding=encoding)
        except UnicodeDecodeError:
            logger.warning(f'Non-UTF-encoded metadata in {path}')
            return self._safe_read_metadata(path, encoding='unicode_escape')
        finally:
            img.close()

        return exif, iptc, xmp

    def get_inaturalist_ids(self):
        """ Look for taxon and/or observation IDs from combined metadata if available """
        # Reduce variations in similarly-named keys
        def _simplify_key(s):
            return s.lower().replace('_', '').split(':')[-1]

        # Get first non-None value from specified keys, if any; otherwise return None
        def _first_match(metadata, keys):
            return next(filter(None, map(metadata.get, keys)), None)

        # Check all possible keys for valid taxon and observation IDs
        simplified_metadata = {
            _simplify_key(k): v
            for k, v in {**self.combined, **self.keyword_meta.kv_keywords}.items()
        }
        taxon_id = _first_match(simplified_metadata, TAXON_KEYS)
        observation_id = _first_match(simplified_metadata, OBSERVATION_KEYS)
        logger.info(f'Taxon ID: {taxon_id} | Observation ID: {observation_id}')
        return taxon_id, observation_id

    @property
    def summary(self):
        """ Get a condensed summary of available metadata """
        meta_types = {
            'EXIF': bool(self.exif),
            'IPTC': bool(self.iptc),
            'XMP': bool(self.xmp),
            'SIDECAR': bool(self.xmp_path),
        }
        meta_special = {
            'TAX': self.taxon_id,
            'OBS': self.observation_id,
            # 'GPS': self.gps,
        }
        from os.path import basename
        return '\n'.join([
            basename(self.image_path),
            ' | '.join([k for k, v in meta_special.items() if v]),
            ' | '.join([k for k, v in meta_types.items() if v]),
        ])


class KeywordMetadata:
    """
    Container for combining, parsing, and organizing keyword metadata into relevant categories
    """
    def __init__(self, metadata):
        self.keywords = self.get_combined_keywords(metadata)
        self.kv_keywords = self.get_kv_keywords()
        self.hier_keywords = self.get_hierarchical_keywords()
        self.normal_keywords = self.get_normal_keywords()

    def get_combined_keywords(self, metadata):
        """ Get keywords from all metadata formats """
        keywords = [self._get_keyword_list(metadata, tag) for tag in KEYWORD_TAGS]
        keywords = set(chain.from_iterable(keywords))
        logger.info(f'{len(keywords)} unique keywords found')
        return [k.replace('"', '') for k in keywords]

    @staticmethod
    def _get_keyword_list(metadata, tag):
        """ Split comma-separated keywords into a list, if not already a list """
        keywords = metadata.get(tag, [])
        if isinstance(keywords, list):
            return keywords
        elif ',' in keywords:
            return [kw.strip() for kw in ','.split(keywords)]
        else:
            return [keywords.strip()] if keywords.strip() else []

    @staticmethod
    def _sort_taxonomy_keywords(keywords):
        """ Sort keywords by taxonomic rank, where applicable """
        def get_rank_idx(tag):
            base_tag = tag.split(':')[-1].split('=')[0]
            return RANKS.index(base_tag) if base_tag in RANKS else 0

        return sorted(keywords, key=get_rank_idx, reverse=True)

    def get_kv_keywords(self):
        """ Get all keywords that contain key-value pairs"""
        kv_keywords = [kw for kw in self.keywords if kw.count('=') == 1 and kw.split('=')[1]]
        kv_keywords = self._sort_taxonomy_keywords(kv_keywords)
        logger.info(f'{len(kv_keywords)} unique key-value pairs found in keywords')
        return dict([kw.split('=') for kw in kv_keywords])

    def get_hierarchical_keywords(self):
        """ Get all hierarchical keywords as a nested dict """
        hier_keywords = [kw.split('|') for kw in self.keywords if '|' in kw]
        kw_tree = {}
        for kw_ranks in hier_keywords:
            kw_tree = self._append_nodes(kw_tree, kw_ranks)
        logger.info(f'{len(hier_keywords)} hierarchical keywords processed')
        return kw_tree

    @staticmethod
    def _append_nodes(tree, kw_tokens):
        tree_node = tree
        for token in kw_tokens:
            tree_node = tree_node.setdefault(token, {})
        return tree

    def get_normal_keywords(self):
        """ Get all single-value keywords that are neither a key-value pair nor hierarchical """
        return sorted([k for k in self.keywords if '=' not in k and '|' not in k])

    @property
    def hier_keyword_str(self):
        return dict_to_indented_tree(self.hier_keywords)


def dict_to_indented_tree(d):
    """ Convert a dict-formatted tree into a single string, in indented tree format """
    def append_children(d, indent_lvl):
        subtree = ''
        for k, v in d.items():
            subtree += ' ' * indent_lvl + k + '\n'
            subtree += append_children(v, indent_lvl + 1)
        return subtree

    return append_children(d, 0)
