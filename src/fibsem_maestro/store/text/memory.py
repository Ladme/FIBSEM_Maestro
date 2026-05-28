# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from collections.abc import Callable
from typing import Self

from fibsem_maestro.core.slice import SliceContext
from fibsem_maestro.store.text.text_store import TextStore


class MemoryTextStore(TextStore):
    """
    TextStore that holds all data in a dictionary rather than writing to disk.

    Args:
        ctx: Slice context used to determine the current slice index.
    """

    def __init__(
        self,
        ctx: SliceContext,
        *,
        _store: dict[tuple[int | None, str], str] | None = None,
        _slice_provider: Callable[[], int | None] | None = None,
    ) -> None:
        self._ctx = ctx
        self._store: dict[tuple[int | None, str], str] = (
            {} if _store is None else _store
        )
        self._slice_provider: Callable[[], int | None] = (
            _slice_provider
            if _slice_provider is not None
            else (lambda: ctx.current_slice)
        )

    def _key(self, filename: str) -> tuple[int | None, str]:
        return (self._slice_provider(), filename)

    def write(self, filename: str, data: str) -> None:
        self._store[self._key(filename)] = data

    def read(self, filename: str) -> str:
        key = self._key(filename)
        try:
            return self._store[key]
        except KeyError:
            slice_idx, fname = key
            raise FileNotFoundError(
                f"No text stored for slice {slice_idx!r}, filename {fname!r}"
            ) from None

    def exists(self, filename: str) -> bool:
        return self._key(filename) in self._store

    def at(self, slice_index: int) -> Self:
        return type(self)(
            self._ctx,
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
            _store=self._store,
            _slice_provider=lambda: slice_index,
        )

    @property
    def slice(self) -> int | None:
        return self._ctx.current_slice
