from __future__ import annotations

import copy
import dataclasses
import hashlib
import inspect
import json
import os
import subprocess
import sys
from fractions import Fraction
from pathlib import Path

import numpy as np
import pytest

from spirallens.core.canonical import canonical_json_bytes
from spirallens.graphs import GraphInput


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "prototype_p4_graph_scale_transport_v0_1.py"
DESIGN_PATH = (
    ROOT
    / "experiments"
    / "qualification"
    / "p4_phase_capture_measurement_chain_v0_1"
    / "design.json"
)

sys.path.insert(0, str(SCRIPT_PATH.parent))
import prototype_p4_graph_scale_transport_v0_1 as prototype  # noqa: E402


@pytest.fixture(scope="module")
def development_bundle() -> tuple[
    tuple[prototype.TransportLaw, ...],
    tuple[prototype.NuisanceCase, ...],
    prototype.StructuralGates,
    prototype.SelectionDecision,
]:
    laws = prototype.development_candidate_laws()
    cases = prototype.development_calibration_cases()
    gates = prototype.development_gates()
    selection = prototype.select_transport_law(laws, cases, gates)
    return laws, cases, gates, selection


@pytest.fixture(scope="module")
def development_report() -> dict[str, object]:
    return prototype.run_development_demo()


def _copy_case(
    case: prototype.NuisanceCase,
    *,
    case_id: str,
    vertex_ids: np.ndarray | None = None,
    states: np.ndarray | None = None,
    boundary_vertex_ids: tuple[int, ...] | None = None,
) -> prototype.NuisanceCase:
    return prototype.NuisanceCase(
        case_id=case_id,
        role=case.role,
        graph_input=GraphInput(
            primary_unit_id=case_id,
            vertex_ids=(
                case.graph_input.vertex_ids if vertex_ids is None else vertex_ids
            ),
            states=case.graph_input.states if states is None else states,
        ),
        boundary_vertex_ids=(
            case.boundary_vertex_ids
            if boundary_vertex_ids is None
            else boundary_vertex_ids
        ),
        nuisance_axes=case.nuisance_axes,
    )


def _graph_edge_hashes(evaluation: dict[str, object]) -> list[str]:
    graphs = evaluation["graphs"]
    assert isinstance(graphs, list)
    return [str(graph["edge_fingerprint_sha256"]) for graph in graphs]


def test_demo_passes_synthetic_plumbing_without_claim_promotion(
    development_report: dict[str, object],
) -> None:
    report = development_report
    assert report["schema_version"] == prototype.PROTOTYPE_SCHEMA_VERSION
    assert report["prototype_id"] == prototype.PROTOTYPE_ID
    assert report["state"] == "pass"
    assert report["reason"] == "synthetic-plumbing-pass"
    assert report["dynamic_timestamp_present"] is False
    assert report["persistent_artifact_written"] is False

    selection = report["selection"]
    assert selection["state"] == "pass"
    assert selection["candidate_law_count"] == 54
    assert selection["calibration_case_count"] == 4
    assert selection["eligible_law_count"] == 6
    assert selection["selected_law"] == {
        "law_id": "m1-development-law-046",
        "neighbor_fraction": {"numerator": 1, "denominator": 4},
        "scale_neighbor_fraction": {"numerator": 1, "denominator": 6},
        "radius_scale_multiplier": {"numerator": 1, "denominator": 1},
        "shared_overlap_fraction": {"numerator": 1, "denominator": 2},
        "all_parameters_dimensionless": True,
    }
    confirmation = report["held_out_confirmation"]
    assert confirmation["state"] == "pass"
    assert confirmation["selector_rerun"] is False
    assert confirmation["threshold_widening"] is False
    assert confirmation["candidate_set_read"] is False

    scope = report["scope"]
    assert scope["model_free"] is True
    assert scope["synthetic_only"] is True
    assert scope["in_memory_only"] is True
    for key in (
        "official_input",
        "protocol_freeze",
        "launch_prepared",
        "execution_authorized",
        "model_accessed",
        "network_accessed",
        "subject_accessed",
        "pythia70_accessed",
        "pythia160_accessed",
        "field_read",
        "core_read",
        "holonomy_read",
        "phase_read",
        "winding_read",
    ):
        assert scope[key] is False
    claim = report["claim_boundary"]
    assert claim["claim_ceiling"] == "level_0"
    assert claim["development_plumbing_only"] is True
    assert claim["graph_transport_calibrated_for_p4_v03"] is False
    assert claim["claim_delta"] == "none"
    assert claim["milestone_credit"] == "none"
    for key in (
        "scientific_authority",
        "topology_authority",
        "semantic_authority",
        "publication_authority",
    ):
        assert claim[key] is False
    json.dumps(report, allow_nan=False, sort_keys=True)


