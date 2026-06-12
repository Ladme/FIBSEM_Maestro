# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from fibsem_maestro.action_context.file import FileActionContext
from fibsem_maestro.gui.connection._common import load_last_profile, save_last_profile
from fibsem_maestro.gui.connection._connect_worker import ConnectWorker
from fibsem_maestro.gui.connection._new_workflow import NewWorkflowScreen
from fibsem_maestro.gui.connection._resume_workflow import ResumeWorkflowScreen
from fibsem_maestro.gui.form_builder.builder import FormBuilder
from fibsem_maestro.microscope.microscope import Microscope
from fibsem_maestro.settings.microscope_settings import MicroscopeSettings


class ConnectionScreen(QDialog):
    """
    Startup dialog presented before the main window.

    On success, exposes the connected Microscope instance, the chosen
    workflow directory, and whether the session is a resumption.

    Args:
        parent: Parent widget.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("FIBSEM Maestro - Connect")
        self.setFixedWidth(480)
        self.setWindowFlags(
            self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint
        )

        self.microscope: Microscope | None = None
        self.workflow_dir: Path | None = None
        self.is_resuming: bool = False

        self._form_builder = FormBuilder()
        self._last_profile = load_last_profile()
        self._worker: ConnectWorker | None = None

        outer = QVBoxLayout(self)
        outer.setSpacing(16)
        outer.setContentsMargins(24, 24, 24, 24)

        # microscope mode selector
        mode_row = QHBoxLayout()
        self._new_btn = QPushButton("New workflow")
        self._new_btn.setCheckable(True)
        self._new_btn.setChecked(True)
        self._new_btn.clicked.connect(lambda: self._set_mode(0))
        mode_row.addWidget(self._new_btn)

        self._resume_btn = QPushButton("Resume workflow")
        self._resume_btn.setCheckable(True)
        self._resume_btn.clicked.connect(lambda: self._set_mode(1))
        mode_row.addWidget(self._resume_btn)
        outer.addLayout(mode_row)

        # stacked screens
        self._stack = QStackedWidget()

        self._new_screen = NewWorkflowScreen(
            last_profile=self._last_profile,
            form_builder=self._form_builder,
        )
        self._stack.addWidget(self._new_screen)

        self._resume_screen = ResumeWorkflowScreen()
        self._stack.addWidget(self._resume_screen)

        outer.addWidget(self._stack)

        # status label
        self._status_label = QLabel("")
        self._status_label.setStyleSheet("font-size: 11px; color: #888888;")
        self._status_label.setWordWrap(True)
        outer.addWidget(self._status_label)

        # connect button
        self._connect_btn = QPushButton("Connect")
        self._connect_btn.setDefault(True)
        self._connect_btn.clicked.connect(self._on_connect)
        outer.addWidget(self._connect_btn)

    def _set_mode(self, index: int) -> None:
        self._stack.setCurrentIndex(index)
        self._new_btn.setChecked(index == 0)
        self._resume_btn.setChecked(index == 1)
        self._status_label.setText("")

    def _on_connect(self) -> None:
        self._status_label.setText("")

        if self._stack.currentIndex() == 0:
            self._connect_new()
        else:
            self._connect_resume()

    def _connect_new(self) -> None:
        """Validate fields, pick a save directory, and attempt connection."""
        values = self._new_screen.get_connection_values()

        try:
            partial_settings = MicroscopeSettings(
                control=values["control"],
                ip_address=values["ip_address"],
            )
        except Exception as e:
            self._status_label.setText(f"Invalid settings: {e}")
            return

        # ask for save directory
        path = QFileDialog.getExistingDirectory(self, "Choose workflow save directory")
        if not path:
            return
        self.workflow_dir = Path(path)
        self.is_resuming = False

        self._attempt_connection(partial_settings)

    def _connect_resume(self) -> None:
        """Load profile from snapshot directory and attempt connection."""
        settings = self._resume_screen.load_profile()
        if settings is None:
            return
        self.workflow_dir = self._resume_screen.get_workflow_dir()
        self.is_resuming = True
        self._attempt_connection(settings)

    def _attempt_connection(self, settings: MicroscopeSettings) -> None:
        """Start a worker thread to construct the Microscope instance."""
        self._connect_btn.setEnabled(False)
        self._status_label.setText("Connecting...")

        # TODO: connect properly to workflow
        self._worker = ConnectWorker(
            settings,
            FileActionContext(
                action_dir=self.workflow_dir / "workflow", name="workflow"
            ),
        )
        self._worker.succeeded.connect(self._on_success)
        self._worker.failed.connect(self._on_failure)
        self._worker.start()

    def _on_success(self, microscope: Microscope) -> None:
        self.microscope = microscope
        save_last_profile(microscope.settings)
        self._connect_btn.setEnabled(True)
        self.accept()

    def _on_failure(self, error: str) -> None:
        self._status_label.setText(f"Connection failed: {error}")
        self._connect_btn.setEnabled(True)
