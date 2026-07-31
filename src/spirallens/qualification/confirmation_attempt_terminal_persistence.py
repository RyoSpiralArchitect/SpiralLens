"""Atomic structural persistence for one complete D7 terminal transaction.

This deep-internal module accepts an already persisted, caller-supplied D7
prefix and already constructed terminal bytes.  It validates their complete
structural joins, then exposes the whole terminal directory with one native
exclusive rename.  It does not authenticate the prefix, observe execution,
authenticate an external witness, authorize finalization, run an experiment,
or confer D7/D8 authority.

The evidence-only prefix remains non-promotable.  A successfully loaded value
means only that the supplied canonical bytes form one closed, atomically
published structural transaction.
"""

from __future__ import annotations

import errno
import hashlib
import os
import secrets
import stat
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import ClassVar

from . import confirmation_attempt_evidence as e
from . import confirmation_attempt_evidence_validation as ev
from . import confirmation_attempt_persistence as p
from . import confirmation_attempt_records as r
from . import confirmation_attempt_validation as v
from . import confirmation_result_component_validation as cv
from . import confirmation_result_components as c
from .common import QualificationContractError

__all__: tuple[str, ...] = ()

_TEMPORARY_SUFFIX = ".tmp"
_STAGING_MARKER = ".d7-terminal-transaction."
_MAX_STAGE_NAME_ATTEMPTS = 32

_COMPONENT_TYPES = MappingProxyType(
    {
        r.D7ResultComponentId.EXECUTION_EVENT_LEDGER: (c.D7ExecutionEventLedgerPayload),
        r.D7ResultComponentId.CORE_CELL_OUTCOMES: c.D7CoreCellOutcomesPayload,
        r.D7ResultComponentId.LOOP_CELL_OUTCOMES: c.D7LoopCellOutcomesPayload,
        r.D7ResultComponentId.PRIMARY_UNIT_OUTCOMES: (c.D7PrimaryUnitOutcomesPayload),
        r.D7ResultComponentId.REQUIRED_STRATUM_OUTCOMES: (
            c.D7RequiredStratumOutcomesPayload
        ),
        r.D7ResultComponentId.AGGREGATE_GATE_OUTCOMES: (
            c.D7AggregateGateOutcomesPayload
        ),
    }
)
_COMPONENT_FILENAMES = MappingProxyType(
    {
        component_id: f"result-{component_id.value}.json"
        for component_id in r.D7_RESULT_COMPONENT_ORDER
    }
)


@dataclass(frozen=True, slots=True)
class D7PersistedStructuralTerminalIdentity:
    """Exact identity and durability facts for one terminal publication."""

    path: Path
    terminal_artifact_kind: r.D7TerminalArtifactKind
    terminal_artifact_sha256: str
    terminal_manifest_sha256: str
    terminal_consumption_sha256: str
    directory_device: int
    directory_inode: int
    parent_directory_fsync_proved: bool
    created_by_call: bool = True
    atomic_no_replace: bool = True
    authority_granted: bool = False
    execution_observed: bool = False
    scientific_claim_eligible: bool = False
    retry_authorized: bool = False
    replay_authorized: bool = False
    d8_eligible: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.path, Path) or not self.path.is_absolute():
            raise TypeError("path must be an absolute Path")
        if type(self.terminal_artifact_kind) is not r.D7TerminalArtifactKind:
            raise TypeError(
                "terminal_artifact_kind must be an exact D7TerminalArtifactKind"
            )
        for name in (
            "terminal_artifact_sha256",
            "terminal_manifest_sha256",
            "terminal_consumption_sha256",
        ):
            p._sha256(getattr(self, name), name)
        for name in ("directory_device", "directory_inode"):
            p._nonnegative_int(getattr(self, name), name)
        for name in (
            "parent_directory_fsync_proved",
            "created_by_call",
            "atomic_no_replace",
            "authority_granted",
            "execution_observed",
            "scientific_claim_eligible",
            "retry_authorized",
            "replay_authorized",
            "d8_eligible",
        ):
            if type(getattr(self, name)) is not bool:
                raise TypeError(f"{name} must be a plain boolean")
        if (
            self.created_by_call is not True
            or self.atomic_no_replace is not True
            or self.authority_granted is not False
            or self.execution_observed is not False
            or self.scientific_claim_eligible is not False
            or self.retry_authorized is not False
            or self.replay_authorized is not False
            or self.d8_eligible is not False
        ):
            raise QualificationContractError(
                "D7 structural terminal identity constants differ"
            )


