# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from pathlib import Path


class SliceView:
    """
    Immutable reference to a single slice directory on disk.

    A `SliceView` knows the directory it represents and creates it on demand
    when `path` is called.

    Args:
        action_dir: The action's root directory.
        slice_index: The index of the slice this view addresses.
    """

    def __init__(self, action_dir: Path, slice_index: int) -> None:
        self._action_dir = action_dir
        self._slice_index = slice_index

    @property
    def action_dir(self) -> Path:
        """
        The action's root directory, creating it if necessary.

        Returns:
            The `Path` to the action directory, guaranteed to exist.
        """
        self._action_dir.mkdir(parents=True, exist_ok=True)
        return self._action_dir

    @property
    def slice_index(self) -> int:
        """
        The slice index this view addresses.

        Returns:
            The integer slice index supplied at construction.
        """
        return self._slice_index

    def path(self) -> Path:
        """
        Return the slice directory path, creating it if necessary.

        Returns:
            The directory `action_dir/slice_NNNN/`, guaranteed to exist.
        """
        p = self._action_dir / f"slice_{self._slice_index:04d}"
        p.mkdir(parents=True, exist_ok=True)
        return p
