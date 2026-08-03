# Released under MIT License.
# Copyright (c) 2024-2026 CEMCOF


from collections.abc import Callable
from typing import Self

from fibsem_maestro.settings.base_settings import BaseSettings
from fibsem_maestro.store.settings.settings_store import SettingsStore


class MemorySettingsStore(SettingsStore):
    """
    `SettingsStore` that holds all data in memory rather than writing to disk.

    All instances sharing the same `_store` dict (created via `at()` or
    `next`) read and write into that shared dict, keyed by slice index and
    filename.

    Args:
        slice_provider: Callable returning the current slice index.
        _store: Shared data store. When `None` a fresh dict is created,
            making this instance the root of a new store group.
    """

    def __init__(
        self,
        slice_provider: Callable[[], int],
        *,
        _store: dict[tuple[int, str], object] | None = None,
    ) -> None:
        self._slice_provider = slice_provider
        self._store: dict[tuple[int, str], object] = {} if _store is None else _store

    def _key(self, filename: str) -> tuple[int, str]:
        return (self._slice_provider(), filename)

    def write(self, filename: str, settings: BaseSettings) -> None:
        self._store[self._key(filename)] = settings

    def read(self, filename: str, cls: type[BaseSettings]) -> BaseSettings:
        key = self._key(filename)
        try:
            return cls.model_validate(self._store[key])
        except KeyError:
            slice_idx, fname = key
            raise FileNotFoundError(
                f"No settings stored for slice {slice_idx!r}, filename {fname!r}"
            ) from None

    def copy_to(self, filename: str, to: Self) -> None:
        key = self._key(filename)
        try:
            value = self._store[key]
        except KeyError:
            slice_idx, fname = key
            raise FileNotFoundError(
                f"No settings stored for slice {slice_idx!r}, filename {fname!r}"
            ) from None

        to._store[to._key(filename)] = value

    def exists(self, filename: str) -> bool:
        return self._key(filename) in self._store

    def at(self, slice_index: int) -> Self:
        """
        Return a view of this store scoped to a specific slice.

        Args:
            slice_index: The slice index to address.

        Returns:
            A `MemoryStateStore` sharing the same data store but addressing the given slice index.
        """
        return type(self)(lambda: slice_index, _store=self._store)

    @property
    def next(self) -> Self:
        """
        Return a view of this store scoped to the next slice.

        Returns:
            A `MemoryStateStore` addressing the slice after the current one.
        """
        next_index = self._slice_provider() + 1
        return type(self)(lambda: next_index, _store=self._store)

    @property
    def slice(self) -> int:
        return self._slice_provider()
