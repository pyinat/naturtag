#!/usr/bin/env python3
from io import BytesIO
from os import makedirs
from os.path import isfile
from zipfile import ZipFile

import pandas as pd
from requests_ftp.ftp import FTPSession
from progress.bar import ChargingBar as Bar

from taxgen.constants import *
from taxgen.format import write_tree

BAR_SUFFIX = '[%(index)d / %(max)d] [%(elapsed_td)s / %(eta_td)s]'
TAXDUMP_URL = 'ftp://ftp.ncbi.nih.gov/pub/taxonomy/taxdmp.zip'

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


def generate_tree(df, root_taxon):
    """
    Convert NCBI taxonomy node structure into a tree using a depth-first search
    """
    print(f"Generating tree from root taxon {root_taxon['rank']}={root_taxon['name']}")
    max_estimate = ESTIMATES.get(root_taxon['tax_id'], 1500000)
    bar = Bar('Processing', max=max_estimate, suffix=BAR_SUFFIX)

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

    tree = find_children(root_taxon)
    bar.finish()
    return tree


def _is_ignored(taxon):
    """ Determine if a taxon is blacklisted """
    has_bl_terms = [term in taxon['name'] for term in BLACKLIST_TERMS]
    is_bl_taxa = [name == taxon['name'] for name in BLACKLIST_TAXA]
    return any(has_bl_terms + is_bl_taxa)


def generate_trees(df, root_taxon_ids):
    """ Generate trees for the given root taxa and write to separate files """
    for taxon_id in root_taxon_ids:
        root_node = df[df['tax_id'] == taxon_id].iloc[0]
        tree = generate_tree(df, root_node)
        write_tree(tree, f"{NCBI_OUTPUT_BASE}_{root_node['name'].lower()}")


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

    # TODO: Make this configurable and/or a CLI param
    # generate_trees(df, [EUKARYOTA_TAX_ID])
    generate_trees(df, [ANIMALIA_TAX_ID, PLANT_TAX_ID, FUNGI_TAX_ID])


if __name__ == '__main__':
    main()
