from __future__ import annotations

import inspect
import json
import os
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "prototype_p4_partial_patterns_v0_1.py"

sys.path.insert(0, str(SCRIPT_PATH.parent))
import prototype_p4_partial_patterns_v0_1 as prototype  # noqa: E402


PATTERNS = (
    "f2_only",
    "f4_only",
    "coherent",
    "core_depression",
    "holonomy_only",
    "flat_defect",
    "dipole",
    "smooth_drift",
    "pure_gauge",
    "zero",
    "collapsed_support",
    "undersampled",
)


@pytest.fixture(scope="module")
def reports() -> dict[str, dict[str, object]]:
    return {
        pattern: prototype.measure_case(prototype.CaseSpec(pattern))
        for pattern in PATTERNS
    }


@pytest.fixture(scope="module")
def development_report() -> dict[str, object]:
    return prototype.run_development_demo()


def test_probe_generation_is_deterministic_and_uses_separate_arrays() -> None:
    spec = prototype.CaseSpec("coherent", seed=7)
    first = prototype.make_probes(spec)
    second = prototype.make_probes(spec)

    assert first.coords.shape == (spec.side * spec.side, 2)
    for key in ("coords", "fit_probes", "evaluation_probes"):
        left, right = getattr(first, key), getattr(second, key)
        np.testing.assert_array_equal(left, right)
        assert np.isfinite(left).all()
        assert left.shape[0] == spec.side * spec.side
    assert not np.shares_memory(first.fit_probes, first.evaluation_probes)


@pytest.mark.parametrize(
    "changes",
    [
        {"pattern": "not-a-development-pattern"},
        {"gauge": "so2-only-unknown"},
        {"side": True},
        {"side": 8},
        {"side": 10},
        {"side": 37},
        {"seed": True},
        {"seed": -1},
        {"seed": 2**32},
        {"amplitude": -0.1},
        {"amplitude": float("nan")},
        {"amplitude": float("inf")},
        {"amplitude": True},
        {"noise": -0.1},
        {"noise": float("nan")},
        {"noise": float("inf")},
        {"noise": True},
    ],
)
def test_development_case_spec_rejects_out_of_scope_inputs(changes: dict) -> None:
    with pytest.raises(ValueError):
        prototype.CaseSpec(**({"pattern": "coherent"} | changes))


@pytest.mark.parametrize(
    "probes",
    [
        np.zeros((4, 3)),
        np.zeros((4, 3, 3)),
        np.zeros((4, 8, 2)),
        np.full((4, 8, 3), np.nan),
        np.full((4, 8, 3), np.inf),
    ],
)
def test_frame_fit_rejects_malformed_or_nonfinite_probe_layout(
    probes: np.ndarray,
) -> None:
    with pytest.raises(ValueError):
        prototype.fit_frames(probes)


def test_fitted_frames_have_no_evaluation_probe_input() -> None:
    assert tuple(inspect.signature(prototype.fit_frames).parameters) == ("fit_probes",)
    bundle = prototype.make_probes(prototype.CaseSpec("coherent"))
    frames, support = prototype.fit_frames(bundle.fit_probes)
    modified_evaluation = np.array(bundle.evaluation_probes, copy=True)
    modified_evaluation[...] = 1.0e6
    frames_again, support_again = prototype.fit_frames(bundle.fit_probes)

    np.testing.assert_array_equal(frames_again, frames)
    np.testing.assert_array_equal(support_again, support)
    assert frames.shape[0] == bundle.coords.shape[0]
    assert frames.shape[-1] == 2
    assert np.isfinite(frames).all()


def test_all_cases_produce_finite_json(
    reports: dict[str, dict[str, object]],
) -> None:
    assert set(reports) == set(PATTERNS)
    for report in reports.values():
        encoded = json.dumps(report, allow_nan=False, sort_keys=True)
        assert json.loads(encoded) == report


def _loop(report: dict[str, object], field: str, name: str = "outer") -> dict:
    return report["fields"][field]["loops"][name]["forward"]


def _assert_winding(loop: dict, value: int) -> None:
    assert loop["state"] == "eligible", loop
    assert loop["value"]["sampled_winding"] == value
    assert loop["value"]["unrounded_winding"] == pytest.approx(value, abs=1e-10)
    assert loop["value"]["closure_residual"] == pytest.approx(0.0, abs=1e-10)


def test_cases_preserve_coprimary_fields_and_nonpromotion(
    reports: dict[str, dict[str, object]],
) -> None:
    for report in reports.values():
        assert set(report["fields"]) == {"F2", "F4"}
        scope = report["scope"]
        assert scope["synthetic_only"] is True
        assert scope["model_free"] is True
        for key in (
            "model_accessed",
            "network_accessed",
            "furnace_accessed",
            "protocol_freeze",
            "execution_authorized",
        ):
            assert scope[key] is False
        claim = report["claim_boundary"]
        assert claim["claim_ceiling"] == "level_0"
        for key in (
            "scientific_authority",
            "topology_authority",
            "semantic_authority",
            "publication_authority",
            "verified_core",
            "model_derived_order_parameter",
        ):
            assert claim[key] is False


