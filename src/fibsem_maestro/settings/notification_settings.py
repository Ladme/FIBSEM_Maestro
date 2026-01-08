# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from typing import Annotated

from pydantic import Field

from fibsem_maestro.notifications.secrets import SecretRef
from fibsem_maestro.settings.base_settings import BaseSettings


class SMTPEmailSettings(BaseSettings):
    """
    Configuration for SMTP-based email notifications.
    """

    host: Annotated[
        str,
        Field(
            description="Hostname or IP address of the SMTP server "
            "(e.g., 'smtp.muni.cz')."
        ),
    ]
    port: Annotated[
        int,
        Field(
            description="TCP port of the SMTP server. "
            "Typically 587 for STARTTLS or 465 for implicit SSL."
        ),
    ]
    username: Annotated[
        str,
        Field(
            description="Username used to authenticate with the SMTP server. "
            "Often an email address."
        ),
    ]
    password_ref: Annotated[
        SecretRef,
        Field(
            description="Reference to the SMTP password stored in the system "
            "keychain. The password itself is retrieved at runtime "
            "using this reference."
        ),
    ]
    sender: Annotated[
        str,
        Field(
            description="Email address used as the sender (From header) of "
            "notification emails."
        ),
    ]
    recipients: Annotated[
        tuple[str, ...],
        Field(
            description="Tuple of recipient email addresses that will receive "
            "notification emails."
        ),
    ]


NotificationSettings = Annotated[SMTPEmailSettings, Field(discriminator="type")]
