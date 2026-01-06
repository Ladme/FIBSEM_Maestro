# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Generic, Self, TypeVar

import numpy as np

if TYPE_CHECKING:
    from numpy.typing import NDArray

TDType = TypeVar("TDType", bound=np.generic)


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

    def __getitem__(self, key: Any) -> Self:
        """Ensure slicing returns Image."""
        result = super().__getitem__(key)
        return result.view(type(self))


class Image8Bit(_ImageBase[np.uint8]):
    def __new__(cls, image: NDArray[np.uint8], pixel_size: float) -> Self:
        return super().__new__(cls, image, pixel_size)

    def __getitem__(self, key: Any) -> Self:
        """Ensure slicing returns Image8Bit."""
        result = super().__getitem__(key)
        return result.view(type(self))
