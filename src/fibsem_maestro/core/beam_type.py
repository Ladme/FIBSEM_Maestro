# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from enum import Enum


class BeamType(str, Enum):
    ELECTRON = "electron"
    ION = "ion"

    def __int__(self) -> int:
        match self:
            case BeamType.ELECTRON:
                return 1
            case BeamType.ION:
                return 2

    def __str__(self) -> str:
        return self.value
