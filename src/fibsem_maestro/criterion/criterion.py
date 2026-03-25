# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from fibsem_maestro.core.area import PixelArea, RelativeArea
from fibsem_maestro.core.point import PixelPoint
from fibsem_maestro.criterion.functions import (
    CriterionRegistry,
)
from fibsem_maestro.criterion.reductors_registry import ReductorsRegistry
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
        self._sharpness_metric_fn = CriterionRegistry.get(settings.sharpness_metric_fn)

        if isinstance(self._tiling_mode, MultiTileMode):
            self._tile_reduction_fn = ReductorsRegistry.get(
                self._tiling_mode.tile_reduction_fn
            )
            self._tile_size = self._tiling_mode.tile_size
            self._tile_relative_overlap = self._tiling_mode.relative_overlap

    @property
    def name(self) -> str:
        return self._name

    @property
    def name_with_underscores(self) -> str:
        return self._name.replace(" ", "_")

    def calculate_sharpness(self, image: Image) -> float:
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
        # crop the image
        cropped = image.crop(self._settings.area)

        # calculate sharpness for the whole image
        if isinstance(self._tiling_mode, SingleTileMode):
            self._txt_log.debug("Calculating sharpness in a single tile mode.")
            tiles = [RelativeArea.full()]
            sharpnesses = [self._calculate_sharpness_for_tile(cropped, tiles[0])]
            final_sharpness = sharpnesses[0]
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

        # get the tile with the best sharpness
        best_tile = (
            cropped.crop(tiles[sharpnesses.index(max(sharpnesses))])
            if self._settings.log_best_tile
            else None
        )

        # convert tiles to pixel coordinates in the original uncropped image
        tiles_px = list(
            Criterion._tiles_to_pixels_in_full_image(
                tiles, self._settings.area, image.resolution, cropped.resolution
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
        Iterate over the coordinates of square tiles covering an image.
        """
        # calculate the tile size in pixels
        tile_size_px = int(tile_size / image.pixel_size)
        tile_size_px -= tile_size_px % 4  # must be divisible by 4

        step = int(tile_size_px * (1 - overlap))
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
        sharpness_map = np.zeros_like(full_image, dtype=np.float64).view(SharpnessMap)

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
        Converts tiles represented as relative areas to pixel areas in the original uncropped image.
        """
        criterion_area_px = criterion_area.to_pixels(full_image_resolution)
        criterion_area_px = criterion_area.to_pixels(full_image_resolution)
        offset_x, offset_y = criterion_area_px.origin.x, criterion_area_px.origin.y

        for tile in tiles:
            tile_px = tile.to_pixels(cropped_image_resolution)
            tile_px.origin.x += offset_x
            tile_px.origin.y += offset_y
            yield tile_px
