# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from abc import ABC, abstractmethod
from typing import Any

from fibsem_maestro.core.beam_shift import BeamShift
from fibsem_maestro.core.beam_type import BeamType
from fibsem_maestro.core.stage_position import StagePosition
from fibsem_maestro.logging.text.text_logger import TextLogger
from fibsem_maestro.microscope.abstract_control.beam_control import BeamControl
from fibsem_maestro.settings.microscope_properties import MicroscopeProperties


class MicroscopeControl(ABC):
    """
    Abstract interface for controlling a microscope and its major subsystems.
    """

    @abstractmethod
    def __init__(self, ip_address: str, txt_log: TextLogger):
        """
        Initialize the microscope control interface.

        Args:
            ip_address (str): Network address of the microscope.
            txt_log (TextLogger): Logger for recording events.
        """
        pass

    @property
    @abstractmethod
    def stage_position(self) -> StagePosition:
        """
        Get the current stage position.

        Returns:
            StagePosition: Current stage position.
        """
        pass

    @property
    @abstractmethod
    def electron_beam(self) -> BeamControl:
        """
        Get the electron beam control interface.

        Returns:
            BeamControl: Electron beam control.
        """
        pass

    @electron_beam.setter
    @abstractmethod
    def electron_beam(self, beam: BeamControl) -> None:
        """
        Set the electron beam control interface.

        Args:
            beam (BeamControl): Electron beam control.
        """
        pass

    @property
    @abstractmethod
    def ion_beam(self) -> BeamControl:
        """
        Get the ion beam control interface.

        Returns:
            BeamControl: Ion beam control.
        """
        pass

    @ion_beam.setter
    @abstractmethod
    def ion_beam(self, beam: BeamControl) -> None:
        """
        Set the ion beam control interface.

        Args:
            beam (BeamControl): Ion beam control.
        """
        pass

    @abstractmethod
    def custom(self, name: str) -> Any:
        """
        Get a custom microscope property.

        Args:
            name (str): Property name.

        Returns:
            Any: Property value.
        """
        pass

    @abstractmethod
    def set_custom(self, name: str, value: Any) -> Any:
        """
        Set a custom microscope property.

        Args:
            name (str): Property name.
            value (Any): Property value.

        Returns:
            Any: Result of setting the property.
        """
        pass

    @abstractmethod
    def try_set_stage_position(self, pos: StagePosition) -> StagePosition:
        """
        Attempt to set the stage to an absolute position.

        Args:
            pos (StagePosition): Target stage position.

        Returns:
            StagePosition: Actual stage position after the operation.
        """
        pass

    @abstractmethod
    def try_move_stage_position(self, delta: StagePosition) -> StagePosition:
        """
        Attempt to move the stage by a relative offset.

        Args:
            delta (StagePosition): Relative stage movement.

        Returns:
            StagePosition: Actual stage position after the operation.
        """
        pass

    @abstractmethod
    def try_set_beam_shift(self, shift: BeamShift) -> BeamShift:
        """
        Attempt to set the beam shift.

        Args:
            shift (BeamShift): Desired beam shift.

        Returns:
            BeamShift: Actual beam shift after the operation.
        """
        pass

    def set_properties(
        self, properties: MicroscopeProperties, beam: BeamType | None
    ) -> None:
        """
        Apply microscope settings.

        Uses this control interface to set the microscope state to the values
        provided in the given properties container.

        Args:
            properties (MicroscopeProperties): Container of microscope property
                values to apply.
            beam (BeamType): Type of the beam which properties should be set.
                Properties for the other beam are not set.
                If `None`, properties of both beams are set.
        """
        if properties.stage_position is not None:
            self.try_set_stage_position(properties.stage_position)

        if (internal := properties.internal) is not None:
            for custom_property, value in internal.items():
                self.set_custom(custom_property, value)

        if properties.electron_beam is not None and (
            beam is None or beam is BeamType.ELECTRON
        ):
            self.electron_beam.set_properties(properties.electron_beam)

        if properties.ion_beam is not None and (beam is None or beam is BeamType.ION):
            self.ion_beam.set_properties(properties.ion_beam)
