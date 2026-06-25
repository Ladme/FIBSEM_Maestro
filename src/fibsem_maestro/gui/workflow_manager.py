# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

import shutil

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
    workflow_interrupted = pyqtSignal(str)
    workflow_reset = pyqtSignal(
        int
    )  # slice number - needed for integration with log panel

    def __init__(self, workflow: Workflow, parent: QObject | None = None):
        super().__init__(parent)

        self.workflow = workflow

        self._state = (
            AppState.EDITING if self.workflow.ctx.slice == 0 else AppState.RELOADED
        )
        self._thread = None
        self._worker = None
        self._start_worker()

    def _start_worker(self) -> None:
        self._thread = QThread()
        self._worker = WorkflowWorker(self.workflow)
        self.workflow.set_callbacks(self._worker)
        self._worker.moveToThread(self._thread)

        # forward worker signals to the GUI
        self._worker.action_finished.connect(self.action_finished)
        self._worker.slice_finished.connect(self.slice_finished)
        self._worker.paused.connect(self._on_paused)
        self._worker.finished.connect(self._on_finished)
        self._worker.interrupted.connect(self._on_interrupted)

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

    def notify_workflow_reset(self) -> None:
        self.workflow_reset.emit(0)

    def start(self, n_slices: int) -> None:
        assert self._worker

        QMetaObject.invokeMethod(
            self._worker,
            "run",
            Qt.ConnectionType.QueuedConnection,
            Q_ARG(int, n_slices),
        )
        self._set_state(AppState.RUNNING)

    def pause(self) -> None:
        if self._worker is not None:
            self._worker.pause()
        self._set_state(AppState.STOPPING)

    def resume(self) -> None:
        if self._worker is not None:
            self._worker.resume()
        self._set_state(AppState.RUNNING)

    def stop(self) -> None:
        if self._thread is not None:
            self._thread.quit()
            self._thread.wait()
        self._set_state(AppState.PAUSED)

    def reset(self) -> None:
        # stop the worker thread
        if self._thread is not None and self._thread.isRunning():
            self._thread.terminate()
            self._thread.wait()

        for action in self.workflow.actions:
            action.reset()
            # delete the action's directory
            if (action_dir := action.ctx.path_to_dir) is not None:
                for item in action_dir.iterdir():
                    shutil.rmtree(item) if item.is_dir() else item.unlink()

            # then write the action's settings and state
            action.ctx.state_store.write("state.yaml", action.state)
            action.ctx.settings_store.write("settings.yaml", action.settings)

        self.workflow.ctx.reset()
        if (workflow_dir := self.workflow.ctx.path_to_dir) is not None:
            for item in workflow_dir.iterdir():
                shutil.rmtree(item) if item.is_dir() else item.unlink()

            # then write the workflow's state and microscope settings
            self.workflow.ctx.state_store.write("state.yaml", self.workflow.state)
            self.workflow.ctx.settings_store.write(
                "microscope_settings.yaml", self.workflow.microscope.settings
            )

        # restart the worker thread
        self._start_worker()

        self._set_state(AppState.EDITING)
        self.notify_workflow_reset()
        self.preparedness_changed.emit(False)

    def _on_paused(self) -> None:
        self._set_state(AppState.PAUSED)

    def _on_action_ready(self, action: Action) -> None:
        _ = action

    def _on_finished(self) -> None:
        self._set_state(AppState.FINISHED)
        if self._thread is not None:
            self._thread.deleteLater()
        if self._worker is not None:
            self._worker.deleteLater()

    def _on_interrupted(self, error: str) -> None:
        self._set_state(AppState.INTERRUPTED)
        self.workflow_interrupted.emit(error)
