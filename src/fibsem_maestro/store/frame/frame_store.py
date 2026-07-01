# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Self

if TYPE_CHECKING:
    from pathlib import Path

    from fibsem_maestro.core.image import Image


class FrameStore(ABC):
    """
    Abstract interface for storing frames acquired directly from the microscope.

    Unlike other stores, frames are not written into per-slice subdirectories.
    Instead they are stored flat in a dedicated directory, with the slice index
    embedded in the filename.
    """

    @abstractmethod
    def path(self) -> Path | None:
        """
        Return the path at which the frame should be saved, or `None`.

        When a `Path` is returned the microscope's internal layer writes
        the frame directly to that location. When `None` is returned the
        caller is responsible for passing the acquired `Image` to
        `save_to_memory`.

        Returns:
            A `Path` for direct-to-disk saving, or `None` for in-memory saving.
        """

    @abstractmethod
    def save_to_memory(self, image: Image) -> None:
        """
        Store an acquired frame in memory.

        Called by `grab_frame` only when `path()` returned `None`.

        Args:
            image: The acquired frame to store.
        """

    @abstractmethod
    def read(self) -> Image:
        """
        Load the frame for the current slice.

        Returns:
            The frame stored for the current slice.

        Raises:
            FileNotFoundError: If no frame exists for the current slice.
        """

    @abstractmethod
    def exists(self) -> bool:
        """
        Return `True` if a frame exists for the current slice.

        Returns:
            `True` if the frame exists, `False` otherwise.
        """

    @abstractmethod
    def raise_if_exists(self, exc_type: type[Exception], msg: str) -> None:
        """
        Raise an exception if a frame already exists for the current slice.

        Args:
            exc_type: The exception type to raise.
            msg: The message to pass to the exception.

        Raises:
            exc_type: If a frame already exists for the current slice.
        """

    @abstractmethod
    def at(self, slice_index: int) -> Self:
        """
        Return a view of this store scoped to a specific slice.

        Args:
            slice_index: The slice index to address.

        Returns:
            A `FrameStore` of the same concrete type addressing the given slice.
        """

    @property
    @abstractmethod
    def next(self) -> Self:
        """
        Return a view of this store scoped to the next slice.

        Returns:
            A `FrameStore` of the same concrete type addressing the slice after the current one.
        """

    @property
    @abstractmethod
    def slice(self) -> int:
        """
        The slice index this store is currently addressing.

        Returns:
            The current slice index.
        """
