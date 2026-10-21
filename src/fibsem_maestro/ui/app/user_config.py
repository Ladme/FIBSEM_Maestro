# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF

"""The last microscope and e-mail profiles, remembered between sessions."""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING, Annotated, Literal

from pydantic import Field

from fibsem_maestro.serializer.yaml_serializer import YamlSerializer
from fibsem_maestro.settings.base_settings import BaseSettings
from fibsem_maestro.settings.microscope_settings import MicroscopeSettings

if TYPE_CHECKING:
    from pathlib import Path

    from fibsem_maestro.app_paths import AppPaths
    from fibsem_maestro.settings.notification_settings import SMTPEmailSettings

LAST_PROFILE_FILE = "last_microscope_profile.yaml"
"""File name of the last microscope profile."""

LAST_EMAIL_FILE = "last_email_settings.yaml"
"""File name of the last e-mail profile."""

CONNECTION_FIELDS: tuple[str, ...] = ("control", "ip_address", "port")
"""Microscope settings fields edited on the connection page, in form order."""


class EmailProfile(BaseSettings):
    """
    The remembered e-mail settings: `SMTPEmailSettings` without the password.

    The password is not a field, so it can never be written. Unknown keys are
    ignored, so a profile saved by a version with more fields still loads.
    """

    model_config = {"extra": "ignore"}

    type: Literal["SMTP"] = "SMTP"
    host: Annotated[
        str, Field(description="Hostname or IP address of the SMTP server.")
    ]
    port: Annotated[int, Field(description="TCP port of the SMTP server.")]
    username: Annotated[
        str, Field(description="Username used to authenticate with the SMTP server.")
    ]
    sender: Annotated[
        str, Field(description="Email address used as the sender of notifications.")
    ]
    recipients: Annotated[
        tuple[str, ...],
        Field(description="Recipient email addresses of notifications."),
    ]


class UserConfig:
    """
    Reads and writes the last microscope and e-mail profiles.

    The files live in `paths.config_dir`. The e-mail password is never written.
    Load errors return None and save errors are ignored: the profiles are a
    convenience, never a reason to fail.

    Args:
        paths: The FIBSEM Maestro folders.
    """

    def __init__(self, paths: AppPaths) -> None:
        self._paths = paths

    def load_microscope_profile(self) -> MicroscopeSettings | None:
        """
        Load the last used microscope profile.

        Returns:
            The profile, or None if there is none or it cannot be read.
        """
        path = self._file(LAST_PROFILE_FILE)
        if not path.is_file():
            return None
        try:
            return MicroscopeSettings.from_file(path)
        except Exception:
            return None

    def save_microscope_profile(self, settings: MicroscopeSettings) -> None:
        """
        Save the microscope profile; failures are ignored.

        Args:
            settings: The microscope settings to remember.
        """
        _write_quietly(settings, self._file(LAST_PROFILE_FILE))

    def load_email_profile(self) -> EmailProfile | None:
        """
        Load the last used e-mail settings, without a password.

        Returns:
            The profile, or None if there is none or it cannot be read.
        """
        path = self._file(LAST_EMAIL_FILE)
        if not path.is_file():
            return None
        try:
            return EmailProfile(**YamlSerializer.load(path))
        except Exception:
            return None

    def save_email_profile(self, settings: SMTPEmailSettings) -> None:
        """
        Save the e-mail settings without the password; failures are ignored.

        Args:
            settings: The e-mail settings to remember.
        """
        try:
            profile = EmailProfile(**settings.model_dump(exclude={"password"}))
        except Exception:
            return
        _write_quietly(profile, self._file(LAST_EMAIL_FILE))

    def _file(self, name: str) -> Path:
        return self._paths.config_dir / name


def _write_quietly(settings: BaseSettings, path: Path) -> None:
    with contextlib.suppress(Exception):
        settings.to_file(path)
