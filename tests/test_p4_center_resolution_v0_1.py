from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import sys

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import prototype_p4_center_resolution_v0_1 as k  # noqa: E402
import run_p4_center_resolution_v0_1 as runner  # noqa: E402


@pytest.fixture(scope="module")
def bank():
    # Nonregistered streams only: no seeds800..863 or geometry900..915.
    report, _ = k.base.calibrate(7, "evaluation_reference", repeats=16, ks=(16,))
    return report["references"], k.inherited_envelope(ROOT)


@pytest.fixture(scope="module")
def primary(bank):
    refs, envelope = bank
    return k.field_unit(
        refs, envelope, "b" * 64, lane="primary", alpha=0.1, geometry_seed=7
    )


def test_protocol_and_inherited_envelope_are_exact():
    assert runner.sha(ROOT / runner.PROTOCOL) == runner.PROTOCOL_SHA256
    assert runner.sha(ROOT / k.ENVELOPE_FILE) == k.ENVELOPE_SHA
    envelope = k.inherited_envelope(ROOT)
    assert envelope["seeds"] == list(range(500, 532))
    assert envelope["ks"] == [16, 256, 4096]
    assert k.base.validate_envelope(envelope)


def test_inherited_envelope_tamper_fails(tmp_path):
    p = tmp_path / k.ENVELOPE_FILE
    p.parent.mkdir()
    p.write_bytes((ROOT / k.ENVELOPE_FILE).read_bytes() + b" ")
    with pytest.raises(ValueError, match="bytes"):
        k.inherited_envelope(tmp_path)


def test_expanded_denominators_and_order():
    c = runner.cases()
    assert len(c) == 188
    assert [
        sum(r["lane"] == lane for r in c)
        for lane in ("evaluation_reference", "primary", "stress", "local")
    ] == [64, 32, 28, 64]
    assert len(k.FIXTURES) == 28 and len(k.DISTANCES) == 17
    assert k.DISTANCES == tuple(range(80, 161, 5))
    assert sum(runner.record_count(r) for r in c) == 372608
    assert sum(runner.record_count(r) for r in c if r["lane"] == "primary") == 345856
    assert 64 * 4096 * 2 == 524288
    assert c[64] == {"lane": "primary", "alpha": 0.08, "geometry_seed": 900}
    assert c[96]["lane"] == "stress" and c[124]["lane"] == "local"
    assert set(k.REFERENCE_SEEDS).isdisjoint(k.base.REFERENCE_SEEDS)
    assert set(k.GEOMETRY_SEEDS).isdisjoint(k.base.GEOMETRY_SEEDS)
    np.testing.assert_array_equal(
        k.SUPPORT, np.concatenate((k.base.FIT, k.base.HELDOUT))
    )


def test_reference_selection_is_predeclared_not_score_based():
    refs = [
        {"reference_seed": s, "k": p, "hypothesis": h}
        for s in k.REFERENCE_SEEDS
        for p in k.KS
        for h in ("F2", "F4")
    ]
    b = {"references": refs}
    assert len(runner.select_references(b, {"lane": "primary"})) == 384
    assert len(runner.select_references(b, {"lane": "stress"})) == 128
    subset = runner.select_references(b, {"lane": "local"})
    assert len(subset) == 24 and {r["reference_seed"] for r in subset} == {
        800,
        801,
        802,
        803,
    }


@pytest.mark.parametrize("fixture", k.FIXTURES)
def test_support_observation_and_numerical_inference_parity(fixture):
    truth = k.geometry(7, fixture)
    grid = k.spatial.grid_coords(256)
    indices = [np.flatnonzero(np.all(grid == p, axis=1))[0] for p in k.SUPPORT]
    probes, compact = k.observe(k.SUPPORT, truth, 0.1)
    full = k.spatial.measure(grid, k.base.injected_field(grid, truth, 0.1))
    assert probes.shape == (25, 128, 3)
    for h in ("F2", "F4"):
        np.testing.assert_array_equal(full[h][indices], compact[h])
        radii = np.array([0.0001, 0.0002, 0.0003])
        a = k.base.infer(
            grid, k.spatial.subtract(full[h], grid, k.spatial.IDEAL), radii
        )
        b = k.base.infer(
            k.SUPPORT, k.spatial.subtract(compact[h], k.SUPPORT, k.spatial.IDEAL), radii
        )
        assert k.numerical_payload(a) == k.numerical_payload(b)
        assert a["input_sha256"] != b["input_sha256"]
        assert a["readout_seal_sha256"] != b["readout_seal_sha256"]
    if fixture.startswith(("pair-", "reverse-")):
        assert truth["separation"] == int(fixture.rsplit("d", 1)[1]) / 1000
        assert np.linalg.norm(np.subtract(*truth["centers"])) == pytest.approx(
            truth["separation"]
        )


