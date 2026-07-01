# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from dataclasses import dataclass
from typing import Any

import numpy as np

from fibsem_maestro.core.area import PixelArea
from fibsem_maestro.core.image import Image


class SharpnessMap(np.ndarray[Any, np.dtype[np.floating[Any]]]):
    pass


@dataclass(frozen=True)
class CriterionResult:
    sharpness: float
    tiles_px: list[PixelArea]
    best_tile: Image | None = None
    sharpness_map: SharpnessMap | None = None
