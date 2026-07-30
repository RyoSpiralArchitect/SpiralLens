"""Pure structural joins for the six future D7 result components.

This validator has no target loader, persistence, writer, runner, seed
supplier, authority, or official instance.  It joins already typed,
attempt-independent component bytes to one structural scientific payload.
"""

from __future__ import annotations

from collections import Counter

from spirallens.core.canonical import canonical_json_sha256

from . import confirmation_attempt_records as ar
from . import confirmation_result_components as c
from .aggregation import (
    REASON_ABSTENTION_ABOVE_MAXIMUM,
    REASON_CORE_CANDIDATE_GRAPH_DRIFT,
    REASON_COVERAGE_BELOW_MINIMUM,
    REASON_GRAPH_CELL_PREDICTION_DISAGREEMENT,
    REASON_LOOP_TOTAL_GRAPH_DRIFT,
    REASON_RECALL_BELOW_MINIMUM,
    REASON_SPECIFICITY_BELOW_MINIMUM,
)
from .common import (
    AttemptStatus,
    CorePredictionClass,
    EvaluationUnit,
    LoopDisposition,
    LoopPredictionClass,
    QualificationContractError,
    QualificationState,
)
from .contracts import (
    CoreCellSummary,
    CorePrimaryUnitSummary,
    CrossedCellSummary,
    PrimaryUnitSummary,
)
from .protocol import LoopRole

__all__: tuple[str, ...] = ()

_EXACT_COMPONENT_TYPES = (
    c.D7ExecutionEventLedgerPayload,
    c.D7CoreCellOutcomesPayload,
    c.D7LoopCellOutcomesPayload,
    c.D7PrimaryUnitOutcomesPayload,
    c.D7RequiredStratumOutcomesPayload,
    c.D7AggregateGateOutcomesPayload,
)
_CASE_SEMANTICS = frozenset(
    {
        "localized-core|nonzero",
        "localized-core|null",
        "no-core|null",
        "prerequisite-failure|prerequisite-failure",
    }
)
_EVENT_STAGE_PAYLOAD_SCHEME = "spirallens.d7-event-stage-payload.v0.1"


def _fail(message: str) -> None:
    raise QualificationContractError(message)


def _validate_component_coordinates(
    components: tuple[c.D7ResultComponentPayload, ...],
    result_payload: ar.D7ScientificResultPayload,
) -> None:
    for component in components:
        if (
            component.replay_target_sha256 != result_payload.replay_target_sha256
            or component.full_inventory_sha256 != result_payload.full_inventory_sha256
            or component.aggregation_sha256 != result_payload.aggregation_sha256
        ):
            _fail("component target/inventory/aggregation coordinates differ")


def _validate_actual_bindings(
    components: tuple[c.D7ResultComponentPayload, ...],
    result_payload: ar.D7ScientificResultPayload,
) -> None:
    for component, binding in zip(
        components, result_payload.component_bindings, strict=True
    ):
        if (
            binding.component_id is not component.component_id
            or binding.component_contract_id != component.component_contract_id
            or binding.component_canonical_sha256 != component.canonical_sha256
            or binding.byte_count != len(component.canonical_bytes)
            or binding.record_count != len(component.records)
        ):
            _fail("scientific payload binding differs from actual component bytes")


def _index_cells(
    component: c.D7CoreCellOutcomesPayload | c.D7LoopCellOutcomesPayload,
    *,
    id_attribute: str,
    label: str,
) -> dict[str, object]:
    result: dict[str, object] = {}
    for row in component.records:
        primary_id = row.primary_unit_id
        identifier = getattr(row, id_attribute)
        if identifier in result:
            _fail(f"{label} contains duplicate cell ID")
        result[identifier] = row
        if not primary_id:
            _fail(f"{label} contains an empty primary ID")
    return result


