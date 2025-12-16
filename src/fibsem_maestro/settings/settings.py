# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from fibsem_maestro.settings.microscope_settings import MicroscopeSettings
from fibsem_maestro.settings.reactive import ReactiveDict

from .base_settings import BaseSettings


class AcquisitionSettings(BaseSettings):
    criterion_name: str
    extended_resolution: bool
    image_name: str
    imaging_enabled: bool
    resolution_threshold: int
    sputter: bool
    sputter_grid: int
    wd_correction: float
    y_correction: int


class AutofunctionSettings(BaseSettings):
    test: int


class Settings(BaseSettings):
    microscope: MicroscopeSettings
    acquisition: AcquisitionSettings
    simple: int
    autofunctions: ReactiveDict[str, AutofunctionSettings]
