# Released under MIT License.
# Copyright (c) 2024-2026 CEMCOF


from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, TypeVar

from fibsem_maestro.core.image import _ImageBase
from fibsem_maestro.logging.image.image_logger import ImageLogger
from fibsem_maestro.logging.text.text_logger import TextLogger
from fibsem_maestro.slice.slice_counter import SliceCounter
from fibsem_maestro.slice.slice_view import SliceView
from fibsem_maestro.store.frame.frame_store import FrameStore
from fibsem_maestro.store.image.image_store import ImageStore
from fibsem_maestro.store.props.props_store import PropsStore
from fibsem_maestro.store.settings.settings_store import SettingsStore
from fibsem_maestro.store.state.state_store import StateStore

T = TypeVar("T", bound=_ImageBase[Any])


class ActionContext(ABC):
    """
    Abstract base providing slice navigation and access to all logging and
    storage resources for a single action.

    Concrete subclasses decide which implementations (file or memory) are
    used. Actions are written against this interface and are therefore
    independent of the storage backend.
    """

    def __init__(self, slice: int = 0) -> None:
        self._counter = SliceCounter(slice)
        self._current_view = self._make_view(self._counter.current)

    @abstractmethod
    def _make_view(self, slice_index: int) -> SliceView:
        """
        Construct a `SliceView` for the given slice index.

        Subclasses must implement this to supply the action directory.

        Args:
            slice_index: The slice index to construct a view for.

        Returns:
            A `SliceView` addressing the given slice.
        """

    def advance(self) -> SliceView:
        """
        Increment the slice counter and return the new `SliceView`.

        Updates the active `SliceView` so all stores and loggers
        automatically begin addressing the new slice on their next call.

        Returns:
            The `SliceView` for the newly activated slice.
        """
        new_index = self._counter.advance()
        self._current_view = self._make_view(new_index)
        return self._current_view

    @property
    def current_view(self) -> SliceView:
        """
        The `SliceView` for the currently active slice.

        Returns:
            The active `SliceView`.
        """
        return self._current_view

    @property
    def slice(self) -> int:
        """
        The currently active slice index.

        Returns:
            The current slice index.
        """
        return self._counter.current

    @property
    @abstractmethod
    def path_to_dir(self) -> Path | None:
        """
        The path to the directory containing this action's files.

        Returns:
            The path to the directory, or `None` if not available.
        """

    @property
    @abstractmethod
    def text_logger(self) -> TextLogger:
        """
        The text logger for this action.

        Returns:
            A `TextLogger` writing to the current slice.
        """

    @property
    @abstractmethod
    def image_logger(self) -> ImageLogger:
        """
        The image logger for this action.

        Returns:
            An `ImageLogger` writing to the current slice.
        """

    @property
    @abstractmethod
    def props_store(self) -> PropsStore:
        """
        The props store for this action.

        Returns:
            A `PropsStore` addressing the current slice.
        """

    @property
    @abstractmethod
    def state_store(self) -> StateStore:
        """
        The state store for this action.

        Returns:
            A `StateStore` addressing the current slice.
        """

    @property
    @abstractmethod
    def settings_store(self) -> SettingsStore:
        """
        The settings store for this action.

        Returns:
            A `SettingsStore` addressing the current slice.
        """

    @property
    @abstractmethod
    def frame_store(self) -> FrameStore:
        """
        The frame store for this action.

        Returns:
            A `FrameStore` addressing the current slice.
        """

    @abstractmethod
    def image_store(self, cls: type[T]) -> ImageStore[T]:
        """
        Create an image store for the given image type.

        Args:
            cls: The concrete image class to read and write.

        Returns:
            An `ImageStore` addressing the current slice.
        """

    @abstractmethod
    def change_action_dir(self, dir: Path) -> None:
        """
        Change the action directory to the given path.

        This also moves contents of the original directory to the new one.

        When working in-memory, this method does nothing.

        Args:
            dir: The new action directory path.
        """

    def set_slice(self, slice_index: int) -> SliceView:
        """
        Set the slice counter to an explicit index.

        All stores and loggers begin addressing the new slice on their next
        call, so this changes which files the action reads and writes.

        Args:
            slice_index: The slice index to activate. Must not be negative.

        Returns:
            The `SliceView` for the newly activated slice.

        Raises:
            ValueError: If `slice_index` is negative.
        """
        if slice_index < 0:
            raise ValueError(f"Slice index must not be negative, got {slice_index}.")
        self._counter = SliceCounter(slice_index)
        self._current_view = self._make_view(self._counter.current)
        return self._current_view

    def reset(self) -> SliceView:
        """
        Reset the slice counter to 0 and return the new `SliceView`.

        Returns:
            The `SliceView` for the current slice.
        """
        return self.set_slice(0)
