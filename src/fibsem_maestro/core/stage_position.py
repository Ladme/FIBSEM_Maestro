# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

import math
from dataclasses import dataclass
from typing import Self

from autoscript_sdb_microscope_client.structures import StagePosition as StagePositionAs


@dataclass
class StagePosition:
    """
    Represents the position and orientation of a stage in an electron microscope.

    Positional attributes (x, y, z) are in nanometers, while rotational attributes (rotation, tilt) are in degrees.
    """

    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    rotation: float = 0.0
    tilt: float = 0.0

    def to_xy(self) -> tuple[float, float]:
        """
        Extract the x and y coordinates of the stage position.

        Returns:
            tuple[float, float]: A tuple containing the x and y coordinates in nanometers.
        """
        return self.x, self.y

    @classmethod
    def from_stage_position_autoscript(
        cls, stage_position_autoscript: StagePositionAs
    ) -> Self:
        """
        Create a StagePosition instance from an AutoScript StagePosition object.

        Converts positional units from meters to nanometers and angular
        units from radians to degrees.

        Args:
            stage_position_autoscript (StagePositionAs): An AutoScript StagePosition object
                with positional coordinates in meters and angular coordinates in radians.

        Returns:
            StagePosition: A StagePosition instance with coordinates
                in nanometers and angles in degrees.
        """
        # TODO: all fields can be None - how should we handle that?
        return cls(
            x=(stage_position_autoscript.x or 0) * 1e9,
            y=(stage_position_autoscript.y or 0) * 1e9,
            z=(stage_position_autoscript.z or 0) * 1e9,
            rotation=math.degrees(stage_position_autoscript.r or 0),
            tilt=math.degrees(stage_position_autoscript.t or 0),
        )

    def to_stage_position_autoscript(self) -> StagePositionAs:
        """
        Convert the StagePosition instance to an AutoScript StagePosition object.

        Converts positional units from nanometers to meters and angular units from degrees to radians.

        Returns:
            StagePositionAs: An AutoScript StagePosition object with
                positional coordinates in meters and angular coordinates in radians.
        """
        return StagePositionAs(
            x=self.x * 1e-9,
            y=self.y * 1e-9,
            z=self.z * 1e-9,
            r=math.radians(self.rotation),
            t=math.radians(self.tilt),
            coordinate_system="Specimen",
        )
