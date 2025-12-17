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

    @abstractmethod
    def __init__(self, ip_address: str):
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

    @property
    @abstractmethod
    def ion_beam(self) -> BeamControl:
        """
        Returns the ion beam of the microscope.
        """
        pass

    @abstractmethod
    def try_set_stage_position(self, pos: StagePosition) -> StagePosition:
        pass

    @abstractmethod
    def try_move_stage_position(self, delta: StagePosition) -> StagePosition:
        pass
