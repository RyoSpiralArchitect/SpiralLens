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

_CARTESIAN_D3_LAWS = (
    "ambient_signed_permutation",
    "reference_rotation",
    "reference_reflection",
    "loop_reversal",
)
_REPRESENTATION_D3_FIELD_GRAPH_IDS = (
    "a-mutual",
    "a-radius",
    "a-shared",
)
_REPRESENTATION_D3_CYCLE_GRAPH_IDS = (
    "b-mutual",
    "b-radius",
    "b-shared",
)
_REPRESENTATION_D3_LOOP_LAWS = (
    "reference_rotation",
    "reference_reflection",
    "loop_reversal",
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
    expected = {
        "cartesian-fourier-family-verified": (
            (
                "cartesian-fourier-fixed-null",
                "cartesian-fourier-no-core-null",
                "cartesian-fourier-positive",
                "cartesian-fourier-prerequisite-failure",
            ),
            (
                "amplitude-max-absolute-error",
                "direction-minimum-cosine",
                "second-harmonic-max-absolute-error",
                "split-max-disagreement",
                "support-mismatch-count",
            ),
        ),
        "representation-family-verified": (
            ("angular-section-positive", "fixed-direction-null"),
            (
                "amplitude-max-absolute-error",
                "phase-law-coherence",
                "support-mismatch-count",
            ),
        ),
    }
    graph_families = ("mutual-knn", "fixed-radius", "shared-neighbor")
    bundle = _mapping(result.get("evidence_bundle"), label="evidence bundle")
    rows: list[dict[str, object]] = []
    observed_family_ids = []
    for family_item in _sequence(
        bundle.get("static_runtime_receipts"), label="static runtime receipts"
    ):
        family = _mapping(family_item, label="static runtime receipt")
        if "cases" not in family:
            continue
        family_evidence_id = _string(
            family.get("evidence_id"), label="D1 family evidence_id"
        )
        if family_evidence_id not in expected:
            raise QualificationContractError("D1 numeric family is not closed")
        observed_family_ids.append(family_evidence_id)
        case_ids, metric_ids = expected[family_evidence_id]
        observed_coordinates = []
        for case_item in _sequence(family.get("cases"), label="D1 cases"):
            case = _mapping(case_item, label="D1 case")
            case_id = _string(case.get("case_id"), label="D1 case_id")
            for metric_item in _sequence(
                case.get("numeric_metric_receipts"), label="D1 numeric metrics"
            ):
                metric = _mapping(metric_item, label="D1 numeric metric")
                graph_family = _string(
                    metric.get("graph_family"), label="D1 graph_family"
                )
                metric_id = _string(metric.get("metric_id"), label="D1 metric_id")
                observed_coordinates.append((case_id, graph_family, metric_id))
                comparator = _string(metric.get("comparator"), label="D1 comparator")
                observed = _number(
                    metric.get("observed_value"), label="D1 observed_value"
                )
                threshold = _number(metric.get("threshold"), label="D1 threshold")
                if comparator == "at-most":
                    margin = threshold - observed
                elif comparator == "at-least":
                    margin = observed - threshold
                elif comparator == "exact-zero":
                    difference = abs(observed - threshold)
                    margin = 0.0 if difference == 0.0 else -difference
                else:
                    raise QualificationContractError("D1 comparator is not closed")
                passed = _boolean(metric.get("passed"), label="D1 metric passed")
                if passed is not (margin >= 0.0):
                    raise QualificationContractError(
                        "D1 persisted pass flag differs from its signed margin"
                    )
                rows.append(
                    {
                        "family_evidence_id": family_evidence_id,
                        "case_id": case_id,
                        "graph_family": graph_family,
                        "metric_id": metric_id,
                        "comparator": comparator,
                        "observed_value": observed,
                        "threshold": threshold,
                        "signed_margin": margin,
                        "passed": passed,
                        "field_graph_fingerprint_sha256": _string(
                            metric.get("field_graph_fingerprint_sha256"),
                            label="D1 field graph fingerprint",
                        ),
                        "estimator_output_sha256": _string(
                            metric.get("estimator_output_sha256"),
                            label="D1 estimator output fingerprint",
                        ),
                        "oracle_fingerprint_sha256": _string(
                            metric.get("oracle_fingerprint_sha256"),
                            label="D1 oracle fingerprint",
                        ),
                    }
                )
        expected_coordinates = tuple(
            (case_id, graph_family, metric_id)
            for case_id in case_ids
            for graph_family in graph_families
            for metric_id in metric_ids
        )
        if tuple(observed_coordinates) != expected_coordinates:
            raise QualificationContractError(
                "D1 persisted analytic-check order or universe differs"
            )
    if tuple(observed_family_ids) != tuple(expected) or len(rows) != 78:
        raise QualificationContractError(
            "D1 numeric family coverage differs from 60 plus 18 checks"
        )
    return rows


def _d1_outputs(result: Mapping[str, object]) -> list[records.D7V1DescriptiveOutput]:
    rows = _numeric_metric_rows(result)
    family_ids = (
        "cartesian-fourier-family-verified",
        "representation-family-verified",
    )
    grouped = {
        family_evidence_id: [
            row for row in rows if row["family_evidence_id"] == family_evidence_id
        ]
        for family_evidence_id in family_ids
    }
    family_row_counts = {
        family_evidence_id: len(grouped[family_evidence_id])
        for family_evidence_id in family_ids
    }
    if family_row_counts != {
        "cartesian-fourier-family-verified": 60,
        "representation-family-verified": 18,
    }:
        raise QualificationContractError("D1 family analytic-check counts differ")

    fragility_rows = []
    for family_evidence_id in family_ids:
        members = grouped[family_evidence_id]
        margins = [float(member["signed_margin"]) for member in members]
        positive = [
            member for member in members if float(member["signed_margin"]) > 0.0
        ]
        if not positive:
            raise QualificationContractError(
                "D1 family has no strictly positive signed margin"
            )
        minimum_positive = min(float(member["signed_margin"]) for member in positive)
        fragility_rows.append(
            {
                "family_evidence_id": family_evidence_id,
                "analytic_check_count": len(members),
                "zero_margin_count": sum(value == 0.0 for value in margins),
                "negative_margin_count": sum(value < 0.0 for value in margins),
                "minimum_signed_margin": min(margins),
                "minimum_strictly_positive_margin": minimum_positive,
                "closest_positive_check_keys": [
                    {
                        "case_id": member["case_id"],
                        "graph_family": member["graph_family"],
                        "metric_id": member["metric_id"],
                    }
                    for member in positive
                    if member["signed_margin"] == minimum_positive
                ],
                "all_persisted_checks_passed": all(
                    member["passed"] is True for member in members
                ),
                "threshold_change_authorized": False,
            }
        )
    if [row["zero_margin_count"] for row in fragility_rows] != [12, 6] or [
        row["negative_margin_count"] for row in fragility_rows
    ] != [0, 0]:
        raise QualificationContractError(
            "D1 exact-zero or negative-margin counts differ"
        )
    global_minimum = min(float(row["signed_margin"]) for row in rows)
    global_minimum_positive = min(
        float(row["minimum_strictly_positive_margin"]) for row in fragility_rows
    )
    if global_minimum != 0.0 or global_minimum_positive != 9.999877875467292e-11:
        raise QualificationContractError("D1 global fragility extrema differ")

    return [
        _output(
            "signed-margin-by-analytic-check",
            {
                "rows": rows,
                "family_row_counts": family_row_counts,
                "row_count": len(rows),
                "thresholds_modified": False,
                "descriptive_only": True,
            },
        ),
        _output(
            "fragility-without-threshold-change",
            {
                "rows": fragility_rows,
                "evaluation_unit": "d1-matched-class-unit",
                "matched_class_unit_count": len(fragility_rows),
                "thresholds_modified": False,
                "gate_reclassified": False,
                "minimum_observed_signed_margin": global_minimum,
                "minimum_strictly_positive_margin": global_minimum_positive,
                "exact_zero_margins_kept_distinct_from_positive_fragility": True,
            },
        ),
    ]


_CORE_DECLARED_OUTCOME_FIELDS = (
    "attempt_status",
    "expected_disposition",
    "prediction_class",
    "reason_codes",
    "state",
)
_CORE_BLIND_DESCRIPTOR_FIELDS = (
    "amplitude",
    "identifiability_score",
    "support_counts",
)
_CORE_BOUNDARY_IDENTITY_FIELDS = (
    "blind_input_fingerprint_sha256",
    "field_estimate_fingerprint_sha256",
    "field_graph_fingerprint_sha256",
    "oracle_fingerprint_sha256",
    "prediction_fingerprint_sha256",
)


def _collapse_core_boundary_repeats(
    primary_units: Sequence[Mapping[str, object]],
    core_cells: Sequence[Mapping[str, object]],
    core_receipts: Sequence[Mapping[str, object]],
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    cells_by_id = {
        _string(item.get("core_cell_id"), label="core_cell_id"): item
        for item in core_cells
    }
    receipts_by_id = {
        _string(item.get("core_cell_id"), label="core receipt cell_id"): item
        for item in core_receipts
    }
    if (
        len(cells_by_id) != 192
        or len(receipts_by_id) != 192
        or set(cells_by_id) != set(receipts_by_id)
    ):
        raise QualificationContractError("D2 core cell evidence universe is not closed")

    repeat_groups: dict[tuple[int, str, str, str], dict[str, Mapping[str, object]]] = {}
    for unit in primary_units:
        assignments = {
            _string(item.get("axis_id"), label="stress axis id"): _string(
                item.get("level"), label="stress level"
            )
            for item in (
                _mapping(value, label="stress assignment")
                for value in _sequence(
                    unit.get("stress_assignments"), label="stress assignments"
                )
            )
        }
        if set(assignments) != {
            "boundary",
            "state-geometry-warp",
            "structured-observation-perturbation",
        }:
            raise QualificationContractError("D2 stress assignments are not closed")
        key = (
            _integer(unit.get("selection_seed"), label="selection_seed"),
            _string(unit.get("control_id"), label="control_id"),
            assignments["state-geometry-warp"],
            assignments["structured-observation-perturbation"],
        )
        boundary_level = assignments["boundary"]
        group = repeat_groups.setdefault(key, {})
        if boundary_level in group:
            raise QualificationContractError("D2 boundary repeat is duplicated")
        group[boundary_level] = unit

    collapsed_units = []
    repeat_rows = []
    for key, boundaries in repeat_groups.items():
        if set(boundaries) != {"central", "wide"}:
            raise QualificationContractError(
                "D2 scientific input requires central and wide boundary repeats"
            )
        central = boundaries["central"]
        wide = boundaries["wide"]
        unit_equalities = {
            field: central.get(field) == wide.get(field)
            for field in (
                "d2_scientific_input_fingerprint_sha256",
                *_CORE_DECLARED_OUTCOME_FIELDS,
            )
        }
        central_ids = _sequence(
            central.get("core_cell_ids"), label="central core_cell_ids"
        )
        wide_ids = _sequence(wide.get("core_cell_ids"), label="wide core_cell_ids")
        if (
            not all(unit_equalities.values())
            or len(central_ids) != 3
            or len(wide_ids) != 3
        ):
            raise QualificationContractError(
                "D2 boundary repeats disagree at the scientific-input grain"
            )

        graph_rows = []
        for central_raw_id, wide_raw_id in zip(central_ids, wide_ids, strict=True):
            central_id = _string(central_raw_id, label="central core_cell_id")
            wide_id = _string(wide_raw_id, label="wide core_cell_id")
            central_cell = cells_by_id[central_id]
            wide_cell = cells_by_id[wide_id]
            field_graph_id = _string(
                central_cell.get("field_graph_id"), label="field_graph_id"
            )
            if wide_cell.get("field_graph_id") != field_graph_id:
                raise QualificationContractError("D2 boundary graph order differs")
            central_receipt = receipts_by_id[central_id]
            wide_receipt = receipts_by_id[wide_id]
            for cell, receipt in (
                (central_cell, central_receipt),
                (wide_cell, wide_receipt),
            ):
                if sha256_bytes(canonical_json_bytes(cell)) != receipt.get(
                    "normalized_summary_sha256"
                ):
                    raise QualificationContractError(
                        "D2 core summary evidence fingerprint differs"
                    )
            central_blind = _mapping(
                central_receipt.get("blind_input_receipt"),
                label="central blind core input",
            )
            wide_blind = _mapping(
                wide_receipt.get("blind_input_receipt"),
                label="wide blind core input",
            )
            descriptor_equalities = {
                f"{field}_descriptor_equal": (
                    central_blind.get(field) == wide_blind.get(field)
                )
                for field in _CORE_BLIND_DESCRIPTOR_FIELDS
            }
            identity_equalities = {
                f"{field}_equal": central_cell.get(field) == wide_cell.get(field)
                for field in _CORE_BOUNDARY_IDENTITY_FIELDS
            }
            cell_equalities = {
                field: central_cell.get(field) == wide_cell.get(field)
                for field in _CORE_DECLARED_OUTCOME_FIELDS
            }
            candidate_rows_equal = central_receipt.get(
                "candidate_rows"
            ) == wide_receipt.get("candidate_rows")
            candidate_fingerprint_equal = central_cell.get(
                "candidate_fingerprint_sha256"
            ) == wide_cell.get("candidate_fingerprint_sha256")
            declared_outcomes_equal = all(cell_equalities.values())
            if (
                not declared_outcomes_equal
                or not candidate_rows_equal
                or not candidate_fingerprint_equal
                or not all(descriptor_equalities.values())
                or any(identity_equalities.values())
            ):
                raise QualificationContractError(
                    "D2 boundary graph evidence differs outside the frozen scope"
                )
            graph_rows.append(
                {
                    "field_graph_id": field_graph_id,
                    "central_core_cell_id": central_id,
                    "wide_core_cell_id": wide_id,
                    "central_candidate_fingerprint_sha256": central_cell[
                        "candidate_fingerprint_sha256"
                    ],
                    "wide_candidate_fingerprint_sha256": wide_cell[
                        "candidate_fingerprint_sha256"
                    ],
                    "declared_outcomes_equal": declared_outcomes_equal,
                    "blind_array_descriptor_equalities": descriptor_equalities,
                    "boundary_specific_identity_equalities": identity_equalities,
                }
            )
            repeat_rows.append(
                {
                    "selection_seed": key[0],
                    "control_id": key[1],
                    "state_geometry_warp_level": key[2],
                    "structured_observation_perturbation_level": key[3],
                    "field_graph_id": field_graph_id,
                    "central_core_cell_id": central_id,
                    "wide_core_cell_id": wide_id,
                    "scientific_input_fingerprint_equal": unit_equalities[
                        "d2_scientific_input_fingerprint_sha256"
                    ],
                    "attempt_status_equal": cell_equalities["attempt_status"],
                    "expected_disposition_equal": cell_equalities[
                        "expected_disposition"
                    ],
                    "prediction_class_equal": cell_equalities["prediction_class"],
                    "candidate_rows_equal": candidate_rows_equal,
                    "candidate_fingerprint_equal": candidate_fingerprint_equal,
                    "reason_codes_equal": cell_equalities["reason_codes"],
                    "state_equal": cell_equalities["state"],
                    "declared_outcomes_equal": declared_outcomes_equal,
                    "blind_array_descriptor_equalities": descriptor_equalities,
                    "boundary_specific_identity_equalities": identity_equalities,
                }
            )
        collapsed_units.append(
            {
                "selection_seed": key[0],
                "control_id": key[1],
                "state_geometry_warp_level": key[2],
                "structured_observation_perturbation_level": key[3],
                "d2_scientific_input_fingerprint_sha256": central[
                    "d2_scientific_input_fingerprint_sha256"
                ],
                "expected_disposition": central["expected_disposition"],
                "attempt_status": central["attempt_status"],
                "prediction_class": central["prediction_class"],
                "state": central["state"],
                "reason_codes": list(
                    _sequence(central.get("reason_codes"), label="reason_codes")
                ),
                "boundary_primary_unit_ids": {
                    "central": _string(
                        central.get("primary_unit_id"), label="central primary_unit_id"
                    ),
                    "wide": _string(
                        wide.get("primary_unit_id"), label="wide primary_unit_id"
                    ),
                },
                "graph_rows": graph_rows,
            }
        )
    if len(collapsed_units) != 32 or len(repeat_rows) != 96:
        raise QualificationContractError("D2 exact boundary grain is not 32 by 3")
    return collapsed_units, repeat_rows


def _d2_confounder_observation_rows(
    bundle: Mapping[str, object],
) -> tuple[list[dict[str, object]], dict[str, object]]:
    matrix = _mapping(
        bundle.get("d2_confounder_matrix_receipt"),
        label="D2 confounder matrix receipt",
    )
    rows = []
    for item in _sequence(matrix.get("cells"), label="D2 confounder cells"):
        cell = _mapping(item, label="D2 confounder cell")
        observation = _mapping(
            cell.get("construction_observation"),
            label="D2 confounder construction observation",
        )
        sealed = _mapping(
            cell.get("sealed_prediction_receipt"),
            label="D2 confounder sealed prediction",
        )
        rows.append(
            {
                "cell_id": _string(cell.get("cell_id"), label="confounder cell_id"),
                "confounder_id": _string(
                    cell.get("confounder_id"), label="confounder_id"
                ),
                "construction_id": _string(
                    cell.get("construction_id"), label="confounder construction_id"
                ),
                "field_graph_id": _string(
                    cell.get("field_graph_id"), label="confounder field_graph_id"
                ),
                "probe_row": _integer(
                    observation.get("probe_row"), label="confounder probe_row"
                ),
                "probe_row_role": _string(
                    observation.get("probe_row_role"),
                    label="confounder probe_row_role",
                ),
                "probe_amplitude": _number(
                    observation.get("probe_amplitude"),
                    label="confounder probe_amplitude",
                ),
                "core_amplitude_ceiling": _number(
                    observation.get("core_amplitude_ceiling"),
                    label="confounder core_amplitude_ceiling",
                ),
                "core_amplitude_threshold_satisfied": _boolean(
                    observation.get("core_amplitude_threshold_satisfied"),
                    label="confounder core amplitude threshold",
                ),
                "probe_identifiability_score": _number(
                    observation.get("probe_identifiability_score"),
                    label="confounder probe_identifiability_score",
                ),
                "identifiability_floor": _number(
                    observation.get("identifiability_floor"),
                    label="confounder identifiability_floor",
                ),
                "direction_loss_threshold_satisfied": _boolean(
                    observation.get("direction_loss_threshold_satisfied"),
                    label="confounder direction loss threshold",
                ),
                "probe_measurement_support": _integer(
                    observation.get("probe_measurement_support"),
                    label="confounder probe_measurement_support",
                ),
                "minimum_support_count": _integer(
                    observation.get("minimum_support_count"),
                    label="confounder minimum_support_count",
                ),
                "measurement_support_threshold_satisfied": _boolean(
                    observation.get("measurement_support_threshold_satisfied"),
                    label="confounder measurement support threshold",
                ),
                "oracle_input_present": _boolean(
                    observation.get("oracle_input_present"),
                    label="confounder oracle_input_present",
                ),
                "selection_seed_present": _boolean(
                    observation.get("selection_seed_present"),
                    label="confounder selection_seed_present",
                ),
                "expected_attempt_status": _string(
                    cell.get("expected_attempt_status"),
                    label="confounder expected_attempt_status",
                ),
                "expected_prediction_class": _string(
                    cell.get("expected_prediction_class"),
                    label="confounder expected_prediction_class",
                ),
                "expected_reason_codes": [
                    _string(reason, label="confounder expected reason")
                    for reason in _sequence(
                        cell.get("expected_reason_codes"),
                        label="confounder expected reason codes",
                    )
                ],
                "observed_attempt_status": _string(
                    sealed.get("observed_attempt_status"),
                    label="confounder observed_attempt_status",
                ),
                "observed_prediction_class": _string(
                    sealed.get("prediction_class"),
                    label="confounder observed prediction_class",
                ),
                "observed_reason_codes": [
                    _string(reason, label="confounder observed reason")
                    for reason in _sequence(
                        sealed.get("reason_codes"),
                        label="confounder observed reason codes",
                    )
                ],
                "blind_input_fingerprint_sha256": _string(
                    sealed.get("blind_input_fingerprint_sha256"),
                    label="confounder blind input fingerprint",
                ),
                "primary_unit_sha256": _string(
                    sealed.get("primary_unit_sha256"),
                    label="confounder primary unit fingerprint",
                ),
                "policy_fingerprint_sha256": _string(
                    sealed.get("policy_fingerprint_sha256"),
                    label="confounder policy fingerprint",
                ),
                "sealed_before_oracle_score": _boolean(
                    sealed.get("sealed_before_oracle_score"),
                    label="confounder sealed_before_oracle_score",
                ),
                "oracle_read": _boolean(
                    sealed.get("oracle_read"),
                    label="confounder oracle_read",
                ),
                "state": _string(cell.get("state"), label="confounder state"),
            }
        )
    rows.sort(key=lambda row: str(row["cell_id"]))
    if len(rows) != 6 or len({str(row["cell_id"]) for row in rows}) != 6:
        raise QualificationContractError("D2 confounder observation set is not closed")
    metadata = {
        "schema_version": _string(
            matrix.get("schema_version"), label="D2 confounder matrix schema"
        ),
        "state": _string(matrix.get("state"), label="D2 confounder matrix state"),
        "failed_cell_ids": [
            _string(cell_id, label="D2 failed confounder cell id")
            for cell_id in _sequence(
                matrix.get("failed_cell_ids"), label="D2 failed confounder cell ids"
            )
        ],
        "field_graph_ids": [
            _string(graph_id, label="D2 confounder field graph id")
            for graph_id in _sequence(
                matrix.get("field_graph_ids"), label="D2 confounder field graph ids"
            )
        ],
        "policy_fingerprint_sha256": _string(
            matrix.get("policy_fingerprint_sha256"),
            label="D2 confounder matrix policy fingerprint",
        ),
        "selection_seed_consumed": _boolean(
            matrix.get("selection_seed_consumed"),
            label="D2 confounder selection_seed_consumed",
        ),
        "oracle_scoring_used": _boolean(
            matrix.get("oracle_scoring_used"),
            label="D2 confounder oracle_scoring_used",
        ),
        "joint_loop_registry_consumed": _boolean(
            matrix.get("joint_loop_registry_consumed"),
            label="D2 confounder joint_loop_registry_consumed",
        ),
    }
    return rows, metadata


def _core_outputs(result: Mapping[str, object]) -> list[records.D7V1DescriptiveOutput]:
    primary_units = [
        _mapping(item, label="core primary unit")
        for item in _sequence(
            result.get("core_primary_units"), label="core primary units"
        )
    ]
    bundle = _mapping(result.get("evidence_bundle"), label="evidence bundle")
    core_receipts = [
        _mapping(item, label="core cell receipt")
        for item in _sequence(
            bundle.get("core_cell_receipts"), label="core cell receipts"
        )
    ]
    core_cells = [
        _mapping(item, label="core cell")
        for item in _sequence(result.get("core_cells"), label="core cells")
    ]
    matrix, repeat_rows = _collapse_core_boundary_repeats(
        primary_units, core_cells, core_receipts
    )
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
    confounder_rows, confounder_metadata = _d2_confounder_observation_rows(bundle)

    return [
        _output(
            "core-no-core-abstain-matrix",
            {
                "rows": matrix,
                "nested_graph_row_count": sum(len(row["graph_rows"]) for row in matrix),
                "expected_disposition_counts": dict(
                    sorted(
                        Counter(row["expected_disposition"] for row in matrix).items()
                    )
                ),
                "prediction_class_counts": dict(
                    sorted(Counter(row["prediction_class"] for row in matrix).items())
                ),
                "attempt_status_counts": dict(
                    sorted(Counter(row["attempt_status"] for row in matrix).items())
                ),
            },
        ),
        _output(
            "boundary-repeat-exact-agreement",
            {
                "rows": repeat_rows,
                "comparison_scope": (
                    "declared-outcomes-and-blind-array-descriptors-not-byte-or-"
                    "graph-identity"
                ),
                "all_declared_outcomes_equal": all(
                    row["declared_outcomes_equal"] is True for row in repeat_rows
                ),
                "all_blind_array_descriptors_equal": all(
                    all(row["blind_array_descriptor_equalities"].values())
                    for row in repeat_rows
                ),
                "blind_array_descriptor_fields": list(_CORE_BLIND_DESCRIPTOR_FIELDS),
                "boundary_specific_identity_fields_expected_to_differ": list(
                    _CORE_BOUNDARY_IDENTITY_FIELDS
                ),
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
                "confounder_observation_rows": confounder_rows,
                "confounder_observation_row_count": len(confounder_rows),
                "confounder_matrix_metadata": confounder_metadata,
                "confounder_rows_are_not_main_d2_scientific_units": True,
                "confounder_rows_do_not_cure_main_d2_absence": True,
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


def _d3_family_aggregates(
    result: Mapping[str, object],
) -> tuple[
    list[dict[str, object]],
    dict[str, object],
    list[dict[str, object]],
    list[dict[str, object]],
    dict[str, object],
]:
    bundle = _mapping(result.get("evidence_bundle"), label="evidence bundle")
    wanted = {
        "cartesian-gauge-pipeline-rerun-verified",
        "representation-gauge-pipeline-rerun-verified",
    }
    families: dict[str, dict[str, object]] = {}
    for item in _sequence(
        bundle.get("static_runtime_receipts"), label="static runtime receipts"
    ):
        family = _mapping(item, label="static runtime receipt")
        evidence_id = _string(family.get("evidence_id"), label="evidence_id")
        if evidence_id not in wanted:
            continue
        if evidence_id in families:
            raise QualificationContractError("D3 family receipt is duplicated")
        families[evidence_id] = family
    if set(families) != wanted:
        raise QualificationContractError("D3 aggregate family receipts are incomplete")

    cartesian = _mapping(
        families["cartesian-gauge-pipeline-rerun-verified"].get(
            "aggregate_runtime_receipt"
        ),
        label="Cartesian D3 aggregate",
    )
    cartesian_checks = [
        _mapping(item, label="Cartesian D3 pipeline check")
        for item in _sequence(cartesian.get("checks"), label="Cartesian D3 checks")
    ]
    if (
        tuple(
            _string(item.get("law"), label="Cartesian D3 law")
            for item in cartesian_checks
        )
        != _CARTESIAN_D3_LAWS
    ):
        raise QualificationContractError(
            "Cartesian D3 checks differ from the exact four-law sequence"
        )
    for item, expected_sign in zip(cartesian_checks, (1, 1, -1, -1), strict=True):
        tolerance = _number(item.get("tolerance"), label="Cartesian D3 tolerance")
        errors = (
            _number(item.get(field), label=f"Cartesian D3 {field}")
            for field in (
                "maximum_distance_error",
                "maximum_field_law_error",
                "maximum_loop_law_error",
            )
        )
        if (
            item.get("state") != "pass"
            or item.get("pipeline_rerun_verified") is not True
            or item.get("claim_relevant_field_law_verified") is not True
            or item.get("continuous_loop_law_verified") is not True
            or item.get("sampled_continuous_observable_only") is not True
            or item.get("integer_output_present") is not False
            or item.get("topology_claimed") is not False
            or item.get("expected_loop_orientation_sign") != expected_sign
            or tolerance <= 0.0
            or any(error < 0.0 or error > tolerance for error in errors)
        ):
            raise QualificationContractError(
                "Cartesian D3 pipeline check boundary differs"
            )

    representation = _mapping(
        families["representation-gauge-pipeline-rerun-verified"].get(
            "aggregate_runtime_receipt"
        ),
        label="representation D3 aggregate",
    )
    if (
        representation.get("schema_version")
        != "spirallens.representation-pipeline-metamorphic-receipt.v0.3"
        or representation.get("verified") is not True
        or representation.get("pipeline_rerun_verified") is not True
        or representation.get("signed_loop_law_verified") is not True
        or representation.get("selection_seed_accessed") is not False
        or representation.get("integer_output_present") is not False
        or representation.get("topology_claimed") is not False
    ):
        raise QualificationContractError("representation D3 aggregate boundary differs")
    tolerance = _number(
        representation.get("tolerance"), label="representation D3 tolerance"
    )
    if tolerance <= 0.0:
        raise QualificationContractError("representation D3 tolerance is not positive")

    algebraic_checks = [
        _mapping(item, label="representation D3 algebraic check")
        for item in _sequence(
            representation.get("all_algebraic_checks"),
            label="representation D3 algebraic checks",
        )
    ]
    ambient_algebraic = [
        item
        for item in algebraic_checks
        if item.get("law") == "ambient_signed_permutation"
    ]
    if len(algebraic_checks) != 7 or len(ambient_algebraic) != 1:
        raise QualificationContractError(
            "representation D3 algebraic surface differs from the closed set"
        )
    if (
        ambient_algebraic[0].get("state") != "pass"
        or ambient_algebraic[0].get("composition_verified") is not True
        or ambient_algebraic[0].get("inverse_verified") is not True
        or ambient_algebraic[0].get("nonidentity_verified") is not True
    ):
        raise QualificationContractError(
            "representation ambient algebraic check is not verified"
        )

    pipeline_checks = [
        _mapping(item, label="representation D3 pipeline check")
        for item in _sequence(
            representation.get("pipeline_checks"),
            label="representation D3 pipeline checks",
        )
    ]
    if (
        tuple(
            _string(item.get("field_graph_id"), label="D3 field_graph_id")
            for item in pipeline_checks
        )
        != _REPRESENTATION_D3_FIELD_GRAPH_IDS
    ):
        raise QualificationContractError(
            "representation D3 pipeline checks differ from the three A graphs"
        )
    for item in pipeline_checks:
        field_graph_id = _string(item.get("field_graph_id"), label="D3 field_graph_id")
        errors = _mapping(item.get("errors"), label="D3 pipeline errors")
        if set(errors) != {
            "alignment_determinant_unit",
            "alignment_orthogonality",
            "ambient_equivariance",
            "amplitude",
            "coherence",
            "identifiability",
            "section_gauge_alignment",
        }:
            raise QualificationContractError(
                "representation D3 pipeline error fields differ"
            )
        for field, value in errors.items():
            error = _number(value, label=f"D3 pipeline error {field}")
            if error < 0.0 or error > tolerance:
                raise QualificationContractError(
                    "representation D3 pipeline error exceeds its tolerance"
                )
        crossed = [
            _mapping(value, label="representation D3 crossed loop")
            for value in _sequence(
                item.get("crossed_loop_checks"), label="D3 crossed loop checks"
            )
        ]
        if tuple(
            _string(value.get("cycle_graph_id"), label="D3 cycle_graph_id")
            for value in crossed
        ) != _REPRESENTATION_D3_CYCLE_GRAPH_IDS or any(
            value.get("field_graph_id") != field_graph_id
            or value.get("law") != "ambient_o2_alignment"
            or value.get("verified") is not True
            for value in crossed
        ):
            raise QualificationContractError(
                "representation D3 crossed-loop surface differs"
            )
        if (
            item.get("verified") is not True
            or item.get("alignment_determinant") != -1.0
            or item.get("adjacency_equal") is not True
            or item.get("edge_distances_bit_identical") is not True
            or item.get("support_equal") is not True
            or any(
                _number(
                    value.get("signed_total_error_cycles"),
                    label="D3 crossed-loop signed-total error",
                )
                > tolerance
                for value in crossed
            )
        ):
            raise QualificationContractError(
                "representation D3 pipeline verification differs"
            )

    loop_variants = [
        _mapping(item, label="representation D3 loop variant")
        for item in _sequence(
            representation.get("loop_variant_checks"),
            label="representation D3 loop variants",
        )
    ]
    expected_variants = tuple(
        (field_graph_id, cycle_graph_id, law)
        for field_graph_id in _REPRESENTATION_D3_FIELD_GRAPH_IDS
        for cycle_graph_id in _REPRESENTATION_D3_CYCLE_GRAPH_IDS
        for law in _REPRESENTATION_D3_LOOP_LAWS
    )
    observed_variants = tuple(
        (
            _string(item.get("field_graph_id"), label="D3 variant field graph"),
            _string(item.get("cycle_graph_id"), label="D3 variant cycle graph"),
            _string(item.get("law"), label="D3 variant law"),
        )
        for item in loop_variants
    )
    expected_signs = {
        "reference_rotation": 1.0,
        "reference_reflection": -1.0,
        "loop_reversal": -1.0,
    }
    if observed_variants != expected_variants or any(
        item.get("verified") is not True
        or item.get("oracle_read") is not False
        or item.get("selection_seed_accessed") is not False
        or item.get("sampled_continuous_observable_only") is not True
        or item.get("integer_output_present") is not False
        or item.get("topology_claimed") is not False
        or item.get("orientation_determinant") != expected_signs[item["law"]]
        or not (
            0.0
            <= _number(
                item.get("signed_total_error_cycles"),
                label="D3 variant signed-total error",
            )
            <= tolerance
        )
        for item in loop_variants
    ):
        raise QualificationContractError(
            "representation D3 loop variants differ from the closed A by B laws"
        )
    return (
        cartesian_checks,
        ambient_algebraic[0],
        pipeline_checks,
        loop_variants,
        representation,
    )


def _cartesian_d3_row(check: Mapping[str, object]) -> dict[str, object]:
    law = _string(check.get("law"), label="Cartesian D3 law")
    return {
        "row_id": law.replace("_", "-"),
        "family_evidence_id": "cartesian-gauge-pipeline-rerun-verified",
        "law": law,
        "source_check_count": 1,
        "structural_checks": {
            "all_graph_adjacencies_verified": _boolean(
                check.get("all_graph_adjacencies_verified"),
                label="Cartesian D3 adjacency verification",
            ),
            "all_graph_edge_distances_bit_identical": _boolean(
                check.get("all_graph_edge_distances_bit_identical"),
                label="Cartesian D3 edge-distance verification",
            ),
            "maximum_distance_error": _number(
                check.get("maximum_distance_error"),
                label="Cartesian D3 distance error",
            ),
        },
        "alignment_errors": {},
        "observable_law_errors": {
            "maximum_field_law_error": _number(
                check.get("maximum_field_law_error"),
                label="Cartesian D3 field-law error",
            ),
            "maximum_loop_law_error": _number(
                check.get("maximum_loop_law_error"),
                label="Cartesian D3 loop-law error",
            ),
        },
        "determinant_or_sign": _integer(
            check.get("expected_loop_orientation_sign"),
            label="Cartesian D3 orientation sign",
        ),
        "tolerance": _number(check.get("tolerance"), label="Cartesian D3 tolerance"),
        "state": check["state"],
        "verified": True,
    }


def _representation_d3_row(
    check: Mapping[str, object],
    *,
    tolerance: float,
) -> dict[str, object]:
    errors = _mapping(check.get("errors"), label="D3 pipeline errors")
    crossed = [
        _mapping(item, label="D3 crossed-loop check")
        for item in _sequence(
            check.get("crossed_loop_checks"), label="D3 crossed-loop checks"
        )
    ]
    return {
        "row_id": check["field_graph_id"],
        "family_evidence_id": "representation-gauge-pipeline-rerun-verified",
        "law": "ambient_o2_alignment",
        "source_check_count": len(crossed),
        "cycle_graph_ids": [item["cycle_graph_id"] for item in crossed],
        "structural_checks": {
            "adjacency_equal": check["adjacency_equal"],
            "edge_distances_bit_identical": check["edge_distances_bit_identical"],
            "support_equal": check["support_equal"],
        },
        "alignment_errors": {
            "alignment_determinant_unit": _number(
                errors.get("alignment_determinant_unit"),
                label="D3 alignment determinant error",
            ),
            "alignment_orthogonality": _number(
                errors.get("alignment_orthogonality"),
                label="D3 alignment orthogonality error",
            ),
        },
        "observable_law_errors": {
            "ambient_equivariance": _number(
                errors.get("ambient_equivariance"),
                label="D3 ambient equivariance error",
            ),
            "amplitude": _number(errors.get("amplitude"), label="D3 amplitude error"),
            "coherence": _number(errors.get("coherence"), label="D3 coherence error"),
            "identifiability": _number(
                errors.get("identifiability"), label="D3 identifiability error"
            ),
            "section_gauge_alignment": _number(
                errors.get("section_gauge_alignment"),
                label="D3 section-gauge error",
            ),
            "maximum_crossed_loop_signed_total_error_cycles": max(
                _number(
                    item.get("signed_total_error_cycles"),
                    label="D3 crossed-loop signed-total error",
                )
                for item in crossed
            ),
        },
        "determinant_or_sign": _number(
            check.get("alignment_determinant"),
            label="D3 alignment determinant",
        ),
        "tolerance": tolerance,
        "state": "pass",
        "verified": True,
    }


def _d3_outputs(
    result: Mapping[str, object],
) -> list[records.D7V1DescriptiveOutput]:
    (
        cartesian_checks,
        representation_ambient,
        representation_pipelines,
        representation_variants,
        representation_aggregate,
    ) = _d3_family_aggregates(result)
    cartesian_by_law = {str(item["law"]): item for item in cartesian_checks}
    representation_tolerance = _number(
        representation_aggregate.get("tolerance"),
        label="representation D3 tolerance",
    )

    cartesian_ambient = cartesian_by_law["ambient_signed_permutation"]
    pipeline_ambient_maximum = max(
        _number(
            _mapping(item.get("errors"), label="D3 pipeline errors").get(
                "ambient_equivariance"
            ),
            label="D3 ambient equivariance error",
        )
        for item in representation_pipelines
    )
    ambient_rows = [
        {
            "family_evidence_id": "cartesian-gauge-pipeline-rerun-verified",
            "law": "ambient_signed_permutation",
            "source_check_count": 1,
            "maximum_distance_error": _number(
                cartesian_ambient.get("maximum_distance_error"),
                label="Cartesian ambient distance error",
            ),
            "maximum_field_law_error": _number(
                cartesian_ambient.get("maximum_field_law_error"),
                label="Cartesian ambient field error",
            ),
            "maximum_loop_law_error": _number(
                cartesian_ambient.get("maximum_loop_law_error"),
                label="Cartesian ambient loop error",
            ),
            "observed_error": None,
            "pipeline_ambient_equivariance_max": None,
            "tolerance": _number(
                cartesian_ambient.get("tolerance"),
                label="Cartesian ambient tolerance",
            ),
            "state": "pass",
            "verified": True,
        },
        {
            "family_evidence_id": "representation-gauge-pipeline-rerun-verified",
            "law": "ambient_signed_permutation",
            "source_check_count": 1 + len(representation_pipelines),
            "maximum_distance_error": None,
            "maximum_field_law_error": None,
            "maximum_loop_law_error": None,
            "observed_error": _number(
                representation_ambient.get("observed_error"),
                label="representation ambient algebraic error",
            ),
            "pipeline_ambient_equivariance_max": pipeline_ambient_maximum,
            "tolerance": representation_tolerance,
            "state": "pass",
            "verified": True,
        },
    ]

    reference_rows: list[dict[str, object]] = []
    for law, sign in (("reference_rotation", 1), ("reference_reflection", -1)):
        cartesian = cartesian_by_law[law]
        reference_rows.append(
            {
                "family_evidence_id": "cartesian-gauge-pipeline-rerun-verified",
                "law": law,
                "source_check_count": 1,
                "expected_orientation_sign": sign,
                "maximum_field_law_error": _number(
                    cartesian.get("maximum_field_law_error"),
                    label="Cartesian reference field error",
                ),
                "maximum_loop_or_signed_total_error": _number(
                    cartesian.get("maximum_loop_law_error"),
                    label="Cartesian reference loop error",
                ),
                "tolerance": _number(
                    cartesian.get("tolerance"),
                    label="Cartesian reference tolerance",
                ),
                "all_verified": True,
            }
        )
    for law, sign in (("reference_rotation", 1), ("reference_reflection", -1)):
        variants = [item for item in representation_variants if item["law"] == law]
        reference_rows.append(
            {
                "family_evidence_id": "representation-gauge-pipeline-rerun-verified",
                "law": law,
                "source_check_count": len(variants),
                "field_cycle_pairs": [
                    [item["field_graph_id"], item["cycle_graph_id"]]
                    for item in variants
                ],
                "expected_orientation_sign": sign,
                "maximum_field_law_error": None,
                "maximum_loop_or_signed_total_error": max(
                    _number(
                        item.get("signed_total_error_cycles"),
                        label="representation reference signed-total error",
                    )
                    for item in variants
                ),
                "tolerance": representation_tolerance,
                "all_verified": True,
            }
        )

    cartesian_reversal = cartesian_by_law["loop_reversal"]
    representation_reversal = [
        item for item in representation_variants if item["law"] == "loop_reversal"
    ]
    reversal_rows = [
        {
            "family_evidence_id": "cartesian-gauge-pipeline-rerun-verified",
            "law": "loop_reversal",
            "source_check_count": 1,
            "expected_orientation_sign": -1,
            "maximum_field_law_error": _number(
                cartesian_reversal.get("maximum_field_law_error"),
                label="Cartesian reversal field error",
            ),
            "maximum_loop_or_signed_total_error": _number(
                cartesian_reversal.get("maximum_loop_law_error"),
                label="Cartesian reversal loop error",
            ),
            "tolerance": _number(
                cartesian_reversal.get("tolerance"),
                label="Cartesian reversal tolerance",
            ),
            "all_verified": True,
        },
        {
            "family_evidence_id": "representation-gauge-pipeline-rerun-verified",
            "law": "loop_reversal",
            "source_check_count": len(representation_reversal),
            "field_cycle_pairs": [
                [item["field_graph_id"], item["cycle_graph_id"]]
                for item in representation_reversal
            ],
            "expected_orientation_sign": -1,
            "maximum_field_law_error": None,
            "maximum_loop_or_signed_total_error": max(
                _number(
                    item.get("signed_total_error_cycles"),
                    label="representation reversal signed-total error",
                )
                for item in representation_reversal
            ),
            "tolerance": representation_tolerance,
            "all_verified": True,
        },
    ]

    separated_rows = [_cartesian_d3_row(item) for item in cartesian_checks] + [
        _representation_d3_row(item, tolerance=representation_tolerance)
        for item in representation_pipelines
    ]
    cartesian_separated = [
        row
        for row in separated_rows
        if row["family_evidence_id"] == "cartesian-gauge-pipeline-rerun-verified"
    ]
    representation_separated = [
        row
        for row in separated_rows
        if row["family_evidence_id"] == "representation-gauge-pipeline-rerun-verified"
    ]
    cartesian_array_or_field_maximum = max(
        max(
            float(row["structural_checks"]["maximum_distance_error"]),
            float(row["observable_law_errors"]["maximum_field_law_error"]),
        )
        for row in cartesian_separated
    )
    representation_array_or_field_maximum = max(
        max(
            [float(value) for value in row["alignment_errors"].values()]
            + [
                float(value)
                for key, value in row["observable_law_errors"].items()
                if key != "maximum_crossed_loop_signed_total_error_cycles"
            ]
        )
        for row in representation_separated
    )
    return [
        _output(
            "ambient-basis-error",
            {
                "rows": ambient_rows,
                "evaluation_unit": "d3-matched-class-unit",
                "matched_class_unit_count": 2,
                "family_row_count": len(ambient_rows),
                "maximum_pipeline_ambient_equivariance_error": (
                    pipeline_ambient_maximum
                ),
                "algebraic_and_pipeline_errors_kept_distinct": True,
                "diagnostic_rows_are_independent_scientific_observations": False,
                "integer_output_present": False,
                "topology_claimed": False,
            },
        ),
        _output(
            "reference-o2-error",
            {
                "rows": reference_rows,
                "evaluation_unit": "d3-matched-class-unit",
                "matched_class_unit_count": 2,
                "law_groups": ["reference_rotation", "reference_reflection"],
                "maximum_observed_field_error": max(
                    float(row["maximum_field_law_error"])
                    for row in reference_rows
                    if row["maximum_field_law_error"] is not None
                ),
                "maximum_observed_loop_or_signed_total_error": max(
                    float(row["maximum_loop_or_signed_total_error"])
                    for row in reference_rows
                ),
                "orientation_preserving_and_reversing_laws_kept_distinct": True,
                "diagnostic_rows_are_independent_scientific_observations": False,
                "integer_output_present": False,
                "topology_claimed": False,
            },
        ),
        _output(
            "loop-reversal-signed-total-error",
            {
                "rows": reversal_rows,
                "evaluation_unit": "d3-matched-class-unit",
                "matched_class_unit_count": 2,
                "maximum_observed_error_cycles": max(
                    float(row["maximum_loop_or_signed_total_error"])
                    for row in reversal_rows
                ),
                "integer_output_used": False,
                "continuous_sampled_total_only": True,
                "diagnostic_rows_are_independent_scientific_observations": False,
                "integer_output_present": False,
                "topology_claimed": False,
            },
        ),
        _output(
            "array-versus-observable-law-separation",
            {
                "rows": separated_rows,
                "evaluation_unit": "d3-matched-class-unit",
                "matched_class_unit_count": 2,
                "cartesian_pipeline_row_count": len(cartesian_checks),
                "representation_pipeline_row_count": len(representation_pipelines),
                "representation_crossed_loop_cell_count": sum(
                    int(row["source_check_count"])
                    for row in separated_rows
                    if row["family_evidence_id"]
                    == "representation-gauge-pipeline-rerun-verified"
                ),
                "family_maximum_errors": {
                    "cartesian_array_or_field": cartesian_array_or_field_maximum,
                    "cartesian_sampled_loop": max(
                        float(row["observable_law_errors"]["maximum_loop_law_error"])
                        for row in cartesian_separated
                    ),
                    "representation_array_or_field": (
                        representation_array_or_field_maximum
                    ),
                    "representation_sampled_loop": max(
                        float(
                            row["observable_law_errors"][
                                "maximum_crossed_loop_signed_total_error_cycles"
                            ]
                        )
                        for row in representation_separated
                    ),
                },
                "array_field_and_sampled_loop_surfaces_collapsed": False,
                "diagnostic_rows_are_independent_scientific_observations": False,
                "integer_output_present": False,
                "topology_claimed": False,
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
        "cell_ids": sorted(
            _string(item.get("cell_id"), label="crossed cell_id") for item in members
        ),
        "unique_execution_count": len(
            {
                _string(item.get("primary_unit_id"), label="primary_unit_id")
                for item in members
            }
        ),
        "evaluable_cell_count": sum(
            item["attempt_status"] == "evaluable" for item in members
        ),
        "prerequisite_cell_count": sum(
            item["attempt_status"] == "insufficient" for item in members
        ),
        "minimum_continuous_signed_total_cycles": min(totals) if totals else None,
        "maximum_continuous_signed_total_cycles": max(totals) if totals else None,
        "maximum_oracle_absolute_error_cycles": max(errors) if errors else None,
    }


def _d4_optional_number(value: object, *, label: str) -> float | None:
    return None if value is None else _number(value, label=label)


def _d4_string_fields(
    source: Mapping[str, object], fields: Sequence[str]
) -> dict[str, str]:
    return {field: _string(source.get(field), label=f"D4 {field}") for field in fields}


def _d4_string_list(value: object, *, label: str) -> list[str]:
    return [_string(item, label=label) for item in _sequence(value, label=f"{label}s")]


def _d4_index(value: object, *, key: str, label: str) -> dict[str, dict[str, object]]:
    result = {}
    for item in _sequence(value, label=label):
        row = _mapping(item, label=label.removesuffix("s"))
        identity = _string(row.get(key), label=f"{label} {key}")
        if identity in result:
            raise QualificationContractError(f"{label} contains duplicate {key}")
        result[identity] = row
    return result


def _d4_stress_assignments(unit: Mapping[str, object]) -> list[dict[str, str]]:
    rows = []
    for item in _sequence(unit.get("stress_assignments"), label="stress assignments"):
        assignment = _mapping(item, label="stress assignment")
        rows.append(
            {
                "axis_id": _string(assignment.get("axis_id"), label="stress axis_id"),
                "level": _string(assignment.get("level"), label="stress level"),
            }
        )
    if len(rows) != 3 or len({row["axis_id"] for row in rows}) != 3:
        raise QualificationContractError(
            "each D4 execution must retain three distinct stress assignments"
        )
    return rows


def _d4_unit_fields(unit: Mapping[str, object]) -> dict[str, object]:
    return {
        **_d4_string_fields(unit, ("primary_unit_id", "control_id")),
        "selection_seed": _integer(unit.get("selection_seed"), label="selection_seed"),
        "stress_assignments": _d4_stress_assignments(unit),
    }


def _d4_descriptor(value: object, *, label: str) -> dict[str, object]:
    descriptor = _mapping(value, label=label)
    if set(descriptor) != {"dtype", "shape", "sha256"}:
        raise QualificationContractError(f"{label} descriptor fields differ")
    shape = [
        _integer(item, label=f"{label} shape")
        for item in _sequence(descriptor.get("shape"), label=f"{label} shape")
    ]
    if not shape or any(dimension <= 0 for dimension in shape):
        raise QualificationContractError(f"{label} shape must be positive")
    return {
        "dtype": _string(descriptor.get("dtype"), label=f"{label} dtype"),
        "shape": shape,
        "sha256": _string(descriptor.get("sha256"), label=f"{label} sha256"),
    }


def _d4_pair_class(field_graph_id: str, cycle_graph_id: str) -> str:
    return (
        "diagonal"
        if field_graph_id.removeprefix("a-") == cycle_graph_id.removeprefix("b-")
        else "offdiagonal"
    )


def _d4_cell_row(cell: Mapping[str, object]) -> dict[str, object]:
    field_graph_id = _string(cell.get("field_graph_id"), label="field_graph_id")
    cycle_graph_id = _string(cell.get("cycle_graph_id"), label="cycle_graph_id")
    return {
        **_d4_string_fields(
            cell,
            (
                "cell_id",
                "field_graph_id",
                "cycle_graph_id",
                "attempt_status",
                "expected_disposition",
                "prediction_class",
                "state",
            ),
        ),
        "pair_class": _d4_pair_class(field_graph_id, cycle_graph_id),
        "continuous_signed_total_cycles": _d4_optional_number(
            cell.get("continuous_signed_total_cycles"), label="crossed signed total"
        ),
        "oracle_absolute_error_cycles": _d4_optional_number(
            cell.get("oracle_absolute_error_cycles"), label="crossed oracle error"
        ),
    }


def _d4_index_inputs(
    result: Mapping[str, object],
) -> tuple[
    dict[str, dict[str, object]],
    dict[str, list[dict[str, object]]],
    dict[str, dict[str, object]],
    dict[str, dict[str, object]],
]:
    field_graph_ids = ("a-mutual", "a-radius", "a-shared")
    cycle_graph_ids = ("b-mutual", "b-radius", "b-shared")
    loop_roles = ("offcore_control", "primary_boundary")
    expected_coordinates = {
        (field_graph_id, cycle_graph_id, loop_role)
        for field_graph_id in field_graph_ids
        for cycle_graph_id in cycle_graph_ids
        for loop_role in loop_roles
    }

    units = _d4_index(
        result.get("primary_units"), key="primary_unit_id", label="primary units"
    )
    for unit in units.values():
        _d4_stress_assignments(unit)
    if len(units) != 64:
        raise QualificationContractError("D4 must retain exactly 64 executions")
    if Counter(str(unit.get("attempt_status")) for unit in units.values()) != {
        "evaluable": 48,
        "insufficient": 16,
    } or any(unit.get("state") != "pass" for unit in units.values()):
        raise QualificationContractError(
            "D4 execution disposition counts differ from the frozen grain"
        )

    cells_by_id = _d4_index(
        result.get("crossed_cells"), key="cell_id", label="crossed cells"
    )
    cells_by_unit: dict[str, list[dict[str, object]]] = defaultdict(list)
    for cell in cells_by_id.values():
        primary_unit_id = _string(
            cell.get("primary_unit_id"), label="crossed primary_unit_id"
        )
        if primary_unit_id not in units:
            raise QualificationContractError("D4 crossed-cell identity is not closed")
        cells_by_unit[primary_unit_id].append(cell)
    if len(cells_by_id) != 1_152 or set(cells_by_unit) != set(units):
        raise QualificationContractError("D4 must retain exactly 1,152 crossed cells")
    for primary_unit_id, members in cells_by_unit.items():
        coordinates = {
            (
                _string(cell.get("field_graph_id"), label="field_graph_id"),
                _string(cell.get("cycle_graph_id"), label="cycle_graph_id"),
                _string(cell.get("loop_role"), label="loop_role"),
            )
            for cell in members
        }
        declared_ids = {
            _string(cell_id, label="declared crossed cell_id")
            for cell_id in _sequence(
                units[primary_unit_id].get("crossed_cell_ids"),
                label="declared crossed cell ids",
            )
        }
        if (
            len(members) != 18
            or coordinates != expected_coordinates
            or declared_ids != {str(cell["cell_id"]) for cell in members}
        ):
            raise QualificationContractError(
                "each D4 execution must retain the exact 3x3x2 crossed leaf set"
            )

    bundle = _mapping(result.get("evidence_bundle"), label="evidence bundle")
    loop_evidence = _d4_index(
        bundle.get("loop_cell_receipts"),
        key="cell_id",
        label="loop cell receipts",
    )
    if set(loop_evidence) != set(cells_by_id):
        raise QualificationContractError("D4 loop evidence does not cover every leaf")
    for cell_id, evidence in loop_evidence.items():
        cell = cells_by_id[cell_id]
        normalized_sha256 = _string(
            evidence.get("normalized_summary_sha256"),
            label="loop normalized summary sha256",
        )
        if sha256_bytes(canonical_json_bytes(cell)) != normalized_sha256:
            raise QualificationContractError(
                "D4 loop normalized summary digest differs"
            )
        for receipt_key, fingerprint_key in (
            ("blind_input_receipt", "blind_input_fingerprint_sha256"),
            ("sealed_prediction_receipt", "prediction_fingerprint_sha256"),
            ("oracle_truth_receipt", "oracle_fingerprint_sha256"),
        ):
            receipt = _mapping(evidence.get(receipt_key), label=receipt_key)
            if sha256_bytes(canonical_json_bytes(receipt)) != cell.get(fingerprint_key):
                raise QualificationContractError(
                    f"D4 {receipt_key} fingerprint join differs"
                )
    nonvacuity = _d4_index(
        result.get("crossed_nonvacuity"),
        key="primary_unit_id",
        label="crossed nonvacuity rows",
    )
    nonvacuity_evidence = _d4_index(
        bundle.get("nonvacuity_receipts"),
        key="primary_unit_id",
        label="nonvacuity receipts",
    )
    if set(nonvacuity) != set(units) or set(nonvacuity_evidence) != set(units):
        raise QualificationContractError(
            "D4 nonvacuity receipts must cover all 64 executions"
        )
    for primary_unit_id, evidence in nonvacuity_evidence.items():
        summary = nonvacuity[primary_unit_id]
        receipt = _mapping(
            evidence.get("crossed_nonvacuity_receipt"),
            label="crossed nonvacuity receipt",
        )
        if (
            sha256_bytes(canonical_json_bytes(summary))
            != evidence.get("normalized_summary_sha256")
            or sha256_bytes(canonical_json_bytes(receipt))
            != summary.get("receipt_fingerprint_sha256")
            or receipt.get("field_graph_pair_effects")
            != summary.get("field_graph_pair_effects")
        ):
            raise QualificationContractError("D4 nonvacuity receipt join differs")
    return units, cells_by_unit, loop_evidence, nonvacuity_evidence


def _d4_outputs(result: Mapping[str, object]) -> list[records.D7V1DescriptiveOutput]:
    (
        units,
        cells_by_unit,
        loop_evidence,
        nonvacuity_evidence,
    ) = _d4_index_inputs(result)
    all_cells = [cell for members in cells_by_unit.values() for cell in members]
    field_graph_ids = ("a-mutual", "a-radius", "a-shared")
    cycle_graph_ids = ("b-mutual", "b-radius", "b-shared")
    loop_roles = ("offcore_control", "primary_boundary")

    matrix_rows = []
    role_rows = []
    for primary_unit_id, unit in sorted(units.items()):
        unit_fields = _d4_unit_fields(unit)
        members = cells_by_unit[primary_unit_id]
        for loop_role in loop_roles:
            role_members = sorted(
                (cell for cell in members if cell.get("loop_role") == loop_role),
                key=lambda cell: (
                    str(cell["field_graph_id"]),
                    str(cell["cycle_graph_id"]),
                ),
            )
            matrix_rows.append(
                {
                    **unit_fields,
                    "loop_role": loop_role,
                    "field_graph_ids": list(field_graph_ids),
                    "cycle_graph_ids": list(cycle_graph_ids),
                    "cells": [_d4_cell_row(cell) for cell in role_members],
                }
            )
            summary = _crossed_summary(role_members)
            maximum_error = summary["maximum_oracle_absolute_error_cycles"]
            role_rows.append(
                {
                    **unit_fields,
                    "loop_role": loop_role,
                    "cell_count": summary["cell_count"],
                    "cell_ids": summary["cell_ids"],
                    "evaluable_cell_count": summary["evaluable_cell_count"],
                    "prerequisite_cell_count": summary["prerequisite_cell_count"],
                    "continuous_total_min_cycles": (
                        summary["minimum_continuous_signed_total_cycles"]
                    ),
                    "continuous_total_max_cycles": (
                        summary["maximum_continuous_signed_total_cycles"]
                    ),
                    "continuous_total_span_cycles": (
                        None
                        if summary["minimum_continuous_signed_total_cycles"] is None
                        else float(summary["maximum_continuous_signed_total_cycles"])
                        - float(summary["minimum_continuous_signed_total_cycles"])
                    ),
                    "maximum_oracle_absolute_error_cycles": maximum_error,
                    "worst_oracle_cell_ids": sorted(
                        str(cell["cell_id"])
                        for cell in role_members
                        if maximum_error is not None
                        and cell.get("oracle_absolute_error_cycles") == maximum_error
                    ),
                    "abstention_reason_codes": sorted(
                        {
                            _string(reason, label="sealed prediction reason code")
                            for cell in role_members
                            for reason in _sequence(
                                _mapping(
                                    loop_evidence[str(cell["cell_id"])].get(
                                        "sealed_prediction_receipt"
                                    ),
                                    label="sealed loop prediction receipt",
                                ).get("reason_codes"),
                                label="sealed prediction reason codes",
                            )
                        }
                    ),
                }
            )

    diagonal_groups: dict[tuple[str, str], list[Mapping[str, object]]] = defaultdict(
        list
    )
    for cell in all_cells:
        field_graph_id = _string(cell.get("field_graph_id"), label="field_graph_id")
        cycle_graph_id = _string(cell.get("cycle_graph_id"), label="cycle_graph_id")
        diagonal_groups[
            (
                _string(cell.get("loop_role"), label="loop_role"),
                _d4_pair_class(field_graph_id, cycle_graph_id),
            )
        ].append(cell)
    diagonal_rows = []
    for (loop_role, pair_class), members in sorted(diagonal_groups.items()):
        summary = _crossed_summary(members)
        diagonal_rows.append(
            {
                "loop_role": loop_role,
                "pair_class": pair_class,
                "cell_count": summary["cell_count"],
                "unique_execution_count": summary["unique_execution_count"],
                "evaluable_cell_count": summary["evaluable_cell_count"],
                "prerequisite_cell_count": summary["prerequisite_cell_count"],
                "graph_cells_are_repeated_measures": True,
            }
        )

    adjacency_rows = []
    component_row_count = 0
    loop_contrast_row_count = 0
    component_rms_values: list[float] = []
    loop_contrast_values: list[float] = []
    expected_pair_ids = {
        "a-mutual--a-radius",
        "a-mutual--a-shared",
        "a-radius--a-shared",
    }
    for primary_unit_id, unit in sorted(units.items()):
        evidence = nonvacuity_evidence[primary_unit_id]
        receipt = _mapping(
            evidence.get("crossed_nonvacuity_receipt"),
            label="crossed nonvacuity receipt",
        )
        effects = [
            _mapping(item, label="field graph pair effect")
            for item in _sequence(
                receipt.get("field_graph_pair_effects"),
                label="field graph pair effects",
            )
        ]
        if {str(effect.get("pair_id")) for effect in effects} != expected_pair_ids:
            raise QualificationContractError(
                "each D4 nonvacuity receipt must retain three field-graph pairs"
            )
        cell_index = {
            (
                str(cell["field_graph_id"]),
                str(cell["cycle_graph_id"]),
                str(cell["loop_role"]),
            ): cell
            for cell in cells_by_unit[primary_unit_id]
        }
        for effect in sorted(effects, key=lambda item: str(item["pair_id"])):
            left_field_graph_id = _string(
                effect.get("left_field_graph_id"), label="left field graph id"
            )
            right_field_graph_id = _string(
                effect.get("right_field_graph_id"), label="right field graph id"
            )
            component_effects = [
                dict(_mapping(item, label="field component effect"))
                for item in _sequence(
                    effect.get("component_effects"), label="component effects"
                )
            ]
            if {
                str(component.get("component_name")) for component in component_effects
            } != {
                "amplitude",
                "identifiability_score",
                "section_values",
                "edge_coherence",
            } or len(component_effects) != 4:
                raise QualificationContractError(
                    "each D4 field-pair effect must retain four exact components"
                )
            component_row_count += len(component_effects)
            component_rms_values.extend(
                _number(component.get("rms_distance"), label="component RMS distance")
                for component in component_effects
            )
            loop_contrasts = []
            for loop_role in loop_roles:
                for cycle_graph_id in cycle_graph_ids:
                    left = cell_index[(left_field_graph_id, cycle_graph_id, loop_role)]
                    right = cell_index[
                        (right_field_graph_id, cycle_graph_id, loop_role)
                    ]
                    left_total = _d4_optional_number(
                        left.get("continuous_signed_total_cycles"),
                        label="left loop total",
                    )
                    right_total = _d4_optional_number(
                        right.get("continuous_signed_total_cycles"),
                        label="right loop total",
                    )
                    signed_difference = (
                        None
                        if left_total is None or right_total is None
                        else right_total - left_total
                    )
                    absolute_difference = (
                        None if signed_difference is None else abs(signed_difference)
                    )
                    if absolute_difference is not None:
                        loop_contrast_values.append(absolute_difference)
                    loop_contrasts.append(
                        {
                            "cycle_graph_id": cycle_graph_id,
                            "loop_role": loop_role,
                            "left_cell_id": _string(
                                left.get("cell_id"), label="left cell_id"
                            ),
                            "right_cell_id": _string(
                                right.get("cell_id"), label="right cell_id"
                            ),
                            "left_total_cycles": left_total,
                            "right_total_cycles": right_total,
                            "signed_difference_cycles": signed_difference,
                            "absolute_difference_cycles": absolute_difference,
                        }
                    )
            loop_contrast_row_count += len(loop_contrasts)
            adjacency_rows.append(
                {
                    **_d4_unit_fields(unit),
                    **_d4_string_fields(
                        effect,
                        (
                            "pair_id",
                            "left_field_graph_id",
                            "right_field_graph_id",
                            "left_field_graph_fingerprint_sha256",
                            "right_field_graph_fingerprint_sha256",
                        ),
                    ),
                    "field_adjacency_identity_differs": (
                        effect.get("left_field_graph_fingerprint_sha256")
                        != effect.get("right_field_graph_fingerprint_sha256")
                    ),
                    "numeric_adjacency_difference_available": False,
                    "component_effects": component_effects,
                    "qualifying_substantive_components": _d4_string_list(
                        effect.get("qualifying_substantive_components"),
                        label="qualifying substantive component",
                    ),
                    "substantive_response_pass": _boolean(
                        effect.get("substantive_response_pass"),
                        label="substantive response pass",
                    ),
                    "loop_contrasts": loop_contrasts,
                }
            )
    if (
        len(adjacency_rows) != 192
        or component_row_count != 768
        or loop_contrast_row_count != 1_152
    ):
        raise QualificationContractError(
            "D4 effects must retain 192 field pairs, 768 components, "
            "and 1,152 contrasts"
        )

    support_rows = []
    for primary_unit_id, unit in sorted(units.items()):
        unit_fields = _d4_unit_fields(unit)
        stratum_ids = [
            f"stress.{item['axis_id']}.{item['level']}"
            for item in unit_fields["stress_assignments"]
        ]
        for cell in sorted(
            cells_by_unit[primary_unit_id],
            key=lambda item: str(item["cell_id"]),
        ):
            cell_id = _string(cell.get("cell_id"), label="crossed cell_id")
            evidence = loop_evidence[cell_id]
            blind = _mapping(
                evidence.get("blind_input_receipt"), label="blind loop input receipt"
            )
            prediction = _mapping(
                evidence.get("sealed_prediction_receipt"),
                label="sealed loop prediction receipt",
            )
            oracle = _mapping(
                evidence.get("oracle_truth_receipt"), label="loop oracle truth receipt"
            )
            if (
                prediction.get("observed_attempt_status") != cell.get("attempt_status")
                or prediction.get("prediction_class") != cell.get("prediction_class")
                or oracle.get("expected_disposition")
                != cell.get("expected_disposition")
                or blind.get("field_graph_fingerprint_sha256")
                != cell.get("field_graph_fingerprint_sha256")
                or blind.get("cycle_graph_fingerprint_sha256")
                != cell.get("cycle_graph_fingerprint_sha256")
            ):
                raise QualificationContractError("D4 support-aware leaf join differs")
            field_graph_id = _string(cell.get("field_graph_id"), label="field_graph_id")
            cycle_graph_id = _string(cell.get("cycle_graph_id"), label="cycle_graph_id")
            row: dict[str, object] = {
                **unit_fields,
                **_d4_string_fields(
                    cell,
                    (
                        "cell_id",
                        "field_graph_id",
                        "cycle_graph_id",
                        "loop_role",
                        "attempt_status",
                        "expected_disposition",
                        "prediction_class",
                        "state",
                        "field_graph_fingerprint_sha256",
                        "cycle_graph_fingerprint_sha256",
                        "field_estimate_fingerprint_sha256",
                        "representative_content_sha256",
                        "prediction_fingerprint_sha256",
                        "oracle_fingerprint_sha256",
                    ),
                ),
                "stratum_ids": stratum_ids,
                "pair_class": _d4_pair_class(field_graph_id, cycle_graph_id),
                "continuous_signed_total_cycles": _d4_optional_number(
                    cell.get("continuous_signed_total_cycles"),
                    label="continuous signed total",
                ),
                "oracle_absolute_error_cycles": _d4_optional_number(
                    cell.get("oracle_absolute_error_cycles"),
                    label="oracle absolute error",
                ),
                "sealed_prediction_reason_codes": _d4_string_list(
                    prediction.get("reason_codes"),
                    label="sealed prediction reason",
                ),
                "oracle_expected_prerequisite_reasons": _d4_string_list(
                    oracle.get("expected_prerequisite_reasons"),
                    label="oracle prerequisite reason",
                ),
                "numeric_support_available": False,
            }
            for output_key, receipt_key in (
                ("boundary_amplitude_descriptor", "boundary_amplitude"),
                ("boundary_coherence_descriptor", "boundary_coherence"),
                (
                    "boundary_identifiability_descriptor",
                    "boundary_identifiability_score",
                ),
            ):
                row[output_key] = _d4_descriptor(
                    blind.get(receipt_key), label=receipt_key.replace("_", " ")
                )
            support_rows.append(row)
    if len(support_rows) != 1_152:
        raise QualificationContractError(
            "D4 support table must retain all 1,152 leaf members"
        )

    return [
        _output(
            "three-by-three-field-cycle-graph-matrix",
            {
                "rows": matrix_rows,
                "evaluation_unit": "d4-d5-loop-execution-unit",
                "scientific_execution_count": len(units),
                "execution_role_row_count": len(matrix_rows),
                "matrix_shape": [3, 3],
                "cells_per_role_per_execution": 9,
                "graph_cells_are_repeated_measures": True,
                "graph_cells_are_independent_samples": False,
            },
        ),
        _output(
            "loop-role-separated-primary-boundary-and-offcore-control-table",
            {
                "rows": role_rows,
                "evaluation_unit": "d4-d5-loop-execution-unit",
                "scientific_execution_count": len(units),
                "cells_per_role_per_execution": 9,
                "role_counts": dict(Counter(row["loop_role"] for row in role_rows)),
                "loop_roles_collapsed": False,
                "graph_cells_are_repeated_measures": True,
                "loop_roles_are_independent_samples": False,
            },
        ),
        _output(
            "diagonal-offdiagonal-separation",
            {
                "rows": diagonal_rows,
                "classification_basis": "exact-declared-graph-family-equality",
                "classified_cell_count": sum(
                    int(row["cell_count"]) for row in diagonal_rows
                ),
                "diagonal_selected_as_winner": False,
                "descriptive_only": True,
                "graph_cells_are_independent_samples": False,
            },
        ),
        _output(
            "adjacency-output-loop-total-effects",
            {
                "rows": adjacency_rows,
                "scientific_execution_count": len(units),
                "field_pair_row_count": len(adjacency_rows),
                "component_row_count": component_row_count,
                "loop_contrast_row_count": loop_contrast_row_count,
                "nonvacuity_receipt_count": len(nonvacuity_evidence),
                "maximum_component_rms_distance": max(component_rms_values),
                "maximum_loop_contrast_absolute_difference_cycles": max(
                    loop_contrast_values
                ),
                "numeric_adjacency_difference_available": False,
                "field_output_and_loop_total_kept_distinct": True,
                "field_pairs_and_loop_contrasts_are_repeated_measures": True,
                "derived_rows_are_independent_samples": False,
            },
        ),
        _output(
            "support-aware-cell-table",
            {
                "rows": support_rows,
                "scientific_execution_count": len(units),
                "leaf_member_count": len(support_rows),
                "evaluable_cell_count": sum(
                    row["attempt_status"] == "evaluable" for row in support_rows
                ),
                "prerequisite_cell_count": sum(
                    row["attempt_status"] == "insufficient" for row in support_rows
                ),
                "numeric_support_available": False,
                "insufficient_is_not_fail": True,
                "support_bookkeeping_is_not_substantive_output": True,
                "leaf_members_are_repeated_measures": True,
                "leaf_members_are_independent_samples": False,
            },
        ),
    ]


def _stress_stratum_ids(unit: Mapping[str, object]) -> list[str]:
    result = []
    seen_axes: set[str] = set()
    for item in _sequence(unit.get("stress_assignments"), label="stress assignments"):
        assignment = _mapping(item, label="stress assignment")
        axis_id = _string(assignment.get("axis_id"), label="axis_id")
        level = _string(assignment.get("level"), label="level")
        if axis_id in seen_axes:
            raise QualificationContractError("stress assignment axis is duplicated")
        seen_axes.add(axis_id)
        result.append(f"stress.{axis_id}.{level}")
    if len(result) != 3:
        raise QualificationContractError(
            "each D4/D5 execution must retain three stress assignments"
        )
    return result


def _d5_crossed_inputs(
    protocol: Mapping[str, object],
    result: Mapping[str, object],
) -> tuple[
    list[dict[str, object]],
    dict[str, dict[str, object]],
    tuple[str, ...],
    tuple[str, ...],
    tuple[str, ...],
]:
    graphs = _mapping(protocol.get("graphs"), label="graphs")
    field_graph_ids = tuple(
        _string(
            _mapping(item, label="field graph").get("graph_id"),
            label="field graph_id",
        )
        for item in _sequence(graphs.get("field_estimation"), label="field graphs")
    )
    cycle_graph_ids = tuple(
        _string(
            _mapping(item, label="cycle graph").get("graph_id"),
            label="cycle graph_id",
        )
        for item in _sequence(graphs.get("cycle_construction"), label="cycle graphs")
    )
    if (
        field_graph_ids != _REPRESENTATION_D3_FIELD_GRAPH_IDS
        or cycle_graph_ids != _REPRESENTATION_D3_CYCLE_GRAPH_IDS
    ):
        raise QualificationContractError("D5 graph order differs from the protocol")

    expected_strata = [
        _mapping(item, label="expected stratum")
        for item in _sequence(protocol.get("expected_strata"), label="expected strata")
    ]
    stratum_ids = tuple(
        _string(item.get("stratum_id"), label="expected stratum_id")
        for item in expected_strata
    )
    if len(stratum_ids) != 6 or len(set(stratum_ids)) != 6:
        raise QualificationContractError("D5 stress-stratum universe is not closed")

    expected_cells = [
        _mapping(item, label="expected crossed cell")
        for item in _sequence(protocol.get("expected_cells"), label="expected cells")
    ]
    expected_by_id = {
        _string(item.get("cell_id"), label="expected cell_id"): item
        for item in expected_cells
    }
    cells = [
        _mapping(item, label="crossed cell")
        for item in _sequence(result.get("crossed_cells"), label="crossed cells")
    ]
    observed_by_id = {
        _string(item.get("cell_id"), label="crossed cell_id"): item for item in cells
    }
    if (
        len(expected_by_id) != 1_152
        or len(observed_by_id) != 1_152
        or set(expected_by_id) != set(observed_by_id)
    ):
        raise QualificationContractError(
            "D5 crossed cells differ from the exact protocol universe"
        )
    primary_units = {
        _string(
            _mapping(item, label="primary unit").get("primary_unit_id"),
            label="primary_unit_id",
        ): _mapping(item, label="primary unit")
        for item in _sequence(result.get("primary_units"), label="primary units")
    }
    if len(primary_units) != 64:
        raise QualificationContractError("D5 primary-unit universe is not closed")
    for cell_id, expected in expected_by_id.items():
        observed = observed_by_id[cell_id]
        direct_fields = (
            "primary_unit_id",
            "field_graph_id",
            "cycle_graph_id",
            "loop_role",
        )
        if any(observed.get(field) != expected.get(field) for field in direct_fields):
            raise QualificationContractError(
                "D5 crossed cell differs from its protocol identity"
            )
        if observed.get("expected_disposition") != expected.get(
            "expected_loop_disposition"
        ):
            raise QualificationContractError(
                "D5 crossed cell disposition differs from the protocol"
            )
        primary_unit_id = _string(
            observed.get("primary_unit_id"), label="crossed primary_unit_id"
        )
        unit = primary_units.get(primary_unit_id)
        if unit is None:
            raise QualificationContractError(
                "D5 crossed cell has no parent primary unit"
            )
        expected_ids = [
            _string(value, label="expected stratum membership")
            for value in _sequence(
                expected.get("stratum_ids"), label="expected stratum memberships"
            )
        ]
        if expected_ids != _stress_stratum_ids(unit) or not set(expected_ids) <= set(
            stratum_ids
        ):
            raise QualificationContractError(
                "D5 crossed-cell stress membership differs"
            )
    return (
        cells,
        expected_by_id,
        stratum_ids,
        field_graph_ids,
        cycle_graph_ids,
    )


def _stress_graph_rows(
    cells: Sequence[Mapping[str, object]],
    expected_by_id: Mapping[str, Mapping[str, object]],
    stratum_ids: Sequence[str],
    field_graph_ids: Sequence[str],
    cycle_graph_ids: Sequence[str],
) -> list[dict[str, object]]:
    grouped: dict[tuple[str, str, str, str], list[Mapping[str, object]]] = defaultdict(
        list
    )
    for cell in cells:
        cell_id = _string(cell.get("cell_id"), label="crossed cell_id")
        expected = expected_by_id[cell_id]
        for stratum_id in _sequence(
            expected.get("stratum_ids"), label="expected stratum memberships"
        ):
            grouped[
                (
                    _string(stratum_id, label="stratum_id"),
                    _string(cell.get("loop_role"), label="loop_role"),
                    _string(cell.get("field_graph_id"), label="field_graph_id"),
                    _string(cell.get("cycle_graph_id"), label="cycle_graph_id"),
                )
            ].append(cell)

    rows = []
    for stratum_id in stratum_ids:
        for loop_role in ("offcore_control", "primary_boundary"):
            for field_graph_id in field_graph_ids:
                for cycle_graph_id in cycle_graph_ids:
                    key = (stratum_id, loop_role, field_graph_id, cycle_graph_id)
                    members = grouped.get(key, [])
                    if len(members) != 32:
                        raise QualificationContractError(
                            "each D5 role-graph stress row must retain 32 cells"
                        )
                    errors = [
                        _number(
                            member.get("oracle_absolute_error_cycles"),
                            label="oracle absolute error",
                        )
                        for member in members
                        if member.get("oracle_absolute_error_cycles") is not None
                    ]
                    if len(errors) != 24:
                        raise QualificationContractError(
                            "each D5 role-graph stress row must retain 24 errors"
                        )
                    maximum_error = max(errors)
                    rows.append(
                        {
                            "stratum_id": stratum_id,
                            "field_graph_id": field_graph_id,
                            "cycle_graph_id": cycle_graph_id,
                            "loop_role": loop_role,
                            "attempted_execution_count": len(members),
                            "evaluable_execution_count": sum(
                                member.get("attempt_status") == "evaluable"
                                for member in members
                            ),
                            "prerequisite_execution_count": sum(
                                member.get("expected_disposition")
                                == "prerequisite_failure"
                                for member in members
                            ),
                            "maximum_oracle_absolute_error_cycles": maximum_error,
                            "worst_cell_ids": sorted(
                                _string(member.get("cell_id"), label="cell_id")
                                for member in members
                                if member.get("oracle_absolute_error_cycles")
                                == maximum_error
                            ),
                            "state_counts": dict(
                                sorted(
                                    Counter(
                                        _string(member.get("state"), label="state")
                                        for member in members
                                    ).items()
                                )
                            ),
                        }
                    )
    if len(rows) != 108 or set(grouped) != {
        (
            stratum_id,
            loop_role,
            field_graph_id,
            cycle_graph_id,
        )
        for stratum_id in stratum_ids
        for loop_role in ("offcore_control", "primary_boundary")
        for field_graph_id in field_graph_ids
        for cycle_graph_id in cycle_graph_ids
    }:
        raise QualificationContractError("D5 role-graph stress table is not closed")
    return rows


def _role_primary_units(
    result: Mapping[str, object],
    expected_by_id: Mapping[str, Mapping[str, object]],
) -> list[dict[str, object]]:
    primary_values = [
        _mapping(item, label="primary unit")
        for item in _sequence(result.get("primary_units"), label="primary units")
    ]
    primary = {
        _string(item.get("primary_unit_id"), label="primary_unit_id"): item
        for item in primary_values
    }
    if len(primary) != 64:
        raise QualificationContractError("D5 primary-unit universe is not closed")
    groups: dict[tuple[str, str], list[dict[str, object]]] = defaultdict(list)
    for item in _sequence(result.get("crossed_cells"), label="crossed cells"):
        cell = _mapping(item, label="crossed cell")
        cell_id = _string(cell.get("cell_id"), label="crossed cell_id")
        if cell_id not in expected_by_id:
            raise QualificationContractError(
                "D5 role reduction contains an unexpected crossed cell"
            )
        groups[
            (
                _string(cell.get("primary_unit_id"), label="primary_unit_id"),
                _string(cell.get("loop_role"), label="loop_role"),
            )
        ].append(cell)
    rows = []
    for (primary_unit_id, loop_role), cells in sorted(groups.items()):
        if len(cells) != 9:
            raise QualificationContractError(
                "each primary-unit loop role must retain nine graph cells"
            )
        observed_pairs = {
            (
                _string(cell.get("field_graph_id"), label="field_graph_id"),
                _string(cell.get("cycle_graph_id"), label="cycle_graph_id"),
            )
            for cell in cells
        }
        if observed_pairs != {
            (field_graph_id, cycle_graph_id)
            for field_graph_id in _REPRESENTATION_D3_FIELD_GRAPH_IDS
            for cycle_graph_id in _REPRESENTATION_D3_CYCLE_GRAPH_IDS
        }:
            raise QualificationContractError(
                "D5 role reduction differs from the nine graph pairs"
            )
        expected = {str(cell["expected_disposition"]) for cell in cells}
        predictions = {str(cell["prediction_class"]) for cell in cells}
        attempts = {str(cell["attempt_status"]) for cell in cells}
        if len(expected) != 1 or len(predictions) != 1 or len(attempts) != 1:
            raise QualificationContractError("graph-cell role projection disagrees")
        unit = primary[primary_unit_id]
        totals = [
            _number(cell.get("continuous_signed_total_cycles"), label="signed total")
            for cell in cells
            if cell.get("continuous_signed_total_cycles") is not None
        ]
        errors = [
            _number(cell.get("oracle_absolute_error_cycles"), label="oracle error")
            for cell in cells
            if cell.get("oracle_absolute_error_cycles") is not None
        ]
        if (not totals) != (next(iter(attempts)) == "insufficient") or len(
            totals
        ) != len(errors):
            raise QualificationContractError(
                "D5 role reduction evaluability differs across graph cells"
            )
        maximum_error = max(errors) if errors else None
        minimum_total = min(totals) if totals else None
        maximum_total = max(totals) if totals else None
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
                "graph_cell_count": len(cells),
                "continuous_span_cycles": (
                    maximum_total - minimum_total
                    if minimum_total is not None and maximum_total is not None
                    else None
                ),
                "span_endpoint_cell_ids": sorted(
                    _string(cell.get("cell_id"), label="cell_id")
                    for cell in cells
                    if cell.get("continuous_signed_total_cycles")
                    in {minimum_total, maximum_total}
                )
                if totals
                else [],
                "maximum_oracle_absolute_error_cycles": maximum_error,
                "worst_error_cell_ids": sorted(
                    _string(cell.get("cell_id"), label="cell_id")
                    for cell in cells
                    if maximum_error is not None
                    and cell.get("oracle_absolute_error_cycles") == maximum_error
                ),
            }
        )
    if len(rows) != 128 or {
        (str(row["primary_unit_id"]), str(row["loop_role"])) for row in rows
    } != {
        (primary_unit_id, loop_role)
        for primary_unit_id in primary
        for loop_role in ("offcore_control", "primary_boundary")
    }:
        raise QualificationContractError(
            "D5 within-execution role reduction is not closed"
        )
    return rows


_PERSISTED_STRATUM_KEYS = frozenset(
    {
        "abstention_fraction",
        "all_expected_primary_units_must_pass",
        "attempt_insufficient_count",
        "attempt_not_run_count",
        "attempted_count",
        "coverage",
        "evaluable_count",
        "evaluation_unit",
        "fail_count",
        "fail_graph_dependence_count",
        "graph_cells_are_repeated_measures",
        "insufficient_count",
        "negative_expected_count",
        "negative_pass_count",
        "not_run_count",
        "pass_count",
        "positive_expected_count",
        "positive_pass_count",
        "prerequisite_expected_count",
        "prerequisite_pass_count",
        "prerequisite_rate_handling",
        "primary_unit_ids",
        "rate_eligible_count",
        "rate_evaluable_count",
        "rate_insufficient_count",
        "rate_not_run_count",
        "reason_codes",
        "recall",
        "required",
        "score_denominator",
        "specificity",
        "state",
        "stratum_id",
    }
)


def _persisted_stratum_rows(
    protocol: Mapping[str, object],
    result: Mapping[str, object],
) -> list[dict[str, object]]:
    expected = [
        _mapping(item, label="expected stratum")
        for item in _sequence(protocol.get("expected_strata"), label="expected strata")
    ]
    observed = [
        _mapping(item, label="stress stratum")
        for item in _sequence(result.get("strata"), label="strata")
    ]
    if len(expected) != 6 or len(observed) != 6:
        raise QualificationContractError("D5 persisted strata are not closed")
    rows = []
    for expected_item, item in zip(expected, observed, strict=True):
        if set(item) != _PERSISTED_STRATUM_KEYS:
            raise QualificationContractError(
                "D5 persisted stratum fields differ from the 33-field record"
            )
        primary_unit_ids = [
            _string(value, label="stratum primary_unit_id")
            for value in _sequence(
                item.get("primary_unit_ids"), label="stratum primary_unit_ids"
            )
        ]
        if (
            item.get("stratum_id") != expected_item.get("stratum_id")
            or primary_unit_ids != expected_item.get("primary_unit_ids")
            or len(primary_unit_ids) != 32
            or len(set(primary_unit_ids)) != 32
            or item.get("evaluation_unit") != expected_item.get("evaluation_unit")
            or item.get("required") != expected_item.get("required")
        ):
            raise QualificationContractError(
                "D5 persisted stratum identity differs from the protocol"
            )
        exact_values = {
            "attempted_count": 32,
            "evaluable_count": 24,
            "attempt_insufficient_count": 8,
            "attempt_not_run_count": 0,
            "pass_count": 32,
            "fail_count": 0,
            "rate_eligible_count": 24,
            "rate_evaluable_count": 24,
            "rate_insufficient_count": 0,
            "rate_not_run_count": 0,
            "prerequisite_expected_count": 8,
            "prerequisite_pass_count": 8,
            "coverage": 1.0,
            "abstention_fraction": 0.0,
            "recall": 1.0,
            "specificity": 1.0,
            "graph_cells_are_repeated_measures": True,
            "score_denominator": "expected_nonprerequisite_primary_units",
            "prerequisite_rate_handling": "excluded_but_mandatory",
            "state": "pass",
        }
        if any(item.get(key) != value for key, value in exact_values.items()):
            raise QualificationContractError(
                "D5 persisted stratum metric differs from the parent record"
            )
        rows.append(dict(item))
    return rows


def _prerequisite_member_rows(
    result: Mapping[str, object],
    bundle: Mapping[str, object],
    core_primary_units: Sequence[Mapping[str, object]],
    loop_primary_units: Sequence[Mapping[str, object]],
) -> list[dict[str, object]]:
    core_by_primary = {
        _string(item.get("primary_unit_id"), label="core primary_unit_id"): item
        for item in core_primary_units
        if item.get("expected_disposition") == "prerequisite_failure"
    }
    loop_by_primary = {
        _string(item.get("primary_unit_id"), label="loop primary_unit_id"): item
        for item in loop_primary_units
        if item.get("expected_disposition") == "prerequisite_failure"
    }
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
    core_evidence = {
        _string(item.get("core_cell_id"), label="core_cell_id"): item
        for item in (
            _mapping(value, label="core evidence")
            for value in _sequence(
                bundle.get("core_cell_receipts"), label="core cell receipts"
            )
        )
    }
    loop_evidence = {
        _string(item.get("cell_id"), label="loop cell_id"): item
        for item in (
            _mapping(value, label="loop evidence")
            for value in _sequence(
                bundle.get("loop_cell_receipts"), label="loop cell receipts"
            )
        )
    }
    if (
        len(core_by_primary) != 16
        or len(loop_by_primary) != 16
        or set(core_by_primary) != set(loop_by_primary)
    ):
        raise QualificationContractError(
            "mandatory prerequisite member universe differs"
        )
    rows = []
    for primary_unit_id in sorted(core_by_primary):
        core = core_by_primary[primary_unit_id]
        loop = loop_by_primary[primary_unit_id]
        if any(
            core.get(field) != loop.get(field)
            for field in (
                "control_id",
                "selection_seed",
                "stress_assignments",
                "expected_disposition",
            )
        ):
            raise QualificationContractError(
                "core and loop prerequisite primary identities differ"
            )
        selected_core = [
            core_cells[_string(value, label="core_cell_id")]
            for value in _sequence(core.get("core_cell_ids"), label="core_cell_ids")
        ]
        selected_loop = [
            loop_cells[_string(value, label="loop cell_id")]
            for value in _sequence(
                loop.get("crossed_cell_ids"), label="crossed_cell_ids"
            )
        ]
        required_pass = all(
            item.get("attempt_status") == "insufficient"
            and item.get("prediction_class") == "abstain"
            and item.get("state") == "pass"
            for item in (core, loop, *selected_core, *selected_loop)
        )
        rows.append(
            {
                "primary_unit_id": primary_unit_id,
                "control_id": _string(core.get("control_id"), label="control_id"),
                "selection_seed": _integer(
                    core.get("selection_seed"), label="selection_seed"
                ),
                "stress_assignments": [
                    dict(_mapping(value, label="stress assignment"))
                    for value in _sequence(
                        core.get("stress_assignments"), label="stress assignments"
                    )
                ],
                "stratum_ids": _stress_stratum_ids(core),
                "core_primary_attempt_status": _string(
                    core.get("attempt_status"), label="core attempt_status"
                ),
                "core_primary_prediction_class": _string(
                    core.get("prediction_class"), label="core prediction_class"
                ),
                "loop_primary_attempt_status": _string(
                    loop.get("attempt_status"), label="loop attempt_status"
                ),
                "loop_primary_prediction_class": _string(
                    loop.get("prediction_class"), label="loop prediction_class"
                ),
                "expected_prerequisite_failure_is_required_pass_route": (required_pass),
                "core_cells": [
                    {
                        "core_cell_id": _string(
                            item.get("core_cell_id"), label="core_cell_id"
                        ),
                        "field_graph_id": _string(
                            item.get("field_graph_id"), label="field_graph_id"
                        ),
                        "reason_codes": [
                            _string(reason, label="core reason code")
                            for reason in _sequence(
                                _mapping(
                                    core_evidence[str(item["core_cell_id"])].get(
                                        "sealed_prediction_receipt"
                                    ),
                                    label="core sealed prediction",
                                ).get("reason_codes"),
                                label="core reason codes",
                            )
                        ],
                    }
                    for item in sorted(
                        selected_core, key=lambda value: str(value["core_cell_id"])
                    )
                ],
                "loop_cells": [
                    {
                        "cell_id": _string(item.get("cell_id"), label="cell_id"),
                        "field_graph_id": _string(
                            item.get("field_graph_id"), label="field_graph_id"
                        ),
                        "cycle_graph_id": _string(
                            item.get("cycle_graph_id"), label="cycle_graph_id"
                        ),
                        "loop_role": _string(item.get("loop_role"), label="loop_role"),
                        "reason_codes": [
                            _string(reason, label="loop reason code")
                            for reason in _sequence(
                                _mapping(
                                    loop_evidence[str(item["cell_id"])].get(
                                        "sealed_prediction_receipt"
                                    ),
                                    label="loop sealed prediction",
                                ).get("reason_codes"),
                                label="loop reason codes",
                            )
                        ],
                    }
                    for item in sorted(
                        selected_loop, key=lambda value: str(value["cell_id"])
                    )
                ],
            }
        )
    if (
        any(
            row["expected_prerequisite_failure_is_required_pass_route"] is not True
            for row in rows
        )
        or sum(len(row["core_cells"]) for row in rows) != 48
        or sum(len(row["loop_cells"]) for row in rows) != 288
    ):
        raise QualificationContractError(
            "mandatory prerequisite leaf coverage differs from 48/288"
        )
    return rows


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


def _independence_outputs(
    plan: Mapping[str, object],
    protocol: Mapping[str, object],
    result: Mapping[str, object],
    manifest: Mapping[str, object],
    consumption: Mapping[str, object],
    d6_decision: Mapping[str, object],
) -> list[records.D7V1DescriptiveOutput]:
    selection = _mapping(protocol.get("selection"), label="selection")
    cartesian = _mapping(protocol.get("cartesian"), label="cartesian")
    graphs = _mapping(protocol.get("graphs"), label="graphs")
    implementation = _mapping(
        protocol.get("implementation_registry"), label="implementation registry"
    )
    thresholds = _mapping(protocol.get("thresholds"), label="locked thresholds")
    engine = _mapping(protocol.get("engine"), label="protocol engine")
    admission = _mapping(
        d6_decision.get("confirmation_admission_spec"),
        label="confirmation admission spec",
    )
    bundle = _mapping(result.get("evidence_bundle"), label="evidence bundle")
    field_graphs = [
        _mapping(item, label="field graph")
        for item in _sequence(graphs.get("field_estimation"), label="field graphs")
    ]
    cycle_graphs = [
        _mapping(item, label="cycle graph")
        for item in _sequence(graphs.get("cycle_construction"), label="cycle graphs")
    ]
    seeds = _sequence(selection.get("seeds"), label="selection seeds")
    implementation_sha256 = sha256_bytes(canonical_json_bytes(implementation))
    thresholds_sha256 = sha256_bytes(canonical_json_bytes(thresholds))
    if (
        implementation_sha256
        != admission.get("selection_implementation_registry_sha256")
        or thresholds_sha256 != admission.get("locked_thresholds_sha256")
        or cartesian.get("generator_family_id")
        != admission.get("selection_generator_family_id")
        or implementation.get("surrogate_estimator_id")
        != admission.get("required_surrogate_estimator_id")
        or engine.get("commit") != consumption.get("engine_commit")
    ):
        raise QualificationContractError(
            "independence-map protocol, admission, and execution joins differ"
        )

    def unique_estimator_id(receipt_key: str) -> str:
        estimator_ids = {
            _string(
                _mapping(
                    _mapping(item, label=receipt_key[:-1]).get(
                        "sealed_prediction_receipt"
                    ),
                    label=f"{receipt_key} sealed prediction",
                ).get("estimator_id"),
                label=f"{receipt_key} estimator_id",
            )
            for item in _sequence(bundle.get(receipt_key), label=receipt_key)
        }
        if len(estimator_ids) != 1:
            raise QualificationContractError(
                f"{receipt_key} does not retain one exact estimator identity"
            )
        return next(iter(estimator_ids))

    core_estimator_id = unique_estimator_id("core_cell_receipts")
    loop_estimator_id = unique_estimator_id("loop_cell_receipts")
    estimator_ids = [
        implementation["surrogate_estimator_id"],
        core_estimator_id,
        loop_estimator_id,
    ]
    if len(set(estimator_ids)) != 3:
        raise QualificationContractError("role-specific estimator identities collapse")

    field_families = sorted(str(item["family"]) for item in field_graphs)
    cycle_families = sorted(str(item["family"]) for item in cycle_graphs)
    if field_families != cycle_families or len(set(field_families)) != 3:
        raise QualificationContractError("field and cycle graph families differ")

    core_oracle_ids = {
        _string(item.get("oracle_fingerprint_sha256"), label="core oracle identity")
        for raw in _sequence(result.get("core_cells"), label="core cells")
        for item in (_mapping(raw, label="core cell"),)
    }
    loop_oracle_ids = {
        _string(item.get("oracle_fingerprint_sha256"), label="loop oracle identity")
        for raw in _sequence(result.get("crossed_cells"), label="crossed cells")
        for item in (_mapping(raw, label="crossed cell"),)
    }
    if (
        len(core_oracle_ids) != 192
        or len(loop_oracle_ids) != 1_152
        or core_oracle_ids & loop_oracle_ids
    ):
        raise QualificationContractError("oracle payload identity surface differs")

    for receipt_key in ("core_cell_receipts", "loop_cell_receipts"):
        for raw in _sequence(bundle.get(receipt_key), label=receipt_key):
            receipt = _mapping(raw, label=receipt_key[:-1])
            prediction = _mapping(
                receipt.get("sealed_prediction_receipt"),
                label=f"{receipt_key} sealed prediction",
            )
            truth = _mapping(
                receipt.get("oracle_truth_receipt"),
                label=f"{receipt_key} oracle truth",
            )
            if (
                prediction.get("oracle_read") is not False
                or prediction.get("sealed_before_oracle_score") is not True
                or truth.get("estimator_input_allowed") is not False
            ):
                raise QualificationContractError(
                    "oracle separation boundary differs in the evidence bundle"
                )
            if (
                receipt_key == "loop_cell_receipts"
                and truth.get("oracle_integer_is_synthetic_expected_sampled_outcome")
                is not True
            ):
                raise QualificationContractError(
                    "loop oracle synthetic-outcome boundary differs"
                )

    map_rows = [
        {
            "dimension_id": "generator-construction",
            "identities": [cartesian["generator_family_id"]],
            "identity_count": 1,
            "sharing_relation": "all selection observations share one family",
            "independence_supported": False,
            "detail": {
                "construction_family_id": admission["selection_construction_family_id"],
                "generator_case_count": len(
                    _sequence(
                        implementation.get("generator_cases"),
                        label="generator cases",
                    )
                ),
            },
        },
        {
            "dimension_id": "seed-block",
            "identities": list(seeds),
            "identity_count": len(seeds),
            "sharing_relation": "same-family repeated seed blocks",
            "independence_supported": False,
            "detail": {"seed_block_independence_proved": False},
        },
        {
            "dimension_id": "boundary-repeat",
            "identities": sorted(
                str(_mapping(item, label="boundary")["level"])
                for item in cartesian["primary_boundaries"]
            ),
            "identity_count": len(cartesian["primary_boundaries"]),
            "sharing_relation": "paired nuisance repeats",
            "independence_supported": False,
            "detail": {
                "d2_repeated_measure": True,
                "d4_d5_execution_retained": True,
            },
        },
        {
            "dimension_id": "graph-family",
            "identities": field_families,
            "identity_count": len(field_families),
            "sharing_relation": "within-execution repeated measures",
            "independence_supported": False,
            "detail": {
                "field_graph_ids": sorted(
                    str(item["graph_id"]) for item in field_graphs
                ),
                "cycle_graph_ids": sorted(
                    str(item["graph_id"]) for item in cycle_graphs
                ),
                "graph_role_record_count": len(field_graphs) + len(cycle_graphs),
                "crossed_cells_per_execution": (
                    len(field_graphs) * len(cycle_graphs) * 2
                ),
            },
        },
        {
            "dimension_id": "implementation",
            "identities": [implementation_sha256],
            "identity_count": 1,
            "sharing_relation": "one frozen implementation registry",
            "independence_supported": False,
            "detail": {"engine_commit": engine["commit"]},
        },
        {
            "dimension_id": "estimator",
            "identities": estimator_ids,
            "identity_count": len(estimator_ids),
            "sharing_relation": "shared role-specific mechanisms",
            "independence_supported": False,
            "detail": {"role_count": 3},
        },
        {
            "dimension_id": "threshold",
            "identities": [thresholds_sha256],
            "identity_count": 1,
            "sharing_relation": "one locked threshold set",
            "independence_supported": False,
            "detail": {"postselection_threshold_change_authorized": False},
        },
        {
            "dimension_id": "oracle",
            "identities": {
                "core_payload_count": len(core_oracle_ids),
                "loop_payload_count": len(loop_oracle_ids),
                "synthetic_oracle_mechanism_shared": True,
            },
            "identity_count": len(core_oracle_ids | loop_oracle_ids),
            "sharing_relation": (
                "different payload hashes do not prove independent observers"
            ),
            "independence_supported": False,
            "detail": {"oracle_read_before_prediction": False},
        },
        {
            "dimension_id": "evidence-bundle",
            "identities": [result["result_evidence_root_sha256"]],
            "identity_count": 1,
            "sharing_relation": "one terminal evidence lineage",
            "independence_supported": False,
            "detail": {
                "consumption_id": consumption["consumption_id"],
                "terminal_artifact_sha256": manifest["terminal_artifact_sha256"],
            },
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
            "category": "deterministic-replay",
            "evidence_state": "observed_scoped",
            "detail": {
                "graph_records_reconstructed": result[
                    "pr8_graph_records_reconstructed"
                ],
                "d8_isolated_replay_state": _mapping(
                    d6_decision.get("d8"), label="D8 decision"
                )["state"],
            },
            "independent_confirmation_credit": False,
        },
        {
            "category": "same-family-replication",
            "evidence_state": "observed",
            "detail": {
                "seed_block_count": len(seeds),
                "seed_block_independence_proved": False,
            },
            "independent_confirmation_credit": False,
        },
        {
            "category": "construction-diversity",
            "evidence_state": "absent",
            "detail": {
                "observed_construction_family_count": construction_unit[
                    "declared_count"
                ],
                "confirmation_family_admitted": d6_decision[
                    "confirmation_family_admitted"
                ],
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
    epistemic_nonclaim_rows = [
        {
            "claim_ceiling": "level_0",
            "claim_delta": "none",
            "observed_construction_family_count": construction_unit["declared_count"],
            "confirmation_family_admitted": d6_decision["confirmation_family_admitted"],
            "independent_confirmation_count": 0,
            "seed_block_independence_proved": False,
            "seed_change_alone_sufficient": admission["seed_change_alone_sufficient"],
            "source_or_implementation_change_alone_sufficient": admission[
                "source_or_implementation_change_alone_sufficient"
            ],
            "boundary_variants_are_repeated_measures": True,
            "graph_cells_are_repeated_measures": True,
            "graph_protocol_difference_is_construction_diversity": False,
            "construction_family_generalization_claimed": False,
            "epistemic_independence_claimed": False,
            "inferential_sample_size_claimed": False,
        }
    ]
    return [
        _output(
            "shared-generator-seed-graph-boundary-implementation-oracle-map",
            {
                "rows": map_rows,
                "dimension_count": len(map_rows),
                "hash_inequality_implies_independence": False,
                "shared_dimensions_are_not_independent_evidence": True,
                "graph_pairs_are_not_iid_replicates": True,
            },
        ),
        _output(
            "replication-versus-construction-diversity-table",
            {
                "rows": diversity_rows,
                "category_count": len(diversity_rows),
                "graph_protocol_difference_is_construction_diversity": False,
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
                "rows": epistemic_nonclaim_rows,
                "claim_ceiling": "level_0",
                "claim_delta": "none",
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
