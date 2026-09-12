"""Deterministic development runner checks, not independent coverage trials."""

from __future__ import annotations

from collections import Counter
from copy import deepcopy
from itertools import product
import json
from pathlib import Path
import sys

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import run_p4_bounded_observation_v0_1 as runner  # noqa: E402


@pytest.fixture(scope="module")
def report():
    return runner.demo()


def reseal(report):
    report["report_seal_sha256"] = runner.kernel.SEAL(
        {key: value for key, value in report.items() if key != "report_seal_sha256"}
    )


def test_registered_plan_and_exact_paired_denominators(report):
    assert runner.sha(ROOT / runner.PROTOCOL) == runner.PROTOCOL_SHA256
    assert report["protocol_sha256"] == runner.PROTOCOL_SHA256
    assert report["record_count"] == len(report["records"]) == 1152
    expected = set(
        product(
            (0.5, 1.0),
            ("none", "constant", "linear", "shared-constant"),
            (0.0, 1e-7, 1e-5, 1e-3),
            (
                "double",
                "pair-d080",
                "pair-d160",
                "reverse-d160",
                "zero",
                "constant",
                "linear",
                "dipole",
                "cubic",
            ),
            ("F2", "F4"),
            ("bounded", "absent"),
        )
    )
    actual = [
        tuple(
            row[key]
            for key in (
                "placement",
                "mode",
                "epsilon",
                "fixture",
                "hypothesis",
                "witness_mode",
            )
        )
        for row in report["records"]
    ]
    assert len(actual) == len(set(actual)) == len(expected)
    assert set(actual) == expected
    assert len(report["observations"]) == 9 * 4 * 2 == 72
    assert set(
        Counter(row["observation_key"] for row in report["records"]).values()
    ) == {16}
    assert len(report["summary"]) == 64
    assert all(group["records"] == 18 for group in report["summary"])
    assert sum(group["records"] for group in report["summary"]) == 1152
    assert report["independent_trials"] is None
    assert report["evaluation_geometry_seeds"] == [7]
    assert report["noise_location"] == "post-adapter-moment-space"
    assert report["campaign_status"] == "not_frozen_not_run"
    assert report["scientific_authority"] is False
    assert report["calibrated_confidence_region"] is False


