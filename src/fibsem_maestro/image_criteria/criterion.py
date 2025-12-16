# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from fibsem_maestro.core.crop_coordinates import CropCoordinates
from fibsem_maestro.core.point import PixelPoint
from fibsem_maestro.core.tile_coordinates import TileCoordinates
from fibsem_maestro.image_criteria.functions import (
    CriterionRegistry,
)
from fibsem_maestro.image_criteria.reductors_registry import ReductorsRegistry
from fibsem_maestro.image_criteria.result import (
    CriterionPerTileResults,
    CriterionResult,
    ResolutionMap,
)
from fibsem_maestro.logging.image.overlay import RectangleOverlay
from fibsem_maestro.settings.criterion_settings import (
    BasicMode,
    MaskMode,
    MultiTileMode,
)

if TYPE_CHECKING:
    from collections.abc import Iterable

    from fibsem_maestro.core.image import Image
    from fibsem_maestro.logging.image.image_logger import ImageLogger
    from fibsem_maestro.logging.text.text_logger import TextLogger
    from fibsem_maestro.settings.criterion_settings import CriterionSettings
    from fibsem_maestro.settings.mask_settings import MaskSettings
    from fibsem_maestro.settings.reactive import ReactiveDict


class Criterion:
    def __init__(
        self,
        name: str,
        settings: CriterionSettings,
        masks: ReactiveDict[str, MaskSettings],
        txt_log: TextLogger,
        img_log: ImageLogger,
    ):
        self._name = name
        self._txt_log = txt_log
        self._img_log = img_log

        # settings for all available masks
        self._masks = masks

        self._apply_settings(settings)
        self._settings.on_change(self._update)

    def _update(self, settings: CriterionSettings) -> None:
        self._apply_settings(settings)

    def _apply_settings(self, settings: CriterionSettings) -> None:
        """Apply all configurable fields from the given settings object."""
        self._settings = settings

        self._resolution_metric_fn = CriterionRegistry.get(
            settings.resolution_metric_fn
        )
        self._calculation_mode = settings.calculation_mode
        self._tiling_mode = settings.tiling_mode

    def calculate_resolution(self, image: Image) -> np.floating:
        self._txt_log.info("Resolution calculation started.")
        crop_coordinates = self._compute_crop_coordinates(
            image, self._settings.border_fraction
        )

        match self._calculation_mode:
            case BasicMode() as mode:
                result = self._calculate_resolution_for_image(image, crop_coordinates)
                self._log_images(
                    "image",
                    image,
                    result.tiles_coordinates,
                    crop_coordinates,
                    result.best_tile,
                    result.resolution_map,
                )
                resolution = result.resolution

            case MaskMode() as mode:
                _ = mode
                raise NotImplementedError("Mask mode is not yet implemented.")
                # TODO: masking
                """
                if not (mask_settings := self._masks.get(mode.mask_name)):
                    raise CriterionError(
                        f"Mask name '{mode.mask_name}' does not correspond to any known mask"
                    )

                mask = Mask(mask_settings, self._txt_log, self._img_log)

                region_reduction_fn = ReductorsRegistry.get(mode.region_reduction_fn)

                regions = mask.mask_image(cropped_image)
                if not regions:
                    self._txt_log.error(
                        "Not enough masked regions for resolution calculation - masking omitted!"
                    )
                    regions = [cropped_image]

                per_region_resolutions = []
                for i, region in enumerate(regions):
                    result = self._calculate_resolution_for_image(image, region)
                    self._log_images(
                        f"image_region_{i}",
                        image,
                        result.tiles_coordinates,
                        crop_coordinates,
                        result.best_tile,
                        result.resolution_map,
                    )
                    per_region_resolutions.append(result.resolution)

                resolution = region_reduction_fn(
                    [x for x in per_region_resolutions if x is not np.isnan(x)]
                )
                """  # pyright: ignore[reportUnreachable]

        self._txt_log.info("Finished resolution calculation.")
        return resolution

    def _calculate_resolution_for_image(
        self, image: Image, crop_coordinates: CropCoordinates
    ) -> CriterionResult:
        # crop the image
        cropped_image = self._crop_image(image, crop_coordinates)

        # get coordinates of individual tiles
        tiles_coordinates = (
            list(
                self._compute_tiles_coordinates(
                    cropped_image,
                    self._tiling_mode.tile_size,
                    self._tiling_mode.relative_overlap,
                )
            )
            if isinstance(self._tiling_mode, MultiTileMode)
            # if this is a single-tile mode, only use a single tile
            else [
                TileCoordinates(
                    origin=PixelPoint(0, 0),
                    width_px=cropped_image.shape[1],
                    height_px=cropped_image.shape[0],
                ),
            ]
        )

        per_tile_results = self._analyze_tiles(cropped_image, tiles_coordinates)

        best_tile = (
            per_tile_results.get_best_tile()[0]
            if self._settings.log_best_tile
            else None
        )

        resolution_map = (
            self._create_resolution_map(
                image, tiles_coordinates, crop_coordinates, per_tile_results
            )
            if self._settings.log_resolution_map
            else None
        )

        return CriterionResult(
            resolution=per_tile_results.get_overall_resolution(
                ReductorsRegistry.get(self._tiling_mode.tile_reduction_fn)
            )
            if isinstance(self._tiling_mode, MultiTileMode)
            else per_tile_results.resolution[0],
            tiles_coordinates=tiles_coordinates,
            best_tile=best_tile,
            resolution_map=resolution_map,
        )

    def _analyze_tiles(
        self,
        image: Image,
        tiles_coordinates: Iterable[TileCoordinates],
    ) -> CriterionPerTileResults:
        tiles: list[Image] = []
        resolutions: list[np.floating] = []

        for tile in tiles_coordinates:
            tile_img = self._tile_from_coors(image, tile)
            tiles.append(tile_img)

            try:
                resolution = self._resolution_metric_fn(
                    tile_img, self._settings, self._txt_log
                )
                resolutions.append(resolution)
            except Exception as e:
                self._txt_log.warning(
                    f"Resolution calculation failed for tile (coordinates {tile}): {e}"
                )

        return CriterionPerTileResults(tiles, resolutions)

    def _create_resolution_map(
        self,
        image: Image,
        tiles_coordinates: Iterable[TileCoordinates],
        crop_coordinates: CropCoordinates,
        per_tile_results: CriterionPerTileResults,
    ) -> ResolutionMap:
        resolution_map = np.zeros_like(image, dtype=np.float64).view(ResolutionMap)
        for resolution, tile in zip(per_tile_results.resolution, tiles_coordinates):
            x = tile.origin.x + crop_coordinates.origin.x
            y = tile.origin.y + crop_coordinates.origin.y

            resolution_map[
                y : y + tile.height_px,
                x : x + tile.width_px,
            ] = resolution

        return resolution_map

    def _compute_tiles_coordinates(
        self,
        image: Image,
        tile_size: float,
        overlap: float,
    ) -> Iterable[TileCoordinates]:
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
                yield TileCoordinates(
                    origin=PixelPoint(x, y),
                    width_px=tile_size_px,
                    height_px=tile_size_px,
                )

    def _iter_tiles(
        self, image: Image, coordinates: Iterable[TileCoordinates]
    ) -> Iterable[Image]:
        """
        Iterate over image tiles extracted from the input image.
        """
        for tile in coordinates:
            yield self._tile_from_coors(image, tile)

    def _tile_from_coors(self, image: Image, tile: TileCoordinates) -> Image:
        return image[
            tile.origin.y : tile.origin.y + tile.height_px,
            tile.origin.x : tile.origin.x + tile.width_px,
        ]

    def _compute_crop_coordinates(
        self, image: Image, border_fraction: float
    ) -> CropCoordinates:
        """
        Compute the crop region based on the configured border fraction.
        """
        height, width = image.shape[:2]
        border_x = int(width * border_fraction)
        border_y = int(height * border_fraction)

        return CropCoordinates(
            origin=PixelPoint(border_x, border_y),
            width_px=width - 2 * border_x,
            height_px=height - 2 * border_y,
        )

    def _crop_image(self, image: Image, coordinates: CropCoordinates) -> Image:
        """
        Return the cropped region of the image.
        """
        return image[
            coordinates.origin.y : coordinates.origin.y + coordinates.height_px,
            coordinates.origin.x : coordinates.origin.x + coordinates.width_px,
        ]

    def _log_image_with_tiles(
        self,
        file: str,
        image: Image,
        tiles_coordinates: Iterable[TileCoordinates],
        crop_coordinates: CropCoordinates,
    ) -> None:
        overlays = []
        for tile in tiles_coordinates:
            x, y = tile.origin.x, tile.origin.y
            x += crop_coordinates.origin.x
            y += crop_coordinates.origin.y

            overlays.append(
                RectangleOverlay(
                    x,
                    y,
                    width=tile.width_px,
                    height=tile.height_px,
                    color="red",
                    alpha=1,
                    linewidth=1,
                )
            )

        try:
            self._img_log.save_image(file, image, overlays, "Image with tiling")
        except Exception as e:
            self._txt_log.warning(f"Could not log image into '{file}': {e}")

    def _log_images(
        self,
        base_name: str,
        full_image: Image,
        tiles_coordinates: Iterable[TileCoordinates],
        crop_coordinates: CropCoordinates,
        best_tile: Image | None,
        map: ResolutionMap | None,
    ):
        self._txt_log.info("Logging criterion images.")
        self._log_image_with_tiles(
            base_name, full_image, tiles_coordinates, crop_coordinates
        )
        if map is not None:
            self._img_log.save_image(f"{base_name}_map", map, None, "Resolution map")
        if best_tile is not None:
            self._img_log.save_image(
                f"{base_name}_best_tile", best_tile, None, "Best tile"
            )
