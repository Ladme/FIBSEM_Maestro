# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from __future__ import annotations

from typing import TYPE_CHECKING, Generic, Self, TypeVar

from pydantic import BaseModel

from fibsem_maestro.core.direction import Direction
from fibsem_maestro.core.errors import AutoscriptNotAvailableError
from fibsem_maestro.core.point import MPoint, NMPoint, PixelPoint, RelativePoint

if TYPE_CHECKING:
    from autoscript_sdb_microscope_client.structures import Rectangle as RectangleAs

    from fibsem_maestro.core.resolution import Resolution

T = TypeVar("T", PixelPoint, RelativePoint, NMPoint, MPoint)
U = TypeVar("U", int, float)


class _Area(BaseModel, Generic[T, U]):
    """
    Represents an area of an image.

    Attributes:
        origin (T):
            Coordinates of the top left corner of the area.
        width (U):
            The width of the area.
        height (U):
            The height of the area.
    """

    origin: T
    width: U
    height: U

    def update(self, other: Self) -> None:
        """
        Update the area with the values from another area instance.

        Args:
            other (_Area): Another _Area instance to copy values from.
        """
        self.origin = other.origin
        self.width = other.width
        self.height = other.height

    def shifted(self, delta: T) -> Self:
        """
        Get an area of the same type and dimensions with origin shifted by `delta`.

        Args:
            delta: The amount to shift the origin by.

        Returns:
            An area of the same type with the shifted origin.
        """
        return type(self)(
            origin=self.origin + delta, width=self.width, height=self.height
        )

    def expanded(self, amount: U) -> Self:
        """
        Get an area expanded by `amount` on all four sides.

        Note:
            The returned area may extend beyond valid image bounds.
            Clamping or padding is the caller's responsibility.

        Args:
            amount: The distance to expand on each side, in the same
                units as `width` and `height`.

        Returns:
            A new area of the same type with the expanded geometry.
        """
        # type-checker ignores - type checker does not see that U must have the same type as the inner fields of self.origin
        return type(self)(
            origin=type(self.origin)(
                x=self.origin.x - amount,  # ty: ignore[invalid-argument-type]
                y=self.origin.y - amount,  # ty: ignore[invalid-argument-type]
            ),
            width=self.width + 2 * amount,
            height=self.height + 2 * amount,
        )

    def shifted_in_direction(self, direction: Direction, delta: U) -> Self:
        """
        Get an area of the same type and dimensions with origin shifted by `delta` in the given direction.

        `UP` corresponds to decreasing y-axis coordinates, `DOWN` corresponds to increasing y-axis coordinates.
        `LEFT` corresponds to decreasing x-axis coordinates, `RIGHT` corresponds to increasing x-axis coordinates.

        Args:
            direction (Direction): The direction to shift in.
            delta (U): The distance to shift by in units of the area's origin.

        Returns:
            A new area of the same type with the shifted origin.
        """
        # type-checker ignores - type checker does not see that U must have the same type as the inner fields of self.origin
        match direction:
            case Direction.UP:
                shift = type(self.origin)(x=0.0, y=-delta)  # ty: ignore[invalid-argument-type]
            case Direction.DOWN:
                shift = type(self.origin)(x=0.0, y=delta)  # ty: ignore[invalid-argument-type]
            case Direction.LEFT:
                shift = type(self.origin)(x=-delta, y=0.0)  # ty: ignore[invalid-argument-type]
            case Direction.RIGHT:
                shift = type(self.origin)(x=delta, y=0.0)  # ty: ignore[invalid-argument-type]

        return self.shifted(shift)


class RelativeArea(_Area[RelativePoint, float]):
    """
    Represents an area using relative coordinates (0-1).
    """

    def to_pixels(self, resolution: Resolution) -> PixelArea:
        """
        Convert the relative area to pixel coordinates.

        Args:
            resolution (Resolution): Resolution of the image in pixels.

        Returns:
            PixelArea: A new instance of PixelArea with coordinates
                and dimensions converted to absolute pixel values.
        """
        return PixelArea(
            origin=self.origin.to_pixels(resolution),
            width=int(round(self.width * resolution.width)),
            height=int(round(self.height * resolution.height)),
        )

    def to_nanometers(self, resolution: Resolution, pixel_size_nm: float) -> NMArea:
        """
        Convert the relative area to nanometers.

        Args:
            resolution (Resolution): Resolution of the image in pixels.
            pixel_size_nm (float): The size of a pixel in nanometers.

        Returns:
            NMArea: A new instance of NMArea with coordinates
                and dimensions converted to nanometers.
        """
        return self.to_pixels(resolution).to_nanometers(pixel_size_nm)

    def to_meters(self, resolution: Resolution, pixel_size_m: float) -> MArea:
        """
        Convert the relative area to meters.

        Args:
            resolution (Resolution): Resolution of the image in pixels.
            pixel_size_m (float): The size of a pixel in meters.

        Returns:
            MArea: A new instance of MArea with coordinates
                and dimensions converted to meters.
        """
        return self.to_pixels(resolution).to_meters(pixel_size_m)

    def is_full_frame(self) -> bool:
        """
        Returns True if the area captures the entire field of view.
        """
        return (
            self.origin.x == 0.0
            and self.origin.y == 0
            and self.width == 1.0
            and self.height == 1.0
        )

    @classmethod
    def full(cls) -> Self:
        """
        Get area that captures the entire field of view.

        Returns:
            RelativeArea: An instance of relative area that captures the entire field of view.
        """
        return cls(origin=RelativePoint(x=0.0, y=0.0), width=1.0, height=1.0)

    def to_autoscript(self) -> RectangleAs:
        """
        Convert the relative scanning area to Autoscript's rectangle.

        Returns:
            RectangleAs: A new instance of RectangleAs with the same coordinates
                and dimensions as the relative scanning area.

        Raises:
            AutoscriptNotAvailableError: If the Autoscript library is not installed.
        """
        try:
            from autoscript_sdb_microscope_client.structures import (
                Rectangle as RectangleAs,
            )
        except ImportError as e:
            raise AutoscriptNotAvailableError() from e

        return RectangleAs(
            left=self.origin.x, top=self.origin.y, width=self.width, height=self.height
        )

    @classmethod
    def from_autoscript(cls, rectangle: RectangleAs) -> Self:
        """
        Convert Autoscript's rectangle to relative area.

        Returns:
            RelativeArea: A new instance of relative area with the same
                coordinates and dimenions as the rectangle.

        Raises:
            AutoscriptNotAvailableError: If the Autoscript library is not installed.
        """
        try:
            from autoscript_sdb_microscope_client.structures import (
                Rectangle,  # noqa: F401
            )
        except ImportError as e:
            raise AutoscriptNotAvailableError() from e

        return cls(
            origin=RelativePoint(x=rectangle.left, y=rectangle.top),
            width=rectangle.width,
            height=rectangle.height,
        )


