# Released under MIT License.
# Copyright (c) 2024-2026 CEMCOF

from abc import ABC, abstractmethod
from typing import Any, Generic, Self, TypeVar

from fibsem_maestro.core.image import _ImageBase

T = TypeVar("T", bound=_ImageBase[Any])
TSelf = TypeVar("TSelf", bound="ImageStore[Any]")


class ImageStore(ABC, Generic[T]):
    """Abstract interface for a readable/writable store of image files."""

    @abstractmethod
    def write(self, filename: str, image: T) -> None:
        """
        Save an image under the given filename.

        Overwrites any existing file with the same name in the current slice
        directory. The `.tif` extension is appended automatically if omitted.

        Args:
            filename: Target filename within the current slice directory.
            image: The image instance to persist.
        """

    @abstractmethod
    def read(self, filename: str) -> T:
        """
        Load a previously written image.

        Args:
            filename: Filename within the current slice directory. The
                `.tif` extension is appended automatically if omitted.

        Returns:
            The loaded image as an instance of `T`.

        Raises:
            FileNotFoundError: If no image with that name exists in the
                current slice directory.
        """

    @abstractmethod
    def copy_to(self, filename: str, to: TSelf) -> None:
        """
        Copy the image at the given filename to the target `ImageStore`.

        Args:
            filename: Filename within the current slice directory. The
                `.tif` extension is appended automatically if omitted.
            to: The target `ImageStore` to copy the image to.
        """

    @abstractmethod
    def exists(self, filename: str) -> bool:
        """
        Return `True` if the given filename exists in the current slice.

        Args:
            filename: Filename to check. The `.tif` extension is appended
                automatically if omitted.

        Returns:
            `True` if the file exists, `False` otherwise.
        """

    @abstractmethod
    def at(self, slice_index: int) -> Self:
        """
        Return a view of this store scoped to a specific slice.

        Args:
            slice_index: The slice index to address.

        Returns:
            An `ImageStore` of the same concrete type addressing the given
            slice.
        """

    @property
    @abstractmethod
    def next(self) -> Self:
        """
        Return a view of this store scoped to the next slice.

        Returns:
            An `ImageStore` of the same concrete type addressing the slice
            after the current one.
        """

    @property
    @abstractmethod
    def slice(self) -> int:
        """
        The slice index this store is currently addressing.

        Returns:
            The current slice index.
        """


def _normalize_tif(filename: str) -> str:
    """
    Ensure a filename ends with the `.tif` extension.

    Args:
        filename: The raw filename provided by the caller.

    Returns:
        The filename with a guaranteed `.tif` suffix.
    """
    return filename if filename.endswith(".tif") else f"{filename}.tif"
