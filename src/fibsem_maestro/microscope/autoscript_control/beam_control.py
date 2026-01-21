# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from abc import abstractmethod
from typing import Any, Generic, TypeVar

from autoscript_sdb_microscope_client.enumerations import ImagingDevice
from autoscript_sdb_microscope_client.sdb_microscope.beams._electron_beam import (
    ElectronBeam as ElectronBeamAs,
)
from autoscript_sdb_microscope_client.sdb_microscope.beams._ion_beam import (
    IonBeam as IonBeamAs,
)
from autoscript_sdb_microscope_client.sdb_microscope_client import SdbMicroscopeClient

from fibsem_maestro.core.beam_shift import BeamShift
from fibsem_maestro.core.beam_type import BeamType
from fibsem_maestro.core.lens_alignment import LensAlignment
from fibsem_maestro.core.scanning_area import ScanningArea
from fibsem_maestro.core.source_tilt import SourceTilt
from fibsem_maestro.core.stigmator import Stigmator
from fibsem_maestro.logging.text.text_logger import TextLogger
from fibsem_maestro.microscope.abstract_control.beam_control import BeamControl
from fibsem_maestro.microscope.error import MicroscopeError
from fibsem_maestro.microscope.internal_props import InternalPropertiesRegistry

BeamT = TypeVar(
    "BeamT",
    ElectronBeamAs,
    IonBeamAs,
)


