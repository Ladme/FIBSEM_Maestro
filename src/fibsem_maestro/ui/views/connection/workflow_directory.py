# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF

"""
Choosing the directory of a new workflow: the file dialog, the "Directory not
empty" confirmation and the report of a failed clearing.

Shared by the start-up dialog and the top bar's "New workflow", so both show
the same texts and handle failures the same way.
"""

from pathlib import Path

from PyQt6.QtWidgets import QFileDialog, QMessageBox, QWidget

from fibsem_maestro.ui.app.errors import DirectoryNotClearedError
from fibsem_maestro.ui.app.files import WorkflowFiles


def choose_new(parent: QWidget, files: WorkflowFiles) -> Path | None:
    """
    Ask for the directory of a new workflow, confirming if it is not empty.

    Args:
        parent: Parent of the dialogs.
        files: Filesystem queries.

    Returns:
        The chosen directory, or None if the user cancelled.
    """
    path = QFileDialog.getExistingDirectory(parent, "Choose workflow save directory")
    if not path:
        return None

    directory = Path(path)

    if not files.is_empty(directory):
        answer = QMessageBox.warning(
            parent,
            "Directory not empty",
            "The selected directory is not empty. Assigning it to a workflow will PERMANENTLY delete all its contents.\n\nAre you sure you want to continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return None

    return directory


def report_not_cleared(parent: QWidget, error: DirectoryNotClearedError) -> None:
    """
    Tell the user which children of the workflow directory could not be deleted.

    Args:
        parent: Parent of the message box.
        error: The failure, listing each child that could not be deleted.
    """
    QMessageBox.critical(
        parent,
        "Error",
        f"Could not fully clear the workflow directory.\n\n{error}",
    )


def clear(parent: QWidget, files: WorkflowFiles, directory: Path) -> bool:
    """
    Delete every child of `directory`, reporting failures to the user.

    Args:
        parent: Parent of the message box.
        files: Filesystem operations.
        directory: The directory to clear (the user already confirmed).

    Returns:
        True if the directory is empty afterwards.
    """
    if failures := files.clear(directory):
        report_not_cleared(parent, DirectoryNotClearedError(failures))
        return False
    return True
