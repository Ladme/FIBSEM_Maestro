# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF

"""The start-up dialog's page for resuming a workflow."""

from pathlib import Path

from PyQt6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class ResumeWorkflowPage(QWidget):
    """
    Page for resuming an interrupted workflow.

    Args:
        parent: Parent widget.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._workflow_dir: Path | None = None

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        layout.addWidget(QLabel("Select workflow to resume:"))

        dir_row = QHBoxLayout()
        self._dir_label = QLabel("No directory selected.")
        self._dir_label.setStyleSheet("color: #888888; font-size: 11px;")
        self._dir_label.setWordWrap(True)
        dir_row.addWidget(self._dir_label)

        browse_btn = QPushButton("Browse...")
        browse_btn.setFixedWidth(80)
        # on click, open a directory dialog to select the workflow directory
        browse_btn.clicked.connect(self._browse)
        dir_row.addWidget(browse_btn)
        layout.addLayout(dir_row)

        self._error_label = QLabel("")
        self._error_label.setStyleSheet("color: #cc4444; font-size: 11px;")
        self._error_label.setWordWrap(True)
        layout.addWidget(self._error_label)

        layout.addStretch()

    def _browse(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Select workflow directory")
        if not path:
            return
        self.set_workflow_dir(Path(path))

    def set_workflow_dir(self, workflow_dir: Path) -> None:
        """
        Show a chosen workflow directory.

        Args:
            workflow_dir: The directory of the workflow to resume.
        """
        self._workflow_dir = workflow_dir
        self._dir_label.setText(str(self._workflow_dir))
        self._error_label.setText("")

    def get_workflow_dir(self) -> Path | None:
        """The chosen workflow directory, or None if none was chosen."""
        return self._workflow_dir
