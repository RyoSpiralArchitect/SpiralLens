from __future__ import annotations

import inspect
import json
import os
import subprocess
import sys
from dataclasses import replace
from itertools import combinations
from pathlib import Path

import numpy as np
import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "prototype_p4_estimand_comparison_v0_1.py"

sys.path.insert(0, str(SCRIPT_PATH.parent))
import prototype_p4_estimand_comparison_v0_1 as prototype  # noqa: E402


PATTERNS = (
    "input_identity",
    "affine_offset",
    "quadratic_excess",
    "f2_nonlinear_only",
    "f4_nonlinear_only",
    "curved_coherent",
    "no_signal",
    "collapsed_support",
    "undersampled",
)
ESTIMANDS = (
    "full",
    "pass_through",
    "local_affine",
    "residual_affine",
    "residual_pass_through",
)
PROBE_ROLES = ("plane_fit_probes", "baseline_fit_probes", "evaluation_probes")


@pytest.fixture(scope="module")
def reports() -> dict[str, dict]:
    return {
        pattern: prototype.measure_case(prototype.ComparisonSpec(pattern))
        for pattern in PATTERNS
    }


def _all_estimands(report: dict):
    yield from report["estimands"].values()
    yield report["controls"]["origin_centered"]


def _field(report: dict, estimand: str, hypothesis: str) -> dict:
    if estimand == "origin_centered":
        return report["controls"][estimand]["fields"][hypothesis]
    return report["estimands"][estimand]["fields"][hypothesis]


def _loop(report: dict, estimand: str, hypothesis: str) -> dict:
    return _field(report, estimand, hypothesis)["loops"]["outer"]["forward"]


def _assert_winding(loop: dict, expected: int) -> None:
    assert loop["state"] == "eligible", loop
    assert loop["value"]["sampled_winding"] == expected
    assert loop["value"]["unrounded_winding"] == pytest.approx(expected, abs=1e-9)
    assert loop["value"]["closure_residual"] == pytest.approx(0, abs=1e-9)


def _assert_zero_abstention(field: dict) -> None:
    np.testing.assert_allclose(field["values"], 0.0, atol=1e-10)
    np.testing.assert_allclose(field["amplitude"], 0.0, atol=1e-10)
    assert not any(field["direction_defined"])
    assert field["core"]["state"] == "insufficient"
    assert field["core"]["value"]["classification"] == "unresolved"
    assert field["core"]["value"]["candidate_count"] is None
    for directions in field["loops"].values():
        for direction in ("forward", "reverse"):
            assert directions[direction]["state"] == "insufficient"
            assert directions[direction]["value"] is None


def test_generator_is_deterministic_with_three_physically_disjoint_roles() -> None:
    spec = prototype.ComparisonSpec("quadratic_excess", seed=7, noise=0.02)
    first = prototype.make_comparison_probes(spec)
    second = prototype.make_comparison_probes(spec)
    np.testing.assert_array_equal(first.coords, second.coords)
    np.testing.assert_array_equal(first.faces, second.faces)
    for name in PROBE_ROLES:
        left, right = getattr(first, name), getattr(second, name)
        np.testing.assert_array_equal(left, right)
        assert np.isfinite(left).all()
        assert left.shape[0] == len(first.coords)
        assert left.shape[-1] == 3
    for left, right in combinations(PROBE_ROLES, 2):
        assert not np.shares_memory(getattr(first, left), getattr(first, right))


@pytest.mark.parametrize(
    "changes",
    [
        {"pattern": "unknown"},
        {"gauge": "so2-only"},
        {"side": True},
        {"side": 8},
        {"side": 10},
        {"side": 37},
        {"seed": True},
        {"seed": -1},
        {"seed": 2**32},
        {"noise": -0.1},
        {"noise": True},
        {"noise": float("nan")},
        {"noise": float("inf")},
    ],
)
def test_comparison_spec_rejects_out_of_scope_values(changes: dict) -> None:
    with pytest.raises(ValueError):
        prototype.ComparisonSpec(**({"pattern": "input_identity"} | changes))


@pytest.mark.parametrize("left,right", list(combinations(PROBE_ROLES, 2)))
def test_measurement_rejects_any_shared_probe_role_storage(
    left: str, right: str
) -> None:
    bundle = prototype.make_comparison_probes(
        prototype.ComparisonSpec("quadratic_excess")
    )
    overlapping = replace(bundle, **{right: getattr(bundle, left).view()})
    with pytest.raises(ValueError, match="disjoint|share|overlap"):
        prototype.measure_comparison(overlapping)


