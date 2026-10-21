# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF

"""Filesystem operations on workflow and action directories."""

import shutil
from collections.abc import Callable
from pathlib import Path

from fibsem_maestro.logging.text.file import close_all_log_files


def delete_path(path: Path) -> None:
    """
    Delete a file or a directory tree.

    Args:
        path: The file or directory to delete. A symbolic link is removed
            itself, never followed.

    Raises:
        OSError: If the path cannot be deleted (including `FileNotFoundError`).
    """
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    else:
        path.unlink()


class WorkflowFiles:
    """
    Filesystem operations on workflow and action directories.

    Every method first closes all per-slice log files (`close_all_log_files()`),
    so that no open handle blocks deletion on Windows. This is the only place in
    `ui` that deletes files. The only move is the action-directory move inside
    `Action.rename`, which `WorkflowSession.rename_action` calls right after
    `close_logs()`.

    Args:
        delete: Deletes one file or directory tree. Tests pass `windows_like_delete`
            to reproduce Windows locking on Linux.
    """

    def __init__(self, delete: Callable[[Path], None] = delete_path) -> None:
        self._delete = delete

    def close_logs(self) -> None:
        """Close all per-slice log files; used before `Action.rename` moves a directory."""
        close_all_log_files()

    def is_empty(self, directory: Path) -> bool:
        """
        Tell whether a directory has no children.

        Args:
            directory: The directory to inspect.

        Returns:
            True if the directory has no files or subdirectories.

        Raises:
            OSError: If the directory cannot be listed.
        """
        close_all_log_files()
        return not any(directory.iterdir())

    def clear(self, directory: Path) -> list[tuple[Path, OSError]]:
        """
        Delete every child of `directory`, carrying on past failures.

        Args:
            directory: The directory to empty; it is kept itself. A missing
                directory has no children, so nothing is deleted.

        Returns:
            Each child that could not be deleted, with its error, in listing
            order; empty on success.
        """
        close_all_log_files()
        if not directory.is_dir():
            return []

        failures: list[tuple[Path, OSError]] = []
        for child in sorted(directory.iterdir()):
            try:
                self._delete(child)
            except OSError as error:
                failures.append((child, error))
        return failures

    def delete_tree(self, path: Path) -> None:
        """
        Delete a file or a directory tree.

        Args:
            path: What to delete; a missing path is not an error.

        Raises:
            OSError: If the path exists but cannot be deleted.
        """
        close_all_log_files()
        if not path.exists() and not path.is_symlink():
            return
        try:
            self._delete(path)
        except FileNotFoundError:
            # deleted by someone else in the meantime: the goal is reached
            return

    def clear_except(self, directory: Path, keep: str) -> None:
        """
        Delete every child directory of `directory` except the one named `keep`.

        Files directly inside `directory` are kept.

        Args:
            directory: The directory whose subdirectories are deleted.
            keep: Name of the subdirectory to keep (e.g. "workflow").

        Raises:
            OSError: If a subdirectory cannot be deleted; the remaining ones
                are then left in place.
        """
        close_all_log_files()
        for child in sorted(directory.iterdir()):
            if child.is_dir() and child.name != keep:
                self._delete(child)
