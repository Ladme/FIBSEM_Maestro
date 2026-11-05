# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF

import importlib
import pkgutil

from fibsem_maestro.linked_libraries import installation_config, link_libraries

_ON_DEMAND_PACKAGES = ("fibsem_maestro.microscope.autoscript_control",)
"""Packages that need an optional dependency; imported only when used."""


def _import_all_modules() -> None:
    """Import every module of the package to trigger class registration."""
    for module_info in pkgutil.walk_packages(
        path=__path__,
        prefix=f"{__name__}.",
    ):
        if module_info.name.startswith(_ON_DEMAND_PACKAGES):
            continue
        importlib.import_module(module_info.name)


link_libraries(installation_config())
_import_all_modules()
