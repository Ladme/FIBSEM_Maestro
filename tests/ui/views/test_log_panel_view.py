# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF

"""The log panel: `LogReader` over log files in `tmp_path`, and the view's slice, source and level choices."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import pytest
from gui_testkit import TIMEOUT_MS
from gui_testkit.app import wait_for_state
from gui_testkit.driving import add_prepared, children, item_of, rename_inline
from PyQt6.QtWidgets import QComboBox

from fibsem_maestro.ui.app.run_state import AppState
from fibsem_maestro.ui.views.log_panel.parsing import LEVELS
from fibsem_maestro.ui.views.log_panel.reader import WORKFLOW_SOURCE, LogReader

if TYPE_CHECKING:
    from pathlib import Path

    from pytestqt.qtbot import QtBot

    from fibsem_maestro.ui.composition import Composition
    from fibsem_maestro.ui.views.log_panel.view import LogPanel

POLL_TIMEOUT_MS = 5_000
"""Comfortably more than the panel's one-second poll."""


def line(second: int, message: str, level: str = "INFO") -> str:
    return f"2026-06-23 14:39:{second:02d},000 [test] {level}: {message}\n"


def append(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(text)


@pytest.fixture
def reader(tmp_path: Path) -> LogReader:
    return LogReader(tmp_path)


def messages(lines: list) -> list[str]:
    return [parsed.message for parsed in lines]


def test_log_reader_merges_sources_by_time_and_filters_the_level(
    reader: LogReader,
) -> None:
    append(reader.log_path("drift correction", 0), line(3, "third") + line(1, "first"))
    append(
        reader.log_path(WORKFLOW_SOURCE, 0),
        line(2, "second") + line(4, "debug", "DEBUG"),
    )

    lines = reader.read(0, ["drift correction", WORKFLOW_SOURCE], logging.INFO)

    assert messages(lines) == ["first", "second", "third"]
    # an action's directory is its name with underscores
    assert reader.log_path("drift correction", 0).parent.parent.name == (
        "drift_correction"
    )


def test_log_reader_poll_returns_only_new_lines(reader: LogReader) -> None:
    path = reader.log_path("a", 0)
    append(path, line(1, "old"))
    assert messages(reader.read(0, ["a"], logging.DEBUG)) == ["old"]

    assert reader.poll(0, ["a"], logging.DEBUG) == []
    append(path, line(2, "new"))

    assert messages(reader.poll(0, ["a"], logging.DEBUG)) == ["new"]


def test_log_reader_returns_a_line_only_once_it_is_complete(reader: LogReader) -> None:
    path = reader.log_path("a", 0)
    append(path, line(1, "complete") + line(2, "still being written").rstrip("\n"))

    assert messages(reader.read(0, ["a"], logging.DEBUG)) == ["complete"]

    append(path, " to the end\n")
    assert messages(reader.poll(0, ["a"], logging.DEBUG)) == [
        "still being written to the end"
    ]


def test_log_reader_read_starts_over(reader: LogReader) -> None:
    append(reader.log_path("a", 0), line(1, "one"))
    reader.read(0, ["a"], logging.DEBUG)

    assert messages(reader.read(0, ["a"], logging.DEBUG)) == ["one"]


def test_log_reader_lists_the_slices_of_every_source(reader: LogReader) -> None:
    append(reader.log_path("a", 2), line(1, "x"))
    append(reader.log_path(WORKFLOW_SOURCE, 0), line(1, "x"))
    (reader.source_dir("a") / "not_a_slice").mkdir()

    assert reader.slices(["a", WORKFLOW_SOURCE, "missing"]) == [0, 2]
    assert reader.has_slice(["a"], 2)
    assert not reader.has_slice(["a"], 1)


def test_log_reader_follows_a_new_workflow_directory(
    reader: LogReader, tmp_path: Path
) -> None:
    append(reader.log_path("a", 0), line(1, "old workflow"))
    reader.read(0, ["a"], logging.DEBUG)
    other = tmp_path / "other"
    reader.set_workflow_dir(other)
    append(reader.log_path("a", 0), line(1, "new workflow"))

    assert reader.log_path("a", 0).is_relative_to(other)
    assert messages(reader.poll(0, ["a"], logging.DEBUG)) == ["new workflow"]


def level_combo(panel: LogPanel) -> QComboBox:
    (combo,) = [
        c
        for c in children(panel, QComboBox)
        if [c.itemText(i) for i in range(c.count())] == LEVELS
    ]
    return combo


def shows(panel: LogPanel, text: str) -> bool:
    return text in panel.log_view.toPlainText()


def test_log_panel_current_shows_the_workflow_slice(app: Composition) -> None:
    app.commands.add_action("imaging", "a")
    panel = app.window.log_panel
    reader = LogReader(app.session.workflow_dir)
    assert panel.slice_combo.currentText() == "current"
    append(reader.log_path("a", 0), line(1, "in slice zero"))
    append(reader.log_path("a", 1), line(1, "in slice one"))

    # choosing re-reads the logs at once
    panel.source_combo.setCurrentText("a")

    assert shows(panel, "in slice zero")
    assert not shows(panel, "in slice one")


def test_log_panel_polls_an_explicitly_selected_slice(
    qtbot: QtBot, app: Composition
) -> None:
    app.commands.add_action("imaging", "a")
    panel = app.window.log_panel
    path = LogReader(app.session.workflow_dir).log_path("a", 1)
    append(path, line(1, "first line"))
    # a newly created slice directory is picked up by the poll
    qtbot.waitUntil(
        lambda: panel.slice_combo.findText("1") >= 0, timeout=POLL_TIMEOUT_MS
    )

    panel.slice_combo.setCurrentText("1")
    assert shows(panel, "first line")

    # D19: lines written later appear without selecting the slice again
    append(path, line(2, "second line"))
    qtbot.waitUntil(lambda: shows(panel, "second line"), timeout=POLL_TIMEOUT_MS)


def test_log_panel_filters_by_source_and_level(app: Composition) -> None:
    app.commands.add_action("imaging", "a")
    app.commands.add_action("imaging", "b")
    panel = app.window.log_panel
    reader = LogReader(app.session.workflow_dir)
    append(reader.log_path("a", 0), line(1, "a info") + line(2, "a warning", "WARNING"))
    append(reader.log_path("b", 0), line(3, "b info"))

    # choosing re-reads the logs at once
    panel.source_combo.setCurrentText("b")
    assert shows(panel, "b info")
    panel.source_combo.setCurrentText("a")
    assert shows(panel, "a info")
    assert not shows(panel, "b info")

    level_combo(panel).setCurrentText("WARNING")
    assert shows(panel, "a warning")
    assert not shows(panel, "a info")


def test_log_panel_sources_follow_the_actions(qtbot: QtBot, app: Composition) -> None:
    action = app.commands.add_action("imaging", "a")
    combo = app.window.log_panel.source_combo
    sources = [combo.itemText(i) for i in range(combo.count())]
    assert sources == ["all", "a", WORKFLOW_SOURCE]

    rename_inline(qtbot, item_of(app, action), "renamed")

    sources = [combo.itemText(i) for i in range(combo.count())]
    assert sources == ["all", "renamed", WORKFLOW_SOURCE]


def test_log_panel_lists_the_slices_of_a_run_and_current_follows_it(
    qtbot: QtBot, app: Composition
) -> None:
    add_prepared(qtbot, app, "first")
    panel = app.window.log_panel

    app.window.top_bar.run_button.click()
    qtbot.waitUntil(lambda: app.session.slice >= 2, timeout=TIMEOUT_MS)
    app.window.top_bar.run_button.click()
    wait_for_state(qtbot, app.run, AppState.PAUSED)

    listed = [panel.slice_combo.itemText(i) for i in range(panel.slice_combo.count())]
    assert {"current", "0", "1"} <= set(listed)
    # "current" is the slice the workflow as a whole is in
    current = app.session.slice
    qtbot.waitUntil(
        lambda: shows(panel, f"Starting slice {current}."), timeout=POLL_TIMEOUT_MS
    )
    assert not shows(panel, f"Starting slice {current - 1}.")
