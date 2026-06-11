# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from collections.abc import Callable
from typing import Self, TypeVar

import yaml

from fibsem_maestro.action.state import ActionState
from fibsem_maestro.slice.slice_view import SliceView
from fibsem_maestro.store.state.state_store import StateStore

T = TypeVar("T", bound=object)


class FileStateStore(StateStore):
    """
    `StateStore` that reads and writes YAML files on disk.

    Files are written directly into the flat slice directory resolved by
    `view_provider`. Existing files with the same name are overwritten.

    Args:
        view_provider: Callable returning the `SliceView` to write to.
    """

    def __init__(self, view_provider: Callable[[], SliceView]) -> None:
        self._view_provider = view_provider

    def _path(self, filename: str):
        return self._view_provider().path() / filename

    def write(self, filename: str, state: ActionState) -> None:
        with self._path(filename).open("w") as f:
            yaml.safe_dump(state.model_dump(), f)

    def read(self, filename: str, cls: type[ActionState]) -> ActionState:
        path = self._path(filename)
        if not path.exists():
            raise FileNotFoundError(f"No state file found at {path!r}")
        with path.open() as f:
            data = yaml.safe_load(f)
        return cls.model_validate(data)

    def exists(self, filename: str) -> bool:
        return self._path(filename).exists()

    def at(self, slice_index: int) -> Self:
        """
        Return a view of this store scoped to a specific slice.

        Args:
            slice_index: The slice index to address.

        Returns:
            A `FileStateStore``writing to the given slice directory.
        """
        fixed = SliceView(self._view_provider().action_dir, slice_index)
        return type(self)(lambda: fixed)

    @property
    def next(self) -> Self:
        """
        Return a view of this store scoped to the next slice.

        Returns:
            A `FileStateStore` writing to the slice after the current one.
        """
        next_index = self._view_provider().slice_index + 1
        fixed = SliceView(self._view_provider().action_dir, next_index)
        return type(self)(lambda: fixed)

    @property
    def slice(self) -> int:
        return self._view_provider().slice_index
