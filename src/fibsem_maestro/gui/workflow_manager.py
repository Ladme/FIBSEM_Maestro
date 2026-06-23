# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from PyQt6.QtCore import Q_ARG, QMetaObject, QObject, Qt, QThread, pyqtSignal

from fibsem_maestro.action.action import Action
from fibsem_maestro.gui.app_state import AppState
from fibsem_maestro.gui.workflow_worker import WorkflowWorker
from fibsem_maestro.microscope.microscope import Microscope
from fibsem_maestro.workflow.actions import Actions
from fibsem_maestro.workflow.propagations import Propagations
from fibsem_maestro.workflow.workflow import Workflow


class WorkflowManager(QObject):
    action_changed = pyqtSignal(Action)
    actions_changed = pyqtSignal(Actions)
    propagations_changed = pyqtSignal(Propagations)
    microscope_changed = pyqtSignal(Microscope)
    action_finished = pyqtSignal(Action)
    slice_finished = pyqtSignal(int)
    app_state_changed = pyqtSignal(AppState)
    preparedness_changed = pyqtSignal(bool)

    def __init__(self, workflow: Workflow, parent: QObject | None = None):
        super().__init__(parent)

        self.workflow = workflow

        self._state = (
            AppState.EDITING if self.workflow.ctx.slice == 0 else AppState.RELOADED
        )
        self._thread = QThread()
        self._worker = WorkflowWorker(workflow)
        self.workflow.set_callbacks(self._worker)
        self._worker.moveToThread(self._thread)

        # forward worker signals to the GUI
        self._worker.action_finished.connect(self.action_finished)
        self._worker.slice_finished.connect(self.slice_finished)
        self._worker.paused.connect(self._on_paused)
        self._worker.finished.connect(self._on_finished)

        self._thread.start()

    @property
    def state(self) -> AppState:
        return self._state

    def _set_state(self, state: AppState) -> None:
        self._state = state
        self.app_state_changed.emit(state)

    def notify_action_changed(self, action: Action) -> None:
        self.action_changed.emit(action)

    def notify_actions_changed(self) -> None:
        self.actions_changed.emit(self.workflow.actions)

    def notify_propagations_changed(self) -> None:
        self.propagations_changed.emit(self.workflow.propagations)

    def notify_microscope_changed(self) -> None:
        self.microscope_changed.emit(self.workflow.microscope)

    def start(self, n_slices: int) -> None:
        QMetaObject.invokeMethod(
            self._worker,
            "run",
            Qt.ConnectionType.QueuedConnection,
            Q_ARG(int, n_slices),
        )
        self._set_state(AppState.RUNNING)

    def pause(self) -> None:
        self._worker.pause()
        self._set_state(AppState.STOPPING)

    def resume(self) -> None:
        self._worker.resume()
        self._set_state(AppState.RUNNING)

    def stop(self) -> None:
        self._thread.quit()
        self._thread.wait()
        self._set_state(AppState.PAUSED)

    def _on_paused(self) -> None:
        self._set_state(AppState.PAUSED)

    def _on_action_ready(self, action: Action) -> None:
        _ = action

    def _on_finished(self) -> None:
        self._set_state(AppState.FINISHED)
        self._thread.deleteLater()
        self._worker.deleteLater()
