# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from typing import Annotated

from pydantic import Field, field_validator

from fibsem_maestro.microscope.microscope_registry import MicroscopeRegistry
from fibsem_maestro.settings.base_settings import BaseSettings
from fibsem_maestro.settings.properties_to_collect import MicroscopePropertiesToCollect


class MicroscopeSettings(BaseSettings):
    control: Annotated[str, Field(description="Type of microscope control.")]
    beam_shift_tolerance: Annotated[
        float,
        Field(description="Relative move between beam shift and stage move."),
    ]
    ip_address: Annotated[str, Field(description="Microscope server address.")]
    relative_beam_shift_to_stage: Annotated[
        tuple[float, float],
        Field(description="Relative move between beam shift and stage move."),
    ]
    stage_tolerance: Annotated[float, Field(description="Maximal allowed stage error.")]
    stage_trials: Annotated[
        int,
        Field(
            description="Number of trials to reach the goal position before raising an error."
        ),
    ]
    properties_to_collect: Annotated[
        MicroscopePropertiesToCollect,
        Field(
            default_factory=MicroscopePropertiesToCollect,
            description="Properties of the microscope that should be written out.",
        ),
    ]

    @field_validator("control")
    def validate_control(cls, c: str):
        if not MicroscopeRegistry.has(c):
            raise ValueError(
                f"Invalid microscope control type '{c}'. Allowed: {MicroscopeRegistry.allowed()}"
            )

        return c
