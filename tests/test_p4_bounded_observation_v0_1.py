"""Analytic, noncampaign development tests of conditional outer bounds."""

from __future__ import annotations

from copy import deepcopy
import inspect
from pathlib import Path
import sys

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import p4_bounded_reference_v0_1 as witness  # noqa: E402
import prototype_p4_bounded_observation_v0_1 as kernel  # noqa: E402


# Unit-test coefficients are intentionally not the generator's IDEAL reference.
BACKGROUND = np.array([[0.031, -0.017], [0.91, 0.13], [-0.09, 1.07]])
CENTER = 0.13 - 0.09j
AMPLITUDE = 0.025 * np.exp(0.31j)


def vector(values):
    return np.column_stack((np.real(values), np.imag(values)))


def analytic(distance=0.0, *, reverse=False):
    """Truth-side fixture construction only; no fixture enters kernel.infer."""
    z = kernel.SUPPORT[:, 0] + 1j * kernel.SUPPORT[:, 1]
    delta = (distance / 2) * np.exp(0.63j)
    residual = AMPLITUDE * ((z - CENTER) ** 2 - delta**2)
    coefficients = np.array(
        [
            AMPLITUDE * (CENTER**2 - delta**2),
            -2 * AMPLITUDE * CENTER,
            -2j * AMPLITUDE * CENTER,
            AMPLITUDE,
            2j * AMPLITUDE,
            -AMPLITUDE,
        ]
    )
    if reverse:
        residual, coefficients = np.conj(residual), np.conj(coefficients)
    design = np.column_stack((np.ones(25), kernel.SUPPORT))
    return design @ BACKGROUND + vector(residual), vector(coefficients)


def budget(reference=BACKGROUND, observed_witness=BACKGROUND, radius=0.0):
    return witness.reference_budget(
        reference,
        observed_witness,
        np.broadcast_to(radius, (3,)),
        witness_independent=True,
        witness_id="unit-test-separate-witness",
    )


def assert_missing_roots(readout):
    for field in (
        "center",
        "center_radius",
        "discriminant",
        "discriminant_radius",
        "separation_lower",
        "separation_upper",
        "estimated_roots",
        "root_radius",
        "root_regions_disjoint",
    ):
        assert readout[field] is None, field


@pytest.mark.parametrize("distance", [0.0, 0.08, 0.16])
@pytest.mark.parametrize("reverse", [False, True])
def test_clean_single_pair_reverse_and_conditional_claims(distance, reverse):
    field, coefficients = analytic(distance, reverse=reverse)
    readout = kernel.infer(field, BACKGROUND, budget(), np.zeros(25))
    assert readout["status"] == (
        "one_not_excluded" if distance == 0 else "two_required_in_family"
    )
    assert readout["orientation"] == ("antiholomorphic" if reverse else "holomorphic")
    assert (
        np.linalg.norm(np.asarray(readout["center"]) - vector([CENTER])[0])
        <= readout["center_radius"]
    )
    assert readout["separation_lower"] <= distance <= readout["separation_upper"]
    assert np.all(
        np.linalg.norm(
            np.asarray(readout["polynomial_coefficients"]) - coefficients, axis=1
        )
        <= readout["coefficient_radii"]
    )
    for claim in (
        "global_family_verified",
        "calibrated_confidence_region",
        "scientific_authority",
    ):
        assert readout[claim] is False
    assert readout["noise_location"] == "post-adapter-moment-space"
    assert kernel.verify_readout(readout, field, BACKGROUND, budget(), np.zeros(25))


@pytest.mark.parametrize("seed", [7, 11, 19])
@pytest.mark.parametrize("epsilon", [0.0, 1e-7, 1e-5])
@pytest.mark.parametrize(
    "distance,reverse", [(0.0, False), (0.16, False), (0.16, True)]
)
def test_bounded_noise_and_reference_discrepancy_preserve_outer_coverage(
    seed, epsilon, distance, reverse
):
    field, truth_coefficients = analytic(distance, reverse=reverse)
    rng = np.random.default_rng(np.random.SeedSequence([seed, 0x424F554E]))
    point_bounds = epsilon * np.linspace(0.25, 1.0, 25)
    noise = (
        point_bounds * rng.uniform(0.0, 1.0, 25) * np.exp(2j * np.pi * rng.random(25))
    )
    observed = field + vector(noise)
    chosen_reference = BACKGROUND + np.array(
        [[5e-4, 2e-4], [2e-5, -1e-5], [-3e-5, 4e-5]]
    )
    witness_radii = np.array([2e-6, 3e-6, 4e-6])
    witness_error = vector(0.8 * witness_radii * np.exp(2j * np.pi * rng.random(3)))
    ref_budget = budget(chosen_reference, BACKGROUND + witness_error, witness_radii)
    before = [value.copy() for value in (observed, chosen_reference, point_bounds)]
    readout = kernel.infer(observed, chosen_reference, ref_budget, point_bounds)
    assert readout["status"] in {"one_not_excluded", "two_required_in_family"}
    assert np.all(np.asarray(readout["heldout_errors"]) <= readout["heldout_limits"])
    assert np.all(
        np.linalg.norm(
            np.asarray(readout["polynomial_coefficients"]) - truth_coefficients, axis=1
        )
        <= readout["coefficient_radii"]
    )
    assert (
        np.linalg.norm(np.asarray(readout["center"]) - vector([CENTER])[0])
        <= readout["center_radius"]
    )
    assert readout["separation_lower"] <= distance <= readout["separation_upper"]
    if distance == 0:
        assert readout["status"] == "one_not_excluded"
    for actual, original in zip(
        (observed, chosen_reference, point_bounds), before, strict=True
    ):
        np.testing.assert_array_equal(actual, original)


