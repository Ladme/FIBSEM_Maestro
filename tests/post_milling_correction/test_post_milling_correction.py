# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF

from __future__ import annotations

import math
from typing import TYPE_CHECKING

import pytest

from fibsem_maestro.action.outcome import Produced
from fibsem_maestro.core.beam_shift import BeamShift
from fibsem_maestro.core.beam_type import BeamType
from fibsem_maestro.core.direction import Direction
from fibsem_maestro.post_milling_correction.correction import PostMillingCorrection
from fibsem_maestro.post_milling_correction.error import PostMillingCorrectionError
from fibsem_maestro.properties.global_properties import GlobalProperties
from fibsem_maestro.settings.post_milling_correction_settings import (
    DynamicFocusMode,
    ManualMode,
)
from fibsem_maestro.settings.property_names import PropertyNames
from fibsem_maestro.workflow.propagations import PropagationRule, Propagations
from fibsem_maestro.workflow.workflow import Workflow

if TYPE_CHECKING:
    from collections.abc import Callable

    from fibsem_maestro.action.action import Action
    from fibsem_maestro.properties.beam_properties import BeamProperties

# per run (nm)
Y_CORRECTION = 10.0
WD_CORRECTION = 20.0

IMAGE_TO_BEAM_SHIFT = (3.0, -2.0)
ION_IMAGE_TO_BEAM_SHIFT = (5.0, 7.0)

CORRECTED = ["working_distance", "beam_shift"]


@pytest.fixture(autouse=True)
def image_to_beam_shift(monkeypatch: pytest.MonkeyPatch, workflow: Workflow) -> None:
    for beam, factors in (
        (workflow.microscope.electron_beam, IMAGE_TO_BEAM_SHIFT),
        (workflow.microscope.ion_beam, ION_IMAGE_TO_BEAM_SHIFT),
    ):
        monkeypatch.setattr(
            type(beam), "image_to_beam_shift", property(lambda _, f=factors: f)
        )


@pytest.fixture
def add_prepared(add_action: Callable[..., Action]) -> Callable[..., Action]:
    """Add an action at the end of the workflow, with its properties collected."""

    def add(type_key: str, name: str, **settings: object) -> Action:
        action = add_action(type_key, name, **settings)
        action.write_properties(action.collect_properties())
        return action

    return add


@pytest.fixture
def add_imaging(add_prepared: Callable[..., Action]) -> Callable[..., Action]:
    """Add an imaging collecting the corrected properties of its beam."""

    def add(name: str, beam_type: BeamType = BeamType.ELECTRON) -> Action:
        names = (
            PropertyNames(electron_beam=CORRECTED)
            if beam_type is BeamType.ELECTRON
            else PropertyNames(ion_beam=CORRECTED)
        )
        return add_prepared(
            "imaging", name, beam_type=beam_type, properties_to_collect=names
        )

    return add


@pytest.fixture
def add_correction(add_prepared: Callable[..., Action]) -> Callable[..., Action]:
    """Add a post-milling correction, by default a manual one."""

    def add(
        corrected: list[str], mode: ManualMode | DynamicFocusMode | None = None
    ) -> Action:
        return add_prepared(
            "post_milling_correction",
            "correction",
            corrected_actions=corrected,
            correction_mode=mode
            or ManualMode(y_correction=Y_CORRECTION, wd_correction=WD_CORRECTION),
        )

    return add


def upcoming(action: Action) -> BeamProperties:
    """The electron-beam properties the action applies on its next run."""
    props = action.read_properties().electron_beam
    assert props is not None
    return props


def shifted(
    props: BeamProperties, runs: int, y: float = Y_CORRECTION, wd: float = WD_CORRECTION
) -> tuple[float, BeamShift]:
    """The working distance and beam shift after `runs` corrections."""
    assert props.working_distance is not None and props.beam_shift is not None
    delta = BeamShift(0.0, IMAGE_TO_BEAM_SHIFT[1] * y * runs)
    return props.working_distance + wd * runs, props.beam_shift + delta


def corrected_values(props: BeamProperties) -> tuple[float, BeamShift]:
    assert props.working_distance is not None and props.beam_shift is not None
    return props.working_distance, props.beam_shift


def test_corrections_accumulate_on_actions_before_and_after_it(
    workflow: Workflow,
    add_imaging: Callable[..., Action],
    add_correction: Callable[..., Action],
) -> None:
    before = add_imaging("before")
    add_correction(["before", "after"])
    after = add_imaging("after")
    initial = {action.name: upcoming(action) for action in (before, after)}

    workflow.run(last_slice=3)

    for action in (before, after):
        expected = shifted(initial[action.name], runs=3)
        assert corrected_values(upcoming(action)) == pytest.approx(expected)


