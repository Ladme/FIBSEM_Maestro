# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from dataclasses import dataclass
from typing import Self

from fibsem_maestro.core.point import RelativePoint


@dataclass
class ScanningArea:
    """
    Represents a scanning area in an electron microscope with relative coordinates.

    Attributes:
        origin (RelativePoint):
            Relative coordinates of the top left corner of the scanning area.
        width (float):
            The width of the scanning area.
        height (float):
            The height of the scanning area.
    """

    origin: RelativePoint
    width: float
    height: float

    def update(self, other: Self) -> None:
        """
        Update the scanning area with the values from another ScanningArea instance.

        Args:
            other (ScanningArea): Another ScanningArea instance to copy values from.
        """
        self.origin = other.origin
        self.width = other.width
        self.height = other.height
