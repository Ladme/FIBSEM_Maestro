# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

import inspect
from abc import ABC, abstractmethod

from fibsem_maestro.core.beam_shift import BeamShift
from fibsem_maestro.core.image import Image
from fibsem_maestro.core.lens_alignment import LensAlignment
from fibsem_maestro.core.scanning_area import ScanningArea
from fibsem_maestro.core.source_tilt import SourceTilt
from fibsem_maestro.core.stigmator import Stigmator


class BeamControl(ABC):
    """
    This is an abstract base class providing an interface for controlling a beam (can be electron or ion) in a microscope.
    """

    @property
    @abstractmethod
    def working_distance(self) -> float:
        """Working distance in nanometers."""
        pass

    @abstractmethod
    def try_set_working_distance(self, value: float) -> float:
        pass

    @property
    @abstractmethod
    def stigmator(self) -> Stigmator:
        pass

    @abstractmethod
    def try_set_stigmator(self, value: Stigmator) -> Stigmator:
        pass

    @property
    @abstractmethod
    def lens_alignment(self) -> LensAlignment:
        pass

    @abstractmethod
    def try_set_lens_alignment(self, value: LensAlignment) -> LensAlignment:
        pass

    @property
    @abstractmethod
    def beam_shift(self) -> BeamShift:
        pass

    @abstractmethod
    def try_set_beam_shift(self, value: BeamShift) -> BeamShift:
        pass

    @property
    @abstractmethod
    def detector_contrast(self) -> float:
        pass

    @abstractmethod
    def try_set_detector_contrast(self, value: float) -> float:
        pass

    @property
    @abstractmethod
    def detector_brightness(self) -> float:
        pass

    @abstractmethod
    def try_set_detector_brightness(self, value: float) -> float:
        pass

    @property
    @abstractmethod
    def source_tilt(self) -> SourceTilt:
        pass

    @abstractmethod
    def try_set_source_tilt(self, value: SourceTilt) -> SourceTilt:
        pass

    @abstractmethod
    def blank(self) -> None:
        pass

    @abstractmethod
    def unblank(self) -> None:
        pass

    @abstractmethod
    def start_acquisition(self) -> None:
        pass

    @abstractmethod
    def stop_acquisition(self) -> None:
        pass

    @abstractmethod
    def grab_frame(self) -> Image:
        pass

    @abstractmethod
    def get_image(self, crop_to_scanning_area: bool = False) -> Image:
        pass

    """
    @abstractmethod
    def rectangle_milling(
        self, app_file: str, leftop, size, depth: float, direction: str
    ):
        pass
    """

    @property
    @abstractmethod
    def line_integration(self) -> int:
        pass

    @abstractmethod
    def try_set_line_integration(self, value: int) -> int:
        pass

    @property
    @abstractmethod
    def dwell_time(self) -> float:
        pass

    @abstractmethod
    def try_set_dwell_time(self, value: float) -> float:
        pass

    @property
    @abstractmethod
    def bit_depth(self) -> int:
        pass

    @abstractmethod
    def try_set_bit_depth(self, value: int) -> int:
        pass

    @property
    @abstractmethod
    def resolution(self) -> tuple[int, int]:
        pass

    @abstractmethod
    def try_set_resolution(self, value: tuple[int, int]) -> tuple[int, int]:
        pass

    @property
    @abstractmethod
    def horizontal_field_width(self) -> float:
        pass

    @abstractmethod
    def try_set_horizontal_field_width(self, value: float) -> float:
        pass

    @property
    @abstractmethod
    def vertical_field_width(self) -> float:
        pass

    @abstractmethod
    def try_set_vertical_field_width(self, value: float) -> float:
        pass

    @property
    @abstractmethod
    def pixel_size(self) -> float:
        pass

    @property
    @abstractmethod
    def scanning_area(self) -> ScanningArea:
        pass

    @abstractmethod
    def try_set_scanning_area(self, value: ScanningArea) -> ScanningArea:
        pass

    @property
    @abstractmethod
    def beam_shift_to_stage_move(self) -> tuple[float, float]:
        pass

    @property
    @abstractmethod
    def image_to_beam_shift(self) -> tuple[float, float]:
        pass

    @property
    @abstractmethod
    def minimal_dwell(self) -> float:
        pass

    @abstractmethod
    def limits(self, var: str) -> tuple[float, float]:
        pass

    @classmethod
    def get_property_names(cls) -> list[str]:
        props = []
        for name, obj in inspect.getmembers(cls):
            if isinstance(obj, property):
                props.append(name)
        return props
