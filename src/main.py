# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

import os
import sys

from fibsem_maestro.core.resolution import Resolution

# fix Qt plugin path on Windows
if sys.platform == "win32":
    from pathlib import Path

    qt_plugins = (
        Path(sys.prefix) / "Lib" / "site-packages" / "PyQt6" / "Qt6" / "plugins"
    )
    assert qt_plugins.exists(), f"Qt plugins path not found: {qt_plugins}"
    os.environ["QT_PLUGIN_PATH"] = str(qt_plugins)


import qdarkstyle
from PyQt6.QtWidgets import QApplication, QDialog

from fibsem_maestro.gui.connection.screen import ConnectionScreen
from fibsem_maestro.gui.window.window import MainWindow


def main() -> None:
    app = QApplication(sys.argv)

    app.setStyleSheet(qdarkstyle.load_stylesheet(qt_api="pyqt6"))

    screen = ConnectionScreen()
    if screen.exec() != QDialog.DialogCode.Accepted:
        sys.exit(0)

    workflow = screen.workflow
    assert workflow is not None, "Workflow not initialized"

    window = MainWindow(workflow, screen.workflow_dir or Path())

    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
