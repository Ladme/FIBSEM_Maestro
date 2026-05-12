# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field

from fibsem_maestro.core.beam_type import BeamType
from fibsem_maestro.properties.global_properties import GlobalProperties
from fibsem_maestro.settings.base_settings import BaseSettings
from fibsem_maestro.settings.criterion_settings import CriterionSettings
from fibsem_maestro.settings.property_names import PropertyNames


class StandardResolution(BaseSettings):
    type: Literal["standard"] = "standard"


class ExtendedResolution(BaseSettings):
    type: Literal["extended"] = "extended"
    pixel_size: Annotated[
        float, Field(default=20, description="Requested size of each pixel in nm.")
    ]


ResolutionMode = Annotated[
    StandardResolution | ExtendedResolution, Field(discriminator="type")
]


class ImagingSettings(BaseSettings):
    properties_file: Path = Field(
        default=Path("imaging_props.yaml"),
        description="Path to a file storing properties of the microscope used for imaging.",
    )
    images_directory: Path = Field(
        default=Path("images"),
        description="Path to a directory where the acquired images should be saved.",
    )
    properties_to_collect: PropertyNames = Field(
        default_factory=PropertyNames,
        description="Properties of the microscope and the beam relevant for imaging.",
    )
    resolution_mode: ResolutionMode = Field(
        default=StandardResolution(),
        description="Use standard or extended resolution?",
    )
    beam_type: BeamType = Field(
        default=BeamType.ELECTRON,
        description="Beam used for imaging.",
    )
    criterion: CriterionSettings | None = Field(
        default=None,
        description="Settings for the criterion to use to calculate image sharpness.",
    )
    external_props: GlobalProperties = Field(
        default=GlobalProperties(),
        description="External properties of the microscope to use for imaging. These properties will overwrite any current microscope properties.",
    )
