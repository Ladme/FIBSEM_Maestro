# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

import cv2
from scipy import ndimage  # type: ignore

from fibsem_maestro.core.action import Action
from fibsem_maestro.core.area import NMArea, RelativeArea
from fibsem_maestro.core.beam_shift import BeamShift
from fibsem_maestro.core.image import Image, Image8Bit
from fibsem_maestro.core.point import NMPoint
from fibsem_maestro.core.resolution import Resolution
from fibsem_maestro.drift_correction.error import DriftCorrectionError
from fibsem_maestro.drift_correction.template_matching_helpers import (
    ShiftsCollection,
    TemplateMatchResult,
)
from fibsem_maestro.imaging.imaging import Imaging
from fibsem_maestro.logging.image.image_logger import ImageLogger
from fibsem_maestro.logging.text.text_logger import TextLogger
from fibsem_maestro.microscope.microscope import Microscope
from fibsem_maestro.settings.template_matching_settings import TemplateMatchingSettings
from fibsem_maestro.store.image.image_store import ImageStore
from fibsem_maestro.store.props.props_store import PropsStore


class TemplateMatchingDriftCorrection(Action):
    def __init__(
        self,
        microscope: Microscope,
        settings: TemplateMatchingSettings,
        imaging: Imaging,
        props_store: PropsStore,
        image_store: ImageStore[Image8Bit],
        txt_log: TextLogger,
        img_log: ImageLogger,
    ):
        self._microscope = microscope
        self._settings = settings
        self._props_store = props_store
        self._image_store = image_store
        self._txt_log = txt_log
        self._img_log = img_log
        self._imaging = imaging

        self._template_matching_results = []

    def create_templates(self) -> None:
        if len(self._settings.areas) == 0:
            raise DriftCorrectionError("No template matching areas defined.")

        # grab an image using the specified microscope properties
        self.set_properties()
        self._txt_log.info("Acquiring template image.")
        template_image = self._microscope.beam.grab_frame()

        for i, area in enumerate(self._settings.areas):
            self._save_template(template_image.crop(area), i)

    def correct_drift(self) -> None:
        # grab image for drift correction
        self.set_properties()
        self._txt_log.info("Acquiring drift correction image.")
        image = self._microscope.beam.grab_frame().to_8bit()

        # calculate shifts for each template
        shifts = self._calculate_shifts(image)

        # convert image shifts to beam shift
        beam_shift = self._shifts_to_beam_shift(shifts)

        # apply beam shift to correct the drift and update the drift correction parameters
        self._microscope.add_beam_shift_with_verification(beam_shift)
        self.save_properties(self._props_store.next)

        # load imaging parameters to the microscope, apply beam shift,
        # and update the imaging parameters for the current slice
        self._imaging.set_properties()
        self._microscope.add_beam_shift_with_verification(beam_shift)
        # TODO: check that beam shift and stage position are saved and print warning if they are not
        self._imaging.save_properties()

    def set_properties(self, store: PropsStore | None = None) -> None:
        """
        Configure the electron microscope with settings from the properties file.
        """
        # default: current frame
        store = store or self._props_store

        # select the beam used for imaging
        self._microscope.set_beam(self._settings.beam_type)

        # read properties
        self._txt_log.debug(
            "Loading microscope properties for template matching drift correction."
        )
        props = store.read(str(self._settings.properties_file))

        # set properties to the microscope
        self._microscope.set_properties(props, beam=self._settings.beam_type)

    def save_properties(self, store: PropsStore | None = None) -> None:
        """
        Save microscope properties for drift correction.
        """
        # default: current frame
        store = store or self._props_store

        self._txt_log.debug(
            "Saving microscope properties for template matching drift correction."
        )

        props = self._microscope.collect_properties(
            self._settings.properties_to_collect
        )

        store.write(str(self._settings.properties_file), props)

    def _calculate_shifts(self, image: Image8Bit) -> ShiftsCollection:
        shifts_x: list[float] = []
        shifts_y: list[float] = []
        for i, area in enumerate(self._settings.areas):
            # load the template from file
            template = self._load_template(i)

            # select the area for template matching from the provided image
            cropped = image.crop_with_correction_margin(
                area, self._settings.correction_margin
            )

            # calculate the match between template and the cropped image
            template_match = TemplateMatchingDriftCorrection._calculate_match(
                template, cropped, self._settings.blur
            )

            # convert shift to nm
            dx_nm = template_match.dx * cropped.pixel_size
            dy_nm = template_match.dy * cropped.pixel_size

            self._txt_log.info(
                f"Drift correction for template {i}: {dx_nm},{dy_nm}. Confidence: {template_match.confidence}."
            )

            # ignore the calculated shift if the confidence is too low
            if template_match.confidence < self._settings.min_confidence:
                self._txt_log.warning(
                    f"Template match confidence ({template_match.confidence}) is too low (limit: {self._settings.min_confidence}). Ignoring."
                )
                # copy the current template to the next slice
                self._copy_template(i, self._image_store, self._image_store.next)
                continue

            shifts_x.append(dx_nm)
            shifts_y.append(dy_nm)

            # use the new acquired image as template for the next slice
            slice = self._image_store.slice or 0
            if slice > 0 and slice % self._settings.rescan == 0:
                self._txt_log.debug(
                    f"Updating template image {i} for slice {slice + 1}."
                )

                new_template = image.crop(
                    # select the correct region for template matching
                    self._shift_area(
                        area, (dx_nm, dy_nm), image.resolution, image.pixel_size
                    )
                )

                self._image_store.next.write(
                    self._construct_template_name(i), new_template
                )
            else:
                # copy the current template to the next slice
                self._copy_template(i, self._image_store, self._image_store.next)

        return ShiftsCollection(dx=shifts_x, dy=shifts_y)

    @staticmethod
    def _calculate_match(
        template: Image8Bit, image: Image8Bit, blur: int
    ) -> TemplateMatchResult:
        # blur the images, if requested
        if blur > 0:
            image = Image8Bit(
                ndimage.gaussian_filter(image, sigma=blur), image.pixel_size
            )
            template = Image8Bit(
                ndimage.gaussian_filter(template, sigma=blur), template.pixel_size
            )

        heatmap = cv2.matchTemplate(
            image,
            template,
            cv2.TM_CCOEFF_NORMED,
        )

        _, max_val, _, max_loc = cv2.minMaxLoc(heatmap)

        best_x, best_y = max_loc

        # center of correlation map
        center_x = heatmap.shape[1] // 2
        center_y = heatmap.shape[0] // 2

        dx = best_x - center_x  # horizontal shift
        dy = best_y - center_y  # vertical shift

        return TemplateMatchResult(
            dx=dx,
            dy=dy,
            confidence=float(max_val),
            heatmap=heatmap,
        )

    def _shifts_to_beam_shift(self, shifts: ShiftsCollection) -> BeamShift:
        if (mean_shift := shifts.get_mean_shift()) is None:
            if self._settings.stop_acquisition_at_failure:
                raise DriftCorrectionError(
                    f"Confidence of all templates is below the limit of {self._settings.min_confidence}. Cannot perform drift correction."
                )

            self._txt_log.warning(
                f"Confidence of all templates is below the limit of {self._settings.min_confidence}. Cannot perform drift correction."
            )
            return BeamShift(x=0.0, y=0.0)

        return BeamShift(
            x=mean_shift[0] * self._microscope.beam.image_to_beam_shift[0],
            y=mean_shift[1] * self._microscope.beam.image_to_beam_shift[1],
        )

    def _shift_area(
        self,
        area: RelativeArea,
        shift_nm: tuple[float, float],
        resolution: Resolution,
        pixel_size: float,
    ) -> RelativeArea:
        area_nm = area.to_nanometers(resolution, pixel_size)
        shifted_area_nm = NMArea(
            origin=NMPoint(
                x=area_nm.origin.x + shift_nm[0], y=area_nm.origin.y + shift_nm[1]
            ),
            width=area_nm.width,
            height=area_nm.height,
        )

        return shifted_area_nm.to_relative(resolution, pixel_size)

    def _save_template(
        self,
        template: Image,
        index: int,
        image_store: ImageStore[Image8Bit] | None = None,
    ) -> None:
        # default: current slice
        store = image_store or self._image_store

        self._txt_log.debug(f"Saving template {index}.")
        store.write(self._construct_template_name(index), template.to_8bit())

    def _load_template(
        self, index: int, image_store: ImageStore[Image8Bit] | None = None
    ) -> Image8Bit:
        # default: current slice
        store = image_store or self._image_store

        self._txt_log.debug(f"Loading template {index}.")
        return store.read(self._construct_template_name(index))

    def _copy_template(
        self, index: int, src: ImageStore[Image8Bit], dest: ImageStore[Image8Bit]
    ) -> None:
        image = src.read(self._construct_template_name(index))
        dest.write(self._construct_template_name(index), image)

    def _construct_template_name(self, index: int) -> str:
        return f"template_drift_corr_{index}.tif"
