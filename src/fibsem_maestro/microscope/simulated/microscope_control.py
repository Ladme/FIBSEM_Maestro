# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

import numpy as np

from fibsem_maestro.core.stage_position import StagePosition
from fibsem_maestro.logging.text.text_logger import TextLogger
from fibsem_maestro.microscope.abstract_control.beam_control import BeamControl
from fibsem_maestro.microscope.abstract_control.microscope_control import (
    MicroscopeControl,
)
from fibsem_maestro.microscope.microscope_registry import MicroscopeRegistry
from fibsem_maestro.microscope.simulated.beam_control import SimulatedBeamControl


@MicroscopeRegistry.register("simulated")
class SimulatedMicroscopeControl(MicroscopeControl):
    """
    Simulated microscope controller.

    This class provides an in-memory simulation of a microscope stage and two beams
    (electron and ion).
    """

    def __init__(self, ip_address: str, txt_log: TextLogger, *, seed: int = 0):
        """Initialize the simulated microscope.

        Args:
            ip_address (str): Address string for compatibility with real controllers.
            txt_log (TextLogger): Text logger.
            seed (int, optional): Seed for deterministic noise. Defaults to 0.
        """
        self.ip_address = ip_address
        self._rng = np.random.default_rng(seed)
        self._txt_log = txt_log

        self._stage_position = StagePosition(
            x=0.0, y=0.0, z=0.0, rotation=0.0, tilt=0.0
        )

        self._electron_beam = SimulatedBeamControl(name="electron", rng=self._rng)
        self._ion_beam = SimulatedBeamControl(name="ion", rng=self._rng)

    @property
    def stage_position(self) -> StagePosition:
        """
        Return the current simulated stage position.

        Returns:
            StagePosition: The current (actual) stage position maintained by the simulator.
        """
        return StagePosition(**self._stage_position.__dict__)

    @property
    def electron_beam(self) -> BeamControl:
        """
        Return the simulated electron beam controller.

        Returns:
            BeamControl: Beam controller implementing the electron beam behavior.
        """
        return self._electron_beam

    @electron_beam.setter
    def electron_beam(self, beam: BeamControl) -> None:
        self._electron_beam = beam

    @property
    def ion_beam(self) -> BeamControl:
        """Return the simulated ion beam controller.

        Returns:
            BeamControl: Beam controller implementing the ion beam behavior.
        """
        return self._ion_beam

    @ion_beam.setter
    def ion_beam(self, beam: BeamControl) -> None:
        self._ion_beam = beam

    def try_set_stage_position(self, pos: StagePosition) -> StagePosition:
        """
        Attempt to set the stage position.

        This method **may fail to reach the requested position exactly**. The simulator
        applies a small random error (noise) and returns the *actual* stage position.

        Args:
            pos (StagePosition): Desired absolute stage position.

        Returns:
            StagePosition: The actual stage position after the attempted move.
        """
        noise_xyz = self._rng.normal(0.0, 10.0, size=3)  # nm
        noise_ang = self._rng.normal(0.0, 0.001, size=2)  # degrees

        self._stage_position = StagePosition(
            x=pos.x + float(noise_xyz[0]),
            y=pos.y + float(noise_xyz[1]),
            z=pos.z + float(noise_xyz[2]),
            rotation=pos.rotation + float(noise_ang[0]),
            tilt=pos.tilt + float(noise_ang[1]),
        )
        return self.stage_position

    def try_move_stage_position(self, delta: StagePosition) -> StagePosition:
        """
        Attempt to move the stage position by a delta.

        This method performs a relative move (`current + delta`) but **may land
        approximately**. The returned value is always the simulator's *actual* position.

        Args:
            delta (StagePosition): Relative movement to apply.

        Returns:
            StagePosition: The actual stage position after the attempted move.
        """
        cur = self._stage_position
        target = StagePosition(
            x=cur.x + delta.x,
            y=cur.y + delta.y,
            z=cur.z + delta.z,
            rotation=cur.rotation + delta.rotation,
            tilt=cur.tilt + delta.tilt,
        )
        return self.try_set_stage_position(target)
