from __future__ import annotations

import json
from pathlib import Path
import sys

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import p4_bounded_reference_v0_1 as kernel  # noqa: E402


REFERENCE = np.array([[0.12, -0.08], [0.94, 0.02], [-0.04, 1.07]])
WITNESS = np.array([[0.01, -0.02], [1.01, 0.01], [0.02, 0.99]])
RADII = np.array([0.03, 0.04, 0.05])


def bounded():
    return kernel.reference_budget(
        REFERENCE,
        WITNESS,
        RADII,
        witness_independent=True,
        witness_id="synthetic-channel-b",
    )


def reseal(report):
    report["budget_seal_sha256"] = kernel.SEAL(
        {key: value for key, value in report.items() if key != "budget_seal_sha256"}
    )


def test_missing_anchor_does_not_invent_zero_radius():
    report = kernel.reference_budget(REFERENCE)
    assert report["status"] == "common_mode_unidentified"
    assert report["reason"] == "witness_missing"
    assert report["radii"] is None
    assert report["witness_sha256"] is None
    assert kernel.validate_budget(report, REFERENCE)


@pytest.mark.parametrize("independent", [False, True])
def test_unbounded_witness_never_produces_reference_bound(independent):
    report = kernel.reference_budget(
        REFERENCE,
        WITNESS,
        witness_independent=independent,
        witness_id="synthetic-channel-b",
    )
    assert report["status"] == "common_mode_unidentified"
    assert report["reason"] == "witness_error_unbounded"
    assert report["radii"] is None
    assert kernel.validate_budget(report, REFERENCE)


def test_shared_provenance_is_unidentified_despite_small_disagreement():
    report = kernel.reference_budget(
        REFERENCE, REFERENCE, RADII, witness_id="shared-channel"
    )
    assert report["row_disagreement"] == [0.0, 0.0, 0.0]
    assert report["radii"] is None
    assert report["status"] == "common_mode_unidentified"


def test_exact_triangle_rule_and_seals_and_json_roundtrip():
    report = bounded()
    difference = REFERENCE - WITNESS
    expected = (
        np.hypot(difference[:, 0], difference[:, 1]) + RADII + kernel.NUMERICAL_MARGIN
    )
    np.testing.assert_array_equal(report["radii"], expected)
    assert report["reference_sha256"] == kernel.HASH(REFERENCE)
    assert report["witness_sha256"] == kernel.HASH(WITNESS)
    assert report["witness_coefficients"] == WITNESS.tolist()
    assert report["status"] == "bounded_relative_to_witness"
    assert kernel.validate_budget(json.loads(json.dumps(report)), REFERENCE)
    assert kernel.verify_budget(
        report,
        REFERENCE,
        WITNESS,
        RADII,
        witness_independent=True,
        witness_id="synthetic-channel-b",
    )


def test_independent_bounded_witness_can_enclose_reference_errors():
    # Test-only truth checks the conditional theorem; production takes no truth.
    truth = np.array([[0.0, 0.0], [1.0, 0.0], [0.0, 1.0]])
    witness_errors = np.linalg.norm(WITNESS - truth, axis=1)
    assert np.all(witness_errors <= RADII)
    reference_errors = np.linalg.norm(REFERENCE - truth, axis=1)
    assert np.all(reference_errors <= bounded()["radii"])


def test_common_affine_shift_is_invisible_to_channel_disagreement():
    # Binary-exact values avoid irrelevant subtraction-roundoff differences.
    reference = np.array([[0.25, -0.5], [1.25, 0.0], [0.0, 0.75]])
    witness = np.array([[0.0, 0.0], [1.0, 0.0], [0.0, 1.0]])
    shared = np.array([[8.0, -4.0], [-2.0, 1.0], [0.5, 2.0]])
    a = kernel.reference_budget(reference, witness, RADII, witness_id="shared")
    b = kernel.reference_budget(
        reference + shared, witness + shared, RADII, witness_id="shared"
    )
    assert a["row_disagreement"] == b["row_disagreement"]
    assert a["radii"] is b["radii"] is None
    # Even declaring independence cannot let this helper verify it physically.
    c = kernel.reference_budget(
        reference, witness, RADII, witness_independent=True, witness_id="claimed"
    )
    d = kernel.reference_budget(
        reference + shared,
        witness + shared,
        RADII,
        witness_independent=True,
        witness_id="claimed",
    )
    assert c["radii"] == d["radii"]
    assert d["shared_bias_diagnosed"] is False
    assert d["physical_independence_verified"] is False


