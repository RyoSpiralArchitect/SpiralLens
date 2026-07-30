"""Pure structural joins for canonical D7 attempt evidence bytes.

Passing these functions establishes schema and digest equality only.  It does
not prove that a filesystem observation occurred, authenticate an external
observer, authorize finalization, or grant scientific authority.
"""

from __future__ import annotations

from pathlib import PurePosixPath

from . import confirmation_attempt_evidence as e
from . import confirmation_attempt_records as r
from . import confirmation_attempt_validation as v
from .common import QualificationContractError

__all__: tuple[str, ...] = ()


def _exact(value: object, expected: type[object], label: str) -> None:
    if type(value) is not expected:
        raise TypeError(f"{label} must be an exact {expected.__name__}")


def _same(expected: object, observed: object, label: str) -> None:
    if type(expected) is not type(observed) or expected != observed:
        raise QualificationContractError(f"{label} differs")


def _physical_subject_key(
    receipt: e.D7AuthorizationPathAbsenceReceipt | e.D7PreStartPathAbsenceReceipt,
) -> tuple[int, int, str]:
    return (
        receipt.parent_device,
        receipt.parent_inode,
        receipt.subject_basename,
    )


def _paths_overlap(left: str, right: str) -> bool:
    left_path = PurePosixPath(left)
    right_path = PurePosixPath(right)
    return (
        left_path == right_path
        or left_path in right_path.parents
        or right_path in left_path.parents
    )


def _join_path_common(
    *,
    receipt: e.D7AuthorizationPathAbsenceReceipt | e.D7PreStartPathAbsenceReceipt,
    declaration: r.D7AttemptDeclarationRecord,
    path_identity_sha256: str,
    label: str,
) -> None:
    for field, expected in (
        ("replay_target_sha256", declaration.replay_target_sha256),
        ("attempt_key_sha256", declaration.attempt_key_sha256),
        ("attempt_declaration_sha256", declaration.canonical_sha256),
        ("authorization_commit", declaration.authorization_commit),
        (
            "execution_identity_receipt_sha256",
            declaration.execution_identity_receipt_sha256,
        ),
        ("store_identity_sha256", declaration.store_identity_sha256),
        ("subject_path_identity_sha256", path_identity_sha256),
    ):
        _same(expected, getattr(receipt, field), f"{label} {field}")


def validate_d7_authorization_path_absence_receipts(
    *,
    declaration: r.D7AttemptDeclarationRecord,
    authorization: r.D7LaunchAuthorizationRecord,
    output_namespace_receipt: e.D7AuthorizationPathAbsenceReceipt,
    terminal_path_receipt: e.D7AuthorizationPathAbsenceReceipt,
) -> None:
    """Join the two authorization-time observations without a hash cycle."""

    _exact(declaration, r.D7AttemptDeclarationRecord, "declaration")
    _exact(authorization, r.D7LaunchAuthorizationRecord, "authorization")
    _exact(
        output_namespace_receipt,
        e.D7AuthorizationPathAbsenceReceipt,
        "output_namespace_receipt",
    )
    _exact(
        terminal_path_receipt,
        e.D7AuthorizationPathAbsenceReceipt,
        "terminal_path_receipt",
    )
    _same(
        declaration.canonical_sha256,
        authorization.attempt_declaration_sha256,
        "authorization attempt declaration",
    )
    for field in (
        "replay_target_sha256",
        "attempt_key_sha256",
        "authorization_commit",
        "execution_identity_receipt_sha256",
        "store_identity_sha256",
        "output_namespace_identity_sha256",
        "terminal_path_identity_sha256",
    ):
        _same(
            getattr(declaration, field),
            getattr(authorization, field),
            f"authorization {field}",
        )
    _same(
        e.D7AbsentPathSubject.OUTPUT_NAMESPACE,
        output_namespace_receipt.subject_kind,
        "authorization output subject",
    )
    _same(
        e.D7AbsentPathSubject.TERMINAL_PATH,
        terminal_path_receipt.subject_kind,
        "authorization terminal subject",
    )
    _join_path_common(
        receipt=output_namespace_receipt,
        declaration=declaration,
        path_identity_sha256=declaration.output_namespace_identity_sha256,
        label="authorization output receipt",
    )
    _join_path_common(
        receipt=terminal_path_receipt,
        declaration=declaration,
        path_identity_sha256=declaration.terminal_path_identity_sha256,
        label="authorization terminal receipt",
    )
    _same(
        output_namespace_receipt.canonical_sha256,
        authorization.authorization_output_namespace_absence_receipt_sha256,
        "authorization output receipt digest",
    )
    _same(
        terminal_path_receipt.canonical_sha256,
        authorization.authorization_terminal_path_absence_receipt_sha256,
        "authorization terminal receipt digest",
    )
    if (
        output_namespace_receipt.subject_path == terminal_path_receipt.subject_path
        or _physical_subject_key(output_namespace_receipt)
        == _physical_subject_key(terminal_path_receipt)
    ):
        raise QualificationContractError(
            "authorization output namespace and terminal path must differ"
        )


