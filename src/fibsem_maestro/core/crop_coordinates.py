# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from dataclasses import dataclass


@dataclass(frozen=True)
class CropCoordinates:
    """Coordinates and size of a rectangular crop region."""

    x: int
    y: int
    width: int
    height: int
