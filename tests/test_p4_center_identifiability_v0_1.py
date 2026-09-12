from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import sys

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import prototype_p4_center_identifiability_v0_1 as kernel  # noqa: E402
import run_p4_center_identifiability_v0_1 as runner  # noqa: E402


@pytest.fixture(scope="module")
def bank():
    a, _ = kernel.calibrate(7, "envelope_calibration", repeats=16, ks=(16,))
    b, _ = kernel.calibrate(8, "envelope_calibration", repeats=16, ks=(16,))
    envelope = kernel.make_envelope([a, b], seeds=(7, 8), ks=(16,))
    reference, _ = kernel.calibrate(9, "evaluation_reference", repeats=16, ks=(16,))
    return envelope, reference["references"]


@pytest.fixture(scope="module")
def local(bank):
    envelope, refs = bank
    return kernel.local_unit(
        refs,
        envelope,
        "b" * 64,
        alpha=0.1,
        geometry_seed=77,
        fixture="pair-016",
        cells=32,
    )


def test_registered_denominators_and_disjoint_stencils():
    cases = runner.cases()
    assert runner.sha(ROOT / runner.PROTOCOL) == runner.PROTOCOL_SHA256
    assert len(cases) == 144
    assert [
        sum(c["lane"] == lane for c in cases)
        for lane in ("envelope_calibration", "evaluation_reference", "geometry")
    ] == [32, 16, 96]
    assert 48 * 4096 * 2 == 393216
    assert 96 * (16 * 3 * 2 + 2) == 9408
    assert kernel.KS == (16, 256, 4096)
    assert set(kernel.ENVELOPE_SEEDS).isdisjoint(kernel.REFERENCE_SEEDS)
    assert set(kernel.REFERENCE_SEEDS).isdisjoint(kernel.GEOMETRY_SEEDS)
    assert not set(map(tuple, kernel.FIT)) & set(map(tuple, kernel.HELDOUT))
    assert np.linalg.matrix_rank(kernel.design(kernel.FIT)) == 6


def test_stream_prefixes_independence_and_namespace():
    a = kernel.draws(7, 17)
    np.testing.assert_array_equal(a[:16], kernel.draws(7, 16))
    assert not np.array_equal(a, kernel.draws(8, 17))
    assert not np.array_equal(a, kernel.prior.calibration_draws(7, 17))
    assert not np.array_equal(a[0], a[1])


@pytest.mark.parametrize(
    "seed,repeats", [(True, 16), (-1, 16), (7, 0), (7, 4097), (7, False)]
)
def test_invalid_streams_fail(seed, repeats):
    with pytest.raises(ValueError):
        kernel.draws(seed, repeats)


def test_chunked_moments_and_prefix_fit_replay():
    report, arrays = kernel.calibrate(
        7, "evaluation_reference", repeats=257, ks=(16, 256)
    )
    assert kernel.verify_calibration(report, arrays)
    first = kernel.prior.fit_repeats(arrays["probes"][:256])
    last = kernel.prior.fit_repeats(arrays["probes"][256:])
    for h in kernel.spatial.HYPOTHESES:
        np.testing.assert_array_equal(
            arrays["moments_" + h], np.concatenate((first[0][h], last[0][h]))
        )
        np.testing.assert_array_equal(
            arrays["fits_" + h], np.concatenate((first[1][h], last[1][h]))
        )
    for r in report["references"]:
        np.testing.assert_array_equal(
            r["coefficients"], arrays["fits_" + r["hypothesis"]][: r["k"]].mean(axis=0)
        )


def test_calibration_tamper_and_geometry_leak():
    report, arrays = kernel.calibrate(7, "envelope_calibration", repeats=16, ks=(16,))
    changed = deepcopy(arrays)
    changed["probes"][0, 0, 0, 0] += 1
    with pytest.raises(ValueError, match="stream"):
        kernel.verify_calibration(report, changed)
    report["geometry_observed"] = True
    with pytest.raises(ValueError, match="chronology"):
        kernel.verify_calibration(report, arrays)