def validate_d7_pre_start_path_absence_receipts(
    *,
    declaration: r.D7AttemptDeclarationRecord,
    authorization: r.D7LaunchAuthorizationRecord,
    claim: r.D7AttemptClaimRecord,
    start: r.D7ExecutionStartRecord,
    output_namespace_receipt: e.D7PreStartPathAbsenceReceipt,
    terminal_path_receipt: e.D7PreStartPathAbsenceReceipt,
) -> None:
    """Join the two immediate pre-start observations to the frozen claim."""

    v.validate_d7_attempt_prefix(
        declaration=declaration,
        authorization=authorization,
        claim=claim,
        start=start,
    )
    _exact(
        output_namespace_receipt,
        e.D7PreStartPathAbsenceReceipt,
        "output_namespace_receipt",
    )
    _exact(
        terminal_path_receipt,
        e.D7PreStartPathAbsenceReceipt,
        "terminal_path_receipt",
    )
    _same(
        e.D7AbsentPathSubject.OUTPUT_NAMESPACE,
        output_namespace_receipt.subject_kind,
        "pre-start output subject",
    )
    _same(
        e.D7AbsentPathSubject.TERMINAL_PATH,
        terminal_path_receipt.subject_kind,
        "pre-start terminal subject",
    )
    for receipt, path_identity, label in (
        (
            output_namespace_receipt,
            declaration.output_namespace_identity_sha256,
            "pre-start output receipt",
        ),
        (
            terminal_path_receipt,
            declaration.terminal_path_identity_sha256,
            "pre-start terminal receipt",
        ),
    ):
        _join_path_common(
            receipt=receipt,
            declaration=declaration,
            path_identity_sha256=path_identity,
            label=label,
        )
        _same(
            authorization.canonical_sha256,
            receipt.launch_authorization_sha256,
            f"{label} launch_authorization_sha256",
        )
        _same(
            claim.canonical_sha256,
            receipt.attempt_claim_sha256,
            f"{label} attempt_claim_sha256",
        )
    _same(
        output_namespace_receipt.canonical_sha256,
        start.pre_start_output_namespace_absence_receipt_sha256,
        "pre-start output receipt digest",
    )
    _same(
        terminal_path_receipt.canonical_sha256,
        start.pre_start_terminal_path_absence_receipt_sha256,
        "pre-start terminal receipt digest",
    )
    if (
        output_namespace_receipt.subject_path == terminal_path_receipt.subject_path
        or _physical_subject_key(output_namespace_receipt)
        == _physical_subject_key(terminal_path_receipt)
    ):
        raise QualificationContractError(
            "pre-start output namespace and terminal path must differ"
        )


