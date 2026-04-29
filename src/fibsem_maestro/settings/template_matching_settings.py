# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from enum import Enum
from pathlib import Path
from typing import Annotated

from pydantic import Field

from fibsem_maestro.core.area import RelativeArea
from fibsem_maestro.settings.base_settings import BaseSettings


class TemplateMatchingMode(str, Enum):
    STANDARD = "standard"
    SUBPIXEL = "subpixel"


class TemplateMatchingSettings(BaseSettings):
    templates_directory: Path = Field(
        default=Path("templates"),
        description="Path to a directory where templates will be saved.",
    )
    matching_mode: TemplateMatchingMode = Field(
        default=TemplateMatchingMode.STANDARD,
        description="Template matching mode.",
    )
    template_scans: Annotated[int, Field(gt=0)] = Field(
        default=1, description="The number of scans to perform for each template."
    )
    areas: list[RelativeArea] = Field(
        default_factory=list,
        description="Areas of the image used for template matching defined in relative units.",
    )
    min_confidence: float | None = Field(
        default=None,
        description="Minimal cross-correlation value required for a template match to be accepted as a valid drift measurement.",
    )
    maximal_drift: float | None = Field(
        default=None,
        description="Maximal accepted drift obtained from template matching (in nm).",
    )
    update_frequency: int | None = Field(
        default=None,
        description="Templates are updated every Nth slice. None disables this condition.",
    )
    update_confidence_limit: float | None = Field(
        default=None,
        description="Templates are updated if the match confidence is below this limit. None disables this condition.",
    )
    blur: int = Field(
        default=3,
        description="Standard deviation (in pixels) of a Gaussian filter applied to the image before template matching.",
    )
    correction_margin: float = Field(
        default=20000,
        description="The maximum expected drift in nanometers defining how far the template is allowed to search for a match.",
    )