def test_transport_uses_exact_fractional_ceiling_and_same_k_for_two_families(
    development_bundle: tuple[
        tuple[prototype.TransportLaw, ...],
        tuple[prototype.NuisanceCase, ...],
        prototype.StructuralGates,
        prototype.SelectionDecision,
    ],
) -> None:
    _laws, cases, _gates, selection = development_bundle
    law = selection.selected_law
    assert law is not None
    parameters = prototype.derive_transported_parameters(law, cases[0].graph_input)

    assert parameters.row_count == 25
    assert parameters.neighbor_count == 6
    assert parameters.scale_neighbor_count == 4
    assert parameters.minimum_shared_neighbors == 3
    assert parameters.radius == parameters.local_scale
    document = parameters.to_dict()
    assert document["clipping_rule"] == (
        "neighbor-min-two-scale-min-one-max-n-minus-one"
    )
    assert document["local_scale_hex"] == parameters.local_scale.hex()
    assert document["radius_hex"] == parameters.radius.hex()


def test_selector_is_candidate_and_calibration_order_invariant(
    development_bundle: tuple[
        tuple[prototype.TransportLaw, ...],
        tuple[prototype.NuisanceCase, ...],
        prototype.StructuralGates,
        prototype.SelectionDecision,
    ],
) -> None:
    laws, cases, gates, baseline = development_bundle
    reordered = prototype.select_transport_law(
        tuple(reversed(laws)),
        tuple(reversed(cases)),
        gates,
    )

    assert reordered.report == baseline.report
    assert reordered.fingerprint_sha256 == baseline.fingerprint_sha256
    assert reordered.selected_law == baseline.selected_law


def test_selected_rank_is_the_exact_coordinatewise_worst_case_minimum(
    development_bundle: tuple[
        tuple[prototype.TransportLaw, ...],
        tuple[prototype.NuisanceCase, ...],
        prototype.StructuralGates,
        prototype.SelectionDecision,
    ],
) -> None:
    laws, cases, gates, selection = development_bundle
    eligible: list[tuple[tuple[object, ...], prototype.TransportLaw]] = []
    for law in laws:
        evaluations = tuple(
            prototype.evaluate_transport_law(law, case, gates) for case in cases
        )
        if all(evaluation.passed for evaluation in evaluations):
            worst = tuple(
                max(evaluation.objective[index] for evaluation in evaluations)
                for index in range(4)
            )
            eligible.append(((*worst, law.parameter_key), law))
    eligible.sort(key=lambda item: item[0])

    assert len(eligible) == selection.report["eligible_law_count"] == 6
    assert selection.selected_law == eligible[0][1]
    assert selection.report["average_case_objective_used"] is False
    assert all(isinstance(value, Fraction) for value in eligible[0][0][:4])


def test_global_scale_and_signed_coordinate_permutation_are_covariant(
    development_bundle: tuple[
        tuple[prototype.TransportLaw, ...],
        tuple[prototype.NuisanceCase, ...],
        prototype.StructuralGates,
        prototype.SelectionDecision,
    ],
) -> None:
    _laws, cases, gates, selection = development_bundle
    law = selection.selected_law
    assert law is not None
    base = cases[2]
    base_evaluation = prototype.evaluate_transport_law(law, base, gates).report

    scaled = _copy_case(
        base,
        case_id="m1-scale-covariance",
        states=np.asarray(base.graph_input.states * 8.0, dtype="<f8"),
    )
    scaled_evaluation = prototype.evaluate_transport_law(law, scaled, gates).report
    assert _graph_edge_hashes(scaled_evaluation) == _graph_edge_hashes(base_evaluation)
    assert scaled_evaluation["transported_parameters"]["local_scale"] == (
        8.0 * base_evaluation["transported_parameters"]["local_scale"]
    )
    assert scaled_evaluation["transported_parameters"]["radius"] == (
        8.0 * base_evaluation["transported_parameters"]["radius"]
    )

    transformed = _copy_case(
        base,
        case_id="m1-orthogonal-covariance",
        states=np.asarray(
            np.column_stack(
                (-base.graph_input.states[:, 1], base.graph_input.states[:, 0])
            ),
            dtype="<f8",
        ),
    )
    transformed_evaluation = prototype.evaluate_transport_law(
        law, transformed, gates
    ).report
    assert _graph_edge_hashes(transformed_evaluation) == _graph_edge_hashes(
        base_evaluation
    )
    assert (
        transformed_evaluation["transported_parameters"]
        == (base_evaluation["transported_parameters"])
    )


