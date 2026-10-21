# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF

"""Fixtures of the contract tests: the form contexts the application builds, with a recording logger."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

import pytest
from gui_testkit.forms import recording_logger

from fibsem_maestro.ui.composition import FormContexts

if TYPE_CHECKING:
    from collections.abc import Callable

    from gui_testkit.app import Services

    from fibsem_maestro.logging.text.memory import MemoryTextLogger
    from fibsem_maestro.ui.forms.context import FormContext


@pytest.fixture
def log() -> MemoryTextLogger:
    """Receives the build-time warnings of the forms built through `recorded`."""
    return recording_logger()


@pytest.fixture
def form_contexts(services: Services) -> FormContexts:
    """The form contexts, built from the services as the composition root builds them."""
    return FormContexts(
        services.session, services.catalogs, services.commands, services.policy
    )


@pytest.fixture
def recorded(log: MemoryTextLogger) -> Callable[[FormContext], FormContext]:
    """The same context, logging to `log` instead of the workflow log."""
    return lambda ctx: replace(ctx, log=log)
