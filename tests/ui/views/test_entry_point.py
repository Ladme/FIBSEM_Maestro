# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF

"""`fibsem_maestro.main.main()`: crash log location, the start-up dialog, the main window."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import PyQt6.QtWidgets
import pytest
from gui_testkit import TIMEOUT_MS
from gui_testkit.app import shut_down
from gui_testkit.driving import answering, button

from fibsem_maestro import main as entry_point
from fibsem_maestro._version import __version__
from fibsem_maestro.settings.microscope_settings import MicroscopeSettings
from fibsem_maestro.ui import composition as composition_module
from fibsem_maestro.ui.app.run_state import AppState
from fibsem_maestro.ui.views.connection.dialog import ConnectionDialog

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

    from gui_testkit.dialogs import DirectoryChoices
    from PyQt6.QtGui import QIcon
    from pytestqt.qtbot import QtBot

    from fibsem_maestro.app_paths import AppPaths
    from fibsem_maestro.ui.app.files import WorkflowFiles
    from fibsem_maestro.ui.app.session import SessionSeed
    from fibsem_maestro.ui.app.user_config import UserConfig
    from fibsem_maestro.ui.composition import Composition
    from fibsem_maestro.ui.views.main_window import MainWindow


@dataclass
class StartUp:
    """What `main()` did, recorded by the stand-ins of the process-wide steps."""

    events: list[str] = field(default_factory=list)
    crash_log: Path | None = None
    composed: list[Composition] = field(default_factory=list)


@pytest.fixture
def start_up(qtbot: QtBot, monkeypatch: pytest.MonkeyPatch) -> Iterator[StartUp]:
    """
    Stand-ins for what `main()` must not do inside a test process.

    Installing the crash diagnostics would replace the process's exception
    hooks, a second `QApplication` cannot exist, and its `exec()` would block.
    The main window is composed for real and shut down after the test.
    """
    record = StartUp()

    def install_crash_diagnostics(path: Path) -> None:
        record.events.append("crash diagnostics")
        record.crash_log = path

    real = PyQt6.QtWidgets.QApplication

    class ForwardStatics(type):
        # static functions (e.g. pytest-qt's `QApplication.instance()`) still reach Qt
        def __getattr__(cls, name: str) -> object:
            return getattr(real, name)

    class Application(metaclass=ForwardStatics):
        def __init__(self, argv: list[str]) -> None:
            _ = argv
            record.events.append("application")

        def setWindowIcon(self, icon: QIcon) -> None:
            assert not icon.isNull()
            record.events.append("icon")

        def setStyleSheet(self, sheet: str) -> None:
            assert sheet
            record.events.append("style sheet")

        def exec(self) -> int:
            record.events.append("event loop")
            return 0

    def build_main_window(
        seed: SessionSeed, user_config: UserConfig, files: WorkflowFiles
    ) -> MainWindow:
        composed = composition_module.compose(seed, user_config, files)
        qtbot.addWidget(composed.window)
        record.composed.append(composed)
        return composed.window

    monkeypatch.setattr(
        entry_point, "install_crash_diagnostics", install_crash_diagnostics
    )
    monkeypatch.setattr(PyQt6.QtWidgets, "QApplication", Application)
    monkeypatch.setattr(composition_module, "build_main_window", build_main_window)
    yield record
    for composed in record.composed:
        shut_down(qtbot, composed.run, composed.tasks)


def test_entry_point_writes_the_crash_log_to_the_logs_folder(
    start_up: StartUp, maestro_home: AppPaths
) -> None:
    with (
        answering(ConnectionDialog, ConnectionDialog.reject),
        pytest.raises(SystemExit),
    ):
        entry_point.main()

    assert start_up.crash_log == maestro_home.logs_dir / "crash.log"
    # diagnostics come first, so a crash while starting Qt is recorded too
    assert start_up.events[:2] == ["crash diagnostics", "application"]


def test_entry_point_closing_the_start_up_dialog_exits_with_zero(
    start_up: StartUp,
) -> None:
    with (
        answering(ConnectionDialog, ConnectionDialog.reject) as shown,
        pytest.raises(SystemExit) as exit_info,
    ):
        entry_point.main()

    assert shown
    assert exit_info.value.code == 0
    assert start_up.composed == []
    assert "event loop" not in start_up.events


def test_entry_point_connecting_shows_the_titled_main_window(
    qtbot: QtBot,
    tmp_path: Path,
    start_up: StartUp,
    user_config: UserConfig,
    directory_choice: DirectoryChoices,
) -> None:
    user_config.save_microscope_profile(
        MicroscopeSettings(control="simulated", ip_address="localhost")
    )
    workflow_dir = tmp_path / "new"
    workflow_dir.mkdir()
    directory_choice.path = str(workflow_dir)

    def connect(dialog: ConnectionDialog) -> None:
        button(dialog, "Connect").click()
        qtbot.waitUntil(lambda: dialog.seed is not None, timeout=TIMEOUT_MS)

    with answering(ConnectionDialog, connect), pytest.raises(SystemExit) as exit_info:
        entry_point.main()

    assert exit_info.value.code == 0
    (composed,) = start_up.composed
    window = composed.window
    assert window.windowTitle() == f"FIBSEM Maestro v{__version__}"
    assert window.isVisible()
    assert composed.session.workflow_dir == workflow_dir
    assert composed.run.state is AppState.EDITING
    assert start_up.events[-1] == "event loop"
