# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from typing import Annotated, Literal

from pydantic import Field

from fibsem_maestro.core.base_settings import BaseSettings
from fibsem_maestro.core.beam_type import BeamType
from fibsem_maestro.settings.template_matching import TemplateMatchingSettings


class TemplateMatchingDriftCorrection(TemplateMatchingSettings):
    type: Literal["template_matching"] = "template_matching"


DriftCorrectionMode = Annotated[
    TemplateMatchingDriftCorrection, Field(discriminator="type")
]


class DriftCorrectionSettings(BaseSettings):
    drift_calculation_mode: DriftCorrectionMode = Field(
        description="Drift correction mode."
    )
    beam_type: BeamType = Field(
        default=BeamType.ELECTRON,
        description="Beam used for drift correction imaging.",
    )
    stop_at_failure: bool = Field(
        default=True,
        description="If `True` and drift correction fails, the execution is stopped. If `False`, warning is printed but execution continues.",
    )
    execution_frequency: Annotated[int, Field(gt=0)] | None = Field(
        default=1,
        description="Drift correction runs every N-th slice. If None, drift correction will never run.",
    )