@pytest.mark.parametrize("role", PROBE_ROLES)
def test_measurement_rejects_nonfinite_probes_in_each_role(role: str) -> None:
    bundle = prototype.make_comparison_probes(
        prototype.ComparisonSpec("quadratic_excess")
    )
    invalid = np.array(getattr(bundle, role), copy=True)
    invalid[0, 0, 0] = np.nan
    with pytest.raises(ValueError):
        prototype.measure_comparison(replace(bundle, **{role: invalid}))


def test_fit_only_baseline_api_has_no_evaluation_or_truth_argument() -> None:
    assert tuple(inspect.signature(prototype.fit_baseline).parameters) == (
        "coords",
        "plane_fit_probes",
        "baseline_fit_probes",
        "gauge",
    )
    assert tuple(inspect.signature(prototype.measure_comparison).parameters) == (
        "bundle",
        "gauge",
    )


def test_evaluation_mutation_cannot_change_baseline_fit_or_geometry() -> None:
    bundle = prototype.make_comparison_probes(
        prototype.ComparisonSpec("quadratic_excess")
    )
    before = prototype.measure_comparison(bundle)
    erased = replace(bundle, evaluation_probes=np.zeros_like(bundle.evaluation_probes))
    after = prototype.measure_comparison(erased)
    assert before["baseline"] == after["baseline"]
    assert before["geometry"] == after["geometry"]
    for hypothesis in ("F2", "F4"):
        before_full = _field(before, "full", hypothesis)
        after_full = _field(after, "full", hypothesis)
        assert before_full["field_sha256"] != after_full["field_sha256"]
        _assert_zero_abstention(after_full)
        np.testing.assert_array_equal(
            _field(before, "local_affine", hypothesis)["values"],
            _field(after, "local_affine", hypothesis)["values"],
        )
        assert (
            _field(before, "residual_affine", hypothesis)["field_sha256"]
            != (_field(after, "residual_affine", hypothesis)["field_sha256"])
        )


def test_baseline_probe_mutation_changes_baseline_without_changing_full_fields() -> (
    None
):
    bundle = prototype.make_comparison_probes(
        prototype.ComparisonSpec("quadratic_excess")
    )
    before = prototype.measure_comparison(bundle)
    modified = 1.5 * bundle.baseline_fit_probes + np.array([0.4, -0.2, 0.0])
    after = prototype.measure_comparison(replace(bundle, baseline_fit_probes=modified))
    assert before["baseline"]["baseline_sha256"] != after["baseline"]["baseline_sha256"]
    assert before["geometry"] == after["geometry"]
    for hypothesis in ("F2", "F4"):
        before_full = _field(before, "full", hypothesis)
        after_full = _field(after, "full", hypothesis)
        np.testing.assert_array_equal(before_full["values"], after_full["values"])
        assert before_full["field_sha256"] == after_full["field_sha256"]
        assert not np.allclose(
            _field(before, "local_affine", hypothesis)["values"],
            _field(after, "local_affine", hypothesis)["values"],
        )


def test_baseline_fit_ignores_response_probes_outside_the_fixed_local_stencil() -> None:
    bundle = prototype.make_comparison_probes(
        prototype.ComparisonSpec("quadratic_excess")
    )
    before = prototype.measure_comparison(bundle)
    stencil_coordinates = {(0.0, 0.0), (0.5, 0.0), (-0.5, 0.0), (0.0, 0.5), (0.0, -0.5)}
    outside = np.array(
        [tuple(coord) not in stencil_coordinates for coord in bundle.coords]
    )
    changed = np.array(bundle.baseline_fit_probes, copy=True)
    changed[outside] = 7.0 * changed[outside] + np.array([17.0, -11.0, 0.0])
    after = prototype.measure_comparison(replace(bundle, baseline_fit_probes=changed))
    for hypothesis in ("F2", "F4"):
        np.testing.assert_array_equal(
            before["baseline"]["coefficients"][hypothesis],
            after["baseline"]["coefficients"][hypothesis],
        )
        np.testing.assert_array_equal(
            _field(before, "local_affine", hypothesis)["values"],
            _field(after, "local_affine", hypothesis)["values"],
        )


