# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


import smtplib

from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from fibsem_maestro.notifications.email_notifier import SMTPEmailNotifier
from fibsem_maestro.settings.notification_settings import SMTPEmailSettings


class EmailSetupDialog(QDialog):
    """Collects SMTP settings for the current session."""

    def __init__(
        self,
        parent: QWidget | None = None,
        previous: SMTPEmailSettings | None = None,
    ) -> None:
        """
        Initialize the dialog.

        Args:
            parent: Parent widget.
            previous: Settings from the last session, used to prefill everything except the password.
        """
        super().__init__(parent)
        self.setWindowTitle("E-mail notifications")
        self.setFixedWidth(420)

        self.settings: SMTPEmailSettings | None = None

        outer = QVBoxLayout(self)
        form = QFormLayout()

        self._host = QLineEdit()
        self._host.setPlaceholderText("smtp.muni.cz")
        self._port = QLineEdit("587")
        self._username = QLineEdit()
        self._username.setPlaceholderText("123456@IS.MUNI.CZ")
        self._sender = QLineEdit()
        self._recipients = QLineEdit()
        self._recipients.setPlaceholderText("me@example.com, colleague@example.com")
        self._password = QLineEdit()
        self._password.setEchoMode(QLineEdit.EchoMode.Password)

        if previous is not None:
            self._host.setText(previous.host)
            self._port.setText(str(previous.port))
            self._username.setText(previous.username)
            self._sender.setText(previous.sender)
            self._recipients.setText(", ".join(previous.recipients))

        form.addRow("SMTP server", self._host)
        form.addRow("Port", self._port)
        form.addRow("Username", self._username)
        form.addRow("Send from", self._sender)
        form.addRow("Send to", self._recipients)
        form.addRow("Password", self._password)
        outer.addLayout(form)

        note = QLabel(
            "The password is used only for this session and is not saved. "
            "Everything else is remembered for next time."
        )
        note.setWordWrap(True)
        outer.addWidget(note)

        self._test_btn = QPushButton("Send test e-mail")
        self._test_btn.clicked.connect(self._on_test)
        outer.addWidget(self._test_btn)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        outer.addWidget(buttons)

    def _collect(self) -> SMTPEmailSettings:
        """
        Build settings from the entered values.

        Returns:
            The collected settings.

        Raises:
            ValueError: If a field is empty or the port is not a number.
        """
        recipients = tuple(
            address.strip()
            for address in self._recipients.text().split(",")
            if address.strip()
        )
        values = {
            "SMTP server": self._host.text().strip(),
            "Username": self._username.text().strip(),
            "Send from": self._sender.text().strip(),
            "Password": self._password.text(),
        }

        for name, value in values.items():
            if not value:
                raise ValueError(f"{name} must not be empty.")

        if not recipients:
            raise ValueError("At least one recipient is required.")
        if not self._port.text().strip().isdigit():
            raise ValueError("Port must be a number.")

        return SMTPEmailSettings(
            host=values["SMTP server"],
            port=int(self._port.text().strip()),
            username=values["Username"],
            sender=values["Send from"],
            recipients=recipients,
            password=values["Password"],
        )

    def _on_test(self) -> None:
        """Send a test message."""
        try:
            settings = self._collect()
        except ValueError as error:
            QMessageBox.warning(self, "Incomplete", str(error))
            return

        self._test_btn.setEnabled(False)
        try:
            SMTPEmailNotifier(settings).notify(
                "FIBSEM Maestro test", "E-mail notifications are working."
            )
        except (smtplib.SMTPException, OSError) as error:
            QMessageBox.critical(self, "Test failed", str(error))
        else:
            QMessageBox.information(self, "Test sent", "Check your inbox.")
        finally:
            self._test_btn.setEnabled(True)

    def _on_accept(self) -> None:
        """Validate and close."""
        try:
            self.settings = self._collect()
        except ValueError as error:
            QMessageBox.warning(self, "Incomplete", str(error))
            return
        self.accept()
