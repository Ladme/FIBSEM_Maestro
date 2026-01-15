# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from dataclasses import dataclass
from typing import Self

from autoscript_sdb_microscope_client.structures import Point as PointAs


@dataclass
class Stigmator:
    x: float
    y: float

    @classmethod
    def from_point_autoscript(cls, point_autoscript: PointAs) -> Self:
        return cls(x=point_autoscript.x * 1e9, y=point_autoscript.y * 1e9)

    def to_point_autoscript(self) -> PointAs:
        return PointAs(x=self.x * 1e-9, y=self.y * 1e-9)
