# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from typing import Annotated, Literal

from pydantic import Field, field_validator

from fibsem_maestro.core.area import RelativeArea
from fibsem_maestro.core.detail_band import DetailBand
from fibsem_maestro.criterion.criterion_registry import CriterionRegistry
from fibsem_maestro.criterion.reductors_registry import ReductorsRegistry
from fibsem_maestro.settings.base_settings import BaseSettings


class BasicMode(BaseSettings):
    type: Literal["basic"] = "basic"


class MaskMode(BaseSettings):
    type: Literal["mask"] = "mask"
    mask_name: Annotated[str, Field(description="Name of the mask to use.")]
    region_reduction_fn: Annotated[
        str,
        Field(
            description="Method for calculating final criterion from all masked regions. Accepts numpy functions (min, mean).",
        ),
    ]

    @field_validator("region_reduction_fn")
    def validate_reduction(cls, v: str):
        if not ReductorsRegistry.has(v):
            raise ValueError(
                f"Invalid numpy function '{v}'. Allowed: {ReductorsRegistry.allowed()}"
            )

        return v


CriterionCalculationMode = Annotated[BasicMode | MaskMode, Field(discriminator="type")]


class SingleTileMode(BaseSettings):
    type: Literal["single"] = "single"


class MultiTileMode(BaseSettings):
    type: Literal["multi"] = "multi"
    tile_reduction_fn: Annotated[
        str,
        Field(
            description="Method for calculating final criterion from all tiles. Accepts numpy functions (min, mean).",
        ),
    ]
    tile_size: Annotated[
        float, Field(gt=0.0, description="Tile size for criterion calculation (in nm).")
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
    sharpness_metric_fn: Annotated[
        str, Field(description="Criterion calculation function.")
    ]
    detail: Annotated[
        DetailBand,
        Field(
            description="Bandpass parameters: low and high details to filter out (in nm).",
        ),
    ]
    area: Annotated[
        RelativeArea,
        Field(
            default=RelativeArea.full(),
            description="Relative area of the image that should be used for image criterion calculation.",
        ),
    ]
    log_sharpness_map: Annotated[
        bool, Field(default=False, description="Should log sharpness map(s).")
    ]
    log_best_tile: Annotated[
        bool,
        Field(
            default=False, description="Should log the tile with the best sharpness."
        ),
    ]
    calculation_mode: Annotated[
        CriterionCalculationMode, Field(description="Mode of calculation.")
    ]
    tiling_mode: Annotated[CriterionTilingMode, Field(description="Mode of tiling.")]

    @field_validator("sharpness_metric_fn")
    def validate_function(cls, v: str):
        if not CriterionRegistry.has(v):
            raise ValueError(
                f"Invalid sharpness_metric_fn '{v}'. Allowed: {CriterionRegistry.allowed()}"
            )
        return v
