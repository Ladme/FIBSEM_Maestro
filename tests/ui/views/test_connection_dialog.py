# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF

"""The start-up dialog: new and resumed workflows, connecting on a thread, e-mail settings."""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING

import pytest
from gui_testkit import TIMEOUT_MS
from gui_testkit.driving import answering, button, children, press
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QMessageBox,
)

from fibsem_maestro.settings.microscope_settings import MicroscopeSettings
from fibsem_maestro.ui.app.files import WorkflowFiles
from fibsem_maestro.ui.app.session import WorkflowSession
from fibsem_maestro.ui.views.connection import connect_worker
from fibsem_maestro.ui.views.connection.dialog import ConnectionDialog
from fibsem_maestro.ui.views.connection.email_dialog import EmailSetupDialog

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator
    from pathlib import Path

    from gui_testkit.dialogs import DirectoryChoices, ExitCalls, MessageBoxes
    from pytestqt.qtbot import QtBot

    from fibsem_maestro.app_paths import AppPaths
    from fibsem_maestro.ui.app.session import SessionSeed
    from fibsem_maestro.ui.app.user_config import UserConfig
    from fibsem_maestro.ui.views.connection.connect_worker import ConnectRequest
    from fibsem_maestro.workflow.workflow import Workflow

SIMULATED = MicroscopeSettings(control="simulated", ip_address="localhost")
PASSWORD = "s3cret-password"


@pytest.fixture
def open_dialog(
    qtbot: QtBot, user_config: UserConfig
) -> Iterator[Callable[[WorkflowFiles], ConnectionDialog]]:
    """Open start-up dialogs, the simulated microscope being the last profile; joined after the test."""
    user_config.save_microscope_profile(SIMULATED)
    opened: list[ConnectionDialog] = []

    def open_one(files: WorkflowFiles) -> ConnectionDialog:
        dialog = ConnectionDialog(user_config, files)
        qtbot.addWidget(dialog)
        dialog.show()
        opened.append(dialog)
        return dialog

    yield open_one
    for dialog in opened:
        qtbot.waitUntil(lambda d=dialog: not d.connecting, timeout=TIMEOUT_MS)


@pytest.fixture
def dialog(
    open_dialog: Callable[[WorkflowFiles], ConnectionDialog], files: WorkflowFiles
) -> ConnectionDialog:
    return open_dialog(files)


@pytest.fixture
def gate(monkeypatch: pytest.MonkeyPatch) -> Iterator[threading.Event]:
    """Connecting waits until the returned event is set (a slow microscope)."""
    release = threading.Event()
    connect = connect_worker.connect

    def slow_connect(request: ConnectRequest) -> SessionSeed:
        release.wait(TIMEOUT_MS / 1000)
        return connect(request)

    monkeypatch.setattr(connect_worker, "connect", slow_connect)
    yield release
    # a failed test must not leave the connection waiting
    release.set()


def connect_and_wait(qtbot: QtBot, dialog: ConnectionDialog) -> None:
    button(dialog, "Connect").click()
    qtbot.waitUntil(lambda: not dialog.connecting, timeout=TIMEOUT_MS)


def new_dir(tmp_path: Path, *files: str) -> Path:
    directory = tmp_path / "new"
    directory.mkdir()
    for name in files:
        (directory / name).write_text("x")
    return directory


def test_connection_new_workflow_yields_a_seed_and_saves_the_profile(
    qtbot: QtBot,
    tmp_path: Path,
    dialog: ConnectionDialog,
    directory_choice: DirectoryChoices,
    boxes: MessageBoxes,
    user_config: UserConfig,
    maestro_home: AppPaths,
) -> None:
    directory = new_dir(tmp_path)
    directory_choice.path = str(directory)
    (maestro_home.config_dir / "last_microscope_profile.yaml").unlink()

    connect_and_wait(qtbot, dialog)

    assert boxes.calls == []
    assert dialog.result() == QDialog.DialogCode.Accepted
    seed = dialog.seed
    assert seed is not None
    assert seed.workflow_dir == directory
    assert seed.workflow.actions == []
    # the catalogs were read on the connection thread
    assert seed.catalogs.pattern_types
    assert user_config.load_microscope_profile() == SIMULATED
    assert QApplication.overrideCursor() is None


def test_connection_new_workflow_into_a_non_empty_directory_asks_first(
    qtbot: QtBot,
    tmp_path: Path,
    dialog: ConnectionDialog,
    directory_choice: DirectoryChoices,
    boxes: MessageBoxes,
) -> None:
    directory = new_dir(tmp_path, "old.txt")
    directory_choice.path = str(directory)
    boxes.answer = QMessageBox.StandardButton.Cancel

    button(dialog, "Connect").click()

    assert boxes.titles() == ["Directory not empty"]
    assert not dialog.connecting
    assert (directory / "old.txt").exists()

    boxes.answer = QMessageBox.StandardButton.Yes
    connect_and_wait(qtbot, dialog)

    assert not (directory / "old.txt").exists()
    assert dialog.seed is not None


