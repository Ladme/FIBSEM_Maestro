# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from fibsem_maestro.core.scanning_area import ScanningArea
from fibsem_maestro.settings.base_settings import BaseSettings


class ImagingSettings(BaseSettings):
    resolution: tuple[int, int] | None = None
    bit_depth: int | None = None
    dwell_time: float | None = None
    line_integration: int | None = None
    scanning_area: ScanningArea | None = None
    pixel_size: float | None = None
    field_of_view: tuple[float, float] | None = None
    detector_contrast: float | None = None
    detector_brightness: float | None = None
