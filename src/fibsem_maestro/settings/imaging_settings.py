# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from typing import Annotated, Literal

from pydantic import Field

from fibsem_maestro.core.area import RelativeArea
from fibsem_maestro.core.beam_type import BeamType
from fibsem_maestro.properties.global_properties import GlobalProperties
from fibsem_maestro.settings.base_settings import BaseSettings
from fibsem_maestro.settings.criterion_settings import CriterionSettings
from fibsem_maestro.settings.form_utils import FieldUnit, FormHint, WidgetType
from fibsem_maestro.settings.property_names import PropertyNames


class StandardResolution(BaseSettings):
    type: Literal["standard"] = "standard"


class ExtendedResolution(BaseSettings):
    type: Literal["extended"] = "extended"
    pixel_size: Annotated[float, Field(gt=0), FieldUnit(suffix="nm")] = Field(
        description="Requested size of each pixel."
    )


ResolutionMode = Annotated[
    StandardResolution | ExtendedResolution, Field(discriminator="type")
]


class ImagingSettings(BaseSettings):
    scanning_area: Annotated[
        list[RelativeArea], FormHint(widget=WidgetType.AREA_SELECT, max_areas=1)
    ] = Field(
        default_factory=list,
        description="Area that should be imaged.",
    )
    resolution_mode: ResolutionMode = Field(
        default=StandardResolution(),
        description="Use standard or extended resolution?",
    )
    beam_type: BeamType = Field(
        default=BeamType.ELECTRON,
        description="Beam used for imaging.",
    )
    execution_frequency: Annotated[int, Field(gt=0)] | None = Field(
        default=1,
        description="Run the action every N-th slice. If not checked, the action will never run.",
    )
    criterion: CriterionSettings | None = Field(
        default=None,
        description="Settings for the criterion to use to calculate image sharpness.",
    )
    properties_to_collect: PropertyNames = Field(
        default_factory=PropertyNames,
        description="Properties of the microscope and the beam relevant for imaging.",
    )
    external_props: GlobalProperties = Field(
        default=GlobalProperties(),
        description="External properties of the microscope to use for imaging. These properties will overwrite any current microscope properties.",
    )
