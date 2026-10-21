# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF

"""
An area selector's Load acquires through the real `PreviewService` on the task thread.

`imaging` is used because its settings hold an area selector and it runs with
its defaults once prepared.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from gui_testkit import TIMEOUT_MS
from gui_testkit.app import wait_for_state
from gui_testkit.driving import (
    add_through_dialog,
    button,
    children,
    panel_of,
    prepare_with_tool,
    task_running,
)
from PyQt6.QtWidgets import QLabel, QPushButton

from fibsem_maestro.ui.app.run_state import AppState
from fibsem_maestro.ui.forms.editors.area_select.widget import AreaSelectWidget

if TYPE_CHECKING:
    from pytestqt.qtbot import QtBot

    from fibsem_maestro.action.action import Action
    from fibsem_maestro.ui.composition import Composition


def selector_of(app: Composition, action: Action) -> AreaSelectWidget:
    return children(panel_of(app, action), AreaSelectWidget)[0]


def load_button(selector: AreaSelectWidget) -> QPushButton:
    return button(selector, "Load")


def status(selector: AreaSelectWidget) -> list[str]:
    return [label.text() for label in children(selector, QLabel)]


def test_flow_previews_load_acquires_an_image_off_the_gui_thread(
    qtbot: QtBot, app: Composition
) -> None:
    imaging = add_through_dialog(app, "imaging", "imaging")
    other = add_through_dialog(app, "imaging", "other")
    app.window.action_list.select(imaging)
    selector = selector_of(app, imaging)
    before = imaging.settings.model_copy(deep=True)

    load_button(selector).click()

    # V6/V7: one task application-wide, and the window keeps responding
    assert app.tasks.busy
    assert "Loading image..." in status(selector)
    assert not load_button(selector).isEnabled()
    assert not panel_of(app, other).header.button("prepare").isEnabled()
    qtbot.waitUntil(lambda: not app.tasks.busy, timeout=TIMEOUT_MS)

    assert any(text.startswith("Image: ") for text in status(selector))
    assert load_button(selector).isEnabled()
    # loading an image alone changes no area
    assert imaging.settings == before


def test_flow_previews_load_waits_for_a_task_and_the_run(
    qtbot: QtBot, app: Composition
) -> None:
    imaging = add_through_dialog(app, "imaging", "imaging")
    selector = selector_of(app, imaging)
    load = load_button(selector)
    assert load.isEnabled()

    with task_running(qtbot, app, imaging):
        assert not load.isEnabled()
    assert load.isEnabled()

    prepare_with_tool(qtbot, app, imaging)
    app.window.top_bar.run_button.click()
    assert not load.isEnabled()
    # danger mode unlocks the settings, not the microscope
    app.commands.set_danger_mode(True)
    assert not load.isEnabled()

    app.window.top_bar.run_button.click()
    wait_for_state(qtbot, app.run, AppState.PAUSED)
    assert load.isEnabled()