def _d7_event_stage_payload_sha256s(
    *,
    replay_target_sha256: str,
    full_inventory_sha256: str,
    aggregation_sha256: str,
    lane_id: str,
    lane_kind: c.D7ExecutionLaneKind,
    cell_id: str,
    outcome: CoreCellSummary | CrossedCellSummary,
) -> tuple[str, ...]:
    """Mechanically derive all six attempt-independent event payload identities."""

    row = outcome.to_dict()
    lane = {
        "lane_id": lane_id,
        "lane_kind": lane_kind.value,
        "cell_id": cell_id,
    }
    if type(outcome) is CoreCellSummary:
        if (
            lane_kind is not c.D7ExecutionLaneKind.CORE
            or cell_id != outcome.core_cell_id
            or lane_id != f"core.{cell_id}"
        ):
            _fail("core event lane identity differs from its exact outcome row")
        blind_fields = (
            "primary_unit_id",
            "field_graph_id",
            "field_graph_fingerprint_sha256",
            "field_estimate_fingerprint_sha256",
            "blind_input_fingerprint_sha256",
        )
        prediction_fields = (
            "prediction_fingerprint_sha256",
            "candidate_fingerprint_sha256",
            "prediction_class",
        )
        oracle_fields = (
            "expected_disposition",
            "oracle_fingerprint_sha256",
            "oracle_anchor_fingerprint_sha256",
        )
        scored_fields = (
            "attempt_status",
            "candidate_anchor_symmetric_difference_rows",
            "state",
            "reason_codes",
        )
    elif type(outcome) is CrossedCellSummary:
        if (
            lane_kind is not c.D7ExecutionLaneKind.LOOP
            or cell_id != outcome.cell_id
            or lane_id != f"loop.{cell_id}"
        ):
            _fail("loop event lane identity differs from its exact outcome row")
        blind_fields = (
            "primary_unit_id",
            "field_graph_id",
            "cycle_graph_id",
            "loop_role",
            "field_graph_fingerprint_sha256",
            "cycle_graph_fingerprint_sha256",
            "field_estimate_fingerprint_sha256",
            "cycle_binding_fingerprint_sha256",
            "representative_content_sha256",
            "blind_input_fingerprint_sha256",
        )
        prediction_fields = (
            "prediction_fingerprint_sha256",
            "prediction_class",
            "continuous_signed_total_cycles",
        )
        oracle_fields = (
            "expected_disposition",
            "oracle_fingerprint_sha256",
        )
        scored_fields = (
            "attempt_status",
            "oracle_absolute_error_cycles",
            "state",
            "reason_codes",
        )
    else:
        raise TypeError("event outcome must be an exact core or loop cell summary")

    stage_payloads = (
        {
            "replay_target_sha256": replay_target_sha256,
            "full_inventory_sha256": full_inventory_sha256,
            "aggregation_sha256": aggregation_sha256,
            "result_schema_sha256": (
                ar.D7_SCIENTIFIC_RESULT_IMPLEMENTATION_SCHEMA_SHA256
            ),
        },
        {name: row[name] for name in blind_fields},
        {name: row[name] for name in prediction_fields},
        {name: row[name] for name in oracle_fields},
        {name: row[name] for name in scored_fields},
    )
    digests = tuple(
        canonical_json_sha256(
            {
                "scheme": _EVENT_STAGE_PAYLOAD_SCHEME,
                "stage": stage.value,
                "lane": lane,
                "payload": payload,
            }
        )
        for stage, payload in zip(
            tuple(c.D7ExecutionStage)[:-1],
            stage_payloads,
            strict=True,
        )
    )
    return (*digests, canonical_json_sha256(row))


def _validate_event_lanes(
    event_component: c.D7ExecutionEventLedgerPayload,
    core_component: c.D7CoreCellOutcomesPayload,
    loop_component: c.D7LoopCellOutcomesPayload,
) -> None:
    core_by_id = {row.core_cell_id: row for row in core_component.records}
    loop_by_id = {row.cell_id: row for row in loop_component.records}
    expected_lane_ids = tuple(
        sorted(
            (
                *(f"core.{identifier}" for identifier in core_by_id),
                *(f"loop.{identifier}" for identifier in loop_by_id),
            )
        )
    )
    observed_lane_ids = tuple(row.lane_id for row in event_component.records)
    if len(expected_lane_ids) != 1344 or observed_lane_ids != expected_lane_ids:
        _fail("event lanes differ from exact 192-core plus 1152-loop inventory")
    for lane in event_component.records:
        outcome = (
            core_by_id[lane.cell_id]
            if lane.lane_kind is c.D7ExecutionLaneKind.CORE
            else loop_by_id[lane.cell_id]
        )
        expected_payloads = _d7_event_stage_payload_sha256s(
            replay_target_sha256=event_component.replay_target_sha256,
            full_inventory_sha256=event_component.full_inventory_sha256,
            aggregation_sha256=event_component.aggregation_sha256,
            lane_id=lane.lane_id,
            lane_kind=lane.lane_kind,
            cell_id=lane.cell_id,
            outcome=outcome,
        )
        if tuple(item.payload_sha256 for item in lane.stage_bindings) != (
            expected_payloads
        ):
            _fail("event lane six semantic stage payloads differ from exact outcomes")


