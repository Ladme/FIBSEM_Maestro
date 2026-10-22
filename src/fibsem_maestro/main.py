# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF

"""
The entry point of the FIBSEM Maestro GUI.
"""

import ctypes
import os
import sys
from importlib.resources import as_file, files
from pathlib import Path
from typing import TYPE_CHECKING

import fibsem_maestro.pillow_config  # noqa: F401
from fibsem_maestro.app_paths import AppPaths
from fibsem_maestro.crash_diagnostics import install_crash_diagnostics

# fix Qt plugin path on Windows
if sys.platform == "win32":
    qt_plugins = (
        Path(sys.prefix) / "Lib" / "site-packages" / "PyQt6" / "Qt6" / "plugins"
    )
    assert qt_plugins.exists(), f"Qt plugins path not found: {qt_plugins}"
    os.environ["QT_PLUGIN_PATH"] = str(qt_plugins)


from PyQt6.QtGui import QIcon

from ._version import __version__

if TYPE_CHECKING:
    from PyQt6.QtWidgets import QMainWindow

GUI_VARIABLE = "FIBSEM_MAESTRO_GUI"
"""Environment variable selecting the GUI; "legacy" runs the old one."""

LEGACY_GUI = "legacy"
"""Value of `GUI_VARIABLE` selecting the old GUI."""


def load_app_icon() -> QIcon:
    """
    Load the application icon bundled with the package.

    Returns:
        The icon.
    """
    resource = files("fibsem_maestro.resources").joinpath("icon.svg")
    with as_file(resource) as path:
        return QIcon(str(path))


def main() -> None:
    """Start the GUI: the start-up dialog, then the main window."""
    paths = AppPaths.default()

    # install crash diagnostics before anything else
    install_crash_diagnostics(paths.logs_dir / "crash.log")

    # set the Windows App User Model ID so the app uses its own taskbar icon
    if sys.platform == "win32":
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            "CEMCOF.FibsemMaestro.Main"
        )

    import qdarkstyle
    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    app.setWindowIcon(load_app_icon())

    app.setStyleSheet(qdarkstyle.load_stylesheet(qt_api="pyqt6"))

    window = _main_window(paths)

    window.setWindowTitle(f"FIBSEM Maestro v{__version__}")

    window.show()
    sys.exit(app.exec())


def _main_window(paths: AppPaths) -> "QMainWindow":
    """
    Run the start-up dialog and build the main window of the new GUI.

    Exits the process with code 0 if the start-up dialog is closed.

    Args:
        paths: The FIBSEM Maestro folders.

    Returns:
        The main window, not yet shown.
    """
    from PyQt6.QtWidgets import QDialog

    from fibsem_maestro.ui.app.files import WorkflowFiles
    from fibsem_maestro.ui.app.user_config import UserConfig
    from fibsem_maestro.ui.composition import build_main_window
    from fibsem_maestro.ui.views.connection.dialog import ConnectionDialog

    user_config = UserConfig(paths)
    workflow_files = WorkflowFiles()

    dialog = ConnectionDialog(user_config, workflow_files)
    if dialog.exec() != QDialog.DialogCode.Accepted:
        sys.exit(0)

    seed = dialog.seed
    assert seed is not None, "Workflow not initialized"

    return build_main_window(seed, user_config, workflow_files)


if __name__ == "__main__":
    main()
