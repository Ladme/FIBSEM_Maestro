# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from dataclasses import dataclass


@dataclass(frozen=True)
class TileCoordinates:
    """Top-left coordinate and size of a tile."""

    x: int
    y: int
    width: int
    height: int
