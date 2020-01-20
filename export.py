import pandas as pd
import json


INAT_TAXONOMIC_RANKS = [
    'taxon_kingdom_name',
    'taxon_phylum_name',
    # 'taxon_subphylum_name',
    # 'taxon_superclass_name',
    'taxon_class_name',
    # 'taxon_subclass_name',
    # 'taxon_superorder_name',
    'taxon_order_name',
    # 'taxon_suborder_name',
    # 'taxon_superfamily_name',
    'taxon_family_name',
    # 'taxon_subfamily_name',
    # 'taxon_supertribe_name',
    # 'taxon_tribe_name',
    # 'taxon_subtribe_name',
    'taxon_genus_name',
    # 'taxon_genushybrid_name',
    'taxon_species_name',
    # 'taxon_hybrid_name',
    # 'taxon_subspecies_name',
    # 'taxon_variety_name',
    # 'taxon_form_name',
    'scientific_name',
    'taxon_id',
    'common_name',
]
INAT_TAXONOMIC_RANK_LABELS = {
    rank: (
        'taxonomy:' + 
        rank
        .replace('scientific_name', 'binomial')
        .replace('taxon_', '')
        .replace('_name', '')
    )
    for rank in INAT_TAXONOMIC_RANKS
}


def table_to_tree(csv_file, column_hierarchy):
    """
    Read tabular data and convert it into a tree, using a defined hierarchy of selected columns
    """
    df = pd.read_csv(csv_file)
    tree = {}
    for i, row in df.iterrows():
        tree = build_tree(tree, row, column_hierarchy)
    with open('out.json', 'w') as f:
        json.dump(tree, f, indent=2)


def build_tree(tree, row, column_hierarchy):
    tree_node = tree
    for level, label in column_hierarchy.items():
        tree_node = tree_node.setdefault(f'{label}={row[level]}', {})
    return tree


if __name__ == '__main__':
    table_to_tree('observations.csv', INAT_TAXONOMIC_RANK_LABELS)