def test_joint_vertex_permutation_preserves_vertex_identity_edges(
    development_bundle: tuple[
        tuple[prototype.TransportLaw, ...],
        tuple[prototype.NuisanceCase, ...],
        prototype.StructuralGates,
        prototype.SelectionDecision,
    ],
) -> None:
    _laws, cases, gates, selection = development_bundle
    law = selection.selected_law
    assert law is not None
    base = cases[1]
    permutation = np.arange(base.graph_input.states.shape[0] - 1, -1, -1)
    permuted = _copy_case(
        base,
        case_id="m1-joint-permutation",
        vertex_ids=base.graph_input.vertex_ids[permutation],
        states=base.graph_input.states[permutation],
    )
    base_parameters = prototype.derive_transported_parameters(law, base.graph_input)
    permuted_parameters = prototype.derive_transported_parameters(
        law, permuted.graph_input
    )
    base_graphs = prototype._construct_graphs(law, base.graph_input, base_parameters)
    permuted_graphs = prototype._construct_graphs(
        law, permuted.graph_input, permuted_parameters
    )

    assert base_parameters == permuted_parameters
    assert [prototype._canonical_vertex_edges(graph) for graph in base_graphs] == [
        prototype._canonical_vertex_edges(graph) for graph in permuted_graphs
    ]


def test_confirmation_binds_selection_gates_and_has_no_reselection_argument(
    development_bundle: tuple[
        tuple[prototype.TransportLaw, ...],
        tuple[prototype.NuisanceCase, ...],
        prototype.StructuralGates,
        prototype.SelectionDecision,
    ],
) -> None:
    _laws, _cases, gates, selection = development_bundle
    assert tuple(
        inspect.signature(prototype.confirm_selected_transport_law).parameters
    ) == (
        "selection",
        "held_out_case",
        "gates",
    )
    confirmation = prototype.confirm_selected_transport_law(
        selection,
        prototype.development_held_out_case(),
        gates,
    )
    assert (
        confirmation["gates_fingerprint_sha256"]
        == selection.report["gates_fingerprint_sha256"]
    )
    widened = dataclasses.replace(
        gates,
        maximum_edge_count_ratio=prototype.PositiveRational(4, 1),
    )
    with pytest.raises(
        prototype.PrototypeContractError,
        match="gates differ",
    ):
        prototype.confirm_selected_transport_law(
            selection,
            prototype.development_held_out_case(),
            widened,
        )

    tampered = copy.deepcopy(selection)
    tampered.report["state"] = "insufficient"
    with pytest.raises(
        prototype.PrototypeContractError,
        match="selection report changed",
    ):
        prototype.confirm_selected_transport_law(
            tampered,
            prototype.development_held_out_case(),
            gates,
        )


def test_selection_receipt_is_factory_only_and_duplicate_parameters_fail(
    development_bundle: tuple[
        tuple[prototype.TransportLaw, ...],
        tuple[prototype.NuisanceCase, ...],
        prototype.StructuralGates,
        prototype.SelectionDecision,
    ],
) -> None:
    laws, cases, gates, selection = development_bundle
    with pytest.raises(
        prototype.PrototypeContractError,
        match="must be produced",
    ):
        prototype.SelectionDecision(
            state=selection.state,
            selected_law=selection.selected_law,
            gates=gates,
            report=selection.report,
        )
    duplicate = dataclasses.replace(laws[0], law_id="duplicate-parameter-law")
    with pytest.raises(
        prototype.PrototypeContractError,
        match="parameterizations must be unique",
    ):
        prototype.select_transport_law((laws[0], duplicate), cases[:1], gates)


