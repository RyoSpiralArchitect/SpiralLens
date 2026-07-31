from __future__ import annotations

import copy
import hashlib
import pickle
from dataclasses import replace
from types import SimpleNamespace

import pytest

import spirallens
from spirallens import qualification
from spirallens.core.canonical import canonical_json_bytes, sha256_bytes
from spirallens.qualification import confirmation_attempt_evidence as e
from spirallens.qualification import confirmation_attempt_evidence_validation as ev
from spirallens.qualification import confirmation_attempt_records as r
from spirallens.qualification import confirmation_external_witness as w
from spirallens.qualification.common import QualificationContractError


def _h(label: str) -> str:
    return hashlib.sha256(label.encode()).hexdigest()


def _prefix(
    label: str = "primary",
    *,
    store_identity: str | None = None,
    store_root: str = "/tmp/spirallens-d7-store",
    resolved_parent: str | None = None,
    parent_inode: int = 23,
    output_leaf: str | None = None,
    terminal_leaf: str | None = None,
    role_evidence: r.D7AttemptRoleEvidence | None = None,
) -> SimpleNamespace:
    store_identity = store_identity or _h("shared-store")
    resolved_parent = resolved_parent or store_root
    output_leaf = output_leaf or f"{label}-output"
    terminal_leaf = terminal_leaf or f"{label}-terminal"
    output_identity = e.d7_path_identity_sha256(
        store_identity_sha256=store_identity,
        resolved_parent_realpath=resolved_parent,
        subject_basename=output_leaf,
    )
    terminal_identity = e.d7_path_identity_sha256(
        store_identity_sha256=store_identity,
        resolved_parent_realpath=resolved_parent,
        subject_basename=terminal_leaf,
    )
    declaration = r.D7AttemptDeclarationRecord(
        replay_target_sha256=_h("target"),
        launch_intent_sha256=_h(f"{label}-intent"),
        role_evidence=role_evidence or r.D7PrimaryRoleEvidence(),
        store_identity_sha256=store_identity,
        output_namespace_identity_sha256=output_identity,
        terminal_path_identity_sha256=terminal_identity,
        authorization_commit="a" * 40,
        execution_identity_receipt_sha256=_h(f"{label}-execution"),
    )

    def authorization_receipt(
        subject: e.D7AbsentPathSubject,
        leaf: str,
        identity: str,
        inode: int,
    ) -> e.D7AuthorizationPathAbsenceReceipt:
        return e.D7AuthorizationPathAbsenceReceipt(
            subject_kind=subject,
            replay_target_sha256=declaration.replay_target_sha256,
            attempt_key_sha256=declaration.attempt_key_sha256,
            attempt_declaration_sha256=declaration.canonical_sha256,
            authorization_commit=declaration.authorization_commit,
            execution_identity_receipt_sha256=(
                declaration.execution_identity_receipt_sha256
            ),
            store_identity_sha256=declaration.store_identity_sha256,
            subject_path_identity_sha256=identity,
            store_root_realpath=store_root,
            resolved_parent_realpath=resolved_parent,
            subject_basename=leaf,
            parent_device=17,
            parent_inode=inode,
        )

    authorization_output = authorization_receipt(
        e.D7AbsentPathSubject.OUTPUT_NAMESPACE,
        output_leaf,
        output_identity,
        parent_inode,
    )
    authorization_terminal = authorization_receipt(
        e.D7AbsentPathSubject.TERMINAL_PATH,
        terminal_leaf,
        terminal_identity,
        parent_inode,
    )
    authorization = r.D7LaunchAuthorizationRecord(
        attempt_declaration_sha256=declaration.canonical_sha256,
        replay_target_sha256=declaration.replay_target_sha256,
        attempt_key_sha256=declaration.attempt_key_sha256,
        authorization_commit=declaration.authorization_commit,
        execution_identity_receipt_sha256=(
            declaration.execution_identity_receipt_sha256
        ),
        execution_source_runtime_receipt_sha256=_h("source-runtime"),
        runtime_specification_sha256=_h("runtime-specification"),
        admission_receipt_sha256=_h("admission"),
        full_design_freeze_receipt_sha256=_h("full-design"),
        store_identity_sha256=declaration.store_identity_sha256,
        output_namespace_identity_sha256=(declaration.output_namespace_identity_sha256),
        terminal_path_identity_sha256=declaration.terminal_path_identity_sha256,
        authorization_output_namespace_absence_receipt_sha256=(
            authorization_output.canonical_sha256
        ),
        authorization_terminal_path_absence_receipt_sha256=(
            authorization_terminal.canonical_sha256
        ),
    )
    claim = r.D7AttemptClaimRecord(
        attempt_declaration_sha256=declaration.canonical_sha256,
        launch_authorization_sha256=authorization.canonical_sha256,
        replay_target_sha256=declaration.replay_target_sha256,
        attempt_key_sha256=declaration.attempt_key_sha256,
        execution_identity_receipt_sha256=(
            declaration.execution_identity_receipt_sha256
        ),
        store_identity_sha256=declaration.store_identity_sha256,
    )

    def pre_start_receipt(
        subject: e.D7AbsentPathSubject,
        leaf: str,
        identity: str,
        inode: int,
    ) -> e.D7PreStartPathAbsenceReceipt:
        return e.D7PreStartPathAbsenceReceipt(
            subject_kind=subject,
            replay_target_sha256=declaration.replay_target_sha256,
            attempt_key_sha256=declaration.attempt_key_sha256,
            attempt_declaration_sha256=declaration.canonical_sha256,
            launch_authorization_sha256=authorization.canonical_sha256,
            attempt_claim_sha256=claim.canonical_sha256,
            authorization_commit=declaration.authorization_commit,
            execution_identity_receipt_sha256=(
                declaration.execution_identity_receipt_sha256
            ),
            store_identity_sha256=declaration.store_identity_sha256,
            subject_path_identity_sha256=identity,
            store_root_realpath=store_root,
            resolved_parent_realpath=resolved_parent,
            subject_basename=leaf,
            parent_device=17,
            parent_inode=inode,
        )

    pre_start_output = pre_start_receipt(
        e.D7AbsentPathSubject.OUTPUT_NAMESPACE,
        output_leaf,
        output_identity,
        parent_inode,
    )
    pre_start_terminal = pre_start_receipt(
        e.D7AbsentPathSubject.TERMINAL_PATH,
        terminal_leaf,
        terminal_identity,
        parent_inode,
    )
    start = r.D7ExecutionStartRecord(
        attempt_declaration_sha256=declaration.canonical_sha256,
        launch_authorization_sha256=authorization.canonical_sha256,
        attempt_claim_sha256=claim.canonical_sha256,
        replay_target_sha256=declaration.replay_target_sha256,
        attempt_key_sha256=declaration.attempt_key_sha256,
        authorization_commit=declaration.authorization_commit,
        execution_identity_receipt_sha256=(
            declaration.execution_identity_receipt_sha256
        ),
        observed_execution_identity_receipt_sha256=(
            declaration.execution_identity_receipt_sha256
        ),
        observed_execution_source_runtime_receipt_sha256=(
            authorization.execution_source_runtime_receipt_sha256
        ),
        observed_runtime_specification_sha256=(
            authorization.runtime_specification_sha256
        ),
        output_namespace_identity_sha256=(declaration.output_namespace_identity_sha256),
        terminal_path_identity_sha256=declaration.terminal_path_identity_sha256,
        pre_start_output_namespace_absence_receipt_sha256=(
            pre_start_output.canonical_sha256
        ),
        pre_start_terminal_path_absence_receipt_sha256=(
            pre_start_terminal.canonical_sha256
        ),
    )
    return SimpleNamespace(
        declaration=declaration,
        authorization=authorization,
        claim=claim,
        start=start,
        authorization_output=authorization_output,
        authorization_terminal=authorization_terminal,
        pre_start_output=pre_start_output,
        pre_start_terminal=pre_start_terminal,
    )


