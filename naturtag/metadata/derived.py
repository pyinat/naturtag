from itertools import accumulate
from logging import getLogger
from typing import Any, Optional

from pyinaturalist import INAT_BASE_URL, RANKS, Coordinates, Observation, Taxon
from pyinaturalist_convert import dwc_record_to_observation, to_dwc

from naturtag.constants import (
    COMMON_NAME_IGNORE_TERMS,
    COMMON_RANKS,
    DATE_TAGS,
    HIER_KEYWORD_TAGS,
    KEYWORD_TAGS,
    OBSERVATION_KEYS,
    TAXON_KEYS,
    IntTuple,
    StrTuple,
)
from naturtag.metadata import (
    BaseMetadata,
    KeywordMetadata,
    convert_dwc_coords,
    convert_exif_coords,
    convert_xmp_coords,
    to_exif_coords,
    to_xmp_coords,
)
from naturtag.utils import quote

NULL_COORDS = (0, 0)
DWC_NAMESPACES = ['dcterms', 'dwc']
logger = getLogger().getChild(__name__)


# TODO: If there's no taxon ID but a `rank=name` tag, look up taxon based on that
class DerivedMetadata(BaseMetadata):
    """Parses observation info and other higher-level details derived from raw image metadata

    Example:

        >>> from naturtag import DerivedMetadata
        >>> meta = DerivedMetadata('/path/to/image.jpg')
        >>> print(meta.summary)
        >>> print(meta.to_observation())
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Define lazy-loaded properties
        self._coordinates = None
        self.inaturalist_ids = None
        self._min_rank = None
        self._simplified = None
        self._summary = None
        self._observation: Observation = None
        self._keyword_meta = None
        self._update_derived_properties()

    def _update_derived_properties(self):
        """Reset/ update all secondary properties derived from base metadata formats"""
        self._coordinates = None
        self.inaturalist_ids = None
        self._min_rank = None
        self._simplified = None
        self._summary = None
        self._observation = None
        self._keyword_meta = None
        self.inaturalist_ids = get_inaturalist_ids(self.simplified)

    @property
    def combined(self) -> dict[str, Any]:
        return {**self.exif, **self.iptc, **self.xmp}

    @property
    def keyword_meta(self) -> KeywordMetadata:
        if self._keyword_meta is None:
            self._keyword_meta = KeywordMetadata(self.combined)
        return self._keyword_meta

    @property
    def coordinates(self) -> Optional[Coordinates]:
        """Get coordinates as decimal degrees from EXIF or XMP metadata"""
        if self._coordinates is None:
            self._coordinates = (
                convert_dwc_coords(self.xmp)
                or convert_exif_coords(self.exif)
                or convert_xmp_coords(self.xmp)
                or NULL_COORDS
            )
        return self._coordinates

    @property
    def date(self) -> Optional[str]:
        """Date taken or created, as a string"""
        return _first_match(self.combined, DATE_TAGS)

    @property
    def has_any_tags(self) -> bool:
        return bool(self.exif or self.iptc or self.xmp)

    @property
    def has_coordinates(self) -> bool:
        return self.coordinates not in [None, NULL_COORDS]

    @property
    def has_observation(self) -> bool:
        return bool(self.observation_id)

    @property
    def has_taxon(self) -> bool:
        return bool(self.taxon_id)

    @property
    def observation_id(self) -> Optional[int]:
        return self.inaturalist_ids[1]

    @property
    def observation_url(self) -> str:
        return f'{INAT_BASE_URL}/observations/{self.observation_id or ""}'

    @property
    def taxon_id(self) -> Optional[int]:
        return self.inaturalist_ids[0]

    @property
    def taxon_url(self) -> str:
        return f'{INAT_BASE_URL}/taxa/{self.taxon_id or ""}'

    @property
    def min_rank(self) -> Optional[StrTuple]:
        """Get the lowest (most specific) taxonomic rank and name from tags, if any

        Returns:
            ``(rank, name)``
        """
        if self._min_rank is None:
            for rank in RANKS:
                if name := self.simplified.get(rank):
                    self._min_rank = (rank, name)
                    break
            else:
                self._min_rank = ()
        return self._min_rank or None

    @property
    def simplified(self) -> dict[str, str]:
        """
        Get simplified/deduplicated key-value pairs from a combination of keywords + basic metadata
        """
        if self._simplified is None:
            self._simplified = simplify_keys({**self.combined, **self.keyword_meta.kv_keywords})
            for k in KEYWORD_TAGS + HIER_KEYWORD_TAGS:
                self._simplified.pop(k, None)
        return self._simplified

    @property
    def summary(self) -> str:
        """Get a condensed summary of available metadata"""
        if self._summary is None:
            obs = self.to_observation()
            meta_types = {
                'EXIF': bool(self.exif),
                'IPTC': bool(self.iptc),
                'XMP': bool(self.xmp),
                'Sidecar': self.has_sidecar,
            }
            summary_info = {
                'Path': self.image_path,
                'Date': self.date,
                'Taxon': obs.taxon.full_name if obs.taxon else 'unknown taxon',
                'Location': f'{obs.place_guess} {obs.location}',
                'Metadata types': ', '.join([k for k, v in meta_types.items() if v]),
            }
            self._summary = '\n'.join([f'{k}: {v}' for k, v in summary_info.items()])
        return self._summary

    def merge(self, other: 'DerivedMetadata') -> 'DerivedMetadata':
        """Update metadata from another instance"""
        self.exif.update(other.exif)
        self.xmp.update(other.xmp)
        self.iptc.update(other.iptc)
        self._update_derived_properties()
        return self

    def update(self, new_metadata: dict):
        """Update arbitrary EXIF, IPTC, and/or XMP metadata, and reset/update derived properties"""
        if not new_metadata:
            return
        super().update(new_metadata)
        self._update_derived_properties()

    def update_coordinates(self, coordinates: Coordinates, accuracy: Optional[int] = None):
        if not coordinates:
            self._coordinates = NULL_COORDS
            return

        self.exif.update(to_exif_coords(coordinates, accuracy))
        self.xmp.update(to_xmp_coords(coordinates, accuracy))
        self._update_derived_properties()
        self._coordinates = coordinates

    def update_keywords(self, keywords):
        """
        Update only keyword metadata.
        Keywords will be written to appropriate tags for each metadata format.
        """
        keyword_meta = KeywordMetadata(keywords=keywords)
        self.update(keyword_meta.tags)
        self._keyword_meta = keyword_meta

    def from_observation(
        self,
        observation: Observation,
        common_names: bool = False,
        hierarchical: bool = False,
    ) -> 'DerivedMetadata':
        """Update metadata from an iNaturalist Observation"""
        # Get all specified keyword categories
        keywords = _get_taxonomy_keywords(observation.taxon)
        if hierarchical:
            keywords.extend(_get_taxon_hierarchical_keywords(observation.taxon))
        if common_names:
            common_keywords = _get_common_keywords(observation.taxon)
            keywords.extend(common_keywords)
            if hierarchical:
                keywords.extend(_get_hierarchical_keywords(common_keywords))
        keywords.extend(_get_id_keywords(observation.id, observation.taxon.id))

        logger.debug(f'{len(keywords)} total keywords generated')
        self.update_keywords(keywords)

        # Convert and add coordinates
        # TODO: Add other metadata like title, description, tags, etc.
        self.update_coordinates(observation.location, observation.positional_accuracy)

        def _format_key(k):
            """Get DwC terms as XMP tags.
            Note: exiv2 will automatically add recognized XML namespace URLs when adding properties
            """
            namespace, term = k.split(':')
            return f'Xmp.{namespace}.{term}' if namespace in DWC_NAMESPACES else None

        # Convert and add DwC metadata
        tag_observations = [observation] if observation.id else None
        dwc = to_dwc(observations=tag_observations, taxa=[observation.taxon])[0]
        dwc_xmp = {fk: v for k, v in dwc.items() if (fk := _format_key(k))}
        self.update(dwc_xmp)

        return self

    def to_observation(self) -> Observation:
        """Convert DwC metadata to an observation object, if possible"""
        if not self._observation:
            # Format Xmp.dwc.* and related tags as DwC terms
            dwc = {k.replace('Xmp.', '').replace('.', ':'): v for k, v in self.xmp.items()}
            self._observation = dwc_record_to_observation(dwc)
        return self._observation

    def __str__(self) -> str:
        return self.summary


def get_inaturalist_ids(metadata: dict) -> IntTuple:
    """Look for taxon and/or observation IDs from metadata if available"""
    # Check all possible keys for valid taxon and observation IDs
    taxon_id = _first_match_int(metadata, TAXON_KEYS)
    observation_id = _first_match_int(metadata, OBSERVATION_KEYS)
    logger.debug(f'Taxon ID: {taxon_id} | Observation ID: {observation_id}')
    return taxon_id, observation_id


def simplify_keys(mapping: dict[str, str]) -> dict[str, str]:
    """
    Simplify/deduplicate dict keys, to reduce variations in similarly-named keys

    Example::
        >>> simplify_keys({'my_namespace:Sub_Family': 'Panorpinae'})
        {'subfamily': 'Panorpinae'}

    Returns:
        dict with simplified/deduplicated keys
    """
    return {k.lower().replace('_', '').split(':')[-1]: v for k, v in mapping.items()}


def _get_taxonomy_keywords(taxon: Taxon) -> list[str]:
    """Format a list of taxa into rank keywords"""
    return [quote(f'taxonomy:{t.rank}={t.name}') for t in taxon.ancestors + [taxon]]


def _get_id_keywords(
    observation_id: Optional[int] = None, taxon_id: Optional[int] = None
) -> list[str]:
    keywords = []
    if taxon_id:
        keywords.append(f'inat:taxon_id={taxon_id}')
        keywords.append(f'dwc:taxonID={taxon_id}')
    if observation_id:
        keywords.append(f'inat:observation_id={observation_id}')
        keywords.append(f'dwc:catalogNumber={observation_id}')
    return keywords


def _get_common_keywords(taxon: Taxon) -> list[str]:
    """Format a list of taxa into common name keywords.
    Filters out terms that aren't useful to keep as tags.
    """
    keywords = [
        t.preferred_common_name for t in taxon.ancestors + [taxon] if t.rank in COMMON_RANKS
    ]

    def is_ignored(kw):
        return any(ignore_term in kw.lower() for ignore_term in COMMON_NAME_IGNORE_TERMS)

    return [quote(kw) for kw in keywords if kw and not is_ignored(kw)]


def _get_taxon_hierarchical_keywords(taxon: Taxon) -> list[str]:
    """Get hierarchical keywords for a taxon"""
    keywords = [t.name for t in taxon.ancestors + [taxon] if t.rank in COMMON_RANKS]
    return _get_hierarchical_keywords(keywords)


def _get_hierarchical_keywords(keywords: list[str]) -> list[str]:
    """Translate a sorted list of flat keywords into pipe-delimited hierarchical keywords"""
    return list(accumulate(keywords, lambda a, b: f'{a}|{b}'))


def _first_match(d: dict, tags: list[str]) -> Optional[str]:
    """Get first non-None value from specified keys, if any; otherwise return None"""
    return next(filter(None, map(d.get, tags)), None)


def _first_match_int(d: dict, tags: list[str]) -> Optional[int]:
    match = _first_match(d, tags)
    return int(match) if match else None
