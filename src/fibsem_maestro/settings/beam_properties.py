# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from typing import Any

from fibsem_maestro.core.beam_shift import BeamShift
from fibsem_maestro.core.lens_alignment import LensAlignment
from fibsem_maestro.core.scanning_area import ScanningArea
from fibsem_maestro.core.source_tilt import SourceTilt
from fibsem_maestro.core.stigmator import Stigmator
from fibsem_maestro.settings.base_settings import BaseSettings


class BeamProperties(BaseSettings):
    stigmator: Stigmator
    lens_alignment: LensAlignment
    beam_shift: BeamShift
    detector_contrast: float
    detector_brightness: float
    source_tilt: SourceTilt
    line_integration: int
    dwell_time: float
    bit_depth: int
    resolution: tuple[int, int]
    horizontal_field_width: float
    vertical_field_width: float
    pixel_size: float
    scanning_area: ScanningArea
    custom: dict[str, Any]
    working_distance: float  # must be last!
