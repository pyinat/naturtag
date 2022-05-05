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
KV_SRC_DIR = PKG_DIR / 'kv'
DATA_DIR = Path(user_data_dir()) / 'Naturtag'

# TODO: These may be useful as user-configurable settings
TRIGGER_DELAY = 0.1
AUTOCOMPLETE_DELAY = 0.5
AUTOCOMPLETE_MIN_CHARS = 3
IMAGE_FILETYPES = ['*.jpg', '*.jpeg', '*.png', '*.gif', '*.webp']
PHOTO_SIZES = ['square', 'small', 'medium', 'large', 'original']

# Thumnbnail & cache settings
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

# Atlas settings
ATLAS_MAX_SIZE = 4096
ATLAS_DIR = ASSETS_DIR / 'atlas'
ATLAS_APP_ICONS = ATLAS_DIR / 'app_icons'
ATLAS_TAXON_ICONS = ATLAS_DIR / 'taxon_icons'
ATLAS_TAXON_PHOTOS = ATLAS_DIR / 'taxon_photos'
ATLAS_LOCAL_PHOTOS = ATLAS_DIR / 'local_photos'
ALL_ATLASES = [ATLAS_APP_ICONS, ATLAS_TAXON_ICONS, ATLAS_TAXON_PHOTOS, ATLAS_LOCAL_PHOTOS]
TAXON_ICON_PLACEHOLDER = f'atlas://{ATLAS_APP_ICONS}/unknown'

APP_ICONS_DIR = ASSETS_DIR / 'iconic_taxa'
APP_LOGO = str(ASSETS_DIR / 'logo.png')
SELECTABLE_ICONIC_TAXA = {k: v for k, v in ICONIC_TAXA.items() if v not in ['Animalia', 'Unknown']}

# Cache settings
# CACHE_FILE = DATA_DIR / 'api_cache.db'
OBS_CACHE_EXPIRY_HOURS = 48
CACHE_EXPIRATION = {
    'api.inaturalist.org/v*/observations*': timedelta(days=2),
    'api.inaturalist.org/v*/taxa*': timedelta(days=60),
    'static.inaturalist.org/*': -1,
    'inaturalist-open-data.s3.amazonaws.com/*': -1,
    '*': timedelta(hours=1),
}

# Config files
CONFIG_PATH = DATA_DIR / 'settings.yml'
DEFAULT_CONFIG_PATH = PKG_DIR / 'default_settings.yml'
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

# Key codes; reference: https://gist.github.com/Enteleform/a2e4daf9c302518bf31fcc2b35da4661
BACKSPACE = 8
ENTER = 13
F11 = 292

# Simplified tags without formatting variations
TAXON_KEYS = ['taxonid', 'dwc:taxonid']
OBSERVATION_KEYS = ['observationid', 'catalognumber', 'dwc:catalognumber']

PLACEHOLDER_ICON = f'{ATLAS_APP_ICONS}/unknown'

# Specific XML namespaces to use terms from when processing DwC observation records
# Note: exiv2 will automatically add recognized namespaces when adding properties
DWC_NAMESPACES = {
    "dcterms": "http://purl.org/dc/terms/",
    "dwc": "http://rs.tdwg.org/dwc/terms/",
}

# Basic DwC fields that can be added for a taxon without an observation
DWC_TAXON_TERMS = [
    'Xmp.dwc.kingdom',
    'Xmp.dwc.phylum',
    'Xmp.dwc.class',
    'Xmp.dwc.order',
    'Xmp.dwc.family',
    'Xmp.dwc.genus',
    'Xmp.dwc.species',
    'Xmp.dwc.scientificName',
    'Xmp.dwc.taxonRank',
    'Xmp.dwc.taxonID',
]

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
