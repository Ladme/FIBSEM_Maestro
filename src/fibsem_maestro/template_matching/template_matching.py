# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from typing import Any

import cv2
import numpy as np
from numpy.typing import NDArray
from scipy import ndimage  # type: ignore

from fibsem_maestro.core.drift import Drift
from fibsem_maestro.core.image import Image, Image8Bit
from fibsem_maestro.core.point import PixelPoint
from fibsem_maestro.logging.image.image_logger import ImageLogger
from fibsem_maestro.logging.image.overlay import RectangleOverlay
from fibsem_maestro.logging.text.text_logger import TextLogger
from fibsem_maestro.microscope.microscope import Microscope
from fibsem_maestro.settings.template_matching_settings import TemplateMatchingSettings
from fibsem_maestro.store.image.image_store import ImageStore
from fibsem_maestro.template_matching.error import TemplateMatchingError
from fibsem_maestro.template_matching.result import TemplateMatchResult


class TemplateMatching:
    """
    Detects and measures image drift using normalized cross-correlation.

    Compares a newly acquired image against stored reference templates to
    determine how much the field of view has shifted since the templates were
    created. The measured drift can then be used by a drift correction action
    to compensate for sample movement between slices.

    Each template corresponds to a configured region of interest in the image.
    Multiple templates can be used simultaneously to improve robustness -
    the final drift estimate is the mean across all templates that meet the
    confidence threshold.

    Args:
        name: Human-readable identifier for this instance, used in log
            messages and template filenames.
        microscope: Interface to the electron microscope.
        settings: Template matching configuration.
        image_store: Store for persisting and retrieving template images.
        txt_log: Logger for diagnostic and status messages.
        img_log: Logger for heatmap and overlay images.
    """

    def __init__(
        self,
        name: str,
        microscope: Microscope,
        settings: TemplateMatchingSettings,
        image_store: ImageStore[Image8Bit],
        txt_log: TextLogger,
        img_log: ImageLogger,
    ):
        self._name = name
        self._microscope = microscope
        self._settings = settings
        self._image_store = image_store
        self._txt_log = txt_log
        self._img_log = img_log

    @property
    def name_with_underscores(self) -> str:
        """Instance name with spaces replaced by underscores."""
        return self._name.replace(" ", "_")

    def create_templates(self, store: ImageStore[Image8Bit] | None = None) -> None:
        """
        Acquire reference images and save an averaged template for each area.

        Acquires `settings.template_scans` frames, crops each configured area
        from every frame, validates that the crops are consistent across scans,
        and saves the per-area average as the reference template.

        Args:
            store: Store to write templates to. If `None`, the current
                slice's store is used.

        Raises:
            TemplateMatchingError: If no template areas are configured, if the
                cross-correlation confidence between any two scans is too low,
                or if the drift between any two scans exceeds the configured
                maximum.
        """
        if not self._settings.areas:
            raise TemplateMatchingError(
                "Cannot create templates: no template matching areas are configured."
            )

        frames = self._acquire_template_frames()

        for area_index, area in enumerate(self._settings.areas):
            template_scans = [frame.crop(area).to_8bit() for frame in frames]
            self._validate_template_scan_consistency(template_scans, area_index)
            self._save_averaged_template(template_scans, area_index, store)

    def update_templates(self, slice_number: int, confidence: float) -> None:
        """
        Refresh templates for the next slice, subject to the update policy.

        If the update conditions are met (slice number matches the update
        frequency or confidence is below the update threshold), acquires
        fresh frames and creates new templates for the next slice. Otherwise,
        copies the existing templates forward unchanged.

        Args:
            slice_number: The current slice index.
            confidence: Average template matching confidence from
                the most recent drift calculation.
        """
        if self._should_update_templates(slice_number, confidence):
            # acquire new templates for the next slice
            self.create_templates(self._image_store.next)

        else:
            # copy templates from the current slice
            for i in range(len(self._settings.areas)):
                self._copy_template(i, self._image_store, self._image_store.next)

    def calculate_drift(self, image: Image) -> Drift:
        """
        Calculate the image drift relative to the stored templates.

        Args:
            image: The current frame to compare against the stored templates.

        Returns:
            A `Drift` instance containing the x and y shift in nanometers
            and the average template matching confidence. If all template
            matches fall below the confidence threshold, `x` and `y` are
            `None`.
        """
        # convert image to 8bit
        img8bit = image.to_8bit()

        # perform template matching for each template
        matches = self._calculate_template_matches(img8bit)

        # log the results of template matching
        self._log_heatmaps(matches)
        self._log_image_shifts(img8bit, matches)

        # get image shift from template matching results
        shift = self._matches_to_image_shift(matches, image.pixel_size)

        # average confidence of the individual template matches
        confidence = self._get_average_confidence(matches)

        if shift is None:
            return Drift(x=None, y=None, confidence=confidence)

        return Drift(x=shift[0], y=shift[1], confidence=confidence)

    @staticmethod
    def calculate_match(
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

    def _acquire_template_frames(self) -> list[Image]:
        """
        Acquire the configured number of frames for template creation.

        Returns:
            A list of acquired frames, one per configured scan.
        """
        frames: list[Image] = []
        for i in range(self._settings.template_scans):
            self._txt_log.info(
                f"Acquiring template image {i + 1}/{self._settings.template_scans}."
            )
            frames.append(self._microscope.beam.grab_frame())
        return frames

    def _validate_template_scan_consistency(
        self, scans: list[Image8Bit], area_index: int
    ) -> None:
        """Validate that all scans of a template area are mutually consistent.

        Compares each unique pair of scans using normalized cross-correlation.
        Raises if any pair has a confidence below `settings.min_confidence`
        or a drift exceeding `settings.maximal_drift`.

        Args:
            scans: Cropped 8-bit images of the area from each acquired frame.
            area_index: Zero-based index of the template area.

        Raises:
            TemplateMatchingError: If any pair of scans has insufficient
                confidence or excessive drift.
        """
        if len(scans) <= 1:
            return

        for i in range(len(scans)):
            for j in range(i + 1, len(scans)):
                result = TemplateMatching.calculate_match(
                    scans[i], scans[j], self._settings.blur
                )

                if (
                    min_conf := self._settings.min_confidence
                ) is not None and result.confidence < min_conf:
                    raise TemplateMatchingError(
                        f"Cannot create template for area {area_index}: "
                        f"confidence between scan {i} and scan {j} is "
                        f"{result.confidence:.3f}, below the required "
                        f"minimum of {self._settings.min_confidence:.3f}."
                    )

                drift = np.sqrt(result.dx**2 + result.dy**2)
                if (
                    max_drift := self._settings.maximal_drift
                ) is not None and drift > max_drift:
                    raise TemplateMatchingError(
                        f"Cannot create template for area {area_index}: "
                        f"drift between scan {i} and scan {j} is "
                        f"{drift:.1f} px, exceeding the maximum of "
                        f"{max_drift:.1f} px."
                    )

    def _save_averaged_template(
        self,
        scans: list[Image8Bit],
        area_index: int,
        store: ImageStore[Image8Bit] | None = None,
    ) -> None:
        """
        Average multiple scans and save the result as the reference template.

        Args:
            scans: Cropped 8-bit images to average.
            area_index: Zero-based index of the template area.
            store: Destination store. If `None`, the current slice's store
                is used.
        """
        averaged = Image8Bit(
            np.mean(scans, axis=0).astype(np.uint8),
            pixel_size=scans[0].pixel_size,
        )
        self._save_template(averaged, index=area_index, image_store=store)

    def _calculate_template_matches(
        self, image: Image8Bit
    ) -> list[TemplateMatchResult]:
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
                TemplateMatching.calculate_match(template, cropped, self._settings.blur)
            )

        return matches

    def _matches_to_image_shift(
        self, matches: list[TemplateMatchResult], pixel_size: float
    ) -> tuple[float, float] | None:
        """
        Convert template match results to a mean image shift in nanometers.

        Converts each match's pixel displacement to nanometers and averages
        the results across all matches that meet the confidence threshold.
        Matches below the threshold are logged as warnings and excluded.

        Args:
            matches: Template match results, one per configured area.
            pixel_size: Physical size of one pixel in nanometers.

        Returns:
            A `(dx_nm, dy_nm)` tuple representing the mean image shift, or
            `None` if no match meets the confidence threshold.
        """
        shifts_x = []
        shifts_y = []
        for i, match in enumerate(matches):
            # convert shift to nm
            dx_nm = match.dx * pixel_size
            dy_nm = match.dy * pixel_size

            self._txt_log.info(
                f"Image shift for template {i}: {dx_nm},{dy_nm}. Confidence: {match.confidence}."
            )

            # ignore matches for which the confidence is too low
            if (
                min_conf := self._settings.min_confidence
            ) is not None and match.confidence < min_conf:
                self._txt_log.warning(
                    f"Template match confidence ({match.confidence}) is too low (limit: {self._settings.min_confidence}). "
                    f"Ignoring match for template {i}."
                )
                continue

            # ignore matches for which the drift is too large
            drift = np.sqrt(dx_nm**2 + dy_nm**2)
            if (
                max_drift := self._settings.maximal_drift
            ) is not None and drift > max_drift:
                self._txt_log.warning(
                    f"Drift ({drift}) is too large (limit: {max_drift}). "
                    f"Ignoring match for template {i}."
                )
                continue

            shifts_x.append(dx_nm)
            shifts_y.append(dy_nm)

        # check that at least one template had a high enough confidence
        if len(shifts_x) == 0 or len(shifts_y) == 0:
            self._txt_log.warning(
                "Template matching failed: all calculated matches were unsuitable."
            )
            return None

        # calculate average image shift
        return float(np.mean(shifts_x)), float(np.mean(shifts_y))

    def _get_average_confidence(self, matches: list[TemplateMatchResult]) -> float:
        """
        Compute the mean confidence across all template match results.

        Args:
            matches: Template match results to average.

        Returns:
            Mean normalised cross-correlation confidence across all matches.
        """
        return float(np.mean([match.confidence for match in matches]))

    def _should_update_templates(self, slice_number: int, confidence: float) -> bool:
        """
        Decide whether templates should be refreshed for the next slice.

        Templates are updated if the slice number matches the configured update
        frequency or if the average confidence falls below the update confidence
        limit.

        Args:
            slice_number: The current slice index.
            confidence: Average template matching confidence from the most
                recent drift calculation.

        Returns:
            `True` if templates should be refreshed, `False` otherwise.
        """
        if (
            freq := self._settings.update_frequency
        ) is not None and slice_number % freq == 0:
            self._txt_log.info(
                f"Updating templates: slice {slice_number} matches update frequency ({freq})."
            )
            return True

        if (
            conf_lim := self._settings.update_confidence_limit
        ) is not None and confidence < conf_lim:
            self._txt_log.info(
                f"Updating templates: template matching confidence ({confidence:.4f}) is below the limit ({conf_lim:.4f})."
            )
            return True

        self._txt_log.debug("Not updating templates.")
        return False

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
            A filename of the form `<name>_template_<index>.tif`,
            with spaces in the name replaced by underscores.
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

            if (
                min_conf := self._settings.min_confidence
            ) is not None and match.confidence < min_conf:
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
