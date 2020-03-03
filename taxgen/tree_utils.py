# Helper functions for navigating a Dataframe containing taxonomy data


def count_descendants(df, name=None, id=None):
    """ Recursively count the total number of descendants of the given taxon """

    def _count_descendants_rec(taxon, depth):
        child_taxa = df[df['parent_tax_id'] == taxon['tax_id']]
        subtotal = 1

        for _, child_taxon in child_taxa.iterrows():
            subtotal += _count_descendants_rec(child_taxon, depth + 1)

        # if depth < 4 and subtotal >= 1000:
        #     print(f"{taxon['rank']}={taxon['name']}: {subtotal}")
        return subtotal

    taxon = get_taxon(df, name, id)
    return _count_descendants_rec(taxon, 0)


def get_parent(df, name=None, id=None):
    """ Get parent taxon """
    taxon = get_taxon(df, name, id)
    return df[df['tax_id'] == taxon['parent_tax_id']].iloc[0]


def get_children(df, name=None, id=None):
    """ Get immediate children (not all descendants) """
    taxon = get_taxon(df, name, id)
    return df[df['parent_tax_id'] == taxon['tax_id']]


def get_siblings(df, name=None, id=None):
    """ Get other taxa with the same parent (not necessarily at the same rank) """
    parent = get_parent(df, name, id)
    return get_children(df, id=parent['tax_id'])


def get_taxon(df, name=None, id=None):
    """ Get a taxon row by either name or ID """
    if name:
        return df[df['name'] == name].iloc[0]
    elif id:
        return df[df['tax_id'] == id].iloc[0]
