from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import prototype_p4_reference_uncertainty_v0_1 as kernel  # noqa: E402
import run_p4_reference_uncertainty_v0_1 as runner  # noqa: E402


@pytest.fixture(scope="module")
def calibration():
    return kernel.calibrate(7, repeats=4, ks=(1, 4))


@pytest.fixture(scope="module")
def local(calibration):
    report, _ = calibration
    return kernel.local_unit(
        report["references"],
        "a" * 64,
        alpha=0.1,
        geometry_seed=7,
        fixture="wide",
        cells=32,
    )


def test_registered_plan_and_all_denominators():
    cases = runner.cases()
    assert runner.sha(ROOT / runner.PROTOCOL) == runner.PROTOCOL_SHA256
    assert len(cases) == 72
    assert len([c for c in cases if c["lane"] == "calibration"]) == 16
    assert len([c for c in cases if c["lane"] == "geometry"]) == 56
    assert 56 * (16 * 5 * 2 + 2) == 9072
    assert kernel.KS == (1, 4, 16, 64, 256)
    assert set(kernel.REFERENCE_SEEDS).isdisjoint(kernel.GEOMETRY_SEEDS)
    assert not set(map(tuple, kernel.FIT)) & set(map(tuple, kernel.HELDOUT))


def test_noise_prefixes_and_independent_cohorts():
    a = kernel.calibration_draws(7, 4)
    np.testing.assert_array_equal(a[:1], kernel.calibration_draws(7, 1))
    np.testing.assert_array_equal(a, kernel.calibration_draws(7, 4))
    assert not np.array_equal(a, kernel.calibration_draws(8, 4))
    assert not np.array_equal(a[0], a[1])


@pytest.mark.parametrize(
    "seed,repeats", [(True, 4), (-1, 4), (7, 0), (7, 257), (7, True)]
)
def test_invalid_calibration_draws_fail(seed, repeats):
    with pytest.raises(ValueError):
        kernel.calibration_draws(seed, repeats)


def test_background_probe_moments_are_observed_not_oracle_coefficients():
    frames = np.broadcast_to(kernel.spatial.FRAME, (len(kernel.FIT), 3, 2))
    moments = kernel.spatial.DenseMomentAdapter().moments(
        frames, kernel.background_probes(kernel.FIT)
    )
    for h in kernel.spatial.HYPOTHESES:
        np.testing.assert_allclose(moments[h], kernel.FIT, rtol=0, atol=1e-14)


def test_fitted_reference_averages_and_raw_replay(calibration):
    report, arrays = calibration
    assert kernel.verify_calibration(report, arrays)
    assert report["geometry_observed"] is False
    design = np.column_stack((np.ones(5), kernel.FIT))
    for r in report["references"]:
        h, k = r["hypothesis"], r["k"]
        np.testing.assert_array_equal(
            r["coefficients"], arrays["fits_" + h][:k].mean(axis=0)
        )
        expected = np.linalg.lstsq(
            design, arrays["moments_" + h][:k].mean(axis=0), rcond=None
        )[0]
        np.testing.assert_allclose(r["coefficients"], expected, rtol=0, atol=1e-14)


def test_f4_repeat_average_is_not_raw_probe_pooling():
    probes = np.broadcast_to(
        kernel.background_probes(kernel.FIT), (2, 5, 128, 3)
    ).copy()
    probes[0, :, :, 0] += 0.1
    probes[1, :, :, 0] -= 0.1
    values, _ = kernel.fit_repeats(probes)
    frames = np.broadcast_to(kernel.spatial.FRAME, (5, 3, 2))
    pooled = probes.transpose(1, 0, 2, 3).reshape(5, 256, 3)
    pooled_f4 = kernel.spatial.DenseMomentAdapter().moments(frames, pooled)["F4"]
    assert np.max(np.abs(values["F4"].mean(axis=0) - pooled_f4)) > 0.001


@pytest.mark.parametrize("field", ["probe", "fit", "prefix", "chronology"])
def test_calibration_tampering_is_rejected(calibration, field):
    report, arrays = deepcopy(calibration)
    if field == "probe":
        arrays["probes"][0, 0, 0, 0] += 1
    elif field == "fit":
        arrays["fits_F2"][0, 0, 0] += 1
    elif field == "prefix":
        report["references"][0]["coefficients"][0][0] += 1
    else:
        report["heldout_observed"] = True
    with pytest.raises(ValueError):
        kernel.verify_calibration(report, arrays)


def test_reference_bank_incomplete_blocks_geometry(tmp_path):
    with pytest.raises(ValueError, match="all16"):
        runner.close_bank(tmp_path, [], {})
    assert not (tmp_path / "reference-bank.json").exists()
    with pytest.raises(OSError):
        runner.load_bank(tmp_path)


