# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from typing import Annotated

from pydantic import Field, field_validator

from fibsem_maestro.autofunctions.sweeping_registry import SweepingRegistry
from fibsem_maestro.core.beam_type import BeamType
from fibsem_maestro.microscope.abstract_control.beam_control import BeamControl
from fibsem_maestro.settings.base_settings import BaseSettings


class SweepingSettings(BaseSettings):
    strategy: Annotated[str, Field(description="Sweeping function to use.")]
    range: Annotated[tuple[float, float], Field(description="Range of variable sweep.")]
    steps: Annotated[int, Field(gt=0, description="Number of steps in sweeping range.")]
    cycles: Annotated[int, Field(gt=0, description="Number of sweeping repeats.")]
    target_beam: Annotated[
        BeamType, Field(description="Beam which property should be optimized.")
    ]
    target_attribute: Annotated[str, Field(description="Attribute to optimize.")]

    @field_validator("strategy")
    def validate_strategy(cls, s: str):
        if not SweepingRegistry.has(s):
            raise ValueError(
                f"Invalid sweeping strategy '{s}'. Allowed: {SweepingRegistry.allowed()}"
            )

        return s

    @field_validator("target_attribute")
    def validate_target_attribute(cls, a: str):
        beam_attributes = BeamControl.get_property_names()
        if a not in beam_attributes:
            raise ValueError(
                f"Invalid beam attribute '{a}'. Allowed: {beam_attributes}"
            )

        return a

    @field_validator("range")
    def validate_range(cls, r: str):
        if r[0] > r[1]:
            raise ValueError(
                f"First value of 'range' ('{r[0]}') cannot be larger than the second ('{r[1]}')"
            )
        return r
