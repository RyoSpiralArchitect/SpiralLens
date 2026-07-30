from __future__ import annotations

import hashlib
from dataclasses import dataclass, replace

import pytest

from spirallens.qualification import confirmation_attempt_records as ar
from spirallens.qualification import confirmation_result_component_validation as v
from spirallens.qualification import confirmation_result_components as c
from spirallens.qualification.common import (
    AttemptStatus,
    CoreDisposition,
    CorePredictionClass,
    EvaluationUnit,
    LoopDisposition,
    LoopPredictionClass,
    QualificationContractError,
    QualificationState,
)
from spirallens.qualification.contracts import (
    CoreCellSummary,
    CorePrimaryUnitSummary,
    CrossedCellSummary,
    PrimaryUnitSummary,
    StratumSummary,
)
from spirallens.qualification.protocol import LoopRole, StressAssignment


def _h(label: str) -> str:
    return hashlib.sha256(label.encode()).hexdigest()


_TARGET = _h("target")
_INVENTORY = _h("inventory")
_AGGREGATION = _h("aggregation")
_GATE_MANIFEST = _h("gate-manifest")
_COMMON = {
    "replay_target_sha256": _TARGET,
    "full_inventory_sha256": _INVENTORY,
    "aggregation_sha256": _AGGREGATION,
}
_CASE_ROWS = (
    (
        CoreDisposition.LOCALIZED_CORE,
        LoopDisposition.NONZERO,
        "localized-core|nonzero",
    ),
    (
        CoreDisposition.LOCALIZED_CORE,
        LoopDisposition.NULL,
        "localized-core|null",
    ),
    (
        CoreDisposition.NO_CORE,
        LoopDisposition.NULL,
        "no-core|null",
    ),
    (
        CoreDisposition.PREREQUISITE_FAILURE,
        LoopDisposition.PREREQUISITE_FAILURE,
        "prerequisite-failure|prerequisite-failure",
    ),
)


@dataclass(frozen=True)
class _Bundle:
    event: c.D7ExecutionEventLedgerPayload
    core: c.D7CoreCellOutcomesPayload
    loop: c.D7LoopCellOutcomesPayload
    primary: c.D7PrimaryUnitOutcomesPayload
    strata: c.D7RequiredStratumOutcomesPayload
    gates: c.D7AggregateGateOutcomesPayload
    result: ar.D7ScientificResultPayload


def _stress(index: int) -> tuple[StressAssignment, ...]:
    block = index // 4
    return (
        StressAssignment("axis-a", "high" if block & 1 else "low"),
        StressAssignment("axis-b", "high" if block & 2 else "low"),
        StressAssignment("axis-c", "high" if block & 4 else "low"),
    )


