# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from abc import ABC, abstractmethod
from typing import Self


class TextStore(ABC):
    """
    Abstract interface for a readable/writable store of any textual data.
    """

    @abstractmethod
    def write(self, filename: str, data: str) -> None:
        """
        Write the given data under the given filename.

        Args:
            filename: Target filename within the text data directory of the addressed slice.
            data: Serialized data to write.
        """

    @abstractmethod
    def read(self, filename: str) -> str:
        """
        Read the previously written data.

        Args:
            filename: Filename within the text data directory of the addressed slice.

        Returns:
            The read data.

        Raises:
            FileNotFoundError: If no file with that name has been written.
        """

    @abstractmethod
    def exists(self, filename: str) -> bool:
        """Return `True` if the given filename has been written to this slice.

        Args:
            filename: Filename to check within the text data directory of the addressed slice.

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
