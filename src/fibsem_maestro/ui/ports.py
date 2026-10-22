# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF

"""
Types shared by the application layer and the forms.

The forms depend on these small protocols instead of on the application
services, so they can be built without a workflow (start-up dialog, tests).
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from PyQt6.QtCore import QObject, pyqtBoundSignal, pyqtSignal

from fibsem_maestro.action.action import Action
from fibsem_maestro.core.area import RelativeArea
from fibsem_maestro.core.beam_type import BeamType


@dataclass(frozen=True)
class PreviewRequest:
    """
    What an area selector needs imaged.

    Attributes:
        beam: Beam to image with; None for the microscope's active beam.
        offset_x_nm: Beam shift along x applied while grabbing, in nm (0.0 for none).
        previous_offset_nm: Offset of the image the selector currently shows, in nm;
            None if it shows none.
        crop: Scanning area to crop the result to, relative to the full frame;
            None for the full frame.
    """

    beam: BeamType | None
    offset_x_nm: float
    previous_offset_nm: float | None
    crop: RelativeArea | None


class TaskHandle(QObject):
    """
    The result of one microscope task.

    Exactly one of the two signals is emitted, once, on the GUI thread.
    Connect them to bound methods of a QObject: if that object is destroyed
    before the task ends, Qt drops the connection and the result is discarded.
    """

    succeeded = pyqtSignal(object)
    """The task's result (an `Image` for previews)."""

    failed = pyqtSignal(object)
    """The exception; `NotAllowedError` if the task was refused."""


class PreviewPort(Protocol):
    """Acquires the image an area selector draws on."""

    def grab(self, request: PreviewRequest) -> TaskHandle:
        """
        Start the acquisition.

        Args:
            request: What to image.

        Returns:
            The task's handle; a refusal is a handle that emits `failed`.
            Never raises.
        """
        ...


class PreviewPermission(Protocol):
    """Whether previews may be acquired right now."""

    @property
    def changed(self) -> pyqtBoundSignal:
        """Emitted whenever `preview_allowed()` may have changed."""
        ...

    def preview_allowed(self) -> bool:
        """True if an area selector may acquire an image now."""
        ...


class ActionCatalog(Protocol):
    """The workflow's actions, as seen by forms (action selectors, linked crops)."""

    @property
    def structure_changed(self) -> pyqtBoundSignal:
        """Emitted after actions were added, removed, reordered or renamed."""
        ...

    @property
    def action_renamed(self) -> pyqtBoundSignal:
        """Emitted with `(action, old_name)` after an action was renamed."""
        ...

    @property
    def actions(self) -> Sequence[Action]:
        """The actions, in workflow order."""
        ...