def validate_d7_path_absence_receipt_chain(
    *,
    declaration: r.D7AttemptDeclarationRecord,
    authorization: r.D7LaunchAuthorizationRecord,
    claim: r.D7AttemptClaimRecord,
    start: r.D7ExecutionStartRecord,
    authorization_output_receipt: e.D7AuthorizationPathAbsenceReceipt,
    authorization_terminal_receipt: e.D7AuthorizationPathAbsenceReceipt,
    pre_start_output_receipt: e.D7PreStartPathAbsenceReceipt,
    pre_start_terminal_receipt: e.D7PreStartPathAbsenceReceipt,
) -> None:
    """Validate both point-in-time observations and their parent continuity."""

    validate_d7_authorization_path_absence_receipts(
        declaration=declaration,
        authorization=authorization,
        output_namespace_receipt=authorization_output_receipt,
        terminal_path_receipt=authorization_terminal_receipt,
    )
    validate_d7_pre_start_path_absence_receipts(
        declaration=declaration,
        authorization=authorization,
        claim=claim,
        start=start,
        output_namespace_receipt=pre_start_output_receipt,
        terminal_path_receipt=pre_start_terminal_receipt,
    )
    for authorization_receipt, pre_start_receipt, label in (
        (
            authorization_output_receipt,
            pre_start_output_receipt,
            "output namespace",
        ),
        (
            authorization_terminal_receipt,
            pre_start_terminal_receipt,
            "terminal path",
        ),
    ):
        for field in (
            "store_root_realpath",
            "resolved_parent_realpath",
            "subject_basename",
            "parent_device",
            "parent_inode",
        ):
            _same(
                getattr(authorization_receipt, field),
                getattr(pre_start_receipt, field),
                f"{label} {field} continuity",
            )


