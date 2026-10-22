# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF

"""Real workflows on the simulated microscope."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fibsem_maestro.action_context.file import FileActionContext
from fibsem_maestro.logging.text.contextual import ContextualTextLogger
from fibsem_maestro.microscope.microscope import Microscope
from fibsem_maestro.settings.microscope_settings import MicroscopeSettings
from fibsem_maestro.ui.app.catalogs import MicroscopeCatalogs
from fibsem_maestro.ui.app.session import SessionSeed
from fibsem_maestro.workflow.actions import Actions
from fibsem_maestro.workflow.propagations import Propagations
from fibsem_maestro.workflow.workflow import Workflow

if TYPE_CHECKING:
    from pathlib import Path


def simulated_workflow(workflow_dir: Path) -> Workflow:
    """
    An empty workflow on a freshly connected simulated microscope.

    Args:
        workflow_dir: The workflow directory; the workflow's own files go to its `workflow/`.

    Returns:
        The workflow.
    """
    ctx = FileActionContext(workflow_dir / "workflow", "workflow")
    microscope = Microscope(
        MicroscopeSettings(control="simulated", ip_address="localhost"),
        ContextualTextLogger(fallback=ctx.text_logger).derive("microscope"),
    )
    return Workflow(microscope, Actions(), Propagations(), ctx)


def seed_for(workflow: Workflow, workflow_dir: Path) -> SessionSeed:
    """
    What the start-up dialog hands to the main window, for an existing workflow.

    Args:
        workflow: The workflow.
        workflow_dir: Its directory.

    Returns:
        The seed, with the catalogs queried from the workflow's microscope.
    """
    return SessionSeed(
        workflow, workflow_dir, MicroscopeCatalogs.query(workflow.microscope)
    )
