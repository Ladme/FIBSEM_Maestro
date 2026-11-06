# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF

"""Danger mode unlocks settings and Edit while the workflow runs, and nothing else."""

from __future__ import annotations

import threading
from contextlib import contextmanager
from typing import TYPE_CHECKING

from gui_testkit import TIMEOUT_MS
from gui_testkit.app import wait_for_state
from gui_testkit.driving import (
    add_prepared,
    answering,
    button,
    click_tool,
    editable,
    first_spin_box,
    panel_of,
    press,
)
from PyQt6.QtWidgets import QDialogButtonBox

from fibsem_maestro.properties.beam_properties import BeamProperties
from fibsem_maestro.properties.global_properties import GlobalProperties
from fibsem_maestro.serializer.yaml_serializer import YamlSerializer
from fibsem_maestro.ui.app.run_state import AppState
from fibsem_maestro.ui.views.dialogs.microscope_settings import (
    MicroscopeSettingsDialog,
)
from fibsem_maestro.ui.widgets.properties_dialog import PropertiesDialog

if TYPE_CHECKING:
    from collections.abc import Generator

    import pytest
    from gui_testkit.dialogs import MessageBoxes
    from pytestqt.qtbot import QtBot

    from fibsem_maestro.action.action import Action
    from fibsem_maestro.action.outcome import StepOutcome
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
    # only the settings (and Edit): rules, the other tools and the structure
    # still follow the run
    rules = panel.propagations
    assert rules is not None
    assert not rules.add_button.isEnabled()
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


@contextmanager
def held_in(
    qtbot: QtBot,
    app: Composition,
    monkeypatch: pytest.MonkeyPatch,
    blocker: Action,
) -> Generator[None]:
    """
    Run the workflow, holding it inside `blocker`'s step for the block, then pause it.

    While it is held, the other actions' slices and props stay as they are.
    """
    entered, release = threading.Event(), threading.Event()
    run_step = blocker._run_step

    def held() -> StepOutcome:
        entered.set()
        release.wait(TIMEOUT_MS / 1000)
        return run_step()

    monkeypatch.setattr(blocker, "_run_step", held)
    top_bar = app.window.top_bar
    top_bar.run_button.click()
    try:
        qtbot.waitUntil(entered.is_set, timeout=TIMEOUT_MS)
        assert app.run.state is AppState.RUNNING
        yield
    finally:
        top_bar.run_button.click()
        release.set()
        wait_for_state(qtbot, app.run, AppState.PAUSED)


def test_flow_danger_mode_edits_the_props_of_a_running_workflow(
    qtbot: QtBot,
    app: Composition,
    monkeypatch: pytest.MonkeyPatch,
    boxes: MessageBoxes,
) -> None:
    target = add_prepared(qtbot, app, "target")
    blocker = add_prepared(qtbot, app, "blocker")
    app.window.action_list.select(target)
    edit = panel_of(app, target).header.button("edit")
    changed_meanwhile = GlobalProperties(
        electron_beam=BeamProperties(working_distance=1.0e6)
    )

    def save(dialog: PropertiesDialog) -> None:
        press(dialog, QDialogButtonBox.StandardButton.Save)

    def save_after_the_props_changed(dialog: PropertiesDialog) -> None:
        # as if the workflow propagated to the action while the dialog was open
        target.write_properties(changed_meanwhile)
        press(dialog, QDialogButtonBox.StandardButton.Save)

    with held_in(qtbot, app, monkeypatch, blocker):
        assert not edit.isEnabled()
        app.window.top_bar.danger_button.click()
        assert edit.isEnabled()
        assert not panel_of(app, target).header.button("prepare").isEnabled()

        with (
            qtbot.waitSignal(app.session.action_props_changed) as saved,
            answering(PropertiesDialog, save) as dialogs,
        ):
            click_tool(app, target, "edit")
        assert dialogs and saved.args == [target]

        with (
            qtbot.assertNotEmitted(app.session.action_props_changed),
            answering(PropertiesDialog, save_after_the_props_changed),
        ):
            click_tool(app, target, "edit")

        # the edits made to outdated props did not overwrite the newer ones
        assert boxes.titles() == ["Properties not saved"]
        assert target.read_properties() == changed_meanwhile
