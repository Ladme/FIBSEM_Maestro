# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray


@dataclass(frozen=True)
class SubpixelLog:
    """
    Log data for subpixel template matching.

    Attributes:
        y_raw (NDArray[np.float64]):
            The raw vertical correlation slice centered around the detected peak position.
        y_fit (NDArray[np.float64]):
            The Gaussian fit evaluated over `y_raw`.
        x_raw (NDArray[np.float64]):
            The raw horizontal correlation slice centered around the detected peak position.
        x_fit (NDArray[np.float64]):
            The Gaussian fit evaluated over `x_raw`.
    """

    y_raw: NDArray[np.floating]
    y_fit: NDArray[np.floating]
    x_raw: NDArray[np.floating]
    x_fit: NDArray[np.floating]
