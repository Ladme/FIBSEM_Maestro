# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from abc import ABC, abstractmethod
from typing import Any, Generic, Self, TypeVar

from fibsem_maestro.core.image import _ImageBase

T = TypeVar("T", bound=_ImageBase[Any])


class ImageStore(ABC, Generic[T]):
    """
    Abstract interface for a readable/writable store of microscope image files.
    """

    @abstractmethod
    def write(self, filename: str, image: T) -> None:
        """
        Save an image under the given filename as a TIF file.

        Args:
            filename: Target filename within the configured directory of the
                addressed slice. The `.tif` extension is added automatically
                if omitted.
            image: The image instance to persist.
        """

    @abstractmethod
    def read(self, filename: str) -> T:
        """
        Load a previously written image.

        Args:
            filename: Filename within the configured directory of the addressed
                slice. The `.tif` extension is added automatically if omitted.

        Returns:
            The loaded image as an instance of the concrete type this store
            was initialised with.

        Raises:
            FileNotFoundError: If no image with that name has been written.
        """

    @abstractmethod
    def exists(self, filename: str) -> bool:
        """Return `True` if the given filename has been written to this slice.

        Args:
            filename: Filename to check within the configured directory of the
                addressed slice. The `.tif` extension is added automatically
                if omitted.

        Returns:
            `True` if the file exists, `False` otherwise.
        """

    @property
    @abstractmethod
    def next(self) -> Self:
        """
        Return a view of this store scoped to the next slice.

        Returns:
            A store of the same concrete type addressing the slice following the current slice.
        """

    @abstractmethod
    def at(self, slice_index: int) -> Self:
        """
        Return a view of this store scoped to a specific slice.

        Args:
            slice_index: The slice index to address.

        Returns:
            A store of the same concrete type addressing the given slice.
        """

    @property
    @abstractmethod
    def slice(self) -> int | None:
        """
        Get the index of the slice this ImageStore relates to.
        """


def normalize_tif(filename: str) -> str:
    """
    Ensure filename ends with the `.tif` extension.

    Args:
        filename: The raw filename provided by the caller.

    Returns:
        The filename with a guaranteed `.tif` suffix.
    """
    return filename if filename.endswith(".tif") else f"{filename}.tif"
