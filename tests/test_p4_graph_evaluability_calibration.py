from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import math
import os
import struct
import subprocess
import sys
import types
from pathlib import Path

import numpy as np
import pytest


ROOT = Path(__file__).resolve().parents[1]
RUNNER_PATH = ROOT / "scripts" / "run_p4_graph_evaluability_calibration.py"
SPEC = importlib.util.spec_from_file_location("p4_graph_evaluability_runner", RUNNER_PATH)
assert SPEC is not None and SPEC.loader is not None
P4 = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = P4
SPEC.loader.exec_module(P4)


def _candidate(
    family: str,
    parameters: tuple[tuple[str, int | float], ...],
    edges: frozenset[tuple[int, int]],
    marker: str,
) -> object:
    digest = (marker * 64)[:64]
    return P4.StructuralCandidate(
        family=family,
        parameters=parameters,
        graph_input_fingerprint_sha256=digest,
        vertex_order_sha256=digest,
        state_sha256=digest,
        specification_fingerprint_sha256=digest,
        family_identity_fingerprint_sha256=digest,
        graph_fingerprint_sha256=digest,
        edge_fingerprint_sha256=digest,
        component_labels_sha256=digest,
        degree_sha256=digest,
        two_core_mask_sha256=digest,
        edges=edges,
        two_core_rows=frozenset(range(49)),
        edge_count=147,
        component_count=1,
        largest_component_vertex_count=49,
        two_core_vertex_count=49,
        cycle_rank=99,
        matched_cycle_classes=("central", "wide"),
        cycle_binding_fingerprints=(("central", digest), ("wide", digest)),
    )


def _disjoint_edges() -> tuple[frozenset[tuple[int, int]], ...]:
    all_edges = [(left, right) for left in range(49) for right in range(left + 1, 49)]
    return tuple(frozenset(all_edges[index * 147 : (index + 1) * 147]) for index in range(3))


def _not_run_result() -> dict[str, object]:
    return {
        "terminal_state": "invalid",
        "reason": "caught-execution-error",
        "calibration_selector": None,
        "graph_selection_seal_sha256": None,
        "threshold_seal_sha256": None,
        "confirmation_access_seal_sha256": None,
        "calibration_matrix": None,
        "calibration_algebraic_diagnostics": None,
        "calibration_scalar_inventory": None,
        "effective_thresholds": None,
        "confirmation_structural": None,
        "confirmation_matrix": None,
        "confirmation_accessed": False,
        "graph_selection_sealed": False,
        "threshold_decision_sealed": False,
        "controls": P4._not_run_controls("caught-execution-error"),
    }


