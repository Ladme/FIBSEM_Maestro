# Released under MIT License.
# Copyright (c) 2024-2026 CEMCOF

from typing import Annotated, Literal

from pydantic import Field

from fibsem_maestro.core.beam_type import BeamType
from fibsem_maestro.properties.global_properties import GlobalProperties
from fibsem_maestro.settings.base_settings import BaseSettings
from fibsem_maestro.settings.property_names import PropertyNames
from fibsem_maestro.settings.template_matching_settings import TemplateMatchingSettings


class TemplateMatchingDriftCorrection(TemplateMatchingSettings):
    type: Literal["template_matching"] = "template_matching"


DriftCorrectionMode = Annotated[
    TemplateMatchingDriftCorrection, Field(discriminator="type")
]


class DriftCorrectionSettings(BaseSettings):
    drift_calculation_mode: DriftCorrectionMode = Field(
        default_factory=TemplateMatchingDriftCorrection,
        description="Drift correction mode.",
    )
    beam_type: BeamType = Field(
        default=BeamType.ELECTRON,
        description="Beam used for drift correction imaging.",
    )
    execution_frequency: Annotated[int, Field(gt=0)] | None = Field(
        default=1,
        description="Drift correction runs every N-th slice. If not checked, drift correction will never run.",
    )
    stop_at_failure: bool = Field(
        default=True,
        description="If checked and drift correction fails, the execution is stopped. If not checked, warning is printed but execution continues.",
    )
    properties_to_collect: PropertyNames = Field(
        default_factory=PropertyNames,
        description="Properties of the microscope and the beam relevant for drift correction.",
    )
    external_props: GlobalProperties = Field(
        default=GlobalProperties(),
        description="External properties of the microscope to use for drift correction. These properties will overwrite any current microscope properties.",
    )
