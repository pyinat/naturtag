from abc import abstractmethod
from logging import getLogger
from queue import Queue
from threading import Event, Thread
from time import sleep

logger = getLogger().getChild(__name__)


class BackgroundThread(Thread):
    """A "consumer" thread for loading data from a queue"""

    def __init__(self):
        super().__init__()
        self.queue = Queue()
        self._stop_event = Event()

    def stop(self):
        if self.queue.qsize() > 0:
            logger.info(f'BackgroundLoader: Canceling {self.queue.qsize()} tasks')
        self.queue.queue.clear()
        self._stop_event.set()
        self.join()

    def run(self):
        while True:
            if self._stop_event.is_set():
                break
            elif not self.queue.empty():
                queue_item = self.queue.get()
                self.process_queue_item(queue_item)
                self.queue.task_done()
            else:
                sleep(0.2)

    @abstractmethod
    def process_queue_item(self, queue_item):
        """Process an item from the queue. Must be implemented by subclasses."""
