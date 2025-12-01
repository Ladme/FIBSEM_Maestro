# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from typing import Annotated, Literal

from pydantic import Field, field_validator

from fibsem_maestro.core.detail_band import DetailBand
from fibsem_maestro.image_criteria.criterion_registry import CriterionRegistry
from fibsem_maestro.image_criteria.reductors_registry import ReductorsRegistry
from fibsem_maestro.settings.base_settings import BaseSettings


class BasicMode(BaseSettings):
    type: Literal["basic"] = "basic"
    get_best_tile: bool = Field(
        False, description="Should return the tile with the best resolution."
    )
    border_fraction: Annotated[
        float,
        Field(
            ge=0,
            le=1,
            description="Fraction of image size that will be excluded from image criterion calculation.",
        ),
    ]


class MapMode(BaseSettings):
    type: Literal["map"] = "map"
    get_best_tile: bool = Field(
        False, description="Should return the tile with the best resolution."
    )


class MaskMode(BaseSettings):
    type: Literal["mask"] = "mask"
    mask_name: str = Field(..., description="Name of the mask to use.")
    region_reduction_fn: str = Field(
        ...,
        description="Method for calculating final criterion from all masked regions. Accepts numpy functions (min, mean).",
    )
    border_fraction: Annotated[
        float,
        Field(
            ge=0,
            le=1,
            description="Fraction of image size that will be excluded from image criterion calculation.",
        ),
    ]

    @field_validator("region_reduction_fn")
    def validate_reduction(cls, v: str):
        if not ReductorsRegistry.has(v):
            raise ValueError(
                f"Invalid numpy function '{v}'. Allowed: {ReductorsRegistry.allowed()}"
            )

        return v


CriterionCalculationMode = Annotated[
    BasicMode | MapMode | MaskMode, Field(discriminator="type")
]


class SingleTileMode(BaseSettings):
    type: Literal["single"] = "single"


class MultiTileMode(BaseSettings):
    type: Literal["multi"] = "multi"
    tile_reduction_fn: str = Field(
        ...,
        description="Method for calculating final criterion from all tiles. Accepts numpy functions (min, mean).",
    )
    tile_size: Annotated[
        float, Field(gt=0.0, description="Tile size for criterion calculation.")
    ]
    relative_overlap: Annotated[
        float, Field(ge=0, le=1, description="Relative overlap between the tiles.")
    ]

    @field_validator("tile_reduction_fn")
    def validate_reduction(cls, v: str):
        if not ReductorsRegistry.has(v):
            raise ValueError(
                f"Invalid numpy function '{v}'. Allowed: {ReductorsRegistry.allowed()}"
            )

        return v


CriterionTilingMode = Annotated[
    SingleTileMode | MultiTileMode, Field(discriminator="type")
]


class CriterionSettings(BaseSettings):
    resolution_metric_fn: str = Field(
        ..., description="Criterion calculation function."
    )
    detail: DetailBand = Field(
        ..., description="Bandpass parameters (low and high details to filter out)."
    )
    calculation_mode: CriterionCalculationMode = Field(
        ..., description="Mode of calculation."
    )
    tiling_mode: CriterionTilingMode = Field(..., description="Mode of tiling.")

    @field_validator("resolution_metric_fn")
    def validate_function(cls, v: str):
        if not CriterionRegistry.has(v):
            raise ValueError(
                f"Invalid quality_metric_fn '{v}'. Allowed: {CriterionRegistry.allowed()}"
            )
        return v
