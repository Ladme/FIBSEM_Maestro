# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from pydantic import BaseModel
from pydantic.dataclasses import dataclass
from typing import Generic, Self, TypeVar

from autoscript_sdb_microscope_client.structures import Rectangle as RectangleAs

from fibsem_maestro.core.point import MPoint, NMPoint, PixelPoint, RelativePoint
from fibsem_maestro.core.resolution import Resolution

T = TypeVar("T", PixelPoint, RelativePoint, NMPoint, MPoint)
U = TypeVar("U", int, float)


class _ScanningArea(BaseModel, Generic[T, U]):
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

    def __init__(self, origin: T, width: U, height: U):
        # pydantic BaseModel requires keyword arguments
        super().__init__(origin=origin, width=width, height=height)

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

    def __init__(self, origin: RelativePoint, width: float, height: float):
        # pydantic BaseModel requires keyword arguments
        super().__init__(origin=origin, width=width, height=height)

    def to_pixels(self, resolution: Resolution) -> "PixelScanningArea":
        """
        Convert the relative scanning area to pixel coordinates.

        Args:
            resolution (Resolution): Resolution of the image in pixels.

        Returns:
            PixelScanningArea: A new instance of PixelScanningArea with coordinates
                and dimensions converted to absolute pixel values.
        """
        return PixelScanningArea(
            origin=self.origin.to_pixels(resolution),
            width=int(round(self.width * resolution.width)),
            height=int(round(self.height * resolution.height)),
        )

    def to_nanometers(
        self, resolution: Resolution, pixel_size_nm: float
    ) -> "NMScanningArea":
        """
        Convert the relative scanning area to nanometers.

        Args:
            resolution (Resolution): Resolution of the image in pixels.
            pixel_size_nm (float): The size of a pixel in nanometers.

        Returns:
            NMScanningArea: A new instance of NMScanningArea with coordinates
                and dimensions converted to nanometers.
        """
        return self.to_pixels(resolution).to_nanometers(pixel_size_nm)

    def to_meters(self, resolution: Resolution, pixel_size_m: float) -> "MScanningArea":
        """
        Convert the relative scanning area to meters.

        Args:
            resolution (Resolution): Resolution of the image in pixels.
            pixel_size_m (float): The size of a pixel in meters.

        Returns:
            MScanningArea: A new instance of MScanningArea with coordinates
                and dimensions converted to meters.
        """
        return self.to_pixels(resolution).to_meters(pixel_size_m)

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

    def __init__(self, origin: PixelPoint, width: int, height: int):
        # pydantic BaseModel requires keyword arguments
        super().__init__(origin=origin, width=width, height=height)

    def to_relative(self, resolution: Resolution) -> "RelativeScanningArea":
        """
        Convert the pixel-based scanning area to relative coordinates.

        Args:
            resolution (Resolution): Resolution of the image in pixels.

        Returns:
            RelativeScanningArea: A new instance of RelativeScanningArea with coordinates
                and dimensions converted to relative values (0-1).
        """
        return RelativeScanningArea(
            origin=self.origin.to_relative(resolution),
            width=self.width / resolution.width,
            height=self.height / resolution.height,
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

    def __init__(self, origin: NMPoint, width: float, height: float):
        # pydantic BaseModel requires keyword arguments
        super().__init__(origin=origin, width=width, height=height)

    def to_relative(
        self, resolution: Resolution, pixel_size_nm: float
    ) -> "RelativeScanningArea":
        """
        Convert the nanometer-based scanning area to relative coordinates.

        Args:
            resolution (Resolution): Resolution of the image in pixels.
            pixel_size_nm (float): The size of a pixel in nanometers.

        Returns:
            RelativeScanningArea: A new instance of RelativeScanningArea with coordinates
                and dimensions converted to relative values (0-1).
        """
        return self.to_pixels(pixel_size_nm).to_relative(resolution)

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

    def __init__(self, origin: MPoint, width: float, height: float):
        # pydantic BaseModel requires keyword arguments
        super().__init__(origin=origin, width=width, height=height)

    def to_relative(
        self, resolution: Resolution, pixel_size_m: float
    ) -> "RelativeScanningArea":
        """
        Convert the meter-based scanning area to relative coordinates.

        Args:
            resolution (Resolution): Resolution of the image in pixels.
            pixel_size_m (float): The size of a pixel in meters.

        Returns:
            RelativeScanningArea: A new instance of RelativeScanningArea with coordinates
                and dimensions converted to relative values (0-1).
        """
        return self.to_pixels(pixel_size_m).to_relative(resolution)

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