def _isolated_role() -> r.D7IsolatedReplayRoleEvidence:
    target = _h("target")
    return r.D7IsolatedReplayRoleEvidence(
        primary_replay_target_sha256=target,
        primary_attempt_key_sha256=r.d7_attempt_key_sha256(
            replay_target_sha256=target,
            attempt_role=r.D7AttemptRole.PRIMARY_CONFIRMATION,
        ),
        primary_attempt_declaration_sha256=_h("primary-declaration"),
        primary_launch_authorization_sha256=_h("primary-authorization"),
        primary_attempt_claim_sha256=_h("primary-claim"),
        primary_execution_start_sha256=_h("primary-start"),
        primary_result_payload_sha256=_h("primary-result-payload"),
        primary_scientific_result_sha256=_h("primary-result"),
        primary_terminal_manifest_sha256=_h("primary-manifest"),
        primary_terminal_consumption_sha256=_h("primary-consumption"),
    )


def _validate_absence(prefix: SimpleNamespace) -> None:
    ev.validate_d7_path_absence_receipt_chain(
        declaration=prefix.declaration,
        authorization=prefix.authorization,
        claim=prefix.claim,
        start=prefix.start,
        authorization_output_receipt=prefix.authorization_output,
        authorization_terminal_receipt=prefix.authorization_terminal,
        pre_start_output_receipt=prefix.pre_start_output,
        pre_start_terminal_receipt=prefix.pre_start_terminal,
    )


def _in_process_failure(prefix: SimpleNamespace) -> SimpleNamespace:
    payload = e.D7FailureEvidencePayload(
        replay_target_sha256=prefix.declaration.replay_target_sha256,
        attempt_key_sha256=prefix.declaration.attempt_key_sha256,
        execution_start_sha256=prefix.start.canonical_sha256,
        execution_identity_receipt_sha256=(
            prefix.declaration.execution_identity_receipt_sha256
        ),
        failure_stage=r.D7FailureStage.EXECUTION_KERNEL,
        origin=r.D7FailureEvidenceOrigin.IN_PROCESS,
        reason_code="runtime-error",
        confirmation_value_access_state=r.D7ConfirmationValueAccessState.UNKNOWN,
        detail=e.D7InProcessFailureDetail(
            exception_class="builtins.RuntimeError",
            exception_message_sha256=_h("message"),
            traceback_sha256=_h("traceback"),
        ),
    )
    evidence = r.D7FailureEvidenceRecord(
        replay_target_sha256=payload.replay_target_sha256,
        attempt_key_sha256=payload.attempt_key_sha256,
        execution_start_sha256=payload.execution_start_sha256,
        execution_identity_receipt_sha256=(payload.execution_identity_receipt_sha256),
        failure_stage=payload.failure_stage,
        origin=payload.origin,
        reason_code=payload.reason_code,
        evidence_payload_sha256=payload.canonical_sha256,
        evidence_payload_byte_count=len(payload.canonical_bytes),
        external_verification_receipt_sha256=None,
        external_verification_receipt_byte_count=None,
    )
    failed = r.D7FailedAttemptRecord(
        replay_target_sha256=payload.replay_target_sha256,
        attempt_key_sha256=payload.attempt_key_sha256,
        execution_start_sha256=payload.execution_start_sha256,
        execution_identity_receipt_sha256=(payload.execution_identity_receipt_sha256),
        failure_stage=payload.failure_stage,
        failure_evidence_sha256=evidence.canonical_sha256,
        started_unresolved_finalization_sha256=None,
        confirmation_value_access_state=payload.confirmation_value_access_state,
    )
    return SimpleNamespace(payload=payload, evidence=evidence, failed=failed)


