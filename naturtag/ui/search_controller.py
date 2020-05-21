from pyinaturalist.node_api import get_taxa, get_taxa_autocomplete
from naturtag.ui.autocomplete import AutocompleteSearch
from naturtag.inat_metadata import get_taxa_autocomplete


class TaxonAutocompleteSearch(AutocompleteSearch):
    """ Autocomplete search for iNaturalist taxa """
    def get_autocomplete(self, search_str):
        return get_taxa_autocomplete(search_str)


class SearchController:
    """ Controller class to manage all taxon and observation search parameters """
    def __init__(self, taxon_inputs, observation_inputs):
        self.taxon_inputs = taxon_inputs
        self.observation_inputs = observation_inputs
