from logging import getLogger
from os.path import join
import webbrowser

from kivymd.uix.list import OneLineListItem, TwoLineAvatarListItem, ImageLeftWidget

from pyinaturalist.node_api import get_taxa_autocomplete
from naturtag.constants import ICONIC_TAXA
from naturtag.models import Taxon, get_icon_path
from naturtag.ui.autocomplete import AutocompleteSearch
from naturtag.ui.image import IconicTaxaIcon

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


class TaxonSearchController:
    """ Controller class to manage taxon search and display """
    def __init__(self, screen):
        self.screen = screen
        # Search inputs
        self.taxon_search_input = screen.taxon_search_input
        self.taxon_id_input = screen.taxon_id_input
        self.taxon_search_input.selection_callback = self.handle_selection

        # Outputs
        self.selected_taxon = None
        self.taxon_photo = screen.selected_taxon_photo
        self.ancestors = screen.selected_taxon_ancestors
        self.children = screen.selected_taxon_children
        self.basic_info = self.screen.selected_taxon_basic_info

        # Set 'Categories' (iconic taxa) icons
        for id in ICONIC_TAXA:
            icon = IconicTaxaIcon(source=get_icon_path(id))
            self.screen.iconic_taxa.add_widget(icon)


    def handle_selection(self, metadata):
        """ Handle selecting a taxon from autocomplete dropdown """
        self.select_taxon(json_result=metadata)

    # TODO: Make this not look terrible
    # TODO: This is a lot of info... Taxon info should probably be its own class
    # TODO: Cache default_photo.square_url for display in autocomplete dropdown
    def select_taxon(self, json_result=None, id=None):
        """ Update taxon info display by either ID, partial record, or complete record """
        logger.info(f'Selecting taxon: {id or json_result["id"]}')
        self.basic_info.clear_widgets()
        self.selected_taxon = Taxon(json_result=json_result, id=id)
        self.taxon_id_input = id

        # Photo
        if self.selected_taxon.photo_url:
            self.taxon_photo.source = self.selected_taxon.photo_url

        # Link
        self.screen.selected_taxon_link_button.bind(
            on_release=lambda *x: webbrowser.open(self.selected_taxon.link))
        self.screen.selected_taxon_link_button.tooltip_text = self.selected_taxon.link

        # Basic info box: Name, rank
        item = TwoLineAvatarListItem(
            text=self.selected_taxon.name, secondary_text=self.selected_taxon.rank.title())

        # Icon (if available)
        icon_path = get_icon_path(self.selected_taxon.iconic_taxon_id)
        if icon_path:
            item.add_widget(ImageLeftWidget(source=icon_path))
        self.basic_info.add_widget(item)

        # Common name (if available)
        if self.selected_taxon.common_name:
            self.basic_info.add_widget(
                OneLineListItem(text=self.selected_taxon.common_name))

        # Basic info box: Other attrs
        for k in ['id', 'is_active', 'observations_count', 'complete_species_count']:
            label = k.title().replace('_', ' ')
            value = self.selected_taxon.json.get(k)
            item = OneLineListItem(text=f'{label}: {value}')
            self.basic_info.add_widget(item)

        # Taxonomy
        self.ancestors.text =\
            '\n' + '\n'.join([f'{t.rank}: {t.name}' for t in self.selected_taxon.ancestors]) + '\n\n'
        self.children.text = \
            '\n'.join([f'{t.rank}: {t.name}' for t in self.selected_taxon.children])