def _external_failure(prefix: SimpleNamespace) -> SimpleNamespace:
    detail = e.D7ExternalAbortObservationDetail(
        observer_identity_receipt_sha256=_h("external-observer"),
        observation_kind=e.D7ExternalAbortObservationKind.PROCESS_EXIT_WITHOUT_TERMINAL,
        observation_payload_sha256=_h("external-observation"),
    )
    payload = e.D7FailureEvidencePayload(
        replay_target_sha256=prefix.declaration.replay_target_sha256,
        attempt_key_sha256=prefix.declaration.attempt_key_sha256,
        execution_start_sha256=prefix.start.canonical_sha256,
        execution_identity_receipt_sha256=(
            prefix.declaration.execution_identity_receipt_sha256
        ),
        failure_stage=r.D7FailureStage.EVIDENCED_ABORT,
        origin=r.D7FailureEvidenceOrigin.EXTERNAL,
        reason_code="external-abort",
        confirmation_value_access_state=r.D7ConfirmationValueAccessState.UNKNOWN,
        detail=detail,
    )
    receipt = e.D7ExternalAbortVerificationReceipt(
        replay_target_sha256=payload.replay_target_sha256,
        attempt_key_sha256=payload.attempt_key_sha256,
        execution_start_sha256=payload.execution_start_sha256,
        execution_identity_receipt_sha256=(payload.execution_identity_receipt_sha256),
        failure_evidence_payload_sha256=payload.canonical_sha256,
        failure_evidence_payload_byte_count=len(payload.canonical_bytes),
        observer_identity_receipt_sha256=detail.observer_identity_receipt_sha256,
        verifier_source_runtime_receipt_sha256=_h("external-verifier-runtime"),
        observation_payload_sha256=detail.observation_payload_sha256,
        verification_method=(
            e.D7ExternalAbortVerificationMethod.EXECUTION_IDENTITY_AND_TERMINAL_INSPECTION
        ),
    )
    evidence = r.D7FailureEvidenceRecord(
        replay_target_sha256=payload.replay_target_sha256,
        attempt_key_sha256=payload.attempt_key_sha256,
        execution_start_sha256=payload.execution_start_sha256,
        execution_identity_receipt_sha256=(payload.execution_identity_receipt_sha256),
        failure_stage=payload.failure_stage,
        origin=payload.origin,
        reason_code=payload.reason_code,
        evidence_payload_sha256=payload.canonical_sha256,
        evidence_payload_byte_count=len(payload.canonical_bytes),
        external_verification_receipt_sha256=receipt.canonical_sha256,
        external_verification_receipt_byte_count=len(receipt.canonical_bytes),
    )
    finalization = r.D7StartedUnresolvedFinalizationRecord(
        replay_target_sha256=payload.replay_target_sha256,
        attempt_key_sha256=payload.attempt_key_sha256,
        execution_start_sha256=payload.execution_start_sha256,
        execution_identity_receipt_sha256=(payload.execution_identity_receipt_sha256),
        external_abort_evidence_sha256=evidence.canonical_sha256,
        external_verification_receipt_sha256=receipt.canonical_sha256,
        external_verification_receipt_byte_count=len(receipt.canonical_bytes),
        signed_external_abort_witness_envelope_sha256=_h(
            "unbound-signed-external-witness-envelope"
        ),
        signed_external_abort_witness_envelope_byte_count=1,
    )
    failed = r.D7FailedAttemptRecord(
        replay_target_sha256=payload.replay_target_sha256,
        attempt_key_sha256=payload.attempt_key_sha256,
        execution_start_sha256=payload.execution_start_sha256,
        execution_identity_receipt_sha256=(payload.execution_identity_receipt_sha256),
        failure_stage=payload.failure_stage,
        failure_evidence_sha256=evidence.canonical_sha256,
        started_unresolved_finalization_sha256=finalization.canonical_sha256,
        confirmation_value_access_state=payload.confirmation_value_access_state,
    )
    return SimpleNamespace(
        payload=payload,
        receipt=receipt,
        evidence=evidence,
        finalization=finalization,
        failed=failed,
    )