@dataclass(frozen=True, slots=True)
class D7LoadedStructuralTerminalTransaction:
    """Strictly loaded structural terminal bytes with no authority semantics."""

    path: Path
    prefix: object
    manifest: r.D7TerminalManifestRecord
    consumption: r.D7TerminalConsumptionRecord
    terminal_artifact: r.D7ScientificResultRecord | r.D7FailedAttemptRecord
    immutable_member_sources: Mapping[str, bytes]
    directory_device: int
    directory_inode: int

    terminal_structure_validated: ClassVar[bool] = True
    authority_granted: ClassVar[bool] = False
    authoritative_lifecycle_eligible: ClassVar[bool] = False
    execution_observed: ClassVar[bool] = False
    started_unresolved_established: ClassVar[bool] = False
    external_abort_authenticated: ClassVar[bool] = False
    external_abort_finalized: ClassVar[bool] = False
    scientific_claim_eligible: ClassVar[bool] = False
    retry_authorized: ClassVar[bool] = False
    replay_authorized: ClassVar[bool] = False
    d8_eligible: ClassVar[bool] = False

    def __post_init__(self) -> None:
        if not isinstance(self.path, Path) or not self.path.is_absolute():
            raise TypeError("path must be an absolute Path")
        if not _is_supported_prefix(self.prefix):
            raise TypeError(
                "prefix must be an exact evidence-only or authoritative-start prefix"
            )
        if type(self.manifest) is not r.D7TerminalManifestRecord:
            raise TypeError("manifest must be an exact D7TerminalManifestRecord")
        if type(self.consumption) is not r.D7TerminalConsumptionRecord:
            raise TypeError("consumption must be an exact D7TerminalConsumptionRecord")
        expected_artifact_type = (
            r.D7ScientificResultRecord
            if self.manifest.terminal_artifact_kind
            is r.D7TerminalArtifactKind.SCIENTIFIC_RESULT
            else r.D7FailedAttemptRecord
        )
        if type(self.terminal_artifact) is not expected_artifact_type:
            raise TypeError("terminal_artifact type differs from manifest kind")
        if type(self.immutable_member_sources) is not MappingProxyType:
            raise TypeError("immutable_member_sources must be read-only")
        expected_names = {member.filename for member in self.manifest.immutable_members}
        if set(self.immutable_member_sources) != expected_names:
            raise QualificationContractError(
                "loaded immutable terminal member inventory differs"
            )
        for member in self.manifest.immutable_members:
            source = self.immutable_member_sources[member.filename]
            if (
                type(source) is not bytes
                or len(source) != member.byte_count
                or hashlib.sha256(source).hexdigest() != member.member_canonical_sha256
            ):
                raise QualificationContractError(
                    "loaded immutable terminal member identity differs"
                )
        if (
            self.manifest.terminal_artifact_sha256
            != self.terminal_artifact.canonical_sha256
            or self.consumption.terminal_manifest_sha256
            != self.manifest.canonical_sha256
            or self.consumption.terminal_artifact_sha256
            != self.terminal_artifact.canonical_sha256
        ):
            raise QualificationContractError(
                "loaded terminal outcome/manifest/consumption identities differ"
            )
        for name in ("directory_device", "directory_inode"):
            p._nonnegative_int(getattr(self, name), name)


def _authoritative_start_type() -> type[object]:
    from . import confirmation_authoritative_start_persistence as authoritative

    return authoritative.D7LoadedAuthoritativeStartTransaction


def _is_supported_prefix(value: object) -> bool:
    return type(value) in {
        p.D7LoadedEvidenceOnlyPrefix,
        _authoritative_start_type(),
    }


def _strictly_reload_prefix(loaded: object) -> object:
    if type(loaded) is p.D7LoadedEvidenceOnlyPrefix:
        reloaded = p.load_d7_evidence_only_prefix(
            loaded.store_root,
            attempt_key_sha256=loaded.declaration.attempt_key_sha256,
            expected_store_identity_sha256=(
                loaded.store_scope.declared_store_identity_sha256
            ),
            expected_declaration_sha256=loaded.declaration.canonical_sha256,
            expected_authorization_sha256=loaded.authorization.canonical_sha256,
            expected_claim_sha256=loaded.claim.canonical_sha256,
            expected_start_sha256=loaded.start.canonical_sha256,
            expected_declaration_envelope_sha256=(
                loaded.declaration_envelope.canonical_sha256
            ),
            expected_authorization_envelope_sha256=(
                loaded.authorization_envelope.canonical_sha256
            ),
            expected_claim_envelope_sha256=loaded.claim_envelope.canonical_sha256,
            expected_start_envelope_sha256=loaded.start_envelope.canonical_sha256,
        )
        original_values = (
            loaded.declaration,
            loaded.authorization,
            loaded.claim,
            loaded.start,
            loaded.authorization_output_receipt,
            loaded.authorization_terminal_receipt,
            loaded.pre_start_output_receipt,
            loaded.pre_start_terminal_receipt,
            loaded.store_scope.canonical_sha256,
            loaded.declaration_envelope.canonical_sha256,
            loaded.authorization_envelope.canonical_sha256,
            loaded.claim_envelope.canonical_sha256,
            loaded.start_envelope.canonical_sha256,
        )
        reloaded_values = (
            reloaded.declaration,
            reloaded.authorization,
            reloaded.claim,
            reloaded.start,
            reloaded.authorization_output_receipt,
            reloaded.authorization_terminal_receipt,
            reloaded.pre_start_output_receipt,
            reloaded.pre_start_terminal_receipt,
            reloaded.store_scope.canonical_sha256,
            reloaded.declaration_envelope.canonical_sha256,
            reloaded.authorization_envelope.canonical_sha256,
            reloaded.claim_envelope.canonical_sha256,
            reloaded.start_envelope.canonical_sha256,
        )
    elif type(loaded) is _authoritative_start_type():
        from . import confirmation_authoritative_start_persistence as authoritative

        reloaded = authoritative.load_d7_authoritative_start_transaction(
            loaded.store_root,
            attempt_key_sha256=loaded.start.attempt_key_sha256,
            expected_manifest_sha256=loaded.manifest.canonical_sha256,
        )
        original_values = (
            loaded.declaration,
            loaded.authorization,
            loaded.claim,
            loaded.start,
            loaded.authorization_output_receipt,
            loaded.authorization_terminal_receipt,
            loaded.pre_start_output_receipt,
            loaded.pre_start_terminal_receipt,
            loaded.manifest.canonical_sha256,
            loaded.directory_identity_sha256,
            loaded.launch_authority_source_envelope_binding,
            loaded.verification_evidence_binding,
            dict(loaded.immutable_member_sources),
        )
        reloaded_values = (
            reloaded.declaration,
            reloaded.authorization,
            reloaded.claim,
            reloaded.start,
            reloaded.authorization_output_receipt,
            reloaded.authorization_terminal_receipt,
            reloaded.pre_start_output_receipt,
            reloaded.pre_start_terminal_receipt,
            reloaded.manifest.canonical_sha256,
            reloaded.directory_identity_sha256,
            reloaded.launch_authority_source_envelope_binding,
            reloaded.verification_evidence_binding,
            dict(reloaded.immutable_member_sources),
        )
    else:
        raise TypeError(
            "loaded_prefix must be an exact evidence-only or authoritative-start prefix"
        )
    if original_values != reloaded_values:
        raise QualificationContractError(
            "D7 persisted prefix changed before terminal transaction"
        )
    return reloaded


