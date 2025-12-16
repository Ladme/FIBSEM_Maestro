# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from dataclasses import dataclass


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
    low: float
    # high-detail cutoff, in nanometers
    high: float

    def to_meters(self) -> tuple[float, float]:
        """Return the DetailBand in meters."""
        return (self.low * 1e-9, self.high * 1e-9)

    def to_frequency_range(self) -> tuple[float, float]:
        """Return the equivalent frequency range (Hz = 1/m)."""
        band_m = self.to_meters()
        return (1.0 / band_m[0], 1.0 / band_m[1])

    def __post_init__(self):
        if self.low <= 0 or self.high <= 0:
            raise ValueError("Detail scales must be positive.")
        if self.low >= self.high:
            raise ValueError("DetailBand.low must be < DetailBand.high.")
