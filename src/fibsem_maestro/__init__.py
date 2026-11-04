# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF

import importlib
import pkgutil
import sys
import tomllib
import warnings
from pathlib import Path

from fibsem_maestro.app_paths import AppPaths

_ON_DEMAND_PACKAGES = ("fibsem_maestro.microscope.autoscript_control",)
"""Packages that need an optional dependency; imported only when used."""


def _configure_autoscript() -> None:
    """
    Make the linked Autoscript installation importable, if one is configured.

    Reads `[autoscript] path` from `config.toml` in the FIBSEM Maestro folder
    (see `AppPaths`). A missing file or entry is not an error: Maestro then runs
    without Autoscript, and selecting the Autoscript control fails with
    `AutoscriptNotAvailableError` when connecting.
    """
    config = AppPaths.default().root / "config.toml"
    if not config.is_file():
        return

    with config.open("rb") as handle:
        data = tomllib.load(handle)

    path = data.get("autoscript", {}).get("path")
    if not path:
        return

    if not Path(path).is_dir():
        warnings.warn(
            f"Autoscript folder '{path}' named in {config} does not exist.",
            stacklevel=2,
        )
        return

    if path not in sys.path:
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


_configure_autoscript()
_import_all_modules()
