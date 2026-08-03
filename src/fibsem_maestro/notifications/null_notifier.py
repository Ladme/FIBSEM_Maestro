# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from fibsem_maestro.notifications.notification_service import NotificationService


class NullNotifier(NotificationService):
    """
    Notification service that discards messages.
    """

    def notify(self, subject: str, body: str) -> None:
        """
        Discard a notification.

        Args:
            subject: Ignored.
            body: Ignored.
        """
