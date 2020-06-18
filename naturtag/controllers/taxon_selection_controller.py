import asyncio
from collections import OrderedDict
from logging import getLogger
from time import time

from kivy.clock import Clock

from kivymd.uix.progressbar import MDProgressBar

from naturtag.app import get_app
from naturtag.constants import MAX_DISPLAY_HISTORY
# from naturtag.controllers.background_loader_pool import BackgroundLoader
from naturtag.controllers.batch_loader import BatchLoader, SleepyBatchLoader, TaxonBatchLoader
from naturtag.controllers.controller import Controller
from naturtag.widgets import StarButton, TaxonListItem

logger = getLogger().getChild(__name__)


# TODO: Better name for this? Maybe 'TaxonQuickAccessController'?
class TaxonSelectionController(Controller):
    """ Controller class to manage selecting stored taxa """
    def __init__(self, screen):
        super().__init__(screen)
        # Tab references
        self.history_tab = screen.history_tab
        self.frequent_tab = screen.frequent_tab
        self.starred_tab = screen.starred_tab
        self.status_bar = screen.status_bar

        # Context menu
        self.context_menu = screen.context_menu
        self.context_menu.ids.move_to_top_ctx.bind(on_release=self.move_starred_to_top)

        # Various taxon lists
        self.taxon_history_ids = []
        self.taxon_history_map = {}
        self.taxon_history_list = screen.history_tab.ids.taxon_history_list
        self.starred_taxa_ids = []
        self.starred_taxa_map = {}
        self.starred_taxa_list = screen.starred_tab.ids.starred_taxa_list
        self.frequent_taxa_ids = {}
        self.frequent_taxa_list = screen.frequent_tab.ids.frequent_taxa_list
        self.frequent_taxa_list.sort_key = self.get_frequent_taxon_idx

    def post_init(self):
        # Clock.schedule_once(lambda *x: self.init_stored_taxa(), 2)
        # Clock.schedule_once(lambda *x: asyncio.run(self.test_loader()), 2)
        Clock.schedule_once(lambda *x: asyncio.run(self.init_stored_taxa()), 2)

    async def test_loader(self):
        self.progress_bar = MDProgressBar(max=1000)
        self.status_bar.add_widget(self.progress_bar)

        def update_progress(obj, value):
            print(value)
            self.progress_bar.value = value

        loader = SleepyBatchLoader()

        def load_complete(*args):
            print('Done loading!')
            self.progress_bar.color = .1, .8, .1, 1

        loader.bind(on_progress=update_progress)
        loader.bind(on_complete=load_complete)
        loader.bind(on_load=lambda *x: print('Loaded', x))

        await loader.add_batch((0.012 for _ in range(250)), key='batch 1')
        await loader.add_batch((0.014 for _ in range(250)), key='batch 2')
        await loader.add_batch((0.016 for _ in range(250)), key='batch 3')
        await loader.add_batch((0.018 for _ in range(250)), key='batch 4')

    async def init_stored_taxa(self):
        """ Load taxon history, starred, and frequently viewed items """
        logger.info('Loading stored taxa')
        stored_taxa = get_app().stored_taxa
        self.taxon_history_ids, self.starred_taxa_ids, self.frequent_taxa_ids = stored_taxa

        unique_history = list(OrderedDict.fromkeys(self.taxon_history_ids[::-1]))[:MAX_DISPLAY_HISTORY]
        top_frequent_ids = list(self.frequent_taxa_ids.keys())[:MAX_DISPLAY_HISTORY]
        total_taxa = sum(map(len, (unique_history, self.starred_taxa_ids, top_frequent_ids)))

        self.progress_bar = MDProgressBar(max=total_taxa)
        self.status_bar.add_widget(self.progress_bar)

        logger.info(f'Loading {len(self.starred_taxa_ids)} starred taxa')
        for taxon_id in self.starred_taxa_ids:
            self.add_star(taxon_id)

        logger.info(f'Loading {len(top_frequent_ids)} frequently viewed taxa')
        for taxon_id in top_frequent_ids:
            item = get_app().get_taxon_list_item(taxon_id=taxon_id, parent_tab=self.frequent_tab)
            self.frequent_taxa_list.add_widget(item)

        # await asyncio.gather(load_history(), load_starred(), load_frequent())

    def update_history(self, taxon_id: int):
        """ Update history + frequency """
        self.taxon_history_ids.append(taxon_id)

        # If item already exists in history, move it from its previous position to the top
        if taxon_id in self.taxon_history_map:
            item = self.taxon_history_map[taxon_id]
            self.taxon_history_list.remove_widget(item)
        else:
            item = get_app().get_taxon_list_item(taxon_id=taxon_id, parent_tab=self.history_tab)
            self.taxon_history_map[taxon_id] = item

        self.taxon_history_list.add_widget(item, len(self.taxon_history_list.children))
        self.add_frequent_taxon(taxon_id)

    def add_frequent_taxon(self, taxon_id: int):
        self.frequent_taxa_ids.setdefault(taxon_id, 0)
        self.frequent_taxa_ids[taxon_id] += 1
        self.frequent_taxa_list.sort()

    def add_star(self, taxon_id: int):
        """ Add a taxon to Starred list """
        logger.info(f'Adding taxon to starred: {taxon_id}')
        if taxon_id not in self.starred_taxa_ids:
            self.starred_taxa_ids.append(taxon_id)

        item = get_app().get_taxon_list_item(taxon_id=taxon_id, disable_button=True)
        self.bind_star(taxon_id, item)

    def bind_star(self, taxon_id: int, item: TaxonListItem):
        """ Bind click events on a starred taxon list item, including an X (remove) button """
        item.bind(on_touch_down=self.on_starred_taxon_click)
        remove_button = StarButton(taxon_id, icon='close')
        remove_button.bind(on_release=lambda x: self.remove_star(x.taxon_id))
        item.add_widget(remove_button)
        self.starred_taxa_map[taxon_id] = item
        self.starred_taxa_list.add_widget(item, len(self.starred_taxa_list.children))

    # TODO: Also remove star from info section if this taxon happens to be currently selected
    def remove_star(self, taxon_id: int):
        """ Remove a taxon from Starred list """
        logger.info(f'Removing taxon from starred: {taxon_id}')
        if taxon_id in self.starred_taxa_map:
            item = self.starred_taxa_map.pop(taxon_id)
            self.starred_taxa_ids.remove(taxon_id)
            self.starred_taxa_list.remove_widget(item)

    def is_starred(self, taxon_id: int) -> bool:
        """ Check if the specified taxon is in the Starred list """
        return taxon_id in self.starred_taxa_map

    def on_starred_taxon_click(self, instance, touch):
        """ Event handler for clicking a item from starred taxa list """
        if not instance.collide_point(*touch.pos):
            return
        # Right-click: Open context menu
        elif touch.button == 'right':
            self.context_menu.show(*get_app().root_window.mouse_pos)
            self.context_menu.ref = instance
            # self.context_menu.ids.view_taxon_ctx.disabled = not instance.metadata.taxon_id
        # Middle-click: remove item
        elif touch.button == 'middle':
            self.remove_star(instance.taxon.id)
        # Left-cliok: select taxon
        else:
            get_app().select_taxon(instance.taxon)

    def move_starred_to_top(self, instance):
        """ Move a starred taxon to the top of the list, both in the UI and in persisted list """
        lst = self.starred_taxa_ids
        lst.append(lst.pop(lst.index(instance.taxon_id)))
        item = self.starred_taxa_map[instance.taxon_id]
        self.starred_taxa_list.remove_widget(item)
        self.starred_taxa_list.add_widget(item, len(self.starred_taxa_list.children))

    def get_frequent_taxon_idx(self, list_item) -> int:
        """ Get sort index for frequently viewed taxa (by number of views, descending) """
        num_views = self.frequent_taxa_ids.get(list_item.taxon.id, 0)
        return num_views * -1  # Effectively the same as reverse=True
