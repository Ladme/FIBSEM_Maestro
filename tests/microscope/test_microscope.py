# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF



import numpy as np
import pytest

from fibsem_maestro.core.stage_position import StagePosition
from fibsem_maestro.logging.image.in_memory import InMemoryImageLogger
from fibsem_maestro.logging.text.in_memory import InMemoryTextLogger
from fibsem_maestro.microscope.error import MicroscopeError
from fibsem_maestro.microscope.microscope import Microscope
from fibsem_maestro.settings.microscope_settings import MicroscopeSettings


def create_microscope(
    *,
    tilt: float = 0.0,
    rotation: float = 0.0,
    pretilt: float = 0.0,
) -> Microscope:
    microscope = Microscope(
        MicroscopeSettings(
            control="mock",
            ip_address="127.0.0.1",
            beam_shift_tolerance=50.0,
            stage_tolerance=100.0,
            stage_trials=3,
            holder_pretilt=pretilt,
        ),
        txt_log=InMemoryTextLogger(),
        img_log=InMemoryImageLogger(),
    )

    microscope.set_stage_position_with_verification(
        StagePosition(x=0, y=0, z=0, rotation=rotation, tilt=tilt)
    )

    return microscope


def test_beam_shift_to_stage_move_zero_tilt_and_rotation_returns_identity():
    microscope = create_microscope()

    matrix = microscope._beam_shift_to_stage_move()

    np.testing.assert_allclose(matrix, np.eye(2))


def test_beam_shift_to_stage_move_pure_tilt_scales_y_only():
    tilt = 60.0
    microscope = create_microscope(tilt=tilt)

    matrix = microscope._beam_shift_to_stage_move()

    expected = np.array([[1.0, 0.0], [0.0, 1.0 / np.cos(np.radians(tilt))]])

    np.testing.assert_allclose(matrix, expected)


def test_beam_shift_to_stage_move_holder_pretilt_is_added():
    stage_tilt = 20.0
    pretilt = 30.0
    effective = stage_tilt + pretilt

    microscope = create_microscope(
        tilt=stage_tilt,
        pretilt=pretilt,
    )

    matrix = microscope._beam_shift_to_stage_move()

    expected_scale = 1.0 / np.cos(np.radians(effective))
    assert np.isclose(matrix[1, 1], expected_scale)


def test_beam_shift_to_stage_move_rotation_only_returns_identity():
    microscope = create_microscope(rotation=45.0)

    matrix = microscope._beam_shift_to_stage_move()

    np.testing.assert_allclose(matrix, np.eye(2), atol=1e-6)


def test_beam_shift_to_stage_move_tilt_and_rotation_determinant_equals_stretch():
    tilt = 45.0
    rotation = 30.0

    microscope = create_microscope(
        tilt=tilt,
        rotation=rotation,
    )

    matrix = microscope._beam_shift_to_stage_move()

    stretch = 1.0 / np.cos(np.radians(tilt))
    det = np.linalg.det(matrix)

    assert np.isclose(det, stretch)


def test_beam_shift_to_stage_matrix_is_symmetric_positive_definite() -> None:
    microscope = create_microscope(
        tilt=40.0,
        rotation=20.0,
        pretilt=10.0,
    )

    matrix = microscope._beam_shift_to_stage_move()

    np.testing.assert_allclose(matrix, matrix.T)

    eigvals = np.linalg.eigvals(matrix)
    assert np.all(eigvals > 0)


def test_beam_shift_to_stage_matrix_effective_tilt_near_90_raises() -> None:
    microscope = create_microscope(tilt=89.999)

    with pytest.raises(MicroscopeError):
        microscope._beam_shift_to_stage_move()


def test_beam_shift_to_stage_matrix_pretilt_can_trigger_singularity() -> None:
    microscope = create_microscope(
        tilt=30.0,
        pretilt=60.0,
    )

    with pytest.raises(MicroscopeError):
        microscope._beam_shift_to_stage_move()


def test_beam_shift_to_stage_matrix_debug_logging_occurs() -> None:
    microscope = create_microscope()

    microscope._beam_shift_to_stage_move()

    assert len(microscope._txt_log.debugs) > 0  # type: ignore
    assert "conversion matrix" in microscope._txt_log.debugs[-1]  # type: ignore
