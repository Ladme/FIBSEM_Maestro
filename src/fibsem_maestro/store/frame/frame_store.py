# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from abc import ABC, abstractmethod
from pathlib import Path

from fibsem_maestro.core.image import Image


class FrameStore(ABC):
    """Abstract interface controlling where acquired microscope frames are saved."""

    @abstractmethod
    def path(self) -> Path | None:
        """
        Return the path for saving the file, or `None` if image should be stored in memory.

        Returns:
            Destination path or `None` to instruct passing the frame to `save_to_memory` instead.
        """

    @abstractmethod
    def save_to_memory(self, image: Image) -> None:
        """
        Store the converted frame in memory.

        Args:
            image: The acquired frame.
        """

    @abstractmethod
    def exists(self) -> bool:
        """
        Return `True` if a frame for the current slice has already been saved.

        Returns:
            `True` if the frame exists, `False` otherwise.
        """

    @abstractmethod
    def raise_if_exists(self, ExceptionType: type[Exception]) -> None:
        """
        Raise an Exception if a frame for the current slice has already been saved.
        """

    @property
    @abstractmethod
    def slice(self) -> int | None:
        """
        Get the index of the slice this FrameStore relates to.
        """
