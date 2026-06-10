# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field

from fibsem_maestro.core.beam_type import BeamType
from fibsem_maestro.properties.global_properties import GlobalProperties
from fibsem_maestro.settings.base_settings import BaseSettings
from fibsem_maestro.settings.form_utils import FieldUnit
from fibsem_maestro.settings.property_names import PropertyNames


class ManualMode(BaseSettings):
    type: Literal["manual"] = "manual"
    y_correction: Annotated[float, FieldUnit(suffix="nm")] = Field(
        default=0.0,
        description="Change in beam shift along the y-dimension applied during the correction.",
    )
    wd_correction: Annotated[float, FieldUnit(suffix="nm")] = Field(
        default=0.0,
        description="Change in working distance applied during the correction.",
    )


class DynamicFocusMode(BaseSettings):
    type: Literal["dynamic_focus"] = "dynamic_focus"


PostMillingCorrectionMode = Annotated[
    ManualMode | DynamicFocusMode, Field(discriminator="type")
]


class PostMillingCorrectionSettings(BaseSettings):
    correction_mode: PostMillingCorrectionMode = Field(
        default_factory=ManualMode,
        description="Mode of post milling correction to use.",
    )
    beam_type: BeamType = Field(
        default=BeamType.ELECTRON,
        description="Beam to which correction is applied.",
    )
    execution_frequency: Annotated[int, Field(gt=0)] | None = Field(
        default=1,
        description="Run the action every N-th slice. If not specified, the action will never run.",
    )
    properties_file: Path = Field(
        default=Path("post_milling_corr_props.yaml"),
        description="Path to a file storing properties of the microscope used for post milling correction.",
    )
    properties_to_collect: PropertyNames = Field(
        default_factory=PropertyNames,
        description="Properties of the microscope and the beams relevant for this action.",
    )
    external_props: GlobalProperties = Field(
        default=GlobalProperties(),
        description="External properties of the microscope to use for post milling correction. These properties will overwrite any current microscope properties.",
    )
