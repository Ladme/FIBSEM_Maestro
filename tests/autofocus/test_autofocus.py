import threading
from collections.abc import Callable
from concurrent.futures import Executor
from typing import Any

from fibsem_maestro.autofocus import InterleavedSweepingStrategy
from fibsem_maestro.autofocus.jobs_manager import JobsManager
from fibsem_maestro.autofocus.result import AutofocusResult
from fibsem_maestro.autofocus.sweep_step import SweepStep
from fibsem_maestro.settings.sweeping_settings import InterleavedStrategySettings


def _interleaved_results(
    values: list[float], sharpness: dict[float, float]
) -> list[AutofocusResult]:
    return [
        AutofocusResult(sharpness[v], SweepStep(0, v, i)) for i, v in enumerate(values)
    ]


def test_interleaved_picks_candidate_sharper_than_base() -> None:
    strategy = InterleavedSweepingStrategy(InterleavedStrategySettings(min_diff=0.0))
    values = [float(v) for v in strategy.generate(0.0, (-2.0, 2.0), 3, 0)]
    # -2 is much worse than the base, +2 is the only value sharper than the base
    sharpness = {0.0: 10.0, -2.0: 2.0, 2.0: 11.0}
    assert strategy.evaluate(_interleaved_results(values, sharpness)) == 2.0


def test_interleaved_keeps_base_when_nothing_is_sharper() -> None:
    strategy = InterleavedSweepingStrategy(InterleavedStrategySettings(min_diff=0.0))
    values = [float(v) for v in strategy.generate(0.0, (-2.0, 2.0), 3, 0)]
    sharpness = {0.0: 10.0, -2.0: 2.0, 2.0: 9.0}
    assert strategy.evaluate(_interleaved_results(values, sharpness)) == 0.0


def test_interleaved_tolerates_a_missing_result() -> None:
    strategy = InterleavedSweepingStrategy(InterleavedStrategySettings(min_diff=0.0))
    values = [float(v) for v in strategy.generate(0.0, (-2.0, 2.0), 3, 0)]
    sharpness = {0.0: 10.0, -2.0: 2.0, 2.0: 11.0}
    results = _interleaved_results(values, sharpness)
    # the job scoring the second base frame failed and was dropped
    del results[2]
    assert strategy.evaluate(results) == 2.0


class _LateCallbackFuture:
    """A future whose done-callbacks run some time after its result is ready."""

    def __init__(self, delay_s: float) -> None:
        self._done = threading.Event()
        self._delay_s = delay_s
        self._result: Any = None
        self._callbacks: list[Callable[[Any], None]] = []

    def run(self, fn: Callable[[], Any]) -> None:
        self._result = fn()
        self._done.set()  # waiters in result() wake up here ...
        threading.Timer(self._delay_s, self._fire).start()  # ... callbacks later

    def _fire(self) -> None:
        for callback in self._callbacks:
            callback(self)

    def add_done_callback(self, fn: Callable[[Any], None]) -> None:
        self._callbacks.append(fn)

    def result(self, timeout: float | None = None) -> Any:
        self._done.wait(timeout)
        return self._result

    def done(self) -> bool:
        return self._done.is_set()

    def exception(self, timeout: float | None = None) -> BaseException | None:
        self._done.wait(timeout)
        return None


class LateCallbackExecutor(Executor):
    """Models a thread switch between a future completing and its callbacks."""

    def submit(self, fn: Callable[..., Any], /, *args: Any, **kwargs: Any) -> Any:
        future = _LateCallbackFuture(delay_s=0.2)
        threading.Thread(target=future.run, args=(lambda: fn(*args, **kwargs),)).start()
        return future


def test_jobs_manager_returns_every_finished_result() -> None:
    jobs = JobsManager(executor=LateCallbackExecutor())
    for i in range(3):
        jobs.submit(lambda i=i: AutofocusResult(float(i), SweepStep(0, float(i), i)))

    results = jobs.wait_and_collect()

    assert sorted(r.sharpness for r in results) == [0.0, 1.0, 2.0]


def test_jobs_manager_drops_failed_jobs() -> None:
    jobs = JobsManager()

    def fail() -> AutofocusResult:
        raise RuntimeError("criterion failed")

    jobs.submit(fail)
    jobs.submit(lambda: AutofocusResult(1.0, SweepStep(0, 1.0, 1)))
    assert [r.sharpness for r in jobs.wait_and_collect()] == [1.0]
