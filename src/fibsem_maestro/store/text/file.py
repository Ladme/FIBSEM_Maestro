# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from collections.abc import Callable
from typing import Self

from fibsem_maestro.core.slice import SliceContext, SliceView
from fibsem_maestro.store.text.text_store import TextStore


class FileTextStore(TextStore):
    """
    TextStore that reads and writes files on disk.

    Args:
        ctx: Slice context used to resolve output directories.
    """

    def __init__(
        self,
        ctx: SliceContext,
        *,
        _view_provider: Callable[[], SliceView] | None = None,
    ) -> None:
        self._ctx = ctx
        self._view_provider: Callable[[], SliceView] = (
            _view_provider if _view_provider is not None else (lambda: ctx.current)
        )

    @property
    def _view(self) -> SliceView:
        return self._view_provider()

    def write(self, filename: str, data: str) -> None:
        (self._view.text() / filename).write_text(data)

    def read(self, filename: str) -> str:
        return (self._view.text() / filename).read_text()

    def exists(self, filename: str) -> bool:
        return (self._view.text() / filename).exists()

    def at(self, slice_index: int) -> Self:
        fixed: SliceView = self._ctx.at(slice_index)
        return type(self)(self._ctx, _view_provider=lambda: fixed)

    @property
    def next(self) -> Self:
        fixed: SliceView = self._ctx.next
        return type(self)(self._ctx, _view_provider=lambda: fixed)

    @property
    def slice(self) -> int | None:
        return self._view.slice_index
