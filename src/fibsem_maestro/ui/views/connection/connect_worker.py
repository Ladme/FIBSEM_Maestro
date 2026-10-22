# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF

"""Connecting to the microscope and building the workflow, off the GUI thread."""

from dataclasses import dataclass
from pathlib import Path

from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot

from fibsem_maestro.action_context.file import FileActionContext
from fibsem_maestro.logging.text.contextual import ContextualTextLogger
from fibsem_maestro.microscope.microscope import Microscope
from fibsem_maestro.notifications.email_notifier import SMTPEmailNotifier
from fibsem_maestro.notifications.notification_service import NotificationService
from fibsem_maestro.notifications.null_notifier import NullNotifier
from fibsem_maestro.settings.microscope_settings import MicroscopeSettings
from fibsem_maestro.settings.notification_settings import SMTPEmailSettings
from fibsem_maestro.ui.app.catalogs import MicroscopeCatalogs
from fibsem_maestro.ui.app.session import SessionSeed
from fibsem_maestro.workflow.actions import Actions
from fibsem_maestro.workflow.propagations import Propagations
from fibsem_maestro.workflow.workflow import Workflow


@dataclass(frozen=True)
class NewWorkflowRequest:
    """
    Connect with the given settings and start an empty workflow.

    Attributes:
        settings: The microscope settings to connect with.
        workflow_dir: The (cleared) directory of the new workflow.
        email: SMTP settings for run-failure e-mails, or None for none.
    """

    settings: MicroscopeSettings
    workflow_dir: Path
    email: SMTPEmailSettings | None


@dataclass(frozen=True)
class ResumeWorkflowRequest:
    """
    Load a workflow from its directory and connect with its microscope settings.

    Attributes:
        workflow_dir: The directory of the workflow to resume.
        email: SMTP settings for run-failure e-mails, or None for none.
    """

    workflow_dir: Path
    email: SMTPEmailSettings | None


ConnectRequest = NewWorkflowRequest | ResumeWorkflowRequest
"""What the start-up dialog asks the worker to do."""


def _notifier(email: SMTPEmailSettings | None) -> NotificationService:
    return SMTPEmailNotifier(email) if email is not None else NullNotifier()


def connect(request: ConnectRequest) -> SessionSeed:
    """
    Connect to the microscope and build the workflow a request describes.

    Blocks for as long as the connection takes; runs on the connect thread.

    Args:
        request: A new or a resumed workflow.

    Returns:
        The workflow, its directory and the microscope catalogs.

    Raises:
        Exception: Whatever connecting or loading raises.
    """
    if isinstance(request, NewWorkflowRequest):
        workflow_context = FileActionContext(
            action_dir=request.workflow_dir / "workflow",
            name="workflow",
        )
        microscope = Microscope(
            request.settings,
            ContextualTextLogger(fallback=workflow_context.text_logger).derive(
                "microscope"
            ),
        )
        workflow = Workflow(
            microscope,
            Actions(),
            Propagations(),
            workflow_context,
            notifier=_notifier(request.email),
        )
    else:
        workflow = Workflow.import_from_dir_with_state(
            request.workflow_dir, notifier=_notifier(request.email)
        )

    catalogs = MicroscopeCatalogs.query(workflow.microscope)
    return SessionSeed(
        workflow=workflow, workflow_dir=request.workflow_dir, catalogs=catalogs
    )


class ConnectWorker(QObject):
    """
    Connects on its own thread and reports the outcome.

    Lives on the connect thread; it touches no widget. `run` is invoked with a
    queued call, and ends with `done` whatever the outcome.

    Args:
        request: What to connect to and build.
    """

    succeeded = pyqtSignal(object)
    """The `SessionSeed`."""

    failed = pyqtSignal(object)
    """The exception connecting or loading raised."""

    done = pyqtSignal()
    """Emitted last, after `succeeded` or `failed`."""

    def __init__(self, request: ConnectRequest) -> None:
        super().__init__()
        self._request = request

    @pyqtSlot()
    def run(self) -> None:
        """Connect and build the workflow, then emit the outcome and `done`."""
        try:
            seed = connect(self._request)
        except Exception as e:
            self.failed.emit(e)
        else:
            self.succeeded.emit(seed)
        finally:
            self.done.emit()
