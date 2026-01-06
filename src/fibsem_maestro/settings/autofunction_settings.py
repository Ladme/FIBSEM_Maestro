# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from dataclasses import field
from typing import Annotated, Literal

from pydantic import Field

from fibsem_maestro.settings.base_settings import BaseSettings
from fibsem_maestro.settings.sweeping_settings import SweepingSettings


class BasicMode(BaseSettings):
    type: Literal["basic"] = "basic"


class LineMode(BaseSettings):
    type: Literal["line"] = "line"
    pre_imaging_delay: Annotated[
        float,
        Field(
            description="Delay before acquisition of the first section in scanning sweep."
        ),
    ]
    lines_per_sweep: Annotated[
        int, Field(description="Number of lines scanned per one sweep value.")
    ]
    forbidden_stripe_indices: list[int] = field(default_factory=list)
    stripe_separator_threshold: int = 10
    minimal_stripe_width: int = 5


class StepMode(BaseSettings):
    type: Literal["step"] = "step"


class ManufacturerMode(BaseSettings):
    type: Literal["manufacturer"] = "manufacturer"


AutofocusMode = Annotated[
    BasicMode | LineMode | StepMode | ManufacturerMode, Field(discriminator="type")
]


class AutofunctionSettings(BaseSettings):
    mode: AutofocusMode
    delta_x: float
    execute_resolution: float
    execute_slices: float
    criterion_name: str
    imaging_name: str
    max_workers: int
    sweeping: SweepingSettings
