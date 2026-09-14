# Released under MIT License.
# Copyright (c) 2024-2026 CEMCOF


from enum import StrEnum


class Provenance(StrEnum):
    """
    Which software's conventions apply to a value, file, or coordinate.
    """

    MAESTRO = "maestro"
    """Produced by, or to be interpreted under, this application."""

    AUTOSCRIPT = "autoscript"
    """Produced by, or to be interpreted under, Thermo Fisher Autoscript."""
