"""Pure structural joins for D7 attempt records.

Absence-receipt hashes are future bindings, not freshness, subject, or stage
proof.  No loading, witness verification, persistence, authority, or execution
is performed here.
"""

from __future__ import annotations

from typing import Protocol

from . import confirmation_attempt_records as r
from .common import QualificationContractError

_EXACT_RECORD_TYPES = {
    "declaration": r.D7AttemptDeclarationRecord,
    "authorization": r.D7LaunchAuthorizationRecord,
    "claim": r.D7AttemptClaimRecord,
    "start": r.D7ExecutionStartRecord,
    "payload": r.D7ScientificResultPayload,
    "result": r.D7ScientificResultRecord,
    "evidence": r.D7FailureEvidenceRecord,
    "finalization": r.D7StartedUnresolvedFinalizationRecord,
    "failed_attempt": r.D7FailedAttemptRecord,
    "manifest": r.D7TerminalManifestRecord,
    "consumption": r.D7TerminalConsumptionRecord,
}


class _Canonical(Protocol):
    schema_version: str
    canonical_bytes: bytes
    canonical_sha256: str


def _same(expected: object, observed: object, label: str) -> None:
    if type(expected) is not type(observed) or expected != observed:
        raise QualificationContractError(f"{label} differs across D7 records")


def _typed(value: object, expected: type[object], label: str) -> None:
    if type(value) is not expected:
        raise TypeError(f"{label} has the wrong D7 record type")


def _types(**values: object) -> None:
    for label, value in values.items():
        _typed(value, _EXACT_RECORD_TYPES[label], label)


def _names(value: str) -> tuple[str, ...]:
    return tuple(value.split())


def _join(*rows: tuple[str, object, object]) -> None:
    for label, expected, observed in rows:
        _same(expected, observed, label)


def _links(*rows: tuple[_Canonical, object, str]) -> None:
    for source, target, field in rows:
        _same(source.canonical_sha256, getattr(target, field), field)


def _distinct(label: str, *values: object) -> None:
    if len(set(values)) != len(values):
        raise QualificationContractError(f"{label} must differ")


def _fields(
    left: object, right: object, label: str, *names: str | tuple[str, str]
) -> None:
    for spec in names:
        left_name, right_name = (spec, spec) if isinstance(spec, str) else spec
        _same(
            getattr(left, left_name),
            getattr(right, right_name),
            f"{label} {right_name}",
        )


_COORDINATE_FIELDS = _names(
    "replay_target_sha256 attempt_key_sha256 execution_identity_receipt_sha256"
)


def validate_d7_attempt_prefix(
    *,
    declaration: r.D7AttemptDeclarationRecord,
    authorization: r.D7LaunchAuthorizationRecord,
    claim: r.D7AttemptClaimRecord,
    start: r.D7ExecutionStartRecord,
) -> None:
    _types(
        declaration=declaration,
        authorization=authorization,
        claim=claim,
        start=start,
    )
    _links(
        (declaration, authorization, "attempt_declaration_sha256"),
        (declaration, claim, "attempt_declaration_sha256"),
        (authorization, claim, "launch_authorization_sha256"),
        (declaration, start, "attempt_declaration_sha256"),
        (authorization, start, "launch_authorization_sha256"),
        (claim, start, "attempt_claim_sha256"),
    )
    _fields(
        declaration,
        authorization,
        "authorization",
        *_names(
            "replay_target_sha256 attempt_key_sha256 authorization_commit "
            "execution_identity_receipt_sha256 store_identity_sha256 "
            "output_namespace_identity_sha256 terminal_path_identity_sha256"
        ),
    )
    _fields(
        declaration,
        claim,
        "claim",
        *_names(
            "replay_target_sha256 attempt_key_sha256 "
            "execution_identity_receipt_sha256 store_identity_sha256"
        ),
    )
    _fields(
        declaration,
        start,
        "start",
        *_names(
            "replay_target_sha256 attempt_key_sha256 authorization_commit "
            "execution_identity_receipt_sha256 output_namespace_identity_sha256 "
            "terminal_path_identity_sha256"
        ),
    )
    _fields(
        authorization,
        start,
        "start",
        (
            "execution_source_runtime_receipt_sha256",
            "observed_execution_source_runtime_receipt_sha256",
        ),
        ("runtime_specification_sha256", "observed_runtime_specification_sha256"),
    )
    _distinct(
        "authorization/pre-start absence receipts",
        authorization.authorization_output_namespace_absence_receipt_sha256,
        authorization.authorization_terminal_path_absence_receipt_sha256,
        start.pre_start_output_namespace_absence_receipt_sha256,
        start.pre_start_terminal_path_absence_receipt_sha256,
    )
    _distinct(
        "identity, source/runtime, and runtime spec",
        declaration.execution_identity_receipt_sha256,
        authorization.execution_source_runtime_receipt_sha256,
        authorization.runtime_specification_sha256,
    )


