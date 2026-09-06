# Released under MIT License.
# Copyright (c) 2024-2026 CEMCOF

from typing import Annotated, Literal

from pydantic import ConfigDict, Field, field_validator

from fibsem_maestro.settings.base_settings import BaseSettings
from fibsem_maestro.settings.form_utils import FormHint, WidgetType


class BasicStrategySettings(BaseSettings):
    type: Literal["basic"] = "basic"


class InterleavedStrategySettings(BaseSettings):
    type: Literal["interleaved"] = "interleaved"
    min_diff: float = Field(
        default=0.005,
        description="Minimal change in resolution relative to base resolution to consider it relevant.",
    )


SweepingStrategySettings = Annotated[
    BasicStrategySettings | InterleavedStrategySettings, Field(discriminator="type")
]


class SweepingSettings(BaseSettings):
    model_config = ConfigDict(use_enum_values=True)

    strategy: SweepingStrategySettings = Field(
        default=BasicStrategySettings(),
        description="Sweeping strategy to use.",
    )
    range: Annotated[tuple[float, float], FormHint(widget=WidgetType.RANGE_PAIR)] = (
        Field(
            default=(0.0, 0.0),
            description="Range of variable sweep in units of the sweep variable.",
        )
    )
    steps: Annotated[int, Field(gt=0)] = Field(
        default=3,
        description="Number of steps in sweeping range.",
    )
    cycles: Annotated[int, Field(gt=0)] = Field(
        default=1,
        description="Number of sweeping repeats.",
    )

    @field_validator("range")
    def validate_range(cls, r: str):
        if r[0] > r[1]:
            raise ValueError(
                f"First value of 'range' ('{r[0]}') cannot be larger than the second ('{r[1]}')"
            )
        return r
