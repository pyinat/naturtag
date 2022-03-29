import asyncio
from logging import getLogger
from time import time
from typing import Any, Callable, Iterable

from kivy.clock import Clock
from kivy.event import EventDispatcher
from kivy.uix.widget import Widget

REPORT_RATE = 1 / 30  # Report progress to UI at 30 FPS
logger = getLogger().getChild(__name__)


class BatchLoader(EventDispatcher):
    """Runs batches of IO-bound tasks asynchronously, with periodic progress updates

    Events:
        on_progress: Called periodically to report progress to the UI
        on_load: Called when a work item is processed
        on_complete: Called when all work items are processed
    """

    def __init__(self, worker_callback: Callable, **kwargs):
        """
        Args:
            runner_callback: Callback for main event loop entry point
            worker_callback: Callback to process work items
            loop: Event loop to use (separate from main kivy event loop)
        """
        self.register_event_type('on_progress')
        self.register_event_type('on_load')
        self.register_event_type('on_complete')
        super().__init__(**kwargs)

        self.items_complete = None
        self.lock = asyncio.Lock()
        self.loop = asyncio.get_running_loop()
        self.progress_event = None
        self.queues = []
        self.start_time = None
        self.worker_tasks = []
        self.worker_callback = worker_callback

    async def add_batch(self, items: Iterable, **kwargs):
        """Add a batch of items to the queue

        Args:
            items: Items to be passed to worker callback
            kwargs: Optional keyword arguments to be passed to worker callback
        """
        queue = asyncio.Queue()
        for item in items:
            queue.put_nowait((item, kwargs))
        # task = asyncio.create_task(self.worker(queue))
        # self.worker_tasks.append(task)
        self.queues.append(queue)

    async def start(self):
        """Run batches, wait to complete, and gracefully shut down"""
        logger.info(f'BatchLoader: Starting {len(self.queues)} batches')
        for queue in self.queues:
            task = asyncio.create_task(self.worker(queue))
            self.worker_tasks.append(task)
        self.start_progress()

        await self.join()
        self.stop_progress()
        self.dispatch('on_complete', None)

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
        """Safely stop all running tasks"""
        logger.info(f'BatchLoader: Stopping {len(self.worker_tasks)} workers')
        self.stop_progress()
        for task in self.worker_tasks:
            task.cancel()
        await asyncio.gather(*self.worker_tasks, return_exceptions=True)

    def start_progress(self):
        """Schedule event to periodically report progress"""
        self.start_time = time()
        self.items_complete = 0
        self.progress_event = Clock.schedule_interval(self.report_progress, REPORT_RATE)

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
        if self.progress_event:
            self.progress_event.cancel()
            self.progress_event = None
            logger.info(
                f'BatchLoader: Finished loading {self.items_complete} items '
                f'in {time() - self.start_time:0.2f} seconds'
            )

    # Default handlers
    def on_load(self, *_):
        pass

    def on_complete(self, *_):
        pass

    def on_progress(self, *_):
        pass


class WidgetBatchLoader(BatchLoader):
    """Generic loader for widgets that perform some sort of I/O on initialization"""

    def __init__(self, widget_cls, **kwargs):
        super().__init__(worker_callback=self.load_widget, **kwargs)
        self.widget_cls = widget_cls

    async def load_widget(self, item: Any, parent: Widget = None, **kwargs) -> Widget:
        """Load information for a new widget"""
        logger.debug(f'BatchLoader: Processing item: {item}')
        widget = self.widget_cls(item, **kwargs)
        if parent:
            parent.add_widget(widget)
        await self.increment_progress()
        return widget
