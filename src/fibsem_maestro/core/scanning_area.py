# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from dataclasses import dataclass
from typing import Generic, Self, TypeVar

from fibsem_maestro.core.point import PixelPoint, RelativePoint

T = TypeVar("T", PixelPoint, RelativePoint)
U = TypeVar("U", int, float)


@dataclass
class _ScanningArea(Generic[T, U]):
    """
    Represents a scanning area in an electron microscope.

    Attributes:
        origin (T):
            Coordinates of the top left corner of the scanning area.
        width (float):
            The width of the scanning area.
        height (float):
            The height of the scanning area.
    """

    origin: T
    width: U
    height: U

    def update(self, other: Self) -> None:
        """
        Update the scanning area with the values from another ScanningArea instance.

        Args:
            other (ScanningArea): Another ScanningArea instance to copy values from.
        """
        self.origin = other.origin
        self.width = other.width
        self.height = other.height


class RelativeScanningArea(_ScanningArea[RelativePoint, float]):
    """
    Represents a scanning area using relative coordinates (0-1).
    """

    def to_pixels(self, img_shape: tuple[int, int]) -> "PixelScanningArea":
        """
        Converts the relative scanning area to pixel coordinates.

        Args:
            img_shape (tuple[int, int]): A tuple representing the (height, width)
                of the image in pixels.

        Returns:
            PixelScanningArea: A new instance of PixelScanningArea with coordinates
                and dimensions converted to absolute pixel values.
        """
        return PixelScanningArea(
            origin=self.origin.to_pixels(img_shape),
            width=int(round(self.width * img_shape[1])),
            height=int(round(self.height * img_shape[0])),
        )


class PixelScanningArea(_ScanningArea[PixelPoint, int]):
    """Represents a scanning area using absolute pixel coordinates."""

    def to_relative(self, img_shape: tuple[int, int]) -> "RelativeScanningArea":
        """
        Converts the pixel-based scanning area to relative coordinates.

        Args:
            img_shape (tuple[int, int]): A tuple representing the (height, width)
                of the image in pixels.

        Returns:
            RelativeScanningArea: A new instance of RelativeScanningArea with coordinates
                and dimensions converted to relative values (0-1).
        """
        return RelativeScanningArea(
            origin=self.origin.to_relative(img_shape),
            width=self.width / img_shape[1],
            height=self.height / img_shape[0],
        )
