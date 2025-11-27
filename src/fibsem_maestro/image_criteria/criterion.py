# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from __future__ import annotations

from fibsem_maestro.image_criteria.functions import (
    CriterionRegistry,
)
from fibsem_maestro.image_criteria.numpy_registry import NumpyRegistry
from fibsem_maestro.settings.criterion_settings import CriterionSettings


class Criterion:
    def __init__(self, settings: CriterionSettings):
        self._settings = settings

        self._function = CriterionRegistry(self._settings.function)
        self._final_regions_resolution = NumpyRegistry(
            self._settings.final_regions_resolution
        )
        self._final_resolution = NumpyRegistry(self._settings.final_resolution)

        self._settings.on_change(self._update_criterion)

    def _update_criterion(self, settings: CriterionSettings) -> None:
        self._function = CriterionRegistry(settings.function)
        self._final_regions_resolution = NumpyRegistry(
            settings.final_regions_resolution
        )
        self._final_resolution = NumpyRegistry(settings.final_resolution)

    """
    def _tiles_resolution(
        self,
        img: Image,
        generate_map: bool = False,
        return_best_tile: bool = False,
        **kwargs: Any,
    ) -> np.floating:
        tile_size = self._settings.tile_size

        if min(img.shape) == 1 or len(img.shape) == 1:
            logging.debug("Line image does not support tiling")
            return self._function(img, self._settings)

        logging.info("Tiles resolution calculation...")
        # Apply resolution border to the acquired image
        if generate_map == False:
            self._img_with_border = self._crop_image_with_border(img)
        else:
            # do not apply bordering if resolution map needed
            self._img_with_border = img
            tiles_coordinates = self._generate_image_fractions(
                self._img_with_border, return_coordinates=True
            )
            resolution_map = np.zeros_like(self._img_with_border, dtype=np.float64)

        return 0.0
"""


"""

    def _old_tiles_resolution(
        self, img, generate_map=False, return_best_tile=False, **kwargs
    ):
        criterion_settings = self.settings("criterion_calculation", self.criterion_name)
        tile_size = self.settings(
            "criterion_calculation", self.criterion_name, "tile_size"
        )

        if min(img.shape) == 1 or len(img.shape) == 1:  # line
            logging.debug("Line image does not support tiling")
            return self.criterion_func(img, criterion_settings)

        logging.info("Tiles resolution calculation...")
        # Apply resolution border to the acquired image
        if generate_map == False:
            self.img_with_border = self._crop_image_with_border(img)
        else:
            # do not apply bordering if resolution map needed
            self.img_with_border = img
            tiles_coordinates = self._generate_image_fractions(
                self.img_with_border, return_coordinates=True
            )
            resolution_map = np.zeros_like(self.img_with_border, dtype=np.float64)

        self.tile_size_px = int(tile_size / self.pixel_size)
        self.tile_size_px -= self.tile_size_px % 4  # must be divisible by 4

        # Get resolution of each tile and calculate final resolution
        res_arr = []

        # if tile size = 0, not apply tilling
        if tile_size == 0:
            tiles = [self.img_with_border]
        else:
            tiles = self._generate_image_fractions(self.img_with_border)

        minimal_resolution = 1
        tile_img_best_res = None
        for tile_img in tiles:
            try:
                res = self.criterion_func(tile_img, criterion_settings)
                if generate_map:
                    coordinates_array = next(tiles_coordinates)
                    resolution_map[
                        coordinates_array[0] : coordinates_array[0]
                        + coordinates_array[2],
                        coordinates_array[1] : coordinates_array[1]
                        + coordinates_array[3],
                    ] = res
                if res < minimal_resolution:
                    minimal_resolution = res
                    tile_img_best_res = tile_img

            except Exception as e:
                logging.warning(
                    "Resolution calculation error on current tile. " + repr(e)
                )
                continue
            logging.info(f"Tile resolution: {res}")
            res_arr.append(res)

        logging.info(f"Image sectioned to {len(res_arr)} sections")

        if len(res_arr) == 0:
            logging.error("Resolution not computed")
            return 0
        else:
            res_arr = np.array(res_arr)
            res_arr = res_arr[~np.isnan(res_arr)]  # remove NaN
            final_res = self.final_resolution(
                res_arr
            )  # apply final function (like min)
            result = (final_res,)
            if generate_map:
                result = result + (resolution_map,)  # append result tuple
            if return_best_tile:
                result = result + (tile_img_best_res,)  # append result tuple
            return result"""
