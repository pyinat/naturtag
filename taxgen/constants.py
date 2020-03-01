# Paths for relevant input & output files
# TODO: Make these configurable, if needed
from os.path import dirname, join

PKG_DIR = dirname(dirname(__file__))
DATA_DIR = join(PKG_DIR, 'taxonomy_data')

NCBI_NAMES_DUMP = join(DATA_DIR, 'names.dmp')
NCBI_NODES_DUMP = join(DATA_DIR, 'nodes.dmp')
NCBI_COMBINED_DUMP = join(DATA_DIR, 'ncbi_taxonomy.csv')
NCBI_OUTPUT_JSON = join(DATA_DIR, 'ncbi_taxonomy.json')
NCBI_OUTPUT_KW = join(DATA_DIR, 'ncbi_taxonomy.txt')

INAT_OBSERVATION_FILE = join(DATA_DIR, 'observations.csv')
INAT_OUTPUT_JSON = join(DATA_DIR, 'inat_taxonomy.json')
INAT_OUTPUT_KW = join(DATA_DIR, 'inat_taxonomy.txt')
