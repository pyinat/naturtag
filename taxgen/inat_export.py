#!/usr/bin/env python3
import pandas as pd

from taxgen.constants import INAT_OBSERVATION_FILE, INAT_OUTPUT_BASE
from taxgen.format import write_tree


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
    'taxon_tribe_name',
    # 'taxon_subtribe_name',
    'taxon_genus_name',
    # 'taxon_genushybrid_name',
    'taxon_species_name',
    # 'taxon_hybrid_name',
    'taxon_subspecies_name',
    'taxon_variety_name',
    # 'taxon_form_name',
    'scientific_name',
    'taxon_id',
    'common_name',
]
# Rename 'taxon_<rank>_name' to 'taxonomy:<rank>' for keyword tags
INAT_TAXONOMIC_RANK_LABELS = {
    rank: (
        'taxonomy:' + rank
        .replace('scientific_name', 'binomial')
        .replace('taxon_', '')
        .replace('_name', '')
    )
    for rank in INAT_TAXONOMIC_RANKS
}


def generate_tree(csv_file, column_hierarchy):
    """
    Read tabular data and convert it into a tree, using a defined hierarchy of selected columns
    """
    df = pd.read_csv(csv_file)
    tree = {}
    for i, row in df.iterrows():
        tree = append_nodes(tree, row, column_hierarchy)
    return tree


def append_nodes(tree, row, column_hierarchy):
    """
    Add groups of all ranks contained in a single observation (row)
    """
    tree_node = tree
    for level, label in column_hierarchy.items():
        tree_node = tree_node.setdefault(f'{label}={row[level]}', {})
    return tree


def main():
    tree = generate_tree(INAT_OBSERVATION_FILE, INAT_TAXONOMIC_RANK_LABELS)
    write_tree(tree, INAT_OUTPUT_BASE)


if __name__ == '__main__':
    main()
