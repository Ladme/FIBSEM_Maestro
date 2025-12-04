# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from dataclasses import dataclass
from typing import Self

from fibsem_maestro.core.point import RelativePoint


@dataclass
class ScanningArea:
    # relative coordinates
    origin: RelativePoint  # top left corner
    width: float
    height: float

    def update(self, other: Self) -> None:
        self.origin = other.origin
        self.width = other.width
        self.height = other.height