def _primary_rows() -> tuple[
    tuple[CoreCellSummary, ...],
    tuple[CrossedCellSummary, ...],
    tuple[c.D7JoinedPrimaryUnitOutcome, ...],
]:
    core_rows: list[CoreCellSummary] = []
    loop_rows: list[CrossedCellSummary] = []
    primary_rows: list[c.D7JoinedPrimaryUnitOutcome] = []
    for index in range(64):
        primary_id = f"d7-unit-{index:02d}"
        case_index = index % 32
        semantic_index = case_index % 4
        core_disposition, loop_disposition, semantics = _CASE_ROWS[semantic_index]
        core_ids = tuple(
            f"core-{primary_id}-a-{graph_index}" for graph_index in range(3)
        )
        loop_ids = tuple(
            sorted(
                f"loop-{primary_id}-a-{a_index}-b-{b_index}-{role.value}"
                for a_index in range(3)
                for b_index in range(3)
                for role in LoopRole
            )
        )
        for graph_index, core_id in enumerate(core_ids):
            core_rows.append(
                CoreCellSummary(
                    core_cell_id=core_id,
                    primary_unit_id=primary_id,
                    field_graph_id=f"a-{graph_index}",
                    expected_disposition=core_disposition,
                    field_graph_fingerprint_sha256=None,
                    field_estimate_fingerprint_sha256=None,
                    blind_input_fingerprint_sha256=None,
                    prediction_fingerprint_sha256=None,
                    oracle_fingerprint_sha256=None,
                    candidate_fingerprint_sha256=None,
                    oracle_anchor_fingerprint_sha256=None,
                    candidate_anchor_symmetric_difference_rows=(),
                    attempt_status=AttemptStatus.NOT_RUN,
                    prediction_class=CorePredictionClass.NONE,
                    state=QualificationState.NOT_RUN,
                    reason_codes=("not-run",),
                )
            )
        for loop_id in loop_ids:
            parts = loop_id.split("-")
            a_index = int(parts[5])
            b_index = int(parts[7])
            role = (
                LoopRole.OFFCORE_CONTROL
                if loop_id.endswith(LoopRole.OFFCORE_CONTROL.value)
                else LoopRole.PRIMARY_BOUNDARY
            )
            expected = (
                loop_disposition
                if role is LoopRole.PRIMARY_BOUNDARY
                else (
                    LoopDisposition.PREREQUISITE_FAILURE
                    if loop_disposition is LoopDisposition.PREREQUISITE_FAILURE
                    else LoopDisposition.NULL
                )
            )
            loop_rows.append(
                CrossedCellSummary(
                    cell_id=loop_id,
                    primary_unit_id=primary_id,
                    field_graph_id=f"a-{a_index}",
                    cycle_graph_id=f"b-{b_index}",
                    loop_role=role,
                    expected_disposition=expected,
                    field_graph_fingerprint_sha256=None,
                    cycle_graph_fingerprint_sha256=None,
                    field_estimate_fingerprint_sha256=None,
                    cycle_binding_fingerprint_sha256=None,
                    representative_content_sha256=None,
                    blind_input_fingerprint_sha256=None,
                    prediction_fingerprint_sha256=None,
                    oracle_fingerprint_sha256=None,
                    attempt_status=AttemptStatus.NOT_RUN,
                    prediction_class=LoopPredictionClass.NONE,
                    state=QualificationState.NOT_RUN,
                    continuous_signed_total_cycles=None,
                    oracle_absolute_error_cycles=None,
                    reason_codes=("not-run",),
                )
            )
        seed_slot_id = (
            "confirmation-seed-slot-00" if index < 32 else "confirmation-seed-slot-01"
        )
        official_seed = 101 if index < 32 else 202
        core_summary = CorePrimaryUnitSummary(
            primary_unit_id=primary_id,
            selection_seed=official_seed,
            control_id=f"control-{semantic_index}",
            expected_disposition=core_disposition,
            stress_assignments=_stress(index),
            d2_scientific_input_fingerprint_sha256=None,
            domain_instance_fingerprint_sha256=None,
            support_instance_fingerprint_sha256=None,
            attempt_status=AttemptStatus.NOT_RUN,
            prediction_class=CorePredictionClass.NONE,
            state=QualificationState.NOT_RUN,
            max_candidate_symmetric_difference_rows=None,
            reason_codes=("not-run",),
            core_cell_ids=core_ids,
        )
        loop_summary = PrimaryUnitSummary(
            primary_unit_id=primary_id,
            selection_seed=official_seed,
            control_id=f"control-{semantic_index}",
            expected_disposition=loop_disposition,
            stress_assignments=_stress(index),
            domain_instance_fingerprint_sha256=None,
            support_instance_fingerprint_sha256=None,
            attempt_status=AttemptStatus.NOT_RUN,
            prediction_class=LoopPredictionClass.NONE,
            state=QualificationState.NOT_RUN,
            continuous_total_span_cycles=None,
            reason_codes=("not-run",),
            crossed_cell_ids=loop_ids,
        )
        primary_rows.append(
            c.D7JoinedPrimaryUnitOutcome(
                primary_unit_id=primary_id,
                seed_slot_id=seed_slot_id,
                official_seed=official_seed,
                case_id=f"spectral-case-{case_index:02d}",
                case_semantics=semantics,
                core_summary=core_summary,
                loop_summary=loop_summary,
                attempt_status=AttemptStatus.NOT_RUN,
                state=ar.D7GateState.NOT_RUN,
                reason_codes=("not-run",),
            )
        )
    return (
        tuple(sorted(core_rows, key=lambda item: item.core_cell_id)),
        tuple(sorted(loop_rows, key=lambda item: item.cell_id)),
        tuple(sorted(primary_rows, key=lambda item: item.primary_unit_id)),
    )


def _event_lane(
    lane_id: str,
    *,
    kind: c.D7ExecutionLaneKind,
    cell_id: str,
    outcome: CoreCellSummary | CrossedCellSummary,
) -> c.D7ExecutionEventLaneOutcome:
    payloads = v._d7_event_stage_payload_sha256s(
        replay_target_sha256=_TARGET,
        full_inventory_sha256=_INVENTORY,
        aggregation_sha256=_AGGREGATION,
        lane_id=lane_id,
        lane_kind=kind,
        cell_id=cell_id,
        outcome=outcome,
    )
    values: list[c.D7ExecutionEventStageBinding] = []
    previous = "0" * 64
    for stage, payload in zip(c.D7ExecutionStage, payloads, strict=True):
        item = c.D7ExecutionEventStageBinding(stage, payload, previous)
        values.append(item)
        previous = item.binding_sha256
    return c.D7ExecutionEventLaneOutcome(
        lane_id=lane_id,
        lane_kind=kind,
        cell_id=cell_id,
        stage_bindings=tuple(values),
    )


