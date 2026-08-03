# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from typing import Annotated, Literal

from pydantic import Field

from fibsem_maestro.settings.base_settings import BaseSettings


class SMTPEmailSettings(BaseSettings):
    """
    Configuration for SMTP-based email notifications.
    """

    type: Literal["SMTP"] = "SMTP"

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
    password: Annotated[
        str,
        Field(description="Password to authenticate with the SMTP server.", repr=False),
    ]


NotificationSettings = Annotated[SMTPEmailSettings, Field(discriminator="type")]