def test_inputs_are_not_mutated_or_aliased():
    reference, witness, radii = REFERENCE.copy(), WITNESS.copy(), RADII.copy()
    report = kernel.reference_budget(
        reference, witness, radii, witness_independent=True, witness_id="b"
    )
    np.testing.assert_array_equal(reference, REFERENCE)
    np.testing.assert_array_equal(witness, WITNESS)
    np.testing.assert_array_equal(radii, RADII)
    report["witness_coefficients"][0][0] = 99.0
    report["witness_radii"][0] = 99.0
    np.testing.assert_array_equal(witness, WITNESS)
    np.testing.assert_array_equal(radii, RADII)


@pytest.mark.parametrize("value", [np.bool_(True), 1, 0, "true", None])
def test_non_boolean_independence_rejected(value):
    with pytest.raises(ValueError):
        kernel.reference_budget(
            REFERENCE, WITNESS, RADII, witness_independent=value, witness_id="b"
        )


@pytest.mark.parametrize(
    "value", [True, False, 1, "", " ", " leading", "trailing ", "line\nbreak"]
)
def test_invalid_witness_identifiers_rejected(value):
    with pytest.raises(ValueError):
        kernel.reference_budget(REFERENCE, WITNESS, RADII, witness_id=value)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"witness_radii": RADII},
        {"witness_id": "b"},
        {"witness_independent": True},
        {"witness": WITNESS, "witness_independent": True},
    ],
)
def test_inconsistent_absent_metadata_rejected(kwargs):
    with pytest.raises(ValueError):
        kernel.reference_budget(REFERENCE, **kwargs)


@pytest.mark.parametrize(
    "bad",
    [
        np.zeros((2, 3)),
        np.zeros((6,)),
        np.full((3, 2), np.nan),
        np.full((3, 2), np.inf),
        np.full((3, 2), True),
        [[True, 0.0], [1.0, 0.0], [0.0, 1.0]],
        np.ones((3, 2), dtype=complex),
        [["0", "0"]] * 3,
    ],
)
@pytest.mark.parametrize("field", ["reference", "witness"])
def test_invalid_coefficients_rejected(bad, field):
    args = {"reference": REFERENCE, "witness": WITNESS}
    args[field] = bad
    with pytest.raises(ValueError):
        kernel.reference_budget(**args)


@pytest.mark.parametrize(
    "bad",
    [
        [-0.1, 0.0, 0.0],
        [0.0, np.nan, 0.0],
        [0.0, np.inf, 0.0],
        [0.0, 0.0],
        np.zeros((3, 1)),
        [True, 0.0, 0.0],
        ["0", "0", "0"],
    ],
)
def test_invalid_witness_radii_rejected(bad):
    with pytest.raises(ValueError):
        kernel.reference_budget(REFERENCE, WITNESS, bad)


@pytest.mark.parametrize(
    "field,value",
    [
        ("radii", [1.0, 1.0, 1.0]),
        ("scientific_authority", True),
        ("scientific_authority", 0),
        ("calibrated_confidence", True),
        ("empirical_confidence", True),
        ("physical_independence_verified", True),
        ("status", "common_mode_unidentified"),
        ("reference_sha256", "f" * 64),
        ("witness_sha256", "f" * 64),
        ("numerical_margin", 1e-6),
        ("unexpected_field", False),
    ],
)
@pytest.mark.parametrize("resealed", [False, True])
def test_tampered_records_fail_even_if_resealed(field, value, resealed):
    report = bounded()
    report[field] = value
    if resealed:
        reseal(report)
    with pytest.raises(ValueError):
        kernel.validate_budget(report, REFERENCE)


def test_external_verification_binds_full_declared_witness():
    report = bounded()
    with pytest.raises(ValueError):
        kernel.verify_budget(
            report,
            REFERENCE,
            WITNESS + 0.01,
            RADII,
            witness_independent=True,
            witness_id="synthetic-channel-b",
        )
    with pytest.raises(ValueError):
        kernel.verify_budget(
            report,
            REFERENCE,
            WITNESS,
            RADII,
            witness_independent=True,
            witness_id="different-channel",
        )
    with pytest.raises(ValueError):
        kernel.validate_budget(report, REFERENCE + 0.01)
    del report["witness_coefficients"]
    with pytest.raises(ValueError):
        kernel.validate_budget(report, REFERENCE)