def validate_d7_isolated_replay_path_disjointness(
    *,
    primary_authorization_output: e.D7AuthorizationPathAbsenceReceipt,
    primary_authorization_terminal: e.D7AuthorizationPathAbsenceReceipt,
    primary_pre_start_output: e.D7PreStartPathAbsenceReceipt,
    primary_pre_start_terminal: e.D7PreStartPathAbsenceReceipt,
    replay_authorization_output: e.D7AuthorizationPathAbsenceReceipt,
    replay_authorization_terminal: e.D7AuthorizationPathAbsenceReceipt,
    replay_pre_start_output: e.D7PreStartPathAbsenceReceipt,
    replay_pre_start_terminal: e.D7PreStartPathAbsenceReceipt,
) -> None:
    """Reject realpath aliases; post-publication inode checks remain separate."""

    receipts = (
        primary_authorization_output,
        primary_authorization_terminal,
        primary_pre_start_output,
        primary_pre_start_terminal,
        replay_authorization_output,
        replay_authorization_terminal,
        replay_pre_start_output,
        replay_pre_start_terminal,
    )
    expected_types = (
        e.D7AuthorizationPathAbsenceReceipt,
        e.D7AuthorizationPathAbsenceReceipt,
        e.D7PreStartPathAbsenceReceipt,
        e.D7PreStartPathAbsenceReceipt,
        e.D7AuthorizationPathAbsenceReceipt,
        e.D7AuthorizationPathAbsenceReceipt,
        e.D7PreStartPathAbsenceReceipt,
        e.D7PreStartPathAbsenceReceipt,
    )
    for index, (receipt, expected) in enumerate(
        zip(receipts, expected_types, strict=True)
    ):
        _exact(receipt, expected, f"isolated receipt {index}")
    primary_store = primary_authorization_output.store_identity_sha256
    if any(receipt.store_identity_sha256 != primary_store for receipt in receipts):
        raise QualificationContractError(
            "isolated replay absence receipts must bind one shared store"
        )
    primary_target = primary_authorization_output.replay_target_sha256
    replay_target = replay_authorization_output.replay_target_sha256
    _same(primary_target, replay_target, "isolated replay target")
    if any(
        receipt.replay_target_sha256 != (primary_target if index < 4 else replay_target)
        for index, receipt in enumerate(receipts)
    ):
        raise QualificationContractError(
            "isolated receipt target coordinates are inconsistent"
        )
    primary_key = primary_authorization_output.attempt_key_sha256
    replay_key = replay_authorization_output.attempt_key_sha256
    if primary_key == replay_key:
        raise QualificationContractError(
            "primary and isolated replay attempt keys must differ"
        )
    if (
        primary_authorization_output.execution_identity_receipt_sha256
        == replay_authorization_output.execution_identity_receipt_sha256
    ):
        raise QualificationContractError(
            "primary and isolated replay execution identities must differ"
        )
    for early, late, label in (
        (
            primary_authorization_output,
            primary_pre_start_output,
            "primary output",
        ),
        (
            primary_authorization_terminal,
            primary_pre_start_terminal,
            "primary terminal",
        ),
        (
            replay_authorization_output,
            replay_pre_start_output,
            "replay output",
        ),
        (
            replay_authorization_terminal,
            replay_pre_start_terminal,
            "replay terminal",
        ),
    ):
        _same(early.subject_path, late.subject_path, f"{label} path continuity")
    primary_paths = {
        primary_authorization_output.subject_path,
        primary_authorization_terminal.subject_path,
    }
    replay_paths = {
        replay_authorization_output.subject_path,
        replay_authorization_terminal.subject_path,
    }
    if any(
        _paths_overlap(primary_path, replay_path)
        for primary_path in primary_paths
        for replay_path in replay_paths
    ):
        raise QualificationContractError(
            "primary and replay output/terminal realpaths must be disjoint "
            "and non-nested"
        )
    primary_identities = {
        primary_authorization_output.subject_path_identity_sha256,
        primary_authorization_terminal.subject_path_identity_sha256,
    }
    replay_identities = {
        replay_authorization_output.subject_path_identity_sha256,
        replay_authorization_terminal.subject_path_identity_sha256,
    }
    if primary_identities & replay_identities:
        raise QualificationContractError(
            "primary and replay path identities must be disjoint"
        )
    primary_physical_subjects = {
        _physical_subject_key(primary_authorization_output),
        _physical_subject_key(primary_authorization_terminal),
    }
    replay_physical_subjects = {
        _physical_subject_key(replay_authorization_output),
        _physical_subject_key(replay_authorization_terminal),
    }
    if primary_physical_subjects & replay_physical_subjects:
        raise QualificationContractError(
            "primary and replay physical parent/leaf identities must be disjoint"
        )


def validate_d7_failure_evidence_payload_chain(
    *,
    start: r.D7ExecutionStartRecord,
    payload: e.D7FailureEvidencePayload,
    evidence: r.D7FailureEvidenceRecord,
    failed_attempt: r.D7FailedAttemptRecord,
) -> None:
    """Join concrete failure bytes to the existing non-scientific envelope."""

    _exact(start, r.D7ExecutionStartRecord, "start")
    _exact(payload, e.D7FailureEvidencePayload, "payload")
    _exact(evidence, r.D7FailureEvidenceRecord, "evidence")
    _exact(failed_attempt, r.D7FailedAttemptRecord, "failed_attempt")
    for field in (
        "replay_target_sha256",
        "attempt_key_sha256",
        "execution_identity_receipt_sha256",
    ):
        _same(
            getattr(start, field),
            getattr(payload, field),
            f"failure start/payload {field}",
        )
    _same(
        start.canonical_sha256,
        payload.execution_start_sha256,
        "failure start/payload execution_start_sha256",
    )
    for field in (
        "replay_target_sha256",
        "attempt_key_sha256",
        "execution_start_sha256",
        "execution_identity_receipt_sha256",
        "failure_stage",
    ):
        _same(
            getattr(payload, field),
            getattr(evidence, field),
            f"failure payload/evidence {field}",
        )
        _same(
            getattr(evidence, field),
            getattr(failed_attempt, field),
            f"failure evidence/attempt {field}",
        )
    _same(payload.origin, evidence.origin, "failure payload/evidence origin")
    _same(
        payload.reason_code,
        evidence.reason_code,
        "failure payload/evidence reason_code",
    )
    _same(
        payload.confirmation_value_access_state,
        failed_attempt.confirmation_value_access_state,
        "failure payload/attempt confirmation access",
    )
    _same(
        payload.canonical_sha256,
        evidence.evidence_payload_sha256,
        "failure evidence payload digest",
    )
    _same(
        len(payload.canonical_bytes),
        evidence.evidence_payload_byte_count,
        "failure evidence payload byte count",
    )
    _same(
        evidence.canonical_sha256,
        failed_attempt.failure_evidence_sha256,
        "failed attempt evidence digest",
    )


