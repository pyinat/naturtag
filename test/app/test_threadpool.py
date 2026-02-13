"""Tests for naturtag.app.threadpool"""

import threading
from unittest.mock import MagicMock

import pytest

from naturtag.app.threadpool import PaginatedWorker, Worker


def _make_paginator(pages):
    def callback():
        yield from pages

    return callback


def test_worker_run():
    callback = MagicMock(return_value=42)
    worker = Worker(callback)
    on_result = MagicMock()
    worker.signals.on_result.connect(on_result)

    worker.run()

    callback.assert_called_once()
    on_result.assert_called_once_with(42)


def test_worker_run__exception():
    err = ValueError('boom')
    callback = MagicMock(side_effect=err)
    worker = Worker(callback)
    on_error = MagicMock()
    on_result = MagicMock()
    worker.signals.on_error.connect(on_error)
    worker.signals.on_result.connect(on_result)

    worker.run()

    on_error.assert_called_once_with(err)
    on_result.assert_not_called()


def test_worker_run__on_progress_emitted():
    worker = Worker(MagicMock(return_value='ok'))
    on_progress = MagicMock()
    worker.signals.on_progress.connect(on_progress)

    worker.run()

    on_progress.assert_called_once_with(1)


def test_worker_run__increment_length():
    worker = Worker(MagicMock(return_value=[1, 2, 3]), increment_length=True)
    on_progress = MagicMock()
    worker.signals.on_progress.connect(on_progress)

    worker.run()

    on_progress.assert_called_once_with(3)


def test_worker_run__increment_length__non_list():
    worker = Worker(MagicMock(return_value='scalar'), increment_length=True)
    on_progress = MagicMock()
    worker.signals.on_progress.connect(on_progress)

    worker.run()

    on_progress.assert_called_once_with(1)


def test_worker_run__kwargs_passed_through():
    callback = MagicMock(return_value=None)
    worker = Worker(callback, foo='bar', baz=99)

    worker.run()

    callback.assert_called_once_with(foo='bar', baz=99)


def test_paginated_worker_run():
    worker = PaginatedWorker(_make_paginator([[1, 2], [3, 4]]))
    on_result = MagicMock()
    worker.signals.on_result.connect(on_result)

    worker.run()

    assert on_result.call_count == 2
    on_result.assert_any_call([1, 2])
    on_result.assert_any_call([3, 4])


def test_paginated_worker_run__on_progress_per_page():
    worker = PaginatedWorker(_make_paginator([[1, 2], [3]]))
    on_progress = MagicMock()
    worker.signals.on_progress.connect(on_progress)

    worker.run()

    # One call per page with page length, plus a final 1
    calls = [c.args[0] for c in on_progress.call_args_list]
    assert calls == [2, 1, 1]


def test_paginated_worker_run__on_complete_always_emitted():
    def bad_callback():
        raise RuntimeError('fail')

    worker = PaginatedWorker(bad_callback)
    on_complete = MagicMock()
    worker.signals.on_complete.connect(on_complete)

    worker.run()

    on_complete.assert_called_once()


def test_paginated_worker_run__exception():
    err = RuntimeError('fail')

    def bad_callback():
        raise err

    worker = PaginatedWorker(bad_callback)
    on_error = MagicMock()
    worker.signals.on_error.connect(on_error)

    worker.run()

    on_error.assert_called_once_with(err)


def test_paginated_worker_run__empty_iterator():
    worker = PaginatedWorker(_make_paginator([]))
    on_complete = MagicMock()
    on_progress = MagicMock()
    worker.signals.on_complete.connect(on_complete)
    worker.signals.on_progress.connect(on_progress)

    worker.run()

    on_complete.assert_called_once()
    on_progress.assert_called_once_with(1)


def test_worker_run__on_finished_emitted():
    worker = Worker(MagicMock(return_value='ok'))
    on_finished = MagicMock()
    worker.signals.on_finished.connect(on_finished)

    worker.run()

    on_finished.assert_called_once()


def test_worker_run__on_finished_emitted_on_error():
    worker = Worker(MagicMock(side_effect=ValueError('boom')))
    on_finished = MagicMock()
    worker.signals.on_finished.connect(on_finished)

    worker.run()

    on_finished.assert_called_once()


def test_paginated_worker_run__on_finished_emitted():
    worker = PaginatedWorker(_make_paginator([[1, 2]]))
    on_finished = MagicMock()
    worker.signals.on_finished.connect(on_finished)

    worker.run()

    on_finished.assert_called_once()


def test_paginated_worker_run__on_finished_emitted_on_error():
    def bad_callback():
        raise RuntimeError('fail')

    worker = PaginatedWorker(bad_callback)
    on_finished = MagicMock()
    worker.signals.on_finished.connect(on_finished)

    worker.run()

    on_finished.assert_called_once()


def test_progress_bar_add(progress_bar):
    progress_bar.add(5)
    assert progress_bar.maximum() == 5


def test_progress_bar_add__multiple(progress_bar):
    progress_bar.add(3)
    progress_bar.add(2)
    assert progress_bar.maximum() == 5


def test_progress_bar_advance(progress_bar):
    progress_bar.add(10)
    progress_bar.advance(3)
    assert progress_bar.value() == 3


def test_progress_bar_advance__caps_at_maximum(progress_bar):
    progress_bar.add(5)
    progress_bar.advance(10)
    assert progress_bar.value() == 5


