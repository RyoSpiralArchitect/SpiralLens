"""Typed terminal operations for the future D7 execution boundary.

This deep-internal module closes two mechanics-only joins:

* a private post-start runner handoff can be converted to one complete
  no-replace structural terminal without accepting unrelated raw manifest
  bytes; and
* a signed external-abort envelope can be verified against explicit runtime
  pins, rechecked against the live prefix/terminal coordinates, included in
  the closed terminal inventory, and published once.

The abort path may strictly reload an authoritative-start transaction without
reconstructing the fused operation's ephemeral private ownership.

Neither operation issues the private post-start ownership object.  Runtime
pins are caller-supplied configuration here, not SpiralLens trust-root
authority.  The returned receipts therefore prove only structural publication
and signature verification relative to those exact pins.  They do not prove
an official start, trusted pin provenance, wall-clock freshness, execution,
scientific eligibility, retry/replay permission, D7, or D8.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import InitVar, dataclass
from pathlib import Path
from typing import ClassVar

from . import confirmation_attempt_evidence as e
from . import confirmation_attempt_evidence_validation as ev
from . import confirmation_attempt_persistence as p
from . import confirmation_attempt_records as r
from . import confirmation_attempt_terminal_persistence as tp
from . import confirmation_attempt_validation as v
from . import confirmation_authoritative_start_persistence as authoritative_start
from . import confirmation_external_witness as w
from . import confirmation_runner as runner
from .common import QualificationContractError

__all__: tuple[str, ...] = ()

_AUTHENTICATION_RECEIPT_FACTORY_TOKEN = object()
_LoadedPrefix = (
    p.D7LoadedEvidenceOnlyPrefix
    | authoritative_start.D7LoadedAuthoritativeStartTransaction
)


@dataclass(frozen=True, slots=True)
class D7ExternalAbortAuthenticationRelativeToPins:
    """A non-authorizing authentication receipt for one visible terminal."""

    path: Path
    terminal_manifest_sha256: str
    terminal_consumption_sha256: str
    failed_attempt_sha256: str
    signed_witness_envelope_sha256: str
    runtime_trust_root_sha256: str
    observer_public_key_sha256: str
    verifier_public_key_sha256: str
    directory_device: int
    directory_inode: int
    created_by_call: bool
    parent_directory_fsync_proved: bool | None
    _factory_token: InitVar[object]

    signature_authentication_scope: ClassVar[str] = "explicit-runtime-pins-only"
    witness_signatures_verified: ClassVar[bool] = True
    trust_root_provenance_verified: ClassVar[bool] = False
    wall_clock_freshness_proved: ClassVar[bool] = False
    authoritative_start_proved: ClassVar[bool] = False
    authority_granted: ClassVar[bool] = False
    execution_observed: ClassVar[bool] = False
    scientific_claim_eligible: ClassVar[bool] = False
    retry_authorized: ClassVar[bool] = False
    replay_authorized: ClassVar[bool] = False
    d8_eligible: ClassVar[bool] = False

    def __post_init__(self, _factory_token: object) -> None:
        if _factory_token is not _AUTHENTICATION_RECEIPT_FACTORY_TOKEN:
            raise TypeError(
                "external-abort authentication receipt requires its verifier"
            )
        if not isinstance(self.path, Path) or not self.path.is_absolute():
            raise TypeError("path must be an absolute Path")
        for name in (
            "terminal_manifest_sha256",
            "terminal_consumption_sha256",
            "failed_attempt_sha256",
            "signed_witness_envelope_sha256",
            "runtime_trust_root_sha256",
            "observer_public_key_sha256",
            "verifier_public_key_sha256",
        ):
            p._sha256(getattr(self, name), name)
        for name in ("directory_device", "directory_inode"):
            p._nonnegative_int(getattr(self, name), name)
        if type(self.created_by_call) is not bool:
            raise TypeError("created_by_call must be a plain boolean")
        if self.parent_directory_fsync_proved is not None and (
            type(self.parent_directory_fsync_proved) is not bool
        ):
            raise TypeError("parent_directory_fsync_proved must be bool or None")


def _preflight_owned_prefix_kind(
    loaded_prefix: object,
    ownership: runner._D7PostStartOwnership,
) -> None:
    if type(ownership) is not runner._D7PostStartOwnership:
        raise TypeError("ownership must be an exact private D7 post-start handoff")
    is_evidence = type(loaded_prefix) is p.D7LoadedEvidenceOnlyPrefix
    is_authoritative = (
        type(loaded_prefix) is authoritative_start.D7LoadedAuthoritativeStartTransaction
    )
    expected_kind_matches = (
        is_authoritative if ownership.requires_authoritative_start else is_evidence
    )
    if not expected_kind_matches:
        raise TypeError("loaded_prefix kind differs from the private ownership binding")


def _reload_owned_prefix(
    loaded_prefix: object,
    ownership: runner._D7PostStartOwnership,
) -> object:
    reloaded = tp._strictly_reload_prefix(loaded_prefix)
    if (
        reloaded.declaration,
        reloaded.authorization,
        reloaded.claim,
        reloaded.start,
    ) != (
        ownership.declaration,
        ownership.authorization,
        ownership.claim,
        ownership.start,
    ):
        raise QualificationContractError(
            "post-start ownership differs from the persisted prefix"
        )
    if reloaded.declaration.attempt_role is not r.D7AttemptRole.PRIMARY_CONFIRMATION:
        raise QualificationContractError(
            "terminal operations currently require a primary confirmation"
        )
    if ownership.requires_authoritative_start and (
        ownership.authoritative_start_manifest_sha256
        != reloaded.manifest.canonical_sha256
        or ownership.authoritative_start_directory_identity_sha256
        != reloaded.directory_identity_sha256
    ):
        raise QualificationContractError(
            "post-start ownership differs from the authoritative-start transaction"
        )
    return reloaded


def _require_owned_prefix(
    loaded_prefix: object,
    ownership: runner._D7PostStartOwnership,
) -> object:
    _preflight_owned_prefix_kind(loaded_prefix, ownership)
    return _reload_owned_prefix(loaded_prefix, ownership)


def _authoritative_start_lineage(prefix: object) -> dict[str, str | None]:
    if type(prefix) is authoritative_start.D7LoadedAuthoritativeStartTransaction:
        return {
            "authoritative_start_manifest_sha256": (prefix.manifest.canonical_sha256),
            "authoritative_start_directory_identity_sha256": (
                prefix.directory_identity_sha256
            ),
            "authority_verification_evidence_sha256": (
                prefix.verification_evidence_binding.canonical_sha256
            ),
        }
    return {
        "authoritative_start_manifest_sha256": None,
        "authoritative_start_directory_identity_sha256": None,
        "authority_verification_evidence_sha256": None,
    }


def _scientific_transaction(
    prefix: object,
    prepared: runner.D7PreparedScientificTerminal,
) -> tuple[
    dict[str, bytes],
    r.D7TerminalManifestRecord,
    r.D7TerminalConsumptionRecord,
]:
    output = prepared.producer_output
    result = prepared.scientific_result
    runner._validate_scientific_output(
        ownership=prepared.ownership,
        producer_output=output,
    )
    runner._validate_prepared_scientific_result(
        ownership=prepared.ownership,
        producer_output=output,
        scientific_result=result,
    )
    components = output.ordered_values[:-1]
    sources = {
        r.D7_SCIENTIFIC_RESULT_FILENAME: result.canonical_bytes,
        r.D7_SCIENTIFIC_RESULT_PAYLOAD_FILENAME: (
            output.result_payload.canonical_bytes
        ),
        **{
            binding.filename: component.canonical_bytes
            for binding, component in zip(
                output.result_payload.component_bindings,
                components,
                strict=True,
            )
        },
    }
    manifest = r.D7TerminalManifestRecord(
        replay_target_sha256=prefix.start.replay_target_sha256,
        attempt_key_sha256=prefix.start.attempt_key_sha256,
        attempt_claim_sha256=prefix.claim.canonical_sha256,
        execution_start_sha256=prefix.start.canonical_sha256,
        execution_identity_receipt_sha256=(
            prefix.start.execution_identity_receipt_sha256
        ),
        terminal_artifact_kind=r.D7TerminalArtifactKind.SCIENTIFIC_RESULT,
        terminal_artifact_sha256=result.canonical_sha256,
        immutable_members=v._scientific_members(output.result_payload, result),
        **_authoritative_start_lineage(prefix),
    )
    consumption = r.D7TerminalConsumptionRecord(
        replay_target_sha256=prefix.start.replay_target_sha256,
        attempt_key_sha256=prefix.start.attempt_key_sha256,
        attempt_claim_sha256=prefix.claim.canonical_sha256,
        execution_start_sha256=prefix.start.canonical_sha256,
        execution_identity_receipt_sha256=(
            prefix.start.execution_identity_receipt_sha256
        ),
        terminal_manifest_sha256=manifest.canonical_sha256,
        terminal_artifact_kind=r.D7TerminalArtifactKind.SCIENTIFIC_RESULT,
        terminal_artifact_sha256=result.canonical_sha256,
        confirmation_value_access_state=r.D7ConfirmationValueAccessState.OBSERVED,
    )
    return sources, manifest, consumption


def _ordinary_failure_transaction(
    prefix: object,
    prepared: runner.D7PreparedFailedTerminal,
) -> tuple[
    dict[str, bytes],
    r.D7TerminalManifestRecord,
    r.D7TerminalConsumptionRecord,
]:
    failed = prepared.failed_attempt
    evidence = prepared.failure_evidence
    payload = prepared.failure_payload
    ev.validate_d7_failure_evidence_payload_chain(
        start=prepared.ownership.start,
        payload=payload,
        evidence=evidence,
        failed_attempt=failed,
    )
    manifest = r.D7TerminalManifestRecord(
        replay_target_sha256=prefix.start.replay_target_sha256,
        attempt_key_sha256=prefix.start.attempt_key_sha256,
        attempt_claim_sha256=prefix.claim.canonical_sha256,
        execution_start_sha256=prefix.start.canonical_sha256,
        execution_identity_receipt_sha256=(
            prefix.start.execution_identity_receipt_sha256
        ),
        terminal_artifact_kind=r.D7TerminalArtifactKind.FAILED_ATTEMPT,
        terminal_artifact_sha256=failed.canonical_sha256,
        immutable_members=v._failure_members(evidence, failed, None),
        **_authoritative_start_lineage(prefix),
    )
    consumption = r.D7TerminalConsumptionRecord(
        replay_target_sha256=prefix.start.replay_target_sha256,
        attempt_key_sha256=prefix.start.attempt_key_sha256,
        attempt_claim_sha256=prefix.claim.canonical_sha256,
        execution_start_sha256=prefix.start.canonical_sha256,
        execution_identity_receipt_sha256=(
            prefix.start.execution_identity_receipt_sha256
        ),
        terminal_manifest_sha256=manifest.canonical_sha256,
        terminal_artifact_kind=r.D7TerminalArtifactKind.FAILED_ATTEMPT,
        terminal_artifact_sha256=failed.canonical_sha256,
        confirmation_value_access_state=(payload.confirmation_value_access_state),
    )
    return (
        {
            r.D7_FAILED_ATTEMPT_FILENAME: failed.canonical_bytes,
            r.D7_FAILURE_EVIDENCE_FILENAME: evidence.canonical_bytes,
            r.D7_FAILURE_EVIDENCE_PAYLOAD_FILENAME: payload.canonical_bytes,
        },
        manifest,
        consumption,
    )


def persist_d7_prepared_terminal_no_replace(
    loaded_prefix: object,
    prepared: runner.D7PreparedScientificTerminal | runner.D7PreparedFailedTerminal,
    /,
) -> tp.D7PersistedStructuralTerminalIdentity:
    """Publish one runner-prepared terminal through a typed, exact-prefix join."""

    if type(prepared) not in (
        runner.D7PreparedScientificTerminal,
        runner.D7PreparedFailedTerminal,
    ):
        raise TypeError("prepared must be an exact D7 runner terminal handoff")
    ownership = prepared.ownership
    _preflight_owned_prefix_kind(loaded_prefix, ownership)
    ownership._consume_for_terminal_publication()
    prefix = _reload_owned_prefix(loaded_prefix, ownership)
    if type(prepared) is runner.D7PreparedScientificTerminal:
        sources, manifest, consumption = _scientific_transaction(prefix, prepared)
    else:
        sources, manifest, consumption = _ordinary_failure_transaction(
            prefix,
            prepared,
        )
    return tp.persist_d7_structural_terminal_transaction_no_replace(
        prefix,
        immutable_member_sources=sources,
        manifest=manifest,
        consumption=consumption,
    )


def _require_live_witness_coordinates(
    value: w.VerifiedD7ExternalAbortWitness,
    *,
    prefix: _LoadedPrefix,
) -> None:
    expected = (
        ("replay_target_sha256", prefix.start.replay_target_sha256),
        ("attempt_key_sha256", prefix.start.attempt_key_sha256),
        ("execution_start_sha256", prefix.start.canonical_sha256),
        (
            "execution_identity_receipt_sha256",
            prefix.start.execution_identity_receipt_sha256,
        ),
        ("store_identity_sha256", prefix.declaration.store_identity_sha256),
        (
            "terminal_path_identity_sha256",
            prefix.declaration.terminal_path_identity_sha256,
        ),
        (
            "store_root_realpath",
            prefix.pre_start_terminal_receipt.store_root_realpath,
        ),
        (
            "terminal_parent_realpath",
            prefix.pre_start_terminal_receipt.resolved_parent_realpath,
        ),
        (
            "terminal_basename",
            prefix.pre_start_terminal_receipt.subject_basename,
        ),
        (
            "terminal_parent_device",
            prefix.pre_start_terminal_receipt.parent_device,
        ),
        (
            "terminal_parent_inode",
            prefix.pre_start_terminal_receipt.parent_inode,
        ),
    )
    for name, expected_value in expected:
        observed = getattr(value, name)
        if type(observed) is not type(expected_value) or observed != expected_value:
            raise QualificationContractError(f"verified witness live {name} differs")


def _require_terminal_absence(
    value: w.VerifiedD7ExternalAbortWitness,
    *,
    prefix: _LoadedPrefix,
) -> None:
    _require_live_witness_coordinates(value, prefix=prefix)
    parent, terminal_leaf = tp._open_terminal_parent(prefix)
    try:
        tp._reject_staging_entries(parent, prefix.start.attempt_key_sha256)
        p._require_absent(
            parent,
            terminal_leaf,
            label="D7 authenticated external-abort terminal",
        )
        p._verify_anchor(parent, label="D7 external-abort terminal parent")
    finally:
        os.close(parent.descriptor)


def _strictly_reload_authoritative_start(
    loaded_start: object,
) -> authoritative_start.D7LoadedAuthoritativeStartTransaction:
    if (
        type(loaded_start)
        is not authoritative_start.D7LoadedAuthoritativeStartTransaction
    ):
        raise TypeError(
            "loaded_start must be an exact D7LoadedAuthoritativeStartTransaction"
        )
    prefix = tp._strictly_reload_prefix(loaded_start)
    assert type(prefix) is authoritative_start.D7LoadedAuthoritativeStartTransaction
    if prefix.declaration.attempt_role is not r.D7AttemptRole.PRIMARY_CONFIRMATION:
        raise QualificationContractError(
            "terminal operations currently require a primary confirmation"
        )
    return prefix


def _external_records(
    prefix: _LoadedPrefix,
    *,
    payload: e.D7FailureEvidencePayload,
    receipt: e.D7ExternalAbortVerificationReceipt,
    envelope: e.D7SignedExternalAbortWitnessEnvelope,
) -> tuple[
    r.D7FailureEvidenceRecord,
    r.D7StartedUnresolvedFinalizationRecord,
    r.D7FailedAttemptRecord,
    r.D7TerminalManifestRecord,
    r.D7TerminalConsumptionRecord,
    dict[str, bytes],
]:
    evidence = r.D7FailureEvidenceRecord(
        replay_target_sha256=prefix.start.replay_target_sha256,
        attempt_key_sha256=prefix.start.attempt_key_sha256,
        execution_start_sha256=prefix.start.canonical_sha256,
        execution_identity_receipt_sha256=(
            prefix.start.execution_identity_receipt_sha256
        ),
        failure_stage=r.D7FailureStage.EVIDENCED_ABORT,
        origin=r.D7FailureEvidenceOrigin.EXTERNAL,
        reason_code=payload.reason_code,
        evidence_payload_sha256=payload.canonical_sha256,
        evidence_payload_byte_count=len(payload.canonical_bytes),
        external_verification_receipt_sha256=receipt.canonical_sha256,
        external_verification_receipt_byte_count=len(receipt.canonical_bytes),
    )
    finalization = r.D7StartedUnresolvedFinalizationRecord(
        replay_target_sha256=prefix.start.replay_target_sha256,
        attempt_key_sha256=prefix.start.attempt_key_sha256,
        execution_start_sha256=prefix.start.canonical_sha256,
        execution_identity_receipt_sha256=(
            prefix.start.execution_identity_receipt_sha256
        ),
        external_abort_evidence_sha256=evidence.canonical_sha256,
        external_verification_receipt_sha256=receipt.canonical_sha256,
        external_verification_receipt_byte_count=len(receipt.canonical_bytes),
        signed_external_abort_witness_envelope_sha256=(envelope.canonical_sha256),
        signed_external_abort_witness_envelope_byte_count=len(envelope.canonical_bytes),
    )
    failed = r.D7FailedAttemptRecord(
        replay_target_sha256=prefix.start.replay_target_sha256,
        attempt_key_sha256=prefix.start.attempt_key_sha256,
        execution_start_sha256=prefix.start.canonical_sha256,
        execution_identity_receipt_sha256=(
            prefix.start.execution_identity_receipt_sha256
        ),
        failure_stage=r.D7FailureStage.EVIDENCED_ABORT,
        failure_evidence_sha256=evidence.canonical_sha256,
        started_unresolved_finalization_sha256=finalization.canonical_sha256,
        confirmation_value_access_state=(payload.confirmation_value_access_state),
    )
    ev.validate_d7_external_abort_verification_receipt(
        start=prefix.start,
        payload=payload,
        receipt=receipt,
        evidence=evidence,
        finalization=finalization,
        failed_attempt=failed,
    )
    ev.validate_d7_signed_external_abort_witness_envelope(
        declaration=prefix.declaration,
        start=prefix.start,
        terminal_path_receipt=prefix.pre_start_terminal_receipt,
        payload=payload,
        structural_receipt=receipt,
        envelope=envelope,
        finalization=finalization,
    )
    manifest = r.D7TerminalManifestRecord(
        replay_target_sha256=prefix.start.replay_target_sha256,
        attempt_key_sha256=prefix.start.attempt_key_sha256,
        attempt_claim_sha256=prefix.claim.canonical_sha256,
        execution_start_sha256=prefix.start.canonical_sha256,
        execution_identity_receipt_sha256=(
            prefix.start.execution_identity_receipt_sha256
        ),
        terminal_artifact_kind=r.D7TerminalArtifactKind.FAILED_ATTEMPT,
        terminal_artifact_sha256=failed.canonical_sha256,
        immutable_members=v._failure_members(evidence, failed, finalization),
        **_authoritative_start_lineage(prefix),
    )
    consumption = r.D7TerminalConsumptionRecord(
        replay_target_sha256=prefix.start.replay_target_sha256,
        attempt_key_sha256=prefix.start.attempt_key_sha256,
        attempt_claim_sha256=prefix.claim.canonical_sha256,
        execution_start_sha256=prefix.start.canonical_sha256,
        execution_identity_receipt_sha256=(
            prefix.start.execution_identity_receipt_sha256
        ),
        terminal_manifest_sha256=manifest.canonical_sha256,
        terminal_artifact_kind=r.D7TerminalArtifactKind.FAILED_ATTEMPT,
        terminal_artifact_sha256=failed.canonical_sha256,
        confirmation_value_access_state=(payload.confirmation_value_access_state),
    )
    sources = {
        r.D7_FAILED_ATTEMPT_FILENAME: failed.canonical_bytes,
        r.D7_FAILURE_EVIDENCE_FILENAME: evidence.canonical_bytes,
        r.D7_FAILURE_EVIDENCE_PAYLOAD_FILENAME: payload.canonical_bytes,
        r.D7_EXTERNAL_ABORT_VERIFICATION_RECEIPT_FILENAME: (receipt.canonical_bytes),
        r.D7_SIGNED_EXTERNAL_ABORT_WITNESS_ENVELOPE_FILENAME: (
            envelope.canonical_bytes
        ),
        r.D7_STARTED_UNRESOLVED_FINALIZATION_FILENAME: (finalization.canonical_bytes),
    }
    return evidence, finalization, failed, manifest, consumption, sources


def _authentication_receipt(
    *,
    loaded: tp.D7LoadedStructuralTerminalTransaction,
    witness: w.VerifiedD7ExternalAbortWitness,
    created_by_call: bool,
    parent_directory_fsync_proved: bool | None,
) -> D7ExternalAbortAuthenticationRelativeToPins:
    return D7ExternalAbortAuthenticationRelativeToPins(
        path=loaded.path,
        terminal_manifest_sha256=loaded.manifest.canonical_sha256,
        terminal_consumption_sha256=loaded.consumption.canonical_sha256,
        failed_attempt_sha256=loaded.terminal_artifact.canonical_sha256,
        signed_witness_envelope_sha256=witness.envelope_sha256,
        runtime_trust_root_sha256=witness.runtime_trust_root_sha256,
        observer_public_key_sha256=witness.observer_public_key_sha256,
        verifier_public_key_sha256=witness.verifier_public_key_sha256,
        directory_device=loaded.directory_device,
        directory_inode=loaded.directory_inode,
        created_by_call=created_by_call,
        parent_directory_fsync_proved=parent_directory_fsync_proved,
        _factory_token=_AUTHENTICATION_RECEIPT_FACTORY_TOKEN,
    )


def _finalize_external_abort_relative_to_pins_no_replace(
    prefix: _LoadedPrefix,
    *,
    envelope_source: bytes,
    expected_envelope_sha256: str,
    trust_root: w.D7PinnedExternalWitnessTrustRoot,
    payload: e.D7FailureEvidencePayload,
    structural_receipt: e.D7ExternalAbortVerificationReceipt,
    strict_reload: Callable[[], _LoadedPrefix],
) -> D7ExternalAbortAuthenticationRelativeToPins:
    verified = w.verify_d7_signed_external_abort_witness(
        envelope_source=envelope_source,
        expected_envelope_sha256=expected_envelope_sha256,
        trust_root=trust_root,
        declaration=prefix.declaration,
        start=prefix.start,
        terminal_path_receipt=prefix.pre_start_terminal_receipt,
        payload=payload,
        structural_receipt=structural_receipt,
    )
    envelope = e.D7SignedExternalAbortWitnessEnvelope.from_canonical_bytes(
        envelope_source,
        expected_sha256=expected_envelope_sha256,
    )
    _, _, _, manifest, consumption, sources = _external_records(
        prefix,
        payload=payload,
        receipt=structural_receipt,
        envelope=envelope,
    )
    verified.consume(
        revalidate=lambda value: _require_terminal_absence(
            value,
            prefix=strict_reload(),
        )
    )
    publication = tp.persist_d7_structural_terminal_transaction_no_replace(
        prefix,
        immutable_member_sources=sources,
        manifest=manifest,
        consumption=consumption,
    )
    loaded = tp.load_d7_structural_terminal_transaction(
        prefix,
        expected_manifest_sha256=manifest.canonical_sha256,
        expected_consumption_sha256=consumption.canonical_sha256,
    )
    return _authentication_receipt(
        loaded=loaded,
        witness=verified,
        created_by_call=True,
        parent_directory_fsync_proved=publication.parent_directory_fsync_proved,
    )


def finalize_d7_external_abort_relative_to_pins_no_replace(
    loaded_prefix: p.D7LoadedEvidenceOnlyPrefix,
    ownership: runner._D7PostStartOwnership,
    *,
    envelope_source: bytes,
    expected_envelope_sha256: str,
    trust_root: w.D7PinnedExternalWitnessTrustRoot,
    payload: e.D7FailureEvidencePayload,
    structural_receipt: e.D7ExternalAbortVerificationReceipt,
) -> D7ExternalAbortAuthenticationRelativeToPins:
    """Verify, fixed-revalidate, derive, and publish one external abort.

    The operation intentionally accepts no preverified witness object and no
    caller-supplied manifest, finalization, failed-attempt, or consumption
    record.
    """

    _preflight_owned_prefix_kind(loaded_prefix, ownership)
    ownership._consume_for_external_finalization()
    prefix = _reload_owned_prefix(loaded_prefix, ownership)
    return _finalize_external_abort_relative_to_pins_no_replace(
        prefix,
        envelope_source=envelope_source,
        expected_envelope_sha256=expected_envelope_sha256,
        trust_root=trust_root,
        payload=payload,
        structural_receipt=structural_receipt,
        strict_reload=lambda: _require_owned_prefix(prefix, ownership),
    )


def finalize_d7_reloaded_authoritative_start_external_abort_relative_to_pins_no_replace(
    loaded_start: authoritative_start.D7LoadedAuthoritativeStartTransaction,
    *,
    envelope_source: bytes,
    expected_envelope_sha256: str,
    trust_root: w.D7PinnedExternalWitnessTrustRoot,
    payload: e.D7FailureEvidencePayload,
    structural_receipt: e.D7ExternalAbortVerificationReceipt,
) -> D7ExternalAbortAuthenticationRelativeToPins:
    """Close a strictly reloaded authoritative start with a signed abort.

    Persisted start bytes replace no same-call ownership.  They only provide
    exact descriptor, attempt, start, and terminal lineage for this one
    signature-authenticated, no-replace structural publication.
    """

    prefix = _strictly_reload_authoritative_start(loaded_start)
    return _finalize_external_abort_relative_to_pins_no_replace(
        prefix,
        envelope_source=envelope_source,
        expected_envelope_sha256=expected_envelope_sha256,
        trust_root=trust_root,
        payload=payload,
        structural_receipt=structural_receipt,
        strict_reload=lambda: _strictly_reload_authoritative_start(prefix),
    )


def load_d7_external_abort_relative_to_pins(
    loaded_prefix: _LoadedPrefix,
    *,
    expected_manifest_sha256: str,
    expected_consumption_sha256: str,
    trust_root: w.D7PinnedExternalWitnessTrustRoot,
) -> D7ExternalAbortAuthenticationRelativeToPins:
    """Strictly reload and reauthenticate an external terminal to exact pins."""

    loaded = tp.load_d7_structural_terminal_transaction(
        loaded_prefix,
        expected_manifest_sha256=expected_manifest_sha256,
        expected_consumption_sha256=expected_consumption_sha256,
    )
    sources = loaded.immutable_member_sources
    required = (
        r.D7_FAILED_ATTEMPT_FILENAME,
        r.D7_FAILURE_EVIDENCE_FILENAME,
        r.D7_FAILURE_EVIDENCE_PAYLOAD_FILENAME,
        r.D7_EXTERNAL_ABORT_VERIFICATION_RECEIPT_FILENAME,
        r.D7_SIGNED_EXTERNAL_ABORT_WITNESS_ENVELOPE_FILENAME,
        r.D7_STARTED_UNRESOLVED_FINALIZATION_FILENAME,
    )
    if any(filename not in sources for filename in required):
        raise QualificationContractError(
            "terminal is not one complete external-abort transaction"
        )
    members = {member.filename: member for member in loaded.manifest.immutable_members}
    payload = e.D7FailureEvidencePayload.from_canonical_bytes(
        sources[r.D7_FAILURE_EVIDENCE_PAYLOAD_FILENAME],
        expected_sha256=members[
            r.D7_FAILURE_EVIDENCE_PAYLOAD_FILENAME
        ].member_canonical_sha256,
    )
    receipt = e.D7ExternalAbortVerificationReceipt.from_canonical_bytes(
        sources[r.D7_EXTERNAL_ABORT_VERIFICATION_RECEIPT_FILENAME],
        expected_sha256=members[
            r.D7_EXTERNAL_ABORT_VERIFICATION_RECEIPT_FILENAME
        ].member_canonical_sha256,
    )
    envelope_source = sources[r.D7_SIGNED_EXTERNAL_ABORT_WITNESS_ENVELOPE_FILENAME]
    envelope = e.D7SignedExternalAbortWitnessEnvelope.from_canonical_bytes(
        envelope_source,
        expected_sha256=members[
            r.D7_SIGNED_EXTERNAL_ABORT_WITNESS_ENVELOPE_FILENAME
        ].member_canonical_sha256,
    )
    finalization = r.D7StartedUnresolvedFinalizationRecord.from_canonical_bytes(
        sources[r.D7_STARTED_UNRESOLVED_FINALIZATION_FILENAME],
        expected_sha256=members[
            r.D7_STARTED_UNRESOLVED_FINALIZATION_FILENAME
        ].member_canonical_sha256,
    )
    ev.validate_d7_signed_external_abort_witness_envelope(
        declaration=loaded.prefix.declaration,
        start=loaded.prefix.start,
        terminal_path_receipt=loaded.prefix.pre_start_terminal_receipt,
        payload=payload,
        structural_receipt=receipt,
        envelope=envelope,
        finalization=finalization,
    )
    verified = w.verify_d7_signed_external_abort_witness(
        envelope_source=envelope_source,
        expected_envelope_sha256=envelope.canonical_sha256,
        trust_root=trust_root,
        declaration=loaded.prefix.declaration,
        start=loaded.prefix.start,
        terminal_path_receipt=loaded.prefix.pre_start_terminal_receipt,
        payload=payload,
        structural_receipt=receipt,
    )

    def revalidate_visible_terminal(
        value: w.VerifiedD7ExternalAbortWitness,
    ) -> None:
        _require_live_witness_coordinates(value, prefix=loaded.prefix)
        reloaded = tp.load_d7_structural_terminal_transaction(
            loaded.prefix,
            expected_manifest_sha256=loaded.manifest.canonical_sha256,
            expected_consumption_sha256=loaded.consumption.canonical_sha256,
        )
        if (
            reloaded.manifest != loaded.manifest
            or reloaded.consumption != loaded.consumption
            or reloaded.terminal_artifact != loaded.terminal_artifact
            or reloaded.directory_device != loaded.directory_device
            or reloaded.directory_inode != loaded.directory_inode
        ):
            raise QualificationContractError(
                "external-abort terminal changed during authentication"
            )

    verified.consume(revalidate=revalidate_visible_terminal)
    return _authentication_receipt(
        loaded=loaded,
        witness=verified,
        created_by_call=False,
        parent_directory_fsync_proved=None,
    )
