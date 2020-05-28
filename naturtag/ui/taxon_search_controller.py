from logging import getLogger
import webbrowser

from kivymd.uix.list import OneLineListItem, ThreeLineAvatarListItem, ImageLeftWidget

from pyinaturalist.node_api import get_taxa_autocomplete
from naturtag.constants import ICONIC_TAXA
from naturtag.models import Taxon, get_icon_path
from naturtag.ui import get_app_settings
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
        self.taxon_history = get_app_settings().taxon_history
        self.taxon_frequency = get_app_settings().taxon_frequency

        # Search inputs
        self.taxon_id_input = screen.taxon_id_input
        self.taxon_id_input.bind(on_text_validate=self.handle_input_id)
        self.taxon_search_input = screen.taxon_search_input
        self.taxon_search_input.selection_callback = self.handle_selection

        # Other Controls
        self.taxon_link = screen.selected_taxon_link_button
        self.taxon_parent_button = screen.taxon_parent_button
        self.taxon_parent_button.bind(on_release=lambda x: self.select_taxon(x.taxon.parent))

        # Outputs
        self.selected_taxon = None
        self.taxon_photo = screen.selected_taxon_photo
        self.taxon_ancestors = screen.taxonomy_section.ids.taxon_ancestors
        self.taxon_children = screen.taxonomy_section.ids.taxon_children
        self.basic_info = self.screen.basic_info_section

        # Set 'Categories' (iconic taxa) icons
        for id in ICONIC_TAXA:
            icon = IconicTaxaIcon(id)
            icon.bind(on_release=lambda x: self.select_taxon(id=x.taxon_id))
            self.screen.iconic_taxa.add_widget(icon)

    def handle_selection(self, metadata):
        """ Handle selecting a taxon from autocomplete dropdown """
        self.select_taxon(taxon_dict=metadata)

    def handle_input_id(self, input):
        self.select_taxon(id=int(input.text))

    def select_taxon(self, taxon_obj=None, taxon_dict=None, id=None):
        """ Update taxon info display by either object, ID, partial record, or complete record """
        if not any([taxon_obj, taxon_dict, id]):
            return
        if not taxon_obj:
            taxon_obj = Taxon.from_dict(taxon_dict) if taxon_dict else  Taxon.from_id(id)

        logger.info(f'Loading from: {[taxon_obj, taxon_dict, id]}')

        self.basic_info.clear_widgets()
        self.selected_taxon = taxon_obj
        self.taxon_id_input = self.selected_taxon.id
        self.taxon_history.append(self.selected_taxon.id)

        logger.info(f'Selecting taxon: {self.selected_taxon.id}')
        self.load_photo_section()
        self.load_basic_info_section()
        self.load_taxonomy_section()

    def load_photo_section(self):
        """ Load taxon photo + links """
        logger.info('Loading photo section')
        if self.selected_taxon.photo_url:
            self.taxon_photo.source = self.selected_taxon.photo_url
        self.taxon_link.bind(on_release=lambda *x: webbrowser.open(self.selected_taxon.link))
        self.taxon_link.tooltip_text = self.selected_taxon.link
        self.taxon_link.disabled = False

        # Configure 'View parent' button
        if self.selected_taxon.parent:
            self.taxon_parent_button.disabled = False
            self.taxon_parent_button.taxon = self.selected_taxon
            self.taxon_parent_button.tooltip_text = f'Go to {self.selected_taxon.parent.name}'
        else:
            self.taxon_parent_button.disabled = True
            self.taxon_parent_button.tooltip_text = ''

    def load_basic_info_section(self):
        """ Load basic info for the currently selected taxon """
        # Basic info box: Name, rank
        logger.info('Loading basic info section')
        item = ThreeLineAvatarListItem(
            text=self.selected_taxon.name,
            secondary_text=self.selected_taxon.rank.title(),
            tertiary_text=self.selected_taxon.preferred_common_name,
        )

        # Icon (if available)
        icon_path = get_icon_path(self.selected_taxon.iconic_taxon_id)
        if icon_path:
            item.add_widget(ImageLeftWidget(source=icon_path))
        self.basic_info.add_widget(item)

        # Basic info box: Other attrs
        for k in ['id', 'is_active', 'observations_count', 'complete_species_count']:
            label = k.title().replace('_', ' ')
            value = getattr(self.selected_taxon, k)
            item = OneLineListItem(text=f'{label}: {value}')
            self.basic_info.add_widget(item)

    def load_taxonomy_section(self):
        """ Populate ancestors and children for the currently selected taxon """
        logger.info('Loading ancestors')
        self.taxon_ancestors.clear_widgets()
        for taxon in self.selected_taxon.parent_taxa:
            self.taxon_ancestors.add_widget(self._get_list_item(taxon))

        # TODO: This can take awhile if there are lots of children; make these async calls?
        logger.info('Loading children')
        self.taxon_children.clear_widgets()
        for taxon in self.selected_taxon.child_taxa:
            self.taxon_children.add_widget(self._get_list_item(taxon))

    def _get_list_item(self, taxon):
        return TaxonListItem(taxon, lambda x: self.select_taxon(x.taxon))
