from pyinaturalist.node_api import get_taxa, get_taxa_autocomplete


class SearchController:
    def __init__(self, taxon_inputs, observation_inputs):
        self.taxon_inputs = taxon_inputs
        self.observation_inputs = observation_inputs

    def get_autocomplete(self):
        get_taxa_autocomplete(q=self.taxon_inputs.taxon_text_input.text)
