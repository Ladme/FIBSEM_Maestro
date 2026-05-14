# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from typing import Annotated

from pydantic import AfterValidator, Field

from fibsem_maestro.microscope.microscope import MICROSCOPE_CONTROLS
from fibsem_maestro.settings.base_settings import BaseSettings

MicroscopeControlName = Annotated[str, AfterValidator(MICROSCOPE_CONTROLS.validate)]


class MicroscopeSettings(BaseSettings):
    control: MicroscopeControlName = Field(description="Type of microscope control.")
    beam_shift_tolerance: float = Field(
        description="Relative move between beam shift and stage move."
    )
    ip_address: str = Field(description="Microscope server address.")
    holder_pretilt: float = Field(
        default=0.0, description="Tilt of the sample holder in degrees."
    )
    stage_tolerance: float = Field(description="Maximal allowed stage error.")
    stage_trials: int = Field(
        description="Number of trials to reach the goal position before raising an error."
    )