class AutoscriptBeamControl(BeamControl, Generic[BeamT]):
    def __init__(
        self,
        autoscript_microscope: SdbMicroscopeClient,
        internal_properties: InternalPropertiesRegistry,
        txt_log: TextLogger,
    ):
        self._microscope = autoscript_microscope
        self._internal_properties = internal_properties
        self._txt_log = txt_log

        self._scanning_area: ScanningArea | None = None
        self._line_integration = 1
        self._vertical_field_width: float | None = (
            None  # dummy var for resolution calculation
        )
        self._extended_resolution: tuple[int, int] | None = (
            None  # extended resolution is set only if the required resolution is not standard
        )
        self._standard_resolutions = (
            [1024, 884],
            [1536, 1024],
            [2048, 1768],
            [3072, 2048],
            [4096, 3536],
            [512, 442],
            [6144, 4096],
            [768, 512],
        )  # available resolutions supported in standard mode

    @property
    @abstractmethod
    def _beam(self) -> BeamT:
        pass

    @property
    @abstractmethod
    def _beam_type(self) -> BeamType:
        pass

    @property
    @abstractmethod
    def _modality(self) -> str:
        pass

    @abstractmethod
    def select_modality(self):
        """
        This method is used to switch the microscope's modality between the Electron Beam (eb) mode and the Ion Beam
        (ib) mode. The selection of the modality will have an impact on starting and stopping the acquisition,
        grab and get image, and on the selected detector.

        The Electron Beam mode is always in Quad 1, while the Ion Beam mode is always in Quad 2.
        """
        pass

    @property
    def stigmator(self) -> Stigmator:
        value = Stigmator.from_point_autoscript(self._beam.stigmator.value)
        self._txt_log.debug(f"Getting stigmator ({self._modality}): {value}.")
        return value

    @stigmator.setter
    def stigmator(self, value: Stigmator) -> None:
        self._txt_log.debug(f"Setting stigmator ({self._modality}): {value}.")
        self._beam.stigmator.value = value.to_point_autoscript()

    @property
    def beam_shift(self) -> BeamShift:
        value = BeamShift.from_point_autoscript(self._beam.beam_shift.value)
        self._txt_log.debug(f"Getting beam shift ({self._modality}): {value}.")
        return value

    @beam_shift.setter
    def beam_shift(self, value: BeamShift) -> None:
        self._txt_log.debug(f"Setting beam shift ({self._modality}): {value}.")
        self._beam.beam_shift.value = value.to_point_autoscript()

    @property
    def detector_contrast(self) -> float:
        self.select_modality()
        value = self._microscope.detector.contrast.value
        self._txt_log.debug(f"Getting detector contrast ({self._modality}): {value}.")
        return value

    @detector_contrast.setter
    def detector_contrast(self, value: float) -> None:
        self.select_modality()
        self._txt_log.debug(
            f"Setting detector contrast ({self._modality}) to: {value}."
        )
        self._microscope.detector.contrast.value = value

    @property
    def detector_brightness(self) -> float:
        self.select_modality()
        value = self._microscope.detector.brightness.value
        self._txt_log.debug(f"Getting detector brightness ({self._modality}): {value}.")
        return value

    @detector_brightness.setter
    def detector_brightness(self, value: float) -> None:
        self.select_modality()
        self._txt_log.debug(
            f"Setting detector brightness ({self._modality}) to: {value}."
        )
        self._microscope.detector.brightness.value = value

    def blank(self):
        self.select_modality()
        self._txt_log.debug(f"Blanking beam ({self._modality}).")
        self._beam.blank()

    def unblank(self):
        self.select_modality()
        self._txt_log.debug(f"Unblanking beam ({self._modality}).")
        self._beam.unblank()

    def start_acquisition(self):
        self.select_modality()
        self._txt_log.debug(f"Starting acquisition ({self._modality}).")
        self._microscope.imaging.start_acquisition()

    def stop_acquisition(self):
        self.select_modality()
        self._txt_log.debug(f"Stopping acquisition ({self._modality}).")
        self._microscope.imaging.stop_acquisition()

    @property
    def line_integration(self) -> int:
        self._txt_log.debug(
            f"Getting line integration ({self._modality}): {self._line_integration}."
        )
        return self._line_integration

    @line_integration.setter
    def line_integration(self, value: int) -> None:
        self._txt_log.debug(f"Setting line integration to ({self._modality}): {value}.")
        self._line_integration = value

    @property
    def dwell_time(self) -> float:
        value = self._beam.scanning.dwell_time.value
        self._txt_log.debug(f"Getting dwell time ({self._modality}): {value}.")
        return value

    @dwell_time.setter
    def dwell_time(self, value: float) -> None:
        self._txt_log.debug(f"Setting dwell time to ({self._modality}): {value}.")
        self._beam.scanning.dwell_time.value = value

    @property
    def bit_depth(self) -> int:
        value = self._beam.scanning.bit_depth
        self._txt_log.debug(f"Getting bit depth ({self._modality}): {value}.")
        return value

    @bit_depth.setter
    def bit_depth(self, value: int) -> None:
        if value not in (8, 16):
            raise MicroscopeError(f"Bit depth must be 8 or 16, not {value}.")
        self._txt_log.debug(f"Setting bit depth to ({self._modality}): {value}.")
        self._beam.scanning.bit_depth = value

    @property
    def resolution(self) -> tuple[int, int]:
        if self._extended_resolution is None:
            x, y = (
                self._beam.scanning.resolution.width,
                self._beam.scanning.resolution.height,
            )
            self._txt_log.debug(
                f"Getting standard resolution ({self._modality}): {x}, {y}."
            )
            return x, y

        self._txt_log.debug(
            f"Getting extended resolution ({self._modality}): {self._extended_resolution}."
        )
        return self._extended_resolution

    @resolution.setter
    def resolution(self, value: tuple[int, int]) -> None:
        resolution = f"{value[0]}x{value[1]}"
        for r in self._standard_resolutions:
            if value[0] == r[0] and value[1] == r[1]:
                self._txt_log.debug(
                    f"Setting standard resolution to ({self._modality}): {resolution}."
                )
                self._beam.scanning.resolution.value = resolution
                return
        self._txt_log.debug(
            f"Setting extended resolution to ({self._modality}): {resolution}."
        )
        self._extended_resolution = value

    @property
    def extended_resolution(self) -> tuple[int, int] | None:
        return self._extended_resolution

    @property
    def horizontal_field_width(self) -> float:
        value = self._beam.horizontal_field_width.value * 1e9  # m -> nm
        self._txt_log.debug(
            f"Getting horizontal field width ({self._modality}): {value}."
        )
        return value

    @horizontal_field_width.setter
    def horizontal_field_width(self, value: float) -> None:
        self._txt_log.debug(
            f"Setting horizontal field width to ({self._modality}): {value}."
        )
        self._beam.horizontal_field_width.value = value * 1e-9  # nm -> m

    @property
    def vertical_field_width(self) -> float:
        if self._vertical_field_width is None:
            self._vertical_field_width = (
                self.horizontal_field_width * self.resolution[1] / self.resolution[0]
            )
            self._txt_log.info(
                "Vertical field width was not set. Calculating from resolution."
            )

        value = self._vertical_field_width
        self._txt_log.debug(
            f"Getting dummy vertical field width ({self._modality}): {value}."
        )
        return value

    @vertical_field_width.setter
    def vertical_field_width(self, value: float) -> None:
        self._txt_log.debug(
            f"Setting dummy vertical field width to ({self._modality}): {value}."
        )
        self._vertical_field_width = value

    @property
    def pixel_size(self) -> float:
        value = self.horizontal_field_width / self.resolution[0]
        self._txt_log.debug(f"Getting pixel size ({self._modality}): {value}.")
        return value

    @pixel_size.setter
    def pixel_size(self, value: float) -> None:
        # it is not possible to set pixel size as property of the microscope, but it is needed for resolution calculation
        extended_res_i_x = int(self.horizontal_field_width / value)
        extended_res_i_y = int(self.vertical_field_width / value)

        extended_res = f"{extended_res_i_x}x{extended_res_i_y}"
        self._txt_log.info(f"Extended resolution set to: {extended_res}.")
        self.resolution = (extended_res_i_x, extended_res_i_y)

    @property
    def scan_rotation(self) -> float:
        value = self._beam.scanning.rotation.value
        self._txt_log.debug(f"Getting scanning rotation ({self._modality}): {value}.")
        return value

    @scan_rotation.setter
    def scan_rotation(self, value: float) -> None:
        self._txt_log.debug(f"Setting scanning rotation ({self._modality}): {value}.")
        self._beam.scanning.rotation.value = value

    @property
    def scanning_area(self) -> ScanningArea | None:
        self._txt_log.debug(
            f"Getting scanning area ({self._modality}): {self._scanning_area}."
        )
        return self._scanning_area

    @scanning_area.setter
    def scanning_area(self, value: ScanningArea | None) -> None:
        # copy dwell and resolution to reduced area scanning mode
        backup_dwell = self.dwell_time
        backup_res = self.resolution

        if (
            value is None
            or (value.height == 1 and value.width == 1)
            or value.height == 0
            or value.width == 0
        ):  # scanning area = FoV or 0
            self._txt_log.debug(f"Disabling scanning area ({self._modality}).")
            self._beam.scanning.mode.set_full_frame()  # used for acquisition started by start_acquisition()
            self._scanning_area = None
        else:
            self._txt_log.debug(
                f"Setting scanning area to ({self._modality}): {value}."
            )
            # used for acquisition started by start_acquisition()
            self._beam.scanning.mode.set_reduced_area(
                left=value.origin.x,
                top=value.origin.y,
                width=value.width,
                height=value.height,
            )
            self._scanning_area = value

        self.dwell_time = backup_dwell
        self.resolution = backup_res

    @property
    def minimal_dwell(self) -> float:
        # in nm
        return 25.0

    def internal(self, name: str) -> Any:
        property = self._internal_properties.get(name)
        value = property.get()
        self._txt_log.debug(
            f"Getting internal property '{name}' ({self._modality}): {value}."
        )
        return value

    def set_internal(self, name: str, value: Any) -> Any:
        self._txt_log.debug(
            f"Setting internal property '{name}' ({self._modality}): {value}."
        )
        property = self._internal_properties.get(name)
        property.set(value)

    @property
    def internal_prop_names(self) -> list[str]:
        return self._internal_properties.allowed()


