# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from dataclasses import field
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field

from fibsem_maestro.core.beam_type import BeamType
from fibsem_maestro.settings.base_settings import BaseSettings
from fibsem_maestro.settings.criterion_settings import CriterionSettings
from fibsem_maestro.settings.property_names import PropertyNames
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
    properties_file: Path = Field(
        default=Path("autofunction_props.yaml"),
        description="Path to a file storing properties of the microscope used for autofocus.",
    )
    properties_to_collect: Annotated[
        PropertyNames,
        Field(
            default_factory=PropertyNames,
            description="Properties of the microscope and the beam relevant for the autofocus.",
        ),
    ]
    mode: AutofocusMode = Field(
        default=BasicMode(),
        description="Autofocus mode to use.",
    )
    beam_type: Annotated[
        BeamType,
        Field(default=BeamType.ELECTRON, description="Beam used for autofocus."),
    ]
    delta_x: float = Field(
        default=0,
        description="Offset for out of sample focusing on the x-axis in nm.",
    )
    sharpness_limit: Annotated[float, Field(gt=0)] | None = Field(
        default=None,
        description="Autofunction runs only if image sharpness is below this limit. None disables this condition.",
    )
    execution_frequency: Annotated[int, Field(gt=0)] | None = Field(
        default=None,
        description="Autofunction runs only every N-th slice. None disables this condition.",
    )
    max_workers: int = Field(
        default=1,
        description="Maximal number of threads used for calculation.",
    )
    sweeping: SweepingSettings = Field(
        description="Settings for sweeping to be used.",
    )
    criterion: CriterionSettings = Field(
        description="Setting for criterion to be used.",
    )
