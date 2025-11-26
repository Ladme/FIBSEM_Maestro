# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from pydantic import field_validator

from fibsem_maestro.image_criteria.registry import CriterionRegistry
from fibsem_maestro.settings.base_settings import BaseSettings


class CriterionSettings(BaseSettings):
    # Criterion calculation function.
    function: str
    # Ratio of image size that will be excluded from image criterion calculation.
    border: float
    # Method for calculating final criterion from all masked areas. Accepts numpy functions (min, mean).
    final_regions_resolution: str
    # Method for calculating final criterion from tiles. Accepts numpy functions (min, mean).
    final_resolution: str
    # The masking parameters associated with this autofunction - see the mask section.
    mask_name: str | None
    # Bandpass parameters (low and high details to filter out).
    detail: list[float]
    # Tile size for criterion calculation in pixels.
    tile_size: int

    @field_validator("function")
    def validate_function(cls, v: str):
        if not CriterionRegistry.has(v):
            raise ValueError(
                f"Invalid criterion '{v}'. Allowed: {CriterionRegistry.allowed()}"
            )
        return v