def test_field_amplitude_and_direction_are_bound_to_same_numeric_values(
    reports: dict[str, dict[str, object]],
) -> None:
    for report in reports.values():
        for field in report["fields"].values():
            values = np.asarray(field["values"])
            amplitude = np.asarray(field["amplitude"])
            defined = np.asarray(field["direction_defined"], dtype=bool)
            assert values.shape[1] == 2
            assert amplitude.shape == defined.shape == (values.shape[0],)
            np.testing.assert_allclose(amplitude, np.linalg.norm(values, axis=1))
            np.testing.assert_array_equal(defined, amplitude > field["amplitude_floor"])
            assert not defined[amplitude == 0.0].any()
            assert isinstance(field["field_sha256"], str)
            assert len(field["field_sha256"]) == 64
            assert field["core"]["field_sha256"] == field["field_sha256"]
            for directions in field["loops"].values():
                for direction in ("forward", "reverse"):
                    assert (
                        directions[direction]["field_sha256"] == field["field_sha256"]
                    )


@pytest.mark.parametrize(
    ("pattern", "eligible_field", "zero_field"),
    [
        ("f2_only", "F2", "F4"),
        ("f4_only", "F4", "F2"),
    ],
)
def test_one_supported_field_does_not_promote_or_erase_the_other(
    reports: dict[str, dict[str, object]],
    pattern: str,
    eligible_field: str,
    zero_field: str,
) -> None:
    report = reports[pattern]
    _assert_winding(_loop(report, eligible_field), 1)
    assert _loop(report, zero_field)["state"] == "insufficient"
    assert report["fields"][zero_field]["core"]["state"] == "insufficient"
    assert report["fields"][zero_field]["core"]["value"]["classification"] == (
        "unresolved"
    )
    assert report["geometry"]["outer"]["forward"]["state"] == "eligible"


@pytest.mark.parametrize("pattern", ["coherent", "smooth_drift", "pure_gauge"])
def test_coherent_and_smooth_gauge_patterns_are_not_defects(
    reports: dict[str, dict[str, object]],
    pattern: str,
) -> None:
    report = reports[pattern]
    for field in ("F2", "F4"):
        _assert_winding(_loop(report, field), 0)
        core = report["fields"][field]["core"]
        assert core["state"] == "eligible"
        assert core["value"]["classification"] == "zero"
        assert core["value"]["candidate_count"] == 0
    geometry = report["geometry"]["outer"]["forward"]
    assert geometry["state"] == "eligible"
    assert geometry["value"]["angle_rad"] == pytest.approx(0.0, abs=1e-10)


def test_core_depression_is_not_silently_promoted_to_winding(
    reports: dict[str, dict[str, object]],
) -> None:
    report = reports["core_depression"]
    for field in ("F2", "F4"):
        core = report["fields"][field]["core"]
        assert core["state"] == "eligible"
        assert core["value"]["classification"] == "one"
        assert core["value"]["candidate_count"] == 1
        _assert_winding(_loop(report, field), 0)


def test_flat_defect_is_distinct_from_connection_curvature(
    reports: dict[str, dict[str, object]],
) -> None:
    report = reports["flat_defect"]
    for field in ("F2", "F4"):
        _assert_winding(_loop(report, field), 1)
        core = report["fields"][field]["core"]
        assert core["state"] == "eligible"
        assert core["value"]["candidate_count"] == 1
    geometry = report["geometry"]["outer"]["forward"]
    assert geometry["state"] == "eligible"
    assert geometry["value"]["angle_rad"] == pytest.approx(0.0, abs=1e-10)


def test_holonomy_does_not_require_a_field_core_or_defect(
    reports: dict[str, dict[str, object]],
) -> None:
    report = reports["holonomy_only"]
    geometry = report["geometry"]["outer"]["forward"]
    assert geometry["state"] == "eligible"
    assert abs(geometry["value"]["angle_rad"]) > 1e-3
    for field in ("F2", "F4"):
        _assert_winding(_loop(report, field), 0)
        core = report["fields"][field]["core"]
        assert core["state"] == "eligible"
        assert core["value"]["candidate_count"] == 0


def test_dipole_preserves_local_opposite_signs_and_outer_cancellation(
    reports: dict[str, dict[str, object]],
) -> None:
    report = reports["dipole"]
    for field in ("F2", "F4"):
        _assert_winding(_loop(report, field, "outer"), 0)
        _assert_winding(_loop(report, field, "local_positive"), 1)
        _assert_winding(_loop(report, field, "local_negative"), -1)
        core = report["fields"][field]["core"]
        assert core["state"] == "eligible"
        assert core["value"]["classification"] == "many"
        assert core["value"]["candidate_count"] == 2


