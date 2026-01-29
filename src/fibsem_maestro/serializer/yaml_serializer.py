# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

import contextlib
import inspect
from pathlib import Path
from typing import Any

import yaml
from yaml import CSafeDumper, CSafeLoader, MappingNode

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

        return data or {}

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


def public_property_dict(obj: object) -> dict[str, Any]:
    """
    Return a dictionary of readable public properties for an object.

    The function inspects the object's class for `@property` descriptors
    whose names do not start with an underscore and attempts to read their
    values from the instance. Properties that raise an exception when
    accessed are silently skipped.

    Args:
        obj (object): The object to introspect.

    Returns:
        dict[str, Any]: A dictionary mapping public property names to their current values.
            The dictionary may be empty if the object exposes no readable public properties.
    """
    result: dict[str, Any] = {}
    cls: type[object] = type(obj)

    for name, attr in inspect.getmembers(cls):
        if name.startswith("_"):
            continue

        if isinstance(attr, property) and attr.fget is not None:
            # skip properties that raise an exception
            with contextlib.suppress(Exception):
                result[name] = getattr(obj, name)

    return result


def generic_object_representer(
    dumper: CSafeDumper,
    data: object,
) -> yaml.nodes.Node:
    """
    YAML multi-representer that serializes objects via public properties.

    This representer acts as a fallback for objects that do not have a more
    specific representer registered.

    Args:
        dumper (CSafeDumper): The active YAML dumper instance.
        data (object): The object to serialize.

    Returns:
        Node: A YAML node representing the object as a mapping.

    Raises:
        RepresenterError: If the object exposes no readable public properties and therefore cannot be serialized.
    """
    props = public_property_dict(data)

    if not props:
        raise yaml.representer.RepresenterError("cannot represent an object", data)

    cls = type(data)
    tag = f"!{cls.__module__}.{cls.__qualname__}"

    return dumper.represent_mapping(tag, props)


def generic_object_constructor(
    loader: CSafeLoader,
    tag_suffix: str,
    node: MappingNode,
) -> object:
    """
    YAML multi-constructor that reconstructs objects from mappings.

    The constructor resolves the target class from the YAML tag suffix,
    imports the corresponding module, and instantiates the class using the
    mapping values found in the YAML node.

    Args:
        loader (CSafeLoader): The active YAML loader instance.
        tag_suffix (str): The class path portion of the YAML tag (`"module.ClassName"`).
        node (MappingNode): The YAML mapping node containing serialized property values.

    Returns:
        object: A newly constructed instance of the resolved class.

    Raises:
        ImportError: If the module cannot be imported.
        AttributeError: If the class cannot be found in the module.
        TypeError: If object construction fails due to invalid arguments.
    """
    module_name, _, class_name = tag_suffix.rpartition(".")
    module = __import__(module_name, fromlist=[class_name])
    cls = getattr(module, class_name)

    values: dict[str, Any] = loader.construct_mapping(node, deep=True)  # type: ignore

    if hasattr(cls, "create_from"):
        return cls.create_from(list(values.values()))

    return cls(**values)


CSafeDumper.add_multi_representer(object, generic_object_representer)
CSafeLoader.add_multi_constructor("!", generic_object_constructor)
