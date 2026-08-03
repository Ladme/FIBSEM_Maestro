# Released under MIT License.
# Copyright (c) 2024-2026 CEMCOF

from unittest.mock import MagicMock

import numpy as np
import pytest

from fibsem_maestro.core.detail_band import DetailBand
from fibsem_maestro.core.image import Image
from fibsem_maestro.criterion.functions import (
    bandpass_criterion,
    bandpass_var_criterion,
    fft_1d_criterion,
    fft_2d_criterion,
    fft_criterion,
)
from fibsem_maestro.logging.text.memory import MemoryTextLogger


def test_bandpass_criterion_flat_image_returns_zero():
    # both Gaussian filters return the same constant on a flat image so their difference is zero
    img = Image(np.full((64, 64), 100, dtype=np.int32), pixel_size=1.0)
    settings = MagicMock()
    settings.detail = DetailBand(low=10.0, high=100.0)

    result = bandpass_criterion(img, settings, MemoryTextLogger())

    assert np.isclose(result, 0.0, atol=1e-6)


def test_bandpass_criterion_structured_image_returns_positive():
    # random spatial structure contains energy at many scales - the band-pass difference must be positive
    rng = np.random.default_rng(42)
    img = Image(rng.integers(0, 255, (64, 64), dtype=np.int32), pixel_size=1.0)
    settings = MagicMock()
    settings.detail = DetailBand(low=2.0, high=20.0)

    result = bandpass_criterion(img, settings, MemoryTextLogger())

    assert result > 0.0


def test_bandpass_var_criterion_flat_image_returns_zero():
    # variance of a zero array is zero
    img = Image(np.full((64, 64), 128, dtype=np.int32), pixel_size=1.0)
    settings = MagicMock()
    settings.detail = DetailBand(low=10.0, high=100.0)

    result = bandpass_var_criterion(img, settings, MemoryTextLogger())

    assert np.isclose(result, 0.0, atol=1e-6)


def test_bandpass_var_criterion_structured_image_returns_positive():
    rng = np.random.default_rng(42)
    img = Image(rng.integers(0, 255, (64, 64), dtype=np.int32), pixel_size=1.0)
    settings = MagicMock()
    settings.detail = DetailBand(low=2.0, high=20.0)

    result = bandpass_var_criterion(img, settings, MemoryTextLogger())

    assert result > 0.0


def test_fft_1d_criterion_sine_inside_band_scores_higher_than_outside():
    # pixel_size = 1 nm, N = 256
    # band: low = 16, high = 64 -> freqs 0.015625, 0.0625
    # in-band: period = 32 nm -> freq = 0.03125 (inside)
    # out-of-band: period = 4 nm -> freq=0.25 (outside)
    pixel_size = 1.0
    pixel_size = 1.0
    N = 256
    x = np.arange(N) * pixel_size

    arr_in = (np.sin(2 * np.pi * x / 32.0) * 1000).astype(np.int32)
    img_in = Image(arr_in, pixel_size=pixel_size)

    arr_out = (np.sin(2 * np.pi * x / 4.0) * 1000).astype(np.int32)
    img_out = Image(arr_out, pixel_size=pixel_size)

    settings = MagicMock()
    settings.detail = DetailBand(low=16.0, high=64.0)
    logger = MemoryTextLogger()

    result_in = fft_1d_criterion(img_in, settings, logger)
    result_out = fft_1d_criterion(img_out, settings, logger)

    assert result_in > result_out


def test_fft_2d_criterion_sine_inside_band_scores_higher_than_outside():
    # pixel_size = 1 nm, 64×64
    # band: low = 8, high = 32 -> freqs 0.03125, 0.125
    # in-band: period = 16 nm -> freq = 0.0625 (inside)
    # out-of-band: period = 2 nm → freq = 0.5 (outside)
    pixel_size = 1.0
    N = 64
    x = np.arange(N) * pixel_size
    ones = np.ones((N, 1))

    arr_in = (np.sin(2 * np.pi * x / 16.0)[np.newaxis, :] * ones * 1000).astype(
        np.int32
    )
    img_in = Image(arr_in, pixel_size=pixel_size)

    arr_out = (np.sin(2 * np.pi * x / 2.0)[np.newaxis, :] * ones * 1000).astype(
        np.int32
    )
    img_out = Image(arr_out, pixel_size=pixel_size)

    settings = MagicMock()
    settings.detail = DetailBand(low=8.0, high=32.0)
    logger = MemoryTextLogger()

    result_in = fft_2d_criterion(img_in, settings, logger)
    result_out = fft_2d_criterion(img_out, settings, logger)

    assert result_in > result_out


def test_fft_criterion_dispatches_to_1d_for_1d_input():
    pixel_size = 1.0
    x = np.arange(256) * pixel_size
    img = Image(
        (np.sin(2 * np.pi * x / 32.0) * 1000).astype(np.int32), pixel_size=pixel_size
    )
    settings = MagicMock()
    settings.detail = DetailBand(low=16.0, high=64.0)
    logger = MemoryTextLogger()

    assert fft_criterion(img, settings, logger) == fft_1d_criterion(
        img, settings, logger
    )


def test_fft_criterion_dispatches_to_2d_for_2d_input():
    pixel_size = 1.0
    N = 64
    x = np.arange(N) * pixel_size
    arr = (np.sin(2 * np.pi * x / 16.0)[np.newaxis, :] * np.ones((N, 1)) * 1000).astype(
        np.int32
    )
    img = Image(arr, pixel_size=pixel_size)
    settings = MagicMock()
    settings.detail = DetailBand(low=8.0, high=32.0)
    logger = MemoryTextLogger()

    assert fft_criterion(img, settings, logger) == fft_2d_criterion(
        img, settings, logger
    )


def test_fft_criterion_raises_not_implemented_for_3d_input():
    img = Image(np.ones((4, 4, 4), dtype=np.int32), pixel_size=1.0)
    settings = MagicMock()
    settings.detail = DetailBand(low=8.0, high=32.0)

    with pytest.raises(NotImplementedError):
        fft_criterion(img, settings, MemoryTextLogger())
