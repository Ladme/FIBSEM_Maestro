# Released under MIT License.
# Copyright (c) 2024-2026 CEMCOF

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Annotated, Self

from fibsem_maestro.core.errors import AutoscriptNotAvailableError
from fibsem_maestro.settings.form_utils import FieldUnit

if TYPE_CHECKING:
    from autoscript_sdb_microscope_client.structures import Point as PointAs


@dataclass
class LensAlignment:
    """Represents the alignment of a lens in a microscope, with coordinates in nanometers."""

    x: Annotated[float, FieldUnit(suffix="nm")]
    y: Annotated[float, FieldUnit(suffix="nm")]

    @classmethod
    def from_point_autoscript(cls, point_autoscript: PointAs) -> Self:
        """Create a LensAlignment instance from an AutoScript Point object.

        Args:
            point_autoscript (PointAs): An AutoScript Point object, with coordinates in meters.

        Returns:
            LensAlignment: A new LensAlignment instance with coordinates converted to nanometers.

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
        Convert the lens alignment coordinates to an AutoScript Point object.

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