def test_every_absent_witness_preserves_missing_absolute_intervals(report):
    rows = [row for row in report["records"] if row["witness_mode"] == "absent"]
    assert len(rows) == 576
    for row in rows:
        assert row["budget"]["status"] == "common_mode_unidentified"
        assert row["budget"]["radii"] is None
        assert row["readout"]["status"] == "common_mode_unidentified"
        for key in (
            "coefficient_radii",
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
            assert row["readout"][key] is None, key
        assert row["score"]["center_covered"] is None
        assert row["score"]["separation_covered"] is None
        assert row["score"]["witness_bound_holds"] is None
    assert all(
        group["witness_contract_violations"] == 0
        for group in report["summary"]
        if group["witness_mode"] == "absent"
    )


def test_valid_witness_quadratic_controls_are_conditionally_covered(report):
    rows = [
        row
        for row in report["records"]
        if row["witness_mode"] == "bounded" and row["mode"] != "shared-constant"
    ]
    assert len(rows) == 432
    assert all(row["score"]["witness_bound_holds"] is True for row in rows)
    quadratics = [row for row in rows if row["score"]["truth_quadratic_family"]]
    assert len(quadratics) == 192
    for row in quadratics:
        assert row["readout"]["status"] in {
            "one_not_excluded",
            "two_required_in_family",
        }
        assert row["score"]["center_covered"] is True
        assert row["score"]["separation_covered"] is True
        assert row["score"]["single_false_two"] is False
        assert row["readout"]["scientific_authority"] is False
        assert row["readout"]["global_family_verified"] is False
    singles = [row for row in quadratics if row["fixture"] == "double"]
    assert len(singles) == 48
    assert all(row["readout"]["status"] == "one_not_excluded" for row in singles)


def test_shared_bias_contract_violations_are_retained_not_pooled_as_valid(report):
    shared = [
        row
        for row in report["records"]
        if row["witness_mode"] == "bounded" and row["mode"] == "shared-constant"
    ]
    assert len(shared) == 144
    assert all(row["score"]["witness_bound_holds"] is False for row in shared)
    assert any(row["score"]["single_false_two"] is True for row in shared)
    assert any(row["score"]["separation_covered"] is False for row in shared)
    for row in shared:
        assert row["budget"]["witness_independent_declared"] is True
        assert row["budget"]["physical_independence_verified"] is False
        assert row["budget"]["shared_bias_diagnosed"] is False
        assert row["budget"]["reference_corrected"] is False
    groups = [
        group
        for group in report["summary"]
        if group["witness_mode"] == "bounded" and group["mode"] == "shared-constant"
    ]
    assert len(groups) == 8
    assert all(group["witness_contract_violations"] == 18 for group in groups)
    assert (
        sum(group["witness_contract_violations"] for group in report["summary"]) == 144
    )


def test_witness_placement_radii_follow_registered_equal_cost_operator(report):
    epsilon = runner.WITNESS_EPSILON
    for h in (0.5, 1.0):
        for hypothesis in ("F2", "F4"):
            witness = report["witnesses"][str(h)][hypothesis]
            fit = witness["fit"]
            coords = np.array(witness["coords"])
            np.testing.assert_array_equal(
                coords, runner.kernel.witness.witness_stencil(h)
            )
            expected = (
                np.abs(np.linalg.pinv(np.column_stack((np.ones(5), coords))))
                @ np.full(5, epsilon)
                + runner.kernel.witness.NUMERICAL_MARGIN
            )
            np.testing.assert_array_equal(fit["radii"], expected)
            np.testing.assert_allclose(
                fit["radii"],
                np.array([epsilon, epsilon / h, epsilon / h])
                + runner.kernel.witness.NUMERICAL_MARGIN,
                rtol=0,
                atol=1e-20,
            )
            assert fit["fit_residual_used_as_error_bound"] is False
    for hypothesis in ("F2", "F4"):
        narrow = np.array(report["witnesses"]["0.5"][hypothesis]["fit"]["radii"])
        wide = np.array(report["witnesses"]["1.0"][hypothesis]["fit"]["radii"])
        np.testing.assert_allclose(
            narrow - runner.kernel.witness.NUMERICAL_MARGIN,
            (wide - runner.kernel.witness.NUMERICAL_MARGIN) * [1.0, 2.0, 2.0],
            rtol=0,
            atol=1e-20,
        )


def test_bounded_post_adapter_draws_are_reused_not_independent(report):
    z = runner.disk_draw(25, 3)
    assert np.all(np.linalg.norm(z, axis=1) <= 1.0)
    np.testing.assert_array_equal(z, runner.disk_draw(25, 3))
    assert not np.array_equal(runner.disk_draw(5, 1), runner.disk_draw(5, 2))
    for fixture in runner.FIXTURES:
        for hypothesis in ("F2", "F4"):
            clean = report["observations"][f"{fixture}/0.0/{hypothesis}"]
            for epsilon in runner.EPSILONS:
                observed = report["observations"][f"{fixture}/{epsilon}/{hypothesis}"]
                np.testing.assert_array_equal(
                    observed["moments"], np.asarray(clean["moments"]) + epsilon * z
                )
                assert observed["point_bounds"] == [epsilon] * 25
                assert observed["clean_probe_sha256"] == clean["clean_probe_sha256"]


def test_record_inputs_readouts_and_scores_replay_without_truth_in_infer(report):
    # One example per mode, placement, witness condition, and both orientations.
    rows = [
        row
        for row in report["records"]
        if row["fixture"] in ("double", "reverse-d160") and row["epsilon"] == 1e-5
    ]
    assert len(rows) == 64
    for row in rows:
        observed = report["observations"][row["observation_key"]]
        assert runner.kernel.verify_readout(
            row["readout"],
            observed["moments"],
            row["reference"],
            row["budget"],
            observed["point_bounds"],
        )
        assert row["score"]["truth_read_after_inference"] is True
        assert "truth" not in row["budget"] and "truth" not in row["readout"]


def test_scoring_requires_inference_seal_before_reading_truth(report):
    class NoTruthAccess(dict):
        def __getitem__(self, key):
            raise AssertionError("truth was read before checking the inference seal")

    row = report["records"][0]
    changed = deepcopy(row["readout"])
    changed["status"] = "tampered"
    with pytest.raises(ValueError, match="before truth scoring"):
        runner.score(
            changed,
            NoTruthAccess(),
            np.asarray(row["reference"]),
            np.zeros((3, 2)),
            np.zeros(3),
            witness_consumed=True,
        )


def test_source_closure_and_full_report_replay(report):
    paths = {str(path.relative_to(ROOT)) for path in (ROOT / "src").rglob("*.py")}
    paths.update(
        str(path.relative_to(ROOT)) for path in (ROOT / "scripts").glob("*p4*.py")
    )
    paths.update((runner.PROTOCOL, "pyproject.toml"))
    assert set(report["source_sha256"]) == paths
    assert report["source_sha256"] == runner.source_lock()
    for filename, expected in report["source_sha256"].items():
        assert runner.sha(ROOT / filename) == expected
    assert runner.verify_demo(report)
    assert report["summary"] == runner.summary(report["records"])


@pytest.mark.parametrize(
    "target",
    [
        "truth",
        "score",
        "source",
        "observation",
        "readout",
        "summary",
        "scope",
        "authority_type",
        "denominator",
        "extra_key",
        "protocol",
    ],
)
def test_full_report_tamper_rejected_even_when_resealed(report, monkeypatch, target):
    changed = deepcopy(report)
    if target == "truth":
        changed["truth"]["double"]["center"][0] += 1.0
    elif target == "score":
        changed["records"][0]["score"]["center_covered"] = False
    elif target == "source":
        changed["source_sha256"][runner.PROTOCOL] = "0" * 64
    elif target == "observation":
        key = next(iter(changed["observations"]))
        changed["observations"][key]["moments"][0][0] += 1e-4
    elif target == "readout":
        changed["records"][0]["readout"]["center_radius"] += 1e-3
    elif target == "summary":
        changed["summary"][0]["records"] += 1
    elif target == "scope":
        changed["campaign_status"] = "complete"
    elif target == "authority_type":
        changed["scientific_authority"] = 0
    elif target == "denominator":
        changed["independent_trials"] = 1152
    elif target == "extra_key":
        changed["unexpected"] = True
    elif target == "protocol":
        changed["protocol_sha256"] = "0" * 64
    reseal(changed)
    # Fresh full replay is covered above; use its unchanged output here to keep
    # mutation-case tests cheap without weakening the canonical comparison.
    monkeypatch.setattr(runner, "demo", lambda: report)
    with pytest.raises(ValueError, match="does not replay"):
        runner.verify_demo(changed)


def test_changed_protocol_stops_before_any_observation(monkeypatch):
    monkeypatch.setattr(runner, "PROTOCOL_SHA256", "0" * 64)
    monkeypatch.setattr(
        runner,
        "observe_background",
        lambda *_: pytest.fail("observations must not precede protocol validation"),
    )
    with pytest.raises(ValueError, match="specification changed"):
        runner.demo()


def test_cli_existing_output_is_never_overwritten(tmp_path, monkeypatch):
    path = tmp_path / "existing.json"
    original = b'{"preserve":true}\n'
    path.write_bytes(original)
    monkeypatch.setattr(sys, "argv", ["bounded-demo", "--output", str(path)])
    monkeypatch.setattr(runner, "demo", lambda: pytest.fail("must stop before demo"))
    with pytest.raises(FileExistsError):
        runner.main()
    assert path.read_bytes() == original


def test_cli_exclusive_create_and_readonly_verification(tmp_path, monkeypatch, capsys):
    path = tmp_path / "new.json"
    minimal = {
        "record_count": 1152,
        "report_seal_sha256": "a" * 64,
        "campaign_status": "not_frozen_not_run",
    }
    monkeypatch.setattr(runner, "demo", lambda: minimal)
    monkeypatch.setattr(sys, "argv", ["bounded-demo", "--output", str(path)])
    runner.main()
    assert json.loads(path.read_text()) == minimal
    assert json.loads(capsys.readouterr().out)["records"] == 1152
    before = path.read_bytes()
    verified = []
    monkeypatch.setattr(
        runner, "verify_demo", lambda value: verified.append(value) or True
    )
    monkeypatch.setattr(sys, "argv", ["bounded-demo", "--verify", str(path)])
    runner.main()
    assert verified == [minimal]
    assert path.read_bytes() == before
    assert "replay verified" in capsys.readouterr().out


def test_cli_race_cannot_replace_existing_file(tmp_path, monkeypatch):
    path = tmp_path / "raced.json"
    original = b'{"created_by_other_writer":true}'

    def racing_demo():
        path.write_bytes(original)
        return {"record_count": 1152}

    monkeypatch.setattr(runner, "demo", racing_demo)
    monkeypatch.setattr(sys, "argv", ["bounded-demo", "--output", str(path)])
    with pytest.raises(FileExistsError):
        runner.main()
    assert path.read_bytes() == original
