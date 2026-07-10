# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from typing import Annotated, Literal

from pydantic import Field

from fibsem_maestro.core.area import RelativeArea
from fibsem_maestro.settings.base_settings import BaseSettings
from fibsem_maestro.settings.form_utils import (
    AreaOverlay,
    FieldUnit,
    FormHint,
    WidgetType,
)


class StandardMode(BaseSettings):
    type: Literal["standard"] = "standard"


class SubpixelMode(BaseSettings):
    type: Literal["subpixel"] = "subpixel"
    upsampling_factor: Annotated[float, Field(ge=1.0)] = Field(
        default=1.0, description="How many times should the image be upsampled?"
    )


TemplateMatchingMode = Annotated[
    StandardMode | SubpixelMode, Field(discriminator="type")
]


class FullFrameMode(BaseSettings):
    type: Literal["full_frame"] = "full_frame"
    dummy_scans: int = Field(
        default=0,
        description="The number of dummy scans to perform before starting the main scan for template matching.",
    )


class ReducedAreaMode(BaseSettings):
    type: Literal["reduced_area"] = "reduced_area"
    full_frame_dummy_scans: int = Field(
        default=0,
        description="The number of full frame dummy scans to perform before starting the main scan for template matching.",
    )
    reduced_area_dummy_scans: int = Field(
        default=0,
        description="The number of reduced area dummy scans to perform before starting the main scan for template matching. This number of dummy scans will be performed for each area of interest.",
    )


FrameGrabbingMode = Annotated[
    FullFrameMode | ReducedAreaMode, Field(discriminator="type")
]


class TemplateMatchingSettings(BaseSettings):
    matching_mode: TemplateMatchingMode = Field(
        default_factory=StandardMode,
        description="Template matching mode.",
    )
    frame_grabbing_mode: FrameGrabbingMode = Field(
        default_factory=FullFrameMode,
        description="Should the areas for template matching be obtained by scanning the full frame and cropping or by using reduced scanning area.",
    )
    template_scans: Annotated[int, Field(gt=0)] = Field(
        default=1,
        description="The number of scans to perform when obtaining or updating templates. The final template will be the average of all scans.",
    )
    areas: Annotated[
        list[RelativeArea],
        FormHint(
            widget=WidgetType.AREA_SELECT,
            max_areas=None,
            area_overlay=AreaOverlay.SHOW_MARGIN,
            overlay_source="correction_margin",
        ),
    ] = Field(
        default_factory=list,
        description="Areas of the image used for template matching.",
    )
    min_confidence: Annotated[float | None, Field(gt=0.0)] = Field(
        default=None,
        description="Minimal cross-correlation value required for a template match to be accepted as a valid drift measurement.",
    )
    maximal_drift: Annotated[float | None, FieldUnit(suffix="nm"), Field(gt=0.0)] = (
        Field(
            default=None,
            description="Maximal accepted drift obtained from template matching.",
        )
    )
    update_frequency: Annotated[int | None, Field(gt=0)] = Field(
        default=None,
        description="Templates are updated every Nth slice. If not checked, this condition is not applied.",
    )
    update_confidence_limit: Annotated[float | None, Field(gt=0.0)] = Field(
        default=None,
        description="Templates are updated if the match confidence is below this limit. If not checked, this condition is not applied.",
    )
    blur: Annotated[int | None, FieldUnit(suffix="px"), Field(gt=0)] = Field(
        default=None,
        description="Standard deviation of a Gaussian filter applied to the image before template matching.",
    )
    correction_margin: Annotated[float, FieldUnit(suffix="nm")] = Field(
        default=0.0,
        description="The maximum expected drift defining how far the template is allowed to search for a match.",
    )
