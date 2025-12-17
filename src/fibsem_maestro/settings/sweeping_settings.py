# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from pydantic import field_validator

from fibsem_maestro.autofunctions.sweeping_registry import SweepingRegistry
from fibsem_maestro.core.beam_type import BeamType
from fibsem_maestro.microscope.abstract_control.beam_control import BeamControl
from fibsem_maestro.settings.base_settings import BaseSettings


class SweepingSettings(BaseSettings):
    strategy: str  # TODO: validate using registry
    range: tuple[float, float]
    steps: int
    cycles: int
    target_beam: BeamType
    target_attribute: str

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