@pytest.mark.parametrize(
    "mode,kind,amount",
    [
        ("none", "none", 0),
        ("constant-bias-0.5", "constant-bias", 0.5),
        ("constant-bias-2", "constant-bias", 2),
        ("linear-bias-1", "linear-bias", 1),
        ("evaluation-noise-1e-9", "evaluation-noise", 1e-9),
        ("evaluation-noise-1e-7", "evaluation-noise", 1e-7),
        ("evaluation-noise-1e-4", "evaluation-noise", 1e-4),
    ],
)
def test_stress_parameters_have_exact_signed_exponents(mode, kind, amount):
    assert k.stress_parameters(mode) == (kind, amount)


def test_shared_bias_is_explicit_and_does_not_mutate_source():
    coefficients = k.spatial.IDEAL.copy()
    radii = np.array([0.001, 0.002, 0.003])
    biased = k.transformed_reference(coefficients, radii, "constant-bias-2")
    np.testing.assert_array_equal(coefficients, k.spatial.IDEAL)
    np.testing.assert_array_equal(biased[1:], coefficients[1:])
    assert np.linalg.norm(biased[0] - coefficients[0]) == pytest.approx(0.002)
    linear = k.transformed_reference(coefficients, radii, "linear-bias-1")
    np.testing.assert_allclose(
        np.linalg.norm(linear - coefficients, axis=1), [0, 0.002, 0.003]
    )
    np.testing.assert_array_equal(
        k.transformed_reference(coefficients, radii, "evaluation-noise-1e-4"),
        coefficients,
    )


def test_evaluation_noise_reuses_one_paired_draw_without_touching_references():
    truth = k.geometry(7, "pair-d120")
    clean, _ = k.observe(k.SUPPORT, truth, 0.1)
    a, _ = k.observe(k.SUPPORT, truth, 0.1, noise=1e-4, geometry_seed=7)
    b, _ = k.observe(k.SUPPORT, truth, 0.1, noise=1e-7, geometry_seed=7)
    c, _ = k.observe(k.SUPPORT, k.geometry(7, "zero"), 0.1, noise=1e-4, geometry_seed=7)
    z, _ = k.observe(k.SUPPORT, k.geometry(7, "zero"), 0.1)
    np.testing.assert_allclose(
        (a - clean) / 1e-4, (b - clean) / 1e-7, atol=5e-9, rtol=0
    )
    np.testing.assert_allclose(a - clean, c - z, atol=1e-15, rtol=0)
    assert not np.array_equal(
        a, k.observe(k.SUPPORT, truth, 0.1, noise=1e-4, geometry_seed=8)[0]
    )


def test_primary_record_closure_and_bound_decomposition(primary, bank):
    report, arrays = primary
    refs, envelope = bank
    assert len(report["records"]) == 28 * 4
    assert report["local_records"] == []
    assert report["columns"] == list(k.COLUMNS)
    assert report["record_seal_sha256"] == k.SEAL(report["records"])
    assert k.verify_field(
        report,
        arrays,
        refs,
        envelope,
        "b" * 64,
        {"lane": "primary", "alpha": 0.1, "geometry_seed": 7},
    )
    for row in report["records"]:
        r = dict(zip(k.COLUMNS, row, strict=True))
        if r["discriminant_radius"] is not None:
            assert r["bound_constant"] + r["bound_center_linear"] + r[
                "bound_numerical"
            ] == pytest.approx(r["discriminant_radius"], rel=1e-12, abs=1e-15)
        else:
            assert r["separation_lower"] is None and r["bound_constant"] is None


@pytest.mark.parametrize(
    "mutation", ["row", "seal", "probes", "field", "extra_array", "source_coefficient"]
)
def test_tampered_compact_or_raw_evidence_fails(primary, bank, mutation):
    report, arrays = deepcopy(primary)
    refs, envelope = bank
    if mutation == "row":
        report["records"][0][k.COL["status"]] = "zero_compatible"
    elif mutation == "seal":
        report["record_seal_sha256"] = "0" * 64
    elif mutation == "probes":
        arrays["probes-0"][0, 0, 0] += 1e-4
    elif mutation == "field":
        arrays["field-0-F2"][0, 0] += 1e-4
    elif mutation == "extra_array":
        arrays["unexpected"] = np.array([1])
    else:
        arrays["coefficients"][0, 0, 0] += 1e-4
    with pytest.raises(ValueError):
        k.verify_field(
            report,
            arrays,
            refs,
            envelope,
            "b" * 64,
            {"lane": "primary", "alpha": 0.1, "geometry_seed": 7},
        )


