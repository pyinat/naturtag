from logging import getLogger
from os.path import join
import webbrowser

from kivymd.uix.list import OneLineListItem, TwoLineAvatarListItem, ThreeLineAvatarListItem, ImageLeftWidget

from pyinaturalist.node_api import get_taxa_autocomplete
from naturtag.constants import ICONIC_TAXA
from naturtag.models import Taxon, get_icon_path
from naturtag.ui.autocomplete import AutocompleteSearch
from naturtag.ui.image import IconicTaxaIcon, TaxonListItem

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
        self.taxon_link = screen.selected_taxon_link_button
        self.taxon_ancestors = screen.taxonomy_section.ids.taxon_ancestors
        self.taxon_children = screen.taxonomy_section.ids.taxon_children
        self.basic_info = self.screen.basic_info_section

        # Set 'Categories' (iconic taxa) icons
        for id in ICONIC_TAXA:
            icon = IconicTaxaIcon(source=get_icon_path(id))
            self.screen.iconic_taxa.add_widget(icon)

    def handle_selection(self, metadata):
        """ Handle selecting a taxon from autocomplete dropdown """
        self.select_taxon(json_result=metadata)

    def select_taxon(self, taxon_obj=None, json_result=None, id=None):
        """ Update taxon info display by either object, ID, partial record, or complete record """
        self.basic_info.clear_widgets()
        self.selected_taxon = taxon_obj or Taxon(json_result=json_result, id=id)
        self.taxon_id_input = self.selected_taxon.id
        logger.info(f'Selecting taxon: {self.selected_taxon.id}')
        self.load_photo_section()
        self.load_basic_info_section()
        self.load_taxonomy_section()

    def load_photo_section(self):
        """ Load taxon photo + link to iNaturalist taxon page """
        if self.selected_taxon.photo_url:
            self.taxon_photo.source = self.selected_taxon.photo_url
        self.taxon_link.bind(
            on_release=lambda *x: webbrowser.open(self.selected_taxon.link))
        self.taxon_link.tooltip_text = self.selected_taxon.link

    def load_basic_info_section(self):
        """ Load basic info for the currently selected taxon """
        # Basic info box: Name, rank
        item = ThreeLineAvatarListItem(
            text=self.selected_taxon.name,
            secondary_text=self.selected_taxon.rank.title(),
            tertiary_text=self.selected_taxon.common_name,
        )

        # Icon (if available)
        icon_path = get_icon_path(self.selected_taxon.iconic_taxon_id)
        if icon_path:
            item.add_widget(ImageLeftWidget(source=icon_path))
        self.basic_info.add_widget(item)

        # Basic info box: Other attrs
        for k in ['id', 'is_active', 'observations_count', 'complete_species_count']:
            label = k.title().replace('_', ' ')
            value = self.selected_taxon.json.get(k)
            item = OneLineListItem(text=f'{label}: {value}')
            self.basic_info.add_widget(item)

    def load_taxonomy_section(self):
        """ Populate ancestors and children for the currently selected taxon """
        self.taxon_ancestors.clear_widgets()
        for taxon in self.selected_taxon.ancestors:
            self.taxon_ancestors.add_widget(self._get_list_item(taxon))

        self.taxon_children.clear_widgets()
        for taxon in self.selected_taxon.children:
            self.taxon_children.add_widget(self._get_list_item(taxon))

    def _get_list_item(self, taxon):
        return TaxonListItem(taxon, lambda x: self.select_taxon(x.taxon))
