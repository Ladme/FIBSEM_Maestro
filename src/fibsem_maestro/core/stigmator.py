# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Self

from fibsem_maestro.core.errors import AutoscriptNotAvailableError

if TYPE_CHECKING:
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

        Raises:
            AutoscriptNotAvailableError: If the Autoscript library is not installed.
        """
        try:
            from autoscript_sdb_microscope_client.structures import (
                Point,  # noqa: F401
            )
        except ImportError as e:
            raise AutoscriptNotAvailableError() from e

        return cls(x=point_autoscript.x, y=point_autoscript.y)

    def to_point_autoscript(self) -> PointAs:
        """
        Convert the stigmator coordinates to an AutoScript Point object.

        Returns:
            PointAs: An AutoScript Point object.

        Raises:
            AutoscriptNotAvailableError: If the Autoscript library is not installed.
        """
        try:
            from autoscript_sdb_microscope_client.structures import Point as PointAs
        except ImportError as e:
            raise AutoscriptNotAvailableError() from e

        return PointAs(x=self.x, y=self.y)