def test_overflow_is_not_an_infinite_budget():
    with pytest.raises(ValueError):
        kernel.reference_budget(np.full((3, 2), 1e308), np.full((3, 2), -1e308))


@pytest.mark.parametrize("h", [0.5, 1.0])
def test_fixed_cross_fit_and_point_error_propagation(h):
    coords = kernel.witness_stencil(h)
    design = np.column_stack((np.ones(5), coords))
    values = design @ WITNESS
    epsilon = 0.01
    report = kernel.fit_affine_witness(coords, values, np.full(5, epsilon))
    np.testing.assert_allclose(report["coefficients"], WITNESS, rtol=0, atol=2e-15)
    np.testing.assert_allclose(
        report["radii"],
        np.array([epsilon, epsilon / h, epsilon / h]) + kernel.NUMERICAL_MARGIN,
        rtol=0,
        atol=1e-16,
    )
    assert report["fit_max_error"] < 2e-15
    assert report["fit_residual_used_as_error_bound"] is False
    assert report["scientific_authority"] is False
    assert report["physical_independence_verified"] is False


def test_wider_placement_only_halves_linear_bound_not_common_bias():
    fits = []
    shift = np.array([0.1, -0.2])
    for h in (0.5, 1.0):
        coords = kernel.witness_stencil(h)
        design = np.column_stack((np.ones(5), coords))
        fit = kernel.fit_affine_witness(
            coords, design @ WITNESS + shift, np.full(5, 0.01)
        )
        fits.append(fit)
        np.testing.assert_allclose(
            np.asarray(fit["coefficients"])[0], WITNESS[0] + shift, atol=1e-15
        )
    narrow, wide = (np.array(fit["radii"]) - kernel.NUMERICAL_MARGIN for fit in fits)
    np.testing.assert_allclose(narrow, wide * [1.0, 2.0, 2.0], atol=1e-16)
    assert all(fit["fit_max_error"] < 2e-15 for fit in fits)


def test_nonuniform_point_bounds_enclose_a_valid_affine_witness():
    coords = kernel.witness_stencil(1.0)
    design = np.column_stack((np.ones(5), coords))
    noise = np.array(
        [[0.01, 0.02], [-0.02, 0.0], [0.04, -0.02], [0.01, -0.01], [0.0, 0.03]]
    )
    bounds = np.linalg.norm(noise, axis=1)
    report = kernel.fit_affine_witness(coords, design @ WITNESS + noise, bounds)
    assert np.all(
        np.linalg.norm(np.asarray(report["coefficients"]) - WITNESS, axis=1)
        <= report["radii"]
    )


def test_registered_cross_permutation_and_no_mutation():
    coords = kernel.witness_stencil(0.5)
    values = np.column_stack((np.ones(5), coords)) @ WITNESS
    bounds = np.full(5, 0.01)
    copies = [v.copy() for v in (coords, values, bounds)]
    permutation = [4, 0, 1, 3, 2]
    fit = kernel.fit_affine_witness(
        coords[permutation], values[permutation], bounds[permutation]
    )
    np.testing.assert_allclose(fit["coefficients"], WITNESS, atol=2e-15)
    for source, before in zip((coords, values, bounds), copies):
        np.testing.assert_array_equal(source, before)


@pytest.mark.parametrize("h", [True, None, "1", 0.0, 0.25, 2.0, np.nan, np.inf])
def test_unregistered_placement_rejected(h):
    with pytest.raises(ValueError):
        kernel.witness_stencil(h)


@pytest.mark.parametrize(
    "field", ["duplicate", "arbitrary", "values", "bounds", "negative", "nan"]
)
def test_invalid_witness_fit_inputs_rejected(field):
    coords = kernel.witness_stencil(1.0)
    values = np.zeros((5, 2))
    bounds = np.zeros(5)
    if field == "duplicate":
        coords[-1] = coords[0]
    elif field == "arbitrary":
        coords *= 0.8
    elif field == "values":
        values = np.zeros((4, 2))
    elif field == "bounds":
        bounds = np.zeros((5, 1))
    elif field == "negative":
        bounds[0] = -0.1
    elif field == "nan":
        values[0, 0] = np.nan
    with pytest.raises(ValueError):
        kernel.fit_affine_witness(coords, values, bounds)