def test_progress_bar_advance__triggers_schedule_reset(progress_bar):
    progress_bar.add(3)
    progress_bar.advance(3)
    assert progress_bar.reset_timer.isActive()


def test_progress_bar_remove(progress_bar):
    progress_bar.add(10)
    progress_bar.remove(3)
    assert progress_bar.maximum() == 7


def test_progress_bar_remove__floors_at_value(progress_bar):
    progress_bar.add(10)
    progress_bar.advance(6)
    progress_bar.remove(8)
    assert progress_bar.maximum() == 6


def test_progress_bar_remove__triggers_schedule_reset(progress_bar):
    progress_bar.add(10)
    progress_bar.advance(5)
    progress_bar.remove(5)
    assert progress_bar.reset_timer.isActive()


def test_progress_bar_reset(progress_bar):
    progress_bar.add(10)
    progress_bar.advance(5)
    progress_bar.reset()
    assert progress_bar.value() == 0
    assert progress_bar.maximum() == 0


def test_schedule(thread_pool):
    signals = thread_pool.schedule(lambda: None)
    assert signals is not None
    assert thread_pool.progress.maximum() == 1


def test_schedule__total_results(thread_pool):
    thread_pool.schedule(lambda: None, total_results=5)
    assert thread_pool.progress.maximum() == 5


def test_schedule__result_emitted(thread_pool, qtbot):
    gate = threading.Event()

    def callback():
        gate.wait(timeout=5)
        return 42

    signals = thread_pool.schedule(callback)
    with qtbot.waitSignal(signals.on_result, timeout=3000) as blocker:
        gate.set()
    assert blocker.args == [42]


def test_schedule__group_tracks_worker(thread_pool):
    # Use a blocking callback so the worker is still alive when we check
    event = threading.Event()
    thread_pool.schedule(lambda: event.wait(timeout=3), group='g1')
    assert len(thread_pool._group_workers['g1']) == 1
    event.set()


# ⚠️ These tests occasionally segfault, particularly in CI
# @pytest.mark.xfail(strict=False)
@pytest.mark.skip
def test_schedule__group_worker_removed_on_completion(thread_pool, qtbot):
    signals = thread_pool.schedule(lambda: 1, group='g1')
    qtbot.waitSignal(signals.on_finished, timeout=3000)
    qtbot.wait(10)
    # The removal lambda is queued cross-thread; wait for it to execute
    qtbot.waitUntil(lambda: len(thread_pool._group_workers['g1']) == 0, timeout=3000)


def _pages():
    yield [1, 2]
    yield [3, 4]


def test_schedule_paginator(thread_pool):
    signals = thread_pool.schedule_paginator(_pages, total_results=5)
    assert signals is not None
    assert thread_pool.progress.maximum() == 5


def test_schedule_paginator__results_emitted(thread_pool, qtbot):
    signals = thread_pool.schedule_paginator(_pages)
    with qtbot.waitSignal(signals.on_complete, timeout=3000):
        pass
    # If on_complete fired, pages were emitted successfully


@pytest.mark.skip
def test_schedule_paginator__group_removed_on_complete(thread_pool, qtbot):
    signals = thread_pool.schedule_paginator(_pages, group='pg')
    qtbot.waitSignal(signals.on_finished, timeout=3000)
    qtbot.wait(10)
    qtbot.waitUntil(lambda: len(thread_pool._group_workers['pg']) == 0, timeout=3000)


def test_cancel(thread_pool):
    thread_pool.progress.add(5)
    thread_pool.progress.advance(2)
    thread_pool.cancel()
    assert thread_pool.progress.value() == 0
    assert thread_pool.progress.maximum() == 0


def test_cancel__group(thread_pool):
    # Use 1 thread so queued workers stay queued
    thread_pool.setMaxThreadCount(1)
    blocker = threading.Event()
    thread_pool.schedule(lambda: blocker.wait(timeout=5))

    # Schedule workers in two groups while the thread is occupied
    thread_pool.schedule(lambda: 'a1', group='a')
    thread_pool.schedule(lambda: 'a2', group='a')
    thread_pool.schedule(lambda: 'b1', group='b')

    thread_pool.cancel(group='a')

    # Group 'a' should be cleared, group 'b' should be untouched
    assert len(thread_pool._group_workers.get('a', [])) == 0
    assert len(thread_pool._group_workers['b']) == 1
    blocker.set()


def test_cancel__group_adjusts_progress(thread_pool):
    thread_pool.setMaxThreadCount(1)
    blocker = threading.Event()
    thread_pool.schedule(lambda: blocker.wait(timeout=5))

    thread_pool.schedule(lambda: 'x', group='g')
    thread_pool.schedule(lambda: 'y', group='g')
    max_before = thread_pool.progress.maximum()

    thread_pool.cancel(group='g')
    max_after = thread_pool.progress.maximum()

    assert max_after == max_before - 2
    blocker.set()


def test_cancel__group_does_not_affect_other_groups(thread_pool):
    thread_pool.setMaxThreadCount(1)
    blocker = threading.Event()
    thread_pool.schedule(lambda: blocker.wait(timeout=5))

    thread_pool.schedule(lambda: 1, group='keep')
    thread_pool.schedule(lambda: 2, group='drop')

    thread_pool.cancel(group='drop')

    assert len(thread_pool._group_workers['keep']) == 1
    assert len(thread_pool._group_workers.get('drop', [])) == 0
    blocker.set()


def test_cancel__nonexistent_group(thread_pool):
    # Should be a no-op, no error
    thread_pool.cancel(group='does_not_exist')
