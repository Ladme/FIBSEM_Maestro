# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from dataclasses import field
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, field_validator

from fibsem_maestro.core.beam_type import BeamType
from fibsem_maestro.microscope.abstract_control.beam_control import BeamControl
from fibsem_maestro.settings.base_settings import BaseSettings
from fibsem_maestro.settings.criterion_settings import CriterionSettings
from fibsem_maestro.settings.property_names import PropertyNames
from fibsem_maestro.settings.sweeping_settings import SweepingSettings


class BasicMode(BaseSettings):
    type: Literal["basic"] = "basic"
    sweeping: SweepingSettings = Field(
        description="Settings for sweeping to be used.",
    )
    criterion: CriterionSettings = Field(
        description="Setting for criterion to be used.",
    )


class LineMode(BaseSettings):
    type: Literal["line"] = "line"
    sweeping: SweepingSettings = Field(
        description="Settings for sweeping to be used.",
    )
    criterion: CriterionSettings = Field(
        description="Setting for criterion to be used.",
    )
    pre_imaging_delay: Annotated[
        float,
        Field(
            description="Delay before acquisition of the first section in scanning sweep."
        ),
    ]
    line_time_correction_factor: Annotated[
        float,
        Field(
            default=1.0, description="Correction factor applied to estimated line time."
        ),
    ]
    lines_per_sweep: Annotated[
        int, Field(description="Number of lines scanned per one sweep value.")
    ]
    forbidden_stripe_indices: list[int] = Field(
        default_factory=list,
        description="Indices of stripes which should be excluded from the analysis.",
    )
    stripe_separator_threshold: int = Field(
        default=10,
        description="Maximal average intensity of separator rows.",
    )
    minimal_stripe_width: Annotated[int, Field(gt=0)] = Field(
        default=5,
        description="Minimum distance (in rows) between two separator rows required to consider the region a valid stripe.",
    )


class StepMode(BaseSettings):
    type: Literal["step"] = "step"
    sweeping: SweepingSettings = Field(
        description="Settings for sweeping to be used.",
    )
    criterion: CriterionSettings = Field(
        description="Setting for criterion to be used.",
    )


class AutoscriptMode(BaseSettings):
    type: Literal["autoscript"] = "autoscript"


AutofocusMode = Annotated[
    BasicMode | LineMode | StepMode | AutoscriptMode, Field(discriminator="type")
]


class AutofocusSettings(BaseSettings):
    properties_file: Path = Field(
        default=Path("autofocus_props.yaml"),
        description="Path to a file storing properties of the microscope used for autofocus.",
    )
    properties_to_collect: PropertyNames = Field(
        default_factory=PropertyNames,
        description="Properties of the microscope and the beam relevant for the autofocus.",
    )
    mode: AutofocusMode = Field(
        description="Autofocus mode to use.",
    )
    target_attribute: str = Field(
        description="Attribute to optimize via the autofocus.",
    )
    beam_type: BeamType = Field(
        default=BeamType.ELECTRON, description="Beam used for autofocus."
    )
    delta_x: float = Field(
        default=0,
        description="Offset for out of sample focusing on the x-axis in nm.",
    )
    sharpness_limit: Annotated[float, Field(gt=0)] | None = Field(
        default=None,
        description="Autofunction runs if image sharpness is below this limit. None disables this condition.",
    )
    execution_frequency: Annotated[int, Field(gt=0)] | None = Field(
        default=None,
        description="Autofunction runs every N-th slice. None disables this condition.",
    )
    max_workers: int = Field(
        default=1,
        description="Maximal number of threads used for calculation.",
    )

    @field_validator("target_attribute")
    def validate_target_attribute(cls, a: str):
        beam_attributes = BeamControl.get_property_names()
        if a not in beam_attributes:
            raise ValueError(
                f"Invalid target attribute '{a}'. Allowed: {beam_attributes}"
            )
        return a