def _signed_external_witness(
    prefix: SimpleNamespace | None = None,
) -> SimpleNamespace:
    ed25519 = pytest.importorskip("cryptography.hazmat.primitives.asymmetric.ed25519")
    serialization = pytest.importorskip("cryptography.hazmat.primitives.serialization")
    prefix = prefix or _prefix()
    failure = _external_failure(prefix)
    observer_private_key = ed25519.Ed25519PrivateKey.generate()
    verifier_private_key = ed25519.Ed25519PrivateKey.generate()
    observer_public_key = observer_private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    verifier_public_key = verifier_private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    trust_root = w.D7PinnedExternalWitnessTrustRoot(
        execution_principal_id="execution-worker",
        execution_identity_receipt_sha256=(
            prefix.start.execution_identity_receipt_sha256
        ),
        observer_principal_id="external-observer",
        observer_identity_receipt_sha256=(
            failure.receipt.observer_identity_receipt_sha256
        ),
        observer_public_key=observer_public_key,
        verifier_principal_id="independent-verifier",
        verifier_source_runtime_receipt_sha256=(
            failure.receipt.verifier_source_runtime_receipt_sha256
        ),
        verifier_public_key=verifier_public_key,
    )
    terminal = prefix.pre_start_terminal
    statement = e.D7ExternalAbortWitnessStatement(
        replay_target_sha256=prefix.start.replay_target_sha256,
        attempt_key_sha256=prefix.start.attempt_key_sha256,
        execution_start_sha256=prefix.start.canonical_sha256,
        execution_identity_receipt_sha256=(
            prefix.start.execution_identity_receipt_sha256
        ),
        failure_evidence_payload_sha256=failure.payload.canonical_sha256,
        failure_evidence_payload_byte_count=len(failure.payload.canonical_bytes),
        structural_verification_receipt_sha256=failure.receipt.canonical_sha256,
        structural_verification_receipt_byte_count=len(failure.receipt.canonical_bytes),
        observer_identity_receipt_sha256=(
            failure.receipt.observer_identity_receipt_sha256
        ),
        verifier_source_runtime_receipt_sha256=(
            failure.receipt.verifier_source_runtime_receipt_sha256
        ),
        observation_kind=failure.payload.detail.observation_kind,
        observation_payload_sha256=(failure.receipt.observation_payload_sha256),
        store_identity_sha256=prefix.declaration.store_identity_sha256,
        terminal_path_identity_sha256=(
            prefix.declaration.terminal_path_identity_sha256
        ),
        store_root_realpath=terminal.store_root_realpath,
        terminal_parent_realpath=terminal.resolved_parent_realpath,
        terminal_basename=terminal.subject_basename,
        terminal_parent_device=terminal.parent_device,
        terminal_parent_inode=terminal.parent_inode,
        execution_principal_id=trust_root.execution_principal_id,
        observer_principal_id=trust_root.observer_principal_id,
        verifier_principal_id=trust_root.verifier_principal_id,
        observer_public_key_sha256=trust_root.observer_public_key_sha256,
        verifier_public_key_sha256=trust_root.verifier_public_key_sha256,
        runtime_trust_root_sha256=trust_root.canonical_sha256,
    )
    unsigned = e.D7SignedExternalAbortWitnessEnvelope(
        statement=statement,
        observer_signature="0" * 128,
        verifier_signature="0" * 128,
    )
    observer_signed = replace(
        unsigned,
        observer_signature=observer_private_key.sign(
            unsigned.observer_signed_bytes
        ).hex(),
    )
    envelope = replace(
        observer_signed,
        verifier_signature=verifier_private_key.sign(
            observer_signed.verifier_signed_bytes
        ).hex(),
    )
    finalization = replace(
        failure.finalization,
        signed_external_abort_witness_envelope_sha256=envelope.canonical_sha256,
        signed_external_abort_witness_envelope_byte_count=len(envelope.canonical_bytes),
    )
    failed = replace(
        failure.failed,
        started_unresolved_finalization_sha256=finalization.canonical_sha256,
    )
    failure.finalization = finalization
    failure.failed = failed
    return SimpleNamespace(
        prefix=prefix,
        failure=failure,
        trust_root=trust_root,
        observer_private_key=observer_private_key,
        verifier_private_key=verifier_private_key,
        envelope=envelope,
    )


def _verify_signed_external_witness(
    witness: SimpleNamespace,
    *,
    trust_root: w.D7PinnedExternalWitnessTrustRoot | None = None,
    prefix: SimpleNamespace | None = None,
    failure: SimpleNamespace | None = None,
    envelope: e.D7SignedExternalAbortWitnessEnvelope | None = None,
    expected_envelope_sha256: str | None = None,
) -> w.VerifiedD7ExternalAbortWitness:
    prefix = prefix or witness.prefix
    failure = failure or witness.failure
    envelope = envelope or witness.envelope
    return w.verify_d7_signed_external_abort_witness(
        envelope_source=envelope.canonical_bytes,
        expected_envelope_sha256=(
            expected_envelope_sha256 or envelope.canonical_sha256
        ),
        trust_root=trust_root or witness.trust_root,
        declaration=prefix.declaration,
        start=prefix.start,
        terminal_path_receipt=prefix.pre_start_terminal,
        payload=failure.payload,
        structural_receipt=failure.receipt,
    )


def _resign_external_witness(
    witness: SimpleNamespace,
    statement: e.D7ExternalAbortWitnessStatement,
) -> e.D7SignedExternalAbortWitnessEnvelope:
    unsigned = e.D7SignedExternalAbortWitnessEnvelope(
        statement=statement,
        observer_signature="0" * 128,
        verifier_signature="0" * 128,
    )
    observer_signed = replace(
        unsigned,
        observer_signature=witness.observer_private_key.sign(
            unsigned.observer_signed_bytes
        ).hex(),
    )
    return replace(
        observer_signed,
        verifier_signature=witness.verifier_private_key.sign(
            observer_signed.verifier_signed_bytes
        ).hex(),
    )


