# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from typing import Annotated, Literal

from pydantic import AfterValidator, Field

from fibsem_maestro.core.area import RelativeArea
from fibsem_maestro.core.detail_band import DetailBand
from fibsem_maestro.criterion.functions import CRITERION_FUNCTIONS
from fibsem_maestro.criterion.reductors import REDUCTORS
from fibsem_maestro.settings.base_settings import BaseSettings
from fibsem_maestro.settings.form_utils import FieldUnit, FormHint, WidgetType

ReductionName = Annotated[
    str,
    AfterValidator(REDUCTORS.validate),
    FormHint(widget=WidgetType.DROPDOWN, choices=lambda: list(REDUCTORS)),
]
CriterionName = Annotated[
    str,
    AfterValidator(CRITERION_FUNCTIONS.validate),
    FormHint(widget=WidgetType.DROPDOWN, choices=lambda: list(CRITERION_FUNCTIONS)),
]


class BasicMode(BaseSettings):
    type: Literal["basic"] = "basic"


class MaskMode(BaseSettings):
    type: Literal["mask"] = "mask"
    mask_name: str = Field(default="mask", description="Name of the mask to use.")
    region_reduction_fn: ReductionName = Field(
        default="mean",
        description="Method for calculating final criterion from all masked regions. Accepts numpy functions (min, mean).",
    )


CriterionCalculationMode = Annotated[BasicMode | MaskMode, Field(discriminator="type")]


class SingleTileMode(BaseSettings):
    type: Literal["single"] = "single"


class MultiTileMode(BaseSettings):
    type: Literal["multi"] = "multi"
    tile_reduction_fn: ReductionName = Field(
        default="mean",
        description="Method for calculating final criterion from all tiles. Accepts numpy functions (min, mean).",
    )
    tile_size: Annotated[float, Field(gt=0), FieldUnit(suffix="nm")] = Field(
        default=0.0, description="Tile size for criterion calculation."
    )
    relative_overlap: Annotated[float, Field(ge=0, le=1)] = Field(
        default=0.0, description="Relative overlap between the tiles."
    )


CriterionTilingMode = Annotated[
    SingleTileMode | MultiTileMode, Field(discriminator="type")
]


class CriterionSettings(BaseSettings):
    sharpness_metric_fn: CriterionName = Field(
        default="bandpass",
        description="Criterion calculation function.",
    )
    detail: Annotated[
        DetailBand,
        FormHint(widget=WidgetType.DETAIL_BAND),
        FieldUnit(suffix="nm"),
        Field(ge=0.0),
    ] = Field(
        default=DetailBand(low=0.0, high=0.0),
        description="Bandpass parameters: low and high details to filter out.",
    )
    area: Annotated[
        list[RelativeArea], FormHint(widget=WidgetType.AREA_SELECT, max_areas=1)
    ] = Field(
        default_factory=lambda: [RelativeArea.full()],
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
