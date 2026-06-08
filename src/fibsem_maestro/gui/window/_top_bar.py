# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from pathlib import Path

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QStyle,
    QWidget,
)

from fibsem_maestro.gui.app_state import AppState
from fibsem_maestro.microscope.microscope import Microscope
from fibsem_maestro.workflow.workflow import Workflow


class TopBar(QWidget):
    """
    Horizontal bar at the top of the main window.

    Args:
        microscope: The connected microscope instance.
        workflow: The current workflow.
        workflow_dir: Directory where the workflow is saved reactively.
    """

    run_requested = pyqtSignal()
    pause_requested = pyqtSignal()

    def __init__(
        self,
        microscope: Microscope,
        workflow: Workflow,
        workflow_dir: Path,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._microscope = microscope
        self._workflow = workflow
        self._workflow_dir = workflow_dir
        self._current_state = AppState.EDITING

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)

        # import workflow
        self._import_btn = QPushButton("Import workflow")
        self._import_btn.clicked.connect(self._on_import_workflow)
        layout.addWidget(self._import_btn)

        self._separator(layout)

        # microscope settings
        microscope_btn = QPushButton("Microscope settings")
        microscope_btn.clicked.connect(self._on_microscope_settings)
        layout.addWidget(microscope_btn)

        self._separator(layout)

        # run controls
        layout.addWidget(QLabel("Slices:"))

        self._slices_spin = QSpinBox()
        self._slices_spin.setRange(1, 10000)
        self._slices_spin.setValue(1)
        self._slices_spin.setFixedWidth(70)
        layout.addWidget(self._slices_spin)

        self._run_btn = QPushButton()
        style = self._run_btn.style()
        self._run_btn.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
        self._run_btn.setText("")
        self._run_btn.clicked.connect(self._on_run)
        layout.addWidget(self._run_btn)

        # push directory label to the right
        layout.addStretch()

        self._dir_label = QLabel(f"Workflow: {self._workflow_dir}")
        self._dir_label.setStyleSheet("color: #888888; font-size: 11px;")
        layout.addWidget(self._dir_label)

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
        # TODO: load actions and propagations from path into self._workflow

    def _on_microscope_settings(self) -> None:
        # TODO: replace placeholder
        pass

    def _on_run(self) -> None:
        match self._current_state:
            case AppState.EDITING | AppState.PAUSED:
                self.run_requested.emit()
            case AppState.RUNNING:
                self.pause_requested.emit()
            case AppState.INTERRUPTED:
                pass

    def on_app_state_changed(self, state: AppState) -> None:
        self._current_state = state
        self._import_btn.setEnabled(state == AppState.EDITING)
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
            case AppState.PAUSED:
                self._run_btn.setIcon(
                    style.standardIcon(QStyle.StandardPixmap.SP_MediaPlay)
                )

                self._run_btn.setEnabled(True)
            case AppState.INTERRUPTED:
                self._run_btn.setIcon(
                    style.standardIcon(QStyle.StandardPixmap.SP_MediaPlay)
                )

                self._run_btn.setEnabled(False)
