# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from dataclasses import dataclass


@dataclass
class AutofocusResult:
    resolution: float
    sweep_value: float
    sweep_index: int