def test_zero_field_abstains_without_erasing_flat_geometry(
    reports: dict[str, dict[str, object]],
) -> None:
    report = reports["zero"]
    for field in report["fields"].values():
        assert field["core"]["state"] == "insufficient"
        assert field["core"]["value"]["classification"] == "unresolved"
        assert field["core"]["value"]["candidate_count"] is None
        for directions in field["loops"].values():
            assert directions["forward"]["state"] == "insufficient"
            assert directions["reverse"]["state"] == "insufficient"
    geometry = report["geometry"]["outer"]["forward"]
    assert geometry["state"] == "eligible"
    assert geometry["value"]["angle_rad"] == pytest.approx(0.0, abs=1e-10)


def test_collapsed_support_and_undersampling_abstain_not_absence(
    reports: dict[str, dict[str, object]],
) -> None:
    for pattern in ("collapsed_support", "undersampled"):
        report = reports[pattern]
        for field in ("F2", "F4"):
            loop = _loop(report, field)
            assert loop["state"] == "insufficient"
            assert loop["value"] is None
            assert loop["reason"]
    report = reports["collapsed_support"]
    assert report["geometry"]["outer"]["forward"]["state"] == "insufficient"
    for field in report["fields"].values():
        assert field["core"]["state"] == "insufficient"


def test_every_branch_retains_coverage_uncertainty_and_reason(
    reports: dict[str, dict[str, object]],
) -> None:
    for report in reports.values():
        branches = list(report["geometry"].values())
        for field in report["fields"].values():
            branches += list(field["loops"].values())
            core = field["core"]
            for key in (
                "state",
                "value",
                "reason",
                "coverage",
                "uncertainty",
                "strata",
            ):
                assert key in core
        for directions in branches:
            for direction in ("forward", "reverse"):
                branch = directions[direction]
                for key in (
                    "state",
                    "value",
                    "reason",
                    "coverage",
                    "uncertainty",
                    "strata",
                ):
                    assert key in branch


def test_reverse_loops_negate_eligible_geometry_and_winding(
    reports: dict[str, dict[str, object]],
) -> None:
    for report in reports.values():
        for directions in report["geometry"].values():
            forward, reverse = directions["forward"], directions["reverse"]
            assert forward["state"] == reverse["state"]
            if forward["state"] == "eligible":
                assert forward["value"]["angle_rad"] == pytest.approx(
                    -reverse["value"]["angle_rad"], abs=1e-10
                )
        for field in report["fields"].values():
            for directions in field["loops"].values():
                forward, reverse = directions["forward"], directions["reverse"]
                assert forward["state"] == reverse["state"]
                if forward["state"] == "eligible":
                    assert forward["value"]["sampled_winding"] == (
                        -reverse["value"]["sampled_winding"]
                    )
                    assert forward["value"]["unrounded_winding"] == pytest.approx(
                        -reverse["value"]["unrounded_winding"], abs=1e-10
                    )


@pytest.mark.parametrize("gauge", ["local_o2", "reflection"])
@pytest.mark.parametrize("pattern", ["flat_defect", "dipole", "holonomy_only"])
def test_reference_oriented_measurements_are_full_o2_gauge_invariant(
    reports: dict[str, dict[str, object]],
    gauge: str,
    pattern: str,
) -> None:
    baseline = reports[pattern]
    transformed = prototype.measure_case(prototype.CaseSpec(pattern, gauge=gauge))
    for name, directions in baseline["geometry"].items():
        other = transformed["geometry"][name]
        for direction in ("forward", "reverse"):
            assert other[direction]["state"] == directions[direction]["state"]
            if directions[direction]["state"] == "eligible":
                assert other[direction]["value"]["angle_rad"] == pytest.approx(
                    directions[direction]["value"]["angle_rad"], abs=1e-10
                )
    for field in ("F2", "F4"):
        left, right = baseline["fields"][field], transformed["fields"][field]
        np.testing.assert_allclose(left["values"], right["values"], atol=1e-10)
        np.testing.assert_allclose(left["amplitude"], right["amplitude"], atol=1e-10)
        assert left["core"]["value"] == right["core"]["value"]
        for name, directions in left["loops"].items():
            for direction in ("forward", "reverse"):
                before, after = directions[direction], right["loops"][name][direction]
                assert before["state"] == after["state"]
                if before["state"] == "eligible":
                    assert (
                        before["value"]["sampled_winding"]
                        == (after["value"]["sampled_winding"])
                    )
                    assert before["value"]["unrounded_winding"] == pytest.approx(
                        after["value"]["unrounded_winding"], abs=1e-10
                    )


