# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF

import ctypes
import os
import sys
from importlib.resources import as_file, files
from pathlib import Path

import fibsem_maestro.pillow_config  # noqa: F401
from fibsem_maestro.crash_diagnostics import install_crash_diagnostics

# fix Qt plugin path on Windows
if sys.platform == "win32":
    from pathlib import Path

    qt_plugins = (
        Path(sys.prefix) / "Lib" / "site-packages" / "PyQt6" / "Qt6" / "plugins"
    )
    assert qt_plugins.exists(), f"Qt plugins path not found: {qt_plugins}"
    os.environ["QT_PLUGIN_PATH"] = str(qt_plugins)


from PyQt6.QtGui import QIcon

from ._version import __version__


def load_app_icon() -> QIcon:
    """
    Load the application icon bundled with the package.
    """
    resource = files("fibsem_maestro.resources").joinpath("icon.svg")
    with as_file(resource) as path:
        return QIcon(str(path))


def _crash_log_path() -> Path:
    """
    Return the per-user crash log location.

    Returns:
        `%LOCALAPPDATA%/fibsem-maestro/logs/crash.log` on Windows, or
        `$XDG_STATE_HOME/fibsem-maestro/logs/crash.log` (default
        `~/.local/state`) elsewhere.
    """
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    else:
        base = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local" / "state"))
    return base / "fibsem-maestro" / "logs" / "crash.log"


def main() -> None:
    # install crash diagnostics before anything else
    install_crash_diagnostics(_crash_log_path())

    # set the Windows App User Model ID so the app uses its own taskbar icon
    if sys.platform == "win32":
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            "CEMCOF.FibsemMaestro.Main"
        )

    import qdarkstyle
    from PyQt6.QtWidgets import QApplication, QDialog

    from fibsem_maestro.gui.connection.screen import ConnectionScreen
    from fibsem_maestro.gui.window.window import MainWindow

    app = QApplication(sys.argv)
    app.setWindowIcon(load_app_icon())

    app.setStyleSheet(qdarkstyle.load_stylesheet(qt_api="pyqt6"))

    screen = ConnectionScreen()
    if screen.exec() != QDialog.DialogCode.Accepted:
        sys.exit(0)

    workflow = screen.workflow
    assert workflow is not None, "Workflow not initialized"

    window = MainWindow(workflow, screen.workflow_dir or Path())
    window.setWindowTitle(f"FIBSEM Maestro v{__version__}")

    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
