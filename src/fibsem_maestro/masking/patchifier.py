# Released under MIT License.
# Copyright (c) 2024-2026 CEMCOF


from dataclasses import dataclass
from typing import cast

import numpy as np
from numpy.typing import NDArray

# from patchify import patchify, unpatchify  # pyright: ignore[reportMissingTypeStubs]
from scipy.ndimage import (  # pyright: ignore[reportMissingTypeStubs]
    binary_fill_holes,
    zoom,
)

from fibsem_maestro.core.image import Image


@dataclass
class PatchifyData:
    original_shape: tuple[int, int]
    padded_shape: tuple[int, int]
    patch_grid_shape: tuple[int, int]


class Patchifier:
    """Handles downsampling, patchify, and unpatchify operations."""

    def __init__(
        self, patch_size: tuple[int, int], downsampling_factor: float, fill_holes: bool
    ):
        self._patch_size = patch_size
        self._downsampling_factor = downsampling_factor
        self._fill_holes = fill_holes

    def patchify(self, image: Image) -> tuple[NDArray[np.floating], PatchifyData]:
        original_shape = image.shape

        # downsample
        ds_image = zoom(image, 1.0 / self._downsampling_factor)

        # pad to multiples of patch size
        ph = (
            self._patch_size[0] - ds_image.shape[0] % self._patch_size[0]
        ) % self._patch_size[0]
        pw = (
            self._patch_size[1] - ds_image.shape[1] % self._patch_size[1]
        ) % self._patch_size[1]
        padded = np.pad(ds_image, ((0, ph), (0, pw)), mode="constant")

        # patchify
        patches = patchify(padded, self._patch_size, step=self._patch_size[0])
        grid_shape = patches.shape[:2]

        # flatten patches
        patches_flat = patches.reshape(-1, *self._patch_size)[..., np.newaxis]

        data = PatchifyData(
            original_shape=original_shape,
            padded_shape=cast("tuple[int, int]", padded.shape),
            patch_grid_shape=grid_shape,
        )

        return patches_flat, data

    def unpatchify(
        self, flat_patches: NDArray[np.floating], data: PatchifyData
    ) -> NDArray[np.floating]:
        """Reconstruct a mask image from predicted patches."""
        # reshape back into patch grid
        patch_grid = flat_patches.reshape(
            data.patch_grid_shape[0],
            data.patch_grid_shape[1],
            self._patch_size[0],
            self._patch_size[1],
        )

        # unpatchify
        padded_mask = unpatchify(patch_grid, data.padded_shape)

        # upsample back
        mask = zoom(padded_mask, self._downsampling_factor)

        # crop to original size
        mask = mask[: data.original_shape[0], : data.original_shape[1]]

        # convert to binary mask
        mask_binary = (mask > 0.5).astype(np.uint8)

        if self._fill_holes:
            mask_binary = binary_fill_holes(mask_binary).astype(np.uint8)

        return mask_binary