def _open_terminal_parent(loaded: object) -> tuple[p._DirectoryAnchor, str]:
    receipt = loaded.pre_start_terminal_receipt
    parent = p._open_real_directory(
        receipt.resolved_parent_realpath,
        label="D7 structural terminal parent",
    )
    try:
        if (
            parent.device,
            parent.inode,
        ) != (
            receipt.parent_device,
            receipt.parent_inode,
        ):
            raise QualificationContractError(
                "D7 structural terminal parent identity changed after start"
            )
        path = parent.path / receipt.subject_basename
        if path != Path(receipt.subject_path):
            raise QualificationContractError(
                "D7 structural terminal path differs from the start receipt"
            )
        p._verify_anchor(parent, label="D7 structural terminal parent")
        return parent, receipt.subject_basename
    except BaseException:
        os.close(parent.descriptor)
        raise


def _staging_prefix(attempt_key_sha256: str) -> str:
    return f".{p._sha256(attempt_key_sha256, 'attempt_key_sha256')}{_STAGING_MARKER}"


def _matching_staging_entries(
    parent: p._DirectoryAnchor,
    attempt_key_sha256: str,
) -> tuple[str, ...]:
    prefix = _staging_prefix(attempt_key_sha256)
    try:
        names = os.listdir(parent.descriptor)
    except OSError as error:
        raise QualificationContractError(
            f"cannot enumerate D7 structural terminal parent: {error}"
        ) from error
    return tuple(
        sorted(
            name
            for name in names
            if name.startswith(prefix) and name.endswith(_TEMPORARY_SUFFIX)
        )
    )


def _reject_staging_entries(
    parent: p._DirectoryAnchor,
    attempt_key_sha256: str,
) -> None:
    if _matching_staging_entries(parent, attempt_key_sha256):
        raise QualificationContractError(
            "D7 terminal parent contains unpublished staging entries; "
            "wait for live writers to quiesce and perform offline recovery only "
            "after orphanhood is established"
        )


def _member_by_filename(
    manifest: r.D7TerminalManifestRecord,
) -> dict[str, r.D7TerminalMemberBinding]:
    return {member.filename: member for member in manifest.immutable_members}


def _exact_member_sources(
    value: Mapping[str, bytes],
    manifest: r.D7TerminalManifestRecord,
) -> dict[str, bytes]:
    if type(value) is not dict:
        raise TypeError("immutable_member_sources must be an exact dict")
    if any(
        type(name) is not str or type(source) is not bytes
        for name, source in value.items()
    ):
        raise TypeError(
            "immutable terminal member names and sources must be exact values"
        )
    result = dict(value)
    members = _member_by_filename(manifest)
    if set(result) != set(members):
        raise QualificationContractError(
            "immutable terminal source inventory differs from manifest"
        )
    for filename, member in members.items():
        source = result[filename]
        if (
            not source
            or len(source) != member.byte_count
            or hashlib.sha256(source).hexdigest() != member.member_canonical_sha256
        ):
            raise QualificationContractError(
                f"terminal member {filename} differs from its manifest identity"
            )
    return result


def _parse_record(
    record_type: type[object],
    source: bytes,
    expected_sha256: str,
) -> object:
    parser = getattr(record_type, "from_canonical_bytes", None)
    if not callable(parser):
        raise TypeError("terminal record type has no canonical parser")
    return parser(source, expected_sha256=expected_sha256)


