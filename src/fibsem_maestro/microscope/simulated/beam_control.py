# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from typing import Any

import numpy as np

from fibsem_maestro.core.beam_shift import BeamShift
from fibsem_maestro.core.image import Image
from fibsem_maestro.core.lens_alignment import LensAlignment
from fibsem_maestro.core.scanning_area import ScanningArea
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
        self._scanning_area: ScanningArea | None = None

        self._beam_shift_to_stage_move = (1.0, 1.0)
        self._image_to_beam_shift = (1.0, 1.0)

        self._internal_properties: dict[str, Any] = {}

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

    def grab_frame(self) -> Image:
        self._txt_log.debug("Grabbing frame.")
        width, height = self._resolution

        arr = np.array(np.zeros((height, width)), dtype=float)

        return Image(arr, pixel_size=self.pixel_size)

    def get_image(self, crop_to_scanning_area: bool = False) -> Image:
        _ = crop_to_scanning_area
        return self.grab_frame()

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
    def scanning_area(self) -> ScanningArea | None:
        value = self._scanning_area
        self._txt_log.debug(f"Getting scanning area: {value}.")
        return value

    @scanning_area.setter
    def scanning_area(self, value: ScanningArea | None) -> None:
        self._txt_log.debug(f"Setting scanning area: {value}.")
        self._scanning_area = value

    def internal(self, name: str) -> Any:
        try:
            value = self._internal_properties[name]
            self._txt_log.debug(f"Getting internal property '{name}': {value}.")
            return value
        except KeyError as e:
            raise MicroscopeError(
                f"Internal property {name} does not exist for the simulated beam"
            ) from e

    def set_internal(self, name: str, value: Any) -> Any:
        self._txt_log.debug(f"Setting internal property '{name}': {value}.")
        self._internal_properties[name] = value

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
    def internal_param_names(self) -> list[str]:
        return list(self._internal_properties.keys())
