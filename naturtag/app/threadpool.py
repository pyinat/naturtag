"""Adapted from examples in Python & Qt6 by Martin Fitzpatrick"""

from collections import defaultdict
from logging import getLogger
from threading import RLock
from typing import Callable, Optional

from PySide6.QtCore import (
    QEasingCurve,
    QObject,
    QPropertyAnimation,
    QRunnable,
    QThread,
    QThreadPool,
    QTimer,
    Signal,
    Slot,
)
from PySide6.QtWidgets import QGraphicsOpacityEffect, QProgressBar
from shiboken6 import isValid

logger = getLogger(__name__)


# TODO: For loading taxa, set/increase progress bar max once up front, instead of once per taxon
class ThreadPool(QThreadPool):
    """Thread pool that enqueues jobs to ber run from separate thread(s), and updates a progress
    bar.
    """

    def __init__(self, num_workers: int = 0, **kwargs):
        super().__init__(**kwargs)
        self.progress = ProgressBar()
        self._group_workers: dict[str, list[QRunnable]] = defaultdict(list)
        self._group_lock = RLock()
        # Keep worker references to prevent premature python GC while queued signals are still live
        self._live_workers: set[BaseWorker] = set()
        if num_workers:
            self.setMaxThreadCount(num_workers)

    def schedule(
        self,
        callback: Callable,
        priority: QThread.Priority = QThread.NormalPriority,
        total_results: Optional[int] = None,
        increment_length: bool = False,
        group: str | None = None,
        **kwargs,
    ) -> 'WorkerSignals':
        """Schedule a task to be run by the next available worker thread"""
        self.progress.add(total_results or 1)
        worker = Worker(callback, increment_length=increment_length, **kwargs)
        worker.signals.on_progress.connect(self.progress.advance)
        self._register_worker(worker, group)
        self.start(worker, priority.value)
        return worker.signals

    def schedule_paginator(
        self,
        callback: Callable,
        priority: QThread.Priority = QThread.NormalPriority,
        total_results: Optional[int] = None,
        group: str | None = None,
        **kwargs,
    ) -> 'WorkerSignals':
        """Schedule a task to be run by the next available worker thread"""
        self.progress.add(total_results or 1)
        worker = PaginatedWorker(callback, **kwargs)
        worker.signals.on_progress.connect(self.progress.advance)
        self._register_worker(worker, group)
        self.start(worker, priority.value)
        return worker.signals

    def _register_worker(self, worker: 'BaseWorker', group: str | None):
        """Pin worker to prevent GC, and track group membership."""
        self._live_workers.add(worker)
        worker.signals.on_finished.connect(
            lambda w=worker: self._live_workers.discard(w) if isValid(self) else None
        )
        if group is not None:
            with self._group_lock:
                self._group_workers[group].append(worker)
            worker.signals.on_finished.connect(
                lambda g=group, w=worker: self._remove_worker(g, w) if isValid(self) else None
            )

    def _remove_worker(self, group: str, worker: QRunnable):
        """Remove a completed worker from group tracking. No-op if already removed by cancel()."""
        with self._group_lock:
            try:
                self._group_workers[group].remove(worker)
            except ValueError:
                pass

    def cancel(self, group: str | None = None):
        """Cancel queued tasks and adjust the progress bar. Currently running tasks will be
        allowed to complete.

        Args:
            group: If provided, only cancel tasks in this group. Otherwise cancel all tasks.
        """
        if group is not None:
            self._cancel_group(group)
            return
        if (active_threads := self.activeThreadCount()) > 0:
            logger.debug(f'Cancelling {active_threads} active threads')
        self.clear()
        self._live_workers.clear()
        self.progress.reset()

    def _cancel_group(self, group: str):
        """Cancel only queued tasks belonging to a specific group."""
        with self._group_lock:
            workers = self._group_workers.pop(group, [])
        cancelled = sum(1 for w in workers if self.tryTake(w))
        if cancelled:
            logger.debug(f'Cancelled {cancelled}/{len(workers)} queued tasks in group {group!r}')
            self.progress.remove(cancelled)