def test_f4_uses_centered_covariance_not_raw_second_moments() -> None:
    bundle = prototype.make_comparison_probes(
        prototype.ComparisonSpec("quadratic_excess")
    )
    before = prototype.measure_comparison(bundle)
    translated = bundle.evaluation_probes + np.array([3.0, -2.0, 0.0])
    after = prototype.measure_comparison(replace(bundle, evaluation_probes=translated))
    assert not np.allclose(
        _field(before, "full", "F2")["values"],
        _field(after, "full", "F2")["values"],
    )
    for estimand in ESTIMANDS:
        np.testing.assert_allclose(
            _field(before, estimand, "F4")["traceless_tensor"],
            _field(after, estimand, "F4")["traceless_tensor"],
            atol=1e-9,
        )


def test_probe_pairing_is_irrelevant_to_tensor_residual_not_covariance_of_residual_probes() -> (
    None
):
    bundle = prototype.make_comparison_probes(
        prototype.ComparisonSpec("quadratic_excess")
    )
    before = prototype.measure_comparison(bundle)
    permuted = np.array(bundle.evaluation_probes[:, ::-1, :], copy=True)
    after = prototype.measure_comparison(replace(bundle, evaluation_probes=permuted))
    for estimand in ESTIMANDS:
        for hypothesis in ("F2", "F4"):
            np.testing.assert_allclose(
                _field(before, estimand, hypothesis)["values"],
                _field(after, estimand, hypothesis)["values"],
                atol=1e-9,
            )


def test_all_comparisons_keep_both_fields_and_finite_json(
    reports: dict[str, dict],
) -> None:
    assert set(reports) == set(PATTERNS)
    for report in reports.values():
        assert set(report["estimands"]) == set(ESTIMANDS)
        assert report["co_primary_hypotheses"] == ["F2", "F4"]
        assert report["winner_selected"] is False
        for estimand in _all_estimands(report):
            assert set(estimand["fields"]) == {"F2", "F4"}
        assert json.loads(json.dumps(report, allow_nan=False, sort_keys=True)) == report


def test_each_derived_field_recomputes_same_field_amplitude_core_and_winding(
    reports: dict[str, dict],
) -> None:
    for report in reports.values():
        for estimand in _all_estimands(report):
            for hypothesis, field in estimand["fields"].items():
                assert len(field["field_sha256"]) == 64
                assert field["core"]["field_sha256"] == field["field_sha256"]
                for directions in field["loops"].values():
                    for direction in ("forward", "reverse"):
                        assert (
                            directions[direction]["field_sha256"]
                            == field["field_sha256"]
                        )
                if field["values"] is None:
                    assert field["state"] == "insufficient"
                    assert field["amplitude"] is None
                    assert field["direction_defined"] is None
                    assert field["core"]["state"] == "insufficient"
                    assert field["core"]["value"]["candidate_count"] is None
                    assert field["missing_reason"]
                    continue
                values = np.asarray(field["values"])
                amplitude = np.asarray(field["amplitude"])
                np.testing.assert_allclose(amplitude, np.linalg.norm(values, axis=1))
                np.testing.assert_array_equal(
                    field["direction_defined"], amplitude > field["amplitude_floor"]
                )
                if hypothesis == "F4":
                    tensor = np.asarray(field["traceless_tensor"])
                    np.testing.assert_allclose(
                        tensor, tensor.swapaxes(-1, -2), atol=1e-10
                    )
                    np.testing.assert_allclose(
                        np.trace(tensor, axis1=-2, axis2=-1), 0, atol=1e-10
                    )
                    np.testing.assert_allclose(
                        values,
                        np.column_stack(
                            ((tensor[:, 0, 0] - tensor[:, 1, 1]) / 2, tensor[:, 0, 1])
                        ),
                        atol=1e-10,
                    )


def test_baseline_field_and_core_hashes_reproduce_their_exact_payloads(
    reports: dict[str, dict],
) -> None:
    for report in reports.values():
        baseline = report["baseline"]
        assert baseline["baseline_sha256"] == prototype.canonical_json_sha256(
            {key: value for key, value in baseline.items() if key != "baseline_sha256"}
        )
        for estimand in _all_estimands(report):
            for field in estimand["fields"].values():
                assert field["field_sha256"] == prototype.canonical_json_sha256(
                    {
                        key: value
                        for key, value in field.items()
                        if key not in {"field_sha256", "core", "loops"}
                    }
                )
                core = field["core"]
                assert core["seal_sha256"] == prototype.canonical_json_sha256(
                    {key: value for key, value in core.items() if key != "seal_sha256"}
                )


