# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF


import pytest
from pydantic import BaseModel, Field, ValidationError

from fibsem_maestro.core.frequency import Every, Frequency, Never


class _Host(BaseModel):
    """Stand-in for a settings class holding a frequency."""

    execution_frequency: Frequency = Field(default_factory=Every)


def _round_trip(host: _Host) -> _Host:
    """Save without None values, as the YAML writer does, and load back."""
    return _Host.model_validate(host.model_dump(exclude_none=True))


def test_default_runs_every_slice() -> None:
    assert _Host().execution_frequency == Every(n=1)


def test_never_survives_a_round_trip() -> None:
    host = _Host(execution_frequency=Never())

    assert isinstance(_round_trip(host).execution_frequency, Never)


def test_every_survives_a_round_trip() -> None:
    host = _Host(execution_frequency=Every(n=3))

    assert _round_trip(host).execution_frequency == Every(n=3)


def test_missing_frequency_loads_as_default() -> None:
    assert _Host.model_validate({}).execution_frequency == Every(n=1)


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        ({"type": "never"}, Never()),
        ({"type": "every", "n": 4}, Every(n=4)),
        ({"type": "every"}, Every(n=1)),
    ],
)
def test_discriminator_selects_the_variant(
    data: dict[str, object], expected: object
) -> None:
    assert (
        _Host.model_validate({"execution_frequency": data}).execution_frequency
        == expected
    )


@pytest.mark.parametrize("data", [{"type": "sometimes"}, {"n": 3}, 3, None])
def test_invalid_frequency_is_rejected(data: object) -> None:
    with pytest.raises(ValidationError):
        _Host.model_validate({"execution_frequency": data})


@pytest.mark.parametrize("n", [0, -1])
def test_non_positive_interval_is_rejected(n: int) -> None:
    with pytest.raises(ValidationError):
        Every(n=n)


@pytest.mark.parametrize(
    ("n", "matching"),
    [
        (1, [1, 2, 3, 4, 5, 6, 7]),
        (2, [1, 3, 5, 7]),
        (3, [1, 4, 7]),
        (10, [1]),
    ],
)
def test_every_matches_the_interval_from_slice_one(n: int, matching: list[int]) -> None:
    frequency = Every(n=n)

    assert [s for s in range(1, 8) if frequency.matches(s)] == matching


def test_never_matches_no_slice() -> None:
    assert not any(Never().matches(s) for s in range(1, 20))


@pytest.mark.parametrize(
    ("frequency", "expected"),
    [(Every(), True), (Every(n=2), False), (Never(), False)],
)
def test_runs_every_slice(frequency: Frequency, expected: bool) -> None:
    assert frequency.runs_every_slice is expected


@pytest.mark.parametrize(
    ("frequency", "expected"),
    [(Every(), "every slice"), (Every(n=3), "every 3 slices"), (Never(), "never")],
)
def test_str_describes_the_schedule(frequency: Frequency, expected: str) -> None:
    assert str(frequency) == expected
