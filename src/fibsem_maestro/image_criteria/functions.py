# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


import numpy as np
from numpy.typing import NDArray
from scipy.ndimage import gaussian_filter  # type: ignore

from fibsem_maestro.core.image import Image
from fibsem_maestro.frc.frc import frc  # type: ignore
from fibsem_maestro.image_criteria.criterion_registry import CriterionRegistry
from fibsem_maestro.settings.criterion_settings import CriterionSettings


@CriterionRegistry.register("bandpass")
def bandpass_criterion(img: Image, settings: CriterionSettings) -> np.floating:
    """
    Compute the mean absolute response of a band-pass filtered image.

    Args:
        img (Image): Input image.
        settings (CriterionSettings): Criterion configuration.

    Returns:
        np.floating: Mean of the absolute band-passed image.
    """
    img_low = gauss_filter(img, img.pixel_size, settings.detail[0])
    img_high = gauss_filter(img, img.pixel_size, settings.detail[1])

    return np.mean(abs(img_high - img_low))


@CriterionRegistry.register("bandpass_var")
def bandpass_var_criterion(img: Image, settings: CriterionSettings) -> np.floating:
    """
    Compute the variance of the band-pass filtered image.

    Args:
        img (Image): Input image.
        settings (CriterionSettings): Criterion configuration.

    Returns:
        np.floating: Variance of the band-passed image.
    """
    img_low = gauss_filter(img, img.pixel_size, settings.detail[0])
    img_high = gauss_filter(img, img.pixel_size, settings.detail[1])

    return np.var(img_high - img_low)


@CriterionRegistry.register("fft_1d")
def fft_1d_criterion(img: Image, settings: CriterionSettings) -> np.floating:
    """
    Compute the 1D FFT amplitude sum within a frequency band.

    Args:
        img (Image): 1D image or signal vector.
        settings (CriterionSettings): Criterion configuration.

    Returns:
        np.floating: Sum of FFT amplitudes in the allowed frequency band.

    Raises:
        ValueError: If the input image is not 1-dimensional.
    """
    # remove 0 frequency
    img0 = img - np.mean(img)
    # fft
    fft_line = np.fft.fft(img0)

    # get freq axis
    freq = np.fft.fftfreq(len(img), img.pixel_size)  # type: ignore
    # remove negative frequencies
    fft_line = fft_line[freq > 0]
    # remove negative frequencies from freq axis
    freq = freq[freq > 0]  # type: ignore

    # filter frequencies
    band_i = np.where(
        (freq < 1 / settings.detail[1]) & (freq > 1 / settings.detail[0])  # type: ignore
    )[0]

    # sum of amplitudes of all filtered frequencies
    return np.sum(abs(fft_line[band_i]))


@CriterionRegistry.register("fft_2d")
def fft_2d_criterion(img: Image, settings: CriterionSettings) -> np.floating:
    """
    Compute the 2D FFT amplitude sum within a radial frequency band.

    Args:
        img (Image): 2D image.
        settings (CriterionSettings): Criterion configuration.

    Returns:
        np.floating: Sum of FFT amplitudes in the radial frequency band.

    Raises:
        ValueError: If the input image is not 2-dimensional.
    """
    # remove 0 frequency
    img0 = img - np.mean(img)
    # fft
    fft_img = np.fft.fft2(img0)

    # get x freq axis
    freq1 = np.fft.fftfreq(fft_img.shape[0], img.pixel_size)  # type: ignore
    # get y freq axis
    freq2 = np.fft.fftfreq(fft_img.shape[1], img.pixel_size)  # type: ignore

    freq1 = np.repeat(freq1[:, np.newaxis], freq2.shape[0], axis=1)  # type: ignore
    freq2 = np.repeat(freq2[:, np.newaxis], freq1.shape[0], axis=1).T  # type: ignore
    # make freq matrix
    freq = np.sqrt(freq1**2 + freq2**2)  # type: ignore

    # highest detail frequency
    high_frequency = 1 / settings.detail[1]
    # lowest detail frequency
    low_frequency = 1 / settings.detail[0]

    # make freq filter
    freq[freq > high_frequency] = 0
    freq[freq < low_frequency] = 0
    freq[freq > 0] = 1

    fft_img *= freq  # filter freq
    return np.sum(abs(fft_img))


@CriterionRegistry.register("fft")
def fft_criterion(img: Image, settings: CriterionSettings) -> np.floating:
    """
    FFT-based criterion for both 1D and 2D images.

    This function is a unified wrapper that dispatches to either
    `fft_1d_criterion` or `fft_2d_criterion` depending on the dimensionality
    of the input image.

    Args:
        img (Image): Input image (1D or 2D).
        settings (CriterionSettings): Criterion configuration.

    Returns:
        np.floating: FFT-based criterion value.

    Raises:
        NotImplementedError: If the input dimensionality is not 1 or 2.
    """
    if np.ndim(img) == 1:
        return fft_1d_criterion(img, settings)
    if np.ndim(img) == 2:
        return fft_2d_criterion(img, settings)

    raise NotImplementedError(
        "Only 1D and 2D images are currently supported for focus criterion."
    )


@CriterionRegistry.register("frc")
def frc_criterion(img: Image, settings: CriterionSettings) -> np.floating:
    """
    Compute the focal quality based on Fourier Ring Correlation (FRC).

    Args:
        img (Image): Input image.
        settings (CriterionSettings): Criterion configuration (unused).

    Returns:
        np.floating: FRC score, or `np.nan` if FRC computation fails.
    """
    _ = settings

    try:
        res = frc(img, img.pixel_size)  # type: ignore
    except Exception as e:
        logging.warning("FRC error on current tile. " + repr(e))
        return np.nan
    return res  # type: ignore


def gauss_filter(x: Image, px_size: int, detail: float) -> NDArray[np.floating]:
    """
    Apply a Gaussian filter to an image.

    Args:
        x (Image): The input image array.
        px_size (int): Pixel size in spatial units.
        detail (float): Detail parameter controlling filter width.

    Returns:
        NDArray[np.float32]: The Gaussian-filtered image.
    """
    px = detail / px_size
    sigma = 1 / (2 * np.pi * (1 / px))
    return gaussian_filter(x.astype(np.float32), sigma, mode="nearest", truncate=6)  # type: ignore
