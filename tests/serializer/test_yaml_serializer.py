# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF

from __future__ import annotations

from enum import Enum
from pathlib import Path

import pytest
import yaml
from yaml import CSafeDumper, CSafeLoader
from yaml.constructor import ConstructorError
from yaml.representer import RepresenterError

from fibsem_maestro.serializer.serializer import SerializerError
from fibsem_maestro.serializer.yaml_serializer import (
    YamlSerializer,
    public_property_dict,
)


class Sample:
    def __init__(self, x: int = 1, y: int = 2) -> None:
        self._x = x
        self._y = y

    @property
    def x(self) -> int:
        return self._x

    @property
    def y(self) -> int:
        return self._y

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Sample) and (self.x, self.y) == (other.x, other.y)


class Nested:
    def __init__(self, inner: Sample) -> None:
        self._inner = inner

    @property
    def inner(self) -> Sample:
        return self._inner


class FromList:
    def __init__(self, a: int, b: int) -> None:
        self._a = a
        self._b = b

    @property
    def a(self) -> int:
        return self._a

    @property
    def b(self) -> int:
        return self._b

    @classmethod
    def create_from(cls, values: list[int]) -> FromList:
        return cls(*values)


class NoProperties:
    pass


class Raising:
    @property
    def readable(self) -> int:
        return 1

    @property
    def broken(self) -> int:
        raise RuntimeError("not available without a connection")


class StrBeam(str, Enum):
    ELECTRON = "electron"
    ION = "ion"


class IntMode(Enum):
    FAST = 1
    SLOW = 2


def test_load_returns_parsed_mapping(tmp_path: Path):
    path = tmp_path / "settings.yaml"
    path.write_text("dwell_time_ns: 100\nbeam: electron\n")

    assert YamlSerializer.load(path) == {"dwell_time_ns": 100, "beam": "electron"}


def test_load_parses_nested_structures(tmp_path: Path):
    path = tmp_path / "settings.yaml"
    path.write_text("imaging:\n  resolution:\n    width: 1536\n    height: 1024\n")

    assert YamlSerializer.load(path) == {
        "imaging": {"resolution": {"width": 1536, "height": 1024}}
    }


def test_load_preserves_scalar_types(tmp_path: Path):
    path = tmp_path / "settings.yaml"
    path.write_text("i: 1\nf: 1.5\ns: text\nb: true\nn: null\n")

    assert YamlSerializer.load(path) == {
        "i": 1,
        "f": 1.5,
        "s": "text",
        "b": True,
        "n": None,
    }


def test_load_empty_file_returns_empty_dict(tmp_path: Path):
    path = tmp_path / "empty.yaml"
    path.write_text("")

    assert YamlSerializer.load(path) == {}


def test_load_comment_only_file_returns_empty_dict(tmp_path: Path):
    path = tmp_path / "comments.yaml"
    path.write_text("# nothing here\n")

    assert YamlSerializer.load(path) == {}


def test_load_explicit_null_returns_empty_dict(tmp_path: Path):
    path = tmp_path / "null.yaml"
    path.write_text("null\n")

    assert YamlSerializer.load(path) == {}


def test_load_empty_mapping_returns_empty_dict(tmp_path: Path):
    path = tmp_path / "empty_map.yaml"
    path.write_text("{}\n")

    assert YamlSerializer.load(path) == {}


def test_load_top_level_sequence_raises(tmp_path: Path):
    path = tmp_path / "list.yaml"
    path.write_text("- alpha\n- beta\n")

    with pytest.raises(SerializerError, match="Expected a mapping"):
        YamlSerializer.load(path)


def test_load_top_level_scalar_raises(tmp_path: Path):
    path = tmp_path / "scalar.yaml"
    path.write_text("42\n")

    with pytest.raises(SerializerError, match="Expected a mapping"):
        YamlSerializer.load(path)


def test_load_falsy_documents_raise_rather_than_becoming_empty(tmp_path: Path):
    for content in ("[]\n", "0\n", "false\n", "''\n"):
        path = tmp_path / "falsy.yaml"
        path.write_text(content)

        with pytest.raises(SerializerError, match="Expected a mapping"):
            YamlSerializer.load(path)


