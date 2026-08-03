# Released under MIT License.
# Copyright (c) 2024-2026 CEMCOF

import threading

from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot

from fibsem_maestro.action.action import Action
from fibsem_maestro.workflow.error import ActionError
from fibsem_maestro.workflow.error_choice import ErrorChoice
from fibsem_maestro.workflow.workflow import Workflow


class AbortedError(Exception):
    """Indicates that the workflow was aborted before completion."""

    pass


class WorkflowWorker(QObject):
    action_finished = pyqtSignal(Action)
    slice_finished = pyqtSignal(int)
    paused = pyqtSignal()
    finished = pyqtSignal()
    workflow_error = pyqtSignal(Exception)
    action_error = pyqtSignal(Exception)

    def __init__(self, workflow: Workflow, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._workflow = workflow
        self._pause_requested = False
        self._resume_event = threading.Event()
        # start in resumed state
        self._resume_event.set()

        self._error_event = threading.Event()
        self._error_choice: ErrorChoice | None = None

        self._aborted = False

    def notify_action_finished(self, finished_action_index: int) -> None:
        self.action_finished.emit(
            # emit the following action of the workflow
            self._workflow.actions[
                (finished_action_index + 1) % len(self._workflow.actions)
            ]
        )

    def notify_slice_finished(self) -> None:
        self.slice_finished.emit(
            # emit the current slice index
            self._workflow.ctx.slice
        )

    def notify_is_paused(self) -> None:
        self.paused.emit()

    def is_pause_requested(self) -> bool:
        return self._pause_requested

    def wait_for_resume(self) -> None:
        while not self._resume_event.wait(timeout=0.1):
            pass

        if self._aborted:
            raise AbortedError()

    def request_error_choice(self, error: ActionError) -> ErrorChoice:
        """
        Ask the GUI how to handle a failed action.

        Called on the worker thread. Blocks until the GUI thread answers via
        submit_error_choice, or the workflow is aborted.
        """
        self._error_choice = None
        self._error_event.clear()
        self.action_error.emit(error)

        while not self._error_event.wait(timeout=0.1):
            pass

        if self._aborted:
            raise AbortedError()

        assert self._error_choice is not None
        return self._error_choice

    def submit_error_choice(self, choice: ErrorChoice) -> None:
        """Called on the GUI thread to unblock request_error_choice."""
        self._error_choice = choice
        self._error_event.set()

    def pause(self) -> None:
        self._pause_requested = True
        self._resume_event.clear()

    def resume(self) -> None:
        self._pause_requested = False
        self._resume_event.set()

    def abort(self) -> None:
        self._aborted = True
        # unblock wait_for_resume
        self._resume_event.set()
        self._error_event.set()

    @pyqtSlot(int)
    def run(self, n_slices: int) -> None:
        """Runs the workflow. Executes on the worker thread via Qt slot dispatch."""
        try:
            self._workflow.set_callbacks(self)
            self._workflow.run(n_slices)
            self.finished.emit()
        except AbortedError:
            # clean exit
            pass
        except Exception as e:
            self.workflow_error.emit(e)
