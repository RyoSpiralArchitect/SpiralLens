"""Fresh, read-only post-D6 descriptive derivation for the D7 v1 successor.

The derivation accepts the exact six historical inputs permitted by the frozen
v1 materialization protocol: the historical descriptive plan followed by the
five D0--D6 scientific parents.  Each byte string is authenticated before it
is parsed and must be the pinned canonical JSON document.

This module deliberately does not read or import the predecessor item-23
result or its value-bearing derivation code.  It performs no persistence,
supplier entry, seed generation, model or subject access, official execution,
or import-time I/O.  Its only product is an in-memory v1 descriptive result
whose 27 outputs remain at the Level-0, no-claim boundary.
"""

from __future__ import annotations

from collections.abc import Mapping

from spirallens.core.canonical import canonical_json_bytes, sha256_bytes

from .common import QualificationContractError
from . import confirmation_v1_records as records
from .confirmation_v1_descriptive_common import (
    _CARTESIAN_D3_LAWS as _CARTESIAN_D3_LAWS,
    _INPUT_SPECS as _INPUT_SPECS,
    _OUTPUT_IDS as _OUTPUT_IDS,
    _REPRESENTATION_D3_CYCLE_GRAPH_IDS as _REPRESENTATION_D3_CYCLE_GRAPH_IDS,
    _REPRESENTATION_D3_FIELD_GRAPH_IDS as _REPRESENTATION_D3_FIELD_GRAPH_IDS,
    _REPRESENTATION_D3_LOOP_LAWS as _REPRESENTATION_D3_LOOP_LAWS,
    _RESULT_ID_DOMAIN as _RESULT_ID_DOMAIN,
    _RESULT_PATH as _RESULT_PATH,
    _InputSpec as _InputSpec,
    _boolean as _boolean,
    _counter_rows as _counter_rows,
    _gate_scope_output as _gate_scope_output,
    _integer as _integer,
    _load_pinned as _load_pinned,
    _mapping as _mapping,
    _nonclaim_output as _nonclaim_output,
    _number as _number,
    _output as _output,
    _parent_identity_output as _parent_identity_output,
    _sequence as _sequence,
    _string as _string,
    _validate_parent_joins as _validate_parent_joins,
    _validate_plan as _validate_plan,
)
from .confirmation_v1_descriptive_d1 import (
    _d1_outputs as _d1_outputs,
    _numeric_metric_rows as _numeric_metric_rows,
)
from .confirmation_v1_descriptive_d2 import (
    _CORE_BLIND_DESCRIPTOR_FIELDS as _CORE_BLIND_DESCRIPTOR_FIELDS,
    _CORE_BOUNDARY_IDENTITY_FIELDS as _CORE_BOUNDARY_IDENTITY_FIELDS,
    _CORE_DECLARED_OUTCOME_FIELDS as _CORE_DECLARED_OUTCOME_FIELDS,
    _collapse_core_boundary_repeats as _collapse_core_boundary_repeats,
    _core_outputs as _core_outputs,
    _d2_confounder_observation_rows as _d2_confounder_observation_rows,
)
from .confirmation_v1_descriptive_d3 import (
    _cartesian_d3_row as _cartesian_d3_row,
    _d3_family_aggregates as _d3_family_aggregates,
    _d3_outputs as _d3_outputs,
    _metamorphic_rows as _metamorphic_rows,
    _representation_d3_row as _representation_d3_row,
)
from .confirmation_v1_descriptive_d4 import (
    _crossed_summary as _crossed_summary,
    _d4_cell_row as _d4_cell_row,
    _d4_descriptor as _d4_descriptor,
    _d4_index as _d4_index,
    _d4_index_inputs as _d4_index_inputs,
    _d4_optional_number as _d4_optional_number,
    _d4_outputs as _d4_outputs,
    _d4_pair_class as _d4_pair_class,
    _d4_stress_assignments as _d4_stress_assignments,
    _d4_string_fields as _d4_string_fields,
    _d4_string_list as _d4_string_list,
    _d4_unit_fields as _d4_unit_fields,
)
from .confirmation_v1_descriptive_d5_inputs import (
    _PERSISTED_STRATUM_KEYS as _PERSISTED_STRATUM_KEYS,
    _d5_crossed_inputs as _d5_crossed_inputs,
    _persisted_stratum_rows as _persisted_stratum_rows,
    _prerequisite_member_rows as _prerequisite_member_rows,
    _role_primary_units as _role_primary_units,
    _stress_graph_rows as _stress_graph_rows,
    _stress_stratum_ids as _stress_stratum_ids,
)
from .confirmation_v1_descriptive_d5_outputs import (
    _abstention_evidence_rows as _abstention_evidence_rows,
    _d5_outputs as _d5_outputs,
    _nonvacuity_evidence_rows as _nonvacuity_evidence_rows,
    _typed_failure_routes as _typed_failure_routes,
)
from .confirmation_v1_descriptive_independence import (
    _independence_outputs as _independence_outputs,
)

