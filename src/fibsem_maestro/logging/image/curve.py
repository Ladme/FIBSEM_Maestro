# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class Curve:
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
    color: str = "black"
    linewidth: float = 1.0