def _strata(
    primary: tuple[c.D7JoinedPrimaryUnitOutcome, ...],
) -> tuple[StratumSummary, ...]:
    result: list[StratumSummary] = []
    for axis_index, axis in enumerate(("axis-a", "axis-b", "axis-c")):
        for level in ("high", "low"):
            members = tuple(
                row.primary_unit_id
                for row in primary
                if row.core_summary.stress_assignments[axis_index].level == level
            )
            result.append(
                StratumSummary(
                    stratum_id=f"stress.{axis}.{level}",
                    evaluation_unit=EvaluationUnit.PHANTOM_INSTANCE,
                    required=True,
                    primary_unit_ids=members,
                    state=QualificationState.NOT_RUN,
                    attempted_count=32,
                    evaluable_count=0,
                    attempt_insufficient_count=0,
                    attempt_not_run_count=32,
                    pass_count=0,
                    fail_count=0,
                    fail_graph_dependence_count=0,
                    insufficient_count=0,
                    not_run_count=32,
                    rate_eligible_count=24,
                    rate_evaluable_count=0,
                    rate_insufficient_count=0,
                    rate_not_run_count=24,
                    positive_expected_count=8,
                    positive_pass_count=0,
                    negative_expected_count=16,
                    negative_pass_count=0,
                    prerequisite_expected_count=8,
                    prerequisite_pass_count=0,
                    coverage=0.0,
                    abstention_fraction=1.0,
                    recall=0.0,
                    specificity=0.0,
                    reason_codes=("not-run",),
                )
            )
    return tuple(sorted(result, key=lambda item: item.stratum_id))


def _binding(
    component: c.D7ResultComponentPayload,
) -> ar.D7ResultComponentBinding:
    return ar.D7ResultComponentBinding(
        component_id=component.component_id,
        component_contract_id=component.component_contract_id,
        component_canonical_sha256=component.canonical_sha256,
        byte_count=len(component.canonical_bytes),
        record_count=len(component.records),
    )


def _result(
    components: tuple[c.D7ResultComponentPayload, ...],
    *,
    gate_states: tuple[ar.D7GateState, ...] | None = None,
) -> ar.D7ScientificResultPayload:
    gate_component = components[-1]
    assert type(gate_component) is c.D7AggregateGateOutcomesPayload
    states = (
        tuple(row.state for row in gate_component.records)
        if gate_states is None
        else gate_states
    )
    summary = ar.D7GateOutcomeSummary.from_gate_states(
        gate_manifest_sha256=gate_component.gate_manifest_sha256,
        gate_states=states,
        gate_results_component_sha256=gate_component.canonical_sha256,
    )
    return ar.D7ScientificResultPayload(
        replay_target_sha256=_TARGET,
        full_inventory_sha256=_INVENTORY,
        aggregation_sha256=_AGGREGATION,
        state=summary.aggregate_state,
        reason_codes=(
            ()
            if summary.aggregate_state is ar.D7ScientificResultState.PASS
            else ("gate-nonpass",)
        ),
        gate_summary=summary,
        component_bindings=tuple(_binding(component) for component in components),
    )


@pytest.fixture(scope="module")
def bundle() -> _Bundle:
    core_rows, loop_rows, primary_rows = _primary_rows()
    core = c.D7CoreCellOutcomesPayload(records=core_rows, **_COMMON)
    loop = c.D7LoopCellOutcomesPayload(records=loop_rows, **_COMMON)
    lanes = tuple(
        sorted(
            (
                *(
                    _event_lane(
                        f"core.{row.core_cell_id}",
                        kind=c.D7ExecutionLaneKind.CORE,
                        cell_id=row.core_cell_id,
                        outcome=row,
                    )
                    for row in core_rows
                ),
                *(
                    _event_lane(
                        f"loop.{row.cell_id}",
                        kind=c.D7ExecutionLaneKind.LOOP,
                        cell_id=row.cell_id,
                        outcome=row,
                    )
                    for row in loop_rows
                ),
            ),
            key=lambda item: item.lane_id,
        )
    )
    event = c.D7ExecutionEventLedgerPayload(records=lanes, **_COMMON)
    primary = c.D7PrimaryUnitOutcomesPayload(records=primary_rows, **_COMMON)
    strata = c.D7RequiredStratumOutcomesPayload(
        records=_strata(primary_rows), **_COMMON
    )
    gates = c.D7AggregateGateOutcomesPayload(
        gate_manifest_sha256=_GATE_MANIFEST,
        records=(
            c.D7AggregateGateOutcome(
                gate_id="d7-confirmation",
                gate_definition_sha256=_h("gate-definition"),
                state=ar.D7GateState.NOT_RUN,
                reason_codes=("not-run",),
                evidence_sha256=_h("gate-evidence"),
            ),
        ),
        **_COMMON,
    )
    components: tuple[c.D7ResultComponentPayload, ...] = (
        event,
        core,
        loop,
        primary,
        strata,
        gates,
    )
    return _Bundle(event, core, loop, primary, strata, gates, _result(components))


