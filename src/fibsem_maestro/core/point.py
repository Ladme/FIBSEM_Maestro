# Released under MIT License.
# Copyright (c) 2024-2026 CEMCOF


from typing import Any, Generic, TypeVar

from pydantic import BaseModel

from fibsem_maestro.core.resolution import Resolution

T = TypeVar("T", int, float)


class Point(BaseModel, Generic[T]):
    """
    Represents a point in two-dimensional space.

    Attributes:
        x (T): The x-coordinate of the point.
        y (T): The y-coordinate of the point.
    """

    x: T
    y: T

    def __init__(self, x: T, y: T):
        # pydantic BaseModel requires keyword arguments
        super().__init__(x=x, y=y)

    def _check_same_type(self, other: Any):
        """Ensure operations only occur between instances of the same subclass."""
        if type(self) is not type(other):
            raise TypeError(
                f"Operation not allowed between {type(self).__name__} "
                f"and {type(other).__name__}"
            )

    def __mul__(self, other: Any):
        """Multiply this point by another point of the same type or by a scalar."""
        if isinstance(other, int):
            return type(self)(self.x * other, self.y * other)

        if isinstance(other, float):
            if isinstance(self.x, float) and isinstance(self.y, float):
                return type(self)(self.x * other, self.y * other)

            raise TypeError("Cannot multiply integer point by float")

        if isinstance(other, Point):
            self._check_same_type(other)
            return type(self)(self.x * other.x, self.y * other.y)

        raise TypeError("Unsupported operand type")

    def __add__(self, other: Any):
        """Add this point to another point of the same class."""
        if isinstance(other, Point):
            self._check_same_type(other)
            return type(self)(self.x + other.x, self.y + other.y)

        raise TypeError("Unsupported operand type")

    def __sub__(self, other: Any):
        """Subtract another point of the same class."""
        if isinstance(other, Point):
            self._check_same_type(other)
            return type(self)(self.x - other.x, self.y - other.y)

        raise TypeError("Unsupported operand type")


class PixelPoint(Point[int]):
    """Point expressed in pixel coordinates."""

    def __init__(self, x: int, y: int):
        # pydantic BaseModel requires keyword arguments
        super().__init__(x=x, y=y)

    def to_relative(self, resolution: Resolution) -> "RelativePoint":
        """
        Convert pixel coordinates to relative (0-1) coordinates.

        Args:
            resolution (Resolution): Resolution of the image in pixels.

        Returns:
            RelativePoint: Point expressed in normalized coordinates.
        """
        return RelativePoint(self.x / resolution.width, self.y / resolution.height)

    def to_nanometers(self, pixel_size_nm: float) -> "NMPoint":
        """
        Convert pixel coordinates to nanometer coordinates.

        Args:
            pixel_size_nm (float): Size of a pixel in nanometers.

        Returns:
            NMPoint: Point expressed in nanometers.
        """
        return NMPoint(self.x * pixel_size_nm, self.y * pixel_size_nm)

    def to_meters(self, pixel_size_m: float) -> "MPoint":
        """
        Convert pixel coordinates to meter coordinates.

        Args:
            pixel_size_m (float): Size of a pixel in meters.

        Returns:
            MPoint: Point expressed in meters.
        """
        return MPoint(self.x * pixel_size_m, self.y * pixel_size_m)


class NMPoint(Point[float]):
    """Point expressed in nanometer coordinates."""

    def __init__(self, x: float, y: float):
        # pydantic BaseModel requires keyword arguments
        super().__init__(x=x, y=y)

    def to_meters(self) -> "MPoint":
        """
        Convert nanometers to meters.

        Returns:
            MPoint: Point expressed in meters.
        """
        return MPoint(self.x * 1e-9, self.y * 1e-9)

    def to_pixels(self, pixel_size_nm: float) -> "PixelPoint":
        """
        Convert nanometer coordinates to pixel coordinates.

        Args:
            pixel_size_nm (float): Size of a pixel in nanometers.

        Returns:
            PixelPoint: Point expressed in pixels.
        """
        return PixelPoint(
            int(round(self.x / pixel_size_nm)), int(round(self.y / pixel_size_nm))
        )

    def to_relative(
        self, resolution: Resolution, pixel_size_nm: float
    ) -> "RelativePoint":
        """
        Convert nanometer coordinates to relative (0-1) coordinates.

        Args:
            resolution (Resolution): Resolution of the image in pixels.
            pixel_size_nm (float): Size of a pixel in nanometers.

        Returns:
            RelativePoint: Point expressed in relative coordinates.
        """
        return self.to_pixels(pixel_size_nm).to_relative(resolution)


class MPoint(Point[float]):
    """Point expressed in meter coordinates."""

    def __init__(self, x: float, y: float):
        # pydantic BaseModel requires keyword arguments
        super().__init__(x=x, y=y)

    def to_nanometers(self) -> "NMPoint":
        """
        Convert meters to nanometers.

        Returns:
            NMPoint: Point expressed in nanometers.
        """
        return NMPoint(self.x * 1e9, self.y * 1e9)

    def to_pixels(self, pixel_size_m: float) -> "PixelPoint":
        """
        Convert meter coordinates to pixel coordinates.

        Args:
            pixel_size_m (float): Size of a pixel in meters.

        Returns:
            PixelPoint: Point expressed in pixels.
        """
        return PixelPoint(
            int(round(self.x / pixel_size_m)), int(round(self.y / pixel_size_m))
        )

    def to_relative(
        self, resolution: Resolution, pixel_size_m: float
    ) -> "RelativePoint":
        """
        Convert meters to relative (0-1) coordinates.

        Args:
            resolution (Resolution): Resolution of the image in pixels.
            pixel_size_m (float): Size of a pixel in meters.

        Returns:
            RelativePoint: Point expressed in normalized coordinates.
        """
        return self.to_pixels(pixel_size_m).to_relative(resolution)


class RelativePoint(Point[float]):
    """Point expressed in normalized 0-1 coordinates."""

    def __init__(self, x: float, y: float):
        # pydantic BaseModel requires keyword arguments
        super().__init__(x=x, y=y)

    def to_pixels(self, resolution: Resolution) -> "PixelPoint":
        """Convert relative coordinates (0-1) to pixel coordinates.

        Args:
            resolution (Resolution): Resolution of the image in pixels.

        Returns:
            PixelPoint: Point expressed in pixels.
        """
        return PixelPoint(
            int(round(self.x * resolution.width)),
            int(round(self.y * resolution.height)),
        )

    def to_nanometers(self, resolution: Resolution, pixel_size_nm: float) -> "NMPoint":
        """Convert relative coordinates (0-1) to nanometers.

        Args:
            resolution (Resolution): Resolution of the image in pixels.
            pixel_size_nm (float): Size of a pixel in nanometers.

        Returns:
            NMPoint: Point expressed in nanometers.
        """
        return self.to_pixels(resolution).to_nanometers(pixel_size_nm)

    def to_meters(self, resolution: Resolution, pixel_size_m: float) -> "MPoint":
        """Convert relative coordinates (0-1) to meters.

        Args:
            resolution (Resolution): Resolution of the image in pixels.
            pixel_size_m (float): Size of a pixel in meters.

        Returns:
            MPoint: Point expressed in meters.
        """
        return self.to_pixels(resolution).to_meters(pixel_size_m)
