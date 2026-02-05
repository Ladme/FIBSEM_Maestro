# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from dataclasses import dataclass


@dataclass
class Resolution:
    """
    Resolution of an image in pixels.
    """

    width: int
    height: int

    def __str__(self) -> str:
        return f"{self.width}x{self.height}"

    def to_tuple(self) -> tuple[int, int]:
        return (self.width, self.height)
