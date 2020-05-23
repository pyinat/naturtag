from logging import getLogger
from os.path import join
import webbrowser

from kivy.uix.image import AsyncImage
from kivymd.uix.imagelist import SmartTile
from kivymd.uix.list import OneLineListItem, TwoLineAvatarListItem, ImageLeftWidget

from pyinaturalist.node_api import get_taxa_autocomplete
from naturtag.ui.autocomplete import AutocompleteSearch
from naturtag.models import Taxon
from naturtag.constants import ICONS_DIR, ICONIC_TAXA
from naturtag.ui.thumbnails import get_thumbnail_if_exists, cache_async_thumbnail

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


def get_iconic_taxon_path(id):
    if id not in ICONIC_TAXA:
        return None
    return join(ICONS_DIR, f'{ICONIC_TAXA[id]}.png')


def get_iconic_taxa_icons():
    return [IconicTaxaIcon(source=get_iconic_taxon_path(id)) for id in ICONIC_TAXA]


class IconicTaxaIcon(SmartTile):
    box_color = (0, 0, 0, 0)


class CachedAsyncImage(AsyncImage):
    """ AsyncImage which, once loaded, caches the image for future use """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.has_thumbnail = False

    def _load_source(self, *args):
        # Before downloading remote image, first check for existing thumbnail
        thumbnail_path = get_thumbnail_if_exists(self.source)
        if thumbnail_path:
            self.has_thumbnail = True
            self.source = thumbnail_path
        super()._load_source(*args)

    def on_load(self, *args):
        """ After loading, cache the downloaded image for future use, if not previously done """
        if self._coreimage.image.texture and not self.has_thumbnail:
            cache_async_thumbnail(self, large=True)


class TaxonSearchController:
    """ Controller class to manage taxon search and display """
    def __init__(self, screen):
        self.screen = screen
        self.taxon_search_input = screen.taxon_search_input
        self.taxon_id_input = screen.taxon_id_input
        self.selected_taxon_photo = screen.selected_taxon_photo
        self.selected_taxon_ancestors = screen.selected_taxon_ancestors
        self.selected_taxon_children = screen.selected_taxon_children
        self.iconic_taxa = screen.iconic_taxa

        self.taxon_search_input.selection_callback = self.handle_selection

        # Set 'Categories' (iconic taxa) icons
        for icon in get_iconic_taxa_icons():
            self.iconic_taxa.add_widget(icon)

        self.selected_taxon = None
        self.selected_observation = None

    def handle_selection(self, metadata):
        """ Handle selecting a taxon from autocomplete dropdown """
        self.select_taxon(json_result=metadata)

    # TODO: add more info, make link clickable, make this not look terrible
    # TODO: This is a lot of info... Taxon info should probably be its own class
    # TODO: Cache default_photo.square_url for display in autocomplete dropdown
    def select_taxon(self, json_result=None, id=None):
        """ Update taxon info display by either ID, partial record, or complete record """
        logger.info(f'Selecting taxon: {id or json_result["id"]}')
        self.screen.selected_taxon_basic_info.clear_widgets()
        self.selected_taxon = Taxon(json_result=json_result, id=id)
        self.taxon_id_input = id

        # Photo
        if self.selected_taxon.photo_url:
            self.selected_taxon_photo.source = self.selected_taxon.photo_url

        # Link
        self.screen.selected_taxon_link_button.bind(
            on_release=lambda *x: webbrowser.open(self.selected_taxon.link))
        self.screen.selected_taxon_link_button.tooltip_text = self.selected_taxon.link

        # Basic info box: Name, rank
        item = TwoLineAvatarListItem(
            text=self.selected_taxon.name, secondary_text=self.selected_taxon.rank.title())

        # Icon (if available)
        icon_path = get_iconic_taxon_path(self.selected_taxon.iconic_taxon_id)
        if icon_path:
            item.add_widget(ImageLeftWidget(source=icon_path))
        self.screen.selected_taxon_basic_info.add_widget(item)

        # Common name (if available)
        common_name = self.selected_taxon.json.get('preferred_common_name')
        if common_name:
            self.screen.selected_taxon_basic_info.add_widget(OneLineListItem(text=common_name))

        # Basic info box: Other attrs
        for k in ['id', 'is_active', 'observations_count', 'complete_species_count']:
            label = k.title().replace('_', ' ')
            value = self.selected_taxon.json.get(k)
            item = OneLineListItem(text=f'{label}: {value}')
            self.screen.selected_taxon_basic_info.add_widget(item)

        # Taxonomy
        self.selected_taxon_ancestors.text =\
            '\n' + '\n'.join([f'{t.rank}: {t.name}' for t in self.selected_taxon.ancestors]) + '\n\n'
        self.selected_taxon_children.text = \
            '\n'.join([f'{t.rank}: {t.name}' for t in self.selected_taxon.children])


class ObservationSearchController:
    """ Controller class to manage observation search and display """
    def __init__(self, screen):
        self.screen = screen
