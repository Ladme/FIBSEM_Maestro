# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF


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
        """
        Args:
            action_dir: The action's root directory.
            slice_index: The index of the slice this view addresses.

        Raises:
            ValueError: If `slice_index` is negative.
        """
        if slice_index < 0:
            raise ValueError(f"Slice index must not be negative, got {slice_index}.")

        self._action_dir = action_dir
        self._slice_index = slice_index

    @property
    def action_dir(self) -> Path:
        """
        The action's root directory.

        The directory is not created; use `path` to create the slice
        directory and its parents when writing.

        Returns:
            The `Path` to the action directory.
        """
        return self._action_dir

    @property
    def slice_index(self) -> int:
        """
        The slice index this view addresses.

        Returns:
            The integer slice index supplied at construction.
        """
        return self._slice_index

    @property
    def expected_path(self) -> Path:
        """
        The slice directory path, without creating it.

        Unlike `path`, this has no side effect, so it is safe for queries
        such as existence checks. The directory may not exist.

        Returns:
            The `Path` to `action_dir/slice_NNNN/`.
        """
        return self._action_dir / f"slice_{self._slice_index:04d}"

    def path(self) -> Path:
        """
        Return the slice directory path, creating it if necessary.

        Returns:
            The directory `action_dir/slice_NNNN/`, guaranteed to exist.
        """
        p = self.expected_path
        p.mkdir(parents=True, exist_ok=True)
        return p