def test_residuals_subtract_vectors_or_tensors_before_deriving_direction(
    reports: dict[str, dict],
) -> None:
    for report in reports.values():
        if report["baseline"]["state"] != "eligible":
            continue
        for residual, baseline in (
            ("residual_affine", "local_affine"),
            ("residual_pass_through", "pass_through"),
        ):
            for hypothesis in ("F2", "F4"):
                key = "values" if hypothesis == "F2" else "traceless_tensor"
                full = np.asarray(_field(report, "full", hypothesis)[key])
                base = np.asarray(_field(report, baseline, hypothesis)[key])
                observed = np.asarray(_field(report, residual, hypothesis)[key])
                np.testing.assert_allclose(observed, full - base, atol=1e-10)


def test_input_identity_winding_is_explained_without_inventing_f4_or_zero_residual_cores(
    reports: dict[str, dict],
) -> None:
    report = reports["input_identity"]
    for estimand in ("full", "pass_through", "local_affine"):
        _assert_winding(_loop(report, estimand, "F2"), 1)
        _assert_zero_abstention(_field(report, estimand, "F4"))
    for estimand in ("residual_affine", "residual_pass_through"):
        for hypothesis in ("F2", "F4"):
            _assert_zero_abstention(_field(report, estimand, hypothesis))


def test_affine_offset_exposes_origin_centering_as_an_imposed_zero(
    reports: dict[str, dict],
) -> None:
    report = reports["affine_offset"]
    for hypothesis in ("F2", "F4"):
        _assert_winding(_loop(report, "full", hypothesis), 0)
        _assert_winding(_loop(report, "origin_centered", hypothesis), 1)
        centered = _field(report, "origin_centered", hypothesis)
        assert centered["core"]["state"] == "eligible"
        assert centered["core"]["value"]["candidate_count"] == 1
        _assert_zero_abstention(_field(report, "residual_affine", hypothesis))


def test_unsupported_origin_blocks_centering_without_erasing_supported_outer_branches() -> (
    None
):
    bundle = prototype.make_comparison_probes(prototype.ComparisonSpec("affine_offset"))
    origin = int(np.flatnonzero((bundle.coords == 0).all(axis=1))[0])
    plane_probes = np.array(bundle.plane_fit_probes, copy=True)
    plane_probes[origin, :, 1] = 0.0
    report = prototype.measure_comparison(
        replace(bundle, plane_fit_probes=plane_probes)
    )

    assert report["baseline"]["state"] == "insufficient"
    assert report["geometry"]["outer"]["forward"]["state"] == "eligible"
    _assert_winding(_loop(report, "pass_through", "F2"), 1)
    for hypothesis in ("F2", "F4"):
        _assert_winding(_loop(report, "full", hypothesis), 0)
        centered = _field(report, "origin_centered", hypothesis)
        assert centered["state"] == "insufficient"
        assert centered["values"] is None
        assert centered["amplitude"] is None
        assert centered["direction_defined"] is None
        assert centered["missing_reason"] == "origin-plane-reference-insufficient"
        assert centered["core"]["state"] == "insufficient"
        assert centered["core"]["value"]["candidate_count"] is None
        for directions in centered["loops"].values():
            for branch in directions.values():
                assert branch["state"] == "insufficient"
                assert branch["value"] is None
                assert branch["reason"] == "origin-plane-reference-insufficient"


def test_unsupported_nonorigin_stencil_blocks_only_dependent_affine_fields() -> None:
    bundle = prototype.make_comparison_probes(prototype.ComparisonSpec("affine_offset"))
    stencil_row = int(np.flatnonzero((bundle.coords == [0.5, 0.0]).all(axis=1))[0])
    plane_probes = np.array(bundle.plane_fit_probes, copy=True)
    plane_probes[stencil_row, :, 1] = 0.0
    report = prototype.measure_comparison(
        replace(bundle, plane_fit_probes=plane_probes)
    )

    assert report["baseline"]["state"] == "insufficient"
    assert report["baseline"]["coefficients"] == {"F2": None, "F4": None}
    assert report["geometry"]["outer"]["forward"]["state"] == "eligible"
    _assert_winding(_loop(report, "pass_through", "F2"), 1)
    for hypothesis in ("F2", "F4"):
        _assert_winding(_loop(report, "full", hypothesis), 0)
        _assert_winding(_loop(report, "origin_centered", hypothesis), 1)
        for estimand in ("local_affine", "residual_affine"):
            field = _field(report, estimand, hypothesis)
            assert field["state"] == "insufficient"
            assert field["values"] is None
            assert field["amplitude"] is None
            assert field["direction_defined"] is None
            assert field["missing_reason"] == "baseline-unavailable-no-field-fabricated"
            for directions in field["loops"].values():
                for branch in directions.values():
                    assert branch["state"] == "insufficient"
                    assert branch["value"] is None
                    assert (
                        branch["reason"] == "baseline-unavailable-no-field-fabricated"
                    )


