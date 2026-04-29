# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from dataclasses import dataclass

from cv2.typing import MatLike


@dataclass(frozen=True)
class TemplateMatchResult:
    """
    Result of a single template matching operation.

    Attributes:
        dx: Horizontal pixel shift relative to the search-region center (columns).
        dy: Vertical pixel shift relative to the search-region center (rows).
        confidence: Normalized cross-correlation coefficient of the best match in the range [0, 1].
        heatmap: Full correlation map as returned by OpenCV.
    """

    dx: int
    dy: int
    confidence: float
    heatmap: MatLike
