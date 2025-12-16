# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from pydantic import field_validator

from fibsem_maestro.microscope.microscope_registry import MicroscopeRegistry
from fibsem_maestro.settings.base_settings import BaseSettings


class MicroscopeSettings(BaseSettings):
    control: str
    beam_shift_tolerance: float
    ip_address: str
    relative_beam_shift_to_stage: tuple[float, float]
    stage_tolerance: float
    stage_trials: int

    @field_validator("control")
    def validate_control(cls, c: str):
        if not MicroscopeRegistry.has(c):
            raise ValueError(
                f"Invalid microscope control type '{c}'. Allowed: {MicroscopeRegistry.allowed()}"
            )

        return c
