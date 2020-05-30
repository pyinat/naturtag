# TODO: This class has gotten large; split this up into at leeast two modules: taxon_select and taxon_view
from logging import getLogger
import webbrowser

from kivymd.uix.list import OneLineListItem, ThreeLineAvatarIconListItem, ImageLeftWidget, IconRightWidget

from pyinaturalist.node_api import get_taxa_autocomplete
from naturtag.constants import ICONIC_TAXA
from naturtag.models import Taxon, get_icon_path
from naturtag.ui import get_app_settings
from naturtag.ui.autocomplete import AutocompleteSearch
from naturtag.ui.image import IconicTaxaIcon, TaxonListItem
from naturtag.ui.widget_classes import StarButton

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
        self.taxon_id_input = screen.search_tab.ids.taxon_id_input
        self.taxon_id_input.bind(on_text_validate=self.handle_input_id)
        self.taxon_search_input = screen.search_tab.ids.taxon_search_input
        self.taxon_search_input.selection_callback = self.handle_selection

        # Other Controls
        self.taxon_link = screen.taxon_links.ids.selected_taxon_link_button
        self.taxon_parent_button = screen.taxon_links.ids.taxon_parent_button
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
            self.screen.search_tab.ids.iconic_taxa.add_widget(icon)

        # History, frequent, and starred items
        self.taxon_history_map = {}
        self.taxon_history_ids = get_app_settings().taxon_history
        self.taxon_history_list = screen.history_tab.ids.taxon_history_list
        self.frequent_taxa = get_app_settings().frequent_taxa
        self.frequent_taxa_list = screen.frequent_tab.ids.frequent_taxa_list
        self.starred_taxa_map = {}
        self.starred_taxa_ids = get_app_settings().starred_taxa
        self.starred_taxa_list = screen.starred_tab.ids.starred_taxa_list
        self.init_stored_taxa()

    def handle_input_id(self, input):
        self.select_taxon(id=int(input.text))

    def handle_selection(self, metadata: dict):
        """ Handle selecting a taxon from autocomplete dropdown """
        self.select_taxon(taxon_dict=metadata)

    # TODO: Add button to items in starred tab to remove from list (in addition to star next to selected taxon)
    def handle_star(self, button):
        """ Either add or remove a taxon from the starred list """
        if button.is_selected:
            self.add_star(self.selected_taxon.id)
        else:
            self.remove_star(self.selected_taxon.id)

    # TODO: This should be delayed / populated asynchronously
    def init_stored_taxa(self):
        """ Load taxon history, starred, and frequently viewed items """
        for taxon_id in self.taxon_history_ids[::-1]:
            if taxon_id not in self.taxon_history_map:
                item = self._get_list_item(taxon_id=taxon_id)
                self.taxon_history_list.add_widget(item)
                self.taxon_history_map[taxon_id] = item

        for taxon_id in self.starred_taxa_ids[::-1]:
            self.add_star(taxon_id)

        for taxon_id in self.frequent_taxa.keys():
            item = self._get_list_item(taxon_id=taxon_id)
            self.frequent_taxa_list.add_widget(item)

    def update_history(self, taxon_id):
        """ Update history + frequency """
        self.taxon_history_ids.append(self.selected_taxon.id)
        # If item already exists in history, move it from its previous position to the top
        if taxon_id in self.taxon_history_map:
            item = self.taxon_history_map[taxon_id]
            self.taxon_history_list.remove_widget(item)
        else:
            item = self._get_list_item(taxon_id=taxon_id)
            self.taxon_history_map[taxon_id] = item
        self.taxon_history_list.add_widget(item, len(self.taxon_history_list.children))

        # Update frequent items
        # TODO: Re-sort frequent items in UI
        self.frequent_taxa.setdefault(taxon_id, 0)
        self.frequent_taxa[taxon_id] += 1

    def add_star(self, taxon_id):
        logger.info(f'Adding taxon to starred: {taxon_id}')
        item = self._get_list_item(taxon_id=taxon_id)
        if taxon_id not in self.starred_taxa_ids:
            self.starred_taxa_ids.append(taxon_id)
        self.starred_taxa_map[taxon_id] = item
        self.starred_taxa_list.add_widget(item, len(self.starred_taxa_list.children))
        # X button
        remove_button = StarButton(taxon_id, icon='close')
        remove_button.bind(on_release=lambda x: self.remove_star(x.taxon_id))
        item.add_widget(remove_button)

    def remove_star(self, taxon_id):
        logger.info(f'Removing taxon from starred: {taxon_id}')
        item = self.starred_taxa_map.pop(taxon_id)
        self.starred_taxa_ids.remove(taxon_id)
        self.starred_taxa_list.remove_widget(item)

    def select_taxon(self, taxon_obj=None, taxon_dict=None, id=None):
        """ Update taxon info display by either object, ID, partial record, or complete record """
        if not any([taxon_obj, taxon_dict, id]):
            return
        if not taxon_obj:
            taxon_obj = Taxon.from_dict(taxon_dict) if taxon_dict else  Taxon.from_id(id)

        self.basic_info.clear_widgets()
        self.selected_taxon = taxon_obj
        self.taxon_id_input.text = str(self.selected_taxon.id)

        logger.info(f'Taxon: Selecting taxon {self.selected_taxon.id}')
        self.load_photo_section()
        self.load_basic_info_section()
        self.load_taxonomy_section()
        self.update_history(self.selected_taxon.id)

    def load_photo_section(self):
        """ Load taxon photo + links """
        logger.info('Taxon: Loading photo section')
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
        logger.info('Taxon: Loading basic info section')
        item = ThreeLineAvatarIconListItem(
            text=self.selected_taxon.name,
            secondary_text=self.selected_taxon.rank.title(),
            tertiary_text=self.selected_taxon.preferred_common_name,
        )

        # Icon (if available)
        icon_path = get_icon_path(self.selected_taxon.iconic_taxon_id)
        if icon_path:
            item.add_widget(ImageLeftWidget(source=icon_path))
        self.basic_info.add_widget(item)

        # Star
        star_icon = StarButton(
            self.selected_taxon.id, is_selected=self.selected_taxon.id in self.starred_taxa_map)
        star_icon.bind(on_release=self.handle_star)
        item.add_widget(star_icon)

        # Basic info box: Other attrs
        for k in ['id', 'is_active', 'observations_count', 'complete_species_count']:
            label = k.title().replace('_', ' ')
            value = getattr(self.selected_taxon, k)
            item = OneLineListItem(text=f'{label}: {value}')
            self.basic_info.add_widget(item)

    def load_taxonomy_section(self):
        """ Populate ancestors and children for the currently selected taxon """
        logger.info('Taxon: Loading ancestors')
        self.taxon_ancestors.clear_widgets()
        for taxon in self.selected_taxon.parent_taxa:
            self.taxon_ancestors.add_widget(self._get_list_item(taxon))

        # TODO: This can take awhile if there are lots of children; make these async calls?
        logger.info('Taxon: Loading children')
        self.taxon_children.clear_widgets()
        for taxon in self.selected_taxon.child_taxa:
            self.taxon_children.add_widget(self._get_list_item(taxon))

    def _get_list_item(self, taxon=None, taxon_id=None):
        taxon = taxon or Taxon.from_id(taxon_id or self.selected_taxon.id)
        return TaxonListItem(taxon, lambda x: self.select_taxon(x.taxon))
