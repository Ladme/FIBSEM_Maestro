# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF

import sys
from pathlib import Path

import pytest

from fibsem_maestro.app_paths import HOME_VARIABLE, AppPaths


def test_app_paths_env_override(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(HOME_VARIABLE, str(tmp_path))
    paths = AppPaths.default()
    assert paths.root == tmp_path
    assert paths.config_dir == tmp_path / "config" and paths.config_dir.is_dir()
    assert paths.logs_dir == tmp_path / "logs" and paths.logs_dir.is_dir()


def test_app_paths_default_is_installation_folder(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(HOME_VARIABLE, raising=False)
    assert AppPaths.default().root == Path(sys.prefix).parent