def _matrix_projection(
    role: str,
    *,
    selected: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    cases = tuple(name for name, _expected in P4.CROSSED_CASES)
    expected = dict(P4.CROSSED_CASES)
    cells: list[dict[str, object]] = []
    for cell_id in P4._required_cell_ids(role, cases):
        _role, case, cycle_class, field_family, cycle_family = cell_id.split("|")
        cells.append(
            {
                "cell_id": cell_id,
                "case": case,
                "cycle_class": cycle_class,
                "field_graph_family": field_family,
                "cycle_graph_family": cycle_family,
                "attempt_status": "evaluable",
                "signed_total_cycles": expected[case],
                "expected_continuous_cycles": expected[case],
                "absolute_error_cycles": 0.0,
                "reason_codes": [],
            }
        )
    selected_edge_order = (
        {
            item["family"]: item["edge_fingerprint_sha256"]
            for item in selected
        }
        if selected is not None
        else {
            family: _candidate_projection(family, f"purpose-{family}")[
                "edge_fingerprint_sha256"
            ]
            for family in P4.FAMILY_ORDER
        }
    )
    checks = [
        {
            "case": case,
            "cycle_class": cycle_class,
            "family": family,
            "field_graph_fingerprint_sha256": "a" * 64,
            "cycle_graph_fingerprint_sha256": "b" * 64,
            "field_canonical_edge_order_sha256": selected_edge_order[family],
            "cycle_canonical_edge_order_sha256": selected_edge_order[family],
            "fingerprint_equality_required": False,
            "canonical_adjacency_equal": True,
            "canonical_edge_order_sha256_equal": True,
        }
        for case in cases
        for cycle_class in P4.CYCLE_CLASS_ORDER
        for family in P4.FAMILY_ORDER
    ]
    spans = [
        {
            "span_id": span_id,
            "case": span_id.split("|")[1],
            "cycle_class": span_id.split("|")[2],
            "graph_family_span_cycles": 0.0,
        }
        for span_id in P4._required_span_ids(role, cases)
    ]
    required_ids = P4._required_cell_ids(role, cases)
    return {
        "role": role,
        "cell_count": 54,
        "required_cell_ids_sha256": P4.canonical_json_sha256(required_ids),
        "cells": cells,
        "purpose_adjacency_checks": checks,
        "purpose_adjacency_check_count": 18,
        "purpose_adjacency_checks_sha256": P4.canonical_json_sha256(checks),
        "worst_oracle_or_null_error_cycles": 0.0,
        "graph_family_spans": spans,
    }


def _candidate_projection(
    family: str,
    marker: str,
    *,
    edge_count: int = 147,
    largest: int = 49,
    core: int = 49,
    cycle_rank: int = 99,
    matched: tuple[str, ...] = P4.CYCLE_CLASS_ORDER,
    edge_shift_offset: int = 0,
) -> dict[str, object]:
    digest = hashlib.sha256(marker.encode("ascii")).hexdigest()
    family_index = P4.FAMILY_ORDER.index(family)
    shifts = range(
        edge_shift_offset + 3 * family_index + 1,
        edge_shift_offset + 3 * family_index + 4,
    )
    canonical_edges = sorted(
        {
            tuple(sorted((row, (row + shift) % 49)))
            for shift in shifts
            for row in range(49)
        }
    )
    if edge_count != 147:
        all_edges = [
            (left, right)
            for left in range(49)
            for right in range(left + 1, 49)
        ]
        path = [(row, row + 1) for row in range(48)]
        canonical_edges = sorted(
            path
            + [edge for edge in all_edges if edge not in path][: edge_count - 48]
        )
    reconstructed = P4._reconstruct_canonical_graph(
        [list(edge) for edge in canonical_edges], label="fixture candidate"
    )
    if family == "mutual-knn":
        parameters: dict[str, object] = {"neighbor_count": 6}
        bits: dict[str, object] = {"neighbor_count": None}
    elif family == "fixed-radius":
        parameters = {"radius": 0.5}
        bits = {"radius": struct.pack(">d", 0.5).hex()}
    else:
        parameters = {"neighbor_count": 6, "minimum_shared_neighbors": 2}
        bits = {"neighbor_count": None, "minimum_shared_neighbors": None}
    return {
        "projection_schema_version": (
            "spirallens.p4-structural-candidate-projection.v0.1"
        ),
        "persisted_projection_of_in_memory_receipt": True,
        "receipt_round_trip_claimed": False,
        "family": family,
        "parameters": parameters,
        "float64_parameter_big_endian_bits": bits,
        "graph_input_fingerprint_sha256": digest,
        "vertex_order_sha256": P4.array_sha256(
            np.arange(49, dtype="<i8")
        ),
        "state_sha256": digest,
        "specification_fingerprint_sha256": digest,
        "family_identity_fingerprint_sha256": digest,
        "graph_fingerprint_sha256": digest,
        "edge_fingerprint_sha256": reconstructed["edge_fingerprint_sha256"],
        "component_labels_sha256": reconstructed["component_labels_sha256"],
        "degree_sha256": reconstructed["degree_sha256"],
        "two_core_mask_sha256": reconstructed["two_core_mask_sha256"],
        "canonical_edges": [list(edge) for edge in canonical_edges],
        "edge_count": reconstructed["edge_count"],
        "mean_degree": 2.0 * int(reconstructed["edge_count"]) / 49.0,
        "component_count": reconstructed["component_count"],
        "largest_component_vertex_count": reconstructed[
            "largest_component_vertex_count"
        ],
        "two_core_vertex_count": reconstructed["two_core_vertex_count"],
        "cycle_rank": reconstructed["cycle_rank"],
        "matched_cycle_classes": list(matched),
        "cycle_binding_fingerprints": {
            cycle_class: digest if cycle_class in matched else ""
            for cycle_class in P4.CYCLE_CLASS_ORDER
        },
    }


def _triplet_measurements_projection(
    selected: list[dict[str, object]],
) -> dict[str, object]:
    edges = [int(item["edge_count"]) for item in selected]
    largest = [int(item["largest_component_vertex_count"]) for item in selected]
    cores = [int(item["two_core_vertex_count"]) for item in selected]
    reconstructed = [
        P4._reconstruct_canonical_graph(
            item["canonical_edges"], label="fixture selected"
        )
        for item in selected
    ]
    pairs = ((0, 1), (0, 2), (1, 2))
    pairwise = [
        {
            "left_family": selected[left]["family"],
            "right_family": selected[right]["family"],
            "intersection_count": len(
                set(reconstructed[left]["edges"])
                & set(reconstructed[right]["edges"])
            ),
            "union_count": len(
                set(reconstructed[left]["edges"])
                | set(reconstructed[right]["edges"])
            ),
            "jaccard": (
                len(
                    set(reconstructed[left]["edges"])
                    & set(reconstructed[right]["edges"])
                )
                / len(
                    set(reconstructed[left]["edges"])
                    | set(reconstructed[right]["edges"])
                )
            ),
            "edge_sets_differ": (
                set(reconstructed[left]["edges"])
                != set(reconstructed[right]["edges"])
            ),
            "jaccard_at_most_0_85": (
                20
                * len(
                    set(reconstructed[left]["edges"])
                    & set(reconstructed[right]["edges"])
                )
                <= 17
                * len(
                    set(reconstructed[left]["edges"])
                    | set(reconstructed[right]["edges"])
                )
            ),
        }
        for left, right in pairs
    ]
    common_core = len(
        set.intersection(
            *(set(item["two_core_rows"]) for item in reconstructed)
        )
    )
    parameter_key: list[int] = []
    for item in selected:
        parameters = item["parameters"]
        if item["family"] == "mutual-knn":
            parameter_key.append(int(parameters["neighbor_count"]))
        elif item["family"] == "fixed-radius":
            parameter_key.append(
                struct.unpack(
                    ">Q", struct.pack(">d", float(parameters["radius"]))
                )[0]
            )
        else:
            parameter_key.extend(
                (
                    int(parameters["neighbor_count"]),
                    int(parameters["minimum_shared_neighbors"]),
                )
            )
    spread = max(edges) - min(edges)
    numerator = sum(abs(2 * edge - 294) for edge in edges)
    return {
        "edge_count_minimum": min(edges),
        "edge_count_maximum": max(edges),
        "edge_count_spread": spread,
        "edge_count_ratio": max(edges) / min(edges),
        "mean_degree_target_deviation_sum": sum(
            abs(2.0 * edge / 49.0 - 6.0) for edge in edges
        ),
        "mean_degree_target_deviation_numerator": numerator,
        "largest_component_vertex_count_spread": max(largest) - min(largest),
        "two_core_vertex_count_spread": max(cores) - min(cores),
        "common_two_core_intersection_count": common_core,
        "component_count_sum": sum(
            int(item["component_count"]) for item in selected
        ),
        "pairwise": pairwise,
        "pairwise_edge_sets_must_differ": True,
        "pairwise_edge_jaccard_at_most_0_85": True,
        "lexicographic_objective": [
            spread,
            numerator,
            -common_core,
            sum(int(item["component_count"]) for item in selected),
            parameter_key,
        ],
        "jaccard_used_as_objective": False,
    }


def _selector_projection(*, passing: bool = True) -> dict[str, object]:
    selected = [
        _candidate_projection(family, f"selector-{family}")
        for family in P4.FAMILY_ORDER
    ]
    audit = {
        "generated_candidate_counts": {family: 1 for family in P4.FAMILY_ORDER},
        "per_graph_eligible_candidate_counts": {
            family: int(passing) for family in P4.FAMILY_ORDER
        },
        "per_graph_rejection_reason_counts": {},
        "all_candidate_projection_sha256": "1" * 64,
        "per_graph_decision_count": 3,
        "all_per_graph_decisions_sha256": "2" * 64,
        "triplets_considered": int(passing),
        "triplet_rejection_reason_counts": {},
        "all_triplet_decisions_sha256": "3" * 64,
        "eligible_triplets": int(passing),
        "radius_unique_finite_distance_count": 1,
        "radius_budget_eligible_distance_count": 1,
        "radius_distance_scan_sha256": "4" * 64,
        "radius_zero_pair_count": 0,
        "radius_float64_uint64_order": True,
        "radius_budget_eligible_zero_unrepresentable": False,
    }
    measurements = _triplet_measurements_projection(selected) if passing else None
    return {
        "projection_schema_version": "spirallens.p4-selector-projection.v0.1",
        "state": "pass" if passing else "insufficient",
        "reason": "ok" if passing else "no-eligible-three-family-triplet",
        "selector_input": {
            "input_type": "GraphInput-plus-oriented-domain-faces-only",
            "graph_input_fingerprint_sha256": "5" * 64,
            "vertex_order_sha256": "6" * 64,
            "state_sha256": "7" * 64,
            "oriented_faces_sha256": "8" * 64,
            "case_object_accepted": False,
            "truth_object_accepted": False,
            "field_object_accepted": False,
            "core_object_accepted": False,
        },
        "selector_audit": audit,
        "selected": selected if passing else None,
        "objective": measurements["lexicographic_objective"] if passing else None,
        "triplet_measurements": measurements,
        "field_read": False,
        "core_read": False,
        "holonomy_read": False,
        "phase_read": False,
        "winding_read": False,
        "charge_read": False,
        "pythia_terminal_candidate_values_read": False,
    }


def _eligible_alternate_selector(
    actual: dict[str, object],
) -> dict[str, object]:
    """Build a self-consistent eligible-looking selector that is not the winner."""

    alternate = copy.deepcopy(actual)
    selected = alternate["selected"]
    structural_keys = (
        "canonical_edges",
        "edge_fingerprint_sha256",
        "component_labels_sha256",
        "degree_sha256",
        "two_core_mask_sha256",
        "edge_count",
        "mean_degree",
        "component_count",
        "largest_component_vertex_count",
        "two_core_vertex_count",
        "cycle_rank",
    )
    left_values = {key: copy.deepcopy(selected[0][key]) for key in structural_keys}
    right_values = {key: copy.deepcopy(selected[1][key]) for key in structural_keys}
    for key in structural_keys:
        selected[0][key] = right_values[key]
        selected[1][key] = left_values[key]
    selected[0]["graph_fingerprint_sha256"] = P4.canonical_json_sha256(
        selected[0]
    )
    selected[1]["graph_fingerprint_sha256"] = P4.canonical_json_sha256(
        selected[1]
    )
    measurements = _triplet_measurements_projection(selected)
    alternate["triplet_measurements"] = measurements
    alternate["objective"] = measurements["lexicographic_objective"]
    assert P4._validate_selector_projection(alternate) == alternate
    assert alternate != actual
    return alternate


def _confirmation_structural(
    selector: dict[str, object],
    *,
    passing: bool = True,
    edge_shift_offset: int = 0,
) -> dict[str, object]:
    selected = [
        _candidate_projection(
            family,
            f"confirmation-{family}",
            edge_shift_offset=edge_shift_offset,
        )
        for family in P4.FAMILY_ORDER
    ]
    if not passing:
        selected[0] = _candidate_projection(
            "mutual-knn",
            "confirmation-mutual-knn-insufficient",
            edge_count=50,
            largest=40,
            core=30,
            cycle_rank=0,
            matched=(),
        )
    for item, sealed in zip(selected, selector["selected"], strict=True):
        item["parameters"] = copy.deepcopy(sealed["parameters"])
        item["float64_parameter_big_endian_bits"] = copy.deepcopy(
            sealed["float64_parameter_big_endian_bits"]
        )
    return {
        "state": "pass" if passing else "insufficient",
        "reason": "ok" if passing else "fixed-triplet-failed-confirmation-support",
        "selected": selected,
        "triplet_measurements": _triplet_measurements_projection(selected),
        "selector_rerun": False,
    }


def _algebraic_projection() -> dict[str, object]:
    return {
        "pure_so2_gauge": {
            "state": "pass",
            "error_cycles": 0.0,
            "coordinate_law_error": 0.0,
            "coordinate_law_tolerance": 1e-8,
            "receipt_sha256": "9" * 64,
        },
        "orientation_reversal": {
            "state": "pass",
            "error_cycles": 0.0,
            "receipt_sha256": "a" * 64,
        },
    }


def _attempted_control_row(
    control_id: str,
    observations: list[dict[str, object]],
    **extras: object,
) -> dict[str, object]:
    contract = next(
        item
        for item in P4._control_contracts_document()
        if item["control_id"] == control_id
    )
    expected = P4.EXPECTED_RAW_CONTROL_STATES[control_id]
    return {
        "control_id": control_id,
        "attempted": True,
        "expected_raw_state": expected,
        "raw_state": expected,
        "control_verdict": "pass",
        "control_contract_sha256": P4.canonical_json_sha256(contract),
        "required_cell_count": len(contract["required_cell_ids"]),
        "required_cell_ids_sha256": P4.canonical_json_sha256(
            contract["required_cell_ids"]
        ),
        "required_span_count": len(contract["required_span_ids"]),
        "required_span_ids_sha256": P4.canonical_json_sha256(
            contract["required_span_ids"]
        ),
        "required_observation_count": len(contract["required_observation_ids"]),
        "required_observation_ids_sha256": P4.canonical_json_sha256(
            contract["required_observation_ids"]
        ),
        "observations": observations,
        **extras,
    }


def _attempted_controls(
    confirmation_matrix: dict[str, object],
    structural: dict[str, object],
    selector: dict[str, object],
) -> list[dict[str, object]]:
    threshold = 1e-8
    controls: dict[str, dict[str, object]] = {}
    controls["known_positive_connection"] = _attempted_control_row(
        "known_positive_connection",
        [],
        observed_cell_count=18,
        worst_error_cycles=0.0,
        oracle_and_null_threshold_cycles=threshold,
    )
    controls["zero_holonomy_finite_amplitude_null"] = _attempted_control_row(
        "zero_holonomy_finite_amplitude_null",
        [],
        observed_cell_count=18,
        worst_error_cycles=0.0,
        oracle_and_null_threshold_cycles=threshold,
        nuisance_diagnostics={
            "definition": "no_core_finite_loop_boundary_amplitude",
            "amplitude_floor": 1e-12,
            "minimum_loop_boundary_amplitude": 1.0,
            "finite": True,
            "passes": True,
        },
    )
    controls["radial_amplitude_depression_without_holonomy"] = _attempted_control_row(
        "radial_amplitude_depression_without_holonomy",
        [],
        observed_cell_count=18,
        worst_error_cycles=0.0,
        oracle_and_null_threshold_cycles=threshold,
        nuisance_diagnostics={
            "definition": "fixed_null_depressed_center_finite_loop_boundary",
            "amplitude_floor": 1e-12,
            "center_amplitude_count": 3,
            "maximum_center_amplitude": 0.0,
            "minimum_loop_boundary_amplitude": 1.0,
            "finite": True,
            "passes": True,
        },
    )
    controls["pure_so2_gauge"] = _attempted_control_row(
        "pure_so2_gauge",
        [
            {
                "observation_id": "pure_so2_gauge|procrustes-connection",
                "state": "pass",
                "angle_error_radians": 0.0,
                "angle_tolerance_radians": 1e-8,
                "residual_frobenius": 0.0,
                "residual_tolerance": 1e-8,
            },
            {
                "observation_id": "pure_so2_gauge|local-frame-gauge",
                "state": "pass",
                "phase_total_gauge_delta_cycles": 0.0,
                "phase_total_tolerance_cycles": 1e-8,
                "coordinate_law_error": 0.0,
                "coordinate_law_tolerance": 1e-8,
                "receipt_sha256": "b" * 64,
            },
        ],
    )
    controls["degree_preserving_rewire"] = _attempted_control_row(
        "degree_preserving_rewire",
        [
            P4._derive_canonical_rewire_observation(
                P4._reconstruct_canonical_graph(
                    item["canonical_edges"], label="fixture rewire"
                )["edges"],
                family=str(item["family"]),
            )
            for item in selector["selected"]
        ],
    )
    controls["amplitude_label_permutation"] = _attempted_control_row(
        "amplitude_label_permutation",
        [
            {
                "observation_id": f"amplitude_label_permutation|{cycle_class}",
                "state": "pass",
                "absolute_error_cycles": 0.0,
                "tolerance_cycles": 1e-8,
                "amplitude_multiset_exact": True,
                "transformation_nonidentity": True,
            }
            for cycle_class in P4.CYCLE_CLASS_ORDER
        ],
    )
    controls["orientation_reversal"] = _attempted_control_row(
        "orientation_reversal",
        [
            {
                "observation_id": f"orientation_reversal|{cycle_class}",
                "state": "pass",
                "error_cycles": 0.0,
                "tolerance_cycles": 1e-8,
                "receipt_sha256": "c" * 64,
            }
            for cycle_class in P4.CYCLE_CLASS_ORDER
        ],
    )
    controls["density_warp_confirmation"] = _attempted_control_row(
        "density_warp_confirmation",
        [
            {
                "observation_id": (
                    "density_warp_confirmation|fixed-triplet-structural-support"
                ),
                "state": "pass",
                "confirmation_structural_sha256": P4.canonical_json_sha256(
                    structural
                ),
            }
        ],
        confirmation_matrix_sha256=P4.canonical_json_sha256(confirmation_matrix),
    )
    invariant_fields = {
        "joint_vertex_permutation": "vertex_id_edge_content_preserved",
        "ambient_orthogonal_transform": "canonical_adjacency_preserved",
        "global_norm_scaling": "canonical_adjacency_preserved_with_radius_covariance",
    }
    selected_by_family = {
        item["family"]: item for item in selector["selected"]
    }
    for control_id, field in invariant_fields.items():
        observations: list[dict[str, object]] = []
        for family in P4.FAMILY_ORDER:
            selected_item = selected_by_family[family]
            base_edges = {
                tuple(edge) for edge in selected_item["canonical_edges"]
            }
            if control_id == "joint_vertex_permutation":
                base_vertex_ids = list(range(49))
                transformed_vertex_ids = list(reversed(base_vertex_ids))
                transformed_edges = {
                    tuple(sorted((48 - right, 48 - left)))
                    for left, right in base_edges
                }
                base_content = P4._row_edge_content_sha256(
                    P4._vertex_id_edges_from_rows(
                        base_edges, base_vertex_ids
                    )
                )
                transformed_content = P4._row_edge_content_sha256(
                    P4._vertex_id_edges_from_rows(
                        transformed_edges, transformed_vertex_ids
                    )
                )
                vertex_evidence: dict[str, object] = {
                    "base_vertex_ids": base_vertex_ids,
                    "base_vertex_order_sha256": P4.array_sha256(
                        np.asarray(base_vertex_ids, dtype="<i8")
                    ),
                    "transformed_vertex_ids": transformed_vertex_ids,
                    "transformed_vertex_order_sha256": P4.array_sha256(
                        np.asarray(transformed_vertex_ids, dtype="<i8")
                    ),
                }
            else:
                transformed_edges = set(base_edges)
                base_content = P4._row_edge_content_sha256(base_edges)
                transformed_content = P4._row_edge_content_sha256(
                    transformed_edges
                )
                vertex_evidence = {}
            transformed_graph = P4._reconstruct_canonical_graph(
                [list(edge) for edge in sorted(transformed_edges)],
                label="fixture transformed graph",
            )
            observations.append(
                {
                    "observation_id": f"{control_id}|{family}",
                    "state": "pass",
                    field: True,
                    **vertex_evidence,
                    "transformed_canonical_edges": [
                        list(edge) for edge in sorted(transformed_edges)
                    ],
                    "base_edge_content_sha256": base_content,
                    "transformed_edge_content_sha256": transformed_content,
                    "base_edge_order_sha256": selected_item[
                        "edge_fingerprint_sha256"
                    ],
                    "transformed_edge_order_sha256": transformed_graph[
                        "edge_fingerprint_sha256"
                    ],
                    "sealed_family_edge_order_sha256": selected_item[
                        "edge_fingerprint_sha256"
                    ],
                    "receipt_equality_scope": (
                        "constructed-graph-receipt-edge-equality-only"
                    ),
                }
            )
        controls[control_id] = _attempted_control_row(
            control_id,
            observations,
        )
    collapsed_edges = [[row, row + 1] for row in range(48)]
    collapsed_graph = P4._reconstruct_canonical_graph(
        collapsed_edges, label="fixture collapsed"
    )
    controls["collapsed_cycleless_phantom"] = _attempted_control_row(
        "collapsed_cycleless_phantom",
        [
            {
                "observation_id": "collapsed_cycleless_phantom|path-graph",
                "state": "insufficient",
                "edge_count": 48,
                "component_count": 1,
                "largest_component_vertex_count": 49,
                "two_core_vertex_count": 0,
                "cycle_rank": 0,
                "edge_fingerprint_sha256": collapsed_graph[
                    "edge_fingerprint_sha256"
                ],
                "canonical_edges": collapsed_edges,
                "state_sha256": "e" * 64,
            },
            {
                "observation_id": "collapsed_cycleless_phantom|central-binding",
                "state": "insufficient",
                "matched": False,
                "binding_fingerprint_sha256": "",
            },
            {
                "observation_id": "collapsed_cycleless_phantom|wide-binding",
                "state": "insufficient",
                "matched": False,
                "binding_fingerprint_sha256": "",
            },
        ],
    )
    controls["field_only_shuffle"] = _attempted_control_row(
        "field_only_shuffle",
        [
            {
                "observation_id": f"field_only_shuffle|{cell_id}",
                "state": "pass",
                "base_total_cycles": 1.0,
                "shuffled_total_cycles": -1.0,
                "sign_reversal_error_cycles": 0.0,
                "tolerance_cycles": 1e-8,
            }
            for cell_id in P4._required_cell_ids("confirmation", ("positive",))
        ],
    )
    for control_id, reason in (
        ("zero_amplitude", "boundary_amplitude_at_or_below_floor"),
        ("low_coherence", "boundary_coherence_at_or_below_floor"),
    ):
        controls[control_id] = _attempted_control_row(
            control_id,
            [
                {
                    "observation_id": f"{control_id}|{cycle_class}",
                    "state": "insufficient",
                    "reason_codes": [reason],
                }
                for cycle_class in P4.CYCLE_CLASS_ORDER
            ],
        )
    controls["non_orientable_frame"] = _attempted_control_row(
        "non_orientable_frame",
        [
            {
                "observation_id": "non_orientable_frame|odd-reflection",
                "state": "insufficient",
                "reason_codes": ["orientation-reversing-cycle"],
                "receipt_sha256": "f" * 64,
            },
            {
                "observation_id": "non_orientable_frame|orientable-companion",
                "state": "fail",
                "reason_codes": ["nonorientable-control-did-not-trigger"],
                "receipt_sha256": "0" * 64,
            },
        ],
    )
    return [controls[control_id] for control_id in P4.EXPECTED_RAW_CONTROL_STATES]


def _full_attempted_result(
    *,
    confirmation_edge_shift_offset: int = 0,
) -> dict[str, object]:
    selector = _selector_projection()
    calibration = _matrix_projection(
        "calibration", selected=selector["selected"]
    )
    structural = _confirmation_structural(
        selector, edge_shift_offset=confirmation_edge_shift_offset
    )
    confirmation = _matrix_projection(
        "confirmation", selected=structural["selected"]
    )
    return {
        "terminal_state": "pass",
        "reason": "model-free-evaluability-qualified",
        "calibration_selector": selector,
        "graph_selection_seal_sha256": "1" * 64,
        "threshold_seal_sha256": "2" * 64,
        "confirmation_access_seal_sha256": "3" * 64,
        "calibration_matrix": calibration,
        "calibration_algebraic_diagnostics": _algebraic_projection(),
        "calibration_scalar_inventory": {
            "absolute_oracle_or_null_error_cycles": 54,
            "graph_family_span_cycles": 6,
            "pure_so2_gauge_error_cycles": 1,
            "orientation_reversal_error_cycles": 1,
            "total": 62,
        },
        "effective_thresholds": {
            "oracle_and_null_selection_worst_error_cycles": 0.0,
            "graph_family_span_selection_worst_error_cycles": 0.0,
            "oracle_and_null_cycles": 1e-8,
            "graph_family_span_cycles": 1e-8,
            "algebraic_gauge_and_reversal_error_cycles": 1e-8,
        },
        "confirmation_structural": structural,
        "confirmation_matrix": confirmation,
        "confirmation_accessed": True,
        "graph_selection_sealed": True,
        "threshold_decision_sealed": True,
        "controls": _attempted_controls(confirmation, structural, selector),
    }


def _not_run_branch(branch: str) -> dict[str, object]:
    if branch == "selector":
        result = _not_run_result()
        result.update(
            {
                "terminal_state": "insufficient",
                "reason": "no-distinct-three-family-scale-triplet",
                "calibration_selector": _selector_projection(passing=False),
                "graph_selection_seal_sha256": "1" * 64,
                "graph_selection_sealed": True,
                "controls": P4._not_run_controls(
                    "no-distinct-three-family-scale-triplet"
                ),
            }
        )
        return result

    result = _full_attempted_result()
    result["terminal_state"] = "insufficient"
    result["confirmation_matrix"] = None
    if branch != "structural":
        result["confirmation_accessed"] = False
        result["confirmation_access_seal_sha256"] = None
        result["confirmation_structural"] = None
    if branch == "nonfinite":
        cell = result["calibration_matrix"]["cells"][0]
        cell.update(
            {
                "attempt_status": "insufficient",
                "signed_total_cycles": None,
                "absolute_error_cycles": None,
                "reason_codes": ["boundary_amplitude_at_or_below_floor"],
            }
        )
        result["calibration_scalar_inventory"] = {
            "absolute_oracle_or_null_error_cycles": 53,
            "graph_family_span_cycles": 6,
            "pure_so2_gauge_error_cycles": 1,
            "orientation_reversal_error_cycles": 1,
            "total": 61,
        }
        result["effective_thresholds"] = None
        result["reason"] = "insufficient_calibration_resolution"
        upstream = "insufficient-calibration-resolution"
    elif branch == "cap":
        cell = result["calibration_matrix"]["cells"][0]
        cell["signed_total_cycles"] = 1.041
        error = abs(1.041 - 1.0)
        cell["absolute_error_cycles"] = error
        result["calibration_matrix"]["worst_oracle_or_null_error_cycles"] = error
        result["calibration_matrix"]["graph_family_spans"][0][
            "graph_family_span_cycles"
        ] = error
        result["effective_thresholds"] = {
            "oracle_and_null_selection_worst_error_cycles": error,
            "graph_family_span_selection_worst_error_cycles": error,
            "oracle_and_null_cycles": max(1e-8, 1.25 * error),
            "graph_family_span_cycles": max(1e-8, 1.25 * error),
        }
        result["reason"] = "insufficient_calibration_resolution"
        upstream = "insufficient-calibration-resolution"
    elif branch == "algebraic":
        result["calibration_algebraic_diagnostics"]["pure_so2_gauge"].update(
            {"state": "fail", "error_cycles": 2e-8}
        )
        result["effective_thresholds"] = {
            "oracle_and_null_selection_worst_error_cycles": 0.0,
            "graph_family_span_selection_worst_error_cycles": 0.0,
            "oracle_and_null_cycles": 1e-8,
            "graph_family_span_cycles": 1e-8,
        }
        result["reason"] = "orientation-or-reverse-consistency-unresolved"
        upstream = result["reason"]
    elif branch == "structural":
        result["confirmation_structural"] = _confirmation_structural(
            result["calibration_selector"], passing=False
        )
        result["reason"] = "held-out-confirmation-structural-gate"
        upstream = result["reason"]
    else:
        raise AssertionError(f"unknown branch {branch}")
    result["controls"] = P4._not_run_controls(upstream)
    return result


def _oriented_grid_faces(side: int = 7) -> np.ndarray:
    faces: list[tuple[int, int, int]] = []
    for y in range(side - 1):
        for x in range(side - 1):
            lower_left = y * side + x
            lower_right = lower_left + 1
            upper_left = lower_left + side
            upper_right = upper_left + 1
            faces.extend(
                ((lower_left, lower_right, upper_right), (lower_left, upper_right, upper_left))
            )
    return np.asarray(faces, dtype="<i8")


def _caught_external_bundle(path: Path) -> tuple[dict[str, object], dict[str, bytes]]:
    """Build a complete all-three-seal caught-error bundle in a temp path."""

    path.mkdir()
    protocol = P4._load_canonical(
        ROOT / P4.REPOSITORY_PROTOCOL,
        label="stale protocol caught-error selector freeze",
    )
    calibration_selector = P4._recompute_calibration_selector(protocol).projection
    launch: dict[str, object] = {
        "source_commit": "a" * 40,
        "runtime": {"source_closure_sha256": "c" * 64},
    }
    launch_sha256 = P4.canonical_json_sha256(launch)
    attempt = {
        "schema_version": "spirallens.p4-exact-one-attempt.v0.1",
        "experiment_id": P4.EXPERIMENT_ID,
        "launch_sha256": launch_sha256,
        "source_commit": launch["source_commit"],
        "protocol_sha256": P4._sha256_file(ROOT / P4.REPOSITORY_PROTOCOL),
        "runner_sha256": P4._sha256_file(ROOT / P4.REPOSITORY_RUNNER),
        "identity_consumed": True,
        "official_input_access_before_attempt": False,
        "attempt_exactly_one": True,
        "terminal_at_most_one": True,
        "terminal_guaranteed": False,
        "unresolved_stage_consumes_attempt": True,
        "retry_resume_rescue_authorized": False,
    }
    attempt_source = P4.canonical_json_bytes(attempt)
    attempt_sha256 = hashlib.sha256(attempt_source).hexdigest()
    graph = {
        "schema_version": "spirallens.p4-graph-selection-seal.v0.1",
        "experiment_id": P4.EXPERIMENT_ID,
        "calibration_selector": calibration_selector,
        "field_read_before_seal": False,
        "readout_before_seal": False,
        "confirmation_accessed_before_seal": False,
        "attempt_sha256": attempt_sha256,
        "launch_sha256": launch_sha256,
    }
    graph_source = P4.canonical_json_bytes(graph)
    graph_sha256 = hashlib.sha256(graph_source).hexdigest()
    threshold = {
        "schema_version": "spirallens.p4-threshold-decision-seal.v0.1",
        "experiment_id": P4.EXPERIMENT_ID,
        "graph_selection_seal_sha256": graph_sha256,
        "decision_state": "pass",
        "calibration_scalar_inventory": {
            "absolute_oracle_or_null_error_cycles": 54,
            "graph_family_span_cycles": 6,
            "pure_so2_gauge_error_cycles": 1,
            "orientation_reversal_error_cycles": 1,
            "total": 62,
        },
        "oracle_and_null_selection_worst_error_cycles": 0.0,
        "oracle_and_null_selection_worst_metric": (
            "maximum-over-54-declared-finite-absolute-errors"
        ),
        "graph_family_span_selection_worst_error_cycles": 0.0,
        "graph_family_span_selection_worst_metric": (
            "maximum-over-6-declared-finite-spans"
        ),
        "oracle_and_null_cycles": 1e-8,
        "oracle_and_null_cap_cycles": 0.05,
        "graph_family_span_cycles": 1e-8,
        "graph_family_span_cap_cycles": 0.1,
        "algebraic_gauge_and_reversal_error_cycles": 1e-8,
        "no_clamping_applied": True,
        "confirmation_accessed_before_seal": False,
        "attempt_sha256": attempt_sha256,
        "launch_sha256": launch_sha256,
    }
    threshold_source = P4.canonical_json_bytes(threshold)
    threshold_sha256 = hashlib.sha256(threshold_source).hexdigest()
    confirmation = {
        "schema_version": "spirallens.p4-confirmation-access-seal.v0.1",
        "experiment_id": P4.EXPERIMENT_ID,
        "attempt_sha256": attempt_sha256,
        "launch_sha256": launch_sha256,
        "graph_selection_seal_sha256": graph_sha256,
        "threshold_seal_sha256": threshold_sha256,
        "confirmation_access_before_seal": False,
        "confirmation_access_authorized_after_seal": True,
    }
    confirmation_source = P4.canonical_json_bytes(confirmation)
    confirmation_sha256 = hashlib.sha256(confirmation_source).hexdigest()
    result = _not_run_result()
    result.update(
        {
            "graph_selection_sealed": True,
            "graph_selection_seal_sha256": graph_sha256,
            "threshold_decision_sealed": True,
            "threshold_seal_sha256": threshold_sha256,
            "confirmation_accessed": True,
            "confirmation_access_seal_sha256": confirmation_sha256,
        }
    )
    base = {
        "schema_version": P4.SCHEMA_VERSION,
        "experiment_id": P4.EXPERIMENT_ID,
        "protocol_sha256": P4._sha256_file(ROOT / P4.REPOSITORY_PROTOCOL),
        "runner_sha256": P4._sha256_file(ROOT / P4.REPOSITORY_RUNNER),
        "launch_sha256": launch_sha256,
        "source_commit": launch["source_commit"],
        "operator_prior_outcome_exposure": True,
        "cryptographic_unseen": False,
        "development_only": True,
        "independent": False,
        "claim_ceiling": "level_0",
        "scientific_authority": False,
        "topology_authority": False,
        "integer_output_present": False,
        "model_accessed": False,
        "network_accessed": False,
        "cache_accessed": False,
        "cache_access_scope": "model-or-subject-data-cache-only",
        "python_bytecode_cache_accessed": False,
        "python_process_pre_import_observation": (
            P4._expected_python_process_observation(ROOT, mode="--run")
        ),
        "python_process_post_import_observation": (
            P4._expected_python_process_observation(ROOT, mode="--run")
        ),
        "python_process_post_execution_observation": (
            P4._expected_python_process_observation(ROOT, mode="--run")
        ),
        "source_closure_pre_sha256": "c" * 64,
        "source_closure_post_sha256": "c" * 64,
        "pythia_raw_capture_accessed": False,
        "subject_data_accessed": False,
        "dynamic_timestamp_present": False,
    }
    terminal = P4._build_terminal(
        base=base,
        attempt_sha256=attempt_sha256,
        execution_terminal="caught_error",
        error={"class": "builtins.RuntimeError", "message_sha256": "e" * 64},
        result=result,
    )
    terminal_source = P4.canonical_json_bytes(terminal)
    sources = {
        P4.ATTEMPT_NAME: attempt_source,
        P4.GRAPH_SELECTION_SEAL_NAME: graph_source,
        P4.THRESHOLD_SEAL_NAME: threshold_source,
        P4.CONFIRMATION_ACCESS_SEAL_NAME: confirmation_source,
        P4.TERMINAL_NAME: terminal_source,
    }
    for name, source in sources.items():
        (path / name).write_bytes(source)
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        manifest = P4._build_store_manifest(descriptor, terminal=terminal)
    finally:
        os.close(descriptor)
    manifest_source = P4.canonical_json_bytes(manifest)
    (path / P4.STORE_MANIFEST_NAME).write_bytes(manifest_source)
    sources[P4.STORE_MANIFEST_NAME] = manifest_source
    return launch, sources


def test_control_contract_is_exactly_16_receipts_and_46_subobservations() -> None:
    contracts = P4._control_contracts_document()

    assert [item["control_id"] for item in contracts] == list(
        P4.EXPECTED_RAW_CONTROL_STATES
    )
    assert sum(len(item["required_observation_ids"]) for item in contracts) == 46
    by_id = {item["control_id"]: item for item in contracts}
    assert len(by_id["known_positive_connection"]["required_cell_ids"]) == 18
    assert all(
        "|no_core_null|" in value
        for value in by_id["zero_holonomy_finite_amplitude_null"]["required_cell_ids"]
    )
    assert all(
        "|fixed_null|" in value
        for value in by_id["radial_amplitude_depression_without_holonomy"][
            "required_cell_ids"
        ]
    )
    assert len(by_id["density_warp_confirmation"]["required_cell_ids"]) == 54
    assert len(by_id["field_only_shuffle"]["required_observation_ids"]) == 18


def test_exact_triplet_objective_uses_radius_bits_and_not_jaccard() -> None:
    edge_sets = _disjoint_edges()
    radius = 0.5
    candidates = (
        _candidate("mutual-knn", (("neighbor_count", 6),), edge_sets[0], "a"),
        _candidate("fixed-radius", (("radius", radius),), edge_sets[1], "b"),
        _candidate(
            "shared-neighbor",
            (("minimum_shared_neighbors", 2), ("neighbor_count", 6)),
            edge_sets[2],
            "c",
        ),
    )

    selected, measurements, audit = P4.choose_graph_triplet(candidates)

    radius_bits = struct.unpack(">Q", struct.pack(">d", radius))[0]
    assert selected == candidates
    assert measurements is not None
    assert measurements["lexicographic_objective"] == [
        0,
        0,
        -49,
        3,
        [6, radius_bits, 6, 2],
    ]
    assert measurements["jaccard_used_as_objective"] is False
    assert audit["eligible_triplets"] == 1


def test_no_eligible_triplet_has_no_winner_or_objective() -> None:
    edges = _disjoint_edges()[0]
    only_one_family = (
        _candidate("mutual-knn", (("neighbor_count", 6),), edges, "a"),
    )

    selected, measurements, audit = P4.choose_graph_triplet(only_one_family)

    assert selected is None
    assert measurements is None
    assert audit["eligible_triplets"] == 0
    assert audit["triplets_considered"] == 0


def test_frozen_selector_recomputation_rejects_refreshed_alternate_winner(
    tmp_path: Path,
) -> None:
    protocol = P4._load_canonical(
        ROOT / P4.REPOSITORY_PROTOCOL,
        label="stale protocol selector freeze",
    )
    actual = P4._recompute_calibration_selector(protocol).projection
    assert actual["state"] == "pass"
    alternate = _eligible_alternate_selector(actual)

    refreshed_downstream = {
        "calibration_selector": alternate,
        "graph_selection_seal_sha256": P4.canonical_json_sha256(alternate),
        "downstream_values_sha256": P4.canonical_json_sha256(
            {"selector": alternate, "terminal_state": "pass"}
        ),
    }
    (tmp_path / "refreshed-alternate.json").write_bytes(
        P4.canonical_json_bytes(refreshed_downstream)
    )

    with pytest.raises(P4.P4ProtocolError, match="frozen recomputation"):
        P4._require_exact_recomputed_calibration_selector(
            refreshed_downstream["calibration_selector"],
            protocol=protocol,
        )


def test_selector_radius_scan_audits_budget_out_zero_pairs(monkeypatch: pytest.MonkeyPatch) -> None:
    graph_input = P4.GraphInput(
        primary_unit_id="toy-zero-distance-selector",
        vertex_ids=np.arange(49, dtype="<i8"),
        states=np.zeros((49, 3), dtype="<f8"),
    )
    distances = np.ones((49, 49), dtype="<f8")
    np.fill_diagonal(distances, np.inf)
    distances[0, 1] = distances[1, 0] = 0.0
    monkeypatch.setattr(P4, "enumerate_structural_candidates", lambda *_args: ())
    monkeypatch.setattr(P4, "_pairwise_distances", lambda _graph_input: distances)

    result = P4.select_structural_triplet(
        graph_input,
        np.asarray(((0, 1, 2),), dtype="<i8"),
        {},
    )

    assert result["state"] == "insufficient"
    assert result["selected"] is None
    assert result["objective"] is None
    assert result["selector_audit"]["radius_zero_pair_count"] == 1
    assert result["selector_audit"]["radius_unique_finite_distance_count"] == 2
    assert result["selector_audit"]["radius_float64_uint64_order"] is True
    assert result["selector_audit"]["radius_budget_eligible_zero_unrepresentable"] is False


def test_selector_fails_closed_for_budget_eligible_zero_radius(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    graph_input = P4.GraphInput(
        primary_unit_id="toy-budget-eligible-zero-radius",
        vertex_ids=np.arange(49, dtype="<i8"),
        states=np.zeros((49, 3), dtype="<f8"),
    )
    distances = np.ones((49, 49), dtype="<f8")
    np.fill_diagonal(distances, np.inf)
    upper_rows, upper_columns = np.triu_indices(49, k=1)
    for left, right in zip(upper_rows[:100], upper_columns[:100], strict=True):
        distances[left, right] = distances[right, left] = 0.0
    monkeypatch.setattr(P4, "enumerate_structural_candidates", lambda *_args: ())
    monkeypatch.setattr(P4, "_pairwise_distances", lambda _graph_input: distances)

    with pytest.raises(P4.P4RunError, match="outside the frozen constructor domain"):
        P4.select_structural_triplet(
            graph_input,
            np.asarray(((0, 1, 2),), dtype="<i8"),
            {},
        )


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (0.0, 0.0),
        (1.25, 1.25),
        (None, None),
        (True, None),
        (-1.0, None),
        (math.inf, None),
        (math.nan, None),
        ("0.1", None),
    ],
)
def test_nonnegative_finite_scalar_is_fail_closed(value: object, expected: object) -> None:
    observed = P4._nonnegative_finite_scalar(value)
    if isinstance(expected, float):
        assert observed == expected
    else:
        assert observed is expected


