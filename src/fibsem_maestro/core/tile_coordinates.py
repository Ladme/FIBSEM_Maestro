# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from dataclasses import dataclass

from fibsem_maestro.core.point import PixelPoint


@dataclass(frozen=True)
class TileCoordinates:
    """
    Represents the coordinates and dimensions of a tile in pixels.

    Attributes:
        origin (PixelPoint):
            The top-left coordinate of the tile (in pixels).
        width_px (int):
            The width of the tile in pixels.
        height_px (int):
            The height of the tile in pixels.
    """

    origin: PixelPoint
    width_px: int
    height_px: int
