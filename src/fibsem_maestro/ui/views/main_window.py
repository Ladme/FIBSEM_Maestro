# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF

"""The main window: top bar, action list, action panel and log panel; run errors; exit."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QMainWindow,
    QMessageBox,
    QScrollArea,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from fibsem_maestro.ui.app.run_state import AppState
from fibsem_maestro.ui.views.action_list.view import ActionListView
from fibsem_maestro.ui.views.common import horizontal_separator
from fibsem_maestro.ui.views.danger_banner import DangerBanner
from fibsem_maestro.ui.views.dialogs.action_error import ActionErrorDialog
from fibsem_maestro.ui.views.log_panel.view import LogPanel
from fibsem_maestro.ui.views.top_bar import TopBar
from fibsem_maestro.workflow.error import ActionError

if TYPE_CHECKING:
    from PyQt6.QtGui import QCloseEvent

    from fibsem_maestro.action.action import Action
    from fibsem_maestro.ui.app.action_status import ActionStatus
    from fibsem_maestro.ui.app.commands import AppCommands
    from fibsem_maestro.ui.app.edit_policy import EditPolicy, Permissions
    from fibsem_maestro.ui.app.files import WorkflowFiles
    from fibsem_maestro.ui.app.readiness import Readiness
    from fibsem_maestro.ui.app.run_controller import RunController
    from fibsem_maestro.ui.app.session import WorkflowSession
    from fibsem_maestro.ui.composition import FormContexts
    from fibsem_maestro.ui.forms.builder import FormBuilder
    from fibsem_maestro.ui.views.action_panel.host import ActionPanelHost
    from fibsem_maestro.workflow.error_choice import ErrorChoice


class MainWindow(QMainWindow):
    """
    The main window.

    Lays out the top bar, the danger banner, the action list, the action panel
    host and the log panel; routes the list's selection to the host; shows the
    run's error dialogs; and ends the process when closed.

    Args:
        session: The workflow session.
        run: The run controller.
        policy: The permissions and danger mode.
        readiness: Why the workflow cannot run, if it cannot.
        status: The per-action indicators.
        commands: Every user intent.
        host: Shows the selected action's panel.
        form_builder: Builds forms (the microscope settings dialog).
        form_contexts: The environments of forms.
        files: Filesystem queries (the top bar's "New workflow").
        parent: Parent widget.
    """

    def __init__(
        self,
        session: WorkflowSession,
        run: RunController,
        policy: EditPolicy,
        readiness: Readiness,
        status: ActionStatus,
        commands: AppCommands,
        host: ActionPanelHost,
        form_builder: FormBuilder,
        form_contexts: FormContexts,
        files: WorkflowFiles,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._run = run
        self._policy = policy
        self._commands = commands
        self._host = host
        self._error_dialog: ActionErrorDialog | None = None
        self._workflow_error_dialog: ActionErrorDialog | None = None
        self._terminating = False

        self.setWindowTitle("FIBSEM Maestro")
        self.setGeometry(self.screen().availableGeometry())

        root = QWidget()
        self.setCentralWidget(root)
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self._top_bar = TopBar(
            session=session,
            run=run,
            policy=policy,
            readiness=readiness,
            commands=commands,
            files=files,
            form_builder=form_builder,
            form_contexts=form_contexts,
        )
        root_layout.addWidget(self._top_bar)

        self._danger_banner = DangerBanner()
        policy.danger_mode_changed.connect(self._danger_banner.setVisible)
        self._danger_banner.setVisible(policy.danger_mode)
        root_layout.addWidget(self._danger_banner)

        root_layout.addWidget(horizontal_separator())

        v_splitter = QSplitter(Qt.Orientation.Vertical)
        root_layout.addWidget(v_splitter)

        h_splitter = QSplitter(Qt.Orientation.Horizontal)
        v_splitter.addWidget(h_splitter)

        self._action_list = ActionListView(
            session=session, status=status, policy=policy, commands=commands
        )

        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_scroll.setMinimumWidth(120)
        h_splitter.addWidget(left_scroll)
        left_scroll.setWidget(self._action_list)

        h_splitter.addWidget(host)

        h_splitter.setStretchFactor(0, 1)
        h_splitter.setStretchFactor(1, 4)

        self._log_panel = LogPanel(session=session, run=run)
        v_splitter.addWidget(self._log_panel)
        v_splitter.setStretchFactor(0, 1)
        v_splitter.setStretchFactor(1, 0)

        h_splitter.setSizes([300, 1080])

        self._action_list.current_action_changed.connect(self._on_current_action)
        run.action_failed.connect(self._on_action_failed)
        run.workflow_failed.connect(self._on_workflow_failed)
        run.state_changed.connect(self._on_run_state_changed)
        policy.changed.connect(self._on_permissions_changed)

    # --- parts (for tests and tools) --------------------------------------------------

    @property
    def top_bar(self) -> TopBar:
        """The top bar."""
        return self._top_bar

    @property
    def danger_banner(self) -> DangerBanner:
        """The danger-mode banner."""
        return self._danger_banner

    @property
    def action_list(self) -> ActionListView:
        """The action list."""
        return self._action_list

    @property
    def panel_host(self) -> ActionPanelHost:
        """The stack of action panels."""
        return self._host

    @property
    def log_panel(self) -> LogPanel:
        """The log panel."""
        return self._log_panel

    @property
    def error_dialog(self) -> ActionErrorDialog | None:
        """The open action-error dialog, if any."""
        return self._error_dialog

    @property
    def workflow_error_dialog(self) -> ActionErrorDialog | None:
        """The open workflow-error dialog, if any."""
        return self._workflow_error_dialog

    # --- selection --------------------------------------------------------------------

    def _on_current_action(self, action: Action | None) -> None:
        self._host.show_action(action)

    # --- run errors -------------------------------------------------------------------

    def _on_action_failed(self, error: ActionError) -> None:
        """A specific action failed; offer retry / skip / skip and pause."""
        dialog = ActionErrorDialog(error.message, error.action.name, parent=self)
        dialog.set_choices_enabled(self._policy.permissions.error_choice_enabled)
        dialog.choice_made.connect(self._on_error_choice)
        dialog.skip_and_pause_chosen.connect(self._on_skip_and_pause)
        dialog.finished.connect(self._on_error_dialog_finished)
        self._error_dialog = dialog
        dialog.show()

    def _on_error_choice(self, choice: ErrorChoice) -> None:
        self._commands.choose_error_option(choice)

    def _on_skip_and_pause(self) -> None:
        self._commands.skip_and_pause()

    def _on_error_dialog_finished(self) -> None:
        dialog = self.sender()
        if dialog is self._error_dialog:
            self._error_dialog = None
        if isinstance(dialog, ActionErrorDialog):
            dialog.deleteLater()

    def _on_permissions_changed(self, permissions: Permissions) -> None:
        if self._error_dialog is not None:
            self._error_dialog.set_choices_enabled(permissions.error_choice_enabled)

    def _on_run_state_changed(self, state: AppState) -> None:
        # Reset and New workflow abandon an interrupted run and end in EDITING; a
        # choice made in the dialog leads to RUNNING or STOPPING, never here, so
        # this cannot re-enter the dialog's own handler. close() would not work:
        # the dialog ignores close events and Esc for action errors.
        if state is AppState.EDITING and self._error_dialog is not None:
            self._error_dialog.accept()

    def _on_workflow_failed(self, error: Exception) -> None:
        if isinstance(error, ActionError):
            # the user already answered this at the action error dialog
            self._terminate()
            return

        dialog = ActionErrorDialog(str(error), None, parent=self)
        # the only button is terminate, so any dismissal terminates
        dialog.finished.connect(self._on_workflow_error_dialog_finished)
        self._workflow_error_dialog = dialog
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()

    def _on_workflow_error_dialog_finished(self) -> None:
        self._workflow_error_dialog = None
        self._terminate()

    def _terminate(self) -> None:
        self._commands.terminate()
        self._terminating = True
        self.close()

    # --- exit -------------------------------------------------------------------------

    def closeEvent(self, a0: QCloseEvent | None) -> None:
        """
        End the process, asking first while the workflow or a microscope task runs.

        The process ends with `os._exit(0)` after the log files were closed.
        """
        if not self._terminating and not self._confirm_quit():
            if a0 is not None:
                a0.ignore()
            return

        self._commands.prepare_exit()
        # The hard exit is deliberate. The run worker or the microscope task
        # thread can be blocked inside an Autoscript call that cannot be
        # interrupted (a milling job, a long acquisition); a normal interpreter
        # exit joins non-daemon threads and would hang, and atexit handlers and
        # finalisers would run against a half-used Autoscript client. Waiting
        # for a pause can take minutes, and QThread.terminate() can kill a thread
        # holding a lock or half-way through writing a file. The confirmation
        # above and the flushed log files cover what a clean exit would add.
        os._exit(0)

    def _confirm_quit(self) -> bool:
        """
        Ask whether to quit while the workflow or a microscope task runs.

        Returns:
            True if nothing runs or the user chose to quit anyway.
        """
        if self._run.state.is_running:
            subject = "The workflow"
        elif self._policy.permissions.task_busy:
            subject = "A microscope task"
        else:
            return True

        answer = QMessageBox.warning(
            self,
            "Quit FIBSEM Maestro",
            f"{subject} is still running. Quitting now stops it immediately, "
            "possibly in the middle of a microscope operation, and the current "
            "slice may be incomplete.\n\nQuit anyway?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        return answer == QMessageBox.StandardButton.Yes
