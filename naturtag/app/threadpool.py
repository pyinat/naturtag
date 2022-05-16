"""Adapted from examples in Python & Qt6 by Martin Fitzpatrick"""
from logging import getLogger
from threading import RLock
from typing import Callable

from PySide6.QtCore import QObject, QRunnable, QThreadPool, QTimer, Signal
from PySide6.QtWidgets import QProgressBar

logger = getLogger(__name__)


class ThreadPool(QThreadPool):
    """Thread pool that enqueues jobs to ber run from separate thread(s), and updates a progress
    bar.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.progress = ProgressBar()

    def schedule(self, callback: Callable, *args, **kwargs) -> 'WorkerSignals':
        """Schedule a task to be run by the next available worker thread"""
        self.progress.add()
        worker = Worker(callback, *args, **kwargs)
        worker.signals.progress.connect(self.progress.advance)
        self.start(worker)
        return worker.signals

    def cancel(self):
        """Cancel all enqueued tasks and reset progress bar"""
        if active_threads := self.activeThreadCount() > 0:
            logger.debug(f'Cancelling {active_threads} active threads')
        self.clear()
        self.progress.reset()


class Worker(QRunnable):
    """A worker thread that takes a callback (and optional args/kwargs), and updates progress when
    done.
    """

    def __init__(self, callback: Callable, *args, **kwargs):
        super().__init__()
        self.callback = callback
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

    def run(self):
        try:
            result = self.callback(*self.args, **self.kwargs)
        except Exception as e:
            logger.exception(f'Worker error for {self.callback}({self.args}, {self.kwargs}):')
            self.signals.error.emit(e)
        else:
            self.signals.result.emit(result)
        self.signals.progress.emit()


class WorkerSignals(QObject):
    """Signals used by a worker thread (can't be set directly on a QRunnable)"""

    error = Signal(Exception)
    result = Signal(object)
    progress = Signal()


class ProgressBar(QProgressBar):
    """Shared progress bar, updated by ThreadPool"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setMaximum(0)
        self.setValue(0)
        self.lock = RLock()
        self.reset_timer = QTimer()
        self.reset_timer.timeout.connect(self.reset)

    def add(self, amount: int = 1):
        if not self.isVisible():
            self.setVisible(True)
        self.reset_timer.stop()
        with self.lock:
            self.setMaximum(self.maximum() + amount)

    def advance(self, amount: int = 1):
        with self.lock:
            new_value = min(self.value() + amount, self.maximum())
            self.setValue(new_value)
            if new_value == self.maximum():
                self.schedule_reset()

    def schedule_reset(self):
        """After a delay, if no new tasks have been added, reset and hide the progress bar"""
        logger.debug(f'{self.value()}/{self.maximum()} tasks complete')
        self.reset_timer.start(1000)

    def reset(self):
        self.setVisible(False)
        self.setValue(0)
        self.setMaximum(0)
