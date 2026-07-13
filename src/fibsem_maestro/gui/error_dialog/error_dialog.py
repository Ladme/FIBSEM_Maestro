# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from fibsem_maestro.workflow.error_choice import ErrorChoice


class ActionErrorDialog(QDialog):
    """
    Modal dialog shown when the workflow raises during a run.

    If `action_name` is given, the failure is attributed to that action and
    the user may restart it, skip it, or terminate the workflow. If it is
    None, the error is not recoverable per-action and terminating is the
    only option.

    The chosen option is available via `choice` after `exec()` returns.

    Args:
        message: Error text to display (traceback or exception message).
        action_name: Name of the failed action, or None for general errors.
    """

    choice_made = pyqtSignal(ErrorChoice)

    def __init__(
        self,
        message: str,
        action_name: str | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Action failed" if action_name else "Workflow error")
        self.setModal(True)
        self.setMinimumWidth(480)
        self.setWindowModality(Qt.WindowModality.NonModal)

        self._choice = ErrorChoice.TERMINATE

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        header = QLabel(
            f"Action '{action_name}' failed."
            if action_name
            else "The workflow encountered an error."
        )
        header.setStyleSheet("font-weight: bold;")
        layout.addWidget(header)

        self._error_view = QPlainTextEdit(message)
        self._error_view.setReadOnly(True)
        self._error_view.setStyleSheet(
            "color: #e05252; font-family: monospace; font-size: 11px;"
        )
        layout.addWidget(self._error_view)

        button_row = QHBoxLayout()
        button_row.setSpacing(6)

        # restart/skip only make sense when a specific action failed
        if action_name is not None:
            restart_btn = QPushButton("Retry action")
            restart_btn.clicked.connect(lambda: self._choose(ErrorChoice.RETRY))
            button_row.addWidget(restart_btn)

            skip_btn = QPushButton("Skip action")
            skip_btn.clicked.connect(lambda: self._choose(ErrorChoice.SKIP))
            button_row.addWidget(skip_btn)
        else:
            button_row.addStretch()

        terminate_btn = QPushButton("Terminate workflow")
        terminate_btn.clicked.connect(lambda: self._choose(ErrorChoice.TERMINATE))
        terminate_btn.setDefault(True)
        button_row.addWidget(terminate_btn)

        layout.addLayout(button_row)

    def _choose(self, choice: ErrorChoice) -> None:
        self.choice_made.emit(choice)
        self.accept()

    @property
    def choice(self) -> ErrorChoice:
        return self._choice

    def reject(self) -> None:
        # closing with Esc or the window X is treated as terminate
        self.choice_made.emit(ErrorChoice.TERMINATE)
        super().reject()
