# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class Serializer(ABC):
    """
    Abstract base class defining a bidirectional serialization interface.
    """

    @classmethod
    @abstractmethod
    def load(cls, file: Path) -> dict[str, Any]:
        """
        Load and deserialize structured data from a file.

        Args:
            file: Path to the file to read from.

        Returns:
            A dictionary containing the deserialized data.

        Raises:
            NotImplementedError: If the method is not implemented by a subclass.
        """
        raise NotImplementedError(f"{cls.__name__}.load is not implemented")

    @classmethod
    @abstractmethod
    def write(cls, file: Path, data: dict[str, Any]) -> None:
        """
        Serialize and write structured data to a file.

        Args:
            file: Path to the file to write to.
            content: A dictionary representing the data to serialize.

        Raises:
            NotImplementedError: If the method is not implemented by a subclass.
        """
        raise NotImplementedError(f"{cls.__name__}.write is not implemented")