class AutoscriptElectronBeamControl(AutoscriptBeamControl[ElectronBeamAs]):
    @property
    def _beam(self) -> ElectronBeamAs:
        return self._microscope.beams.electron_beam

    @property
    def _beam_type(self) -> BeamType:
        return BeamType.ELECTRON

    @property
    def _modality(self) -> str:
        return "eb"

    def select_modality(self) -> None:
        self._microscope.imaging.set_active_view(1)
        self._microscope.imaging.set_active_device(ImagingDevice.ELECTRON_BEAM)

    @property
    def working_distance(self):
        wd = self._beam.working_distance.value
        self._txt_log.debug(f"Getting working distance ({self._modality}): {wd}.")
        return wd

    @working_distance.setter
    def working_distance(self, value: float):
        self._txt_log.debug(f"Setting working distance ({self._modality}): {value}.")
        self._beam.working_distance.set_value_no_degauss(value)

    @property
    def lens_alignment(self) -> LensAlignment:
        value = LensAlignment.from_point_autoscript(self._beam.lens_alignment.value)
        self._txt_log.debug(f"Getting lens alignment ({self._modality}): {value}.")
        return value

    @lens_alignment.setter
    def lens_alignment(self, value: LensAlignment):
        self._txt_log.debug(f"Setting lens alignment ({self._modality}): {value}.")
        self._beam.lens_alignment.value = value.to_point_autoscript()

    @property
    def source_tilt(self) -> SourceTilt:
        self.select_modality()
        value = SourceTilt.from_point_autoscript(self._beam.source_tilt.value)
        self._txt_log.debug(f"Getting source tilt ({self._modality}): {value}.")
        return value

    @source_tilt.setter
    def source_tilt(self, value: SourceTilt) -> None:
        """Set the source tilt"""
        self.select_modality()
        self._txt_log.debug(f"Setting source tilt ({self._modality}) to: {value}.")
        self._beam.source_tilt.value = value.to_point_autoscript()

    @property
    def beam_shift_to_stage_move(self) -> tuple[int, int] | None:
        return (-1, -1)

    @property
    def image_to_beam_shift(self) -> tuple[int, int] | None:
        return (-1, 1)

    def limits(self, var: str) -> tuple[float, float]:
        match var:
            case "working_distance":
                return (0.0005, 0.07)
            case "stigmator_x":
                return (-0.99, 0.88)
            case "stigmator_y":
                return (-0.99, 0.77)
            case "lens_alignment_x":
                return (-0.00072005208, 0.00069791667)
            case "lens_alignment_y":
                return (-0.00069140625, 0.00068945312)
            case _:
                raise MicroscopeError(f"{var} is not valid microscope variable")