def test_threshold_formula_has_no_clamp() -> None:
    assert P4._effective_threshold(0.0, cap=0.05) == (1e-8, True)
    assert P4._effective_threshold(0.04, cap=0.05) == (0.05, True)
    threshold, within = P4._effective_threshold(0.041, cap=0.05)
    assert threshold == pytest.approx(0.05125)
    assert within is False


def test_terminal_result_rejects_missing_and_unknown_root_keys() -> None:
    valid = _not_run_result()
    assert P4._normalize_result(valid) == valid

    missing = dict(valid)
    missing.pop("reason")
    with pytest.raises(P4.P4ProtocolError, match="terminal result keys differ"):
        P4._normalize_result(missing)

    unknown = {**valid, "unexpected": False}
    with pytest.raises(P4.P4ProtocolError, match="terminal result keys differ"):
        P4._normalize_result(unknown)


def test_deep_type_equality_rejects_false_as_zero() -> None:
    assert P4._type_exact_equal(False, 0) is False
    with pytest.raises(P4.P4ProtocolError):
        P4._constant({"value": False}, {"value": 0}, label="deep type")


def test_selector_rejects_impossible_rank_after_opaque_digest_refresh() -> None:
    forged = _selector_projection()
    candidate = forged["selected"][0]
    candidate["cycle_rank"] += 1
    candidate["graph_fingerprint_sha256"] = P4.canonical_json_sha256(candidate)

    with pytest.raises(P4.P4ProtocolError, match="reconstructed cycle_rank"):
        P4._validate_selector_projection(forged)


