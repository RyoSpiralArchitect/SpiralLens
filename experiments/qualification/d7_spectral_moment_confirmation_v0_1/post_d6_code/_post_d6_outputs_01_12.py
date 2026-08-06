"""Deterministic post-D6 descriptive outputs 1--12.

This repository-only module only tabulates already-persisted
Level-0 parent records.  It performs no file access, historical reexecution,
current-engine reconstruction, model/subject access, or authority transition.
"""

from __future__ import annotations

import math
from collections import Counter
from collections.abc import Mapping

from spirallens.core.canonical import canonical_json_sha256

from spirallens.qualification.common import QualificationContractError

__all__ = ()


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
)

_D1_FAMILIES = (
    "cartesian-fourier-family-verified",
    "representation-family-verified",
)
_D3_CARTESIAN = "cartesian-gauge-pipeline-rerun-verified"
_D3_REPRESENTATION = "representation-gauge-pipeline-rerun-verified"
_FIELD_GRAPHS = ("a-mutual", "a-radius", "a-shared")


def _fail(message: str) -> None:
    raise QualificationContractError(message)


def _mapping(value: object, *, label: str) -> dict[str, object]:
    if not isinstance(value, dict) or any(not isinstance(key, str) for key in value):
        _fail(f"{label} must be a JSON object")
    return value


def _sequence(value: object, *, label: str) -> list[object]:
    if not isinstance(value, list):
        _fail(f"{label} must be a JSON array")
    return value


def _text(value: object, *, label: str) -> str:
    if not isinstance(value, str) or not value:
        _fail(f"{label} must be a non-empty string")
    return value


def _plain_int(value: object, *, label: str) -> int:
    if type(value) is not int:
        _fail(f"{label} must be a plain integer")
    return value


