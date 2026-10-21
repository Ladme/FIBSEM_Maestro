# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF

"""Driving the composed main window as a user would: dialogs, the list, tools, runs."""

from __future__ import annotations

import threading
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any, TypeVar, cast

from PyQt6.QtCore import QObject, Qt, QTimer
from PyQt6.QtWidgets import (
    QAbstractSpinBox,
    QApplication,
    QDialog,
    QDialogButtonBox,
    QMenu,
    QPushButton,
    QWidget,
)

from fibsem_maestro.logging.text.file import close_all_log_files
from fibsem_maestro.ui.views.action_list.add_dialog import AddActionDialog
from fibsem_maestro.ui.views.log_panel.parsing import LEVELS, level_value
from fibsem_maestro.ui.views.log_panel.reader import LogReader
from gui_testkit import TIMEOUT_MS
from gui_testkit.app import shut_down, wait_for_task
from gui_testkit.workflows import seed_for

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator
    from pathlib import Path

    import pytest
    from pytestqt.qtbot import QtBot

    from fibsem_maestro.action.action import Action
    from fibsem_maestro.ui.app.files import WorkflowFiles
    from fibsem_maestro.ui.app.user_config import UserConfig
    from fibsem_maestro.ui.composition import Composition
    from fibsem_maestro.ui.views.action_list.item import ActionListItem
    from fibsem_maestro.ui.views.action_list.view import ActionListView
    from fibsem_maestro.ui.views.action_panel.panel import ActionPanel
    from fibsem_maestro.workflow.workflow import Workflow

T = TypeVar("T", bound=QObject)
D = TypeVar("D", bound=QDialog)

RUNNABLE_ACTION = "adjust_props"
"""
An action type that runs on the simulated microscope with its default settings once prepared.

Used by flows that need a run, whatever the action does; any type with this
property would do.
"""


def children(parent: QObject, cls: type[T]) -> list[T]:
    """The descendants of `parent` of type `cls`, in creation order."""
    return [cast("T", child) for child in parent.findChildren(cls)]


def button(parent: QWidget, text: str) -> QPushButton:
    """
    The push button with a given text among the descendants of `parent`.

    Raises:
        AssertionError: If there is none.
    """
    for candidate in children(parent, QPushButton):
        if candidate.text() == text:
            return candidate
    raise AssertionError(f"no button {text!r}")


def first_spin_box(parent: QWidget) -> QAbstractSpinBox:
    """The first shown spin box among the descendants of `parent` (a form's first number field)."""
    found = [s for s in children(parent, QAbstractSpinBox) if s.isVisibleTo(parent)]
    assert found, "the form shows no number field"
    return found[0]


def editable(field: QWidget) -> bool:
    """Whether a form input accepts edits (spin boxes are made read-only, others disabled)."""
    if isinstance(field, QAbstractSpinBox) and field.isReadOnly():
        return False
    return field.isEnabled()


@contextmanager
def answering(cls: type[D], handle: Callable[[D], None]) -> Iterator[list[D]]:
    """
    Answer the next modal dialog of type `cls` opened inside the block, as a user would.

    `handle(dialog)` runs once the dialog is shown (inside its `exec()`), and
    should end it (e.g. click OK). If it does not, or raises, the dialog is
    rejected so the test cannot hang; an exception is re-raised when the block ends.

    Yields:
        The dialogs answered (at most one).
    """
    answered: list[D] = []
    errors: list[BaseException] = []
    armed = True

    def answer() -> None:
        if not armed or answered:
            return
        dialog = QApplication.activeModalWidget()
        if not isinstance(dialog, cls):
            # not shown yet; look again
            QTimer.singleShot(10, answer)
            return
        answered.append(dialog)
        try:
            handle(dialog)
        except BaseException as e:
            errors.append(e)
        finally:
            if dialog.isVisible():
                dialog.reject()

    QTimer.singleShot(0, answer)
    try:
        yield answered
    finally:
        armed = False
    if errors:
        raise errors[0]


def press(dialog: QDialog, which: QDialogButtonBox.StandardButton) -> None:
    """Click a standard button (OK, Save, Cancel, ...) of a dialog's button box."""
    for box in children(dialog, QDialogButtonBox):
        if (found := box.button(which)) is not None:
            found.click()
            return
    raise AssertionError(f"the dialog has no {which.name} button")


def choose_from_context_menu(
    monkeypatch: pytest.MonkeyPatch, view: ActionListView, row: int, text: str | None
) -> dict[str, bool]:
    """
    Open the action list's context menu on a row and pick an entry (None: dismiss it).

    `QMenu.exec` is replaced, so the menu never blocks.

    Returns:
        Whether each entry of the menu was enabled, by its text.
    """
    entries: dict[str, bool] = {}

    def pick(menu: QMenu, *_: object) -> Any:
        actions = menu.actions()
        entries.update({a.text(): a.isEnabled() for a in actions})
        return next((a for a in actions if a.text() == text and a.isEnabled()), None)

    monkeypatch.setattr(QMenu, "exec", pick)
    widget = view.list_widget
    item = widget.item(row)
    assert item is not None
    widget.customContextMenuRequested.emit(widget.visualItemRect(item).center())
    return entries


