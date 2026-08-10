"""Private D5 evidence outputs for the D7 v1 descriptive successor."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence

from spirallens.core.canonical import canonical_json_bytes, sha256_bytes

from .common import QualificationContractError
from . import confirmation_v1_records as records
from .confirmation_v1_descriptive_common import (
    _integer,
    _mapping,
    _number,
    _output,
    _sequence,
    _string,
)
from .confirmation_v1_descriptive_d5_inputs import (
    _d5_crossed_inputs,
    _persisted_stratum_rows,
    _prerequisite_member_rows,
    _role_primary_units,
    _stress_graph_rows,
)

__all__: tuple[str, ...] = ()


def _nonvacuity_evidence_rows(
    result: Mapping[str, object],
    bundle: Mapping[str, object],
) -> tuple[list[dict[str, object]], int, int]:
    summaries = {
        _string(item.get("primary_unit_id"), label="nonvacuity primary_unit_id"): item
        for item in (
            _mapping(value, label="crossed nonvacuity")
            for value in _sequence(
                result.get("crossed_nonvacuity"), label="crossed nonvacuity"
            )
        )
    }
    receipts = [
        _mapping(item, label="nonvacuity evidence")
        for item in _sequence(
            bundle.get("nonvacuity_receipts"), label="nonvacuity receipts"
        )
    ]
    if len(summaries) != 64 or len(receipts) != 64:
        raise QualificationContractError("nonvacuity evidence universe is not closed")
    primary_units = {
        _string(item.get("primary_unit_id"), label="primary_unit_id"): item
        for item in (
            _mapping(value, label="primary unit")
            for value in _sequence(result.get("primary_units"), label="primary units")
        )
    }
    if set(primary_units) != set(summaries):
        raise QualificationContractError(
            "nonvacuity evidence primary units differ from the result"
        )
    rows = []
    pair_count = 0
    component_count = 0
    expected_pair_ids = {
        "a-mutual--a-radius",
        "a-mutual--a-shared",
        "a-radius--a-shared",
    }
    expected_components = {
        "amplitude",
        "identifiability_score",
        "section_values",
        "edge_coherence",
    }
    for evidence in receipts:
        if set(evidence) != {
            "schema_version",
            "primary_unit_id",
            "crossed_nonvacuity_receipt",
            "normalized_summary_sha256",
        }:
            raise QualificationContractError("nonvacuity evidence root fields differ")
        primary_unit_id = _string(
            evidence.get("primary_unit_id"), label="nonvacuity primary_unit_id"
        )
        summary = summaries.get(primary_unit_id)
        if summary is None:
            raise QualificationContractError(
                "nonvacuity evidence has no normalized summary"
            )
        receipt = _mapping(
            evidence.get("crossed_nonvacuity_receipt"),
            label="crossed nonvacuity receipt",
        )
        if evidence.get("normalized_summary_sha256") != sha256_bytes(
            canonical_json_bytes(summary)
        ) or summary.get("receipt_fingerprint_sha256") != sha256_bytes(
            canonical_json_bytes(receipt)
        ):
            raise QualificationContractError(
                "nonvacuity evidence fingerprints differ from the parent summary"
            )
        pair_effects = [
            _mapping(item, label="field graph pair effect")
            for item in _sequence(
                receipt.get("field_graph_pair_effects"),
                label="field graph pair effects",
            )
        ]
        if (
            len(pair_effects) != 3
            or {_string(item.get("pair_id"), label="pair_id") for item in pair_effects}
            != expected_pair_ids
        ):
            raise QualificationContractError(
                "nonvacuity field-graph pair universe differs"
            )
        pair_count += len(pair_effects)
        for pair in pair_effects:
            components = [
                _mapping(item, label="component effect")
                for item in _sequence(
                    pair.get("component_effects"), label="component effects"
                )
            ]
            if (
                len(components) != 4
                or {
                    _string(item.get("component_name"), label="component_name")
                    for item in components
                }
                != expected_components
            ):
                raise QualificationContractError(
                    "nonvacuity component-effect universe differs"
                )
            component_count += len(components)
        unit = primary_units[primary_unit_id]
        rows.append(
            {
                "primary_unit_id": primary_unit_id,
                "control_id": _string(unit.get("control_id"), label="control_id"),
                "selection_seed": _integer(
                    unit.get("selection_seed"), label="selection_seed"
                ),
                "stress_assignments": [
                    dict(_mapping(item, label="stress assignment"))
                    for item in _sequence(
                        unit.get("stress_assignments"), label="stress assignments"
                    )
                ],
                "normalized_summary_sha256": _string(
                    evidence.get("normalized_summary_sha256"),
                    label="normalized_summary_sha256",
                ),
                "receipt_fingerprint_sha256": _string(
                    summary.get("receipt_fingerprint_sha256"),
                    label="receipt_fingerprint_sha256",
                ),
                "receipt": receipt,
            }
        )
    if (
        {str(row["primary_unit_id"]) for row in rows} != set(summaries)
        or pair_count != 192
        or component_count != 768
    ):
        raise QualificationContractError(
            "nonvacuity evidence coverage differs from 64/192/768"
        )
    rows.sort(key=lambda row: str(row["primary_unit_id"]))
    return rows, pair_count, component_count


def _abstention_evidence_rows(
    result: Mapping[str, object],
    bundle: Mapping[str, object],
) -> list[dict[str, object]]:
    core_cells = {
        _string(item.get("core_cell_id"), label="core_cell_id"): item
        for item in (
            _mapping(value, label="core cell")
            for value in _sequence(result.get("core_cells"), label="core cells")
        )
    }
    loop_cells = {
        _string(item.get("cell_id"), label="loop cell_id"): item
        for item in (
            _mapping(value, label="loop cell")
            for value in _sequence(result.get("crossed_cells"), label="crossed cells")
        )
    }
    rows = []
    for source_kind, receipt_key, id_key, summaries in (
        ("core-cell", "core_cell_receipts", "core_cell_id", core_cells),
        ("loop-cell", "loop_cell_receipts", "cell_id", loop_cells),
    ):
        for value in _sequence(bundle.get(receipt_key), label=receipt_key):
            evidence = _mapping(value, label=source_kind)
            record_id = _string(evidence.get(id_key), label=id_key)
            summary = summaries.get(record_id)
            if summary is None:
                raise QualificationContractError(
                    "abstention evidence has no normalized cell summary"
                )
            sealed = _mapping(
                evidence.get("sealed_prediction_receipt"),
                label="sealed prediction receipt",
            )
            if sealed.get("prediction_class") != "abstain":
                continue
            oracle = _mapping(
                evidence.get("oracle_truth_receipt"), label="oracle truth receipt"
            )
            expected_reasons = [
                _string(reason, label="expected reason code")
                for reason in _sequence(
                    oracle.get("expected_prerequisite_reasons"),
                    label="expected prerequisite reasons",
                )
            ]
            reason_codes = [
                _string(reason, label="reason code")
                for reason in _sequence(
                    sealed.get("reason_codes"), label="sealed reason codes"
                )
            ]
            if (
                summary.get("attempt_status") != sealed.get("observed_attempt_status")
                or summary.get("prediction_class") != sealed.get("prediction_class")
                or summary.get("expected_disposition")
                != oracle.get("expected_disposition")
                or summary.get("reason_codes") != []
                or expected_reasons != reason_codes
            ):
                raise QualificationContractError(
                    "abstention leaf differs from its full evidence receipt"
                )
            rows.append(
                {
                    "source_kind": source_kind,
                    "record_id": record_id,
                    "primary_unit_id": _string(
                        summary.get("primary_unit_id"), label="primary_unit_id"
                    ),
                    "expected_disposition": _string(
                        oracle.get("expected_disposition"),
                        label="expected disposition",
                    ),
                    "attempt_status": _string(
                        sealed.get("observed_attempt_status"),
                        label="observed attempt status",
                    ),
                    "prediction_class": "abstain",
                    "expected_reason_codes": expected_reasons,
                    "reason_codes": reason_codes,
                }
            )

    matrix = _mapping(
        bundle.get("d2_confounder_matrix_receipt"),
        label="D2 confounder matrix receipt",
    )
    for value in _sequence(matrix.get("cells"), label="D2 confounder cells"):
        cell = _mapping(value, label="D2 confounder cell")
        sealed = _mapping(
            cell.get("sealed_prediction_receipt"),
            label="D2 confounder sealed prediction",
        )
        if sealed.get("prediction_class") != "abstain":
            continue
        expected_reasons = [
            _string(reason, label="confounder expected reason code")
            for reason in _sequence(
                cell.get("expected_reason_codes"),
                label="confounder expected reason codes",
            )
        ]
        reason_codes = [
            _string(reason, label="confounder reason code")
            for reason in _sequence(
                sealed.get("reason_codes"), label="confounder reason codes"
            )
        ]
        if (
            cell.get("expected_attempt_status") != sealed.get("observed_attempt_status")
            or cell.get("expected_prediction_class") != sealed.get("prediction_class")
            or expected_reasons != reason_codes
            or cell.get("state") != "pass"
        ):
            raise QualificationContractError("D2 confounder abstention route differs")
        rows.append(
            {
                "source_kind": "d2-confounder-cell",
                "record_id": _string(cell.get("cell_id"), label="confounder cell_id"),
                "primary_unit_id": None,
                "expected_disposition": "prerequisite_failure",
                "attempt_status": _string(
                    sealed.get("observed_attempt_status"),
                    label="observed attempt status",
                ),
                "prediction_class": "abstain",
                "expected_reason_codes": expected_reasons,
                "reason_codes": reason_codes,
            }
        )
    rows.sort(
        key=lambda row: (
            str(row["source_kind"]),
            str(row["record_id"]),
            str(row["primary_unit_id"]),
        )
    )
    if len(rows) != 339 or sum(len(row["reason_codes"]) for row in rows) != 915:
        raise QualificationContractError(
            "abstention evidence coverage differs from 339/915"
        )
    return rows


def _typed_failure_routes(
    protocol: Mapping[str, object],
    result: Mapping[str, object],
    bundle: Mapping[str, object],
    metamorphic_rows: Sequence[Mapping[str, object]],
    d6_decision: Mapping[str, object],
    abstention_rows: Sequence[Mapping[str, object]],
) -> list[dict[str, object]]:
    core_reason = "amplitude_at_or_below_core_ceiling_not_localized"
    loop_reasons = [
        "boundary_amplitude_at_or_below_floor",
        "boundary_coherence_at_or_below_floor",
        "boundary_identifiability_at_or_below_floor",
    ]
    confounder_reason = "candidate_measurement_support_below_minimum"
    d3_reason = "orientation-reversing-cycle"

    core_rows = [row for row in abstention_rows if row["source_kind"] == "core-cell"]
    loop_rows = [row for row in abstention_rows if row["source_kind"] == "loop-cell"]
    confounder_rows = [
        row for row in abstention_rows if row["source_kind"] == "d2-confounder-cell"
    ]
    if (
        len(core_rows) != 48
        or len({str(row["primary_unit_id"]) for row in core_rows}) != 16
        or any(row["reason_codes"] != [core_reason] for row in core_rows)
        or len(loop_rows) != 288
        or len({str(row["primary_unit_id"]) for row in loop_rows}) != 16
        or any(row["reason_codes"] != loop_reasons for row in loop_rows)
        or len(confounder_rows) != 3
        or any(row["reason_codes"] != [confounder_reason] for row in confounder_rows)
    ):
        raise QualificationContractError(
            "typed prerequisite routes differ from the evidence leaves"
        )

    core_evidence = [
        _mapping(value, label="core evidence")
        for value in _sequence(
            bundle.get("core_cell_receipts"), label="core cell receipts"
        )
    ]
    core_stored = sum(
        core_reason
        in _sequence(
            _mapping(item.get(surface), label=surface).get(field),
            label=f"{surface} {field}",
        )
        for item in core_evidence
        for surface, field in (
            ("sealed_prediction_receipt", "reason_codes"),
            ("oracle_truth_receipt", "expected_prerequisite_reasons"),
        )
    )
    loop_evidence = [
        _mapping(value, label="loop evidence")
        for value in _sequence(
            bundle.get("loop_cell_receipts"), label="loop cell receipts"
        )
    ]
    loop_stored = sum(
        reason
        in _sequence(
            _mapping(item.get(surface), label=surface).get(field),
            label=f"{surface} {field}",
        )
        for item in loop_evidence
        for reason in loop_reasons
        for surface, field in (
            ("sealed_prediction_receipt", "reason_codes"),
            ("oracle_truth_receipt", "expected_prerequisite_reasons"),
        )
    )

    protocol_confounders = [
        _mapping(value, label="protocol D2 confounder")
        for value in _sequence(
            protocol.get("d2_core_confounders"), label="protocol D2 confounders"
        )
    ]
    matrix = _mapping(
        bundle.get("d2_confounder_matrix_receipt"),
        label="D2 confounder matrix receipt",
    )
    matrix_declarations = [
        _mapping(value, label="D2 confounder declaration")
        for value in _sequence(
            matrix.get("confounder_declarations"),
            label="D2 confounder declarations",
        )
    ]
    matrix_cells = [
        _mapping(value, label="D2 confounder cell")
        for value in _sequence(matrix.get("cells"), label="D2 confounder cells")
    ]
    confounder_stored = (
        sum(
            confounder_reason
            in _sequence(
                item.get("expected_reason_codes"), label="expected reason codes"
            )
            for item in protocol_confounders
        )
        + sum(
            confounder_reason
            in _sequence(
                item.get("expected_reason_codes"), label="expected reason codes"
            )
            for item in matrix_declarations
        )
        + sum(
            confounder_reason
            in _sequence(
                item.get("expected_reason_codes"), label="expected reason codes"
            )
            for item in matrix_cells
        )
        + sum(
            confounder_reason
            in _sequence(
                _mapping(
                    item.get("sealed_prediction_receipt"),
                    label="D2 confounder prediction",
                ).get("reason_codes"),
                label="D2 confounder reason codes",
            )
            for item in matrix_cells
        )
    )

    representation_families = [
        _mapping(value, label="static runtime receipt")
        for value in _sequence(
            bundle.get("static_runtime_receipts"), label="static runtime receipts"
        )
        if _mapping(value, label="static runtime receipt").get("evidence_id")
        == "representation-gauge-pipeline-rerun-verified"
    ]
    if len(representation_families) != 1:
        raise QualificationContractError("D3 typed route family is not unique")
    family = representation_families[0]
    aggregate = _mapping(
        family.get("aggregate_runtime_receipt"),
        label="representation aggregate receipt",
    )
    obligation_receipts = [
        _mapping(value, label="D3 obligation receipt")
        for value in _sequence(
            family.get("obligation_receipts"), label="D3 obligation receipts"
        )
    ]
    d3_receipts = [
        _mapping(item.get("receipt"), label="D3 nonorientable receipt")
        for item in obligation_receipts
        if item.get("obligation_id") == "nonorientable-control"
    ]
    d3_receipts.extend(
        _mapping(value, label="D3 algebraic check")
        for value in _sequence(
            aggregate.get("all_algebraic_checks"), label="D3 algebraic checks"
        )
        if _mapping(value, label="D3 algebraic check").get("check_id")
        == "nonorientable-cycle-control"
    )
    d3_receipts.extend(
        _mapping(
            _mapping(value, label="D3 aggregate check").get("receipt"),
            label="D3 aggregate check receipt",
        )
        for value in _sequence(aggregate.get("checks"), label="D3 aggregate checks")
        if _mapping(
            _mapping(value, label="D3 aggregate check").get("receipt"),
            label="D3 aggregate check receipt",
        ).get("check_id")
        == "nonorientable-cycle-control"
    )
    d3_metamorphic = [
        row
        for row in metamorphic_rows
        if row.get("obligation_id") == "nonorientable-control"
    ]
    if (
        len(d3_receipts) != 3
        or any(
            receipt.get("law") != "nonorientable_control"
            or receipt.get("state") != "insufficient"
            or receipt.get("reason_codes") != [d3_reason]
            for receipt in d3_receipts
        )
        or len(d3_metamorphic) != 1
        or d3_metamorphic[0].get("state") != "insufficient"
    ):
        raise QualificationContractError("D3 nonorientable typed route differs")

    decisions = {}
    for gate_id, expected_reasons in (
        (
            "d7",
            [
                "full-d2-d5-confirmation-path-not-implemented",
                "independent-construction-family-not-admitted",
            ],
        ),
        ("d8", ["d7-not-pass", "replay-not-run"]),
    ):
        decision = _mapping(d6_decision.get(gate_id), label=f"{gate_id} decision")
        reasons = [
            _string(reason, label=f"{gate_id} reason code")
            for reason in _sequence(
                decision.get("reason_codes"), label=f"{gate_id} reason codes"
            )
        ]
        if decision.get("state") != "not_run" or reasons != expected_reasons:
            raise QualificationContractError(f"{gate_id} typed not-run route differs")
        decisions[gate_id] = reasons

    if core_stored != 96 or loop_stored != 1_728 or confounder_stored != 8:
        raise QualificationContractError(
            "typed prerequisite stored-reason coverage differs"
        )
    routes = [
        {
            "coverage": "complete_observed_route",
            "expected_state": "pass",
            "leaf_record_count": 48,
            "logical_reason_occurrence_count": 48,
            "observed_attempt_status": "insufficient",
            "primary_unit_count": 16,
            "reason_codes": [core_reason],
            "route_id": "core-expected-prerequisite",
            "stored_reason_occurrence_count": core_stored,
        },
        {
            "coverage": "complete_observed_route",
            "expected_state": "pass",
            "leaf_record_count": 288,
            "logical_reason_occurrence_count": 864,
            "observed_attempt_status": "insufficient",
            "primary_unit_count": 16,
            "reason_codes": loop_reasons,
            "route_id": "loop-expected-prerequisite",
            "stored_reason_occurrence_count": loop_stored,
        },
        {
            "coverage": "complete_observed_route",
            "expected_state": "pass",
            "leaf_record_count": 3,
            "logical_reason_occurrence_count": 3,
            "observed_attempt_status": "insufficient",
            "primary_unit_count": 0,
            "reason_codes": [confounder_reason],
            "route_id": "d2-low-support-confounder",
            "stored_reason_occurrence_count": confounder_stored,
        },
        {
            "coverage": "complete_observed_route",
            "expected_state": "insufficient",
            "leaf_record_count": 1,
            "logical_reason_occurrence_count": 1,
            "observed_attempt_status": "insufficient",
            "primary_unit_count": 0,
            "reason_codes": [d3_reason],
            "route_id": "d3-nonorientable-control",
            "stored_reason_occurrence_count": len(d3_receipts),
        },
        {
            "coverage": "complete_observed_route",
            "expected_state": "not_run",
            "leaf_record_count": 1,
            "logical_reason_occurrence_count": 2,
            "observed_attempt_status": "not_run",
            "primary_unit_count": 0,
            "reason_codes": decisions["d7"],
            "route_id": "d7-not-run",
            "stored_reason_occurrence_count": 2,
        },
        {
            "coverage": "complete_observed_route",
            "expected_state": "not_run",
            "leaf_record_count": 1,
            "logical_reason_occurrence_count": 2,
            "observed_attempt_status": "not_run",
            "primary_unit_count": 0,
            "reason_codes": decisions["d8"],
            "route_id": "d8-not-run",
            "stored_reason_occurrence_count": 2,
        },
    ]
    return routes


def _d5_outputs(
    protocol: Mapping[str, object],
    result: Mapping[str, object],
    metamorphic_rows: Sequence[Mapping[str, object]],
    d6_decision: Mapping[str, object],
) -> list[records.D7V1DescriptiveOutput]:
    (
        crossed_cells,
        expected_by_id,
        stratum_ids,
        field_graph_ids,
        cycle_graph_ids,
    ) = _d5_crossed_inputs(protocol, result)
    stress_rows = _stress_graph_rows(
        crossed_cells,
        expected_by_id,
        stratum_ids,
        field_graph_ids,
        cycle_graph_ids,
    )
    global_cell_error = max(
        float(row["maximum_oracle_absolute_error_cycles"]) for row in stress_rows
    )
    global_cell_error_rows = [
        {
            key: row[key]
            for key in (
                "stratum_id",
                "field_graph_id",
                "cycle_graph_id",
                "loop_role",
            )
        }
        for row in stress_rows
        if row["maximum_oracle_absolute_error_cycles"] == global_cell_error
    ]
    if global_cell_error != 2.220446049250313e-16 or len(global_cell_error_rows) != 8:
        raise QualificationContractError(
            "D5 graph-cell worst-case error differs from the parent"
        )

    role_units = _role_primary_units(result, expected_by_id)
    role_groups: dict[tuple[str, str], list[Mapping[str, object]]] = defaultdict(list)
    for item in role_units:
        for stratum_id in _sequence(item.get("stratum_ids"), label="stratum_ids"):
            role_groups[
                (
                    _string(stratum_id, label="stratum_id"),
                    _string(item.get("loop_role"), label="loop_role"),
                )
            ].append(item)
    role_rows = []
    for stratum_id in stratum_ids:
        for loop_role in ("offcore_control", "primary_boundary"):
            members = role_groups.get((stratum_id, loop_role), [])
            if len(members) != 32:
                raise QualificationContractError(
                    "each D5 role stress row must retain 32 executions"
                )
            eligible = [
                item
                for item in members
                if item.get("expected_disposition") != "prerequisite_failure"
            ]
            evaluable = [
                item for item in eligible if item.get("attempt_status") == "evaluable"
            ]
            prerequisites = [
                item
                for item in members
                if item.get("expected_disposition") == "prerequisite_failure"
            ]
            spans = [
                _number(
                    item.get("continuous_span_cycles"),
                    label="execution graph total span",
                )
                for item in evaluable
            ]
            errors = [
                _number(
                    item.get("maximum_oracle_absolute_error_cycles"),
                    label="execution oracle error",
                )
                for item in evaluable
            ]
            if len(evaluable) != 24 or len(prerequisites) != 8:
                raise QualificationContractError(
                    "D5 role stress denominator differs from 32/24/8"
                )
            maximum_span = max(spans)
            maximum_error = max(errors)
            role_rows.append(
                {
                    "stratum_id": stratum_id,
                    "loop_role": loop_role,
                    "attempted_execution_count": len(members),
                    "evaluable_execution_count": len(evaluable),
                    "prerequisite_execution_count": len(prerequisites),
                    "graph_cells_reduced_within_execution_first": True,
                    "maximum_execution_graph_total_span_cycles": maximum_span,
                    "worst_span_primary_unit_ids": sorted(
                        _string(item.get("primary_unit_id"), label="primary_unit_id")
                        for item in evaluable
                        if item.get("continuous_span_cycles") == maximum_span
                    ),
                    "maximum_execution_oracle_error_cycles": maximum_error,
                    "worst_error_primary_unit_ids": sorted(
                        _string(item.get("primary_unit_id"), label="primary_unit_id")
                        for item in evaluable
                        if item.get("maximum_oracle_absolute_error_cycles")
                        == maximum_error
                    ),
                    "coverage": len(evaluable) / len(eligible),
                    "abstention_fraction": (
                        sum(
                            item.get("prediction_class") == "abstain"
                            for item in eligible
                        )
                        / len(eligible)
                    ),
                    "score_denominator": "expected_nonprerequisite_primary_units",
                }
            )
    if len(role_rows) != 12 or set(role_groups) != {
        (stratum_id, loop_role)
        for stratum_id in stratum_ids
        for loop_role in ("offcore_control", "primary_boundary")
    }:
        raise QualificationContractError("D5 role stress table is not closed")
    global_span = max(
        float(row["maximum_execution_graph_total_span_cycles"]) for row in role_rows
    )
    global_role_error = max(
        float(row["maximum_execution_oracle_error_cycles"]) for row in role_rows
    )
    global_span_rows = [
        {"stratum_id": row["stratum_id"], "loop_role": row["loop_role"]}
        for row in role_rows
        if row["maximum_execution_graph_total_span_cycles"] == global_span
    ]
    global_role_error_rows = [
        {"stratum_id": row["stratum_id"], "loop_role": row["loop_role"]}
        for row in role_rows
        if row["maximum_execution_oracle_error_cycles"] == global_role_error
    ]
    if (
        global_span != 2.220446049250313e-16
        or global_role_error != 2.220446049250313e-16
        or len(global_span_rows) != 4
        or len(global_role_error_rows) != 4
    ):
        raise QualificationContractError(
            "D5 within-execution worst cases differ from the parent"
        )

    persisted_strata = _persisted_stratum_rows(protocol, result)
    bundle = _mapping(result.get("evidence_bundle"), label="evidence bundle")
    core_primary_units = [
        _mapping(item, label="core primary unit")
        for item in _sequence(
            result.get("core_primary_units"), label="core primary units"
        )
    ]
    loop_primary_units = [
        _mapping(item, label="loop primary unit")
        for item in _sequence(result.get("primary_units"), label="primary units")
    ]
    prerequisite_rows = _prerequisite_member_rows(
        result,
        bundle,
        core_primary_units,
        loop_primary_units,
    )
    nonvacuity_rows, pair_count, component_count = _nonvacuity_evidence_rows(
        result, bundle
    )
    required_variation_count = sum(
        _mapping(row.get("receipt"), label="nonvacuity receipt").get(
            "substantive_output_variation_required"
        )
        is True
        for row in nonvacuity_rows
    )
    if required_variation_count != 16:
        raise QualificationContractError(
            "required nonvacuity execution count differs from 16"
        )
    abstention_rows = _abstention_evidence_rows(result, bundle)
    typed_rows = _typed_failure_routes(
        protocol,
        result,
        bundle,
        metamorphic_rows,
        d6_decision,
        abstention_rows,
    )

    return [
        _output(
            "worst-case-by-stress-stratum",
            {
                "rows": stress_rows,
                "global_maximum_oracle_absolute_error_cycles": global_cell_error,
                "global_worst_row_keys": global_cell_error_rows,
                "required_strata_are_overlapping_marginals": True,
                "stratum_rows_may_be_summed": False,
                "graph_cells_are_repeated_measures": True,
            },
        ),
        _output(
            "loop-role-separated-worst-case-and-coverage-table",
            {
                "rows": role_rows,
                "global_maximum_execution_graph_total_span_cycles": global_span,
                "global_worst_span_row_keys": global_span_rows,
                "global_maximum_execution_oracle_error_cycles": global_role_error,
                "global_worst_error_row_keys": global_role_error_rows,
                "execution_denominator_per_row": 32,
                "graph_cells_reduced_within_execution_first": True,
                "loop_roles_collapsed": False,
            },
        ),
        _output(
            "coverage-abstention-recall-specificity-table",
            {
                "rows": persisted_strata,
                "score_denominator": "expected_nonprerequisite_primary_units",
                "prerequisite_rate_handling": "excluded_but_mandatory",
                "stratum_rows_may_be_summed": False,
                "silent_denominator_change": False,
            },
        ),
        _output(
            "mandatory-prerequisite-failure-table",
            {
                "rows": prerequisite_rows,
                "primary_unit_count": len(prerequisite_rows),
                "core_leaf_record_count": sum(
                    len(row["core_cells"]) for row in prerequisite_rows
                ),
                "loop_leaf_record_count": sum(
                    len(row["loop_cells"]) for row in prerequisite_rows
                ),
                "core_boundary_repeats_retained": True,
                "expected_prerequisite_failure_is_required_pass_route": True,
                "prerequisite_failures_removed_from_artifact": False,
            },
        ),
        _output(
            "required-nonvacuity-evidence",
            {
                "rows": nonvacuity_rows,
                "execution_count": len(nonvacuity_rows),
                "field_graph_pair_effect_count": pair_count,
                "component_effect_count": component_count,
                "required_variation_execution_count": required_variation_count,
                "all_states_pass": all(
                    _mapping(row["receipt"], label="nonvacuity receipt").get("state")
                    == "pass"
                    for row in nonvacuity_rows
                ),
                "graph_cells_are_repeated_measures": True,
                "id_only_nonvacuity_forbidden": True,
            },
        ),
        _output(
            "abstention-reason-table",
            {
                "rows": abstention_rows,
                "abstention_count": len(abstention_rows),
                "logical_reason_occurrence_count": sum(
                    len(row["reason_codes"]) for row in abstention_rows
                ),
                "top_level_empty_reason_codes_do_not_erase_evidence_receipts": True,
                "abstention_relabelled_as_failure": False,
            },
        ),
        _output(
            "typed-failure-coverage",
            {
                "rows": typed_rows,
                "route_count": len(typed_rows),
                "coverage_scope": "observed-typed-routes-only",
                "exhaustive": False,
                "insufficient_retained_as_distinct_status": True,
                "not_run_retained_as_distinct_status": True,
            },
        ),
    ]
