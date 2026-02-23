# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from dataclasses import dataclass

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