class PixelArea(_Area[PixelPoint, int]):
    """Represents an area using absolute pixel coordinates."""

    def to_relative(self, resolution: Resolution) -> RelativeArea:
        """
        Convert the pixel-based area to relative coordinates.

        Args:
            resolution (Resolution): Resolution of the image in pixels.

        Returns:
            RelativeArea: A new instance of RelativeArea with coordinates
                and dimensions converted to relative values (0-1).
        """
        return RelativeArea(
            origin=self.origin.to_relative(resolution),
            width=self.width / resolution.width,
            height=self.height / resolution.height,
        )

    def to_nanometers(self, pixel_size_nm: float) -> NMArea:
        """
        Convert the pixel-based scanning area to nanometers.

        Args:
            pixel_size_nm (float): The size of a pixel in nanometers.

        Returns:
            NMArea: A new instance of NMArea with coordinates
                and dimensions converted to nanometers.
        """
        return NMArea(
            origin=self.origin.to_nanometers(pixel_size_nm),
            width=self.width * pixel_size_nm,
            height=self.height * pixel_size_nm,
        )

    def to_meters(self, pixel_size_m: float) -> MArea:
        """
        Convert the pixel-based area to meters.

        Args:
            pixel_size_m (float): The size of a pixel in meters.

        Returns:
            MArea: A new instance of MArea with coordinates
                and dimensions converted to meters.
        """
        return MArea(
            origin=self.origin.to_meters(pixel_size_m),
            width=self.width * pixel_size_m,
            height=self.height * pixel_size_m,
        )


class NMArea(_Area[NMPoint, float]):
    """Represents an area in nanometers."""

    def to_relative(self, resolution: Resolution, pixel_size_nm: float) -> RelativeArea:
        """
        Convert the nanometer-based area to relative coordinates.

        Args:
            resolution (Resolution): Resolution of the image in pixels.
            pixel_size_nm (float): The size of a pixel in nanometers.

        Returns:
            RelativeArea: A new instance of RelativeArea with coordinates
                and dimensions converted to relative values (0-1).
        """
        return self.to_pixels(pixel_size_nm).to_relative(resolution)

    def to_pixels(self, pixel_size_nm: float) -> PixelArea:
        """
        Convert the nanometer-based scanning area to pixel coordinates.

        Args:
            pixel_size_nm (float): The size of a pixel in nanometers.

        Returns:
            PixelArea: A new instance of PixelArea with coordinates
                and dimensions converted to absolute pixel values.
        """
        return PixelArea(
            origin=self.origin.to_pixels(pixel_size_nm),
            width=int(round(self.width / pixel_size_nm)),
            height=int(round(self.height / pixel_size_nm)),
        )

    def to_meters(self) -> MArea:
        """
        Convert the nanometer-based area to meters.

        Returns:
            MArea: A new instance of MArea with coordinates
                and dimensions converted to meters.
        """
        return MArea(
            origin=self.origin.to_meters(),
            width=self.width * 1e-9,
            height=self.height * 1e-9,
        )


class MArea(_Area[MPoint, float]):
    """Represents an area in meters."""

    def to_relative(self, resolution: Resolution, pixel_size_m: float) -> RelativeArea:
        """
        Convert the meter-based area to relative coordinates.

        Args:
            resolution (Resolution): Resolution of the image in pixels.
            pixel_size_m (float): The size of a pixel in meters.

        Returns:
            RelativeArea: A new instance of RelativeArea with coordinates
                and dimensions converted to relative values (0-1).
        """
        return self.to_pixels(pixel_size_m).to_relative(resolution)

    def to_pixels(self, pixel_size_m: float) -> PixelArea:
        """
        Convert the meter-based area to pixel coordinates.

        Args:
            pixel_size_m (float): The size of a pixel in meters.

        Returns:
            PixelArea: A new instance of PixelArea with coordinates
                and dimensions converted to absolute pixel values.
        """
        return PixelArea(
            origin=self.origin.to_pixels(pixel_size_m),
            width=int(round(self.width / pixel_size_m)),
            height=int(round(self.height / pixel_size_m)),
        )

    def to_nanometers(self) -> NMArea:
        """
        Convert the meter-based area to nanometers.

        Returns:
            NMArea: A new instance of NMArea with coordinates
                and dimensions converted to nanometers.
        """
        return NMArea(
            origin=self.origin.to_nanometers(),
            width=self.width * 1e9,
            height=self.height * 1e9,
        )
