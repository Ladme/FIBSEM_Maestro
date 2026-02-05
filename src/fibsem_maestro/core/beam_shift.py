# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from dataclasses import dataclass
from typing import Self

from autoscript_sdb_microscope_client.structures import Point as PointAs


@dataclass
class BeamShift:
    """Represents a beam shift in a microscope, with coordinates in nanometers."""

    x: float
    y: float

    def to_tuple(self) -> tuple[float, float]:
        """
        Converts the beam shift coordinates to a tuple.

        Returns:
            tuple[float, float]: A tuple containing (x, y) coordinates in nanometers.
        """
        return (self.x, self.y)

    @classmethod
    def from_point_autoscript(cls, point_autoscript: PointAs) -> Self:
        """
        Create a BeamShift instance from an AutoScript Point object.

        Args:
            point_autoscript (PointAs): An AutoScript Point object, with coordinates in meters.

        Returns:
            BeamShift: A new BeamShift instance with coordinates converted to nanometers.
        """
        return cls(x=point_autoscript.x * 1e9, y=point_autoscript.y * 1e9)

    def to_point_autoscript(self) -> PointAs:
        """
        Convert the beam shift coordinates to an AutoScript Point object.

        Returns:
            PointAs: An AutoScript Point object with coordinates converted to meters.
        """
        return PointAs(x=self.x * 1e-9, y=self.y * 1e-9)

    def __add__(self, other: "BeamShift") -> "BeamShift":
        """
        Adds two BeamShift instances element-wise.

        Args:
            other (BeamShift): Another BeamShift instance to add to this one.

        Returns:
            BeamShift: A new BeamShift instance with the summed x, y, z, rotation, and tilt values.
        """
        return BeamShift(
            x=self.x + other.x,
            y=self.y + other.y,
        )