def test_noise_propagation_matches_absolute_design_operator():
    field, _ = analytic(0.16)
    residual = kernel.spatial.subtract(field, kernel.SUPPORT, BACKGROUND)
    bounds = np.linspace(1e-7, 3e-7, 25)
    _, radii, _, limits = kernel.polynomial_fit(residual, bounds)
    qf = kernel.base.design(kernel.base.FIT)
    qv = kernel.base.design(kernel.base.HELDOUT)
    inverse = np.linalg.pinv(qf)
    np.testing.assert_array_equal(radii, np.abs(inverse) @ bounds[:9] + kernel.NUM)
    np.testing.assert_array_equal(
        limits, bounds[9:] + np.abs(qv @ inverse) @ bounds[:9] + kernel.NUM
    )
    readout = kernel.infer(field, BACKGROUND, budget(radius=2e-6), bounds)
    np.testing.assert_array_equal(
        np.asarray(readout["coefficient_radii"])[3:], radii[3:]
    )
    np.testing.assert_allclose(
        np.asarray(readout["coefficient_radii"])[:3] - radii[:3],
        budget(radius=2e-6)["radii"],
        rtol=1e-15,
        atol=0,
    )


def test_absent_witness_prevents_absolute_root_claims():
    field, _ = analytic(0.16)
    ref_budget = witness.reference_budget(BACKGROUND)
    readout = kernel.infer(field, BACKGROUND, ref_budget, np.zeros(25))
    assert readout["status"] == "common_mode_unidentified"
    assert readout["coefficient_radii"] is None
    assert_missing_roots(readout)


def test_nonindependent_witness_is_not_an_absolute_anchor():
    field, _ = analytic(0.16)
    ref_budget = witness.reference_budget(BACKGROUND, BACKGROUND, np.zeros(3))
    readout = kernel.infer(field, BACKGROUND, ref_budget, np.zeros(25))
    assert readout["status"] == "common_mode_unidentified"
    assert_missing_roots(readout)


def test_shared_bias_remains_a_declared_witness_assumption_blind_spot():
    field, _ = analytic(0.0)
    biased = BACKGROUND.copy()
    biased[0] += np.array([5e-4, 2e-4])
    # Valid contract: independent clean witness exposes the reference offset.
    valid_budget = budget(biased, BACKGROUND)
    valid = kernel.infer(field, biased, valid_budget, np.zeros(25))
    assert valid["status"] == "one_not_excluded"
    assert valid["separation_lower"] == 0
    # Deliberately false contract: both channels share an unbounded offset.
    # Agreement alone cannot reveal it; this is not a valid-contract success.
    invalid_budget = budget(biased, biased)
    invalid = kernel.infer(field, biased, invalid_budget, np.zeros(25))
    assert invalid_budget["shared_bias_diagnosed"] is False
    assert invalid_budget["physical_independence_verified"] is False
    assert (
        np.linalg.norm(biased[0] - BACKGROUND[0]) > invalid_budget["witness_radii"][0]
    )
    assert invalid["status"] == "two_required_in_family"
    assert invalid["separation_lower"] > 0
    assert invalid["global_family_verified"] is False


@pytest.mark.parametrize("constant", [0.0, 0.1])
def test_unresolved_curvature_does_not_become_verified_zero_or_affine(constant):
    design = np.column_stack((np.ones(25), kernel.SUPPORT))
    field = design @ BACKGROUND + np.array([constant, 0.0])
    readout = kernel.infer(field, BACKGROUND, budget(), np.full(25, 1e-3))
    assert readout["status"] == (
        "zero_not_excluded" if constant == 0 else "curvature_unresolved"
    )
    assert readout["global_family_verified"] is False
    assert_missing_roots(readout)


def test_tiny_quadratic_curvature_has_no_division_by_uncertain_denominator():
    field, _ = analytic()
    background = np.column_stack((np.ones(25), kernel.SUPPORT)) @ BACKGROUND
    field = background + (field - background) * 1e-7
    readout = kernel.infer(field, BACKGROUND, budget(), np.full(25, 1e-5))
    assert readout["status"] in {"zero_not_excluded", "curvature_unresolved"}
    assert_missing_roots(readout)


