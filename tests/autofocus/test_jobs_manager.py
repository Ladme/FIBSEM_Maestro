# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from concurrent.futures import ThreadPoolExecutor

import pytest

from fibsem_maestro.autofocus.jobs_manager import JobsManager
from fibsem_maestro.autofocus.result import AutofocusResult
from fibsem_maestro.autofocus.sweep_step import SweepStep


def _make_result(sharpness: float, index: int = 0) -> AutofocusResult:
    return AutofocusResult(
        sharpness=sharpness,
        sweep=SweepStep(repetition=0, value=float(index), index=index),
    )


def test_wait_and_collect_returns_all_successful_results():
    manager = JobsManager()
    manager.submit(lambda: _make_result(0.8, 0))
    manager.submit(lambda: _make_result(0.9, 1))

    results = manager.wait_and_collect()

    assert len(results) == 2
    assert {r.sharpness for r in results} == {0.8, 0.9}


def test_wait_and_collect_excludes_failed_jobs():
    manager = JobsManager()
    manager.submit(lambda: _make_result(0.8, 0))
    manager.submit(lambda: (_ for _ in ()).throw(RuntimeError("fail")))

    results = manager.wait_and_collect()

    assert len(results) == 1
    assert results[0].sharpness == 0.8


def test_clear_discards_accumulated_results():
    manager = JobsManager()
    manager.submit(lambda: _make_result(0.8, 0))
    manager.wait_and_collect()

    manager.clear()

    assert manager.wait_and_collect() == []


def test_context_manager_shuts_down_owned_executor():
    with JobsManager() as manager:
        manager.submit(lambda: _make_result(0.5, 0))

    # executor is shut down - further submissions must raise an exception
    with pytest.raises(RuntimeError):
        manager.submit(lambda: _make_result(0.5, 0))


def test_external_executor_is_not_shut_down_on_exit():
    external = ThreadPoolExecutor()

    with JobsManager(executor=external) as manager:
        manager.submit(lambda: _make_result(0.5, 0))

    # external executor must still accept work after the manager exits
    future = external.submit(lambda: 1 + 1)
    assert future.result() == 2

    external.shutdown(wait=True)
