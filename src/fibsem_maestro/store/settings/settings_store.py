# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from abc import ABC, abstractmethod
from typing import Self, TypeVar

from fibsem_maestro.settings.base_settings import BaseSettings

T = TypeVar("T", bound=BaseSettings)
TSelf = TypeVar("TSelf", bound="SettingsStore")


class SettingsStore(ABC):
    """
    Abstract interface for a readable/writable store of action settings.
    """

    @abstractmethod
    def write(self, filename: str, settings: T) -> None:
        """
        Serialize a settings instance to YAML under the given filename.

        Overwrites any existing file with the same name in the current slice
        directory.

        Args:
            filename: Target filename within the current slice directory.
            settings: Settings instance to serialize.
        """

    @abstractmethod
    def read(self, filename: str, cls: type[T]) -> T:
        """
        Deserialize a previously written YAML file into a settings instance.

        Args:
            filename: Filename within the current slice directory.
            cls: The settings type to deserialize into.

        Returns:
            The deserialized settings instance.

        Raises:
            FileNotFoundError: If no file with that name exists in the current slice directory.
        """

    @abstractmethod
    def copy_to(self, filename: str, to: TSelf) -> None:
        """
        Copy the given settings file to the target `SettingsStore`.

        Args:
            filename: Filename within the current slice directory.
            to: The target `SettingsStore` to copy the settings to.
        """

    @abstractmethod
    def exists(self, filename: str) -> bool:
        """Return `True` if the given filename exists in the current slice.

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
            A `StateStore` of the same concrete type addressing the given slice.
        """

    @property
    @abstractmethod
    def next(self) -> Self:
        """
        Return a view of this store scoped to the next slice.

        Returns:
            A `StateStore` of the same concrete type addressing the slice
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
