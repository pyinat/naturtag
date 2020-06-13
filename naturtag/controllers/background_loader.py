from concurrent.futures import ThreadPoolExecutor, as_completed
from logging import getLogger
from time import time

from kivy.clock import mainthread
from kivy.event import EventDispatcher

from kivymd.uix.progressbar import MDProgressBar
from naturtag.app import get_app
from naturtag.models import Taxon
from naturtag.widgets import TaxonListItem

logger = getLogger().getChild(__name__)


class BackgroundLoader(EventDispatcher):
    __events__ = ('on_load',)

    def __init__(self, status_bar, total, **kwargs):
        super().__init__(**kwargs)
        # Schedule all events to run on the main thread
        self.dispatch = mainthread(self.dispatch)

        # Progress bar stuff
        self.start_time = time()
        self.status_bar = status_bar
        self.progress_bar = None
        self.total = total
        self.start_progress()

    @mainthread
    def start_progress(self):
        self.progress_bar = MDProgressBar(max=self.total)
        self.status_bar.add_widget(self.progress_bar)

    @mainthread
    def increment_progress(self):
        self.progress_bar.value += 1

    @mainthread
    def stop_progress(self):
        self.status_bar.remove_widget(self.progress_bar)
        self.progress_bar = None

    def stop(self):
        logger.info(f'Finished loading in {time() - self.start_time} seconds')
        self.start_time = None
        self.stop_progress()

    def load_taxon(self, taxon_id, **kwargs):
        item = TaxonListItem(Taxon.from_id(taxon_id), **kwargs)
        mainthread(get_app().bind_to_select_taxon)(item)
        self.increment_progress()
        return item

    def load_taxa(self, taxon_ids, **kwargs):
        # Using only 1 worker because these are short tasks, and we only need to make them non-blocking
        with ThreadPoolExecutor(max_workers=1) as executor:
            future_taxa = {
                executor.submit(self.load_taxon, taxon_id, **kwargs): taxon_id
                for taxon_id in taxon_ids
            }
            for future in as_completed(future_taxa):
                yield future_taxa[future], future.result()

    def on_load(self, *_):
        pass
