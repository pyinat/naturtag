#!/usr/bin/env python3
import json
import logging
from io import BytesIO
from os import makedirs
from os.path import isfile, join
from zipfile import ZipFile

import pandas as pd
from requests_ftp.ftp import FTPSession
from progress.bar import ChargingBar as Bar

logging.basicConfig(level='INFO')

BAR_SUFFIX = '[%(index)d / %(max)d] [%(elapsed_td)s / %(eta_td)s]'

TAXDUMP_URL = 'ftp://ftp.ncbi.nih.gov/pub/taxonomy/taxdmp.zip'
DATA_DIR = 'taxonomy_data'
NAMES_DUMP = join(DATA_DIR, 'names.dmp')
NODES_DUMP = join(DATA_DIR, 'nodes.dmp')
FLAT_FILE = join(DATA_DIR, 'ncbi_taxonomy.csv')
TREE_FILE = join(DATA_DIR, 'ncbi_taxonomy.json')

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

ROOT_TAX_ID = 1
CELLULAR_ORGANISMS_TAX_ID = 131567
BACTERIA_TAX_ID = 2
ARCHAEA_TAX_ID = 2157
EUKARYOTA_TAX_ID = 2759

# Estimate based on NCBI taxonomy browser, used for progress bar
# Can't get an exact estimate ddirectly from dataframe without traversing the whole tree
EUKARYOTE_TAXA_ESTIMATE = 1500000


def download_ncbi_taxdump():
    """
    Download and extract dump files from FTP site
    """
    print('Downloading NCBI taxonomy dump')
    response = FTPSession().retr(TAXDUMP_URL)
    taxdump = ZipFile(BytesIO(response.content))

    print('Extracting')
    makedirs(DATA_DIR, exist_ok=True)
    taxdump.extractall(path=DATA_DIR)


def flatten_ncbi_taxdump():
    """
    Denormalize dump files into a single CSV
    """
    print('Flattening taxonomy dump files')
    df = load_ncbi_dump(NAMES_DUMP, NAME_COLS, usecols=[0, 1, 3])
    df_nodes = load_ncbi_dump(NODES_DUMP, NODE_COLS, usecols=[0, 1, 2])

    # Only keep scientific names, and ensure IDs are unique
    df = df[df['name_class'] == 'scientific name']
    df = df.drop_duplicates('tax_id')

    # Merge nodes and names, keeping only IDs, name, and rank
    df = df.merge(df_nodes, on='tax_id')
    df[SORTED_COLS].to_csv(FLAT_FILE, index=False)
    print(f'Flattened data written to {FLAT_FILE}')
    return df


def load_ncbi_dump(file_path, col_names, **kwargs):
    """
    Load an NCBI taxonomy dump file as a CSV
    """
    print(f'Loading {file_path}')
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


def generate_tree(df):
    """
    Convert NCBI taxonomy node structure into a tree using a depth-first search
    """
    print('Generating tree from taxonomy nodes')
    bar = Bar('Processing', max=EUKARYOTE_TAXA_ESTIMATE, suffix=BAR_SUFFIX)

    def find_children(taxon, tree_node):
        """
        Get a row and all its children as a dict
        """
        tax_label = f"taxonomy:{taxon['rank']}={taxon['name']}"
        tree_node = {tax_label: {}}
        children = df[df['parent_tax_id'] == taxon['tax_id']]
        bar.next()

        # Base case: no children; Recursive case: update tree with all children
        for _, child_node in children.iterrows():
            tree_node[tax_label].update(find_children(child_node, tree_node))
        return tree_node

    eukaryote_node = df[df['tax_id'] == EUKARYOTA_TAX_ID].iloc[0]
    tree = find_children(eukaryote_node, {})
    bar.finish()

    with open(TREE_FILE, 'w') as f:
        json.dump(tree, f, indent=2)
    print(f'Taxonomy tree written to {TREE_FILE}')
    return tree


if __name__ == '__main__':
    if isfile(NAMES_DUMP) and isfile(NODES_DUMP):
        print('Found existing taxonomy dump files')
    else:
        download_ncbi_taxdump()

    if isfile(FLAT_FILE):
        print('Found existing flattened taxonomy file')
        df = pd.read_csv(FLAT_FILE)
    else:
        df = flatten_ncbi_taxdump()

    generate_tree(df)
