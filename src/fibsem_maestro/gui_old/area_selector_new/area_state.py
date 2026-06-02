# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from enum import Enum


class AreaState(Enum):
    FINALIZED = "finalized"
    ACTIVE = "active"
    OBSOLETE = "obsolete"
