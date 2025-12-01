# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from typing import Any, Self

import numpy as np
from numpy.typing import NDArray


class Image(np.ndarray[Any, np.dtype[np.floating[Any]]]):
    pixel_size: int

    def __new__(cls, image: NDArray[np.floating], pixel_size: int) -> Self:
        obj = np.asarray(image).view(cls)
        obj.pixel_size = pixel_size
        return obj

    def __array_finalize__(self, obj: Any) -> None:
        """Called whenever the array is created."""
        if obj is None:
            return

        # preserve pixel_size when array is sliced or copied
        self.pixel_size = getattr(obj, "pixel_size", 1)

    def __getitem__(self, key: Any) -> Self:
        """Ensure slicing returns an Image instance."""
        result = super().__getitem__(key)

        return result.view(type(self))
