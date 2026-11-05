# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF

"""Tests for the libraries linked by the installer."""

import logging
import sys
from typing import TYPE_CHECKING

import pytest

from fibsem_maestro import linked_libraries

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def config(tmp_path: Path) -> Path:
    """Path of a `config.toml`, not yet written."""
    return tmp_path / "config.toml"


@pytest.fixture
def folder(tmp_path: Path) -> Path:
    """An existing library folder."""
    path = tmp_path / "Autoscript"
    path.mkdir()
    return path


@pytest.fixture(autouse=True)
def isolated_sys_path(monkeypatch: pytest.MonkeyPatch) -> None:
    """Undo every change a test makes to `sys.path`."""
    monkeypatch.setattr(sys, "path", list(sys.path))


def _write(config: Path, text: str) -> None:
    config.write_text(text, encoding="utf-8")


def _link(table: str, folder: Path) -> str:
    # a literal string ('...') keeps Windows backslashes as they are
    return f"[{table}]\npath = '{folder}'\n"


def test_installation_config_is_next_to_the_virtual_environment(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(sys, "prefix", str(tmp_path / "runtime"))

    assert linked_libraries.installation_config() == tmp_path / "config.toml"


def test_read_linked_folders_is_empty_without_config(config: Path) -> None:
    # a development checkout or CI has no config.toml; that is not an error
    assert linked_libraries.read_linked_folders(config) == {}


def test_read_linked_folders_reads_the_installer_table(
    config: Path, folder: Path
) -> None:
    _write(config, _link("libraries.autoscript", folder))

    assert linked_libraries.read_linked_folders(config) == {"autoscript": folder}


def test_read_linked_folders_ignores_a_broken_file(
    config: Path, caplog: pytest.LogCaptureFixture
) -> None:
    _write(config, "[libraries.autoscript\n")

    with caplog.at_level(logging.WARNING):
        assert linked_libraries.read_linked_folders(config) == {}
    assert "Cannot read" in caplog.text


def test_read_linked_folders_skips_a_link_without_path(
    config: Path, folder: Path
) -> None:
    _write(
        config,
        "[libraries.other]\nversion = 1\n" + _link("libraries.autoscript", folder),
    )

    assert linked_libraries.read_linked_folders(config) == {"autoscript": folder}


def test_link_libraries_puts_the_folder_first_on_sys_path(
    config: Path, folder: Path
) -> None:
    _write(config, _link("libraries.autoscript", folder))

    assert linked_libraries.link_libraries(config) == {"autoscript": folder}
    assert sys.path[0] == str(folder)


def test_link_libraries_adds_a_folder_once(config: Path, folder: Path) -> None:
    _write(config, _link("libraries.autoscript", folder))

    linked_libraries.link_libraries(config)
    linked_libraries.link_libraries(config)

    assert sys.path.count(str(folder)) == 1


def test_link_libraries_skips_a_missing_folder(
    config: Path, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    missing = tmp_path / "uninstalled"
    _write(config, _link("libraries.autoscript", missing))

    with caplog.at_level(logging.WARNING):
        assert linked_libraries.link_libraries(config) == {}
    assert str(missing) not in sys.path
    assert "does not exist" in caplog.text