def test_role_boundary_rejects_holdout_selection_and_calibration_confirmation(
    development_bundle: tuple[
        tuple[prototype.TransportLaw, ...],
        tuple[prototype.NuisanceCase, ...],
        prototype.StructuralGates,
        prototype.SelectionDecision,
    ],
) -> None:
    laws, cases, gates, selection = development_bundle
    with pytest.raises(
        prototype.PrototypeContractError,
        match="calibration cases only",
    ):
        prototype.select_transport_law(
            laws[:1],
            (prototype.development_held_out_case(),),
            gates,
        )
    with pytest.raises(
        prototype.PrototypeContractError,
        match="held-out case",
    ):
        prototype.confirm_selected_transport_law(selection, cases[0], gates)


def test_nuisance_input_surface_is_field_blind_and_closed() -> None:
    assert tuple(prototype.NuisanceCase.__dataclass_fields__) == (
        "case_id",
        "role",
        "graph_input",
        "boundary_vertex_ids",
        "nuisance_axes",
    )
    assert tuple(inspect.signature(prototype.select_transport_law).parameters) == (
        "laws",
        "calibration_cases",
        "gates",
    )
    descriptor = prototype.development_calibration_cases()[0].to_descriptor()
    for key in (
        "field_read",
        "core_read",
        "holonomy_read",
        "phase_read",
        "winding_read",
        "subject_outcome_read",
    ):
        assert descriptor[key] is False
    cases = prototype.development_calibration_cases()
    assert set(dict(cases[0].nuisance_axes)) == set(prototype.NUISANCE_AXES)
    for axis in prototype.NUISANCE_AXES:
        assert len({dict(case.nuisance_axes)[axis] for case in cases}) > 1


@pytest.mark.parametrize(
    ("numerator", "denominator", "message"),
    [
        (0, 1, "at least 1"),
        (1, 0, "at least 1"),
        (2, 4, "must be reduced"),
        (True, 1, "must be an integer"),
        (1_000_001, 1, "fixed development bound"),
    ],
)
def test_rational_contract_fails_closed(
    numerator: int,
    denominator: int,
    message: str,
) -> None:
    with pytest.raises(prototype.PrototypeContractError, match=message):
        prototype.PositiveRational(numerator, denominator)


def test_structural_gates_reject_an_impossible_edge_ratio_bound() -> None:
    with pytest.raises(
        prototype.PrototypeContractError,
        match="maximum_edge_count_ratio must be at least one",
    ):
        dataclasses.replace(
            prototype.development_gates(),
            maximum_edge_count_ratio=prototype.PositiveRational(1, 2),
        )


def test_zero_local_scale_is_insufficient_not_absence() -> None:
    graph_input = GraphInput(
        primary_unit_id="m1-zero-scale",
        vertex_ids=np.arange(4, dtype="<i8"),
        states=np.zeros((4, 2), dtype="<f8"),
    )
    case = prototype.NuisanceCase(
        case_id="m1-zero-scale",
        role=prototype.CaseRole.CALIBRATION,
        graph_input=graph_input,
        boundary_vertex_ids=(0, 1, 2, 3),
        nuisance_axes=(
            ("seed", "0"),
            ("density-warp", "0/1"),
            ("noise", "0/1"),
            ("sampling-density", "2x2"),
        ),
    )
    evaluation = prototype.evaluate_transport_law(
        prototype.development_candidate_laws()[0],
        case,
        prototype.development_gates(),
    )

    assert evaluation.report["state"] == "insufficient"
    assert evaluation.report["reason"] == "nonpositive-or-nonfinite-local-scale"
    assert evaluation.report["rejection_reasons"] == [
        "nonpositive-or-nonfinite-local-scale"
    ]
    assert evaluation.report["graphs"] is None


