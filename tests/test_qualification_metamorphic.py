from __future__ import annotations

import math

import numpy as np
import pytest

from spirallens.qualification.common import (
    QualificationContractError,
    QualificationState,
)
from spirallens.qualification.metamorphic import (
    ambient_signed_permutation_check,
    local_frame_gauge_check,
    loop_reversal_check,
    nonorientable_control_check,
    reference_orientation_check,
    sampled_phase_total,
    spin_two_double_angle_check,
)


def _rotation(angle: float) -> np.ndarray:
    return np.asarray(
        (
            (math.cos(angle), -math.sin(angle)),
            (math.sin(angle), math.cos(angle)),
        ),
        dtype=np.float64,
    )


def _circle(samples: int = 16) -> tuple[np.ndarray, np.ndarray]:
    phase = np.linspace(0.0, 2.0 * math.pi, samples, endpoint=False)
    values = np.column_stack((np.cos(phase), np.sin(phase))).astype(np.float64)
    return values, np.arange(samples, dtype=np.int64)


def test_local_frame_gauge_cancels_vertexwise_o2() -> None:
    rng = np.random.default_rng(7)
    frames = np.empty((5, 4, 2), dtype=np.float64)
    for row in range(5):
        q, _ = np.linalg.qr(rng.normal(size=(4, 2)))
        frames[row] = q
    coordinates = rng.normal(size=(5, 2)).astype(np.float64)
    gauges = np.stack(
        (
            _rotation(0.2),
            np.diag((1.0, -1.0)),
            _rotation(-0.7),
            np.asarray(((0.0, 1.0), (1.0, 0.0)), dtype=np.float64),
            _rotation(1.1),
        )
    )
    check = local_frame_gauge_check(
        local_frames=frames,
        local_coordinates=coordinates,
        gauges=gauges,
    )
    assert check.state is QualificationState.PASS
    assert check.nonidentity_verified
    assert check.to_dict()["integer_output_present"] is False


def test_local_frame_gauge_rejects_nonorthogonal_transform() -> None:
    frames = np.broadcast_to(np.eye(2), (2, 2, 2)).copy()
    coordinates = np.ones((2, 2), dtype=np.float64)
    gauges = np.broadcast_to(np.eye(2), (2, 2, 2)).copy()
    gauges[1, 0, 0] = 2.0
    with pytest.raises(QualificationContractError, match="orthogonal"):
        local_frame_gauge_check(
            local_frames=frames,
            local_coordinates=coordinates,
            gauges=gauges,
        )


def test_reference_rotations_preserve_and_reflections_flip_phase_total() -> None:
    values, rows = _circle()
    rotation = reference_orientation_check(
        section_values=values,
        loop_rows=rows,
        reference_transform=_rotation(0.31),
    )
    reflection = reference_orientation_check(
        section_values=values,
        loop_rows=rows,
        reference_transform=np.diag((1.0, -1.0)).astype(np.float64),
    )
    assert rotation.state is QualificationState.PASS
    assert reflection.state is QualificationState.PASS
    assert sampled_phase_total(values, rows) == pytest.approx(1.0)


def test_loop_reversal_is_signed_and_involutive() -> None:
    values, rows = _circle(12)
    check = loop_reversal_check(section_values=values, loop_rows=rows)
    assert check.state is QualificationState.PASS
    assert check.inverse_verified
    assert sampled_phase_total(values, rows[::-1]) == pytest.approx(-1.0)


def test_zero_amplitude_makes_sampled_phase_undefined() -> None:
    values, rows = _circle()
    values[3] = 0.0
    with pytest.raises(QualificationContractError, match="undefined"):
        sampled_phase_total(values, rows)


def test_ambient_signed_permutation_preserves_distances_and_projectors() -> None:
    rng = np.random.default_rng(11)
    states = rng.normal(size=(6, 4)).astype(np.float64)
    frames = np.empty((6, 4, 2), dtype=np.float64)
    for row in range(6):
        q, _ = np.linalg.qr(rng.normal(size=(4, 2)))
        frames[row] = q
    transform = np.asarray(
        (
            (0.0, 0.0, -1.0, 0.0),
            (1.0, 0.0, 0.0, 0.0),
            (0.0, 0.0, 0.0, 1.0),
            (0.0, -1.0, 0.0, 0.0),
        ),
        dtype=np.float64,
    )
    check = ambient_signed_permutation_check(
        states=states,
        local_frames=frames,
        signed_permutation=transform,
    )
    assert check.state is QualificationState.PASS


def test_spin_two_uses_double_angle_not_vector_angle() -> None:
    values = np.asarray(((1.0, 0.0), (0.3, -0.4)), dtype=np.float64)
    check = spin_two_double_angle_check(
        spin_two_values=values,
        physical_angle=math.pi / 4.0,
    )
    assert check.state is QualificationState.PASS
    assert check.observed_error < 1e-12


def test_nonorientable_cycle_is_insufficient_not_forced_so2() -> None:
    check = nonorientable_control_check(
        edge_determinants=np.asarray((1.0, -1.0, 1.0), dtype=np.float64),
        cycle_edge_rows=np.asarray((0, 1, 2), dtype=np.int64),
    )
    assert check.state is QualificationState.INSUFFICIENT
    assert check.reason_codes == ("orientation-reversing-cycle",)

    orientable_control = nonorientable_control_check(
        edge_determinants=np.ones(3, dtype=np.float64),
        cycle_edge_rows=np.asarray((0, 1, 2), dtype=np.int64),
    )
    assert orientable_control.state is QualificationState.FAIL
