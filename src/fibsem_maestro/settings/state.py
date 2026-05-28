# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from pydantic import Field

from fibsem_maestro.core.base_settings import BaseSettings
from fibsem_maestro.core.property_names import PropertyNames


class StateSettings(BaseSettings):
    props_file: str = Field(
        description="Name of the file where the microscope properties are stored."
    )
    properties_to_collect: PropertyNames = Field(
        default_factory=PropertyNames,
        description="Names of the properties to collect from the microscope.",
    )


class StateControlSettings(BaseSettings):
    state: str = Field(description="Name of the state to control.")
