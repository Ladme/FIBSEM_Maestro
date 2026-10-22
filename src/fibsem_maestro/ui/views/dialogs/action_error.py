# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF

"""The dialog shown when an action or the whole workflow fails during a run."""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QCloseEvent
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from fibsem_maestro.ui.widgets.icons import (
    ICON_CANCEL,
    ICON_ERROR,
    ICON_PAUSE,
    ICON_RETRY,
    ICON_SKIP,
    svg_icon,
)
from fibsem_maestro.workflow.error_choice import ErrorChoice

_HEADER_ICON_SIZE = 24  # px


class ActionErrorDialog(QDialog):
    """
    Non-modal dialog shown when the workflow raises during a run.

    If `action_name` is given, the failure is attributed to that action and
    the user may restart it, skip it, or skip it and pause the workflow; the
    run is never abandoned from here. If it is None, the error is not
    recoverable per-action and terminating is the only option.

    Args:
        message: Error text to display (traceback or exception message).
        action_name: Name of the failed action, or None for general errors.
        parent: Parent widget.
    """

    choice_made = pyqtSignal(ErrorChoice)
    """Retry or Skip for a failed action (a general error is answered by closing)."""

    skip_and_pause_chosen = pyqtSignal()
    """"Skip action and pause" for a failed action."""

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

        self._recoverable = action_name is not None
        self._choice_buttons: list[QPushButton] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # header: critical icon + message
        header_row = QHBoxLayout()
        header_row.setSpacing(8)

        icon_label = QLabel()
        icon_label.setPixmap(
            svg_icon(ICON_ERROR, _HEADER_ICON_SIZE).pixmap(
                _HEADER_ICON_SIZE, _HEADER_ICON_SIZE
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
            self._set_icon(retry_btn, ICON_RETRY)
            retry_btn.setToolTip(f"Run '{action_name}' for this slice again.")
            retry_btn.clicked.connect(self._choose_retry)
            button_row.addWidget(retry_btn)

            skip_btn = QPushButton("Skip action")
            self._set_icon(skip_btn, ICON_SKIP)
            skip_btn.setToolTip(
                f"Continue with the next action, leaving '{action_name}' unexecuted for this slice."
            )
            skip_btn.clicked.connect(self._choose_skip)
            button_row.addWidget(skip_btn)

            pause_btn = QPushButton("Skip action and pause")
            self._set_icon(pause_btn, ICON_PAUSE)
            pause_btn.setToolTip(
                f"Leave '{action_name}' unexecuted for this slice and pause the workflow before the next action."
            )
            pause_btn.clicked.connect(self._choose_skip_and_pause)
            pause_btn.setDefault(True)
            button_row.addWidget(pause_btn)

            self._choice_buttons = [retry_btn, skip_btn, pause_btn]
        else:
            button_row.addStretch()

            terminate_btn = QPushButton("Terminate workflow")
            terminate_btn.setStyleSheet("color: #e05252;")
            # after the style sheet: the icon takes the (red) text colour
            self._set_icon(terminate_btn, ICON_CANCEL)
            terminate_btn.setToolTip(
                "Abandon the run and close the application. Slices already acquired are kept."
            )
            terminate_btn.clicked.connect(self.accept)
            terminate_btn.setDefault(True)
            button_row.addWidget(terminate_btn)

        layout.addLayout(button_row)

    def set_choices_enabled(self, enabled: bool) -> None:
        """
        Enable or disable the Retry / Skip / Skip and pause buttons.

        Does nothing for a general error, whose only button (Terminate) stays enabled.

        Args:
            enabled: True to let the user choose.
        """
        for button in self._choice_buttons:
            button.setEnabled(enabled)

    @staticmethod
    def _set_icon(button: QPushButton, body: str) -> None:
        """Give a button an SVG icon in its text colour, at its icon size."""
        # the application style sheet sets the text colour in the palette on polish
        button.ensurePolished()
        button.setIcon(
            svg_icon(
                body,
                button.iconSize().width(),
                palette=button.palette(),
                device_pixel_ratio=button.devicePixelRatioF(),
            )
        )

    def _choose_retry(self) -> None:
        self._choose(ErrorChoice.RETRY)

    def _choose_skip(self) -> None:
        self._choose(ErrorChoice.SKIP)

    def _choose(self, choice: ErrorChoice) -> None:
        self.choice_made.emit(choice)
        self.accept()

    def _choose_skip_and_pause(self) -> None:
        self.skip_and_pause_chosen.emit()
        self.accept()

    def reject(self) -> None:
        """Esc: ignored for a failed action; closes a general error's dialog (terminating)."""
        # a failed action offers no way to abandon the run, so Esc does nothing;
        # a general error's dialog terminates whenever it finishes
        if self._recoverable:
            return
        super().reject()

    def closeEvent(self, a0: QCloseEvent | None) -> None:
        """Ignore the window's close button: the user must pick one of the buttons."""
        if a0 is not None:
            a0.ignore()
