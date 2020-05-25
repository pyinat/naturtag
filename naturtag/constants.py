from collections import OrderedDict
from os.path import dirname, join
from appdirs import user_data_dir
from pyinaturalist.constants import RANKS

# Resource directories
PKG_DIR = dirname(dirname(__file__))
ASSETS_DIR = join(PKG_DIR, 'assets', '')
KV_SRC_DIR = join(PKG_DIR, 'kv')
ICONS_DIR = join(ASSETS_DIR, 'iconic_taxa')
DATA_DIR = join(user_data_dir(), 'Naturtag')

# TODO: These may be useful as user-configurable settings
AUTOCOMPLETE_DELAY = 0.5
AUTOCOMPLETE_MIN_CHARS = 3
IMAGE_FILETYPES = ['*.jpg', '*.jpeg', '*.png', '*.gif']

# Thumnbnail & cache settings
THUMBNAILS_DIR = join(DATA_DIR, 'thumbnails')
THUMBNAIL_DEFAULT_FORMAT = 'png'
THUMBNAIL_SIZE_DEFAULT = (200, 200)
THUMBNAIL_SIZE_SM = (75, 75)
THUMBNAIL_SIZE_LG = (500, 500)
CACHE_PATH = join(DATA_DIR, 'inaturalist_api_cache')
CACHE_BACKEND = 'sqlite'

# Config files
CONFIG_PATH = join(DATA_DIR, 'settings.yml')
DEFAULT_CONFIG_PATH = join(PKG_DIR, 'default_settings.yml')

# URLs
TAXON_BASE_URL = 'https://www.inaturalist.org/taxa'
OBSERVATION_BASE_URL = 'https://www.inaturalist.org/observations'
PLACES_BASE_URL = 'https://www.inaturalist.org/places'

# Theme/window settings
INIT_WINDOW_SIZE = (1250, 800)
MD_PRIMARY_PALETTE = 'Teal'
MD_ACCENT_PALETTE = 'Cyan'

# Key codes; reference: https://gist.github.com/Enteleform/a2e4daf9c302518bf31fcc2b35da4661
BACKSPACE = 8
F11 = 292

# Simplified tags without formatting variations
TAXON_KEYS = ['taxonid', 'dwc:taxonid']
OBSERVATION_KEYS = ['observationid', 'catalognumber', 'dwc:catalognumber']

# Iconic taxa, aka common taxon search categories, in the same order as shown on the iNar web UI
ICONIC_TAXA = OrderedDict([
    (3, 'aves'),
    (20978, 'amphibia'),
    (26036, 'reptilia'),
    (40151, 'mammalia'),
    (47178, 'actinopterygii'),
    (47115, 'mollusca'),
    (47119, 'arachnida'),
    (47158, 'insecta'),
    (47126, 'plantae'),
    (47170, 'fungi'),
    (48222, 'chromista'),
    (47686, 'protozoa'),
    # (1, 'animalia'),
    # (0, 'unknown'),
])

# Specific XML namespaces to use terms from when processing DwC observation records
# Note: exiv2 will automatically add recognized namespaces when adding properties
DWC_NAMESPACES = {
    "dcterms": "http://purl.org/dc/terms/",
    "dwc": "http://rs.tdwg.org/dwc/terms/",
}

# Basic DwC fields that can be added for a taxon without an observation
MINIMAL_DWC_TERMS = [
    'dwc:kingdom',
    'dwc:phylum',
    'dwc:class',
    'dwc:order',
    'dwc:family',
    'dwc:genus',
    'dwc:species',
    'dwc:scientificName',
    'dwc:taxonRank',
    'dwc:taxonID',
]