def test_absence_receipts_have_strict_canonical_bytes_and_acyclic_shapes() -> None:
    prefix = _prefix()
    _validate_absence(prefix)
    assert (
        prefix.authorization_output.canonical_sha256
        == "31c9e51ec92b14b7320b7ea5780222d0be10d56eec1fbc7a8bdd0a22a115b2d1"
    )
    for value in (
        prefix.authorization_output,
        prefix.authorization_terminal,
        prefix.pre_start_output,
        prefix.pre_start_terminal,
    ):
        rebuilt = type(value).from_dict(value.to_dict())
        assert rebuilt == value
        assert (
            type(value).from_canonical_bytes(
                value.canonical_bytes,
                expected_sha256=value.canonical_sha256,
            )
            == value
        )
        assert value.canonical_sha256 == sha256_bytes(value.canonical_bytes)

    authorization_document = prefix.authorization_output.to_dict()
    authorization_document["launch_authorization_sha256"] = _h("future-cycle")
    with pytest.raises(QualificationContractError, match="fields differ"):
        e.D7AuthorizationPathAbsenceReceipt.from_dict(authorization_document)
    pre_start_document = prefix.pre_start_output.to_dict()
    pre_start_document["execution_start_sha256"] = _h("future-cycle")
    with pytest.raises(QualificationContractError, match="fields differ"):
        e.D7PreStartPathAbsenceReceipt.from_dict(pre_start_document)


def test_absence_receipts_reject_type_laundering_and_identity_mismatch() -> None:
    prefix = _prefix()
    document = prefix.authorization_output.to_dict()
    document["directory_entry_absent"] = 1
    with pytest.raises(QualificationContractError, match="directory_entry_absent"):
        e.D7AuthorizationPathAbsenceReceipt.from_dict(document)
    for non_realpath in (
        "/tmp/spirallens-d7-store/../aliased-parent",
        "//tmp/spirallens-d7-store",
        "/tmp//spirallens-d7-store",
        "/tmp/./spirallens-d7-store",
    ):
        document = prefix.authorization_output.to_dict()
        document["resolved_parent_realpath"] = non_realpath
        with pytest.raises(QualificationContractError, match="realpath"):
            e.D7AuthorizationPathAbsenceReceipt.from_dict(document)
    document = prefix.authorization_output.to_dict()
    document["subject_basename"] = "CaseAlias"
    with pytest.raises(QualificationContractError, match="lowercase portable"):
        e.D7AuthorizationPathAbsenceReceipt.from_dict(document)
    with pytest.raises(QualificationContractError, match="path identity"):
        replace(
            prefix.authorization_output,
            subject_path_identity_sha256=_h("wrong-path"),
        )
    wrong = replace(
        prefix.pre_start_output,
        attempt_claim_sha256=_h("wrong-claim"),
    )
    with pytest.raises(QualificationContractError, match="attempt_claim_sha256"):
        ev.validate_d7_pre_start_path_absence_receipts(
            declaration=prefix.declaration,
            authorization=prefix.authorization,
            claim=prefix.claim,
            start=prefix.start,
            output_namespace_receipt=wrong,
            terminal_path_receipt=prefix.pre_start_terminal,
        )


def test_absence_chain_requires_stable_parent_and_isolated_paths() -> None:
    primary = _prefix("primary")
    replay = _prefix("replay", role_evidence=_isolated_role())
    _validate_absence(primary)
    _validate_absence(replay)
    ev.validate_d7_isolated_replay_path_disjointness(
        primary_authorization_output=primary.authorization_output,
        primary_authorization_terminal=primary.authorization_terminal,
        primary_pre_start_output=primary.pre_start_output,
        primary_pre_start_terminal=primary.pre_start_terminal,
        replay_authorization_output=replay.authorization_output,
        replay_authorization_terminal=replay.authorization_terminal,
        replay_pre_start_output=replay.pre_start_output,
        replay_pre_start_terminal=replay.pre_start_terminal,
    )
    changed_parent = replace(primary.pre_start_output, parent_inode=99)
    with pytest.raises(QualificationContractError, match="parent_inode continuity"):
        ev.validate_d7_path_absence_receipt_chain(
            declaration=primary.declaration,
            authorization=primary.authorization,
            claim=primary.claim,
            start=replace(
                primary.start,
                pre_start_output_namespace_absence_receipt_sha256=(
                    changed_parent.canonical_sha256
                ),
            ),
            authorization_output_receipt=primary.authorization_output,
            authorization_terminal_receipt=primary.authorization_terminal,
            pre_start_output_receipt=changed_parent,
            pre_start_terminal_receipt=primary.pre_start_terminal,
        )
    alias = _prefix(
        "replay-alias",
        output_leaf=primary.authorization_output.subject_basename,
        role_evidence=_isolated_role(),
    )
    with pytest.raises(QualificationContractError, match="realpaths"):
        ev.validate_d7_isolated_replay_path_disjointness(
            primary_authorization_output=primary.authorization_output,
            primary_authorization_terminal=primary.authorization_terminal,
            primary_pre_start_output=primary.pre_start_output,
            primary_pre_start_terminal=primary.pre_start_terminal,
            replay_authorization_output=alias.authorization_output,
            replay_authorization_terminal=alias.authorization_terminal,
            replay_pre_start_output=alias.pre_start_output,
            replay_pre_start_terminal=alias.pre_start_terminal,
        )
    physical_alias = _prefix(
        "replay-physical-alias",
        store_root="/tmp/spirallens-d7-store-bind-alias",
        output_leaf=primary.authorization_output.subject_basename,
        role_evidence=_isolated_role(),
    )
    _validate_absence(physical_alias)
    with pytest.raises(QualificationContractError, match="physical parent/leaf"):
        ev.validate_d7_isolated_replay_path_disjointness(
            primary_authorization_output=primary.authorization_output,
            primary_authorization_terminal=primary.authorization_terminal,
            primary_pre_start_output=primary.pre_start_output,
            primary_pre_start_terminal=primary.pre_start_terminal,
            replay_authorization_output=physical_alias.authorization_output,
            replay_authorization_terminal=physical_alias.authorization_terminal,
            replay_pre_start_output=physical_alias.pre_start_output,
            replay_pre_start_terminal=physical_alias.pre_start_terminal,
        )
    nested = _prefix(
        "replay-nested",
        resolved_parent=primary.authorization_output.subject_path,
        parent_inode=24,
        role_evidence=_isolated_role(),
    )
    _validate_absence(nested)
    with pytest.raises(QualificationContractError, match="non-nested"):
        ev.validate_d7_isolated_replay_path_disjointness(
            primary_authorization_output=primary.authorization_output,
            primary_authorization_terminal=primary.authorization_terminal,
            primary_pre_start_output=primary.pre_start_output,
            primary_pre_start_terminal=primary.pre_start_terminal,
            replay_authorization_output=nested.authorization_output,
            replay_authorization_terminal=nested.authorization_terminal,
            replay_pre_start_output=nested.pre_start_output,
            replay_pre_start_terminal=nested.pre_start_terminal,
        )


