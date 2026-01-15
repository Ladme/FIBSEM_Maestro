# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from abc import ABC, abstractmethod
from typing import Any

from fibsem_maestro.core.beam_shift import BeamShift
from fibsem_maestro.core.stage_position import StagePosition
from fibsem_maestro.logging.text.text_logger import TextLogger
from fibsem_maestro.microscope.abstract_control.beam_control import BeamControl
from fibsem_maestro.settings.microscope_properties import MicroscopeProperties


class MicroscopeControl(ABC):
    """
    This is an abstract base class designated for controlling a microscope.

    The methods provided by this class serve as an interface that should be
    concretely implemented by any microscope-specific control class
    (for example: FIBSEM API, direct Autoscript).

    These methods include the basic functionalities needed for controlling
    the various components and parameters of a microscope such as the stage,
    and beams.
    """

    @abstractmethod
    def __init__(self, ip_address: str, txt_log: TextLogger):
        pass

    @property
    @abstractmethod
    def stage_position(self) -> StagePosition:
        pass

    @property
    @abstractmethod
    def electron_beam(self) -> BeamControl:
        """
        Returns the electron beam of the microscope.
        """
        pass

    @electron_beam.setter
    @abstractmethod
    def electron_beam(self, beam: BeamControl) -> None:
        pass

    @property
    @abstractmethod
    def ion_beam(self) -> BeamControl:
        """
        Returns the ion beam of the microscope.
        """
        pass

    @ion_beam.setter
    @abstractmethod
    def ion_beam(self, beam: BeamControl) -> None:
        pass

    @abstractmethod
    def custom(self, name: str) -> Any:
        pass

    @abstractmethod
    def set_custom(self, name: str, value: Any) -> Any:
        pass

    @abstractmethod
    def try_set_stage_position(self, pos: StagePosition) -> StagePosition:
        pass

    @abstractmethod
    def try_move_stage_position(self, delta: StagePosition) -> StagePosition:
        pass

    @abstractmethod
    def try_set_beam_shift(self, shift: BeamShift) -> BeamShift:
        pass

    def apply_microscope_properties(self, properties: MicroscopeProperties) -> None:
        self.try_set_stage_position(properties.stage_position)
        for custom_property, value in properties.custom.items():
            self.set_custom(custom_property, value)

        self.electron_beam.apply_beam_properties(properties.electron_beam)
        self.ion_beam.apply_beam_properties(properties.ion_beam)
