# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from enum import Enum


class BeamType(str, Enum):
    ION = "ion"
    ELECTRON = "electron"
