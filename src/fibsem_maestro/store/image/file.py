# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from collections.abc import Callable
from pathlib import Path
from typing import Any, Self, TypeVar

import tifffile

from fibsem_maestro.core.format import ImageFormat
from fibsem_maestro.core.image import _ImageBase
from fibsem_maestro.core.slice import SliceContext, SliceView
from fibsem_maestro.store.image.image_store import ImageStore, normalize_tif

T = TypeVar("T", bound=_ImageBase[Any])


class FileImageStore(ImageStore[T]):
    """
    ImageStore that reads and writes TIF files on disk.
    """

    def __init__(
        self,
        ctx: SliceContext,
        cls: type[T],
        directory: Path,
        *,
        _view_provider: Callable[[], SliceView] | None = None,
    ) -> None:
        self._ctx = ctx
        self._cls = cls
        self._directory = directory
        self._view_provider: Callable[[], SliceView] = (
            _view_provider if _view_provider is not None else (lambda: ctx.current)
        )

    @property
    def _view(self) -> SliceView:
        return self._view_provider()

    def _path(self, filename: str) -> Path:
        return self._view.custom(str(self._directory)) / normalize_tif(filename)

    def write(self, filename: str, image: T) -> None:
        image.save(self._path(filename), ImageFormat.TIF)

    def read(self, filename: str) -> T:
        path = self._path(filename)
        with tifffile.TiffFile(path) as tif:
            return self._cls.from_tiff(tif)

    def exists(self, filename: str) -> bool:
        return self._path(filename).exists()

    def at(self, slice_index: int) -> Self:
        fixed: SliceView = self._ctx.at(slice_index)
        return type(self)(
            self._ctx, self._cls, self._directory, _view_provider=lambda: fixed
        )

    @property
    def next(self) -> Self:
        fixed: SliceView = self._ctx.next
        return type(self)(
            self._ctx, self._cls, self._directory, _view_provider=lambda: fixed
        )

    @property
    def slice(self) -> int | None:
        return self._ctx.current_slice