def test_connection_new_workflow_reports_a_directory_it_could_not_clear(
    tmp_path: Path,
    open_dialog: Callable[[WorkflowFiles], ConnectionDialog],
    directory_choice: DirectoryChoices,
    boxes: MessageBoxes,
) -> None:
    def refuse(_: Path) -> None:
        raise PermissionError("in use")

    dialog = open_dialog(WorkflowFiles(refuse))
    directory_choice.path = str(new_dir(tmp_path, "locked.txt"))

    button(dialog, "Connect").click()

    assert boxes.titles() == ["Directory not empty", "Error"]
    assert boxes.texts()[1].startswith("Could not fully clear the workflow directory.")
    assert "locked.txt" in boxes.texts()[1]
    assert not dialog.connecting
    assert dialog.seed is None


def test_connection_cancelled_directory_choice_does_not_connect(
    dialog: ConnectionDialog, directory_choice: DirectoryChoices
) -> None:
    directory_choice.path = ""

    button(dialog, "Connect").click()

    assert directory_choice.titles == ["Choose workflow save directory"]
    assert not dialog.connecting


def test_connection_failure_shows_an_error_and_restores_the_inputs(
    qtbot: QtBot,
    tmp_path: Path,
    dialog: ConnectionDialog,
    directory_choice: DirectoryChoices,
    boxes: MessageBoxes,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail(_: ConnectRequest) -> SessionSeed:
        raise ConnectionError("no microscope")

    monkeypatch.setattr(connect_worker, "connect", fail)
    directory_choice.path = str(new_dir(tmp_path))

    connect_and_wait(qtbot, dialog)

    assert boxes.texts() == ["Connection failed: no microscope"]
    assert dialog.seed is None
    assert dialog.isVisible()
    assert button(dialog, "Connect").isEnabled()
    assert dialog.email_check.isEnabled()
    assert QApplication.overrideCursor() is None


def test_connection_disables_every_input_while_connecting(
    qtbot: QtBot,
    tmp_path: Path,
    dialog: ConnectionDialog,
    directory_choice: DirectoryChoices,
    gate: threading.Event,
) -> None:
    directory_choice.path = str(new_dir(tmp_path))

    button(dialog, "Connect").click()

    assert dialog.connecting
    for text in ("Connect", "New workflow", "Resume workflow"):
        assert not button(dialog, text).isEnabled()
    assert not dialog.email_check.isEnabled()
    assert not dialog.new_page.isEnabled()
    assert QApplication.overrideCursor() is not None
    # Esc is ignored
    dialog.reject()
    assert dialog.isVisible()

    gate.set()
    qtbot.waitUntil(lambda: dialog.seed is not None, timeout=TIMEOUT_MS)
    assert QApplication.overrideCursor() is None


def test_connection_close_while_connecting_asks_and_quits_hard(
    qtbot: QtBot,
    tmp_path: Path,
    dialog: ConnectionDialog,
    directory_choice: DirectoryChoices,
    gate: threading.Event,
    boxes: MessageBoxes,
    exits: ExitCalls,
) -> None:
    directory_choice.path = str(new_dir(tmp_path))
    button(dialog, "Connect").click()

    boxes.answer = QMessageBox.StandardButton.Cancel
    dialog.close()
    assert boxes.titles() == ["Quit FIBSEM Maestro"]
    assert exits.codes == []
    assert dialog.isVisible()

    boxes.answer = QMessageBox.StandardButton.Yes
    dialog.close()
    assert exits.codes == [0]

    gate.set()
    qtbot.waitUntil(lambda: not dialog.connecting, timeout=5000)


def test_connection_close_while_idle_closes_without_asking(
    dialog: ConnectionDialog, boxes: MessageBoxes, exits: ExitCalls
) -> None:
    dialog.close()

    assert not dialog.isVisible()
    assert boxes.calls == []
    assert exits.codes == []


def test_connection_resume_loads_the_workflow(
    qtbot: QtBot, dialog: ConnectionDialog, workflow: Workflow, workflow_dir: Path
) -> None:
    # a workflow written by an earlier session
    WorkflowSession(workflow, workflow_dir, WorkflowFiles()).add_action(
        "imaging", "kept"
    )

    dialog.set_mode(1)
    dialog.resume_page.set_workflow_dir(workflow_dir)
    connect_and_wait(qtbot, dialog)

    seed = dialog.seed
    assert seed is not None
    assert seed.workflow_dir == workflow_dir
    assert [a.name for a in seed.workflow.actions] == ["kept"]


def test_connection_resume_without_a_directory_shows_an_error(
    dialog: ConnectionDialog, boxes: MessageBoxes
) -> None:
    dialog.set_mode(1)

    button(dialog, "Connect").click()

    assert boxes.texts() == ["No workflow directory selected"]
    assert not dialog.connecting


def test_connection_resume_of_a_non_workflow_reports_loading_failed(
    qtbot: QtBot,
    tmp_path: Path,
    dialog: ConnectionDialog,
    boxes: MessageBoxes,
) -> None:
    dialog.set_mode(1)
    dialog.resume_page.set_workflow_dir(new_dir(tmp_path))

    connect_and_wait(qtbot, dialog)

    assert len(boxes.texts()) == 1
    assert boxes.texts()[0].startswith("Loading failed: ")
    assert dialog.seed is None


def field(dialog: EmailSetupDialog, label: str) -> QLineEdit:
    """The input of the form row labelled `label`."""
    for form in children(dialog, QFormLayout):
        for row in range(form.rowCount()):
            label_item = form.itemAt(row, QFormLayout.ItemRole.LabelRole)
            field_item = form.itemAt(row, QFormLayout.ItemRole.FieldRole)
            if label_item is None or field_item is None:
                continue
            shown_label = label_item.widget()
            widget = field_item.widget()
            if (
                shown_label is not None
                and getattr(shown_label, "text", lambda: "")() == label
                and isinstance(widget, QLineEdit)
            ):
                return widget
    raise AssertionError(f"no field {label!r}")


def fill_email(dialog: EmailSetupDialog, password: str = PASSWORD) -> None:
    field(dialog, "SMTP server").setText("smtp.example.com")
    field(dialog, "Username").setText("user")
    field(dialog, "Send from").setText("maestro@example.com")
    field(dialog, "Send to").setText("me@example.com, you@example.com")
    field(dialog, "Password").setText(password)


def test_connection_email_setup_shows_recipients_and_never_saves_the_password(
    dialog: ConnectionDialog, user_config: UserConfig, maestro_home: AppPaths
) -> None:
    def fill_and_accept(email: EmailSetupDialog) -> None:
        fill_email(email)
        press(email, QDialogButtonBox.StandardButton.Ok)

    with answering(EmailSetupDialog, fill_and_accept) as shown:
        dialog.email_check.setChecked(True)

    assert shown
    assert dialog.email_check.isChecked()
    assert dialog.email_summary.isVisibleTo(dialog)
    assert "me@example.com" in dialog.email_summary.text()
    assert "you@example.com" in dialog.email_summary.text()
    assert dialog.email_settings is not None
    profile = user_config.load_email_profile()
    assert profile is not None
    assert profile.recipients == ("me@example.com", "you@example.com")
    stored = "".join(p.read_text() for p in maestro_home.config_dir.iterdir())
    assert PASSWORD not in stored


def test_connection_email_setup_rejects_incomplete_settings(
    dialog: ConnectionDialog, boxes: MessageBoxes
) -> None:
    def leave_password_empty(email: EmailSetupDialog) -> None:
        fill_email(email, password="")
        press(email, QDialogButtonBox.StandardButton.Ok)
        # the dialog stays open after the warning
        assert email.isVisible()
        press(email, QDialogButtonBox.StandardButton.Cancel)

    with answering(EmailSetupDialog, leave_password_empty):
        dialog.email_check.setChecked(True)

    assert boxes.titles() == ["Incomplete"]
    assert boxes.texts() == ["Password must not be empty."]
    assert not dialog.email_check.isChecked()
    assert dialog.email_settings is None


def test_connection_email_unchecked_drops_the_settings(
    dialog: ConnectionDialog,
) -> None:
    def fill_and_accept(email: EmailSetupDialog) -> None:
        fill_email(email)
        press(email, QDialogButtonBox.StandardButton.Ok)

    with answering(EmailSetupDialog, fill_and_accept):
        dialog.email_check.setChecked(True)

    dialog.email_check.setChecked(False)

    assert dialog.email_settings is None
    assert not dialog.email_summary.isVisibleTo(dialog)


def test_connection_email_setup_prefills_the_last_profile_but_not_the_password(
    dialog: ConnectionDialog,
) -> None:
    def fill_and_accept(email: EmailSetupDialog) -> None:
        fill_email(email)
        press(email, QDialogButtonBox.StandardButton.Ok)

    with answering(EmailSetupDialog, fill_and_accept):
        dialog.email_check.setChecked(True)
    dialog.email_check.setChecked(False)
    prefilled: dict[str, str] = {}

    def look(email: EmailSetupDialog) -> None:
        for label in ("SMTP server", "Send to", "Password"):
            prefilled[label] = field(email, label).text()
        press(email, QDialogButtonBox.StandardButton.Cancel)

    with answering(EmailSetupDialog, look):
        dialog.email_check.setChecked(True)

    assert prefilled == {
        "SMTP server": "smtp.example.com",
        "Send to": "me@example.com, you@example.com",
        "Password": "",
    }
    assert not dialog.email_check.isChecked()
