# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from typing import Annotated

from pydantic import Field

from fibsem_maestro.core.stage_position import StagePosition
from fibsem_maestro.settings.base_settings import BaseSettings


class MicroscopeProperties(BaseSettings):
    model_config = {"extra": "allow"}

    stage_position: Annotated[
        StagePosition | None,
        Field(
            default=None,
            description="Position and orientation of the microscope stage (in nanometers and degrees).",
        ),
    ]