class AutoscriptIonBeamControl(AutoscriptBeamControl[IonBeamAs]):
    @property
    def _beam(self) -> IonBeamAs:
        return self._microscope.beams.ion_beam

    @property
    def _beam_type(self) -> BeamType:
        return BeamType.ION

    @property
    def _modality(self) -> str:
        return "ib"

    def select_modality(self) -> None:
        self._microscope.imaging.set_active_view(2)
        self._microscope.imaging.set_active_device(ImagingDevice.ION_BEAM)

    @property
    def working_distance(self):
        wd = self._beam.working_distance.value
        self._txt_log.debug(f"Getting working distance ({self._modality}): {wd}.")
        return wd

    @working_distance.setter
    def working_distance(self, value: float):
        self._txt_log.debug(f"Setting working distance ({self._modality}): {value}.")
        self._beam.working_distance.value = value

    @property
    def lens_alignment(self) -> LensAlignment:
        raise MicroscopeError("Lens alignment is not defined for an ion beam.")

    @lens_alignment.setter
    def lens_alignment(self, value: LensAlignment):
        _ = value
        raise MicroscopeError("Lens alignment is not defined for an ion beam.")

    @property
    def source_tilt(self) -> SourceTilt:
        raise MicroscopeError("Source tilt is not defined for an ion beam.")

    @source_tilt.setter
    def source_tilt(self, value: SourceTilt) -> None:
        _ = value
        raise MicroscopeError("Source tilt is not defined for an ion beam.")

    @property
    def beam_shift_to_stage_move(self) -> tuple[int, int] | None:
        return None

    @property
    def image_to_beam_shift(self) -> tuple[int, int] | None:
        return (-1, 1)

    def limits(self, var: str) -> tuple[float, float]:
        raise MicroscopeError(f"{var} is not valid microscope variable")