def _collapsed_cell_state(
    states: tuple[QualificationState, ...],
) -> QualificationState:
    if not states or all(state is QualificationState.NOT_RUN for state in states):
        return QualificationState.NOT_RUN
    if QualificationState.FAIL_GRAPH_DEPENDENCE in states:
        return QualificationState.FAIL_GRAPH_DEPENDENCE
    if QualificationState.FAIL in states:
        return QualificationState.FAIL
    if all(state is QualificationState.PASS for state in states):
        return QualificationState.PASS
    return QualificationState.INSUFFICIENT


def _max_set_symmetric_difference(values: tuple[set[int], ...]) -> int:
    maximum = 0
    for index, left in enumerate(values):
        for right in values[index + 1 :]:
            maximum = max(maximum, len(left ^ right))
    return maximum


def _validate_core_summary_from_cells(
    summary: object,
    cells: tuple[object, ...],
) -> None:
    if type(summary) is not CorePrimaryUnitSummary or any(
        type(cell) is not CoreCellSummary for cell in cells
    ):
        raise TypeError("core summary reconciliation requires exact core types")
    attempted = tuple(
        cell for cell in cells if cell.attempt_status is not AttemptStatus.NOT_RUN
    )
    if (
        attempted
        and len({cell.oracle_anchor_fingerprint_sha256 for cell in attempted}) != 1
    ):
        _fail("core cells carry different oracle anchor sets")
    evaluable = tuple(
        cell for cell in cells if cell.attempt_status is AttemptStatus.EVALUABLE
    )
    candidate_sets = tuple(
        set(cell.candidate_anchor_symmetric_difference_rows) for cell in evaluable
    )
    span = _max_set_symmetric_difference(candidate_sets)
    predictions = tuple(cell.prediction_class for cell in evaluable)
    prediction_disagreement = len(set(predictions)) > 1
    if all(cell.attempt_status is AttemptStatus.NOT_RUN for cell in cells):
        expected_status = AttemptStatus.NOT_RUN
        expected_prediction = CorePredictionClass.NONE
        expected_span: int | None = None
    elif all(cell.attempt_status is AttemptStatus.EVALUABLE for cell in cells):
        expected_status = AttemptStatus.EVALUABLE
        expected_prediction = predictions[0]
        expected_span = span
    else:
        expected_status = AttemptStatus.INSUFFICIENT
        expected_prediction = CorePredictionClass.ABSTAIN
        expected_span = span
    if (
        summary.attempt_status is not expected_status
        or summary.prediction_class is not expected_prediction
        or summary.max_candidate_symmetric_difference_rows != expected_span
    ):
        _fail("core primary summary differs from its exact cell outcomes")
    base_state = _collapsed_cell_state(tuple(cell.state for cell in cells))
    drift_possible = span > 0
    allowed_states = (
        {QualificationState.FAIL_GRAPH_DEPENDENCE}
        if prediction_disagreement
        else (
            {base_state, QualificationState.FAIL_GRAPH_DEPENDENCE}
            if drift_possible
            else {base_state}
        )
    )
    if summary.state not in allowed_states:
        _fail("core primary state differs from its exact cell outcomes")
    base_reasons = {
        reason
        for cell in cells
        if cell.state is not QualificationState.PASS
        for reason in cell.reason_codes
    }
    allowed_reason_sets: set[tuple[str, ...]]
    if summary.state is not QualificationState.FAIL_GRAPH_DEPENDENCE:
        allowed_reason_sets = {tuple(sorted(base_reasons))}
    elif prediction_disagreement:
        mandatory = {
            *base_reasons,
            REASON_GRAPH_CELL_PREDICTION_DISAGREEMENT,
        }
        allowed_reason_sets = {tuple(sorted(mandatory))}
        if drift_possible:
            allowed_reason_sets.add(
                tuple(sorted({*mandatory, REASON_CORE_CANDIDATE_GRAPH_DRIFT}))
            )
    else:
        allowed_reason_sets = {
            tuple(sorted({*base_reasons, REASON_CORE_CANDIDATE_GRAPH_DRIFT}))
        }
    if summary.reason_codes not in allowed_reason_sets:
        _fail("core primary reasons differ from its exact cell outcomes")


