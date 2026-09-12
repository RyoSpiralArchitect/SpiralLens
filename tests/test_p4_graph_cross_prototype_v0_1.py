from __future__ import annotations

import inspect
import json
import os
import subprocess
import sys
from dataclasses import replace
from itertools import combinations, product
from pathlib import Path

import numpy as np
import pytest

from spirallens.graphs.common import GraphPurpose


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "prototype_p4_graph_cross_v0_1.py"

sys.path.insert(0, str(SCRIPT_PATH.parent))
import prototype_p4_graph_cross_v0_1 as prototype  # noqa: E402


FAMILIES = ("mutual-knn", "fixed-radius", "shared-neighbor")
ESTIMANDS = (
    "full",
    "pass_through",
    "local_affine",
    "residual_affine",
    "residual_pass_through",
)


@pytest.fixture(scope="module")
def reports() -> dict[str, dict]:
    return {
        pattern: prototype.measure_case(prototype.GraphCrossSpec(pattern=pattern))
        for pattern in (
            "input_identity",
            "quadratic_excess",
            "no_signal",
            "collapsed_support",
            "collapsed_substrate",
        )
    }


@pytest.fixture(scope="module")
def curved_report() -> dict:
    return prototype.measure_case(
        prototype.GraphCrossSpec(pattern="curved_coherent", probe_noise=0.03, seed=7)
    )


def _row_field(report: dict, family: str, estimand: str, hypothesis: str) -> dict:
    row = report["rows"][family]
    branch = row["controls"] if estimand == "origin_centered" else row["estimands"]
    return branch[estimand]["fields"][hypothesis]


def _cell_field(cell: dict, estimand: str, hypothesis: str) -> dict:
    branch = cell["controls"] if estimand == "origin_centered" else cell["estimands"]
    return branch[estimand]["fields"][hypothesis]


def _loop(cell: dict, estimand: str, hypothesis: str) -> dict:
    return _cell_field(cell, estimand, hypothesis)["loops"]["outer"]["forward"]


def _assert_winding(branch: dict, expected: int) -> None:
    assert branch["state"] == "eligible", branch
    assert branch["value"]["sampled_winding"] == expected
    assert branch["value"]["unrounded_winding"] == pytest.approx(expected, abs=1e-9)


def _centered_covariance(probes: np.ndarray) -> np.ndarray:
    centered = probes - probes.mean(axis=1, keepdims=True)
    return np.einsum("npi,npj->nij", centered, centered) / probes.shape[1]


@pytest.mark.parametrize(
    "changes",
    [
        {"pattern": "not-a-development-pattern"},
        {"side": True},
        {"side": 8},
        {"side": 10},
        {"side": 13},
        {"side": 37},
        {"seed": True},
        {"seed": -1},
        {"seed": 2**32},
        {"gauge": "so2-only"},
        {"probe_noise": -0.1},
        {"probe_noise": True},
        {"probe_noise": float("nan")},
        {"probe_noise": float("inf")},
        {"graph_noise": -0.1},
        {"graph_noise": True},
        {"graph_noise": float("nan")},
        {"graph_noise": float("inf")},
        {"warp": True},
        {"warp": float("nan")},
        {"warp": float("inf")},
    ],
)
def test_graph_cross_spec_rejects_out_of_scope_inputs(changes: dict) -> None:
    with pytest.raises(ValueError):
        prototype.GraphCrossSpec(**({"pattern": "quadratic_excess"} | changes))


def test_generator_is_deterministic_and_preserves_disjoint_probe_roles() -> None:
    spec = prototype.GraphCrossSpec(
        pattern="curved_coherent", graph_noise=0.01, probe_noise=0.02, seed=7
    )
    before, after = (
        prototype.make_graph_cross_probes(spec),
        prototype.make_graph_cross_probes(spec),
    )
    np.testing.assert_array_equal(before.graph_input.states, after.graph_input.states)
    np.testing.assert_array_equal(
        before.graph_input.vertex_ids, after.graph_input.vertex_ids
    )
    roles = ("plane_fit_probes", "baseline_fit_probes", "evaluation_probes")
    for role in roles:
        np.testing.assert_array_equal(
            getattr(before.observations, role), getattr(after.observations, role)
        )
    for left, right in combinations(roles, 2):
        assert not np.shares_memory(
            getattr(before.observations, left), getattr(before.observations, right)
        )
    assert not np.shares_memory(
        before.graph_input.states, before.observations.evaluation_probes
    )


def test_graph_construction_api_cannot_receive_outcomes_or_choose_a_winner() -> None:
    assert tuple(inspect.signature(prototype.build_graphs).parameters) == (
        "graph_input",
        "purpose",
    )
    assert tuple(inspect.signature(prototype.prepare_field_graph).parameters) == (
        "observations",
        "graph",
    )


