# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

import threading

from PyQt6.QtCore import QObject, pyqtSignal

from fibsem_maestro.action.action import Action
from fibsem_maestro.workflow.workflow import Workflow


class WorkflowWorker(QObject):
    action_finished = pyqtSignal(Action)
    slice_finished = pyqtSignal(int)
    paused = pyqtSignal()

    def __init__(self, workflow: Workflow, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._workflow = workflow
        self._pause_requested = False
        self._resume_event = threading.Event()
        # start in resumed state
        self._resume_event.set()

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
        self._resume_event.wait()

    def pause(self) -> None:
        self._pause_requested = True
        self._resume_event.clear()

    def resume(self) -> None:
        self._pause_requested = False
        self._resume_event.set()

    def run(self, n_slices: int) -> None:
        self._workflow.run(n_slices)
