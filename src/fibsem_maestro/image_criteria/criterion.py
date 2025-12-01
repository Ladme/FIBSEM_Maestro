# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

from fibsem_maestro.core.crop_coordinates import CropCoordinates
from fibsem_maestro.core.tile_coordinates import TileCoordinates
from fibsem_maestro.image_criteria.error import CriterionError
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
from fibsem_maestro.masking.mask import Mask
from fibsem_maestro.settings.criterion_settings import (
    BasicMode,
    MapMode,
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

    def calculate_resolution(self, image: Image) -> CriterionResult:
        self._txt_log.info("Resolution calculation started.")

        match self._calculation_mode:
            # TODO: handle 1D images
            case BasicMode() as mode:
                result = self._calculate_resolution_basic_mode(
                    image, mode.get_best_tile, mode.border_fraction
                )
            case MapMode() as mode:
                result = self._calculate_resolution_map_mode(image, mode.get_best_tile)
            case MaskMode() as mode:
                result = self._calculate_resolution_mask_mode(
                    image,
                    mode.mask_name,
                    mode.region_reduction_fn,
                    mode.border_fraction,
                )

        self._txt_log.info("Finished resolution calculation.")
        return result

    def _calculate_resolution_basic_mode(
        self,
        image: Image,
        get_best_tile: bool,
        border_fraction: float,
        index: int | None = None,
    ) -> CriterionResult:
        crop_coordinates = self._compute_crop_coordinates(image, border_fraction)
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
                    x=0,
                    y=0,
                    width=cropped_image.shape[1],
                    height=cropped_image.shape[0],
                ),
            ]
        )

        per_tile_results = self._analyze_tiles(cropped_image, tiles_coordinates)

        best_tile = per_tile_results.get_best_tile()[0] if get_best_tile else None

        self._log_images(
            f"criterion_{self._name}"
            if index is None
            else f"criterion_{self._name}_region_{index}",
            image,
            tiles_coordinates,
            crop_coordinates,
            best_tile,
            None,
        )

        return CriterionResult(
            resolution=per_tile_results.get_overall_resolution(
                ReductorsRegistry.get(self._tiling_mode.tile_reduction_fn)
            )
            if isinstance(self._tiling_mode, MultiTileMode)
            else per_tile_results.resolution[0],
            best_tile=best_tile,
        )

    def _calculate_resolution_map_mode(
        self, image: Image, get_best_tile: bool
    ) -> CriterionResult:
        # get coordinates of individual tiles
        coordinates = (
            list(
                self._compute_tiles_coordinates(
                    image,
                    self._tiling_mode.tile_size,
                    self._tiling_mode.relative_overlap,
                )
            )
            if isinstance(self._tiling_mode, MultiTileMode)
            # if this is a single-tile mode, only use a single tile
            else [
                TileCoordinates(
                    x=0,
                    y=0,
                    width=image.shape[1],
                    height=image.shape[0],
                ),
            ]
        )

        per_tile_results = self._analyze_tiles(image, coordinates)

        best_tile = per_tile_results.get_best_tile()[0] if get_best_tile else None
        resolution_map = self._create_resolution_map(
            image, coordinates, per_tile_results
        )

        self._log_images(
            f"criterion_{self._name}",
            image,
            coordinates,
            None,
            best_tile,
            resolution_map,
        )

        return CriterionResult(
            resolution=per_tile_results.get_overall_resolution(
                ReductorsRegistry.get(self._tiling_mode.tile_reduction_fn)
            )
            if isinstance(self._tiling_mode, MultiTileMode)
            else per_tile_results.resolution[0],
            best_tile=best_tile,
            resolution_map=self._create_resolution_map(
                image, coordinates, per_tile_results
            ),
        )

    def _calculate_resolution_mask_mode(
        self,
        image: Image,
        mask_name: str,
        reduction_fn_name: str,
        border_fraction: float,
    ) -> CriterionResult:
        if not (mask_settings := self._masks.get(mask_name)):
            raise CriterionError(
                f"Mask name '{mask_name}' does not correspond to any known mask"
            )
        mask = Mask(mask_settings, self._txt_log, self._img_log)

        region_reduction_fn = ReductorsRegistry.get(reduction_fn_name)

        regions = mask.mask_image(image)  # TODO: line number
        if not regions:
            self._txt_log.error(
                "Not enough masked regions for resolution calculation - masking omitted!"
            )
            regions = [image]

        per_region_resolutions = [
            self._calculate_resolution_basic_mode(
                region, False, border_fraction, index
            ).resolution
            for (index, region) in enumerate(regions)
        ]

        return CriterionResult(
            resolution=region_reduction_fn(
                [x for x in per_region_resolutions if x is not np.isnan(x)]
            ),
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
        per_tile_results: CriterionPerTileResults,
    ) -> ResolutionMap:
        resolution_map = np.zeros_like(image, dtype=np.float64).view(ResolutionMap)
        for resolution, tile in zip(per_tile_results.resolution, tiles_coordinates):
            resolution_map[
                tile.y : tile.y + tile.height,
                tile.x : tile.x + tile.width,
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
                    x=x,
                    y=y,
                    width=tile_size_px,
                    height=tile_size_px,
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
        return image[tile.y : tile.y + tile.height, tile.x : tile.x + tile.width]

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
            x=border_x,
            y=border_y,
            width=width - 2 * border_x,
            height=height - 2 * border_y,
        )

    def _crop_image(self, image: Image, coordinates: CropCoordinates) -> Image:
        """
        Return the cropped region of the image.
        """
        return image[
            coordinates.y : coordinates.y + coordinates.height,
            coordinates.x : coordinates.x + coordinates.width,
        ]

    def _log_image_with_tiles(
        self,
        file: Path,
        image: Image,
        tiles_coordinates: Iterable[TileCoordinates],
        crop_coordinates: CropCoordinates | None,
    ) -> None:
        overlays = []
        for tile in tiles_coordinates:
            x, y = tile.x, tile.y
            # if the image was cropped, we have to move the tiles
            if crop_coordinates is not None:
                x += crop_coordinates.x
                y += crop_coordinates.y

            overlays.append(
                RectangleOverlay(
                    x,
                    y,
                    width=tile.width,
                    height=tile.height,
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
        crop_coordinates: CropCoordinates | None,
        best_tile: Image | None,
        map: ResolutionMap | None,
    ):
        self._txt_log.info("Logging criterion images.")
        self._log_image_with_tiles(
            Path(base_name), full_image, tiles_coordinates, crop_coordinates
        )
        if map is not None:
            self._img_log.save_image(
                Path(f"{base_name}_map"), map, None, "Resolution map"
            )
        if best_tile is not None:
            self._img_log.save_image(
                Path(f"{base_name}_best_tile"), best_tile, None, "Best tile"
            )
