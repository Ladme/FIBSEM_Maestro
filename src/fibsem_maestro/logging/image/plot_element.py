# Released under MIT License.
# Copyright (c) 2024-2026 CEMCOF


from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class PlotElement:
    """Base class for elements drawn on a plot."""

    color: str
    linewidth: float


@dataclass(frozen=True)
class Curve(PlotElement):
    """
    A single plot curve defined by x/y data.

    Attributes:
        x: Sequence of x-values. If None, the curve is plotted as y[i] vs. i.
        y: Sequence of y-values.
        color: Line color for rendering.
        linewidth: Line width for rendering.
    """

    x: Sequence[float] | None
    y: Sequence[float]


@dataclass(frozen=True)
class VerticalLine(PlotElement):
    """
    A vertical line drawn on a plot at a fixed x position.

    Attributes:
        x: The x-coordinate at which to draw the vertical line.
        color: Line color.
        linewidth: Line width for rendering.
    """

    x: float
