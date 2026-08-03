# Released under MIT License.
# Copyright (c) 2024-2026 CEMCOF

from __future__ import annotations

from typing import TYPE_CHECKING, Self

import tifffile

from fibsem_maestro.core.image import Image
from fibsem_maestro.slice.slice_view import SliceView
from fibsem_maestro.store.frame.frame_store import FrameStore

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path


class FileFrameStore(FrameStore):
    """
    `FrameStore` that persists frames as TIF files in a flat directory.

    `path()` returns the destination path for the current slice, directing
    the internal microscope layer to write directly to disk.

    `save_to_memory()` should never be called on this implementation.

    Frames are stored as `slice_NNNN.tif` directly inside a dedicated
    subdirectory of the action directory. The action directory is derived
    from the `SliceView` returned by `view_provider`.

    Args:
        view_provider: Callable returning the current `SliceView`.
        directory_name: Name of the frames subdirectory within the action
            directory. Defaults to `"frames"`.
    """

    def __init__(
        self,
        view_provider: Callable[[], SliceView],
        directory_name: str = "frames",
    ) -> None:
        self._view_provider = view_provider
        self._directory_name = directory_name

    def _frame_path(self) -> Path:
        frames_dir = self._view_provider().action_dir / self._directory_name
        frames_dir.mkdir(parents=True, exist_ok=True)
        return frames_dir / f"slice_{self._view_provider().slice_index:04d}.tif"

    def path(self) -> Path:
        return self._frame_path()

    def save_to_memory(self, image: Image) -> None:
        _ = image
        raise RuntimeError(
            "FileFrameStore.save_to_memory should never be called - "
            "path() always returns a Path. This is a bug."
        )

    def read(self) -> Image:
        path = self._frame_path()
        if not path.exists():
            raise FileNotFoundError(f"No frame found at {path!r}")
        with tifffile.TiffFile(path) as tif:
            return Image.from_tiff(tif)

    def exists(self) -> bool:
        return self._frame_path().exists()

    def raise_if_exists(self, exc_type: type[Exception], msg: str) -> None:
        if self.exists():
            raise exc_type(msg)

    def at(self, slice_index: int) -> Self:
        """
        Return a view of this store scoped to a specific slice.

        Args:
            slice_index: The slice index to address.

        Returns:
            A `FileFrameStore` addressing the given slice index.
        """
        fixed = SliceView(self._view_provider().action_dir, slice_index)
        return type(self)(lambda: fixed, self._directory_name)

    @property
    def next(self) -> Self:
        """Return a view of this store scoped to the next slice.

        Returns:
            A `FileFrameStore` addressing the slice after the current one.
        """
        next_index = self._view_provider().slice_index + 1
        fixed = SliceView(self._view_provider().action_dir, next_index)
        return type(self)(lambda: fixed, self._directory_name)

    @property
    def slice(self) -> int:
        return self._view_provider().slice_index
