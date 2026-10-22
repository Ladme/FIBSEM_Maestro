# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF

"""`WorkflowFiles`: deleting workflow data, with Windows' locking semantics in mind."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from gui_testkit.windows_lock import WindowsLikeLockError, windows_like_delete

from fibsem_maestro.action_context.file import FileActionContext
from fibsem_maestro.ui.app.files import WorkflowFiles

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def windows_files() -> WorkflowFiles:
    return WorkflowFiles(windows_like_delete)


@pytest.fixture
def tree(tmp_path: Path) -> Path:
    """`root/` with `a/deep/file.txt`, `b/`, `workflow/` and `top.txt`."""
    root = tmp_path / "root"
    (root / "a" / "deep").mkdir(parents=True)
    (root / "a" / "deep" / "file.txt").write_text("x")
    (root / "b").mkdir()
    (root / "workflow").mkdir()
    (root / "top.txt").write_text("y")
    return root


def names(directory: Path) -> list[str]:
    return sorted(p.name for p in directory.iterdir())


def test_windows_like_delete_refuses_open_file(tree: Path) -> None:
    with (tree / "a" / "deep" / "file.txt").open(), pytest.raises(WindowsLikeLockError):
        windows_like_delete(tree / "a")
    windows_like_delete(tree / "a")
    assert not (tree / "a").exists()


def test_files_clear_deletes_children_and_keeps_directory(tree: Path) -> None:
    assert WorkflowFiles().clear(tree) == []
    assert tree.is_dir()
    assert names(tree) == []


def test_files_clear_returns_failures_and_carries_on(
    tree: Path, windows_files: WorkflowFiles
) -> None:
    with (tree / "a" / "deep" / "file.txt").open():
        failures = windows_files.clear(tree)

    assert [(path.name, type(error)) for path, error in failures] == [
        ("a", WindowsLikeLockError)
    ]
    assert names(tree) == ["a"]


def test_files_clear_missing_directory_has_nothing_to_delete(tmp_path: Path) -> None:
    assert WorkflowFiles().clear(tmp_path / "missing") == []


def test_files_close_log_files_before_deleting(
    tmp_path: Path, windows_files: WorkflowFiles
) -> None:
    ctx = FileActionContext(tmp_path / "root" / "action", "action")
    ctx.text_logger.info("opens run.log")

    assert windows_files.clear(tmp_path / "root") == []
    ctx.text_logger.info("reopens run.log")
    windows_files.delete_tree(tmp_path / "root" / "action")
    ctx.text_logger.info("and again")
    windows_files.clear_except(tmp_path / "root", keep="workflow")

    assert names(tmp_path / "root") == []


def test_files_clear_except_keeps_named_directory_and_files(tree: Path) -> None:
    WorkflowFiles().clear_except(tree, keep="workflow")
    assert names(tree) == ["top.txt", "workflow"]


def test_files_clear_except_raises_on_failure(
    tree: Path, windows_files: WorkflowFiles
) -> None:
    with (tree / "a" / "deep" / "file.txt").open(), pytest.raises(OSError):
        windows_files.clear_except(tree, keep="workflow")


def test_files_delete_tree(tree: Path, windows_files: WorkflowFiles) -> None:
    WorkflowFiles().delete_tree(tree / "missing")  # not an error

    with (tree / "top.txt").open(), pytest.raises(OSError):
        windows_files.delete_tree(tree / "top.txt")

    windows_files.delete_tree(tree / "a")
    assert names(tree) == ["b", "top.txt", "workflow"]


def test_files_is_empty(tmp_path: Path) -> None:
    files = WorkflowFiles()
    assert files.is_empty(tmp_path)
    (tmp_path / "file").write_text("")
    assert not files.is_empty(tmp_path)
