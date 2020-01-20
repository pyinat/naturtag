# PoC to process NCBI taxonomy into hierarchical keyword collection
import pandas as pd


name_cols = [
    'tax_id',
    'name',
    'name_unique',
    'name_class'
]
node_cols = [
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
sorted_cols = [
    'tax_id',
    'parent_tax_id',
    'name',
    'rank',
    'name_class'
]


def flatten_ncbi_dumps():
    df = load_ncbi_dump('NCBI Taxonomy/names.dmp', name_cols, ['name', 'name_class'], usecols=[0, 1, 3])
    df_nodes = load_ncbi_dump('NCBI Taxonomy/nodes.dmp', node_cols, ['rank'], usecols=[0, 1, 2])
    df = df.merge(df_nodes, on='tax_id', how='outer')
    df[sorted_cols].to_csv('ncbi_taxonomy.csv', index=False)
    return df


def load_ncbi_dump(file_path, col_names, str_col_names, **kwargs):
    df = pd.read_csv(
        file_path,
        sep='|',
        index_col=False,
        header=None,
        names=col_names,
        **kwargs,
    )
    # TODO: Better way to automatically strip strings?
    for col in str_col_names:
        df[col] = df[col].str.strip()
    return df


if __name__ == '__main__':
    flatten_ncbi_dumps()
