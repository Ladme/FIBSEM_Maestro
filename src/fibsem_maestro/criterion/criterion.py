# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from __future__ import annotations

from typing import TYPE_CHECKING, cast

import numpy as np

from fibsem_maestro.core.area import PixelArea, RelativeArea
from fibsem_maestro.core.point import PixelPoint
from fibsem_maestro.criterion.error import CriterionError
from fibsem_maestro.criterion.functions import (
    CRITERION_FUNCTIONS,
)
from fibsem_maestro.criterion.reductors import REDUCTORS
from fibsem_maestro.criterion.result import (
    CriterionResult,
    SharpnessMap,
)
from fibsem_maestro.logging.image.overlay import RectangleOverlay
from fibsem_maestro.settings.criterion_settings import (
    BasicMode,
    MaskMode,
    MultiTileMode,
    SingleTileMode,
)

if TYPE_CHECKING:
    from collections.abc import Iterable

    from fibsem_maestro.core.image import Image
    from fibsem_maestro.core.resolution import Resolution
    from fibsem_maestro.logging.image.image_logger import ImageLogger
    from fibsem_maestro.logging.text.text_logger import TextLogger
    from fibsem_maestro.settings.criterion_settings import CriterionSettings


class Criterion:
    """
    Computes a sharpness score for an image using a configurable metric pipeline.

    The pipeline consists of three stages: area cropping, tiling, and metric
    evaluation. The image is first cropped to a configured region of interest,
    then optionally subdivided into overlapping square tiles, and finally scored
    using a registered criterion function. Multi-tile scores are reduced to a
    single value via a NumPy reduction function.

    1D images bypass cropping, tiling, and masking entirely and are passed
    directly to the metric function.

    Args:
        name: Human-readable name identifying this criterion instance.
        settings: Criterion configuration.
        txt_log: Logger for diagnostic and status messages.
        img_log: Logger for saving tile overlays, sharpness maps, and best tile images.
    """

    def __init__(
        self,
        name: str,
        settings: CriterionSettings,
        txt_log: TextLogger,
        img_log: ImageLogger,
    ):
        self._name = name
        self._txt_log = txt_log
        self._img_log = img_log

        self._settings = settings
        self._calculation_mode = settings.calculation_mode
        self._tiling_mode = settings.tiling_mode
        self._sharpness_metric_fn = CRITERION_FUNCTIONS.get(
            settings.sharpness_metric_fn
        )

        if isinstance(self._tiling_mode, MultiTileMode):
            self._tile_reduction_fn = REDUCTORS.get(self._tiling_mode.tile_reduction_fn)
            self._tile_size = self._tiling_mode.tile_size
            self._tile_relative_overlap = self._tiling_mode.relative_overlap

    @property
    def name(self) -> str:
        """Human-readable name of this criterion instance."""
        return self._name

    @property
    def name_with_underscores(self) -> str:
        """Criterion name with spaces replaced by underscores, used for file naming."""
        return self._name.replace(" ", "_")

    def calculate_sharpness(self, image: Image) -> float:
        """
        Compute the sharpness score for an image.

        For 1D images, the metric function is applied directly without cropping
        or tiling. For 2D images, the configured calculation and tiling modes
        are applied.

        Args:
            image: The image to evaluate.

        Returns:
            Sharpness score as a single float. Higher values indicate a sharper
            image, though the scale depends on the chosen metric function.
        """
        self._txt_log.info("Sharpness calculation started.")

        # handle 1D images - no cropping, no tiling, no masking
        if len(image.shape) == 1:
            sharpness = float(
                self._sharpness_metric_fn(image, self._settings, self._txt_log)
            )
            self._txt_log.info("Finished sharpness calculation.")
            return sharpness

        match self._calculation_mode:
            case BasicMode() as mode:
                result = self._calculate_sharpness_for_image(image)
                self._log_images(
                    image,
                    result.tiles_px,
                    result.best_tile,
                    result.sharpness_map,
                )
                sharpness = result.sharpness

            case MaskMode() as mode:
                _ = mode
                raise NotImplementedError("Mask mode is not yet implemented")
                # TODO: masking

        self._txt_log.info("Finished sharpness calculation.")
        return sharpness

    def _calculate_sharpness_for_image(self, image: Image) -> CriterionResult:
        """
        Run the full sharpness pipeline on a 2D image.

        Crops the image to the configured area, computes per-tile sharpness
        scores, reduces them to a single value, and optionally assembles
        logging artefacts.

        Args:
            image: The full 2D image to evaluate.

        Returns:
            A CriterionResult containing the final sharpness score, tile pixel
            coordinates, the best-scoring tile image (if logging is enabled),
            and a sharpness map (if logging is enabled).
        """
        # crop the image
        if len(self._settings.area) != 1:
            raise CriterionError(
                f"Expected exactly one criterion area, got {len(self._settings.area)}."
            )
        cropped = image.crop(self._settings.area[0])

        # calculate sharpness for the whole image
        if isinstance(self._tiling_mode, SingleTileMode):
            self._txt_log.debug("Calculating sharpness in a single tile mode.")
            tiles = [RelativeArea.full()]
            sharpnesses = [self._calculate_sharpness_for_tile(cropped, tiles[0])]
            final_sharpness = sharpnesses[0]
            self._txt_log.debug(f"Final sharpness for image: {final_sharpness}.")
        # calculate sharpness for the individual tiles
        else:
            self._txt_log.debug("Calculating sharpness in a multi tile mode.")
            tiles = list(
                self._iter_tiles(
                    cropped,
                    self._tile_size,
                    self._tile_relative_overlap,
                )
            )

            self._txt_log.debug(f"Number of tiles for criterion: {len(tiles)}.")

            sharpnesses: list[float] = []
            for tile in tiles:
                sharpnesses.append(self._calculate_sharpness_for_tile(cropped, tile))

            final_sharpness = float(
                self._tile_reduction_fn([x for x in sharpnesses if not np.isnan(x)])
            )

            self._txt_log.debug(f"Final sharpness for image: {final_sharpness}.")

        # get the tile with the best sharpness
        best_tile = (
            cropped.crop(tiles[int(np.nanargmax(sharpnesses))])
            if self._settings.log_best_tile
            else None
        )

        # convert tiles to pixel coordinates in the original uncropped image
        tiles_px = list(
            Criterion._tiles_to_pixels_in_full_image(
                tiles, self._settings.area[0], image.resolution, cropped.resolution
            )
        )

        # create a sharpness map
        sharpness_map = (
            self._create_sharpness_map(image, tiles_px, sharpnesses)
            if self._settings.log_sharpness_map
            else None
        )

        return CriterionResult(
            sharpness=final_sharpness,
            tiles_px=tiles_px,
            best_tile=best_tile,
            sharpness_map=sharpness_map,
        )

    def _calculate_sharpness_for_tile(self, image: Image, tile: RelativeArea) -> float:
        """
        Compute the sharpness score for a single tile of an image.

        Crops the image to the given tile and applies the configured
        metric function. If the metric raises an exception, a warning is logged
        and NaN is returned so the tile can be excluded from reduction.

        Args:
            image: The image to tile into.
            tile: Relative area defining the tile within the image.

        Returns:
            Sharpness score for the tile, or NaN if computation failed.
        """
        tile_img = image.crop(tile)

        try:
            sharpness = float(
                self._sharpness_metric_fn(tile_img, self._settings, self._txt_log)
            )
            self._txt_log.debug(f"Sharpness for tile {tile}: {sharpness}")
            return sharpness
        except Exception as e:
            self._txt_log.warning(f"Resolution calculation failed for tile {tile}: {e}")
            return np.nan

    def _iter_tiles(
        self,
        image: Image,
        tile_size: float,
        overlap: float,
    ) -> Iterable[RelativeArea]:
        """
        Iterate over square tiles covering an image.

        Tiles are generated left-to-right, top-to-bottom, with a fixed step
        size derived from the tile size and overlap fraction. Tiles that would
        extend beyond the image boundary are omitted.

        Args:
            image: The image to tile.
            tile_size: Side length of each square tile in nanometers.
            overlap: Fractional overlap between adjacent tiles, in the range [0, 1).

        Yields:
            RelativeArea instances, each describing one tile's position and
            size relative to the image dimensions.
        """
        # calculate the tile size in pixels
        tile_size_px = int(tile_size / image.pixel_size)
        tile_size_px -= tile_size_px % 4  # must be divisible by 4
        if tile_size_px < 4:
            raise CriterionError(
                "Tile size is smaller than 4x4 pixels. Increase the tile size."
            )

        step = int(tile_size_px * (1 - overlap))
        if step == 0:
            raise CriterionError(
                "Tiles could not be constructed. Overlap is too large or tiles are too small."
            )
        height, width = image.shape[:2]

        for y in range(0, height - tile_size_px + 1, step):
            for x in range(0, width - tile_size_px + 1, step):
                yield PixelArea(
                    origin=PixelPoint(x, y),
                    width=tile_size_px,
                    height=tile_size_px,
                ).to_relative(image.resolution)

    def _create_sharpness_map(
        self,
        full_image: Image,
        tiles: Iterable[PixelArea],
        sharpnesses: Iterable[float],
    ) -> SharpnessMap:
        """
        Build a sharpness map by painting tile scores onto a zero image.

        Each tile's region in the output array is filled with the corresponding
        sharpness value. Pixels not covered by any tile remain zero.

        Args:
            full_image: The original full-resolution image, used only for its shape.
            tiles: Tile positions in pixel coordinates within the full image.
            sharpnesses: Sharpness score for each tile, in the same order as tiles.

        Returns:
            A SharpnessMap with the same spatial dimensions as full_image.
        """
        sharpness_map = cast(
            "SharpnessMap",
            np.zeros_like(full_image, dtype=np.float64).view(SharpnessMap),
        )

        for sharpness, tile in zip(sharpnesses, tiles):
            sharpness_map[
                tile.origin.y : tile.origin.y + tile.height,
                tile.origin.x : tile.origin.x + tile.width,
            ] = sharpness

        return sharpness_map

    def _log_image_with_tiles(
        self,
        filename: str,
        full_image: Image,
        tiles: Iterable[PixelArea],
    ) -> None:
        """
        Save the full image annotated with red tile outlines.

        Each tile is drawn as a rectangle overlay. Failures are caught and
        logged as warnings.

        Args:
            filename: Output filename passed to the image logger.
            full_image: The image to annotate.
            tiles: Tile positions in pixel coordinates to draw as overlays.
        """
        overlays = []
        for tile in tiles:
            overlays.append(
                RectangleOverlay(
                    tile.origin.x,
                    tile.origin.y,
                    width=tile.width,
                    height=tile.height,
                    color="red",
                    alpha=1,
                    linewidth=1,
                )
            )

        try:
            self._img_log.save_image(
                filename, full_image, overlays, "Image with tiling"
            )
        except Exception as e:
            self._txt_log.warning(f"Could not log a criterion image with tiles: {e}")

    def _log_images(
        self,
        full_image: Image,
        tiles: Iterable[PixelArea],
        best_tile: Image | None,
        map: SharpnessMap | None,
    ):
        """
        Save all optional diagnostic images for a completed sharpness calculation.

        Always saves the full image with tile overlays. Saves the sharpness map
        and best tile only when they are provided. Each save is attempted
        independently so that one failure does not prevent the others.

        Args:
            full_image: The original full-resolution image.
            tiles: Tile positions in pixel coordinates, used for overlays.
            best_tile: The tile with the highest sharpness score, or None if best-tile logging is disabled.
            map: The sharpness map, or None if sharpness map logging is disabled.
        """
        self._txt_log.debug("Logging criterion images.")

        self._log_image_with_tiles(self.name_with_underscores, full_image, tiles)
        if map is not None:
            try:
                self._img_log.save_image(
                    f"{self.name_with_underscores}_sharpness_map",
                    map,
                    None,
                    "Sharpness map",
                )
            except Exception as e:
                self._txt_log.warning(f"Could not log a sharpness map: {e}")
        if best_tile is not None:
            try:
                self._img_log.save_image(
                    f"{self.name_with_underscores}_best_tile",
                    best_tile,
                    None,
                    "Best tile",
                )
            except Exception as e:
                self._txt_log.warning(f"Could not log a criterion best tile: {e}")

    @staticmethod
    def _tiles_to_pixels_in_full_image(
        tiles: Iterable[RelativeArea],
        criterion_area: RelativeArea,
        full_image_resolution: Resolution,
        cropped_image_resolution: Resolution,
    ) -> Iterable[PixelArea]:
        """
        Convert tile relative areas to pixel coordinates in the original uncropped image.

        Tiles are initially expressed relative to the cropped image. This method
        translates them back into the coordinate space of the full image by
        adding the pixel offset of the cropped area's origin.

        Args:
            tiles: Tile positions relative to the cropped image.
            criterion_area: The relative area that was cropped from the full image, used to compute the pixel offset.
            full_image_resolution: Resolution of the original uncropped image.
            cropped_image_resolution: Resolution of the cropped image.

        Yields:
            PixelArea instances in the coordinate space of the full image.
        """
        criterion_area_px = criterion_area.to_pixels(full_image_resolution)
        offset_x, offset_y = criterion_area_px.origin.x, criterion_area_px.origin.y

        for tile in tiles:
            tile_px = tile.to_pixels(cropped_image_resolution)
            tile_px.origin.x += offset_x
            tile_px.origin.y += offset_y
            yield tile_px
