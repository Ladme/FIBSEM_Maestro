# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF

"""`MicroscopeCatalogs`: the microscope's choice lists, read once per session."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fibsem_maestro.logging.text.memory import MemoryTextLogger
from fibsem_maestro.ui.app.catalogs import MicroscopeCatalogs

if TYPE_CHECKING:
    import pytest

    from fibsem_maestro.workflow.workflow import Workflow


def test_catalogs_query_reads_the_microscope(workflow: Workflow) -> None:
    control = workflow.microscope.control
    catalogs = MicroscopeCatalogs.query(workflow.microscope)
    assert catalogs.manufacturer_property_names == tuple(
        control.manufacturer_prop_names
    )
    assert catalogs.pattern_types == tuple(control.available_patterns)
    assert catalogs.pattern_types  # the simulated microscope offers some


def test_catalogs_query_failure_yields_empty_lists_and_warnings(
    workflow: Workflow, monkeypatch: pytest.MonkeyPatch
) -> None:
    def unavailable(_: object) -> list[str]:
        raise ConnectionError("server gone")

    control_cls = type(workflow.microscope.control)
    monkeypatch.setattr(control_cls, "manufacturer_prop_names", property(unavailable))
    monkeypatch.setattr(control_cls, "available_patterns", property(unavailable))
    log = MemoryTextLogger(lambda: 0)

    catalogs = MicroscopeCatalogs.query(workflow.microscope, log)

    assert catalogs == MicroscopeCatalogs()
    assert [(r.level, r.message) for r in log.records[0]] == [
        ("warning", "Could not read the manufacturer property names: server gone"),
        ("warning", "Could not read the available pattern types: server gone"),
    ]
