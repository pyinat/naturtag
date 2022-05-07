# flake8: noqa: F401
from datetime import timedelta
from pathlib import Path
from typing import IO, Iterable, Optional, Union

from platformdirs import user_data_dir
from pyinaturalist.constants import ICONIC_TAXA, Coordinates

from naturtag import __version__

# Resource directories
PKG_DIR = Path(__file__).parent.parent
ASSETS_DIR = PKG_DIR / 'assets'
DATA_DIR = Path(user_data_dir()) / 'Naturtag'

# Autocomplete settings
TRIGGER_DELAY = 0.1
AUTOCOMPLETE_DELAY = 0.5
AUTOCOMPLETE_MIN_CHARS = 3

# Thumnbnail settings
IMAGE_FILETYPES = ['*.jpg', '*.jpeg', '*.png', '*.gif', '*.webp']
PHOTO_SIZES = ['square', 'small', 'medium', 'large', 'original']
THUMBNAILS_DIR = DATA_DIR / 'thumbnails'
THUMBNAIL_DEFAULT_FORMAT = 'png'
THUMBNAIL_SIZE_SM = (75, 75)
THUMBNAIL_SIZE_DEFAULT = (200, 200)
THUMBNAIL_SIZE_LG = (500, 500)
THUMBNAIL_SIZES = {
    'small': THUMBNAIL_SIZE_SM,
    'medium': THUMBNAIL_SIZE_DEFAULT,
    'large': THUMBNAIL_SIZE_LG,
}

# Image metadata settings
EXIF_HIDE_PREFIXES = [
    'Exif.Image.PrintImageMatching',
    'Exif.MakerNote',
    'Exif.Olympus2.CameraID',
    'Exif.OlympusCs.0x',
    'Exif.OlympusCs.AFAreas',
    'Exif.OlympusFi.0x',
    'Exif.OlympusFi.ImageStabilization',
    'Exif.OlympusFi.SceneDetectData',
    'Exif.OlympusIp.0x',
    'Exif.OlympusIp.FaceDetectArea',
    'Exif.Photo.MakerNote',
]
EXIF_ORIENTATION_ID = '0x0112'

ICONIC_TAXA_DIR = ASSETS_DIR / 'iconic_taxa'
APP_LOGO = str(ASSETS_DIR / 'logo.png')
SELECTABLE_ICONIC_TAXA = {k: v for k, v in ICONIC_TAXA.items() if v not in ['Animalia', 'Unknown']}

# Cache settings
OBS_CACHE_EXPIRY_HOURS = 48

# Config files
CONFIG_PATH = DATA_DIR / 'settings.yml'
STORED_TAXA_PATH = DATA_DIR / 'stored_taxa.json'
MAX_DISPLAY_HISTORY = 50  # Max number of history items to display at a time

# URLs / API settings
OBSERVATION_BASE_URL = 'https://www.inaturalist.org/observations'
PHOTO_BASE_URL = 'https://static.inaturalist.org/photos'
PHOTO_INFO_BASE_URL = 'https://www.inaturalist.org/photos'
PLACES_BASE_URL = 'https://www.inaturalist.org/places'
TAXON_BASE_URL = 'https://www.inaturalist.org/taxa'
USER_AGENT = f'naturtag/{__version__}'.lower()

# Theme/window settings
INIT_WINDOW_POSITION = ('custom', 100, 100)
INIT_WINDOW_SIZE = (1500, 900)
MD_PRIMARY_PALETTE = 'Teal'
MD_ACCENT_PALETTE = 'Cyan'
MAX_LABEL_CHARS = 80

# Simplified tags without formatting variations
TAXON_KEYS = ['taxonid', 'dwc:taxonid']
OBSERVATION_KEYS = ['observationid', 'catalognumber', 'dwc:catalognumber']


# Specific XML namespaces to use terms from when processing DwC observation records
# Note: exiv2 will automatically add recognized namespace URLs when adding properties
DWC_NAMESPACES = ['dcterms', 'dwc']

COMMON_NAME_IGNORE_TERMS = [
    ',',
    ' and ',
    'allies',
    'relatives',
]

# Type aliases
JSON = Union[dict, IO, Iterable[dict], Path, str]
IntTuple = tuple[Optional[int], Optional[int]]
StrTuple = tuple[Optional[str], Optional[str]]