__all__: tuple[str, ...] = ()


def _derive_outputs(
    plan: Mapping[str, object],
    protocol: Mapping[str, object],
    result: Mapping[str, object],
    manifest: Mapping[str, object],
    consumption: Mapping[str, object],
    d6_decision: Mapping[str, object],
) -> tuple[records.D7V1DescriptiveOutput, ...]:
    documents = (plan, protocol, result, manifest, consumption, d6_decision)
    metamorphic_rows = _metamorphic_rows(result)
    outputs = [
        _parent_identity_output(documents),
        _gate_scope_output(result, d6_decision),
        _nonclaim_output(plan, result, d6_decision),
        *_d1_outputs(result),
        *_core_outputs(result),
        *_d3_outputs(result),
        *_d4_outputs(result),
        *_d5_outputs(protocol, result, metamorphic_rows, d6_decision),
        *_independence_outputs(
            plan,
            protocol,
            result,
            manifest,
            consumption,
            d6_decision,
        ),
    ]
    by_id = {output.output_id: output for output in outputs}
    if len(outputs) != len(_OUTPUT_IDS) or tuple(by_id) != _OUTPUT_IDS:
        raise QualificationContractError(
            "fresh derivation did not produce exact 27 outputs"
        )
    return tuple(outputs)


def _require_result_parent_join(
    parent_attempt: records.D7V1OfficialExecutionAttemptReservation,
    chronology_receipt: records.D7V1PreItem23ChronologyReceipt,
) -> None:
    receipt_payload = _mapping(
        chronology_receipt.to_dict().get("payload"), label="chronology receipt payload"
    )
    predecessor_files = _mapping(
        receipt_payload.get("predecessor_files"), label="predecessor files"
    )
    attempt_file = _mapping(
        predecessor_files.get(parent_attempt.artifact_role),
        label="attempt predecessor file",
    )
    observed = records.D7V1ArtifactBinding.from_dict(
        attempt_file.get("artifact_binding")
    )
    expected = records.D7V1ArtifactBinding.from_record(parent_attempt)
    if observed != expected:
        raise QualificationContractError(
            "chronology receipt does not bind the supplied attempt reservation"
        )
    absence = _mapping(
        receipt_payload.get("descriptive_result_namespace_absence"),
        label="descriptive result namespace absence",
    )
    if (
        absence.get("repository_path") != _RESULT_PATH
        or absence.get("path_absent") is not True
    ):
        raise QualificationContractError(
            "chronology receipt does not bind the v1 result namespace absence"
        )


