from io import BytesIO
from logging import getLogger
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
    NCBI_OUTPUT_BASE,
    ESTIMATES,
    BLACKLIST_TAXA,
    BLACKLIST_TERMS,
)
from taxgen.format import write_tree


BAR_SUFFIX = '[%(index)d / %(max)d] [%(elapsed_td)s / %(eta_td)s]'

logger = getLogger(__name__)


def generate_trees(df, output_dir, root_taxon_ids):
    """ Generate trees for the given root taxa and write to separate files """
    for taxon_id in root_taxon_ids:
        root_node = df[df['tax_id'] == taxon_id].iloc[0]
        root_name = root_node['name'].lower()
        tree = generate_tree(df, root_node)
        write_tree(tree, output_dir, f"{NCBI_OUTPUT_BASE}_{root_name}")


def generate_tree(df, root_taxon):
    """
    Convert NCBI taxonomy node structure into a tree using a depth-first search
    """
    logger.info(f"Generating tree from root taxon {root_taxon['rank']}={root_taxon['name']}")
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