def validate_d7_started_unresolved_finalization(
    *,
    start: r.D7ExecutionStartRecord,
    evidence: r.D7FailureEvidenceRecord,
    finalization: r.D7StartedUnresolvedFinalizationRecord,
) -> None:
    _types(start=start, evidence=evidence, finalization=finalization)
    if (
        evidence.failure_stage is not r.D7FailureStage.EVIDENCED_ABORT
        or evidence.origin is not r.D7FailureEvidenceOrigin.EXTERNAL
        or evidence.external_verification_receipt_sha256 is None
        or evidence.external_verification_receipt_byte_count is None
    ):
        raise QualificationContractError(
            "finalization requires external abort evidence and receipt"
        )
    _fields(start, evidence, "evidence", *_COORDINATE_FIELDS)
    _fields(start, finalization, "finalization", *_COORDINATE_FIELDS)
    _links(
        (start, evidence, "execution_start_sha256"),
        (start, finalization, "execution_start_sha256"),
        (evidence, finalization, "external_abort_evidence_sha256"),
    )
    _join(
        (
            "finalization receipt",
            evidence.external_verification_receipt_sha256,
            finalization.external_verification_receipt_sha256,
        ),
        (
            "finalization receipt size",
            evidence.external_verification_receipt_byte_count,
            finalization.external_verification_receipt_byte_count,
        ),
    )


def _member(
    filename: str,
    kind: r.D7TerminalMemberKind,
    contract_id: str,
    digest: str,
    byte_count: int,
) -> r.D7TerminalMemberBinding:
    return r.D7TerminalMemberBinding(filename, kind, contract_id, digest, byte_count)


def _record_member(
    filename: str, kind: r.D7TerminalMemberKind, value: _Canonical
) -> r.D7TerminalMemberBinding:
    return _member(
        filename,
        kind,
        value.schema_version,
        value.canonical_sha256,
        len(value.canonical_bytes),
    )


def _sorted_members(
    values: list[r.D7TerminalMemberBinding],
) -> tuple[r.D7TerminalMemberBinding, ...]:
    return tuple(sorted(values, key=lambda item: item.filename))


def _scientific_members(
    payload: r.D7ScientificResultPayload, result: r.D7ScientificResultRecord
) -> tuple[r.D7TerminalMemberBinding, ...]:
    members = [
        _record_member(
            r.D7_SCIENTIFIC_RESULT_FILENAME,
            r.D7TerminalMemberKind.SCIENTIFIC_RESULT,
            result,
        ),
        _record_member(
            r.D7_SCIENTIFIC_RESULT_PAYLOAD_FILENAME,
            r.D7TerminalMemberKind.SCIENTIFIC_RESULT_PAYLOAD,
            payload,
        ),
        *[
            _member(
                item.filename,
                r.D7TerminalMemberKind.RESULT_COMPONENT,
                item.component_contract_id,
                item.component_canonical_sha256,
                item.byte_count,
            )
            for item in payload.component_bindings
        ],
    ]
    return _sorted_members(members)


