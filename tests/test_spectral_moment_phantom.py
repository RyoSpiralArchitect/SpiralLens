from __future__ import annotations

import ast
import hashlib
import inspect
import re
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from spirallens.synthetic import (
    SPECTRAL_MOMENT_FIXED_NULL,
    SPECTRAL_MOMENT_POSITIVE,
    SPECTRAL_MOMENT_PREREQUISITE_FAILURE,
    ExpectedControlDisposition,
    SpectralMomentCase,
    SpectralMomentGenerator,
    SpectralMomentPhantomSpec,
)
from spirallens.synthetic import spectral_moment_phantom as module


def _moments(
    angles: np.ndarray,
    values: np.ndarray,
    *,
    baseline: float,
) -> tuple[np.ndarray, np.ndarray]:
    centered = values - baseline
    scale = 2.0 / angles.shape[0]
    first = scale * np.column_stack(
        (
            centered @ np.cos(angles),
            centered @ np.sin(angles),
        )
    )
    second = scale * np.column_stack(
        (
            centered @ np.cos(2.0 * angles),
            centered @ np.sin(2.0 * angles),
        )
    )
    return first, second


def test_spectral_generator_is_deterministic_and_source_bound() -> None:
    generator = SpectralMomentGenerator()
    spec = SpectralMomentPhantomSpec()
    first = generator.generate(spec)
    second = generator.generate(spec)

    assert first.receipt_bytes == second.receipt_bytes
    assert first.receipt_sha256 == second.receipt_sha256
    assert (
        generator.family_identity.source_sha256
        == hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest()
    )
    assert "representation_phantom" not in Path(module.__file__).read_text(
        encoding="utf-8"
    )


def test_seed_changes_values_but_not_construction_family() -> None:
    generator = SpectralMomentGenerator()
    first = generator.generate(SpectralMomentPhantomSpec(seed=1))
    second = generator.generate(SpectralMomentPhantomSpec(seed=2))

    assert first.family_identity == second.family_identity
    assert first.receipt_sha256 != second.receipt_sha256


def test_cases_and_phantom_are_bound_to_observations_and_spec() -> None:
    generator = SpectralMomentGenerator()
    first = generator.generate(SpectralMomentPhantomSpec(seed=1))
    second = generator.generate(SpectralMomentPhantomSpec(seed=2))

    with pytest.raises(ValueError, match="observations do not recover"):
        replace(
            first.cases[0],
            oracle_truth=second.cases[0].oracle_truth,
        )

    with pytest.raises(ValueError, match="canonical controls"):
        replace(first, cases=second.cases)

    with pytest.raises(ValueError, match="canonical controls"):
        replace(first, spec=second.spec)


def test_fit_and_evaluation_quadrature_are_disjoint() -> None:
    phantom = SpectralMomentGenerator().generate(SpectralMomentPhantomSpec())
    for case in phantom.cases:
        inputs = case.estimator_inputs
        assert set(inputs.fit_sample_ids.tolist()).isdisjoint(
            inputs.evaluation_sample_ids.tolist()
        )
        assert (
            np.intersect1d(
                inputs.fit_angles_rad,
                inputs.evaluation_angles_rad,
            ).size
            == 0
        )
        assert inputs.to_dict()["truth_present"] is False
        assert re.fullmatch(r"smi_[0-9a-f]{32}", inputs.input_id)
        assert all(
            token not in inputs.input_id
            for token in ("positive", "null", "prerequisite", "failure")
        )
        assert case.case_id not in inputs.input_id
        assert "disposition" not in inputs.to_dict()
        assert "case_id" not in inputs.to_dict()
        for value in (
            inputs.row_ids,
            inputs.fit_sample_ids,
            inputs.fit_angles_rad,
            inputs.fit_values,
            inputs.evaluation_sample_ids,
            inputs.evaluation_angles_rad,
            inputs.evaluation_values,
        ):
            assert value.flags.c_contiguous
            assert value.flags.writeable is False
            with pytest.raises(ValueError):
                value.setflags(write=True)
        for value in (
            case.oracle_truth.row_ids,
            case.oracle_truth.f2_coordinates,
            case.oracle_truth.f2_amplitude,
            case.oracle_truth.f2_support,
            case.oracle_truth.f4_spin_two_coordinates,
            case.oracle_truth.f4_traceless_tensor,
            case.oracle_truth.f4_amplitude,
            case.oracle_truth.f4_support,
        ):
            assert value.flags.c_contiguous
            assert value.flags.writeable is False
            with pytest.raises(ValueError):
                value.setflags(write=True)


