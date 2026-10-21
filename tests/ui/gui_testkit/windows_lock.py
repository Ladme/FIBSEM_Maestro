# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF

"""Windows' refusal to delete open files, reproduced on Linux (for `WorkflowFiles(delete=...)`)."""

from __future__ import annotations

import os
import shutil
from pathlib import Path


class WindowsLikeLockError(PermissionError):
    """
    The `PermissionError` Windows raises when deleting an open file (WinError 32).

    Attributes:
        open_paths: The open files that blocked the deletion.
    """

    def __init__(self, blocked_path: Path, open_paths: list[Path]) -> None:
        self.open_paths = open_paths
        listed = ", ".join(str(p) for p in open_paths)
        super().__init__(32, f"Cannot delete {blocked_path}: open handles {listed}")


def _open_paths() -> set[Path]:
    """The files this process holds open (from `/proc/self/fd`)."""
    paths: set[Path] = set()
    for entry in Path("/proc/self/fd").iterdir():
        try:
            target = os.readlink(entry)  # noqa: PTH115
        except OSError:
            continue
        if target.startswith("/") and not target.endswith(" (deleted)"):
            paths.add(Path(target).resolve())
    return paths


def windows_like_delete(path: Path) -> None:
    """
    Delete a file or tree, refusing like Windows if this process holds a file in it open.

    Args:
        path: The file or directory to delete.

    Raises:
        WindowsLikeLockError: If the file, or a file inside the directory, is open.
    """
    target = path.resolve()
    if blocking := sorted(
        p for p in _open_paths() if p == target or target in p.parents
    ):
        raise WindowsLikeLockError(path, blocking)
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    else:
        path.unlink()
