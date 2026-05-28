# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from typing import Annotated, Literal

from pydantic import AfterValidator, Field

from fibsem_maestro.core.area import RelativeArea
from fibsem_maestro.core.base_settings import BaseSettings
from fibsem_maestro.core.detail_band import DetailBand
from fibsem_maestro.criterion.functions import CRITERION_FUNCTIONS
from fibsem_maestro.criterion.reductors import REDUCTORS

ReductionName = Annotated[str, AfterValidator(REDUCTORS.validate)]
CriterionName = Annotated[str, AfterValidator(CRITERION_FUNCTIONS.validate)]


class BasicMode(BaseSettings):
    type: Literal["basic"] = "basic"


class MaskMode(BaseSettings):
    type: Literal["mask"] = "mask"
    mask_name: str = Field(description="Name of the mask to use.")
    region_reduction_fn: ReductionName = Field(
        description="Method for calculating final criterion from all masked regions. Accepts numpy functions (min, mean)."
    )


CriterionCalculationMode = Annotated[BasicMode | MaskMode, Field(discriminator="type")]


class SingleTileMode(BaseSettings):
    type: Literal["single"] = "single"


class MultiTileMode(BaseSettings):
    type: Literal["multi"] = "multi"
    tile_reduction_fn: ReductionName = Field(
        description="Method for calculating final criterion from all tiles. Accepts numpy functions (min, mean).",
    )
    tile_size: float = Field(
        gt=0.0, description="Tile size for criterion calculation (in nm)."
    )
    relative_overlap: float = Field(
        ge=0, le=1, description="Relative overlap between the tiles."
    )


CriterionTilingMode = Annotated[
    SingleTileMode | MultiTileMode, Field(discriminator="type")
]


class CriterionSettings(BaseSettings):
    sharpness_metric_fn: CriterionName = Field(
        description="Criterion calculation function.",
    )
    detail: DetailBand = Field(
        description="Bandpass parameters: low and high details to filter out (in nm).",
    )
    area: RelativeArea = Field(
        default=RelativeArea.full(),
        description="Relative area of the image that should be used for image criterion calculation.",
    )
    log_sharpness_map: bool = Field(
        default=False,
        description="Should log sharpness map(s).",
    )
    log_best_tile: bool = Field(
        default=False,
        description="Should log the tile with the best sharpness.",
    )
    calculation_mode: CriterionCalculationMode = Field(
        default=BasicMode(),
        description="Mode of calculation.",
    )
    tiling_mode: CriterionTilingMode = Field(
        default=SingleTileMode(),
        description="Mode of tiling.",
    )
