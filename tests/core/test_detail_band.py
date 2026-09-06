# Released under MIT License.
# Copyright (c) 2024-2026 CEMCOF

import numpy as np
import pytest

from fibsem_maestro.core.detail_band import DetailBand


def test_detail_band_stores_low_and_high():
    band = DetailBand(low=10.0, high=100.0)

    assert np.isclose(band.low, 10.0)
    assert np.isclose(band.high, 100.0)


def test_detail_band_raises_when_low_is_zero():
    with pytest.raises(ValueError, match="positive"):
        DetailBand(low=0.0, high=100.0)


def test_detail_band_raises_when_low_is_negative():
    with pytest.raises(ValueError, match="positive"):
        DetailBand(low=-1.0, high=100.0)


def test_detail_band_raises_when_high_is_zero():
    with pytest.raises(ValueError, match="positive"):
        DetailBand(low=10.0, high=0.0)


def test_detail_band_raises_when_low_equals_high():
    with pytest.raises(ValueError, match="low must be"):
        DetailBand(low=10.0, high=10.0)


def test_detail_band_raises_when_low_exceeds_high():
    with pytest.raises(ValueError, match="low must be"):
        DetailBand(low=100.0, high=10.0)


def test_to_frequency_range_returns_correct_values():
    band = DetailBand(low=10.0, high=100.0)

    freq1, freq2 = band.to_frequency_range()

    assert np.isclose(freq1, 0.01)
    assert np.isclose(freq2, 0.1)