def test_envelope_pair_max_is_frozen_without_oracle(bank):
    envelope, _ = bank
    assert kernel.validate_envelope(envelope)
    assert envelope["oracle_baseline_used"] is False
    for row in envelope["rows"]:
        assert row["pairs"][0]["seeds"] == [7, 8]
        np.testing.assert_array_equal(
            row["radii"], np.asarray(row["pairs"][0]["row_differences"]) + kernel.TOL
        )
        assert row["calibrated_confidence_region"] is False


@pytest.mark.parametrize("field", ["radii", "role", "pair", "seal"])
def test_envelope_tampering_fails(bank, field):
    envelope, _ = deepcopy(bank)
    if field == "radii":
        envelope["rows"][0]["radii"][0] += 1
    elif field == "role":
        envelope["evaluation_references_observed"] = True
    elif field == "pair":
        envelope["rows"][0]["pairs"][0]["seeds"].reverse()
    else:
        envelope["envelope_seal_sha256"] = "0" * 64
    with pytest.raises(ValueError):
        kernel.validate_envelope(envelope)


def test_missing_calibration_blocks_all_downstream(tmp_path):
    with pytest.raises(ValueError, match="complete"):
        runner.close_envelope(tmp_path, [])
    assert not (tmp_path / "envelope-bank.json").exists()
    with pytest.raises(OSError):
        runner.close_references(tmp_path, [])
    assert not (tmp_path / "reference-bank.json").exists()


def test_bank_file_seal_and_plan_tamper(tmp_path):
    runner.write(tmp_path / "plan.json", {"test": "nonmeasurement"})
    runner.seal_file(
        tmp_path / "bank.json",
        {
            "plan_sha256": runner.sha(tmp_path / "plan.json"),
            "scientific_authority": False,
        },
    )
    runner.load_sealed(tmp_path / "bank.json", tmp_path)
    with (tmp_path / "plan.json").open("a") as stream:
        stream.write(" ")
    with pytest.raises(ValueError, match="closure"):
        runner.load_sealed(tmp_path / "bank.json", tmp_path)


def test_one_and_two_fields_are_constant_term_confounded():
    coords = kernel.spatial.grid_coords(32)
    single = kernel.geometry(77, "double")
    pair = kernel.geometry(77, "pair-008")
    difference = kernel.injected_field(coords, pair, 0.1) - kernel.injected_field(
        coords, single, 0.1
    )
    expected = -0.025 * (0.04 * np.exp(1j * pair["angle"])) ** 2
    np.testing.assert_allclose(difference, expected, rtol=0, atol=3e-17)


@pytest.mark.parametrize(
    "fixture",
    [
        "double",
        "pair-004",
        "pair-008",
        "pair-016",
        "pair-040",
        "reverse-008",
        "reverse-040",
    ],
)
def test_ideal_separation_and_center_coverage(fixture):
    coords = kernel.spatial.grid_coords(32)
    truth = kernel.geometry(77, fixture)
    residual = kernel.spatial.vector_values(kernel.injected_field(coords, truth, 0.1))
    result = kernel.infer(coords, residual, np.full(3, kernel.TOL))
    score = kernel.score_inference(
        result, truth, kernel.spatial.IDEAL, np.full(3, kernel.TOL)
    )
    assert result["status"] == (
        "one_not_excluded" if fixture == "double" else "two_required_in_family"
    )
    assert score["center_covered"] and score["separation_covered"]
    assert score["false_two"] is False
    assert result["orientation"] == (
        "antiholomorphic" if fixture.startswith("reverse") else "holomorphic"
    )


@pytest.mark.parametrize("fixture", ["double", "pair-008", "pair-040", "reverse-008"])
def test_algebraic_outer_bounds_cover_bounded_affine_changes(fixture):
    coords = kernel.spatial.grid_coords(32)
    truth = kernel.geometry(77, fixture)
    full = kernel.spatial.vector_values(
        kernel.spatial.complex_values(coords)
        + kernel.injected_field(coords, truth, 0.1)
    )
    rng = np.random.default_rng(77)
    radii = np.array([0.0004, 0.0006, 0.0005])
    for _ in range(24):
        delta = (
            radii * rng.uniform(0, 0.99, 3) * np.exp(1j * rng.uniform(-np.pi, np.pi, 3))
        )
        coefficients = kernel.spatial.IDEAL + kernel.spatial.vector_values(delta)
        result = kernel.infer(
            coords, kernel.spatial.subtract(full, coords, coefficients), radii
        )
        score = kernel.score_inference(result, truth, coefficients, radii)
        assert score["reference_inside_envelope"]
        assert score["center_covered"] and score["separation_covered"]
        if fixture == "double":
            assert result["status"] == "one_not_excluded"
        estimates = np.asarray(result["estimated_roots"])
        distances = np.linalg.norm(
            np.asarray(truth["centers"])[:, None, :] - estimates[None, :, :], axis=-1
        )
        assert np.all(distances.min(axis=1) <= result["root_radius"])