def test_evaluation_mutation_changes_both_fields_but_not_fitted_geometry() -> None:
    bundle = prototype.make_probes(prototype.CaseSpec("holonomy_only"))
    baseline = prototype.measure_probes(bundle)
    erased = replace(bundle, evaluation_probes=np.zeros_like(bundle.evaluation_probes))
    changed = prototype.measure_probes(erased)

    assert changed["geometry"] == baseline["geometry"]
    for field in ("F2", "F4"):
        before, after = baseline["fields"][field], changed["fields"][field]
        assert before["field_sha256"] != after["field_sha256"]
        np.testing.assert_allclose(after["values"], 0.0, atol=1e-10)
        np.testing.assert_allclose(after["amplitude"], 0.0, atol=1e-10)
        assert after["core"]["state"] == "insufficient"
        assert after["core"]["value"]["classification"] == "unresolved"
        assert _loop(changed, field)["state"] == "insufficient"


def test_measurement_entry_point_has_no_pattern_or_truth_input() -> None:
    assert tuple(inspect.signature(prototype.measure_probes).parameters) == (
        "bundle",
        "gauge",
    )


def test_measurement_rejects_shared_fit_evaluation_storage() -> None:
    bundle = prototype.make_probes(prototype.CaseSpec("coherent"))
    with pytest.raises(ValueError, match="disjoint|share|overlap"):
        prototype.measure_probes(replace(bundle, evaluation_probes=bundle.fit_probes))


def test_core_seals_for_both_fields_precede_any_winding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events = []
    core, winding = prototype._core, prototype._winding

    def record_core(*args, **kwargs):
        events.append("core")
        return core(*args, **kwargs)

    def record_winding(*args, **kwargs):
        events.append("winding")
        return winding(*args, **kwargs)

    monkeypatch.setattr(prototype, "_core", record_core)
    monkeypatch.setattr(prototype, "_winding", record_winding)
    prototype.measure_case(prototype.CaseSpec("flat_defect"))
    assert events[:2] == ["core", "core"]
    assert events.count("core") == 2
    assert events[2:] and set(events[2:]) == {"winding"}


def test_unimplemented_estimands_remain_explicitly_not_evaluated(
    reports: dict[str, dict[str, object]],
) -> None:
    for report in reports.values():
        assert report["provenance"]["external_probe_provenance_verified"] is False
        for key in ("phase", "transition", "residual_estimands"):
            assert report[key]["state"] == "not_evaluated"
            assert report[key]["value"] is None


def test_development_surface_retains_denominators_and_abstentions(
    development_report: dict[str, object],
) -> None:
    assert development_report["status"] == "development_only_not_qualification"
    assert development_report["threshold_transfer_authorized"] is False
    rows = development_report["surface"]
    assert len(rows) == 32
    assert {row["hypothesis"] for row in rows} == {"F2", "F4"}
    assert (
        len(
            {
                tuple(
                    row[key]
                    for key in ("pattern", "hypothesis", "amplitude", "noise", "side")
                )
                for row in rows
            }
        )
        == 32
    )
    for row in rows:
        assert row["eligible_count"] + row["abstention_count"] == row["seed_count"]
        assert row["coverage"] == row["eligible_count"] / row["seed_count"]
        assert 0 <= row["detected_count"] <= row["eligible_count"]
        assert row["qualified_detection_limit"] is False
        if row["noise"] == 0:
            assert row["conditional_wilson_95"] is None
        if row["eligible_count"] == 0:
            assert row["conditional_detection_rate"] is None
            assert row["conditional_false_positive_rate"] is None
        else:
            assert (
                row["conditional_detection_rate"]
                == row["detected_count"] / row["eligible_count"]
            )
        if row["pattern"] != "coherent":
            assert row["conditional_false_positive_rate"] is None
        if row["side"] == 9:
            assert row["eligible_count"] == 0


def test_demo_is_deterministic_finite_json(
    development_report: dict[str, object],
) -> None:
    assert prototype.run_development_demo() == development_report
    json.dumps(development_report, allow_nan=False, sort_keys=True)


@pytest.mark.parametrize("flag", ["--demo", "--self-test"])
def test_cli_emits_finite_json_without_persistent_outputs(
    tmp_path: Path, flag: str
) -> None:
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONPATH"] = str(ROOT / "src")
    completed = subprocess.run(
        [sys.executable, "-B", str(SCRIPT_PATH), flag],
        cwd=tmp_path,
        env=env,
        text=True,
        capture_output=True,
        check=False,
        timeout=120,
    )
    assert completed.returncode == 0, completed.stderr
    result = json.loads(completed.stdout)
    json.dumps(result, allow_nan=False, sort_keys=True)
    assert list(tmp_path.iterdir()) == []
