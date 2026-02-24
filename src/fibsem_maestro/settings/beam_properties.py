# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from typing import Annotated

from pydantic import Field

from fibsem_maestro.core.area import RelativeArea
from fibsem_maestro.core.beam_shift import BeamShift
from fibsem_maestro.core.lens_alignment import LensAlignment
from fibsem_maestro.core.resolution import Resolution
from fibsem_maestro.core.source_tilt import SourceTilt
from fibsem_maestro.core.stigmator import Stigmator
from fibsem_maestro.settings.base_settings import BaseSettings


class BeamProperties(BaseSettings):
    model_config = {"extra": "allow"}

    stigmator: Annotated[
        Stigmator | None,
        Field(
            default=None,
            description="Stigmator settings for beam correction (in nanometers).",
        ),
    ]
    lens_alignment: Annotated[
        LensAlignment | None,
        Field(
            default=None,
            description="Alignment of lens in the microscope (in nanometers).",
        ),
    ]
    beam_shift: Annotated[
        BeamShift | None,
        Field(default=None, description="Beam shift settings (in nanometers)."),
    ]
    detector_contrast: Annotated[
        float | None, Field(default=None, description="Contrast level of the detector.")
    ]
    detector_brightness: Annotated[
        float | None,
        Field(default=None, description="Brightness level of the detector."),
    ]
    source_tilt: Annotated[
        SourceTilt | None,
        Field(
            default=None,
            description="Tilt settings for the electron source (in degrees).",
        ),
    ]
    line_integration: Annotated[
        int | None,
        Field(default=None, gt=0, description="Number of line integrations per scan."),
    ]
    dwell_time: Annotated[
        float | None,
        Field(default=None, gt=0, description="Dwell time per pixel in seconds."),
    ]
    bit_depth: Annotated[
        int | None,
        Field(default=None, gt=0, description="Bit depth of the detector output."),
    ]
    resolution: Annotated[
        Resolution | None,
        Field(default=None, description="Resolution of the scan in pixels."),
    ]
    horizontal_field_width: Annotated[
        float | None,
        Field(
            default=None, gt=0, description="Horizontal field of view in nanometers."
        ),
    ]
    vertical_field_width: Annotated[
        float | None,
        Field(default=None, gt=0, description="Vertical field of view in nanometers."),
    ]
    pixel_size: Annotated[
        float | None,
        Field(
            default=None, gt=0, description="Physical size of a pixel in nanometers."
        ),
    ]
    scanning_area: Annotated[
        RelativeArea | None,
        Field(default=None, description="Area to be scanned."),
    ]
    working_distance: Annotated[
        float | None,
        Field(
            default=None,
            gt=0,
            description="Working distance between sample and objective lens in nanometers.",
        ),
    ]