@pytest.mark.parametrize(
    "fixture,status",
    [
        ("zero", "zero_compatible"),
        ("constant", "nonzero_no_core_on_domain"),
        ("linear", "affine_unresolved"),
        ("dipole", "out_of_family"),
        ("cubic", "out_of_family"),
    ],
)
def test_null_and_out_of_family_controls(fixture, status):
    coords = kernel.spatial.grid_coords(32)
    truth = kernel.geometry(77, fixture)
    residual = kernel.spatial.vector_values(kernel.injected_field(coords, truth, 0.1))
    result = kernel.infer(coords, residual, np.full(3, 1e-5))
    assert result["status"] == status
    assert result["center"] is None and result["separation_lower"] is None
    if fixture == "cubic":
        assert result["reason"] == "heldout-quadratic-prediction"


def test_zero_compatible_does_not_erase_legacy_charged_component():
    coords = kernel.spatial.grid_coords(32)
    c = kernel.spatial.IDEAL * 1.0001
    record = kernel.local_record(
        coords, coords.copy(), c, np.full(3, 0.0002), kernel.geometry(77, "zero")
    )
    assert record["inference"]["status"] == "zero_compatible"
    assert record["observable"]["resolved_count"] == 1
    assert record["legacy_score"]["false_positive_count"] == 1
    assert record["inference_score"]["false_two"] is False


def test_inactive_linear_term_cannot_be_projected_away():
    coords = kernel.spatial.grid_coords(32)
    z = kernel.spatial.complex_values(coords)
    result = kernel.infer(
        coords,
        kernel.spatial.vector_values(0.025 * z * z + 0.01 * np.conj(z)),
        np.full(3, 0.0001),
    )
    assert result["status"] == "reference_envelope_mismatch"
    assert result["center"] is None


@pytest.mark.parametrize(
    "kind", ["missing", "duplicate", "nonfinite", "negative_radius"]
)
def test_invalid_inference_inputs_fail(kind):
    coords = kernel.spatial.grid_coords(32)
    values = coords.copy()
    radii = np.full(3, 0.001)
    if kind == "missing":
        coords, values = coords[1:], values[1:]
    elif kind == "duplicate":
        coords[1] = coords[0]
    elif kind == "nonfinite":
        values[0, 0] = np.nan
    else:
        radii[0] = -0.1
    with pytest.raises(ValueError):
        kernel.infer(coords, values, radii)


def test_both_evidence_lanes_replay_and_share_observed_fields(local, bank):
    report, arrays = local
    envelope, refs = bank
    assert kernel.verify_local(report, arrays, refs, envelope, "b" * 64)
    assert len(report["records"]) == 4
    for r in report["records"]:
        assert r["inference"]["input_sha256"] == r["candidates"]["input_sha256"]
        assert r["inference_score"]["truth_read_after_inference"] is True
        assert r["legacy_score"]["truth_read_after_reconstruction"] is True
    json.dumps(report, allow_nan=False)


@pytest.mark.parametrize(
    "field", ["truth", "inference", "legacy", "missing_reference", "array"]
)
def test_local_tampering_fails(local, bank, field):
    report, arrays = deepcopy(local)
    envelope, refs = bank
    if field == "truth":
        report["truth"]["separation"] = 0
    elif field == "inference":
        report["records"][0]["inference"]["status"] = "two_required_in_family"
        report["records"][0]["inference"]["separation_lower"] = 9
    elif field == "legacy":
        report["records"][0]["reconstruction"]["outer"]["sampled_winding"] = 99
    elif field == "missing_reference":
        report["records"].pop()
    else:
        arrays["full_F2"][0, 0] += 1
    with pytest.raises((ValueError, KeyError)):
        kernel.verify_local(report, arrays, refs, envelope, "b" * 64)
