# Released under MIT License.
# Copyright (c) 2024-2026 CEMCOF

from dataclasses import dataclass
from typing import Generic, TypeVar

from cv2.typing import MatLike

ShiftPrecision = TypeVar("ShiftPrecision", int, float)


@dataclass(frozen=True)
class TemplateMatchResult(Generic[ShiftPrecision]):
    """
    Result of a single template matching operation.

    Type Args:
        ShiftPrecision: Numeric type of the pixel shift fields; either `int` for
           integer-pixel accuracy or `float` for sub-pixel accuracy.

    Attributes:
        dx: Horizontal pixel shift relative to the search-region centre
            (columns). Positive values indicate a rightward shift.
        dy: Vertical pixel shift relative to the search-region centre
            (rows). Positive values indicate a downward shift.
        confidence: Normalised cross-correlation coefficient of the best
            match in the range `[-1, 1]`.
        heatmap: Full correlation map as returned by OpenCV.
    """

    dx: ShiftPrecision
    dy: ShiftPrecision
    confidence: float
    heatmap: MatLike