def _validate(bundle: _Bundle) -> None:
    v.validate_d7_result_component_bundle(
        event_ledger=bundle.event,
        core_cells=bundle.core,
        loop_cells=bundle.loop,
        primary_units=bundle.primary,
        required_strata=bundle.strata,
        aggregate_gates=bundle.gates,
        result_payload=bundle.result,
    )


def _replace_components(
    bundle: _Bundle,
    *,
    event: c.D7ExecutionEventLedgerPayload | None = None,
    core: c.D7CoreCellOutcomesPayload | None = None,
    loop: c.D7LoopCellOutcomesPayload | None = None,
    primary: c.D7PrimaryUnitOutcomesPayload | None = None,
    strata: c.D7RequiredStratumOutcomesPayload | None = None,
    gates: c.D7AggregateGateOutcomesPayload | None = None,
) -> _Bundle:
    values = (
        bundle.event if event is None else event,
        bundle.core if core is None else core,
        bundle.loop if loop is None else loop,
        bundle.primary if primary is None else primary,
        bundle.strata if strata is None else strata,
        bundle.gates if gates is None else gates,
    )
    return _Bundle(*values, _result(values))


def _rederive_strata(
    strata: c.D7RequiredStratumOutcomesPayload,
    primary: c.D7PrimaryUnitOutcomesPayload,
) -> c.D7RequiredStratumOutcomesPayload:
    primary_by_id = {row.primary_unit_id: row for row in primary.records}
    return replace(
        strata,
        records=tuple(
            v._derive_stratum(
                row,
                tuple(primary_by_id[key] for key in row.primary_unit_ids),
            )
            for row in strata.records
        ),
    )


def test_complete_d7_component_bundle_round_trips_and_validates(
    bundle: _Bundle,
) -> None:
    _validate(bundle)
    for component in (
        bundle.event,
        bundle.core,
        bundle.loop,
        bundle.primary,
        bundle.strata,
        bundle.gates,
    ):
        restored = type(component).from_canonical_bytes(
            component.canonical_bytes,
            expected_sha256=component.canonical_sha256,
        )
        assert restored.canonical_bytes == component.canonical_bytes
        assert restored.component_root_sha256 == component.component_root_sha256
        assert component.schema_version != component.component_contract_id
        assert (
            component.component_contract_id
            == ar.D7_RESULT_COMPONENT_CONTRACT_IDS[component.component_id]
        )
        with pytest.raises(QualificationContractError, match="SHA-256 differs"):
            type(component).from_canonical_bytes(
                component.canonical_bytes,
                expected_sha256=_h("wrong-component-digest"),
            )
        noncanonical = b" " + component.canonical_bytes
        with pytest.raises(QualificationContractError):
            type(component).from_canonical_bytes(
                noncanonical,
                expected_sha256=hashlib.sha256(noncanonical).hexdigest(),
            )
    assert len(bundle.event.records) == 1344
    assert len(bundle.core.records) == 192
    assert len(bundle.loop.records) == 1152
    assert len(bundle.primary.records) == 64
    assert len(bundle.strata.records) == 6
    assert c.__all__ == ()
    assert v.__all__ == ()


def test_component_roots_bind_attempt_independent_coordinates(bundle: _Bundle) -> None:
    for component in (
        bundle.event,
        bundle.core,
        bundle.loop,
        bundle.primary,
        bundle.strata,
        bundle.gates,
    ):
        document = component.to_dict()
        assert document["attempt_independent"] is True
        assert document["replay_target_sha256"] == _TARGET
        assert document["full_inventory_sha256"] == _INVENTORY
        assert document["aggregation_sha256"] == _AGGREGATION
        assert (
            document["result_schema_sha256"]
            == ar.D7_SCIENTIFIC_RESULT_IMPLEMENTATION_SCHEMA_SHA256
        )
        assert not {
            "attempt_key_sha256",
            "execution_start_sha256",
            "output_namespace_identity_sha256",
            "terminal_path_identity_sha256",
        } & set(document)


