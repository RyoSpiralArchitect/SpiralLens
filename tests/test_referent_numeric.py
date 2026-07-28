from __future__ import annotations

import math
from dataclasses import replace

import numpy as np
import pytest

from spirallens.referents import (
    ReferentContractError,
    derive_f2_section,
    derive_f3_section,
    derive_f4_spin_two,
    validate_observation_partition,
)


def _rotation(angle: float) -> np.ndarray:
    return np.array(
        [
            [math.cos(angle), -math.sin(angle)],
            [math.sin(angle), math.cos(angle)],
        ],
        dtype=np.float64,
    )


def _partition(row_identities: np.ndarray):
    rows = np.asarray(row_identities, dtype=np.int64)
    fit = np.column_stack((rows, np.zeros(rows.shape[0], dtype=np.int64)))
    evaluation = np.column_stack((rows, np.ones(rows.shape[0], dtype=np.int64)))
    return validate_observation_partition(fit, evaluation)


def test_f2_derives_amplitude_and_direction_from_the_same_coordinates() -> None:
    frames = np.broadcast_to(np.eye(3, 2), (3, 3, 2)).copy()
    responses = np.array([[3.0, 4.0, 9.0], [0.0, 0.0, 1.0], [1.0, 0.0, -2.0]])

    observation = derive_f2_section(
        frames,
        responses,
        partition=_partition(np.arange(3)),
        input_row_identities=np.arange(3),
        amplitude_floor=0.5,
    )

    assert np.array_equal(
        observation.values,
        np.array([[3.0, 4.0], [0.0, 0.0], [1.0, 0.0]]),
    )
    assert observation.partition_canonical_sha256 is not None
    assert observation.row_identity_sha256 == (
        observation.partition.ordered_row_identity_sha256
    )
    assert np.array_equal(observation.amplitude, np.array([5.0, 0.0, 1.0]))
    assert np.array_equal(
        observation.direction_defined,
        np.array([True, False, True]),
    )
    assert np.array_equal(
        observation.unit_direction,
        np.array([[0.6, 0.8], [0.0, 0.0], [1.0, 0.0]]),
    )
    for array in (
        observation.values,
        observation.amplitude,
        observation.unit_direction,
        observation.direction_defined,
    ):
        assert not array.flags.writeable
        with pytest.raises(ValueError):
            array.setflags(write=True)

    wrong_amplitude = observation.amplitude.copy()
    wrong_amplitude[0] = 6.0
    with pytest.raises(
        ReferentContractError,
        match="amplitude must be the norm",
    ):
        replace(observation, amplitude=wrong_amplitude)

    with pytest.raises(
        ReferentContractError,
        match="values must have 2 dimensions",
    ):
        replace(observation, values=np.array(1.0))


def test_f2_obeys_ambient_and_full_o2_covariance() -> None:
    frames = np.broadcast_to(np.eye(3, 2), (2, 3, 2)).copy()
    responses = np.array([[1.0, 2.0, 3.0], [-2.0, 1.0, 0.5]])
    partition = _partition(np.arange(2))
    original = derive_f2_section(
        frames,
        responses,
        partition=partition,
        input_row_identities=np.arange(2),
    )

    ambient = np.array([[0.0, -1.0, 0.0], [1.0, 0.0, 0.0], [0.0, 0.0, 1.0]])
    ambient_frames = np.einsum("ab,nbi->nai", ambient, frames)
    ambient_responses = responses @ ambient.T
    ambient_observation = derive_f2_section(
        ambient_frames,
        ambient_responses,
        partition=partition,
        input_row_identities=np.arange(2),
    )
    assert np.allclose(ambient_observation.values, original.values)

    for gauge in (_rotation(0.37), np.diag([1.0, -1.0])):
        gauged_frames = np.einsum("ndi,ij->ndj", frames, gauge)
        gauged = derive_f2_section(
            gauged_frames,
            responses,
            partition=partition,
            input_row_identities=np.arange(2),
        )
        expected = np.einsum("ij,nj->ni", gauge.T, original.values)
        assert np.allclose(gauged.values, expected)
        assert np.allclose(gauged.amplitude, original.amplitude)


