# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from __future__ import annotations

import tomllib
from functools import cache
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _distribution_version
from pathlib import Path

PACKAGE_NAME = "fibsem-maestro"
_FALLBACK_VERSION = "0.0.0+unknown"


def _find_pyproject() -> Path | None:
    """
    Locate the project's `pyproject.toml` above this module.

    Returns:
        Path to the project's `pyproject.toml`, or None if not found.
    """
    for directory in Path(__file__).resolve().parents:
        candidate = directory / "pyproject.toml"
        if not candidate.is_file():
            continue
        if _project_table(candidate).get("name") == PACKAGE_NAME:
            return candidate
    return None


def _project_table(path: Path) -> dict[str, object]:
    """
    Read the `[project]` table of a TOML file.

    Args:
        path: Path to a `pyproject.toml` file.

    Returns:
        The `[project]` table, or an empty dict if the file is unreadable
        or malformed.
    """
    try:
        with path.open("rb") as handle:
            data = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError):
        return {}
    project = data.get("project")
    return project if isinstance(project, dict) else {}


@cache
def get_version() -> str:
    """
    Return the version of the FIBSEM Maestro package.

    Reads installed distribution metadata first, then `pyproject.toml`.

    Returns:
        The version string, or `"0.0.0+unknown"` if neither source is available.
    """
    try:
        return _distribution_version(PACKAGE_NAME)
    except PackageNotFoundError:
        pass

    pyproject = _find_pyproject()
    if pyproject is not None:
        version = _project_table(pyproject).get("version")
        if isinstance(version, str):
            return version

    return _FALLBACK_VERSION
