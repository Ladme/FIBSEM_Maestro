# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

import smtplib
from email.message import EmailMessage

from fibsem_maestro.notifications.notification_service import NotificationService
from fibsem_maestro.notifications.secrets import SecretStore
from fibsem_maestro.settings.notification_settings import SMTPEmailSettings


class SMTPEmailNotifier(NotificationService):
    """Email-based notification service using an SMTP server.

    This implementation sends notification messages via an SMTP server
    using STARTTLS authentication.

    SMTP credentials are retrieved at send time from a `SecretStore`.
    """

    def __init__(self, settings: SMTPEmailSettings, secrets: SecretStore):
        """
        Initialize the SMTP email notifier.

        Args:
            settings (SMTPEmailSettings):
                Non-secret SMTP configuration, including server host,
                port, username, sender address, recipients, and a
                reference to the stored password.
            secrets (SecretStore):
                Secret store used to retrieve the SMTP password at
                notification time.
        """
        self._settings = settings
        self._secrets = secrets

    def notify(self, subject: str, body: str) -> None:
        """
        Send a notification email via SMTP.

        The SMTP password is retrieved from the secret store immediately
        before sending the message. A new SMTP connection is opened for
        each call and closed after delivery.

        Args:
            subject (str):
                Subject line of the email.
            body (str):
                Plain-text body of the email.

        Raises:
            SecretsError:
                If the SMTP password cannot be retrieved from the secret
                store.
            smtplib.SMTPException:
                If an error occurs while connecting to the SMTP server,
                authenticating, or sending the message.
        """
        password = self._secrets.get(self._settings.password_ref)

        msg = EmailMessage()
        msg["From"] = self._settings.sender
        msg["To"] = ", ".join(self._settings.recipients)
        msg["Subject"] = subject
        msg.set_content(body)

        with smtplib.SMTP(self._settings.host, self._settings.port) as server:
            server.starttls()
            server.login(self._settings.username, password)
            server.send_message(msg)
