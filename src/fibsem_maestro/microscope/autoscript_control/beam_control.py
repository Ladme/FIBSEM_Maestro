# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from abc import abstractmethod
from pathlib import Path
from typing import Any, Generic, TypeVar

from autoscript_sdb_microscope_client.enumerations import ImageFileFormat, ImagingDevice
from autoscript_sdb_microscope_client.sdb_microscope.beams._electron_beam import (
    ElectronBeam as ElectronBeamAs,
)
from autoscript_sdb_microscope_client.sdb_microscope.beams._ion_beam import (
    IonBeam as IonBeamAs,
)
from autoscript_sdb_microscope_client.sdb_microscope_client import SdbMicroscopeClient
from autoscript_sdb_microscope_client.structures import AdornedImage, GrabFrameSettings

from fibsem_maestro.core.area import RelativeArea
from fibsem_maestro.core.beam_shift import BeamShift
from fibsem_maestro.core.beam_type import BeamType
from fibsem_maestro.core.image import Image
from fibsem_maestro.core.lens_alignment import LensAlignment
from fibsem_maestro.core.resolution import Resolution
from fibsem_maestro.core.source_tilt import SourceTilt
from fibsem_maestro.core.stigmator import Stigmator
from fibsem_maestro.logging.text.text_logger import TextLogger
from fibsem_maestro.microscope.abstract_control.beam_control import BeamControl
from fibsem_maestro.microscope.autoscript_control.manufacturer_props import (
    AutoscriptManufacturerPropertiesRegistry,
)
from fibsem_maestro.microscope.error import MicroscopeError

BeamT = TypeVar(
    "BeamT",
    ElectronBeamAs,
    IonBeamAs,
)


