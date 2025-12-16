# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from dataclasses import dataclass


@dataclass
class SourceTilt:
    # units are in degrees
    x: float
    y: float