def _validate_scientific_sources(
    prefix: object,
    sources: dict[str, bytes],
    manifest: r.D7TerminalManifestRecord,
    consumption: r.D7TerminalConsumptionRecord,
) -> r.D7ScientificResultRecord:
    members = _member_by_filename(manifest)
    result_member = members.get(r.D7_SCIENTIFIC_RESULT_FILENAME)
    payload_member = members.get(r.D7_SCIENTIFIC_RESULT_PAYLOAD_FILENAME)
    if result_member is None or payload_member is None:
        raise QualificationContractError(
            "scientific terminal lacks result or result payload"
        )
    result = _parse_record(
        r.D7ScientificResultRecord,
        sources[r.D7_SCIENTIFIC_RESULT_FILENAME],
        result_member.member_canonical_sha256,
    )
    payload = _parse_record(
        r.D7ScientificResultPayload,
        sources[r.D7_SCIENTIFIC_RESULT_PAYLOAD_FILENAME],
        payload_member.member_canonical_sha256,
    )
    assert type(result) is r.D7ScientificResultRecord
    assert type(payload) is r.D7ScientificResultPayload

    components: list[c.D7ResultComponentPayload] = []
    for component_id in r.D7_RESULT_COMPONENT_ORDER:
        filename = _COMPONENT_FILENAMES[component_id]
        member = members.get(filename)
        if member is None:
            raise QualificationContractError(
                f"scientific terminal lacks {component_id.value}"
            )
        component = _parse_record(
            _COMPONENT_TYPES[component_id],
            sources[filename],
            member.member_canonical_sha256,
        )
        components.append(component)  # type: ignore[arg-type]
    (
        event_ledger,
        core_cells,
        loop_cells,
        primary_units,
        required_strata,
        aggregate_gates,
    ) = components
    assert type(event_ledger) is c.D7ExecutionEventLedgerPayload
    assert type(core_cells) is c.D7CoreCellOutcomesPayload
    assert type(loop_cells) is c.D7LoopCellOutcomesPayload
    assert type(primary_units) is c.D7PrimaryUnitOutcomesPayload
    assert type(required_strata) is c.D7RequiredStratumOutcomesPayload
    assert type(aggregate_gates) is c.D7AggregateGateOutcomesPayload
    cv.validate_d7_result_component_bundle(
        event_ledger=event_ledger,
        core_cells=core_cells,
        loop_cells=loop_cells,
        primary_units=primary_units,
        required_strata=required_strata,
        aggregate_gates=aggregate_gates,
        result_payload=payload,
    )
    v.validate_d7_scientific_attempt_chain(
        declaration=prefix.declaration,
        authorization=prefix.authorization,
        claim=prefix.claim,
        start=prefix.start,
        payload=payload,
        result=result,
        manifest=manifest,
        consumption=consumption,
    )
    return result


