# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


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
