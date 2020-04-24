from io import BytesIO
from logging import getLogger
from os import makedirs
from os.path import isfile
from zipfile import ZipFile

import pandas as pd
from requests_ftp.ftp import FTPSession

from taxgen.constants import (
    DATA_DIR,
    NCBI_NAMES_DUMP,
    NCBI_NODES_DUMP,
    NCBI_COMBINED_DUMP,
    NCBI_TAXDUMP_URL,
)

# Columns for NCBI data structures
NAME_COLS = [
    'tax_id',
    'name',
    'name_unique',
    'name_class'
]
NODE_COLS = [
    'tax_id',
    'parent_tax_id',
    'rank',
    'embl_code',
    'division_id',
    'inherited_div_flag',
    'genetic_code_id',
    'inherited_gc__flag',
    'mitochondrial_genetic_code_id',
    'inherited_mgc_flag',
    'genbank_hidden_flag',
    'hidden_subtree_root_flag',
    'comments',
]
SORTED_COLS = [
    'tax_id',
    'parent_tax_id',
    'name',
    'rank',
]

logger = getLogger(__name__)


def prepare_ncbi_taxdump():
    """ Download and process NCBI dump files, or load existing ones if present """
    if isfile(NCBI_NAMES_DUMP) and isfile(NCBI_NODES_DUMP):
        logger.info('Found existing taxonomy dump files')
    else:
        download_ncbi_taxdump()

    if isfile(NCBI_COMBINED_DUMP):
        logger.info('Found existing flattened taxonomy file')
        df = pd.read_csv(NCBI_COMBINED_DUMP)
    else:
        df = combine_ncbi_taxdump()

    return df


def download_ncbi_taxdump():
    """
    Download and extract dump files from FTP site
    """
    logger.info('Downloading NCBI taxonomy dump')
    response = FTPSession().retr(NCBI_TAXDUMP_URL)
    taxdump = ZipFile(BytesIO(response.content))

    logger.info('Extracting')
    makedirs(DATA_DIR, exist_ok=True)
    taxdump.extractall(path=DATA_DIR)


def combine_ncbi_taxdump():
    """
    Denormalize dump files into one combined CSV
    """
    logger.info('Flattening taxonomy dump files')
    df = load_ncbi_dump(NCBI_NAMES_DUMP, NAME_COLS, usecols=[0, 1, 3])
    df_nodes = load_ncbi_dump(NCBI_NODES_DUMP, NODE_COLS, usecols=[0, 1, 2])

    # Only keep scientific names, and ensure IDs are unique
    df = df[df['name_class'] == 'scientific name']
    df = df.drop_duplicates('tax_id')

    # Merge nodes and names, keeping only IDs, name, and rank
    df = df.merge(df_nodes, on='tax_id')
    df[SORTED_COLS].to_csv(NCBI_COMBINED_DUMP, index=False)
    logger.info(f'Flattened data written to {NCBI_COMBINED_DUMP}')
    return df


def load_ncbi_dump(file_path, col_names, **kwargs):
    """
    Load an NCBI taxonomy dump file as a CSV
    """
    logger.info(f'Loading {file_path}')
    df = pd.read_csv(
        file_path,
        sep='|',
        index_col=False,
        header=None,
        names=col_names,
        **kwargs,
    )

    # Strip string columns
    for col in df.columns:
        if df[col].dtype == object:
            df[col] = df[col].str.strip()
    return df
