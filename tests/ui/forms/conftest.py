# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF

"""Fixtures of the form tests: a form context for the synthetic settings, and a form maker."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest
from gui_testkit.forms import FakeCatalog, recording_logger
from gui_testkit.sample_settings import LINKED_NAME, PATTERN_TYPES, VENDOR_PROPERTIES
from gui_testkit.workflows import simulated_workflow

from fibsem_maestro.action.registry import ACTION_REGISTRY
from fibsem_maestro.ui.app.files import WorkflowFiles
from fibsem_maestro.ui.app.session import WorkflowSession
from fibsem_maestro.ui.forms.context import FormContext

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from PyQt6.QtWidgets import QApplication
    from pytestqt.qtbot import QtBot

    from fibsem_maestro.action.action import Action
    from fibsem_maestro.logging.text.memory import MemoryTextLogger
    from fibsem_maestro.ui.forms.builder import Form, FormBuilder


@pytest.fixture
def log() -> MemoryTextLogger:
    """Receives the build-time warnings of forms built in `sink_context`."""
    return recording_logger()


@pytest.fixture(scope="session")
def linked_action(
    qapp: QApplication, tmp_path_factory: pytest.TempPathFactory
) -> Action:
    """
    A real action named `LINKED_NAME`, shared by all tests; its type does not matter.

    Tests only list it in catalogs and read its name; never rename or remove it.
    """
    _ = qapp  # the session is a QObject
    directory = tmp_path_factory.mktemp("linked_workflow")
    session = WorkflowSession(simulated_workflow(directory), directory, WorkflowFiles())
    return session.add_action(next(iter(ACTION_REGISTRY)), LINKED_NAME)


@pytest.fixture
def catalog(linked_action: Action) -> FakeCatalog:
    """An action catalog holding `linked_action`."""
    return FakeCatalog([linked_action])


@pytest.fixture
def sink_context(log: MemoryTextLogger, catalog: FakeCatalog) -> FormContext:
    """The context the synthetic settings are valid in: catalogs, actions and a logger."""
    return FormContext(
        log=log,
        actions=catalog.port(),
        manufacturer_property_names=VENDOR_PROPERTIES,
        pattern_types=PATTERN_TYPES,
    )


@pytest.fixture
def live_form(
    qtbot: QtBot, form_builder: FormBuilder, sink_context: FormContext
) -> Callable[..., Form]:
    """
    Build a live form in `sink_context`; its widget is cleaned up after the test.

    Call as `live_form(settings, fields=None, on_commit=None, ctx=None)`.
    """

    def build(
        settings: Any,
        fields: Sequence[str] | None = None,
        on_commit: Callable[[str], None] | None = None,
        ctx: FormContext | None = None,
    ) -> Form:
        form = form_builder.build_live(
            settings,
            ctx if ctx is not None else sink_context,
            fields=fields,
            on_commit=on_commit if on_commit is not None else _ignore,
        )
        qtbot.addWidget(form.widget)
        return form

    return build


def _ignore(path: str) -> None:
    _ = path
