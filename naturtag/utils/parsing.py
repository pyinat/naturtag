"""Misc URL and string parsing utilities"""

from typing import Optional
from urllib.parse import urlparse

from naturtag.constants import IntTuple


def get_ids_from_url(url: str) -> IntTuple:
    """If a URL is provided containing an ID, return the taxon or observation ID.

    Returns:
        ``(observation_id, taxon_id)``
    """
    observation_id, taxon_id = None, None
    id = strip_url(url)

    if 'observation' in url:
        observation_id = id
    elif 'taxa' in url:
        taxon_id = id

    return observation_id, taxon_id


def strip_url(value: str) -> Optional[int]:
    """If a URL is provided containing an ID, return just the ID"""
    try:
        path = urlparse(value).path
        return int(path.split('/')[-1].split('-')[0])
    except (TypeError, ValueError):
        return None


def quote(s: str) -> str:
    """Surround keyword in quotes if it contains whitespace"""
    return f'"{s}"' if ' ' in s else s