def test_graph_families_have_real_edge_diversity_and_fixed_purpose_independent_edges() -> (
    None
):
    bundle = prototype.make_graph_cross_probes(prototype.GraphCrossSpec())
    field_graphs, _ = prototype.build_graphs(
        bundle.graph_input, GraphPurpose.FIELD_ESTIMATION
    )
    loop_graphs, _ = prototype.build_graphs(
        bundle.graph_input, GraphPurpose.CYCLE_CONSTRUCTION
    )
    assert set(field_graphs) == set(loop_graphs) == set(FAMILIES)
    edge_sets = []
    for family in FAMILIES:
        graph = field_graphs[family]
        assert graph is not None
        assert loop_graphs[family] is not None
        np.testing.assert_array_equal(
            graph.canonical_edges, loop_graphs[family].canonical_edges
        )
        edge_sets.append(set(map(tuple, graph.canonical_edges.tolist())))
    for left, right in combinations(edge_sets, 2):
        assert left and right
        assert left != right
        assert len(left & right) < len(left | right)


def test_field_graph_pooling_reproduces_neighbor_centered_covariances_not_labels() -> (
    None
):
    bundle = prototype.make_graph_cross_probes(
        prototype.GraphCrossSpec(pattern="curved_coherent", probe_noise=0.02, seed=7)
    )
    graphs, _ = prototype.build_graphs(
        bundle.graph_input, GraphPurpose.FIELD_ESTIMATION
    )
    original_covariance = _centered_covariance(bundle.observations.plane_fit_probes)
    pooled_covariances = []
    for graph in graphs.values():
        assert graph is not None
        carrier, _ = prototype.prepare_field_graph(bundle.observations, graph)
        pooled = _centered_covariance(carrier.plane_fit_probes)
        assert not np.shares_memory(
            carrier.plane_fit_probes, bundle.observations.plane_fit_probes
        )
        for row in range(len(bundle.observations.coords)):
            incident = graph.canonical_edges[
                np.any(graph.canonical_edges == row, axis=1)
            ].ravel()
            neighbors = sorted(set(incident.tolist()) | {row})
            if np.linalg.norm(pooled[row]) > 0:
                np.testing.assert_allclose(
                    pooled[row], original_covariance[neighbors].mean(axis=0), atol=1e-9
                )
        pooled_covariances.append(pooled)
    assert any(
        not np.allclose(left, right, atol=1e-9)
        for left, right in combinations(pooled_covariances, 2)
    )


def test_field_graph_pooling_does_not_read_evaluation_or_baseline_values() -> None:
    bundle = prototype.make_graph_cross_probes(prototype.GraphCrossSpec())
    graphs, _ = prototype.build_graphs(
        bundle.graph_input, GraphPurpose.FIELD_ESTIMATION
    )
    graph = graphs[FAMILIES[0]]
    carrier, receipt = prototype.prepare_field_graph(bundle.observations, graph)
    changed = replace(
        bundle.observations,
        baseline_fit_probes=1e6 * bundle.observations.baseline_fit_probes,
        evaluation_probes=np.zeros_like(bundle.observations.evaluation_probes),
    )
    changed_carrier, changed_receipt = prototype.prepare_field_graph(changed, graph)
    np.testing.assert_array_equal(
        carrier.plane_fit_probes, changed_carrier.plane_fit_probes
    )
    assert receipt == changed_receipt


def test_missing_graph_and_original_rank_collapse_never_manufacture_supported_planes() -> (
    None
):
    bundle = prototype.make_graph_cross_probes(
        prototype.GraphCrossSpec(pattern="collapsed_support")
    )
    graphs, _ = prototype.build_graphs(
        bundle.graph_input, GraphPurpose.FIELD_ESTIMATION
    )
    for graph in (None, *graphs.values()):
        carrier, _ = prototype.prepare_field_graph(bundle.observations, graph)
        _, support = prototype.chain.fit_frames(carrier.plane_fit_probes)
        assert not support.any()


def test_supported_neighbors_cannot_repair_an_originally_rank_one_center() -> None:
    bundle = prototype.make_graph_cross_probes(prototype.GraphCrossSpec())
    origin = int(np.flatnonzero((bundle.observations.coords == 0).all(axis=1))[0])
    plane = np.array(bundle.observations.plane_fit_probes, copy=True)
    plane[origin, :, 1] = 0.0
    observations = replace(bundle.observations, plane_fit_probes=plane)
    graphs, _ = prototype.build_graphs(
        bundle.graph_input, GraphPurpose.FIELD_ESTIMATION
    )
    for graph in graphs.values():
        carrier, receipt = prototype.prepare_field_graph(observations, graph)
        # The pooled neighborhood would have rank two; only the original-row gate
        # keeps this support loss from being manufactured into a successful frame.
        eigenvalues = np.linalg.eigvalsh(
            np.asarray(receipt["pooled_covariances"])[origin]
        )
        assert eigenvalues[-2] > 0.1
        assert receipt["original_support"][origin] is False
        assert receipt["carrier_permitted"][origin] is False
        np.testing.assert_array_equal(carrier.plane_fit_probes[origin], 0)
        _, support = prototype.chain.fit_frames(carrier.plane_fit_probes)
        assert not support[origin]
        assert support.sum() == len(support) - 1


