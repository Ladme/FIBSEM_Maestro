# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF

"""The start-up dialog: connect to the microscope and start or resume a workflow."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from PyQt6.QtCore import QMetaObject, Qt, QThread
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from fibsem_maestro.ui.forms.builder import FormBuilder
from fibsem_maestro.ui.forms.registry import default_registry
from fibsem_maestro.ui.views.connection import workflow_directory
from fibsem_maestro.ui.views.connection.connect_worker import (
    ConnectRequest,
    ConnectWorker,
    NewWorkflowRequest,
    ResumeWorkflowRequest,
)
from fibsem_maestro.ui.views.connection.email_dialog import EmailSetupDialog
from fibsem_maestro.ui.views.connection.new_page import NewWorkflowPage
from fibsem_maestro.ui.views.connection.resume_page import ResumeWorkflowPage

if TYPE_CHECKING:
    from PyQt6.QtGui import QCloseEvent

    from fibsem_maestro.settings.notification_settings import SMTPEmailSettings
    from fibsem_maestro.ui.app.files import WorkflowFiles
    from fibsem_maestro.ui.app.session import SessionSeed
    from fibsem_maestro.ui.app.user_config import UserConfig


class ConnectionDialog(QDialog):
    """
    Startup dialog presented before the main window.

    Connecting runs on a thread of its own; meanwhile every input is disabled,
    the wait cursor is shown, Esc is ignored and closing asks before quitting
    the process. On success the dialog is accepted and `seed` holds the
    workflow, its directory and the microscope catalogs.

    Args:
        user_config: The last microscope and e-mail profiles.
        files: Filesystem operations (clearing the new workflow's directory).
        parent: Parent widget.
    """

    def __init__(
        self,
        user_config: UserConfig,
        files: WorkflowFiles,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._user_config = user_config
        self._files = files

        self._seed: SessionSeed | None = None
        self._email_settings: SMTPEmailSettings | None = None

        # the connection in progress, if any
        self._thread: QThread | None = None
        # the worker has no Qt parent (it is moved to the thread), so this
        # reference keeps it alive until the thread's `finished` deletes it
        self._worker: ConnectWorker | None = None
        self._connect_error: Exception | None = None
        self._connect_seed: SessionSeed | None = None
        self._failure_text = ""

        self.setWindowTitle("FIBSEM Maestro - Connect")
        self.setFixedWidth(480)
        self.setWindowFlags(
            self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint
        )

        form_builder = FormBuilder(default_registry())

        outer = QVBoxLayout(self)
        outer.setSpacing(16)
        outer.setContentsMargins(24, 24, 24, 24)

        mode_row = QHBoxLayout()
        self._new_btn = QPushButton("New workflow")
        self._new_btn.setCheckable(True)
        self._new_btn.setChecked(True)
        self._new_btn.clicked.connect(self._on_new_mode)
        mode_row.addWidget(self._new_btn)

        self._resume_btn = QPushButton("Resume workflow")
        self._resume_btn.setCheckable(True)
        self._resume_btn.clicked.connect(self._on_resume_mode)
        mode_row.addWidget(self._resume_btn)
        outer.addLayout(mode_row)

        self._stack = QStackedWidget()

        self._new_page = NewWorkflowPage(
            last_microscope_profile=user_config.load_microscope_profile(),
            form_builder=form_builder,
        )
        self._stack.addWidget(self._new_page)

        self._resume_page = ResumeWorkflowPage()
        self._stack.addWidget(self._resume_page)

        outer.addWidget(self._stack)

        self._email_check = QCheckBox("E-mail me if a run fails")
        self._email_check.toggled.connect(self._on_email_toggled)
        outer.addWidget(self._email_check)

        self._email_summary = QLabel()
        self._email_summary.setWordWrap(True)
        self._email_summary.setVisible(False)
        outer.addWidget(self._email_summary)

        self._connect_btn = QPushButton("Connect")
        self._connect_btn.setDefault(True)
        self._connect_btn.clicked.connect(self._on_connect)
        outer.addWidget(self._connect_btn)

    @property
    def email_settings(self) -> SMTPEmailSettings | None:
        """The e-mail settings entered for this session (password included), if enabled."""
        return self._email_settings

    @property
    def email_check(self) -> QCheckBox:
        """The "E-mail me if a run fails" check box."""
        return self._email_check

    @property
    def email_summary(self) -> QLabel:
        """The label naming the e-mail recipients, shown while e-mails are enabled."""
        return self._email_summary

    @property
    def seed(self) -> SessionSeed | None:
        """What the main window is built from, once the dialog was accepted."""
        return self._seed

    @property
    def connecting(self) -> bool:
        """Whether a connection attempt is in progress."""
        return self._thread is not None

    @property
    def new_page(self) -> NewWorkflowPage:
        """The page for a new workflow."""
        return self._new_page

    @property
    def resume_page(self) -> ResumeWorkflowPage:
        """The page for resuming a workflow."""
        return self._resume_page

    def set_mode(self, index: int) -> None:
        """
        Show the new-workflow (0) or the resume (1) page.

        Args:
            index: The page index.
        """
        self._stack.setCurrentIndex(index)
        self._new_btn.setChecked(index == 0)
        self._resume_btn.setChecked(index == 1)

    def _on_new_mode(self) -> None:
        self.set_mode(0)

    def _on_resume_mode(self) -> None:
        self.set_mode(1)

    def _on_connect(self) -> None:
        if self._stack.currentIndex() == 0:
            self._connect_new()
        else:
            self._connect_resume()

    def _connect_new(self) -> None:
        """Validate fields, pick and clear a save directory, and connect."""
        try:
            settings = self._new_page.get_microscope_settings()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Invalid settings: {str(e)}")
            return

        directory = workflow_directory.choose_new(self, self._files)
        if directory is None:
            return

        # cleared before connecting: the microscope logs into the workflow directory
        if not workflow_directory.clear(self, self._files, directory):
            return

        self._start(
            NewWorkflowRequest(settings, directory, self._email_settings),
            "Connection failed",
        )

    def _connect_resume(self) -> None:
        """Load the workflow and connect to its microscope."""
        if not (workflow_dir := self._resume_page.get_workflow_dir()):
            QMessageBox.critical(self, "Error", "No workflow directory selected")
            return

        self._start(
            ResumeWorkflowRequest(workflow_dir, self._email_settings), "Loading failed"
        )

    def _start(self, request: ConnectRequest, failure_text: str) -> None:
        """Connect on a fresh thread; the outcome arrives in the handlers below."""
        thread = QThread()
        thread.setObjectName("microscope-connect")
        worker = ConnectWorker(request)
        worker.moveToThread(thread)

        worker.succeeded.connect(self._on_connect_succeeded)
        worker.failed.connect(self._on_connect_failed)
        worker.done.connect(self._on_connect_done)
        # deleted on its own thread while that thread's event loop still runs
        thread.finished.connect(worker.deleteLater)

        self._thread = thread
        self._worker = worker
        self._connect_error = None
        self._connect_seed = None
        self._failure_text = failure_text

        self._set_inputs_enabled(False)
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        thread.start()
        QMetaObject.invokeMethod(worker, "run", Qt.ConnectionType.QueuedConnection)

    def _on_connect_succeeded(self, seed: SessionSeed) -> None:
        self._connect_seed = seed

    def _on_connect_failed(self, error: Exception) -> None:
        self._connect_error = error

    def _on_connect_done(self) -> None:
        """Join the connect thread and finish the attempt."""
        if self._thread is not None:
            self._thread.quit()
            self._thread.wait()
            self._thread.deleteLater()
        self._thread = None
        self._worker = None
        QApplication.restoreOverrideCursor()

        if self._connect_seed is None:
            self._set_inputs_enabled(True)
            QMessageBox.critical(
                self, "Error", f"{self._failure_text}: {str(self._connect_error)}"
            )
            return

        self._seed = self._connect_seed
        self._user_config.save_microscope_profile(
            self._seed.workflow.microscope.settings
        )
        self.accept()

    def _set_inputs_enabled(self, enabled: bool) -> None:
        for widget in (
            self._new_btn,
            self._resume_btn,
            self._stack,
            self._email_check,
            self._connect_btn,
        ):
            widget.setEnabled(enabled)

    def reject(self) -> None:
        """Esc: ignored while connecting; otherwise closes the dialog."""
        if self.connecting:
            return
        super().reject()

    def closeEvent(self, a0: QCloseEvent | None) -> None:
        """While connecting, ask before quitting; the connection cannot be interrupted."""
        if not self.connecting:
            if a0 is not None:
                super().closeEvent(a0)
            return

        if a0 is not None:
            a0.ignore()
        answer = QMessageBox.warning(
            self,
            "Quit FIBSEM Maestro",
            "Still connecting to the microscope. Quit anyway?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if answer == QMessageBox.StandardButton.Yes:
            # a hung Autoscript connect cannot be interrupted, and a normal exit
            # would wait for the connect thread forever
            os._exit(0)

    def _on_email_toggled(self, checked: bool) -> None:
        """
        Open the setup dialog when enabled, clear the settings when not.

        Args:
            checked: New state of the checkbox.
        """
        if not checked:
            self._email_settings = None
            self._email_summary.setVisible(False)
            return

        dialog = EmailSetupDialog(self, previous=self._user_config.load_email_profile())
        if dialog.exec() != QDialog.DialogCode.Accepted:
            self._email_check.setChecked(False)
            return

        settings = dialog.settings
        assert settings is not None
        self._email_settings = settings
        self._user_config.save_email_profile(settings)
        self._email_summary.setText(
            "E-mails will be sent to " + ", ".join(settings.recipients)
        )
        self._email_summary.setVisible(True)