def _failure_members(
    evidence: r.D7FailureEvidenceRecord,
    failed: r.D7FailedAttemptRecord,
    finalization: r.D7StartedUnresolvedFinalizationRecord | None,
) -> tuple[r.D7TerminalMemberBinding, ...]:
    members = [
        _record_member(
            r.D7_FAILED_ATTEMPT_FILENAME,
            r.D7TerminalMemberKind.FAILED_ATTEMPT,
            failed,
        ),
        _record_member(
            r.D7_FAILURE_EVIDENCE_FILENAME,
            r.D7TerminalMemberKind.FAILURE_EVIDENCE,
            evidence,
        ),
        _member(
            r.D7_FAILURE_EVIDENCE_PAYLOAD_FILENAME,
            r.D7TerminalMemberKind.FAILURE_EVIDENCE_PAYLOAD,
            r.D7_FAILURE_EVIDENCE_PAYLOAD_CONTRACT_ID,
            evidence.evidence_payload_sha256,
            evidence.evidence_payload_byte_count,
        ),
    ]
    if finalization is not None:
        if (
            evidence.external_verification_receipt_sha256 is None
            or evidence.external_verification_receipt_byte_count is None
        ):
            raise QualificationContractError(
                "external finalization lacks receipt binding"
            )
        members.extend(
            [
                _record_member(
                    r.D7_STARTED_UNRESOLVED_FINALIZATION_FILENAME,
                    r.D7TerminalMemberKind.STARTED_UNRESOLVED_FINALIZATION,
                    finalization,
                ),
                _member(
                    r.D7_EXTERNAL_ABORT_VERIFICATION_RECEIPT_FILENAME,
                    r.D7TerminalMemberKind.EXTERNAL_ABORT_VERIFICATION_RECEIPT,
                    r.D7_EXTERNAL_ABORT_VERIFICATION_RECEIPT_CONTRACT_ID,
                    evidence.external_verification_receipt_sha256,
                    evidence.external_verification_receipt_byte_count,
                ),
            ]
        )
    return _sorted_members(members)


def _validate_terminal_common(
    *,
    claim: r.D7AttemptClaimRecord,
    start: r.D7ExecutionStartRecord,
    manifest: r.D7TerminalManifestRecord,
    consumption: r.D7TerminalConsumptionRecord,
    kind: r.D7TerminalArtifactKind,
    artifact_sha256: str,
    members: tuple[r.D7TerminalMemberBinding, ...],
) -> None:
    _fields(claim, start, "start", *_COORDINATE_FIELDS)
    _fields(start, manifest, "manifest", *_COORDINATE_FIELDS)
    _fields(start, consumption, "consumption", *_COORDINATE_FIELDS)
    _links(
        (claim, start, "attempt_claim_sha256"),
        (claim, manifest, "attempt_claim_sha256"),
        (start, manifest, "execution_start_sha256"),
        (claim, consumption, "attempt_claim_sha256"),
        (start, consumption, "execution_start_sha256"),
        (manifest, consumption, "terminal_manifest_sha256"),
    )
    _join(
        ("manifest kind", kind, manifest.terminal_artifact_kind),
        ("manifest artifact", artifact_sha256, manifest.terminal_artifact_sha256),
        ("manifest members", members, manifest.immutable_members),
        ("consumption kind", kind, consumption.terminal_artifact_kind),
        ("consumption artifact", artifact_sha256, consumption.terminal_artifact_sha256),
    )


def validate_d7_scientific_terminal_chain(
    *,
    claim: r.D7AttemptClaimRecord,
    start: r.D7ExecutionStartRecord,
    payload: r.D7ScientificResultPayload,
    result: r.D7ScientificResultRecord,
    manifest: r.D7TerminalManifestRecord,
    consumption: r.D7TerminalConsumptionRecord,
) -> None:
    _types(
        claim=claim,
        start=start,
        payload=payload,
        result=result,
        manifest=manifest,
        consumption=consumption,
    )
    _fields(
        start,
        result,
        "result",
        *_names(
            "replay_target_sha256 attempt_key_sha256 execution_identity_receipt_sha256"
        ),
    )
    _links(
        (start, result, "execution_start_sha256"),
        (payload, result, "result_payload_sha256"),
    )
    _join(
        ("payload target", start.replay_target_sha256, payload.replay_target_sha256),
        (
            "result payload size",
            len(payload.canonical_bytes),
            result.result_payload_byte_count,
        ),
        (
            "scientific access",
            r.D7ConfirmationValueAccessState.OBSERVED,
            consumption.confirmation_value_access_state,
        ),
    )
    _validate_terminal_common(
        claim=claim,
        start=start,
        manifest=manifest,
        consumption=consumption,
        kind=r.D7TerminalArtifactKind.SCIENTIFIC_RESULT,
        artifact_sha256=result.canonical_sha256,
        members=_scientific_members(payload, result),
    )