def _role_total_span(cells: tuple[object, ...]) -> float:
    totals = tuple(
        cell.continuous_signed_total_cycles
        for cell in cells
        if cell.attempt_status is AttemptStatus.EVALUABLE
    )
    numeric = tuple(float(total) for total in totals if total is not None)
    return 0.0 if len(numeric) < 2 else max(numeric) - min(numeric)


def _validate_loop_summary_from_cells(
    summary: object,
    cells: tuple[object, ...],
) -> None:
    if type(summary) is not PrimaryUnitSummary or any(
        type(cell) is not CrossedCellSummary for cell in cells
    ):
        raise TypeError("loop summary reconciliation requires exact loop types")
    by_role = {
        role: tuple(cell for cell in cells if cell.loop_role is role)
        for role in LoopRole
    }
    if any(not role_cells for role_cells in by_role.values()):
        _fail("loop primary lacks one exact loop role")
    prediction_disagreement = any(
        len(
            {
                cell.prediction_class
                for cell in role_cells
                if cell.attempt_status is AttemptStatus.EVALUABLE
            }
        )
        > 1
        for role_cells in by_role.values()
    )
    span = max((_role_total_span(by_role[role]) for role in LoopRole), default=0.0)
    if all(cell.attempt_status is AttemptStatus.NOT_RUN for cell in cells):
        expected_status = AttemptStatus.NOT_RUN
        expected_prediction = LoopPredictionClass.NONE
        expected_span: float | None = None
    elif all(cell.attempt_status is AttemptStatus.EVALUABLE for cell in cells):
        expected_status = AttemptStatus.EVALUABLE
        boundary_predictions = tuple(
            cell.prediction_class for cell in by_role[LoopRole.PRIMARY_BOUNDARY]
        )
        expected_prediction = boundary_predictions[0]
        expected_span = span
    else:
        expected_status = AttemptStatus.INSUFFICIENT
        expected_prediction = LoopPredictionClass.ABSTAIN
        expected_span = span
    if (
        summary.attempt_status is not expected_status
        or summary.prediction_class is not expected_prediction
        or summary.continuous_total_span_cycles != expected_span
    ):
        _fail("loop primary summary differs from its exact cell outcomes")
    base_state = _collapsed_cell_state(tuple(cell.state for cell in cells))
    drift_possible = span > 0.0
    allowed_states = (
        {QualificationState.FAIL_GRAPH_DEPENDENCE}
        if prediction_disagreement
        else (
            {base_state, QualificationState.FAIL_GRAPH_DEPENDENCE}
            if drift_possible
            else {base_state}
        )
    )
    if summary.state not in allowed_states:
        _fail("loop primary state differs from its exact cell outcomes")
    base_reasons = {
        reason
        for cell in cells
        if cell.state is not QualificationState.PASS
        for reason in cell.reason_codes
    }
    if summary.state is not QualificationState.FAIL_GRAPH_DEPENDENCE:
        allowed_reason_sets = {tuple(sorted(base_reasons))}
    elif prediction_disagreement:
        mandatory = {
            *base_reasons,
            REASON_GRAPH_CELL_PREDICTION_DISAGREEMENT,
        }
        allowed_reason_sets = {tuple(sorted(mandatory))}
        if drift_possible:
            allowed_reason_sets.add(
                tuple(sorted({*mandatory, REASON_LOOP_TOTAL_GRAPH_DRIFT}))
            )
    else:
        allowed_reason_sets = {
            tuple(sorted({*base_reasons, REASON_LOOP_TOTAL_GRAPH_DRIFT}))
        }
    if summary.reason_codes not in allowed_reason_sets:
        _fail("loop primary reasons differ from its exact cell outcomes")


