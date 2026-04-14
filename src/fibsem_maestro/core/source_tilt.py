# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING, Self

from fibsem_maestro.core.errors import AutoscriptNotAvailableError

if TYPE_CHECKING:
    from autoscript_sdb_microscope_client.structures import Point as PointAs


@dataclass
class SourceTilt:
    """
    Represents the tilt of a source in an electron microscope, with coordinates in degrees.
    """

    x: float
    y: float

    @classmethod
    def from_point_autoscript(cls, point_autoscript: PointAs) -> Self:
        """
        Create a SourceTilt instance from an AutoScript Point object.

        Converts the coordinates from radians to degrees.

        Args:
            point_autoscript (PointAs): An AutoScript Point object with angular coordinates in radians.

        Returns:
            SourceTilt: A SourceTilt instance with coordinates converted to degrees.

        Raises:
            AutoscriptNotAvailableError: If the Autoscript library is not installed.
        """
        try:
            from autoscript_sdb_microscope_client.structures import (
                Point,  # noqa: F401 # type: ignore
            )
        except ImportError as e:
            raise AutoscriptNotAvailableError() from e

        return cls(
            x=math.degrees(point_autoscript.x), y=math.degrees(point_autoscript.y)
        )

    def to_point_autoscript(self) -> PointAs:
        """
        Convert the source tilt coordinates to an AutoScript Point object with coordinates in radians.

        Returns:
            PointAs: An AutoScript Point object with angular coordinates converted to radians.

        Raises:
            AutoscriptNotAvailableError: If the Autoscript library is not installed.
        """
        try:
            from autoscript_sdb_microscope_client.structures import Point as PointAs
        except ImportError as e:
            raise AutoscriptNotAvailableError() from e

        return PointAs(x=math.radians(self.x), y=math.radians(self.y))