def test_in_process_failure_payload_is_concrete_and_structurally_joined() -> None:
    prefix = _prefix()
    failure = _in_process_failure(prefix)
    ev.validate_d7_failure_evidence_payload_chain(
        start=prefix.start,
        payload=failure.payload,
        evidence=failure.evidence,
        failed_attempt=failure.failed,
    )
    assert (
        e.D7FailureEvidencePayload.from_canonical_bytes(
            failure.payload.canonical_bytes,
            expected_sha256=failure.payload.canonical_sha256,
        )
        == failure.payload
    )
    wrong = replace(failure.evidence, evidence_payload_sha256=_h("wrong"))
    with pytest.raises(QualificationContractError, match="payload digest"):
        ev.validate_d7_failure_evidence_payload_chain(
            start=prefix.start,
            payload=failure.payload,
            evidence=wrong,
            failed_attempt=replace(
                failure.failed,
                failure_evidence_sha256=wrong.canonical_sha256,
            ),
        )
    forged_payload = replace(
        failure.payload,
        execution_start_sha256=_h("forged-start"),
    )
    forged_evidence = replace(
        failure.evidence,
        execution_start_sha256=forged_payload.execution_start_sha256,
        evidence_payload_sha256=forged_payload.canonical_sha256,
        evidence_payload_byte_count=len(forged_payload.canonical_bytes),
    )
    forged_failed = replace(
        failure.failed,
        execution_start_sha256=forged_payload.execution_start_sha256,
        failure_evidence_sha256=forged_evidence.canonical_sha256,
    )
    with pytest.raises(QualificationContractError, match="execution_start_sha256"):
        ev.validate_d7_failure_evidence_payload_chain(
            start=prefix.start,
            payload=forged_payload,
            evidence=forged_evidence,
            failed_attempt=forged_failed,
        )


def test_failure_detail_union_rejects_origin_and_field_mixing() -> None:
    prefix = _prefix()
    failure = _in_process_failure(prefix)
    with pytest.raises(QualificationContractError, match="detail, origin"):
        replace(
            failure.payload,
            origin=r.D7FailureEvidenceOrigin.EXTERNAL,
        )
    document = failure.payload.to_dict()
    detail = document["detail"]
    assert type(detail) is dict
    detail["observer_identity_receipt_sha256"] = _h("mixed")
    with pytest.raises(QualificationContractError, match="fields differ"):
        e.D7FailureEvidencePayload.from_dict(document)


def test_external_abort_receipt_closes_bytes_but_not_witness_authority() -> None:
    prefix = _prefix()
    failure = _external_failure(prefix)
    ev.validate_d7_external_abort_verification_receipt(
        start=prefix.start,
        payload=failure.payload,
        receipt=failure.receipt,
        evidence=failure.evidence,
        finalization=failure.finalization,
        failed_attempt=failure.failed,
    )
    rebuilt = e.D7ExternalAbortVerificationReceipt.from_canonical_bytes(
        failure.receipt.canonical_bytes,
        expected_sha256=failure.receipt.canonical_sha256,
    )
    assert rebuilt == failure.receipt
    assertions = failure.receipt.to_dict()["finalization_assertions"]
    assert assertions == {
        "execution_start_sha256": prefix.start.canonical_sha256,
        "execution_identity_receipt_sha256": (
            prefix.declaration.execution_identity_receipt_sha256
        ),
        "aggregate_outcome_observed": False,
    }


