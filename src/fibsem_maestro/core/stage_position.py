# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from dataclasses import dataclass


@dataclass
class StagePosition:
    """
    Class representing the stage position
    Rotation and tilt is in degrees.
    """

    x: float
    y: float
    z: float
    rotation: float  # in degrees
    tilt: float  # in degrees

    def to_xy(self) -> tuple[float, float]:
        return self.x, self.y