def validate_d7_failed_terminal_chain(
    *,
    claim: r.D7AttemptClaimRecord,
    start: r.D7ExecutionStartRecord,
    evidence: r.D7FailureEvidenceRecord,
    failed_attempt: r.D7FailedAttemptRecord,
    manifest: r.D7TerminalManifestRecord,
    consumption: r.D7TerminalConsumptionRecord,
    finalization: r.D7StartedUnresolvedFinalizationRecord | None = None,
) -> None:
    _types(
        claim=claim,
        start=start,
        evidence=evidence,
        failed_attempt=failed_attempt,
        manifest=manifest,
        consumption=consumption,
    )
    if evidence.failure_stage is r.D7FailureStage.EVIDENCED_ABORT:
        if finalization is None:
            raise QualificationContractError("evidenced abort requires finalization")
        validate_d7_started_unresolved_finalization(
            start=start, evidence=evidence, finalization=finalization
        )
    elif finalization is not None:
        raise QualificationContractError("ordinary failure cannot carry finalization")
    _fields(start, evidence, "failure", *_COORDINATE_FIELDS)
    _fields(start, failed_attempt, "failed", *_COORDINATE_FIELDS)
    _links(
        (start, evidence, "execution_start_sha256"),
        (start, failed_attempt, "execution_start_sha256"),
        (evidence, failed_attempt, "failure_evidence_sha256"),
    )
    _join(
        ("failed stage", evidence.failure_stage, failed_attempt.failure_stage),
        (
            "failed finalization",
            None if finalization is None else finalization.canonical_sha256,
            failed_attempt.started_unresolved_finalization_sha256,
        ),
        (
            "failed access",
            failed_attempt.confirmation_value_access_state,
            consumption.confirmation_value_access_state,
        ),
    )
    if (
        failed_attempt.to_dict()["aggregate_outcome_observed"] is not False
        or consumption.to_dict()["aggregate_outcome_observed"] is not False
    ):
        raise QualificationContractError("failed terminal aggregate must be false")
    _validate_terminal_common(
        claim=claim,
        start=start,
        manifest=manifest,
        consumption=consumption,
        kind=r.D7TerminalArtifactKind.FAILED_ATTEMPT,
        artifact_sha256=failed_attempt.canonical_sha256,
        members=_failure_members(evidence, failed_attempt, finalization),
    )


def validate_d7_scientific_attempt_chain(
    *,
    declaration: r.D7AttemptDeclarationRecord,
    authorization: r.D7LaunchAuthorizationRecord,
    claim: r.D7AttemptClaimRecord,
    start: r.D7ExecutionStartRecord,
    payload: r.D7ScientificResultPayload,
    result: r.D7ScientificResultRecord,
    manifest: r.D7TerminalManifestRecord,
    consumption: r.D7TerminalConsumptionRecord,
) -> None:
    validate_d7_attempt_prefix(
        declaration=declaration, authorization=authorization, claim=claim, start=start
    )
    if declaration.attempt_role is not r.D7AttemptRole.PRIMARY_CONFIRMATION:
        raise QualificationContractError(
            "isolated replay requires the combined primary-and-replay validator"
        )
    validate_d7_scientific_terminal_chain(
        claim=claim,
        start=start,
        payload=payload,
        result=result,
        manifest=manifest,
        consumption=consumption,
    )


def validate_d7_isolated_replay_role_evidence(
    *,
    evidence: r.D7IsolatedReplayRoleEvidence,
    primary_declaration: r.D7AttemptDeclarationRecord,
    primary_authorization: r.D7LaunchAuthorizationRecord,
    primary_claim: r.D7AttemptClaimRecord,
    primary_start: r.D7ExecutionStartRecord,
    primary_payload: r.D7ScientificResultPayload,
    primary_result: r.D7ScientificResultRecord,
    primary_manifest: r.D7TerminalManifestRecord,
    primary_consumption: r.D7TerminalConsumptionRecord,
) -> None:
    _typed(evidence, r.D7IsolatedReplayRoleEvidence, "evidence")
    validate_d7_scientific_attempt_chain(
        declaration=primary_declaration,
        authorization=primary_authorization,
        claim=primary_claim,
        start=primary_start,
        payload=primary_payload,
        result=primary_result,
        manifest=primary_manifest,
        consumption=primary_consumption,
    )
    if (
        primary_declaration.attempt_role is not r.D7AttemptRole.PRIMARY_CONFIRMATION
        or primary_payload.state is not r.D7ScientificResultState.PASS
    ):
        raise QualificationContractError("isolated replay requires passed primary")
    pairs = (
        ("primary_replay_target_sha256", primary_declaration.replay_target_sha256),
        ("primary_attempt_key_sha256", primary_declaration.attempt_key_sha256),
        ("primary_attempt_declaration_sha256", primary_declaration.canonical_sha256),
        ("primary_launch_authorization_sha256", primary_authorization.canonical_sha256),
        ("primary_attempt_claim_sha256", primary_claim.canonical_sha256),
        ("primary_execution_start_sha256", primary_start.canonical_sha256),
        ("primary_result_payload_sha256", primary_payload.canonical_sha256),
        ("primary_scientific_result_sha256", primary_result.canonical_sha256),
        ("primary_terminal_manifest_sha256", primary_manifest.canonical_sha256),
        ("primary_terminal_consumption_sha256", primary_consumption.canonical_sha256),
    )
    for name, expected in pairs:
        _same(expected, getattr(evidence, name), name)


