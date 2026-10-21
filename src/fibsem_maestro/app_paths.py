# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF

"""
The one folder holding every per-user file of FIBSEM Maestro.

This module imports only the standard library: `fibsem_maestro/__init__.py`
runs before any other module of the package is available.
"""

import contextlib
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Self

HOME_VARIABLE = "FIBSEM_MAESTRO_HOME"
"""Environment variable overriding the folder (used by tests)."""


@dataclass(frozen=True)
class AppPaths:
    """
    Locations of the per-user files: the last profiles and the logs.

    `config.toml` is not managed here; it is installation configuration and is
    always read from the installation folder.

    Attributes:
        root: The FIBSEM Maestro folder.
    """

    root: Path

    @classmethod
    def default(cls) -> Self:
        """
        The folder given by `FIBSEM_MAESTRO_HOME`, or else the installation folder.

        The installation folder is the parent of the virtual environment, i.e.
        the folder holding `config.toml`. In a development checkout this is the
        repository root.

        Returns:
            The paths rooted in that folder.
        """
        override = os.environ.get(HOME_VARIABLE)
        if override:
            return cls(Path(override))
        return cls(Path(sys.prefix).parent)

    @property
    def config_dir(self) -> Path:
        """Folder of the user configuration files (created on first access)."""
        return self._ensure(self.root / "config")

    @property
    def logs_dir(self) -> Path:
        """Folder of the application logs, e.g. `crash.log` (created on first access)."""
        return self._ensure(self.root / "logs")

    @staticmethod
    def _ensure(path: Path) -> Path:
        # a missing folder is created; failing to create it is not fatal here,
        # because every caller already handles failing to write into it
        with contextlib.suppress(OSError):
            path.mkdir(parents=True, exist_ok=True)
        return path
