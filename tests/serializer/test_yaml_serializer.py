# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from pathlib import Path
from typing import Any

import pytest
import yaml

from fibsem_maestro.serializer.yaml_serializer import YamlSerializer


def test_load_reads_valid_yaml(tmp_path: Path):
    file = tmp_path / "config.yaml"
    file.write_text("x: 10\ny: 20\n")

    data = YamlSerializer.load(file)

    assert data == {"x": 10, "y": 20}


def test_load_empty_file_returns_none_or_empty_dict(tmp_path: Path):
    file = tmp_path / "empty.yaml"
    file.write_text("")

    data = YamlSerializer.load(file)

    assert data is None or data == {}


def test_load_invalid_yaml_raises_error(tmp_path: Path):
    file = tmp_path / "invalid.yaml"
    file.write_text("::: not valid yaml :::")

    with pytest.raises(yaml.YAMLError):
        YamlSerializer.load(file)


def test_load_missing_file_raises_oserror(tmp_path: Path):
    file = tmp_path / "does_not_exist.yaml"

    with pytest.raises(OSError):
        YamlSerializer.load(file)


def test_write_writes_yaml(tmp_path: Path):
    file = tmp_path / "output.yaml"

    data = {"a": 1, "b": 2}
    YamlSerializer.write(file, data)

    content = file.read_text()
    assert "a: 1" in content
    assert "b: 2" in content


def test_write_overwrites_existing_file(tmp_path: Path):
    file = tmp_path / "out.yaml"

    file.write_text("old: data\n")

    YamlSerializer.write(file, {"new": 123})

    text = file.read_text()
    assert "new: 123" in text
    assert "old:" not in text


def test_write_to_unwritable_location_raises_oserror(tmp_path: Path):
    directory = tmp_path

    file = directory  # misuse: file is a directory, not a file

    with pytest.raises(OSError):
        YamlSerializer.write(file, {"a": 1})


def test_yaml_roundtrip(tmp_path: Path):
    file = tmp_path / "round.yaml"

    original: dict[str, Any] = {"x": 1, "y": 2, "child": {"a": 3}}

    YamlSerializer.write(file, original)
    loaded = YamlSerializer.load(file)

    assert loaded == original