def test_invalid_branch_reason_is_closed() -> None:
    forged = _not_run_result()
    forged["reason"] = "infra-looked-fine"
    for row in forged["controls"]:
        row["upstream_reason"] = "infra-looked-fine"

    with pytest.raises(P4.P4ProtocolError, match="caught invalid reason"):
        P4._normalize_result(forged)


def test_matrix_rejects_axis_and_status_value_forgery() -> None:
    valid = _matrix_projection("calibration")
    selected = _selector_projection()["selected"]
    assert P4._validate_matrix_projection(
        valid, role="calibration", sealed_selected=selected
    ) == valid

    axis_forge = copy.deepcopy(valid)
    axis_forge["cells"][0]["case"] = "fixed_null"
    with pytest.raises(P4.P4ProtocolError, match="cell case"):
        P4._validate_matrix_projection(
            axis_forge, role="calibration", sealed_selected=selected
        )

    status_forge = copy.deepcopy(valid)
    status_forge["cells"][0]["attempt_status"] = "insufficient"
    status_forge["cells"][0]["reason_codes"] = [
        "boundary_amplitude_at_or_below_floor"
    ]
    with pytest.raises(P4.P4RunError, match="requires null values"):
        P4._validate_matrix_projection(
            status_forge, role="calibration", sealed_selected=selected
        )


