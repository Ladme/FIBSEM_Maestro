# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field

from fibsem_maestro.core.area import RelativeArea
from fibsem_maestro.core.base_settings import BaseSettings
from fibsem_maestro.core.beam_type import BeamType
from fibsem_maestro.settings.criterion import CriterionSettings


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
    scanning_area: RelativeArea = Field(
        default=RelativeArea.full(),
        description="Area in which the scanning will be performed, defined in relative units.",
    )
    images_directory: Path = Field(
        default=Path("images"),
        description="Path to a directory where the acquired images should be saved.",
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
        description="Imaging runs every N-th slice. If None, imaging will never run.",
    )
    criterion: CriterionSettings | None = Field(
        default=None,
        description="Settings for the criterion to use to calculate image sharpness.",
    )