def test_correction_never_changes_the_microscope(
    workflow: Workflow,
    add_imaging: Callable[..., Action],
    add_correction: Callable[..., Action],
) -> None:
    add_imaging("imaging")
    correction = add_correction(["imaging"])
    microscope = workflow.microscope
    microscope.set_beam(BeamType.ION)
    beam = microscope.electron_beam
    before = (beam.working_distance, beam.beam_shift)

    outcome = correction.execute()

    # not even the beam is selected
    assert microscope.beam is microscope.ion_beam

    assert isinstance(outcome, Produced)
    assert (beam.working_distance, beam.beam_shift) == before


def test_correction_patches_only_the_corrected_properties(
    add_imaging: Callable[..., Action],
    add_correction: Callable[..., Action],
) -> None:
    imaging = add_imaging("imaging")
    correction = add_correction(["imaging"])
    expected_wd, expected_shift = shifted(upcoming(imaging), runs=1)

    outcome = correction.execute()

    assert isinstance(outcome, Produced)
    assert set(outcome.patches) == {"imaging"}
    patch = outcome.patches["imaging"]
    assert set(patch.get_property_names().electron_beam) == set(CORRECTED)
    assert patch.microscope is None and patch.ion_beam is None
    assert patch.electron_beam is not None
    assert patch.electron_beam.working_distance == pytest.approx(expected_wd)
    assert patch.electron_beam.beam_shift == expected_shift
    # it stores no properties of its own
    assert outcome.props == GlobalProperties()


def test_each_target_is_corrected_on_its_own_beam(
    add_imaging: Callable[..., Action],
    add_correction: Callable[..., Action],
) -> None:
    electron = add_imaging("electron")
    ion = add_imaging("ion", beam_type=BeamType.ION)
    correction = add_correction(["electron", "ion"])
    ion_props = ion.read_properties().ion_beam
    assert ion_props is not None and ion_props.working_distance is not None
    assert ion_props.beam_shift is not None
    expected_ion = (
        ion_props.working_distance + WD_CORRECTION,
        ion_props.beam_shift
        + BeamShift(0.0, ION_IMAGE_TO_BEAM_SHIFT[1] * Y_CORRECTION),
    )
    expected_electron = shifted(upcoming(electron), runs=1)

    outcome = correction.execute()

    assert isinstance(outcome, Produced)
    ion_patch = outcome.patches["ion"]
    assert ion_patch.electron_beam is None and ion_patch.ion_beam is not None
    assert corrected_values(ion_patch.ion_beam) == pytest.approx(expected_ion)
    electron_patch = outcome.patches["electron"]
    assert electron_patch.ion_beam is None and electron_patch.electron_beam is not None
    assert corrected_values(electron_patch.electron_beam) == pytest.approx(
        expected_electron
    )


def test_action_of_any_type_is_corrected(
    add_prepared: Callable[..., Action],
    add_correction: Callable[..., Action],
) -> None:
    milling = add_prepared(
        "milling",
        "milling",
        beam_type=BeamType.ELECTRON,
        properties_to_collect=PropertyNames(electron_beam=CORRECTED),
    )
    correction = add_correction(["milling"])
    expected = shifted(upcoming(milling), runs=1)

    outcome = correction.execute()

    assert correction.preparation_issues() == []
    assert isinstance(outcome, Produced)
    patch = outcome.patches["milling"].electron_beam
    assert patch is not None
    assert corrected_values(patch) == pytest.approx(expected)


def test_action_without_a_beam_cannot_be_corrected(
    add_prepared: Callable[..., Action],
    add_correction: Callable[..., Action],
) -> None:
    # it even collects the corrected properties, but has no beam to correct them on
    add_prepared(
        "adjust_props",
        "adjust",
        properties_to_collect=PropertyNames(electron_beam=CORRECTED),
    )
    correction = add_correction(["adjust"])

    assert correction.preparation_issues() == [
        "'adjust' works on no beam, so it cannot be corrected."
    ]
    with pytest.raises(PostMillingCorrectionError, match="works on no beam"):
        correction.execute()


def test_zero_correction_patches_nothing(
    add_imaging: Callable[..., Action],
    add_correction: Callable[..., Action],
) -> None:
    add_imaging("imaging")
    correction = add_correction(["imaging"], ManualMode())

    outcome = correction.execute()

    assert isinstance(outcome, Produced)
    assert outcome.patches == {}


def test_manual_correction_patches_only_its_non_zero_part(
    add_imaging: Callable[..., Action],
    add_correction: Callable[..., Action],
) -> None:
    add_imaging("imaging")
    correction = add_correction(["imaging"], ManualMode(wd_correction=WD_CORRECTION))

    outcome = correction.execute()

    assert isinstance(outcome, Produced)
    assert outcome.patches["imaging"].get_property_names() == PropertyNames(
        electron_beam=["working_distance"]
    )


