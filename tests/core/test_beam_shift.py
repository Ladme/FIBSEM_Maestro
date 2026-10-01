# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF


import pytest

from fibsem_maestro.core.beam_shift import BeamShift


def test_beam_shift_to_tuple():
    shift = BeamShift(x=100.0, y=200.0)
    assert shift.to_tuple() == (100.0, 200.0)


def test_beam_shift_addition():
    shift1 = BeamShift(x=100.0, y=200.0)
    shift2 = BeamShift(x=50.0, y=100.0)
    result = shift1 + shift2
    assert result.x == 150.0
    assert result.y == 300.0


def test_beam_shift_inverted_negates_both_axes():
    shift = BeamShift(x=10.0, y=-25.0)

    result = shift.inverted()

    assert result.x == pytest.approx(-10.0)
    assert result.y == pytest.approx(25.0)


def test_beam_shift_inverted_does_not_modify_original():
    shift = BeamShift(x=10.0, y=-25.0)

    shift.inverted()

    assert shift.x == pytest.approx(10.0)
    assert shift.y == pytest.approx(-25.0)


def test_beam_shift_inverted_zero_stays_zero():
    shift = BeamShift(x=0.0, y=0.0)

    result = shift.inverted()

    assert result.x == 0.0
    assert result.y == 0.0
