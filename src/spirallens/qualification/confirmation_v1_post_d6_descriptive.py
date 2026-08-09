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

from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
import math

from spirallens.core.canonical import (
    CanonicalJsonError,
    canonical_json_bytes,
    parse_canonical_json,
    sha256_bytes,
)

from .common import QualificationContractError
from . import confirmation_v1_records as records

__all__: tuple[str, ...] = ()


_RESULT_PATH = (
    "experiments/qualification/d7_spectral_moment_confirmation_v1/"
    "post-d6-descriptive-analysis-result.json"
)
_RESULT_ID_DOMAIN = "spirallens.d7-v1-post-d6-descriptive-result-id.v0.1"


@dataclass(frozen=True, slots=True)
class _InputSpec:
    role: str
    artifact_contract_id: str
    repository_path: str
    source_commit: str
    canonical_sha256: str
    byte_count: int

    def binding(self) -> records.D7V1ArtifactBinding:
        return records.D7V1ArtifactBinding(
            artifact_role=self.role,
            artifact_contract_id=self.artifact_contract_id,
            canonical_sha256=self.canonical_sha256,
            byte_count=self.byte_count,
        )


_INPUT_SPECS = (
    _InputSpec(
        role="historical-post-d6-plan",
        artifact_contract_id="spirallens.postselection-descriptive-analysis-plan.v0.1",
        repository_path="protocols/post_d6_descriptive_analysis_v0_1.json",
        source_commit="4838cef49997a70f1d6281b8097905510e7ec351",
        canonical_sha256=(
            "9b1a8d9c3857fd18fff7b4dfb20a75eade2f56f4933e05126830669cd8ccb981"
        ),
        byte_count=10_735,
    ),
    _InputSpec(
        role="parent-protocol",
        artifact_contract_id="spirallens.qualification-protocol.v0.8",
        repository_path="protocols/d0_d5_f2_cartesian_selection_v0_1.json",
        source_commit="22eb9bd6bcd447f9a9afde0a7c26b8a1aef42993",
        canonical_sha256=(
            "9908bb83bb5ff5642416aa09d9e468e0a9499185cec9305e69a54143f2578bd1"
        ),
        byte_count=969_147,
    ),
    _InputSpec(
        role="parent-result",
        artifact_contract_id="spirallens.qualification-result.v0.10",
        repository_path=(
            "experiments/qualification/d0_d5_f2_cartesian_selection_v0_1/"
            "attempt/f63dcc162a896d0957cb7a8d437eace87eeadfc2574921819e7f98a27a704d58"
            ".selection-terminal/terminal-artifact.json"
        ),
        source_commit="22eb9bd6bcd447f9a9afde0a7c26b8a1aef42993",
        canonical_sha256=(
            "44749d8d237b8b35874099c605f8de3d76130691ce8beb92e1ccf80fa368c13a"
        ),
        byte_count=20_269_314,
    ),
    _InputSpec(
        role="parent-manifest",
        artifact_contract_id="spirallens.selection-terminal-manifest.v0.1",
        repository_path=(
            "experiments/qualification/d0_d5_f2_cartesian_selection_v0_1/"
            "attempt/f63dcc162a896d0957cb7a8d437eace87eeadfc2574921819e7f98a27a704d58"
            ".selection-terminal/terminal-manifest.json"
        ),
        source_commit="22eb9bd6bcd447f9a9afde0a7c26b8a1aef42993",
        canonical_sha256=(
            "518b66d715cf9bd05e12de62cb5681ec63ec7f978fd4d2538ba3c2594deed4b1"
        ),
        byte_count=690,
    ),
    _InputSpec(
        role="parent-consumption",
        artifact_contract_id="spirallens.selection-consumption.v0.2",
        repository_path=(
            "experiments/qualification/d0_d5_f2_cartesian_selection_v0_1/"
            "attempt/f63dcc162a896d0957cb7a8d437eace87eeadfc2574921819e7f98a27a704d58"
            ".selection-terminal/selection-consumption.json"
        ),
        source_commit="22eb9bd6bcd447f9a9afde0a7c26b8a1aef42993",
        canonical_sha256=(
            "a42ae9cffb6a2c87de6ed645e0982e85b09046a4ed5ad3f815a8a8ce38c0cadb"
        ),
        byte_count=1_342,
    ),
    _InputSpec(
        role="parent-d6-decision",
        artifact_contract_id="spirallens.surrogate-advancement-decision.v0.1",
        repository_path=(
            "experiments/qualification/d0_d5_f2_cartesian_selection_v0_1/"
            "d6-surrogate-advancement-decision.json"
        ),
        source_commit="f869d53d890ae35b43c3dbca2ce6363c78fea367",
        canonical_sha256=(
            "c1c3fbbb9a06e8df120755dcf159e015636d96993bd6ec3a6792312618587a07"
        ),
        byte_count=6_835,
    ),
)

