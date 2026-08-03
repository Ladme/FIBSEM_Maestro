# Released under MIT License.
# Copyright (c) 2024-2026 CEMCOF


from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from fibsem_maestro.core.point import Point


@dataclass(frozen=True)
class Overlay:
    """Base class for overlay elements drawn on images."""

    pass


@dataclass(frozen=True)
class RectangleOverlay(Overlay):
    """
    Axis-aligned rectangular overlay drawn on top of an image.

    Attributes:
        x: X-coordinate of the rectangle's top-left corner.
        y: Y-coordinate of the rectangle's top-left corner.
        width: Rectangle width in image coordinate units.
        height: Rectangle height in image coordinate units.
        color: Outline color.
        alpha: Transparency of the rectangle outline.
        linewidth: Line width used to draw the rectangle.
    """

    x: float
    y: float
    width: float
    height: float
    color: str = "black"
    alpha: float = 1.0
    linewidth: float = 1.0


@dataclass(frozen=True)
class PolylineOverlay(Overlay):
    """
    A polyline overlay defined by a sequence of connected points.

    Attributes:
        points: Sequence of point objects forming the polyline.
        color: Line color.
        linewidth: Line width used to draw the polyline.
    """

    # TODO: change point to a non-generic structure
    points: Sequence[Point]
    color: str = "black"
    linewidth: float = 1.0


@dataclass(frozen=True)
class HeatmapOverlay(Overlay):
    """
    Heatmap overlay rendered semi-transparently on top of an image.

    Attributes:
        data: 2D array-like numeric data representing heatmap intensity.
        alpha: Transparency level of the heatmap.
    """

    data: Any  # TODO: add proper type hint
    alpha: float = 0.5


@dataclass(frozen=True)
class VerticalLineOverlay(Overlay):
    """
    Vertical line overlay drawn across the entire image.

    Attributes:
        x: X-coordinate of the vertical line.
        color: Line color.
        linewidth: Line width of the rendered line.
    """

    x: float
    color: str = "black"
    linewidth: float = 1.0
