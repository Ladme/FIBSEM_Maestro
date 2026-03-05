# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from pathlib import Path

from fibsem_maestro.core.image import Image
from fibsem_maestro.core.slice import SliceContext
from fibsem_maestro.store.frame.frame_store import FrameStore


class FileFrameStore(FrameStore):
    """
    FrameStore that persists frames as TIF/PNG files in a flat directory.

    Args:
        ctx: Slice context used to determine the current slice index.
        directory: Root directory where frames are stored.
    """

    def __init__(self, ctx: SliceContext, directory: Path) -> None:
        self._ctx = ctx
        self._directory = directory

    def _frame_path(self) -> Path:
        self._directory.mkdir(parents=True, exist_ok=True)
        return self._directory / f"slice_{self._ctx.current_slice:04d}.tif"

    def path(self) -> Path:
        return self._frame_path()

    def save_to_memory(self, image: Image) -> None:
        _ = image
        raise RuntimeError(
            "FileFrameStore.save_to_memory should never be called. This is a bug."
        )

    def exists(self) -> bool:
        return self._frame_path().exists()

    def raise_if_exists(self, ExceptionType: type[Exception]) -> None:
        if self.exists():
            raise ExceptionType(
                f"Frame for slice {self._ctx.current_slice} already exists."
            )

    @property
    def slice(self) -> int | None:
        return self._ctx.current_slice
