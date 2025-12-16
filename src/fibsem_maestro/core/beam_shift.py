# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from dataclasses import dataclass


@dataclass
class BeamShift:
    # units are in nanometers
    x: float
    y: float
