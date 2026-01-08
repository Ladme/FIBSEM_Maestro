# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from dataclasses import dataclass


@dataclass(frozen=True)
class SweepStep:
    repetition: int
    value: float
    index: int
