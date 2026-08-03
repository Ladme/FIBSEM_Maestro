# Released under MIT License.
# Copyright (c) 2024-2026 CEMCOF

from __future__ import annotations

from typing import TYPE_CHECKING, Self

from fibsem_maestro.store.frame.frame_store import FrameStore

if TYPE_CHECKING:
    from collections.abc import Callable

    from fibsem_maestro.core.image import Image


class MemoryFrameStore(FrameStore):
    """
    `FrameStore` that holds frames in memory rather than writing to disk.

    `path()` always returns `None`, directing `grab_frame` to pass the
    acquired image to `save_to_memory` instead of writing it to disk.

    All instances sharing the same `_store` dict (created via `at()` or
    `next()`) read and write into that shared dict, keyed by slice index.

    Args:
        slice_provider: Callable returning the current slice index.
        _store: Shared frame store. When `None` a fresh dict is created,
            making this instance the root of a new store group.
    """

    def __init__(
        self,
        slice_provider: Callable[[], int],
        *,
        _store: dict[int, Image] | None = None,
    ) -> None:
        self._slice_provider = slice_provider
        self._store: dict[int, Image] = {} if _store is None else _store

    def path(self) -> None:
        return None

    def save_to_memory(self, image: Image) -> None:
        self._store[self._slice_provider()] = image

    def read(self) -> Image:
        idx = self._slice_provider()
        try:
            return self._store[idx]
        except KeyError:
            raise FileNotFoundError(f"No frame stored for slice {idx!r}") from None

    def exists(self) -> bool:
        return self._slice_provider() in self._store

    def raise_if_exists(self, exc_type: type[Exception], msg: str) -> None:
        if self.exists():
            raise exc_type(msg)

    def at(self, slice_index: int) -> Self:
        """
        Return a view of this store scoped to a specific slice.

        Args:
            slice_index: The slice index to address.

        Returns:
            A `MemoryFrameStore` sharing the same data store but addressing
            the given slice index.
        """
        return type(self)(lambda: slice_index, _store=self._store)

    @property
    def next(self) -> Self:
        """
        Return a view of this store scoped to the next slice.

        Returns:
            A `MemoryFrameStore` addressing the slice after the current one.
        """
        next_index = self._slice_provider() + 1
        return type(self)(lambda: next_index, _store=self._store)

    @property
    def slice(self) -> int:
        return self._slice_provider()
