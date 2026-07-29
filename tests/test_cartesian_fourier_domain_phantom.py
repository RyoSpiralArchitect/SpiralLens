from __future__ import annotations

import hashlib
import inspect
from dataclasses import fields, replace
from pathlib import Path

import numpy as np
import pytest

import spirallens.synthetic.cartesian_fourier_domain_phantom as cartesian_module
from spirallens.synthetic.cartesian_fourier_domain_phantom import (
    CARTESIAN_FOURIER_FIXED_NULL,
    CARTESIAN_FOURIER_NO_CORE_NULL,
    CARTESIAN_FOURIER_POSITIVE,
    CARTESIAN_FOURIER_PREREQUISITE_FAILURE,
    CARTESIAN_FOURIER_RESOURCE_ESTIMATOR_ID,
    CARTESIAN_FOURIER_STATE_MIXING_ID,
    CartesianExpectedDisposition,
    CartesianFourierCase,
    CartesianFourierDomainGenerator,
    CartesianFourierDomainPhantom,
    CartesianFourierDomainSpec,
    CartesianFourierEstimatorInputs,
    CartesianFourierOracleTruth,
)
from spirallens.synthetic.generators import (
    representation_phantom_family_identity,
    require_distinct_construction_families,
)
from spirallens.synthetic.spectral_moment_phantom import (
    SpectralMomentGenerator,
)


def _observed_coordinates(
    angles: np.ndarray,
    values: np.ndarray,
    harmonic: int,
) -> np.ndarray:
    centered = values - values.mean(axis=1, keepdims=True)
    return (2.0 / angles.shape[0]) * np.column_stack(
        (
            centered @ np.cos(harmonic * angles),
            centered @ np.sin(harmonic * angles),
        )
    )


def _sampled_winding(
    coordinates: np.ndarray,
    loop_rows: np.ndarray,
) -> int:
    complex_values = coordinates[loop_rows, 0] + 1j * coordinates[loop_rows, 1]
    increments = np.angle(np.roll(complex_values, -1) * np.conjugate(complex_values))
    return int(np.rint(increments.sum() / (2.0 * np.pi)))


def _observable_arrays(
    inputs: CartesianFourierEstimatorInputs,
) -> tuple[np.ndarray, ...]:
    names = {
        "row_ids",
        "states",
        "site_coordinates",
        "oriented_faces",
        "fit_sample_ids",
        "fit_angles_rad",
        "fit_values",
        "evaluation_sample_ids",
        "evaluation_angles_rad",
        "evaluation_values",
    }
    return tuple(
        getattr(inputs, item.name) for item in fields(inputs) if item.name in names
    )


def _oracle_arrays(
    truth: CartesianFourierOracleTruth,
) -> tuple[np.ndarray, ...]:
    return tuple(
        value
        for item in fields(truth)
        if isinstance((value := getattr(truth, item.name)), np.ndarray)
    )


@pytest.mark.parametrize("side", [5, 7, 9])
def test_generator_is_deterministic_for_supported_odd_grids(side: int) -> None:
    spec = CartesianFourierDomainSpec(
        grid_side=side,
        ambient_dimension=12,
        noise_scale=0.2,
        density_warp_strength=0.4,
    )

    first = CartesianFourierDomainGenerator().generate(spec)
    second = CartesianFourierDomainGenerator().generate(spec)

    assert first.receipt_bytes == second.receipt_bytes
    assert first.receipt_sha256 == second.receipt_sha256
    assert first.spec.receipt_bytes == second.spec.receipt_bytes
    assert tuple(case.case_id for case in first.cases) == (
        CARTESIAN_FOURIER_POSITIVE,
        CARTESIAN_FOURIER_FIXED_NULL,
        CARTESIAN_FOURIER_NO_CORE_NULL,
        CARTESIAN_FOURIER_PREREQUISITE_FAILURE,
    )
    for left, right in zip(first.cases, second.cases, strict=True):
        assert left.to_dict() == right.to_dict()
        for left_array, right_array in zip(
            _observable_arrays(left.estimator_inputs),
            _observable_arrays(right.estimator_inputs),
            strict=True,
        ):
            assert np.array_equal(left_array, right_array)
        for left_array, right_array in zip(
            _oracle_arrays(left.oracle_truth),
            _oracle_arrays(right.oracle_truth),
            strict=True,
        ):
            assert np.array_equal(left_array, right_array)


def test_family_identity_is_bound_to_this_source() -> None:
    generator = CartesianFourierDomainGenerator()
    module_path = Path(inspect.getfile(CartesianFourierDomainGenerator))
    source_digest = hashlib.sha256(module_path.read_bytes()).hexdigest()

    assert generator.family_identity.source_sha256 == source_digest
    assert (
        generator.family_identity.construction_family_id
        == "cartesian-fourier-quadrature-lattice"
    )


