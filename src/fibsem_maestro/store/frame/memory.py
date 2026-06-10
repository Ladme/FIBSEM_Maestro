# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from __future__ import annotations

from typing import TYPE_CHECKING

from fibsem_maestro.store.frame.frame_store import FrameStore

if TYPE_CHECKING:
    from fibsem_maestro.core.image import Image
    from fibsem_maestro.core.slice import SliceContext


class MemoryFrameStore(FrameStore):
    """
    FrameStore that captures frames in memory without writing to disk.

    Args:
        ctx: Slice context used to determine the current slice index.
        frames: Shared dictionary to store frames, keyed by name and slice index.
        name: Name of the imaging action this store is scoped to, or `None` for the root store.
    """

    def __init__(
        self,
        ctx: SliceContext,
        frames: dict[str, dict[int | None, Image]] | None = None,
        name: str | None = None,
    ) -> None:
        self._ctx = ctx
        self._frames = frames if frames is not None else {}
        self._name = name
        if name is not None:
            self._frames.setdefault(name, {})

    def derive(self, name: str) -> MemoryFrameStore:
        return MemoryFrameStore(self._ctx, self._frames, name)

    def path(self) -> None:
        return None

    def save_to_memory(self, image: Image) -> None:
        assert self._name is not None, "Cannot save to root MemoryFrameStore."
        self._frames[self._name][self._ctx.current_slice] = image

    def exists(self) -> bool:
        assert self._name is not None, (
            "Cannot check existence on root MemoryFrameStore."
        )
        return self._ctx.current_slice in self._frames[self._name]

    def raise_if_exists(self, ExceptionType: type[Exception], action_name: str) -> None:
        if self.exists():
            raise ExceptionType(
                f"Frame for slice {self._ctx.current_slice} and action '{action_name}' already exists."
            )

    @property
    def slice(self) -> int | None:
        return self._ctx.current_slice