def test_load_missing_file_raises_os_error(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        YamlSerializer.load(tmp_path / "does_not_exist.yaml")


def test_load_directory_raises_os_error(tmp_path: Path):
    with pytest.raises(IsADirectoryError):
        YamlSerializer.load(tmp_path)


def test_load_invalid_yaml_raises_yaml_error(tmp_path: Path):
    path = tmp_path / "broken.yaml"
    path.write_text("a: [1, 2\nb: {\n")

    with pytest.raises(yaml.YAMLError):
        YamlSerializer.load(path)


def test_load_closes_the_file_handle(tmp_path: Path):
    path = tmp_path / "settings.yaml"
    path.write_text("a: 1\n")

    YamlSerializer.load(path)
    path.unlink()

    assert not path.exists()


def test_load_closes_the_file_handle_on_parse_error(tmp_path: Path):
    path = tmp_path / "broken.yaml"
    path.write_text("a: [1, 2\n")

    with pytest.raises(yaml.YAMLError):
        YamlSerializer.load(path)
    path.unlink()

    assert not path.exists()


def test_write_creates_file(tmp_path: Path):
    path = tmp_path / "out.yaml"

    YamlSerializer.write(path, {"a": 1})

    assert path.exists()


def test_write_then_load_round_trips_scalars(tmp_path: Path):
    path = tmp_path / "out.yaml"
    data = {"i": 1, "f": 1.5, "s": "text", "b": True, "n": None}

    YamlSerializer.write(path, data)

    assert YamlSerializer.load(path) == data


def test_write_then_load_round_trips_nested_containers(tmp_path: Path):
    path = tmp_path / "out.yaml"
    data = {"outer": {"inner": [1, 2, {"deep": "value"}]}}

    YamlSerializer.write(path, data)

    assert YamlSerializer.load(path) == data


def test_write_empty_dict_round_trips(tmp_path: Path):
    path = tmp_path / "out.yaml"

    YamlSerializer.write(path, {})

    assert YamlSerializer.load(path) == {}


def test_write_overwrites_existing_file(tmp_path: Path):
    path = tmp_path / "out.yaml"
    YamlSerializer.write(path, {"old": 1, "stale": 2})

    YamlSerializer.write(path, {"new": 3})

    assert YamlSerializer.load(path) == {"new": 3}


def test_write_converts_tuples_to_lists(tmp_path: Path):
    """Round-trip is not type-preserving for sequences."""
    path = tmp_path / "out.yaml"

    YamlSerializer.write(path, {"t": (1, 2)})

    assert YamlSerializer.load(path) == {"t": [1, 2]}


def test_write_produces_plain_text_yaml(tmp_path: Path):
    """Settings files are hand-edited on the instrument PC; no tags for plain data."""
    path = tmp_path / "out.yaml"

    YamlSerializer.write(path, {"dwell_time_ns": 100})

    assert path.read_text() == "dwell_time_ns: 100\n"


def test_write_str_enum_emits_its_value(tmp_path: Path):
    """`model_dump(mode='python')` hands over the member itself, not a str."""
    path = tmp_path / "out.yaml"

    YamlSerializer.write(path, {"beam": StrBeam.ELECTRON})

    assert path.read_text() == "beam: electron\n"


def test_write_int_enum_emits_its_value(tmp_path: Path):
    path = tmp_path / "out.yaml"

    YamlSerializer.write(path, {"mode": IntMode.SLOW})

    assert path.read_text() == "mode: 2\n"


def test_enum_round_trips_as_its_value_not_the_member(tmp_path: Path):
    """Lossy on purpose: pydantic re-coerces on load, matching mode='json'."""
    path = tmp_path / "out.yaml"

    YamlSerializer.write(path, {"beam": StrBeam.ION})

    assert YamlSerializer.load(path) == {"beam": "ion"}


def test_write_path_emits_a_plain_string(tmp_path: Path):
    path = tmp_path / "out.yaml"

    YamlSerializer.write(path, {"out_dir": Path("/data/scan")})

    assert YamlSerializer.load(path) == {"out_dir": "/data/scan"}


def test_write_nested_enum_and_path(tmp_path: Path):
    """The representers must apply inside containers, not just at the top level."""
    path = tmp_path / "out.yaml"

    YamlSerializer.write(
        path, {"actions": [{"beam": StrBeam.ION, "dir": Path("/data")}]}
    )

    assert YamlSerializer.load(path) == {"actions": [{"beam": "ion", "dir": "/data"}]}


def test_write_object_uses_import_path_as_tag(tmp_path: Path):
    path = tmp_path / "obj.yaml"

    YamlSerializer.write(path, {"s": Sample(3, 4)})

    assert f"!{Sample.__module__}.{Sample.__qualname__}" in path.read_text()


def test_write_object_serializes_public_properties(tmp_path: Path):
    path = tmp_path / "obj.yaml"

    YamlSerializer.write(path, {"s": Sample(3, 4)})

    contents = path.read_text()
    assert "x: 3" in contents
    assert "y: 4" in contents


def test_object_round_trips_through_write_and_load(tmp_path: Path):
    path = tmp_path / "obj.yaml"

    YamlSerializer.write(path, {"s": Sample(3, 4)})
    loaded = YamlSerializer.load(path)

    assert isinstance(loaded["s"], Sample)
    assert loaded["s"] == Sample(3, 4)


def test_nested_object_round_trips(tmp_path: Path):
    path = tmp_path / "obj.yaml"

    YamlSerializer.write(path, {"n": Nested(Sample(1, 2))})
    loaded = YamlSerializer.load(path)

    assert isinstance(loaded["n"], Nested)
    assert loaded["n"].inner == Sample(1, 2)


def test_object_in_a_list_round_trips(tmp_path: Path):
    path = tmp_path / "obj.yaml"

    YamlSerializer.write(path, {"samples": [Sample(1, 2), Sample(3, 4)]})
    loaded = YamlSerializer.load(path)

    assert loaded["samples"] == [Sample(1, 2), Sample(3, 4)]


def test_object_with_create_from_uses_that_constructor(tmp_path: Path):
    path = tmp_path / "obj.yaml"

    YamlSerializer.write(path, {"f": FromList(7, 8)})
    loaded = YamlSerializer.load(path)

    assert isinstance(loaded["f"], FromList)
    assert (loaded["f"].a, loaded["f"].b) == (7, 8)


def test_write_object_without_public_properties_raises(tmp_path: Path):
    with pytest.raises(RepresenterError):
        YamlSerializer.write(tmp_path / "obj.yaml", {"o": NoProperties()})


def test_write_object_skips_properties_that_raise(tmp_path: Path):
    """Instrument properties raise without a live connection; they are dropped."""
    path = tmp_path / "obj.yaml"

    YamlSerializer.write(path, {"r": Raising()})

    contents = path.read_text()
    assert "readable: 1" in contents
    assert "broken" not in contents


def test_public_property_dict_collects_public_properties():
    assert public_property_dict(Sample(3, 4)) == {"x": 3, "y": 4}


def test_public_property_dict_skips_properties_that_raise():
    assert public_property_dict(Raising()) == {"readable": 1}


def test_public_property_dict_returns_empty_for_plain_object():
    assert public_property_dict(NoProperties()) == {}


def test_public_property_dict_ignores_non_property_attributes():
    class WithMethods:
        attribute = 1

        def method(self) -> int:
            return 2

        @property
        def prop(self) -> int:
            return 3

    assert public_property_dict(WithMethods()) == {"prop": 3}


def test_public_property_dict_ignores_underscore_names():
    class WithPrivate:
        @property
        def visible(self) -> int:
            return 1

        @property
        def _hidden(self) -> int:
            return 2

    assert public_property_dict(WithPrivate()) == {"visible": 1}


def test_global_dumper_does_not_gain_the_object_representer():
    """Representers live on a private subclass; other libraries are unaffected."""
    with pytest.raises(RepresenterError):
        yaml.dump({"s": Sample(1, 2)}, Dumper=CSafeDumper)


def test_global_dumper_does_not_gain_the_enum_representer():
    with pytest.raises(RepresenterError):
        yaml.dump({"beam": StrBeam.ELECTRON}, Dumper=CSafeDumper)


def test_global_loader_does_not_gain_the_object_constructor():
    document = f"x: !{Sample.__module__}.{Sample.__qualname__} {{x: 1, y: 2}}\n"

    with pytest.raises(ConstructorError):
        yaml.load(document, Loader=CSafeLoader)