def test_d0_d5_relabel_and_bool_int_laundering_are_rejected(
    bundle: _Bundle,
) -> None:
    relabelled = bundle.event.to_dict()
    relabelled["schema_version"] = bundle.core.schema_version
    relabelled["component_id"] = bundle.core.component_id.value
    relabelled["component_contract_id"] = bundle.core.component_contract_id
    with pytest.raises(QualificationContractError):
        c.D7CoreCellOutcomesPayload.from_dict(relabelled)

    invalid_count = bundle.core.to_dict()
    invalid_count["record_count"] = True
    with pytest.raises(QualificationContractError, match="plain integer"):
        c.D7CoreCellOutcomesPayload.from_dict(invalid_count)

    joined = bundle.primary.records[0].to_dict()
    joined["official_seed"] = True
    with pytest.raises(QualificationContractError, match="plain integer"):
        c.D7JoinedPrimaryUnitOutcome.from_dict(joined)


def test_reused_rows_must_be_canonically_self_reconstructing(bundle: _Bundle) -> None:
    row = next(
        item
        for item in bundle.loop.records
        if item.expected_disposition in {LoopDisposition.NONZERO, LoopDisposition.NULL}
    )
    prediction = (
        LoopPredictionClass.NONZERO
        if row.expected_disposition is LoopDisposition.NONZERO
        else LoopPredictionClass.NULL
    )
    integer_float_row = replace(
        row,
        field_graph_fingerprint_sha256=_h("field-graph"),
        cycle_graph_fingerprint_sha256=_h("cycle-graph"),
        field_estimate_fingerprint_sha256=_h("field-estimate"),
        cycle_binding_fingerprint_sha256=_h("cycle-binding"),
        representative_content_sha256=_h("representative"),
        blind_input_fingerprint_sha256=_h("blind"),
        prediction_fingerprint_sha256=_h("prediction"),
        oracle_fingerprint_sha256=_h("oracle"),
        attempt_status=AttemptStatus.EVALUABLE,
        prediction_class=prediction,
        state=QualificationState.PASS,
        continuous_signed_total_cycles=0,
        oracle_absolute_error_cycles=0,
        reason_codes=(),
    )
    records = tuple(
        integer_float_row if item.cell_id == row.cell_id else item
        for item in bundle.loop.records
    )
    with pytest.raises(QualificationContractError, match="self-reconstructing"):
        c.D7LoopCellOutcomesPayload(records=records, **_COMMON)


def test_subclasses_and_noncanonical_record_order_are_rejected(
    bundle: _Bundle,
) -> None:
    class GateSubclass(c.D7AggregateGateOutcome):
        pass

    gate = bundle.gates.records[0]
    with pytest.raises(TypeError, match="subclasses"):
        GateSubclass(
            gate.gate_id,
            gate.gate_definition_sha256,
            gate.state,
            gate.reason_codes,
            gate.evidence_sha256,
        )
    with pytest.raises(QualificationContractError, match="canonical"):
        c.D7CoreCellOutcomesPayload(
            records=tuple(reversed(bundle.core.records)),
            **_COMMON,
        )


def test_event_all_stages_must_bind_actual_cell_outcome(bundle: _Bundle) -> None:
    lane = bundle.event.records[0]
    stages = list(lane.stage_bindings)
    stages[-1] = c.D7ExecutionEventStageBinding(
        stages[-1].stage,
        _h("wrong-result-outcome"),
        stages[-1].previous_stage_binding_sha256,
    )
    changed_lane = replace(lane, stage_bindings=tuple(stages))
    changed_event = replace(
        bundle.event,
        records=(changed_lane, *bundle.event.records[1:]),
    )
    changed = _replace_components(bundle, event=changed_event)
    with pytest.raises(QualificationContractError, match="six semantic stage"):
        _validate(changed)

    payloads = [item.payload_sha256 for item in lane.stage_bindings]
    payloads[1] = _h("wrong-early-stage")
    rebuilt: list[c.D7ExecutionEventStageBinding] = []
    previous = "0" * 64
    for stage, payload in zip(c.D7ExecutionStage, payloads, strict=True):
        item = c.D7ExecutionEventStageBinding(stage, payload, previous)
        rebuilt.append(item)
        previous = item.binding_sha256
    changed_lane = replace(lane, stage_bindings=tuple(rebuilt))
    changed_event = replace(
        bundle.event,
        records=(changed_lane, *bundle.event.records[1:]),
    )
    changed = _replace_components(bundle, event=changed_event)
    with pytest.raises(QualificationContractError, match="six semantic stage"):
        _validate(changed)


def test_joined_primary_must_bind_exact_cell_inventory(bundle: _Bundle) -> None:
    first = bundle.primary.records[0]
    second = bundle.primary.records[1]
    changed_core = replace(
        first.core_summary,
        core_cell_ids=second.core_summary.core_cell_ids,
    )
    changed_primary_row = replace(first, core_summary=changed_core)
    changed_primary = replace(
        bundle.primary,
        records=(changed_primary_row, *bundle.primary.records[1:]),
    )
    changed = _replace_components(bundle, primary=changed_primary)
    with pytest.raises(QualificationContractError, match="cell IDs"):
        _validate(changed)


