import asyncio
from logging import getLogger
from threading import Thread
from time import time
from typing import List, Dict, Callable, Any, Union

from kivy.clock import mainthread, Clock
from kivy.event import EventDispatcher
from kivy.uix.widget import Widget

from naturtag.app import get_app
from naturtag.models import Taxon
from naturtag.widgets import TaxonListItem

REPORT_RATE = 1/30  # Report progress to UI at 30 FPS
logger = getLogger().getChild(__name__)


class BatchRunner(EventDispatcher):
    """ Runs batches of tasks asynchronously in a separate thread from the main GUI thread

    Events:
        on_progress: Called periodically to report progress
        on_load: Called when a work item is processed
        on_complete: Called when all work items are processed
    """
    def __init__(self, runner_callback: Callable, worker_callback: Callable, **kwargs):
        """
        Args:
            runner_callback: Callback for main event loop entry point
            worker_callback: Callback to process work items
        """
        # Schedule all events to run on the main thread
        self.dispatch = mainthread(self.dispatch)
        self.register_event_type('on_progress')
        self.register_event_type('on_load')
        self.register_event_type('on_complete')
        super().__init__(**kwargs)

        self.loop = None
        self.thread = None
        self.queues = []
        self.runner_callback = runner_callback
        self.worker_callback = worker_callback

    async def add_batch(self, items: List, **kwargs: Dict):
        """ Add a batch of items to the queue (from another thread)

        Args:
            items: Items to be passed to worker callback
            kwargs: Optional keyword arguments to be passed to worker callback

        """
        def _add_batch():
            queue = asyncio.Queue()
            for item in items:
                queue.put_nowait((item, kwargs))
            self.queues.append(queue)
            asyncio.create_task(self.worker(queue))

        while not self.loop:
            await asyncio.sleep(0.05)
        self.loop.call_soon_threadsafe(_add_batch)

    def start(self):
        """ Start the background loader event loop and thread """
        def start_loop():
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            self.loop.create_task(self.runner_callback())
            self.loop.run_forever()

        self.thread = Thread(target=start_loop, daemon=True)
        self.thread.start()

    async def worker(self, queue: asyncio.Queue):
        """ Run a worker to process items on a single queue """
        while True:
            item, kwargs = await queue.get()
            results = await self.worker_callback(item, **kwargs)
            self.dispatch('on_load', results)
            queue.task_done()

    async def join(self):
        """ Wait for all queues to be initialized and then processed """
        while not self.queues:
            await asyncio.sleep(0.1)
        for queue in self.queues:
            await queue.join()
        self.queues = []

    def stop(self):
        """ Safely stop the event loop and thread """
        pending = asyncio.all_tasks(loop=self.loop)
        print('Processed:', self.items_complete, 'Remaining:', sum(q.qsize() for q in self.queues))
        for task in pending:
            print('Canceling:', task)
            task.cancel()
        self.loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        self.loop.close()
        self.thread.join()

    # Default handlers
    def on_load(self, *_): pass
    def on_complete(self, *_): pass
    def on_progress(self, *_): pass


class BatchLoader(BatchRunner):
    """ Loads batches of items with periodic progress updates sent back to the UI """
    def __init__(self,  **kwargs):
        super().__init__(runner_callback=self.run, **kwargs)
        self.event = None
        self.items_complete = None
        self.start_time = None
        self.lock = asyncio.Lock()
        self.start()

    async def run(self):
        """ Run batches, wait to complete, and gracefully shut down """
        self.start_progress()
        await self.join()
        self.stop_progress()
        self.dispatch('on_complete', None)
        self.stop()

    def start_progress(self):
        """ Schedule event to periodically report progress """
        self.start_time = time()
        self.items_complete = 0
        self.event = Clock.schedule_interval(self.report_progress, REPORT_RATE)

    async def increment_progress(self):
        """ Async-safe function to increment progress """
        async with self.lock:
            self.items_complete += 1

    def report_progress(self, *_):
        """ Report how many items have been loaded so far """
        self.dispatch('on_progress', self.items_complete)

    def stop_progress(self):
        """ Unschedule progress event and log total execution time """
        self.event.cancel()
        logger.info(
            f'Finished loading {self.items_complete} items '
            f'in {time() - self.start_time} seconds'
        )

    # TODO: Not yet working
    def cancel(self):
        """ Safely stop the event loop and thread (from another thread) """
        self.loop.call_soon_threadsafe(self.stop_progress)
        for task in asyncio.all_tasks(loop=self.loop):
            task.cancel()


class WidgetBatchLoader(BatchLoader):
    """ Generic loader for widgets that perform some sort of I/O on initialization  """
    def __init__(self, widget_cls, **kwargs):
        super().__init__(worker_callback=self.load_widget, **kwargs)
        self.widget_cls = widget_cls

    async def load_widget(self, item: Any, parent: Widget = None, **kwargs) -> Widget:
        """ Load information for a new widget """
        widget = self.widget_cls(item, **kwargs)
        self.add_widget(widget, parent)
        await self.increment_progress()
        return widget

    @mainthread
    def add_widget(self, widget: Widget, parent: Widget):
        """ Add a widget to its parent on the main thread """
        if parent:
            parent.add_widget(widget)


class TaxonBatchLoader(WidgetBatchLoader):
    """ Loads batches of TaxonListItems """
    def __init__(self, **kwargs):
        super().__init__(widget_cls=TaxonListItem, **kwargs)

    def add_widget(self, widget: Widget, parent: Widget):
        """ Add a TaxonListItem to its parent list and bind its click event """
        super().add_widget(widget, parent)
        mainthread(get_app().bind_to_select_taxon)(widget)
