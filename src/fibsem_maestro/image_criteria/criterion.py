# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from __future__ import annotations

from collections.abc import Iterable
import itertools
from typing import TYPE_CHECKING

import numpy as np

from fibsem_maestro.core.crop_coordinates import CropCoordinates
from fibsem_maestro.core.image import Image
from fibsem_maestro.core.tile_coordinates import TileCoordinates
from fibsem_maestro.image_criteria.error import CriterionError
from fibsem_maestro.image_criteria.functions import (
    CriterionRegistry,
)
from fibsem_maestro.image_criteria.mode import (
    BasicMode,
    MapMode,
    MaskMode,
)
from fibsem_maestro.image_criteria.numpy_registry import NumpyRegistry
from fibsem_maestro.image_criteria.result import (
    CriterionPerTileResults,
    CriterionResult,
    ResolutionMap,
)
from fibsem_maestro.masking.mask import Mask

if TYPE_CHECKING:
    from fibsem_maestro.logging.image.image_logger import ImageLogger
    from fibsem_maestro.logging.text.text_logger import TextLogger
    from fibsem_maestro.settings.criterion_settings import CriterionSettings


# TODO: logging
class Criterion:
    def __init__(
        self, settings: CriterionSettings, txt_log: TextLogger, img_log: ImageLogger
    ):
        self._txt_log = txt_log
        self._img_log = img_log

        self._apply_settings(settings)
        self._settings.on_change(self._update)

    def _update(self, settings: CriterionSettings) -> None:
        self._apply_settings(settings)

    def _apply_settings(self, settings: CriterionSettings) -> None:
        """Apply all configurable fields from the given settings object."""
        self._settings = settings

        self._resolution_metric_fn = CriterionRegistry(settings.resolution_metric_fn)
        self._region_reduction_fn = NumpyRegistry(settings.region_reduction_fn)
        self._tile_reduction_fn = NumpyRegistry(settings.tile_reduction_fn)
        self._tile_size = settings.tile_size
        self._relative_overlap = settings.relative_overlap
        self._border_fraction = settings.border_fraction
        self._calculation_mode = settings.calculation_mode

    def calculate_resolution(self, image: Image) -> CriterionResult:
        match self._calculation_mode:
            # TODO: what if self.tile_size is 0
            # TODO: handle 1D images
            case BasicMode() as mode:
                return self._calculate_resolution_basic_mode(image, mode.get_best_tile)
            case MapMode() as mode:
                return self._calculate_resolution_map_mode(image, mode.get_best_tile)
            case MaskMode() as mode:
                # TODO mask mode
                raise NotImplementedError("Masking not yet implemented.")

    def _calculate_resolution_basic_mode(
        self, image: Image, get_best_tile: bool
    ) -> CriterionResult:
        cropped_image = self._crop_image(image)

        per_tile_results = self._analyze_tiles(
            cropped_image,
            self._iter_tile_coordinates(cropped_image, self._relative_overlap),
        )

        return CriterionResult(
            resolution=per_tile_results.get_overall_resolution(self._tile_reduction_fn),
            best_tile=per_tile_results.get_best_tile()[0] if get_best_tile else None,
        )

    def _calculate_resolution_map_mode(
        self, image: Image, get_best_tile: bool
    ) -> CriterionResult:
        coordinates = self._iter_tile_coordinates(image, self._relative_overlap)
        # create two copies of the coordinates iterator
        coors1, coors2 = itertools.tee(coordinates, 2)
        per_tile_results = self._analyze_tiles(image, coors1)

        return CriterionResult(
            resolution=per_tile_results.get_overall_resolution(self._tile_reduction_fn),
            resolution_map=self._create_resolution_map(image, coors2, per_tile_results),
            best_tile=per_tile_results.get_best_tile()[0] if get_best_tile else None,
        )

    def _calculate_resolution_mask_mode(
        self, image: Image, mask: Mask
    ) -> CriterionResult:
        raise NotImplementedError()

    def _analyze_tiles(
        self,
        image: Image,
        tiles_coordinates: Iterable[TileCoordinates],
    ) -> CriterionPerTileResults:
        tiles: list[Image] = []
        qualities: list[np.floating] = []

        for tile in tiles_coordinates:
            tile_img = image[
                tile.x : tile.x + tile.width,
                tile.y : tile.y + tile.height,
            ].view(Image)
            tiles.append(tile_img)

            resolution = self._resolution_metric_fn(
                tile_img, self._settings, self._txt_log
            )
            qualities.append(resolution)

        return CriterionPerTileResults(tiles, qualities)

    def _create_resolution_map(
        self,
        image: Image,
        tiles_coordinates: Iterable[TileCoordinates],
        per_tile_results: CriterionPerTileResults,
    ) -> ResolutionMap:
        resolution_map = np.zeros_like(image, dtype=np.float64).view(ResolutionMap)
        for resolution, tile in zip(per_tile_results.resolution, tiles_coordinates):
            resolution_map[
                tile.x : tile.x + tile.height,
                tile.y : tile.y + tile.width,
            ] = resolution

        return resolution_map

    def _iter_tile_coordinates(
        self,
        image: Image,
        overlap: float,
    ) -> Iterable[TileCoordinates]:
        """
        Iterate over the coordinates of square tiles covering an image.
        """
        # calculate the tile size in pixels
        tile_size_px = int(self._tile_size / image.pixel_size)
        tile_size_px -= tile_size_px % 4  # must be divisible by 4

        step = int(tile_size_px * (1 - overlap))
        height, width = image.shape[:2]

        for x in range(0, height - tile_size_px + 1, step):
            for y in range(0, width - tile_size_px + 1, step):
                yield TileCoordinates(
                    x=x,
                    y=y,
                    width=tile_size_px,
                    height=tile_size_px,
                )

    def _iter_tiles(
        self,
        image: Image,
        overlap: float,
    ) -> Iterable[Image]:
        """
        Iterate over image tiles extracted from the input image.
        """
        for tile in self._iter_tile_coordinates(image, overlap):
            yield image[
                tile.x : tile.x + tile.width,
                tile.y : tile.y + tile.height,
            ].view(Image)

    def _compute_crop_coordinates(self, image: Image) -> CropCoordinates:
        """
        Compute the crop region based on the configured border fraction.
        """
        height, width = image.shape[:2]
        border_x = int(height * self._border_fraction)
        border_y = int(width * self._border_fraction)

        return CropCoordinates(
            x=border_x,
            y=border_y,
            width=height - 2 * border_x,
            height=width - 2 * border_y,
        )

    def _crop_image(self, image: Image) -> Image:
        """
        Return the cropped region of the image based on border settings.
        """
        coords = self._compute_crop_coordinates(image)
        return image[
            coords.x : coords.x + coords.width,
            coords.y : coords.y + coords.height,
        ].view(Image)
