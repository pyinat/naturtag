"""Utilities for converting GPS coordinates to/from EXIF and XMP image metadata"""
import re
from typing import Optional

from pyinaturalist.constants import Coordinates


def convert_exif_coords(metadata: dict) -> Optional[Coordinates]:
    """Translate Exif.GPSInfo into decimal degrees, if available"""
    try:
        return (
            _get_exif_coord(
                metadata['Exif.GPSInfo.GPSLatitude'],
                metadata.get('Exif.GPSInfo.GPSLatitudeRef', 'N'),
            ),
            _get_exif_coord(
                metadata['Exif.GPSInfo.GPSLongitude'],
                metadata.get('Exif.GPSInfo.GPSLongitudeRef', 'W'),
            ),
        )
    except (IndexError, KeyError, ValueError):
        return None


def convert_xmp_coords(metadata: dict) -> Optional[Coordinates]:
    """Translate Xmp.exif.GPS into decimal degrees, if available"""
    try:
        return (
            _get_xmp_coord(metadata['Xmp.exif.GPSLatitude']),
            _get_xmp_coord(metadata['Xmp.exif.GPSLongitude']),
        )
    except (IndexError, KeyError, ValueError):
        return None


def convert_dwc_coords(metadata: dict) -> Optional[Coordinates]:
    """Get coordinates from XMP-formatted DwC, if available"""
    try:
        return (
            float(metadata['Xmp.dwc.decimalLatitude']),
            float(metadata['Xmp.dwc.decimalLongitude']),
        )
    except (KeyError, ValueError):
        return None


def to_exif_coords(coords: Coordinates) -> dict[str, str]:
    """Convert decimal degrees to Exif.GPSInfo coordinates (DMS)"""
    metadata = {}

    degrees, minutes, seconds = _decimal_to_dms(coords[0])
    seconds = int(seconds * 10000)
    metadata['Exif.GPSInfo.GPSLatitudeRef'] = 'S' if coords[0] < 0 else 'N'
    metadata['Exif.GPSInfo.GPSLatitude'] = f'{degrees}/1 {minutes}/1 {seconds}/10000'

    degrees, minutes, seconds = _decimal_to_dms(coords[1])
    seconds = int(seconds * 10000)
    metadata['Exif.GPSInfo.GPSLongitudeRef'] = 'E' if coords[1] < 0 else 'W'
    metadata['Exif.GPSInfo.GPSLongitude'] = f'{degrees}/1 {minutes}/1 {seconds}/10000'

    return metadata


def to_xmp_coords(coords: Coordinates) -> dict[str, str]:
    """Convert decimal degrees to XMP-formatted GPS coordinates (DDM)"""
    metadata = {}

    degrees, minutes = _decimal_to_ddm(coords[0])
    direction = 'S' if coords[0] < 0 else 'N'
    metadata['Xmp.exif.GPSLatitude'] = f'{degrees},{minutes}{direction}'

    degrees, minutes = _decimal_to_ddm(coords[1])
    direction = 'W' if coords[1] < 0 else 'W'
    metadata['Xmp.exif.GPSLongitude'] = f'{degrees},{minutes}{direction}'

    return metadata


def _decimal_to_ddm(dd: float) -> tuple[int, float]:
    """Convert decimal degrees to degrees, decimal minutes"""
    degrees, minutes = divmod(abs(dd) * 60, 60)
    return int(degrees), minutes


def _decimal_to_dms(dd: float) -> tuple[int, int, float]:
    """Convert decimal degrees to degrees, minutes, seconds"""
    degrees, minutes = divmod(abs(dd) * 60, 60)
    minutes, seconds = divmod(minutes * 60, 60)
    return int(degrees), int(minutes), seconds


def _dms_to_decimal(degrees: float, minutes: float, seconds: float, direction: str) -> float:
    dd = degrees + (minutes / 60) + (seconds / 3600)
    return dd * (-1 if direction in ['S', 'E'] else 1)


def _ddm_to_decimal(degrees: float, minutes: float, direction: str) -> float:
    dd = degrees + (minutes / 60)
    return dd * (-1 if direction in ['S', 'E'] else 1)


def _get_exif_coord(value: str, direction: str) -> Optional[float]:
    """Translate a value from Exif.GPSInfo into decimal degrees.
    Example: '41/1 32/1 251889/10000'
    """
    tokens = [int(n) for n in re.split(r'[/\s]', value)]
    dms = (tokens[0] / tokens[1], tokens[2] / tokens[3], tokens[4] / tokens[5])
    return _dms_to_decimal(*dms, direction)


def _get_xmp_coord(value: str) -> Optional[float]:
    """Translate a value from XMP-formatted EXIF GPSInfo into decimal degrees.
    Example: '41,37.10N'
    """
    match = re.match(r'(\d+),([\d\.]+)(\w)', value)
    if not match:
        return None

    groups = match.groups()
    return _ddm_to_decimal(int(groups[0]), float(groups[1]), groups[2])