def validate_d7_isolated_replay_attempt_chain(
    *,
    declaration: r.D7AttemptDeclarationRecord,
    authorization: r.D7LaunchAuthorizationRecord,
    claim: r.D7AttemptClaimRecord,
    start: r.D7ExecutionStartRecord,
    payload: r.D7ScientificResultPayload,
    result: r.D7ScientificResultRecord,
    manifest: r.D7TerminalManifestRecord,
    consumption: r.D7TerminalConsumptionRecord,
    primary_declaration: r.D7AttemptDeclarationRecord,
    primary_authorization: r.D7LaunchAuthorizationRecord,
    primary_claim: r.D7AttemptClaimRecord,
    primary_start: r.D7ExecutionStartRecord,
    primary_payload: r.D7ScientificResultPayload,
    primary_result: r.D7ScientificResultRecord,
    primary_manifest: r.D7TerminalManifestRecord,
    primary_consumption: r.D7TerminalConsumptionRecord,
) -> None:
    if type(declaration.role_evidence) is not r.D7IsolatedReplayRoleEvidence:
        raise QualificationContractError(
            "isolated replay declaration requires typed primary role evidence"
        )
    validate_d7_isolated_replay_role_evidence(
        evidence=declaration.role_evidence,
        primary_declaration=primary_declaration,
        primary_authorization=primary_authorization,
        primary_claim=primary_claim,
        primary_start=primary_start,
        primary_payload=primary_payload,
        primary_result=primary_result,
        primary_manifest=primary_manifest,
        primary_consumption=primary_consumption,
    )
    validate_d7_attempt_prefix(
        declaration=declaration,
        authorization=authorization,
        claim=claim,
        start=start,
    )
    validate_d7_scientific_terminal_chain(
        claim=claim,
        start=start,
        payload=payload,
        result=result,
        manifest=manifest,
        consumption=consumption,
    )


def derive_d7_isolated_replay_role_evidence(
    *,
    primary_declaration: r.D7AttemptDeclarationRecord,
    primary_authorization: r.D7LaunchAuthorizationRecord,
    primary_claim: r.D7AttemptClaimRecord,
    primary_start: r.D7ExecutionStartRecord,
    primary_payload: r.D7ScientificResultPayload,
    primary_result: r.D7ScientificResultRecord,
    primary_manifest: r.D7TerminalManifestRecord,
    primary_consumption: r.D7TerminalConsumptionRecord,
) -> r.D7IsolatedReplayRoleEvidence:
    evidence = r.D7IsolatedReplayRoleEvidence(
        primary_declaration.replay_target_sha256,
        primary_declaration.attempt_key_sha256,
        primary_declaration.canonical_sha256,
        primary_authorization.canonical_sha256,
        primary_claim.canonical_sha256,
        primary_start.canonical_sha256,
        primary_payload.canonical_sha256,
        primary_result.canonical_sha256,
        primary_manifest.canonical_sha256,
        primary_consumption.canonical_sha256,
    )
    validate_d7_isolated_replay_role_evidence(
        evidence=evidence,
        primary_declaration=primary_declaration,
        primary_authorization=primary_authorization,
        primary_claim=primary_claim,
        primary_start=primary_start,
        primary_payload=primary_payload,
        primary_result=primary_result,
        primary_manifest=primary_manifest,
        primary_consumption=primary_consumption,
    )
    return evidence
