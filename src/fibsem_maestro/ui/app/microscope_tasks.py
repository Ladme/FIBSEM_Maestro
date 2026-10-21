# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF

"""The serial runner of GUI-initiated microscope work."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Generic, TypeVar

from PyQt6.QtCore import QObject, Qt, QThread, pyqtSignal, pyqtSlot

from fibsem_maestro.ui.app.errors import NotAllowedError
from fibsem_maestro.ui.ports import TaskHandle

if TYPE_CHECKING:
    from collections.abc import Callable

    from fibsem_maestro.logging.text.text_logger import TextLogger

T = TypeVar("T")


@dataclass(frozen=True)
class MicroscopeTask(Generic[T]):
    """
    One piece of microscope work requested from the GUI.

    Attributes:
        run: The work; executed on the task thread.
        description: E.g. "Preparing 'imaging'". Logged as "<description>...",
            then "<description> completed." or "<description> failed: <error>"
            (error level).
        log: Logger receiving those lines, or None to log nothing (area-selector previews).
        then: Application-layer follow-up run on the GUI thread with the result,
            before the handle emits `succeeded` (e.g. announcing new props after
            Prepare). It must not capture widgets; view reactions go through the
            handle's signals.
    """

    run: Callable[[], T]
    description: str
    log: TextLogger | None = None
    then: Callable[[T], None] | None = None


class _Job:
    """A submitted task with the handle reporting its outcome."""

    def __init__(self, task: MicroscopeTask[Any], handle: TaskHandle) -> None:
        self.task = task
        self.handle = handle


class _TaskWorker(QObject):
    """Executes jobs on the task thread; touches nothing but the job's callable."""

    completed = pyqtSignal(object, object, object)
    """`(job, result, error)`: exactly one of `result` / `error` is meaningful."""

    @pyqtSlot(object)
    def execute(self, job: _Job) -> None:
        """
        Run a job's work and report the outcome.

        Args:
            job: The job; its `run` executes on this thread.
        """
        try:
            result = job.task.run()
        except Exception as e:
            self.completed.emit(job, None, e)
        else:
            self.completed.emit(job, result, None)


class MicroscopeTasks(QObject):
    """
    The only way GUI-initiated work reaches the microscope: one task at a time.

    A long-lived thread executes the tasks. A task is refused while another runs
    (`busy`) and while the workflow executes (`locked`, set by the run controller).
    Results are delivered through each task's `TaskHandle` on the GUI thread.

    Args:
        parent: Optional Qt parent.
    """

    busy_changed = pyqtSignal(bool)
    """Emitted with the new value of `busy`."""

    _dispatch = pyqtSignal(object)
    """Hands a `_Job` to the worker (queued: the worker lives on the task thread)."""

    _refused = pyqtSignal(object, object)
    """`(handle, error)`; connected queued, so a refusal is reported on the next turn."""

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._busy = False
        self._locked = False
        # handles stay referenced here until they have emitted
        self._pending: dict[int, TaskHandle] = {}

        self._thread = QThread()
        self._thread.setObjectName("microscope-tasks")
        self._worker = _TaskWorker()
        self._worker.moveToThread(self._thread)

        # the worker is deleted on its own thread while that thread's loop still runs
        self._thread.finished.connect(self._worker.deleteLater)
        # work reaches the worker only through a queued signal into its slot, so it
        # runs on the task thread (a plain callable connected to `started` would not);
        # the PyQt6 stubs omit connect's connection-type parameter
        queued = Qt.ConnectionType.QueuedConnection
        # PyQt stubs are incorrect, ignore them
        self._dispatch.connect(self._worker.execute, queued)  # ty: ignore[too-many-positional-arguments]
        self._worker.completed.connect(self._on_completed, queued)  # ty: ignore[too-many-positional-arguments]
        # queued even though both live on the GUI thread: a refusal is reported on
        # the next event-loop turn, after the caller connected to the handle
        self._refused.connect(self._on_refused, queued)  # ty: ignore[too-many-positional-arguments]

        self._thread.start()

    @property
    def busy(self) -> bool:
        """True from an accepted `submit` until its handle's slots have returned."""
        return self._busy

    @property
    def locked(self) -> bool:
        """True while the workflow is executing (set by the run controller)."""
        return self._locked

    def set_locked(self, locked: bool) -> None:
        """
        Allow or refuse new tasks because the workflow is executing.

        Args:
            locked: True while the workflow executes.
        """
        self._locked = locked

    def submit(self, task: MicroscopeTask[T]) -> TaskHandle:
        """
        Queue a task and return its handle.

        Never raises: if a task is running or the workflow is executing, the
        handle emits `failed(NotAllowedError(...))` on the next event-loop turn
        and nothing runs. Otherwise `busy` turns true before this returns.

        Args:
            task: The work to run.

        Returns:
            The handle reporting the outcome.
        """
        if self._busy:
            return self.refuse(NotAllowedError("A microscope task is already running."))
        if self._locked:
            return self.refuse(NotAllowedError("The workflow is running."))

        handle = TaskHandle()
        self._pending[id(handle)] = handle
        if task.log is not None:
            task.log.info(f"{task.description}...")
        self._set_busy(True)
        self._dispatch.emit(_Job(task, handle))
        return handle

    def refuse(self, error: Exception) -> TaskHandle:
        """
        Return a handle that reports `error` through `failed` on the next event-loop turn.

        Used for every refused request, so callers handle refusals and failures alike.

        Args:
            error: The reason, usually a `NotAllowedError`.

        Returns:
            The handle; it never emits `succeeded`.
        """
        handle = TaskHandle()
        self._pending[id(handle)] = handle
        self._refused.emit(handle, error)
        return handle

    def shutdown(self, timeout_ms: int = 0) -> None:
        """
        Ask the task thread to quit.

        Args:
            timeout_ms: How long to wait for it, in ms; 0 does not wait. A
                running task is never interrupted.
        """
        self._thread.quit()
        if timeout_ms > 0:
            self._thread.wait(timeout_ms)

    def _on_refused(self, handle: TaskHandle, error: Exception) -> None:
        try:
            handle.failed.emit(error)
        finally:
            self._release(handle)

    def _on_completed(self, job: _Job, result: object, error: Exception | None) -> None:
        task, handle = job.task, job.handle
        try:
            if error is None:
                if task.log is not None:
                    task.log.info(f"{task.description} completed.")
                try:
                    if task.then is not None:
                        task.then(result)
                except Exception as e:
                    error = e

            if error is None:
                handle.succeeded.emit(result)
            else:
                if task.log is not None:
                    task.log.error(f"{task.description} failed: {error}")
                handle.failed.emit(error)
        finally:
            # cleared only after the handle's slots returned and even if one raised,
            # so a follow-up lands before any control is re-enabled
            self._release(handle)
            self._set_busy(False)

    def _release(self, handle: TaskHandle) -> None:
        self._pending.pop(id(handle), None)
        handle.deleteLater()

    def _set_busy(self, busy: bool) -> None:
        if busy == self._busy:
            return
        self._busy = busy
        self.busy_changed.emit(busy)
