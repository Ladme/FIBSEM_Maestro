# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from pathlib import Path
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
        description="Drift correction mode."
    )
    properties_file: Path = Field(
        default=Path("drift_corr_props.yaml"),
        description="Path to a file storing properties of the microscope used for drift correction imaging.",
    )
    properties_to_collect: PropertyNames = Field(
        default_factory=PropertyNames,
        description="Properties of the microscope and the beam relevant for drift correction.",
    )
    beam_type: BeamType = Field(
        default=BeamType.ELECTRON,
        description="Beam used for drift correction imaging.",
    )
    stop_at_failure: bool = Field(
        default=True,
        description="If `True` and drift correction fails, the execution is stopped. If `False`, warning is printed but execution continues.",
    )
    external_props: GlobalProperties = Field(
        default=GlobalProperties(),
        description="External properties of the microscope to use for drift correction. These properties will overwrite any current microscope properties.",
    )