_OUTPUT_IDS = (
    "parent-identity-table",
    "gate-scope-table",
    "non-claim-table",
    "signed-margin-by-analytic-check",
    "fragility-without-threshold-change",
    "core-no-core-abstain-matrix",
    "boundary-repeat-exact-agreement",
    "amplitude-identifiability-support-separation",
    "ambient-basis-error",
    "reference-o2-error",
    "loop-reversal-signed-total-error",
    "array-versus-observable-law-separation",
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

_REFERENCE_O2_OBLIGATION_IDS = (
    "local-frame-gauge",
    "reference-orientation",
    "reference-reflection",
    "reference-rotation",
    "spin-two-double-angle",
)


def _mapping(value: object, *, label: str) -> dict[str, object]:
    if type(value) is not dict or any(type(key) is not str for key in value):
        raise QualificationContractError(f"{label} must be a JSON object")
    return value


def _sequence(value: object, *, label: str) -> list[object]:
    if type(value) is not list:
        raise QualificationContractError(f"{label} must be a JSON array")
    return value


def _string(value: object, *, label: str) -> str:
    if type(value) is not str or not value or value != value.strip():
        raise QualificationContractError(f"{label} must be a non-empty string")
    return value


def _integer(value: object, *, label: str) -> int:
    if type(value) is not int:
        raise QualificationContractError(f"{label} must be an integer")
    return value


def _number(value: object, *, label: str) -> float:
    if type(value) not in {int, float} or not math.isfinite(float(value)):
        raise QualificationContractError(f"{label} must be a finite number")
    return float(value)


def _boolean(value: object, *, label: str) -> bool:
    if type(value) is not bool:
        raise QualificationContractError(f"{label} must be boolean")
    return value


def _load_pinned(source: bytes, spec: _InputSpec) -> dict[str, object]:
    if type(source) is not bytes or len(source) != spec.byte_count:
        raise QualificationContractError(f"{spec.role} byte count differs before parse")
    if sha256_bytes(source) != spec.canonical_sha256:
        raise QualificationContractError(f"{spec.role} digest differs before parse")
    try:
        value = parse_canonical_json(source, label=spec.role)
        if canonical_json_bytes(value) != source:
            raise QualificationContractError(
                f"{spec.role} canonical round-trip differs"
            )
    except CanonicalJsonError as error:
        raise QualificationContractError(str(error)) from error
    document = _mapping(value, label=spec.role)
    if document.get("schema_version") != spec.artifact_contract_id:
        raise QualificationContractError(f"{spec.role} schema differs")
    return document


def _validate_plan(
    plan: Mapping[str, object],
    protocol: Mapping[str, object],
) -> None:
    if plan.get("status") != "frozen_not_run":
        raise QualificationContractError("historical plan must remain frozen_not_run")
    policy = _mapping(plan.get("input_policy"), label="plan input_policy")
    allowed_paths = tuple(
        _string(item, label="allowed input path")
        for item in _sequence(
            policy.get("allowed_input_paths"), label="allowed input paths"
        )
    )
    if allowed_paths != tuple(spec.repository_path for spec in _INPUT_SPECS[1:]):
        raise QualificationContractError("historical plan allowed inputs differ")
    work_packages = _sequence(plan.get("work_packages"), label="work packages")
    planned_outputs: list[str] = []
    for expected_sequence, item in enumerate(work_packages, start=1):
        package = _mapping(item, label="work package")
        if package.get("sequence") != expected_sequence or package.get("status") != (
            "planned"
        ):
            raise QualificationContractError("historical work package state differs")
        planned_outputs.extend(
            _string(output_id, label="planned output id")
            for output_id in _sequence(
                package.get("required_outputs"), label="required outputs"
            )
        )
    if tuple(planned_outputs) != _OUTPUT_IDS:
        raise QualificationContractError("historical plan output set differs")
    if protocol.get("protocol_id") != "d0-d5-f2-cartesian-selection-v0-1":
        raise QualificationContractError("parent protocol id differs")


def _validate_parent_joins(
    plan: Mapping[str, object],
    protocol: Mapping[str, object],
    result: Mapping[str, object],
    manifest: Mapping[str, object],
    consumption: Mapping[str, object],
    d6_decision: Mapping[str, object],
) -> None:
    parent = _mapping(plan.get("parent_evidence"), label="plan parent_evidence")
    joins = (
        (parent.get("protocol_canonical_sha256"), _INPUT_SPECS[1].canonical_sha256),
        (parent.get("terminal_result_sha256"), _INPUT_SPECS[2].canonical_sha256),
        (parent.get("terminal_manifest_sha256"), _INPUT_SPECS[3].canonical_sha256),
        (parent.get("terminal_consumption_sha256"), _INPUT_SPECS[4].canonical_sha256),
        (parent.get("d6_decision_sha256"), _INPUT_SPECS[5].canonical_sha256),
        (result.get("protocol_canonical_sha256"), _INPUT_SPECS[1].canonical_sha256),
        (result.get("protocol_source_sha256"), _INPUT_SPECS[1].canonical_sha256),
        (manifest.get("terminal_artifact_sha256"), _INPUT_SPECS[2].canonical_sha256),
        (manifest.get("consumption_sha256"), _INPUT_SPECS[4].canonical_sha256),
        (consumption.get("terminal_artifact_sha256"), _INPUT_SPECS[2].canonical_sha256),
        (
            consumption.get("protocol_canonical_sha256"),
            _INPUT_SPECS[1].canonical_sha256,
        ),
    )
    if any(observed != expected for observed, expected in joins):
        raise QualificationContractError("six-input historical identity join differs")
    terminal = _mapping(
        d6_decision.get("selection_terminal"), label="D6 selection terminal"
    )
    d6_joins = (
        (terminal.get("result_sha256"), _INPUT_SPECS[2].canonical_sha256),
        (terminal.get("terminal_manifest_sha256"), _INPUT_SPECS[3].canonical_sha256),
        (terminal.get("consumption_sha256"), _INPUT_SPECS[4].canonical_sha256),
        (terminal.get("protocol_canonical_sha256"), _INPUT_SPECS[1].canonical_sha256),
    )
    if any(observed != expected for observed, expected in d6_joins):
        raise QualificationContractError("D6 parent join differs")
    if protocol.get("protocol_id") != result.get("protocol_id") or result.get(
        "protocol_id"
    ) != consumption.get("protocol_id"):
        raise QualificationContractError("parent protocol identifiers differ")


def _output(
    output_id: str,
    data: Mapping[str, object],
    *,
    status: str = "available",
) -> records.D7V1DescriptiveOutput:
    return records.D7V1DescriptiveOutput.create(
        output_id=output_id,
        status=status,
        data=data,
    )


def _counter_rows(
    items: Iterable[Mapping[str, object]],
    fields: Sequence[str],
) -> list[dict[str, object]]:
    counter: Counter[tuple[object, ...]] = Counter()
    for item in items:
        key: list[object] = []
        for field in fields:
            value = item.get(field)
            if type(value) not in {str, int, bool}:
                raise QualificationContractError(
                    f"counter field {field} has a non-scalar value"
                )
            key.append(value)
        counter[tuple(key)] += 1
    rows: list[dict[str, object]] = []
    for key, count in sorted(counter.items(), key=lambda item: repr(item[0])):
        row = {field: value for field, value in zip(fields, key, strict=True)}
        row["count"] = count
        rows.append(row)
    return rows


def _parent_identity_output(
    documents: Sequence[Mapping[str, object]],
) -> records.D7V1DescriptiveOutput:
    rows = []
    for sequence, (spec, document) in enumerate(
        zip(_INPUT_SPECS, documents, strict=True), start=1
    ):
        rows.append(
            {
                "sequence": sequence,
                "artifact_role": spec.role,
                "artifact_contract_id": spec.artifact_contract_id,
                "repository_path": spec.repository_path,
                "source_commit": spec.source_commit,
                "canonical_sha256": spec.canonical_sha256,
                "byte_count": spec.byte_count,
                "observed_schema_version": document["schema_version"],
            }
        )
    return _output(
        "parent-identity-table",
        {
            "rows": rows,
            "read_binding_count": len(rows),
            "digest_before_parse": True,
            "canonical_round_trip_verified": True,
            "cross_parent_join_verified": True,
        },
    )


def _gate_scope_output(
    result: Mapping[str, object],
    d6_decision: Mapping[str, object],
) -> records.D7V1DescriptiveOutput:
    rows = []
    for item in _sequence(result.get("gate_results"), label="gate results"):
        gate = _mapping(item, label="gate result")
        rows.append(
            {
                key: gate[key]
                for key in (
                    "gate_id",
                    "state",
                    "claim_scope",
                    "evaluation_unit",
                    "attempted_count",
                    "evaluable_count",
                    "attempt_insufficient_count",
                    "pass_count",
                    "fail_count",
                    "insufficient_count",
                    "not_run_count",
                )
            }
        )
    later = []
    for gate_id in ("d6", "d7", "d8"):
        gate = _mapping(d6_decision.get(gate_id), label=f"{gate_id} decision")
        later.append(
            {
                "gate_id": gate_id,
                "state": gate["state"],
                "scope": gate.get("scope"),
                "reason_codes": list(gate.get("reason_codes", [])),
            }
        )
    return _output(
        "gate-scope-table",
        {
            "d0_d5_rows": rows,
            "d6_d8_rows": later,
            "official_gate_reclassification_performed": False,
        },
    )


def _nonclaim_output(
    plan: Mapping[str, object],
    result: Mapping[str, object],
    d6_decision: Mapping[str, object],
) -> records.D7V1DescriptiveOutput:
    boundary = _mapping(plan.get("claim_boundary"), label="plan claim boundary")
    authority = _mapping(d6_decision.get("authority"), label="D6 authority")
    result_nonclaims = {
        key: result[key]
        for key in (
            "d6_d8_advanced",
            "hidden_confirmation_accessed",
            "integer_claimed",
            "localized_core_loop_join_established",
            "p0_winner_selected",
            "pythia_accessed",
            "representation_d2_d5_qualified",
            "semantic_labels_accessed",
            "subject_accessed",
            "synthetic_qualified",
        )
    }
    false_values = (
        [
            value
            for key, value in boundary.items()
            if key not in {"claim_ceiling", "claim_delta"}
        ]
        + list(authority.values())
        + list(result_nonclaims.values())
    )
    if any(value is not False for value in false_values):
        raise QualificationContractError("historical non-claim boundary differs")
    return _output(
        "non-claim-table",
        {
            "claim_ceiling": boundary["claim_ceiling"],
            "claim_delta": boundary["claim_delta"],
            "plan_boundary": dict(boundary),
            "d6_authority": dict(authority),
            "parent_result_nonclaims": result_nonclaims,
            "all_authority_flags_false": True,
        },
    )


def _numeric_metric_rows(result: Mapping[str, object]) -> list[dict[str, object]]:
    bundle = _mapping(result.get("evidence_bundle"), label="evidence bundle")
    runtime = _sequence(
        bundle.get("static_runtime_receipts"), label="static runtime receipts"
    )
    rows: list[dict[str, object]] = []
    for family_item in runtime:
        family = _mapping(family_item, label="static runtime receipt")
        if "cases" not in family:
            continue
        evidence_id = _string(family.get("evidence_id"), label="evidence_id")
        for case_item in _sequence(family.get("cases"), label="D1 cases"):
            case = _mapping(case_item, label="D1 case")
            case_id = _string(case.get("case_id"), label="case_id")
            for metric_item in _sequence(
                case.get("numeric_metric_receipts"), label="numeric metrics"
            ):
                metric = _mapping(metric_item, label="numeric metric")
                comparator = _string(metric.get("comparator"), label="comparator")
                observed = _number(metric.get("observed_value"), label="observed_value")
                threshold = _number(metric.get("threshold"), label="threshold")
                if comparator == "at-most":
                    margin = threshold - observed
                elif comparator == "at-least":
                    margin = observed - threshold
                elif comparator == "exact-zero":
                    difference = abs(observed - threshold)
                    margin = 0.0 if difference == 0.0 else -difference
                else:
                    raise QualificationContractError("D1 comparator is not closed")
                passed = _boolean(metric.get("passed"), label="metric passed")
                if passed is not (margin >= 0.0):
                    raise QualificationContractError(
                        "D1 persisted pass flag differs from its signed margin"
                    )
                rows.append(
                    {
                        "evidence_id": evidence_id,
                        "case_id": case_id,
                        "graph_family": metric["graph_family"],
                        "metric_id": metric["metric_id"],
                        "comparator": comparator,
                        "observed_value": observed,
                        "threshold": threshold,
                        "signed_margin": margin,
                        "passed": passed,
                    }
                )
    rows.sort(
        key=lambda row: (
            str(row["evidence_id"]),
            str(row["case_id"]),
            str(row["graph_family"]),
            str(row["metric_id"]),
        )
    )
    if not rows:
        raise QualificationContractError("D1 metric rows are absent")
    return rows


def _d1_outputs(result: Mapping[str, object]) -> list[records.D7V1DescriptiveOutput]:
    rows = _numeric_metric_rows(result)
    grouped: dict[tuple[str, str], list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        grouped[(str(row["evidence_id"]), str(row["metric_id"]))].append(row)
    fragility_rows = []
    for (evidence_id, metric_id), members in sorted(grouped.items()):
        margins = [float(member["signed_margin"]) for member in members]
        thresholds = sorted({float(member["threshold"]) for member in members})
        fragility_rows.append(
            {
                "evidence_id": evidence_id,
                "metric_id": metric_id,
                "observation_count": len(members),
                "minimum_signed_margin": min(margins),
                "maximum_signed_margin": max(margins),
                "zero_margin_count": sum(value == 0.0 for value in margins),
                "negative_margin_count": sum(value < 0.0 for value in margins),
                "thresholds_observed": thresholds,
            }
        )
    return [
        _output(
            "signed-margin-by-analytic-check",
            {
                "rows": rows,
                "row_count": len(rows),
                "thresholds_modified": False,
                "descriptive_only": True,
            },
        ),
        _output(
            "fragility-without-threshold-change",
            {
                "rows": fragility_rows,
                "thresholds_modified": False,
                "gate_reclassified": False,
                "minimum_observed_signed_margin": min(
                    float(row["signed_margin"]) for row in rows
                ),
            },
        ),
    ]


_CORE_BOUNDARY_AGREEMENT_FIELDS = (
    "d2_scientific_input_fingerprint_sha256",
    "max_candidate_symmetric_difference_rows",
    "attempt_status",
    "expected_disposition",
    "prediction_class",
    "state",
    "reason_codes",
)


def _collapse_core_boundary_repeats(
    primary_units: Sequence[Mapping[str, object]],
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    repeat_groups: dict[tuple[object, ...], list[dict[str, object]]] = defaultdict(list)
    for unit in primary_units:
        assignments = {
            _string(item["axis_id"], label="stress axis id"): _string(
                item["level"], label="stress level"
            )
            for item in (
                _mapping(value, label="stress assignment")
                for value in _sequence(
                    unit.get("stress_assignments"), label="stress assignments"
                )
            )
        }
        key = (
            unit["selection_seed"],
            unit["control_id"],
            assignments["state-geometry-warp"],
            assignments["structured-observation-perturbation"],
        )
        projected = {
            "selection_seed": unit["selection_seed"],
            "control_id": unit["control_id"],
            "state_geometry_warp": assignments["state-geometry-warp"],
            "structured_observation_perturbation": assignments[
                "structured-observation-perturbation"
            ],
            "boundary_level": assignments["boundary"],
            "d2_scientific_input_fingerprint_sha256": unit[
                "d2_scientific_input_fingerprint_sha256"
            ],
            "max_candidate_symmetric_difference_rows": unit[
                "max_candidate_symmetric_difference_rows"
            ],
            "attempt_status": unit["attempt_status"],
            "expected_disposition": unit["expected_disposition"],
            "prediction_class": unit["prediction_class"],
            "state": unit["state"],
            "reason_codes": list(unit["reason_codes"]),
        }
        repeat_groups[key].append(projected)
    collapsed_units = []
    repeat_rows = []
    for key, members in sorted(repeat_groups.items(), key=lambda item: repr(item[0])):
        boundary_levels = sorted(str(member["boundary_level"]) for member in members)
        agreement = boundary_levels == ["central", "wide"] and all(
            canonical_json_bytes({"value": member[field]})
            == canonical_json_bytes({"value": members[0][field]})
            for field in _CORE_BOUNDARY_AGREEMENT_FIELDS
            for member in members[1:]
        )
        if not agreement:
            raise QualificationContractError(
                "D2 boundary repeats cannot be collapsed without exact agreement"
            )
        collapsed_units.append(
            {
                "control_id": members[0]["control_id"],
                "expected_disposition": members[0]["expected_disposition"],
                "prediction_class": members[0]["prediction_class"],
                "attempt_status": members[0]["attempt_status"],
                "state": members[0]["state"],
            }
        )
        repeat_rows.append(
            {
                "selection_seed": key[0],
                "control_id": key[1],
                "state_geometry_warp": key[2],
                "structured_observation_perturbation": key[3],
                "boundary_levels": boundary_levels,
                "repeat_count": len(members),
                "exact_agreement": agreement,
            }
        )
    return collapsed_units, repeat_rows


def _core_outputs(result: Mapping[str, object]) -> list[records.D7V1DescriptiveOutput]:
    primary_units = [
        _mapping(item, label="core primary unit")
        for item in _sequence(
            result.get("core_primary_units"), label="core primary units"
        )
    ]
    collapsed_units, repeat_rows = _collapse_core_boundary_repeats(primary_units)
    matrix = _counter_rows(
        collapsed_units,
        (
            "control_id",
            "expected_disposition",
            "prediction_class",
            "attempt_status",
            "state",
        ),
    )

    bundle = _mapping(result.get("evidence_bundle"), label="evidence bundle")
    core_receipts = [
        _mapping(item, label="core cell receipt")
        for item in _sequence(
            bundle.get("core_cell_receipts"), label="core cell receipts"
        )
    ]
    scalar_fields = ("amplitude", "identifiability_score", "support_counts")
    descriptor_only_count = 0
    for receipt in core_receipts:
        blind = _mapping(receipt.get("blind_input_receipt"), label="blind core input")
        if all(
            set(_mapping(blind.get(field), label=field)) == {"dtype", "shape", "sha256"}
            for field in scalar_fields
        ):
            descriptor_only_count += 1
    blocked = descriptor_only_count == len(core_receipts) and bool(core_receipts)
    if not blocked:
        raise QualificationContractError(
            "main D2 scalar persistence boundary unexpectedly changed"
        )

    return [
        _output(
            "core-no-core-abstain-matrix",
            {
                "rows": matrix,
                "evaluation_unit": "d2-scientific-input-unit",
                "source_boundary_repeat_row_count": len(primary_units),
                "unit_count": len(collapsed_units),
                "boundary_repeat_collapsed": True,
                "graph_cells_are_repeated_measures": True,
            },
        ),
        _output(
            "boundary-repeat-exact-agreement",
            {
                "rows": repeat_rows,
                "paired_unit_count": len(repeat_rows),
                "exact_agreement_count": sum(
                    row["exact_agreement"] is True for row in repeat_rows
                ),
                "all_pairs_exact": all(
                    row["exact_agreement"] is True for row in repeat_rows
                ),
                "agreement_scope_fields": list(_CORE_BOUNDARY_AGREEMENT_FIELDS),
                "graph_cell_payload_byte_equality_claimed": False,
                "boundary_repeats_are_not_independent_samples": True,
            },
        ),
        _output(
            "amplitude-identifiability-support-separation",
            {
                "blocked_reason": (
                    "historical-main-d2-amplitude-identifiability-support-values-"
                    "not-persisted"
                ),
                "required_scalar_fields": list(scalar_fields),
                "main_core_cell_receipt_count": len(core_receipts),
                "descriptor_only_receipt_count": descriptor_only_count,
                "persisted_representation": "dtype-shape-sha256-only",
                "rerun_authorized": False,
                "partial_or_confounder_values_may_not_cure_main_d2_absence": True,
            },
            status="blocked",
        ),
    ]


def _metamorphic_rows(result: Mapping[str, object]) -> list[dict[str, object]]:
    bundle = _mapping(result.get("evidence_bundle"), label="evidence bundle")
    rows: list[dict[str, object]] = []
    for item in _sequence(
        bundle.get("static_runtime_receipts"), label="static runtime receipts"
    ):
        family = _mapping(item, label="static runtime receipt")
        if "obligation_receipts" not in family:
            continue
        evidence_id = _string(family.get("evidence_id"), label="evidence_id")
        for obligation_item in _sequence(
            family.get("obligation_receipts"), label="obligation receipts"
        ):
            obligation = _mapping(obligation_item, label="obligation receipt")
            receipt = _mapping(obligation.get("receipt"), label="metamorphic receipt")
            component_errors = {
                field: (
                    _number(receipt[field], label=field)
                    if receipt.get(field) is not None
                    else None
                )
                for field in (
                    "maximum_distance_error",
                    "maximum_field_law_error",
                    "maximum_loop_law_error",
                )
            }
            if receipt.get("observed_error") is not None:
                observed_error = _number(
                    receipt["observed_error"], label="metamorphic observed_error"
                )
            else:
                present_errors = [
                    value for value in component_errors.values() if value is not None
                ]
                if not present_errors:
                    raise QualificationContractError(
                        "metamorphic receipt has no numeric error"
                    )
                observed_error = max(present_errors)
            rows.append(
                {
                    "evidence_id": evidence_id,
                    "obligation_id": obligation["obligation_id"],
                    "law": receipt["law"],
                    "state": receipt["state"],
                    "observed_error": observed_error,
                    **component_errors,
                    "tolerance": _number(
                        receipt["tolerance"], label="metamorphic tolerance"
                    ),
                    "composition_verified": receipt["composition_verified"],
                    "inverse_verified": receipt["inverse_verified"],
                    "nonidentity_verified": receipt["nonidentity_verified"],
                    "integer_output_present": receipt["integer_output_present"],
                    "topology_claimed": receipt["topology_claimed"],
                }
            )
    rows.sort(key=lambda row: (str(row["evidence_id"]), str(row["obligation_id"])))
    if not rows:
        raise QualificationContractError("D3 metamorphic receipts are absent")
    return rows


def _d3_outputs(
    rows: Sequence[Mapping[str, object]],
) -> list[records.D7V1DescriptiveOutput]:

    def select(*ids: str, prefix: str | None = None) -> list[dict[str, object]]:
        selected = []
        for row in rows:
            obligation_id = str(row["obligation_id"])
            if obligation_id in ids or (
                prefix is not None and obligation_id.startswith(prefix)
            ):
                selected.append(dict(row))
        if not selected:
            raise QualificationContractError("required D3 law rows are absent")
        return selected

    ambient = select("ambient-signed-permutation")
    reference = select(*_REFERENCE_O2_OBLIGATION_IDS)
    reversal = select("loop-reversal")
    classified = []
    for row in rows:
        item = dict(row)
        item["law_surface"] = (
            "sampled-loop-observable"
            if row["obligation_id"] in {"loop-reversal", "nonorientable-control"}
            else "array-or-field-object"
        )
        classified.append(item)
    return [
        _output(
            "ambient-basis-error",
            {
                "rows": ambient,
                "maximum_field_law_error": max(
                    float(
                        row["maximum_field_law_error"]
                        if row["maximum_field_law_error"] is not None
                        else row["observed_error"]
                    )
                    for row in ambient
                ),
            },
        ),
        _output(
            "reference-o2-error",
            {
                "rows": reference,
                "maximum_observed_field_or_object_error": max(
                    float(
                        row["maximum_field_law_error"]
                        if row["maximum_field_law_error"] is not None
                        else row["observed_error"]
                    )
                    for row in reference
                ),
                "orientation_preserving_and_reversing_laws_kept_distinct": True,
                "obligation_ids": list(_REFERENCE_O2_OBLIGATION_IDS),
            },
        ),
        _output(
            "loop-reversal-signed-total-error",
            {
                "rows": reversal,
                "maximum_observed_error_cycles": max(
                    float(
                        row["maximum_loop_law_error"]
                        if row["maximum_loop_law_error"] is not None
                        else row["observed_error"]
                    )
                    for row in reversal
                ),
                "integer_output_used": False,
                "continuous_sampled_total_only": True,
            },
        ),
        _output(
            "array-versus-observable-law-separation",
            {
                "rows": classified,
                "array_or_field_row_count": sum(
                    row["law_surface"] == "array-or-field-object" for row in classified
                ),
                "sampled_loop_observable_row_count": sum(
                    row["law_surface"] == "sampled-loop-observable"
                    for row in classified
                ),
                "law_surfaces_collapsed": False,
            },
        ),
    ]


def _crossed_summary(
    members: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    totals = [
        _number(item["continuous_signed_total_cycles"], label="signed total")
        for item in members
        if item.get("continuous_signed_total_cycles") is not None
    ]
    errors = [
        _number(item["oracle_absolute_error_cycles"], label="oracle error")
        for item in members
        if item.get("oracle_absolute_error_cycles") is not None
    ]
    return {
        "cell_count": len(members),
        "primary_unit_count": len({str(item["primary_unit_id"]) for item in members}),
        "evaluable_cell_count": sum(
            item["attempt_status"] == "evaluable" for item in members
        ),
        "insufficient_cell_count": sum(
            item["attempt_status"] == "insufficient" for item in members
        ),
        "pass_cell_count": sum(item["state"] == "pass" for item in members),
        "fail_cell_count": sum(item["state"] == "fail" for item in members),
        "prediction_match_count": sum(
            item["prediction_class"] == item["expected_disposition"]
            or (
                item["expected_disposition"] == "prerequisite_failure"
                and item["prediction_class"] == "abstain"
            )
            for item in members
        ),
        "minimum_continuous_signed_total_cycles": min(totals) if totals else None,
        "maximum_continuous_signed_total_cycles": max(totals) if totals else None,
        "maximum_oracle_absolute_error_cycles": max(errors) if errors else None,
    }


def _group_crossed(
    cells: Sequence[Mapping[str, object]],
    fields: Sequence[str],
) -> list[dict[str, object]]:
    groups: dict[tuple[str, ...], list[Mapping[str, object]]] = defaultdict(list)
    for cell in cells:
        key = tuple(_string(cell[field], label=field) for field in fields)
        groups[key].append(cell)
    rows = []
    for key, members in sorted(groups.items()):
        row = {field: value for field, value in zip(fields, key, strict=True)}
        row.update(_crossed_summary(members))
        rows.append(row)
    return rows


def _d4_outputs(result: Mapping[str, object]) -> list[records.D7V1DescriptiveOutput]:
    cells = [
        _mapping(item, label="crossed cell")
        for item in _sequence(result.get("crossed_cells"), label="crossed cells")
    ]
    matrix_rows = _group_crossed(cells, ("field_graph_id", "cycle_graph_id"))
    role_rows = _group_crossed(cells, ("field_graph_id", "cycle_graph_id", "loop_role"))

    diagonal_groups: dict[tuple[str, str], list[Mapping[str, object]]] = defaultdict(
        list
    )
    for cell in cells:
        field_name = _string(
            cell["field_graph_id"], label="field_graph_id"
        ).removeprefix("a-")
        cycle_name = _string(
            cell["cycle_graph_id"], label="cycle_graph_id"
        ).removeprefix("b-")
        diagonal_groups[
            (
                "diagonal" if field_name == cycle_name else "off_diagonal",
                str(cell["loop_role"]),
            )
        ].append(cell)
    diagonal_rows = []
    for (relation, loop_role), members in sorted(diagonal_groups.items()):
        row = {"relation": relation, "loop_role": loop_role}
        row.update(_crossed_summary(members))
        totals = [
            abs(_number(item["continuous_signed_total_cycles"], label="signed total"))
            for item in members
            if item.get("continuous_signed_total_cycles") is not None
        ]
        row["mean_absolute_continuous_total_cycles"] = (
            sum(totals) / len(totals) if totals else None
        )
        diagonal_rows.append(row)

    nonvacuity = [
        _mapping(item, label="crossed nonvacuity")
        for item in _sequence(
            result.get("crossed_nonvacuity"), label="crossed nonvacuity"
        )
    ]
    primary_units = [
        _mapping(item, label="primary unit")
        for item in _sequence(result.get("primary_units"), label="primary units")
    ]
    spans_by_control: dict[str, list[float]] = defaultdict(list)
    for unit in primary_units:
        spans_by_control[str(unit["control_id"])].append(
            _number(unit["continuous_total_span_cycles"], label="total span")
        )
    adjacency_groups: dict[str, list[Mapping[str, object]]] = defaultdict(list)
    for item in nonvacuity:
        adjacency_groups[str(item["control_id"])].append(item)
    adjacency_rows = []
    for control_id, members in sorted(adjacency_groups.items()):
        distances = [
            _number(
                item["maximum_pairwise_substantive_output_distance"],
                label="substantive output distance",
            )
            for item in members
        ]
        spans = spans_by_control[control_id]
        adjacency_rows.append(
            {
                "control_id": control_id,
                "unit_count": len(members),
                "variation_required_count": sum(
                    item["substantive_output_variation_required"] is True
                    for item in members
                ),
                "three_graph_response_count": sum(
                    item["substantive_response_field_graph_count"] == 3
                    for item in members
                ),
                "minimum_pairwise_substantive_output_distance": min(distances),
                "maximum_pairwise_substantive_output_distance": max(distances),
                "minimum_loop_total_span_cycles": min(spans),
                "maximum_loop_total_span_cycles": max(spans),
                "all_states_pass": all(item["state"] == "pass" for item in members),
            }
        )
    effect_thresholds = {
        _number(
            item["minimum_substantive_output_distance"],
            label="minimum substantive output distance",
        )
        for item in nonvacuity
    }
    if len(effect_thresholds) != 1:
        raise QualificationContractError(
            "nonvacuity minimum effect threshold differs across units"
        )

    bundle = _mapping(result.get("evidence_bundle"), label="evidence bundle")
    support_rows = []
    for surface, receipt_key in (
        ("core", "core_cell_receipts"),
        ("loop", "loop_cell_receipts"),
    ):
        predictions = []
        for item in _sequence(bundle.get(receipt_key), label=receipt_key):
            receipt = _mapping(item, label=receipt_key[:-1])
            predictions.append(
                _mapping(receipt.get("sealed_prediction_receipt"), label="prediction")
            )
        counter: Counter[tuple[str, str, tuple[str, ...]]] = Counter()
        for prediction in predictions:
            reasons = tuple(
                sorted(
                    _string(reason, label="reason code")
                    for reason in _sequence(
                        prediction.get("reason_codes"), label="reason codes"
                    )
                )
            )
            counter[
                (
                    _string(
                        prediction.get("observed_attempt_status"),
                        label="observed attempt status",
                    ),
                    _string(
                        prediction.get("prediction_class"), label="prediction class"
                    ),
                    reasons,
                )
            ] += 1
        for (attempt_status, prediction_class, reasons), count in sorted(
            counter.items()
        ):
            support_rows.append(
                {
                    "surface": surface,
                    "attempt_status": attempt_status,
                    "prediction_class": prediction_class,
                    "reason_codes": list(reasons),
                    "cell_count": count,
                }
            )

    return [
        _output(
            "three-by-three-field-cycle-graph-matrix",
            {
                "rows": matrix_rows,
                "field_graph_count": len(
                    {row["field_graph_id"] for row in matrix_rows}
                ),
                "cycle_graph_count": len(
                    {row["cycle_graph_id"] for row in matrix_rows}
                ),
                "graph_cells_are_repeated_measures": True,
            },
        ),
        _output(
            "loop-role-separated-primary-boundary-and-offcore-control-table",
            {
                "rows": role_rows,
                "loop_roles_collapsed": False,
                "graph_cells_are_repeated_measures": True,
            },
        ),
        _output(
            "diagonal-offdiagonal-separation",
            {
                "rows": diagonal_rows,
                "diagonal_selected_as_winner": False,
                "descriptive_only": True,
            },
        ),
        _output(
            "adjacency-output-loop-total-effects",
            {
                "rows": adjacency_rows,
                "minimum_effect_distance": next(iter(effect_thresholds)),
                "field_output_and_loop_total_kept_distinct": True,
            },
        ),
        _output(
            "support-aware-cell-table",
            {
                "rows": support_rows,
                "insufficient_is_not_fail": True,
                "support_bookkeeping_is_not_substantive_output": True,
            },
        ),
    ]


def _stress_stratum_ids(unit: Mapping[str, object]) -> list[str]:
    result = []
    for item in _sequence(unit.get("stress_assignments"), label="stress assignments"):
        assignment = _mapping(item, label="stress assignment")
        result.append(
            f"stress.{_string(assignment['axis_id'], label='axis_id')}."
            f"{_string(assignment['level'], label='level')}"
        )
    return result


def _role_primary_units(
    result: Mapping[str, object],
) -> list[dict[str, object]]:
    primary = {
        str(item["primary_unit_id"]): _mapping(item, label="primary unit")
        for item in _sequence(result.get("primary_units"), label="primary units")
    }
    groups: dict[tuple[str, str], list[dict[str, object]]] = defaultdict(list)
    for item in _sequence(result.get("crossed_cells"), label="crossed cells"):
        cell = _mapping(item, label="crossed cell")
        groups[(str(cell["primary_unit_id"]), str(cell["loop_role"]))].append(cell)
    rows = []
    for (primary_unit_id, loop_role), cells in sorted(groups.items()):
        if len(cells) != 9:
            raise QualificationContractError(
                "each primary-unit loop role must retain nine graph cells"
            )
        expected = {str(cell["expected_disposition"]) for cell in cells}
        predictions = {str(cell["prediction_class"]) for cell in cells}
        attempts = {str(cell["attempt_status"]) for cell in cells}
        if len(expected) != 1 or len(predictions) != 1 or len(attempts) != 1:
            raise QualificationContractError("graph-cell role projection disagrees")
        unit = primary[primary_unit_id]
        rows.append(
            {
                "primary_unit_id": primary_unit_id,
                "loop_role": loop_role,
                "expected_disposition": next(iter(expected)),
                "prediction_class": next(iter(predictions)),
                "attempt_status": next(iter(attempts)),
                "state": "pass"
                if all(cell["state"] == "pass" for cell in cells)
                else "fail",
                "control_id": unit["control_id"],
                "stratum_ids": _stress_stratum_ids(unit),
            }
        )
    return rows


def _classification_summary(
    members: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    rate_units = [
        item
        for item in members
        if item["expected_disposition"] != "prerequisite_failure"
    ]
    positives = [
        item for item in rate_units if item["expected_disposition"] == "nonzero"
    ]
    negatives = [item for item in rate_units if item["expected_disposition"] == "null"]
    evaluable = [item for item in rate_units if item["attempt_status"] == "evaluable"]
    prerequisites = [
        item
        for item in members
        if item["expected_disposition"] == "prerequisite_failure"
    ]
    return {
        "attempted_primary_unit_count": len(members),
        "rate_eligible_count": len(rate_units),
        "rate_evaluable_count": len(evaluable),
        "coverage": len(evaluable) / len(rate_units) if rate_units else None,
        "abstention_fraction": (
            sum(item["prediction_class"] == "abstain" for item in rate_units)
            / len(rate_units)
            if rate_units
            else None
        ),
        "positive_expected_count": len(positives),
        "negative_expected_count": len(negatives),
        "recall": (
            sum(item["prediction_class"] == "nonzero" for item in positives)
            / len(positives)
            if positives
            else None
        ),
        "specificity": (
            sum(item["prediction_class"] == "null" for item in negatives)
            / len(negatives)
            if negatives
            else None
        ),
        "prerequisite_expected_count": len(prerequisites),
        "prerequisite_pass_count": sum(
            item["state"] == "pass"
            and item["prediction_class"] == "abstain"
            and item["attempt_status"] == "insufficient"
            for item in prerequisites
        ),
        "all_graph_cells_pass": all(item["state"] == "pass" for item in members),
    }


def _d5_outputs(
    result: Mapping[str, object],
    metamorphic_rows: Sequence[Mapping[str, object]],
    d6_decision: Mapping[str, object],
) -> list[records.D7V1DescriptiveOutput]:
    strata = [
        _mapping(item, label="stress stratum")
        for item in _sequence(result.get("strata"), label="strata")
    ]
    stratum_rows = []
    for item in strata:
        stratum_rows.append(
            {
                key: item[key]
                for key in (
                    "stratum_id",
                    "state",
                    "attempted_count",
                    "evaluable_count",
                    "attempt_insufficient_count",
                    "pass_count",
                    "fail_count",
                    "coverage",
                    "abstention_fraction",
                    "recall",
                    "specificity",
                    "positive_expected_count",
                    "negative_expected_count",
                    "prerequisite_expected_count",
                    "prerequisite_pass_count",
                    "score_denominator",
                    "prerequisite_rate_handling",
                )
            }
        )

    role_units = _role_primary_units(result)
    role_groups: dict[tuple[str, str], list[Mapping[str, object]]] = defaultdict(list)
    for item in role_units:
        for stratum_id in item["stratum_ids"]:
            role_groups[(str(stratum_id), str(item["loop_role"]))].append(item)
    role_rows = []
    for (stratum_id, loop_role), members in sorted(role_groups.items()):
        row = {"stratum_id": stratum_id, "loop_role": loop_role}
        row.update(_classification_summary(members))
        role_rows.append(row)

    def minimum_present(field: str) -> float | None:
        values = [float(row[field]) for row in role_rows if row.get(field) is not None]
        return min(values) if values else None

    bundle = _mapping(result.get("evidence_bundle"), label="evidence bundle")
    prediction_sets: list[tuple[str, list[dict[str, object]]]] = []
    for surface, key in (
        ("core", "core_cell_receipts"),
        ("loop", "loop_cell_receipts"),
    ):
        predictions = []
        for item in _sequence(bundle.get(key), label=key):
            receipt = _mapping(item, label=key[:-1])
            predictions.append(
                _mapping(receipt.get("sealed_prediction_receipt"), label="prediction")
            )
        prediction_sets.append((surface, predictions))

    reason_counter: Counter[tuple[str, str]] = Counter()
    for surface, predictions in prediction_sets:
        for prediction in predictions:
            for reason in _sequence(
                prediction.get("reason_codes"), label="prediction reason codes"
            ):
                reason_counter[(surface, _string(reason, label="reason code"))] += 1
    reason_rows = [
        {"surface": surface, "reason_code": reason, "cell_count": count}
        for (surface, reason), count in sorted(reason_counter.items())
    ]

    prerequisite_primary = [
        item
        for item in _sequence(result.get("primary_units"), label="primary units")
        if _mapping(item, label="primary unit").get("expected_disposition")
        == "prerequisite_failure"
    ]
    core_primary_units = [
        _mapping(item, label="core primary unit")
        for item in _sequence(
            result.get("core_primary_units"), label="core primary units"
        )
    ]
    collapsed_core_units, _repeat_rows = _collapse_core_boundary_repeats(
        core_primary_units
    )
    prerequisite_core = [
        item
        for item in collapsed_core_units
        if item.get("expected_disposition") == "prerequisite_failure"
    ]

    nonvacuity = [
        _mapping(item, label="crossed nonvacuity")
        for item in _sequence(
            result.get("crossed_nonvacuity"), label="crossed nonvacuity"
        )
    ]
    nonvacuity_rows = _counter_rows(
        nonvacuity,
        (
            "control_id",
            "attempt_status",
            "state",
            "substantive_output_variation_required",
            "substantive_response_field_graph_count",
        ),
    )

    abstention_rows = []
    for surface, predictions in prediction_sets:
        counter: Counter[tuple[str, tuple[str, ...]]] = Counter()
        for prediction in predictions:
            if prediction["prediction_class"] != "abstain":
                continue
            reasons = tuple(
                sorted(str(reason) for reason in prediction["reason_codes"])
            )
            counter[(str(prediction["observed_attempt_status"]), reasons)] += 1
        for (attempt_status, reasons), count in sorted(counter.items()):
            abstention_rows.append(
                {
                    "surface": surface,
                    "attempt_status": attempt_status,
                    "reason_codes": list(reasons),
                    "cell_count": count,
                }
            )

    typed_rows = []
    for surface, values, status_field in (
        ("gate", _sequence(result.get("gate_results"), label="gate results"), "state"),
        (
            "core-primary",
            collapsed_core_units,
            "attempt_status",
        ),
        (
            "loop-primary",
            _sequence(result.get("primary_units"), label="loop primary"),
            "attempt_status",
        ),
    ):
        counts = Counter(
            str(_mapping(item, label=surface).get(status_field)) for item in values
        )
        for status, count in sorted(counts.items()):
            typed_rows.append(
                {
                    "surface": surface,
                    "status_field": status_field,
                    "status": status,
                    "count": count,
                }
            )
    for gate_id in ("d6", "d7", "d8"):
        decision = _mapping(d6_decision.get(gate_id), label=f"{gate_id} decision")
        typed_rows.append(
            {
                "surface": "advancement-decision",
                "gate_id": gate_id,
                "status_field": "state",
                "status": _string(decision.get("state"), label=f"{gate_id} state"),
                "count": 1,
            }
        )
    metamorphic_counts = Counter(str(row["state"]) for row in metamorphic_rows)
    for status, count in sorted(metamorphic_counts.items()):
        typed_rows.append(
            {
                "surface": "d3-metamorphic-obligation",
                "status_field": "state",
                "status": status,
                "count": count,
            }
        )

    return [
        _output(
            "worst-case-by-stress-stratum",
            {
                "rows": stratum_rows,
                "worst_case_coverage": min(
                    float(row["coverage"]) for row in stratum_rows
                ),
                "worst_case_recall": min(float(row["recall"]) for row in stratum_rows),
                "worst_case_specificity": min(
                    float(row["specificity"]) for row in stratum_rows
                ),
                "stress_cells_are_not_iid_samples": True,
            },
        ),
        _output(
            "loop-role-separated-worst-case-and-coverage-table",
            {
                "rows": role_rows,
                "worst_case_coverage": minimum_present("coverage"),
                "worst_case_recall_where_defined": minimum_present("recall"),
                "worst_case_specificity_where_defined": minimum_present("specificity"),
                "loop_roles_collapsed": False,
            },
        ),
        _output(
            "coverage-abstention-recall-specificity-table",
            {
                "rows": stratum_rows,
                "score_denominator": "expected_nonprerequisite_primary_units",
                "prerequisites_excluded_but_mandatory": True,
                "silent_denominator_change": False,
            },
        ),
        _output(
            "mandatory-prerequisite-failure-table",
            {
                "loop_primary_unit_count": len(prerequisite_primary),
                "core_primary_unit_count": len(prerequisite_core),
                "all_loop_prerequisites_pass": all(
                    _mapping(item, label="primary unit")["state"] == "pass"
                    for item in prerequisite_primary
                ),
                "all_core_prerequisites_pass": all(
                    _mapping(item, label="core primary unit")["state"] == "pass"
                    for item in prerequisite_core
                ),
                "reason_rows": reason_rows,
                "prerequisite_failures_removed_from_artifact": False,
            },
        ),
        _output(
            "required-nonvacuity-evidence",
            {
                "rows": nonvacuity_rows,
                "unit_count": len(nonvacuity),
                "all_states_pass": all(item["state"] == "pass" for item in nonvacuity),
                "graph_cells_are_repeated_measures": True,
                "id_only_nonvacuity_forbidden": True,
            },
        ),
        _output(
            "abstention-reason-table",
            {
                "rows": abstention_rows,
                "abstention_count": sum(
                    int(row["cell_count"]) for row in abstention_rows
                ),
                "abstention_relabelled_as_failure": False,
            },
        ),
        _output(
            "typed-failure-coverage",
            {
                "rows": typed_rows,
                "reason_rows": reason_rows,
                "insufficient_retained_as_distinct_status": True,
                "not_run_retained_as_distinct_status": True,
                "not_run_row_count": sum(
                    int(row["count"])
                    for row in typed_rows
                    if row["status"] == "not_run"
                ),
            },
        ),
    ]


def _independence_outputs(
    plan: Mapping[str, object],
    protocol: Mapping[str, object],
    result: Mapping[str, object],
    d6_decision: Mapping[str, object],
) -> list[records.D7V1DescriptiveOutput]:
    selection = _mapping(protocol.get("selection"), label="selection")
    cartesian = _mapping(protocol.get("cartesian"), label="cartesian")
    graphs = _mapping(protocol.get("graphs"), label="graphs")
    implementation = _mapping(
        protocol.get("implementation_registry"), label="implementation registry"
    )
    field_graphs = [
        _mapping(item, label="field graph")
        for item in _sequence(graphs.get("field_estimation"), label="field graphs")
    ]
    cycle_graphs = [
        _mapping(item, label="cycle graph")
        for item in _sequence(graphs.get("cycle_construction"), label="cycle graphs")
    ]
    controls = [
        _mapping(item, label="control")
        for item in _sequence(selection.get("controls"), label="controls")
    ]
    seeds = _sequence(selection.get("seeds"), label="selection seeds")
    stress_axes = [
        _mapping(item, label="stress axis")
        for item in _sequence(selection.get("stress_axes"), label="stress axes")
    ]
    map_rows = [
        {
            "dimension": "generator-family",
            "level_count": 1,
            "levels": [cartesian["generator_family_id"]],
            "epistemic_role": "shared-construction",
        },
        {
            "dimension": "seed",
            "level_count": len(seeds),
            "levels": list(seeds),
            "epistemic_role": "within-construction-replication",
        },
        {
            "dimension": "control",
            "level_count": len(controls),
            "levels": sorted(str(item["control_id"]) for item in controls),
            "epistemic_role": "matched-case-semantics",
        },
        {
            "dimension": "field-graph",
            "level_count": len(field_graphs),
            "levels": sorted(str(item["graph_id"]) for item in field_graphs),
            "epistemic_role": "repeated-measure-construction-choice",
        },
        {
            "dimension": "cycle-graph",
            "level_count": len(cycle_graphs),
            "levels": sorted(str(item["graph_id"]) for item in cycle_graphs),
            "epistemic_role": "repeated-measure-construction-choice",
        },
        {
            "dimension": "boundary",
            "level_count": len(cartesian["primary_boundaries"]),
            "levels": sorted(
                str(_mapping(item, label="boundary")["level"])
                for item in cartesian["primary_boundaries"]
            ),
            "epistemic_role": "paired-nuisance-repeat",
        },
        {
            "dimension": "implementation",
            "level_count": 1,
            "levels": [implementation["surrogate_estimator_id"]],
            "epistemic_role": "shared-implementation",
        },
        {
            "dimension": "oracle",
            "level_count": 1,
            "levels": ["generator-coupled-synthetic-oracle"],
            "epistemic_role": "shared-not-independent-confirmation",
        },
    ]

    scientific_units = [
        _mapping(item, label="scientific unit")
        for item in _sequence(plan.get("scientific_units"), label="scientific units")
    ]
    construction_unit = next(
        item
        for item in scientific_units
        if item.get("unit_id") == "construction-family-unit"
    )
    diversity_rows = [
        {
            "axis": "selection-seed",
            "observed_count": len(seeds),
            "diversity_class": "replication-within-one-construction",
            "independent_confirmation": False,
        },
        {
            "axis": "stress-combination",
            "observed_count": math.prod(
                len(_sequence(item.get("levels"), label="stress levels"))
                for item in stress_axes
            ),
            "diversity_class": "paired-stress-repeat",
            "independent_confirmation": False,
        },
        {
            "axis": "field-cycle-graph-pair",
            "observed_count": len(field_graphs) * len(cycle_graphs),
            "diversity_class": "crossed-repeated-measure",
            "independent_confirmation": False,
        },
        {
            "axis": "construction-family",
            "observed_count": _integer(
                construction_unit.get("declared_count"),
                label="construction family count",
            ),
            "diversity_class": "construction",
            "independent_confirmation": False,
        },
        {
            "axis": "admitted-confirmation-family",
            "observed_count": int(
                _boolean(
                    d6_decision.get("confirmation_family_admitted"),
                    label="confirmation_family_admitted",
                )
            ),
            "diversity_class": "independent-construction",
            "independent_confirmation": False,
        },
    ]

    nonclaim_fields = {
        "external_prior_observation_excluded": result[
            "external_prior_observation_excluded"
        ],
        "hidden_confirmation_accessed": result["hidden_confirmation_accessed"],
        "representation_d2_d5_qualified": result["representation_d2_d5_qualified"],
        "synthetic_qualified": result["synthetic_qualified"],
        "confirmation_family_admitted": d6_decision["confirmation_family_admitted"],
        "confirmation_values_accessed": d6_decision["confirmation_values_accessed"],
    }
    return [
        _output(
            "shared-generator-seed-graph-boundary-implementation-oracle-map",
            {
                "rows": map_rows,
                "shared_dimensions_are_not_independent_evidence": True,
                "graph_pairs_are_not_iid_replicates": True,
            },
        ),
        _output(
            "replication-versus-construction-diversity-table",
            {
                "rows": diversity_rows,
                "observed_construction_family_count": construction_unit[
                    "declared_count"
                ],
                "seed_block_independence_proved": False,
                "independent_confirmation_observed": False,
            },
        ),
        _output(
            "epistemic-independence-nonclaim",
            {
                "observed_parent_facts": nonclaim_fields,
                "one_immutable_evidence_lineage_is_not_a_scientific_replicate": True,
                "replication_is_not_construction_diversity": True,
                "independent_confirmation_observed": False,
                "d0_d6_claim_strengthened": False,
                "d7_design_selected_from_these_descriptive_values": False,
                "scientific_claim_eligible": False,
            },
        ),
    ]


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
        *_d3_outputs(metamorphic_rows),
        *_d4_outputs(result),
        *_d5_outputs(result, metamorphic_rows, d6_decision),
        *_independence_outputs(plan, protocol, result, d6_decision),
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
