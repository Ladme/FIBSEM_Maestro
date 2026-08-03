# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

import shutil
from pathlib import Path

from PyQt6.QtCore import QSize, Qt, QTimer
from PyQt6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QStyle,
    QWidget,
)

from fibsem_maestro.action_context.file import FileActionContext
from fibsem_maestro.gui.app_state import AppState
from fibsem_maestro.gui.form_builder.builder import FormBuilder
from fibsem_maestro.gui.window._microscope_dialog import MicroscopeSettingsDialog
from fibsem_maestro.gui.workflow_manager import WorkflowManager
from fibsem_maestro.workflow.actions import Actions
from fibsem_maestro.workflow.propagations import Propagations
from fibsem_maestro.workflow.workflow import Workflow


class TopBar(QWidget):
    """
    Horizontal bar at the top of the main window.
    """

    def __init__(
        self,
        workflow_manager: WorkflowManager,
        workflow_dir: Path,
        form_builder: FormBuilder,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._manager = workflow_manager
        self._microscope = self._manager.workflow.microscope
        self._workflow_dir = workflow_dir
        self._form_builder = form_builder

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)

        # new workflow
        self._new_btn = QPushButton("New workflow")
        self._new_btn.clicked.connect(self._on_new_workflow)
        layout.addWidget(self._new_btn)

        # import workflow
        self._import_btn = QPushButton("Import workflow")
        self._import_btn.clicked.connect(self._on_import_workflow)
        layout.addWidget(self._import_btn)

        # reset workflow
        self._reset_btn = QPushButton("Reset workflow")
        self._reset_btn.clicked.connect(self._on_reset_workflow)
        layout.addWidget(self._reset_btn)

        self._separator(layout)

        # microscope settings
        microscope_btn = QPushButton("Microscope settings")
        microscope_btn.clicked.connect(self._on_microscope_settings)
        layout.addWidget(microscope_btn)

        layout.addStretch()

        # run controls
        self._run_btn = QPushButton()
        style = self._run_btn.style()
        icon_size = 20
        self._run_btn.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
        self._run_btn.setIconSize(QSize(icon_size, icon_size))
        self._run_btn.setFixedSize(QSize(icon_size + 8, icon_size + 8))
        self._run_btn.clicked.connect(self._on_run)
        self._run_btn.setEnabled(self._manager.state is not AppState.EDITING)
        layout.addWidget(self._run_btn)

        status_layout = QHBoxLayout()
        status_layout.setSpacing(1)
        status_layout.setContentsMargins(0, 0, 0, 0)

        # slice number
        self._slice_label = QLabel()
        slice_font = self._slice_label.font()
        slice_font.setPointSize(20)
        slice_font.setBold(True)
        self._slice_label.setFont(slice_font)
        self._slice_label.setAlignment(
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignHCenter
        )
        self._slice_label.setFixedWidth(100)
        status_layout.addWidget(self._slice_label)

        # current app state
        self._state_label = QLabel()
        state_font = self._state_label.font()
        state_font.setPointSize(15)
        state_font.setBold(True)
        self._state_label.setFont(state_font)
        self._state_label.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        self._state_label.setFixedWidth(120)
        status_layout.addWidget(self._state_label)

        layout.addLayout(status_layout)
        self._update_status()
        layout.addStretch()

        # workflow directory
        self._dir_label = QLabel(str(self._workflow_dir))
        self._dir_label.setAlignment(
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight
        )
        self._dir_label.setStyleSheet("color: #888888;")
        dir_font = self._dir_label.font()
        dir_font.setPointSize(9)
        self._dir_label.setFont(dir_font)
        layout.addWidget(self._dir_label)

        # setup the animation of the states
        self._setup_state_animation()

        # enable/disable the run button based on whether the workflow is prepared
        self._manager.preparedness_changed.connect(self._on_preparedness_changed)

    @staticmethod
    def _separator(layout: QHBoxLayout) -> None:
        line = QWidget()
        line.setFixedWidth(1)
        line.setFixedHeight(20)
        line.setStyleSheet("background: #444444;")
        layout.addWidget(line)

    def _on_import_workflow(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Select workflow directory")
        if not path:
            return

        try:
            imported = Workflow.import_from_dir(
                Path(path),
                self._manager.workflow.microscope,
                self._workflow_dir,
                self._manager.workflow.notifier,
            )

            # delete all directories in the original workflow_dir, except for the workflow directory
            for dir in self._workflow_dir.iterdir():
                if dir.is_dir() and dir.name != "workflow":
                    shutil.rmtree(dir)

            # store action states and settings
            for action in imported.actions:
                action.ctx.state_store.write("state.yaml", action.state)
                action.ctx.settings_store.write("settings.yaml", action.settings)

            self._manager.workflow.actions = imported.actions
            self._manager.workflow.propagations = imported.propagations
            self._manager.notify_actions_changed()
            self._manager.notify_propagations_changed()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not import workflow: {str(e)}")

        self._manager.notify_actions_changed()

    def _on_new_workflow(self) -> None:
        # ask for save directory
        path = QFileDialog.getExistingDirectory(self, "Choose workflow save directory")
        if not path:
            return

        new_workflow_dir = Path(path)

        # warn if directory is not empty
        if any(new_workflow_dir.iterdir()):
            answer = QMessageBox.warning(
                self,
                "Directory not empty",
                "The selected directory is not empty. Assigning it to a workflow will PERMANENTLY delete all its contents.\n\nAre you sure you want to continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return

        # clear the new workflow directory
        for item in new_workflow_dir.iterdir():
            shutil.rmtree(item) if item.is_dir() else item.unlink()

        # create new workflow
        workflow = Workflow(
            microscope=self._microscope,
            actions=Actions(),
            propagations=Propagations(),
            context=FileActionContext(
                action_dir=new_workflow_dir / "workflow", name="workflow"
            ),
        )

        self._manager.workflow = workflow
        self._workflow_dir = new_workflow_dir

        self._manager.notify_new_workflow(new_workflow_dir)

        # update the display workflow directory
        self._dir_label.setText(str(new_workflow_dir))

        # update the preparedness
        self._on_preparedness_changed(False)

    def _on_reset_workflow(self) -> None:
        answer = QMessageBox.warning(
            self,
            "Data will be lost!",
            "Resetting the workflow will PERMANENTLY delete all data from all completed slices!\n\nAre you sure you want to continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        self._manager.reset()

    def _on_microscope_settings(self) -> None:
        """Opens the microscope settings dialog."""
        dialog = MicroscopeSettingsDialog(
            workflow_manager=self._manager,
            form_builder=self._form_builder,
            app_state=self._manager.state,
            parent=self,
        )
        dialog.exec()

    def _on_run(self) -> None:
        match self._manager.state:
            case AppState.EDITING | AppState.RELOADED:
                self._manager.start(9000)
            case AppState.PAUSED:
                self._manager.resume()
            case AppState.RUNNING:
                self._manager.pause()
            case AppState.INTERRUPTED:
                pass
            case AppState.FINISHED:
                pass

    def on_app_state_changed(self, state: AppState) -> None:
        self._update_status()
        self._import_btn.setEnabled(state == AppState.EDITING)
        self._reset_btn.setEnabled(state not in (AppState.RUNNING, AppState.STOPPING))
        self._new_btn.setEnabled(state not in (AppState.RUNNING, AppState.STOPPING))
        style = self._run_btn.style()
        match state:
            case AppState.EDITING:
                self._run_btn.setIcon(
                    style.standardIcon(QStyle.StandardPixmap.SP_MediaPlay)
                )

                self._run_btn.setEnabled(True)
            case AppState.RUNNING:
                self._run_btn.setIcon(
                    style.standardIcon(QStyle.StandardPixmap.SP_MediaPause)
                )

                self._run_btn.setEnabled(True)
            case AppState.PAUSED | AppState.FINISHED | AppState.RELOADED:
                self._run_btn.setIcon(
                    style.standardIcon(QStyle.StandardPixmap.SP_MediaPlay)
                )

                self._run_btn.setEnabled(True)
            case AppState.INTERRUPTED:
                self._run_btn.setIcon(
                    style.standardIcon(QStyle.StandardPixmap.SP_MediaPlay)
                )

                self._run_btn.setEnabled(False)

    def on_slice_changed(self, _: int) -> None:
        self._update_status()

    def _on_preparedness_changed(self, prepared: bool) -> None:
        self._run_btn.setEnabled(prepared)

    def _update_status(self) -> None:
        """Updates slice number and state label to reflect `_current_state`."""
        color = self._animated_color()

        self._slice_label.setText(str(self._manager.workflow.ctx.slice))
        self._slice_label.setStyleSheet(f"color: {color};")
        self._slice_label.repaint

        self._state_label.setText(str(self._manager.state))
        self._state_label.setStyleSheet(f"color: {color};")
        self._state_label.repaint()

    def _setup_state_animation(self) -> None:
        """Sets up the timer driving state symbol animation."""
        self._animation_frame = 0
        self._animation_timer = QTimer(self)
        self._animation_timer.setInterval(500)
        self._animation_timer.timeout.connect(self._on_animation_tick)
        self._animation_timer.start()

    def _on_animation_tick(self) -> None:
        """Advances the animation frame and refreshes the state label."""
        self._animation_frame += 1
        self._update_status()

    def _animated_color(self) -> str:
        """Returns the current color for `_current_state`."""
        match self._manager.state:
            case AppState.EDITING:
                return "#f0c040"
            case AppState.RUNNING:
                return "#4caf50"
            case AppState.STOPPING:
                return "#4caf50" if self._animation_frame % 2 == 0 else "#9e9e9e"
            case AppState.PAUSED | AppState.RELOADED:
                return "#9e9e9e"
            case AppState.INTERRUPTED:
                return "#f44336"
            case AppState.FINISHED:
                return "#3734eb"
