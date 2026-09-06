# Released under MIT License.
# Copyright (c) 2024-2026 CEMCOF


from pathlib import Path
from typing import Any, TypeVar

from fibsem_maestro.action_context.action_context import ActionContext
from fibsem_maestro.core.image import _ImageBase
from fibsem_maestro.logging.image.image_logger import ImageLogger
from fibsem_maestro.logging.image.memory import MemoryImageLogger
from fibsem_maestro.logging.text.memory import MemoryTextLogger
from fibsem_maestro.logging.text.text_logger import TextLogger
from fibsem_maestro.slice.slice_view import SliceView
from fibsem_maestro.store.frame.frame_store import FrameStore
from fibsem_maestro.store.frame.memory import MemoryFrameStore
from fibsem_maestro.store.image.image_store import ImageStore
from fibsem_maestro.store.image.memory import MemoryImageStore
from fibsem_maestro.store.props.memory import MemoryPropsStore
from fibsem_maestro.store.props.props_store import PropsStore
from fibsem_maestro.store.settings.memory import MemorySettingsStore
from fibsem_maestro.store.settings.settings_store import SettingsStore
from fibsem_maestro.store.state.memory import MemoryStateStore
from fibsem_maestro.store.state.state_store import StateStore

T = TypeVar("T", bound=_ImageBase[Any])


class MemoryActionContext(ActionContext):
    """
    `ActionContext` backed by in-memory stores and loggers.

    Args:
        name: Human-readable action name used as the text logger name.
    """

    def __init__(self, name: str, slice: int = 0) -> None:
        super().__init__(slice)

        self._text_logger = MemoryTextLogger(
            slice_provider=lambda: self._counter.current,
            name=name,
        )
        self._image_logger = MemoryImageLogger(
            slice_provider=lambda: self._counter.current,
        )
        self._props_store = MemoryPropsStore(
            slice_provider=lambda: self._counter.current,
        )
        self._state_store = MemoryStateStore(
            slice_provider=lambda: self._counter.current,
        )
        self._settings_store = MemorySettingsStore(
            slice_provider=lambda: self._counter.current,
        )
        self._frame_store = MemoryFrameStore(
            slice_provider=lambda: self._counter.current,
        )

    def _make_view(self, slice_index: int) -> SliceView:
        # memory context has no real action dir
        # use sentinel path (is never accessed)
        return SliceView(Path(f"memory://{self.__class__.__name__}"), slice_index)

    @property
    def path_to_dir(self) -> Path | None:
        return None

    @property
    def text_logger(self) -> TextLogger:
        return self._text_logger

    @property
    def image_logger(self) -> ImageLogger:
        return self._image_logger

    @property
    def props_store(self) -> PropsStore:
        return self._props_store

    @property
    def state_store(self) -> StateStore:
        return self._state_store

    @property
    def settings_store(self) -> SettingsStore:
        return self._settings_store

    @property
    def frame_store(self) -> FrameStore:
        return self._frame_store

    def image_store(self, cls: type[T]) -> ImageStore[T]:
        """
        Create an in-memory image store for the given image type.

        Args:
            cls: The concrete image class to store.

        Returns:
            A ``MemoryImageStore`` addressing the current slice.
        """
        return MemoryImageStore(
            slice_provider=lambda: self._counter.current,
            cls=cls,
        )

    def change_action_dir(self, dir: Path) -> None:
        _ = dir
        pass