def _validate_primary_cell_joins(
    core_component: c.D7CoreCellOutcomesPayload,
    loop_component: c.D7LoopCellOutcomesPayload,
    primary_component: c.D7PrimaryUnitOutcomesPayload,
) -> None:
    primary_by_id = {row.primary_unit_id: row for row in primary_component.records}
    core_groups: dict[str, list[object]] = {key: [] for key in primary_by_id}
    loop_groups: dict[str, list[object]] = {key: [] for key in primary_by_id}
    for row in core_component.records:
        if row.primary_unit_id not in core_groups:
            _fail("core cell references an unknown joined primary")
        core_groups[row.primary_unit_id].append(row)
    for row in loop_component.records:
        if row.primary_unit_id not in loop_groups:
            _fail("loop cell references an unknown joined primary")
        loop_groups[row.primary_unit_id].append(row)

    slot_counts = Counter(row.seed_slot_id for row in primary_component.records)
    slot_seeds: dict[str, set[int]] = {}
    semantics = Counter(row.case_semantics for row in primary_component.records)
    for row in primary_component.records:
        slot_seeds.setdefault(row.seed_slot_id, set()).add(row.official_seed)
        core_rows = tuple(
            sorted(
                core_groups[row.primary_unit_id],
                key=lambda item: item.core_cell_id,  # type: ignore[attr-defined]
            )
        )
        loop_rows = tuple(
            sorted(
                loop_groups[row.primary_unit_id],
                key=lambda item: item.cell_id,  # type: ignore[attr-defined]
            )
        )
        if len(core_rows) != 3 or len(loop_rows) != 18:
            _fail("each joined primary requires exactly 3 core and 18 loop cells")
        if tuple(item.core_cell_id for item in core_rows) != (
            row.core_summary.core_cell_ids
        ):
            _fail("joined core summary cell IDs differ from core outcomes")
        if tuple(item.cell_id for item in loop_rows) != (
            row.loop_summary.crossed_cell_ids
        ):
            _fail("joined loop summary cell IDs differ from loop outcomes")
        if len({item.field_graph_id for item in core_rows}) != 3 or any(
            item.expected_disposition is not row.core_summary.expected_disposition
            for item in core_rows
        ):
            _fail("core cells differ from joined-primary identity")
        loop_axes = {
            (item.field_graph_id, item.cycle_graph_id, item.loop_role)
            for item in loop_rows
        }
        loop_field_ids = {item.field_graph_id for item in loop_rows}
        loop_cycle_ids = {item.cycle_graph_id for item in loop_rows}
        loop_roles = {item.loop_role for item in loop_rows}
        expected_loop_axes = {
            (field_id, cycle_id, role)
            for field_id in {item.field_graph_id for item in core_rows}
            for cycle_id in loop_cycle_ids
            for role in LoopRole
        }
        if (
            len(loop_cycle_ids) != 3
            or loop_roles != set(LoopRole)
            or loop_field_ids != {item.field_graph_id for item in core_rows}
            or loop_axes != expected_loop_axes
        ):
            _fail("loop cells do not cover exact 3A-by-3B-by-2 roles")
        for item in loop_rows:
            expected = (
                row.loop_summary.expected_disposition
                if item.loop_role is LoopRole.PRIMARY_BOUNDARY
                else (
                    LoopDisposition.PREREQUISITE_FAILURE
                    if row.loop_summary.expected_disposition
                    is LoopDisposition.PREREQUISITE_FAILURE
                    else LoopDisposition.NULL
                )
            )
            if item.expected_disposition is not expected:
                _fail("loop role disposition differs from joined primary")
        core_field = {
            item.field_graph_id: item.field_estimate_fingerprint_sha256
            for item in core_rows
        }
        core_graph = {
            item.field_graph_id: item.field_graph_fingerprint_sha256
            for item in core_rows
        }
        if any(
            core_field.get(item.field_graph_id)
            != item.field_estimate_fingerprint_sha256
            for item in loop_rows
        ):
            _fail("core and loop cells do not share each A-bound field estimate")
        if any(
            core_graph.get(item.field_graph_id) != item.field_graph_fingerprint_sha256
            for item in loop_rows
        ):
            _fail("core and loop cells do not share each A-bound field graph")
        for cycle_id in loop_cycle_ids:
            if (
                len(
                    {
                        item.cycle_graph_fingerprint_sha256
                        for item in loop_rows
                        if item.cycle_graph_id == cycle_id
                    }
                )
                != 1
            ):
                _fail("one cycle graph ID denotes multiple graph fingerprints")
        _validate_core_summary_from_cells(row.core_summary, core_rows)
        _validate_loop_summary_from_cells(row.loop_summary, loop_rows)

    if (
        len(primary_by_id) != 64
        or set(slot_counts.values()) != {32}
        or set(slot_seeds) != set(slot_counts)
        or any(len(values) != 1 for values in slot_seeds.values())
        or len({next(iter(values)) for values in slot_seeds.values()}) != 2
    ):
        _fail("joined-primary seed-slot inventory differs from two blocks of 32")
    if set(semantics) != set(_CASE_SEMANTICS) or set(semantics.values()) != {16}:
        _fail("joined-primary case inventory differs from four classes of 16")
    case_groups: dict[str, list[c.D7JoinedPrimaryUnitOutcome]] = {}
    for row in primary_component.records:
        case_groups.setdefault(row.case_id, []).append(row)
    expected_slots = set(slot_counts)

    def case_signature(
        row: c.D7JoinedPrimaryUnitOutcome,
    ) -> tuple[object, ...]:
        return (
            row.case_semantics,
            row.core_summary.control_id,
            row.core_summary.stress_assignments,
            row.core_summary.expected_disposition,
            row.loop_summary.expected_disposition,
        )

    if (
        len(case_groups) != 32
        or any(len(rows) != 2 for rows in case_groups.values())
        or any(
            {row.seed_slot_id for row in rows} != expected_slots
            for rows in case_groups.values()
        )
        or any(
            case_signature(rows[0]) != case_signature(rows[1])
            for rows in case_groups.values()
        )
    ):
        _fail("joined-primary cases must pair exactly once across both seed slots")


