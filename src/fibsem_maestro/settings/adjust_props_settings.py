# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from typing import Annotated

from pydantic import Field

from fibsem_maestro.properties.global_properties import GlobalProperties
from fibsem_maestro.settings.base_settings import BaseSettings
from fibsem_maestro.settings.property_names import PropertyNames


class AdjustPropsSettings(BaseSettings):
    properties_to_adjust: GlobalProperties = Field(
        default_factory=GlobalProperties,
        description="Properties of the microscope and the beams which should be adjusted and values to adjust them by.",
    )
    execution_frequency: Annotated[int, Field(gt=0)] | None = Field(
        default=1,
        description="The action runs every N-th slice. If None, the action will never run.",
    )
    properties_to_collect: PropertyNames = Field(
        default_factory=PropertyNames,
        description="Properties of the microscope and the beams relevant for this action.",
    )
