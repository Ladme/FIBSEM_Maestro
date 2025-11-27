# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from dataclasses import dataclass


@dataclass(frozen=True)
class Point:
    """Coordinates of a point in two-dimensional space."""

    x: int
    y: int
