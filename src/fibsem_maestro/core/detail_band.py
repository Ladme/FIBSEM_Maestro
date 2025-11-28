# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from dataclasses import dataclass


@dataclass(frozen=True)
class DetailBand:
    """
    Spatial detail band used by resolution criteria.

    Attributes:
        low (float):
            Lower spatial scale of the passband, in meters.
        high (float):
            Upper spatial scale of the passband, in meters.
    """

    # low-detail cutoff, in meters
    low: float
    # high-detail cutoff, in meters
    high: float

    def to_frequency_range(self) -> tuple[float, float]:
        """Return the equivalent frequency range (Hz = 1/m)."""
        return (1.0 / self.low, 1.0 / self.high)

    def __post_init__(self):
        if self.low <= 0 or self.high <= 0:
            raise ValueError("Detail scales must be positive.")
        if self.low >= self.high:
            raise ValueError("DetailBand.low must be < DetailBand.high.")