def test_matrix_rejects_purpose_adjacency_true_without_sealed_edge_order() -> None:
    matrix = _matrix_projection("calibration")
    selected = _selector_projection()["selected"]
    row = matrix["purpose_adjacency_checks"][0]
    row["field_canonical_edge_order_sha256"] = "f" * 64
    matrix["purpose_adjacency_checks_sha256"] = P4.canonical_json_sha256(
        matrix["purpose_adjacency_checks"]
    )
    assert row["canonical_adjacency_equal"] is True
    assert row["canonical_edge_order_sha256_equal"] is True

    with pytest.raises(P4.P4ProtocolError, match="sealed field edge order"):
        P4._validate_matrix_projection(
            matrix, role="calibration", sealed_selected=selected
        )


def test_confirmation_matrix_binds_held_out_structural_edges_not_calibration() -> None:
    result = _full_attempted_result(confirmation_edge_shift_offset=9)
    selector_selected = result["calibration_selector"]["selected"]
    confirmation_selected = result["confirmation_structural"]["selected"]
    assert [item["edge_fingerprint_sha256"] for item in selector_selected] != [
        item["edge_fingerprint_sha256"] for item in confirmation_selected
    ]
    assert P4._normalize_result(result) == result

    forged = copy.deepcopy(result)
    calibration_by_family = {
        item["family"]: item["edge_fingerprint_sha256"]
        for item in selector_selected
    }
    row = forged["confirmation_matrix"]["purpose_adjacency_checks"][0]
    row["field_canonical_edge_order_sha256"] = calibration_by_family[row["family"]]
    row["cycle_canonical_edge_order_sha256"] = calibration_by_family[row["family"]]
    forged["confirmation_matrix"]["purpose_adjacency_checks_sha256"] = (
        P4.canonical_json_sha256(
            forged["confirmation_matrix"]["purpose_adjacency_checks"]
        )
    )

    with pytest.raises(P4.P4ProtocolError, match="sealed field edge order"):
        P4._normalize_result(forged)


def test_full_attempted_pass_is_rederived_from_persisted_payload() -> None:
    result = _full_attempted_result()

    assert P4._normalize_result(result) == result


