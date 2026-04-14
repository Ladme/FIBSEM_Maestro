# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from abc import ABC, abstractmethod
from typing import Self

from fibsem_maestro.properties.global_properties import GlobalProperties


class PropsStore(ABC):
    """
    Abstract interface for a readable/writable store of microscope properties.
    """

    @abstractmethod
    def write(self, filename: str, props: GlobalProperties) -> None:
        """
        Serialize and persist properties of the microscope under the given filename.

        Args:
            filename: Target filename within the props directory of the addressed slice.
            props: The properties to serialize.
        """

    @abstractmethod
    def read(self, filename: str) -> GlobalProperties:
        """
        Deserialize and return previously written microscope properties.

        Args:
            filename: Filename within the props directory of the addressed slice.

        Returns:
            The deserialized properties instance.

        Raises:
            FileNotFoundError: If no file with that name has been written.
        """

    @abstractmethod
    def exists(self, filename: str) -> bool:
        """Return `True` if the given filename has been written to this slice.

        Args:
            filename: Filename to check within the props directory of the addressed slice.

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
        Get the index of the slice this PropsStore relates to.
        """
