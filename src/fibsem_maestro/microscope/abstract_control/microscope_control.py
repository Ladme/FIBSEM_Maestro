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

    Methods:
        position - Getter and setter for the position of the microscope stage.
    """

    @property
    @abstractmethod
    def position(self):
        pass

    @position.setter
    @abstractmethod
    def position(self, goal: StagePosition):
        pass

    @property
    @abstractmethod
    def relative_position(self):
        pass

    @relative_position.setter
    @abstractmethod
    def relative_position(self, goal: StagePosition):
        pass

    @position.setter
    @abstractmethod
    def position(self, goal: StagePosition):
        pass

    @property
    @abstractmethod
    def electron_beam(self) -> BeamControl:
        """
        Returns the electron beam of the microscope.

        :return: The electron_beam instance of BeamControl
        """
        pass

    @property
    @abstractmethod
    def ion_beam(self) -> BeamControl:
        """
        Returns the ion beam of the microscope.

        :return: The ion_beam instance of BeamControl
        """
        pass
