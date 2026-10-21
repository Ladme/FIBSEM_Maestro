# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF

from collections.abc import Callable

import pytest

from fibsem_maestro.action.action import Action
from fibsem_maestro.core.area import RelativeArea
from fibsem_maestro.core.point import RelativePoint
from fibsem_maestro.milling.error import MillingError
from fibsem_maestro.milling.milling import Milling, MillingState
from fibsem_maestro.workflow.workflow import Workflow

# The simulated microscope images 1024 x 768 px at 1.953125 nm/px, so the frame
# is 1500 nm high: an area 0.2 high holds exactly three 100 nm slices.
SLICE_NM = 100.0


def _area(height: float, y: float = 0.1) -> RelativeArea:
    return RelativeArea(origin=RelativePoint(0.1, y), width=0.5, height=height)


@pytest.fixture
def milling(add_action: Callable[..., Action]) -> Milling:
    action = add_action(
        "milling",
        "milling",
        milling_area=[_area(0.2)],
        pattern_type="rectangle",
        slice_distance=SLICE_NM,
    )
    action.prepare()
    assert isinstance(action, Milling)
    return action


def test_workflow_run_stops_after_last_slice(
    workflow: Workflow, add_action: Callable[..., Action]
) -> None:
    add_action("adjust_props", "adjust").prepare()
    workflow.run(last_slice=3)
    # slices 1, 2 and 3 were acquired; the counter points at the next one
    assert workflow.ctx.slice == 4


def test_workflow_run_never_passes_max_slice(
    workflow: Workflow,
    add_action: Callable[..., Action],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(Workflow, "MAX_SLICE", 2)
    add_action("adjust_props", "adjust").prepare()
    workflow.run(last_slice=50)
    assert workflow.ctx.slice == 3


def test_workflow_run_returns_on_completion_reason(
    workflow: Workflow,
    add_action: Callable[..., Action],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    action = add_action("adjust_props", "adjust")
    action.prepare()
    monkeypatch.setattr(
        type(action),
        "completion_reason",
        lambda self: "done" if self.ctx.slice >= 3 else None,
    )
    workflow.run()
    assert workflow.ctx.slice == 3
    assert workflow.completion_reasons() == ["'adjust': done"]


def test_milling_finishes_at_end_of_area_and_images_last_slice(
    workflow: Workflow, milling: Milling, add_action: Callable[..., Action]
) -> None:
    imaging = add_action("adjust_props", "after milling")
    imaging.prepare()
    workflow.run()
    # three slices fit; the action after milling also ran in the last one
    assert workflow.ctx.slice == 4
    assert imaging.ctx.slice == 4
    assert milling.completion_reason() == (
        "the milling area is used up; change it to continue"
    )


def test_milling_never_mills_outside_area(workflow: Workflow, milling: Milling) -> None:
    workflow.run()
    # what "Retry action" would do after the end: it must refuse, not mill
    with pytest.raises(MillingError, match="used up"):
        milling._run_step()


def test_milling_rejects_stored_slice_outside_area(milling: Milling) -> None:
    from fibsem_maestro.core.area import NMArea
    from fibsem_maestro.core.point import NMPoint

    outside = NMArea(origin=NMPoint(x=200.0, y=1400.0), width=750.0, height=SLICE_NM)
    milling.set_state(MillingState(milling_slice=outside))
    with pytest.raises(MillingError, match="outside the designated milling area"):
        milling._run_step()


def test_milling_continues_after_area_change(
    workflow: Workflow, milling: Milling
) -> None:
    workflow.run()
    milling.settings.milling_area = [_area(0.2, y=0.4)]
    assert milling.completion_reason() is None
    assert workflow.completion_reasons() == []
    workflow.run()
    assert workflow.ctx.slice == 7


def test_milling_slice_distance_change_keeps_stop(
    workflow: Workflow, milling: Milling
) -> None:
    workflow.run()
    milling.settings.slice_distance = 50.0
    assert milling.completion_reason() is not None
    assert milling.state.milling_slice is None


def test_milling_reset_clears_used_up_area(
    workflow: Workflow, milling: Milling
) -> None:
    workflow.run()
    milling.reset()
    assert milling.completion_reason() is None
    assert milling.state == MillingState()


def test_milling_completion_reason_without_area_is_none(
    add_action: Callable[..., Action],
) -> None:
    action = add_action("milling", "new milling")
    assert isinstance(action, Milling)
    action.set_state(MillingState(used_up_area=_area(0.2)))
    assert action.completion_reason() is None


def test_milling_used_up_area_survives_resume(
    workflow: Workflow, milling: Milling
) -> None:
    workflow.run()
    # the state written for the action's current slice is what a resume reads
    stored = milling.ctx.state_store.read("state.yaml", MillingState)
    assert stored.used_up_area == _area(0.2)


def test_milling_state_without_used_up_area_loads() -> None:
    assert MillingState.model_validate({"milling_slice": None}).used_up_area is None