class BaseWorker(QRunnable):
    """Base for all worker types. Subclasses must emit ``on_finished`` as their
    very last signal emission in ``run()``.
    """

    def __init__(self, callback: Callable, **kwargs):
        super().__init__()
        self.setAutoDelete(False)
        self.callback = callback
        self.kwargs = kwargs
        self.signals = WorkerSignals()


class Worker(BaseWorker):
    """A worker thread that takes a callback (and optional args/kwargs), and updates progress when
    done.
    """

    def __init__(self, callback: Callable, increment_length: bool = False, **kwargs):
        super().__init__(callback, **kwargs)
        self.increment_length = increment_length

    def run(self):
        try:
            result = self.callback(**self.kwargs)
        except Exception as e:
            logger.warning('Worker error:', exc_info=True)
            self.signals.on_error.emit(e)
            self.signals.on_progress.emit(1)
        else:
            self.signals.on_result.emit(result)
            increment = len(result) if self.increment_length and isinstance(result, list) else 1
            self.signals.on_progress.emit(increment)
        finally:
            self.signals.on_finished.emit()


class PaginatedWorker(BaseWorker):
    """A worker thread that specifically handles paginated requests via iNatClient/iNatDbClient"""

    def run(self):
        try:
            for next_page in self.callback(**self.kwargs):
                self.signals.on_result.emit(next_page)
                self.signals.on_progress.emit(len(next_page))
        except Exception as e:
            logger.warning('Worker error:', exc_info=True)
            self.signals.on_error.emit(e)
        finally:
            # Always consume the reserved progress slot. If pages were yielded, their
            # advances already exceeded the reservation, so this extra 1 just caps at max.
            self.signals.on_progress.emit(1)
            self.signals.on_complete.emit()
            self.signals.on_finished.emit()


class WorkerSignals(QObject):
    """Signals used by a worker thread (can't be set directly on a QRunnable)"""

    on_error = Signal(Exception)  #: Return exception info on error
    on_result_total = Signal(int)  #: Return total results
    on_result = Signal(object)  #: Return result on completion
    on_progress = Signal(int)  #: Increment progress bar
    on_complete = Signal()  #: Emitted when the worker has finished all work
    on_finished = Signal()  #: Always the last signal emitted; used for lifecycle cleanup


class ProgressBar(QProgressBar):
    """Shared progress bar, updated by ThreadPool"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.setMaximum(0)
        self.setValue(0)
        self.lock = RLock()

        self.reset_timer = QTimer()
        self.reset_timer.timeout.connect(self.reset)
        self.op_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.op_effect)
        self.anim = QPropertyAnimation(self.op_effect, b'opacity')
        self.anim.setEasingCurve(QEasingCurve.InOutCubic)

    @Slot(int)
    def add(self, amount: int = 1):
        if not isValid(self):
            return
        self.fadein()
        with self.lock:
            self.setMaximum(self.maximum() + amount)

    @Slot(int)
    def advance(self, amount: int = 1):
        if not isValid(self):
            return
        with self.lock:
            new_value = min(self.value() + amount, self.maximum())
            self.setValue(new_value)
            if new_value == self.maximum():
                self.schedule_reset()

    def remove(self, amount: int):
        """Decrease maximum by ``amount`` to account for cancelled tasks."""
        with self.lock:
            new_max = max(self.maximum() - amount, self.value())
            self.setMaximum(new_max)
            if self.value() == new_max:
                self.schedule_reset()

    def schedule_reset(self):
        """After a delay, if no new tasks have been added, reset and hide the progress bar"""
        if self.value() > 0:
            self.reset_timer.start(2000)
            self.fadeout()

    def reset(self):
        if not isValid(self):
            return
        logger.debug(f'{self.value()}/{self.maximum()} tasks complete')
        self.reset_timer.stop()
        self.setValue(0)
        self.setMaximum(0)

    def fadeout(self):
        self.anim.stop()
        self.anim.setEndValue(0)
        self.anim.setDuration(2000)
        self.anim.start()

    def fadein(self):
        if self.anim.currentValue() != 1 or self.reset_timer.isActive():
            self.reset_timer.stop()
            self.anim.stop()
            self.anim.setEndValue(1)
            self.anim.setDuration(500)
            self.anim.start()

    # def show(self):
    #     self.reset_timer.stop()
    #     self.op_effect.setOpacity(1)
