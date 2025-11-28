# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from pathlib import Path
from typing import Self

from fibsem_maestro.serializer.serializer import Serializer
from fibsem_maestro.serializer.yaml_serializer import YamlSerializer

from .reactive import ReactiveModel


class BaseSettings(ReactiveModel):
    """
    Base class for configuration objects with file serialization support.
    """

    # forbid extra fields
    model_config = {"extra": "forbid"}

    @classmethod
    def from_file(
        cls, file: Path, SerializerCls: type[Serializer] = YamlSerializer
    ) -> Self:
        """
        Create a new settings instance by loading data from a file.

        Args:
            file: Path to the settings file.
            SerializerCls: Serializer class used to decode the file
                (default: `YamlSerializer`).

        Returns:
            A new `BaseSettings` instance containing the loaded data.

        Raises:
            OSError: If the file cannot be opened or read.
            Exception: Propagated from the serializer on parsing or decoding errors.
        """
        return cls(**SerializerCls.load(file))

    def to_file(
        self, file: Path, SerializerCls: type[Serializer] = YamlSerializer
    ) -> None:
        """
        Serialize this settings object and write it to a file.

        Args:
            file: Path to the output file.
            SerializerCls: Serializer class used to encode and write the data
                (default: `YamlSerializer`).

        Raises:
            OSError: If the file cannot be opened or written to.
            Exception: Propagated from the serializer on serialization failure.
        """
        SerializerCls.write(
            file,
            self.model_dump(),
        )

    def reload(
        self, file: Path, SerializerCls: type[Serializer] = YamlSerializer
    ) -> None:
        """
        Reload settings from a file into the current instance.

        The loaded values overwrite the existing fields, and the update is applied
        using the reactive `update()` method. This ensures that registered hooks
        are triggered exactly once, regardless of how many fields change.

        Args:
            file: Path to the settings file to load from.
            SerializerCls: Serializer class used to decode the file
                (default: `YamlSerializer`).

        Raises:
            OSError: If the file cannot be opened or read.
            Exception: Propagated from the serializer on parsing or decoding errors.
        """
        new_settings = type(self).from_file(file, SerializerCls)
        self.update(new_settings)
