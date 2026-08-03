# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from pathlib import Path

from platformdirs import user_config_dir

from fibsem_maestro.settings.microscope_settings import MicroscopeSettings
from fibsem_maestro.settings.notification_settings import SMTPEmailSettings

CONFIG_DIR = Path(user_config_dir("fibsem-maestro"))
LAST_PROFILE_PATH = CONFIG_DIR / "last_microscope_profile.yaml"
LAST_EMAIL_PATH = CONFIG_DIR / "last_email_settings.yaml"

CONNECTION_FIELDS = {"control", "ip_address", "port"}


def load_last_microscope_profile() -> MicroscopeSettings | None:
    """Load the last used microscope profile from the config directory."""
    if not LAST_PROFILE_PATH.exists():
        return None
    try:
        return MicroscopeSettings.from_file(LAST_PROFILE_PATH)
    except Exception:
        return None


def save_last_microscope_profile(settings: MicroscopeSettings) -> None:
    """Save the microscope profile to the config directory."""
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        settings.to_file(LAST_PROFILE_PATH)
    except Exception:
        pass


def load_last_email_settings() -> SMTPEmailSettings | None:
    """Load the last used e-mail settings from the config directory."""
    if not LAST_EMAIL_PATH.exists():
        return None
    try:
        return SMTPEmailSettings.from_file(LAST_EMAIL_PATH)
    except Exception:
        return None


def save_last_email_settings(settings: SMTPEmailSettings) -> None:
    """Save the e-mail settings to the config directory."""
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        settings.to_file(LAST_EMAIL_PATH)
    except Exception:
        pass
