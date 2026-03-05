# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

import inspect
from abc import ABC, abstractmethod
from typing import Any

from fibsem_maestro.core.area import RelativeArea
from fibsem_maestro.core.beam_shift import BeamShift
from fibsem_maestro.core.image import Image
from fibsem_maestro.core.lens_alignment import LensAlignment
from fibsem_maestro.core.resolution import Resolution
from fibsem_maestro.core.source_tilt import SourceTilt
from fibsem_maestro.core.stigmator import Stigmator
from fibsem_maestro.logging.text.text_logger import TextLogger
from fibsem_maestro.microscope.error import MicroscopeError
from fibsem_maestro.settings.beam_properties import BeamProperties
from fibsem_maestro.store.frame.frame_store import FrameStore


class BeamControl(ABC):
    """
    Abstract interface for controlling an electron or ion beam in a microscope.
    """

    @property
    @abstractmethod
    def working_distance(self) -> float:
        """
        Get the working distance.

        Returns:
            float: Working distance in nanometers.
        """
        pass

    @working_distance.setter
    @abstractmethod
    def working_distance(self, value: float) -> None:
        """
        Set the working distance.

        Args:
            value (float): Working distance in nanometers.
        """
        pass

    @property
    @abstractmethod
    def stigmator(self) -> Stigmator:
        """
        Get the beam stigmator settings.

        Returns:
            Stigmator: Stigmator values (x, y).
        """
        pass

    @stigmator.setter
    @abstractmethod
    def stigmator(self, value: Stigmator) -> None:
        """
        Set the beam stigmator settings.

        Args:
            value (Stigmator): New stigmator values.
        """
        pass

    @property
    def stigmator_x(self) -> float:
        """
        Get the x-component of the stigmator.

        Returns:
            float: X stigmatism value.
        """
        return self.stigmator.x

    @stigmator_x.setter
    def stigmator_x(self, value: float) -> None:
        """
        Set the x-component of the stigmator.

        Args:
            value (float): X stigmatism value.
        """
        self.stigmator = Stigmator(value, self.stigmator_y)

    @property
    def stigmator_y(self) -> float:
        """
        Get the y-component of the stigmator.

        Returns:
            float: Y stigmatism value.
        """
        return self.stigmator.y

    @stigmator_y.setter
    def stigmator_y(self, value: float) -> None:
        """
        Set the y-component of the stigmator.

        Args:
            value (float): Y stigmatism value.
        """
        self.stigmator = Stigmator(self.stigmator_x, value)

    @property
    @abstractmethod
    def lens_alignment(self) -> LensAlignment:
        """
        Get the lens alignment settings.

        Returns:
            LensAlignment: Lens alignment values (x, y).
        """
        pass

    @lens_alignment.setter
    @abstractmethod
    def lens_alignment(self, value: LensAlignment) -> None:
        """
        Set the lens alignment settings.

        Args:
            value (LensAlignment): New lens alignment values.
        """
        pass

    @property
    def lens_alignment_x(self) -> float:
        """
        Get the x-component of the lens alignment.

        Returns:
            float: X alignment value.
        """
        return self.lens_alignment.x

    @lens_alignment_x.setter
    def lens_alignment_x(self, value: float) -> None:
        """
        Set the x-component of the lens alignment.

        Args:
            value (float): X alignment value.
        """
        self.lens_alignment = LensAlignment(value, self.lens_alignment_y)

    @property
    def lens_alignment_y(self) -> float:
        """
        Get the y-component of the lens alignment.

        Returns:
            float: Y alignment value.
        """
        return self.lens_alignment.y

    @lens_alignment_y.setter
    def lens_alignment_y(self, value: float) -> None:
        """
        Set the y-component of the lens alignment.

        Args:
            value (float): Y alignment value.
        """
        self.lens_alignment = LensAlignment(self.lens_alignment_x, value)

    @property
    @abstractmethod
    def beam_shift(self) -> BeamShift:
        """
        Get the beam shift.

        Returns:
            BeamShift: Beam shift values (x, y).
        """
        pass

    @beam_shift.setter
    def beam_shift(self, value: BeamShift):
        """
        Set the beam shift.

        Args:
            value (BeamShift): New beam shift values.
        """
        pass

    @property
    @abstractmethod
    def detector_contrast(self) -> float:
        """
        Get the detector contrast.

        Returns:
            float: Detector contrast value.
        """
        pass

    @detector_contrast.setter
    @abstractmethod
    def detector_contrast(self, value: float) -> None:
        """
        Set the detector contrast.

        Args:
            value (float): Detector contrast value.
        """
        pass

    @property
    @abstractmethod
    def detector_brightness(self) -> float:
        """
        Get the detector brightness.

        Returns:
            float: Detector brightness value.
        """
        pass

    @detector_brightness.setter
    @abstractmethod
    def detector_brightness(self, value: float) -> None:
        """
        Set the detector brightness.

        Args:
            value (float): Detector brightness value.
        """
        pass

    @property
    @abstractmethod
    def source_tilt(self) -> SourceTilt:
        """
        Get the source tilt.

        Returns:
            SourceTilt: Source tilt values.
        """
        pass

    @source_tilt.setter
    @abstractmethod
    def source_tilt(self, value: SourceTilt) -> None:
        """
        Set the source tilt.

        Args:
            value (SourceTilt): New source tilt values.
        """
        pass

    @abstractmethod
    def blank(self) -> None:
        """Blank the beam."""
        pass

    @abstractmethod
    def unblank(self) -> None:
        """Unblank the beam."""
        pass

    @abstractmethod
    def start_acquisition(self) -> None:
        """Start image acquisition."""
        pass

    @abstractmethod
    def stop_acquisition(self) -> None:
        """Stop image acquisition."""
        pass

    @abstractmethod
    def grab_frame(self, frame_store: FrameStore | None = None) -> Image:
        """
        Scan and retrieve an image from the microscope.

        Args:
            frame_store: Optional store controlling how the acquired frame is
                persisted. If `None`, the frame is returned but not stored.

        Returns:
            The acquired image.
        """
        pass

    @abstractmethod
    def get_image(self, crop_to_scanning_area: bool = False) -> Image:
        """
        Retrieve the current image displayed on the microscope without performing a new scan.

        This method fetches the currently displayed image from the microscope. It does not initiate
        a new scan. Optionally, the image can be cropped to the scanning area if specified.

        Args:
            crop_to_scanning_area (bool): If True, crop the image to the scanning area.
                                        If False, return the full image.

        Returns:
            Image: The current image displayed on the microscope.
        """
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
        """
        Get the number of integrations per scan line.

        Returns:
            int: Number of integrations per scan line.
        """
        pass

    @line_integration.setter
    @abstractmethod
    def line_integration(self, value: int) -> None:
        """
        Set the number of integrations per scan line.

        Args:
            value (int): Number of integrations per scan line.
        """
        pass

    @property
    @abstractmethod
    def dwell_time(self) -> float:
        """
        Get the dwell time.

        Returns:
            float: Dwell time in seconds.
        """
        pass

    @dwell_time.setter
    @abstractmethod
    def dwell_time(self, value: float) -> None:
        """
        Set the dwell time.

        Args:
            value (float): Dwell time in seconds.
        """
        pass

    @property
    @abstractmethod
    def bit_depth(self) -> int:
        """
        Get the image bit depth.

        Returns:
            int: Bit depth.
        """
        pass

    @bit_depth.setter
    @abstractmethod
    def bit_depth(self, value: int) -> None:
        """
        Set the image bit depth.

        Args:
            value (int): Bit depth.
        """
        pass

    @property
    @abstractmethod
    def resolution(self) -> Resolution:
        """
        Get the image resolution.

        Returns:
            Resolution: Image resolution in pixels.
        """
        pass

    @resolution.setter
    @abstractmethod
    def resolution(self, value: Resolution) -> None:
        """
        Set the image resolution.

        Args:
            value (Resolution): Image resolution in pixels.
        """
        pass

    @property
    @abstractmethod
    def horizontal_field_width(self) -> float:
        """
        Get the horizontal field width.

        Returns:
            float: Horizontal field width.
        """
        pass

    @horizontal_field_width.setter
    @abstractmethod
    def horizontal_field_width(self, value: float) -> None:
        """
        Set the horizontal field width.

        Args:
            value (float): Horizontal field width.
        """
        pass

    @property
    @abstractmethod
    def vertical_field_width(self) -> float:
        """
        Get the vertical field width.

        Returns:
            float: Vertical field width.
        """
        pass

    @vertical_field_width.setter
    @abstractmethod
    def vertical_field_width(self, value: float) -> None:
        """
        Set the vertical field width.

        Args:
            value (float): Vertical field width.
        """
        pass

    @property
    @abstractmethod
    def pixel_size(self) -> float:
        """
        Get the pixel size.

        Returns:
            float: Pixel size.
        """
        pass

    @pixel_size.setter
    @abstractmethod
    def pixel_size(self, value: float) -> None:
        """
        Set the pixel size.

        Args:
            value (float): Pixel size.
        """
        pass

    @property
    @abstractmethod
    def scanning_area(self) -> RelativeArea:
        """
        Get the active scanning area.

        Returns:
            RelativeArea: The current scanning area.
        """
        pass

    @scanning_area.setter
    @abstractmethod
    def scanning_area(self, value: RelativeArea) -> None:
        """
        Set the active scanning area.

        Args:
            value (RelativeArea): Scanning area definition.
        """
        pass

    @abstractmethod
    def manufacturer_prop(self, name: str) -> Any:
        """
        Get a manufacturer beam property.

        Args:
            name (str): Property name.

        Returns:
            Any: Property value.
        """
        pass

    @abstractmethod
    def set_manufacturer_prop(self, name: str, value: Any) -> None:
        """
        Set a manufacturer beam property.

        Args:
            name (str): Property name.
            value (Any): Property value.
        """
        pass

    @property
    @abstractmethod
    def beam_shift_to_stage_move(self) -> tuple[float, float]:
        """
        Get conversion from beam shift to stage movement.

        Returns:
            tuple[float, float]: Conversion factors.
        """
        pass

    @property
    @abstractmethod
    def image_to_beam_shift(self) -> tuple[float, float]:
        """
        Get conversion from image coordinates to beam shift.

        Returns:
            tuple[float, float]: Conversion factors.
        """
        pass

    @property
    @abstractmethod
    def minimal_dwell(self) -> float:
        """
        Get the minimal supported dwell time.

        Returns:
            float: Minimal dwell time.
        """
        pass

    @abstractmethod
    def limits(self, var: str) -> tuple[float, float]:
        """
        Get hardware limits for a beam parameter.

        Args:
            var (str): Parameter name.

        Returns:
            tuple[float, float]: Minimum and maximum allowed values.
        """
        pass

    @property
    @abstractmethod
    def manufacturer_prop_names(self) -> list[str]:
        """
        Get a list of all manufacturer properties of the beam.

        Returns:
            list[str]: List of all manufacturer properties of the beam.
        """
        pass

    @property
    @abstractmethod
    def txt_log(self) -> TextLogger:
        pass

    @classmethod
    def get_property_names(cls) -> list[str]:
        """
        Return the names of all properties defined on the class.

        Returns:
            list[str]: Names of property attributes on this class.
        """
        props = []
        for name, obj in inspect.getmembers(cls):
            if isinstance(obj, property):
                props.append(name)
        return props

    @property
    def prop_names(self) -> list[str]:
        """
        Get a list of all properties of the beam, including the manufacturer properties.

        Return:
            MicroscopePropertyNames: Collection of all the properties of the microscope.
        """
        properties = list(BeamProperties.model_fields.keys())
        properties.extend(self.manufacturer_prop_names)

        return properties

    def set_properties(self, properties: BeamProperties) -> None:
        """
        Apply beam-related microscope settings.

        Uses this beam control to set multiple beam-related properties of the
        microscope to the values provided in the given container.

        Args:
            properties (BeamProperties): Container of beam property values to apply.

        Raises:
            AttributeError: If a required property setter is missing or not callable.
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
