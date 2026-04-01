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
from fibsem_maestro.core.image import Image8Bit
from fibsem_maestro.core.point import PixelPoint
from fibsem_maestro.drift_correction.error import DriftCorrectionError
from fibsem_maestro.drift_correction.result import (
    TemplateMatchResult,
)
from fibsem_maestro.logging.image.image_logger import ImageLogger
from fibsem_maestro.logging.image.overlay import RectangleOverlay
from fibsem_maestro.logging.text.text_logger import TextLogger
from fibsem_maestro.microscope.microscope import Microscope
from fibsem_maestro.settings.property_names import PropertyNames
from fibsem_maestro.settings.template_matching_settings import TemplateMatchingSettings
from fibsem_maestro.store.image.image_store import ImageStore
from fibsem_maestro.store.props.props_store import PropsStore


class TemplateMatchingDriftCorrection(Action):
    """
    Drift correction action based on normalized cross-correlation template matching.

    Args:
        name: Human-readable identifier for this action instance.
        microscope: Interface to the electron microscope hardware.
        settings: Template matching settings.
        props_store: Store used to read and write microscope properties.
        image_store: Store used to persist template images across slices.
        txt_log: Logger for status and diagnostic text messages.
        img_log: Logger for annotated images and heatmaps.
    """

    def __init__(
        self,
        name: str,
        microscope: Microscope,
        settings: TemplateMatchingSettings,
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
        """
        Acquire a reference image and save a template crop for each configured area.

        Sets the microscope properties defined in the action's properties file,
        acquires a single frame, crops each configured area from that frame, and
        writes the resulting templates to the image store.

        Raises:
            DriftCorrectionError: If no template matching areas have been configured
                in the settings.
        """
        if len(self._settings.areas) == 0:
            raise DriftCorrectionError("No template matching areas defined.")

        # grab an image using the specified microscope properties
        self.read_and_set_properties()
        self._txt_log.info("Acquiring template image.")
        template_image = self._microscope.beam.grab_frame()

        for i, area in enumerate(self._settings.areas):
            self._save_template(template_image.crop(area).to_8bit(), i)

    def correct_drift(self) -> None:
        """
        Acquire a new frame, calculate the drift, and apply a compensating beam shift.

        The correction is performed in up to two passes:

        1. A frame is acquired and template matching is used to calculate the
           required beam shift. The shift is applied via `Microscope.add_beam_shift_with_verification`.
        2. If the beam shift limit was exceeded and the stage had to be moved
           instead, a second frame is acquired and a fine-tuning correction is
           applied to remove any residual stage-positioning error.

        After correction the current microscope properties are written to the
        property store and the templates are updated for the next slice.
        """
        # grab image for drift correction
        self.read_and_set_properties()
        self._txt_log.info("Acquiring drift correction image.")
        image = self._microscope.beam.grab_frame().to_8bit()
        beam_shift, matches = self._calculate_correction_beam_shift(image)

        if not (self._microscope.add_beam_shift_with_verification(beam_shift)):
            # this branch is taken if stage is moved
            self._txt_log.info(
                "Fine-tuning drift correction to remove stage positioning error."
            )

            # grab a new image
            image = self._microscope.beam.grab_frame().to_8bit()
            beam_shift, matches = self._calculate_correction_beam_shift(image)
            # we assume that beam shift will always be in limit here
            self._microscope.add_beam_shift_with_verification(beam_shift)

        # collect and save the microscope properties for the next slice
        self.collect_and_write_properties(self._props_store.next)

        # update the templates for the next slice
        self._update_templates(image, matches)

    def _calculate_correction_beam_shift(
        self, image: Image8Bit
    ) -> tuple[BeamShift, list[TemplateMatchResult]]:
        """
        Run template matching and convert the results to a beam shift.

        Args:
            image: The drift-correction frame to match templates against.

        Returns:
            A tuple of:
                - The beam shift that compensates for the detected drift.
                - The individual match results for each template area.
        """
        # perform template matching for each template
        matches = self._get_template_matches(image)

        # log the results of template matching
        self._log_heatmaps(matches)
        self._log_image_shifts(image, matches)

        # get beam shift based on the template matching
        beam_shift = self._matches_to_beam_shift(matches, image.pixel_size)

        return beam_shift, matches

    def _get_template_matches(self, image: Image8Bit) -> list[TemplateMatchResult]:
        """
        Load each template and compute its match within the corresponding image region.

        Args:
            image: Full drift-correction frame to search within.

        Returns:
            One `TemplateMatchResult` per configured template area, in the
            same order as `settings.areas`.
        """
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
        """
        Compute the normalized cross-correlation between `template` and `image`.

        Optionally applies a Gaussian blur to both images before matching in order
        to suppress high-frequency noise that could otherwise dominate the
        correlation. The peak of the resulting heatmap is located and its offset
        from the heatmap centre is returned as the image-space displacement.

        Args:
            template: Reference patch to locate within `image`.
            image: Image region to search; must be larger than `template` by at
                least the expected drift on each side.
            blur: Standard deviation of the Gaussian kernel applied before
                matching. Pass `0` to skip blurring.

        Returns:
            A `TemplateMatchResult` containing the pixel displacement
            `(dx, dy)` from the image centre to the best-match location,
            together with the peak normalised cross-correlation score and the
            full heatmap array.
        """
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
        """
        Convert a list of template match results to a single compensating beam shift.

        Args:
            matches: Template match results, one per configured area.
            pixel_size: Physical size of one pixel in nanometres.

        Returns:
            The beam shift to apply in order to compensate for the detected
            drift. Returns a zero shift when no template exceeds the confidence
            threshold and the acquisition is configured to continue.

        Raises:
            DriftCorrectionError: If all template confidences are below
                `settings.min_confidence` and
                `settings.stop_acquisition_at_failure` is `True`.
        """
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
        """
        Refresh the stored templates for the next slice, subject to the rescan period.

        For each template area:
        - If the match confidence was too low, the existing template is copied forward unchanged.
        - Otherwise, if the current slice index is a nonzero multiple of
          `settings.rescan`, the template is re-cropped from the corrected
          position in the current frame and written to the next-slice image store.
        - In all other cases the existing template is copied forward.

        Args:
            image: Drift-correction frame from the current slice.
            matches: Template match results for the current slice.
        """
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
        template: Image8Bit,
        index: int,
        image_store: ImageStore[Image8Bit] | None = None,
    ) -> None:
        """
        Save a template to the image store.

        Args:
            template: 8-bit image to save.
            index: Zero-based template index.
            image_store: Destination store. Defaults to the current-slice store if `None`.
        """
        # default: current slice
        store = image_store or self._image_store

        self._txt_log.debug(f"Saving template {index}.")
        store.write(self._construct_template_name(index), template)

    def _load_template(
        self, index: int, image_store: ImageStore[Image8Bit] | None = None
    ) -> Image8Bit:
        """
        Read a previously saved template from the image store.

        Args:
            index: Zero-based template index matching the one used when saving.
            image_store: Source store. Defaults to the current-slice store if `None`.

        Returns:
            The stored 8-bit template image.
        """
        # default: current slice
        store = image_store or self._image_store

        self._txt_log.debug(f"Loading template {index}.")
        return store.read(self._construct_template_name(index))

    def _copy_template(
        self, index: int, src: ImageStore[Image8Bit], dest: ImageStore[Image8Bit]
    ) -> None:
        """
        Copy a template image from one store to another without modification.

        Args:
            index: Zero-based template index.
            src: Store to read the template from.
            dest: Store to write the template to.
        """
        image = src.read(self._construct_template_name(index))
        dest.write(self._construct_template_name(index), image)

    def _construct_template_name(self, index: int) -> str:
        """
        Build the filename used to persist a template image.

        Args:
            index: Zero-based template index.

        Returns:
            A filename of the form `<action_name>_template_<index>.tif`,
            with spaces in the action name replaced by underscores.
        """
        return f"{self.name_with_underscores}_template_{index}.tif"

    def _log_heatmaps(self, matches: list[TemplateMatchResult]) -> None:
        """
        Save a heatmap image for each template match result to the image log.

        Args:
            matches: Template match results whose heatmaps should be logged.
        """
        for i, match in enumerate(matches):
            self._log_heatmap(match.heatmap, i)

    def _log_image_shifts(
        self, image: Image8Bit, matches: list[TemplateMatchResult]
    ) -> None:
        """
        Overlay the original and shifted template areas on the drift-correction frame and log it.

        Args:
            image: Drift-correction frame to annotate.
            matches: Template match results providing per-area displacements
                and confidence scores.
        """

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
        """
        Save a single normalised cross-correlation heatmap to the image log.

        Args:
            heatmap: 2D array of normalised cross-correlation scores.
            index: Zero-based template index, used to construct the filename.
        """
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