def test_disjoint_splits_recover_the_same_declared_f2_and_f4_moments() -> None:
    spec = SpectralMomentPhantomSpec()
    phantom = SpectralMomentGenerator().generate(spec)
    for case in phantom.cases:
        inputs = case.estimator_inputs
        truth = case.oracle_truth
        fit_first, fit_second = _moments(
            inputs.fit_angles_rad,
            inputs.fit_values,
            baseline=spec.baseline,
        )
        evaluation_first, evaluation_second = _moments(
            inputs.evaluation_angles_rad,
            inputs.evaluation_values,
            baseline=spec.baseline,
        )
        assert np.allclose(fit_first, truth.f2_coordinates, atol=2e-15)
        assert np.allclose(
            evaluation_first,
            truth.f2_coordinates,
            atol=2e-15,
        )
        assert np.allclose(
            fit_second,
            truth.f4_spin_two_coordinates,
            atol=2e-15,
        )
        assert np.allclose(
            evaluation_second,
            truth.f4_spin_two_coordinates,
            atol=2e-15,
        )


def test_positive_null_and_prerequisite_failure_are_explicit_non_gate_controls() -> (
    None
):
    phantom = SpectralMomentGenerator().generate(SpectralMomentPhantomSpec())
    positive, fixed_null, failure = phantom.cases

    assert positive.case_id == SPECTRAL_MOMENT_POSITIVE
    assert fixed_null.case_id == SPECTRAL_MOMENT_FIXED_NULL
    assert failure.case_id == SPECTRAL_MOMENT_PREREQUISITE_FAILURE
    assert positive.oracle_truth.f2_disposition is ExpectedControlDisposition.POSITIVE
    assert fixed_null.oracle_truth.f4_disposition is ExpectedControlDisposition.NULL
    assert (
        failure.oracle_truth.f2_disposition
        is ExpectedControlDisposition.PREREQUISITE_FAILURE
    )

    assert np.ptp(positive.oracle_truth.f2_coordinates[:, 0]) > 0.0
    assert np.allclose(
        fixed_null.oracle_truth.f2_coordinates,
        fixed_null.oracle_truth.f2_coordinates[:1],
    )
    assert np.all(failure.oracle_truth.f2_support == 0)
    assert np.all(failure.oracle_truth.f4_support == 0)
    assert np.all(failure.oracle_truth.f2_amplitude == 0.0)
    assert np.all(failure.oracle_truth.f4_amplitude == 0.0)
    assert all(
        code == "zero_first_moment_direction_undefined"
        for code in failure.oracle_truth.f2_reason_codes
    )
    assert phantom.to_dict()["qualification_gate_evaluated"] is False
    assert phantom.to_dict()["integer_output_authorized"] is False


def test_oracle_truth_rejects_tampered_same_object_equations() -> None:
    positive = SpectralMomentGenerator().generate(SpectralMomentPhantomSpec()).cases[0]
    truth = positive.oracle_truth

    with pytest.raises(ValueError, match="f2_amplitude"):
        replace(
            truth,
            f2_amplitude=np.asarray(truth.f2_amplitude) + 0.125,
        )

    tampered_tensor = np.asarray(truth.f4_traceless_tensor).copy()
    tampered_tensor[0, 1, 0] += 0.125
    with pytest.raises(ValueError, match="f4_traceless_tensor"):
        replace(truth, f4_traceless_tensor=tampered_tensor)

    with pytest.raises(ValueError, match="f4_amplitude"):
        replace(
            truth,
            f4_amplitude=np.asarray(truth.f4_amplitude) + 0.125,
        )


def test_oracle_truth_rejects_nonzero_unsupported_rows() -> None:
    failure = SpectralMomentGenerator().generate(SpectralMomentPhantomSpec()).cases[2]
    truth = failure.oracle_truth
    coordinates = np.asarray(truth.f2_coordinates).copy()
    coordinates[0] = (1.0, 0.0)
    amplitude = np.linalg.norm(coordinates, axis=1)

    with pytest.raises(ValueError, match="unsupported f2 rows"):
        replace(
            truth,
            f2_coordinates=coordinates,
            f2_amplitude=amplitude,
        )