def test_estimator_inputs_are_label_free_and_truth_separated() -> None:
    phantom = CartesianFourierDomainGenerator().generate(CartesianFourierDomainSpec())
    forbidden_attribute_names = {
        "case_id",
        "disposition",
        "geometric_center_mask",
        "core_anchor_mask",
        "supplied_charge",
        "expected_outer_sampled_winding",
        "expected_central_sampled_winding",
        "expected_offcore_sampled_winding",
    }

    assert len({case.estimator_inputs.input_id for case in phantom.cases}) == 4
    for case in phantom.cases:
        inputs = case.estimator_inputs
        assert forbidden_attribute_names.isdisjoint(
            item.name for item in fields(inputs)
        )
        assert case.case_id not in inputs.input_id
        receipt = inputs.to_dict()
        assert receipt["truth_present"] is False
        assert receipt["case_id_present"] is False
        assert receipt["disposition_present"] is False
        assert receipt["center_anchor_present"] is False
        assert receipt["charge_present"] is False
        assert receipt["expected_loop_response_present"] is False
        assert set(inputs.fit_sample_ids).isdisjoint(set(inputs.evaluation_sample_ids))


def test_owner_factory_derives_the_content_id_from_observable_arrays() -> None:
    inputs = (
        CartesianFourierDomainGenerator()
        .generate(CartesianFourierDomainSpec())
        .positive.estimator_inputs
    )
    values = {
        item.name: getattr(inputs, item.name)
        for item in fields(inputs)
        if item.name != "input_id"
    }

    rebuilt = CartesianFourierEstimatorInputs.from_observable_arrays(**values)
    assert rebuilt.input_id == inputs.input_id
    assert rebuilt.fingerprint_sha256 == inputs.fingerprint_sha256

    changed_evaluation = np.array(
        inputs.evaluation_values,
        dtype=np.float64,
        copy=True,
    )
    changed_evaluation[0, 0] += 1e-6
    changed = CartesianFourierEstimatorInputs.from_observable_arrays(
        **{**values, "evaluation_values": changed_evaluation}
    )
    assert changed.input_id != inputs.input_id


@pytest.mark.parametrize("case_name", ["positive", "fixed_null"])
@pytest.mark.parametrize("split_name", ["fit", "evaluation"])
def test_interleaved_quadrature_recovers_oracle_fourier_coordinates(
    case_name: str,
    split_name: str,
) -> None:
    phantom = CartesianFourierDomainGenerator().generate(
        CartesianFourierDomainSpec(noise_scale=0.0)
    )
    case = getattr(phantom, case_name)
    inputs = case.estimator_inputs
    truth = case.oracle_truth
    angles = getattr(inputs, f"{split_name}_angles_rad")
    values = getattr(inputs, f"{split_name}_values")

    assert np.allclose(
        _observed_coordinates(angles, values, 1),
        truth.f2_coordinates,
        rtol=1e-9,
        atol=1e-13,
    )
    assert np.allclose(
        _observed_coordinates(angles, values, 2),
        truth.f4_coordinates,
        rtol=1e-9,
        atol=1e-13,
    )


def test_prerequisite_failure_has_exactly_zero_moments() -> None:
    case = (
        CartesianFourierDomainGenerator()
        .generate(CartesianFourierDomainSpec(noise_scale=0.2))
        .prerequisite_failure
    )
    truth = case.oracle_truth

    assert truth.disposition is CartesianExpectedDisposition.PREREQUISITE_FAILURE
    assert not np.any(truth.f2_coordinates)
    assert not np.any(truth.f4_coordinates)
    assert not np.any(truth.f2_amplitude)
    assert not np.any(truth.f4_amplitude)
    assert not np.any(truth.f2_support)
    assert not np.any(truth.f4_support)
    assert truth.supplied_charge is None
    assert truth.expected_outer_sampled_winding is None


def test_positive_and_null_have_center_only_zero_amplitude() -> None:
    phantom = CartesianFourierDomainGenerator().generate(CartesianFourierDomainSpec())
    positive = phantom.positive.oracle_truth
    fixed_null = phantom.fixed_null.oracle_truth

    for truth in (positive, fixed_null):
        assert np.count_nonzero(truth.geometric_center_mask) == 1
        assert np.count_nonzero(truth.core_anchor_mask) == 1
        assert np.array_equal(~truth.f2_support, truth.core_anchor_mask)
        assert np.array_equal(~truth.f4_support, truth.core_anchor_mask)
        assert np.all(truth.f2_amplitude[truth.f2_support] > 0.0)
        assert np.all(truth.f4_amplitude[truth.f4_support] > 0.0)
    assert np.allclose(
        positive.f2_amplitude,
        fixed_null.f2_amplitude,
        rtol=0.0,
        atol=np.finfo(np.float64).eps,
    )
    assert np.allclose(
        positive.f4_amplitude,
        fixed_null.f4_amplitude,
        rtol=0.0,
        atol=np.finfo(np.float64).eps,
    )


