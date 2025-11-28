# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from dataclasses import dataclass

import numpy as np

from fibsem_maestro.core.image import Image
from fibsem_maestro.image_criteria.numpy_registry import NumpyFunction


class ResolutionMap(np.ndarray):  # type: ignore
    pass


@dataclass(frozen=True)
class CriterionPerTileResults:
    tiles: list[Image]
    resolution: list[np.floating]

    def get_best_tile(self) -> tuple[Image, np.floating]:
        # returns tile with minimum resolution
        return min(
            zip(self.tiles, self.resolution),
            key=lambda pair: pair[1],  # compare by resolution value
        )

    def get_overall_resolution(self, reduction_function: NumpyFunction) -> np.floating:
        return reduction_function(self.resolution)


@dataclass(frozen=True)
class CriterionResult:
    resolution: np.floating
    best_tile: Image | None = None
    resolution_map: ResolutionMap | None = None