def test_self_consistent_pass_labels_cannot_forge_numeric_control() -> None:
    forged = _full_attempted_result()
    row = next(
        item for item in forged["controls"] if item["control_id"] == "field_only_shuffle"
    )
    observation = row["observations"][0]
    observation["shuffled_total_cycles"] = 1.0
    observation["sign_reversal_error_cycles"] = 0.0
    observation["state"] = "pass"
    row["raw_state"] = "pass"
    row["control_verdict"] = "pass"

    with pytest.raises(P4.P4ProtocolError, match="recomputed error"):
        P4._normalize_result(forged)


@pytest.mark.parametrize(
    ("mutation", "terminal_state", "reason"),
    [
        ("amplitude_fail", "fail", "required-control-or-graph-span-wrong"),
        ("amplitude_insufficient", "insufficient", "required-control-unresolved"),
    ],
)
def test_full_attempted_fail_and_insufficient_folds_are_exact(
    mutation: str,
    terminal_state: str,
    reason: str,
) -> None:
    result = _full_attempted_result()
    if mutation == "amplitude_fail":
        row = next(
            item
            for item in result["controls"]
            if item["control_id"] == "amplitude_label_permutation"
        )
        observation = row["observations"][0]
        observation["absolute_error_cycles"] = 1.0
        observation["state"] = "fail"
        row["raw_state"] = "fail"
        row["control_verdict"] = "fail"
    else:
        row = next(
            item
            for item in result["controls"]
            if item["control_id"] == "amplitude_label_permutation"
        )
        observation = row["observations"][0]
        observation["absolute_error_cycles"] = None
        observation["amplitude_multiset_exact"] = False
        observation["transformation_nonidentity"] = False
        observation["state"] = "insufficient"
        row["raw_state"] = "insufficient"
        row["control_verdict"] = "insufficient"
    result["terminal_state"] = terminal_state
    result["reason"] = reason

    assert P4._normalize_result(result) == result


def test_rewire_rejects_non_degree_preserving_edges_with_true_flags() -> None:
    result = _full_attempted_result()
    row = next(
        item
        for item in result["controls"]
        if item["control_id"] == "degree_preserving_rewire"
    )
    observation = row["observations"][0]
    observation["removed_edges"] = [[0, 1], [4, 5]]
    observation["added_edges"] = [[0, 4], [1, 6]]
    assert observation["degree_preserved"] is True
    assert observation["simple_graph_verified"] is True

    with pytest.raises(P4.P4ProtocolError, match="raw-edge derivation"):
        P4._normalize_result(result)


def test_invariance_rejects_equal_forged_digests_over_unequal_raw_edges() -> None:
    result = _full_attempted_result()
    row = next(
        item
        for item in result["controls"]
        if item["control_id"] == "ambient_orthogonal_transform"
    )
    observation = row["observations"][0]
    original_edges = {
        tuple(edge) for edge in observation["transformed_canonical_edges"]
    }
    raw_edges = set(original_edges)
    raw_edges.remove(min(raw_edges))
    replacement = next(
        edge
        for edge in (
            (left, right)
            for left in range(49)
            for right in range(left + 1, 49)
        )
        if edge not in original_edges
    )
    raw_edges.add(replacement)
    observation["transformed_canonical_edges"] = [
        list(edge) for edge in sorted(raw_edges)
    ]
    forged_graph = P4._reconstruct_canonical_graph(
        observation["transformed_canonical_edges"], label="forged transformed"
    )
    forged_content = P4._row_edge_content_sha256(raw_edges)
    observation["transformed_edge_order_sha256"] = forged_graph[
        "edge_fingerprint_sha256"
    ]
    observation["base_edge_content_sha256"] = forged_content
    observation["transformed_edge_content_sha256"] = forged_content
    assert observation["canonical_adjacency_preserved"] is True

    with pytest.raises(P4.P4ProtocolError, match="edge-content derivation"):
        P4._normalize_result(result)


def test_joint_invariance_rejects_nonreversed_ids_and_forged_hashes() -> None:
    result = _full_attempted_result()
    row = next(
        item
        for item in result["controls"]
        if item["control_id"] == "joint_vertex_permutation"
    )
    observation = row["observations"][0]
    observation["transformed_vertex_ids"] = list(observation["base_vertex_ids"])
    observation["base_edge_content_sha256"] = "e" * 64
    observation["transformed_edge_content_sha256"] = "e" * 64
    assert observation["vertex_id_edge_content_preserved"] is True

    with pytest.raises(P4.P4ProtocolError, match="frozen reversed vertex ids"):
        P4._normalize_result(result)


def test_collapsed_control_rejects_non_path_tree_with_refreshed_metrics() -> None:
    result = _full_attempted_result()
    row = next(
        item
        for item in result["controls"]
        if item["control_id"] == "collapsed_cycleless_phantom"
    )
    observation = row["observations"][0]
    star = [[0, row] for row in range(1, 49)]
    reconstructed = P4._reconstruct_canonical_graph(star, label="forged tree")
    observation["canonical_edges"] = star
    for key in (
        "edge_count",
        "component_count",
        "largest_component_vertex_count",
        "two_core_vertex_count",
        "cycle_rank",
        "edge_fingerprint_sha256",
    ):
        observation[key] = reconstructed[key]

    with pytest.raises(P4.P4ProtocolError, match="exact canonical path"):
        P4._normalize_result(result)


def test_confirmation_triplet_must_reuse_sealed_selector_parameters() -> None:
    forged = _full_attempted_result()
    forged["confirmation_structural"]["selected"][0]["parameters"] = {
        "neighbor_count": 7
    }

    with pytest.raises(P4.P4ProtocolError, match="parameter binding"):
        P4._normalize_result(forged)


@pytest.mark.parametrize(
    "branch",
    ["selector", "nonfinite", "cap", "algebraic", "structural"],
)
def test_not_run_scientific_branch_table_is_exact(branch: str) -> None:
    result = _not_run_branch(branch)

    assert P4._normalize_result(result) == result


def test_not_run_branch_cannot_relabel_cap_as_algebraic() -> None:
    forged = _not_run_branch("cap")
    forged["reason"] = "orientation-or-reverse-consistency-unresolved"
    forged["controls"] = P4._not_run_controls(forged["reason"])

    with pytest.raises(P4.P4ProtocolError, match="calibration gate reason"):
        P4._normalize_result(forged)


def test_graph_and_threshold_seals_cross_bind_semantic_result() -> None:
    result = _full_attempted_result()
    protocol = P4._load_canonical(
        ROOT / P4.REPOSITORY_PROTOCOL,
        label="stale protocol graph-selection seal test",
    )
    graph_result = copy.deepcopy(result)
    graph_result["calibration_selector"] = P4._recompute_calibration_selector(
        protocol
    ).projection
    attempt_sha256 = "4" * 64
    launch_sha256 = "5" * 64
    graph_sha256 = "6" * 64
    graph_seal = {
        "schema_version": "spirallens.p4-graph-selection-seal.v0.1",
        "experiment_id": P4.EXPERIMENT_ID,
        "calibration_selector": copy.deepcopy(graph_result["calibration_selector"]),
        "field_read_before_seal": False,
        "readout_before_seal": False,
        "confirmation_accessed_before_seal": False,
        "attempt_sha256": attempt_sha256,
        "launch_sha256": launch_sha256,
    }
    P4._validate_graph_selection_seal(
        graph_seal,
        result=graph_result,
        protocol=protocol,
        attempt_sha256=attempt_sha256,
        launch_sha256=launch_sha256,
    )
    threshold_seal = P4._expected_threshold_seal_document(
        result,
        attempt_sha256=attempt_sha256,
        launch_sha256=launch_sha256,
        graph_selection_sha256=graph_sha256,
    )
    P4._validate_threshold_seal(
        threshold_seal,
        result=result,
        attempt_sha256=attempt_sha256,
        launch_sha256=launch_sha256,
        graph_selection_sha256=graph_sha256,
    )

    graph_forge = copy.deepcopy(graph_seal)
    graph_forge["calibration_selector"]["selected"][0][
        "graph_fingerprint_sha256"
    ] = "7" * 64
    with pytest.raises(P4.P4ProtocolError, match="frozen recomputation"):
        P4._validate_graph_selection_seal(
            graph_forge,
            result=graph_result,
            protocol=protocol,
            attempt_sha256=attempt_sha256,
            launch_sha256=launch_sha256,
        )

    cap_result = _not_run_branch("cap")
    with pytest.raises(P4.P4ProtocolError, match="result cross-binding"):
        P4._validate_threshold_seal(
            threshold_seal,
            result=cap_result,
            attempt_sha256=attempt_sha256,
            launch_sha256=launch_sha256,
            graph_selection_sha256=graph_sha256,
        )


def test_git_queries_use_absolute_binary_and_closed_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed: dict[str, object] = {}

    def fake_run(argv: object, **kwargs: object) -> object:
        observed["argv"] = argv
        observed.update(kwargs)
        return types.SimpleNamespace(returncode=0, stdout=b"", stderr=b"")

    monkeypatch.setattr(P4.subprocess, "run", fake_run)

    assert P4._git_bytes(ROOT, "status", "--porcelain=v1", "-z") == b""
    assert tuple(observed["argv"][: len(P4.GIT_ARGV_PREFIX)]) == P4.GIT_ARGV_PREFIX
    assert observed["env"] == {
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_CONFIG_SYSTEM": "/dev/null",
        "GIT_NO_REPLACE_OBJECTS": "1",
        "GIT_OPTIONAL_LOCKS": "0",
        "LANG": "C",
        "LC_ALL": "C",
    }
    assert "HOME" not in observed["env"]


