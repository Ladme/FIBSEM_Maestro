# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from typing import Any

import cv2
import numpy as np
from numpy.typing import NDArray
from scipy import ndimage  # type: ignore

from fibsem_maestro.core.action import Action
from fibsem_maestro.core.beam_shift import BeamShift
from fibsem_maestro.core.beam_type import BeamType
from fibsem_maestro.core.image import Image, Image8Bit
from fibsem_maestro.core.point import PixelPoint
from fibsem_maestro.drift_correction.error import DriftCorrectionError
from fibsem_maestro.drift_correction.helpers import (
    TemplateMatchResult,
)
from fibsem_maestro.imaging.imaging import Imaging
from fibsem_maestro.logging.image.image_logger import ImageLogger
from fibsem_maestro.logging.image.overlay import RectangleOverlay
from fibsem_maestro.logging.text.text_logger import TextLogger
from fibsem_maestro.microscope.microscope import Microscope
from fibsem_maestro.settings.property_names import PropertyNames
from fibsem_maestro.settings.template_matching_settings import TemplateMatchingSettings
from fibsem_maestro.store.image.image_store import ImageStore
from fibsem_maestro.store.props.props_store import PropsStore


class TemplateMatchingDriftCorrection(Action):
    def __init__(
        self,
        name: str,
        microscope: Microscope,
        settings: TemplateMatchingSettings,
        imagings: list[Imaging],
        props_store: PropsStore,
        image_store: ImageStore[Image8Bit],
        txt_log: TextLogger,
        img_log: ImageLogger,
    ):
        self._name = name
        self._microscope = microscope
        self._settings = settings
        self._props_store = props_store
        self._image_store = image_store
        self._txt_log = txt_log
        self._img_log = img_log
        self._imagings = imagings

    @property
    def name(self) -> str:
        return self._name

    @property
    def name_with_underscores(self) -> str:
        return self._name.replace(" ", "_")

    @property
    def props_file(self) -> str:
        return str(self._settings.properties_file)

    @property
    def props_store(self) -> PropsStore:
        return self._props_store

    @property
    def beam_type(self) -> BeamType:
        return self._settings.beam_type

    @property
    def props_to_collect(self) -> PropertyNames:
        return self._settings.properties_to_collect

    @property
    def microscope(self) -> Microscope:
        return self._microscope

    @property
    def txt_log(self) -> TextLogger:
        return self._txt_log

    def create_templates(self) -> None:
        if len(self._settings.areas) == 0:
            raise DriftCorrectionError("No template matching areas defined.")

        # grab an image using the specified microscope properties
        self.read_and_set_properties()
        self._txt_log.info("Acquiring template image.")
        template_image = self._microscope.beam.grab_frame()

        for i, area in enumerate(self._settings.areas):
            self._save_template(template_image.crop(area), i)

    def correct_drift(self) -> None:
        # grab image for drift correction
        self.read_and_set_properties()
        self._txt_log.info("Acquiring drift correction image.")
        image = self._microscope.beam.grab_frame().to_8bit()

        # perform template matching for each template
        matches = self._get_template_matches(image)

        # log the results of template matching
        self._log_heatmaps(matches)
        self._log_image_shifts(image, matches)

        # get beam shift based on the template matching
        beam_shift = self._matches_to_beam_shift(matches, image.pixel_size)

        # update the templates for the next slice
        self._update_templates(image, matches)

        # add the beam shift to the drift correction parameters for the next slice
        self._txt_log.debug(f"Updating microscope properties for '{self.name}'.")
        props = self.read_properties()
        props.accumulate_property("beam_shift", beam_shift, self.beam_type)
        self.write_properties(props, self._props_store.next)

        # add the beam shift to the imaging parameters for the current slice
        for imaging in self._imagings:
            self._txt_log.debug(f"Updating microscope properties for '{imaging.name}'.")
            props = imaging.read_properties()
            props.accumulate_property("beam_shift", beam_shift, imaging.beam_type)
            imaging.write_properties(props)

    def _get_template_matches(self, image: Image8Bit) -> list[TemplateMatchResult]:
        matches = []
        for i, area in enumerate(self._settings.areas):
            # load the template from file
            template = self._load_template(i)

            # select the area for template matching from the provided image
            cropped = image.crop_with_padding(area, self._settings.correction_margin)

            # calculate the match between template and the cropped image
            matches.append(
                TemplateMatchingDriftCorrection._calculate_match(
                    template, cropped, self._settings.blur
                )
            )

        return matches

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

    def _matches_to_beam_shift(
        self, matches: list[TemplateMatchResult], pixel_size: float
    ) -> BeamShift:
        shifts_x = []
        shifts_y = []
        for i, match in enumerate(matches):
            # convert shift to nm
            dx_nm = match.dx * pixel_size
            dy_nm = match.dy * pixel_size

            self._txt_log.info(
                f"Drift correction for template {i}: {dx_nm},{dy_nm}. Confidence: {match.confidence}."
            )

            # ignore templates for which the template matching confidence was too low
            if match.confidence < self._settings.min_confidence:
                self._txt_log.warning(
                    f"Template match confidence ({match.confidence}) is too low (limit: {self._settings.min_confidence}). Ignoring."
                )
                continue

            shifts_x.append(dx_nm)
            shifts_y.append(dy_nm)

        # check that at least one template had a high enough confidence
        if len(shifts_x) == 0 or len(shifts_y) == 0:
            if self._settings.stop_acquisition_at_failure:
                raise DriftCorrectionError(
                    f"Confidence of all templates is below the limit of {self._settings.min_confidence}. Cannot perform drift correction."
                )

            self._txt_log.warning(
                f"Confidence of all templates is below the limit of {self._settings.min_confidence}. Cannot perform drift correction."
            )
            return BeamShift(x=0.0, y=0.0)

        # calculate average image shift
        mean_shift_x = float(np.mean(shifts_x))
        mean_shift_y = float(np.mean(shifts_y))

        # convert image shift to beam shift
        return BeamShift(
            x=mean_shift_x * self._microscope.beam.image_to_beam_shift[0],
            y=mean_shift_y * self._microscope.beam.image_to_beam_shift[1],
        )

    def _update_templates(
        self, image: Image8Bit, matches: list[TemplateMatchResult]
    ) -> None:
        for i, (area, match) in enumerate(zip(self._settings.areas, matches)):
            if match.confidence < self._settings.min_confidence:
                self._copy_template(i, self._image_store, self._image_store.next)
                continue

            slice = self._image_store.slice or 0
            if slice > 0 and slice % self._settings.rescan == 0:
                self._txt_log.debug(
                    f"Updating template image {i} for slice {slice + 1}."
                )

                new_template = image.crop(
                    area.shifted(
                        PixelPoint(x=match.dx, y=match.dy).to_relative(image.resolution)
                    )
                )

                self._image_store.next.write(
                    self._construct_template_name(i), new_template
                )
            else:
                self._copy_template(i, self._image_store, self._image_store.next)

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
        return f"{self.name_with_underscores}_template_{index}.tif"

    def _log_heatmaps(self, matches: list[TemplateMatchResult]) -> None:
        for i, match in enumerate(matches):
            self._log_heatmap(match.heatmap, i)

    def _log_image_shifts(
        self, image: Image8Bit, matches: list[TemplateMatchResult]
    ) -> None:
        overlays = []
        for i, (area, match) in enumerate(zip(self._settings.areas, matches)):
            area_px = area.to_pixels(image.resolution)

            overlays.append(
                RectangleOverlay(
                    x=area_px.origin.x,
                    y=area_px.origin.y,
                    width=area_px.width,
                    height=area_px.height,
                    color="red",
                )
            )

            if match.confidence < self._settings.min_confidence:
                self._txt_log.debug(
                    f"Confidence is too low for template {i}. Shifted template area will not be displayed in the log."
                )
                continue

            shifted_area_px = area_px.shifted(PixelPoint(x=match.dx, y=match.dy))

            overlays.append(
                RectangleOverlay(
                    x=shifted_area_px.origin.x,
                    y=shifted_area_px.origin.y,
                    width=shifted_area_px.width,
                    height=shifted_area_px.height,
                    color="blue",
                )
            )

        try:
            self._img_log.save_image(
                f"{self.name_with_underscores}_log.png",
                image,
                overlays,
                title="Template matching drift correction",
            )
        except Exception as e:
            self._txt_log.warning(
                f"Could not log a template matching drift correction result image: {e}"
            )

    def _log_heatmap(self, heatmap: NDArray[Any], index: int) -> None:
        try:
            self._img_log.save_image(
                f"{self.name_with_underscores}_heatmap_{index}.png",
                heatmap,
                overlays=None,
                title=f"Template matching heatmap for template {index}",
            )
        except Exception as e:
            self._txt_log.warning(
                f"Could not log a template matching drift correction heatmap: {e}"
            )
