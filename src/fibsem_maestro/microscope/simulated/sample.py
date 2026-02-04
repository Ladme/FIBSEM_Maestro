# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

import math
from typing import Any

import numpy as np
from numpy.typing import NDArray
from scipy.ndimage import gaussian_filter1d  # type: ignore


class SimulatedSample:
    def __init__(self, rng: np.random.Generator):
        self.pixel_size = 10.0
        self.data = self._generate_perlin_noise(rng, 2000, 2000, scale=100.0, octaves=8)

    def sample(
        self,
        X: NDArray[np.floating],
        Y: NDArray[np.floating],
    ) -> NDArray[np.floating]:
        """
        Sample the surface at world coordinates (nm).
        Coordinates outside the sample are clipped.
        """

        px = (X / self.pixel_size).astype(np.int64)
        py = (Y / self.pixel_size).astype(np.int64)

        px = np.clip(px, 0, self.data.shape[1] - 1)
        py = np.clip(py, 0, self.data.shape[0] - 1)

        return self.data[py, px]

    @staticmethod
    def world_grid(
        center_x_nm: float,
        center_y_nm: float,
        width_px: int,
        height_px: int,
        fov_x_nm: float,
        fov_y_nm: float,
    ) -> tuple[NDArray[np.floating], NDArray[np.floating]]:
        """
        Create a world-coordinate sampling grid for an SEM scan.

        Returns X, Y arrays of shape (height_px, width_px) giving
        the world-space position (in nm) of each pixel.

        The grid is centered at (center_x_nm, center_y_nm).
        """

        xs = np.linspace(
            center_x_nm - fov_x_nm / 2.0,
            center_x_nm + fov_x_nm / 2.0,
            width_px,
            endpoint=False,
        )

        ys = np.linspace(
            center_y_nm - fov_y_nm / 2.0,
            center_y_nm + fov_y_nm / 2.0,
            height_px,
            endpoint=False,
        )

        X, Y = np.meshgrid(xs, ys, indexing="xy")
        return X, Y

    @staticmethod
    def rotate_grid(
        X: NDArray[np.floating],
        Y: NDArray[np.floating],
        cx: float,
        cy: float,
        theta: float,
    ) -> tuple[NDArray[np.floating], NDArray[np.floating]]:
        """
        Rotate world-coordinate grid around (cx, cy) by theta (in degrees).
        """

        dx = X - cx
        dy = Y - cy

        cos_t = np.cos(math.radians(theta))
        sin_t = np.sin(math.radians(theta))

        Xr = cos_t * dx - sin_t * dy + cx
        Yr = sin_t * dx + cos_t * dy + cy

        return Xr, Yr

    @staticmethod
    def apply_focus_and_astigmatism(
        image: NDArray[np.floating],
        Y: NDArray[np.floating],
        center_y: float,
        defocus: float,
        tilt_rad: float,
        pixel_size: float,
        stigmator_x: float,
        stigmator_y: float,
    ) -> NDArray[np.floating]:
        """
        Apply focus blur with tilt-induced defocus gradient and astigmatism.
        """

        height, _ = image.shape
        out = np.empty_like(image)

        base_sigma_nm = 2.0  # probe size
        k = 1e-4  # nm blur per nm defocus

        for row in range(height):
            z_offset = (Y[row, 0] - center_y) * np.sin(tilt_rad)
            local_defocus = defocus + z_offset

            sigma_nm = base_sigma_nm + abs(local_defocus) * k
            sigma_px = sigma_nm / pixel_size

            sig_x = sigma_px * (1.0 + stigmator_x)
            sig_y = sigma_px * (1.0 + stigmator_y)

            # blur horizontally then vertically
            tmp = gaussian_filter1d(
                image[row, :],
                sigma=sig_x,
                mode="nearest",
            )

            out[row, :] = gaussian_filter1d(
                tmp,
                sigma=sig_y,
                mode="nearest",
            )

        return out

    @staticmethod
    def apply_brightness_contrast(
        image: NDArray[np.floating],
        brightness: float,
        contrast: float,
    ) -> NDArray[np.floating]:
        mu = np.mean(image)
        img_contrast = mu + (image - mu) * (2 * contrast)
        img_bright = img_contrast * (2 * brightness)
        return np.clip(img_bright, 0, 1)

    def _generate_perlin_noise(
        self,
        rng: np.random.Generator,
        height: int,
        width: int,
        scale: float = 50.0,
        octaves: int = 4,
        persistence: float = 0.5,
    ) -> NDArray[np.floating[Any]]:
        """
        Generates sharp fractal Perlin noise (FBM).

        Args:
            rng (np.random.Generator): Random number generator.
            height (int): The height of the image.
            width (int): The width of the image.
            scale (float): The scale of the noise, affecting the smoothness and feature size.
            octaves (int): Number of noise layers (higher = sharper).
            persistence (float): Amplitude decay per octave.

        Returns:
            NDArray[np.floating[Any]]: A 2D numpy array representing the Perlin noise image with values between 0 and 1.
        """

        FloatArray = NDArray[np.floating[Any]]

        def fade(t: FloatArray) -> FloatArray:
            return 6 * t**5 - 15 * t**4 + 10 * t**3

        def lerp(a: FloatArray, b: FloatArray, t: FloatArray) -> FloatArray:
            return a + t * (b - a)

        def perlin(scale: float) -> FloatArray:
            grid_y = int(np.ceil(height / scale)) + 1
            grid_x = int(np.ceil(width / scale)) + 1

            angles = rng.uniform(0.0, 2.0 * np.pi, size=(grid_y, grid_x))
            gradients = np.stack((np.cos(angles), np.sin(angles)), axis=-1)

            y, x = np.meshgrid(np.arange(height), np.arange(width), indexing="ij")
            xf = x / scale
            yf = y / scale

            x0 = xf.astype(int)
            y0 = yf.astype(int)
            x1 = x0 + 1
            y1 = y0 + 1

            sx = fade(xf - x0)
            sy = fade(yf - y0)

            def dot(
                ix: NDArray[np.integer[Any]],
                iy: NDArray[np.integer[Any]],
            ) -> NDArray[np.floating[Any]]:
                dx = xf - ix
                dy = yf - iy
                g = gradients[iy, ix]
                return dx * g[..., 0] + dy * g[..., 1]

            n00 = dot(x0, y0)
            n10 = dot(x1, y0)
            n01 = dot(x0, y1)
            n11 = dot(x1, y1)

            return lerp(lerp(n00, n10, sx), lerp(n01, n11, sx), sy)

        noise = np.zeros((height, width), dtype=float)
        amplitude = 1.0
        max_amp = 0.0
        current_scale = scale

        for _ in range(octaves):
            noise += amplitude * perlin(current_scale)
            max_amp += amplitude
            amplitude *= persistence
            current_scale /= 2.0

        noise /= max_amp

        # normalize
        noise -= noise.min()
        noise /= noise.max()

        return noise