def _joined_qualification_state(state: ar.D7GateState) -> QualificationState:
    return {
        ar.D7GateState.PASS: QualificationState.PASS,
        ar.D7GateState.FAIL: QualificationState.FAIL,
        ar.D7GateState.INSUFFICIENT: QualificationState.INSUFFICIENT,
        ar.D7GateState.NOT_RUN: QualificationState.NOT_RUN,
    }[state]


def _derive_stratum(
    actual: object,
    units: tuple[c.D7JoinedPrimaryUnitOutcome, ...],
) -> object:
    from .contracts import StratumSummary

    stratum = actual
    statuses = tuple(unit.attempt_status for unit in units)
    states = tuple(_joined_qualification_state(unit.state) for unit in units)
    counts = {
        "attempted_count": len(units),
        "evaluable_count": statuses.count(AttemptStatus.EVALUABLE),
        "attempt_insufficient_count": statuses.count(AttemptStatus.INSUFFICIENT),
        "attempt_not_run_count": statuses.count(AttemptStatus.NOT_RUN),
        "pass_count": states.count(QualificationState.PASS),
        "fail_count": states.count(QualificationState.FAIL),
        "fail_graph_dependence_count": 0,
        "insufficient_count": states.count(QualificationState.INSUFFICIENT),
        "not_run_count": states.count(QualificationState.NOT_RUN),
    }
    rate_units = tuple(
        unit
        for unit in units
        if unit.loop_summary.expected_disposition
        in {LoopDisposition.NONZERO, LoopDisposition.NULL}
    )
    positive = tuple(
        unit
        for unit in rate_units
        if unit.loop_summary.expected_disposition is LoopDisposition.NONZERO
    )
    negative = tuple(
        unit
        for unit in rate_units
        if unit.loop_summary.expected_disposition is LoopDisposition.NULL
    )
    prerequisite = tuple(
        unit
        for unit in units
        if unit.loop_summary.expected_disposition
        is LoopDisposition.PREREQUISITE_FAILURE
    )
    if not rate_units or not positive or not negative:
        _fail("D7 stratum must retain nonempty rate, positive, and negative universes")
    rate_evaluable = sum(
        unit.attempt_status is AttemptStatus.EVALUABLE for unit in rate_units
    )
    rate_insufficient = sum(
        unit.attempt_status is AttemptStatus.INSUFFICIENT for unit in rate_units
    )
    rate_not_run = sum(
        unit.attempt_status is AttemptStatus.NOT_RUN for unit in rate_units
    )
    positive_pass = sum(
        unit.attempt_status is AttemptStatus.EVALUABLE
        and unit.loop_summary.prediction_class is LoopPredictionClass.NONZERO
        and unit.state is ar.D7GateState.PASS
        for unit in positive
    )
    negative_pass = sum(
        unit.attempt_status is AttemptStatus.EVALUABLE
        and unit.loop_summary.prediction_class is LoopPredictionClass.NULL
        and unit.state is ar.D7GateState.PASS
        for unit in negative
    )
    prerequisite_pass = sum(unit.state is ar.D7GateState.PASS for unit in prerequisite)
    coverage = rate_evaluable / len(rate_units)
    abstention = (rate_insufficient + rate_not_run) / len(rate_units)
    recall = positive_pass / len(positive)
    specificity = negative_pass / len(negative)
    all_not_run = counts["not_run_count"] == len(units)
    policy_reasons: list[str] = []
    accuracy_failed = False
    support_failed = False
    if not all_not_run:
        if coverage < 1.0:
            support_failed = True
            policy_reasons.append(REASON_COVERAGE_BELOW_MINIMUM)
        if abstention > 0.0:
            support_failed = True
            policy_reasons.append(REASON_ABSTENTION_ABOVE_MAXIMUM)
        if recall < 1.0:
            accuracy_failed = True
            policy_reasons.append(REASON_RECALL_BELOW_MINIMUM)
        if specificity < 1.0:
            accuracy_failed = True
            policy_reasons.append(REASON_SPECIFICITY_BELOW_MINIMUM)
    if all_not_run:
        state = QualificationState.NOT_RUN
    elif counts["fail_count"] or accuracy_failed:
        state = QualificationState.FAIL
    elif counts["insufficient_count"] or support_failed:
        state = QualificationState.INSUFFICIENT
    elif counts["not_run_count"]:
        state = QualificationState.NOT_RUN
    else:
        state = QualificationState.PASS
    reasons = {
        reason
        for unit in units
        if unit.state is not ar.D7GateState.PASS
        for reason in unit.reason_codes
    }
    reasons.update(policy_reasons)
    reason_codes = () if state is QualificationState.PASS else tuple(sorted(reasons))
    return StratumSummary(
        stratum_id=stratum.stratum_id,
        evaluation_unit=EvaluationUnit.PHANTOM_INSTANCE,
        required=True,
        primary_unit_ids=stratum.primary_unit_ids,
        state=state,
        rate_eligible_count=len(rate_units),
        rate_evaluable_count=rate_evaluable,
        rate_insufficient_count=rate_insufficient,
        rate_not_run_count=rate_not_run,
        positive_expected_count=len(positive),
        positive_pass_count=positive_pass,
        negative_expected_count=len(negative),
        negative_pass_count=negative_pass,
        prerequisite_expected_count=len(prerequisite),
        prerequisite_pass_count=prerequisite_pass,
        coverage=coverage,
        abstention_fraction=abstention,
        recall=recall,
        specificity=specificity,
        reason_codes=reason_codes,
        **counts,
    )