def test_git_fsmonitor_repository_setting_cannot_execute(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    sentinel = tmp_path / "fsmonitor-executed"
    hook = tmp_path / "fsmonitor.sh"
    hook.write_text(
        "#!/bin/sh\n: > " + repr(str(sentinel)) + "\nexit 1\n",
        encoding="utf-8",
    )
    hook.chmod(0o755)
    P4._git_bytes(repo, "init", "-q")
    P4._git_bytes(repo, "config", "core.fsmonitor", str(hook))
    (repo / "tracked.txt").write_text("tracked\n", encoding="utf-8")
    P4._git_bytes(repo, "add", "tracked.txt")

    P4._git_bytes(repo, "status", "--porcelain=v1", "-z")

    assert not sentinel.exists()


def test_exact_argv_isolated_from_existing_project_bytecode() -> None:
    argv = P4._exact_run_argv(ROOT)
    prefix = f"pycache_prefix={P4._python_bytecode_cache_prefix(ROOT)}"

    assert argv[1:5] == ["-I", "-B", "-X", prefix]
    P4._validate_exact_run_argv(argv, repo_root=ROOT, label="test argv")
    assert str(ROOT / "src") not in prefix


def test_expected_run_and_prepare_process_flags_are_exact() -> None:
    run = P4._expected_python_process_observation(ROOT, mode="--run")
    prepare = P4._expected_python_process_observation(
        ROOT, mode="--prepare-launch"
    )

    assert run["orig_argv"] == P4._exact_run_argv(ROOT)
    assert run["isolated"] == 1
    assert run["dont_write_bytecode_flag"] == 1
    assert run["dont_write_bytecode_runtime"] is True
    assert run["xoptions"] == {"pycache_prefix": run["pycache_prefix"]}
    assert prepare["orig_argv"][-1] == "--prepare-launch"
    assert prepare["orig_argv"][1:5] == run["orig_argv"][1:5]


@pytest.mark.parametrize("variant", ["omitted", "mismatched-prefix"])
def test_raw_run_guard_rejects_python_flag_bypass(
    tmp_path: Path,
    variant: str,
) -> None:
    python = str(ROOT / ".venv" / "bin" / "python")
    if variant == "omitted":
        argv = [python, str(RUNNER_PATH), "--run"]
    else:
        argv = [
            python,
            "-I",
            "-B",
            "-X",
            f"pycache_prefix={tmp_path / 'wrong-cache'}",
            str(RUNNER_PATH),
            "--run",
        ]

    completed = subprocess.run(
        argv,
        cwd=ROOT,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    assert completed.returncode != 0
    assert "Python process flags/cache boundary differ from freeze" in completed.stderr


def test_dedicated_pycache_prefix_must_remain_absent(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    prefix = P4._require_python_bytecode_cache_absent(repo)
    prefix.mkdir()

    with pytest.raises(P4.P4ProtocolError, match="bytecode cache prefix"):
        P4._require_python_bytecode_cache_absent(repo)


def test_loaded_module_origin_is_bound_regular_nlink_one_source(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    source = repo / "src" / "spirallens" / "bound.py"
    source.parent.mkdir(parents=True)
    source.write_text("VALUE = 1\n", encoding="utf-8")
    relative = source.relative_to(repo).as_posix()
    protocol = {
        "source_bindings": {
            "runtime_files": [
                {"path": relative, "sha256": hashlib.sha256(source.read_bytes()).hexdigest()}
            ]
        }
    }
    module = types.ModuleType("spirallens.bound")
    module.__file__ = str(source)
    module.__spec__ = types.SimpleNamespace(origin=str(source))
    modules = {"spirallens.bound": module}

    assert P4._loaded_spirallens_source_manifest(
        repo, protocol, modules=modules
    ) == [
        {
            "module": "spirallens.bound",
            "path": relative,
            "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        }
    ]

    alias = source.with_name("alias.py")
    os.link(source, alias)
    with pytest.raises(P4.P4ProtocolError, match="nlink=1"):
        P4._loaded_spirallens_source_manifest(repo, protocol, modules=modules)


def test_loaded_module_origin_and_file_must_be_same_source(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    origin = repo / "src" / "spirallens" / "origin.py"
    module_file = origin.with_name("file.py")
    origin.parent.mkdir(parents=True)
    origin.write_text("ORIGIN = 1\n", encoding="utf-8")
    module_file.write_text("FILE = 1\n", encoding="utf-8")
    relative = origin.relative_to(repo).as_posix()
    protocol = {
        "source_bindings": {
            "runtime_files": [
                {
                    "path": relative,
                    "sha256": hashlib.sha256(origin.read_bytes()).hexdigest(),
                }
            ]
        }
    }
    module = types.ModuleType("spirallens.mismatch")
    module.__file__ = str(module_file)
    module.__spec__ = types.SimpleNamespace(origin=str(origin))

    with pytest.raises(P4.P4ProtocolError, match="origin and __file__ differ"):
        P4._loaded_spirallens_source_manifest(
            repo, protocol, modules={"spirallens.mismatch": module}
        )


def test_loaded_module_rejects_pyc_origin(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    source = repo / "src" / "spirallens" / "bound.py"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"pyc")
    relative = source.relative_to(repo).as_posix()
    protocol = {
        "source_bindings": {
            "runtime_files": [
                {
                    "path": relative,
                    "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                }
            ]
        }
    }
    module = types.ModuleType("spirallens.bound")
    pyc = source.with_suffix(".pyc")
    pyc.write_bytes(b"pyc")
    module.__file__ = str(pyc)
    module.__spec__ = types.SimpleNamespace(origin=str(pyc))

    with pytest.raises(P4.P4ProtocolError, match="frozen .py source"):
        P4._loaded_spirallens_source_manifest(
            repo, protocol, modules={"spirallens.bound": module}
        )


def test_runtime_source_paths_reject_traversal_and_unused_declaration(
    tmp_path: Path,
) -> None:
    traversal = {
        "source_bindings": {
            "runtime_files": [
                {"path": "src/spirallens/../escape.py", "sha256": "a" * 64}
            ]
        }
    }
    with pytest.raises(P4.P4ProtocolError, match="not canonical"):
        P4._runtime_source_bindings(traversal)

    repo = tmp_path / "repo"
    source_root = repo / "src" / "spirallens"
    source_root.mkdir(parents=True)
    used = source_root / "used.py"
    unused = source_root / "unused.py"
    used.write_text("USED = 1\n", encoding="utf-8")
    unused.write_text("UNUSED = 1\n", encoding="utf-8")
    protocol = {
        "source_bindings": {
            "runtime_files": [
                {
                    "path": path.relative_to(repo).as_posix(),
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                }
                for path in (used, unused)
            ]
        }
    }
    module = types.ModuleType("spirallens.used")
    module.__file__ = str(used)
    module.__spec__ = types.SimpleNamespace(origin=str(used))

    with pytest.raises(P4.P4ProtocolError, match="source set differs"):
        P4._loaded_spirallens_source_manifest(
            repo, protocol, modules={"spirallens.used": module}
        )


def test_current_loaded_source_closure_is_protocol_bound(tmp_path: Path) -> None:
    script = r"""
import importlib.util
import json
import sys
from pathlib import Path

root = Path(sys.argv[1]).resolve()
runner = root / "scripts" / "run_p4_graph_evaluability_calibration.py"
spec = importlib.util.spec_from_file_location("p4_fresh_closure", runner)
if spec is None or spec.loader is None:
    raise SystemExit("cannot construct fresh runner import")
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
protocol = module._load_canonical(
    root / module.REPOSITORY_PROTOCOL, label="frozen protocol source bindings"
)
closure = module._source_closure_snapshot(root, protocol)
declared = {
    item["path"] for item in protocol["source_bindings"]["runtime_files"]
}
loaded = {item["path"] for item in closure["loaded_spirallens_sources"]}
if not loaded or loaded != declared:
    raise SystemExit("fresh loaded source set differs from frozen declarations")
print(json.dumps({
    "declared_count": len(declared),
    "loaded_count": len(loaded),
    "git_binary": closure["git_binary"]["path"],
    "git_argv_prefix": closure["git_argv_prefix"],
    "python_bytecode_cache_prefix_absent": (
        closure["python_bytecode_cache_prefix_absent"]
    ),
}, sort_keys=True))
"""
    bytecode_prefix = (tmp_path / "python-cache").resolve()
    assert not bytecode_prefix.exists()
    completed = subprocess.run(
        (
            sys.executable,
            "-I",
            "-B",
            "-X",
            f"pycache_prefix={bytecode_prefix}",
            "-c",
            script,
            str(ROOT),
        ),
        check=True,
        cwd=tmp_path,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    assert not bytecode_prefix.exists()
    observed = json.loads(completed.stdout)
    assert observed["loaded_count"] == observed["declared_count"] > 0
    assert observed["git_binary"] == "/usr/bin/git"
    assert tuple(observed["git_argv_prefix"]) == P4.GIT_ARGV_PREFIX
    assert observed["python_bytecode_cache_prefix_absent"] is True


def test_control_verdict_distinguishes_unresolved_from_wrong() -> None:
    controls = [
        {"control_id": control_id, "control_verdict": "pass"}
        for control_id in P4.EXPECTED_RAW_CONTROL_STATES
    ]
    controls[0]["control_verdict"] = "insufficient"

    state, reason = P4._fold_attempted_controls(
        controls, oracle_ok=True, span_ok=True
    )

    assert state == "insufficient"
    assert reason == "known-positive-or-required-null-unresolved"


def test_collapsed_control_is_a_rank_one_radius_path() -> None:
    graph_input = P4.GraphInput(
        primary_unit_id="toy-collapsed-control-source",
        vertex_ids=np.arange(49, dtype="<i8"),
        states=np.zeros((49, 3), dtype="<f8"),
    )
    protocol = {"cycle_classes": {"central": [2, 2, 4, 4], "wide": [1, 1, 5, 5]}}

    result = P4._collapsed_cycleless_control(
        graph_input,
        _oriented_grid_faces(),
        protocol,
    )

    assert result["observed_state"] == "insufficient"
    assert [item["observation_id"] for item in result["observations"]] == [
        "collapsed_cycleless_phantom|path-graph",
        "collapsed_cycleless_phantom|central-binding",
        "collapsed_cycleless_phantom|wide-binding",
    ]
    assert result["observations"][0]["edge_count"] == 48
    assert result["observations"][0]["cycle_rank"] == 0
    assert result["observations"][0]["two_core_vertex_count"] == 0
    assert result["observations"][1]["matched"] is False
    assert result["observations"][2]["matched"] is False


def test_official_launch_and_terminal_are_not_created_by_unit_import() -> None:
    assert not (ROOT / P4.REPOSITORY_LAUNCH).exists()
    assert not (ROOT / P4.REPOSITORY_ATTEMPT).exists()
    assert not (ROOT / P4.REPOSITORY_TERMINAL).exists()


def test_external_manifest_validates_exact_members_and_three_seal_chain(
    tmp_path: Path,
) -> None:
    store = tmp_path / "store"
    launch, sources = _caught_external_bundle(store)

    observed = P4._validate_external_bundle_path(
        store, repo_root=ROOT, launch=launch
    )

    assert observed["attempt_sha256"] == hashlib.sha256(
        sources[P4.ATTEMPT_NAME]
    ).hexdigest()
    assert observed["terminal_sha256"] == hashlib.sha256(
        sources[P4.TERMINAL_NAME]
    ).hexdigest()
    assert observed["manifest_sha256"] == hashlib.sha256(
        sources[P4.STORE_MANIFEST_NAME]
    ).hexdigest()


def test_caught_error_bundle_rejects_fully_rehashed_alternate_selector(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = tmp_path / "store"
    launch, _sources = _caught_external_bundle(store)

    graph = P4._load_canonical(
        store / P4.GRAPH_SELECTION_SEAL_NAME,
        label="caught alternate graph seal",
    )
    graph["calibration_selector"] = _eligible_alternate_selector(
        graph["calibration_selector"]
    )
    graph_source = P4.canonical_json_bytes(graph)
    graph_sha256 = hashlib.sha256(graph_source).hexdigest()
    (store / P4.GRAPH_SELECTION_SEAL_NAME).write_bytes(graph_source)

    threshold = P4._load_canonical(
        store / P4.THRESHOLD_SEAL_NAME,
        label="caught alternate threshold seal",
    )
    threshold["graph_selection_seal_sha256"] = graph_sha256
    threshold_source = P4.canonical_json_bytes(threshold)
    threshold_sha256 = hashlib.sha256(threshold_source).hexdigest()
    (store / P4.THRESHOLD_SEAL_NAME).write_bytes(threshold_source)

    confirmation = P4._load_canonical(
        store / P4.CONFIRMATION_ACCESS_SEAL_NAME,
        label="caught alternate confirmation seal",
    )
    confirmation["graph_selection_seal_sha256"] = graph_sha256
    confirmation["threshold_seal_sha256"] = threshold_sha256
    confirmation_source = P4.canonical_json_bytes(confirmation)
    confirmation_sha256 = hashlib.sha256(confirmation_source).hexdigest()
    (store / P4.CONFIRMATION_ACCESS_SEAL_NAME).write_bytes(confirmation_source)

    terminal = P4._load_canonical(
        store / P4.TERMINAL_NAME,
        label="caught alternate terminal",
    )
    terminal["result"]["graph_selection_seal_sha256"] = graph_sha256
    terminal["result"]["threshold_seal_sha256"] = threshold_sha256
    terminal["result"]["confirmation_access_seal_sha256"] = confirmation_sha256
    terminal_source = P4.canonical_json_bytes(terminal)
    terminal_sha256 = hashlib.sha256(terminal_source).hexdigest()
    (store / P4.TERMINAL_NAME).write_bytes(terminal_source)

    manifest = P4._load_canonical(
        store / P4.STORE_MANIFEST_NAME,
        label="caught alternate manifest",
    )
    for record in manifest["members"]:
        member_source = (store / record["name"]).read_bytes()
        record["sha256"] = hashlib.sha256(member_source).hexdigest()
        record["size_bytes"] = len(member_source)
    manifest["terminal_sha256"] = terminal_sha256
    (store / P4.STORE_MANIFEST_NAME).write_bytes(
        P4.canonical_json_bytes(manifest)
    )

    with pytest.raises(P4.P4ProtocolError, match="frozen recomputation"):
        P4._validate_external_bundle_path(store, repo_root=ROOT, launch=launch)

    protocol = P4._load_canonical(
        ROOT / P4.REPOSITORY_PROTOCOL,
        label="stale protocol repair rejection",
    )
    monkeypatch.setattr(
        P4,
        "validate_committed_launch",
        lambda _root, *, projection_repair: (protocol, launch),
    )
    monkeypatch.setattr(P4, "EXTERNAL_STAGE", tmp_path / "absent-stage")
    monkeypatch.setattr(P4, "EXTERNAL_STORE", store)
    monkeypatch.setattr(P4, "REPOSITORY_ATTEMPT", tmp_path / "repair-attempt.json")
    monkeypatch.setattr(P4, "REPOSITORY_TERMINAL", tmp_path / "repair-terminal.json")
    with pytest.raises(P4.P4ProtocolError, match="frozen recomputation"):
        P4.repair_repository_projections(ROOT)
    assert not (tmp_path / "repair-attempt.json").exists()
    assert not (tmp_path / "repair-terminal.json").exists()


@pytest.mark.parametrize(
    "member",
    [
        P4.GRAPH_SELECTION_SEAL_NAME,
        P4.THRESHOLD_SEAL_NAME,
        P4.CONFIRMATION_ACCESS_SEAL_NAME,
    ],
)
def test_external_manifest_rejects_each_mutated_seal(
    tmp_path: Path,
    member: str,
) -> None:
    store = tmp_path / "store"
    launch, _sources = _caught_external_bundle(store)
    source = (store / member).read_bytes()
    (store / member).write_bytes(source[:-1] + bytes([source[-1] ^ 1]))

    with pytest.raises(P4.P4ProtocolError):
        P4._validate_external_bundle_path(store, repo_root=ROOT, launch=launch)


def test_external_manifest_rejects_extra_member_and_chain_rewrite(
    tmp_path: Path,
) -> None:
    extra_store = tmp_path / "extra-store"
    launch, _sources = _caught_external_bundle(extra_store)
    (extra_store / "unexpected.json").write_bytes(P4.canonical_json_bytes({"x": 1}))
    with pytest.raises(P4.P4ProtocolError, match="member set"):
        P4._validate_external_bundle_path(
            extra_store, repo_root=ROOT, launch=launch
        )

    chain_store = tmp_path / "chain-store"
    launch, _sources = _caught_external_bundle(chain_store)
    threshold = P4._load_canonical(
        chain_store / P4.THRESHOLD_SEAL_NAME, label="test threshold"
    )
    threshold["graph_selection_seal_sha256"] = "f" * 64
    threshold_source = P4.canonical_json_bytes(threshold)
    (chain_store / P4.THRESHOLD_SEAL_NAME).write_bytes(threshold_source)
    terminal = P4._load_canonical(
        chain_store / P4.TERMINAL_NAME, label="test terminal"
    )
    terminal["result"]["threshold_seal_sha256"] = hashlib.sha256(
        threshold_source
    ).hexdigest()
    terminal_source = P4.canonical_json_bytes(terminal)
    (chain_store / P4.TERMINAL_NAME).write_bytes(terminal_source)
    manifest = P4._load_canonical(
        chain_store / P4.STORE_MANIFEST_NAME, label="test manifest"
    )
    for item in manifest["members"]:
        if item["name"] == P4.THRESHOLD_SEAL_NAME:
            item["sha256"] = hashlib.sha256(threshold_source).hexdigest()
            item["size_bytes"] = len(threshold_source)
        elif item["name"] == P4.TERMINAL_NAME:
            item["sha256"] = hashlib.sha256(terminal_source).hexdigest()
            item["size_bytes"] = len(terminal_source)
    manifest["terminal_sha256"] = hashlib.sha256(terminal_source).hexdigest()
    (chain_store / P4.STORE_MANIFEST_NAME).write_bytes(
        P4.canonical_json_bytes(manifest)
    )
    with pytest.raises(P4.P4ProtocolError, match="graph-selection chain"):
        P4._validate_external_bundle_path(
            chain_store, repo_root=ROOT, launch=launch
        )


def test_stage_write_failure_is_unresolved_and_never_promoted(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stage_path = tmp_path / ".stage"
    store_path = tmp_path / "store"
    monkeypatch.setattr(P4, "EXTERNAL_STAGE", stage_path)
    monkeypatch.setattr(P4, "EXTERNAL_STORE", store_path)
    stage = P4._reserve_external_stage()
    try:
        monkeypatch.setattr(
            P4.os,
            "write",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("injected")),
        )
        with pytest.raises(P4.P4PersistenceError, match="persist stage member"):
            P4._write_stage_document(stage, P4.ATTEMPT_NAME, {"x": 1})
    finally:
        stage.close()

    assert stage_path.is_dir()
    assert not store_path.exists()


def test_atomic_projection_resumes_exact_prefix_and_is_inode_idempotent(
    tmp_path: Path,
) -> None:
    target = tmp_path / "projection.json"
    temporary = P4._projection_temp_path(target)
    source = P4.canonical_json_bytes({"payload": [1, 2, 3]})
    temporary.write_bytes(source[:7])
    temporary.chmod(0o600)

    assert P4._publish_repository_projection(target, source) == "published"
    assert target.read_bytes() == source
    first = target.stat()
    assert not temporary.exists()
    assert P4._publish_repository_projection(target, source) == "already_exact"
    second = target.stat()
    assert (first.st_dev, first.st_ino) == (second.st_dev, second.st_ino)


def test_atomic_projection_rejects_different_target_and_temp_without_mutation(
    tmp_path: Path,
) -> None:
    source = P4.canonical_json_bytes({"expected": True})
    target = tmp_path / "projection.json"
    different = P4.canonical_json_bytes({"expected": False})
    target.write_bytes(different)
    with pytest.raises(P4.P4ProtocolError, match="projection differs"):
        P4._publish_repository_projection(target, source)
    assert target.read_bytes() == different

    target.unlink()
    temporary = P4._projection_temp_path(target)
    temporary.write_bytes(b"not-a-prefix")
    temporary.chmod(0o600)
    with pytest.raises(P4.P4ProtocolError, match="exact prefix"):
        P4._publish_repository_projection(target, source)
    assert temporary.read_bytes() == b"not-a-prefix"
    assert not target.exists()


def test_atomic_projection_promotion_failure_leaves_repairable_exact_temp(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "projection.json"
    temporary = P4._projection_temp_path(target)
    source = P4.canonical_json_bytes({"terminal": "at-most-one"})
    monkeypatch.setattr(P4, "_native_file_no_replace", lambda *_args: os.errno.EIO if hasattr(os, "errno") else 5)

    with pytest.raises(P4.P4PersistenceError, match="no-replace failed"):
        P4._publish_repository_projection(target, source)

    assert not target.exists()
    assert temporary.read_bytes() == source
    assert temporary.stat().st_mode & 0o777 == 0o444