def test_null_without_core_is_a_distinct_required_control() -> None:
    truth = (
        CartesianFourierDomainGenerator()
        .generate(CartesianFourierDomainSpec())
        .no_core_null.oracle_truth
    )

    assert truth.disposition is CartesianExpectedDisposition.NULL_WITHOUT_CORE
    assert np.count_nonzero(truth.geometric_center_mask) == 1
    assert not np.any(truth.core_anchor_mask)
    assert np.all(truth.f2_support)
    assert np.all(truth.f4_support)
    assert np.all(truth.f2_amplitude == 1.0)
    assert truth.expected_outer_sampled_winding == 0
    assert truth.expected_central_sampled_winding == 0
    assert truth.expected_offcore_sampled_winding == 0


def test_oracle_supplies_center_and_offcore_loop_controls() -> None:
    phantom = CartesianFourierDomainGenerator().generate(CartesianFourierDomainSpec())
    positive = phantom.positive.oracle_truth
    fixed_null = phantom.fixed_null.oracle_truth
    center_row = int(np.flatnonzero(positive.geometric_center_mask)[0])

    for loop in (
        positive.outer_loop_vertex_rows,
        positive.central_loop_vertex_rows,
        positive.offcore_loop_vertex_rows,
    ):
        assert center_row not in loop
    assert np.all(positive.f2_support[positive.offcore_loop_vertex_rows])
    assert (
        _sampled_winding(
            positive.f2_coordinates,
            positive.outer_loop_vertex_rows,
        )
        == 1
    )
    assert (
        _sampled_winding(
            positive.f2_coordinates,
            positive.central_loop_vertex_rows,
        )
        == 1
    )
    assert (
        _sampled_winding(
            positive.f2_coordinates,
            positive.offcore_loop_vertex_rows,
        )
        == 0
    )
    for loop in (
        fixed_null.outer_loop_vertex_rows,
        fixed_null.central_loop_vertex_rows,
        fixed_null.offcore_loop_vertex_rows,
    ):
        assert _sampled_winding(fixed_null.f2_coordinates, loop) == 0


def test_cartesian_family_is_distinct_from_existing_constructions() -> None:
    cartesian = CartesianFourierDomainGenerator().family_identity
    representation = representation_phantom_family_identity(source_sha256="a" * 64)
    spectral = SpectralMomentGenerator().family_identity

    require_distinct_construction_families((representation, spectral, cartesian))
    assert (
        len(
            {
                representation.construction_family_id,
                spectral.construction_family_id,
                cartesian.construction_family_id,
            }
        )
        == 3
    )


def test_noise_changes_observations_without_changing_field_or_state() -> None:
    base = CartesianFourierDomainGenerator().generate(
        CartesianFourierDomainSpec(noise_scale=0.0)
    )
    noisy = CartesianFourierDomainGenerator().generate(
        CartesianFourierDomainSpec(noise_scale=0.01)
    )

    for base_case, noisy_case in zip(base.cases, noisy.cases, strict=True):
        assert np.array_equal(
            base_case.estimator_inputs.states,
            noisy_case.estimator_inputs.states,
        )
        if (
            base_case.oracle_truth.disposition
            is CartesianExpectedDisposition.PREREQUISITE_FAILURE
        ):
            assert np.array_equal(
                base_case.estimator_inputs.fit_values,
                noisy_case.estimator_inputs.fit_values,
            )
            assert np.array_equal(
                base_case.estimator_inputs.evaluation_values,
                noisy_case.estimator_inputs.evaluation_values,
            )
        else:
            assert not np.array_equal(
                base_case.estimator_inputs.fit_values,
                noisy_case.estimator_inputs.fit_values,
            )
            assert not np.array_equal(
                base_case.estimator_inputs.evaluation_values,
                noisy_case.estimator_inputs.evaluation_values,
            )
            observed = _observed_coordinates(
                noisy_case.estimator_inputs.evaluation_angles_rad,
                noisy_case.estimator_inputs.evaluation_values,
                1,
            )
            assert not np.allclose(
                observed,
                noisy_case.oracle_truth.f2_coordinates,
                rtol=0.0,
                atol=1e-6,
            )
        assert np.array_equal(
            base_case.oracle_truth.f2_coordinates,
            noisy_case.oracle_truth.f2_coordinates,
        )
        assert np.array_equal(
            base_case.oracle_truth.f4_coordinates,
            noisy_case.oracle_truth.f4_coordinates,
        )


