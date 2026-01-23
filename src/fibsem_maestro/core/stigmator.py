# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from dataclasses import dataclass
from typing import Self

from autoscript_sdb_microscope_client.structures import Point as PointAs


@dataclass
class Stigmator:
    """Represents the stigmator settings in a microscope."""

    x: float
    y: float

    @classmethod
    def from_point_autoscript(cls, point_autoscript: PointAs) -> Self:
        """
        Create a Stigmator instance from an AutoScript Point object.

        Args:
            point_autoscript (PointAs): An AutoScript Point object.

        Returns:
            Stigmator: A converted Stigmator instance.
        """
        return cls(x=point_autoscript.x, y=point_autoscript.y)

    def to_point_autoscript(self) -> PointAs:
        """
        Convert the stigmator coordinates to an AutoScript Point object.

        Returns:
            PointAs: An AutoScript Point object.
        """
        return PointAs(x=self.x, y=self.y)
