# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from fibsem_maestro.settings.autofunction_settings import AutofunctionSettings
from fibsem_maestro.settings.criterion_settings import CriterionSettings
from fibsem_maestro.settings.imaging_settings import ImagingSettings
from fibsem_maestro.settings.mask_settings import MaskSettings
from fibsem_maestro.settings.microscope_settings import MicroscopeSettings
from fibsem_maestro.settings.notification_settings import NotificationSettings
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


class Settings(BaseSettings):
    microscope: MicroscopeSettings
    acquisition: AcquisitionSettings
    autofunctions: ReactiveDict[str, AutofunctionSettings]
    imaging: ReactiveDict[str, ImagingSettings]
    criteria: ReactiveDict[str, CriterionSettings]
    masks: ReactiveDict[str, MaskSettings]
    notification: NotificationSettings
