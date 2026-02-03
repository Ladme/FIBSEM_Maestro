# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

from fibsem_maestro.core.beam_shift import BeamShift
from fibsem_maestro.core.image import Image
from fibsem_maestro.core.lens_alignment import LensAlignment
from fibsem_maestro.core.scanning_area import RelativeScanningArea
from fibsem_maestro.core.source_tilt import SourceTilt
from fibsem_maestro.core.stigmator import Stigmator
from fibsem_maestro.logging.text.text_logger import TextLogger
from fibsem_maestro.microscope.abstract_control.beam_control import BeamControl
from fibsem_maestro.microscope.error import MicroscopeError


class SimulatedBeamControl(BeamControl):
    """Simulated beam controller."""

    def __init__(self, *, name: str, txt_log: TextLogger, rng: np.random.Generator):
        self._name = name
        self._txt_log = txt_log
        self._rng = rng

        # current state
        self._working_distance_nm = 5_000_000.0  # 5 mm in nm
        self._stigmator = Stigmator(x=0.0, y=0.0)
        self._lens_alignment = LensAlignment(x=0.0, y=0.0)  # nm
        self._beam_shift = BeamShift(x=0.0, y=0.0)  # nm

        self._detector_contrast = 0.5
        self._detector_brightness = 0.5
        self._source_tilt = SourceTilt(x=0.0, y=0.0)  # degrees

        self._blanked = False
        self._acquiring = False

        self._line_integration = 1
        self._dwell_time = 1e-6  # seconds
        self._bit_depth = 8
        self._resolution = (1024, 768)
        self._horizontal_field_width_nm = 200_000.0  # 200 µm in nm
        self._vertical_field_width_nm = 200_000.0
        self._scanning_area: RelativeScanningArea | None = None

        self._beam_shift_to_stage_move = (1.0, 1.0)
        self._image_to_beam_shift = (1.0, 1.0)

        self._manufacturer_properties: dict[str, Any] = {
            "beam.custom_parameter": 0.5,
            "beam.inner.parameter": 1.2,
        }

        self._current_image: Image | None = None

        self._limits: dict[str, tuple[float, float]] = {
            "working_distance": (
                500_000.0,
                70_000_000.0,
            ),
            "stigmator_x": (-0.99, 0.88),
            "stigmator_y": (-0.99, 0.77),
            "lens_alignment_x": (-720_052.0, 697_917.0),
            "lens_alignment_y": (-691_406.0, 689_453.0),
            "beam_shift_x": (-5_000_000.0, 5_000_000.0),
            "beam_shift_y": (-5_000_000.0, 5_000_000.0),
            "detector_contrast": (0.0, 1.0),
            "detector_brightness": (0.0, 1.0),
            "source_tilt_x": (-5.0, 5.0),
            "source_tilt_y": (-5.0, 5.0),
            "horizontal_field_width": (1_000.0, 5_000_000_000.0),
            "vertical_field_width": (1_000.0, 5_000_000_000.0),
            "dwell_time": (50e-9, 10e-6),  # in s
        }

    def limits(self, var: str) -> tuple[float, float]:
        return self._limits.get(var, (-float("inf"), float("inf")))

    @property
    def working_distance(self) -> float:
        value = self._working_distance_nm
        self._txt_log.debug(f"Getting working distance: {value}.")
        return value

    @working_distance.setter
    def working_distance(self, value: float):
        self._txt_log.debug(f"Setting working distance: {value}.")
        self._working_distance_nm = value

    @property
    def stigmator(self) -> Stigmator:
        value = self._stigmator
        self._txt_log.debug(f"Getting stigmator: {value}.")
        return value

    @stigmator.setter
    def stigmator(self, value: Stigmator) -> None:
        self._txt_log.debug(f"Setting stigmator: {value}.")
        self._stigmator = value

    @property
    def lens_alignment(self) -> LensAlignment:
        value = self._lens_alignment
        self._txt_log.debug(f"Getting lens alignment: {value}.")
        return value

    @lens_alignment.setter
    def lens_alignment(self, value: LensAlignment) -> None:
        self._txt_log.debug(f"Setting lens alignment: {value}.")
        self._lens_alignment = value

    @property
    def beam_shift(self) -> BeamShift:
        value = self._beam_shift
        self._txt_log.debug(f"Getting beam shift: {value}.")
        return value

    @beam_shift.setter
    def beam_shift(self, value: BeamShift) -> None:
        self._txt_log.debug(f"Setting beam shift: {value}.")
        self._beam_shift = value

    @property
    def detector_contrast(self) -> float:
        value = self._detector_contrast
        self._txt_log.debug(f"Getting detector contrast: {value}.")
        return value

    @detector_contrast.setter
    def detector_contrast(self, value: float) -> None:
        self._txt_log.debug(f"Setting detector contrast: {value}.")
        self._detector_contrast = value

    @property
    def detector_brightness(self) -> float:
        value = self._detector_brightness
        self._txt_log.debug(f"Getting detector brightness: {value}.")
        return value

    @detector_brightness.setter
    def detector_brightness(self, value: float) -> None:
        self._txt_log.debug(f"Setting detector brightness: {value}.")
        self._detector_brightness = value

    @property
    def source_tilt(self) -> SourceTilt:
        value = self._source_tilt
        self._txt_log.debug(f"Getting source tilt: {value}.")
        return value

    @source_tilt.setter
    def source_tilt(self, value: SourceTilt) -> None:
        self._txt_log.debug(f"Setting source tilt: {value}.")
        self._source_tilt = value

    def blank(self) -> None:
        self._txt_log.debug("Blanking.")
        self._blanked = True

    def unblank(self) -> None:
        self._txt_log.debug("Unblanking.")
        self._blanked = False

    def start_acquisition(self) -> None:
        self._txt_log.debug("Acquisition started.")
        self._acquiring = True

    def stop_acquisition(self) -> None:
        self._txt_log.debug("Acquisition stopped.")
        self._acquiring = False

    def grab_frame(self, file_name: Path | None = None) -> Image:
        self._txt_log.debug("Grabbing frame.")
        width, height = self._resolution

        arr = generate_perlin_noise(self._rng, height, width, scale=200.0, octaves=8)
        image = Image(arr, pixel_size=self.pixel_size)

        if self.scanning_area is not None:
            image = image.crop(self.scanning_area)

        # cache the grabbed image
        self._current_image = image

        if file_name is not None:
            image.save(file_name)

        return image

    def get_image(self, crop_to_scanning_area: bool = False) -> Image:
        self._txt_log.debug("Getting an image.")
        image = (
            self._current_image
            if self._current_image is not None
            else self.grab_frame()
        )

        if crop_to_scanning_area and self.scanning_area is not None:
            return image.crop(self.scanning_area)

        return image

    @property
    def line_integration(self) -> int:
        value = self._line_integration
        self._txt_log.debug(f"Getting line integration: {value}.")
        return value

    @line_integration.setter
    def line_integration(self, value: int) -> None:
        self._txt_log.debug(f"Setting line integration: {value}.")
        self._line_integration = value

    @property
    def dwell_time(self) -> float:
        value = self._dwell_time
        self._txt_log.debug(f"Getting dwell time: {value}.")
        return value

    @dwell_time.setter
    def dwell_time(self, value: float) -> None:
        self._txt_log.debug(f"Setting dwell time: {value}.")
        self._dwell_time = value

    @property
    def bit_depth(self) -> int:
        value = self._bit_depth
        self._txt_log.debug(f"Getting bit depth: {value}.")
        return value

    @bit_depth.setter
    def bit_depth(self, value: int) -> None:
        self._txt_log.debug(f"Setting bit depth: {value}.")
        self._bit_depth = value

    @property
    def resolution(self) -> tuple[int, int]:
        value = self._resolution
        self._txt_log.debug(f"Getting resolution: {value}.")
        return value

    @resolution.setter
    def resolution(self, value: tuple[int, int]) -> None:
        self._txt_log.debug(f"Setting resolution: {value}.")
        self._resolution = value

    @property
    def horizontal_field_width(self) -> float:
        value = self._horizontal_field_width_nm
        self._txt_log.debug(f"Getting horizontal field width: {value}.")
        return value

    @horizontal_field_width.setter
    def horizontal_field_width(self, value: float) -> None:
        self._txt_log.debug(f"Setting horizontal field width: {value}.")
        self._horizontal_field_width_nm = value

    @property
    def vertical_field_width(self) -> float:
        value = self._vertical_field_width_nm
        self._txt_log.debug(f"Getting vertical field width: {value}.")
        return value

    @vertical_field_width.setter
    def vertical_field_width(self, value: float) -> None:
        self._txt_log.debug(f"Setting vertical field width: {value}.")
        self._vertical_field_width_nm = value

    @property
    def pixel_size(self) -> float:
        value = self.horizontal_field_width / self.resolution[0]
        self._txt_log.debug(f"Getting pixel size: {value}.")
        return value

    @pixel_size.setter
    def pixel_size(self, value: float) -> None:
        raise NotImplementedError(
            "Setting pixel size is not implemented in the simulator."
        )

    @property
    def scanning_area(self) -> RelativeScanningArea | None:
        value = self._scanning_area
        self._txt_log.debug(f"Getting scanning area: {value}.")
        return value

    @scanning_area.setter
    def scanning_area(self, value: RelativeScanningArea | None) -> None:
        self._txt_log.debug(f"Setting scanning area: {value}.")
        self._scanning_area = value

    def manufacturer_prop(self, name: str) -> Any:
        try:
            value = self._manufacturer_properties[name]
            self._txt_log.debug(f"Getting manufacturer property '{name}': {value}.")
            return value
        except KeyError as e:
            raise MicroscopeError(
                f"Internal property {name} does not exist for the simulated beam"
            ) from e

    def set_manufacturer_prop(self, name: str, value: Any) -> Any:
        self._txt_log.debug(f"Setting manufacturer property '{name}': {value}.")
        self._manufacturer_properties[name] = value

    @property
    def beam_shift_to_stage_move(self) -> tuple[float, float]:
        return self._beam_shift_to_stage_move

    @property
    def image_to_beam_shift(self) -> tuple[float, float]:
        return self._image_to_beam_shift

    @property
    def minimal_dwell(self) -> float:
        lo, _ = self.limits("dwell_time")
        return float(lo)

    def _apply_numeric(
        self,
        var: str,
        requested: float,
        *,
        rel_noise: float = 0.0,
        abs_noise: float = 0.0,
    ) -> float:
        lo, hi = self.limits(var)

        v = requested
        if rel_noise:
            v += requested * self._rng.normal(0.0, rel_noise)
        if abs_noise:
            v += self._rng.normal(0.0, abs_noise)

        return min(max(v, lo), hi)

    @property
    def manufacturer_prop_names(self) -> list[str]:
        return list(self._manufacturer_properties.keys())

    @property
    def txt_log(self) -> TextLogger:
        return self._txt_log


def generate_perlin_noise(
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
