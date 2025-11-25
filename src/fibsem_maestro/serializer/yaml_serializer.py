# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from pathlib import Path
from typing import Any

import yaml
from yaml import CSafeDumper, CSafeLoader

from .serializer import Serializer


class YamlSerializer(Serializer):
    """
    YAML-based implementation of the `Serializer` interface.
    """

    @classmethod
    def load(cls, file: Path) -> dict[str, Any]:
        """
        Load and deserialize YAML content from a file.

        Args:
            file: Path to the YAML file to read.

        Returns:
            A dictionary representing the deserialized YAML structure.

        Raises:
            yaml.YAMLError: If the file contains invalid YAML.
            OSError: If the file cannot be opened or read.
        """
        with file.open("r") as input:
            data: dict[str, Any] = yaml.load(input, Loader=CSafeLoader)

        return data

    @classmethod
    def write(cls, file: Path, data: dict[str, Any]) -> None:
        """
        Serialize a dictionary and write it to a YAML file.

        Args:
            file: Path to the YAML file to write.
            data: The data to serialize and store in the file.

        Raises:
            yaml.YAMLError: If serialization fails.
            OSError: If the file cannot be opened or written to.
        """
        with file.open("w") as output:
            yaml.dump(data, output, Dumper=CSafeDumper)
