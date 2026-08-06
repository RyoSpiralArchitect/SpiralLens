"""Exact post-D6 descriptive derivations for frozen outputs 13 through 27.

This repository-only module performs no I/O and grants no
authority; it only joins already-validated parent documents and derives the
Level-0 descriptive tables frozen by the post-D6 plan.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from itertools import combinations
from typing import Any

from spirallens.qualification.common import QualificationContractError

__all__ = ()


_OUTPUT_IDS = (
    "three-by-three-field-cycle-graph-matrix",
    "loop-role-separated-primary-boundary-and-offcore-control-table",
    "diagonal-offdiagonal-separation",
    "adjacency-output-loop-total-effects",
    "support-aware-cell-table",
    "worst-case-by-stress-stratum",
    "loop-role-separated-worst-case-and-coverage-table",
    "coverage-abstention-recall-specificity-table",
    "mandatory-prerequisite-failure-table",
    "required-nonvacuity-evidence",
    "abstention-reason-table",
    "typed-failure-coverage",
    "shared-generator-seed-graph-boundary-implementation-oracle-map",
    "replication-versus-construction-diversity-table",
    "epistemic-independence-nonclaim",
)

_LOOP_ROLES = ("offcore_control", "primary_boundary")
_PREREQUISITE_CORE_REASON = ("amplitude_at_or_below_core_ceiling_not_localized",)
_PREREQUISITE_LOOP_REASONS = (
    "boundary_amplitude_at_or_below_floor",
    "boundary_coherence_at_or_below_floor",
    "boundary_identifiability_at_or_below_floor",
)
_D2_SUPPORT_REASON = ("candidate_measurement_support_below_minimum",)


def _fail(message: str) -> None:
    raise QualificationContractError(message)


def _expect(condition: bool, message: str) -> None:
    if not condition:
        _fail(message)


def _mapping(value: object, *, label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        _fail(f"{label} must be a string-keyed mapping")
    return value


def _records(
    document: dict[str, Any],
    key: str,
    *,
    count: int,
    label: str,
) -> list[dict[str, Any]]:
    value = document.get(key)
    if not isinstance(value, list) or len(value) != count:
        _fail(f"{label} must contain exactly {count} rows")
    rows = [_mapping(item, label=f"{label} row") for item in value]
    return rows


def _index(
    rows: list[dict[str, Any]],
    key: str,
    *,
    label: str,
) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        value = row.get(key)
        if not isinstance(value, str) or not value or value in result:
            _fail(f"{label} requires unique nonempty {key} values")
        result[value] = row
    return result


def _reason_tuple(value: object, *, label: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        _fail(f"{label} must be a string array")
    return tuple(value)


def _plan_output_ids(plan: dict[str, Any]) -> tuple[str, ...]:
    packages = plan.get("work_packages")
    if not isinstance(packages, list):
        _fail("plan work_packages must be an array")
    ordered = sorted(
        (_mapping(item, label="plan work package") for item in packages),
        key=lambda item: item.get("sequence", -1),
    )
    flattened: list[str] = []
    for package in ordered:
        outputs = package.get("required_outputs")
        if not isinstance(outputs, list) or not all(
            isinstance(item, str) for item in outputs
        ):
            _fail("plan required_outputs must be string arrays")
        flattened.extend(outputs)
    _expect(len(flattened) == 27, "plan must declare exactly 27 required outputs")
    observed = tuple(flattened[12:27])
    _expect(
        observed == _OUTPUT_IDS, "plan outputs 13 through 27 differ from frozen IDs"
    )
    return observed


def _numeric_extrema(
    rows: list[dict[str, Any]],
    key: str,
) -> tuple[float | None, float | None, float | None]:
    values = [row[key] for row in rows if row.get(key) is not None]
    if not values:
        return None, None, None
    if not all(type(value) in (int, float) for value in values):
        _fail(f"{key} values must be numeric or null")
    minimum = min(values)
    maximum = max(values)
    return float(minimum), float(maximum), float(maximum - minimum)


def _maximum_with_ids(
    rows: list[dict[str, Any]],
    *,
    value_key: str,
    id_key: str,
) -> tuple[float | None, list[str]]:
    available = [row for row in rows if row.get(value_key) is not None]
    if not available:
        return None, []
    values = [row[value_key] for row in available]
    if not all(type(value) in (int, float) for value in values):
        _fail(f"{value_key} values must be numeric or null")
    maximum = max(values)
    ids = sorted(
        row[id_key]
        for row in available
        if row[value_key] == maximum and isinstance(row.get(id_key), str)
    )
    _expect(bool(ids), f"{value_key} maximum must retain at least one identity")
    return float(maximum), ids


def _walk_mappings(value: object) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    if isinstance(value, dict):
        found.append(value)
        for child in value.values():
            found.extend(_walk_mappings(child))
    elif isinstance(value, list):
        for child in value:
            found.extend(_walk_mappings(child))
    return found


def _entry(
    sequence: int,
    output_id: str,
    rows: list[dict[str, Any]],
    **metadata: object,
) -> dict[str, Any]:
    return {
        "sequence": sequence,
        "output_id": output_id,
        "status": "available",
        "row_count": len(rows),
        "data": {**metadata, "rows": rows},
    }


def derive_outputs_13_27(
    *,
    plan: dict,
    protocol: dict,
    terminal: dict,
    manifest: dict,
    consumption: dict,
    d6_decision: dict,
) -> list[dict]:
    """Derive the exact frozen output tables numbered 13 through 27."""

    plan = _mapping(plan, label="post-D6 plan")
    protocol = _mapping(protocol, label="selection protocol")
    terminal = _mapping(terminal, label="selection terminal")
    manifest = _mapping(manifest, label="terminal manifest")
    consumption = _mapping(consumption, label="terminal consumption")
    d6_decision = _mapping(d6_decision, label="D6 decision")
    _plan_output_ids(plan)

    primary_rows = _records(
        terminal, "primary_units", count=64, label="loop primary units"
    )
    core_primary_rows = _records(
        terminal, "core_primary_units", count=64, label="core primary units"
    )
    crossed_rows = _records(
        terminal, "crossed_cells", count=1152, label="crossed loop cells"
    )
    core_rows = _records(terminal, "core_cells", count=192, label="core cells")
    nonvacuity_rows = _records(
        terminal, "crossed_nonvacuity", count=64, label="nonvacuity summaries"
    )
    stratum_rows = _records(terminal, "strata", count=6, label="stress strata")

    expected_rows = _records(
        protocol, "expected_cells", count=1152, label="expected loop cells"
    )
    expected_core_rows = _records(
        protocol, "expected_core_cells", count=192, label="expected core cells"
    )
    expected_strata = _records(
        protocol, "expected_strata", count=6, label="expected stress strata"
    )

    evidence = _mapping(terminal.get("evidence_bundle"), label="evidence bundle")
    loop_receipts = _records(
        evidence,
        "loop_cell_receipts",
        count=1152,
        label="loop evidence receipts",
    )
    core_receipts = _records(
        evidence,
        "core_cell_receipts",
        count=192,
        label="core evidence receipts",
    )
    nonvacuity_receipts = _records(
        evidence,
        "nonvacuity_receipts",
        count=64,
        label="nonvacuity evidence receipts",
    )
    confounder_matrix = _mapping(
        evidence.get("d2_confounder_matrix_receipt"),
        label="D2 confounder matrix",
    )
    confounder_cells = _records(
        confounder_matrix, "cells", count=6, label="D2 confounder cells"
    )

    primary_by_id = _index(primary_rows, "primary_unit_id", label="loop primary units")
    core_primary_by_id = _index(
        core_primary_rows, "primary_unit_id", label="core primary units"
    )
    crossed_by_id = _index(crossed_rows, "cell_id", label="crossed loop cells")
    expected_by_id = _index(expected_rows, "cell_id", label="expected loop cells")
    loop_receipt_by_id = _index(
        loop_receipts, "cell_id", label="loop evidence receipts"
    )
    core_by_id = _index(core_rows, "core_cell_id", label="core cells")
    expected_core_by_id = _index(
        expected_core_rows, "core_cell_id", label="expected core cells"
    )
    core_receipt_by_id = _index(
        core_receipts, "core_cell_id", label="core evidence receipts"
    )
    nonvacuity_by_id = _index(
        nonvacuity_rows, "primary_unit_id", label="nonvacuity summaries"
    )
    nonvacuity_receipt_by_id = _index(
        nonvacuity_receipts,
        "primary_unit_id",
        label="nonvacuity evidence receipts",
    )
    stratum_by_id = _index(stratum_rows, "stratum_id", label="stress strata")
    expected_stratum_by_id = _index(
        expected_strata, "stratum_id", label="expected stress strata"
    )

    _expect(
        set(crossed_by_id) == set(expected_by_id) == set(loop_receipt_by_id),
        "loop cell parent identities do not form an exact join",
    )
    _expect(
        set(core_by_id) == set(expected_core_by_id) == set(core_receipt_by_id),
        "core cell parent identities do not form an exact join",
    )
    _expect(
        set(primary_by_id)
        == set(core_primary_by_id)
        == set(nonvacuity_by_id)
        == set(nonvacuity_receipt_by_id),
        "primary-unit parent identities do not form an exact join",
    )
    _expect(
        set(stratum_by_id) == set(expected_stratum_by_id),
        "required stress strata do not form an exact join",
    )

    graphs = _mapping(protocol.get("graphs"), label="protocol graph axes")
    field_graphs = _records(graphs, "field_estimation", count=3, label="field graphs")
    cycle_graphs = _records(graphs, "cycle_construction", count=3, label="cycle graphs")
    field_ids = tuple(row.get("graph_id") for row in field_graphs)
    cycle_ids = tuple(row.get("graph_id") for row in cycle_graphs)
    _expect(
        all(isinstance(item, str) for item in field_ids + cycle_ids),
        "graph IDs must be strings",
    )
    _expect(
        len(set(field_ids)) == 3 and len(set(cycle_ids)) == 3,
        "graph axes must contain three unique IDs each",
    )
    field_family = {row["graph_id"]: row.get("family") for row in field_graphs}
    cycle_family = {row["graph_id"]: row.get("family") for row in cycle_graphs}
    _expect(
        set(field_family.values()) == set(cycle_family.values()),
        "field and cycle graph families must match exactly",
    )
    field_pairs = tuple(combinations(field_ids, 2))

    d6_terminal = _mapping(
        d6_decision.get("selection_terminal"), label="D6 terminal binding"
    )
    _expect(
        manifest.get("terminal_artifact_sha256")
        == consumption.get("terminal_artifact_sha256")
        == d6_terminal.get("result_sha256"),
        "terminal artifact identity differs across manifest, consumption, and D6",
    )
    _expect(
        terminal.get("protocol_id")
        == protocol.get("protocol_id")
        == d6_terminal.get("protocol_id"),
        "protocol identity differs across parents",
    )
    _expect(
        terminal.get("protocol_canonical_sha256")
        == d6_terminal.get("protocol_canonical_sha256")
        == consumption.get("protocol_canonical_sha256"),
        "protocol digest differs across parents",
    )

    support_rows: list[dict[str, Any]] = []
    support_by_id: dict[str, dict[str, Any]] = {}
    crossed_key: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for cell_id in sorted(crossed_by_id):
        observed = crossed_by_id[cell_id]
        expected = expected_by_id[cell_id]
        receipt = loop_receipt_by_id[cell_id]
        primary_id = expected.get("primary_unit_id")
        _expect(
            isinstance(primary_id, str) and primary_id in primary_by_id,
            "loop cell refers to an unknown primary unit",
        )
        primary = primary_by_id[primary_id]
        for key, observed_key in (
            ("primary_unit_id", "primary_unit_id"),
            ("field_graph_id", "field_graph_id"),
            ("cycle_graph_id", "cycle_graph_id"),
            ("loop_role", "loop_role"),
        ):
            _expect(
                observed.get(observed_key) == expected.get(key),
                f"loop cell {cell_id} differs from expected {key}",
            )
        _expect(
            observed.get("expected_disposition")
            == expected.get("expected_loop_disposition"),
            f"loop cell {cell_id} expected disposition differs",
        )
        _expect(
            primary.get("selection_seed") == expected.get("selection_seed")
            and primary.get("control_id") == expected.get("control_id")
            and primary.get("stress_assignments") == expected.get("stress_assignments"),
            f"loop cell {cell_id} primary metadata differs",
        )
        sealed = _mapping(
            receipt.get("sealed_prediction_receipt"),
            label=f"loop cell {cell_id} sealed prediction",
        )
        oracle = _mapping(
            receipt.get("oracle_truth_receipt"),
            label=f"loop cell {cell_id} oracle truth",
        )
        blind = _mapping(
            receipt.get("blind_input_receipt"),
            label=f"loop cell {cell_id} blind input",
        )
        reasons = _reason_tuple(
            sealed.get("reason_codes"), label=f"loop cell {cell_id} reasons"
        )
        expected_reasons = _reason_tuple(
            oracle.get("expected_prerequisite_reasons"),
            label=f"loop cell {cell_id} expected reasons",
        )
        expected_disposition = expected["expected_loop_disposition"]
        if expected_disposition == "prerequisite_failure":
            _expect(
                observed.get("attempt_status") == "insufficient"
                and observed.get("prediction_class") == "abstain"
                and reasons == expected_reasons == _PREREQUISITE_LOOP_REASONS,
                f"loop cell {cell_id} prerequisite route differs",
            )
        else:
            _expect(
                observed.get("attempt_status") == "evaluable"
                and not reasons
                and not expected_reasons,
                f"loop cell {cell_id} evaluable route carries abstention reasons",
            )
        field_id = expected["field_graph_id"]
        cycle_id = expected["cycle_graph_id"]
        pair_class = (
            "diagonal"
            if field_family[field_id] == cycle_family[cycle_id]
            else "offdiagonal"
        )
        row = {
            "cell_id": cell_id,
            "primary_unit_id": primary_id,
            "selection_seed": expected["selection_seed"],
            "control_id": expected["control_id"],
            "stress_assignments": expected["stress_assignments"],
            "stratum_ids": expected["stratum_ids"],
            "field_graph_id": field_id,
            "cycle_graph_id": cycle_id,
            "loop_role": expected["loop_role"],
            "pair_class": pair_class,
            "expected_disposition": expected_disposition,
            "attempt_status": observed["attempt_status"],
            "prediction_class": observed["prediction_class"],
            "state": observed["state"],
            "continuous_signed_total_cycles": observed[
                "continuous_signed_total_cycles"
            ],
            "oracle_absolute_error_cycles": observed["oracle_absolute_error_cycles"],
            "field_graph_fingerprint_sha256": observed[
                "field_graph_fingerprint_sha256"
            ],
            "cycle_graph_fingerprint_sha256": observed[
                "cycle_graph_fingerprint_sha256"
            ],
            "field_estimate_fingerprint_sha256": observed[
                "field_estimate_fingerprint_sha256"
            ],
            "prediction_fingerprint_sha256": observed["prediction_fingerprint_sha256"],
            "oracle_fingerprint_sha256": observed["oracle_fingerprint_sha256"],
            "representative_content_sha256": observed["representative_content_sha256"],
            "sealed_prediction_reason_codes": list(reasons),
            "oracle_expected_prerequisite_reasons": list(expected_reasons),
            "numeric_support_available": False,
            "boundary_amplitude_descriptor": blind.get("boundary_amplitude"),
            "boundary_coherence_descriptor": blind.get("boundary_coherence"),
            "boundary_identifiability_descriptor": blind.get(
                "boundary_identifiability_score"
            ),
        }
        support_rows.append(row)
        support_by_id[cell_id] = row
        key = (primary_id, row["loop_role"], field_id, cycle_id)
        _expect(key not in crossed_key, "crossed cell execution key is duplicated")
        crossed_key[key] = row
    _expect(len(crossed_key) == 1152, "crossed execution keys are incomplete")

    cells_by_layer: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in support_rows:
        cells_by_layer[(row["primary_unit_id"], row["loop_role"])].append(row)
    _expect(len(cells_by_layer) == 128, "loop-role matrix must contain 128 layers")

    matrix_rows: list[dict[str, Any]] = []
    role_rows: list[dict[str, Any]] = []
    role_reduction_by_key: dict[tuple[str, str], dict[str, Any]] = {}
    expected_pairs = {
        (field_id, cycle_id) for field_id in field_ids for cycle_id in cycle_ids
    }
    for (primary_id, role), layer in sorted(cells_by_layer.items()):
        _expect(len(layer) == 9, "each loop-role layer must contain nine cells")
        _expect(
            {(row["field_graph_id"], row["cycle_graph_id"]) for row in layer}
            == expected_pairs,
            "loop-role layer is not the exact three-by-three graph product",
        )
        ordered = sorted(
            layer,
            key=lambda row: (
                field_ids.index(row["field_graph_id"]),
                cycle_ids.index(row["cycle_graph_id"]),
            ),
        )
        primary = primary_by_id[primary_id]
        matrix_rows.append(
            {
                "primary_unit_id": primary_id,
                "selection_seed": primary["selection_seed"],
                "control_id": primary["control_id"],
                "stress_assignments": primary["stress_assignments"],
                "loop_role": role,
                "field_graph_ids": list(field_ids),
                "cycle_graph_ids": list(cycle_ids),
                "cells": [
                    {
                        key: row[key]
                        for key in (
                            "cell_id",
                            "field_graph_id",
                            "cycle_graph_id",
                            "pair_class",
                            "expected_disposition",
                            "attempt_status",
                            "prediction_class",
                            "state",
                            "continuous_signed_total_cycles",
                            "oracle_absolute_error_cycles",
                        )
                    }
                    for row in ordered
                ],
            }
        )
        minimum, maximum, span = _numeric_extrema(
            ordered, "continuous_signed_total_cycles"
        )
        maximum_error, worst_cell_ids = _maximum_with_ids(
            ordered,
            value_key="oracle_absolute_error_cycles",
            id_key="cell_id",
        )
        reason_codes = sorted(
            {
                reason
                for row in ordered
                for reason in row["sealed_prediction_reason_codes"]
            }
        )
        attempts = Counter(row["attempt_status"] for row in ordered)
        role_row = {
            "primary_unit_id": primary_id,
            "selection_seed": primary["selection_seed"],
            "control_id": primary["control_id"],
            "stress_assignments": primary["stress_assignments"],
            "loop_role": role,
            "cell_count": 9,
            "evaluable_cell_count": attempts["evaluable"],
            "prerequisite_cell_count": attempts["insufficient"],
            "cell_ids": [row["cell_id"] for row in ordered],
            "continuous_total_min_cycles": minimum,
            "continuous_total_max_cycles": maximum,
            "continuous_total_span_cycles": span,
            "maximum_oracle_absolute_error_cycles": maximum_error,
            "worst_oracle_cell_ids": worst_cell_ids,
            "abstention_reason_codes": reason_codes,
        }
        _expect(
            (attempts["evaluable"], attempts["insufficient"]) in {(9, 0), (0, 9)},
            "loop-role layer mixes evaluable and prerequisite cells",
        )
        role_rows.append(role_row)
        role_reduction_by_key[(primary_id, role)] = role_row
    _expect(
        sum(row["evaluable_cell_count"] == 9 for row in role_rows) == 96
        and sum(row["prerequisite_cell_count"] == 9 for row in role_rows) == 32,
        "loop-role evaluability counts differ from the frozen grain",
    )
    _expect(
        Counter(row["attempt_status"] for row in support_rows)
        == Counter({"evaluable": 864, "insufficient": 288})
        and Counter(row["state"] for row in support_rows) == Counter({"pass": 1152}),
        "support-aware loop-cell states differ from the frozen terminal",
    )

    diagonal_rows: list[dict[str, Any]] = []
    for role in _LOOP_ROLES:
        for pair_class in ("diagonal", "offdiagonal"):
            selected = [
                row
                for row in support_rows
                if row["loop_role"] == role and row["pair_class"] == pair_class
            ]
            diagonal_rows.append(
                {
                    "loop_role": role,
                    "pair_class": pair_class,
                    "cell_count": len(selected),
                    "unique_execution_count": len(
                        {row["primary_unit_id"] for row in selected}
                    ),
                    "evaluable_cell_count": sum(
                        row["attempt_status"] == "evaluable" for row in selected
                    ),
                    "prerequisite_cell_count": sum(
                        row["attempt_status"] == "insufficient" for row in selected
                    ),
                    "graph_cells_are_repeated_measures": True,
                }
            )
    _expect(
        [
            (
                row["cell_count"],
                row["evaluable_cell_count"],
                row["prerequisite_cell_count"],
            )
            for row in diagonal_rows
        ]
        == [(192, 144, 48), (384, 288, 96)] * 2,
        "diagonal and offdiagonal cell counts differ from the frozen design",
    )

    effect_rows: list[dict[str, Any]] = []
    component_row_count = 0
    loop_contrast_row_count = 0
    expected_pair_ids = {f"{left}--{right}" for left, right in field_pairs}
    for primary_id in sorted(primary_by_id):
        summary = nonvacuity_by_id[primary_id]
        evidence_row = nonvacuity_receipt_by_id[primary_id]
        receipt = _mapping(
            evidence_row.get("crossed_nonvacuity_receipt"),
            label=f"nonvacuity receipt {primary_id}",
        )
        _expect(
            summary.get("field_graph_pair_effects")
            == receipt.get("field_graph_pair_effects"),
            "nonvacuity pair effects differ between summary and evidence",
        )
        pair_effects = summary.get("field_graph_pair_effects")
        if not isinstance(pair_effects, list) or len(pair_effects) != 3:
            _fail("each nonvacuity summary must contain three field pairs")
        _expect(
            {item.get("pair_id") for item in pair_effects} == expected_pair_ids,
            "nonvacuity field-pair IDs differ from the protocol graph axis",
        )
        primary = primary_by_id[primary_id]
        for pair_effect in sorted(pair_effects, key=lambda item: item["pair_id"]):
            pair_effect = _mapping(pair_effect, label="field graph pair effect")
            left = pair_effect.get("left_field_graph_id")
            right = pair_effect.get("right_field_graph_id")
            _expect(
                isinstance(left, str)
                and isinstance(right, str)
                and (left, right) in field_pairs,
                "field graph pair effect is not a declared unordered pair",
            )
            components = pair_effect.get("component_effects")
            if not isinstance(components, list) or len(components) != 4:
                _fail("field graph pair effect must contain four components")
            component_names = {item.get("component_name") for item in components}
            _expect(
                component_names
                == {
                    "amplitude",
                    "identifiability_score",
                    "section_values",
                    "edge_coherence",
                },
                "field graph pair components differ from the frozen set",
            )
            contrasts: list[dict[str, Any]] = []
            for role in _LOOP_ROLES:
                for cycle_id in cycle_ids:
                    left_cell = crossed_key[(primary_id, role, left, cycle_id)]
                    right_cell = crossed_key[(primary_id, role, right, cycle_id)]
                    left_total = left_cell["continuous_signed_total_cycles"]
                    right_total = right_cell["continuous_signed_total_cycles"]
                    if left_total is None or right_total is None:
                        difference = None
                    else:
                        difference = float(right_total - left_total)
                    contrasts.append(
                        {
                            "loop_role": role,
                            "cycle_graph_id": cycle_id,
                            "left_cell_id": left_cell["cell_id"],
                            "right_cell_id": right_cell["cell_id"],
                            "left_total_cycles": left_total,
                            "right_total_cycles": right_total,
                            "signed_difference_cycles": difference,
                            "absolute_difference_cycles": (
                                None if difference is None else abs(difference)
                            ),
                        }
                    )
            _expect(len(contrasts) == 6, "field pair must contain six loop contrasts")
            effect_rows.append(
                {
                    "primary_unit_id": primary_id,
                    "selection_seed": primary["selection_seed"],
                    "control_id": primary["control_id"],
                    "stress_assignments": primary["stress_assignments"],
                    "pair_id": pair_effect["pair_id"],
                    "left_field_graph_id": left,
                    "right_field_graph_id": right,
                    "left_field_graph_fingerprint_sha256": pair_effect[
                        "left_field_graph_fingerprint_sha256"
                    ],
                    "right_field_graph_fingerprint_sha256": pair_effect[
                        "right_field_graph_fingerprint_sha256"
                    ],
                    "field_adjacency_identity_differs": pair_effect[
                        "left_field_graph_fingerprint_sha256"
                    ]
                    != pair_effect["right_field_graph_fingerprint_sha256"],
                    "numeric_adjacency_difference_available": False,
                    "component_effects": components,
                    "qualifying_substantive_components": pair_effect[
                        "qualifying_substantive_components"
                    ],
                    "substantive_response_pass": pair_effect[
                        "substantive_response_pass"
                    ],
                    "loop_contrasts": contrasts,
                }
            )
            component_row_count += len(components)
            loop_contrast_row_count += len(contrasts)
    _expect(
        len(effect_rows) == 192
        and component_row_count == 768
        and loop_contrast_row_count == 1152,
        "adjacency/output/loop effect row counts differ from the frozen design",
    )
    qualifying = Counter(
        component["component_name"]
        for row in effect_rows
        for component in row["component_effects"]
        if component.get("qualifies") is True
    )
    _expect(
        qualifying == Counter({"section_values": 96}),
        "substantive component qualifications differ from the parent evidence",
    )
    _expect(
        all(
            component.get("effect_eligible") is False
            for row in effect_rows
            for component in row["component_effects"]
            if component.get("component_name") == "edge_coherence"
        ),
        "edge coherence must remain diagnostic and effect-ineligible",
    )

    stratum_members: dict[str, set[str]] = {}
    for stratum_id in sorted(stratum_by_id):
        observed = stratum_by_id[stratum_id]
        expected = expected_stratum_by_id[stratum_id]
        observed_ids = observed.get("primary_unit_ids")
        expected_ids = expected.get("primary_unit_ids")
        _expect(
            isinstance(observed_ids, list)
            and isinstance(expected_ids, list)
            and len(observed_ids) == len(expected_ids) == 32
            and set(observed_ids) == set(expected_ids)
            and len(set(observed_ids)) == 32,
            f"required stratum {stratum_id} membership differs",
        )
        stratum_members[stratum_id] = set(observed_ids)

    stress_pair_rows: list[dict[str, Any]] = []
    for stratum_id in sorted(stratum_members):
        members = stratum_members[stratum_id]
        for role in _LOOP_ROLES:
            for field_id in field_ids:
                for cycle_id in cycle_ids:
                    selected = [
                        crossed_key[(primary_id, role, field_id, cycle_id)]
                        for primary_id in sorted(members)
                    ]
                    maximum_error, worst_ids = _maximum_with_ids(
                        selected,
                        value_key="oracle_absolute_error_cycles",
                        id_key="cell_id",
                    )
                    stress_pair_rows.append(
                        {
                            "stratum_id": stratum_id,
                            "field_graph_id": field_id,
                            "cycle_graph_id": cycle_id,
                            "loop_role": role,
                            "attempted_execution_count": 32,
                            "evaluable_execution_count": sum(
                                row["attempt_status"] == "evaluable" for row in selected
                            ),
                            "prerequisite_execution_count": sum(
                                row["attempt_status"] == "insufficient"
                                for row in selected
                            ),
                            "maximum_oracle_absolute_error_cycles": maximum_error,
                            "worst_cell_ids": worst_ids,
                            "state_counts": dict(
                                sorted(
                                    Counter(row["state"] for row in selected).items()
                                )
                            ),
                        }
                    )
    _expect(
        len(stress_pair_rows) == 108
        and all(
            row["evaluable_execution_count"] == 24
            and row["prerequisite_execution_count"] == 8
            for row in stress_pair_rows
        )
        and all(row["state_counts"] == {"pass": 32} for row in stress_pair_rows),
        "stress pair-role reductions differ from the frozen denominators",
    )

    stress_role_rows: list[dict[str, Any]] = []
    for stratum_id in sorted(stratum_members):
        stratum = stratum_by_id[stratum_id]
        members = stratum_members[stratum_id]
        for role in _LOOP_ROLES:
            reduced = [
                role_reduction_by_key[(primary_id, role)]
                for primary_id in sorted(members)
            ]
            numeric_spans = [
                row
                for row in reduced
                if row["continuous_total_span_cycles"] is not None
            ]
            numeric_errors = [
                row
                for row in reduced
                if row["maximum_oracle_absolute_error_cycles"] is not None
            ]
            max_span, worst_span_ids = _maximum_with_ids(
                numeric_spans,
                value_key="continuous_total_span_cycles",
                id_key="primary_unit_id",
            )
            max_error, worst_error_ids = _maximum_with_ids(
                numeric_errors,
                value_key="maximum_oracle_absolute_error_cycles",
                id_key="primary_unit_id",
            )
            stress_role_rows.append(
                {
                    "stratum_id": stratum_id,
                    "loop_role": role,
                    "attempted_execution_count": 32,
                    "evaluable_execution_count": len(numeric_spans),
                    "prerequisite_execution_count": 32 - len(numeric_spans),
                    "graph_cells_reduced_within_execution_first": True,
                    "maximum_execution_graph_total_span_cycles": max_span,
                    "worst_span_primary_unit_ids": worst_span_ids,
                    "maximum_execution_oracle_error_cycles": max_error,
                    "worst_error_primary_unit_ids": worst_error_ids,
                    "coverage": stratum["coverage"],
                    "abstention_fraction": stratum["abstention_fraction"],
                    "score_denominator": stratum["score_denominator"],
                }
            )
    _expect(
        len(stress_role_rows) == 12
        and all(
            row["evaluable_execution_count"] == 24
            and row["prerequisite_execution_count"] == 8
            for row in stress_role_rows
        ),
        "stress role reductions differ from the frozen denominators",
    )

    coverage_rows = [dict(stratum_by_id[key]) for key in sorted(stratum_by_id)]
    for row in coverage_rows:
        _expect(
            row.get("attempted_count") == 32
            and row.get("evaluable_count") == 24
            and row.get("prerequisite_expected_count") == 8
            and row.get("pass_count") == 32
            and row.get("attempt_insufficient_count") == 8
            and row.get("rate_eligible_count") == 24
            and row.get("rate_evaluable_count") == 24
            and row.get("coverage") == 1.0
            and row.get("recall") == 1.0
            and row.get("specificity") == 1.0
            and row.get("abstention_fraction") == 0.0
            and row.get("prerequisite_rate_handling") == "excluded_but_mandatory"
            and row.get("graph_cells_are_repeated_measures") is True,
            "coverage stratum differs from the frozen denominator contract",
        )

    core_cells_by_primary: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for core_id, row in core_by_id.items():
        expected = expected_core_by_id[core_id]
        _expect(
            row.get("primary_unit_id") == expected.get("primary_unit_id")
            and row.get("field_graph_id") == expected.get("field_graph_id")
            and row.get("expected_disposition")
            == expected.get("expected_core_disposition"),
            f"core cell {core_id} differs from its expected row",
        )
        core_cells_by_primary[row["primary_unit_id"]].append(row)

    prerequisite_primary_ids = sorted(
        row["primary_unit_id"]
        for row in primary_rows
        if row.get("expected_disposition") == "prerequisite_failure"
    )
    _expect(len(prerequisite_primary_ids) == 16, "expected 16 prerequisite executions")
    prerequisite_rows: list[dict[str, Any]] = []
    for primary_id in prerequisite_primary_ids:
        loop_primary = primary_by_id[primary_id]
        core_primary = core_primary_by_id[primary_id]
        core_cells = sorted(
            core_cells_by_primary[primary_id], key=lambda row: row["core_cell_id"]
        )
        loop_cells = sorted(
            cells_by_layer[(primary_id, "offcore_control")]
            + cells_by_layer[(primary_id, "primary_boundary")],
            key=lambda row: row["cell_id"],
        )
        _expect(
            len(core_cells) == 3 and len(loop_cells) == 18,
            "prerequisite cell coverage differs",
        )
        core_reason_rows: list[dict[str, Any]] = []
        for core_cell in core_cells:
            receipt = core_receipt_by_id[core_cell["core_cell_id"]]
            sealed = _mapping(
                receipt.get("sealed_prediction_receipt"), label="core sealed prediction"
            )
            oracle = _mapping(
                receipt.get("oracle_truth_receipt"), label="core oracle truth"
            )
            reasons = _reason_tuple(sealed.get("reason_codes"), label="core reasons")
            expected_reasons = _reason_tuple(
                oracle.get("expected_prerequisite_reasons"),
                label="core expected reasons",
            )
            _expect(
                core_cell.get("attempt_status") == "insufficient"
                and core_cell.get("prediction_class") == "abstain"
                and reasons == expected_reasons == _PREREQUISITE_CORE_REASON,
                "core prerequisite leaf differs from the frozen typed route",
            )
            core_reason_rows.append(
                {
                    "core_cell_id": core_cell["core_cell_id"],
                    "field_graph_id": core_cell["field_graph_id"],
                    "reason_codes": list(reasons),
                }
            )
        _expect(
            loop_primary.get("attempt_status") == "insufficient"
            and loop_primary.get("prediction_class") == "abstain"
            and loop_primary.get("state") == "pass"
            and core_primary.get("attempt_status") == "insufficient"
            and core_primary.get("prediction_class") == "abstain"
            and core_primary.get("state") == "pass",
            "prerequisite primary summaries differ from the leaf route",
        )
        stratum_ids = sorted(
            {stratum_id for row in loop_cells for stratum_id in row["stratum_ids"]}
        )
        _expect(len(stratum_ids) == 3, "prerequisite execution must join three strata")
        prerequisite_rows.append(
            {
                "primary_unit_id": primary_id,
                "selection_seed": loop_primary["selection_seed"],
                "control_id": loop_primary["control_id"],
                "stress_assignments": loop_primary["stress_assignments"],
                "stratum_ids": stratum_ids,
                "core_primary_attempt_status": core_primary["attempt_status"],
                "core_primary_prediction_class": core_primary["prediction_class"],
                "loop_primary_attempt_status": loop_primary["attempt_status"],
                "loop_primary_prediction_class": loop_primary["prediction_class"],
                "core_cells": core_reason_rows,
                "loop_cells": [
                    {
                        "cell_id": row["cell_id"],
                        "field_graph_id": row["field_graph_id"],
                        "cycle_graph_id": row["cycle_graph_id"],
                        "loop_role": row["loop_role"],
                        "reason_codes": row["sealed_prediction_reason_codes"],
                    }
                    for row in loop_cells
                ],
                "expected_prerequisite_failure_is_required_pass_route": True,
            }
        )

    nonvacuity_output_rows: list[dict[str, Any]] = []
    nonvacuity_pair_count = 0
    nonvacuity_component_count = 0
    required_variation_count = 0
    for primary_id in sorted(nonvacuity_by_id):
        summary = nonvacuity_by_id[primary_id]
        evidence_row = nonvacuity_receipt_by_id[primary_id]
        receipt = _mapping(
            evidence_row.get("crossed_nonvacuity_receipt"),
            label=f"nonvacuity receipt {primary_id}",
        )
        _expect(
            summary.get("state") == receipt.get("state") == "pass"
            and summary.get("field_graph_pair_effects")
            == receipt.get("field_graph_pair_effects")
            and summary.get("field_adjacency_variant_count") == 3
            and summary.get("cycle_adjacency_variant_count") == 3
            and summary.get("field_consumption_variant_count") == 3
            and summary.get("representative_content_variant_count") == 2,
            "nonvacuity summary differs from the full evidence receipt",
        )
        pairs = receipt["field_graph_pair_effects"]
        nonvacuity_pair_count += len(pairs)
        nonvacuity_component_count += sum(
            len(pair["component_effects"]) for pair in pairs
        )
        if receipt.get("substantive_output_variation_required") is True:
            required_variation_count += 1
            _expect(
                receipt.get("substantive_response_field_graph_count") == 3,
                "required nonvacuity row lacks all three substantive responses",
            )
        primary = primary_by_id[primary_id]
        nonvacuity_output_rows.append(
            {
                "primary_unit_id": primary_id,
                "selection_seed": primary["selection_seed"],
                "control_id": primary["control_id"],
                "stress_assignments": primary["stress_assignments"],
                "normalized_summary_sha256": evidence_row["normalized_summary_sha256"],
                "receipt_fingerprint_sha256": summary["receipt_fingerprint_sha256"],
                "receipt": receipt,
            }
        )
    _expect(
        nonvacuity_pair_count == 192
        and nonvacuity_component_count == 768
        and required_variation_count == 16,
        "nonvacuity row counts differ from the frozen evidence",
    )

    abstention_rows: list[dict[str, Any]] = []
    for core_id in sorted(core_receipt_by_id):
        receipt = core_receipt_by_id[core_id]
        sealed = _mapping(
            receipt.get("sealed_prediction_receipt"), label="core sealed prediction"
        )
        if sealed.get("prediction_class") != "abstain":
            continue
        oracle = _mapping(
            receipt.get("oracle_truth_receipt"), label="core oracle truth"
        )
        reasons = _reason_tuple(sealed.get("reason_codes"), label="core reasons")
        expected_reasons = _reason_tuple(
            oracle.get("expected_prerequisite_reasons"), label="core expected reasons"
        )
        _expect(
            reasons == expected_reasons,
            "core abstention reasons differ from oracle route",
        )
        observed = core_by_id[core_id]
        abstention_rows.append(
            {
                "source_kind": "core-cell",
                "record_id": core_id,
                "primary_unit_id": observed["primary_unit_id"],
                "attempt_status": sealed["observed_attempt_status"],
                "prediction_class": sealed["prediction_class"],
                "expected_disposition": oracle["expected_disposition"],
                "reason_codes": list(reasons),
                "expected_reason_codes": list(expected_reasons),
            }
        )
    for cell_id in sorted(loop_receipt_by_id):
        receipt = loop_receipt_by_id[cell_id]
        sealed = _mapping(
            receipt.get("sealed_prediction_receipt"), label="loop sealed prediction"
        )
        if sealed.get("prediction_class") != "abstain":
            continue
        oracle = _mapping(
            receipt.get("oracle_truth_receipt"), label="loop oracle truth"
        )
        reasons = _reason_tuple(sealed.get("reason_codes"), label="loop reasons")
        expected_reasons = _reason_tuple(
            oracle.get("expected_prerequisite_reasons"), label="loop expected reasons"
        )
        _expect(
            reasons == expected_reasons,
            "loop abstention reasons differ from oracle route",
        )
        observed = crossed_by_id[cell_id]
        abstention_rows.append(
            {
                "source_kind": "loop-cell",
                "record_id": cell_id,
                "primary_unit_id": observed["primary_unit_id"],
                "attempt_status": sealed["observed_attempt_status"],
                "prediction_class": sealed["prediction_class"],
                "expected_disposition": oracle["expected_disposition"],
                "reason_codes": list(reasons),
                "expected_reason_codes": list(expected_reasons),
            }
        )
    for cell in sorted(confounder_cells, key=lambda item: item["cell_id"]):
        sealed = _mapping(
            cell.get("sealed_prediction_receipt"), label="D2 confounder prediction"
        )
        if sealed.get("prediction_class") != "abstain":
            continue
        reasons = _reason_tuple(
            sealed.get("reason_codes"), label="D2 confounder reasons"
        )
        expected_reasons = _reason_tuple(
            cell.get("expected_reason_codes"), label="D2 confounder expected reasons"
        )
        _expect(
            reasons == expected_reasons == _D2_SUPPORT_REASON,
            "D2 confounder abstention differs",
        )
        abstention_rows.append(
            {
                "source_kind": "d2-confounder-cell",
                "record_id": cell["cell_id"],
                "primary_unit_id": None,
                "attempt_status": sealed["observed_attempt_status"],
                "prediction_class": sealed["prediction_class"],
                "expected_disposition": "prerequisite_failure",
                "reason_codes": list(reasons),
                "expected_reason_codes": list(expected_reasons),
            }
        )
    abstention_rows.sort(key=lambda row: (row["source_kind"], row["record_id"]))
    abstention_counts = Counter(row["source_kind"] for row in abstention_rows)
    _expect(
        abstention_counts
        == Counter({"loop-cell": 288, "core-cell": 48, "d2-confounder-cell": 3})
        and sum(len(row["reason_codes"]) for row in abstention_rows) == 915,
        "abstention leaf counts differ from the frozen evidence",
    )

    nonorientable = [
        item
        for item in _walk_mappings(evidence.get("static_runtime_receipts"))
        if item.get("law") == "nonorientable_control"
        and item.get("check_id") == "nonorientable-cycle-control"
    ]
    _expect(
        len(nonorientable) == 3,
        "nonorientable control must have three mirrored receipts",
    )
    _expect(
        all(item == nonorientable[0] for item in nonorientable[1:])
        and nonorientable[0].get("state") == "insufficient"
        and _reason_tuple(
            nonorientable[0].get("reason_codes"), label="nonorientable reasons"
        )
        == ("orientation-reversing-cycle",),
        "nonorientable control mirrors differ",
    )
    d7 = _mapping(d6_decision.get("d7"), label="D6 D7 state")
    d8 = _mapping(d6_decision.get("d8"), label="D6 D8 state")
    d7_reasons = _reason_tuple(d7.get("reason_codes"), label="D7 reasons")
    d8_reasons = _reason_tuple(d8.get("reason_codes"), label="D8 reasons")
    _expect(
        d7.get("state") == d8.get("state") == "not_run"
        and d7_reasons
        == (
            "full-d2-d5-confirmation-path-not-implemented",
            "independent-construction-family-not-admitted",
        )
        and d8_reasons == ("d7-not-pass", "replay-not-run"),
        "D7/D8 typed nonpass routes differ from D6",
    )
    protocol_confounders = protocol.get("d2_core_confounders")
    if not isinstance(protocol_confounders, list) or len(protocol_confounders) != 2:
        _fail("protocol must contain two D2 confounder declarations")
    low_support_protocol = [
        row
        for row in protocol_confounders
        if row.get("confounder_id") == "low-amplitude-missing-candidate-support-abstain"
    ]
    _expect(
        len(low_support_protocol) == 1
        and _reason_tuple(
            low_support_protocol[0].get("expected_reason_codes"),
            label="protocol D2 confounder reasons",
        )
        == _D2_SUPPORT_REASON,
        "protocol low-support confounder route differs",
    )
    failure_route_rows = [
        {
            "route_id": "core-expected-prerequisite",
            "primary_unit_count": 16,
            "leaf_record_count": 48,
            "logical_reason_occurrence_count": 48,
            "stored_reason_occurrence_count": 96,
            "expected_state": "pass",
            "observed_attempt_status": "insufficient",
            "reason_codes": list(_PREREQUISITE_CORE_REASON),
            "coverage": "complete_observed_route",
        },
        {
            "route_id": "loop-expected-prerequisite",
            "primary_unit_count": 16,
            "leaf_record_count": 288,
            "logical_reason_occurrence_count": 864,
            "stored_reason_occurrence_count": 1728,
            "expected_state": "pass",
            "observed_attempt_status": "insufficient",
            "reason_codes": list(_PREREQUISITE_LOOP_REASONS),
            "coverage": "complete_observed_route",
        },
        {
            "route_id": "d2-low-support-confounder",
            "primary_unit_count": 0,
            "leaf_record_count": 3,
            "logical_reason_occurrence_count": 3,
            "stored_reason_occurrence_count": 8,
            "expected_state": "pass",
            "observed_attempt_status": "insufficient",
            "reason_codes": list(_D2_SUPPORT_REASON),
            "coverage": "complete_observed_route",
        },
        {
            "route_id": "d3-nonorientable-control",
            "primary_unit_count": 0,
            "leaf_record_count": 1,
            "logical_reason_occurrence_count": 1,
            "stored_reason_occurrence_count": 3,
            "expected_state": "insufficient",
            "observed_attempt_status": "insufficient",
            "reason_codes": ["orientation-reversing-cycle"],
            "coverage": "complete_observed_route",
        },
        {
            "route_id": "d7-not-run",
            "primary_unit_count": 0,
            "leaf_record_count": 1,
            "logical_reason_occurrence_count": 2,
            "stored_reason_occurrence_count": 2,
            "expected_state": "not_run",
            "observed_attempt_status": "not_run",
            "reason_codes": list(d7_reasons),
            "coverage": "complete_observed_route",
        },
        {
            "route_id": "d8-not-run",
            "primary_unit_count": 0,
            "leaf_record_count": 1,
            "logical_reason_occurrence_count": 2,
            "stored_reason_occurrence_count": 2,
            "expected_state": "not_run",
            "observed_attempt_status": "not_run",
            "reason_codes": list(d8_reasons),
            "coverage": "complete_observed_route",
        },
    ]

    selection = _mapping(protocol.get("selection"), label="protocol selection")
    seeds = selection.get("seeds")
    controls = selection.get("controls")
    stress_axes = selection.get("stress_axes")
    _expect(
        isinstance(seeds, list)
        and len(seeds) == 2
        and len(set(seeds)) == 2
        and isinstance(controls, list)
        and len(controls) == 4
        and isinstance(stress_axes, list)
        and len(stress_axes) == 3,
        "selection axes differ from the frozen design",
    )
    evaluation_design = _mapping(
        protocol.get("evaluation_design"), label="protocol evaluation design"
    )
    admission = _mapping(
        d6_decision.get("confirmation_admission_spec"), label="D6 admission"
    )
    implementation_registry = _mapping(
        protocol.get("implementation_registry"), label="implementation registry"
    )
    engine = _mapping(protocol.get("engine"), label="protocol engine")
    estimator_ids = [
        implementation_registry.get("surrogate_estimator_id"),
        "truth-blind-localized-amplitude-core-v0.3",
        "truth-blind-sampled-phase-total-v0.2",
    ]
    _expect(
        all(isinstance(item, str) for item in estimator_ids),
        "estimator IDs must be strings",
    )
    oracle_fingerprints = {row["oracle_fingerprint_sha256"] for row in core_rows} | {
        row["oracle_fingerprint_sha256"] for row in crossed_rows
    }
    _expect(
        len(oracle_fingerprints) == 1344,
        "oracle payload identities must be unique per leaf",
    )
    independence_rows = [
        {
            "dimension_id": "generator-construction",
            "identity_count": 1,
            "identities": [admission["selection_generator_family_id"]],
            "detail": {
                "construction_family_id": admission["selection_construction_family_id"],
                "generator_case_count": 4,
            },
            "sharing_relation": "all selection observations share one family",
            "independence_supported": False,
        },
        {
            "dimension_id": "seed-block",
            "identity_count": 2,
            "identities": seeds,
            "detail": {"seed_block_independence_proved": False},
            "sharing_relation": "same-family repeated seed blocks",
            "independence_supported": False,
        },
        {
            "dimension_id": "boundary-repeat",
            "identity_count": 2,
            "identities": ["central", "wide"],
            "detail": {
                "d2_repeated_measure": True,
                "d4_d5_execution_retained": True,
            },
            "sharing_relation": "paired nuisance repeats",
            "independence_supported": False,
        },
        {
            "dimension_id": "graph-family",
            "identity_count": 3,
            "identities": sorted(set(field_family.values())),
            "detail": {
                "graph_role_record_count": 6,
                "field_graph_ids": list(field_ids),
                "cycle_graph_ids": list(cycle_ids),
                "crossed_cells_per_execution": 18,
            },
            "sharing_relation": "within-execution repeated measures",
            "independence_supported": False,
        },
        {
            "dimension_id": "implementation",
            "identity_count": 1,
            "identities": [admission["selection_implementation_registry_sha256"]],
            "detail": {"engine_commit": engine.get("commit")},
            "sharing_relation": "one frozen implementation registry",
            "independence_supported": False,
        },
        {
            "dimension_id": "estimator",
            "identity_count": 3,
            "identities": estimator_ids,
            "detail": {"role_count": 3},
            "sharing_relation": "shared role-specific mechanisms",
            "independence_supported": False,
        },
        {
            "dimension_id": "threshold",
            "identity_count": 1,
            "identities": [d6_terminal["locked_thresholds_sha256"]],
            "detail": {"postselection_threshold_change_authorized": False},
            "sharing_relation": "one locked threshold set",
            "independence_supported": False,
        },
        {
            "dimension_id": "oracle",
            "identity_count": 1344,
            "identities": {
                "core_payload_count": 192,
                "loop_payload_count": 1152,
                "synthetic_oracle_mechanism_shared": True,
            },
            "detail": {"oracle_read_before_prediction": False},
            "sharing_relation": "different payload hashes do not prove independent observers",
            "independence_supported": False,
        },
        {
            "dimension_id": "evidence-bundle",
            "identity_count": 1,
            "identities": [terminal["result_evidence_root_sha256"]],
            "detail": {
                "terminal_artifact_sha256": manifest["terminal_artifact_sha256"],
                "consumption_id": consumption["consumption_id"],
            },
            "sharing_relation": "one terminal evidence lineage",
            "independence_supported": False,
        },
    ]
    _expect(
        len(independence_rows) == 9, "independence map must contain nine dimensions"
    )

    replication_rows = [
        {
            "category": "deterministic-replay",
            "evidence_state": "observed_scoped",
            "detail": {
                "graph_records_reconstructed": terminal.get(
                    "pr8_graph_records_reconstructed"
                ),
                "d8_isolated_replay_state": d8["state"],
            },
            "independent_confirmation_credit": False,
        },
        {
            "category": "same-family-replication",
            "evidence_state": "observed",
            "detail": {
                "seed_block_count": 2,
                "seed_block_independence_proved": evaluation_design.get(
                    "seed_block_independence_proved"
                ),
            },
            "independent_confirmation_credit": False,
        },
        {
            "category": "construction-diversity",
            "evidence_state": "absent",
            "detail": {
                "observed_construction_family_count": 1,
                "confirmation_family_admitted": d6_decision.get(
                    "confirmation_family_admitted"
                ),
                "graph_protocol_difference_is_construction_diversity": False,
            },
            "independent_confirmation_credit": False,
        },
        {
            "category": "implementation-diversity",
            "evidence_state": "absent",
            "detail": {"implementation_registry_count": 1},
            "independent_confirmation_credit": False,
        },
        {
            "category": "epistemic-independence",
            "evidence_state": "not_established",
            "detail": {"independent_confirmation_count": 0},
            "independent_confirmation_credit": False,
        },
    ]

    scientific_units = plan.get("scientific_units")
    if not isinstance(scientific_units, list):
        _fail("plan scientific_units must be an array")
    _expect(
        all(
            _mapping(item, label="scientific unit").get(
                "inferential_sample_size_claimed"
            )
            is False
            for item in scientific_units
        ),
        "scientific units must all deny inferential sample-size claims",
    )
    nonclaim_rows = [
        {
            "claim_ceiling": "level_0",
            "claim_delta": "none",
            "seed_block_independence_proved": evaluation_design.get(
                "seed_block_independence_proved"
            ),
            "inferential_sample_size_claimed": False,
            "observed_construction_family_count": 1,
            "confirmation_family_admitted": d6_decision.get(
                "confirmation_family_admitted"
            ),
            "seed_change_alone_sufficient": admission.get(
                "seed_change_alone_sufficient"
            ),
            "source_or_implementation_change_alone_sufficient": admission.get(
                "source_or_implementation_change_alone_sufficient"
            ),
            "graph_cells_are_repeated_measures": True,
            "boundary_variants_are_repeated_measures": True,
            "graph_protocol_difference_is_construction_diversity": False,
            "independent_confirmation_count": 0,
            "epistemic_independence_claimed": False,
            "construction_family_generalization_claimed": False,
        }
    ]
    _expect(
        nonclaim_rows[0]["seed_block_independence_proved"] is False
        and nonclaim_rows[0]["confirmation_family_admitted"] is False
        and nonclaim_rows[0]["seed_change_alone_sufficient"] is False
        and nonclaim_rows[0]["source_or_implementation_change_alone_sufficient"]
        is False,
        "epistemic-independence nonclaim differs from D6",
    )

    outputs = [
        _entry(
            13,
            _OUTPUT_IDS[0],
            matrix_rows,
            evaluation_unit="d4-d5-loop-execution-unit",
            matrix_shape=[3, 3],
            graph_cells_are_repeated_measures=True,
        ),
        _entry(
            14,
            _OUTPUT_IDS[1],
            role_rows,
            role_counts={"offcore_control": 64, "primary_boundary": 64},
            cells_per_role_per_execution=9,
        ),
        _entry(
            15,
            _OUTPUT_IDS[2],
            diagonal_rows,
            classification_basis="exact-declared-graph-family-equality",
            classified_cell_count=1152,
        ),
        _entry(
            16,
            _OUTPUT_IDS[3],
            effect_rows,
            component_row_count=component_row_count,
            loop_contrast_row_count=loop_contrast_row_count,
            numeric_adjacency_difference_available=False,
        ),
        _entry(
            17,
            _OUTPUT_IDS[4],
            support_rows,
            evaluable_cell_count=864,
            prerequisite_cell_count=288,
            numeric_support_available=False,
        ),
        _entry(
            18,
            _OUTPUT_IDS[5],
            stress_pair_rows,
            required_strata_are_overlapping_marginals=True,
            stratum_rows_may_be_summed=False,
        ),
        _entry(
            19,
            _OUTPUT_IDS[6],
            stress_role_rows,
            graph_cells_reduced_within_execution_first=True,
            execution_denominator_per_row=32,
        ),
        _entry(
            20,
            _OUTPUT_IDS[7],
            coverage_rows,
            score_denominator="expected_nonprerequisite_primary_units",
            prerequisite_rate_handling="excluded_but_mandatory",
        ),
        _entry(
            21,
            _OUTPUT_IDS[8],
            prerequisite_rows,
            core_leaf_count=48,
            loop_leaf_count=288,
            prerequisite_rows_are_mandatory=True,
        ),
        _entry(
            22,
            _OUTPUT_IDS[9],
            nonvacuity_output_rows,
            field_pair_row_count=192,
            component_row_count=768,
            required_variation_execution_count=16,
        ),
        _entry(
            23,
            _OUTPUT_IDS[10],
            abstention_rows,
            logical_reason_occurrence_count=915,
            top_level_empty_reason_codes_are_not_used=True,
        ),
        _entry(
            24,
            _OUTPUT_IDS[11],
            failure_route_rows,
            coverage_scope="observed-typed-routes-only",
            exhaustive_code_path_coverage=False,
        ),
        _entry(
            25,
            _OUTPUT_IDS[12],
            independence_rows,
            hash_inequality_implies_independence=False,
        ),
        _entry(
            26,
            _OUTPUT_IDS[13],
            replication_rows,
            graph_protocol_difference_is_construction_diversity=False,
        ),
        _entry(
            27,
            _OUTPUT_IDS[14],
            nonclaim_rows,
            claim_ceiling="level_0",
            claim_delta="none",
        ),
    ]
    _expect(
        [(item["sequence"], item["output_id"]) for item in outputs]
        == list(enumerate(_OUTPUT_IDS, start=13)),
        "derived output order differs from the frozen plan",
    )
    _expect(
        [item["row_count"] for item in outputs]
        == [128, 128, 4, 192, 1152, 108, 12, 6, 16, 64, 339, 6, 9, 5, 1],
        "derived output row counts differ from the frozen tables",
    )
    return outputs