def test_density_warp_changes_state_density_but_not_field_truth() -> None:
    base = CartesianFourierDomainGenerator().generate(
        CartesianFourierDomainSpec(density_warp_strength=0.0)
    )
    warped = CartesianFourierDomainGenerator().generate(
        CartesianFourierDomainSpec(density_warp_strength=0.7)
    )

    for base_case, warped_case in zip(base.cases, warped.cases, strict=True):
        assert not np.array_equal(
            base_case.estimator_inputs.states,
            warped_case.estimator_inputs.states,
        )
        assert np.array_equal(
            base_case.estimator_inputs.site_coordinates,
            warped_case.estimator_inputs.site_coordinates,
        )
        assert np.array_equal(
            base_case.estimator_inputs.fit_values,
            warped_case.estimator_inputs.fit_values,
        )
        assert np.array_equal(
            base_case.oracle_truth.f2_coordinates,
            warped_case.oracle_truth.f2_coordinates,
        )
        assert np.array_equal(
            base_case.oracle_truth.f4_coordinates,
            warped_case.oracle_truth.f4_coordinates,
        )


def test_high_dimensional_states_and_counterclockwise_faces() -> None:
    spec = CartesianFourierDomainSpec(
        grid_side=7,
        ambient_dimension=16,
    )
    inputs = CartesianFourierDomainGenerator().generate(spec).positive.estimator_inputs

    assert inputs.states.shape == (spec.row_count, spec.ambient_dimension)
    assert np.linalg.matrix_rank(inputs.states) >= 4
    assert inputs.oriented_faces.shape == (spec.face_count, 3)
    first = inputs.site_coordinates[inputs.oriented_faces[:, 0]]
    second = inputs.site_coordinates[inputs.oriented_faces[:, 1]]
    third = inputs.site_coordinates[inputs.oriented_faces[:, 2]]
    signed_twice_area = (second[:, 0] - first[:, 0]) * (third[:, 1] - first[:, 1]) - (
        second[:, 1] - first[:, 1]
    ) * (third[:, 0] - first[:, 0])
    assert np.all(signed_twice_area > 0.0)


def test_all_arrays_are_c_contiguous_bytes_backed_and_immutable() -> None:
    phantom = CartesianFourierDomainGenerator().generate(CartesianFourierDomainSpec())

    for case in phantom.cases:
        for array in (
            *_observable_arrays(case.estimator_inputs),
            *_oracle_arrays(case.oracle_truth),
        ):
            assert array.flags.c_contiguous
            assert not array.flags.writeable
            assert isinstance(array.base, (bytes, np.ndarray))
            with pytest.raises(ValueError):
                array.setflags(write=True)


def test_input_tampering_and_layout_errors_fail_closed() -> None:
    inputs = (
        CartesianFourierDomainGenerator()
        .generate(CartesianFourierDomainSpec())
        .positive.estimator_inputs
    )

    tampered_values = np.array(inputs.fit_values, copy=True)
    tampered_values[0, 0] += 0.1
    with pytest.raises(ValueError, match="input_id"):
        replace(inputs, fit_values=tampered_values)
    with pytest.raises(ValueError, match="states"):
        replace(inputs, states=inputs.states[:, :7])
    bad_faces = np.array(inputs.oriented_faces, copy=True)
    bad_faces[0, 2] = inputs.row_ids.shape[0]
    with pytest.raises(ValueError, match="out-of-range"):
        replace(inputs, oriented_faces=bad_faces)
    with pytest.raises(TypeError, match="integer"):
        replace(
            inputs,
            fit_sample_ids=inputs.fit_sample_ids.astype(np.float64),
        )


def test_truth_and_case_relation_tampering_fail_closed() -> None:
    phantom = CartesianFourierDomainGenerator().generate(CartesianFourierDomainSpec())
    positive = phantom.positive
    truth = positive.oracle_truth

    bad_amplitude = np.array(truth.f2_amplitude, copy=True)
    bad_amplitude[0] += 0.1
    with pytest.raises(ValueError, match="derive"):
        replace(truth, f2_amplitude=bad_amplitude)
    with pytest.raises(ValueError, match="expected sampled responses"):
        replace(truth, expected_outer_sampled_winding=0)
    with pytest.raises(ValueError, match="disposition"):
        CartesianFourierCase(
            case_id=CARTESIAN_FOURIER_POSITIVE,
            estimator_inputs=positive.estimator_inputs,
            oracle_truth=phantom.fixed_null.oracle_truth,
            observation_noise_scale=0.0,
        )
    with pytest.raises(ValueError, match="noise bound"):
        CartesianFourierCase(
            case_id=CARTESIAN_FOURIER_POSITIVE,
            estimator_inputs=phantom.fixed_null.estimator_inputs,
            oracle_truth=positive.oracle_truth,
            observation_noise_scale=0.0,
        )


