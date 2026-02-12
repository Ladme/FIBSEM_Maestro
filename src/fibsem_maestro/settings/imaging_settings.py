# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from pathlib import Path
from typing import Annotated

from pydantic import Field

from fibsem_maestro.core.beam_type import BeamType
from fibsem_maestro.settings.base_settings import BaseSettings
from fibsem_maestro.settings.property_names import PropertyNames


class ImagingSettings(BaseSettings):
    properties_file: Annotated[
        Path,
        Field(
            description="Path to a file storing properties of the microscope used for imaging.",
        ),
    ]
    images_directory: Annotated[
        Path,
        Field(
            default=Path("images"),
            description="Path to a directory where the acquired images should be saved.",
        ),
    ]
    properties_to_collect: Annotated[
        PropertyNames,
        Field(
            default_factory=PropertyNames,
            description="Properties of the microscope and the beam relevant for imaging.",
        ),
    ]
    use_extended_resolution: Annotated[
        bool, Field(default=False, description="Should extended resolution be used?")
    ]
    beam_type: Annotated[
        BeamType, Field(default=BeamType.ELECTRON, description="Beam used for imaging.")
    ]
