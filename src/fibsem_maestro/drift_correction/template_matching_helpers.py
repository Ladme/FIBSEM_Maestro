# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from dataclasses import dataclass

import numpy as np
from cv2.typing import MatLike


@dataclass(frozen=True)
class TemplateMatchResult:
    """Result of template matching."""

    dx: int
    """Horizontal pixel shift relative to search-region center (columns)."""

    dy: int
    """Vertical pixel shift relative to search-region center (rows)."""

    confidence: float
    """Maximum normalized cross-correlation coefficient."""

    heatmap: MatLike
    """Full correlation map returned by OpenCV."""


@dataclass(frozen=True)
class ShiftsCollection:
    dx: list[float]
    """Horizontal shifts in nanometers for all areas with enough confidence."""

    dy: list[float]
    """Vertical shifts in nanometers for all areas with enough confidence."""

    def get_mean_shift(self) -> tuple[float, float] | None:
        if len(self.dx) == 0 or len(self.dy) == 0:
            return None

        return (float(np.mean(self.dx)), float(np.mean(self.dy)))