def validate_d7_external_abort_verification_receipt(
    *,
    start: r.D7ExecutionStartRecord,
    payload: e.D7FailureEvidencePayload,
    receipt: e.D7ExternalAbortVerificationReceipt,
    evidence: r.D7FailureEvidenceRecord,
    finalization: r.D7StartedUnresolvedFinalizationRecord,
    failed_attempt: r.D7FailedAttemptRecord,
) -> None:
    """Join external receipt bytes without authenticating their issuer."""

    _exact(start, r.D7ExecutionStartRecord, "start")
    _exact(receipt, e.D7ExternalAbortVerificationReceipt, "receipt")
    _exact(finalization, r.D7StartedUnresolvedFinalizationRecord, "finalization")
    validate_d7_failure_evidence_payload_chain(
        start=start,
        payload=payload,
        evidence=evidence,
        failed_attempt=failed_attempt,
    )
    if type(payload.detail) is not e.D7ExternalAbortObservationDetail:
        raise QualificationContractError(
            "external abort receipt requires external observation detail"
        )
    if (
        payload.failure_stage is not r.D7FailureStage.EVIDENCED_ABORT
        or payload.origin is not r.D7FailureEvidenceOrigin.EXTERNAL
    ):
        raise QualificationContractError(
            "external abort receipt requires evidenced external abort"
        )
    for field in (
        "replay_target_sha256",
        "attempt_key_sha256",
        "execution_start_sha256",
        "execution_identity_receipt_sha256",
    ):
        expected = getattr(payload, field)
        _same(expected, getattr(receipt, field), f"external receipt {field}")
        if field != "execution_start_sha256":
            _same(expected, getattr(start, field), f"external start {field}")
    _same(
        start.canonical_sha256,
        receipt.execution_start_sha256,
        "external receipt execution_start_sha256",
    )
    _same(
        payload.canonical_sha256,
        receipt.failure_evidence_payload_sha256,
        "external receipt failure payload digest",
    )
    _same(
        len(payload.canonical_bytes),
        receipt.failure_evidence_payload_byte_count,
        "external receipt failure payload byte count",
    )
    _same(
        payload.detail.observer_identity_receipt_sha256,
        receipt.observer_identity_receipt_sha256,
        "external receipt observer identity",
    )
    _same(
        payload.detail.observation_payload_sha256,
        receipt.observation_payload_sha256,
        "external receipt observation payload",
    )
    _same(
        receipt.canonical_sha256,
        evidence.external_verification_receipt_sha256,
        "failure evidence external receipt digest",
    )
    _same(
        len(receipt.canonical_bytes),
        evidence.external_verification_receipt_byte_count,
        "failure evidence external receipt byte count",
    )
    _same(
        receipt.canonical_sha256,
        finalization.external_verification_receipt_sha256,
        "finalization external receipt digest",
    )
    _same(
        len(receipt.canonical_bytes),
        finalization.external_verification_receipt_byte_count,
        "finalization external receipt byte count",
    )
    _same(
        finalization.canonical_sha256,
        failed_attempt.started_unresolved_finalization_sha256,
        "failed attempt unresolved finalization digest",
    )
    v.validate_d7_started_unresolved_finalization(
        start=start,
        evidence=evidence,
        finalization=finalization,
    )
