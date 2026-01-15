# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from typing import Any

from fibsem_maestro.core.stage_position import StagePosition
from fibsem_maestro.settings.base_settings import BaseSettings
from fibsem_maestro.settings.beam_properties import BeamProperties


class MicroscopeProperties(BaseSettings):
    stage_position: StagePosition
    electron_beam: BeamProperties
    ion_beam: BeamProperties
    custom: dict[str, Any]
