# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from pydantic import Field

from fibsem_maestro.core.base_settings import BaseSettings
from fibsem_maestro.core.stage_position import StagePosition


class MicroscopeProperties(BaseSettings):
    model_config = {"extra": "allow"}

    stage_position: StagePosition | None = Field(
        default=None,
        description="Position and orientation of the microscope stage (in nanometers and degrees).",
    )

    def get_property_names(self) -> list[str]:
        """
        Return a list of all property names that are not None.

        Returns:
            list[str]: List of property names.
        """
        return [
            name for name in type(self).model_fields if getattr(self, name) is not None
        ]