def _validate_strata(
    primary_component: c.D7PrimaryUnitOutcomesPayload,
    stratum_component: c.D7RequiredStratumOutcomesPayload,
) -> None:
    primary_by_id = {row.primary_unit_id: row for row in primary_component.records}
    membership_counts: Counter[str] = Counter()
    for stratum in stratum_component.records:
        if (
            stratum.required is not True
            or stratum.evaluation_unit is not EvaluationUnit.PHANTOM_INSTANCE
            or len(stratum.primary_unit_ids) != 32
            or not set(stratum.primary_unit_ids) <= set(primary_by_id)
            or stratum.fail_graph_dependence_count != 0
        ):
            _fail("D7 stratum differs from a required 32-primary projection")
        membership_counts.update(stratum.primary_unit_ids)
        units = tuple(primary_by_id[key] for key in stratum.primary_unit_ids)
        expected = _derive_stratum(stratum, units)
        if stratum.to_dict() != expected.to_dict():
            _fail("D7 stratum differs from joined-primary mechanical derivation")
    if (
        len(stratum_component.records) != 6
        or set(membership_counts) != set(primary_by_id)
        or set(membership_counts.values()) != {3}
    ):
        _fail("six required strata must cover every primary exactly three times")


def _validate_gate_summary(
    gate_component: c.D7AggregateGateOutcomesPayload,
    primary_component: c.D7PrimaryUnitOutcomesPayload,
    stratum_component: c.D7RequiredStratumOutcomesPayload,
    result_payload: ar.D7ScientificResultPayload,
) -> None:
    observed = result_payload.gate_summary
    expected = ar.D7GateOutcomeSummary.from_gate_states(
        gate_manifest_sha256=gate_component.gate_manifest_sha256,
        gate_states=tuple(row.state for row in gate_component.records),
        gate_results_component_sha256=gate_component.canonical_sha256,
    )
    if observed.to_dict() != expected.to_dict():
        _fail("gate summary differs from actual four-state gate component")
    structural_states = (
        *(row.state for row in primary_component.records),
        *(
            {
                QualificationState.PASS: ar.D7GateState.PASS,
                QualificationState.FAIL: ar.D7GateState.FAIL,
                QualificationState.FAIL_GRAPH_DEPENDENCE: ar.D7GateState.FAIL,
                QualificationState.INSUFFICIENT: ar.D7GateState.INSUFFICIENT,
                QualificationState.NOT_RUN: ar.D7GateState.NOT_RUN,
            }[row.state]
            for row in stratum_component.records
        ),
    )
    if (
        ar.D7GateState.FAIL in structural_states
        and observed.aggregate_state is not ar.D7ScientificResultState.FAIL
    ):
        _fail("aggregate gates are more favorable than failed structural evidence")
    if (
        ar.D7GateState.FAIL not in structural_states
        and any(
            state in {ar.D7GateState.INSUFFICIENT, ar.D7GateState.NOT_RUN}
            for state in structural_states
        )
        and observed.aggregate_state is ar.D7ScientificResultState.PASS
    ):
        _fail("aggregate gates pass despite incomplete structural evidence")


