# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


import shutil
from pathlib import Path
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from fibsem_maestro.action_context.file import FileActionContext
from fibsem_maestro.gui.connection._common import (
    load_last_email_settings,
    load_last_microscope_profile,
    save_last_email_settings,
    save_last_microscope_profile,
)
from fibsem_maestro.gui.connection._email_setup import EmailSetupDialog
from fibsem_maestro.gui.connection._new_workflow import NewWorkflowScreen
from fibsem_maestro.gui.connection._resume_workflow import ResumeWorkflowScreen
from fibsem_maestro.gui.form_builder.builder import FormBuilder
from fibsem_maestro.logging.text.contextual import ContextualTextLogger
from fibsem_maestro.microscope.microscope import Microscope
from fibsem_maestro.notifications.email_notifier import SMTPEmailNotifier
from fibsem_maestro.notifications.null_notifier import NullNotifier
from fibsem_maestro.workflow.actions import Actions
from fibsem_maestro.workflow.propagations import Propagations
from fibsem_maestro.workflow.workflow import Workflow

if TYPE_CHECKING:
    from fibsem_maestro.settings.notification_settings import SMTPEmailSettings


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

        self.workflow_dir: Path | None = None
        self.workflow: Workflow | None = None

        self.setWindowTitle("FIBSEM Maestro - Connect")
        self.setFixedWidth(480)
        self.setWindowFlags(
            self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint
        )

        self._form_builder = FormBuilder()
        self._last_microscope_profile = load_last_microscope_profile()

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
            last_microscope_profile=self._last_microscope_profile,
            form_builder=self._form_builder,
        )
        self._stack.addWidget(self._new_screen)

        self._resume_screen = ResumeWorkflowScreen()
        self._stack.addWidget(self._resume_screen)

        outer.addWidget(self._stack)

        # e-mail notifications
        self.email_settings: SMTPEmailSettings | None = None

        self._email_check = QCheckBox("E-mail me if a run fails")
        self._email_check.toggled.connect(self._on_email_toggled)
        outer.addWidget(self._email_check)

        self._email_summary = QLabel()
        self._email_summary.setWordWrap(True)
        self._email_summary.setVisible(False)
        outer.addWidget(self._email_summary)

        # connect button
        self._connect_btn = QPushButton("Connect")
        self._connect_btn.setDefault(True)
        self._connect_btn.clicked.connect(self._on_connect)
        outer.addWidget(self._connect_btn)

    def _set_mode(self, index: int) -> None:
        self._stack.setCurrentIndex(index)
        self._new_btn.setChecked(index == 0)
        self._resume_btn.setChecked(index == 1)

    def _on_connect(self) -> None:
        if self._stack.currentIndex() == 0:
            self._connect_new()
        else:
            self._connect_resume()

    def _connect_new(self) -> None:
        """Validate fields, pick a save directory, and attempt connection."""
        try:
            settings = self._new_screen.get_microscope_settings()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Invalid settings: {str(e)}")
            return

        # ask for save directory
        path = QFileDialog.getExistingDirectory(self, "Choose workflow save directory")
        if not path:
            return

        self.workflow_dir = Path(path)

        # warn if directory is not empty
        if any(self.workflow_dir.iterdir()):
            answer = QMessageBox.warning(
                self,
                "Directory not empty",
                "The selected directory is not empty. Assigning it to a workflow will PERMANENTLY delete all its contents.\n\nAre you sure you want to continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return

        # clear the workflow directory
        for item in self.workflow_dir.iterdir():
            shutil.rmtree(item) if item.is_dir() else item.unlink()

        self._workflow_context = FileActionContext(
            action_dir=self.workflow_dir / "workflow",
            name="workflow",
        )

        # attempt to connect to the microscope
        self._connect_btn.setEnabled(False)
        try:
            microscope = Microscope(
                settings,
                ContextualTextLogger(
                    fallback=self._workflow_context.text_logger
                ).derive("microscope"),
            )
            self.workflow = Workflow(
                microscope,
                Actions(),
                Propagations(),
                self._workflow_context,
                notifier=SMTPEmailNotifier(self.email_settings)
                if self.email_settings is not None
                else NullNotifier(),
            )
            save_last_microscope_profile(microscope.settings)
            self._connect_btn.setEnabled(True)
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Connection failed: {str(e)}")
            self._connect_btn.setEnabled(True)

    def _connect_resume(self) -> None:
        """Load workflow and attempt connection to the microscope."""

        if not (workflow_dir := self._resume_screen.get_workflow_dir()):
            QMessageBox.critical(self, "Error", "No workflow directory selected")
            return
        self.workflow_dir = workflow_dir

        self._connect_btn.setEnabled(False)

        try:
            self.workflow = Workflow.import_from_dir_with_state(
                workflow_dir,
                notifier=SMTPEmailNotifier(self.email_settings)
                if self.email_settings is not None
                else NullNotifier(),
            )
            save_last_microscope_profile(self.workflow.microscope.settings)
            self._connect_btn.setEnabled(True)
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Loading failed: {str(e)}")
            self._connect_btn.setEnabled(True)

    def _on_email_toggled(self, checked: bool) -> None:
        """
        Open the setup dialog when enabled, clear the settings when not.

        Args:
            checked: New state of the checkbox.
        """
        if not checked:
            self.email_settings = None
            self._email_summary.setVisible(False)
            return

        dialog = EmailSetupDialog(self, previous=load_last_email_settings())
        if dialog.exec() != QDialog.DialogCode.Accepted:
            self._email_check.setChecked(False)
            return

        self.email_settings = dialog.settings
        assert self.email_settings is not None
        save_last_email_settings(self.email_settings)
        self._email_summary.setText(
            "E-mails will be sent to " + ", ".join(self.email_settings.recipients)
        )
        self._email_summary.setVisible(True)
