# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF


import pytest

from fibsem_maestro.core.stage_position import StagePosition


def test_stage_position_addition():
    pos1 = StagePosition(x=100.0, y=200.0, z=300.0, rotation=45.0, tilt=30.0)
    pos2 = StagePosition(x=50.0, y=100.0, z=150.0, rotation=10.0, tilt=15.0)
    result = pos1 + pos2
    assert result.x == 150.0
    assert result.y == 300.0
    assert result.z == 450.0
    assert result.rotation == 55.0
    assert result.tilt == 45.0


def test_stage_position_to_xy():
    pos = StagePosition(x=100.0, y=200.0, z=300.0, rotation=45.0, tilt=30.0)

    x, y = pos.to_xy()

    assert x == pos.x
    assert y == pos.y


def test_stage_position_inverted_negates_all_fields():
    position = StagePosition(x=10.0, y=-20.0, z=30.0, rotation=45.0, tilt=-7.0)

    result = position.inverted()

    assert result.x == pytest.approx(-10.0)
    assert result.y == pytest.approx(20.0)
    assert result.z == pytest.approx(-30.0)
    assert result.rotation == pytest.approx(-45.0)
    assert result.tilt == pytest.approx(7.0)


def test_stage_position_inverted_returns_new_instance():
    position = StagePosition(x=10.0, y=-20.0)

    result = position.inverted()

    assert result is not position


def test_stage_position_inverted_does_not_modify_original():
    position = StagePosition(x=10.0, y=-20.0, z=30.0, rotation=45.0, tilt=-7.0)

    position.inverted()

    assert position.x == pytest.approx(10.0)
    assert position.y == pytest.approx(-20.0)
    assert position.z == pytest.approx(30.0)
    assert position.rotation == pytest.approx(45.0)
    assert position.tilt == pytest.approx(-7.0)


def test_stage_position_inverted_twice_is_identity():
    position = StagePosition(x=10.0, y=-20.0, z=30.0, rotation=45.0, tilt=-7.0)

    result = position.inverted().inverted()

    assert result == position


def test_stage_position_inverted_of_default_is_all_zeros():
    result = StagePosition().inverted()

    assert result.x == 0.0
    assert result.y == 0.0
    assert result.z == 0.0
    assert result.rotation == 0.0
    assert result.tilt == 0.0
