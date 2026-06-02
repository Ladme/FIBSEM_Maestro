# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from enum import Enum


class AreaType(Enum):
    SCANNING = "scanning_area"
    TEMPLATE = "template_area"
    FIDUCIAL = "fiducial"
    MILLING = "milling"