def _derive_d7_v1_post_d6_descriptive_result(
    *,
    historical_plan_source: bytes,
    parent_protocol_source: bytes,
    parent_result_source: bytes,
    parent_manifest_source: bytes,
    parent_consumption_source: bytes,
    parent_d6_decision_source: bytes,
    parent_attempt: records.D7V1OfficialExecutionAttemptReservation,
    chronology_receipt: records.D7V1PreItem23ChronologyReceipt,
) -> records.D7V1PostselectionDescriptiveResult:
    """Derive the exact v1 27-output descriptive result without persistence."""

    if not isinstance(parent_attempt, records.D7V1OfficialExecutionAttemptReservation):
        raise TypeError(
            "parent_attempt must be a D7V1OfficialExecutionAttemptReservation"
        )
    if not isinstance(chronology_receipt, records.D7V1PreItem23ChronologyReceipt):
        raise TypeError("chronology_receipt must be a D7V1PreItem23ChronologyReceipt")

    sources = (
        historical_plan_source,
        parent_protocol_source,
        parent_result_source,
        parent_manifest_source,
        parent_consumption_source,
        parent_d6_decision_source,
    )
    documents = tuple(
        _load_pinned(source, spec)
        for source, spec in zip(sources, _INPUT_SPECS, strict=True)
    )
    plan, protocol, result, manifest, consumption, d6_decision = documents
    _validate_plan(plan, protocol)
    _validate_parent_joins(
        plan,
        protocol,
        result,
        manifest,
        consumption,
        d6_decision,
    )
    _require_result_parent_join(parent_attempt, chronology_receipt)

    outputs = _derive_outputs(
        plan,
        protocol,
        result,
        manifest,
        consumption,
        d6_decision,
    )
    read_trace = tuple(
        records.D7V1ReadTraceEntry(sequence=sequence, artifact_binding=spec.binding())
        for sequence, spec in enumerate(_INPUT_SPECS, start=1)
    )
    identity = {
        "domain": _RESULT_ID_DOMAIN,
        "parent_attempt_sha256": parent_attempt.canonical_sha256,
        "chronology_receipt_sha256": chronology_receipt.canonical_sha256,
        "read_binding_sha256": [spec.canonical_sha256 for spec in _INPUT_SPECS],
        "output_sha256": [output.canonical_sha256 for output in outputs],
    }
    record_id = (
        f"d7-v1-post-d6-descriptive-{sha256_bytes(canonical_json_bytes(identity))[:24]}"
    )
    descriptive_result = records.D7V1PostselectionDescriptiveResult.create(
        record_id=record_id,
        repository_path=_RESULT_PATH,
        parent_binding=records.D7V1ArtifactBinding.from_record(parent_attempt),
        chronology_receipt_binding=records.D7V1ArtifactBinding.from_record(
            chronology_receipt
        ),
        read_trace=read_trace,
        status="insufficient",
        outputs=outputs,
    )
    return records.D7V1PostselectionDescriptiveResult.from_canonical_bytes(
        descriptive_result.canonical_bytes,
        expected_sha256=descriptive_result.canonical_sha256,
    )


def _verify_d7_v1_post_d6_descriptive_result(
    candidate: records.D7V1PostselectionDescriptiveResult,
    *,
    historical_plan_source: bytes,
    parent_protocol_source: bytes,
    parent_result_source: bytes,
    parent_manifest_source: bytes,
    parent_consumption_source: bytes,
    parent_d6_decision_source: bytes,
    parent_attempt: records.D7V1OfficialExecutionAttemptReservation,
    chronology_receipt: records.D7V1PreItem23ChronologyReceipt,
) -> records.D7V1PostselectionDescriptiveResult:
    """Require a candidate to equal the fresh six-input derivation byte-for-byte."""

    if not isinstance(candidate, records.D7V1PostselectionDescriptiveResult):
        raise TypeError("candidate must be a D7V1PostselectionDescriptiveResult")
    expected = _derive_d7_v1_post_d6_descriptive_result(
        historical_plan_source=historical_plan_source,
        parent_protocol_source=parent_protocol_source,
        parent_result_source=parent_result_source,
        parent_manifest_source=parent_manifest_source,
        parent_consumption_source=parent_consumption_source,
        parent_d6_decision_source=parent_d6_decision_source,
        parent_attempt=parent_attempt,
        chronology_receipt=chronology_receipt,
    )
    if candidate.canonical_bytes != expected.canonical_bytes:
        raise QualificationContractError(
            "candidate descriptive result differs from the fresh six-input derivation"
        )
    return candidate