def _validate_failed_sources(
    prefix: object,
    sources: dict[str, bytes],
    manifest: r.D7TerminalManifestRecord,
    consumption: r.D7TerminalConsumptionRecord,
) -> r.D7FailedAttemptRecord:
    members = _member_by_filename(manifest)
    required = (
        r.D7_FAILED_ATTEMPT_FILENAME,
        r.D7_FAILURE_EVIDENCE_FILENAME,
        r.D7_FAILURE_EVIDENCE_PAYLOAD_FILENAME,
    )
    if any(filename not in members for filename in required):
        raise QualificationContractError(
            "failed terminal lacks failed-attempt or failure evidence"
        )
    failed_attempt = _parse_record(
        r.D7FailedAttemptRecord,
        sources[r.D7_FAILED_ATTEMPT_FILENAME],
        members[r.D7_FAILED_ATTEMPT_FILENAME].member_canonical_sha256,
    )
    evidence = _parse_record(
        r.D7FailureEvidenceRecord,
        sources[r.D7_FAILURE_EVIDENCE_FILENAME],
        members[r.D7_FAILURE_EVIDENCE_FILENAME].member_canonical_sha256,
    )
    payload = _parse_record(
        e.D7FailureEvidencePayload,
        sources[r.D7_FAILURE_EVIDENCE_PAYLOAD_FILENAME],
        members[r.D7_FAILURE_EVIDENCE_PAYLOAD_FILENAME].member_canonical_sha256,
    )
    assert type(failed_attempt) is r.D7FailedAttemptRecord
    assert type(evidence) is r.D7FailureEvidenceRecord
    assert type(payload) is e.D7FailureEvidencePayload
    ev.validate_d7_failure_evidence_payload_chain(
        start=prefix.start,
        payload=payload,
        evidence=evidence,
        failed_attempt=failed_attempt,
    )
    v.validate_d7_attempt_prefix(
        declaration=prefix.declaration,
        authorization=prefix.authorization,
        claim=prefix.claim,
        start=prefix.start,
    )
    if prefix.declaration.attempt_role is not r.D7AttemptRole.PRIMARY_CONFIRMATION:
        raise QualificationContractError(
            "isolated replay requires the combined primary-and-replay validator"
        )
    finalization: r.D7StartedUnresolvedFinalizationRecord | None = None
    if evidence.origin is r.D7FailureEvidenceOrigin.EXTERNAL:
        external_required = (
            r.D7_EXTERNAL_ABORT_VERIFICATION_RECEIPT_FILENAME,
            r.D7_SIGNED_EXTERNAL_ABORT_WITNESS_ENVELOPE_FILENAME,
            r.D7_STARTED_UNRESOLVED_FINALIZATION_FILENAME,
        )
        if any(filename not in members for filename in external_required):
            raise QualificationContractError(
                "external failed terminal lacks its signed witness chain"
            )
        receipt = _parse_record(
            e.D7ExternalAbortVerificationReceipt,
            sources[r.D7_EXTERNAL_ABORT_VERIFICATION_RECEIPT_FILENAME],
            members[
                r.D7_EXTERNAL_ABORT_VERIFICATION_RECEIPT_FILENAME
            ].member_canonical_sha256,
        )
        envelope = _parse_record(
            e.D7SignedExternalAbortWitnessEnvelope,
            sources[r.D7_SIGNED_EXTERNAL_ABORT_WITNESS_ENVELOPE_FILENAME],
            members[
                r.D7_SIGNED_EXTERNAL_ABORT_WITNESS_ENVELOPE_FILENAME
            ].member_canonical_sha256,
        )
        finalization_value = _parse_record(
            r.D7StartedUnresolvedFinalizationRecord,
            sources[r.D7_STARTED_UNRESOLVED_FINALIZATION_FILENAME],
            members[
                r.D7_STARTED_UNRESOLVED_FINALIZATION_FILENAME
            ].member_canonical_sha256,
        )
        assert type(receipt) is e.D7ExternalAbortVerificationReceipt
        assert type(envelope) is e.D7SignedExternalAbortWitnessEnvelope
        assert type(finalization_value) is r.D7StartedUnresolvedFinalizationRecord
        finalization = finalization_value
        ev.validate_d7_external_abort_verification_receipt(
            start=prefix.start,
            payload=payload,
            receipt=receipt,
            evidence=evidence,
            finalization=finalization,
            failed_attempt=failed_attempt,
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
    elif evidence.origin is not r.D7FailureEvidenceOrigin.IN_PROCESS:
        raise QualificationContractError(
            "failed terminal evidence origin is unsupported"
        )
    v.validate_d7_failed_terminal_chain(
        claim=prefix.claim,
        start=prefix.start,
        evidence=evidence,
        failed_attempt=failed_attempt,
        manifest=manifest,
        consumption=consumption,
        finalization=finalization,
    )
    return failed_attempt


def _validate_transaction_sources(
    prefix: object,
    immutable_member_sources: Mapping[str, bytes],
    manifest: r.D7TerminalManifestRecord,
    consumption: r.D7TerminalConsumptionRecord,
) -> tuple[
    dict[str, bytes],
    r.D7ScientificResultRecord | r.D7FailedAttemptRecord,
]:
    if type(manifest) is not r.D7TerminalManifestRecord:
        raise TypeError("manifest must be an exact D7TerminalManifestRecord")
    if type(consumption) is not r.D7TerminalConsumptionRecord:
        raise TypeError("consumption must be an exact D7TerminalConsumptionRecord")
    observed_start_lineage = (
        manifest.authoritative_start_manifest_sha256,
        manifest.authoritative_start_directory_identity_sha256,
        manifest.authority_verification_evidence_sha256,
    )
    if type(prefix) is _authoritative_start_type():
        expected_start_lineage = (
            prefix.manifest.canonical_sha256,
            prefix.directory_identity_sha256,
            prefix.verification_evidence_binding.canonical_sha256,
        )
    else:
        expected_start_lineage = (None, None, None)
    if observed_start_lineage != expected_start_lineage:
        raise QualificationContractError(
            "terminal authoritative-start lineage differs from its persisted prefix"
        )
    sources = _exact_member_sources(immutable_member_sources, manifest)
    if manifest.terminal_artifact_kind is r.D7TerminalArtifactKind.SCIENTIFIC_RESULT:
        artifact: r.D7ScientificResultRecord | r.D7FailedAttemptRecord = (
            _validate_scientific_sources(
                prefix,
                sources,
                manifest,
                consumption,
            )
        )
    else:
        artifact = _validate_failed_sources(
            prefix,
            sources,
            manifest,
            consumption,
        )
    return sources, artifact


def _member_maximum_bytes(member: r.D7TerminalMemberBinding) -> int:
    if member.member_kind is r.D7TerminalMemberKind.RESULT_COMPONENT:
        return r.MAX_D7_RESULT_COMPONENT_BYTES
    if member.member_kind is r.D7TerminalMemberKind.SCIENTIFIC_RESULT_PAYLOAD:
        return r.MAX_D7_RESULT_PAYLOAD_BYTES
    if member.member_kind in {
        r.D7TerminalMemberKind.FAILURE_EVIDENCE_PAYLOAD,
        r.D7TerminalMemberKind.EXTERNAL_ABORT_VERIFICATION_RECEIPT,
        r.D7TerminalMemberKind.SIGNED_EXTERNAL_ABORT_WITNESS_ENVELOPE,
    }:
        return e.MAX_D7_ATTEMPT_EVIDENCE_BYTES
    return r.MAX_D7_CHRONOLOGY_RECORD_BYTES


def _write_stage_file(
    stage: p._DirectoryAnchor,
    filename: str,
    source: bytes,
    *,
    expected_sha256: str,
    maximum_bytes: int,
    label: str,
) -> tuple[int, int]:
    expected = p._sha256(expected_sha256, f"{label} expected_sha256")
    if (
        type(source) is not bytes
        or not source
        or len(source) > maximum_bytes
        or hashlib.sha256(source).hexdigest() != expected
    ):
        raise QualificationContractError(
            f"{label} differs from its bounded canonical identity"
        )
    descriptor: int | None = None
    try:
        descriptor = os.open(
            filename,
            p._file_create_flags(),
            0o600,
            dir_fd=stage.descriptor,
        )
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
            raise QualificationContractError(f"{label} staged identity is invalid")
        p._write_all(descriptor, source)
        os.fsync(descriptor)
        after = os.fstat(descriptor)
        if (
            p._identity(after) != p._identity(before)
            or not stat.S_ISREG(after.st_mode)
            or after.st_nlink != 1
            or after.st_size != len(source)
        ):
            raise QualificationContractError(f"{label} changed while staging")
    except OSError as error:
        raise QualificationContractError(f"cannot stage {label}: {error}") from error
    finally:
        if descriptor is not None:
            os.close(descriptor)
    persisted, observed = p._read_exact_file(
        stage,
        filename,
        expected_sha256=expected,
        maximum_bytes=maximum_bytes,
        label=f"staged {label}",
    )
    if persisted != source:
        raise QualificationContractError(f"staged {label} bytes differ")
    return p._identity(observed)


def _create_stage(
    parent: p._DirectoryAnchor,
    attempt_key_sha256: str,
) -> tuple[p._DirectoryAnchor, str]:
    prefix = _staging_prefix(attempt_key_sha256)
    for _index in range(_MAX_STAGE_NAME_ATTEMPTS):
        leaf = f"{prefix}{secrets.token_hex(12)}{_TEMPORARY_SUFFIX}"
        try:
            os.mkdir(leaf, 0o700, dir_fd=parent.descriptor)
        except FileExistsError:
            continue
        except OSError as error:
            raise QualificationContractError(
                f"cannot create D7 terminal staging directory: {error}"
            ) from error
        try:
            os.fsync(parent.descriptor)
        except OSError as error:
            try:
                os.rmdir(leaf, dir_fd=parent.descriptor)
                os.fsync(parent.descriptor)
            except OSError:
                pass
            raise QualificationContractError(
                "D7 terminal staging-directory creation durability is unproved"
            ) from error
        return (
            p._open_child_directory(
                parent,
                leaf=leaf,
                label="D7 terminal staging directory",
                create=False,
            ),
            leaf,
        )
    raise QualificationContractError(
        "cannot allocate a unique D7 terminal staging directory"
    )


def _cleanup_stage(
    parent: p._DirectoryAnchor,
    stage: p._DirectoryAnchor,
    stage_leaf: str,
    owned_files: dict[str, tuple[int, int]],
) -> bool:
    try:
        names = set(os.listdir(stage.descriptor))
    except OSError:
        return False
    if names != set(owned_files):
        return False
    for filename in sorted(names):
        observed = p._relative_stat(stage, filename)
        if (
            observed is None
            or not stat.S_ISREG(observed.st_mode)
            or observed.st_nlink != 1
            or p._identity(observed) != owned_files[filename]
        ):
            return False
        try:
            os.unlink(filename, dir_fd=stage.descriptor)
        except OSError:
            return False
    try:
        os.rmdir(stage_leaf, dir_fd=parent.descriptor)
        os.fsync(parent.descriptor)
    except OSError:
        return False
    return p._relative_stat(parent, stage_leaf) is None


def _published_stage_identity_matches(
    parent: p._DirectoryAnchor,
    *,
    stage_leaf: str,
    terminal_leaf: str,
    stage_identity: tuple[int, int],
) -> bool:
    staged = p._relative_stat(parent, stage_leaf)
    terminal = p._relative_stat(parent, terminal_leaf)
    return (
        staged is None
        and terminal is not None
        and stat.S_ISDIR(terminal.st_mode)
        and p._identity(terminal) == stage_identity
    )


def _rename_stage_no_replace(
    parent: p._DirectoryAnchor,
    stage_leaf: str,
    terminal_leaf: str,
) -> None:
    p._rename_file_no_replace(parent, stage_leaf, terminal_leaf)


def _load_member_sources(
    terminal: p._DirectoryAnchor,
    manifest: r.D7TerminalManifestRecord,
) -> tuple[dict[str, bytes], tuple[tuple[int, int], ...]]:
    sources: dict[str, bytes] = {}
    identities: list[tuple[int, int]] = []
    for member in manifest.immutable_members:
        source, observed = p._read_exact_file(
            terminal,
            member.filename,
            expected_sha256=member.member_canonical_sha256,
            maximum_bytes=_member_maximum_bytes(member),
            label=f"D7 terminal member {member.filename}",
        )
        if len(source) != member.byte_count:
            raise QualificationContractError(
                f"D7 terminal member {member.filename} byte count differs"
            )
        sources[member.filename] = source
        identities.append(p._identity(observed))
    return sources, tuple(identities)


def _revalidate_file_set(
    directory: p._DirectoryAnchor,
    expected: Mapping[
        str,
        tuple[bytes, tuple[int, int], str, int, str],
    ],
) -> None:
    """Re-read a closed file set and require its original bytes and identities."""

    try:
        observed_names = set(os.listdir(directory.descriptor))
    except OSError as error:
        raise QualificationContractError(
            "cannot enumerate D7 terminal files during final revalidation"
        ) from error
    if observed_names != set(expected):
        raise QualificationContractError(
            "D7 terminal file inventory changed during structural validation"
        )
    for filename in sorted(expected):
        source, identity, expected_sha256, maximum_bytes, label = expected[filename]
        reloaded, observed = p._read_exact_file(
            directory,
            filename,
            expected_sha256=expected_sha256,
            maximum_bytes=maximum_bytes,
            label=f"final {label}",
        )
        if reloaded != source or p._identity(observed) != identity:
            raise QualificationContractError(
                f"{label} changed during structural validation"
            )


def load_d7_structural_terminal_transaction(
    loaded_prefix: object,
    *,
    expected_manifest_sha256: str,
    expected_consumption_sha256: str,
) -> D7LoadedStructuralTerminalTransaction:
    """Strictly load one closed D7 terminal directory as structural evidence."""

    expected_manifest = p._sha256(
        expected_manifest_sha256,
        "expected_manifest_sha256",
    )
    expected_consumption = p._sha256(
        expected_consumption_sha256,
        "expected_consumption_sha256",
    )
    prefix = _strictly_reload_prefix(loaded_prefix)
    parent, terminal_leaf = _open_terminal_parent(prefix)
    terminal: p._DirectoryAnchor | None = None
    try:
        displayed = p._relative_stat(parent, terminal_leaf)
        if displayed is None:
            if _matching_staging_entries(parent, prefix.start.attempt_key_sha256):
                raise QualificationContractError(
                    "D7 terminal is absent with unpublished staging entries; "
                    "offline recovery is required"
                )
            raise QualificationContractError("D7 structural terminal is absent")
        if not stat.S_ISDIR(displayed.st_mode):
            raise QualificationContractError(
                "D7 structural terminal must be one real directory"
            )
        terminal = p._open_child_directory(
            parent,
            leaf=terminal_leaf,
            label="D7 structural terminal transaction",
            create=False,
        )
        manifest_source, manifest_stat = p._read_exact_file(
            terminal,
            r.D7_TERMINAL_MANIFEST_FILENAME,
            expected_sha256=expected_manifest,
            maximum_bytes=r.MAX_D7_TERMINAL_MANIFEST_BYTES,
            label="D7 terminal manifest",
        )
        manifest = r.D7TerminalManifestRecord.from_canonical_bytes(
            manifest_source,
            expected_sha256=expected_manifest,
        )
        expected_names = {
            *(member.filename for member in manifest.immutable_members),
            r.D7_TERMINAL_MANIFEST_FILENAME,
            r.D7_TERMINAL_CONSUMPTION_FILENAME,
        }
        try:
            observed_names = set(os.listdir(terminal.descriptor))
        except OSError as error:
            raise QualificationContractError(
                f"cannot enumerate D7 structural terminal: {error}"
            ) from error
        if observed_names != expected_names:
            raise QualificationContractError(
                "D7 structural terminal members differ from the closed inventory"
            )
        consumption_source, consumption_stat = p._read_exact_file(
            terminal,
            r.D7_TERMINAL_CONSUMPTION_FILENAME,
            expected_sha256=expected_consumption,
            maximum_bytes=r.MAX_D7_CHRONOLOGY_RECORD_BYTES,
            label="D7 terminal consumption",
        )
        consumption = r.D7TerminalConsumptionRecord.from_canonical_bytes(
            consumption_source,
            expected_sha256=expected_consumption,
        )
        member_sources, member_identities = _load_member_sources(terminal, manifest)
        member_identity_by_name = {
            member.filename: identity
            for member, identity in zip(
                manifest.immutable_members,
                member_identities,
                strict=True,
            )
        }
        all_identities = (
            p._identity(manifest_stat),
            p._identity(consumption_stat),
            *member_identities,
        )
        if len(all_identities) != len(set(all_identities)):
            raise QualificationContractError(
                "D7 terminal members must have distinct file identities"
            )
        sources, artifact = _validate_transaction_sources(
            prefix,
            member_sources,
            manifest,
            consumption,
        )
        try:
            final_names = set(os.listdir(terminal.descriptor))
        except OSError as error:
            raise QualificationContractError(
                f"cannot re-enumerate D7 structural terminal: {error}"
            ) from error
        if final_names != expected_names:
            raise QualificationContractError(
                "D7 structural terminal inventory changed during strict reload"
            )
        _revalidate_file_set(
            terminal,
            {
                r.D7_TERMINAL_MANIFEST_FILENAME: (
                    manifest_source,
                    p._identity(manifest_stat),
                    manifest.canonical_sha256,
                    r.MAX_D7_TERMINAL_MANIFEST_BYTES,
                    "D7 terminal manifest",
                ),
                r.D7_TERMINAL_CONSUMPTION_FILENAME: (
                    consumption_source,
                    p._identity(consumption_stat),
                    consumption.canonical_sha256,
                    r.MAX_D7_CHRONOLOGY_RECORD_BYTES,
                    "D7 terminal consumption",
                ),
                **{
                    member.filename: (
                        member_sources[member.filename],
                        member_identity_by_name[member.filename],
                        member.member_canonical_sha256,
                        _member_maximum_bytes(member),
                        f"D7 terminal member {member.filename}",
                    )
                    for member in manifest.immutable_members
                },
            },
        )
        p._verify_anchor(terminal, label="D7 structural terminal transaction")
        p._verify_anchor(parent, label="D7 structural terminal parent")
        return D7LoadedStructuralTerminalTransaction(
            path=parent.path / terminal_leaf,
            prefix=prefix,
            manifest=manifest,
            consumption=consumption,
            terminal_artifact=artifact,
            immutable_member_sources=MappingProxyType(sources),
            directory_device=terminal.device,
            directory_inode=terminal.inode,
        )
    finally:
        if terminal is not None:
            os.close(terminal.descriptor)
        os.close(parent.descriptor)


def persist_d7_structural_terminal_transaction_no_replace(
    loaded_prefix: object,
    *,
    immutable_member_sources: Mapping[str, bytes],
    manifest: r.D7TerminalManifestRecord,
    consumption: r.D7TerminalConsumptionRecord,
) -> D7PersistedStructuralTerminalIdentity:
    """Atomically persist one prevalidated structural D7 terminal transaction."""

    prefix = _strictly_reload_prefix(loaded_prefix)
    sources, expected_artifact = _validate_transaction_sources(
        prefix,
        immutable_member_sources,
        manifest,
        consumption,
    )
    parent, terminal_leaf = _open_terminal_parent(prefix)
    stage: p._DirectoryAnchor | None = None
    stage_leaf: str | None = None
    owned_files: dict[str, tuple[int, int]] = {}
    published = False
    parent_fsync_proved = False
    try:
        _reject_staging_entries(parent, prefix.start.attempt_key_sha256)
        p._require_absent(
            parent,
            terminal_leaf,
            label="D7 structural terminal transaction",
        )
        stage, stage_leaf = _create_stage(parent, prefix.start.attempt_key_sha256)
        members = _member_by_filename(manifest)
        for filename in sorted(sources):
            member = members[filename]
            owned_files[filename] = _write_stage_file(
                stage,
                filename,
                sources[filename],
                expected_sha256=member.member_canonical_sha256,
                maximum_bytes=_member_maximum_bytes(member),
                label=f"D7 terminal member {filename}",
            )
        owned_files[r.D7_TERMINAL_MANIFEST_FILENAME] = _write_stage_file(
            stage,
            r.D7_TERMINAL_MANIFEST_FILENAME,
            manifest.canonical_bytes,
            expected_sha256=manifest.canonical_sha256,
            maximum_bytes=r.MAX_D7_TERMINAL_MANIFEST_BYTES,
            label="D7 terminal manifest",
        )
        owned_files[r.D7_TERMINAL_CONSUMPTION_FILENAME] = _write_stage_file(
            stage,
            r.D7_TERMINAL_CONSUMPTION_FILENAME,
            consumption.canonical_bytes,
            expected_sha256=consumption.canonical_sha256,
            maximum_bytes=r.MAX_D7_CHRONOLOGY_RECORD_BYTES,
            label="D7 terminal consumption",
        )
        try:
            os.fsync(stage.descriptor)
        except OSError as error:
            raise QualificationContractError(
                "D7 terminal staging-directory durability is unproved"
            ) from error

        prefix_before_publish = _strictly_reload_prefix(prefix)
        if prefix_before_publish.start != prefix.start:
            raise QualificationContractError(
                "D7 persisted start changed before terminal publication"
            )
        p._verify_anchor(parent, label="D7 structural terminal parent")
        p._require_absent(
            parent,
            terminal_leaf,
            label="D7 structural terminal transaction",
        )
        _revalidate_file_set(
            stage,
            {
                **{
                    filename: (
                        sources[filename],
                        owned_files[filename],
                        members[filename].member_canonical_sha256,
                        _member_maximum_bytes(members[filename]),
                        f"staged D7 terminal member {filename}",
                    )
                    for filename in sources
                },
                r.D7_TERMINAL_MANIFEST_FILENAME: (
                    manifest.canonical_bytes,
                    owned_files[r.D7_TERMINAL_MANIFEST_FILENAME],
                    manifest.canonical_sha256,
                    r.MAX_D7_TERMINAL_MANIFEST_BYTES,
                    "staged D7 terminal manifest",
                ),
                r.D7_TERMINAL_CONSUMPTION_FILENAME: (
                    consumption.canonical_bytes,
                    owned_files[r.D7_TERMINAL_CONSUMPTION_FILENAME],
                    consumption.canonical_sha256,
                    r.MAX_D7_CHRONOLOGY_RECORD_BYTES,
                    "staged D7 terminal consumption",
                ),
            },
        )
        p._verify_anchor(stage, label="D7 terminal staging directory")
        p._verify_anchor(parent, label="D7 structural terminal parent")
        stage_identity = (stage.device, stage.inode)
        try:
            _rename_stage_no_replace(parent, stage_leaf, terminal_leaf)
            published = True
        except OSError as error:
            if _published_stage_identity_matches(
                parent,
                stage_leaf=stage_leaf,
                terminal_leaf=terminal_leaf,
                stage_identity=stage_identity,
            ):
                published = True
            elif error.errno in (errno.EEXIST, errno.ENOTEMPTY):
                raise QualificationContractError(
                    "refusing to replace existing D7 structural terminal "
                    f"transaction: {parent.path / terminal_leaf}"
                ) from error
            else:
                raise QualificationContractError(
                    f"cannot atomically publish D7 structural terminal: {error}"
                ) from error
        if not _published_stage_identity_matches(
            parent,
            stage_leaf=stage_leaf,
            terminal_leaf=terminal_leaf,
            stage_identity=stage_identity,
        ):
            raise QualificationContractError(
                "published D7 structural terminal directory identity differs"
            )
        try:
            os.fsync(parent.descriptor)
            parent_fsync_proved = True
        except OSError:
            parent_fsync_proved = False
    finally:
        cleanup_proved = published
        cleanup_error: BaseException | None = None
        try:
            if stage is not None:
                try:
                    if not published and stage_leaf is not None:
                        cleanup_proved = _cleanup_stage(
                            parent,
                            stage,
                            stage_leaf,
                            owned_files,
                        )
                except BaseException as error:
                    cleanup_error = error
                finally:
                    os.close(stage.descriptor)
        finally:
            os.close(parent.descriptor)
        if cleanup_error is not None:
            raise QualificationContractError(
                "D7 terminal staging cleanup is unproved; offline recovery is required"
            ) from cleanup_error
        if stage is not None and not cleanup_proved:
            raise QualificationContractError(
                "D7 terminal staging cleanup is unproved; offline recovery is required"
            )

    if not published:
        raise QualificationContractError("D7 structural terminal was not published")
    loaded = load_d7_structural_terminal_transaction(
        prefix,
        expected_manifest_sha256=manifest.canonical_sha256,
        expected_consumption_sha256=consumption.canonical_sha256,
    )
    if (
        loaded.manifest != manifest
        or loaded.consumption != consumption
        or loaded.terminal_artifact != expected_artifact
    ):
        raise QualificationContractError(
            "strictly reloaded D7 structural terminal differs from staged values"
        )
    return D7PersistedStructuralTerminalIdentity(
        path=loaded.path,
        terminal_artifact_kind=manifest.terminal_artifact_kind,
        terminal_artifact_sha256=expected_artifact.canonical_sha256,
        terminal_manifest_sha256=manifest.canonical_sha256,
        terminal_consumption_sha256=consumption.canonical_sha256,
        directory_device=loaded.directory_device,
        directory_inode=loaded.directory_inode,
        parent_directory_fsync_proved=parent_fsync_proved,
    )
