# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

"""
Link an existing Autoscript installation into the current Python environment.

This script creates a .pth file inside the active virtual environment's
site-packages directory that points to an existing Autoscript installation.

You only need to run it once after creating the virtual environment with `uv sync`.

Usage:
    uv run src/link_autoscript.py /path/to/autoscript
"""

from __future__ import annotations

import site
import sys
from pathlib import Path

# get the path to autoscript
try:
    autoscript_path = sys.argv[1]
except Exception as e:
    raise RuntimeError("Path to autoscript was not provided") from e

autoscript_path = Path(autoscript_path).resolve()

if not autoscript_path.exists():
    raise RuntimeError(f"Path to autoscript does not exist: {autoscript_path}")

# find site-packages of this Python interpreter
site_packages_dirs = site.getsitepackages()

if not site_packages_dirs:
    raise RuntimeError("Could not locate site-packages")

site_packages = Path(site_packages_dirs[0])

# write the .pth file
pth_file = site_packages / "autoscript.pth"
pth_file.write_text(str(autoscript_path) + "\n", encoding="utf-8")

# sanity check
sys.path.insert(0, str(autoscript_path))
try:
    from autoscript_sdb_microscope_client.sdb_microscope_client import (
        SdbMicroscopeClient,  # noqa: F401
    )
except ImportError as e:
    raise RuntimeError(
        "Autoscript could not be imported even after linking - check that you have provided the correct path"
    ) from e

print(f"Autoscript successfully linked via .pth file {pth_file}.")
