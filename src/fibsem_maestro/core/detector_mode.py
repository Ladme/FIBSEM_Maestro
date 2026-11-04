# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF

from enum import StrEnum


class DetectorMode(StrEnum):
    """
    Signal a detector records, e.g. secondary or backscattered electrons.
    """

    NONE = "None"
    DEFAULT = "Default"
    SECONDARY_ELECTRONS = "SecondaryElectrons"
    SECONDARY_IONS = "SecondaryIons"
    BACKSCATTER_ELECTRONS = "BackscatterElectrons"
    CHARGE_NEUTRALIZATION = "ChargeNeutralization"
    DOWN_HOLE_VISIBILITY = "DownHoleVisibility"
    CUSTOM = "Custom"
    SEGMENT_A = "SegmentA"
    SEGMENT_B = "SegmentB"
    Z_CONTRAST = "ZContrast"
    TOPOGRAPHY = "Topography"
    CATHODO_LUMINESCENCE = "CathodoLuminescence"