def test_external_abort_receipt_rejects_weak_or_disconnected_assertions() -> None:
    prefix = _prefix()
    failure = _external_failure(prefix)
    document = failure.receipt.to_dict()
    document["process_absence_alone_sufficient"] = True
    with pytest.raises(QualificationContractError, match="process_absence"):
        e.D7ExternalAbortVerificationReceipt.from_dict(document)
    document = failure.receipt.to_dict()
    assertions = document["finalization_assertions"]
    assert type(assertions) is dict
    assertions["aggregate_outcome_observed"] = 0
    with pytest.raises(QualificationContractError, match="aggregate_outcome"):
        e.D7ExternalAbortVerificationReceipt.from_dict(document)
    document = failure.receipt.to_dict()
    assertions = document["finalization_assertions"]
    assert type(assertions) is dict

    class StringSubclass(str):
        pass

    assertions["execution_start_sha256"] = StringSubclass(
        failure.receipt.execution_start_sha256
    )
    with pytest.raises(QualificationContractError, match="exact string"):
        e.D7ExternalAbortVerificationReceipt.from_dict(document)
    with pytest.raises(QualificationContractError, match="receipt cap"):
        replace(
            failure.receipt,
            failure_evidence_payload_byte_count=(e.MAX_D7_ATTEMPT_EVIDENCE_BYTES + 1),
        )
    wrong = replace(
        failure.receipt,
        observation_payload_sha256=_h("wrong-observation"),
    )
    wrong_evidence = replace(
        failure.evidence,
        external_verification_receipt_sha256=wrong.canonical_sha256,
        external_verification_receipt_byte_count=len(wrong.canonical_bytes),
    )
    wrong_finalization = replace(
        failure.finalization,
        external_abort_evidence_sha256=wrong_evidence.canonical_sha256,
        external_verification_receipt_sha256=wrong.canonical_sha256,
        external_verification_receipt_byte_count=len(wrong.canonical_bytes),
    )
    wrong_failed = replace(
        failure.failed,
        failure_evidence_sha256=wrong_evidence.canonical_sha256,
        started_unresolved_finalization_sha256=(wrong_finalization.canonical_sha256),
    )
    with pytest.raises(QualificationContractError, match="observation payload"):
        ev.validate_d7_external_abort_verification_receipt(
            start=prefix.start,
            payload=failure.payload,
            receipt=wrong,
            evidence=wrong_evidence,
            finalization=wrong_finalization,
            failed_attempt=wrong_failed,
        )


def test_signed_external_witness_is_authenticated_internal_and_one_shot() -> None:
    witness = _signed_external_witness()
    ev.validate_d7_signed_external_abort_witness_envelope(
        declaration=witness.prefix.declaration,
        start=witness.prefix.start,
        terminal_path_receipt=witness.prefix.pre_start_terminal,
        payload=witness.failure.payload,
        structural_receipt=witness.failure.receipt,
        envelope=witness.envelope,
        finalization=witness.failure.finalization,
    )
    with pytest.raises(QualificationContractError, match="envelope digest"):
        ev.validate_d7_signed_external_abort_witness_envelope(
            declaration=witness.prefix.declaration,
            start=witness.prefix.start,
            terminal_path_receipt=witness.prefix.pre_start_terminal,
            payload=witness.failure.payload,
            structural_receipt=witness.failure.receipt,
            envelope=witness.envelope,
            finalization=replace(
                witness.failure.finalization,
                signed_external_abort_witness_envelope_sha256=_h("wrong-envelope"),
            ),
        )
    rebuilt = e.D7SignedExternalAbortWitnessEnvelope.from_canonical_bytes(
        witness.envelope.canonical_bytes,
        expected_sha256=witness.envelope.canonical_sha256,
    )
    assert rebuilt == witness.envelope

    verified = _verify_signed_external_witness(witness)
    assert verified.envelope_canonical_bytes == witness.envelope.canonical_bytes
    assert verified.envelope_sha256 == witness.envelope.canonical_sha256
    assert (
        verified.observer_public_key_sha256
        == witness.trust_root.observer_public_key_sha256
    )
    assert (
        verified.store_identity_sha256
        == witness.prefix.declaration.store_identity_sha256
    )
    assert (
        verified.terminal_path_identity_sha256
        == witness.prefix.declaration.terminal_path_identity_sha256
    )
    with pytest.raises(TypeError, match="cannot be constructed directly"):
        w.VerifiedD7ExternalAbortWitness(
            token=object(),
            envelope=witness.envelope,
            trust_root=witness.trust_root,
        )
    with pytest.raises(TypeError, match="cannot be copied"):
        copy.copy(verified)
    with pytest.raises(TypeError, match="cannot be serialized"):
        pickle.dumps(verified)

    revalidated: list[str] = []

    def revalidate(value: w.VerifiedD7ExternalAbortWitness) -> None:
        revalidated.append(value.terminal_basename)
        assert (
            value.terminal_parent_inode
            == witness.prefix.pre_start_terminal.parent_inode
        )

    verified.consume(revalidate=revalidate)
    assert revalidated == [witness.prefix.pre_start_terminal.subject_basename]
    assert verified.is_consumed is True
    with pytest.raises(QualificationContractError, match="already consumed"):
        verified.consume(revalidate=revalidate)

    boolean_shortcut = _verify_signed_external_witness(witness)
    with pytest.raises(TypeError, match="must raise on failure and return None"):
        boolean_shortcut.consume(revalidate=lambda _: True)  # type: ignore[arg-type]
    assert boolean_shortcut.is_consumed is True


def test_caller_constructed_v01_receipt_is_not_an_authenticated_witness() -> None:
    witness = _signed_external_witness()
    failure = witness.failure
    ev.validate_d7_external_abort_verification_receipt(
        start=witness.prefix.start,
        payload=failure.payload,
        receipt=failure.receipt,
        evidence=failure.evidence,
        finalization=failure.finalization,
        failed_attempt=failure.failed,
    )
    forged = replace(
        witness.envelope,
        observer_signature="0" * 128,
        verifier_signature="0" * 128,
    )
    forged_finalization = replace(
        failure.finalization,
        signed_external_abort_witness_envelope_sha256=forged.canonical_sha256,
        signed_external_abort_witness_envelope_byte_count=len(forged.canonical_bytes),
    )
    ev.validate_d7_signed_external_abort_witness_envelope(
        declaration=witness.prefix.declaration,
        start=witness.prefix.start,
        terminal_path_receipt=witness.prefix.pre_start_terminal,
        payload=failure.payload,
        structural_receipt=failure.receipt,
        envelope=forged,
        finalization=forged_finalization,
    )
    with pytest.raises(QualificationContractError, match="observer signature"):
        _verify_signed_external_witness(witness, envelope=forged)


