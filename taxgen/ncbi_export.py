#!/usr/bin/env python3
from io import BytesIO
from os import makedirs
from os.path import isfile
from zipfile import ZipFile

import pandas as pd
from requests_ftp.ftp import FTPSession
from progress.bar import ChargingBar as Bar

from taxgen.constants import (
    DATA_DIR,
    NCBI_NAMES_DUMP,
    NCBI_NODES_DUMP,
    NCBI_COMBINED_DUMP,
    NCBI_OUTPUT_JSON,
)
from taxgen.format import write_tree

BAR_SUFFIX = '[%(index)d / %(max)d] [%(elapsed_td)s / %(eta_td)s]'
TAXDUMP_URL = 'ftp://ftp.ncbi.nih.gov/pub/taxonomy/taxdmp.zip'

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
BLACKLIST_TAXA = [
    'Amoebozoa',
    'Ancyromonadida',
    'Apusozoa',
    'Breviatea',
    'Chlorophyta',
    'CRuMs',
    'Cryptophyceae',
    'Discoba',
    'Euglenozoa',
    'Glaucocystophyceae',
    'Haptista',
    'Hemimastigophora',
    'Heterolobosea',
    'Jakobida',
    'Malawimonadidae',
    'Metamonada',
    'Rhodelphea',
    'Rhodophyta',
    'Sar',
    'Trebouxiophyceae',
]
BLACKLIST_TERMS = [
    'environmental samples',
    'incertae sedis',
    'unclassified',
]


# Estimate based on NCBI taxonomy browser, used for progress bar
# Can't get an exact estimate directly from dataframe without traversing the whole tree
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


def combine_ncbi_taxdump():
    """
    Denormalize dump files into one combined CSV
    """
    print('Flattening taxonomy dump files')
    df = load_ncbi_dump(NCBI_NAMES_DUMP, NAME_COLS, usecols=[0, 1, 3])
    df_nodes = load_ncbi_dump(NCBI_NODES_DUMP, NODE_COLS, usecols=[0, 1, 2])

    # Only keep scientific names, and ensure IDs are unique
    df = df[df['name_class'] == 'scientific name']
    df = df.drop_duplicates('tax_id')

    # Merge nodes and names, keeping only IDs, name, and rank
    df = df.merge(df_nodes, on='tax_id')
    df[SORTED_COLS].to_csv(NCBI_COMBINED_DUMP, index=False)
    print(f'Flattened data written to {NCBI_COMBINED_DUMP}')
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

   def find_children(taxon):
        """ Get a row and all its children as a dict """
        # If the taxon is blacklisted, ignore it and all its children
        if _is_ignored(taxon):
            return {}

        child_taxa = df[df['parent_tax_id'] == taxon['tax_id']]
        child_nodes = {}
        bar.next()

        # Base case: no children; Recursive case: update tree with all children
        for _, child_taxon in child_taxa.iterrows():
            child_nodes.update(find_children(child_taxon))

        # Skip over node if it's 'no rank' (typically meaning unclassified)
        if taxon['rank'] == 'no rank':
            return child_nodes
        else:
            return {f"taxonomy:{taxon['rank']}={taxon['name']}": child_nodes}

    eukaryota_node = df[df['tax_id'] == EUKARYOTA_TAX_ID].iloc[0]
    tree = find_children(eukaryota_node)
    bar.finish()
    return tree


def _is_ignored(taxon):
    """ Determine if a taxon is blacklisted """
    has_bl_terms = [term in taxon['name'] for term in BLACKLIST_TERMS]
    is_bl_taxa = [name == taxon['name'] for name in BLACKLIST_TAXA]
    return any(has_bl_terms + is_bl_taxa)


def main():
    if isfile(NCBI_NAMES_DUMP) and isfile(NCBI_NODES_DUMP):
        print('Found existing taxonomy dump files')
    else:
        download_ncbi_taxdump()

    if isfile(NCBI_COMBINED_DUMP):
        print('Found existing flattened taxonomy file')
        df = pd.read_csv(NCBI_COMBINED_DUMP)
    else:
        df = combine_ncbi_taxdump()

    tree = generate_tree(df)
    write_tree(tree, NCBI_OUTPUT_JSON)


if __name__ == '__main__':
    main()