def test_case_requires_exact_ordered_row_identity() -> None:
    case = SpectralMomentGenerator().generate(SpectralMomentPhantomSpec()).cases[0]
    reversed_truth = replace(
        case.oracle_truth,
        row_ids=case.oracle_truth.row_ids[::-1],
    )
    with pytest.raises(ValueError, match="identical ordered row identities"):
        SpectralMomentCase(
            case_id=case.case_id,
            estimator_inputs=case.estimator_inputs,
            oracle_truth=reversed_truth,
        )

    shifted_truth = replace(
        case.oracle_truth,
        row_ids=case.oracle_truth.row_ids + 1,
    )
    with pytest.raises(ValueError, match="identical ordered row identities"):
        replace(case, oracle_truth=shifted_truth)

    repeated_ids = np.asarray(case.oracle_truth.row_ids).copy()
    repeated_ids[-1] = repeated_ids[0]
    with pytest.raises(ValueError, match="row_ids must be unique"):
        replace(case.oracle_truth, row_ids=repeated_ids)


def test_phantom_rejects_forged_family_or_source_identity() -> None:
    phantom = SpectralMomentGenerator().generate(SpectralMomentPhantomSpec())
    forged = replace(
        phantom.family_identity,
        source_sha256="0" * 64,
    )

    with pytest.raises(ValueError, match="canonical source-bound"):
        replace(phantom, family_identity=forged)


def test_estimator_input_identifier_rejects_disposition_leaks() -> None:
    case = SpectralMomentGenerator().generate(SpectralMomentPhantomSpec()).cases[0]
    for leaked in (
        "spectral-moment-positive",
        "spectral-moment-fixed-null",
        "spectral-moment-prerequisite-failure",
    ):
        with pytest.raises(ValueError, match="label-free"):
            replace(case.estimator_inputs, input_id=leaked)

    with pytest.raises(ValueError, match="observable content"):
        replace(case.estimator_inputs, input_id=f"smi_{'0' * 32}")


def test_content_pseudonym_has_no_case_or_disposition_parameter() -> None:
    expected_observables = {
        "row_ids",
        "fit_sample_ids",
        "fit_angles_rad",
        "fit_values",
        "evaluation_sample_ids",
        "evaluation_angles_rad",
        "evaluation_values",
    }
    signature = inspect.signature(module._label_free_content_pseudonym)
    assert set(signature.parameters) == expected_observables
    assert all(
        parameter.kind is inspect.Parameter.KEYWORD_ONLY
        for parameter in signature.parameters.values()
    )

    case_source = inspect.getsource(module._case)
    calls = [
        node
        for node in ast.walk(ast.parse(case_source))
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "_label_free_content_pseudonym"
    ]
    assert len(calls) == 1
    assert {keyword.arg for keyword in calls[0].keywords} == expected_observables
    assert all(
        forbidden not in signature.parameters
        for forbidden in ("slot", "case_id", "disposition")
    )

    case = SpectralMomentGenerator().generate(SpectralMomentPhantomSpec()).cases[0]
    inputs = case.estimator_inputs
    assert inputs.input_id == module._label_free_content_pseudonym(
        row_ids=inputs.row_ids,
        fit_sample_ids=inputs.fit_sample_ids,
        fit_angles_rad=inputs.fit_angles_rad,
        fit_values=inputs.fit_values,
        evaluation_sample_ids=inputs.evaluation_sample_ids,
        evaluation_angles_rad=inputs.evaluation_angles_rad,
        evaluation_values=inputs.evaluation_values,
    )
    assert "cryptographic blindness" in (inspect.getdoc(type(inputs)) or "")


def test_identity_arrays_reject_silent_numeric_coercion() -> None:
    inputs = (
        SpectralMomentGenerator()
        .generate(SpectralMomentPhantomSpec())
        .cases[0]
        .estimator_inputs
    )

    fractional_rows = inputs.row_ids.astype(np.float64)
    fractional_rows[0] += 0.5
    with pytest.raises(TypeError, match="integer, non-boolean"):
        replace(inputs, row_ids=fractional_rows)

    boolean_fit_ids = inputs.fit_sample_ids.astype(np.bool_)
    with pytest.raises(TypeError, match="integer, non-boolean"):
        replace(inputs, fit_sample_ids=boolean_fit_ids)

    out_of_range_evaluation_ids = inputs.evaluation_sample_ids.astype(np.uint64)
    out_of_range_evaluation_ids[0] = np.uint64(2**63)
    with pytest.raises(ValueError, match="outside int64 range"):
        replace(
            inputs,
            evaluation_sample_ids=out_of_range_evaluation_ids,
        )


