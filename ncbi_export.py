#!/usr/bin/env python3
# PoC to process NCBI taxonomy into hierarchical keyword collection
import pandas as pd
import json
from progress.bar import ChargingBar as Bar
# from progress.bar import IncrementalBar as Bar


# Download dump files from: ftp://ftp.ncbi.nih.gov/pub/taxonomy/taxdmp.zip
NAMES_DUMP = 'NCBI Taxonomy/names.dmp'
NODES_DUMP = 'NCBI Taxonomy/nodes.dmp'
FLAT_FILE = 'ncbi_taxonomy.csv'
TREE_FILE = 'ncbi_taxonomy.json'

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
BACTERIA_TAX_ID = 2
ARCHAEA_TAX_ID = 2157
CELLULAR_ORGANISMS_TAX_ID = 131567


def flatten_ncbi_dumps():
    """
    Denormalize NCBI dump files into a single CSV
    """
    print('Flatting NCBI dump files')
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
    Load an NCBI dump file as a CSV
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
    for col in col_names:
        if df[col].dtype == object:
            df[col] = df[col].str.strip()
    return df


# TODO: This is inefficient, a parallelized DFS would be better, but too lazy for that right now
def nodes_to_dict(df):
    """
    Convert NCBI taxonomy node structure into a tree
    """
    print('Converting rows into a tree')
    tree = {}
    bar = Bar('Processing', max=len(df.index), suffix='[%(index)d / %(max)d] [%(elapsed_td)s / %(eta_td)s]')

    def find_parents(row, lst):
        """
        Get this row and all its parents as a list, highest ranks first
        """
        # Base case: (super)kingdom of eukaryotic cellular organisms: return it with its descendants
        if row['tax_id'] == CELLULAR_ORGANISMS_TAX_ID:
            return lst
        # Base case: viruses, sequences, and prokaryotes: discard it and all its descendants
        elif row['tax_id'] in [ROOT_TAX_ID, BACTERIA_TAX_ID, ARCHAEA_TAX_ID]:
            return []

        # Recursive case: find parent node and append current node
        parent_row = df[df['tax_id'] == row['parent_tax_id']].iloc[0]

        # Skip past 'no rank' groups
        if row['rank'] != 'no rank':
            lst.insert(0, f"taxonomy:{row['rank']}={row['name']}")
        return find_parents(parent_row, lst)

    for _, row in df.iterrows():
        # Start over at root
        tree_node = tree
        # Populate tree with this clade and all its parents, starting with highest ranks first
        for level in find_parents(row, []):
            tree_node = tree_node.setdefault(level, {})
        bar.next()
    bar.finish()

    with open(TREE_FILE, 'w') as f:
        json.dump(tree, f, indent=2)
    print(f'Hierarchical data written to {TREE_FILE}')
    return tree


if __name__ == '__main__':
    # df = flatten_ncbi_dumps()
    df = pd.read_csv(FLAT_FILE)
    nodes_to_dict(df)
