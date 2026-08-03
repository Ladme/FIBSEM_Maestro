# Released under MIT License.
# Copyright (c) 2024-2026 CEMCOF


from typing import Annotated

from pydantic import Field
from pydantic.dataclasses import dataclass

from fibsem_maestro.settings.form_utils import FieldUnit


@dataclass(frozen=True)
class DetailBand:
    """
    Spatial detail band used by resolution criteria.

    Attributes:
        low (float):
            Lower spatial scale of the passband, in nanometers.
        high (float):
            Upper spatial scale of the passband, in nanometers.
    """

    # low-detail cutoff, in nanometers
    low: Annotated[float, FieldUnit(suffix="nm"), Field(gt=0.0)]
    # high-detail cutoff, in nanometers
    high: Annotated[float, FieldUnit(suffix="nm"), Field(gt=0.0)]

    def to_frequency_range(self) -> tuple[float, float]:
        """Return the equivalent spatial frequency range in 1/nm."""
        return (1.0 / self.high, 1.0 / self.low)

    def __post_init__(self):
        if self.low > self.high:
            raise ValueError("DetailBand.low cannot be greater than DetailBand.high.")