def test_support_masks_and_float_fields_require_exact_dtype_kinds() -> None:
    case = SpectralMomentGenerator().generate(SpectralMomentPhantomSpec()).cases[0]
    integer_support = np.full(
        case.oracle_truth.f2_support.shape,
        2,
        dtype=np.int64,
    )
    with pytest.raises(TypeError, match="boolean dtype"):
        replace(case.oracle_truth, f2_support=integer_support)
    with pytest.raises(TypeError, match="boolean dtype"):
        replace(case.oracle_truth, f4_support=integer_support)

    integer_angles = np.arange(
        case.estimator_inputs.fit_angles_rad.shape[0],
        dtype=np.int64,
    )
    with pytest.raises(TypeError, match="real floating dtype"):
        replace(case.estimator_inputs, fit_angles_rad=integer_angles)
    with pytest.raises(TypeError, match="real floating dtype"):
        replace(
            case.estimator_inputs,
            fit_values=case.estimator_inputs.fit_values.astype(np.complex128),
        )


def test_public_records_reject_empty_domains_and_duplicate_angles() -> None:
    case = SpectralMomentGenerator().generate(SpectralMomentPhantomSpec()).cases[0]
    inputs = case.estimator_inputs
    with pytest.raises(ValueError, match="row identities must be nonempty"):
        replace(inputs, row_ids=np.asarray([], dtype=np.int64))
    with pytest.raises(
        ValueError,
        match="fit sample identities must be nonempty",
    ):
        replace(inputs, fit_sample_ids=np.asarray([], dtype=np.int64))
    with pytest.raises(
        ValueError,
        match="evaluation sample identities must be nonempty",
    ):
        replace(
            inputs,
            evaluation_sample_ids=np.asarray([], dtype=np.int64),
        )
    with pytest.raises(ValueError, match="oracle rows must be nonempty"):
        replace(
            case.oracle_truth,
            f2_coordinates=np.empty((0, 2), dtype=np.float64),
        )

    duplicate_fit_angles = np.asarray(inputs.fit_angles_rad).copy()
    duplicate_fit_angles[1] = duplicate_fit_angles[0]
    with pytest.raises(ValueError, match="fit quadrature angles must be unique"):
        replace(inputs, fit_angles_rad=duplicate_fit_angles)

    duplicate_evaluation_angles = np.asarray(inputs.evaluation_angles_rad).copy()
    duplicate_evaluation_angles[1] = duplicate_evaluation_angles[0]
    with pytest.raises(
        ValueError,
        match="evaluation quadrature angles must be unique",
    ):
        replace(
            inputs,
            evaluation_angles_rad=duplicate_evaluation_angles,
        )


def test_oracle_rejects_arbitrary_failure_reasons_and_vacuous_support() -> None:
    phantom = SpectralMomentGenerator().generate(SpectralMomentPhantomSpec())
    positive = phantom.cases[0].oracle_truth
    failure = phantom.cases[2].oracle_truth
    arbitrary = tuple("arbitrary_failure" for _ in failure.f2_reason_codes)

    with pytest.raises(ValueError, match="f2 reason codes"):
        replace(failure, f2_reason_codes=arbitrary)
    with pytest.raises(ValueError, match="f4 reason codes"):
        replace(failure, f4_reason_codes=arbitrary)

    zero_f2 = np.zeros_like(positive.f2_coordinates)
    with pytest.raises(ValueError, match="supported f2 rows"):
        replace(
            positive,
            f2_coordinates=zero_f2,
            f2_amplitude=np.zeros_like(positive.f2_amplitude),
        )

    zero_f4 = np.zeros_like(positive.f4_spin_two_coordinates)
    with pytest.raises(ValueError, match="supported f4 rows"):
        replace(
            positive,
            f4_spin_two_coordinates=zero_f4,
            f4_traceless_tensor=np.zeros_like(positive.f4_traceless_tensor),
            f4_amplitude=np.zeros_like(positive.f4_amplitude),
        )