def test_boundary_support_failure_is_retained_as_insufficient(
    development_bundle: tuple[
        tuple[prototype.TransportLaw, ...],
        tuple[prototype.NuisanceCase, ...],
        prototype.StructuralGates,
        prototype.SelectionDecision,
    ],
) -> None:
    _laws, cases, gates, selection = development_bundle
    law = selection.selected_law
    assert law is not None
    strict = dataclasses.replace(gates, maximum_boundary_hops_per_domain_edge=1)
    evaluation = prototype.evaluate_transport_law(law, cases[0], strict)

    assert evaluation.report["state"] == "insufficient"
    assert (
        "shared-neighbor:declared-boundary-unsupported"
        in evaluation.report["rejection_reasons"]
    )


def test_no_eligible_law_returns_insufficient_without_fallback(
    development_bundle: tuple[
        tuple[prototype.TransportLaw, ...],
        tuple[prototype.NuisanceCase, ...],
        prototype.StructuralGates,
        prototype.SelectionDecision,
    ],
) -> None:
    laws, cases, gates, _selection = development_bundle
    impossible = dataclasses.replace(
        gates,
        minimum_mean_degree=prototype.PositiveRational(100, 1),
        maximum_mean_degree=prototype.PositiveRational(100, 1),
    )
    decision = prototype.select_transport_law(laws[:3], cases[:1], impossible)

    assert decision.state == "insufficient"
    assert decision.selected_law is None
    assert decision.report["eligible_law_count"] == 0
    assert decision.report["selected_worst_case_objective"] is None
    with pytest.raises(prototype.PrototypeContractError, match="passing selection"):
        prototype.confirm_selected_transport_law(
            decision,
            prototype.development_held_out_case(),
            impossible,
        )


def test_demo_is_byte_deterministic_and_cli_writes_nothing(
    development_report: dict[str, object],
    tmp_path: Path,
) -> None:
    second = prototype.run_development_demo()
    assert canonical_json_bytes(second) == canonical_json_bytes(development_report)

    before = tuple(tmp_path.iterdir())
    environment = {
        "PYTHONPATH": str(ROOT / "src"),
        "PYTHONDONTWRITEBYTECODE": "1",
        "PATH": os.environ.get("PATH", ""),
    }
    completed = subprocess.run(
        [sys.executable, "-B", str(SCRIPT_PATH)],
        cwd=tmp_path,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )
    assert tuple(tmp_path.iterdir()) == before
    cli_report = json.loads(completed.stdout)
    assert cli_report == development_report
    assert completed.stderr == ""


def test_predecessor_design_and_consumed_v02_artifacts_are_unchanged() -> None:
    design = json.loads(DESIGN_PATH.read_bytes())
    assert design["status"] == "planned_not_frozen_not_run"
    graph = design["graph_reception"]
    assert graph["strategy"] == (
        "dimensionless-field-blind-scale-transport-plus-"
        "multi-nuisance-worst-case-calibration"
    )
    assert graph["post_confirmation_threshold_widening_authorized"] is False
    assert graph["selector_rerun_on_confirmation_authorized"] is False
    assert design["authority"]["p4_v03_source_freeze_authorized"] is False
    assert design["authority"]["execution_authorized"] is False
    assert design["authority"]["model_access_authorized"] is False

    expected = {
        "launch.json": (
            "c6bfb9edf4f8ff22aaf2df8badcb137fb780158edf229543fc337e8e9400aeac"
        ),
        "attempt.json": (
            "cce96c962ae3fd62b9eff75bc1205edde08f5943ee3a1ce63dc858fa7638e576"
        ),
        "terminal-result.json": (
            "606893f6cfeb31fac476fd0658a6f1c9dab7ade4d40c7ba3c40f71c754fdfed0"
        ),
    }
    artifact_root = (
        ROOT
        / "experiments"
        / "qualification"
        / "p4_graph_evaluability_calibration_v0_2"
    )
    assert {
        name: hashlib.sha256((artifact_root / name).read_bytes()).hexdigest()
        for name in expected
    } == expected


def test_source_has_no_model_network_or_official_lifecycle_imports() -> None:
    source = SCRIPT_PATH.read_text(encoding="utf-8")
    forbidden = (
        "torch",
        "transformers",
        "huggingface_hub",
        "requests",
        "urllib",
        "socket",
        "run_p4_graph_evaluability_calibration_v0_2",
        "prepare-launch",
        "repair-projections",
    )
    for token in forbidden:
        assert token not in source
