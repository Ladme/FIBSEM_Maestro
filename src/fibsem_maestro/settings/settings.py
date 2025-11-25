# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

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


class MicroscopeSettings(BaseSettings):
    beam_shift_tolerance: float
    ip_address: str
    relative_beam_shift_to_stage: list[int]
    stage_tolerance: float
    stage_trials: int


class AutofunctionSettings(BaseSettings):
    test: int


class CriterionSettings(BaseSettings):
    detail: list[float]


class Settings(BaseSettings):
    acquisition: AcquisitionSettings
    microscope: MicroscopeSettings
    simple: int
    autofunctions: dict[str, list[AutofunctionSettings]]


class SettingsComments(BaseSettings):
    pass
