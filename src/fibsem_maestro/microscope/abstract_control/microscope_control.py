# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from abc import ABC, abstractmethod
from typing import Any

from fibsem_maestro.core.stage_position import StagePosition
from fibsem_maestro.logging.text.text_logger import TextLogger
from fibsem_maestro.microscope.abstract_control.beam_control import BeamControl


class MicroscopeControl(ABC):
    """
    Abstract interface for controlling a microscope and its major subsystems.

    Args:
        ip_address: Network address of the microscope server.
        txt_log: Logger for diagnostic and status messages.
    """

    @abstractmethod
    def __init__(self, ip_address: str, port: int | None, txt_log: TextLogger):
        """
        Initialize the microscope control interface.

        Args:
            ip_address: Network address of the microscope server.
            port: Port number of the microscope server.
                If None, the default port is used.
            txt_log: Logger for diagnostic and status messages.
        """

    @property
    @abstractmethod
    def stage_position(self) -> StagePosition:
        """Current stage position in nanometers and degrees."""

    @property
    @abstractmethod
    def electron_beam(self) -> BeamControl:
        """Control interface for the electron beam."""

    @electron_beam.setter
    @abstractmethod
    def electron_beam(self, beam: BeamControl) -> None:
        """
        Replace the electron beam control interface.

        Args:
            beam: New electron beam control implementation.
        """

    @property
    @abstractmethod
    def ion_beam(self) -> BeamControl:
        """Control interface for the ion beam."""

    @ion_beam.setter
    @abstractmethod
    def ion_beam(self, beam: BeamControl) -> None:
        """
        Replace the ion beam control interface.

        Args:
            beam: New ion beam control implementation.
        """

    @abstractmethod
    def manufacturer_prop(self, name: str) -> Any:
        """
        Retrieve a manufacturer-specific microscope property by name.

        Args:
            name: Property name as defined by the manufacturer.

        Returns:
            The current value of the property.
        """

    @abstractmethod
    def set_manufacturer_prop(self, name: str, value: Any) -> None:
        """
        Set a manufacturer-specific microscope property by name.

        Args:
            name: Property name as defined by the manufacturer.
            value: New property value.
        """

    @property
    @abstractmethod
    def manufacturer_prop_names(self) -> list[str]:
        """Names of all manufacturer-specific properties available on this microscope."""

    @abstractmethod
    def try_set_stage_position(self, pos: StagePosition) -> StagePosition:
        """
        Attempt to move the stage to an absolute position.

        Args:
            pos: Target stage position in nanometers and degrees.

        Returns:
            The actual stage position after the operation, which may differ
            from the requested position due to hardware limitations.
        """

    @abstractmethod
    def try_move_stage_position(self, delta: StagePosition) -> StagePosition:
        """
        Attempt to move the stage by a relative offset.

        Args:
            delta: Relative stage movement in nanometers and degrees.

        Returns:
            The actual stage position after the operation, which may differ
            from the expected position due to hardware limitations.
        """