@pytest.mark.parametrize("radius", (0.001, 10.0))
def test_too_sparse_or_nonlocal_field_graphs_cannot_silently_supply_eligible_carriers(
    radius: float,
) -> None:
    bundle = prototype.make_graph_cross_probes(prototype.GraphCrossSpec(side=9))
    graph = prototype.construct_radius_graph(
        bundle.graph_input,
        prototype.RadiusGraphSpec(
            "pool-gate-counterexample", GraphPurpose.FIELD_ESTIMATION, radius
        ),
    )
    carrier, receipt = prototype.prepare_field_graph(bundle.observations, graph)
    assert not any(receipt["carrier_permitted"])
    assert not any(receipt["pooled_support"])
    np.testing.assert_array_equal(carrier.plane_fit_probes, 0)
    if radius < 1:
        assert not any(receipt["neighbor_count_excluding_self"])
    else:
        assert (
            min(receipt["max_neighbor_domain_distance"])
            > receipt["locality_gate_domain_units"]
        )


def test_every_pattern_retains_the_exact_nine_cartesian_cells(
    reports: dict[str, dict],
) -> None:
    expected = set(product(FAMILIES, repeat=2))
    for report in reports.values():
        assert set(report["rows"]) == set(FAMILIES)
        assert len(report["cells"]) == 9
        assert {
            (cell["field_graph"], cell["loop_graph"]) for cell in report["cells"]
        } == expected
        for row in report["rows"].values():
            assert set(row["estimands"]) == set(ESTIMANDS)
            assert set(row["controls"]) == {"origin_centered"}
        for cell in report["cells"]:
            assert set(cell["estimands"]) == set(ESTIMANDS)
            assert set(cell["controls"]) == {"origin_centered"}
            for estimand in (*ESTIMANDS, "origin_centered"):
                for hypothesis in ("F2", "F4"):
                    assert _cell_field(cell, estimand, hypothesis)


def test_loop_graph_changes_only_loop_branch_and_reuses_exact_row_fields_and_core_seals(
    reports: dict[str, dict],
) -> None:
    for report in reports.values():
        for cell in report["cells"]:
            family = cell["field_graph"]
            for estimand in (*ESTIMANDS, "origin_centered"):
                for hypothesis in ("F2", "F4"):
                    field = _row_field(report, family, estimand, hypothesis)
                    branch = _cell_field(cell, estimand, hypothesis)
                    assert "loops" not in field
                    assert branch["field_sha256"] == field["field_sha256"]
                    assert branch["core_sha256"] == field["core"]["seal_sha256"]
                    for directions in branch["loops"].values():
                        for loop in directions.values():
                            assert loop["field_sha256"] == field["field_sha256"]


