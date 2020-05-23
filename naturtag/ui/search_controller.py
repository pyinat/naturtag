from logging import getLogger
from os.path import join

from kivy.uix.image import AsyncImage
from kivymd.uix.imagelist import SmartTile

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


class IconicTaxaIcon(SmartTile):
    box_color = (0, 0, 0, 0)
    def __init__(self, taxon, **kwargs):
        icon_path = join(ICONS_DIR, f'{taxon}.png')
        super().__init__(source=icon_path, **kwargs)


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
        self.selected_taxon_name = screen.selected_taxon_name
        self.iconic_taxa = screen.iconic_taxa

        self.taxon_search_input.selection_callback = self.handle_selection

        # Set 'Categories' (iconic taxa) icons
        for taxon in ICONIC_TAXA.values():
            self.iconic_taxa.add_widget(IconicTaxaIcon(taxon))

        self.selected_taxon = None
        self.selected_observation = None

    def handle_selection(self, metadata):
        """ Handle selecting a taxon from autocomplete dropdown """
        self.select_taxon(json_result=metadata)

    # TODO: add more info, make link clickable, make this not look terrible
    def select_taxon(self, json_result=None, id=None):
        """ Update taxon info display by either ID, partial record, or complete record """
        # TODO: Cache default_photo.square_url for display in autocomplete dropdown
        logger.info(f'Selecting taxon: {id or json_result["id"]}')
        self.selected_taxon = Taxon(json_result=json_result, id=id)
        self.taxon_id_input = id
        if self.selected_taxon.photo_url:
            self.selected_taxon_photo.source = self.selected_taxon.photo_url
        self.selected_taxon_name.text = (
            f'[{self.selected_taxon.id}] {self.selected_taxon.rank.title()}: '
            f'{self.selected_taxon.name}\n'
            f'[ref=https://www.inaturalist.org/taxa/{self.selected_taxon.id}]link[/ref]'
        )


class ObservationSearchController:
    """ Controller class to manage observation search and display """
    def __init__(self, screen):
        self.screen = screen
