# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


import contextlib
import threading
from collections.abc import Callable
from concurrent.futures import Executor, Future, ThreadPoolExecutor
from typing import Self

from fibsem_maestro.autofocus.result import AutofocusResult


class JobsManager:
    """
    Manages concurrent resolution calculation jobs during an autofocus sweep.

    Submits resolution calculations to a thread pool as images are acquired,
    collects results asynchronously, and returns them once all jobs complete.

    Args:
        criterion: The resolution criterion used to evaluate images.
        log: Logger for per-job diagnostics.
        executor: Optional external executor. If omitted, an internal one is
            created and owned by this instance.
    """

    def __init__(
        self,
        executor: Executor | None = None,
    ) -> None:
        self._own_executor = executor is None
        self._executor: Executor = executor or ThreadPoolExecutor()

        self._pending: list[Future[float]] = []
        self._pending_lock = threading.Lock()
        self._results: list[AutofocusResult] = []
        self._results_lock = threading.Lock()

    def submit(self, fn: Callable[[], AutofocusResult]) -> None:
        future = self._executor.submit(fn)

        def _on_done(f: Future[AutofocusResult]) -> None:
            try:
                self._results.append(f.result())
            except Exception:
                return

        future.add_done_callback(_on_done)

    def wait_and_collect(self) -> list[AutofocusResult]:
        """
        Block until all submitted jobs finish and return the results.

        Returns:
            All successfully computed AutofocusResult instances, in completion
            order. Failed jobs are logged and excluded.
        """
        self._drain()
        with self._results_lock:
            return list(self._results)

    def clear(self) -> None:
        """Discard all accumulated results, preparing for a fresh sweep."""
        with self._results_lock:
            self._results = []

    def _drain(self) -> None:
        while True:
            with self._pending_lock:
                if not self._pending:
                    return
                pending, self._pending = self._pending, []

            for future in pending:
                with contextlib.suppress(Exception):
                    future.result()  # errors already handled in callback

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_: object) -> None:
        if self._own_executor:
            self._executor.shutdown(wait=True)
