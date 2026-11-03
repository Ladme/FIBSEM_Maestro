# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF
#
from __future__ import annotations

import os
import subprocess
import sys
import textwrap
from pathlib import Path

import fibsem_maestro

SRC_DIR = Path(fibsem_maestro.__file__).resolve().parents[1]

_HIDE_AUTOSCRIPT = """
import importlib.abc, sys

class _HideAutoscript(importlib.abc.MetaPathFinder):
    def find_spec(self, name, path=None, target=None):
        if name.split(".")[0].startswith(("autoscript", "thermoscientific")):
            raise ModuleNotFoundError(f"No module named {name!r}", name=name)
        return None

sys.meta_path.insert(0, _HideAutoscript())
"""


def _run_without_autoscript(home: Path, body: str) -> subprocess.CompletedProcess[str]:
    """Run `body` in a new interpreter with Autoscript hidden and no config.toml."""
    env = dict(os.environ)
    env["FIBSEM_MAESTRO_HOME"] = str(home)
    env["PYTHONPATH"] = str(SRC_DIR)
    env["QT_QPA_PLATFORM"] = "offscreen"
    code = _HIDE_AUTOSCRIPT + textwrap.dedent(body)
    return subprocess.run(
        [sys.executable, "-c", code],
        env=env,
        cwd=home,
        capture_output=True,
        text=True,
        timeout=300,
    )


def test_package_imports_without_autoscript_or_config(tmp_path: Path) -> None:
    result = _run_without_autoscript(
        tmp_path,
        """
        import fibsem_maestro
        """,
    )
    assert result.returncode == 0, result.stderr


def test_every_module_imports_without_autoscript(tmp_path: Path) -> None:
    result = _run_without_autoscript(
        tmp_path,
        """
        import importlib, pkgutil
        import fibsem_maestro

        failed = []
        for info in pkgutil.walk_packages(fibsem_maestro.__path__, "fibsem_maestro."):
            if ".autoscript_control" in info.name:
                continue  # the Autoscript adapter itself may require Autoscript
            try:
                importlib.import_module(info.name)
            except ImportError as e:
                failed.append(f"{info.name}: {e}")
        assert not failed, failed
        """,
    )
    assert result.returncode == 0, result.stderr


def test_simulated_microscope_works_without_autoscript(tmp_path: Path) -> None:
    result = _run_without_autoscript(
        tmp_path,
        """
        from fibsem_maestro.logging.text.memory import MemoryTextLogger
        from fibsem_maestro.microscope.microscope import Microscope
        from fibsem_maestro.settings.microscope_settings import MicroscopeSettings

        m = Microscope(
            MicroscopeSettings(control="simulated", ip_address="localhost"),
            MemoryTextLogger(lambda: 0),
        )
        assert m.electron_beam.grab_frame().size > 0
        """,
    )
    assert result.returncode == 0, result.stderr


def test_autoscript_control_stays_selectable_and_fails_clearly(tmp_path: Path) -> None:
    result = _run_without_autoscript(
        tmp_path,
        """
        from fibsem_maestro.core.errors import AutoscriptNotAvailableError
        from fibsem_maestro.logging.text.memory import MemoryTextLogger
        from fibsem_maestro.microscope.microscope import Microscope
        from fibsem_maestro.microscope.registry import MICROSCOPE_CONTROLS
        from fibsem_maestro.settings.microscope_settings import MicroscopeSettings

        # saved settings naming the Autoscript control must still load
        assert "autoscript" in MICROSCOPE_CONTROLS
        settings = MicroscopeSettings(control="autoscript", ip_address="localhost")

        try:
            Microscope(settings, MemoryTextLogger(lambda: 0))
        except AutoscriptNotAvailableError:
            pass
        else:
            raise AssertionError("connecting must fail with AutoscriptNotAvailableError")
        """,
    )
    assert result.returncode == 0, result.stderr
