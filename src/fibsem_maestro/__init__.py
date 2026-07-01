# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

import importlib
import pkgutil


def _import_all_modules() -> None:
    """Auto-imports all modules in this package recursively to trigger class registration."""
    for module_info in pkgutil.walk_packages(
        path=__path__,
        prefix=f"{__name__}.",
    ):
        importlib.import_module(module_info.name)


_import_all_modules()
