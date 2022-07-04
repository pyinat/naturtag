from itertools import chain
from logging import getLogger
from typing import Any

from naturtag.constants import HIER_KEYWORD_TAGS, KEYWORD_TAGS, RANKS

# All tags that support regular and hierarchical keyword lists

logger = getLogger().getChild(__name__)


class KeywordMetadata:
    """
    Container for combining, parsing, and organizing keyword metadata into relevant categories
    """

    def __init__(self, metadata: dict[str, Any] = None, keywords: list[str] = None):
        """Initialize with full metadata or keywords only"""
        self.keywords = keywords or self._get_combined_keywords(metadata)
        self.kv_keywords = self._get_kv_keywords()
        self.hier_keywords = self._get_hierarchical_keywords()
        self.normal_keywords = self._get_normal_keywords()

    def _get_combined_keywords(self, metadata: dict[str, Any] = None) -> list[str]:
        """Get keywords from all metadata formats"""
        if not metadata:
            return []

        # Split comma-separated keywords into a list, if not already a list
        def get_keyword_list(tag):
            keywords = metadata.get(tag, [])
            if isinstance(keywords, list):
                return keywords
            elif ',' in keywords:
                return [kw.strip() for kw in ','.split(keywords)]
            else:
                return [keywords.strip()] if keywords.strip() else []

        # Combine and re-sort all keywords, to account for invalid tags created by other apps
        keywords = [get_keyword_list(tag) for tag in KEYWORD_TAGS + HIER_KEYWORD_TAGS]
        unique_keywords = [
            k.replace('"', '') for k in set(chain.from_iterable(keywords)) if k != ','
        ]

        logger.debug(f'{len(unique_keywords)} unique keywords found')
        return unique_keywords

    def _get_kv_keywords(self) -> dict[str, str]:
        """Get all keywords that contain key-value pairs"""
        kv_keywords = [kw for kw in self.keywords if kw.count('=') == 1 and kw.split('=')[1]]
        kv_keywords = sort_taxonomy_keywords(kv_keywords)
        logger.debug(f'{len(kv_keywords)} unique key-value pairs found in keywords')
        return dict([kw.split('=') for kw in kv_keywords])

    def _get_hierarchical_keywords(self) -> list[str]:
        """Get all hierarchical keywords as flat strings.
        Also account for root node (single value without '|')
        """
        hier_keywords = [kw for kw in self.keywords if '|' in kw]
        if len(hier_keywords) > 1:
            root = hier_keywords[0].split('|')[0]
            hier_keywords.insert(0, root)
        return hier_keywords

    def _get_normal_keywords(self) -> list[str]:
        """Get all single-value keywords that are neither a key-value pair nor hierarchical"""
        return sorted({k for k in self.keywords if '=' not in k and '|' not in k})

    @property
    def flickr_tags(self):
        """Get all taxonomy and normal keywords as quoted, space-separated tags compatible with
        Flickr"""
        tags = [_quote(kw) for kw in self.kv_keyword_list + self.normal_keywords]
        return ' '.join(tags)

    @property
    def hier_keyword_tree(self) -> dict[str, Any]:
        """Get all hierarchical keywords as a nested dict"""
        kw_tree: dict[str, Any] = {}

        def append_nodes(tree, kw_tokens):
            tree_node = tree
            for token in kw_tokens:
                tree_node = tree_node.setdefault(token, {})
            return tree

        for kw_ranks in [kw.split('|') for kw in self.hier_keywords]:
            kw_tree = append_nodes(kw_tree, kw_ranks)
        return kw_tree

    @property
    def hier_keyword_tree_str(self) -> str:
        """Get all hierarchical keywords as a single string, in indented tree format"""

        def append_children(d, indent_lvl):
            subtree = ''
            for k, v in d.items():
                subtree += ' ' * indent_lvl + k + '\n'
                subtree += append_children(v, indent_lvl + 1)
            return subtree

        return append_children(self.hier_keyword_tree, 0)

    @property
    def kv_keyword_list(self) -> list[str]:
        """Join key-value pairs back into strings"""
        return [f'{k}={v}' for k, v in self.kv_keywords.items()]

    @property
    def tags(self) -> dict[str, Any]:
        """
        Add all keywords to all appropriate XMP, EXIF, and IPTC tags

        Returns:
            dict: Mapping from qualified tag name to tag value(s)
        """
        flat_keywords = self.normal_keywords + self.kv_keyword_list
        metadata = {tag: flat_keywords for tag in KEYWORD_TAGS}
        metadata.update({tag: self.hier_keywords for tag in HIER_KEYWORD_TAGS})
        return metadata


def sort_taxonomy_keywords(keywords: list[str]) -> list[str]:
    """Sort keywords by taxonomic rank, where applicable"""

    def get_rank_idx(tag: str) -> int:
        rank = tag.split(':')[-1].split('=')[0]
        return RANKS.index(rank) if rank in RANKS else 0

    return sorted(keywords, key=get_rank_idx, reverse=True)


def _quote(s: str) -> str:
    """Surround keyword in quotes if it contains whitespace"""
    return f'"{s}"' if ' ' in s else s
