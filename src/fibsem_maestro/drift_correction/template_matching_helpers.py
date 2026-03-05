# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from dataclasses import dataclass, field

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


@dataclass
class ShiftsCollection:
    dx: dict[int, float] = field(default_factory=dict)
    """Horizontal shifts in nanometers for individual templates."""
    dy: dict[int, float] = field(default_factory=dict)
    """Vertical shifts in nanometers for individual templates."""

    def get_mean_shift(self) -> tuple[float, float] | None:
        """
        Returns the mean horizontal and vertical shift across all templates.

        Returns:
            A tuple of (mean_dx, mean_dy) in nanometers, or None if either
            collection is empty.
        """
        if len(self.dx) == 0 or len(self.dy) == 0:
            return None

        return (
            float(np.mean(list(self.dx.values()))),
            float(np.mean(list(self.dy.values()))),
        )
