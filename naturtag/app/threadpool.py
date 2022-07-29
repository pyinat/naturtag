"""Adapted from examples in Python & Qt6 by Martin Fitzpatrick"""
from logging import getLogger
from threading import RLock
from typing import Callable

from PySide6.QtCore import (
    QEasingCurve,
    QObject,
    QPropertyAnimation,
    QRunnable,
    QThread,
    QThreadPool,
    QTimer,
    Signal,
)
from PySide6.QtWidgets import QGraphicsOpacityEffect, QProgressBar

logger = getLogger(__name__)


# TODO: For loading taxa, set/increase progress bar max once up front, instead of once per taxon
class ThreadPool(QThreadPool):
    """Thread pool that enqueues jobs to ber run from separate thread(s), and updates a progress
    bar.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.progress = ProgressBar()

    def schedule(
        self, callback: Callable, priority: QThread.Priority = QThread.NormalPriority, **kwargs
    ) -> 'WorkerSignals':
        """Schedule a task to be run by the next available worker thread"""
        self.progress.add()
        worker = Worker(callback, **kwargs)
        worker.signals.on_progress.connect(self.progress.advance)
        self.start(worker, priority)
        return worker.signals

    def schedule_all(self, callbacks: list[Callable], **kwargs) -> list['WorkerSignals']:
        """Schedule multiple tasks to be run by the next available worker thread"""
        self.progress.add(len(callbacks))
        for callback in callbacks:
            worker = Worker(callback, **kwargs)
            worker.signals.on_progress.connect(self.progress.advance)
            self.start(worker)
        return worker.signals

    def cancel(self):
        """Cancel all queued tasks and reset progress bar. Currently running tasks will be allowed
        to complete.
        """
        if active_threads := self.activeThreadCount() > 0:
            logger.debug(f'Cancelling {active_threads} active threads')
        self.clear()
        self.progress.reset()


class Worker(QRunnable):
    """A worker thread that takes a callback (and optional args/kwargs), and updates progress when
    done.
    """

    def __init__(self, callback: Callable, **kwargs):
        super().__init__()
        self.callback = callback
        self.kwargs = kwargs
        self.signals = WorkerSignals()

    def run(self):
        try:
            result = self.callback(**self.kwargs)
        except Exception as e:
            logger.warning('Worker error:', exc_info=True)
            self.signals.on_error.emit(e)
        else:
            self.signals.on_result.emit(result)
        self.signals.on_progress.emit()


class WorkerSignals(QObject):
    """Signals used by a worker thread (can't be set directly on a QRunnable)"""

    on_error = Signal(Exception)  #: Return exception info on error
    on_result = Signal(object)  #: Return result on completion
    on_progress = Signal()  #: Increment progress bar


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

    def add(self, amount: int = 1):
        self.fadein()
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
        if self.value() > 0:
            self.reset_timer.start(2000)
            self.fadeout()

    def reset(self):
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