@pytest.mark.parametrize("declared", [0.0, 1e-5])
def test_heldout_only_underdeclared_errors_are_rejected(declared):
    field, _ = analytic(0.16)
    field[9] += np.array([1e-3, -2e-3])
    readout = kernel.infer(field, BACKGROUND, budget(), np.full(25, declared))
    assert readout["status"] == "observation_model_mismatch"
    assert readout["heldout_compatible"] is False
    assert_missing_roots(readout)


def test_declared_heldout_error_is_propagated_without_changing_coefficient_fit():
    field, _ = analytic(0.16)
    field[9] += np.array([1e-3, -2e-3])
    bounds = np.zeros(25)
    bounds[9] = np.hypot(1e-3, 2e-3) + 1e-12
    readout = kernel.infer(field, BACKGROUND, budget(), bounds)
    assert readout["status"] == "two_required_in_family"
    assert readout["heldout_compatible"] is True
    np.testing.assert_array_equal(
        readout["coefficient_noise_radii"], np.full(6, kernel.NUM)
    )


@pytest.mark.parametrize("family", ["dipole", "cubic", "inactive-linear"])
def test_unsupported_families_preserve_unavailable_bounds(family):
    z = kernel.SUPPORT[:, 0] + 1j * kernel.SUPPORT[:, 1] - CENTER
    background = np.column_stack((np.ones(25), kernel.SUPPORT)) @ BACKGROUND
    if family == "dipole":
        residual = AMPLITUDE * (z - 0.2) * np.conj(z + 0.2)
    elif family == "cubic":
        residual = AMPLITUDE * z**3
    else:
        residual = AMPLITUDE * (z**2 + 0.1 * np.conj(z))
    readout = kernel.infer(
        background + vector(residual), BACKGROUND, budget(), np.zeros(25)
    )
    assert readout["status"] in {"out_of_family", "observation_model_mismatch"}
    assert_missing_roots(readout)


def test_inference_cannot_access_fixture_truth_or_ideal(monkeypatch):
    field, _ = analytic(0.16)
    ref_budget = budget()
    expected = kernel.infer(field, BACKGROUND, ref_budget, np.zeros(25))

    def forbidden(*args, **kwargs):
        raise AssertionError("inference accessed fixture/oracle truth")

    monkeypatch.setattr(kernel.base, "geometry", forbidden)
    monkeypatch.setattr(kernel.base, "injected_field", forbidden)
    monkeypatch.setattr(kernel.base, "score_inference", forbidden)
    monkeypatch.setattr(kernel.spatial, "IDEAL", None)
    assert list(inspect.signature(kernel.infer).parameters) == [
        "measured_field",
        "reference",
        "reference_budget",
        "observation_bounds",
    ]
    assert kernel.infer(field, BACKGROUND, ref_budget, np.zeros(25)) == expected


@pytest.mark.parametrize("position", [0, 1, 3])
@pytest.mark.parametrize("invalid", ["complex", "nan", "inf", "shape"])
def test_malformed_numeric_inputs_fail(position, invalid):
    field, _ = analytic(0.16)
    arguments = [field.copy(), BACKGROUND.copy(), budget(), np.zeros(25)]
    value = arguments[position]
    if invalid == "complex":
        value = value.astype(complex)
        value.flat[0] += 1j
    elif invalid == "shape":
        value = value[:-1]
    else:
        value.flat[0] = np.nan if invalid == "nan" else np.inf
    arguments[position] = value
    with pytest.raises(ValueError):
        kernel.infer(*arguments)


def test_negative_observation_bound_fails():
    field, _ = analytic(0.16)
    bounds = np.zeros(25)
    bounds[4] = -1e-12
    with pytest.raises(ValueError):
        kernel.infer(field, BACKGROUND, budget(), bounds)


@pytest.mark.parametrize(
    "change", ["missing", "negative-radius", "reference", "witness-id"]
)
def test_bad_or_unbound_reference_budget_fails(change):
    field, _ = analytic(0.16)
    reference = BACKGROUND.copy()
    ref_budget = budget()
    if change == "missing":
        ref_budget = None
    elif change == "negative-radius":
        ref_budget["radii"][0] = -1
    elif change == "reference":
        reference[0, 0] += 1e-5
    else:
        ref_budget["witness_id"] = "other-source"
    with pytest.raises(ValueError):
        kernel.infer(field, reference, ref_budget, np.zeros(25))


@pytest.mark.parametrize(
    "change", ["status", "radius", "seal", "authority-type", "input", "bounds"]
)
def test_readout_and_external_input_tampering_fails_replay(change):
    field, _ = analytic(0.16)
    ref_budget = budget()
    bounds = np.zeros(25)
    readout = deepcopy(kernel.infer(field, BACKGROUND, ref_budget, bounds))
    if change == "status":
        readout["status"] = "one_not_excluded"
    elif change == "radius":
        readout["center_radius"] += 1
    elif change == "seal":
        readout["readout_seal_sha256"] = "0" * 64
    elif change == "authority-type":
        readout["scientific_authority"] = 0
    elif change == "input":
        field[0, 0] += 1e-6
    else:
        bounds[0] = 1e-6
    with pytest.raises(ValueError):
        kernel.verify_readout(readout, field, BACKGROUND, ref_budget, bounds)