def test_joined_primary_summary_must_be_derived_from_cells(bundle: _Bundle) -> None:
    template = bundle.primary.records[0]
    core = CorePrimaryUnitSummary(
        primary_unit_id=template.primary_unit_id,
        selection_seed=template.official_seed,
        control_id=template.core_summary.control_id,
        expected_disposition=template.core_summary.expected_disposition,
        stress_assignments=template.core_summary.stress_assignments,
        d2_scientific_input_fingerprint_sha256=_h("fabricated-scientific-input"),
        domain_instance_fingerprint_sha256=_h("fabricated-domain"),
        support_instance_fingerprint_sha256=_h("fabricated-support"),
        attempt_status=AttemptStatus.EVALUABLE,
        prediction_class=CorePredictionClass.LOCALIZED_CORE,
        state=QualificationState.PASS,
        max_candidate_symmetric_difference_rows=0,
        reason_codes=(),
        core_cell_ids=template.core_summary.core_cell_ids,
    )
    loop = PrimaryUnitSummary(
        primary_unit_id=template.primary_unit_id,
        selection_seed=template.official_seed,
        control_id=template.loop_summary.control_id,
        expected_disposition=template.loop_summary.expected_disposition,
        stress_assignments=template.loop_summary.stress_assignments,
        domain_instance_fingerprint_sha256=_h("fabricated-domain"),
        support_instance_fingerprint_sha256=_h("fabricated-support"),
        attempt_status=AttemptStatus.EVALUABLE,
        prediction_class=LoopPredictionClass.NONZERO,
        state=QualificationState.PASS,
        continuous_total_span_cycles=0.0,
        reason_codes=(),
        crossed_cell_ids=template.loop_summary.crossed_cell_ids,
    )
    fabricated = replace(
        template,
        core_summary=core,
        loop_summary=loop,
        attempt_status=AttemptStatus.EVALUABLE,
        state=ar.D7GateState.PASS,
        reason_codes=(),
    )
    primary = replace(
        bundle.primary,
        records=(fabricated, *bundle.primary.records[1:]),
    )
    strata = _rederive_strata(bundle.strata, primary)
    changed = _replace_components(bundle, primary=primary, strata=strata)
    with pytest.raises(QualificationContractError, match="summary differs"):
        _validate(changed)


def test_threshold_opaque_reconciliation_accepts_disagreement_without_drift_reason(
    bundle: _Bundle,
) -> None:
    template = bundle.primary.records[0].core_summary
    source_cells = tuple(
        row
        for row in bundle.core.records
        if row.primary_unit_id == template.primary_unit_id
    )
    cells = tuple(
        replace(
            row,
            field_graph_fingerprint_sha256=_h(f"field-graph-{index}"),
            field_estimate_fingerprint_sha256=_h(f"field-estimate-{index}"),
            blind_input_fingerprint_sha256=_h(f"blind-{index}"),
            prediction_fingerprint_sha256=_h(f"prediction-{index}"),
            oracle_fingerprint_sha256=_h(f"oracle-{index}"),
            candidate_fingerprint_sha256=_h(f"candidate-{index}"),
            oracle_anchor_fingerprint_sha256=_h("shared-oracle-anchor"),
            candidate_anchor_symmetric_difference_rows=((1,) if index == 1 else ()),
            attempt_status=AttemptStatus.EVALUABLE,
            prediction_class=(
                CorePredictionClass.NO_CORE
                if index == 1
                else CorePredictionClass.LOCALIZED_CORE
            ),
            state=(QualificationState.FAIL if index == 1 else QualificationState.PASS),
            reason_codes=(("wrong-core",) if index == 1 else ()),
        )
        for index, row in enumerate(source_cells)
    )
    summary = replace(
        template,
        d2_scientific_input_fingerprint_sha256=_h("scientific-input"),
        domain_instance_fingerprint_sha256=_h("domain"),
        support_instance_fingerprint_sha256=_h("support"),
        attempt_status=AttemptStatus.EVALUABLE,
        prediction_class=CorePredictionClass.LOCALIZED_CORE,
        state=QualificationState.FAIL_GRAPH_DEPENDENCE,
        max_candidate_symmetric_difference_rows=1,
        reason_codes=("graph_cell_prediction_disagreement", "wrong-core"),
    )
    v._validate_core_summary_from_cells(summary, cells)


