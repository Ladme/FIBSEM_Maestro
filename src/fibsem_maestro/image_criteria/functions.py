# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from abc import ABCMeta
from collections.abc import Callable
from enum import Enum
from typing import Any, ClassVar

import numpy as np
from numpy.typing import NDArray
from scipy.ndimage import gaussian_filter  # type: ignore

from fibsem_maestro.core.image import Image
from fibsem_maestro.frc.frc import frc  # type: ignore
from fibsem_maestro.settings.settings import CriterionSettings


class CriterionFunctionVariant(Enum):
    BANDPASS = "bandpass"
    BANDPASS_VARIANCE = "bandpass-var"
    FFT = "fft"
    FRC = "frc"


class CriterionFunctionMeta(ABCMeta):
    _registry: ClassVar[
        dict[
            CriterionFunctionVariant,
            Callable[[Image, CriterionSettings], np.floating[Any]],
        ]
    ]

    def __call__(
        cls, variant: CriterionFunctionVariant
    ) -> Callable[[Image, CriterionSettings], np.floating[Any]]:
        return cls._registry[variant]


class CriterionFunction(metaclass=CriterionFunctionMeta):
    _registry: dict[
        CriterionFunctionVariant,
        Callable[[Image, CriterionSettings], np.floating[Any]],
    ] = {}


def criterion_function(
    variant: CriterionFunctionVariant,
):
    """
    Decorator that registers a criterion function under a given name.
    """

    def decorator(
        func: Callable[[Image, CriterionSettings], np.floating[Any]],
    ) -> Callable[[Image, CriterionSettings], np.floating[Any]]:
        CriterionFunction._registry[variant] = func
        return func

    return decorator


@criterion_function(CriterionFunctionVariant.BANDPASS)
def bandpass_criterion(img: Image, settings: CriterionSettings) -> np.floating[Any]:
    """
    Mean value of band-passed image.
    """
    img_low = gauss_filter(img, img.pixel_size, settings.detail[0])
    img_high = gauss_filter(img, img.pixel_size, settings.detail[1])

    return np.mean(abs(img_high - img_low))  # mean of absolute images


@criterion_function(CriterionFunctionVariant.BANDPASS_VARIANCE)
def bandpass_var_criterion(img: Image, settings: CriterionSettings) -> np.floating[Any]:
    """
    Variance of band-passed image.
    """
    img_low = gauss_filter(img, img.pixel_size, settings.detail[0])
    img_high = gauss_filter(img, img.pixel_size, settings.detail[1])

    return np.var(img_high - img_low)


@criterion_function(CriterionFunctionVariant.FFT)
def fft_criterion(img: Image, settings: CriterionSettings) -> np.floating[Any]:
    """
    :param img: The image data. It can be either a 1-dimensional array representing an image line
    or a 2-dimensional array representing the entire image.

    :return: The sum of the amplitudes of the filtered frequencies.

    This method calculates the FFT (Fast Fourier Transform) of the given image data. It removes frequencies within
    the specified range and returns the sum of the amplitudes of the remaining frequencies.
    """

    def fft_criterion1d() -> np.floating[Any]:
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

    def fft_criterion_2d() -> np.floating[Any]:
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

    if np.ndim(img) == 1:
        return fft_criterion1d()
    if np.ndim(img) == 2:
        return fft_criterion_2d()

    raise NotImplementedError(
        "Only 1D and 2D images are currently supported for focus criterion."
    )


@criterion_function(CriterionFunctionVariant.FRC)
def frc_criterion(img: Image, settings: CriterionSettings) -> np.floating[Any]:
    try:
        res = frc(img, img.pixel_size)  # type: ignore
    except Exception as e:
        logging.warning("FRC error on current tile. " + repr(e))
        return np.nan
    return res  # type: ignore


def gauss_filter(x: Image, px_size: int, detail: float) -> NDArray[np.float64]:
    """
    Applies a Gaussian filter to the input array.
    """
    px = detail / px_size
    sigma = 1 / (2 * np.pi * (1 / px))
    return gaussian_filter(x.astype(np.float32), sigma, mode="nearest", truncate=6)  # type: ignore
