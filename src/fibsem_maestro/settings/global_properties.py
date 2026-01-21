# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from typing import Annotated

from pydantic import Field

from fibsem_maestro.settings.base_settings import BaseSettings
from fibsem_maestro.settings.beam_properties import BeamProperties
from fibsem_maestro.settings.microscope_properties import MicroscopeProperties


class GlobalProperties(BaseSettings):
    microscope: Annotated[
        MicroscopeProperties | None,
        Field(default=None, description="General properties of the microscope."),
    ]
    electron_beam: Annotated[
        BeamProperties | None,
        Field(default=None, description="Properties of the electron beam."),
    ]
    ion_beam: Annotated[
        BeamProperties | None,
        Field(default=None, description="Properties of the ion beam."),
    ]
