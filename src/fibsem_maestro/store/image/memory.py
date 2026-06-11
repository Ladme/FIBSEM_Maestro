# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from collections.abc import Callable
from typing import Any, Self, TypeVar

from fibsem_maestro.core.image import _ImageBase
from fibsem_maestro.store.image.image_store import (
    ImageStore,
    _normalize_tif,
)

T = TypeVar("T", bound=_ImageBase[Any])


class MemoryImageStore(ImageStore[T]):
    """
    `ImageStore` that holds all images in memory rather than writing to disk.

    All instances sharing the same `_store` dict (created via `at()` or
    `next`) read and write into that shared dict, keyed by slice index and
    filename.

    Args:
        slice_provider: Callable returning the current slice index.
        cls: The concrete image class used to type-check stored values.
        _store: Shared data store. When `None`, a fresh dict is created,
            making this instance the root of a new store group.
    """

    def __init__(
        self,
        slice_provider: Callable[[], int],
        cls: type[T],
        *,
        _store: dict[tuple[int, str], T] | None = None,
    ) -> None:
        self._slice_provider = slice_provider
        self._cls = cls
        self._store: dict[tuple[int, str], T] = {} if _store is None else _store

    def _key(self, filename: str) -> tuple[int, str]:
        return (self._slice_provider(), _normalize_tif(filename))

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
        """
        Return a view of this store scoped to a specific slice.

        Args:
            slice_index: The slice index to address.

        Returns:
            A `MemoryImageStore` sharing the same data store but addressing
            the given slice index.
        """
        return type(self)(
            lambda: slice_index,
            self._cls,
            _store=self._store,
        )

    @property
    def next(self) -> Self:
        """
        Return a view of this store scoped to the next slice.

        Returns:
            A `MemoryImageStore` addressing the slice after the current one.
        """
        next_index = self._slice_provider() + 1
        return type(self)(
            lambda: next_index,
            self._cls,
            _store=self._store,
        )

    @property
    def slice(self) -> int:
        return self._slice_provider()
