# Released under MIT License.
# Copyright (c) 2024-2026 CEMCOF


from enum import Enum
from typing import Annotated, Literal

from pydantic import Field

from fibsem_maestro.core.beam_type import BeamType
from fibsem_maestro.imaging.imaging import Imaging
from fibsem_maestro.properties.beam_properties import BeamProperties
from fibsem_maestro.settings.base_settings import BaseSettings
from fibsem_maestro.settings.criterion_settings import CriterionSettings
from fibsem_maestro.settings.form_utils import (
    FieldUnit,
    FormHint,
    NestedUnion,
    WidgetType,
)
from fibsem_maestro.settings.property_names import PropertyNames
from fibsem_maestro.settings.sweeping_settings import SweepingSettings


class BasicMode(BaseSettings):
    type: Literal["basic"] = "basic"
    sweeping: SweepingSettings = Field(
        default_factory=SweepingSettings,
        description="Settings for sweeping to be used.",
    )
    criterion: CriterionSettings = Field(
        default_factory=CriterionSettings,
        description="Setting for criterion to be used.",
    )


class LineMode(BaseSettings):
    type: Literal["line"] = "line"
    sweeping: SweepingSettings = Field(
        default_factory=SweepingSettings,
        description="Settings for sweeping to be used.",
    )
    criterion: CriterionSettings = Field(
        default_factory=CriterionSettings,
        description="Setting for criterion to be used.",
    )
    lines_per_sweep: Annotated[int, Field(gt=0)] = Field(
        default=5, description="Number of lines scanned per one sweep value."
    )
    pre_imaging_delay: Annotated[float, Field(ge=0.0), FieldUnit(suffix="s")] = Field(
        default=0.0,
        description="Delay before acquisition of the first section in scanning sweep.",
    )
    line_time_correction_factor: Annotated[float, Field(gt=0.0)] = Field(
        default=1.0, description="Correction factor applied to estimated line time."
    )
    forbidden_stripe_indices: list[int] = Field(
        default_factory=list,
        description="Indices of stripes which should be excluded from the analysis.",
    )
    stripe_separator_threshold: Annotated[int, Field(gt=0)] = Field(
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
        default_factory=SweepingSettings,
        description="Settings for sweeping to be used.",
    )
    criterion: CriterionSettings = Field(
        default_factory=CriterionSettings,
        description="Setting for criterion to be used.",
    )


class AutoscriptFunctionBase(BaseSettings):
    """
    Base for auto-functions delegated to Autoscript's `auto_functions` API.

    Attributes:
        type: Outer discriminator. Identical for every Autoscript variant.
    """

    type: Literal["autoscript"] = "autoscript"


class AutoscriptAutoFocusMethod(Enum):
    STANDARD = "standard"
    VOLUMESCOPE = "volumescope"


class AutoscriptAutoFocus(AutoscriptFunctionBase):
    target_attribute: Literal["working_distance"] = "working_distance"
    method: AutoscriptAutoFocusMethod = Field(
        default=AutoscriptAutoFocusMethod.STANDARD,
        description="Autofocus algorithm to use.",
    )
    working_distance_step: Annotated[
        float | None, Field(ge=0), FieldUnit(suffix="nm")
    ] = Field(
        default=None,
        description="Working distance step to use. Volumescope only; defaults if unset.",
    )
    number_of_frames: Annotated[int | None, Field(ge=0)] = Field(
        default=None,
        description="Number of frames to integrate. Volumescope only; defaults if unset.",
    )
    maximum_iterations: Annotated[int | None, Field(ge=0)] = Field(
        default=None,
        description="Max iterations for finding optimal focus. Volumescope only; defaults if unset.",
    )


class AutoscriptAutoStigmatorMethod(Enum):
    STANDARD = "standard"
    ONGETAL = "OngEtAl"


class AutoscriptAutoStigmator(AutoscriptFunctionBase):
    target_attribute: Literal["stigmator"] = "stigmator"
    method: AutoscriptAutoStigmatorMethod = Field(
        default=AutoscriptAutoStigmatorMethod.STANDARD,
        description="Autostigmator algorithm to use.",
    )
    stigmation_step: Annotated[float | None, Field(ge=0)] = Field(
        default=None,
        description="Stigmation step to use. OngEtAl only; defaults if unset.",
    )
    number_of_frames: Annotated[int | None, Field(ge=0)] = Field(
        default=None,
        description="Number of frames to integrate. OngEtAl only; defaults if unset.",
    )
    maximum_iterations: Annotated[int | None, Field(ge=0)] = Field(
        default=None,
        description="Max iterations for finding optimal stigmator settings. OngEtAl only; defaults if unset.",
    )


class AutoscriptAutoLensAlignment(AutoscriptFunctionBase):
    target_attribute: Literal["lens_alignment"] = "lens_alignment"
    number_of_frames: Annotated[int | None, Field(ge=0)] = Field(
        default=None,
        description="Number of frames to integrate. Defaults if unset.",
    )


class AutoscriptAutoSourceTilt(AutoscriptFunctionBase):
    target_attribute: Literal["source_tilt"] = "source_tilt"


AutoscriptMode = Annotated[
    AutoscriptAutoFocus
    | AutoscriptAutoStigmator
    | AutoscriptAutoLensAlignment
    | AutoscriptAutoSourceTilt,
    Field(discriminator="target_attribute"),
    NestedUnion(label="autoscript mode", follows="target_attribute"),
]

AutofocusMode = Annotated[
    BasicMode | LineMode | StepMode | AutoscriptMode,
    Field(discriminator="type"),
]


class AutofocusSettings(BaseSettings):
    linked_imaging: Annotated[
        str, FormHint(widget=WidgetType.ACTION_SELECTOR, action_type_filter=[Imaging])
    ] = Field(
        default="", description="Name of the imaging action linked to this autofocus."
    )
    target_attribute: Annotated[
        str,
        FormHint(
            widget=WidgetType.PROPERTY_SELECTOR,
            # manufacturer properties are added dynamically
            choices=lambda: list(BeamProperties.model_fields.keys()),
        ),
    ] = Field(
        default="working_distance",
        description="Attribute to optimize.",
    )
    mode: AutofocusMode = Field(
        default_factory=BasicMode,
        description="Autofocus mode to use.",
    )
    beam_type: BeamType = Field(
        default=BeamType.ELECTRON,
        description="Beam on which the autofocus should be performed.",
    )
    delta_x: Annotated[float, FieldUnit(suffix="nm")] = Field(
        default=0,
        description="Offset for out of sample focusing on the x-axis.",
    )
    execution_frequency: Annotated[int, Field(gt=0)] | None = Field(
        default=None,
        description="Autofunction runs every N-th slice. If not checked, this condition is not applied.",
    )
    sharpness_limit: Annotated[float, Field(gt=0)] | None = Field(
        default=None,
        description="Autofunction runs if image sharpness is below this limit. If not checked, this condition is not applied.",
    )
    max_workers: Annotated[int, Field(gt=0)] = Field(
        default=1,
        description="Maximal number of threads used for the calculations in this action.",
    )
    properties_to_collect: PropertyNames = Field(
        default_factory=PropertyNames,
        description="Selection of microscope and beam properties relevant for this action.",
    )
