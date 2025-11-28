# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from typing import Annotated
from pydantic import Field, field_validator

from fibsem_maestro.core.detail_band import DetailBand
from fibsem_maestro.image_criteria.criterion_registry import CriterionRegistry
from fibsem_maestro.image_criteria.mode import CriterionMode
from fibsem_maestro.image_criteria.numpy_registry import NumpyRegistry
from fibsem_maestro.settings.base_settings import BaseSettings


class CriterionSettings(BaseSettings):
    # Criterion calculation function.
    resolution_metric_fn: str
    # Method for calculating final criterion from all masked regions. Accepts numpy functions (min, mean).
    region_reduction_fn: str
    # Method for calculating final criterion from all tiles. Accepts numpy functions (min, mean).
    tile_reduction_fn: str
    # Fraction of image size that will be excluded from image criterion calculation.
    border_fraction: Annotated[float, Field(ge=0, le=1)]
    # Bandpass parameters (low and high details to filter out).
    detail: DetailBand
    # Tile size for criterion calculation.
    tile_size: float
    # Relative overlap between the tiles.
    relative_overlap: Annotated[float, Field(ge=0, le=1)]
    # Mode of calculation.
    calculation_mode: CriterionMode

    @field_validator("quality_metric_fn")
    def validate_function(cls, v: str):
        if not CriterionRegistry.has(v):
            raise ValueError(
                f"Invalid quality_metric_fn '{v}'. Allowed: {CriterionRegistry.allowed()}"
            )
        return v

    @field_validator("region_reduction_fn", "tile_reduction_fn")
    def validate_numpy(cls, v: str):
        if not NumpyRegistry.has(v):
            raise ValueError(
                f"Invalid numpy function '{v}'. Allowed: {NumpyRegistry.allowed()}"
            )

        return v