def open_app(
    qtbot: QtBot,
    request: pytest.FixtureRequest,
    workflow: Workflow,
    workflow_dir: Path,
    user_config: UserConfig,
    files: WorkflowFiles,
) -> Composition:
    """
    Compose and show a main window, as the `app` fixture does, for a custom workflow or files.

    It is shut down when the test ends.
    """
    from fibsem_maestro.ui.composition import compose

    composition = compose(seed_for(workflow, workflow_dir), user_config, files)
    qtbot.addWidget(composition.window)
    composition.window.show()
    request.addfinalizer(lambda: shut_down(qtbot, composition.run, composition.tasks))
    return composition


def add_through_dialog(app: Composition, type_key: str, name: str) -> Action:
    """Add an action with "+ Add action" and the Add dialog, as a user does."""

    def fill(dialog: AddActionDialog) -> None:
        dialog.type_combo.setCurrentText(type_key)
        dialog.name_edit.setText(name)
        press(dialog, QDialogButtonBox.StandardButton.Ok)

    with answering(AddActionDialog, fill) as shown:
        app.window.action_list.add_button.click()
    assert shown, "the Add dialog was not shown"
    action = app.session.action_named(name)
    assert action is not None
    return action


def panel_of(app: Composition, action: Action) -> ActionPanel:
    """The cached panel of an action (select it first)."""
    panel = app.window.panel_host.panel(action)
    assert panel is not None, f"no panel for {action.name!r}"
    return panel


def item_of(app: Composition, action: Action) -> ActionListItem:
    """The list item of an action."""
    item = app.window.action_list.item_widget(action)
    assert item is not None, f"no list item for {action.name!r}"
    return item


def click_tool(app: Composition, action: Action, key: str) -> None:
    """Select an action and click one of its header's tool buttons."""
    app.window.action_list.select(action)
    panel_of(app, action).header.button(key).click()


def prepare_with_tool(qtbot: QtBot, app: Composition, action: Action) -> None:
    """Prepare an action with its Prepare tool and wait for the task."""
    click_tool(app, action, "prepare")
    qtbot.waitUntil(lambda: not app.tasks.busy, timeout=TIMEOUT_MS)


def add_prepared(qtbot: QtBot, app: Composition, name: str) -> Action:
    """Add a `RUNNABLE_ACTION` and prepare it through the commands."""
    action = app.commands.add_action(RUNNABLE_ACTION, name)
    wait_for_task(qtbot, app.tasks, app.commands.prepare_action(action))
    assert action.has_stored_properties()
    return action


def rename_inline(qtbot: QtBot, item: ActionListItem, name: str) -> None:
    """Double-click an item's name, type a new one and press Enter."""
    qtbot.mouseDClick(item.name_label, Qt.MouseButton.LeftButton)
    assert item.name_edit.isVisible(), "the inline editor did not open"
    item.name_edit.setText(name)
    qtbot.keyClick(item.name_edit, Qt.Key.Key_Return)


FAILURE_MESSAGE = "beam lost"
"""What a failing action (`fail_while`) raises."""


def fail_while(
    monkeypatch: pytest.MonkeyPatch, action: Action, condition: Callable[[], bool]
) -> None:
    """
    Make one action fail during a run for as long as `condition()` holds.

    The action's class gets a `should_execute` raising `RuntimeError(FAILURE_MESSAGE)`
    for this action (and deferring to the original otherwise), so the workflow
    reports an action error as for any failing step.
    """
    cls = type(action)
    original = cls.should_execute

    def should_execute(self: Action) -> bool:
        if self is action and condition():
            raise RuntimeError(FAILURE_MESSAGE)
        return original(self)

    monkeypatch.setattr(cls, "should_execute", should_execute)


def interrupt_run(
    qtbot: QtBot,
    app: Composition,
    monkeypatch: pytest.MonkeyPatch,
    condition: Callable[[Action], bool] = lambda _: True,
) -> tuple[Action, Action]:
    """
    Start a run of two prepared actions whose second fails, and wait for the error dialog.

    Args:
        condition: The second action fails while this holds for it.

    Returns:
        The first and the failing action.
    """
    first = add_prepared(qtbot, app, "first")
    second = add_prepared(qtbot, app, "second")
    fail_while(monkeypatch, second, lambda: condition(second))

    app.window.top_bar.run_button.click()
    qtbot.waitUntil(lambda: app.window.error_dialog is not None, timeout=TIMEOUT_MS)
    return first, second


@contextmanager
def task_running(qtbot: QtBot, app: Composition, action: Action) -> Iterator[None]:
    """Keep the microscope task runner busy for the block (a task waiting for it to end)."""
    release = threading.Event()
    handle = app.commands.run_microscope_task(action, "Waiting", release.wait)
    assert app.tasks.busy
    try:
        yield
    finally:
        release.set()
        wait_for_task(qtbot, app.tasks, handle)


def logged_messages(workflow_dir: Path, source: str, slice_index: int) -> list[str]:
    """
    The messages a source logged for a slice (all levels), after flushing the log files.

    Args:
        workflow_dir: The workflow directory.
        source: An action name or "workflow".
        slice_index: The slice.
    """
    close_all_log_files()
    lines = LogReader(workflow_dir).read(slice_index, [source], level_value(LEVELS[0]))
    return [line.message for line in lines]