def test_subtracting_pass_through_can_create_winding_from_a_no_signal_full_field(
    reports: dict[str, dict],
) -> None:
    report = reports["no_signal"]
    for hypothesis in ("F2", "F4"):
        _assert_zero_abstention(_field(report, "full", hypothesis))
        _assert_zero_abstention(_field(report, "residual_affine", hypothesis))
    residual = _field(report, "residual_pass_through", "F2")
    pass_through = _field(report, "pass_through", "F2")
    np.testing.assert_allclose(
        residual["values"], -np.asarray(pass_through["values"]), atol=1e-10
    )
    _assert_winding(_loop(report, "residual_pass_through", "F2"), 1)
    _assert_zero_abstention(_field(report, "residual_pass_through", "F4"))
    assert report["claim_boundary"]["nonlinearity_proven"] is False
    assert (
        residual["parents"]["subtracted_field_sha256"] == pass_through["field_sha256"]
    )


def test_baseline_digest_is_sealed_before_evaluation_moments_are_read(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events = []
    fit, moments = prototype.fit_baseline, prototype._reference_moments

    def record_fit(*args, **kwargs):
        result = fit(*args, **kwargs)
        assert len(result["baseline_sha256"]) == 64
        events.append("baseline_sealed")
        return result

    def record_moments(frames, gauges, probes, role):
        events.append("baseline_moments" if role == 1 else "evaluation_moments")
        return moments(frames, gauges, probes, role)

    monkeypatch.setattr(prototype, "fit_baseline", record_fit)
    monkeypatch.setattr(prototype, "_reference_moments", record_moments)
    prototype.measure_case(prototype.ComparisonSpec("quadratic_excess"))
    assert events == ["baseline_moments", "baseline_sealed", "evaluation_moments"]


def test_nonlinear_residual_charge_is_not_a_difference_of_winding_integers(
    reports: dict[str, dict],
) -> None:
    report = reports["quadratic_excess"]
    for hypothesis in ("F2", "F4"):
        full = _loop(report, "full", hypothesis)
        baseline = _loop(report, "local_affine", hypothesis)
        residual = _loop(report, "residual_affine", hypothesis)
        _assert_winding(full, 1)
        _assert_winding(baseline, 1)
        _assert_winding(residual, 2)
        assert residual["value"]["sampled_winding"] != (
            full["value"]["sampled_winding"] - baseline["value"]["sampled_winding"]
        )


@pytest.mark.parametrize(
    "pattern,nonlinear,zero",
    [("f2_nonlinear_only", "F2", "F4"), ("f4_nonlinear_only", "F4", "F2")],
)
def test_one_nonlinear_field_cannot_promote_or_erase_its_coprimary_peer(
    reports: dict[str, dict], pattern: str, nonlinear: str, zero: str
) -> None:
    report = reports[pattern]
    _assert_winding(_loop(report, "residual_affine", nonlinear), 2)
    _assert_zero_abstention(_field(report, "residual_affine", zero))


def test_pass_through_f4_is_isotropic_even_on_curved_fitted_planes(
    reports: dict[str, dict],
) -> None:
    for report in reports.values():
        np.testing.assert_allclose(
            _field(report, "pass_through", "F4")["values"], 0, atol=1e-10
        )
    report = reports["curved_coherent"]
    geometry = report["geometry"]["outer"]["forward"]
    assert geometry["state"] == "eligible"
    assert abs(geometry["value"]["angle_rad"]) > 1e-3


def test_collapsed_support_and_coarse_loops_abstain_instead_of_claiming_absence(
    reports: dict[str, dict],
) -> None:
    for pattern in ("collapsed_support", "undersampled"):
        for estimand in _all_estimands(reports[pattern]):
            for field in estimand["fields"].values():
                loop = field["loops"]["outer"]["forward"]
                assert loop["state"] == "insufficient"
                assert loop["value"] is None
                assert loop["reason"]


@pytest.mark.parametrize("gauge", ("local_o2", "reflection"))
@pytest.mark.parametrize(
    "pattern", ("quadratic_excess", "affine_offset", "curved_coherent")
)
def test_all_estimands_are_consistent_under_full_o2_gauge_changes(
    reports: dict[str, dict], pattern: str, gauge: str
) -> None:
    before = reports[pattern]
    after = prototype.measure_case(prototype.ComparisonSpec(pattern, gauge=gauge))
    for estimand in (*ESTIMANDS, "origin_centered"):
        for hypothesis in ("F2", "F4"):
            left, right = (
                _field(before, estimand, hypothesis),
                _field(after, estimand, hypothesis),
            )
            np.testing.assert_allclose(left["values"], right["values"], atol=1e-9)
            np.testing.assert_allclose(left["amplitude"], right["amplitude"], atol=1e-9)
            assert left["core"]["value"] == right["core"]["value"]
            for name, directions in left["loops"].items():
                for direction in ("forward", "reverse"):
                    old, new = directions[direction], right["loops"][name][direction]
                    assert old["state"] == new["state"]
                    if old["state"] == "eligible":
                        assert old["value"]["unrounded_winding"] == pytest.approx(
                            new["value"]["unrounded_winding"], abs=1e-9
                        )
    for name, directions in before["geometry"].items():
        for direction in ("forward", "reverse"):
            old, new = directions[direction], after["geometry"][name][direction]
            assert old["state"] == new["state"]
            if old["state"] == "eligible":
                assert old["value"]["angle_rad"] == pytest.approx(
                    new["value"]["angle_rad"], abs=1e-9
                )


def test_every_branch_preserves_denominators_uncertainty_and_reverse_loops(
    reports: dict[str, dict],
) -> None:
    for report in reports.values():
        for estimand in _all_estimands(report):
            for field in estimand["fields"].values():
                for key in (
                    "state",
                    "value",
                    "reason",
                    "coverage",
                    "uncertainty",
                    "strata",
                ):
                    assert key in field["core"]
                for directions in field["loops"].values():
                    forward, reverse = directions["forward"], directions["reverse"]
                    for branch in (forward, reverse):
                        for key in (
                            "state",
                            "value",
                            "reason",
                            "coverage",
                            "uncertainty",
                            "strata",
                        ):
                            assert key in branch
                    assert forward["state"] == reverse["state"]
                    if forward["state"] == "eligible":
                        assert (
                            forward["value"]["sampled_winding"]
                            == -reverse["value"]["sampled_winding"]
                        )


def test_all_twelve_charge_blind_core_seals_precede_any_winding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events = []
    core, winding = prototype.chain._core, prototype.chain._winding

    def record_core(*args, **kwargs):
        events.append("core")
        return core(*args, **kwargs)

    def record_winding(*args, **kwargs):
        events.append("winding")
        return winding(*args, **kwargs)

    monkeypatch.setattr(prototype.chain, "_core", record_core)
    monkeypatch.setattr(prototype.chain, "_winding", record_winding)
    prototype.measure_case(prototype.ComparisonSpec("quadratic_excess"))
    assert events[:12] == ["core"] * 12
    assert events.count("core") == 12
    assert events[12:] and set(events[12:]) == {"winding"}


def test_comparison_keeps_level_zero_and_unassessed_scientific_branches(
    reports: dict[str, dict],
) -> None:
    for report in reports.values():
        assert report["scope"]["model_free"] is True
        assert report["scope"]["synthetic_only"] is True
        for key in (
            "model_accessed",
            "network_accessed",
            "furnace_accessed",
            "protocol_freeze",
            "execution_authorized",
        ):
            assert report["scope"][key] is False
        assert report["claim_boundary"]["claim_ceiling"] == "level_0"
        for key in (
            "scientific_authority",
            "topology_authority",
            "semantic_authority",
            "publication_authority",
            "verified_core",
            "model_derived_order_parameter",
        ):
            assert report["claim_boundary"][key] is False
        for key in ("phase", "transition"):
            assert report[key]["state"] == "not_evaluated"
            assert report[key]["value"] is None


@pytest.mark.parametrize("flag", ("--demo", "--self-test"))
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
