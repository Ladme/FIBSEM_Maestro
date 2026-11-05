# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF

"""
Manufacturer libraries linked by the installer, such as Autoscript.
"""

import logging
import sys
import tomllib
from pathlib import Path

LIBRARIES_TABLE = "libraries"
"""Table holding one subtable per linked library."""

_log = logging.getLogger(__name__)


def installation_config() -> Path:
    """
    Locate the `config.toml` of the running installation.

    Returns:
        `config.toml` next to the virtual environment; in a development
        checkout, at the repository root.
    """
    return Path(sys.prefix).parent / "config.toml"


def read_linked_folders(config: Path) -> dict[str, Path]:
    """
    Read the folder of each linked library.

    Args:
        config: The `config.toml` to read.

    Returns:
        The folder of each linked library, by library key; empty if the file
        is missing or unreadable.
    """
    if not config.is_file():
        return {}

    try:
        with config.open("rb") as handle:
            data = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError) as error:
        _log.warning("Cannot read %s, so no libraries are linked: %s", config, error)
        return {}

    tables = data.get(LIBRARIES_TABLE, {})
    if not isinstance(tables, dict):
        _log.warning("Ignoring [%s] in %s: it is not a table.", LIBRARIES_TABLE, config)
        return {}

    folders: dict[str, Path] = {}
    for key, table in tables.items():
        path = table.get("path") if isinstance(table, dict) else None
        if not isinstance(path, str) or not path:
            _log.warning(
                "Ignoring the link of '%s' in %s: it has no path.", key, config
            )
            continue
        folders[key] = Path(path)
    return folders


def link_libraries(config: Path) -> dict[str, Path]:
    """
    Make the linked libraries importable by putting their folders on `sys.path`.

    A folder that does not exist is skipped with a warning.

    Args:
        config: The `config.toml` to read.

    Returns:
        The folders put on `sys.path`, by library key.
    """
    linked: dict[str, Path] = {}
    for key, folder in read_linked_folders(config).items():
        if not folder.is_dir():
            _log.warning("The folder linked for '%s' does not exist: %s", key, folder)
            continue
        entry = str(folder)
        if entry not in sys.path:
            sys.path.insert(0, entry)
        linked[key] = folder
    return linked