def test_f3_is_an_explicit_projection_dependent_baseline() -> None:
    plane = np.eye(4, 2)
    responses = np.array([[1.0, -2.0, 8.0, 9.0], [0.0, 3.0, 1.0, 1.0]])

    observation = derive_f3_section(
        plane,
        responses,
        learned_plane=False,
        input_row_identities=np.arange(2),
    )

    assert np.array_equal(
        observation.values,
        np.array([[1.0, -2.0], [0.0, 3.0]]),
    )
    assert np.allclose(
        observation.amplitude,
        np.array([math.sqrt(5.0), 3.0]),
    )
    assert observation.partition_canonical_sha256 is None

    learned = derive_f3_section(
        plane,
        responses,
        learned_plane=True,
        partition=_partition(np.arange(2)),
        input_row_identities=np.arange(2),
    )
    assert learned.partition_canonical_sha256 is not None


def test_f4_uses_one_traceless_tensor_with_doubled_angle_covariance() -> None:
    tensors = np.array(
        [
            [[3.0, 0.0], [0.0, 1.0]],
            [[2.0, 1.0], [1.0, 2.0]],
            [[4.0, 0.0], [0.0, 4.0]],
        ]
    )
    partition = _partition(np.arange(3))
    original = derive_f4_spin_two(
        tensors,
        partition=partition,
        input_row_identities=np.arange(3),
        amplitude_floor=0.1,
    )

    assert np.array_equal(
        original.section.values,
        np.array([[1.0, 0.0], [0.0, 1.0], [0.0, 0.0]]),
    )
    assert np.array_equal(
        original.section.amplitude,
        np.array([1.0, 1.0, 0.0]),
    )
    assert np.array_equal(
        original.section.direction_defined,
        np.array([True, True, False]),
    )

    angle = 0.31
    gauge = _rotation(angle)
    gauged_tensors = np.einsum(
        "ab,nbc,cd->nad",
        gauge.T,
        tensors,
        gauge,
    )
    gauged = derive_f4_spin_two(
        gauged_tensors,
        partition=partition,
        input_row_identities=np.arange(3),
        amplitude_floor=0.1,
    )
    original_complex = (
        original.section.values[:, 0] + 1j * original.section.values[:, 1]
    )
    gauged_complex = gauged.section.values[:, 0] + 1j * gauged.section.values[:, 1]
    assert np.allclose(
        gauged_complex,
        np.exp(-2j * angle) * original_complex,
    )
    assert np.allclose(gauged.section.amplitude, original.section.amplitude)

    reflection = np.diag([1.0, -1.0])
    reflected_tensors = np.einsum(
        "ab,nbc,cd->nad",
        reflection.T,
        tensors,
        reflection,
    )
    reflected = derive_f4_spin_two(
        reflected_tensors,
        partition=partition,
        input_row_identities=np.arange(3),
        amplitude_floor=0.1,
    )
    reflected_complex = (
        reflected.section.values[:, 0] + 1j * reflected.section.values[:, 1]
    )
    assert np.allclose(reflected_complex, np.conjugate(original_complex))


