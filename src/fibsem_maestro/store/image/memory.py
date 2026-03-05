# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from collections.abc import Callable
from typing import Any, Self, TypeVar

from fibsem_maestro.core.image import _ImageBase
from fibsem_maestro.core.slice import SliceContext
from fibsem_maestro.store.image.image_store import ImageStore, normalize_tif

T = TypeVar("T", bound=_ImageBase[Any])


class MemoryImageStore(ImageStore[T]):
    """
    ImageStore that holds all images in a dictionary rather than writing to disk.
    """

    def __init__(
        self,
        ctx: SliceContext,
        cls: type[T],
        directory: str,
        *,
        _store: dict[tuple[int | None, str], T] | None = None,
        _slice_provider: Callable[[], int | None] | None = None,
    ) -> None:
        self._ctx = ctx
        self._cls = cls
        self._directory = directory
        self._store: dict[tuple[int | None, str], T] = {} if _store is None else _store
        self._slice_provider: Callable[[], int | None] = (
            _slice_provider
            if _slice_provider is not None
            else (lambda: ctx.current_slice)
        )

    def _key(self, filename: str) -> tuple[int | None, str]:
        return (self._slice_provider(), f"{self._directory}/{normalize_tif(filename)}")

    def write(self, filename: str, image: T) -> None:
        self._store[self._key(filename)] = image

    def read(self, filename: str) -> T:
        key = self._key(filename)
        try:
            return self._store[key]
        except KeyError:
            slice_idx, fname = key
            raise FileNotFoundError(
                f"No image stored for slice {slice_idx!r}, filename {fname!r}"
            ) from None

    def exists(self, filename: str) -> bool:
        return self._key(filename) in self._store

    def at(self, slice_index: int) -> Self:
        return type(self)(
            self._ctx,
            self._cls,
            self._directory,
            _store=self._store,
            _slice_provider=lambda: slice_index,
        )

    @property
    def next(self) -> Self:
        slice_index = (
            self._ctx.current_slice if self._ctx.current_slice is not None else None
        )
        return type(self)(
            self._ctx,
            self._cls,
            self._directory,
            _store=self._store,
            _slice_provider=lambda: slice_index,
        )

    @property
    def slice(self) -> int | None:
        return self._ctx.current_slice