@pytest.mark.parametrize("mode", k.STRESSES)
def test_stress_remains_separate_with_all_outcomes(bank, mode):
    refs, envelope = bank
    report, arrays = k.field_unit(
        refs, envelope, "b" * 64, lane="stress", alpha=0.1, geometry_seed=7, stress=mode
    )
    assert len(report["records"]) == 14
    assert all(r[k.COL["reference_seed"]] is not None for r in report["records"])
    assert report["local_records"] == [] and report["stress"] == mode
    assert k.verify_field(
        report,
        arrays,
        refs,
        envelope,
        "b" * 64,
        {"lane": "stress", "alpha": 0.1, "geometry_seed": 7, "stress": mode},
    )
    if mode == "evaluation-noise-1e-4":
        assert {r[k.COL["status"]] for r in report["records"]} == {"out_of_family"}
        assert all(r[k.COL["separation_lower"]] is None for r in report["records"])


def test_local_reader_is_a_paired_subset_without_regrading(bank):
    refs, envelope = bank
    case = {"lane": "local", "alpha": 0.1, "geometry_seed": 7, "fixture": "pair-d080"}
    report, arrays = k.field_unit(refs, envelope, "b" * 64, **case)
    assert len(report["records"]) == len(report["local_records"]) == 4
    for compact, local in zip(report["records"], report["local_records"], strict=True):
        assert (
            compact[k.COL["separation_lower"]] == local["inference"]["separation_lower"]
        )
        assert local["legacy_secondary_score"]["match_tolerance"] == 0.01
        assert (
            local["inference"]["readout_seal_sha256"]
            != compact[k.COL["readout_seal_sha256"]]
        )
    assert k.verify_field(report, arrays, refs, envelope, "b" * 64, case)


def test_lanes_fail_closed_on_unregistered_or_leaked_inputs(bank):
    refs, envelope = bank
    for kwargs in (
        {"lane": "primary", "stress": "constant-bias-1"},
        {"lane": "stress"},
        {"lane": "local", "fixture": "cubic"},
        {"lane": "unknown"},
    ):
        with pytest.raises(ValueError):
            k.field_unit(refs, envelope, "b" * 64, alpha=0.1, geometry_seed=7, **kwargs)
    with pytest.raises(ValueError):
        k.stress_parameters("evaluation-noise-1e-3")
    with pytest.raises(ValueError):
        k.choices([], envelope, "none", ideals=True)
    with pytest.raises(ValueError):
        k.choices(refs + refs, envelope, "none", ideals=False)
    with pytest.raises(ValueError):
        k.choices(refs, envelope, "constant-bias-1", ideals=True)


def test_incomplete_or_reordered_reference_bank_blocks_geometry(tmp_path):
    with pytest.raises(ValueError, match="64"):
        runner.close_references(tmp_path, [])
    with pytest.raises(ValueError, match="64"):
        runner.reference_reports(tmp_path, [{"index": i} for i in reversed(range(64))])
    assert not (tmp_path / "reference-bank.json").exists()


def test_bank_seal_and_plan_binding_are_checked(tmp_path):
    runner.write(tmp_path / "plan.json", {"fixture": "nonmeasurement"})
    runner.write(tmp_path / "reference-bank.json", {"file_seal_sha256": "0" * 64})
    with pytest.raises(ValueError, match="sealed"):
        runner.load_references(tmp_path)


def test_source_manifest_detects_condition_and_envelope_mutation():
    plan = {
        "source_sha256": runner.source_lock(),
        "protocol_sha256": runner.PROTOCOL_SHA256,
        "inherited_envelope_sha256": k.ENVELOPE_SHA,
        "cases": runner.cases(),
    }
    runner.assert_source(plan)
    plan["inherited_envelope_sha256"] = "0" * 64
    with pytest.raises(ValueError):
        runner.assert_source(plan)


def test_bootstrap_keeps_two_cohort_axes_and_fixed_draws():
    weights = k.bootstrap_weights()
    assert weights[0].shape == (2000, 64) and weights[1].shape == (2000, 16)
    for a, b in zip(weights, k.bootstrap_weights(), strict=True):
        np.testing.assert_array_equal(a, b)
        np.testing.assert_array_equal(a.sum(axis=1), np.ones(2000))
    for value in (0, 1):
        result = k.decision_band(np.full((16, 64), value), weights)
        assert result["fraction"] == result["q05"] == result["q95"] == value
    x = np.tile(np.arange(64) % 2, (16, 1))
    result = k.decision_band(x, weights)
    assert result["q05"] < result["fraction"] == 0.5 < result["q95"]
    assert result["reference_fractions"] == (np.arange(64) % 2).tolist()
    assert result["geometry_fractions"] == [0.5] * 16
    assert result["calibrated_confidence_band"] is False
    with pytest.raises(ValueError):
        k.decision_band(np.full((16, 64), np.nan), weights)
    with pytest.raises(ValueError):
        k.decision_band(np.zeros((64, 16)), weights)
    with pytest.raises(ValueError):
        k.bootstrap_weights(0)


def test_report_serialization_stays_finite_and_non_authoritative(primary):
    report, _ = primary
    json.dumps(report, allow_nan=False)
    assert report["scientific_authority"] is False
    assert report["graph_admission_inherited"] is False