def test_all_thirty_six_sealed_core_payloads_precede_every_loop_read(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events = []
    make_field = prototype.comparison._make_field
    winding, geometry = prototype.chain._winding, prototype.chain._geometry

    def record_field(*args, **kwargs):
        result = make_field(*args, **kwargs)
        assert len(result["core"]["seal_sha256"]) == 64
        events.append("sealed_core")
        return result

    def record_winding(*args, **kwargs):
        events.append("winding")
        return winding(*args, **kwargs)

    def record_geometry(*args, **kwargs):
        events.append("geometry")
        return geometry(*args, **kwargs)

    monkeypatch.setattr(prototype.comparison, "_make_field", record_field)
    monkeypatch.setattr(prototype.chain, "_winding", record_winding)
    monkeypatch.setattr(prototype.chain, "_geometry", record_geometry)
    prototype.measure_case(prototype.GraphCrossSpec())
    assert events[:36] == ["sealed_core"] * 36
    assert events.count("sealed_core") == 36
    assert events[36:]
    assert set(events[36:]) <= {"winding", "geometry"}


def test_curved_noisy_case_has_numerically_distinct_field_graph_frames_and_sections(
    curved_report: dict,
) -> None:
    for hypothesis in ("F2", "F4"):
        values = [
            np.asarray(_row_field(curved_report, family, "full", hypothesis)["values"])
            for family in FAMILIES
        ]
        assert any(
            not np.allclose(left, right, atol=1e-9)
            for left, right in combinations(values, 2)
        )


def test_every_numeric_field_rederives_same_field_amplitude_and_seals(
    reports: dict[str, dict],
) -> None:
    for report in reports.values():
        for family in FAMILIES:
            for estimand in (*ESTIMANDS, "origin_centered"):
                for hypothesis in ("F2", "F4"):
                    field = _row_field(report, family, estimand, hypothesis)
                    assert field["core"]["field_sha256"] == field["field_sha256"]
                    assert field["core"]["charge_blind"] is True
                    if field["values"] is None:
                        assert field["state"] == "insufficient"
                        assert field["amplitude"] is None
                        assert field["direction_defined"] is None
                        assert field["missing_reason"]
                        continue
                    values = np.asarray(field["values"])
                    amplitude = np.asarray(field["amplitude"])
                    np.testing.assert_allclose(
                        amplitude, np.linalg.norm(values, axis=1)
                    )
                    np.testing.assert_array_equal(
                        field["direction_defined"], amplitude > field["amplitude_floor"]
                    )
                    if hypothesis == "F4":
                        tensor = np.asarray(field["traceless_tensor"])
                        np.testing.assert_allclose(tensor, tensor.swapaxes(-1, -2))
                        np.testing.assert_allclose(
                            np.trace(tensor, axis1=-2, axis2=-1), 0
                        )


def test_missing_support_preserves_baseline_and_centering_dependency_failures(
    reports: dict[str, dict],
) -> None:
    for pattern in ("collapsed_support", "collapsed_substrate"):
        report = reports[pattern]
        for family in FAMILIES:
            assert report["rows"][family]["baseline"]["state"] == "insufficient"
            for estimand in ("local_affine", "residual_affine", "origin_centered"):
                for hypothesis in ("F2", "F4"):
                    field = _row_field(report, family, estimand, hypothesis)
                    assert field["values"] is None
                    assert field["core"]["state"] == "insufficient"
                    assert field["core"]["value"]["candidate_count"] is None
        for cell in report["cells"]:
            for estimand in (*ESTIMANDS, "origin_centered"):
                for hypothesis in ("F2", "F4"):
                    for directions in _cell_field(cell, estimand, hypothesis)[
                        "loops"
                    ].values():
                        for branch in directions.values():
                            assert branch["state"] == "insufficient"
                            assert branch["value"] is None


def test_reports_are_deterministic_finite_json(reports: dict[str, dict]) -> None:
    for report in reports.values():
        assert json.loads(json.dumps(report, allow_nan=False, sort_keys=True)) == report
    assert (
        prototype.measure_case(prototype.GraphCrossSpec())
        == reports["quadratic_excess"]
    )


def test_graph_input_metadata_binds_the_exact_numeric_source_and_vertex_identity(
    reports: dict[str, dict],
) -> None:
    for report in reports.values():
        bundle = prototype.make_graph_cross_probes(
            prototype.GraphCrossSpec(**report["spec"])
        )
        source = bundle.graph_input
        assert report["graph_input"] == {
            "fingerprint_sha256": source.fingerprint_sha256,
            "state_sha256": source.state_sha256,
            "vertex_order_sha256": source.vertex_order_sha256,
            "primary_unit_id": source.primary_unit_id,
        }
    assert (
        reports["quadratic_excess"]["graph_input"]
        == reports["input_identity"]["graph_input"]
    )
    assert (
        reports["collapsed_substrate"]["graph_input"]["state_sha256"]
        != reports["quadratic_excess"]["graph_input"]["state_sha256"]
    )


def test_evaluation_mutation_cannot_change_graphs_pooling_baselines_or_geometry() -> (
    None
):
    bundle = prototype.make_graph_cross_probes(prototype.GraphCrossSpec())
    before = prototype.measure_graph_cross(bundle)
    erased = replace(
        bundle.observations,
        evaluation_probes=np.zeros_like(bundle.observations.evaluation_probes),
    )
    after = prototype.measure_graph_cross(replace(bundle, observations=erased))
    assert before["graphs"] == after["graphs"]
    assert before["graph_input"] == after["graph_input"]
    assert before["domain"] == after["domain"]
    for family in FAMILIES:
        assert before["rows"][family]["pooling"] == after["rows"][family]["pooling"]
        assert before["rows"][family]["baseline"] == after["rows"][family]["baseline"]
        for hypothesis in ("F2", "F4"):
            old, new = (
                _row_field(before, family, "full", hypothesis),
                _row_field(after, family, "full", hypothesis),
            )
            assert old["field_sha256"] != new["field_sha256"]
            np.testing.assert_allclose(new["values"], 0, atol=1e-10)
            np.testing.assert_array_equal(
                _row_field(before, family, "local_affine", hypothesis)["values"],
                _row_field(after, family, "local_affine", hypothesis)["values"],
            )
    for before_cell, after_cell in zip(before["cells"], after["cells"], strict=True):
        assert before_cell["geometry"] == after_cell["geometry"]


def test_baseline_mutation_changes_affine_fields_without_changing_full_fields_or_graphs() -> (
    None
):
    bundle = prototype.make_graph_cross_probes(prototype.GraphCrossSpec())
    before = prototype.measure_graph_cross(bundle)
    changed = replace(
        bundle.observations,
        baseline_fit_probes=1.5 * bundle.observations.baseline_fit_probes
        + np.array([0.4, -0.2, 0.0]),
    )
    after = prototype.measure_graph_cross(replace(bundle, observations=changed))
    assert before["graphs"] == after["graphs"]
    for family in FAMILIES:
        assert before["rows"][family]["pooling"] == after["rows"][family]["pooling"]
        assert before["rows"][family]["baseline"] != after["rows"][family]["baseline"]
        for hypothesis in ("F2", "F4"):
            before_full = _row_field(before, family, "full", hypothesis)
            after_full = _row_field(after, family, "full", hypothesis)
            np.testing.assert_array_equal(before_full["values"], after_full["values"])
            assert before_full["field_sha256"] == after_full["field_sha256"]
            assert not np.allclose(
                _row_field(before, family, "local_affine", hypothesis)["values"],
                _row_field(after, family, "local_affine", hypothesis)["values"],
            )


@pytest.mark.parametrize(
    "role", ("plane_fit_probes", "baseline_fit_probes", "evaluation_probes")
)
def test_nonfinite_probe_roles_are_rejected_before_reporting_results(role: str) -> None:
    bundle = prototype.make_graph_cross_probes(prototype.GraphCrossSpec())
    changed = np.array(getattr(bundle.observations, role), copy=True)
    changed[0, 0, 0] = np.nan
    with pytest.raises(ValueError):
        prototype.measure_graph_cross(
            replace(
                bundle, observations=replace(bundle.observations, **{role: changed})
            )
        )


@pytest.mark.parametrize(
    "left,right",
    list(
        combinations(
            ("plane_fit_probes", "baseline_fit_probes", "evaluation_probes"), 2
        )
    ),
)
def test_shared_probe_role_storage_is_rejected(left: str, right: str) -> None:
    bundle = prototype.make_graph_cross_probes(prototype.GraphCrossSpec())
    shared = replace(
        bundle.observations, **{right: getattr(bundle.observations, left).view()}
    )
    with pytest.raises(ValueError, match="disjoint|share|overlap"):
        prototype.measure_graph_cross(replace(bundle, observations=shared))


def test_nonlinear_residual_is_recomputed_in_each_cell_not_subtracted_winding_numbers(
    reports: dict[str, dict],
) -> None:
    report = reports["quadratic_excess"]
    eligible_cells = 0
    for cell in report["cells"]:
        for hypothesis in ("F2", "F4"):
            full = _loop(cell, "full", hypothesis)
            baseline = _loop(cell, "local_affine", hypothesis)
            residual = _loop(cell, "residual_affine", hypothesis)
            if residual["state"] == "eligible":
                eligible_cells += 1
                _assert_winding(full, 1)
                _assert_winding(baseline, 1)
                _assert_winding(residual, 2)
                assert residual["value"]["sampled_winding"] != (
                    full["value"]["sampled_winding"]
                    - baseline["value"]["sampled_winding"]
                )
    assert eligible_cells > 0


def test_zero_residual_is_an_abstention_not_a_found_core_in_every_graph_cell(
    reports: dict[str, dict],
) -> None:
    report = reports["input_identity"]
    for family in FAMILIES:
        for estimand in ("residual_affine", "residual_pass_through"):
            for hypothesis in ("F2", "F4"):
                field = _row_field(report, family, estimand, hypothesis)
                np.testing.assert_allclose(field["values"], 0, atol=1e-10)
                assert not any(field["direction_defined"])
                assert field["core"]["state"] == "insufficient"
                assert field["core"]["value"]["candidate_count"] is None
    for cell in report["cells"]:
        for hypothesis in ("F2", "F4"):
            assert _loop(cell, "residual_affine", hypothesis)["state"] == "insufficient"


def test_subtracting_a_pass_through_can_create_a_residual_pattern_without_full_signal(
    reports: dict[str, dict],
) -> None:
    report = reports["no_signal"]
    retained_counterexample = False
    for family in FAMILIES:
        full = _row_field(report, family, "full", "F2")
        base = _row_field(report, family, "pass_through", "F2")
        residual = _row_field(report, family, "residual_pass_through", "F2")
        np.testing.assert_allclose(full["values"], 0, atol=1e-10)
        np.testing.assert_allclose(
            residual["values"], -np.asarray(base["values"]), atol=1e-10
        )
    for cell in report["cells"]:
        assert _loop(cell, "full", "F2")["state"] == "insufficient"
        branch = _loop(cell, "residual_pass_through", "F2")
        if branch["state"] == "eligible":
            _assert_winding(branch, 1)
            retained_counterexample = True
    assert retained_counterexample


def test_all_loop_branches_retain_coverage_uncertainty_reason_and_reverse_orientation(
    reports: dict[str, dict],
) -> None:
    for report in reports.values():
        for cell in report["cells"]:
            for estimand in (*ESTIMANDS, "origin_centered"):
                for hypothesis in ("F2", "F4"):
                    for directions in _cell_field(cell, estimand, hypothesis)[
                        "loops"
                    ].values():
                        forward, reverse = directions["forward"], directions["reverse"]
                        for branch in (forward, reverse):
                            assert {
                                "state",
                                "value",
                                "reason",
                                "coverage",
                                "uncertainty",
                                "strata",
                            } <= branch.keys()
                        assert forward["state"] == reverse["state"]
                        if forward["state"] == "eligible":
                            assert (
                                forward["value"]["sampled_winding"]
                                == -reverse["value"]["sampled_winding"]
                            )


def test_graph_cross_remains_level_zero_model_free_and_does_not_evaluate_phase(
    reports: dict[str, dict],
) -> None:
    for report in reports.values():
        assert report["scope"]["synthetic_only"] is True
        assert report["scope"]["model_free"] is True
        for key in (
            "model_accessed",
            "network_accessed",
            "furnace_accessed",
            "protocol_freeze",
            "execution_authorized",
            "external_probe_provenance_verified",
            "raw_role_identity_attested",
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


def test_self_test_cli_emits_json_and_creates_no_artifact(tmp_path: Path) -> None:
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONPATH"] = str(ROOT / "src")
    completed = subprocess.run(
        [sys.executable, "-B", str(SCRIPT_PATH), "--self-test"],
        cwd=tmp_path,
        env=env,
        text=True,
        capture_output=True,
        check=False,
        timeout=120,
    )
    assert completed.returncode == 0, completed.stderr
    result = json.loads(completed.stdout)
    assert result["status"] == "pass"
    json.dumps(result, allow_nan=False)
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("flag", ("--output", "--model", "--furnace"))
def test_cli_has_no_persistent_output_model_or_furnace_route(
    tmp_path: Path, flag: str
) -> None:
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONPATH"] = str(ROOT / "src")
    completed = subprocess.run(
        [sys.executable, "-B", str(SCRIPT_PATH), "--self-test", flag, "not-authorized"],
        cwd=tmp_path,
        env=env,
        text=True,
        capture_output=True,
        check=False,
        timeout=30,
    )
    assert completed.returncode == 2
    assert "unrecognized arguments" in completed.stderr
    assert list(tmp_path.iterdir()) == []


def test_each_exact_boundary_binding_is_equivalent_to_actual_direct_edge_availability(
    reports: dict[str, dict],
) -> None:
    for report in reports.values():
        for loop in report["domain"]["loops"].values():
            assert loop["max_domain_edges_per_graph_edge"] == 1
            vertices = loop["boundary_vertex_rows"]
            boundary_edges = {
                tuple(sorted((left, right)))
                for left, right in zip(
                    vertices, vertices[1:] + vertices[:1], strict=True
                )
            }
            assert len(boundary_edges) == len(vertices)
            for family, binding in loop["bindings"].items():
                graph = report["graphs"]["loop"]["families"][family]
                if graph["canonical_edges"] is None:
                    assert not binding["matched"]
                    continue
                actual_edges = set(map(tuple, graph["canonical_edges"]))
                assert binding["matched"] is boundary_edges.issubset(actual_edges)
                if binding["matched"]:
                    assert len(binding["binding_sha256"]) == 64
                else:
                    assert binding["binding_sha256"] is None


def test_two_hop_paths_through_an_interior_hub_are_not_the_declared_boundary() -> None:
    bundle = prototype.make_graph_cross_probes(prototype.GraphCrossSpec(side=9))
    observations = bundle.observations
    outer_rows = np.flatnonzero((np.abs(observations.coords) == 1).any(axis=1))
    # Orthogonal leaves are each one unit from every interior hub, but sqrt(2)
    # from one another: all boundary endpoints have two-hop paths, no direct edge.
    states = np.zeros((len(observations.coords), len(outer_rows)))
    states[outer_rows] = np.eye(len(outer_rows))
    graph_input = prototype.GraphInput(
        primary_unit_id="boundary-hub-counterexample",
        vertex_ids=bundle.graph_input.vertex_ids,
        states=states,
    )
    graph = prototype.construct_radius_graph(
        graph_input,
        prototype.RadiusGraphSpec(
            "hub-paths-not-boundary", GraphPurpose.CYCLE_CONSTRUCTION, 1.01
        ),
    )
    _, domain = prototype.bind_loops(
        graph_input,
        observations.coords,
        observations.faces,
        {"fixed-radius": graph},
    )
    outer = domain["loops"]["outer"]
    edges = set(map(tuple, graph.canonical_edges.tolist()))
    origin = int(np.flatnonzero((observations.coords == 0).all(axis=1))[0])
    vertices = outer["boundary_vertex_rows"]
    for left, right in zip(vertices, vertices[1:] + vertices[:1], strict=True):
        assert tuple(sorted((left, right))) not in edges
        assert tuple(sorted((left, origin))) in edges
        assert tuple(sorted((origin, right))) in edges
    assert outer["bindings"]["fixed-radius"]["matched"] is False
    assert outer["bindings"]["fixed-radius"]["binding_sha256"] is None


def test_unavailable_loop_column_cannot_change_any_row_field_or_other_column(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bundle = prototype.make_graph_cross_probes(prototype.GraphCrossSpec())
    before = prototype.measure_graph_cross(bundle)
    constructor = prototype.build_graphs

    def drop_loop_column(graph_input, purpose):
        graphs, receipt = constructor(graph_input, purpose)
        if purpose is GraphPurpose.CYCLE_CONSTRUCTION:
            graphs["fixed-radius"] = None
            receipt["families"]["fixed-radius"] = {
                "state": "insufficient",
                "reason": "deliberately-unavailable-column",
                "canonical_edges": None,
            }
            receipt["distinct_edge_sets"] = False
        return graphs, receipt

    monkeypatch.setattr(prototype, "build_graphs", drop_loop_column)
    after = prototype.measure_graph_cross(bundle)
    assert before["rows"] == after["rows"]
    for old, new in zip(before["cells"], after["cells"], strict=True):
        if new["loop_graph"] != "fixed-radius":
            assert old == new
            continue
        for estimand in (*ESTIMANDS, "origin_centered"):
            for hypothesis in ("F2", "F4"):
                for directions in _cell_field(new, estimand, hypothesis)[
                    "loops"
                ].values():
                    for branch in directions.values():
                        assert branch["state"] == "insufficient"
                        assert branch["value"] is None
        assert new["geometry"]["outer"]["forward"]["state"] == "insufficient"
    summary = after["summary"]["winding"]["residual_affine"]["F2"]
    assert summary["state"] == "incomplete_support"
    assert summary["eligible_cell_count"] == 6
    assert summary["insufficient_cell_count"] == 3
    assert summary["eligible_subset_agrees"] is True
    assert summary["complete_grid_agreement"] is False


def test_summary_denominators_include_all_nine_not_just_the_eligible_subset(
    reports: dict[str, dict],
) -> None:
    for report in reports.values():
        for estimand in ESTIMANDS:
            for hypothesis in ("F2", "F4"):
                branches = [
                    _loop(cell, estimand, hypothesis) for cell in report["cells"]
                ]
                eligible = [
                    branch for branch in branches if branch["state"] == "eligible"
                ]
                summary = report["summary"]["winding"][estimand][hypothesis]
                assert summary["required_cell_count"] == 9
                assert summary["eligible_cell_count"] == len(eligible)
                assert summary["insufficient_cell_count"] == 9 - len(eligible)
                assert summary["coverage"] == len(eligible) / 9
                assert summary["all_nine_eligible"] is (len(eligible) == 9)
                assert summary["qualified_graph_invariance"] is False
                assert summary["independent_replication_count"] is None
                assert "not-calibrated" in summary["uncertainty"]
                if len(eligible) < 9:
                    assert summary["state"] == "incomplete_support"
                    assert summary["complete_grid_agreement"] is False
        assert report["design"]["axis_sizes"] == [3, 3, 1]
        assert report["design"]["graph_cells_are_independent_replicates"] is False
        assert report["claim_boundary"]["complete_m8"] is False
        assert report["claim_boundary"]["winner_selected"] is False


@pytest.mark.parametrize(
    "charges,distinct,state",
    [
        ([1] * 9, True, "complete_agreement"),
        ([1] * 8 + [2], True, "complete_disagreement"),
        ([1] * 9, False, "graph_diversity_insufficient"),
    ],
)
def test_summary_distinguishes_agreement_disagreement_and_only_label_diversity(
    charges: list[int], distinct: bool, state: str
) -> None:
    branches = [
        {"state": "eligible", "value": {"sampled_winding": charge}}
        for charge in charges
    ]
    summary = prototype._aggregate(branches, distinct=distinct)
    assert summary["state"] == state
    assert summary["complete_grid_agreement"] is (state == "complete_agreement")
    assert summary["qualified_graph_invariance"] is False


def test_baseline_seals_for_all_three_rows_precede_any_evaluation_moment_read(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events = []
    fit, moments = (
        prototype.comparison.fit_baseline,
        prototype.comparison._reference_moments,
    )

    def record_fit(*args, **kwargs):
        result = fit(*args, **kwargs)
        assert len(result["baseline_sha256"]) == 64
        events.append("baseline_sealed")
        return result

    def record_moments(frames, gauges, probes, role):
        if role == 2:
            events.append("evaluation_moments")
        return moments(frames, gauges, probes, role)

    monkeypatch.setattr(prototype.comparison, "fit_baseline", record_fit)
    monkeypatch.setattr(prototype.comparison, "_reference_moments", record_moments)
    prototype.measure_case(prototype.GraphCrossSpec())
    assert events == ["baseline_sealed"] * 3 + ["evaluation_moments"] * 3


@pytest.mark.parametrize("gauge", ("local_o2", "reflection"))
def test_o2_gauges_preserve_both_hypotheses_under_all_graph_cross_cells(
    gauge: str, curved_report: dict
) -> None:
    changed = prototype.measure_case(
        prototype.GraphCrossSpec(
            pattern="curved_coherent", probe_noise=0.03, seed=7, gauge=gauge
        )
    )
    assert curved_report["graphs"] == changed["graphs"]
    for family in FAMILIES:
        for estimand in (*ESTIMANDS, "origin_centered"):
            for hypothesis in ("F2", "F4"):
                old, new = (
                    _row_field(curved_report, family, estimand, hypothesis),
                    _row_field(changed, family, estimand, hypothesis),
                )
                np.testing.assert_allclose(old["values"], new["values"], atol=1e-9)
                np.testing.assert_allclose(
                    old["amplitude"], new["amplitude"], atol=1e-9
                )
                assert old["core"]["value"] == new["core"]["value"]
    for old, new in zip(curved_report["cells"], changed["cells"], strict=True):
        for estimand in (*ESTIMANDS, "origin_centered"):
            for hypothesis in ("F2", "F4"):
                before, after = (
                    _loop(old, estimand, hypothesis),
                    _loop(new, estimand, hypothesis),
                )
                assert before["state"] == after["state"]
                if before["state"] == "eligible":
                    assert (
                        before["value"]["sampled_winding"]
                        == after["value"]["sampled_winding"]
                    )
        before, after = (
            old["geometry"]["outer"]["forward"],
            new["geometry"]["outer"]["forward"],
        )
        assert before["state"] == after["state"]
        if before["state"] == "eligible":
            np.testing.assert_allclose(
                before["value"]["matrix"], after["value"]["matrix"], atol=1e-9
            )


def test_graph_input_row_identity_cannot_be_silently_reordered() -> None:
    bundle = prototype.make_graph_cross_probes(prototype.GraphCrossSpec())
    changed = prototype.GraphInput(
        primary_unit_id=bundle.graph_input.primary_unit_id,
        vertex_ids=bundle.graph_input.vertex_ids[::-1],
        states=bundle.graph_input.states,
    )
    with pytest.raises(ValueError, match="identity|row"):
        prototype.measure_graph_cross(replace(bundle, graph_input=changed))


@pytest.mark.parametrize(
    "pattern,nonlinear,zero",
    [
        ("f2_nonlinear_only", "F2", "F4"),
        ("f4_nonlinear_only", "F4", "F2"),
    ],
)
def test_one_nonlinear_hypothesis_cannot_promote_its_coprimary_peer(
    pattern: str, nonlinear: str, zero: str
) -> None:
    report = prototype.measure_case(prototype.GraphCrossSpec(pattern))
    positive_count = 0
    for cell in report["cells"]:
        assert _loop(cell, "residual_affine", zero)["state"] == "insufficient"
        branch = _loop(cell, "residual_affine", nonlinear)
        if branch["state"] == "eligible":
            _assert_winding(branch, 2)
            positive_count += 1
    assert positive_count > 0
    assert report["claim_boundary"]["winner_selected"] is False


def test_nuisance_panel_is_crossed_not_a_confounded_case_list(
    monkeypatch: pytest.MonkeyPatch, curved_report: dict
) -> None:
    seen = []

    def record_case(spec):
        seen.append(spec)
        return curved_report

    monkeypatch.setattr(prototype, "measure_case", record_case)
    panel = prototype.run_nuisance_panel()
    expected = set(product((9, 17), (0.0, 0.75), (0.0, 0.2), (0, 1)))
    assert len(seen) == panel["case_count"] == 16
    assert {
        (spec.side, spec.warp, spec.graph_noise, spec.seed) for spec in seen
    } == expected
    assert {spec.pattern for spec in seen} == {"curved_coherent"}
    assert {spec.probe_noise for spec in seen} == {0.0}
    assert panel["held_out_confirmation"] is False
    assert panel["threshold_selection"] is False
    assert "not-calibrated" in panel["uncertainty"]
    assert "duplicate" in panel["uncertainty"]
    for case in panel["cases"]:
        assert len(case["outer_cells"]) == 9
        assert set(case["summary"]["winding"]) == set(ESTIMANDS)
        assert case["graph_input"] == curved_report["graph_input"]
        assert set(case["locality"]) == set(FAMILIES)
        for family in FAMILIES:
            pooling = curved_report["rows"][family]["pooling"]
            assert case["locality"][family] == {
                "pooling_sha256": pooling["pooling_sha256"],
                "max_neighbor_domain_distance": max(
                    pooling["max_neighbor_domain_distance"]
                ),
                "neighbor_mass_fraction_range": [
                    min(pooling["neighbor_mass_fraction"]),
                    max(pooling["neighbor_mass_fraction"]),
                ],
                "original_supported_count": sum(pooling["original_support"]),
                "pooled_supported_count": sum(pooling["pooled_support"]),
                "locality_gate_domain_units": pooling["locality_gate_domain_units"],
            }
