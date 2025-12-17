# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


import numpy as np

from fibsem_maestro.core.beam_shift import BeamShift
from fibsem_maestro.core.image import Image
from fibsem_maestro.core.lens_alignment import LensAlignment
from fibsem_maestro.core.point import RelativePoint
from fibsem_maestro.core.scanning_area import ScanningArea
from fibsem_maestro.core.source_tilt import SourceTilt
from fibsem_maestro.core.stigmator import Stigmator
from fibsem_maestro.microscope.abstract_control.beam_control import BeamControl


class SimulatedBeamControl(BeamControl):
    """Simulated beam controller."""

    def __init__(self, *, name: str, rng: np.random.Generator):
        self._name = name
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
        self._scanning_area = ScanningArea(
            origin=RelativePoint(0.0, 0.0), width=0.1, height=0.1
        )

        self._beam_shift_to_stage_move = (1.0, 1.0)
        self._image_to_beam_shift = (1.0, 1.0)

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
        """
        Return numeric limits for a variable.

        Args:
            var (str): Variable name (e.g. "working_distance", "stigmator_x").

        Returns:
            tuple[float, float]: (min, max) in the units of that variable
            (nm for distance-like vars, unitless for stigmator, degrees for tilts).
        """
        return self._limits.get(var, (-float("inf"), float("inf")))

    @property
    def working_distance(self) -> float:
        """Working distance in nanometers."""
        return self._working_distance_nm

    def try_set_working_distance(self, value: float) -> float:
        """Attempt to set working distance (approximately).

        Adds small relative noise and clamps to limits.

        Args:
            value (float): Requested working distance (nm).

        Returns:
            float: Actual working distance after the attempted set (nm).
        """
        self._working_distance_nm = self._apply_numeric(
            "working_distance", value, rel_noise=1e-4
        )
        return self._working_distance_nm

    @property
    def stigmator(self) -> Stigmator:
        """Return the current stigmator."""
        return self._stigmator

    def try_set_stigmator(self, value: Stigmator) -> Stigmator:
        """
        Attempt to set stigmator (approximately).

        Args:
            value (Stigmator): Requested stigmator.

        Returns:
            Stigmator: Actual stigmator after setting.
        """
        x = self._apply_numeric("stigmator_x", value.x, abs_noise=0.001)
        y = self._apply_numeric("stigmator_y", value.y, abs_noise=0.001)
        self._stigmator = Stigmator(x=x, y=y)
        return self._stigmator

    @property
    def lens_alignment(self) -> LensAlignment:
        """Return the current lens alignment (nm)."""
        return self._lens_alignment

    def try_set_lens_alignment(self, value: LensAlignment) -> LensAlignment:
        """
        Attempt to set lens alignment (approximately).

        Args:
            value (LensAlignment): Requested lens alignment (nm).

        Returns:
            LensAlignment: Actual lens alignment after setting (nm).
        """
        x = self._apply_numeric("lens_alignment_x", value.x, abs_noise=50.0)
        y = self._apply_numeric("lens_alignment_y", value.y, abs_noise=50.0)
        self._lens_alignment = LensAlignment(x=x, y=y)
        return self._lens_alignment

    @property
    def beam_shift(self) -> BeamShift:
        """Return the current beam shift (nm)."""
        return self._beam_shift

    def try_set_beam_shift(self, value: BeamShift) -> BeamShift:
        """
        Attempt to set beam shift (approximately).

        Args:
            value (BeamShift): Requested beam shift (nm).

        Returns:
            BeamShift: Actual beam shift after setting (nm).
        """
        x = self._apply_numeric("beam_shift_x", value.x, abs_noise=20.0)
        y = self._apply_numeric("beam_shift_y", value.y, abs_noise=20.0)
        self._beam_shift = BeamShift(x=x, y=y)
        return self._beam_shift

    @property
    def detector_contrast(self) -> float:
        return float(self._detector_contrast)

    def try_set_detector_contrast(self, value: float) -> float:
        self._detector_contrast = self._apply_numeric(
            "detector_contrast", value, abs_noise=0.01
        )
        return float(self._detector_contrast)

    @property
    def detector_brightness(self) -> float:
        return float(self._detector_brightness)

    def try_set_detector_brightness(self, value: float) -> float:
        self._detector_brightness = self._apply_numeric(
            "detector_brightness", value, abs_noise=0.01
        )
        return float(self._detector_brightness)

    @property
    def source_tilt(self) -> SourceTilt:
        return self._source_tilt

    def try_set_source_tilt(self, value: SourceTilt) -> SourceTilt:
        x = self._apply_numeric("source_tilt_x", value.x, abs_noise=0.01)
        y = self._apply_numeric("source_tilt_y", value.y, abs_noise=0.01)
        self._source_tilt = SourceTilt(x=x, y=y)
        return self._source_tilt

    def blank(self) -> None:
        self._blanked = True

    def unblank(self) -> None:
        self._blanked = False

    def start_acquisition(self) -> None:
        self._acquiring = True

    def stop_acquisition(self) -> None:
        self._acquiring = False

    def grab_frame(self) -> Image:
        """Acquire and return a single synthetic frame."""
        width, height = self._resolution

        arr = np.array(np.zeros((height, width)), dtype=float)

        return Image(arr, pixel_size=self.pixel_size)

    def get_image(self, crop_to_scanning_area: bool = False) -> Image:
        _ = crop_to_scanning_area
        return self.grab_frame()

    @property
    def line_integration(self) -> int:
        return int(self._line_integration)

    def try_set_line_integration(self, value: int) -> int:
        self._line_integration = max(1, int(value))
        return int(self._line_integration)

    @property
    def dwell_time(self) -> float:
        return float(self._dwell_time)

    def try_set_dwell_time(self, value: float) -> float:
        self._dwell_time = self._apply_numeric(
            "dwell_time", float(value), rel_noise=1e-3
        )
        return float(self._dwell_time)

    @property
    def bit_depth(self) -> int:
        return int(self._bit_depth)

    def try_set_bit_depth(self, value: int) -> int:
        self._bit_depth = 16 if int(value) >= 16 else 8
        return int(self._bit_depth)

    @property
    def resolution(self) -> tuple[int, int]:
        return (int(self._resolution[0]), int(self._resolution[1]))

    def try_set_resolution(self, value: tuple[int, int]) -> tuple[int, int]:
        self._resolution = (max(1, int(value[0])), max(1, int(value[1])))
        return self.resolution

    @property
    def horizontal_field_width(self) -> float:
        """Horizontal field width in nanometers."""
        return float(self._horizontal_field_width_nm)

    def try_set_horizontal_field_width(self, value: float) -> float:
        self._horizontal_field_width_nm = self._apply_numeric(
            "horizontal_field_width", value, rel_noise=1e-3
        )
        return float(self._horizontal_field_width_nm)

    @property
    def vertical_field_width(self) -> float:
        """Vertical field width in nanometers."""
        return float(self._vertical_field_width_nm)

    def try_set_vertical_field_width(self, value: float) -> float:
        self._vertical_field_width_nm = self._apply_numeric(
            "vertical_field_width", value, rel_noise=1e-3
        )
        return float(self._vertical_field_width_nm)

    @property
    def pixel_size(self) -> float:
        """Return the pixel size in nanometers per pixel."""
        return self.horizontal_field_width / self.resolution[0]

    @property
    def scanning_area(self) -> ScanningArea:
        return self._scanning_area

    def try_set_scanning_area(self, value: ScanningArea) -> ScanningArea:
        self._scanning_area = value
        return self._scanning_area

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
