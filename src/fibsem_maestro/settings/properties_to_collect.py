# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from pydantic import Field

from fibsem_maestro.settings.base_settings import BaseSettings


class MicroscopePropertiesToCollect(BaseSettings):
    microscope: list[str] = Field(default_factory=list)
    electron_beam: list[str] = Field(default_factory=list)
    ion_beam: list[str] = Field(default_factory=list)
