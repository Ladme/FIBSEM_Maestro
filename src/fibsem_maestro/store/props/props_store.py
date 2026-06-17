# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from abc import ABC, abstractmethod
from typing import Self, TypeVar

from fibsem_maestro.properties.global_properties import GlobalProperties

TSelf = TypeVar("TSelf", bound="PropsStore")


class PropsStore(ABC):
    """Abstract interface for a readable/writable store of microscope properties."""

    @abstractmethod
    def write(self, filename: str, props: GlobalProperties) -> None:
        """
        Serialize and persist microscope properties under the given filename.

        Overwrites any existing file with the same name in the current slice
        directory.

        Args:
            filename: Target filename within the current slice directory.
            props: The properties to serialize.
        """

    @abstractmethod
    def read(self, filename: str) -> GlobalProperties:
        """
        Deserialize and return previously written microscope properties.

        Args:
            filename: Filename within the current slice directory.

        Returns:
            The deserialized `GlobalProperties` instance.

        Raises:
            FileNotFoundError: If no file with that name exists in the current
                slice directory.
        """

    @abstractmethod
    def copy_to(self, filename: str, to: TSelf) -> None:
        """
        Copy the given properties file to the target `PropsStore`.

        Args:
            filename: Filename within the current slice directory.
            to: The target `PropsStore` to copy the properties to.
        """

    @abstractmethod
    def exists(self, filename: str) -> bool:
        """
        Return `True` if the given filename exists in the current slice.

        Args:
            filename: Filename to check within the current slice directory.

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
            A `PropsStore` of the same concrete type addressing the given slice.
        """

    @property
    @abstractmethod
    def next(self) -> Self:
        """
        Return a view of this store scoped to the next slice.

        Returns:
            A `PropsStore` of the same concrete type addressing the slice
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
