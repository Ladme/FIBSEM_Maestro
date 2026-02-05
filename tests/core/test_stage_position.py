# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


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
