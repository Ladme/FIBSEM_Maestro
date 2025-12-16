# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from abc import ABC, abstractmethod

from fibsem_maestro.core.stage_position import StagePosition
from fibsem_maestro.microscope.abstract_control.beam_control import BeamControl


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

    @property
    @abstractmethod
    def position(self) -> StagePosition:
        pass

    @position.setter
    @abstractmethod
    def position(self, goal: StagePosition) -> None:
        pass

    @abstractmethod
    def move_relative(self, goal: StagePosition) -> None:
        pass

    @property
    @abstractmethod
    def electron_beam(self) -> BeamControl:
        """
        Returns the electron beam of the microscope.
        """
        pass

    @property
    @abstractmethod
    def ion_beam(self) -> BeamControl:
        """
        Returns the ion beam of the microscope.
        """
        pass
