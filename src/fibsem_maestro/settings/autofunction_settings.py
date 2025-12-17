# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from fibsem_maestro.settings.base_settings import BaseSettings
from fibsem_maestro.settings.sweeping_settings import SweepingSettings


class AutofunctionSettings(BaseSettings):
    autofunction_type: str  # ENUM
    delta_x: float
    execute_resolution: float
    execute_slices: float
    criterion_name: str
    sweeping: SweepingSettings
