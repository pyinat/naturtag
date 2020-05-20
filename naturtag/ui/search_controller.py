from pyinaturalist.node_api import get_taxa, get_taxa_autocomplete
from naturtag.ui.autocomplete import AutocompleteSearch


class TaxonAutocompleteSearch(AutocompleteSearch):
    """ Autocomplete search for iNaturalist taxa """
    def get_autocomplete(self, search_str):
        results = get_taxa_autocomplete(q=search_str).get('results', [])
        return [self._get_taxon_labels(taxon) for taxon in results]

    @staticmethod
    def _get_taxon_labels(taxon):
        # Padding in format strings is to visually align taxon IDs (< 7 chars) and ranks (< 11 chars)
        # TODO: Monospace font
        display_text = "{:>8}: {:>12} {}".format(taxon["id"], taxon["rank"].title(), taxon["name"])
        if 'preferred_common_name' in taxon:
            display_text += f' ({taxon["preferred_common_name"]})'
        return display_text, taxon['matched_term']

class SearchController:
    """ Controller class to manage all taxon and observation search parameters """
    def __init__(self, taxon_inputs, observation_inputs):
        self.taxon_inputs = taxon_inputs
        self.observation_inputs = observation_inputs
