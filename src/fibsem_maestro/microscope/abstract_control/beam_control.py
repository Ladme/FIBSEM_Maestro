# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

import inspect
from abc import ABC, abstractmethod
from typing import Any

from fibsem_maestro.core.beam_shift import BeamShift
from fibsem_maestro.core.image import Image
from fibsem_maestro.core.lens_alignment import LensAlignment
from fibsem_maestro.core.scanning_area import ScanningArea
from fibsem_maestro.core.source_tilt import SourceTilt
from fibsem_maestro.core.stigmator import Stigmator
from fibsem_maestro.settings.beam_properties import BeamProperties


class BeamControl(ABC):
    """
    This is an abstract base class providing an interface for controlling a beam (can be electron or ion) in a microscope.
    """

    @property
    @abstractmethod
    def working_distance(self) -> float:
        """Working distance in nanometers."""
        pass

    @working_distance.setter
    @abstractmethod
    def working_distance(self, value: float) -> None:
        pass

    @property
    @abstractmethod
    def stigmator(self) -> Stigmator:
        pass

    @stigmator.setter
    @abstractmethod
    def stigmator(self, value: Stigmator) -> None:
        pass

    @property
    def stigmator_x(self) -> float:
        return self.stigmator.x

    @stigmator_x.setter
    def stigmator_x(self, value: float) -> None:
        self.stigmator = Stigmator(value, self.stigmator_y)

    @property
    def stigmator_y(self) -> float:
        return self.stigmator.y

    @stigmator_y.setter
    def stigmator_y(self, value: float) -> None:
        self.stigmator = Stigmator(self.stigmator_x, value)

    @property
    @abstractmethod
    def lens_alignment(self) -> LensAlignment:
        pass

    @lens_alignment.setter
    @abstractmethod
    def lens_alignment(self, value: LensAlignment) -> None:
        pass

    @property
    def lens_alignment_x(self) -> float:
        return self.lens_alignment.x

    @lens_alignment_x.setter
    def lens_alignment_x(self, value: float) -> None:
        self.lens_alignment = LensAlignment(value, self.lens_alignment_y)

    @property
    def lens_alignment_y(self) -> float:
        return self.lens_alignment.y

    @lens_alignment_y.setter
    def lens_alignment_y(self, value: float) -> None:
        self.lens_alignment = LensAlignment(self.lens_alignment_x, value)

    @property
    @abstractmethod
    def beam_shift(self) -> BeamShift:
        pass

    @beam_shift.setter
    def beam_shift(self, value: BeamShift):
        pass

    @property
    @abstractmethod
    def detector_contrast(self) -> float:
        pass

    @detector_contrast.setter
    @abstractmethod
    def detector_contrast(self, value: float) -> None:
        pass

    @property
    @abstractmethod
    def detector_brightness(self) -> float:
        pass

    @detector_brightness.setter
    @abstractmethod
    def detector_brightness(self, value: float) -> None:
        pass

    @property
    @abstractmethod
    def source_tilt(self) -> SourceTilt:
        pass

    @source_tilt.setter
    @abstractmethod
    def source_tilt(self, value: SourceTilt) -> None:
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

    @line_integration.setter
    @abstractmethod
    def line_integration(self, value: int) -> None:
        pass

    @property
    @abstractmethod
    def dwell_time(self) -> float:
        pass

    @dwell_time.setter
    @abstractmethod
    def dwell_time(self, value: float) -> None:
        pass

    @property
    @abstractmethod
    def bit_depth(self) -> int:
        pass

    @bit_depth.setter
    @abstractmethod
    def bit_depth(self, value: int) -> None:
        pass

    @property
    @abstractmethod
    def resolution(self) -> tuple[int, int]:
        pass

    @resolution.setter
    @abstractmethod
    def resolution(self, value: tuple[int, int]) -> None:
        pass

    @property
    @abstractmethod
    def horizontal_field_width(self) -> float:
        pass

    @horizontal_field_width.setter
    @abstractmethod
    def horizontal_field_width(self, value: float) -> None:
        pass

    @property
    @abstractmethod
    def vertical_field_width(self) -> float:
        pass

    @vertical_field_width.setter
    @abstractmethod
    def vertical_field_width(self, value: float) -> None:
        pass

    @property
    @abstractmethod
    def pixel_size(self) -> float:
        pass

    @property
    @abstractmethod
    def scanning_area(self) -> ScanningArea:
        pass

    @scanning_area.setter
    @abstractmethod
    def scanning_area(self, value: ScanningArea) -> None:
        pass

    @abstractmethod
    def custom(self, name: str) -> Any:
        pass

    @abstractmethod
    def set_custom(self, name: str, value: Any) -> Any:
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

    def apply_beam_properties(self, properties: BeamProperties) -> None:
        field_names = list(BeamProperties.model_fields.keys())
        field_names.remove("custom")

        # set custom beam properties
        for custom_property, value in properties.custom.items():
            self.set_custom(custom_property, value)

        # set the pre-defined properties
        for field_name in field_names:
            value = getattr(properties, field_name)

            setter = getattr(self, field_name, None)
            if setter is None or not callable(setter):
                raise AttributeError(
                    f"BeamControl is missing required callable setter '{field_name}'"
                )

            setter(value)
