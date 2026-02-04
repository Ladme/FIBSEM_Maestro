# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Generic, Self, TypeVar

import numpy as np

if TYPE_CHECKING:
    from pathlib import Path

    from autoscript_sdb_microscope_client.structures import (
        AdornedImage as AdornedImageAs,
    )
    from numpy.typing import NDArray

    from fibsem_maestro.core.scanning_area import RelativeScanningArea

TDType = TypeVar("TDType", bound=np.generic)


class ImageError(BaseException):
    """
    Exception raised for errors related to images.
    """

    pass


class _ImageBase(np.ndarray[Any, np.dtype[TDType]], Generic[TDType]):
    pixel_size: float

    def __new__(cls, image: NDArray[TDType], pixel_size: float) -> Self:
        obj = np.asarray(image).view(cls)
        obj.pixel_size = pixel_size
        return obj

    def __array_finalize__(self, obj: Any) -> None:
        """Called whenever the array is created."""
        if obj is None:
            return
        # preserve pixel_size when array is sliced or copied
        self.pixel_size = getattr(obj, "pixel_size", 1)

    def __getitem__(self, key: Any) -> Self:  # type: ignore
        """Ensure slicing returns an instance of the same type."""
        result = super().__getitem__(key)
        return result.view(type(self))

    def crop(self, relative_area: RelativeScanningArea) -> Self:
        """
        Crops the image to the specified relative scanning area.

        Converts the given relative scanning area to pixel coordinates and returns
        the corresponding subregion of the image. The cropped image retains the
        same pixel size as the original image.

        Args:
            relative_area (RelativeScanningArea): The relative scanning area specifying the region to crop.
                This area is defined in relative coordinates (0 to 1).

        Returns:
            Self: The cropped image as an instance of the same class as the original image.
        """
        pixel_area = relative_area.to_pixels(self.shape)
        return self[
            pixel_area.origin.y : pixel_area.origin.y + pixel_area.height,
            pixel_area.origin.x : pixel_area.origin.x + pixel_area.width,
        ]

    def save(self, file_name: Path) -> None:
        """
        Save the image in PNG format.
        """
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(
            figsize=(self.shape[1] / 100, self.shape[0] / 100), dpi=100
        )

        ax.imshow(self, cmap="gray", interpolation="nearest", vmin=0.0, vmax=1.0)
        ax.axis("off")
        fig.subplots_adjust(left=0, right=1, bottom=0, top=1)
        plt.savefig(file_name, format="png", dpi=100)


class Image(_ImageBase[np.floating[Any]]):
    def __new__(cls, image: NDArray[np.floating[Any]], pixel_size: float) -> Self:
        return super().__new__(cls, image, pixel_size)

    def to_8bit(self) -> Image8Bit:
        """Get an 8-bit copy of the image."""
        pixel_size = self.pixel_size
        output = self.copy()
        if np.max(output) > 255:
            output = output / np.max(output) * 255
        output = np.ascontiguousarray(np.uint8(output))
        return Image8Bit(output, pixel_size)

    @classmethod
    def from_autoscript(cls, as_image: AdornedImageAs) -> Self:
        """
        Construct a native Image from Autoscript's AdornedImage.
        """
        if (metadata := as_image.metadata) is None:
            raise ImageError(
                "Could not convert autoscript image. Metadata not available."
            )

        if (pixel_size := metadata.binary_result.pixel_size) is None:
            raise ImageError(
                "Could not convert autoscript image. Pixel size not available."
            )

        return cls(np.asarray(as_image.data), pixel_size.x)


class Image8Bit(_ImageBase[np.uint8]):
    def __new__(cls, image: NDArray[np.uint8], pixel_size: float) -> Self:
        return super().__new__(cls, image, pixel_size)
