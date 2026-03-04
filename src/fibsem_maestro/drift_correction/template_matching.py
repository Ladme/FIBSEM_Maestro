# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

import shutil
from pathlib import Path

import cv2
import numpy as np
from scipy import ndimage  # type: ignore
from tifffile import TiffFile

from fibsem_maestro.core.action import Action
from fibsem_maestro.core.area import RelativeArea
from fibsem_maestro.core.beam_shift import BeamShift
from fibsem_maestro.core.format import ImageFormat
from fibsem_maestro.core.image import Image, Image8Bit
from fibsem_maestro.drift_correction.error import DriftCorrectionError
from fibsem_maestro.drift_correction.template_match_result import TemplateMatchResult
from fibsem_maestro.imaging.imaging import Imaging
from fibsem_maestro.logging.context import LogContext
from fibsem_maestro.logging.image.image_logger import ImageLogger
from fibsem_maestro.logging.text.text_logger import TextLogger
from fibsem_maestro.microscope.microscope import Microscope
from fibsem_maestro.settings.global_properties import GlobalProperties
from fibsem_maestro.settings.template_matching_settings import TemplateMatchingSettings


class TemplateMatchingDriftCorrection(Action):
    def __init__(
        self,
        microscope: Microscope,
        settings: TemplateMatchingSettings,
        imaging: Imaging,
        log_ctx: LogContext,
        txt_log: TextLogger,
        img_log: ImageLogger,
    ):
        self._microscope = microscope
        self._settings = settings
        self._log_ctx = log_ctx
        self._txt_log = txt_log
        self._img_log = img_log
        self._imaging = imaging

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
        shifts_x: list[float] = []
        shifts_y: list[float] = []
        for i, area in enumerate(self._settings.areas):
            shift = self._calculate_shift(image, area, i)

            if shift is None:
                continue

            shifts_x.append(shift[0])
            shifts_y.append(shift[1])

        # make sure that at least one template match had sufficient confidence
        if len(shifts_x) == 0:
            if self._settings.stop_acquisition_at_failure:
                raise DriftCorrectionError(
                    f"Confidence of all templates is below the limit of {self._settings.min_confidence}. Cannot perform drift correction."
                )

            self._txt_log.warning(
                f"Confidence of all templates is below the limit of {self._settings.min_confidence}. Cannot perform drift correction."
            )
            beam_shift = BeamShift(x=0.0, y=0.0)
        else:
            # get the mean image shift and convert to beam shift
            beam_shift_x = (
                float(np.mean(shifts_x)) * self._microscope.beam.image_to_beam_shift[0]
            )
            beam_shift_y = (
                float(np.mean(shifts_y)) * self._microscope.beam.image_to_beam_shift[1]
            )
            beam_shift = BeamShift(x=beam_shift_x, y=beam_shift_y)

        next_slice = (self._log_ctx.slice_ctx.current_slice or 0) + 1
        # apply beam shift to correct the drift and update the drift correction parameters
        self._microscope.add_beam_shift_with_verification(beam_shift)
        # update templates - we need to do this AFTER adding the beam shift
        # otherwise newly scanned templates may already compensate for the drift in the next slice
        self._update_templates()
        self.save_properties(slice=next_slice)

        # load imaging parameters to the microscope, apply beam shift,
        # and update the imaging parameters for the current slice
        self._imaging.set_properties()
        self._microscope.add_beam_shift_with_verification(beam_shift)
        # TODO: check that beam shift and stage position are saved and print warning if they are not
        self._imaging.save_properties()

    def set_properties(self) -> None:
        """
        Set the microscope properties.
        """
        # select the beam used for drift correction imaging
        self._microscope.set_beam(self._settings.beam_type)

        # set properties of the microscope
        properties_file = self._construct_props_path()
        self._txt_log.debug(
            f"Loading microscope properties from {str(properties_file)}."
        )
        props = GlobalProperties.from_file(properties_file)
        self._microscope.set_properties(props, beam=self._settings.beam_type)

    def save_properties(self, slice: int | None = None) -> None:
        """
        Save microscope properties for drift correction into an output YAML file.
        """
        properties_file = self._construct_props_path(slice)
        self._txt_log.debug(f"Saving microscope properties to {str(properties_file)}.")

        props = self._microscope.collect_properties(
            self._settings.properties_to_collect
        )

        props.to_file(properties_file)

    def _calculate_shift(
        self, image: Image8Bit, area: RelativeArea, index: int
    ) -> tuple[float, float] | None:
        # load the template from file
        template = self._load_template(index)

        # select the area for template matching from the acquired image
        cropped = self._select_area(image, area)

        # perform template matching
        template_match = self._template_matching(template, cropped)
        dx_nm = template_match.dx * cropped.pixel_size
        dy_nm = template_match.dy * cropped.pixel_size

        self._txt_log.info(
            f"Drift correction for template {index}: {dx_nm},{dy_nm}. Confidence: {template_match.confidence}."
        )

        # ignore the calculated shift if the confidence is too low
        if template_match.confidence < self._settings.min_confidence:
            self._txt_log.warning(
                f"Template match confidence ({template_match.confidence}) is too low (limit: {self._settings.min_confidence}). Ignoring."
            )
            return None

        return (dx_nm, dy_nm)

    def _select_area(self, image: Image8Bit, area: RelativeArea):
        pixel_size = image.pixel_size
        pixel_area = area.to_pixels(image.resolution)
        correction_margin_px = int(self._settings.correction_margin / pixel_size)

        # pad the image to accomodate the correction_margin
        image_padded = Image8Bit(
            np.pad(image, correction_margin_px, mode="edge"), image.pixel_size
        )

        # select the region for template matching
        return image_padded[
            pixel_area.origin.y : pixel_area.origin.y
            + pixel_area.height
            + 2 * correction_margin_px,
            pixel_area.origin.x : pixel_area.origin.x
            + pixel_area.width
            + 2 * correction_margin_px,
        ]

    def _template_matching(
        self,
        template: Image8Bit,
        image: Image8Bit,
    ) -> TemplateMatchResult:
        # blur the images, if requested
        if (blur := self._settings.blur) > 0:
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

    def _save_template(self, template: Image, index: int) -> None:
        template_path = self._construct_template_path(index)

        # make sure that the directory for storing templates exists
        if not template_path.parent.exists():
            template_path.parent.mkdir(parents=True, exist_ok=True)

        self._txt_log.debug(f"Saving template {index} into {str(template_path)}.")
        template.to_8bit().save(template_path, format=ImageFormat.TIF)

    def _load_template(self, index: int) -> Image8Bit:
        template_path = self._construct_template_path(index)
        self._txt_log.debug(f"Loading template {index} from {str(template_path)}.")
        with TiffFile(template_path) as tiff_file:
            return Image8Bit.from_tiff(tiff_file)

    def _update_templates(self) -> None:
        slice = self._log_ctx.slice_ctx.current_slice or 0
        template_path = self._construct_template_path(0, slice + 1)

        # make sure that the template directory for the next slice exists
        if not template_path.parent.exists():
            template_path.parent.mkdir(parents=True, exist_ok=True)

        if slice > 0 and slice % self._settings.rescan == 0:
            # perform new scan and save the templates
            self._txt_log.info(
                f"Rescanning drift correction templates for slice {slice + 1}."
            )
            image = self._microscope.beam.grab_frame().to_8bit()
            for i, area in enumerate(self._settings.areas):
                image.crop(area).save(
                    self._construct_template_path(i, slice + 1), format=ImageFormat.TIF
                )
        else:
            # continue using the current templates
            for i, area in enumerate(self._settings.areas):
                shutil.copyfile(
                    self._construct_template_path(i),
                    self._construct_template_path(i, slice + 1),
                )

    def _construct_template_path(self, index: int, slice: int | None = None) -> Path:
        return (
            self._log_ctx.slice_dir(slice)
            / self._settings.templates_directory
            / f"drift_correction_template_{index}.tif"
        )

    def _construct_props_path(self, slice: int | None = None) -> Path:
        """
        Construct the path to the microscope properties file.

        The returned path can be used either to load existing microscope properties
        or to save updated properties.

        Returns:
            Path: Path to the microscope properties file.
        """
        return self._log_ctx.slice_dir(slice) / self._settings.properties_file