def test_numeric_derivations_fail_closed_on_invalid_inputs() -> None:
    one_row_partition = _partition(np.array([0]))
    with pytest.raises(
        ReferentContractError,
        match="orthonormal columns",
    ):
        derive_f2_section(
            np.ones((1, 3, 2), dtype=np.float64),
            np.ones((1, 3), dtype=np.float64),
            partition=one_row_partition,
            input_row_identities=np.array([0]),
        )

    with pytest.raises(ReferentContractError, match="must be symmetric"):
        derive_f4_spin_two(
            np.array([[[1.0, 2.0], [0.0, 1.0]]]),
            partition=one_row_partition,
            input_row_identities=np.array([0]),
        )

    with pytest.raises(ReferentContractError, match="floating dtype"):
        derive_f3_section(
            np.eye(3, 2, dtype=np.int64),
            np.ones((1, 3), dtype=np.float64),
            learned_plane=False,
            input_row_identities=np.array([0]),
        )

    with pytest.raises(ReferentContractError, match="negative zero"):
        derive_f3_section(
            np.eye(3, 2, dtype=np.float64),
            np.ones((1, 3), dtype=np.float64),
            learned_plane=False,
            input_row_identities=np.array([0]),
            amplitude_floor=-0.0,
        )

    with pytest.raises(
        ReferentContractError,
        match="require a validated ObservationPartition",
    ):
        derive_f2_section(
            np.broadcast_to(np.eye(3, 2), (1, 3, 2)),
            np.ones((1, 3), dtype=np.float64),
            partition=None,  # type: ignore[arg-type]
            input_row_identities=np.array([0]),
        )

    with pytest.raises(
        ReferentContractError,
        match="input row identity differs",
    ):
        derive_f2_section(
            np.broadcast_to(np.eye(3, 2), (2, 3, 2)),
            np.ones((2, 3), dtype=np.float64),
            partition=_partition(np.array([0, 1])),
            input_row_identities=np.array([1, 0]),
        )

    with pytest.raises(
        ReferentContractError,
        match="learned F3 plane requires",
    ):
        derive_f3_section(
            np.eye(3, 2, dtype=np.float64),
            np.ones((1, 3), dtype=np.float64),
            learned_plane=True,
            input_row_identities=np.array([0]),
        )


def test_partition_computes_disjointness_and_same_row_domain() -> None:
    fit = np.array([[0, 0], [0, 2], [1, 0], [1, 2]], dtype=np.int64)
    evaluation = np.array(
        [[0, 1], [0, 3], [1, 1], [1, 3]],
        dtype=np.int64,
    )

    partition = validate_observation_partition(fit, evaluation)

    assert partition.fit_identity_sha256 != (partition.evaluation_identity_sha256)
    assert partition.fit_identities.flags.writeable is False
    assert partition.evaluation_identities.flags.writeable is False
    assert partition.ordered_row_identities.tolist() == [0, 0, 1, 1]
    assert partition.ordered_row_identity_sha256 in partition.to_dict().values()
    assert partition.to_dict()["receipt_version"] == (
        "spirallens.observation-partition-receipt.v0.1"
    )
    assert partition.to_dict()["record_scope"] == "in-memory-fingerprint-only"
    assert partition.to_dict()["persistence_round_trip_supported"] is False
    assert "schema_version" not in partition.to_dict()

    with pytest.raises(
        ReferentContractError,
        match="differs from the computed identity",
    ):
        replace(partition, fit_identity_sha256="0" * 64)

    with pytest.raises(
        ReferentContractError,
        match="ordered_row_identity_sha256 differs",
    ):
        replace(partition, ordered_row_identity_sha256="0" * 64)

    with pytest.raises(ReferentContractError, match="must be disjoint"):
        validate_observation_partition(fit, fit)

    with pytest.raises(ReferentContractError, match="must be unique"):
        validate_observation_partition(
            np.vstack((fit, fit[0])),
            evaluation,
        )

    with pytest.raises(ReferentContractError, match="exact ordered row domain"):
        validate_observation_partition(
            fit,
            np.array([[0, 1], [0, 3]], dtype=np.int64),
        )

    with pytest.raises(ReferentContractError, match="exact ordered row domain"):
        validate_observation_partition(fit, evaluation[::-1])

    with pytest.raises(ReferentContractError, match="exact ordered row domain"):
        validate_observation_partition(fit, evaluation[:-1])


def test_partition_defensively_seals_aliases_and_digest_bound_arrays() -> None:
    partition = _partition(np.array([0, 1], dtype=np.int64))
    writable_owner = np.asarray(partition.fit_identities).copy()
    read_only_view = writable_owner.view()
    read_only_view.setflags(write=False)

    sealed = replace(partition, fit_identities=read_only_view)
    original_rows = sealed.ordered_row_identities.copy()
    original_digest = sealed.ordered_row_identity_sha256
    writable_owner[0, 0] = 999

    assert np.array_equal(sealed.ordered_row_identities, original_rows)
    assert sealed.ordered_row_identity_sha256 == original_digest
    for array in (
        sealed.fit_identities,
        sealed.evaluation_identities,
        sealed.ordered_row_identities,
    ):
        with pytest.raises(ValueError):
            array.setflags(write=True)
