# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from pathlib import Path
from typing import Annotated

from pydantic import Field

from fibsem_maestro.core.area import RelativeArea
from fibsem_maestro.core.beam_type import BeamType
from fibsem_maestro.settings.base_settings import BaseSettings
from fibsem_maestro.settings.property_names import PropertyNames


class TemplateMatchingSettings(BaseSettings):
    properties_file: Annotated[
        Path,
        Field(
            description="Path to a file storing properties of the microscope used for drift correction imaging."
        ),
    ]
    templates_directory: Annotated[
        Path,
        Field(
            default=Path(
                "template_matching",
                description="Path to a directory where templates will be saved.",
            )
        ),
    ]
    properties_to_collect: Annotated[
        PropertyNames,
        Field(
            default_factory=PropertyNames,
            description="Properties of the microscope and the beam relevant for drift correction.",
        ),
    ]
    beam_type: Annotated[
        BeamType,
        Field(
            default=BeamType.ELECTRON,
            description="Beam used for drift correction imaging.",
        ),
    ]
    areas: Annotated[
        list[RelativeArea],
        Field(
            min_length=1,
            description="Areas of the image used for template matching defined in relative units.",
        ),
    ]
    min_confidence: Annotated[
        float,
        Field(
            description="Minimal cross-correlation value required for a template match to be accepted as a valid drift measurement."
        ),
    ]
    rescan: Annotated[
        int,
        Field(default=50, description="Number of slices between template refreshing."),
    ]
    blur: Annotated[
        int,
        Field(
            default=0,
            description="Standard deviation (in pixels) of a Gaussian filter applied to the image before template matching.",
        ),
    ]
    correction_margin: Annotated[
        float,
        Field(
            description="The maximum expected drift in nanometers defining how far the template is allowed to search for a match."
        ),
    ]
    stop_acquisition_at_failure: Annotated[
        bool,
        Field(
            default=False,
            description="Should image acquisition be stopped if drift correction fails?",
        ),
    ]
