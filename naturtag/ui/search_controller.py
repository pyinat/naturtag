from pyinaturalist.node_api import get_taxa, get_taxa_autocomplete
from naturtag.ui.autocomplete import AutocompleteSearch


# TODO: Split taxon results into tokens, use only part of it (matched term) for suggestion test
class TaxonAutocompleteSearch(AutocompleteSearch):
    """ Autocomplete search for iNaturalist taxa """
    def get_autocomplete(self, search_str):
        return get_taxa_autocomplete(q=search_str, minify=True).get('results', [])

class SearchController:
    """ Controller class to manage all taxon and observation search parameters """
    pass