def test_loop_cells_require_exact_cartesian_axes(bundle: _Bundle) -> None:
    template = bundle.primary.records[0]
    old_ids = set(template.loop_summary.crossed_cell_ids)
    old_rows = tuple(row for row in bundle.loop.records if row.cell_id in old_ids)
    replacement_rows = tuple(
        replace(
            row,
            cell_id=f"loop-{template.primary_unit_id}-forged-{index:02d}",
            field_graph_id="a-0",
            cycle_graph_id=f"forged-b-{index:02d}",
            loop_role=LoopRole.PRIMARY_BOUNDARY,
            expected_disposition=template.loop_summary.expected_disposition,
        )
        for index, row in enumerate(old_rows)
    )
    loop = replace(
        bundle.loop,
        records=tuple(
            sorted(
                (
                    *(row for row in bundle.loop.records if row.cell_id not in old_ids),
                    *replacement_rows,
                ),
                key=lambda row: row.cell_id,
            )
        ),
    )
    primary_row = replace(
        template,
        loop_summary=replace(
            template.loop_summary,
            crossed_cell_ids=tuple(sorted(row.cell_id for row in replacement_rows)),
        ),
    )
    primary = replace(
        bundle.primary,
        records=(primary_row, *bundle.primary.records[1:]),
    )
    with pytest.raises(QualificationContractError, match="3A-by-3B-by-2"):
        v._validate_primary_cell_joins(bundle.core, loop, primary)


def test_graph_ids_have_functional_fingerprints_within_primary(
    bundle: _Bundle,
) -> None:
    template = bundle.primary.records[0]
    core_ids = set(template.core_summary.core_cell_ids)
    loop_ids = set(template.loop_summary.crossed_cell_ids)
    core_rows = []
    for row in bundle.core.records:
        if row.core_cell_id not in core_ids:
            core_rows.append(row)
            continue
        core_rows.append(
            replace(
                row,
                field_graph_fingerprint_sha256=_h(f"field-graph-{row.field_graph_id}"),
                field_estimate_fingerprint_sha256=_h(
                    f"field-estimate-{row.field_graph_id}"
                ),
                blind_input_fingerprint_sha256=_h(f"blind-{row.core_cell_id}"),
                prediction_fingerprint_sha256=_h(f"prediction-{row.core_cell_id}"),
                oracle_fingerprint_sha256=_h(f"oracle-{row.core_cell_id}"),
                candidate_fingerprint_sha256=_h(f"candidate-{row.core_cell_id}"),
                oracle_anchor_fingerprint_sha256=_h("shared-anchor"),
                attempt_status=AttemptStatus.INSUFFICIENT,
                prediction_class=CorePredictionClass.ABSTAIN,
                state=QualificationState.INSUFFICIENT,
                reason_codes=("insufficient",),
            )
        )
    loop_rows = []
    changed_one = False
    for row in bundle.loop.records:
        if row.cell_id not in loop_ids:
            loop_rows.append(row)
            continue
        field_graph = _h(f"field-graph-{row.field_graph_id}")
        if not changed_one and row.field_graph_id == "a-0":
            field_graph = _h("inconsistent-field-graph")
            changed_one = True
        loop_rows.append(
            replace(
                row,
                field_graph_fingerprint_sha256=field_graph,
                cycle_graph_fingerprint_sha256=_h(f"cycle-graph-{row.cycle_graph_id}"),
                field_estimate_fingerprint_sha256=_h(
                    f"field-estimate-{row.field_graph_id}"
                ),
                cycle_binding_fingerprint_sha256=_h(f"cycle-binding-{row.cell_id}"),
                representative_content_sha256=_h(f"representative-{row.cell_id}"),
                blind_input_fingerprint_sha256=_h(f"blind-{row.cell_id}"),
                prediction_fingerprint_sha256=_h(f"prediction-{row.cell_id}"),
                oracle_fingerprint_sha256=_h(f"oracle-{row.cell_id}"),
                attempt_status=AttemptStatus.INSUFFICIENT,
                prediction_class=LoopPredictionClass.ABSTAIN,
                state=QualificationState.INSUFFICIENT,
                reason_codes=("insufficient",),
            )
        )
    core = c.D7CoreCellOutcomesPayload(
        records=tuple(sorted(core_rows, key=lambda row: row.core_cell_id)),
        **_COMMON,
    )
    loop = c.D7LoopCellOutcomesPayload(
        records=tuple(sorted(loop_rows, key=lambda row: row.cell_id)),
        **_COMMON,
    )
    with pytest.raises(QualificationContractError, match="field graph"):
        v._validate_primary_cell_joins(core, loop, bundle.primary)


