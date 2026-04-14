# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from fibsem_maestro.core.image import Image
from fibsem_maestro.core.slice import SliceContext
from fibsem_maestro.store.frame.frame_store import FrameStore


class MemoryFrameStore(FrameStore):
    """
    FrameStore that captures frames in memory without writing to disk.

    Args:
        ctx: Slice context used to determine the current slice index.
    """

    def __init__(self, ctx: SliceContext) -> None:
        self._ctx = ctx
        self.frames: dict[int | None, Image] = {}

    def path(self) -> None:
        return None

    def save(self, image: Image) -> None:
        self.frames[self._ctx.current_slice] = image

    def save_to_memory(self, image: Image) -> None:
        return self.save(image)

    def exists(self) -> bool:
        return self._ctx.current_slice in self.frames

    def raise_if_exists(self, ExceptionType: type[Exception]) -> None:
        if self.exists():
            raise ExceptionType(
                f"Frame for slice {self._ctx.current_slice} already exists."
            )

    @property
    def slice(self) -> int | None:
        return self._ctx.current_slice
