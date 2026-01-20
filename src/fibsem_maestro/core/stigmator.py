# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from dataclasses import dataclass
from typing import Self

from autoscript_sdb_microscope_client.structures import Point as PointAs


@dataclass
class Stigmator:
    """Represents the stigmator settings in a microscope, with coordinates in nanometers."""

    x: float
    y: float

    @classmethod
    def from_point_autoscript(cls, point_autoscript: PointAs) -> Self:
        """
        Create a Stigmator instance from an AutoScript Point object.

        Args:
            point_autoscript (PointAs): An AutoScript Point object
                with positional coordinates in meters.

        Returns:
            Stigmator: A Stigmator instance with coordinates in nanometers.
        """
        return cls(x=point_autoscript.x * 1e9, y=point_autoscript.y * 1e9)

    def to_point_autoscript(self) -> PointAs:
        """
        Convert the stigmator coordinates to an AutoScript Point object.

        Returns:
            PointAs: An AutoScript Point object with positional coordinates in meters.
        """
        return PointAs(x=self.x * 1e-9, y=self.y * 1e-9)