def validate_d7_result_component_bundle(
    *,
    event_ledger: c.D7ExecutionEventLedgerPayload,
    core_cells: c.D7CoreCellOutcomesPayload,
    loop_cells: c.D7LoopCellOutcomesPayload,
    primary_units: c.D7PrimaryUnitOutcomesPayload,
    required_strata: c.D7RequiredStratumOutcomesPayload,
    aggregate_gates: c.D7AggregateGateOutcomesPayload,
    result_payload: ar.D7ScientificResultPayload,
) -> None:
    """Validate one complete structural D7 component bundle.

    Success establishes canonical component bytes and their closed structural
    joins only.  It is not D7 admission, execution, persistence, publication,
    authority, or scientific evidence.
    """

    values = (
        event_ledger,
        core_cells,
        loop_cells,
        primary_units,
        required_strata,
        aggregate_gates,
    )
    if tuple(type(value) for value in values) != _EXACT_COMPONENT_TYPES:
        raise TypeError("D7 components must have the six exact payload types")
    if type(result_payload) is not ar.D7ScientificResultPayload:
        raise TypeError("result_payload must be an exact D7ScientificResultPayload")
    _validate_component_coordinates(values, result_payload)
    _validate_actual_bindings(values, result_payload)
    _validate_event_lanes(event_ledger, core_cells, loop_cells)
    _validate_primary_cell_joins(core_cells, loop_cells, primary_units)
    _validate_strata(primary_units, required_strata)
    _validate_gate_summary(
        aggregate_gates,
        primary_units,
        required_strata,
        result_payload,
    )
