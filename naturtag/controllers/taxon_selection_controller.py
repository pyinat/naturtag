import asyncio
from logging import getLogger

from naturtag.app import get_app
from naturtag.widgets import StarButton

logger = getLogger().getChild(__name__)


# TODO: Better name for this?
class TaxonSelectionController:
    """ Controller class to manage selecting stored taxa """
    def __init__(self, screen):
        # Tab references
        self.history_tab = screen.history_tab
        self.frequent_tab = screen.frequent_tab
        self.starred_tab = screen.starred_tab

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
        asyncio.run(self.init_stored_taxa())

    async def init_stored_taxa(self):
        """ Load taxon history, starred, and frequently viewed items """
        logger.info('Loading stored taxa')
        stored_taxa = get_app().stored_taxa
        self.taxon_history_ids, self.starred_taxa_ids, self.frequent_taxa_ids = stored_taxa

        async def load_history():
            logger.info(f'Loading {len(self.taxon_history_ids)} (unique) taxa from history')
            for taxon_id in self.taxon_history_ids[::-1]:
                if taxon_id not in self.taxon_history_map:
                    item = get_app().get_taxon_list_item(
                        taxon_id=taxon_id, parent_tab=self.history_tab)
                    self.taxon_history_list.add_widget(item)
                    self.taxon_history_map[taxon_id] = item

        async def load_starred():
            logger.info(f'Loading {len(self.starred_taxa_ids)} starred taxa')
            for taxon_id in self.starred_taxa_ids:
                self.add_star(taxon_id)

        async def load_frequent():
            logger.info(f'Loading {len(self.frequent_taxa_ids)} frequently viewed taxa')
            for taxon_id in self.frequent_taxa_ids.keys():
                item = get_app().get_taxon_list_item(
                    taxon_id=taxon_id, parent_tab=self.frequent_tab)
                self.frequent_taxa_list.add_widget(item)

        await asyncio.gather(load_history(), load_starred(), load_frequent())

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

        item = get_app().get_taxon_list_item(
            taxon_id=taxon_id,
            parent_tab=self.starred_tab,
            disable_button=True,
        )
        item.bind(on_touch_down=self.on_starred_taxon_click)
        # Add X (remove) button
        remove_button = StarButton(taxon_id, icon='close')
        remove_button.bind(on_release=lambda x: self.remove_star(x.taxon_id))
        item.add_widget(remove_button)
        self.starred_taxa_map[taxon_id] = item
        self.starred_taxa_list.add_widget(item, len(self.starred_taxa_list.children))

    def remove_star(self, taxon_id: int):
        """ Remove a taxon from Starred list """
        logger.info(f'Removing taxon from starred: {taxon_id}')
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
