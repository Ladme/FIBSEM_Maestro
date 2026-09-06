# Released under MIT License.
# Copyright (c) 2024-2026 CEMCOF

from abc import ABC, abstractmethod


class NotificationService(ABC):
    """Interface for sending user-facing notifications such as e-mails."""

    @abstractmethod
    def notify(self, subject: str, body: str) -> None:
        """
        Send a notification message.

        Args:
            subject (str):
                Short summary or title of the notification.
            body (str):
                Full notification message content.

        Raises:
            Exception:
                Implementations may raise an exception if notification
                delivery fails.
        """
        pass
