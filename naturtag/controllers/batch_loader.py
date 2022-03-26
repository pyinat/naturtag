import asyncio
from logging import getLogger
from threading import Thread
from time import time
from typing import Any, Callable, Iterable

from kivy.clock import Clock, mainthread
from kivy.event import EventDispatcher
from kivy.uix.widget import Widget

from naturtag.app import get_app
from naturtag.inat_metadata import get_taxon
from naturtag.widgets import ImageMetaTile, TaxonListItem

REPORT_RATE = 1 / 30  # Report progress to UI at 30 FPS
logger = getLogger().getChild(__name__)


class BatchRunner(EventDispatcher):
    """Runs batches of IO-bound tasks asynchronously, in a separate thread from the main UI thread

    Events:
        on_progress: Called periodically to report progress
        on_load: Called when a work item is processed
        on_complete: Called when all work items are processed
    """

    def __init__(self, runner_callback: Callable, worker_callback: Callable, loop=None, **kwargs):
        """
        Args:
            runner_callback: Callback for main event loop entry point
            worker_callback: Callback to process work items
            loop: Event loop to use (separate from main kivy event loop)
        """
        # Schedule all events to run on the main thread
        self.dispatch = mainthread(self.dispatch)
        self.register_event_type('on_progress')
        self.register_event_type('on_load')
        self.register_event_type('on_complete')
        super().__init__(**kwargs)

        self.loop = loop or get_app().bg_loop
        self.thread = None
        self.queues = []
        self.worker_tasks = []
        self.runner_callback = runner_callback
        self.worker_callback = worker_callback

    def add_batch(self, items: Iterable, **kwargs):
        """Add a batch of items to the queue (from another thread)

        Args:
            items: Items to be passed to worker callback
            kwargs: Optional keyword arguments to be passed to worker callback
        """

        def _add_batch():
            queue = asyncio.Queue()
            for item in items:
                queue.put_nowait((item, kwargs))
            self.queues.append(queue)

        self.loop.call_soon_threadsafe(_add_batch)

    def start_thread(self):
        """Start the background loader event loop in a new thread"""

        def start_wrapper():
            asyncio.run_coroutine_threadsafe(self.start_workers(), self.loop)

        Thread(target=start_wrapper).start()

    async def start_workers(self):
        """Start running workers in the the background loader event loop"""
        logger.info(f'BatchRunner: Starting {len(self.queues)} batches')
        for queue in self.queues:
            task = asyncio.create_task(self.worker(queue))
            self.worker_tasks.append(task)
        await self.runner_callback()

    async def worker(self, queue: asyncio.Queue):
        """Run a worker to process items on a single queue"""
        while True:
            item, kwargs = await queue.get()
            results = await self.worker_callback(item, **kwargs)
            self.dispatch('on_load', results)
            queue.task_done()
            await asyncio.sleep(0)

    async def join(self):
        """Wait for all queues to be initialized and then processed"""
        while not self.queues:
            await asyncio.sleep(0.1)
        for queue in self.queues:
            await queue.join()

    async def stop(self):
        """Safely stop the event loop"""
        logger.info(f'BatchRunner: stopping {len(self.worker_tasks)} workers')
        for task in self.worker_tasks:
            task.cancel()
        self.loop.run_until_complete(asyncio.gather(*self.worker_tasks, return_exceptions=True))

    # Default handlers
    def on_load(self, *_):
        pass

    def on_complete(self, *_):
        pass

    def on_progress(self, *_):
        pass


class BatchLoader(BatchRunner):
    """Loads batches of items with periodic progress updates sent back to the UI"""

    def __init__(self, **kwargs):
        super().__init__(runner_callback=self.run, **kwargs)
        self.event = None
        self.items_complete = None
        self.start_time = None
        self.lock = asyncio.Lock()

    async def run(self):
        """Run batches, wait to complete, and gracefully shut down"""
        self.start_progress()
        await self.join()
        self.stop_progress()
        self.dispatch('on_complete', None)
        await self.stop()

    def start_progress(self):
        """Schedule event to periodically report progress"""
        self.start_time = time()
        self.items_complete = 0
        self.event = Clock.schedule_interval(self.report_progress, REPORT_RATE)

    async def increment_progress(self):
        """Async-safe function to increment progress"""
        async with self.lock:
            self.items_complete += 1

    def report_progress(self, *_):
        """Report how many items have been loaded so far"""
        self.dispatch('on_progress', self.items_complete)

    def stop_progress(self):
        """Unschedule progress event and log total execution time"""
        self.report_progress()
        if self.event:
            self.event.cancel()
            self.event = None
            logger.info(
                f'BatchLoader: Finished loading {self.items_complete} items '
                f'in {time() - self.start_time:0.2f} seconds'
            )

    def cancel(self):
        """Safely stop the event loop and thread (from another thread)"""
        logger.info(f'BatchLoader: Canceling {len(self.queues)} batches')
        self.loop.call_soon_threadsafe(self.stop_progress)
        asyncio.run_coroutine_threadsafe(self.stop(), self.loop)


class WidgetBatchLoader(BatchLoader):
    """Generic loader for widgets that perform some sort of I/O on initialization"""

    def __init__(self, widget_cls, **kwargs):
        super().__init__(worker_callback=self.load_widget, **kwargs)
        self.widget_cls = widget_cls

    async def load_widget(self, item: Any, parent: Widget = None, **kwargs) -> Widget:
        """Load information for a new widget"""
        logger.debug(f'BatchLoader: Processing item: {item}')
        widget = self.widget_cls(item, **kwargs)
        self.add_widget(widget, parent)

        logger.debug(f'BatchLoader: Item complete: {item}')
        await self.increment_progress()
        return widget

    @mainthread
    def add_widget(self, widget: Widget, parent: Widget):
        """Add a widget to its parent on the main thread"""
        if parent:
            parent.add_widget(widget)


class TaxonBatchLoader(WidgetBatchLoader):
    """Loads batches of TaxonListItems"""

    def __init__(self, **kwargs):
        super().__init__(widget_cls=TaxonListItem, **kwargs)

    async def load_widget(self, item: Any, parent: Widget = None, **kwargs) -> Widget:
        """Fetch a Taxon by ID, add a TaxonListItem to its parent list, and bind its click event"""
        taxon = get_taxon(item)
        widget = await super().load_widget(taxon, parent, **kwargs)
        self.bind_click(widget)
        return widget

    @mainthread
    def bind_click(self, widget):
        get_app().bind_to_select_taxon(widget)


class ImageBatchLoader(WidgetBatchLoader):
    """Loads batches of ImageMetaTiles"""

    def __init__(self, **kwargs):
        super().__init__(widget_cls=ImageMetaTile, **kwargs)

    async def load_widget(self, item: Any, parent: Widget = None, **kwargs) -> Widget:
        """Add an ImageMetaTile to its parent view and bind its click event"""
        widget = await super().load_widget(item, parent, **kwargs)
        self.bind_click(widget)
        return widget

    @mainthread
    def bind_click(self, widget):
        widget.bind(on_touch_down=get_app().image_selection_controller.on_image_click)
