from logging import getLogger
from os.path import basename
from typing import Any, Optional

from pyinaturalist import INAT_BASE_URL, RANKS, Coordinates, Observation
from pyinaturalist_convert import dwc_record_to_observation

from naturtag.constants import OBSERVATION_KEYS, TAXON_KEYS, IntTuple, StrTuple
from naturtag.metadata import (
    HIER_KEYWORD_TAGS,
    KEYWORD_TAGS,
    ImageMetadata,
    KeywordMetadata,
    convert_dwc_coords,
    convert_exif_coords,
    convert_xmp_coords,
    to_exif_coords,
    to_xmp_coords,
)

NULL_COORDS = (0, 0)
logger = getLogger().getChild(__name__)


# TODO: If there's no taxon ID but a `rank=name` tag, look up taxon based on that
class MetaMetadata(ImageMetadata):
    """Class for parsing & organizing higher-level info derived from raw image metadata"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Define lazy-loaded properties
        self._coordinates = None
        self._inaturalist_ids = None
        self._min_rank = None
        self._simplified = None
        self._summary = None
        self.keyword_meta = None
        self._update_derived_properties()

    def _update_derived_properties(self):
        """Reset/ update all secondary properties derived from base metadata formats"""
        self._coordinates = None
        self._inaturalist_ids = None
        self._min_rank = None
        self._simplified = None
        self._summary = None
        self.keyword_meta = KeywordMetadata(self.combined)

    @property
    def combined(self) -> dict[str, Any]:
        return {**self.exif, **self.iptc, **self.xmp}

    @property
    def filtered_combined(self) -> dict[str, Any]:
        return {**self.filtered_exif, **self.iptc, **self.xmp}

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
    def has_any_tags(self) -> bool:
        return bool(self.exif or self.iptc or self.xmp)

    @property
    def has_coordinates(self) -> bool:
        return bool(self.coordinates) and self.coordinates != NULL_COORDS

    @property
    def has_observation(self) -> bool:
        return bool(self.observation_id)

    @property
    def has_taxon(self) -> bool:
        return bool(self.taxon_id)

    @property
    def inaturalist_ids(self) -> IntTuple:
        """Get taxon and/or observation IDs from metadata if available"""
        if self._inaturalist_ids is None:
            self._inaturalist_ids = get_inaturalist_ids(self.simplified)
        return self._inaturalist_ids

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
            meta_types = {
                'TAX': self.has_taxon,
                'OBS': self.has_observation,
                'GPS': self.has_coordinates,
                'EXIF': bool(self.exif),
                'IPTC': bool(self.iptc),
                'XMP': bool(self.xmp),
                'SIDECAR': self.has_sidecar,
            }
            self._summary = f'{basename(self.image_path)}\n' if self.image_path else ''
            self._summary += ' | '.join([k for k, v in meta_types.items() if v])
            logger.debug(f'Metadata summary: {self._summary}')
        return self._summary

    def merge(self, other: 'MetaMetadata') -> 'MetaMetadata':
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

    def update_coordinates(self, coordinates: Coordinates):
        if not coordinates:
            return
        self._coordinates = coordinates
        self.exif.update(to_exif_coords(coordinates))
        self.xmp.update(to_xmp_coords(coordinates))

    def update_keywords(self, keywords):
        """
        Update only keyword metadata.
        Keywords will be written to appropriate tags for each metadata format.
        """
        self.update(KeywordMetadata(keywords=keywords).tags)

    def to_observation(self) -> Observation:
        """Convert DwC metadata to an observation object, if possible"""
        # Format Xmp.dwc.* and related tags as DwC terms
        dwc = {k.replace('Xmp.', '').replace('.', ':'): v for k, v in self.xmp.items()}
        return dwc_record_to_observation(dwc)

    def __str__(self) -> str:
        return self.summary


def get_inaturalist_ids(metadata: dict) -> IntTuple:
    """Look for taxon and/or observation IDs from metadata if available"""
    # Get first non-None value from specified keys, if any; otherwise return None
    def _first_match(d, keys):
        id = next(filter(None, map(d.get, keys)), None)
        return int(id) if id else None

    # Check all possible keys for valid taxon and observation IDs
    taxon_id = _first_match(metadata, TAXON_KEYS)
    observation_id = _first_match(metadata, OBSERVATION_KEYS)
    logger.debug(f'Taxon ID: {taxon_id} | Observation ID: {observation_id}')
    return taxon_id, observation_id


def simplify_keys(mapping: dict[str, str]) -> dict[str, str]:
    """
    Simplify/deduplicate dict keys, to reduce variations in similarly-named keys

    Example::
        >>> simplify_keys({'my_namepace:Super_Order': 'Panorpida'})
        {'superfamily': 'Panorpida'}

    Returns:
        dict with simplified/deduplicated keys
    """
    return {k.lower().replace('_', '').split(':')[-1]: v for k, v in mapping.items()}