def test_case_dispositions_are_verified_from_exact_direction_structure() -> None:
    positive_case, null_case, _ = (
        SpectralMomentGenerator().generate(SpectralMomentPhantomSpec()).cases
    )
    positive = positive_case.oracle_truth
    fixed = null_case.oracle_truth

    positive_with_fixed_f2 = replace(
        positive,
        f2_coordinates=fixed.f2_coordinates,
        f2_amplitude=fixed.f2_amplitude,
    )
    with pytest.raises(ValueError, match="vary f2 direction"):
        replace(positive_case, oracle_truth=positive_with_fixed_f2)

    positive_with_fixed_f4 = replace(
        positive,
        f4_spin_two_coordinates=fixed.f4_spin_two_coordinates,
        f4_traceless_tensor=fixed.f4_traceless_tensor,
        f4_amplitude=fixed.f4_amplitude,
    )
    with pytest.raises(ValueError, match="vary f4 direction"):
        replace(positive_case, oracle_truth=positive_with_fixed_f4)

    null_with_varying_f2 = replace(
        fixed,
        f2_coordinates=positive.f2_coordinates,
        f2_amplitude=positive.f2_amplitude,
    )
    with pytest.raises(ValueError, match="fixed f2 direction"):
        replace(null_case, oracle_truth=null_with_varying_f2)

    null_with_varying_f4 = replace(
        fixed,
        f4_spin_two_coordinates=positive.f4_spin_two_coordinates,
        f4_traceless_tensor=positive.f4_traceless_tensor,
        f4_amplitude=positive.f4_amplitude,
    )
    with pytest.raises(ValueError, match="fixed f4 direction"):
        replace(null_case, oracle_truth=null_with_varying_f4)


def test_spectral_dicts_are_fingerprint_receipts_not_persistence_schemas() -> None:
    phantom = SpectralMomentGenerator().generate(SpectralMomentPhantomSpec())
    records = (
        phantom.spec.to_dict(),
        phantom.cases[0].estimator_inputs.to_dict(),
        phantom.cases[0].oracle_truth.to_dict(),
        phantom.cases[0].to_dict(),
        phantom.to_dict(),
    )

    for record in records:
        assert "schema_version" not in record
        assert record["record_scope"] == "in-memory-fingerprint-only"
        assert record["persistence_round_trip_supported"] is False


def test_spec_rejects_parameter_induced_runaway_allocation_before_generation() -> None:
    with pytest.raises(ValueError, match="estimated peak allocation"):
        SpectralMomentPhantomSpec(row_count=2**62)
    with pytest.raises(ValueError, match="estimated peak allocation"):
        SpectralMomentPhantomSpec(samples_per_split=2**62)

    spec = SpectralMomentPhantomSpec()
    receipt = spec.to_dict()
    assert (
        receipt["resource_estimator_id"] == module.SPECTRAL_MOMENT_RESOURCE_ESTIMATOR_ID
    )
    assert receipt["estimated_peak_bytes"] == spec.estimated_peak_bytes
    assert receipt["estimated_peak_bytes"] <= receipt["max_estimated_peak_bytes"]
    assert (
        receipt["resource_claim_boundary"]
        == "parameter-induced-runaway-allocation-guard-not-os-oom-guarantee"
    )


@pytest.mark.parametrize(
    "overrides",
    [
        {"f2_amplitude": 1e-18},
        {"f4_amplitude": 1e-18},
        {"baseline": 1e16},
    ],
)
def test_spec_rejects_numerically_unresolvable_harmonics(
    overrides: dict[str, float],
) -> None:
    with pytest.raises(ValueError, match="resolvability floor"):
        SpectralMomentPhantomSpec(**overrides)

    with pytest.raises(ValueError, match="finite combined numerical scale"):
        SpectralMomentPhantomSpec(
            baseline=1e308,
            f2_amplitude=1e308,
            f4_amplitude=1e308,
        )

    with pytest.raises(ValueError, match="derived-arithmetic safety bound"):
        SpectralMomentPhantomSpec(
            baseline=1e300,
            f2_amplitude=2e294,
            f4_amplitude=2e294,
        )
