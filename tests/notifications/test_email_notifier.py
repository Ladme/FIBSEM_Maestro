from __future__ import annotations

import smtplib
from typing import TYPE_CHECKING, Any

from fibsem_maestro.notifications.email_notifier import SMTPEmailNotifier
from fibsem_maestro.settings.notification_settings import SMTPEmailSettings

if TYPE_CHECKING:
    import pytest


class RecordingSmtp:
    """Records how the SMTP connection is opened; sends nothing."""

    opened_with: dict[str, Any] = {}

    def __init__(self, host: str, port: int, **kwargs: Any) -> None:
        RecordingSmtp.opened_with = {"host": host, "port": port, **kwargs}

    def __enter__(self) -> RecordingSmtp:
        return self

    def __exit__(self, *_: object) -> None:
        pass

    def starttls(self) -> None:
        pass

    def login(self, user: str, password: str) -> None:
        pass

    def send_message(self, msg: object) -> None:
        pass


def test_email_notifier_uses_a_finite_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(smtplib, "SMTP", RecordingSmtp)
    notifier = SMTPEmailNotifier(
        SMTPEmailSettings(
            host="smtp.example.org",
            port=587,
            username="user",
            sender="maestro@example.org",
            recipients=("me@example.org",),
            password="secret",
        )
    )

    notifier.notify("subject", "body")

    timeout = RecordingSmtp.opened_with.get("timeout")
    assert timeout is not None and 0 < timeout <= 120
