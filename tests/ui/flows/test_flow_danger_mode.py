# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF

"""Danger mode unlocks settings while the workflow runs, and nothing else."""

from __future__ import annotations

from typing import TYPE_CHECKING

from gui_testkit.app import wait_for_state
from gui_testkit.driving import (
    add_prepared,
    answering,
    button,
    editable,
    first_spin_box,
    panel_of,
)

from fibsem_maestro.serializer.yaml_serializer import YamlSerializer
from fibsem_maestro.ui.app.run_state import AppState
from fibsem_maestro.ui.views.dialogs.microscope_settings import (
    MicroscopeSettingsDialog,
)

if TYPE_CHECKING:
    from pytestqt.qtbot import QtBot

    from fibsem_maestro.ui.app.user_config import UserConfig
    from fibsem_maestro.ui.composition import Composition


def test_flow_danger_mode_edits_the_settings_of_a_running_workflow(
    qtbot: QtBot, app: Composition
) -> None:
    action = add_prepared(qtbot, app, "first")
    app.window.action_list.select(action)
    panel = panel_of(app, action)
    field = first_spin_box(panel.form.widget)
    top_bar = app.window.top_bar
    top_bar.run_button.click()
    assert not editable(field)

    top_bar.danger_button.click()

    assert app.window.danger_banner.isVisible()
    assert editable(field)
    with qtbot.waitSignal(app.session.action_settings_changed):
        field.stepBy(1)
    edited = action.settings.model_copy(deep=True)
    # only the settings: rules, tools and the structure still follow the run
    assert not panel.propagations.add_button.isEnabled()
    assert not panel.header.button("prepare").isEnabled()
    assert not app.window.action_list.add_button.isEnabled()

    top_bar.danger_button.click()
    assert not app.window.danger_banner.isVisible()
    assert not editable(field)

    top_bar.run_button.click()
    wait_for_state(qtbot, app.run, AppState.PAUSED)
    # the run picked the edit up: the action's later slices carry it
    assert action.settings == edited
    stored = (
        app.session.workflow_dir
        / "first"
        / f"slice_{action.ctx.slice:04d}"
        / "settings.yaml"
    )
    assert type(edited).model_validate(YamlSerializer.load(stored)) == edited


def test_flow_danger_mode_unlocks_the_microscope_settings_while_running(
    qtbot: QtBot, app: Composition, user_config: UserConfig
) -> None:
    add_prepared(qtbot, app, "first")
    top_bar = app.window.top_bar
    top_bar.run_button.click()
    top_bar.danger_button.click()
    read_only: list[bool] = []

    def apply(dialog: MicroscopeSettingsDialog) -> None:
        read_only.append(dialog.read_only)
        first_spin_box(dialog).stepBy(1)
        button(dialog, "Apply").click()

    with answering(MicroscopeSettingsDialog, apply):
        top_bar.microscope_button.click()

    assert read_only == [False]
    assert user_config.load_microscope_profile() == app.session.microscope.settings

    top_bar.run_button.click()
    wait_for_state(qtbot, app.run, AppState.PAUSED)