def test_all_references_validate_before_any_observation(calibration, monkeypatch):
    references = calibration[0]["references"]
    events = []
    original = kernel.validate_reference
    measurement = kernel.spatial.measure

    def validate(ref):
        events.append("reference")
        return original(ref)

    def observe(*args, **kwargs):
        assert events.count("reference") == len(references)
        events.append("observation")
        return measurement(*args, **kwargs)

    monkeypatch.setattr(kernel, "validate_reference", validate)
    monkeypatch.setattr(kernel.spatial, "measure", observe)
    kernel.local_unit(
        references, "a" * 64, alpha=0.1, geometry_seed=7, fixture="wide", cells=16
    )
    assert events[: len(references)] == ["reference"] * len(references)


def test_reconstruction_replay_primary_score_and_missingness(local, calibration):
    report, arrays = local
    references = calibration[0]["references"]
    assert len(report["records"]) == 6
    assert kernel.verify_local(report, arrays, references, "a" * 64)
    for r in report["records"]:
        assert r["score"] == kernel.spatial.score(r["reconstruction"], report["truth"])
        assert r["reconstruction"]["chronology"][0] == "candidate-sealed"
    null = {"components": [], "outer": {"sampled_winding": None}}
    assert kernel.measured_shape(null)["absolute_charge_centroid"] is None
    assert kernel.measured_shape(null)["span"] is None


def test_dipole_centroid_uses_absolute_charge_not_zero_signed_sum():
    rec = {
        "components": [
            {
                "resolved_charged_component": True,
                "position": [x, 0],
                "diagnostic": {"sampled_winding": q},
            }
            for x, q in ((-0.2, 1), (0.2, -1))
        ],
        "outer": {"sampled_winding": 0},
    }
    result = kernel.measured_shape(rec)
    assert result["signed_charge_sum"] == 0
    assert result["absolute_charge_centroid"] == [0, 0]
    assert result["span"] == 0.4
    rec["components"] = rec["components"][:1]
    assert kernel.measured_shape(rec)["span"] == 0


def test_strict_secondary_does_not_replace_primary():
    rec = {
        "components": [
            {
                "id": 1,
                "resolved_charged_component": True,
                "position": [0.02, 0],
                "diagnostic": {"sampled_winding": 2},
            }
        ],
        "outer": {"sampled_winding": 2},
    }
    truth = {"centers": [[0, 0]], "charges": [2], "everywhere_degenerate": False}
    assert kernel.spatial.score(rec, truth)["exact_local_structure"]
    assert not kernel.strict_score(rec, truth)["exact_local_structure"]


@pytest.mark.parametrize("target", ["truth", "field", "reference", "join", "missing"])
def test_geometry_evidence_tampering_fails(local, calibration, target):
    report, arrays = deepcopy(local)
    if target == "truth":
        report["truth"]["centers"][0][0] += 1
    elif target == "field":
        arrays["full_F2"][0, 0] += 0.1
    elif target == "reference":
        arrays["coefficient-s7-k1-F2"][0, 0] += 1
    elif target == "join":
        report["records"][1]["reference_seal_sha256"] = "b" * 64
    else:
        report["records"].pop()
    with pytest.raises(ValueError):
        kernel.verify_local(report, arrays, calibration[0]["references"], "a" * 64)


def test_conditional_uncertainty_keeps_missing_cohorts(local):
    rows = deepcopy(local[0]["records"][:2])
    rows[1]["observable"]["absolute_charge_centroid"] = None
    rows[1]["shape_error"]["centroid_error"] = None
    result = kernel.summarize_group(rows)
    assert result["cohorts"] == 2
    assert result["center_valid"] == result["center_missing"] == 1
    assert result["centroid_error"]["valid"] == 1
    assert result["spread_is_calibrated_confidence_region"] is False


def test_constant_and_zero_truth_have_no_position_error(calibration):
    for fixture in ("constant", "zero"):
        report, _ = kernel.local_unit(
            calibration[0]["references"],
            "a" * 64,
            alpha=0.08,
            geometry_seed=7,
            fixture=fixture,
            cells=16,
        )
        for record in report["records"]:
            assert record["shape_error"]["centroid_error"] is None
            assert record["shape_error"]["span_error"] is None
        if fixture == "zero":
            ideal = report["records"][0]
            assert ideal["reconstruction"]["state"] == "globally_below_floor"
            assert ideal["observable"]["outer_winding"] is None


def test_changed_seed_prefix_and_duplicate_reference_fail(calibration):
    references = deepcopy(calibration[0]["references"])
    with pytest.raises(ValueError, match="unique"):
        kernel.local_unit(
            references + references,
            "a" * 64,
            alpha=0.1,
            geometry_seed=7,
            fixture="wide",
            cells=16,
        )
    references[0]["k"] = 16
    with pytest.raises(ValueError, match="seal"):
        kernel.local_unit(
            references, "a" * 64, alpha=0.1, geometry_seed=7, fixture="wide", cells=16
        )
