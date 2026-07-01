# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Self

from fibsem_maestro.properties.global_properties import GlobalProperties
from fibsem_maestro.slice.slice_view import SliceView
from fibsem_maestro.store.props.props_store import PropsStore


class FilePropsStore(PropsStore):
    """
    `PropsStore` that reads and writes YAML files on disk.

    Files are written directly into the flat slice directory resolved by
    `view_provider`. Existing files with the same name are overwritten.

    Args:
        view_provider: Callable returning the `SliceView` to write to.
    """

    def __init__(self, view_provider: Callable[[], SliceView]) -> None:
        self._view_provider = view_provider

    def _path(self, filename: str) -> Path:
        return self._view_provider().path() / filename

    def write(self, filename: str, props: GlobalProperties) -> None:
        props.to_file(self._path(filename))

    def read(self, filename: str) -> GlobalProperties:
        return GlobalProperties.from_file(self._path(filename))

    def copy_to(self, filename: str, to: Self) -> None:
        src = self._path(filename)
        if not src.exists():
            raise FileNotFoundError(f"No props file found at {src!r}")

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
            A `FilePropsStore` writing to the given slice directory.
        """
        fixed = SliceView(self._view_provider().action_dir, slice_index)
        return type(self)(lambda: fixed)

    @property
    def next(self) -> Self:
        """
        Return a view of this store scoped to the next slice.

        Returns:
            A `FilePropsStore` writing to the slice after the current one.
        """
        next_index = self._view_provider().slice_index + 1
        fixed = SliceView(self._view_provider().action_dir, next_index)
        return type(self)(lambda: fixed)

    @property
    def slice(self) -> int:
        return self._view_provider().slice_index