def _finite(value: object, *, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        _fail(f"{label} must be a finite real number")
    result = float(value)
    if not math.isfinite(result):
        _fail(f"{label} must be a finite real number")
    return result


def _boolean(value: object, *, label: str) -> bool:
    if type(value) is not bool:
        _fail(f"{label} must be a boolean")
    return value


def _sha256(value: object, *, label: str) -> str:
    result = _text(value, label=label)
    if len(result) != 64 or any(char not in "0123456789abcdef" for char in result):
        _fail(f"{label} must be a lowercase SHA-256 digest")
    return result


def _optional_sha256(value: object, *, label: str) -> str | None:
    if value is None:
        return None
    return _sha256(value, label=label)


def _reason_codes(value: object, *, label: str) -> list[str]:
    result = _sequence(value, label=label)
    if any(not isinstance(item, str) or not item for item in result):
        _fail(f"{label} must contain non-empty strings")
    if len(set(result)) != len(result):
        _fail(f"{label} must not contain duplicates")
    return list(result)  # type: ignore[arg-type]


def _exact_keys(
    value: Mapping[str, object],
    expected: set[str] | frozenset[str],
    *,
    label: str,
) -> None:
    observed = set(value)
    if observed != set(expected):
        _fail(
            f"{label} keys differ: missing={sorted(set(expected) - observed)!r}, "
            f"extra={sorted(observed - set(expected))!r}"
        )


def _require_equal(left: object, right: object, *, label: str) -> None:
    if left != right:
        _fail(f"{label} differs")


def _output(
    sequence: int,
    *,
    status: str,
    row_count: int,
    data: dict[str, object],
    blocked_reason_codes: list[str] | None = None,
) -> dict[str, object]:
    if status not in {"available", "blocked"}:
        _fail("post-D6 output status is outside the closed vocabulary")
    result: dict[str, object] = {
        "sequence": sequence,
        "output_id": _OUTPUT_IDS[sequence - 1],
        "status": status,
        "row_count": row_count,
        "data": data,
    }
    if status == "blocked":
        if not blocked_reason_codes:
            _fail("blocked post-D6 output requires reason codes")
        result["blocked_reason_codes"] = blocked_reason_codes
    elif blocked_reason_codes is not None:
        _fail("available post-D6 output cannot carry blocked reason codes")
    return result


def _frozen_output_ids(plan: dict[str, object]) -> tuple[str, ...]:
    packages = _sequence(plan.get("work_packages"), label="plan work_packages")
    if len(packages) != 8:
        _fail("post-D6 plan must contain exactly eight work packages")
    flattened: list[str] = []
    for expected_sequence, raw in enumerate(packages, start=1):
        package = _mapping(raw, label=f"plan work_packages[{expected_sequence - 1}]")
        if (
            _plain_int(
                package.get("sequence"),
                label=f"plan work_packages[{expected_sequence - 1}].sequence",
            )
            != expected_sequence
        ):
            _fail("post-D6 work-package sequence differs from the frozen order")
        outputs = _sequence(
            package.get("required_outputs"),
            label=f"plan work_packages[{expected_sequence - 1}].required_outputs",
        )
        for value in outputs:
            flattened.append(_text(value, label="plan required output id"))
    if len(flattened) != 27 or tuple(flattened[:12]) != _OUTPUT_IDS:
        _fail("post-D6 required-output universe differs from frozen outputs 1--12")
    return tuple(flattened)


def _runtime_receipts(terminal: dict[str, object]) -> dict[str, dict[str, object]]:
    bundle = _mapping(terminal.get("evidence_bundle"), label="terminal evidence_bundle")
    raw = _sequence(
        bundle.get("static_runtime_receipts"),
        label="terminal static_runtime_receipts",
    )
    result: dict[str, dict[str, object]] = {}
    for index, value in enumerate(raw):
        receipt = _mapping(value, label=f"static_runtime_receipts[{index}]")
        evidence_id = _text(receipt.get("evidence_id"), label="runtime evidence_id")
        if evidence_id in result:
            _fail("static runtime evidence_id is duplicated")
        result[evidence_id] = receipt
    expected = {*_D1_FAMILIES, _D3_CARTESIAN, _D3_REPRESENTATION}
    if set(result) != expected:
        _fail("static runtime receipt universe differs from frozen D1/D3 evidence")
    return result


def _derive_parent_identity(
    *,
    plan: dict[str, object],
    protocol: dict[str, object],
    terminal: dict[str, object],
    manifest: dict[str, object],
    consumption: dict[str, object],
    d6_decision: dict[str, object],
    runtime_freeze_row: dict[str, object],
) -> dict[str, object]:
    parent = _mapping(plan.get("parent_evidence"), label="plan parent_evidence")
    protocol_source = _sha256(
        parent.get("protocol_source_sha256"),
        label="plan protocol_source_sha256",
    )
    protocol_canonical = _sha256(
        parent.get("protocol_canonical_sha256"),
        label="plan protocol_canonical_sha256",
    )
    result_sha = _sha256(
        parent.get("terminal_result_sha256"),
        label="plan terminal_result_sha256",
    )
    manifest_sha = _sha256(
        parent.get("terminal_manifest_sha256"),
        label="plan terminal_manifest_sha256",
    )
    consumption_sha = _sha256(
        parent.get("terminal_consumption_sha256"),
        label="plan terminal_consumption_sha256",
    )
    decision_sha = _sha256(
        parent.get("d6_decision_sha256"),
        label="plan d6_decision_sha256",
    )
    evidence_root = _sha256(
        parent.get("result_evidence_root_sha256"),
        label="plan result_evidence_root_sha256",
    )
    launch_sha = _sha256(
        parent.get("selection_launch_authorization_sha256"),
        label="plan selection_launch_authorization_sha256",
    )
    admission_sha = _sha256(
        parent.get("d6_admission_spec_sha256"),
        label="plan d6_admission_spec_sha256",
    )

    _require_equal(
        canonical_json_sha256(protocol),
        protocol_canonical,
        label="protocol canonical identity",
    )
    _require_equal(protocol_source, protocol_canonical, label="protocol identities")
    _require_equal(
        canonical_json_sha256(terminal), result_sha, label="terminal result identity"
    )
    _require_equal(
        canonical_json_sha256(manifest),
        manifest_sha,
        label="terminal manifest identity",
    )
    _require_equal(
        canonical_json_sha256(consumption),
        consumption_sha,
        label="terminal consumption identity",
    )
    _require_equal(
        canonical_json_sha256(d6_decision), decision_sha, label="D6 decision identity"
    )
    admission = _mapping(
        d6_decision.get("confirmation_admission_spec"),
        label="D6 confirmation_admission_spec",
    )
    _require_equal(
        canonical_json_sha256(admission), admission_sha, label="D6 admission identity"
    )
    selection_terminal = _mapping(
        d6_decision.get("selection_terminal"), label="D6 selection_terminal"
    )
    joins = (
        (
            terminal.get("protocol_source_sha256"),
            protocol_source,
            "result protocol source",
        ),
        (
            terminal.get("protocol_canonical_sha256"),
            protocol_canonical,
            "result protocol canonical",
        ),
        (manifest.get("terminal_artifact_sha256"), result_sha, "manifest result"),
        (manifest.get("consumption_sha256"), consumption_sha, "manifest consumption"),
        (consumption.get("terminal_artifact_sha256"), result_sha, "consumption result"),
        (
            terminal.get("result_evidence_root_sha256"),
            evidence_root,
            "result evidence root",
        ),
        (
            selection_terminal.get("result_evidence_root_sha256"),
            evidence_root,
            "decision evidence root",
        ),
        (
            terminal.get("selection_launch_authorization_sha256"),
            launch_sha,
            "result launch authorization",
        ),
        (
            selection_terminal.get("launch_authorization_sha256"),
            launch_sha,
            "decision launch authorization",
        ),
        (selection_terminal.get("result_sha256"), result_sha, "decision result"),
        (
            selection_terminal.get("terminal_manifest_sha256"),
            manifest_sha,
            "decision terminal manifest",
        ),
        (
            selection_terminal.get("consumption_sha256"),
            consumption_sha,
            "decision terminal consumption",
        ),
    )
    for observed, expected, label in joins:
        _require_equal(observed, expected, label=label)

    row_keys = {
        "identity_kind",
        "storage_kind",
        "repository_path",
        "source_sha256",
        "canonical_sha256",
        "parent_field_path",
        "verified",
    }

    def file_row(
        identity_kind: str,
        path_key: str,
        digest: str,
        field_path: str,
    ) -> dict[str, object]:
        path = _text(parent.get(path_key), label=f"plan {path_key}")
        if path.startswith("/") or ".." in path.split("/"):
            _fail(f"plan {path_key} must be repository-relative")
        return {
            "identity_kind": identity_kind,
            "storage_kind": "file",
            "repository_path": path,
            "source_sha256": digest,
            "canonical_sha256": digest,
            "parent_field_path": field_path,
            "verified": True,
        }

    rows = [
        file_row("protocol", "protocol_path", protocol_source, "plan.parent_evidence"),
        file_row(
            "terminal-result",
            "terminal_result_path",
            result_sha,
            "plan.parent_evidence",
        ),
        {
            "identity_kind": "result-evidence-root",
            "storage_kind": "derived_identity",
            "repository_path": None,
            "source_sha256": None,
            "canonical_sha256": evidence_root,
            "parent_field_path": "terminal.result_evidence_root_sha256",
            "verified": True,
        },
        file_row(
            "terminal-manifest",
            "terminal_manifest_path",
            manifest_sha,
            "plan.parent_evidence",
        ),
        file_row(
            "terminal-consumption",
            "terminal_consumption_path",
            consumption_sha,
            "plan.parent_evidence",
        ),
        {
            "identity_kind": "selection-launch-authorization",
            "storage_kind": "derived_identity",
            "repository_path": None,
            "source_sha256": None,
            "canonical_sha256": launch_sha,
            "parent_field_path": "terminal.selection_launch_authorization_sha256",
            "verified": True,
        },
        file_row(
            "d6-decision", "d6_decision_path", decision_sha, "plan.parent_evidence"
        ),
        {
            "identity_kind": "d6-admission-specification",
            "storage_kind": "embedded_object",
            "repository_path": _text(
                parent.get("d6_decision_path"), label="plan d6_decision_path"
            ),
            "source_sha256": None,
            "canonical_sha256": admission_sha,
            "parent_field_path": "d6_decision.confirmation_admission_spec",
            "verified": True,
        },
    ]
    runtime = _mapping(runtime_freeze_row, label="runtime freeze identity row")
    _exact_keys(runtime, row_keys, label="runtime freeze identity row")
    if (
        runtime.get("identity_kind") != "d7-full-design-freeze-receipt"
        or runtime.get("storage_kind") != "file"
        or runtime.get("verified") is not True
    ):
        _fail("runtime freeze row does not identify a verified D7 freeze file")
    runtime_path = _text(
        runtime.get("repository_path"), label="runtime freeze repository_path"
    )
    if runtime_path.startswith("/") or ".." in runtime_path.split("/"):
        _fail("runtime freeze repository_path must be repository-relative")
    _sha256(runtime.get("source_sha256"), label="runtime freeze source_sha256")
    _sha256(runtime.get("canonical_sha256"), label="runtime freeze canonical_sha256")
    _text(runtime.get("parent_field_path"), label="runtime freeze parent_field_path")
    rows.append(dict(runtime))
    if len(rows) != 9 or any(set(row) != row_keys for row in rows):
        _fail("parent identity table differs from the exact nine-row contract")
    return _output(
        1,
        status="available",
        row_count=9,
        data={"historical_parent_count": 8, "runtime_parent_count": 1, "rows": rows},
    )


def _derive_gate_scope(
    terminal: dict[str, object], d6_decision: dict[str, object]
) -> dict[str, object]:
    raw_gates = _sequence(terminal.get("gate_results"), label="terminal gate_results")
    expected = (
        ("d0", "engine-and-protocol-contracts", 2, 2, 2, 0),
        ("d1", "cartesian-surrogate-and-representation-development", 2, 2, 2, 0),
        ("d2", "cartesian-surrogate-only", 32, 24, 32, 8),
        ("d3", "cartesian-surrogate-and-representation-development", 2, 2, 2, 0),
        ("d4", "cartesian-surrogate-only", 64, 48, 64, 16),
        ("d5", "cartesian-surrogate-only", 64, 48, 64, 16),
    )
    if len(raw_gates) != len(expected):
        _fail("terminal must contain exactly D0--D5 gate results")
    rows: list[dict[str, object]] = []
    for index, (raw, frozen) in enumerate(zip(raw_gates, expected, strict=True)):
        gate = _mapping(raw, label=f"terminal gate_results[{index}]")
        gate_id, claim_scope, attempted, evaluable, passed, attempt_insufficient = (
            frozen
        )
        observed = (
            gate.get("gate_id"),
            gate.get("claim_scope"),
            gate.get("attempted_count"),
            gate.get("evaluable_count"),
            gate.get("pass_count"),
            gate.get("attempt_insufficient_count"),
        )
        if observed != frozen or gate.get("state") != "pass":
            _fail(f"terminal {gate_id} summary differs from the frozen result")
        if gate.get("fail_count") != 0:
            _fail(f"terminal {gate_id} fail_count differs from zero")
        rows.append(
            {
                "gate_id": gate_id,
                "state": "pass",
                "claim_scope": claim_scope,
                "attempted_count": attempted,
                "evaluable_count": evaluable,
                "pass_count": passed,
                "fail_count": 0,
                "attempt_insufficient_count": attempt_insufficient,
                "reason_codes": _reason_codes(
                    gate.get("reason_codes"), label=f"terminal {gate_id} reason_codes"
                ),
                "source_field_path": f"terminal.gate_results[{index}]",
            }
        )
    selection_terminal = _mapping(
        d6_decision.get("selection_terminal"), label="D6 selection_terminal"
    )
    states = _sequence(selection_terminal.get("gate_states"), label="D6 gate_states")
    scopes = _sequence(
        selection_terminal.get("gate_claim_scopes"), label="D6 gate_claim_scopes"
    )
    expected_states = [[item[0], "pass"] for item in expected]
    expected_scopes = [[item[0], item[1]] for item in expected]
    if states != expected_states or scopes != expected_scopes:
        _fail("D6 embedded D0--D5 states/scopes differ from the result")

    d6 = _mapping(d6_decision.get("d6"), label="D6 decision d6")
    d7 = _mapping(d6_decision.get("d7"), label="D6 decision d7")
    d8 = _mapping(d6_decision.get("d8"), label="D6 decision d8")
    if d6 != {"scope": "surrogate-profile-confirmation-only", "state": "pass"}:
        _fail("D6 state/scope differs from the frozen decision")
    expected_reasons = {
        "d7": [
            "full-d2-d5-confirmation-path-not-implemented",
            "independent-construction-family-not-admitted",
        ],
        "d8": ["d7-not-pass", "replay-not-run"],
    }
    for gate_id, gate in (("d7", d7), ("d8", d8)):
        if (
            gate.get("state") != "not_run"
            or gate.get("reason_codes") != expected_reasons[gate_id]
        ):
            _fail(f"{gate_id.upper()} state/reasons differ from the frozen decision")
    for gate_id, state, scope, reasons in (
        ("d6", "pass", "surrogate-profile-confirmation-only", []),
        ("d7", "not_run", None, expected_reasons["d7"]),
        ("d8", "not_run", None, expected_reasons["d8"]),
    ):
        rows.append(
            {
                "gate_id": gate_id,
                "state": state,
                "claim_scope": scope,
                "attempted_count": None,
                "evaluable_count": None,
                "pass_count": None,
                "fail_count": None,
                "attempt_insufficient_count": None,
                "reason_codes": reasons,
                "source_field_path": f"d6_decision.{gate_id}",
            }
        )
    if len(rows) != 9:
        _fail("gate/scope output must contain exactly D0--D8")
    return _output(2, status="available", row_count=9, data={"rows": rows})


def _derive_non_claim(plan: dict[str, object]) -> dict[str, object]:
    boundary = _mapping(plan.get("claim_boundary"), label="plan claim_boundary")
    expected_names = {
        "claim_ceiling",
        "claim_delta",
        "d0_d6_claim_strengthening_authorized",
        "d7_design_input_authorized",
        "d7_execution_authorized",
        "d8_execution_authorized",
        "integer_output_authorized",
        "localized_core_loop_join_authorized",
        "official_gate_reclassification_authorized",
        "p0_winner_selection_authorized",
        "pythia_scientific_use_authorized",
        "representation_transfer_authorized",
        "scientific_claim_eligible",
        "semantic_sae_causal_authorized",
        "subject_execution_authorized",
        "subject_preparation_authorized",
        "synthetic_qualified",
        "topology_claim_authorized",
    }
    _exact_keys(boundary, expected_names, label="plan claim_boundary")
    if (
        boundary.get("claim_ceiling") != "level_0"
        or boundary.get("claim_delta") != "none"
    ):
        _fail("post-D6 claim ceiling/delta differs from Level 0 / none")
    for name in expected_names - {"claim_ceiling", "claim_delta"}:
        if boundary.get(name) is not False:
            _fail(f"post-D6 claim boundary {name} must remain false")
    claim_rows = [
        {
            "name": name,
            "value": boundary[name],
            "source_field_path": f"plan.claim_boundary.{name}",
        }
        for name in sorted(boundary)
    ]
    validation_rows = [
        {
            "validation_kind": "source-identity",
            "established": True,
            "claim_effect": "none",
        },
        {
            "validation_kind": "archival-validation",
            "established": True,
            "claim_effect": "none",
        },
        {
            "validation_kind": "historical-engine-reexecution",
            "established": False,
            "claim_effect": "none",
        },
        {
            "validation_kind": "current-source-compatibility",
            "established": False,
            "claim_effect": "none",
        },
    ]
    return _output(
        3,
        status="available",
        row_count=22,
        data={
            "claim_boundary_rows": claim_rows,
            "validation_boundary_rows": validation_rows,
            "historical_d1_recomputation_performed": False,
        },
    )


def _derive_d1(
    runtime: dict[str, dict[str, object]],
) -> tuple[dict[str, object], dict[str, object]]:
    expected_cases = {
        _D1_FAMILIES[0]: (
            "cartesian-fourier-fixed-null",
            "cartesian-fourier-no-core-null",
            "cartesian-fourier-positive",
            "cartesian-fourier-prerequisite-failure",
        ),
        _D1_FAMILIES[1]: ("angular-section-positive", "fixed-direction-null"),
    }
    expected_metrics = {
        _D1_FAMILIES[0]: (
            "amplitude-max-absolute-error",
            "direction-minimum-cosine",
            "second-harmonic-max-absolute-error",
            "split-max-disagreement",
            "support-mismatch-count",
        ),
        _D1_FAMILIES[1]: (
            "amplitude-max-absolute-error",
            "phase-law-coherence",
            "support-mismatch-count",
        ),
    }
    expected_graphs = ("mutual-knn", "fixed-radius", "shared-neighbor")
    rows: list[dict[str, object]] = []
    family_counts: dict[str, int] = {}
    for family_id in _D1_FAMILIES:
        receipt = runtime[family_id]
        cases = _sequence(receipt.get("cases"), label=f"{family_id} cases")
        observed_case_ids = tuple(
            _text(
                _mapping(case, label=f"{family_id} case").get("case_id"),
                label=f"{family_id} case_id",
            )
            for case in cases
        )
        if observed_case_ids != expected_cases[family_id]:
            _fail(f"{family_id} case universe differs from the frozen D1 family")
        before = len(rows)
        for raw_case in cases:
            case = _mapping(raw_case, label=f"{family_id} case")
            case_id = _text(case.get("case_id"), label=f"{family_id} case_id")
            metrics = _sequence(
                case.get("numeric_metric_receipts"),
                label=f"{family_id} {case_id} numeric metrics",
            )
            expected_count = 3 * len(expected_metrics[family_id])
            if len(metrics) != expected_count:
                _fail(f"{family_id} {case_id} D1 metric matrix has wrong size")
            observed_order: list[tuple[str, str]] = []
            for raw_metric in metrics:
                metric = _mapping(raw_metric, label=f"{family_id} D1 metric")
                graph = _text(metric.get("graph_family"), label="D1 graph_family")
                metric_id = _text(metric.get("metric_id"), label="D1 metric_id")
                observed_order.append((graph, metric_id))
                comparator = _text(metric.get("comparator"), label="D1 comparator")
                observed = _finite(metric.get("observed_value"), label="D1 observed")
                threshold = _finite(metric.get("threshold"), label="D1 threshold")
                if comparator == "at-most":
                    margin = threshold - observed
                    expected_pass = observed <= threshold
                elif comparator == "at-least":
                    margin = observed - threshold
                    expected_pass = observed >= threshold
                elif comparator == "exact-zero":
                    if threshold != 0.0:
                        _fail("D1 exact-zero threshold must equal zero")
                    margin = 0.0 if observed == 0.0 else -abs(observed)
                    expected_pass = observed == 0.0
                else:
                    _fail("D1 comparator is outside the frozen universe")
                passed = _boolean(metric.get("passed"), label="D1 passed")
                if passed is not expected_pass:
                    _fail("D1 persisted pass flag differs from its frozen comparison")
                rows.append(
                    {
                        "family_evidence_id": family_id,
                        "case_id": case_id,
                        "graph_family": graph,
                        "metric_id": metric_id,
                        "comparator": comparator,
                        "observed_value": observed,
                        "threshold": threshold,
                        "signed_margin": 0.0 if margin == 0.0 else margin,
                        "passed": passed,
                        "field_graph_fingerprint_sha256": _sha256(
                            metric.get("field_graph_fingerprint_sha256"),
                            label="D1 field graph fingerprint",
                        ),
                        "estimator_output_sha256": _sha256(
                            metric.get("estimator_output_sha256"),
                            label="D1 estimator output",
                        ),
                        "oracle_fingerprint_sha256": _sha256(
                            metric.get("oracle_fingerprint_sha256"),
                            label="D1 oracle fingerprint",
                        ),
                    }
                )
            frozen_order = tuple(
                (graph, metric)
                for graph in expected_graphs
                for metric in expected_metrics[family_id]
            )
            if tuple(observed_order) != frozen_order:
                _fail(f"{family_id} {case_id} metric order differs from the contract")
        family_counts[family_id] = len(rows) - before
    if family_counts != {_D1_FAMILIES[0]: 60, _D1_FAMILIES[1]: 18} or len(rows) != 78:
        _fail("D1 margin atlas differs from the exact 60 + 18 checks")
    margin_output = _output(
        4,
        status="available",
        row_count=78,
        data={"family_row_counts": family_counts, "rows": rows},
    )

    summaries: list[dict[str, object]] = []
    for family_id, expected_zero in ((_D1_FAMILIES[0], 12), (_D1_FAMILIES[1], 6)):
        family_rows = [row for row in rows if row["family_evidence_id"] == family_id]
        margins = [float(row["signed_margin"]) for row in family_rows]
        positive = [value for value in margins if value > 0.0]
        minimum_positive = min(positive)
        closest = [
            {
                "case_id": row["case_id"],
                "graph_family": row["graph_family"],
                "metric_id": row["metric_id"],
            }
            for row in family_rows
            if row["signed_margin"] == minimum_positive
        ]
        zero_count = sum(value == 0.0 for value in margins)
        negative_count = sum(value < 0.0 for value in margins)
        if zero_count != expected_zero or negative_count != 0:
            _fail(f"{family_id} D1 fragility counts differ from frozen evidence")
        summaries.append(
            {
                "family_evidence_id": family_id,
                "analytic_check_count": len(family_rows),
                "zero_margin_count": zero_count,
                "negative_margin_count": negative_count,
                "minimum_signed_margin": min(margins),
                "minimum_strictly_positive_margin": minimum_positive,
                "closest_positive_check_keys": closest,
                "all_persisted_checks_passed": all(
                    row["passed"] is True for row in family_rows
                ),
                "threshold_change_authorized": False,
            }
        )
    fragility_output = _output(
        5,
        status="available",
        row_count=2,
        data={"rows": summaries},
    )
    return margin_output, fragility_output


def _stress_levels(unit: Mapping[str, object]) -> tuple[str, str, str]:
    raw = _sequence(unit.get("stress_assignments"), label="D2 stress_assignments")
    if len(raw) != 3:
        _fail("D2 unit must contain exactly three stress assignments")
    assignments: dict[str, str] = {}
    for value in raw:
        item = _mapping(value, label="D2 stress assignment")
        axis = _text(item.get("axis_id"), label="D2 stress axis_id")
        level = _text(item.get("level"), label="D2 stress level")
        if axis in assignments:
            _fail("D2 stress axis is duplicated")
        assignments[axis] = level
    if set(assignments) != {
        "boundary",
        "state-geometry-warp",
        "structured-observation-perturbation",
    }:
        _fail("D2 stress axes differ from the frozen Cartesian design")
    return (
        assignments["boundary"],
        assignments["state-geometry-warp"],
        assignments["structured-observation-perturbation"],
    )


def _derive_d2_main(
    terminal: dict[str, object],
) -> tuple[
    dict[str, object],
    dict[str, object],
    list[dict[str, object]],
    dict[str, dict[str, object]],
]:
    raw_units = _sequence(
        terminal.get("core_primary_units"), label="terminal core_primary_units"
    )
    raw_cells = _sequence(terminal.get("core_cells"), label="terminal core_cells")
    if len(raw_units) != 64 or len(raw_cells) != 192:
        _fail("D2 main evidence must contain 64 units and 192 core cells")
    cells_by_id: dict[str, dict[str, object]] = {}
    for raw in raw_cells:
        cell = _mapping(raw, label="D2 core cell")
        cell_id = _text(cell.get("core_cell_id"), label="D2 core_cell_id")
        if cell_id in cells_by_id:
            _fail("D2 core_cell_id is duplicated")
        cells_by_id[cell_id] = cell

    bundle = _mapping(terminal.get("evidence_bundle"), label="terminal evidence_bundle")
    raw_receipts = _sequence(
        bundle.get("core_cell_receipts"), label="terminal core_cell_receipts"
    )
    if len(raw_receipts) != 192:
        _fail("D2 evidence bundle must contain 192 core-cell receipts")
    receipts_by_id: dict[str, dict[str, object]] = {}
    for raw in raw_receipts:
        receipt = _mapping(raw, label="D2 core-cell receipt")
        cell_id = _text(receipt.get("core_cell_id"), label="D2 receipt core_cell_id")
        if cell_id in receipts_by_id:
            _fail("D2 receipt core_cell_id is duplicated")
        receipts_by_id[cell_id] = receipt
    if set(receipts_by_id) != set(cells_by_id):
        _fail("D2 core summaries and evidence receipts have different cell IDs")

    grouped: dict[tuple[int, str, str, str], dict[str, dict[str, object]]] = {}
    group_order: list[tuple[int, str, str, str]] = []
    for raw in raw_units:
        unit = _mapping(raw, label="D2 core primary unit")
        seed = _plain_int(unit.get("selection_seed"), label="D2 selection_seed")
        control = _text(unit.get("control_id"), label="D2 control_id")
        boundary, state_warp, observation = _stress_levels(unit)
        if boundary not in {"central", "wide"}:
            _fail("D2 boundary repeat must be central or wide")
        key = (seed, control, state_warp, observation)
        if key not in grouped:
            grouped[key] = {}
            group_order.append(key)
        if boundary in grouped[key]:
            _fail("D2 boundary repeat is duplicated")
        grouped[key][boundary] = unit
    if len(grouped) != 32 or any(
        set(value) != {"central", "wide"} for value in grouped.values()
    ):
        _fail("D2 boundary collapse must yield exactly 32 paired units")

    outcome_fields = (
        "attempt_status",
        "expected_disposition",
        "prediction_class",
        "state",
        "reason_codes",
        "max_candidate_symmetric_difference_rows",
        "d2_scientific_input_fingerprint_sha256",
    )
    matrix_rows: list[dict[str, object]] = []
    agreement_rows: list[dict[str, object]] = []
    for seed, control, state_warp, observation in group_order:
        pair = grouped[(seed, control, state_warp, observation)]
        central = pair["central"]
        wide = pair["wide"]
        for field in outcome_fields:
            _require_equal(
                central.get(field), wide.get(field), label=f"D2 boundary {field}"
            )
        fingerprint = _sha256(
            central.get("d2_scientific_input_fingerprint_sha256"),
            label="D2 scientific input fingerprint",
        )
        central_ids = _sequence(
            central.get("core_cell_ids"), label="D2 central core_cell_ids"
        )
        wide_ids = _sequence(wide.get("core_cell_ids"), label="D2 wide core_cell_ids")
        if len(central_ids) != 3 or len(wide_ids) != 3:
            _fail("D2 boundary unit must retain exactly three graph cells")
        central_by_graph: dict[str, dict[str, object]] = {}
        wide_by_graph: dict[str, dict[str, object]] = {}
        for label, ids, destination in (
            ("central", central_ids, central_by_graph),
            ("wide", wide_ids, wide_by_graph),
        ):
            for raw_id in ids:
                cell_id = _text(raw_id, label=f"D2 {label} core cell ID")
                cell = cells_by_id.get(cell_id)
                if cell is None:
                    _fail(f"D2 {label} core cell is absent from summaries")
                graph = _text(cell.get("field_graph_id"), label="D2 field_graph_id")
                if graph in destination:
                    _fail("D2 field graph is duplicated within one boundary")
                destination[graph] = cell
        if (
            tuple(central_by_graph) != _FIELD_GRAPHS
            or tuple(wide_by_graph) != _FIELD_GRAPHS
        ):
            _fail("D2 graph order differs from the frozen three-family order")
        graph_rows: list[dict[str, object]] = []
        for graph in _FIELD_GRAPHS:
            left = central_by_graph[graph]
            right = wide_by_graph[graph]
            left_id = _text(left.get("core_cell_id"), label="D2 central cell ID")
            right_id = _text(right.get("core_cell_id"), label="D2 wide cell ID")
            left_receipt = receipts_by_id[left_id]
            right_receipt = receipts_by_id[right_id]
            left_blind = _mapping(
                left_receipt.get("blind_input_receipt"),
                label="D2 central blind input receipt",
            )
            right_blind = _mapping(
                right_receipt.get("blind_input_receipt"),
                label="D2 wide blind input receipt",
            )
            blind_descriptor_equalities = {
                f"{field}_descriptor_equal": left_blind.get(field)
                == right_blind.get(field)
                for field in ("amplitude", "identifiability_score", "support_counts")
            }
            if not all(blind_descriptor_equalities.values()):
                _fail("D2 boundary repeat blind array descriptors differ")
            candidate_rows_equal = left_receipt.get(
                "candidate_rows"
            ) == right_receipt.get("candidate_rows")
            comparisons = {
                "scientific_input_fingerprint_equal": (
                    central.get("d2_scientific_input_fingerprint_sha256")
                    == wide.get("d2_scientific_input_fingerprint_sha256")
                ),
                "attempt_status_equal": left.get("attempt_status")
                == right.get("attempt_status"),
                "expected_disposition_equal": left.get("expected_disposition")
                == right.get("expected_disposition"),
                "prediction_class_equal": left.get("prediction_class")
                == right.get("prediction_class"),
                "candidate_rows_equal": candidate_rows_equal,
                "candidate_fingerprint_equal": left.get("candidate_fingerprint_sha256")
                == right.get("candidate_fingerprint_sha256"),
                "reason_codes_equal": left.get("reason_codes")
                == right.get("reason_codes"),
                "state_equal": left.get("state") == right.get("state"),
            }
            declared_outcomes_equal = all(comparisons.values())
            if not declared_outcomes_equal:
                _fail("D2 boundary repeat differs for a frozen field graph")
            boundary_specific_identity_equalities = {
                f"{field}_equal": left.get(field) == right.get(field)
                for field in (
                    "blind_input_fingerprint_sha256",
                    "field_estimate_fingerprint_sha256",
                    "field_graph_fingerprint_sha256",
                    "oracle_fingerprint_sha256",
                    "prediction_fingerprint_sha256",
                )
            }
            if any(boundary_specific_identity_equalities.values()):
                _fail("D2 boundary-specific nuisance identity unexpectedly matches")
            graph_rows.append(
                {
                    "field_graph_id": graph,
                    "central_core_cell_id": left_id,
                    "wide_core_cell_id": right_id,
                    "central_candidate_fingerprint_sha256": _optional_sha256(
                        left.get("candidate_fingerprint_sha256"),
                        label="D2 central candidate fingerprint",
                    ),
                    "wide_candidate_fingerprint_sha256": _optional_sha256(
                        right.get("candidate_fingerprint_sha256"),
                        label="D2 wide candidate fingerprint",
                    ),
                    "declared_outcomes_equal": True,
                    "blind_array_descriptor_equalities": (blind_descriptor_equalities),
                    "boundary_specific_identity_equalities": (
                        boundary_specific_identity_equalities
                    ),
                }
            )
            agreement_rows.append(
                {
                    "selection_seed": seed,
                    "control_id": control,
                    "state_geometry_warp_level": state_warp,
                    "structured_observation_perturbation_level": observation,
                    "field_graph_id": graph,
                    "central_core_cell_id": left_id,
                    "wide_core_cell_id": right_id,
                    **comparisons,
                    "declared_outcomes_equal": True,
                    "blind_array_descriptor_equalities": (blind_descriptor_equalities),
                    "boundary_specific_identity_equalities": (
                        boundary_specific_identity_equalities
                    ),
                }
            )
        matrix_rows.append(
            {
                "selection_seed": seed,
                "control_id": control,
                "state_geometry_warp_level": state_warp,
                "structured_observation_perturbation_level": observation,
                "d2_scientific_input_fingerprint_sha256": fingerprint,
                "expected_disposition": _text(
                    central.get("expected_disposition"), label="D2 expected_disposition"
                ),
                "attempt_status": _text(
                    central.get("attempt_status"), label="D2 attempt_status"
                ),
                "prediction_class": _text(
                    central.get("prediction_class"), label="D2 prediction_class"
                ),
                "state": _text(central.get("state"), label="D2 state"),
                "reason_codes": _reason_codes(
                    central.get("reason_codes"), label="D2 reason_codes"
                ),
                "boundary_primary_unit_ids": {
                    "central": _text(
                        central.get("primary_unit_id"),
                        label="D2 central primary_unit_id",
                    ),
                    "wide": _text(
                        wide.get("primary_unit_id"), label="D2 wide primary_unit_id"
                    ),
                },
                "graph_rows": graph_rows,
            }
        )
    expected_counts = {
        "expected_disposition": Counter(
            {"localized_core": 16, "no_core": 8, "prerequisite_failure": 8}
        ),
        "prediction_class": Counter({"localized_core": 16, "no_core": 8, "abstain": 8}),
        "attempt_status": Counter({"evaluable": 24, "insufficient": 8}),
        "state": Counter({"pass": 32}),
    }
    for field, expected in expected_counts.items():
        observed = Counter(str(row[field]) for row in matrix_rows)
        if observed != expected:
            _fail(f"D2 {field} counts differ from the frozen 32-unit matrix")
    if len(matrix_rows) != 32 or len(agreement_rows) != 96:
        _fail("D2 outputs must contain 32 units and 96 graph comparisons")
    matrix_output = _output(
        6,
        status="available",
        row_count=32,
        data={
            "rows": matrix_rows,
            "nested_graph_row_count": 96,
            "expected_disposition_counts": dict(
                expected_counts["expected_disposition"]
            ),
            "prediction_class_counts": dict(expected_counts["prediction_class"]),
            "attempt_status_counts": dict(expected_counts["attempt_status"]),
        },
    )
    agreement_output = _output(
        7,
        status="available",
        row_count=96,
        data={
            "rows": agreement_rows,
            "comparison_scope": (
                "declared-outcomes-and-blind-array-descriptors-"
                "not-byte-or-graph-identity"
            ),
            "all_declared_outcomes_equal": True,
            "all_blind_array_descriptors_equal": True,
            "blind_array_descriptor_fields": [
                "amplitude",
                "identifiability_score",
                "support_counts",
            ],
            "boundary_specific_identity_fields_expected_to_differ": [
                "blind_input_fingerprint_sha256",
                "field_estimate_fingerprint_sha256",
                "field_graph_fingerprint_sha256",
                "oracle_fingerprint_sha256",
                "prediction_fingerprint_sha256",
            ],
        },
    )
    return matrix_output, agreement_output, matrix_rows, receipts_by_id


def _derive_d2_separation(
    *,
    terminal: dict[str, object],
    matrix_rows: list[dict[str, object]],
    receipts_by_id: dict[str, dict[str, object]],
) -> dict[str, object]:
    bundle = _mapping(terminal.get("evidence_bundle"), label="terminal evidence_bundle")
    matrix = _mapping(
        bundle.get("d2_confounder_matrix_receipt"), label="D2 confounder matrix"
    )
    cells = _sequence(matrix.get("cells"), label="D2 confounder cells")
    if len(cells) != 6 or matrix.get("state") != "pass":
        _fail("D2 confounder matrix must contain six passing cells")
    field_graphs = _sequence(
        matrix.get("field_graph_ids"), label="D2 confounder graphs"
    )
    if tuple(field_graphs) != _FIELD_GRAPHS:
        _fail("D2 confounder graph universe differs from the frozen design")
    partial_rows: list[dict[str, object]] = []
    confounder_counts: Counter[str] = Counter()
    for raw in cells:
        cell = _mapping(raw, label="D2 confounder cell")
        observation = _mapping(
            cell.get("construction_observation"), label="D2 construction_observation"
        )
        sealed = _mapping(
            cell.get("sealed_prediction_receipt"), label="D2 confounder prediction"
        )
        confounder_id = _text(cell.get("confounder_id"), label="D2 confounder_id")
        confounder_counts[confounder_id] += 1
        partial_rows.append(
            {
                "confounder_id": confounder_id,
                "construction_id": _text(
                    cell.get("construction_id"), label="D2 confounder construction_id"
                ),
                "field_graph_id": _text(
                    cell.get("field_graph_id"), label="D2 confounder field_graph_id"
                ),
                "probe_row": _plain_int(
                    observation.get("probe_row"), label="D2 confounder probe_row"
                ),
                "probe_row_role": _text(
                    observation.get("probe_row_role"),
                    label="D2 confounder probe_row_role",
                ),
                "probe_amplitude": _finite(
                    observation.get("probe_amplitude"), label="D2 probe_amplitude"
                ),
                "probe_identifiability_score": _finite(
                    observation.get("probe_identifiability_score"),
                    label="D2 probe_identifiability_score",
                ),
                "probe_measurement_support": _plain_int(
                    observation.get("probe_measurement_support"),
                    label="D2 probe_measurement_support",
                ),
                "core_amplitude_ceiling": _finite(
                    observation.get("core_amplitude_ceiling"),
                    label="D2 core_amplitude_ceiling",
                ),
                "identifiability_floor": _finite(
                    observation.get("identifiability_floor"),
                    label="D2 identifiability_floor",
                ),
                "minimum_support_count": _plain_int(
                    observation.get("minimum_support_count"),
                    label="D2 minimum_support_count",
                ),
                "core_amplitude_threshold_satisfied": _boolean(
                    observation.get("core_amplitude_threshold_satisfied"),
                    label="D2 amplitude threshold flag",
                ),
                "direction_loss_threshold_satisfied": _boolean(
                    observation.get("direction_loss_threshold_satisfied"),
                    label="D2 direction threshold flag",
                ),
                "measurement_support_threshold_satisfied": _boolean(
                    observation.get("measurement_support_threshold_satisfied"),
                    label="D2 support threshold flag",
                ),
                "expected_attempt_status": _text(
                    cell.get("expected_attempt_status"),
                    label="D2 expected_attempt_status",
                ),
                "expected_prediction_class": _text(
                    cell.get("expected_prediction_class"),
                    label="D2 expected_prediction_class",
                ),
                "expected_reason_codes": _reason_codes(
                    cell.get("expected_reason_codes"),
                    label="D2 expected_reason_codes",
                ),
                "observed_attempt_status": _text(
                    sealed.get("observed_attempt_status"),
                    label="D2 observed_attempt_status",
                ),
                "observed_prediction_class": _text(
                    sealed.get("prediction_class"), label="D2 observed prediction_class"
                ),
                "observed_reason_codes": _reason_codes(
                    sealed.get("reason_codes"), label="D2 observed reason_codes"
                ),
                "state": _text(cell.get("state"), label="D2 confounder state"),
            }
        )
    if sorted(confounder_counts.values()) != [3, 3]:
        _fail("D2 confounder matrix must contain two three-graph constructions")

    descriptor_fields = ("amplitude", "identifiability_score", "support_counts")
    for receipt in receipts_by_id.values():
        blind = _mapping(receipt.get("blind_input_receipt"), label="D2 blind input")
        if (
            blind.get("record_scope") != "in-memory-fingerprint-only"
            or blind.get("persistence_round_trip_supported") is not False
        ):
            _fail("D2 main blind input unexpectedly claims persisted values")
        for field in descriptor_fields:
            descriptor = _mapping(blind.get(field), label=f"D2 blind input {field}")
            _exact_keys(descriptor, {"dtype", "shape", "sha256"}, label=f"D2 {field}")
            _text(descriptor.get("dtype"), label=f"D2 {field} dtype")
            shape = _sequence(descriptor.get("shape"), label=f"D2 {field} shape")
            if not shape or any(type(item) is not int or item <= 0 for item in shape):
                _fail(f"D2 {field} shape is invalid")
            _sha256(descriptor.get("sha256"), label=f"D2 {field} sha256")
    if len(matrix_rows) != 32 or len(receipts_by_id) != 192:
        _fail("D2 missing-scope accounting differs from 32 units / 192 receipts")
    blocked = [
        "historical-main-d2-amplitude-identifiability-support-values-not-persisted"
    ]
    return _output(
        8,
        status="blocked",
        row_count=6,
        data={
            "full_scope_status": "blocked",
            "partial_rows": partial_rows,
            "partial_row_count": 6,
            "missing_scientific_unit_count": 32,
            "missing_field_graph_row_count": 96,
            "persisted_descriptor_bundle_count": 192,
            "persisted_relevant_array_descriptor_count": 576,
            "rerun_or_current_code_reconstruction_performed": False,
        },
        blocked_reason_codes=blocked,
    )


def _obligations(
    receipt: dict[str, object], *, label: str
) -> dict[str, dict[str, object]]:
    raw = _sequence(receipt.get("obligation_receipts"), label=f"{label} obligations")
    result: dict[str, dict[str, object]] = {}
    for value in raw:
        wrapper = _mapping(value, label=f"{label} obligation wrapper")
        obligation_id = _text(
            wrapper.get("obligation_id"), label=f"{label} obligation_id"
        )
        if obligation_id in result:
            _fail(f"{label} obligation_id is duplicated")
        result[obligation_id] = _mapping(
            wrapper.get("receipt"), label=f"{label} {obligation_id} receipt"
        )
    return result


def _derive_d3(
    runtime: dict[str, dict[str, object]],
) -> tuple[dict[str, object], dict[str, object], dict[str, object], dict[str, object]]:
    cartesian = runtime[_D3_CARTESIAN]
    representation = runtime[_D3_REPRESENTATION]
    cart_obligations = _obligations(cartesian, label="Cartesian D3")
    rep_obligations = _obligations(representation, label="representation D3")
    if tuple(cart_obligations) != (
        "ambient-signed-permutation",
        "loop-reversal",
        "reference-reflection",
        "reference-rotation",
    ):
        _fail("Cartesian D3 obligation order differs from the frozen contract")
    if tuple(rep_obligations) != (
        "ambient-signed-permutation",
        "local-frame-gauge",
        "loop-reversal",
        "nonorientable-control",
        "reference-orientation",
        "spin-two-double-angle",
    ):
        _fail("representation D3 obligation order differs from the frozen contract")
    cart_ambient = cart_obligations["ambient-signed-permutation"]
    rep_ambient = rep_obligations["ambient-signed-permutation"]
    rep_aggregate = _mapping(
        representation.get("aggregate_runtime_receipt"),
        label="representation D3 aggregate",
    )
    pipeline_checks = _sequence(
        rep_aggregate.get("pipeline_checks"), label="representation D3 pipeline_checks"
    )
    if len(pipeline_checks) != 3:
        _fail("representation D3 must contain three graph pipeline checks")
    pipeline_documents = [
        _mapping(value, label="representation D3 pipeline check")
        for value in pipeline_checks
    ]
    if (
        tuple(item.get("field_graph_id") for item in pipeline_documents)
        != _FIELD_GRAPHS
    ):
        _fail("representation D3 pipeline graph order differs")
    ambient_errors = [
        _finite(
            _mapping(item.get("errors"), label="representation D3 errors").get(
                "ambient_equivariance"
            ),
            label="representation D3 ambient_equivariance",
        )
        for item in pipeline_documents
    ]
    ambient_rows = [
        {
            "family_evidence_id": _D3_CARTESIAN,
            "law": _text(cart_ambient.get("law"), label="Cartesian ambient law"),
            "source_check_count": 1,
            "observed_error": None,
            "pipeline_ambient_equivariance_max": None,
            "maximum_distance_error": _finite(
                cart_ambient.get("maximum_distance_error"),
                label="Cartesian ambient distance error",
            ),
            "maximum_field_law_error": _finite(
                cart_ambient.get("maximum_field_law_error"),
                label="Cartesian ambient field error",
            ),
            "maximum_loop_law_error": _finite(
                cart_ambient.get("maximum_loop_law_error"),
                label="Cartesian ambient loop error",
            ),
            "tolerance": _finite(
                cart_ambient.get("tolerance"), label="Cartesian ambient tolerance"
            ),
            "state": _text(cart_ambient.get("state"), label="Cartesian ambient state"),
            "verified": cart_ambient.get("pipeline_rerun_verified") is True,
        },
        {
            "family_evidence_id": _D3_REPRESENTATION,
            "law": _text(rep_ambient.get("law"), label="representation ambient law"),
            "source_check_count": 4,
            "observed_error": _finite(
                rep_ambient.get("observed_error"),
                label="representation ambient observed_error",
            ),
            "pipeline_ambient_equivariance_max": max(ambient_errors),
            "maximum_distance_error": None,
            "maximum_field_law_error": None,
            "maximum_loop_law_error": None,
            "tolerance": _finite(
                rep_ambient.get("tolerance"), label="representation ambient tolerance"
            ),
            "state": _text(
                rep_ambient.get("state"), label="representation ambient state"
            ),
            "verified": all(
                item.get("verified") is True for item in pipeline_documents
            ),
        },
    ]
    if any(
        row["state"] != "pass" or row["verified"] is not True for row in ambient_rows
    ):
        _fail("D3 ambient-basis evidence is not fully verified")
    ambient_output = _output(
        9, status="available", row_count=2, data={"rows": ambient_rows}
    )

    loop_variants = _sequence(
        rep_aggregate.get("loop_variant_checks"),
        label="representation D3 loop_variant_checks",
    )
    if len(loop_variants) != 27:
        _fail("representation D3 must contain 27 crossed loop variants")
    variants = [
        _mapping(value, label="representation D3 loop variant")
        for value in loop_variants
    ]

    def cart_law_row(obligation_id: str) -> dict[str, object]:
        receipt = cart_obligations[obligation_id]
        if (
            receipt.get("state") != "pass"
            or receipt.get("pipeline_rerun_verified") is not True
        ):
            _fail(f"Cartesian D3 {obligation_id} is not verified")
        return {
            "family_evidence_id": _D3_CARTESIAN,
            "law": _text(receipt.get("law"), label=f"Cartesian {obligation_id} law"),
            "source_check_count": 1,
            "maximum_field_law_error": _finite(
                receipt.get("maximum_field_law_error"),
                label=f"Cartesian {obligation_id} field error",
            ),
            "maximum_loop_or_signed_total_error": _finite(
                receipt.get("maximum_loop_law_error"),
                label=f"Cartesian {obligation_id} loop error",
            ),
            "tolerance": _finite(
                receipt.get("tolerance"), label=f"Cartesian {obligation_id} tolerance"
            ),
            "expected_orientation_sign": _plain_int(
                receipt.get("expected_loop_orientation_sign"),
                label=f"Cartesian {obligation_id} orientation sign",
            ),
            "all_verified": True,
        }

    def rep_law_row(law: str) -> dict[str, object]:
        selected = [item for item in variants if item.get("law") == law]
        if len(selected) != 9:
            _fail(f"representation D3 {law} must contain nine A-by-B checks")
        pairs = [
            (
                _text(item.get("field_graph_id"), label=f"{law} field graph"),
                _text(item.get("cycle_graph_id"), label=f"{law} cycle graph"),
            )
            for item in selected
        ]
        if len(set(pairs)) != 9:
            _fail(f"representation D3 {law} A-by-B pairs are not unique")
        signs = {
            _finite(item.get("orientation_determinant"), label=f"{law} determinant")
            for item in selected
        }
        if len(signs) != 1:
            _fail(f"representation D3 {law} determinant is inconsistent")
        sign = signs.pop()
        errors = [
            _finite(
                item.get("signed_total_error_cycles"), label=f"{law} signed total error"
            )
            for item in selected
        ]
        tolerances = {
            _finite(item.get("tolerance"), label=f"{law} tolerance")
            for item in selected
        }
        if len(tolerances) != 1 or any(
            item.get("verified") is not True for item in selected
        ):
            _fail(f"representation D3 {law} is not uniformly verified")
        return {
            "family_evidence_id": _D3_REPRESENTATION,
            "law": law,
            "source_check_count": 9,
            "maximum_field_law_error": None,
            "maximum_loop_or_signed_total_error": max(errors),
            "tolerance": tolerances.pop(),
            "expected_orientation_sign": int(sign),
            "all_verified": True,
        }

    o2_rows = [
        cart_law_row("reference-rotation"),
        cart_law_row("reference-reflection"),
        rep_law_row("reference_rotation"),
        rep_law_row("reference_reflection"),
    ]
    if [row["expected_orientation_sign"] for row in o2_rows] != [1, -1, 1, -1]:
        _fail("D3 reference O(2) determinant/sign sequence differs")
    o2_output = _output(10, status="available", row_count=4, data={"rows": o2_rows})

    reversal_rows = [cart_law_row("loop-reversal"), rep_law_row("loop_reversal")]
    if any(row["expected_orientation_sign"] != -1 for row in reversal_rows):
        _fail("D3 loop-reversal rows must carry orientation sign -1")
    reversal_output = _output(
        11, status="available", row_count=2, data={"rows": reversal_rows}
    )

    separation_rows: list[dict[str, object]] = []
    for obligation_id, receipt in cart_obligations.items():
        separation_rows.append(
            {
                "family_evidence_id": _D3_CARTESIAN,
                "row_id": obligation_id,
                "law": _text(
                    receipt.get("law"), label=f"Cartesian {obligation_id} law"
                ),
                "source_check_count": 1,
                "structural_checks": {
                    "all_graph_adjacencies_verified": _boolean(
                        receipt.get("all_graph_adjacencies_verified"),
                        label=f"Cartesian {obligation_id} adjacency flag",
                    ),
                    "all_graph_edge_distances_bit_identical": _boolean(
                        receipt.get("all_graph_edge_distances_bit_identical"),
                        label=f"Cartesian {obligation_id} distance flag",
                    ),
                    "maximum_distance_error": _finite(
                        receipt.get("maximum_distance_error"),
                        label=f"Cartesian {obligation_id} distance error",
                    ),
                },
                "alignment_errors": {},
                "observable_law_errors": {
                    "maximum_field_law_error": _finite(
                        receipt.get("maximum_field_law_error"),
                        label=f"Cartesian {obligation_id} field error",
                    ),
                    "maximum_loop_law_error": _finite(
                        receipt.get("maximum_loop_law_error"),
                        label=f"Cartesian {obligation_id} loop error",
                    ),
                },
                "determinant_or_sign": _plain_int(
                    receipt.get("expected_loop_orientation_sign"),
                    label=f"Cartesian {obligation_id} sign",
                ),
                "tolerance": _finite(
                    receipt.get("tolerance"),
                    label=f"Cartesian {obligation_id} tolerance",
                ),
                "state": _text(
                    receipt.get("state"), label=f"Cartesian {obligation_id} state"
                ),
                "verified": receipt.get("pipeline_rerun_verified") is True,
            }
        )
    expected_error_keys = {
        "alignment_determinant_unit",
        "alignment_orthogonality",
        "ambient_equivariance",
        "amplitude",
        "coherence",
        "identifiability",
        "section_gauge_alignment",
    }
    for check in pipeline_documents:
        graph = _text(
            check.get("field_graph_id"), label="representation D3 field graph"
        )
        errors = _mapping(
            check.get("errors"), label=f"representation D3 {graph} errors"
        )
        _exact_keys(
            errors, expected_error_keys, label=f"representation D3 {graph} errors"
        )
        crossed = _sequence(
            check.get("crossed_loop_checks"),
            label=f"representation D3 {graph} crossed loops",
        )
        if len(crossed) != 3:
            _fail("representation D3 pipeline row must contain three cycle graphs")
        loop_errors = [
            _finite(
                _mapping(value, label="representation D3 crossed loop").get(
                    "signed_total_error_cycles"
                ),
                label="representation D3 crossed loop error",
            )
            for value in crossed
        ]
        separation_rows.append(
            {
                "family_evidence_id": _D3_REPRESENTATION,
                "row_id": graph,
                "law": "ambient_o2_alignment",
                "source_check_count": 3,
                "structural_checks": {
                    "adjacency_equal": _boolean(
                        check.get("adjacency_equal"), label=f"{graph} adjacency_equal"
                    ),
                    "edge_distances_bit_identical": _boolean(
                        check.get("edge_distances_bit_identical"),
                        label=f"{graph} edge distances",
                    ),
                    "support_equal": _boolean(
                        check.get("support_equal"), label=f"{graph} support_equal"
                    ),
                },
                "alignment_errors": {
                    name: _finite(errors[name], label=f"{graph} {name}")
                    for name in (
                        "alignment_determinant_unit",
                        "alignment_orthogonality",
                    )
                },
                "observable_law_errors": {
                    name: _finite(errors[name], label=f"{graph} {name}")
                    for name in (
                        "ambient_equivariance",
                        "amplitude",
                        "coherence",
                        "identifiability",
                        "section_gauge_alignment",
                    )
                }
                | {"maximum_crossed_loop_signed_total_error_cycles": max(loop_errors)},
                "determinant_or_sign": _finite(
                    check.get("alignment_determinant"), label=f"{graph} determinant"
                ),
                "tolerance": _finite(
                    rep_aggregate.get("tolerance"), label="representation D3 tolerance"
                ),
                "state": "pass" if check.get("verified") is True else "fail",
                "verified": check.get("verified") is True,
            }
        )
    if len(separation_rows) != 7 or any(
        row["verified"] is not True or row["state"] != "pass" for row in separation_rows
    ):
        _fail("D3 array/observable separation must contain seven verified rows")
    separation_output = _output(
        12,
        status="available",
        row_count=7,
        data={"rows": separation_rows},
    )
    return ambient_output, o2_output, reversal_output, separation_output


def derive_outputs_01_12(
    *,
    plan: dict,
    protocol: dict,
    terminal: dict,
    manifest: dict,
    consumption: dict,
    d6_decision: dict,
    runtime_freeze_row: dict,
) -> list[dict]:
    """Derive frozen descriptive outputs 1--12 from already-opened parents.

    The function is intentionally value-preserving.  It does not execute an
    estimator, reconstruct fingerprint-only arrays, access D7/subject/model
    values, or grant any scientific/operational authority.
    """

    inputs = {
        "plan": plan,
        "protocol": protocol,
        "terminal": terminal,
        "manifest": manifest,
        "consumption": consumption,
        "d6_decision": d6_decision,
        "runtime_freeze_row": runtime_freeze_row,
    }
    for label, value in inputs.items():
        if not isinstance(value, dict) or any(
            not isinstance(key, str) for key in value
        ):
            raise TypeError(f"{label} must be a dict with string keys")
    _frozen_output_ids(plan)
    if plan.get("analysis_class") != "postselection_descriptive_only":
        _fail("plan is not the frozen postselection-only analysis")
    if terminal.get("claim_ceiling") != "level_0":
        _fail("terminal claim ceiling differs from Level 0")
    if any(
        terminal.get(name) is not False
        for name in (
            "hidden_confirmation_accessed",
            "pythia_accessed",
            "subject_accessed",
            "semantic_labels_accessed",
            "integer_claimed",
            "localized_core_loop_join_established",
        )
    ):
        _fail("terminal exceeds the allowed post-D6 descriptive boundary")

    runtime = _runtime_receipts(terminal)
    output_1 = _derive_parent_identity(
        plan=plan,
        protocol=protocol,
        terminal=terminal,
        manifest=manifest,
        consumption=consumption,
        d6_decision=d6_decision,
        runtime_freeze_row=runtime_freeze_row,
    )
    output_2 = _derive_gate_scope(terminal, d6_decision)
    output_3 = _derive_non_claim(plan)
    output_4, output_5 = _derive_d1(runtime)
    output_6, output_7, matrix_rows, receipts_by_id = _derive_d2_main(terminal)
    output_8 = _derive_d2_separation(
        terminal=terminal,
        matrix_rows=matrix_rows,
        receipts_by_id=receipts_by_id,
    )
    output_9, output_10, output_11, output_12 = _derive_d3(runtime)
    outputs = [
        output_1,
        output_2,
        output_3,
        output_4,
        output_5,
        output_6,
        output_7,
        output_8,
        output_9,
        output_10,
        output_11,
        output_12,
    ]
    if [item["sequence"] for item in outputs] != list(range(1, 13)) or [
        item["output_id"] for item in outputs
    ] != list(_OUTPUT_IDS):
        _fail("derived post-D6 output order differs from the frozen plan")
    if [item["status"] for item in outputs] != [
        "available",
        "available",
        "available",
        "available",
        "available",
        "available",
        "available",
        "blocked",
        "available",
        "available",
        "available",
        "available",
    ]:
        _fail("post-D6 outputs 1--12 have an unexpected availability pattern")
    return outputs