def test_case_inventory_pairs_once_across_seed_slots(bundle: _Bundle) -> None:
    first, second, *rest = bundle.primary.records
    changed_first = replace(first, case_id=second.case_id)
    primary = replace(bundle.primary, records=(changed_first, second, *rest))
    with pytest.raises(QualificationContractError, match="pair exactly once"):
        v._validate_primary_cell_joins(bundle.core, bundle.loop, primary)
    mate = next(
        row
        for row in bundle.primary.records
        if row.case_id == first.case_id and row.seed_slot_id != first.seed_slot_id
    )
    changed_mate = replace(
        mate,
        core_summary=replace(mate.core_summary, control_id="forged-control"),
        loop_summary=replace(mate.loop_summary, control_id="forged-control"),
    )
    paired_records = tuple(
        changed_mate if row.primary_unit_id == mate.primary_unit_id else row
        for row in bundle.primary.records
    )
    paired = replace(bundle.primary, records=paired_records)
    with pytest.raises(QualificationContractError, match="pair exactly once"):
        v._validate_primary_cell_joins(bundle.core, bundle.loop, paired)


def test_strata_must_cover_every_primary_exactly_three_times(bundle: _Bundle) -> None:
    first = bundle.strata.records[0]
    replacement_id = next(
        row.primary_unit_id
        for row in bundle.primary.records
        if row.primary_unit_id not in first.primary_unit_ids
    )
    changed_ids = tuple(sorted((*first.primary_unit_ids[1:], replacement_id)))
    changed_row = replace(first, primary_unit_ids=changed_ids)
    changed_strata = replace(
        bundle.strata,
        records=tuple(
            sorted(
                (changed_row, *bundle.strata.records[1:]),
                key=lambda item: item.stratum_id,
            )
        ),
    )
    changed = _replace_components(bundle, strata=changed_strata)
    with pytest.raises(QualificationContractError):
        _validate(changed)


def test_gate_summary_is_derived_from_actual_four_state_rows(bundle: _Bundle) -> None:
    components: tuple[c.D7ResultComponentPayload, ...] = (
        bundle.event,
        bundle.core,
        bundle.loop,
        bundle.primary,
        bundle.strata,
        bundle.gates,
    )
    wrong_result = _result(components, gate_states=(ar.D7GateState.FAIL,))
    changed = replace(bundle, result=wrong_result)
    with pytest.raises(QualificationContractError, match="gate summary"):
        _validate(changed)

    gate_document = bundle.gates.records[0].to_dict()
    gate_document["state"] = "fail_graph_dependence"
    with pytest.raises(QualificationContractError, match="not supported"):
        c.D7AggregateGateOutcome.from_dict(gate_document)
    pass_gate = replace(
        bundle.gates.records[0],
        state=ar.D7GateState.PASS,
        reason_codes=(),
    )
    pass_gates = replace(bundle.gates, records=(pass_gate,))
    pass_result = _replace_components(bundle, gates=pass_gates)
    with pytest.raises(QualificationContractError, match="incomplete structural"):
        _validate(pass_result)


def test_core_failure_cannot_project_to_joined_pass(bundle: _Bundle) -> None:
    template = bundle.primary.records[0]
    core = CorePrimaryUnitSummary(
        primary_unit_id=template.primary_unit_id,
        selection_seed=template.official_seed,
        control_id=template.core_summary.control_id,
        expected_disposition=template.core_summary.expected_disposition,
        stress_assignments=template.core_summary.stress_assignments,
        d2_scientific_input_fingerprint_sha256=_h("scientific-input"),
        domain_instance_fingerprint_sha256=_h("domain"),
        support_instance_fingerprint_sha256=_h("support"),
        attempt_status=AttemptStatus.EVALUABLE,
        prediction_class=CorePredictionClass.LOCALIZED_CORE,
        state=QualificationState.FAIL,
        max_candidate_symmetric_difference_rows=0,
        reason_codes=("core-failed",),
        core_cell_ids=template.core_summary.core_cell_ids,
    )
    loop = PrimaryUnitSummary(
        primary_unit_id=template.primary_unit_id,
        selection_seed=template.official_seed,
        control_id=template.loop_summary.control_id,
        expected_disposition=template.loop_summary.expected_disposition,
        stress_assignments=template.loop_summary.stress_assignments,
        domain_instance_fingerprint_sha256=_h("domain"),
        support_instance_fingerprint_sha256=_h("support"),
        attempt_status=AttemptStatus.EVALUABLE,
        prediction_class=LoopPredictionClass.NONZERO,
        state=QualificationState.PASS,
        continuous_total_span_cycles=0.0,
        reason_codes=(),
        crossed_cell_ids=template.loop_summary.crossed_cell_ids,
    )
    with pytest.raises(QualificationContractError, match="four-state projection"):
        c.D7JoinedPrimaryUnitOutcome(
            primary_unit_id=template.primary_unit_id,
            seed_slot_id=template.seed_slot_id,
            official_seed=template.official_seed,
            case_id=template.case_id,
            case_semantics=template.case_semantics,
            core_summary=core,
            loop_summary=loop,
            attempt_status=AttemptStatus.EVALUABLE,
            state=ar.D7GateState.PASS,
            reason_codes=(),
        )
