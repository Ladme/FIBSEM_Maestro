# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from abc import ABC, abstractmethod
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from fibsem_maestro.core.area import NMArea, RelativeArea
from fibsem_maestro.core.beam_shift import BeamShift
from fibsem_maestro.core.beam_type import BeamType
from fibsem_maestro.core.direction import Direction
from fibsem_maestro.core.image import Image
from fibsem_maestro.core.lens_alignment import LensAlignment
from fibsem_maestro.core.resolution import Resolution
from fibsem_maestro.core.source_tilt import SourceTilt
from fibsem_maestro.core.stigmator import Stigmator
from fibsem_maestro.logging.text.text_logger import TextLogger
from fibsem_maestro.microscope.error import MicroscopeError
from fibsem_maestro.properties.beam_properties import BeamProperties
from fibsem_maestro.store.frame.frame_store import FrameStore


class BeamControl(ABC):
    """
    Abstract interface for controlling an electron or ion beam in a microscope.
    """

    @classmethod
    def beam_type(cls) -> BeamType:
        """Returns the beam type (electron or ion)."""
        raise NotImplementedError(f"beam_type is not implemented for {cls.__name__}")

    @property
    @abstractmethod
    def working_distance(self) -> float:
        """Working distance between the sample and the objective lens in nanometers."""

    @working_distance.setter
    @abstractmethod
    def working_distance(self, value: float) -> None:
        """
        Set the working distance in nanometers.

        Args:
            value: Working distance in nanometers.
        """

    @property
    @abstractmethod
    def stigmator(self) -> Stigmator:
        """Stigmator settings used for beam astigmatism correction."""

    @stigmator.setter
    @abstractmethod
    def stigmator(self, value: Stigmator) -> None:
        """
        Set the stigmator settings.

        Args:
            value: New stigmator values.
        """

    @property
    def stigmator_x(self) -> float:
        """X-component of the stigmator."""
        return self.stigmator.x

    @stigmator_x.setter
    def stigmator_x(self, value: float) -> None:
        """
        Set the x-component of the stigmator, preserving the y-component.

        Args:
            value: New x stigmatism value.
        """
        self.stigmator = Stigmator(value, self.stigmator_y)

    @property
    def stigmator_y(self) -> float:
        """Y-component of the stigmator."""
        return self.stigmator.y

    @stigmator_y.setter
    def stigmator_y(self, value: float) -> None:
        """
        Set the y-component of the stigmator, preserving the x-component.

        Args:
            value: New y stigmatism value.
        """
        self.stigmator = Stigmator(self.stigmator_x, value)

    @property
    @abstractmethod
    def lens_alignment(self) -> LensAlignment:
        """Lens alignment settings in nanometers."""

    @lens_alignment.setter
    @abstractmethod
    def lens_alignment(self, value: LensAlignment) -> None:
        """
        Set the lens alignment settings.

        Args:
            value: New lens alignment values in nanometers.
        """

    @property
    def lens_alignment_x(self) -> float:
        """X-component of the lens alignment in nanometers."""
        return self.lens_alignment.x

    @lens_alignment_x.setter
    def lens_alignment_x(self, value: float) -> None:
        """
        Set the x-component of the lens alignment, preserving the y-component.

        Args:
            value: New x alignment value in nanometers.
        """
        self.lens_alignment = LensAlignment(value, self.lens_alignment_y)

    @property
    def lens_alignment_y(self) -> float:
        """Y-component of the lens alignment in nanometers."""
        return self.lens_alignment.y

    @lens_alignment_y.setter
    def lens_alignment_y(self, value: float) -> None:
        """
        Set the y-component of the lens alignment, preserving the x-component.

        Args:
            value: New y alignment value in nanometers.
        """
        self.lens_alignment = LensAlignment(self.lens_alignment_x, value)

    @property
    @abstractmethod
    def beam_shift(self) -> BeamShift:
        """Current beam shift in nanometers."""

    @beam_shift.setter
    @abstractmethod
    def beam_shift(self, value: BeamShift) -> None:
        """
        Set the beam shift.

        Args:
            value: New beam shift in nanometers.
        """

    @property
    @abstractmethod
    def detector_contrast(self) -> float:
        """Detector contrast level in the range [0, 1]."""

    @detector_contrast.setter
    @abstractmethod
    def detector_contrast(self, value: float) -> None:
        """
        Set the detector contrast level.

        Args:
            value: Contrast value in the range [0, 1].
        """

    @property
    @abstractmethod
    def detector_brightness(self) -> float:
        """Detector brightness level in the range [0, 1]."""

    @detector_brightness.setter
    @abstractmethod
    def detector_brightness(self, value: float) -> None:
        """
        Set the detector brightness level.

        Args:
            value: Brightness value in the range [0, 1].
        """

    @property
    @abstractmethod
    def source_tilt(self) -> SourceTilt:
        """Electron source tilt settings in degrees."""

    @source_tilt.setter
    @abstractmethod
    def source_tilt(self, value: SourceTilt) -> None:
        """
        Set the electron source tilt.

        Args:
            value: New source tilt values in degrees.
        """

    @abstractmethod
    def blank(self) -> None:
        """Blank the beam, stopping it from reaching the sample."""

    @abstractmethod
    def unblank(self) -> None:
        """Unblank the beam, allowing it to reach the sample."""

    @abstractmethod
    def start_acquisition(self) -> None:
        """Start continuous image acquisition."""

    @abstractmethod
    def stop_acquisition(self) -> None:
        """Stop continuous image acquisition."""

    @abstractmethod
    def grab_frame(self, frame_store: FrameStore | None = None) -> Image:
        """
        Perform a new scan and return the acquired image.

        Args:
            frame_store: Optional store controlling how the acquired frame is
                persisted. If `None`, the frame is returned but not stored.

        Returns:
            The acquired image.
        """

    @abstractmethod
    def get_image(self, crop_to_scanning_area: bool = False) -> Image:
        """
        Return the currently displayed image without performing a new scan.

        Args:
            crop_to_scanning_area: If `True`, crop the returned image to the
                active scanning area. If `False`, return the full image.

        Returns:
            The current image displayed on the microscope.
        """

    @abstractmethod
    def rectangle_milling(
        self,
        milling_area: NMArea,
        milling_depth: float,
        direction: Direction,
        pattern_file: Path | str,
    ) -> None:
        """Perform milling in a rectangular area."""

    @property
    @abstractmethod
    def line_integration(self) -> int:
        """Number of times each scan line is integrated before advancing."""

    @line_integration.setter
    @abstractmethod
    def line_integration(self, value: int) -> None:
        """
        Set the number of line integrations per scan.

        Args:
            value: Number of integrations per scan line.
        """

    @property
    @abstractmethod
    def dwell_time(self) -> float:
        """Time spent per pixel during a scan in seconds."""

    @dwell_time.setter
    @abstractmethod
    def dwell_time(self, value: float) -> None:
        """
        Set the dwell time per pixel.

        Args:
            value: Dwell time in seconds.
        """

    @property
    @abstractmethod
    def bit_depth(self) -> int:
        """Bit depth of the detector output."""

    @bit_depth.setter
    @abstractmethod
    def bit_depth(self, value: int) -> None:
        """
        Set the detector bit depth.

        Args:
            value: Bit depth.
        """

    @property
    @abstractmethod
    def resolution(self) -> Resolution:
        """Scan resolution in pixels."""

    @resolution.setter
    @abstractmethod
    def resolution(self, value: Resolution) -> None:
        """
        Set the scan resolution.

        Args:
            value: Scan resolution in pixels.
        """

    @property
    @abstractmethod
    def horizontal_field_width(self) -> float:
        """Horizontal field of view in nanometers."""

    @horizontal_field_width.setter
    @abstractmethod
    def horizontal_field_width(self, value: float) -> None:
        """
        Set the horizontal field of view.

        Args:
            value: Horizontal field width in nanometers.
        """

    @property
    @abstractmethod
    def vertical_field_width(self) -> float:
        """Vertical field of view in nanometers."""

    @vertical_field_width.setter
    @abstractmethod
    def vertical_field_width(self, value: float) -> None:
        """
        Set the vertical field of view.

        Args:
            value: Vertical field width in nanometers.
        """

    @property
    @abstractmethod
    def pixel_size(self) -> float:
        """Physical size of a single pixel in nanometers."""

    @pixel_size.setter
    @abstractmethod
    def pixel_size(self, value: float) -> None:
        """
        Set the pixel size.

        Args:
            value: Pixel size in nanometers.
        """

    @property
    @abstractmethod
    def scanning_area(self) -> RelativeArea:
        """Active scanning area expressed in relative coordinates."""

    @scanning_area.setter
    @abstractmethod
    def scanning_area(self, value: RelativeArea) -> None:
        """
        Set the active scanning area.

        Args:
            value: Scanning area in relative coordinates.
        """

    @abstractmethod
    def manufacturer_prop(self, name: str) -> Any:
        """
        Retrieve a manufacturer-specific beam property by name.

        Args:
            name: Property name as defined by the manufacturer.

        Returns:
            The current value of the property.
        """

    @abstractmethod
    def set_manufacturer_prop(self, name: str, value: Any) -> None:
        """
        Set a manufacturer-specific beam property by name.

        Args:
            name: Property name as defined by the manufacturer.
            value: New property value.
        """

    @property
    @abstractmethod
    def image_to_beam_shift(self) -> tuple[float, float]:
        """Per-axis scale factors for converting image coordinates to beam shift."""

    @property
    @abstractmethod
    def minimal_dwell(self) -> float:
        """Minimum supported dwell time in seconds."""

    @abstractmethod
    def limits(self, var: str) -> tuple[float, float]:
        """
        Return the hardware limits for a beam parameter.

        Args:
            var: Parameter name.

        Returns:
            A `(min, max)` tuple of the allowed value range.
        """

    @property
    @abstractmethod
    def manufacturer_prop_names(self) -> list[str]:
        """Names of all manufacturer-specific properties available on this beam."""

    @property
    @abstractmethod
    def txt_log(self) -> TextLogger:
        """Logger for diagnostic and status messages."""

    @contextmanager
    def total_blanked(self) -> Iterator[None]:
        """
        Context manager that fully blanks the beam during the enclosed block.

        Saves the current detector contrast and brightness, sets both to zero,
        and blanks the beam on entry. Restores the original values and unblanks
        the beam on exit, even if an exception occurs inside the block.

        Yields:
            None: Control is yielded to the caller with the beam fully blanked.
        """
        contrast_backup = self.detector_contrast
        brightness_backup = self.detector_brightness

        self.detector_contrast = 0
        self.detector_brightness = 0
        self.blank()

        try:
            yield
        finally:
            self.detector_contrast = contrast_backup
            self.detector_brightness = brightness_backup
            self.unblank()

    @property
    def prop_names(self) -> list[str]:
        """
        All available property names, including manufacturer-specific ones.

        Combines the standard `BeamProperties` field names with any
        manufacturer-specific property names exposed by the control.

        Returns:
            A list of all property names available on this beam.
        """
        properties = list(BeamProperties.model_fields.keys())
        properties.extend(self.manufacturer_prop_names)

        return properties

    def set_properties(self, properties: BeamProperties) -> None:
        """
        Apply a set of beam properties to this beam control.

        Iterates over the non-None fields of `properties` and applies each
        one via the corresponding setter. Manufacturer-specific properties are
        routed to `set_manufacturer_prop`. Fields without a setter raise a
        `MicroscopeError`.

        Args:
            properties: Container of beam property values to apply.

        Raises:
            MicroscopeError: If a manufacturer property cannot be set, or if a
                field has no corresponding setter.
        """
        field_names = list(properties.model_dump(exclude_none=True).keys())
        manufacturer_properties = self.manufacturer_prop_names

        # set the pre-defined properties
        for field_name in field_names:
            value = getattr(properties, field_name)
            if value is None:
                continue

            # if the property is a manufacturer property
            if field_name in manufacturer_properties:
                try:
                    self.set_manufacturer_prop(field_name, value)
                    continue
                except Exception as e:
                    raise MicroscopeError(
                        f"Could not set manufacturer property '{field_name}': {e}"
                    ) from e

            # check whether a setter exists for this property
            attr = getattr(type(self), field_name, None)
            if not isinstance(attr, property) or attr.fset is None:
                raise MicroscopeError(f"No setter defined for property '{field_name}'")

            setattr(self, field_name, value)

    def collect_properties(self, selected: list[str]) -> BeamProperties:
        """
        Read selected beam properties and return them as a `BeamProperties` instance.

        Collects only the properties whose names appear in `selected`.
        Standard `BeamProperties` fields are read via their property accessors;
        manufacturer-specific properties are retrieved via `manufacturer_prop`.
        Unknown names are logged as warnings and excluded from the result.

        Args:
            selected: Names of the properties to collect.

        Returns:
            A `BeamProperties` instance containing the collected values.
        """
        # get field names to write out
        field_names = list(
            filter(lambda x: x in selected, BeamProperties.model_fields.keys())
        )

        # collect the values of the properties
        values = {}
        for field_name in field_names:
            values[field_name] = getattr(self, field_name)

        # collect manufacturer properties
        for field_name in filter(lambda x: x in selected, self.manufacturer_prop_names):
            values[field_name] = self.manufacturer_prop(field_name)

        # get unknown properties
        unknown = [prop for prop in selected if prop not in values]
        if len(unknown) > 0:
            self.txt_log.warning(
                f"The following selected beam properties are not known: {' '.join(unknown)}"
            )

        return BeamProperties(**values)
