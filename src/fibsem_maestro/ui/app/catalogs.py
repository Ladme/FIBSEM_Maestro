# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF

"""What the connected microscope offers to choose from, read once per session."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Self

if TYPE_CHECKING:
    from fibsem_maestro.core.pattern_type import PatternType
    from fibsem_maestro.logging.text.text_logger import TextLogger
    from fibsem_maestro.microscope.microscope import Microscope


@dataclass(frozen=True)
class MicroscopeCatalogs:
    """
    Choice lists that depend on the connected microscope.

    Attributes:
        manufacturer_property_names: Manufacturer-specific property names of the
            microscope control, offered by the property selectors.
        pattern_types: Milling pattern types the microscope offers.
    """

    manufacturer_property_names: tuple[str, ...] = ()
    pattern_types: tuple[PatternType, ...] = ()

    @classmethod
    def query(cls, microscope: Microscope, log: TextLogger | None = None) -> Self:
        """
        Read the catalogs from the microscope.

        Called once per session, right after connecting and off the GUI thread.
        A list that cannot be read is logged as a warning and left empty, so a
        catalog problem never fails the connection.

        Args:
            microscope: The connected microscope.
            log: Receives the warnings; defaults to the microscope's logger,
                which writes to the workflow log.

        Returns:
            The catalogs.
        """
        log = log if log is not None else microscope.txt_log

        try:
            names = tuple(microscope.control.manufacturer_prop_names)
        except Exception as e:
            log.warning(f"Could not read the manufacturer property names: {e}")
            names = ()

        try:
            patterns = tuple(microscope.control.available_patterns)
        except Exception as e:
            log.warning(f"Could not read the available pattern types: {e}")
            patterns = ()

        return cls(manufacturer_property_names=names, pattern_types=patterns)
