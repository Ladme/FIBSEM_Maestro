# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF


import pytest

from fibsem_maestro.core.drift import Drift


def test_drift_stores_x_and_y():
    drift = Drift(x=1.5, y=-2.5)

    assert drift.x == pytest.approx(1.5)
    assert drift.y == pytest.approx(-2.5)


def test_drift_confidence_defaults_to_none():
    drift = Drift(x=1.0, y=2.0)

    assert drift.confidence is None


def test_drift_stores_confidence_when_given():
    drift = Drift(x=1.0, y=2.0, confidence=0.83)

    assert drift.confidence == pytest.approx(0.83)


def test_drift_accepts_positional_x_and_y():
    drift = Drift(1.0, 2.0)

    assert drift.x == pytest.approx(1.0)
    assert drift.y == pytest.approx(2.0)


def test_drift_is_valid_when_both_axes_defined():
    assert Drift(x=1.0, y=2.0).is_valid() is True


def test_drift_is_valid_when_both_axes_are_zero():
    """Zero drift is a successful measurement, not a missing one."""
    assert Drift(x=0.0, y=0.0).is_valid() is True


def test_drift_is_valid_when_one_axis_is_zero():
    assert Drift(x=0.0, y=5.0).is_valid() is True
    assert Drift(x=5.0, y=0.0).is_valid() is True


def test_drift_is_not_valid_when_x_is_none():
    assert Drift(x=None, y=2.0).is_valid() is False


def test_drift_is_not_valid_when_y_is_none():
    assert Drift(x=1.0, y=None).is_valid() is False


def test_drift_is_not_valid_when_both_axes_are_none():
    assert Drift(x=None, y=None).is_valid() is False


def test_drift_is_valid_ignores_confidence():
    assert Drift(x=1.0, y=2.0, confidence=None).is_valid() is True
    assert Drift(x=1.0, y=2.0, confidence=0.0).is_valid() is True
    assert Drift(x=None, y=None, confidence=1.0).is_valid() is False


def test_drift_equality_compares_all_fields():
    assert Drift(x=1.0, y=2.0, confidence=0.5) == Drift(x=1.0, y=2.0, confidence=0.5)
    assert Drift(x=1.0, y=2.0, confidence=0.5) != Drift(x=1.0, y=2.0, confidence=0.9)
    assert Drift(x=1.0, y=2.0) != Drift(x=1.0, y=3.0)


def test_drift_is_not_valid_when_x_is_nan():
    assert Drift(x=float("nan"), y=2.0).is_valid() is False


def test_drift_is_not_valid_when_y_is_nan():
    assert Drift(x=1.0, y=float("nan")).is_valid() is False


def test_drift_is_not_valid_when_both_axes_are_nan():
    assert Drift(x=float("nan"), y=float("nan")).is_valid() is False


def test_drift_is_not_valid_when_axis_is_infinite():
    assert Drift(x=float("inf"), y=2.0).is_valid() is False
    assert Drift(x=1.0, y=float("-inf")).is_valid() is False


def test_drift_is_valid_accepts_very_large_finite_drift():
    assert Drift(x=1e12, y=-1e12).is_valid() is True


def test_drift_is_not_valid_when_one_axis_is_none_and_other_is_nan():
    assert Drift(x=None, y=float("nan")).is_valid() is False
