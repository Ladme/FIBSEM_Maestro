# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF

import importlib
import pkgutil
import sys
import tomllib
from pathlib import Path

_ON_DEMAND_PACKAGES = ("fibsem_maestro.microscope.autoscript_control",)
"""Packages that need an optional dependency; imported only when used."""


def _configure_linked_libraries() -> None:
    """
    Make the manufacturer libraries linked by the installer importable.

    Raises:
        RuntimeError: If the installation has no `config.toml`.
    """
    config = Path(sys.prefix).parent / "config.toml"
    if not config.is_file():
        raise RuntimeError(f"No configuration found at {config}.")

    with config.open("rb") as handle:
        data = tomllib.load(handle)

    tables = data.get("libraries", {})
    tables = dict(tables) if isinstance(tables, dict) else {}
    legacy = data.get("autoscript")
    if isinstance(legacy, dict):
        tables.setdefault("autoscript", legacy)

    for table in tables.values():
        path = table.get("path") if isinstance(table, dict) else None
        if isinstance(path, str) and path:
            sys.path.insert(0, path)


def _import_all_modules() -> None:
    """Import every module of the package to trigger class registration."""
    for module_info in pkgutil.walk_packages(
        path=__path__,
        prefix=f"{__name__}.",
    ):
        if module_info.name.startswith(_ON_DEMAND_PACKAGES):
            continue
        importlib.import_module(module_info.name)


_configure_linked_libraries()
_import_all_modules()