@pytest.mark.parametrize(
    ("direction", "sign"), [(Direction.DOWN, 1.0), (Direction.UP, -1.0)]
)
def test_dynamic_correction_follows_the_milling_geometry(
    add_prepared: Callable[..., Action],
    add_imaging: Callable[..., Action],
    add_correction: Callable[..., Action],
    direction: Direction,
    sign: float,
) -> None:
    add_prepared("milling", "milling", slice_distance=10.0, milling_direction=direction)
    imaging = add_imaging("imaging")
    correction = add_correction(["imaging"], DynamicFocusMode())
    correction.settings.linked_milling = "milling"
    angle = math.radians(52.0)
    expected = shifted(
        upcoming(imaging),
        runs=1,
        y=sign * 10.0 * math.cos(angle),
        wd=sign * 10.0 * math.sin(angle),
    )

    outcome = correction.execute()

    assert isinstance(outcome, Produced)
    patch = outcome.patches["imaging"].electron_beam
    assert patch is not None
    assert corrected_values(patch) == pytest.approx(expected)


def test_correction_fails_if_a_target_stores_no_value_to_correct(
    add_imaging: Callable[..., Action],
    add_correction: Callable[..., Action],
) -> None:
    imaging = add_imaging("imaging")
    # e.g. collected before the properties were added
    imaging.write_properties(GlobalProperties())
    correction = add_correction(["imaging"])

    with pytest.raises(PostMillingCorrectionError, match="stores no"):
        correction.execute()


@pytest.fixture
def ready(
    add_prepared: Callable[..., Action],
    add_imaging: Callable[..., Action],
    add_correction: Callable[..., Action],
) -> Action:
    """A correction of `imaging` that is ready to run."""
    add_imaging("imaging")
    add_prepared("milling", "milling")
    return add_correction(["imaging"])


def test_ready_correction_reports_no_issues(ready: Action) -> None:
    assert ready.preparation_issues() == []


@pytest.mark.parametrize(
    ("change", "issue"),
    [
        ({"corrected_actions": []}, "No actions to correct are selected."),
        (
            {"corrected_actions": ["imaging", "ghost"]},
            "The corrected action 'ghost' does not exist.",
        ),
        ({"correction_mode": DynamicFocusMode()}, "No milling is linked."),
        (
            {"correction_mode": DynamicFocusMode(), "linked_milling": "ghost"},
            "The linked milling 'ghost' does not exist.",
        ),
        (
            {"correction_mode": DynamicFocusMode(), "linked_milling": "imaging"},
            "The linked action 'imaging' is not a milling.",
        ),
    ],
)
def test_correction_reports_what_it_cannot_correct(
    ready: Action, change: dict[str, object], issue: str
) -> None:
    for name, value in change.items():
        setattr(ready.settings, name, value)

    assert ready.preparation_issues() == [issue]


@pytest.mark.parametrize(
    ("mode", "missing"),
    [
        (ManualMode(wd_correction=WD_CORRECTION), ["working_distance"]),
        (ManualMode(y_correction=Y_CORRECTION), ["beam_shift"]),
        (ManualMode(), []),
    ],
)
def test_correction_requires_targets_to_collect_what_it_corrects(
    add_prepared: Callable[..., Action],
    add_correction: Callable[..., Action],
    mode: ManualMode,
    missing: list[str],
) -> None:
    add_prepared("imaging", "imaging", properties_to_collect=PropertyNames())
    correction = add_correction(["imaging"], mode)

    assert correction.preparation_issues() == [
        f"'imaging' does not collect '{name}', so it cannot be corrected."
        for name in missing
    ]


def test_workflow_drops_propagation_rules_from_or_to_a_correction(
    workflow: Workflow,
    add_imaging: Callable[..., Action],
    add_correction: Callable[..., Action],
) -> None:
    add_imaging("imaging")
    add_imaging("other")
    add_correction(["imaging"])
    wd = PropertyNames(electron_beam=["working_distance"])
    rules = [
        PropagationRule("correction", ["imaging"], wd),
        PropagationRule("imaging", ["correction", "other"], wd),
    ]

    # e.g. loaded from a workflow saved while the correction propagated
    loaded = Workflow(
        workflow.microscope,
        workflow.actions,
        Propagations.from_rules(rules),
        workflow.ctx,
    )

    assert isinstance(loaded.actions[2], PostMillingCorrection)
    assert loaded.propagations.rules == [PropagationRule("imaging", ["other"], wd)]
