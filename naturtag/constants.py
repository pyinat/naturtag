# flake8: noqa: F401
from pathlib import Path
from typing import Optional, Union

from platformdirs import user_data_dir
from pyinaturalist.constants import ICONIC_TAXA, RANKS
from pyinaturalist_convert.constants import DB_PATH

# In an sdist/wheel, package files will be
# In a pyinstaller package, source files will be in the root dir
PKG_DIR = Path(__file__).parent.parent

# Packaged assets
ASSETS_DIR = PKG_DIR / 'assets'
ICONS_DIR = ASSETS_DIR / 'icons'
CLI_COMPLETE_DIR = ASSETS_DIR / 'autocomplete'
FTS_DB = ASSETS_DIR / 'taxon-fts-en.tar.gz'
APP_ICON = ICONS_DIR / 'logo.ico'
APP_LOGO = ICONS_DIR / 'logo.png'

# Local settings & data paths
DATA_DIR = Path(user_data_dir()) / 'Naturtag'
IMAGE_CACHE = DATA_DIR / 'images.db'
LOGFILE = DATA_DIR / 'naturtag.log'
CONFIG_PATH = DATA_DIR / 'settings.yml'
USER_TAXA_PATH = DATA_DIR / 'stored_taxa.yml'

# Project info
DOCS_URL = 'https://naturtag.readthedocs.io/en/latest/app.html'
REPO_URL = 'https://github.com/pyinat/naturtag'

# Thumnbnail settings
IMAGE_FILETYPES = ['*.jpg', '*.jpeg', '*.png', '*.gif', '*.webp']
PHOTO_SIZES = ['square', 'small', 'medium', 'large', 'original']
THUMBNAIL_SIZE_SM = (75, 75)
THUMBNAIL_SIZE_DEFAULT = (250, 250)
THUMBNAIL_SIZE_LG = (500, 500)
THUMBNAIL_SIZES = {
    'small': THUMBNAIL_SIZE_SM,
    'medium': THUMBNAIL_SIZE_DEFAULT,
    'large': THUMBNAIL_SIZE_LG,
}

# Relevant groups of image metadata tags
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

DATE_TAGS = [
    'Exif.Photo.DateTimeOriginal',
    'Xmp.exif.DateTimeOriginal',
    'Exif.Photo.DateTimeDigitized',
    'Xmp.exif.DateTimeDigitized',
    'Xmp.dwc.eventDate',
]
KEYWORD_TAGS = [
    'Exif.Image.XPSubject',
    'Iptc.Application2.Subject',
    'Xmp.dc.subject',
]
HIER_KEYWORD_TAGS = [
    'Exif.Image.XPKeywords',
    'Iptc.Application2.Keywords',
    'Xmp.lr.hierarchicalSubject',
]

# Theme/window/display settings
DEFAULT_WINDOW_SIZE = (1500, 1024)
MAX_LABEL_CHARS = 80
QSS_PATH = ASSETS_DIR / 'style.qss'
MAX_DISPLAY_HISTORY = 50  # Max number of history items to display at a time
MAX_DISPLAY_OBSERVED = 100  # Max number of observed taxa to display at a time

# Simplified tags without formatting variations
TAXON_KEYS = ['taxonid', 'dwc:taxonid']
OBSERVATION_KEYS = ['observationid', 'catalognumber', 'dwc:catalognumber']

COMMON_NAME_IGNORE_TERMS = [',', ' and ', 'allies', 'relatives', 'typical']
SELECTABLE_ICONIC_TAXA = {k: v for k, v in ICONIC_TAXA.items() if v not in ['Animalia', 'Unknown']}

# Simplified subset of ranks that are useful for display
COMMON_RANKS = [
    'form',
    'variety',
    'species',
    'genus',
    'tribe',
    'family',
    'order',
    'class',
    'phylum',
    'kingdom',
]
ROOT_TAXON_ID = 48460

# Type aliases
IntTuple = tuple[Optional[int], Optional[int]]
StrTuple = tuple[str, str]
PathOrStr = Union[Path, str]
