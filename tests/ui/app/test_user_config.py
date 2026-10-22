# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF

"""`UserConfig`: the remembered microscope and e-mail profiles."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from fibsem_maestro.app_paths import AppPaths
from fibsem_maestro.settings.microscope_settings import MicroscopeSettings
from fibsem_maestro.settings.notification_settings import SMTPEmailSettings
from fibsem_maestro.ui.app.user_config import (
    LAST_EMAIL_FILE,
    LAST_PROFILE_FILE,
    EmailProfile,
    UserConfig,
)

if TYPE_CHECKING:
    from pathlib import Path

PASSWORD = "hunter2-secret"  # lol


def email() -> SMTPEmailSettings:
    return SMTPEmailSettings(
        host="smtp.example.com",
        port=587,
        username="user",
        sender="maestro@example.com",
        recipients=("a@example.com", "b@example.com"),
        password=PASSWORD,
    )


def test_user_config_microscope_profile_round_trip(user_config: UserConfig) -> None:
    assert user_config.load_microscope_profile() is None
    settings = MicroscopeSettings(
        control="simulated", ip_address="10.0.0.1", port="7520"
    )

    user_config.save_microscope_profile(settings)

    assert user_config.load_microscope_profile() == settings


def test_user_config_email_profile_round_trip_without_password(
    user_config: UserConfig, maestro_home: AppPaths
) -> None:
    assert user_config.load_email_profile() is None

    user_config.save_email_profile(email())

    text = (maestro_home.config_dir / LAST_EMAIL_FILE).read_text(encoding="utf-8")
    assert PASSWORD not in text
    assert "password" not in text
    assert user_config.load_email_profile() == EmailProfile(
        **email().model_dump(exclude={"password"})
    )


def test_user_config_ignores_password_in_stored_profile(
    user_config: UserConfig, maestro_home: AppPaths
) -> None:
    # e.g. written by hand or by an old version
    path = maestro_home.config_dir / LAST_EMAIL_FILE
    email().to_file(path)
    assert PASSWORD in path.read_text(encoding="utf-8")

    profile = user_config.load_email_profile()

    assert profile is not None
    assert PASSWORD not in repr(profile.model_dump())


@pytest.mark.parametrize(
    ("file", "text"),
    [
        (LAST_PROFILE_FILE, "control: [unclosed"),
        (LAST_PROFILE_FILE, "unknown_field: 1"),
        (LAST_EMAIL_FILE, "host: only-a-host"),
        (LAST_EMAIL_FILE, "- a list"),
    ],
)
def test_user_config_unreadable_profile_loads_as_none(
    user_config: UserConfig, maestro_home: AppPaths, file: str, text: str
) -> None:
    (maestro_home.config_dir / file).write_text(text, encoding="utf-8")
    if file == LAST_PROFILE_FILE:
        assert user_config.load_microscope_profile() is None
    else:
        assert user_config.load_email_profile() is None


def test_user_config_save_errors_are_ignored(tmp_path: Path) -> None:
    blocked = tmp_path / "home"
    blocked.mkdir()
    (blocked / "config").write_text("a file where the folder must go")
    config = UserConfig(AppPaths(blocked))

    config.save_microscope_profile(
        MicroscopeSettings(control="simulated", ip_address="localhost")
    )
    config.save_email_profile(email())

    assert config.load_microscope_profile() is None
