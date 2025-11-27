# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING

from fibsem_maestro.core.crop_coordinates import CropCoordinates
from fibsem_maestro.core.image import Image
from fibsem_maestro.core.tile_coordinates import TileCoordinates
from fibsem_maestro.image_criteria.error import CriterionError
from fibsem_maestro.image_criteria.functions import (
    CriterionRegistry,
)
from fibsem_maestro.image_criteria.numpy_registry import NumpyRegistry

if TYPE_CHECKING:
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
        self.name = name
        self._settings = settings
        self._txt_log = txt_log
        self._img_log = img_log

        self.criterion_images: list[Image] = []

        # fields set based on the properties of each image
        self._pixel_size: int | None = None
        self._tile_size_px: int | None = None
        self._image_without_border: Image | None = None

        # updateable fields set from settings
        self.function = CriterionRegistry(self._settings.function)
        self._final_regions_resolution = NumpyRegistry(
            self._settings.final_regions_resolution
        )
        self._final_resolution = NumpyRegistry(self._settings.final_resolution)
        self._tile_size: int = self._settings.tile_size
        self._border_fraction: float = self._settings.border

        self._settings.on_change(self._update_criterion)

    def iter_tile_coordinates(
        self,
        img: Image,
        overlap: float = 0.0,
    ) -> Iterable[TileCoordinates]:
        """
        Iterate over the coordinates of square tiles covering an image.

        This generator computes a grid of tile positions that scan the image in a
        sliding-window fashion. Tiles have a fixed size defined by
        `self._tile_size_px` and may optionally overlap. Each yielded
        `TileCoordinates` object encodes the top-left coordinate and size of the tile.

        The iteration proceeds row-by-row over the image until no further full tiles
        fit within the image bounds. Partial tiles (those extending beyond the
        image edge) are not generated.

        Args:
            img (Image):
                The input 2-D image array from which tile coordinates should be
                computed.
            overlap (float, optional):
                Fraction of overlap between adjacent tiles, in the range
                `0.0`-`1.0`.
                - `0.0` → tiles touch exactly
                - `0.5` → 50% overlap
                - `1.0` → tile origin does not move (all tiles identical)
                Defaults to `0.0`.

        Yields:
            TileCoordinates:
                The coordinates and dimensions of each tile.

        Raises:
            CriterionError:
                If `self._tile_size_px` has not been configured.
        """

        if self._tile_size_px is None:
            raise CriterionError("Tile size is not set.")

        step = int(self._tile_size_px * (1 - overlap))
        height, width = img.shape[:2]

        for x in range(0, height - self._tile_size_px + 1, step):
            for y in range(0, width - self._tile_size_px + 1, step):
                yield TileCoordinates(
                    x=x,
                    y=y,
                    width=self._tile_size_px,
                    height=self._tile_size_px,
                )

    def iter_tiles(
        self,
        img: Image,
        overlap: float = 0.0,
    ) -> Iterable[Image]:
        """
        Iterate over image tiles extracted from the input image.

        This generator yields the actual cropped image regions (tiles) corresponding
        to the spatial coordinates produced by `iter_tile_coordinates`. Each
        tile is a `tile_size_px x tile_size_px` NumPy array view into the original
        image.

        Tiles are returned in row-major order, starting at the top-left corner and
        progressing left-to-right, top-to-bottom. Only fully contained tiles are
        produced; regions extending beyond the image boundary are skipped.

        Args:
            img (Image):
                The full input 2-D image from which tiles should be extracted.
            overlap (float, optional):
                Fraction of overlap between adjacent tiles. Defaults to ``0.0``.

        Yields:
            Image:
                A tile extracted from the input image.
        """
        for tile in self.iter_tile_coordinates(img, overlap):
            yield img[
                tile.x : tile.x + tile.width,
                tile.y : tile.y + tile.height,
            ].view(Image)

    def compute_crop_coordinates(self, img: Image) -> CropCoordinates:
        """
        Compute the crop region based on the configured border fraction.

        Args:
            img (Image):
                Input 2-D image array.

        Returns:
            CropCoordinates:
                Coordinates and dimensions of the cropped region.
        """
        height, width = img.shape[:2]
        border_x = int(height * self._border_fraction)
        border_y = int(width * self._border_fraction)

        return CropCoordinates(
            x=border_x,
            y=border_y,
            width=height - 2 * border_x,
            height=width - 2 * border_y,
        )

    def crop_image(self, img: Image) -> Image:
        """Return the cropped region of an image based on border settings.

        The crop geometry is computed by `compute_crop_coordinates`.

        Args:
            img (Image):
                Input 2-D image array.

        Returns:
            Image:
                The cropped image region.
        """
        coords = self.compute_crop_coordinates(img)
        return img[
            coords.x : coords.x + coords.width,
            coords.y : coords.y + coords.height,
        ].view(Image)

    def _update_criterion(self, settings: CriterionSettings) -> None:
        self.function = CriterionRegistry(settings.function)
        self._final_regions_resolution = NumpyRegistry(
            settings.final_regions_resolution
        )
        self._final_resolution = NumpyRegistry(settings.final_resolution)
        self._tile_size = self._settings.tile_size
        self._border_fraction = self._settings.border

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
