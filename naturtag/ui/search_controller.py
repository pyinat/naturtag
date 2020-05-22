from logging import getLogger
from os.path import join

from kivymd.uix.imagelist import SmartTile

from pyinaturalist.node_api import get_taxa_autocomplete
from naturtag.ui.autocomplete import AutocompleteSearch
from naturtag.models import Taxon
from naturtag.constants import ICONS_DIR, ICONIC_TAXA

logger = getLogger().getChild(__name__)


class TaxonAutocompleteSearch(AutocompleteSearch):
    """ Autocomplete search for iNaturalist taxa """
    def get_autocomplete(self, search_str):
        """ Get taxa autocomplete search results, as display text + other metadata """
        def get_dropdown_info(taxon):
            common_name = f' ({taxon["preferred_common_name"]})' if 'preferred_common_name' in taxon else ''
            display_text = f'{taxon["rank"].title()}: {taxon["name"]}{common_name}'
            return {'text': display_text, 'suggestion_text': taxon['matched_term'], 'metadata': taxon}

        results = get_taxa_autocomplete(q=search_str).get('results', [])
        return [get_dropdown_info(taxon) for taxon in results]


class IconicTaxaIcon(SmartTile):
    box_color = (0, 0, 0, 0)
    def __init__(self, taxon, **kwargs):
        icon_path = join(ICONS_DIR, f'{taxon}.png')
        super().__init__(source=icon_path, **kwargs)


# TODO: One controller class for each screen, or combined?
class SearchController:
    """ Controller class to manage all taxon and observation search parameters """
    def __init__(self, taxon_screen, observation_screen):
        self.taxon_screen = taxon_screen
        self.observation_screen = observation_screen
        self.taxon_search_input = taxon_screen.taxon_search_input
        self.taxon_id_input = taxon_screen.taxon_id_input
        self.selected_taxon_photo = taxon_screen.selected_taxon_photo
        self.selected_taxon_name = taxon_screen.selected_taxon_name
        self.iconic_taxa = taxon_screen.iconic_taxa

        self.taxon_search_input.selection_callback = self.handle_selection

        # Set 'Categories' (iconic taxa) icons
        for taxon in ICONIC_TAXA.values():
            self.iconic_taxa.add_widget(IconicTaxaIcon(taxon))

        self.selected_taxon = None
        self.selected_observation = None

    def handle_selection(self, metadata):
        self.select_taxon(metadata['id'])

    # TODO: add more info, make link clickable, make this not look terrible
    def select_taxon(self, id):
        logger.warning(f'Selecting taxon: {id}')
        self.selected_taxon = Taxon(id=id)
        # TODO: Cache thumbnails for these (default_photo.square_url)
        self.selected_taxon_photo.source = self.selected_taxon.photo_url
        self.selected_taxon_name.text = (
            f'[{self.selected_taxon.id}] {self.selected_taxon.rank.title()}: '
            f'{self.selected_taxon.name}\n'
            f'[ref=https://www.inaturalist.org/taxa/{self.selected_taxon.id}]link[/ref]'
        )