def test_phantom_rejects_noncanonical_cases_for_spec() -> None:
    generator = CartesianFourierDomainGenerator()
    original = generator.generate(CartesianFourierDomainSpec(seed=3))

    with pytest.raises(ValueError, match="canonical spec"):
        CartesianFourierDomainPhantom(
            spec=CartesianFourierDomainSpec(seed=4),
            family_identity=original.family_identity,
            cases=original.cases,
        )


@pytest.mark.parametrize(
    ("kwargs", "exception"),
    [
        ({"seed": True}, TypeError),
        ({"seed": 2**63}, ValueError),
        ({"grid_side": 4}, ValueError),
        ({"grid_side": 6}, ValueError),
        ({"ambient_dimension": 7}, ValueError),
        ({"samples_per_split": 6}, ValueError),
        ({"samples_per_split": 10}, ValueError),
        ({"baseline": 0.0}, ValueError),
        ({"second_harmonic_scale": -0.1}, ValueError),
        ({"noise_scale": -0.0}, ValueError),
        ({"density_warp_strength": 0.9}, ValueError),
        ({"grid_side": 129}, ValueError),
    ],
)
def test_spec_rejects_invalid_and_resource_unbounded_values(
    kwargs: dict[str, object],
    exception: type[Exception],
) -> None:
    with pytest.raises(exception):
        CartesianFourierDomainSpec(**kwargs)


def test_linear_signed_permutation_replaces_the_dense_qr_oom_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def reject_dense_qr(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("Cartesian state mixing must not call dense QR")

    monkeypatch.setattr(np.linalg, "qr", reject_dense_qr)
    spec = CartesianFourierDomainSpec(ambient_dimension=64)
    phantom = CartesianFourierDomainGenerator().generate(spec)
    receipt = spec.to_dict()
    first_permutation, first_signs = cartesian_module._deterministic_signed_permutation(
        spec.ambient_dimension,
        seed=spec.seed ^ 0x43A71E,
    )
    second_permutation, second_signs = (
        cartesian_module._deterministic_signed_permutation(
            spec.ambient_dimension,
            seed=spec.seed ^ 0x43A71E,
        )
    )

    assert phantom.positive.estimator_inputs.states.shape == (
        spec.row_count,
        spec.ambient_dimension,
    )
    assert np.array_equal(first_permutation, second_permutation)
    assert np.array_equal(first_signs, second_signs)
    assert np.array_equal(
        np.sort(first_permutation),
        np.arange(spec.ambient_dimension, dtype="<i8"),
    )
    assert np.all(np.abs(first_signs) == 1.0)
    assert receipt["state_mixing_id"] == CARTESIAN_FOURIER_STATE_MIXING_ID
    assert receipt["state_mixing_dense_square_allocation"] is False
    assert receipt["state_mixing_peak_order"] == "rows-times-ambient-dimension"
    assert receipt["resource_estimator_id"] == CARTESIAN_FOURIER_RESOURCE_ESTIMATOR_ID


def test_hundred_thousand_dimensions_fail_the_resource_guard_before_generation() -> (
    None
):
    with pytest.raises(ValueError, match="fixed 256 MiB cap"):
        CartesianFourierDomainSpec(ambient_dimension=100_000)


def test_receipts_keep_level_zero_and_nonclaim_boundaries_explicit() -> None:
    phantom = CartesianFourierDomainGenerator().generate(CartesianFourierDomainSpec())
    receipt = phantom.to_dict()

    assert receipt["record_scope"] == "in-memory-fingerprint-only"
    assert receipt["persistence_round_trip_supported"] is False
    assert receipt["claim_ceiling"] == "level_0"
    assert receipt["graph_constructed"] is False
    assert receipt["core_localized"] is False
    assert receipt["loop_constructed"] is False
    assert receipt["sampled_winding_observed"] is False
    assert receipt["integer_output_authorized"] is False
    assert receipt["qualification_gate_evaluated"] is False
    assert receipt["d0_d8_advanced"] is False
    assert receipt["subject_access_authorized"] is False
