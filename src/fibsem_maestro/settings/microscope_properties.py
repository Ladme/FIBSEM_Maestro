# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from typing import Annotated, Any

from pydantic import Field

from fibsem_maestro.core.stage_position import StagePosition
from fibsem_maestro.settings.base_settings import BaseSettings
from fibsem_maestro.settings.beam_properties import BeamProperties
from fibsem_maestro.settings.reactive import ReactiveDict


class MicroscopeProperties(BaseSettings):
    stage_position: Annotated[
        StagePosition | None,
        Field(
            default=None,
            description="Position and orientation of the microscope stage (in nanometers and degrees).",
        ),
    ]
    electron_beam: Annotated[
        BeamProperties | None,
        Field(default=None, description="Properties of the electron beam."),
    ]
    ion_beam: Annotated[
        BeamProperties | None,
        Field(default=None, description="Properties of the ion beam."),
    ]
    internal: Annotated[
        ReactiveDict[str, Any] | None,
        Field(
            default=None, description="Custom internal properties of the microscope."
        ),
    ]
