# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

import logging
from pathlib import Path
from typing import Any, TypeVar

from fibsem_maestro.action_context.action_context import ActionContext
from fibsem_maestro.core.image import _ImageBase
from fibsem_maestro.logging.image.file import FileImageLogger
from fibsem_maestro.logging.image.image_logger import ImageLogger
from fibsem_maestro.logging.text.file import FileTextLogger
from fibsem_maestro.logging.text.text_logger import TextLogger
from fibsem_maestro.slice.slice_view import SliceView
from fibsem_maestro.store.frame.file import FileFrameStore
from fibsem_maestro.store.frame.frame_store import FrameStore
from fibsem_maestro.store.image.file import FileImageStore
from fibsem_maestro.store.image.image_store import ImageStore
from fibsem_maestro.store.props.file import FilePropsStore
from fibsem_maestro.store.props.props_store import PropsStore
from fibsem_maestro.store.settings.file import FileSettingsStore
from fibsem_maestro.store.settings.settings_store import SettingsStore
from fibsem_maestro.store.state.file import FileStateStore
from fibsem_maestro.store.state.state_store import StateStore

T = TypeVar("T", bound=_ImageBase[Any])


class FileActionContext(ActionContext):
    """
    `ActionContext` backed by file-based stores and loggers.

    All data is persisted to disk under `action_dir`.

    Args:
        action_dir: Root directory for this action.
        name: Action name with underscores used as the text logger name.
        log_filename: Name of the log file written inside each slice directory.
            Defaults to `run.log`.
        log_level: Logging level for the `FileTextLogger`.
            Defaults to `logging.INFO`.
        frames_directory_name: Name of the flat frames subdirectory inside
            `action_dir`. Defaults to `frames`.
    """

    def __init__(
        self,
        action_dir: Path,
        name: str,
        slice: int = 0,
        log_filename: str = "run.log",
        log_level: int = logging.INFO,
        frames_directory_name: str = "frames",
    ) -> None:
        self._action_dir = action_dir
        self._frames_directory_name = frames_directory_name

        super().__init__(slice)

        self._text_logger = FileTextLogger(
            view_provider=lambda: self._current_view,
            name=name,
            filename=log_filename,
            level=log_level,
        )
        self._image_logger = FileImageLogger(
            view_provider=lambda: self._current_view,
        )
        self._props_store = FilePropsStore(
            view_provider=lambda: self._current_view,
        )
        self._state_store = FileStateStore(
            view_provider=lambda: self._current_view,
        )
        self._settings_store = FileSettingsStore(
            view_provider=lambda: self._current_view
        )
        self._frame_store = FileFrameStore(
            view_provider=lambda: self._current_view,
            directory_name=frames_directory_name,
        )

    def _make_view(self, slice_index: int) -> SliceView:
        return SliceView(self._action_dir, slice_index)

    @property
    def path_to_dir(self) -> Path | None:
        return self._action_dir

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
        Create a file-backed image store for the given image type.

        Args:
            cls: The concrete image class to read and write.

        Returns:
            A `FileImageStore` addressing the current slice.
        """
        return FileImageStore(
            view_provider=lambda: self._current_view,
            cls=cls,
        )

    def change_action_dir(self, dir: Path) -> None:
        if dir.exists():
            raise FileExistsError(f"Target action directory already exists: {dir}")

        self._action_dir.rename(dir)
        self._action_dir = dir
        self._current_view = self._make_view(self._current_view.slice_index)
