# Released under MIT License.
# Copyright (c) 2024-2026 CEMCOF


from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QCloseEvent
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStyle,
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
        self.setMinimumWidth(480)
        # not modal: the user can still browse logs and panels while deciding
        self.setWindowModality(Qt.WindowModality.NonModal)
        # no close button: the user must pick one of the buttons explicitly
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.CustomizeWindowHint
            | Qt.WindowType.WindowTitleHint
        )

        self._choice = ErrorChoice.TERMINATE

        style = self.style()
        assert style is not None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # header: critical icon + message
        header_row = QHBoxLayout()
        header_row.setSpacing(8)

        icon_label = QLabel()
        icon_label.setPixmap(
            style.standardIcon(QStyle.StandardPixmap.SP_MessageBoxCritical).pixmap(
                24, 24
            )
        )
        header_row.addWidget(icon_label)

        header = QLabel(
            f"Action '{action_name}' failed."
            if action_name
            else "The workflow encountered an error."
        )
        header.setStyleSheet("font-weight: bold;")
        header_row.addWidget(header)

        header_row.addStretch()
        layout.addLayout(header_row)

        # error text
        self._error_view = QLabel(message)
        self._error_view.setWordWrap(True)
        self._error_view.setStyleSheet("color: #e05252;")
        self._error_view.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        layout.addWidget(self._error_view)

        # buttons
        button_row = QHBoxLayout()
        button_row.setSpacing(6)

        # retry/skip only make sense when a specific action failed
        if action_name is not None:
            retry_btn = QPushButton("Retry action")
            retry_btn.setIcon(
                style.standardIcon(QStyle.StandardPixmap.SP_BrowserReload)
            )
            retry_btn.setToolTip(f"Run '{action_name}' for this slice again.")
            retry_btn.clicked.connect(lambda: self._choose(ErrorChoice.RETRY))
            button_row.addWidget(retry_btn)

            skip_btn = QPushButton("Skip action")
            skip_btn.setIcon(
                style.standardIcon(QStyle.StandardPixmap.SP_MediaSkipForward)
            )
            skip_btn.setToolTip(
                f"Continue with the next action, leaving '{action_name}' unexecuted for this slice."
            )
            skip_btn.clicked.connect(lambda: self._choose(ErrorChoice.SKIP))
            button_row.addWidget(skip_btn)
        else:
            button_row.addStretch()

        terminate_btn = QPushButton("Terminate workflow")
        terminate_btn.setIcon(
            style.standardIcon(QStyle.StandardPixmap.SP_DialogCancelButton)
        )
        terminate_btn.setStyleSheet("color: #e05252;")
        terminate_btn.setToolTip(
            "Abandon the run and close the application. Slices already acquired are kept."
        )
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

    def closeEvent(self, a0: QCloseEvent | None) -> None:
        # the user must pick one of the buttons; ignore the window's X
        if a0 is not None:
            a0.ignore()