def test_signed_external_witness_checks_digest_before_crypto(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    witness = _signed_external_witness()

    def crypto_must_not_run(**_: object) -> None:
        raise AssertionError("signature verification ran before the digest check")

    monkeypatch.setattr(w, "_verify_ed25519_signature", crypto_must_not_run)
    with pytest.raises(QualificationContractError, match="SHA-256 differs"):
        _verify_signed_external_witness(
            witness,
            expected_envelope_sha256=_h("wrong-envelope"),
        )


def test_signed_external_witness_rejects_invalid_verifier_signature() -> None:
    witness = _signed_external_witness()
    signature = witness.envelope.verifier_signature
    replacement = "0" if signature[0] != "0" else "1"
    tampered = replace(
        witness.envelope,
        verifier_signature=replacement + signature[1:],
    )
    with pytest.raises(QualificationContractError, match="verifier signature"):
        _verify_signed_external_witness(witness, envelope=tampered)


def test_signed_external_witness_rejects_wrong_runtime_trust_root() -> None:
    ed25519 = pytest.importorskip("cryptography.hazmat.primitives.asymmetric.ed25519")
    serialization = pytest.importorskip("cryptography.hazmat.primitives.serialization")
    witness = _signed_external_witness()
    wrong_verifier_key = (
        ed25519.Ed25519PrivateKey.generate()
        .public_key()
        .public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
    )
    wrong_root = replace(
        witness.trust_root,
        verifier_public_key=wrong_verifier_key,
    )
    with pytest.raises(QualificationContractError, match="runtime trust root"):
        _verify_signed_external_witness(witness, trust_root=wrong_root)


def test_signed_external_witness_rejects_cross_attempt_replay() -> None:
    witness = _signed_external_witness()
    other_prefix = _prefix("isolated", role_evidence=_isolated_role())
    other_failure = _external_failure(other_prefix)
    with pytest.raises(QualificationContractError, match="attempt_key_sha256"):
        _verify_signed_external_witness(
            witness,
            prefix=other_prefix,
            failure=other_failure,
        )


def test_signed_external_witness_rejects_principal_aliases() -> None:
    witness = _signed_external_witness()
    with pytest.raises(QualificationContractError, match="principals must differ"):
        replace(
            witness.trust_root,
            observer_principal_id=witness.trust_root.execution_principal_id,
        )
    with pytest.raises(QualificationContractError, match="public keys must differ"):
        replace(
            witness.trust_root,
            verifier_public_key=witness.trust_root.observer_public_key,
        )


def test_signed_external_witness_rejects_resigned_terminal_rebinding() -> None:
    witness = _signed_external_witness()
    other = _prefix("other-terminal")
    other_terminal = other.pre_start_terminal
    rebound_statement = replace(
        witness.envelope.statement,
        terminal_path_identity_sha256=other_terminal.subject_path_identity_sha256,
        store_root_realpath=other_terminal.store_root_realpath,
        terminal_parent_realpath=other_terminal.resolved_parent_realpath,
        terminal_basename=other_terminal.subject_basename,
        terminal_parent_device=other_terminal.parent_device,
        terminal_parent_inode=other_terminal.parent_inode,
    )
    rebound = _resign_external_witness(witness, rebound_statement)
    with pytest.raises(QualificationContractError, match="terminal path identity"):
        _verify_signed_external_witness(witness, envelope=rebound)


def test_signed_external_witness_has_no_weak_boolean_shortcut() -> None:
    witness = _signed_external_witness()
    document = witness.envelope.statement.to_dict()
    document["process_absence_alone_sufficient"] = True
    with pytest.raises(QualificationContractError, match="process_absence"):
        e.D7ExternalAbortWitnessStatement.from_dict(document)


def test_evidence_bytes_reject_wrong_digest_and_noncanonical_json() -> None:
    receipt = _prefix().authorization_output
    with pytest.raises(QualificationContractError, match="SHA-256 differs"):
        e.D7AuthorizationPathAbsenceReceipt.from_canonical_bytes(
            receipt.canonical_bytes,
            expected_sha256=_h("wrong"),
        )
    pretty = canonical_json_bytes(receipt.to_dict()).replace(b",", b", ", 1)
    with pytest.raises(QualificationContractError, match="not canonical"):
        e.D7AuthorizationPathAbsenceReceipt.from_canonical_bytes(
            pretty,
            expected_sha256=sha256_bytes(pretty),
        )


def test_attempt_evidence_modules_are_deep_internal_only() -> None:
    assert e.__all__ == ()
    assert ev.__all__ == ()
    assert w.__all__ == ()
    for name in (
        "D7AuthorizationPathAbsenceReceipt",
        "D7PreStartPathAbsenceReceipt",
        "D7FailureEvidencePayload",
        "D7ExternalAbortVerificationReceipt",
        "D7SignedExternalAbortWitnessEnvelope",
        "VerifiedD7ExternalAbortWitness",
    ):
        assert name not in spirallens.__all__
        assert name not in qualification.__all__
        assert not hasattr(spirallens, name)
        assert not hasattr(qualification, name)
