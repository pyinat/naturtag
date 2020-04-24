from os.path import splitext

import pandas as pd

from taxgen.format import write_tree


# Mapping from iNat metadata to keyword tags
INAT_TAXONOMIC_RANKS = {
    'taxon_kingdom_name':       'taxonomy:kingdom',
    'taxon_phylum_name':        'taxonomy:phylum',
    'taxon_subphylum_name':     'taxonomy:subphylum',
    'taxon_superclass_name':    'taxonomy:superclass',
    'taxon_class_name':         'taxonomy:class',
    'taxon_subclass_name':      'taxonomy:subclass',
    'taxon_superorder_name':    'taxonomy:superorder',
    'taxon_order_name':         'taxonomy:order',
    'taxon_suborder_name':      'taxonomy:suborder',
    'taxon_superfamily_name':   'taxonomy:superfamily',
    'taxon_family_name':        'taxonomy:family',
    'taxon_subfamily_name':     'taxonomy:subfamily',
    'taxon_supertribe_name':    'taxonomy:supertribe',
    'taxon_tribe_name':         'taxonomy:tribe',
    'taxon_subtribe_name':      'taxonomy:subtribe',
    'taxon_genus_name':         'taxonomy:genus',
    'taxon_genushybrid_name':   'taxonomy:genushybrid',
    'taxon_species_name':       'taxonomy:species',
    'taxon_hybrid_name':        'taxonomy:hybrid',
    'taxon_subspecies_name':    'taxonomy:subspecies',
    'taxon_variety_name':       'taxonomy:variety',
    'taxon_form_name':          'taxonomy:form',
    'scientific_name':          'taxonomy:binomial',
    'common_name':              'taxonomy:common',
    'taxon_id':                 'inat:taxon_id',
}


def generate_tree(csv_file, output_dir, column_hierarchy=INAT_TAXONOMIC_RANKS):
    """
    Read tabular data and convert it into a tree, using a defined hierarchy of selected columns
    """
    df = pd.read_csv(csv_file)
    tree = {}
    for i, row in df.iterrows():
        tree = append_nodes(tree, row, column_hierarchy)

    output_file_base = splitext(csv_file)[0]
    write_tree(tree, output_dir, output_file_base)


def append_nodes(tree, row, column_hierarchy):
    """
    Add groups of all ranks contained in a single observation (row)
    """
    tree_node = tree
    for level, label in column_hierarchy.items():
        tree_node = tree_node.setdefault(f'{label}={row[level]}', {})
    return tree
