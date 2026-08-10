"""Private shared vocabulary for the D7 v1 descriptive work packages."""

from __future__ import annotations

from collections import Counter
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
