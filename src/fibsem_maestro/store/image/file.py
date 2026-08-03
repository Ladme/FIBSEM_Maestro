# Released under MIT License.
# Copyright (c) 2024-2026 CEMCOF


import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Any, Self, TypeVar

import tifffile

from fibsem_maestro.core.format import ImageFormat
from fibsem_maestro.core.image import _ImageBase
from fibsem_maestro.slice.slice_view import SliceView
from fibsem_maestro.store.image.image_store import ImageStore, _normalize_tif

T = TypeVar("T", bound=_ImageBase[Any])


class FileImageStore(ImageStore[T]):
    """
    `ImageStore` that reads and writes TIF files on disk.

    Files are written directly into the flat slice directory resolved by
    `view_provider`. Existing files with the same name are overwritten.

    Args:
        view_provider: Callable returning the `SliceView` to write to.
        cls: The concrete image class used to deserialize loaded files.
    """

    def __init__(
        self,
        view_provider: Callable[[], SliceView],
        cls: type[T],
    ) -> None:
        self._view_provider = view_provider
        self._cls = cls

    def _path(self, filename: str) -> Path:
        return self._view_provider().path() / _normalize_tif(filename)

    def write(self, filename: str, image: T) -> None:
        image.save(self._path(filename), ImageFormat.TIF)

    def read(self, filename: str) -> T:
        path = self._path(filename)
        if not path.exists():
            raise FileNotFoundError(f"No image found at {path!r}")
        with tifffile.TiffFile(path) as tif:
            return self._cls.from_tiff(tif)

    def copy_to(self, filename: str, to: Self) -> None:
        src = self._path(filename)
        if not src.exists():
            raise FileNotFoundError(f"No image found at {src!r}")

        target = to._path(filename)

        shutil.copy(src, target)

    def exists(self, filename: str) -> bool:
        return self._path(filename).exists()

    def at(self, slice_index: int) -> Self:
        """
        Return a view of this store scoped to a specific slice.

        Args:
            slice_index: The slice index to address.

        Returns:
            A `FileImageStore` writing to the given slice directory.
        """
        fixed = SliceView(self._view_provider().action_dir, slice_index)
        return type(self)(lambda: fixed, self._cls)

    @property
    def next(self) -> Self:
        """
        Return a view of this store scoped to the next slice.

        Returns:
            A `FileImageStore` writing to the slice after the current one.
        """
        next_index = self._view_provider().slice_index + 1
        fixed = SliceView(self._view_provider().action_dir, next_index)
        return type(self)(lambda: fixed, self._cls)

    @property
    def slice(self) -> int:
        return self._view_provider().slice_index
