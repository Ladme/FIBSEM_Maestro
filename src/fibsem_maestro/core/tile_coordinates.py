# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from dataclasses import dataclass

from fibsem_maestro.core.point import PixelPoint


@dataclass(frozen=True)
class TileCoordinates:
    """Top-left coordinate and pixel size of a tile."""

    origin: PixelPoint
    width_px: int
    height_px: int
