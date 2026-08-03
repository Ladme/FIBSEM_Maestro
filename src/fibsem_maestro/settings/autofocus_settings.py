# Released under MIT License.
# Copyright (c) 2024-2026 CEMCOF


from typing import Annotated, Literal

from pydantic import Field

from fibsem_maestro.core.beam_type import BeamType
from fibsem_maestro.imaging.imaging import Imaging
from fibsem_maestro.properties.beam_properties import BeamProperties
from fibsem_maestro.properties.global_properties import GlobalProperties
from fibsem_maestro.settings.base_settings import BaseSettings
from fibsem_maestro.settings.criterion_settings import CriterionSettings
from fibsem_maestro.settings.form_utils import FieldUnit, FormHint, WidgetType
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


class AutoscriptMode(BaseSettings):
    type: Literal["autoscript"] = "autoscript"


AutofocusMode = Annotated[
    BasicMode | LineMode | StepMode | AutoscriptMode, Field(discriminator="type")
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
    external_props: GlobalProperties = Field(
        default=GlobalProperties(),
        description="External properties of the microscope to use for this action. These properties will overwrite any current microscope properties.",
    )
