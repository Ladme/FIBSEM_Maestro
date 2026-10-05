# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF

from typing import Protocol, TypeVar

from fibsem_maestro.core.beam_type import BeamType
from fibsem_maestro.settings.property_names import PropertyNames


class ActionSettingsLike(Protocol):
    """
    What the base `Action` requires of its settings.

    Satisfied structurally by any settings class declaring these fields.
    We are using a protocol instead of a base class since the order
    of fields in the settings is translated to the form in the GUI.
    """

    @property
    def beam_type(self) -> BeamType | None:
        """Beam the action works with, or `None` for both or neither."""
        ...

    @property
    def properties_to_collect(self) -> PropertyNames:
        """Names of the microscope properties the action collects."""
        ...

    @property
    def execution_frequency(self) -> int | None:
        """Run every N slices (slice 1 always runs), or `None` for never."""
        ...


TSettings = TypeVar("TSettings", bound=ActionSettingsLike)
