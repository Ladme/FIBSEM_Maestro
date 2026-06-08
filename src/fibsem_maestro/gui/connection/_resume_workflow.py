# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from pathlib import Path

from PyQt6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from fibsem_maestro.settings.microscope_settings import MicroscopeSettings


class ResumeWorkflowScreen(QWidget):
    """
    Screen for resuming an interrupted workflow.

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
        self._workflow_dir = Path(path)
        self._dir_label.setText(str(self._workflow_dir))
        self._error_label.setText("")

    def get_workflow_dir(self) -> Path | None:
        return self._workflow_dir

    def load_profile(self) -> MicroscopeSettings | None:
        """
        Attempt to load a MicroscopeSettings profile from the snapshot directory.

        Returns None and sets an error message if loading fails.
        """
        # TODO: placeholder
        pass
