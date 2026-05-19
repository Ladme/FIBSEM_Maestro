# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from enum import Enum


class PatternType(str, Enum):
    CLEANING_CROSS_SECTION_PATTERN = "ccs"
    REGULAR_CROSS_SECTION_PATTERN = "rcs"
