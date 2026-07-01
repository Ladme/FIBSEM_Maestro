# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from dataclasses import dataclass
from typing import Annotated

from fibsem_maestro.settings.form_utils import FieldUnit


@dataclass
class Resolution:
    """
    Resolution of an image in pixels.
    """

    width: Annotated[int, FieldUnit(suffix="px")]
    height: Annotated[int, FieldUnit(suffix="px")]

    def __str__(self) -> str:
        return f"{self.width}x{self.height}"

    def to_tuple(self) -> tuple[int, int]:
        return (self.width, self.height)
