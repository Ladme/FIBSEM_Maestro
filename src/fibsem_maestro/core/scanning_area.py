# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from dataclasses import dataclass
from typing import Generic, Self, TypeVar

from autoscript_sdb_microscope_client.structures import Rectangle as RectangleAs

from fibsem_maestro.core.point import MPoint, NMPoint, PixelPoint, RelativePoint

T = TypeVar("T", PixelPoint, RelativePoint, NMPoint, MPoint)
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
        Convert the relative scanning area to pixel coordinates.

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

    def to_nanometers(
        self, img_shape: tuple[int, int], pixel_size_nm: float
    ) -> "NMScanningArea":
        """
        Convert the relative scanning area to nanometers.

        Args:
            img_shape (tuple[int, int]): A tuple representing the (height, width)
                of the image in pixels.
            pixel_size_nm (float): The size of a pixel in nanometers.

        Returns:
            NMScanningArea: A new instance of NMScanningArea with coordinates
                and dimensions converted to nanometers.
        """
        return self.to_pixels(img_shape).to_nanometers(pixel_size_nm)

    def to_meters(
        self, img_shape: tuple[int, int], pixel_size_m: float
    ) -> "MScanningArea":
        """
        Convert the relative scanning area to meters.

        Args:
            img_shape (tuple[int, int]): A tuple representing the (height, width)
                of the image in pixels.
            pixel_size_m (float): The size of a pixel in meters.

        Returns:
            MScanningArea: A new instance of MScanningArea with coordinates
                and dimensions converted to meters.
        """
        return self.to_pixels(img_shape).to_meters(pixel_size_m)

    def to_autoscript(self) -> RectangleAs:
        """
        Convert the relative scanning area to Autoscript's rectangle.

        Returns:
            RectangleAs: A new instance of RectangleAs with the same coordinates
                and dimensions as the relative scanning area.
        """
        return RectangleAs(
            left=self.origin.x, top=self.origin.y, width=self.width, height=self.height
        )


class PixelScanningArea(_ScanningArea[PixelPoint, int]):
    """Represents a scanning area using absolute pixel coordinates."""

    def to_relative(self, img_shape: tuple[int, int]) -> "RelativeScanningArea":
        """
        Convert the pixel-based scanning area to relative coordinates.

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

    def to_nanometers(self, pixel_size_nm: float) -> "NMScanningArea":
        """
        Convert the pixel-based scanning area to nanometers.

        Args:
            pixel_size_nm (float): The size of a pixel in nanometers.

        Returns:
            NMScanningArea: A new instance of NMScanningArea with coordinates
                and dimensions converted to nanometers.
        """
        return NMScanningArea(
            origin=self.origin.to_nanometers(pixel_size_nm),
            width=self.width * pixel_size_nm,
            height=self.height * pixel_size_nm,
        )

    def to_meters(self, pixel_size_m: float) -> "MScanningArea":
        """
        Convert the pixel-based scanning area to meters.

        Args:
            pixel_size_m (float): The size of a pixel in meters.

        Returns:
            MScanningArea: A new instance of MScanningArea with coordinates
                and dimensions converted to meters.
        """
        return MScanningArea(
            origin=self.origin.to_meters(pixel_size_m),
            width=self.width * pixel_size_m,
            height=self.height * pixel_size_m,
        )


class NMScanningArea(_ScanningArea[NMPoint, float]):
    """Represents a scanning area in nanometers."""

    def to_relative(
        self, img_shape: tuple[int, int], pixel_size_nm: float
    ) -> "RelativeScanningArea":
        """
        Convert the nanometer-based scanning area to relative coordinates.

        Args:
            img_shape (tuple[int, int]): A tuple representing the (height, width)
                of the image in pixels.
            pixel_size_nm (float): The size of a pixel in nanometers.

        Returns:
            RelativeScanningArea: A new instance of RelativeScanningArea with coordinates
                and dimensions converted to relative values (0-1).
        """
        return self.to_pixels(pixel_size_nm).to_relative(img_shape)

    def to_pixels(self, pixel_size_nm: float) -> "PixelScanningArea":
        """
        Convert the nanometer-based scanning area to pixel coordinates.

        Args:
            pixel_size_nm (float): The size of a pixel in nanometers.

        Returns:
            PixelScanningArea: A new instance of PixelScanningArea with coordinates
                and dimensions converted to absolute pixel values.
        """
        return PixelScanningArea(
            origin=self.origin.to_pixels(pixel_size_nm),
            width=int(round(self.width / pixel_size_nm)),
            height=int(round(self.height / pixel_size_nm)),
        )

    def to_meters(self) -> "MScanningArea":
        """
        Convert the nanometer-based scanning area to meters.

        Returns:
            MScanningArea: A new instance of MScanningArea with coordinates
                and dimensions converted to meters.
        """
        return MScanningArea(
            origin=self.origin.to_meters(),
            width=self.width * 1e-9,
            height=self.height * 1e-9,
        )


class MScanningArea(_ScanningArea[MPoint, float]):
    """Represents a scanning area in meters."""

    def to_relative(
        self, img_shape: tuple[int, int], pixel_size_m: float
    ) -> "RelativeScanningArea":
        """
        Convert the meter-based scanning area to relative coordinates.

        Args:
            img_shape (tuple[int, int]): A tuple representing the (height, width)
                of the image in pixels.
            pixel_size_m (float): The size of a pixel in meters.

        Returns:
            RelativeScanningArea: A new instance of RelativeScanningArea with coordinates
                and dimensions converted to relative values (0-1).
        """
        return self.to_pixels(pixel_size_m).to_relative(img_shape)

    def to_pixels(self, pixel_size_m: float) -> "PixelScanningArea":
        """
        Convert the meter-based scanning area to pixel coordinates.

        Args:
            pixel_size_m (float): The size of a pixel in meters.

        Returns:
            PixelScanningArea: A new instance of PixelScanningArea with coordinates
                and dimensions converted to absolute pixel values.
        """
        return PixelScanningArea(
            origin=self.origin.to_pixels(pixel_size_m),
            width=int(round(self.width / pixel_size_m)),
            height=int(round(self.height / pixel_size_m)),
        )

    def to_nanometers(self) -> "NMScanningArea":
        """
        Convert the meter-based scanning area to nanometers.

        Returns:
            NMScanningArea: A new instance of NMScanningArea with coordinates
                and dimensions converted to nanometers.
        """
        return NMScanningArea(
            origin=self.origin.to_nanometers(),
            width=self.width * 1e9,
            height=self.height * 1e9,
        )
