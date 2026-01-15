# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

import math
from dataclasses import dataclass
from typing import Self

from autoscript_sdb_microscope_client.structures import StagePosition as StagePositionAs


@dataclass
class StagePosition:
    """
    Class representing the stage position
    Rotation and tilt is in degrees.
    Position in nanometers.
    """

    x: float = 0.0  # in nm
    y: float = 0.0
    z: float = 0.0
    rotation: float = 0.0  # in degrees
    tilt: float = 0.0  # in degrees

    def to_xy(self) -> tuple[float, float]:
        return self.x, self.y

    @classmethod
    def from_stage_position_autoscript(
        cls, stage_position_autoscript: StagePositionAs
    ) -> Self:
        """Create a StagePosition instance from an autoscript's StagePosition instance."""
        # TODO: all fields can be None - how should we handle that?
        return cls(
            x=stage_position_autoscript.x
            or 0 * 10e9,  # convert from meters to nanometers
            y=stage_position_autoscript.y or 0 * 1e9,
            z=stage_position_autoscript.z or 0 * 1e9,
            rotation=math.degrees(stage_position_autoscript.r or 0),
            tilt=math.degrees(stage_position_autoscript.t or 0),
        )

    def to_stage_position_autoscript(self) -> StagePositionAs:
        """Convert a StagePoisition instance to autoscript's StagePosition instance."""
        return StagePositionAs(
            x=self.x * 1e-9,
            y=self.y * 1e-9,
            z=self.z * 1e-9,
            r=math.radians(self.rotation),
            t=math.radians(self.tilt),
            coordinate_system="Specimen",
        )
