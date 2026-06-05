# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Annotated, Self

from fibsem_maestro.core.errors import AutoscriptNotAvailableError
from fibsem_maestro.settings.form_utils import FieldUnit

if TYPE_CHECKING:
    from autoscript_sdb_microscope_client.structures import Point as PointAs


@dataclass
class BeamShift:
    """Represents a beam shift in a microscope, with coordinates in nanometers."""

    x: Annotated[float, FieldUnit(suffix="nm")]
    y: Annotated[float, FieldUnit(suffix="nm")]

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

        Raises:
            AutoscriptNotAvailableError: If the Autoscript library is not installed.
        """
        try:
            from autoscript_sdb_microscope_client.structures import (
                Point,  # noqa: F401
            )
        except ImportError as e:
            raise AutoscriptNotAvailableError() from e

        return cls(x=point_autoscript.x * 1e9, y=point_autoscript.y * 1e9)

    def to_point_autoscript(self) -> PointAs:
        """
        Convert the beam shift coordinates to an AutoScript Point object.

        Returns:
            PointAs: An AutoScript Point object with coordinates converted to meters.

        Raises:
            AutoscriptNotAvailableError: If the Autoscript library is not installed.
        """
        try:
            from autoscript_sdb_microscope_client.structures import Point as PointAs
        except ImportError as e:
            raise AutoscriptNotAvailableError() from e

        return PointAs(x=self.x * 1e-9, y=self.y * 1e-9)

    def __add__(self, other: BeamShift) -> BeamShift:
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
