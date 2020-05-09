# Paths for relevant input & output files
from os.path import dirname, join

PKG_DIR = dirname(dirname(__file__))
DATA_DIR = join(PKG_DIR, 'taxonomy_data')

NCBI_NAMES_DUMP = join(DATA_DIR, 'names.dmp')
NCBI_NODES_DUMP = join(DATA_DIR, 'nodes.dmp')
NCBI_COMBINED_DUMP = join(DATA_DIR, 'ncbi_taxonomy.csv')
NCBI_OUTPUT_BASE = join(DATA_DIR, 'inat_taxonomy')
NCBI_TAXDUMP_URL = 'ftp://ftp.ncbi.nih.gov/pub/taxonomy/taxdmp.zip'

INAT_OBSERVATION_FILE = join(DATA_DIR, 'observations.csv')
INAT_DWC_ARCHIVE_URL = 'http://www.inaturalist.org/observations/gbif-observations-dwca.zip'

# NCBI taxon IDs for relevant groups
ROOT_TAX_ID = 1
CELLULAR_ORGANISMS_TAX_ID = 131567
BACTERIA_TAX_ID = 2
ARCHAEA_TAX_ID = 2157
EUKARYOTA_TAX_ID = 2759
FUNGI_TAX_ID = 4751
ANIMALIA_TAX_ID = 33208
PLANT_TAX_ID = 33090

# Approximate estimates of total numbers of taxa in main kingdoms of interest;
ESTIMATES = {
    EUKARYOTA_TAX_ID: 1500000,
    PLANT_TAX_ID: 220000,
    ANIMALIA_TAX_ID: 1041000,
    FUNGI_TAX_ID: 167000,
}

# Taxa and terms to omit; mainly unicellular and other microscopic organisms
BLACKLIST_TAXA = [
    'Amoebozoa',
    'Ancyromonadida',
    'Apusozoa',
    'Archaea',
    'Bacteria',
    'Breviatea',
    'CRuMs',
    'Chlorophyta',
    'Choanoflagellata',
    'Cryptophyceae',
    'Discoba',
    'Euglenozoa',
    'Glaucocystophyceae',
    'Haptista',
    'Hemimastigophora',
    'Heterolobosea',
    'Ichthyosporea',
    'Jakobida',
    'Malawimonadidae',
    'Metamonada',
    'Rhodelphea',
    'Rhodophyta',
    'Rotosphaerida',
    'Sar',
    'Trebouxiophyceae',
    'Viruses',
]
BLACKLIST_TERMS = [
    'environmental samples',
    'incertae sedis',
    'sequences',
    'unclassified',
]