class AutoscriptBeamControl(BeamControl, Generic[BeamT]):
    def __init__(
        self,
        autoscript_microscope: SdbMicroscopeClient,
        txt_log: TextLogger,
    ):
        self._microscope = autoscript_microscope
        self._manufacturer_properties = AutoscriptManufacturerPropertiesRegistry(
            self._beam
        )
        self._txt_log = txt_log

        self._extended_resolution: Resolution | None = (
            None  # extended resolution is set only if the required resolution is not standard
        )
        self._standard_resolutions = (
            Resolution(1024, 884),
            Resolution(1536, 1024),
            Resolution(2048, 1768),
            Resolution(3072, 2048),
            Resolution(4096, 3536),
            Resolution(512, 442),
            Resolution(6144, 4096),
            Resolution(768, 512),
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

    def get_image(self, crop_to_scanning_area: bool = False) -> Image:
        self.select_modality()
        self._txt_log.debug(f"Getting an image ({self._modality}).")
        image = Image.from_autoscript(self._microscope.imaging.get_image())

        if crop_to_scanning_area and not self.scanning_area.is_full_frame():
            return image.crop(self.scanning_area)

        return image

    def grab_frame(self, file_name: Path | None = None) -> Image:
        self.select_modality()
        self._txt_log.debug(f"Grabbing frame ({self._modality}).")

        imaging_settings = GrabFrameSettings(
            line_integration=self.line_integration,
            bit_depth=self.bit_depth,
            resolution=str(self.resolution),
            dwell_time=self.dwell_time,
        )

        if not self.scanning_area.is_full_frame():
            imaging_settings.reduced_area = self.scanning_area.to_autoscript()

        self._txt_log.info(
            "Acquiring image "
            f"(bit_depth={self.bit_depth}, "
            f"resolution={self.resolution}, "
            f"pixel_size={self.pixel_size}, "
            f"line_integration={self.line_integration}, "
            f"scanning_area={self.scanning_area}, "
            f"dwell_time={self.dwell_time}, "
            f"working_distance={self.working_distance})"
        )

        try:
            grabbed_image = self._microscope.imaging.grab_frame(imaging_settings)
            self._txt_log.info("Image grabbed.")
            if file_name is not None:
                grabbed_image.save(str(file_name))
        # the `grab_frame` method can fail if the image is too large
        # if that happens, we grab the image to disk and then load it to memory
        except Exception as e:
            self._txt_log.warning(f"Grab frame error: {e} Grabbing image to disk.")

            if file_name is None:
                file_name = Path("temp.tif")
                self._txt_log.warning(
                    f"File name not provided. The image will be saved as '{str(file_name)}'."
                )

            self._microscope.imaging.grab_frame_to_disk(
                str(file_name), ImageFileFormat.TIFF, imaging_settings
            )
            self._txt_log.info("Image grabbed to disk.")
            grabbed_image = AdornedImage.load(str(file_name))

        return Image.from_autoscript(grabbed_image)

    @property
    def line_integration(self) -> int:
        li = self._beam.scanning.line_integration
        self._txt_log.debug(f"Getting line integration ({self._modality}): {li}.")
        return li

    @line_integration.setter
    def line_integration(self, value: int) -> None:
        self._txt_log.debug(f"Setting line integration to ({self._modality}): {value}.")
        self._beam.scanning.line_integration = value

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
    def resolution(self) -> Resolution:
        if self._extended_resolution is None:
            x, y = (
                self._beam.scanning.resolution.width,
                self._beam.scanning.resolution.height,
            )
            self._txt_log.debug(
                f"Getting standard resolution ({self._modality}): {x}, {y}."
            )
            return Resolution(x, y)

        self._txt_log.debug(
            f"Getting extended resolution ({self._modality}): {self._extended_resolution}."
        )
        return self._extended_resolution

    @resolution.setter
    def resolution(self, value: Resolution) -> None:
        resolution = str(value)
        if value in self._standard_resolutions:
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
    def extended_resolution(self) -> Resolution | None:
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
        value = (
            self.horizontal_field_width * self.resolution.height / self.resolution.width
        )
        self._txt_log.debug(
            f"Getting vertical field width ({self._modality}): {value}."
        )

        return value

    @vertical_field_width.setter
    def vertical_field_width(self, value: float) -> None:
        # change the resolution of the image so that the requested vertical field width is achieved
        # without changing the pixel size
        pixel_size = self.pixel_size
        self.resolution = Resolution(self.resolution.width, int(value / pixel_size))
        self._txt_log.info(
            f"Extended resolution set to: {str(self.resolution)} (via setting vertical field width)."
        )

    @property
    def pixel_size(self) -> float:
        value = self.horizontal_field_width / self.resolution.width
        self._txt_log.debug(f"Getting pixel size ({self._modality}): {value}.")
        return value

    @pixel_size.setter
    def pixel_size(self, value: float) -> None:
        # change the resolution of the image so that the pixel size matches the provided value
        # but the field width is not changed
        self.resolution = Resolution(
            int(self.horizontal_field_width / value),
            int(self.vertical_field_width / value),
        )
        self._txt_log.info(
            f"Extended resolution set to: {str(self.resolution)} (via setting pixel size)."
        )

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
    def scanning_area(self) -> RelativeArea:
        area = RelativeArea.from_autoscript(self._beam.scanning.mode.reduced_area.value)
        self._txt_log.debug(f"Getting scanning area ({self._modality}): {area}.")
        return area

    @scanning_area.setter
    def scanning_area(self, value: RelativeArea) -> None:
        # copy dwell and resolution to reduced area scanning mode
        backup_dwell = self.dwell_time
        backup_res = self.resolution

        if value.is_full_frame():
            self._txt_log.debug(f"Disabling scanning area ({self._modality}).")
            self._beam.scanning.mode.reduced_area.value = value.to_autoscript()
            self._beam.scanning.mode.set_full_frame()  # used for acquisition started by start_acquisition()
        else:
            self._txt_log.debug(f"Setting scanning area ({self._modality}): {value}.")
            # used for acquisition started by start_acquisition()
            self._beam.scanning.mode.set_reduced_area(
                left=value.origin.x,
                top=value.origin.y,
                width=value.width,
                height=value.height,
            )

        self.dwell_time = backup_dwell
        self.resolution = backup_res

    @property
    def minimal_dwell(self) -> float:
        # in s
        return 25e-9

    def manufacturer_prop(self, name: str) -> Any:
        property = self._manufacturer_properties.get(name)
        value = property.get()
        self._txt_log.debug(
            f"Getting manufacturer property '{name}' ({self._modality}): {value}."
        )
        return value

    def set_manufacturer_prop(self, name: str, value: Any) -> None:
        self._txt_log.debug(
            f"Setting manufacturer property '{name}' ({self._modality}): {value}."
        )
        property = self._manufacturer_properties.get(name)
        property.set(value)

    @property
    def manufacturer_prop_names(self) -> list[str]:
        return self._manufacturer_properties.allowed()

    @property
    def txt_log(self) -> TextLogger:
        return self._txt_log


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
        wd = self._beam.working_distance.value * 1e9  # m -> nm
        self._txt_log.debug(f"Getting working distance ({self._modality}): {wd}.")
        return wd

    @working_distance.setter
    def working_distance(self, value: float):
        self._txt_log.debug(f"Setting working distance ({self._modality}): {value}.")
        self._beam.working_distance.set_value_no_degauss(value * 1e-9)  # nm -> m

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
        self.select_modality()
        self._txt_log.debug(f"Setting source tilt ({self._modality}): {value}.")
        self._beam.source_tilt.value = value.to_point_autoscript()

    @property
    def beam_shift_to_stage_move(self) -> tuple[int, int]:
        return (-1, -1)

    @property
    def image_to_beam_shift(self) -> tuple[int, int]:
        return (-1, 1)

    def limits(self, var: str) -> tuple[float, float]:
        # TODO: maybe this should not be hardcoded?
        match var:
            case "working_distance":
                return (500_000.0, 70_000_000.0)
            case "stigmator_x":
                return (-0.99, 0.88)
            case "stigmator_y":
                return (-0.99, 0.77)
            case "lens_alignment_x":
                return (-720_052.0, 697_917.0)
            case "lens_alignment_y":
                return (-691_406.25, 689_453.125)
            case _:
                raise MicroscopeError(
                    f"{var} is not a valid microscope variable for an electron beam"
                )


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
        wd = self._beam.working_distance.value * 1e9  # m -> nm
        self._txt_log.debug(f"Getting working distance ({self._modality}): {wd}.")
        return wd

    @working_distance.setter
    def working_distance(self, value: float):
        self._txt_log.debug(f"Setting working distance ({self._modality}): {value}.")
        self._beam.working_distance.value = value * 1e-9  # nm -> m

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
    def beam_shift_to_stage_move(self) -> tuple[int, int]:
        return (0, 0)

    @property
    def image_to_beam_shift(self) -> tuple[int, int]:
        return (-1, 1)

    def limits(self, var: str) -> tuple[float, float]:
        raise MicroscopeError(f"{var} is not valid microscope variable for an ion beam")
