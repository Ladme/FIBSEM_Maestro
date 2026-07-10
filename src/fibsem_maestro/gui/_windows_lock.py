# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

"""
Simulating Windows-like file/directory deletion behavior on Linux.
"""

import os
import shutil
from pathlib import Path


class WindowsLikeLockError(PermissionError):
    """
    A `PermissionError` naming the open handles that blocked a deletion.

    Behaves like the `PermissionError` (WinError 32) that Windows raises when a
    path is deleted while open, but also exposes the specific paths responsible.

    Attributes:
        blocked_path: The path whose deletion was refused.
        open_paths: The open handles that caused the refusal.
    """

    def __init__(self, blocked_path: Path, open_paths: list[Path]) -> None:
        self.blocked_path = blocked_path
        self.open_paths = open_paths
        listed = ", ".join(str(p) for p in open_paths)
        super().__init__(
            32,
            f"The process cannot access {blocked_path} because these handles "
            f"are still open: {listed}",
        )


def _open_paths() -> set[Path]:
    """
    Return the real filesystem paths this process currently holds open.

    Reads `/proc/self/fd`, skipping non-file descriptors (sockets, pipes,
    anon inodes) and entries for already-unlinked files.

    Returns:
        Absolute paths of files open by the current process.
    """
    paths: set[Path] = set()
    for entry in Path("/proc/self/fd").iterdir():
        try:
            target = os.readlink(entry)  # noqa: PTH115
        except OSError:
            continue
        if not target.startswith("/") or target.endswith(" (deleted)"):
            continue
        paths.add(Path(target))
    return paths


def _blocking_handles(path: Path, open_paths: set[Path]) -> list[Path]:
    """
    Return the open handles that would block deleting `path`, as on Windows.

    A file is blocked by an open handle to itself; a directory is blocked by
    any open handle to a file inside its tree.

    Args:
        path: The file or directory about to be deleted.
        open_paths: Paths currently held open by this process.

    Returns:
        The subset of `open_paths` blocking the deletion, sorted for stable output.
    """
    if path.is_dir():
        blocking = {p for p in open_paths if path == p or path in p.parents}
    else:
        target = path.resolve()
        blocking = {p for p in open_paths if p.resolve() == target}
    return sorted(blocking)


def windows_like_delete(path: Path) -> None:
    """
    Delete a file or tree, raising like Windows if a handle is still open.

    Mimics Windows' refusal to remove a path that this process has open, so
    tests on Linux fail exactly where the real deletion would. The raised error
    names the open handles responsible.

    Args:
        path: The file or directory to remove.

    Raises:
        WindowsLikeLockError: If the path is held open by this process.
    """
    if blocking := _blocking_handles(path, _open_paths()):
        raise WindowsLikeLockError(path, blocking)

    shutil.rmtree(path) if path.is_dir() else path.unlink()
