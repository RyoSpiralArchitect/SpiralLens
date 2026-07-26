from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest

from spirallens.synthetic.representation_phantom import (
    REASON_ZERO_AMPLITUDE,
    RepresentationPhantom,
    RepresentationPhantomSpec,
)


def test_generation_is_byte_deterministic_and_frozen() -> None:
    spec = RepresentationPhantomSpec()
    first = RepresentationPhantom.generate(spec)
    second = RepresentationPhantom.generate(spec)

    assert first.spec.canonical_bytes == second.spec.canonical_bytes
    assert first.canonical_bytes == second.canonical_bytes
    assert first.canonical_sha256 == second.canonical_sha256
    for first_case, second_case in zip(
        first.cases, second.cases, strict=True
    ):
        assert first_case.canonical_bytes == second_case.canonical_bytes
        for name in first_case._ARRAY_DTYPES:
            first_array = getattr(first_case, name)
            second_array = getattr(second_case, name)
            assert np.array_equal(first_array, second_array)
            assert first_array.flags.c_contiguous
            assert not first_array.flags.writeable
    first.validate()


def test_paired_cases_share_substrate_graph_and_fit_probes() -> None:
    phantom = RepresentationPhantom.generate()
    positive = phantom.angular_section_positive
    null = phantom.fixed_direction_null

    for name in (
        "states",
        "vertex_identities",
        "valid_mask",
        "center_support_mask",
        "neighbor_indices",
        "edges",
        "graph_weights",
        "components",
        "degree",
        "two_core_mask",
        "cycle_support",
        "local_covariance",
        "f0_values",
        "f1_frames",
    ):
        assert np.array_equal(getattr(positive, name), getattr(null, name))
    assert np.array_equal(
        positive.accounted_response[
            :, phantom.spec.even_probe_indices, :
        ],
        null.accounted_response[:, phantom.spec.even_probe_indices, :],
    )
    assert not np.array_equal(
        positive.observation_identities,
        null.observation_identities,
    )
    assert positive.cycle_support.shape[0] > 0


def test_center_has_declared_amplitude_depression() -> None:
    phantom = RepresentationPhantom.generate()

    for case in phantom.cases:
        center_index = int(np.flatnonzero(case.center_support_mask)[0])
        noncenter = ~case.center_support_mask
        assert case.f2_amplitude[center_index] <= (
            128.0 * np.finfo(float).eps * phantom.spec.probe_scale
        )
        assert case.f2_amplitude[center_index] < np.min(
            case.f2_amplitude[noncenter]
        )
        assert not case.f2_support[center_index]
        assert (
            case.f2_reason_codes[center_index] == REASON_ZERO_AMPLITUDE
        )


def test_f2_amplitude_is_norm_of_odd_mean_frame_coordinates() -> None:
    phantom = RepresentationPhantom.generate()

    for case in phantom.cases:
        odd_mean = case.accounted_response[
            :, phantom.spec.odd_probe_indices, :
        ].mean(axis=1)
        expected_coordinates = np.einsum(
            "ndi,nd->ni", case.f1_frames, odd_mean, optimize=False
        )
        assert np.array_equal(case.f2_coordinates, expected_coordinates)
        assert np.array_equal(
            case.f2_amplitude,
            np.linalg.norm(expected_coordinates, axis=1),
        )


def test_f1_projector_recovers_seeded_rank_two_plane() -> None:
    phantom = RepresentationPhantom.generate()
    expected = (
        phantom.ambient_basis[:, :2]
        @ phantom.ambient_basis[:, :2].T
    )

    for case in phantom.cases:
        assert np.all(case.f1_support)
        for frame in case.f1_frames:
            recovered = frame @ frame.T
            assert np.allclose(
                recovered,
                expected,
                rtol=5e-12,
                atol=5e-12,
            )
        assert np.max(case.f1_eigenvalues[:, 2]) <= 5e-13


def test_validate_rejects_value_tamper_and_row_permutation() -> None:
    case = RepresentationPhantom.generate().angular_section_positive

    tampered_amplitude = case.f2_amplitude.copy()
    tampered_amplitude[1] += 0.25
    with pytest.raises(ValueError, match="f2_amplitude"):
        replace(case, f2_amplitude=tampered_amplitude).validate()

    permutation = np.arange(case.spec.row_count)
    permutation[[0, 1]] = permutation[[1, 0]]
    permuted = replace(
        case,
        states=case.states[permutation],
        vertex_identities=case.vertex_identities[permutation],
        observation_identities=case.observation_identities[permutation],
        valid_mask=case.valid_mask[permutation],
        center_support_mask=case.center_support_mask[permutation],
        accounted_response=case.accounted_response[permutation],
    )
    with pytest.raises(ValueError, match="canonical row order"):
        permuted.validate()


@pytest.mark.parametrize(
    ("field", "value", "message"),
    (
        ("grid_side", 6, "odd"),
        ("ambient_dimension", 7, "at least 8"),
        ("probe_count", 6, "divisible by 4"),
        ("neighbor_count", 3, "at least 4"),
        ("radial_scale", 0.0, "positive"),
        ("probe_scale", 0.0, "positive"),
        ("nuisance_scale", -0.1, "non-negative"),
    ),
)
def test_spec_rejects_out_of_contract_values(
    field: str,
    value: object,
    message: str,
) -> None:
    with pytest.raises((TypeError, ValueError), match=message):
        RepresentationPhantomSpec(**{field: value})
