# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from dataclasses import dataclass


@dataclass
class StagePosition:
    """
    Class representing the stage position
    Rotation and tilt is in degrees.
    """

    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    rotation: float = 0.0  # in degrees
    tilt: float = 0.0  # in degrees

    def to_xy(self) -> tuple[float, float]:
        return self.x, self.y
