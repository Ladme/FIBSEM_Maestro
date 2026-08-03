# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

import importlib
import pkgutil
import sys
import tomllib
from pathlib import Path


def _configure_autoscript() -> None:
    """Make the linked Autoscript installation importable."""

    config = Path(sys.prefix).parent / "config.toml"
    if not config.is_file():
        raise RuntimeError(f"No configuration found at {config}.")

    with config.open("rb") as handle:
        data = tomllib.load(handle)

    path = data.get("autoscript", {}).get("path")
    if path:
        sys.path.insert(0, path)


def _import_all_modules() -> None:
    """Auto-imports all modules in this package recursively to trigger class registration."""
    for module_info in pkgutil.walk_packages(
        path=__path__,
        prefix=f"{__name__}.",
    ):
        importlib.import_module(module_info.name)


_configure_autoscript()
_import_all_modules()
