from __future__ import annotations

import numpy as np
import pytest

from spirallens.factors import (
    apply_rope,
    attention_routing_jvp,
    attention_value_jvp,
    derotate_rope,
    layernorm,
    layernorm_jvp,
    rope_angles,
)
from spirallens.gauge import procrustes_connection, track_subspaces
from spirallens.interventions import cyclic_mode_rotate, patch_subspace
from spirallens.jacobians import finite_difference_jvp, token_block_jacobian
from spirallens.nulls import (
    account_routing,
    baseline_corrected_operator,
    check_orientation_reversal,
    conjugate_operator,
    random_orthogonal,
    spectrum_invariance_error,
)


def test_finite_difference_jvp_and_token_block_are_actual_operators() -> None:
    matrix = np.array([[2.0, -1.0], [0.5, 3.0]])
    point = np.array([0.2, -0.4])
    tangent = np.array([0.7, 0.1])
    image = finite_difference_jvp(lambda x: matrix @ x, point, tangent)
    np.testing.assert_allclose(image, matrix @ tangent, atol=1e-9)

    sequence_point = np.zeros((2, 2))

    def coupled(sequence: np.ndarray) -> np.ndarray:
        return np.stack(
            (sequence[0] + 2.0 * sequence[1], 3.0 * sequence[0] - sequence[1])
        )

    block = token_block_jacobian(
        coupled,
        sequence_point,
        source_token=1,
        target_token=0,
    )
    np.testing.assert_allclose(block, 2.0 * np.eye(2), atol=1e-9)


def test_layernorm_analytic_jvp_matches_finite_difference() -> None:
    value = np.array([0.2, -0.4, 1.1, 0.3])
    tangent = np.array([0.5, 0.1, -0.3, 0.2])
    gain = np.array([1.0, 0.7, 1.4, 0.9])
    analytic = layernorm_jvp(value, tangent, gain=gain)
    numerical = finite_difference_jvp(
        lambda x: layernorm(x, gain=gain),
        value,
        tangent,
    )
    np.testing.assert_allclose(analytic, numerical, rtol=1e-7, atol=1e-8)


def test_rope_round_trip_and_attention_path_decomposition() -> None:
    values = np.array([[1.0, 2.0, 3.0, 4.0], [-1.0, 0.5, 0.2, 2.0]])
    angles = rope_angles(np.array([3.0, 4.0]), rotary_dimension=4)
    np.testing.assert_allclose(
        derotate_rope(apply_rope(values, angles), angles),
        values,
        atol=1e-12,
    )
    cosine = np.cos(angles)
    sine = np.sin(angles)
    hf_gpt_neox_oracle = np.concatenate(
        (
            values[..., :2] * cosine - values[..., 2:4] * sine,
            values[..., :2] * sine + values[..., 2:4] * cosine,
        ),
        axis=-1,
    )
    np.testing.assert_allclose(apply_rope(values, angles), hf_gpt_neox_oracle)
    assert not np.allclose(
        apply_rope(values, angles, layout="interleaved"),
        hf_gpt_neox_oracle,
    )

    scores = np.array([[0.2, -0.1], [0.4, 0.3]])
    score_tangent = np.array([[0.1, 0.3], [-0.2, 0.5]])
    value_tangent = np.array([[0.2, 0.1], [-0.4, 0.7]])
    base_values = np.array([[1.0, 0.5], [-0.2, 0.3]])

    def softmax(rows: np.ndarray) -> np.ndarray:
        shifted = rows - rows.max(axis=-1, keepdims=True)
        weights = np.exp(shifted)
        return weights / weights.sum(axis=-1, keepdims=True)

    probabilities = softmax(scores)
    value_path = attention_value_jvp(probabilities, value_tangent)
    routing_path = attention_routing_jvp(
        probabilities,
        score_tangent,
        base_values,
    )

    def joint(parameter: np.ndarray) -> np.ndarray:
        scale = float(parameter[0])
        return softmax(scores + scale * score_tangent) @ (
            base_values + scale * value_tangent
        )

    full = finite_difference_jvp(joint, np.array([0.0]), np.array([1.0]))
    np.testing.assert_allclose(full, value_path + routing_path, rtol=1e-7, atol=1e-8)
    accounting = account_routing(full, value_path)
    assert accounting.routing_residual_norm == pytest.approx(np.linalg.norm(routing_path))


def test_gauge_alignment_removes_basis_flip_but_not_subspace_drift() -> None:
    frame = np.eye(4)[:, :2]
    gauge_rotation = np.array([[0.0, -1.0], [1.0, 0.0]])
    changed_gauge = frame @ gauge_rotation
    connection = procrustes_connection(changed_gauge, frame)
    np.testing.assert_allclose(changed_gauge @ connection.rotation, frame, atol=1e-12)

    tracked = track_subspaces((frame, changed_gauge))
    np.testing.assert_allclose(tracked.frames[0], tracked.frames[1], atol=1e-12)
    np.testing.assert_allclose(tracked.principal_angles[0], np.zeros(2), atol=1e-12)


def test_null_controls_and_interventions_preserve_declared_invariants() -> None:
    operator = np.array([[0.8, -0.6], [0.6, 0.8]])
    basis = random_orthogonal(2, seed=7)
    changed = conjugate_operator(operator, basis)
    assert spectrum_invariance_error(operator, changed) < 1e-12
    np.testing.assert_allclose(
        baseline_corrected_operator(np.eye(2) @ operator, np.eye(2)),
        operator,
    )
    assert check_orientation_reversal(0.7, -0.7).passed

    frame = np.eye(3)[:, :2]
    value = np.array([2.0, 1.0, 4.0])
    audit = cyclic_mode_rotate(value, frame, np.pi / 2.0)
    np.testing.assert_allclose(audit.value, np.array([-1.0, 2.0, 4.0]), atol=1e-12)
    assert audit.input_norm == pytest.approx(audit.output_norm)
    assert audit.mode_input_norm == pytest.approx(audit.mode_output_norm)

    donor = np.array([9.0, 8.0, 7.0])
    patched = patch_subspace(value, donor, frame[:, :1])
    np.testing.assert_allclose(patched, np.array([9.0, 1.0, 4.0]))
