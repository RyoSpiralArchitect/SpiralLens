"""Descriptor-anchored evidence-only persistence for future D7 attempts.

This module persists caller-supplied, already typed Level-0 records.  It does
not load a replay target, grant admission or execution authority, authenticate
an external witness, publish a terminal, establish ``started_unresolved``, run
an experiment, or advance D7/D8. The lifecycle records are nested inside a
different top-level envelope whose canonical bytes permanently state that no
authority or execution/finalization capability was issued.

The evidence chronology is declaration -> authorization -> claim -> start.
Each envelope is published under a dedicated evidence-only namespace with a
descriptor-relative native exclusive rename, so an existing destination is
never replaced and no two-name publication window is introduced. Authorization
and pre-start absence receipts are content-addressed companion files. A complete
prefix with no terminal entry is reported only as a structural observation.
"""

from __future__ import annotations

import ctypes
import errno
import hashlib
import os
import re
import secrets
import stat
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path, PurePosixPath
from typing import ClassVar

from spirallens.core.canonical import (
    CanonicalJsonError,
    canonical_json_bytes,
    parse_canonical_json,
    sha256_bytes,
)

from . import confirmation_attempt_evidence as e
from . import confirmation_attempt_evidence_validation as ev
from . import confirmation_attempt_records as r
from . import confirmation_attempt_validation as v
from .common import QualificationContractError

__all__: tuple[str, ...] = ()

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_ATTEMPT_DECLARATION_SUFFIX = ".attempt-declaration.envelope.json"
_LAUNCH_AUTHORIZATION_SUFFIX = ".launch-authorization.envelope.json"
_ATTEMPT_CLAIM_SUFFIX = ".attempt-claim.envelope.json"
_EXECUTION_START_SUFFIX = ".execution-start.envelope.json"
_PREFIX_LANE_DIRECTORY_LEAF = "d7-prefix-evidence-only-v0"
_PREFIX_SCOPE_LEAF = "store-scope.json"
_EVIDENCE_DIRECTORY_LEAF = "d7-attempt-evidence"
_TEMPORARY_SUFFIX = ".tmp"
_CHRONOLOGY_LEAF_RE = re.compile(
    r"^[0-9a-f]{64}\."
    r"(?:attempt-declaration|launch-authorization|attempt-claim|execution-start)"
    r"(?:\.envelope)?\.json$"
)
_PREFIX_ENVELOPE_SCHEMA_VERSION = "spirallens.d7-prefix-persistence-envelope.v0.1"
_PREFIX_SCOPE_SCHEMA_VERSION = "spirallens.d7-caller-supplied-prefix-store-scope.v0.1"
_PREFIX_LANE_ID = "d7-level0-prefix-evidence-only-v0"
_PREFIX_ENVELOPE_RECORD_KIND = "persistence-only-stage-envelope"
_PREFIX_SCOPE_RECORD_KIND = "caller-supplied-prefix-store-scope"
_PREFIX_RECORD_SCOPE = "persistence-only-structural-observation"
_PREFIX_PERSISTENCE_MODE = "caller-supplied-level-0"
_PREFIX_STORAGE_LAYOUT = "spirallens.d7-prefix-evidence-only-layout.v0.1"
_PREFIX_ENVELOPE_CLAIM_CEILING = "level_0"
_MAX_PREFIX_ENVELOPE_BYTES = 256 * 1024
_DARWIN_RENAME_EXCL = 0x00000004
_DARWIN_RENAME_NOFOLLOW_ANY = 0x00000010
_DARWIN_RENAME_RESOLVE_BENEATH = 0x00000020
_LINUX_RENAME_NOREPLACE = 1


class D7EvidenceOnlyPrefixState(str, Enum):
    """Structural states this evidence-only slice can establish."""

    CALLER_SUPPLIED_START_RECORD_PRESENT_TERMINAL_ABSENT = (
        "caller_supplied_start_record_present_terminal_absent"
    )
    TERMINAL_PATH_PRESENT_UNVERIFIED = "terminal_path_present_unverified"


class _D7PrefixStageKind(str, Enum):
    ATTEMPT_DECLARATION = "attempt-declaration"
    LAUNCH_AUTHORIZATION = "launch-authorization"
    ATTEMPT_CLAIM = "attempt-claim"
    EXECUTION_START = "execution-start"


@dataclass(frozen=True, slots=True)
class D7PersistedRecordIdentity:
    """Exact identity of one visible canonical file publication."""

    path: Path
    canonical_sha256: str
    byte_count: int
    device: int
    inode: int
    parent_directory_fsync_proved: bool
    created_by_call: bool
    atomic_no_replace: bool = True
    authority_granted: bool = False

    def __post_init__(self) -> None:
        if (
            not isinstance(self.path, Path)
            or not self.path.is_absolute()
            or type(self.canonical_sha256) is not str
            or _SHA256_RE.fullmatch(self.canonical_sha256) is None
        ):
            raise TypeError("persisted identity path or SHA-256 is invalid")
        if type(self.byte_count) is not int or self.byte_count <= 0:
            raise TypeError("byte_count must be a positive plain integer")
        for name in ("device", "inode"):
            value = getattr(self, name)
            if type(value) is not int or value < 0:
                raise TypeError(f"{name} must be a nonnegative plain integer")
        for name in (
            "parent_directory_fsync_proved",
            "created_by_call",
            "atomic_no_replace",
            "authority_granted",
        ):
            if type(getattr(self, name)) is not bool:
                raise TypeError(f"{name} must be a plain boolean")
        if self.atomic_no_replace is not True or self.authority_granted is not False:
            raise QualificationContractError("D7 persistence identity constants differ")


@dataclass(frozen=True, slots=True)
class _D7PrefixStoreScope:
    """Immutable evidence-lane scope; every stage envelope binds its digest."""

    store_root_realpath: str
    store_device: int
    store_inode: int
    lane_realpath: str
    lane_device: int
    lane_inode: int
    declared_store_identity_sha256: str

    schema_version: ClassVar[str] = _PREFIX_SCOPE_SCHEMA_VERSION
    record_kind: ClassVar[str] = _PREFIX_SCOPE_RECORD_KIND
    record_scope: ClassVar[str] = _PREFIX_RECORD_SCOPE
    claim_ceiling: ClassVar[str] = _PREFIX_ENVELOPE_CLAIM_CEILING
    persistence_mode: ClassVar[str] = _PREFIX_PERSISTENCE_MODE
    storage_layout: ClassVar[str] = _PREFIX_STORAGE_LAYOUT
    authority_granted: ClassVar[bool] = False
    authoritative_lifecycle_eligible: ClassVar[bool] = False
    in_place_promotion_allowed: ClassVar[bool] = False
    authoritative_replay_target_loaded: ClassVar[bool] = False
    launch_intent_loaded: ClassVar[bool] = False
    source_runtime_verified: ClassVar[bool] = False
    execution_identity_verified: ClassVar[bool] = False
    d7_execution_authorized: ClassVar[bool] = False
    terminal_publication_authorized: ClassVar[bool] = False
    unresolved_finalization_authorized: ClassVar[bool] = False
    d7_result_produced: ClassVar[bool] = False
    isolated_replay_authorized: ClassVar[bool] = False
    d8_execution_authorized: ClassVar[bool] = False

    def __post_init__(self) -> None:
        _absolute_path_string(self.store_root_realpath, "store_root_realpath")
        _absolute_path_string(self.lane_realpath, "lane_realpath")
        for name in ("store_device", "store_inode", "lane_device", "lane_inode"):
            _nonnegative_int(getattr(self, name), name)
        _sha256(
            self.declared_store_identity_sha256,
            "declared_store_identity_sha256",
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "record_kind": self.record_kind,
            "record_scope": self.record_scope,
            "claim_ceiling": self.claim_ceiling,
            "persistence_mode": self.persistence_mode,
            "storage_layout": self.storage_layout,
            "store_root_realpath": self.store_root_realpath,
            "store_device": self.store_device,
            "store_inode": self.store_inode,
            "lane_realpath": self.lane_realpath,
            "lane_device": self.lane_device,
            "lane_inode": self.lane_inode,
            "declared_store_identity_sha256": (self.declared_store_identity_sha256),
            "authority_granted": self.authority_granted,
            "authoritative_lifecycle_eligible": (self.authoritative_lifecycle_eligible),
            "in_place_promotion_allowed": self.in_place_promotion_allowed,
            "authoritative_replay_target_loaded": (
                self.authoritative_replay_target_loaded
            ),
            "launch_intent_loaded": self.launch_intent_loaded,
            "source_runtime_verified": self.source_runtime_verified,
            "execution_identity_verified": self.execution_identity_verified,
            "d7_execution_authorized": self.d7_execution_authorized,
            "terminal_publication_authorized": (self.terminal_publication_authorized),
            "unresolved_finalization_authorized": (
                self.unresolved_finalization_authorized
            ),
            "d7_result_produced": self.d7_result_produced,
            "isolated_replay_authorized": self.isolated_replay_authorized,
            "d8_execution_authorized": self.d8_execution_authorized,
        }

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_dict())

    @property
    def canonical_sha256(self) -> str:
        return sha256_bytes(self.canonical_bytes)

    @classmethod
    def from_canonical_bytes(
        cls,
        source: bytes,
        *,
        expected_sha256: str,
    ) -> _D7PrefixStoreScope:
        expected = _sha256(expected_sha256, "scope expected_sha256")
        if (
            type(source) is not bytes
            or not source
            or len(source) > r.MAX_D7_CHRONOLOGY_RECORD_BYTES
            or sha256_bytes(source) != expected
        ):
            raise QualificationContractError(
                "D7 prefix store scope bytes differ from identity"
            )
        try:
            document = parse_canonical_json(
                source,
                label="D7 prefix store scope",
            )
        except CanonicalJsonError as error:
            raise QualificationContractError(str(error)) from error
        if type(document) is not dict:
            raise QualificationContractError("D7 prefix store scope must be an object")
        constants = {
            "schema_version": cls.schema_version,
            "record_kind": cls.record_kind,
            "record_scope": cls.record_scope,
            "claim_ceiling": cls.claim_ceiling,
            "persistence_mode": cls.persistence_mode,
            "storage_layout": cls.storage_layout,
            "authority_granted": False,
            "authoritative_lifecycle_eligible": False,
            "in_place_promotion_allowed": False,
            "authoritative_replay_target_loaded": False,
            "launch_intent_loaded": False,
            "source_runtime_verified": False,
            "execution_identity_verified": False,
            "d7_execution_authorized": False,
            "terminal_publication_authorized": False,
            "unresolved_finalization_authorized": False,
            "d7_result_produced": False,
            "isolated_replay_authorized": False,
            "d8_execution_authorized": False,
        }
        dynamic_fields = {
            "store_root_realpath",
            "store_device",
            "store_inode",
            "lane_realpath",
            "lane_device",
            "lane_inode",
            "declared_store_identity_sha256",
        }
        if set(document) != set(constants).union(dynamic_fields):
            raise QualificationContractError(
                "D7 prefix store scope fields differ from the contract"
            )
        if any(
            type(document[name]) is not type(value) or document[name] != value
            for name, value in constants.items()
        ):
            raise QualificationContractError(
                "D7 prefix store scope authority constants differ"
            )
        result = cls(
            store_root_realpath=_absolute_path_string(
                document["store_root_realpath"],
                "store_root_realpath",
            ),
            store_device=_nonnegative_int(
                document["store_device"],
                "store_device",
            ),
            store_inode=_nonnegative_int(
                document["store_inode"],
                "store_inode",
            ),
            lane_realpath=_absolute_path_string(
                document["lane_realpath"],
                "lane_realpath",
            ),
            lane_device=_nonnegative_int(
                document["lane_device"],
                "lane_device",
            ),
            lane_inode=_nonnegative_int(
                document["lane_inode"],
                "lane_inode",
            ),
            declared_store_identity_sha256=_sha256(
                document["declared_store_identity_sha256"],
                "declared_store_identity_sha256",
            ),
        )
        if result.canonical_bytes != source:
            raise QualificationContractError(
                "D7 prefix store scope differs after reconstruction"
            )
        return result


@dataclass(frozen=True, slots=True)
class _D7PrefixPersistenceEnvelope:
    """Canonical byte-level discriminator for one non-authoritative stage."""

    stage_kind: _D7PrefixStageKind
    attempt_key_sha256: str
    store_scope_sha256: str
    previous_envelope_sha256: str | None
    embedded_record_schema_version: str
    embedded_record_sha256: str
    embedded_record_byte_count: int
    embedded_record: object
    store_root_realpath: str
    store_device: int
    store_inode: int
    lane_realpath: str
    lane_device: int
    lane_inode: int

    schema_version: ClassVar[str] = _PREFIX_ENVELOPE_SCHEMA_VERSION
    lane_id: ClassVar[str] = _PREFIX_LANE_ID
    record_kind: ClassVar[str] = _PREFIX_ENVELOPE_RECORD_KIND
    claim_ceiling: ClassVar[str] = _PREFIX_ENVELOPE_CLAIM_CEILING
    authority_granted: ClassVar[bool] = False
    authoritative_lifecycle_eligible: ClassVar[bool] = False
    execution_capability_issued: ClassVar[bool] = False
    terminal_finalization_capability_issued: ClassVar[bool] = False

    def __post_init__(self) -> None:
        if type(self.stage_kind) is not _D7PrefixStageKind:
            raise TypeError("stage_kind must be an exact _D7PrefixStageKind")
        _sha256(self.attempt_key_sha256, "attempt_key_sha256")
        _sha256(self.store_scope_sha256, "store_scope_sha256")
        if self.stage_kind is _D7PrefixStageKind.ATTEMPT_DECLARATION:
            if self.previous_envelope_sha256 is not None:
                raise QualificationContractError(
                    "declaration envelope cannot bind a predecessor"
                )
        else:
            _sha256(
                self.previous_envelope_sha256,
                "previous_envelope_sha256",
            )
        expected_type = _stage_record_type(self.stage_kind)
        if type(self.embedded_record) is not expected_type:
            raise TypeError("embedded_record has the wrong exact stage type")
        record_bytes = self.embedded_record.canonical_bytes
        if (
            self.embedded_record_schema_version != self.embedded_record.schema_version
            or self.embedded_record_sha256 != self.embedded_record.canonical_sha256
            or self.embedded_record_byte_count != len(record_bytes)
            or self.embedded_record.attempt_key_sha256 != self.attempt_key_sha256
        ):
            raise QualificationContractError(
                "embedded record identity differs from its envelope"
            )
        for value, label in (
            (self.store_root_realpath, "store_root_realpath"),
            (self.lane_realpath, "lane_realpath"),
        ):
            if (
                type(value) is not str
                or not value
                or value != value.strip()
                or not Path(value).is_absolute()
            ):
                raise QualificationContractError(
                    f"{label} must be one absolute non-empty path"
                )
        for name in ("store_device", "store_inode", "lane_device", "lane_inode"):
            value = getattr(self, name)
            if type(value) is not int or value < 0:
                raise QualificationContractError(
                    f"{name} must be a nonnegative plain integer"
                )
        if type(self.embedded_record_byte_count) is not int or (
            self.embedded_record_byte_count <= 0
        ):
            raise QualificationContractError(
                "embedded_record_byte_count must be a positive plain integer"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "lane_id": self.lane_id,
            "record_kind": self.record_kind,
            "claim_ceiling": self.claim_ceiling,
            "authority_granted": self.authority_granted,
            "authoritative_lifecycle_eligible": (self.authoritative_lifecycle_eligible),
            "execution_capability_issued": self.execution_capability_issued,
            "terminal_finalization_capability_issued": (
                self.terminal_finalization_capability_issued
            ),
            "stage_kind": self.stage_kind.value,
            "attempt_key_sha256": self.attempt_key_sha256,
            "store_scope_sha256": self.store_scope_sha256,
            "previous_envelope_sha256": self.previous_envelope_sha256,
            "embedded_record_schema_version": self.embedded_record_schema_version,
            "embedded_record_sha256": self.embedded_record_sha256,
            "embedded_record_byte_count": self.embedded_record_byte_count,
            "embedded_record": parse_canonical_json(
                self.embedded_record.canonical_bytes,
                label="embedded D7 prefix record",
            ),
            "store_root_realpath": self.store_root_realpath,
            "store_device": self.store_device,
            "store_inode": self.store_inode,
            "lane_realpath": self.lane_realpath,
            "lane_device": self.lane_device,
            "lane_inode": self.lane_inode,
        }

    @property
    def canonical_bytes(self) -> bytes:
        source = canonical_json_bytes(self.to_dict())
        if len(source) > _MAX_PREFIX_ENVELOPE_BYTES:
            raise QualificationContractError(
                "D7 prefix persistence envelope exceeds its byte cap"
            )
        return source

    @property
    def canonical_sha256(self) -> str:
        return sha256_bytes(self.canonical_bytes)

    @classmethod
    def from_canonical_bytes(
        cls,
        source: bytes,
        *,
        expected_sha256: str,
    ) -> _D7PrefixPersistenceEnvelope:
        expected = _sha256(expected_sha256, "envelope expected_sha256")
        if (
            type(source) is not bytes
            or not source
            or len(source) > _MAX_PREFIX_ENVELOPE_BYTES
            or sha256_bytes(source) != expected
        ):
            raise QualificationContractError(
                "D7 prefix persistence envelope bytes differ from identity"
            )
        try:
            document = parse_canonical_json(
                source,
                label="D7 prefix persistence envelope",
            )
        except CanonicalJsonError as error:
            raise QualificationContractError(str(error)) from error
        if type(document) is not dict:
            raise QualificationContractError(
                "D7 prefix persistence envelope must be an object"
            )
        expected_fields = {
            "schema_version",
            "lane_id",
            "record_kind",
            "claim_ceiling",
            "authority_granted",
            "authoritative_lifecycle_eligible",
            "execution_capability_issued",
            "terminal_finalization_capability_issued",
            "stage_kind",
            "attempt_key_sha256",
            "store_scope_sha256",
            "previous_envelope_sha256",
            "embedded_record_schema_version",
            "embedded_record_sha256",
            "embedded_record_byte_count",
            "embedded_record",
            "store_root_realpath",
            "store_device",
            "store_inode",
            "lane_realpath",
            "lane_device",
            "lane_inode",
        }
        if set(document) != expected_fields:
            raise QualificationContractError(
                "D7 prefix persistence envelope fields differ from the contract"
            )
        constants = {
            "schema_version": cls.schema_version,
            "lane_id": cls.lane_id,
            "record_kind": cls.record_kind,
            "claim_ceiling": cls.claim_ceiling,
            "authority_granted": False,
            "authoritative_lifecycle_eligible": False,
            "execution_capability_issued": False,
            "terminal_finalization_capability_issued": False,
        }
        if any(
            type(document[name]) is not type(value) or document[name] != value
            for name, value in constants.items()
        ):
            raise QualificationContractError(
                "D7 prefix persistence envelope authority constants differ"
            )
        try:
            stage_kind = _D7PrefixStageKind(document["stage_kind"])
        except (TypeError, ValueError) as error:
            raise QualificationContractError(
                "D7 prefix persistence envelope stage_kind is unsupported"
            ) from error
        embedded_document = document["embedded_record"]
        if type(embedded_document) is not dict:
            raise QualificationContractError("embedded_record must be an object")
        embedded_bytes = canonical_json_bytes(embedded_document)
        embedded_sha256 = _sha256(
            document["embedded_record_sha256"],
            "embedded_record_sha256",
        )
        embedded_byte_count = document["embedded_record_byte_count"]
        if (
            type(embedded_byte_count) is not int
            or embedded_byte_count <= 0
            or embedded_byte_count != len(embedded_bytes)
            or sha256_bytes(embedded_bytes) != embedded_sha256
        ):
            raise QualificationContractError(
                "embedded record bytes differ from envelope binding"
            )
        record_type = _stage_record_type(stage_kind)
        embedded_record = record_type.from_canonical_bytes(
            embedded_bytes,
            expected_sha256=embedded_sha256,
        )
        previous = document["previous_envelope_sha256"]
        if previous is not None:
            previous = _sha256(previous, "previous_envelope_sha256")
        result = cls(
            stage_kind=stage_kind,
            attempt_key_sha256=_sha256(
                document["attempt_key_sha256"],
                "attempt_key_sha256",
            ),
            store_scope_sha256=_sha256(
                document["store_scope_sha256"],
                "store_scope_sha256",
            ),
            previous_envelope_sha256=previous,
            embedded_record_schema_version=_nonempty_string(
                document["embedded_record_schema_version"],
                "embedded_record_schema_version",
            ),
            embedded_record_sha256=embedded_sha256,
            embedded_record_byte_count=embedded_byte_count,
            embedded_record=embedded_record,
            store_root_realpath=_absolute_path_string(
                document["store_root_realpath"],
                "store_root_realpath",
            ),
            store_device=_nonnegative_int(
                document["store_device"],
                "store_device",
            ),
            store_inode=_nonnegative_int(
                document["store_inode"],
                "store_inode",
            ),
            lane_realpath=_absolute_path_string(
                document["lane_realpath"],
                "lane_realpath",
            ),
            lane_device=_nonnegative_int(
                document["lane_device"],
                "lane_device",
            ),
            lane_inode=_nonnegative_int(
                document["lane_inode"],
                "lane_inode",
            ),
        )
        if result.canonical_bytes != source:
            raise QualificationContractError(
                "D7 prefix persistence envelope differs after reconstruction"
            )
        return result


@dataclass(frozen=True, slots=True)
class D7LoadedEvidenceOnlyPrefix:
    """Strictly reloaded non-authoritative prefix through a start record."""

    store_root: Path
    declaration: r.D7AttemptDeclarationRecord
    authorization: r.D7LaunchAuthorizationRecord
    claim: r.D7AttemptClaimRecord
    start: r.D7ExecutionStartRecord
    authorization_output_receipt: e.D7AuthorizationPathAbsenceReceipt
    authorization_terminal_receipt: e.D7AuthorizationPathAbsenceReceipt
    pre_start_output_receipt: e.D7PreStartPathAbsenceReceipt
    pre_start_terminal_receipt: e.D7PreStartPathAbsenceReceipt
    store_scope: _D7PrefixStoreScope
    declaration_envelope: _D7PrefixPersistenceEnvelope
    authorization_envelope: _D7PrefixPersistenceEnvelope
    claim_envelope: _D7PrefixPersistenceEnvelope
    start_envelope: _D7PrefixPersistenceEnvelope
    store_scope_identity: D7PersistedRecordIdentity
    declaration_identity: D7PersistedRecordIdentity
    authorization_identity: D7PersistedRecordIdentity
    claim_identity: D7PersistedRecordIdentity
    start_identity: D7PersistedRecordIdentity

    _EXACT_TYPES: ClassVar[tuple[type[object], ...]] = (
        r.D7AttemptDeclarationRecord,
        r.D7LaunchAuthorizationRecord,
        r.D7AttemptClaimRecord,
        r.D7ExecutionStartRecord,
        e.D7AuthorizationPathAbsenceReceipt,
        e.D7AuthorizationPathAbsenceReceipt,
        e.D7PreStartPathAbsenceReceipt,
        e.D7PreStartPathAbsenceReceipt,
        _D7PrefixStoreScope,
        _D7PrefixPersistenceEnvelope,
        _D7PrefixPersistenceEnvelope,
        _D7PrefixPersistenceEnvelope,
        _D7PrefixPersistenceEnvelope,
        D7PersistedRecordIdentity,
        D7PersistedRecordIdentity,
        D7PersistedRecordIdentity,
        D7PersistedRecordIdentity,
        D7PersistedRecordIdentity,
    )

    def __post_init__(self) -> None:
        if not isinstance(self.store_root, Path) or not self.store_root.is_absolute():
            raise TypeError("store_root must be an absolute Path")
        values = (
            self.declaration,
            self.authorization,
            self.claim,
            self.start,
            self.authorization_output_receipt,
            self.authorization_terminal_receipt,
            self.pre_start_output_receipt,
            self.pre_start_terminal_receipt,
            self.store_scope,
            self.declaration_envelope,
            self.authorization_envelope,
            self.claim_envelope,
            self.start_envelope,
            self.store_scope_identity,
            self.declaration_identity,
            self.authorization_identity,
            self.claim_identity,
            self.start_identity,
        )
        if tuple(type(value) for value in values) != self._EXACT_TYPES:
            raise TypeError("loaded D7 evidence-only prefix values have wrong types")
        v.validate_d7_attempt_prefix(
            declaration=self.declaration,
            authorization=self.authorization,
            claim=self.claim,
            start=self.start,
        )
        ev.validate_d7_path_absence_receipt_chain(
            declaration=self.declaration,
            authorization=self.authorization,
            claim=self.claim,
            start=self.start,
            authorization_output_receipt=self.authorization_output_receipt,
            authorization_terminal_receipt=self.authorization_terminal_receipt,
            pre_start_output_receipt=self.pre_start_output_receipt,
            pre_start_terminal_receipt=self.pre_start_terminal_receipt,
        )
        if (
            self.store_scope.canonical_sha256
            != self.store_scope_identity.canonical_sha256
            or len(self.store_scope.canonical_bytes)
            != self.store_scope_identity.byte_count
            or self.store_scope_identity.path
            != self.store_root / _PREFIX_LANE_DIRECTORY_LEAF / _PREFIX_SCOPE_LEAF
            or self.store_scope.store_root_realpath != str(self.store_root)
            or self.store_scope.lane_realpath
            != str(self.store_root / _PREFIX_LANE_DIRECTORY_LEAF)
            or self.store_scope.declared_store_identity_sha256
            != self.declaration.store_identity_sha256
            or self.store_scope.authority_granted is not False
            or self.store_scope.authoritative_lifecycle_eligible is not False
            or self.store_scope.in_place_promotion_allowed is not False
        ):
            raise QualificationContractError(
                "loaded D7 evidence store scope differs from its identity"
            )
        stages = (
            (
                self.declaration,
                self.declaration_envelope,
                self.declaration_identity,
                _D7PrefixStageKind.ATTEMPT_DECLARATION,
                None,
            ),
            (
                self.authorization,
                self.authorization_envelope,
                self.authorization_identity,
                _D7PrefixStageKind.LAUNCH_AUTHORIZATION,
                self.declaration_envelope.canonical_sha256,
            ),
            (
                self.claim,
                self.claim_envelope,
                self.claim_identity,
                _D7PrefixStageKind.ATTEMPT_CLAIM,
                self.authorization_envelope.canonical_sha256,
            ),
            (
                self.start,
                self.start_envelope,
                self.start_identity,
                _D7PrefixStageKind.EXECUTION_START,
                self.claim_envelope.canonical_sha256,
            ),
        )
        for value, envelope, identity, stage_kind, previous in stages:
            if (
                envelope.embedded_record != value
                or envelope.stage_kind is not stage_kind
                or envelope.store_scope_sha256 != self.store_scope.canonical_sha256
                or envelope.previous_envelope_sha256 != previous
                or envelope.store_root_realpath != self.store_scope.store_root_realpath
                or (envelope.store_device, envelope.store_inode)
                != (
                    self.store_scope.store_device,
                    self.store_scope.store_inode,
                )
                or envelope.lane_realpath != self.store_scope.lane_realpath
                or (envelope.lane_device, envelope.lane_inode)
                != (
                    self.store_scope.lane_device,
                    self.store_scope.lane_inode,
                )
                or envelope.canonical_sha256 != identity.canonical_sha256
                or len(envelope.canonical_bytes) != identity.byte_count
                or identity.path
                != (
                    self.store_root
                    / _PREFIX_LANE_DIRECTORY_LEAF
                    / _attempt_leaf(
                        self.declaration.attempt_key_sha256,
                        _stage_suffix(stage_kind),
                    )
                )
                or envelope.authority_granted is not False
                or envelope.authoritative_lifecycle_eligible is not False
                or envelope.execution_capability_issued is not False
                or envelope.terminal_finalization_capability_issued is not False
            ):
                raise QualificationContractError(
                    "loaded D7 evidence envelope chain differs from its identity"
                )


@dataclass(frozen=True, slots=True)
class D7EvidenceOnlyPrefixInspection:
    """Fail-closed terminal-entry inspection for one evidence-only prefix."""

    state: D7EvidenceOnlyPrefixState
    terminal_path: Path
    retry_authorized: bool = False
    replay_authorized: bool = False
    d8_eligible: bool = False
    elapsed_time_used: bool = False
    process_absence_used: bool = False
    caller_assertion_used: bool = False
    terminal_validated: bool = False
    external_abort_finalized: bool = False
    execution_observed: bool = False
    started_unresolved_established: bool = False

    def __post_init__(self) -> None:
        if type(self.state) is not D7EvidenceOnlyPrefixState:
            raise TypeError("state must be an exact D7EvidenceOnlyPrefixState")
        if (
            not isinstance(self.terminal_path, Path)
            or not self.terminal_path.is_absolute()
        ):
            raise TypeError("terminal_path must be an absolute Path")
        for name in (
            "retry_authorized",
            "replay_authorized",
            "d8_eligible",
            "elapsed_time_used",
            "process_absence_used",
            "caller_assertion_used",
            "terminal_validated",
            "external_abort_finalized",
            "execution_observed",
            "started_unresolved_established",
        ):
            if getattr(self, name) is not False:
                raise QualificationContractError(
                    f"persistence-only inspection requires {name}=false"
                )


@dataclass(frozen=True, slots=True)
class _DirectoryAnchor:
    path: Path
    descriptor: int
    device: int
    inode: int


def _sha256(value: object, label: str) -> str:
    if type(value) is not str or _SHA256_RE.fullmatch(value) is None:
        raise QualificationContractError(f"{label} must be a lowercase SHA-256")
    return value


def _nonempty_string(value: object, label: str) -> str:
    if type(value) is not str or not value or value != value.strip():
        raise QualificationContractError(f"{label} must be a non-empty string")
    return value


def _absolute_path_string(value: object, label: str) -> str:
    result = _nonempty_string(value, label)
    if not Path(result).is_absolute():
        raise QualificationContractError(f"{label} must be an absolute path")
    return result


def _nonnegative_int(value: object, label: str) -> int:
    if type(value) is not int or value < 0:
        raise QualificationContractError(f"{label} must be a nonnegative plain integer")
    return value


def _stage_record_type(stage_kind: _D7PrefixStageKind) -> type[object]:
    if stage_kind is _D7PrefixStageKind.ATTEMPT_DECLARATION:
        return r.D7AttemptDeclarationRecord
    if stage_kind is _D7PrefixStageKind.LAUNCH_AUTHORIZATION:
        return r.D7LaunchAuthorizationRecord
    if stage_kind is _D7PrefixStageKind.ATTEMPT_CLAIM:
        return r.D7AttemptClaimRecord
    if stage_kind is _D7PrefixStageKind.EXECUTION_START:
        return r.D7ExecutionStartRecord
    raise TypeError("stage_kind must be an exact _D7PrefixStageKind")


def _directory_flags() -> int:
    flags = os.O_RDONLY
    flags |= getattr(os, "O_DIRECTORY", 0)
    flags |= getattr(os, "O_CLOEXEC", 0)
    no_follow_any = getattr(os, "O_NOFOLLOW_ANY", 0)
    flags |= no_follow_any or getattr(os, "O_NOFOLLOW", 0)
    return flags


def _file_read_flags() -> int:
    # O_NONBLOCK is inert for regular files and prevents a hostile FIFO from
    # blocking before the descriptor-level regular-file check can reject it.
    flags = os.O_RDONLY | getattr(os, "O_NONBLOCK", 0)
    for name in ("O_NOFOLLOW", "O_CLOEXEC"):
        flags |= getattr(os, name, 0)
    return flags


def _file_create_flags() -> int:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    for name in ("O_NOFOLLOW", "O_CLOEXEC"):
        flags |= getattr(os, name, 0)
    return flags


def _identity(value: os.stat_result) -> tuple[int, int]:
    return value.st_dev, value.st_ino


def _stable_file_identity(value: os.stat_result) -> tuple[int, ...]:
    return (
        value.st_dev,
        value.st_ino,
        value.st_mode,
        value.st_nlink,
        value.st_size,
        value.st_mtime_ns,
        value.st_ctime_ns,
    )


def _absolute(path: str | Path) -> Path:
    return Path(os.path.abspath(Path(path)))


def _open_real_directory(path: str | Path, *, label: str) -> _DirectoryAnchor:
    display = _absolute(path)
    if Path(os.path.realpath(display)) != display:
        raise QualificationContractError(
            f"{label} must contain no symbolic-link or alias component: {display}"
        )
    try:
        descriptor = os.open(display, _directory_flags())
    except OSError as error:
        raise QualificationContractError(f"cannot open {label}: {error}") from error
    try:
        opened = os.fstat(descriptor)
        displayed = os.stat(display, follow_symlinks=False)
        if (
            not stat.S_ISDIR(opened.st_mode)
            or not stat.S_ISDIR(displayed.st_mode)
            or _identity(opened) != _identity(displayed)
        ):
            raise QualificationContractError(
                f"{label} is not one stable real directory"
            )
        return _DirectoryAnchor(
            path=display,
            descriptor=descriptor,
            device=opened.st_dev,
            inode=opened.st_ino,
        )
    except BaseException:
        os.close(descriptor)
        raise


def _verify_anchor(anchor: _DirectoryAnchor, *, label: str) -> None:
    opened = os.fstat(anchor.descriptor)
    try:
        displayed = os.stat(anchor.path, follow_symlinks=False)
    except OSError as error:
        raise QualificationContractError(f"cannot restat {label}: {error}") from error
    if (
        not stat.S_ISDIR(opened.st_mode)
        or not stat.S_ISDIR(displayed.st_mode)
        or _identity(opened) != (anchor.device, anchor.inode)
        or _identity(displayed) != (anchor.device, anchor.inode)
        or Path(os.path.realpath(anchor.path)) != anchor.path
    ):
        raise QualificationContractError(f"{label} directory identity changed")


def _relative_stat(anchor: _DirectoryAnchor, leaf: str) -> os.stat_result | None:
    try:
        return os.stat(
            leaf,
            dir_fd=anchor.descriptor,
            follow_symlinks=False,
        )
    except FileNotFoundError:
        return None
    except OSError as error:
        raise QualificationContractError(
            f"cannot inspect {anchor.path / leaf}: {error}"
        ) from error


def _require_absent(anchor: _DirectoryAnchor, leaf: str, *, label: str) -> None:
    if _relative_stat(anchor, leaf) is not None:
        raise QualificationContractError(
            f"refusing to replace existing {label}: {anchor.path / leaf}"
        )


def _reject_unpublished_staging_entries(
    anchor: _DirectoryAnchor,
    *,
    label: str,
) -> None:
    try:
        names = os.listdir(anchor.descriptor)
    except OSError as error:
        raise QualificationContractError(
            f"cannot enumerate {label}: {error}"
        ) from error
    staged = sorted(name for name in names if name.endswith(_TEMPORARY_SUFFIX))
    if staged:
        raise QualificationContractError(
            f"{label} contains unpublished staging entries; "
            "wait for active writers to quiesce and, only after orphanhood is "
            "established, perform offline recovery before retry or reload"
        )


def _open_child_directory(
    store: _DirectoryAnchor,
    *,
    leaf: str,
    label: str,
    create: bool,
) -> _DirectoryAnchor:
    if create:
        try:
            os.mkdir(leaf, 0o700, dir_fd=store.descriptor)
        except FileExistsError:
            pass
        except OSError as error:
            raise QualificationContractError(
                f"cannot create {label}: {error}"
            ) from error
        try:
            os.fsync(store.descriptor)
        except OSError as error:
            raise QualificationContractError(
                f"{label} creation durability is unproved"
            ) from error
    try:
        descriptor = os.open(
            leaf,
            _directory_flags(),
            dir_fd=store.descriptor,
        )
    except OSError as error:
        raise QualificationContractError(f"cannot open {label}: {error}") from error
    try:
        opened = os.fstat(descriptor)
        displayed = _relative_stat(store, leaf)
        if (
            displayed is None
            or not stat.S_ISDIR(opened.st_mode)
            or not stat.S_ISDIR(displayed.st_mode)
            or _identity(opened) != _identity(displayed)
        ):
            raise QualificationContractError(
                f"{label} path is not one stable real directory"
            )
        anchor = _DirectoryAnchor(
            path=store.path / leaf,
            descriptor=descriptor,
            device=opened.st_dev,
            inode=opened.st_ino,
        )
        _reject_unpublished_staging_entries(anchor, label=label)
        return anchor
    except BaseException:
        os.close(descriptor)
        raise


def _open_evidence_directory(
    store: _DirectoryAnchor,
    *,
    create: bool,
) -> _DirectoryAnchor:
    return _open_child_directory(
        store,
        leaf=_EVIDENCE_DIRECTORY_LEAF,
        label="D7 absence-receipt directory",
        create=create,
    )


def _open_prefix_lane(
    store: _DirectoryAnchor,
    *,
    create: bool,
) -> _DirectoryAnchor:
    return _open_child_directory(
        store,
        leaf=_PREFIX_LANE_DIRECTORY_LEAF,
        label="D7 evidence-only prefix lane",
        create=create,
    )


def _attempt_leaf(attempt_key_sha256: str, suffix: str) -> str:
    return f"{_sha256(attempt_key_sha256, 'attempt_key_sha256')}{suffix}"


def _declaration_leaf(attempt_key_sha256: str) -> str:
    return _attempt_leaf(attempt_key_sha256, _ATTEMPT_DECLARATION_SUFFIX)


def _authorization_leaf(attempt_key_sha256: str) -> str:
    return _attempt_leaf(attempt_key_sha256, _LAUNCH_AUTHORIZATION_SUFFIX)


def _claim_leaf(attempt_key_sha256: str) -> str:
    return _attempt_leaf(attempt_key_sha256, _ATTEMPT_CLAIM_SUFFIX)


def _start_leaf(attempt_key_sha256: str) -> str:
    return _attempt_leaf(attempt_key_sha256, _EXECUTION_START_SUFFIX)


def _stage_suffix(stage_kind: _D7PrefixStageKind) -> str:
    if stage_kind is _D7PrefixStageKind.ATTEMPT_DECLARATION:
        return _ATTEMPT_DECLARATION_SUFFIX
    if stage_kind is _D7PrefixStageKind.LAUNCH_AUTHORIZATION:
        return _LAUNCH_AUTHORIZATION_SUFFIX
    if stage_kind is _D7PrefixStageKind.ATTEMPT_CLAIM:
        return _ATTEMPT_CLAIM_SUFFIX
    if stage_kind is _D7PrefixStageKind.EXECUTION_START:
        return _EXECUTION_START_SUFFIX
    raise TypeError("stage_kind must be an exact _D7PrefixStageKind")


def _receipt_leaf(canonical_sha256: str) -> str:
    return f"{_sha256(canonical_sha256, 'receipt canonical_sha256')}.json"


def _write_all(descriptor: int, payload: bytes) -> None:
    remaining = memoryview(payload)
    while remaining:
        written = os.write(descriptor, remaining)
        if written <= 0:
            raise OSError(errno.EIO, "short write while persisting D7 bytes")
        remaining = remaining[written:]


def _cleanup_temporary(
    anchor: _DirectoryAnchor,
    leaf: str,
    *,
    expected_identity: tuple[int, int],
) -> bool:
    observed = _relative_stat(anchor, leaf)
    if observed is None:
        return True
    if _identity(observed) != expected_identity or not stat.S_ISREG(observed.st_mode):
        return False
    try:
        os.unlink(leaf, dir_fd=anchor.descriptor)
    except OSError:
        return False
    return True


def _rename_file_no_replace(
    anchor: _DirectoryAnchor,
    source_leaf: str,
    destination_leaf: str,
) -> None:
    """Atomically rename one descriptor-relative leaf without replacement."""

    library = ctypes.CDLL(None, use_errno=True)
    if sys.platform == "darwin":
        function_name = "renameatx_np"
        flags = (
            _DARWIN_RENAME_EXCL
            | _DARWIN_RENAME_NOFOLLOW_ANY
            | _DARWIN_RENAME_RESOLVE_BENEATH
        )
    elif sys.platform.startswith("linux"):
        function_name = "renameat2"
        flags = _LINUX_RENAME_NOREPLACE
    else:
        raise OSError(
            errno.ENOSYS,
            f"native exclusive rename is unsupported on {sys.platform}",
        )
    try:
        rename = getattr(library, function_name)
    except AttributeError as error:
        raise OSError(
            errno.ENOSYS,
            f"{function_name} is unavailable on {sys.platform}",
        ) from error
    rename.argtypes = (
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_uint,
    )
    rename.restype = ctypes.c_int
    ctypes.set_errno(0)
    result = rename(
        anchor.descriptor,
        os.fsencode(source_leaf),
        anchor.descriptor,
        os.fsencode(destination_leaf),
        flags,
    )
    if result == 0:
        return
    observed_errno = ctypes.get_errno() or errno.EIO
    raise OSError(
        observed_errno,
        os.strerror(observed_errno),
        f"{source_leaf} -> {destination_leaf}",
    )


def _read_bounded_file(
    anchor: _DirectoryAnchor,
    leaf: str,
    *,
    maximum_bytes: int,
    label: str,
) -> tuple[bytes, os.stat_result]:
    try:
        descriptor = os.open(leaf, _file_read_flags(), dir_fd=anchor.descriptor)
    except OSError as error:
        raise QualificationContractError(f"cannot open {label}: {error}") from error
    try:
        before = os.fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_nlink != 1
            or before.st_size <= 0
            or before.st_size > maximum_bytes
        ):
            raise QualificationContractError(
                f"{label} is not one bounded unaliased regular file"
            )
        chunks: list[bytes] = []
        remaining = maximum_bytes + 1
        while remaining:
            chunk = os.read(descriptor, min(128 * 1024, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        source = b"".join(chunks)
        after = os.fstat(descriptor)
        if (
            _stable_file_identity(before) != _stable_file_identity(after)
            or len(source) != after.st_size
            or not source
            or len(source) > maximum_bytes
        ):
            raise QualificationContractError(
                f"{label} changed during bounded descriptor read"
            )
        display = _relative_stat(anchor, leaf)
        if (
            display is None
            or _identity(display) != _identity(after)
            or not stat.S_ISREG(display.st_mode)
        ):
            raise QualificationContractError(f"{label} display identity changed")
        return source, after
    finally:
        os.close(descriptor)


def _read_exact_file(
    anchor: _DirectoryAnchor,
    leaf: str,
    *,
    expected_sha256: str,
    maximum_bytes: int,
    label: str,
) -> tuple[bytes, os.stat_result]:
    expected = _sha256(expected_sha256, f"{label} expected_sha256")
    source, observed = _read_bounded_file(
        anchor,
        leaf,
        maximum_bytes=maximum_bytes,
        label=label,
    )
    if hashlib.sha256(source).hexdigest() != expected:
        raise QualificationContractError(f"{label} source SHA-256 differs before parse")
    return source, observed


def _identity_from_stat(
    *,
    path: Path,
    canonical_sha256: str,
    source: bytes,
    observed: os.stat_result,
    created_by_call: bool,
    parent_directory_fsync_proved: bool,
) -> D7PersistedRecordIdentity:
    return D7PersistedRecordIdentity(
        path=path,
        canonical_sha256=canonical_sha256,
        byte_count=len(source),
        device=observed.st_dev,
        inode=observed.st_ino,
        parent_directory_fsync_proved=parent_directory_fsync_proved,
        created_by_call=created_by_call,
    )


def _write_canonical_file_no_replace(
    anchor: _DirectoryAnchor,
    leaf: str,
    payload: bytes,
    *,
    expected_sha256: str,
    maximum_bytes: int,
    label: str,
    allow_identical_existing: bool,
) -> D7PersistedRecordIdentity:
    expected = _sha256(expected_sha256, f"{label} expected_sha256")
    if (
        type(payload) is not bytes
        or not payload
        or len(payload) > maximum_bytes
        or hashlib.sha256(payload).hexdigest() != expected
    ):
        raise QualificationContractError(
            f"{label} payload differs from its bounded canonical identity"
        )
    _verify_anchor(anchor, label=f"{label} parent")
    existing = _relative_stat(anchor, leaf)
    if existing is not None:
        if not allow_identical_existing:
            raise QualificationContractError(
                f"refusing to overwrite existing {label}: {anchor.path / leaf}"
            )
        source, observed = _read_exact_file(
            anchor,
            leaf,
            expected_sha256=expected,
            maximum_bytes=maximum_bytes,
            label=label,
        )
        if source != payload:
            raise QualificationContractError(f"content-addressed {label} bytes differ")
        try:
            os.fsync(anchor.descriptor)
        except OSError as error:
            raise QualificationContractError(
                f"existing {label} parent durability is unproved"
            ) from error
        return _identity_from_stat(
            path=anchor.path / leaf,
            canonical_sha256=expected,
            source=source,
            observed=observed,
            created_by_call=False,
            parent_directory_fsync_proved=True,
        )

    temporary_leaf = f".{leaf}.{secrets.token_hex(12)}{_TEMPORARY_SUFFIX}"
    descriptor: int | None = None
    temporary_identity: tuple[int, int] | None = None
    existing_winner: tuple[bytes, os.stat_result] | None = None
    published = False
    directory_fsync_proved = False
    try:
        descriptor = os.open(
            temporary_leaf,
            _file_create_flags(),
            0o600,
            dir_fd=anchor.descriptor,
        )
        opened_stat = os.fstat(descriptor)
        temporary_identity = _identity(opened_stat)
        if not stat.S_ISREG(opened_stat.st_mode) or opened_stat.st_nlink != 1:
            raise QualificationContractError(
                f"{label} temporary file identity is invalid"
            )
        _write_all(descriptor, payload)
        os.fsync(descriptor)
        temporary_stat = os.fstat(descriptor)
        if (
            _identity(temporary_stat) != temporary_identity
            or not stat.S_ISREG(temporary_stat.st_mode)
            or temporary_stat.st_nlink != 1
            or temporary_stat.st_size != len(payload)
        ):
            raise QualificationContractError(
                f"{label} temporary file identity is invalid"
            )
        os.close(descriptor)
        descriptor = None
        try:
            _rename_file_no_replace(
                anchor,
                temporary_leaf,
                leaf,
            )
            published = True
        except OSError as error:
            winner = _relative_stat(anchor, leaf)
            staged = _relative_stat(anchor, temporary_leaf)
            if (
                winner is not None
                and temporary_identity is not None
                and _identity(winner) == temporary_identity
                and staged is None
                and stat.S_ISREG(winner.st_mode)
                and winner.st_nlink == 1
            ):
                published = True
            elif error.errno in (errno.EEXIST, errno.ENOTEMPTY):
                if not allow_identical_existing:
                    raise QualificationContractError(
                        f"refusing to overwrite existing {label}: {anchor.path / leaf}"
                    ) from error
                winner_source, winner_observed = _read_exact_file(
                    anchor,
                    leaf,
                    expected_sha256=expected,
                    maximum_bytes=maximum_bytes,
                    label=label,
                )
                if winner_source != payload:
                    raise QualificationContractError(
                        f"content-addressed {label} bytes differ"
                    ) from error
                existing_winner = (winner_source, winner_observed)
            else:
                raise QualificationContractError(
                    f"cannot atomically publish {label}: {error}"
                ) from error
        try:
            os.fsync(anchor.descriptor)
            directory_fsync_proved = True
        except OSError:
            directory_fsync_proved = False
    finally:
        if descriptor is not None:
            os.close(descriptor)
        if temporary_identity is not None:
            cleaned = _cleanup_temporary(
                anchor,
                temporary_leaf,
                expected_identity=temporary_identity,
            )
            if not cleaned:
                raise QualificationContractError(
                    f"{label} temporary cleanup is unproved"
                )
            if not published:
                try:
                    os.fsync(anchor.descriptor)
                    directory_fsync_proved = True
                except OSError as error:
                    raise QualificationContractError(
                        f"{label} temporary cleanup durability is unproved"
                    ) from error
                if _relative_stat(anchor, temporary_leaf) is not None:
                    raise QualificationContractError(
                        f"{label} temporary cleanup is unproved"
                    )

    if existing_winner is not None:
        winner_source, winner_observed = existing_winner
        return _identity_from_stat(
            path=anchor.path / leaf,
            canonical_sha256=expected,
            source=winner_source,
            observed=winner_observed,
            created_by_call=False,
            parent_directory_fsync_proved=directory_fsync_proved,
        )

    if not published:
        raise QualificationContractError(f"{label} was not published")
    source, observed = _read_exact_file(
        anchor,
        leaf,
        expected_sha256=expected,
        maximum_bytes=maximum_bytes,
        label=label,
    )
    if source != payload:
        raise QualificationContractError(
            f"published {label} differs from staged canonical bytes"
        )
    return _identity_from_stat(
        path=anchor.path / leaf,
        canonical_sha256=expected,
        source=source,
        observed=observed,
        created_by_call=True,
        parent_directory_fsync_proved=directory_fsync_proved,
    )


def _load_typed(
    anchor: _DirectoryAnchor,
    leaf: str,
    *,
    expected_sha256: str,
    maximum_bytes: int,
    label: str,
    record_type: type[object],
) -> tuple[object, D7PersistedRecordIdentity]:
    source, observed = _read_exact_file(
        anchor,
        leaf,
        expected_sha256=expected_sha256,
        maximum_bytes=maximum_bytes,
        label=label,
    )
    loader = getattr(record_type, "from_canonical_bytes", None)
    if not callable(loader):
        raise TypeError(f"{label} record type has no canonical loader")
    value = loader(source, expected_sha256=expected_sha256)
    if type(value) is not record_type:
        raise TypeError(f"{label} loader returned the wrong exact type")
    _verify_anchor(anchor, label=f"{label} parent")
    try:
        os.fsync(anchor.descriptor)
    except OSError as error:
        raise QualificationContractError(
            f"{label} parent-directory durability cannot be established"
        ) from error
    return value, _identity_from_stat(
        path=anchor.path / leaf,
        canonical_sha256=expected_sha256,
        source=source,
        observed=observed,
        created_by_call=False,
        parent_directory_fsync_proved=True,
    )


def _make_store_scope(
    store: _DirectoryAnchor,
    lane: _DirectoryAnchor,
    *,
    declared_store_identity_sha256: str,
) -> _D7PrefixStoreScope:
    return _D7PrefixStoreScope(
        store_root_realpath=str(store.path),
        store_device=store.device,
        store_inode=store.inode,
        lane_realpath=str(lane.path),
        lane_device=lane.device,
        lane_inode=lane.inode,
        declared_store_identity_sha256=_sha256(
            declared_store_identity_sha256,
            "declared_store_identity_sha256",
        ),
    )


def _write_store_scope(
    store: _DirectoryAnchor,
    lane: _DirectoryAnchor,
    *,
    declared_store_identity_sha256: str,
) -> tuple[_D7PrefixStoreScope, D7PersistedRecordIdentity]:
    scope = _make_store_scope(
        store,
        lane,
        declared_store_identity_sha256=declared_store_identity_sha256,
    )
    identity = _write_canonical_file_no_replace(
        lane,
        _PREFIX_SCOPE_LEAF,
        scope.canonical_bytes,
        expected_sha256=scope.canonical_sha256,
        maximum_bytes=r.MAX_D7_CHRONOLOGY_RECORD_BYTES,
        label="D7 evidence-only prefix store scope",
        allow_identical_existing=True,
    )
    _require_durable(identity, label="D7 evidence-only prefix store scope")
    return scope, identity


def _load_store_scope(
    store: _DirectoryAnchor,
    lane: _DirectoryAnchor,
    *,
    expected_declared_store_identity_sha256: str,
) -> tuple[_D7PrefixStoreScope, D7PersistedRecordIdentity]:
    expected = _make_store_scope(
        store,
        lane,
        declared_store_identity_sha256=expected_declared_store_identity_sha256,
    )
    value, identity = _load_typed(
        lane,
        _PREFIX_SCOPE_LEAF,
        expected_sha256=expected.canonical_sha256,
        maximum_bytes=r.MAX_D7_CHRONOLOGY_RECORD_BYTES,
        label="D7 evidence-only prefix store scope",
        record_type=_D7PrefixStoreScope,
    )
    if type(value) is not _D7PrefixStoreScope or value != expected:
        raise QualificationContractError(
            "D7 evidence-only prefix store scope differs from this store"
        )
    return value, identity


def _make_stage_envelope(
    store: _DirectoryAnchor,
    lane: _DirectoryAnchor,
    *,
    scope: _D7PrefixStoreScope,
    stage_kind: _D7PrefixStageKind,
    record: object,
    previous_envelope_sha256: str | None,
) -> _D7PrefixPersistenceEnvelope:
    return _D7PrefixPersistenceEnvelope(
        stage_kind=stage_kind,
        attempt_key_sha256=record.attempt_key_sha256,
        store_scope_sha256=scope.canonical_sha256,
        previous_envelope_sha256=previous_envelope_sha256,
        embedded_record_schema_version=record.schema_version,
        embedded_record_sha256=record.canonical_sha256,
        embedded_record_byte_count=len(record.canonical_bytes),
        embedded_record=record,
        store_root_realpath=str(store.path),
        store_device=store.device,
        store_inode=store.inode,
        lane_realpath=str(lane.path),
        lane_device=lane.device,
        lane_inode=lane.inode,
    )


def _write_stage_envelope(
    store: _DirectoryAnchor,
    lane: _DirectoryAnchor,
    *,
    scope: _D7PrefixStoreScope,
    stage_kind: _D7PrefixStageKind,
    record: object,
    previous_envelope_sha256: str | None,
) -> tuple[_D7PrefixPersistenceEnvelope, D7PersistedRecordIdentity]:
    envelope = _make_stage_envelope(
        store,
        lane,
        scope=scope,
        stage_kind=stage_kind,
        record=record,
        previous_envelope_sha256=previous_envelope_sha256,
    )
    identity = _write_canonical_file_no_replace(
        lane,
        _attempt_leaf(record.attempt_key_sha256, _stage_suffix(stage_kind)),
        envelope.canonical_bytes,
        expected_sha256=envelope.canonical_sha256,
        maximum_bytes=_MAX_PREFIX_ENVELOPE_BYTES,
        label=f"D7 evidence-only {stage_kind.value} envelope",
        allow_identical_existing=False,
    )
    return envelope, identity


def _load_stage_envelope(
    store: _DirectoryAnchor,
    lane: _DirectoryAnchor,
    *,
    scope: _D7PrefixStoreScope,
    attempt_key_sha256: str,
    stage_kind: _D7PrefixStageKind,
    expected_envelope_sha256: str,
    expected_record_sha256: str,
    expected_previous_envelope_sha256: str | None,
) -> tuple[object, _D7PrefixPersistenceEnvelope, D7PersistedRecordIdentity]:
    expected_envelope = _sha256(
        expected_envelope_sha256,
        f"{stage_kind.value} expected_envelope_sha256",
    )
    source, observed = _read_exact_file(
        lane,
        _attempt_leaf(attempt_key_sha256, _stage_suffix(stage_kind)),
        expected_sha256=expected_envelope,
        maximum_bytes=_MAX_PREFIX_ENVELOPE_BYTES,
        label=f"D7 evidence-only {stage_kind.value} envelope",
    )
    envelope = _D7PrefixPersistenceEnvelope.from_canonical_bytes(
        source,
        expected_sha256=expected_envelope,
    )
    if (
        envelope.stage_kind is not stage_kind
        or envelope.attempt_key_sha256 != attempt_key_sha256
        or envelope.store_scope_sha256 != scope.canonical_sha256
        or envelope.previous_envelope_sha256 != expected_previous_envelope_sha256
        or envelope.embedded_record_sha256
        != _sha256(
            expected_record_sha256,
            f"{stage_kind.value} expected_record_sha256",
        )
        or envelope.store_root_realpath != str(store.path)
        or (envelope.store_device, envelope.store_inode) != (store.device, store.inode)
        or envelope.lane_realpath != str(lane.path)
        or (envelope.lane_device, envelope.lane_inode) != (lane.device, lane.inode)
    ):
        raise QualificationContractError(
            f"D7 evidence-only {stage_kind.value} envelope binding differs"
        )
    _verify_anchor(store, label="D7 attempt store")
    _verify_anchor(lane, label="D7 evidence-only prefix lane")
    try:
        os.fsync(lane.descriptor)
    except OSError as error:
        raise QualificationContractError(
            f"D7 evidence-only {stage_kind.value} parent durability is unproved"
        ) from error
    return (
        envelope.embedded_record,
        envelope,
        _identity_from_stat(
            path=lane.path
            / _attempt_leaf(attempt_key_sha256, _stage_suffix(stage_kind)),
            canonical_sha256=expected_envelope,
            source=source,
            observed=observed,
            created_by_call=False,
            parent_directory_fsync_proved=True,
        ),
    )


def _reserved_paths(store_root: Path, attempt_key_sha256: str) -> tuple[Path, ...]:
    return (
        store_root / _PREFIX_LANE_DIRECTORY_LEAF,
        store_root / _EVIDENCE_DIRECTORY_LEAF,
        store_root / _declaration_leaf(attempt_key_sha256),
        store_root / _authorization_leaf(attempt_key_sha256),
        store_root / _claim_leaf(attempt_key_sha256),
        store_root / _start_leaf(attempt_key_sha256),
    )


def _paths_overlap(left: Path, right: Path) -> bool:
    left_parts = PurePosixPath(left).parts
    right_parts = PurePosixPath(right).parts
    return (
        left_parts == right_parts
        or left_parts == right_parts[: len(left_parts)]
        or right_parts == left_parts[: len(right_parts)]
    )


def _reject_reserved_subjects(
    store_root: Path,
    attempt_key_sha256: str,
    *receipts: e.D7AuthorizationPathAbsenceReceipt | e.D7PreStartPathAbsenceReceipt,
) -> None:
    reserved = _reserved_paths(store_root, attempt_key_sha256)
    for receipt in receipts:
        subject = Path(receipt.subject_path)
        is_chronology_leaf = (
            subject.parent == store_root
            and _CHRONOLOGY_LEAF_RE.fullmatch(subject.name) is not None
        )
        if is_chronology_leaf or any(
            _paths_overlap(subject, path) for path in reserved
        ):
            raise QualificationContractError(
                "D7 output/terminal subject overlaps persistence-reserved paths"
            )


def _reobserve_absence(
    store_root: Path,
    receipt: e.D7AuthorizationPathAbsenceReceipt | e.D7PreStartPathAbsenceReceipt,
) -> None:
    if receipt.store_root_realpath != str(store_root):
        raise QualificationContractError(
            "path-absence receipt store root differs from persistence store"
        )
    parent = _open_real_directory(
        receipt.resolved_parent_realpath,
        label=f"{receipt.subject_kind.value} observed parent",
    )
    try:
        if (parent.device, parent.inode) != (
            receipt.parent_device,
            receipt.parent_inode,
        ):
            raise QualificationContractError(
                "path-absence receipt parent device/inode differs from observation"
            )
        if _relative_stat(parent, receipt.subject_basename) is not None:
            raise QualificationContractError(
                f"{receipt.subject_kind.value} is present at observation time"
            )
        _verify_anchor(parent, label=f"{receipt.subject_kind.value} observed parent")
    finally:
        os.close(parent.descriptor)


def _verify_receipt_location(
    store_root: Path,
    receipt: e.D7AuthorizationPathAbsenceReceipt | e.D7PreStartPathAbsenceReceipt,
) -> None:
    if receipt.store_root_realpath != str(store_root):
        raise QualificationContractError(
            "persisted path-absence receipt belongs to another store root"
        )
    parent = _open_real_directory(
        receipt.resolved_parent_realpath,
        label=f"{receipt.subject_kind.value} persisted parent",
    )
    try:
        if (parent.device, parent.inode) != (
            receipt.parent_device,
            receipt.parent_inode,
        ):
            raise QualificationContractError(
                "persisted path-absence receipt parent identity changed"
            )
        _verify_anchor(parent, label=f"{receipt.subject_kind.value} persisted parent")
    finally:
        os.close(parent.descriptor)


def _write_receipt(
    evidence: _DirectoryAnchor,
    receipt: e.D7AuthorizationPathAbsenceReceipt | e.D7PreStartPathAbsenceReceipt,
) -> D7PersistedRecordIdentity:
    return _write_canonical_file_no_replace(
        evidence,
        _receipt_leaf(receipt.canonical_sha256),
        receipt.canonical_bytes,
        expected_sha256=receipt.canonical_sha256,
        maximum_bytes=e.MAX_D7_ATTEMPT_EVIDENCE_BYTES,
        label=f"{receipt.subject_kind.value} absence receipt",
        allow_identical_existing=True,
    )


def _load_receipt(
    evidence: _DirectoryAnchor,
    *,
    expected_sha256: str,
    record_type: type[object],
    label: str,
) -> object:
    value, _identity_value = _load_typed(
        evidence,
        _receipt_leaf(expected_sha256),
        expected_sha256=expected_sha256,
        maximum_bytes=e.MAX_D7_ATTEMPT_EVIDENCE_BYTES,
        label=label,
        record_type=record_type,
    )
    return value


def _require_durable(identity: D7PersistedRecordIdentity, *, label: str) -> None:
    if identity.parent_directory_fsync_proved is not True:
        raise QualificationContractError(
            f"{label} is visible but parent-directory durability is unproved; "
            "do not republish or advance"
        )


def persist_d7_attempt_declaration_evidence_no_replace(
    store_directory: str | Path,
    declaration: r.D7AttemptDeclarationRecord,
) -> D7PersistedRecordIdentity:
    """Persist one caller-supplied primary declaration as evidence only."""

    if type(declaration) is not r.D7AttemptDeclarationRecord:
        raise TypeError("declaration must be an exact D7AttemptDeclarationRecord")
    if declaration.attempt_role is not r.D7AttemptRole.PRIMARY_CONFIRMATION:
        raise QualificationContractError(
            "evidence-only persistence cannot derive isolated-replay authority"
        )
    store = _open_real_directory(store_directory, label="D7 attempt store")
    lane: _DirectoryAnchor | None = None
    try:
        lane = _open_prefix_lane(store, create=True)
        key = declaration.attempt_key_sha256
        for leaf, label in (
            (_declaration_leaf(key), "D7 attempt declaration"),
            (_authorization_leaf(key), "D7 launch authorization"),
            (_claim_leaf(key), "D7 attempt claim"),
            (_start_leaf(key), "D7 execution start"),
        ):
            _require_absent(lane, leaf, label=label)
        scope, _scope_identity = _write_store_scope(
            store,
            lane,
            declared_store_identity_sha256=declaration.store_identity_sha256,
        )
        _envelope, identity = _write_stage_envelope(
            store,
            lane,
            scope=scope,
            stage_kind=_D7PrefixStageKind.ATTEMPT_DECLARATION,
            record=declaration,
            previous_envelope_sha256=None,
        )
        return identity
    finally:
        if lane is not None:
            os.close(lane.descriptor)
        os.close(store.descriptor)


def persist_d7_launch_authorization_evidence_no_replace(
    store_directory: str | Path,
    *,
    authorization: r.D7LaunchAuthorizationRecord,
    expected_declaration_envelope_sha256: str,
    output_namespace_receipt: e.D7AuthorizationPathAbsenceReceipt,
    terminal_path_receipt: e.D7AuthorizationPathAbsenceReceipt,
) -> D7PersistedRecordIdentity:
    """Persist a caller-supplied authorization record as non-authority evidence."""

    if type(authorization) is not r.D7LaunchAuthorizationRecord:
        raise TypeError("authorization must be an exact D7LaunchAuthorizationRecord")
    store = _open_real_directory(store_directory, label="D7 attempt store")
    lane: _DirectoryAnchor | None = None
    evidence: _DirectoryAnchor | None = None
    try:
        lane = _open_prefix_lane(store, create=False)
        key = authorization.attempt_key_sha256
        _require_absent(
            lane,
            _authorization_leaf(key),
            label="D7 launch authorization",
        )
        _require_absent(lane, _claim_leaf(key), label="D7 attempt claim")
        _require_absent(lane, _start_leaf(key), label="D7 execution start")
        scope, _scope_identity = _load_store_scope(
            store,
            lane,
            expected_declared_store_identity_sha256=(
                authorization.store_identity_sha256
            ),
        )
        (
            declaration_value,
            declaration_envelope,
            _declaration_identity,
        ) = _load_stage_envelope(
            store,
            lane,
            scope=scope,
            attempt_key_sha256=key,
            stage_kind=_D7PrefixStageKind.ATTEMPT_DECLARATION,
            expected_envelope_sha256=expected_declaration_envelope_sha256,
            expected_record_sha256=authorization.attempt_declaration_sha256,
            expected_previous_envelope_sha256=None,
        )
        declaration = declaration_value
        assert type(declaration) is r.D7AttemptDeclarationRecord
        if declaration.attempt_role is not r.D7AttemptRole.PRIMARY_CONFIRMATION:
            raise QualificationContractError(
                "evidence-only persistence cannot derive isolated-replay authority"
            )
        v.validate_d7_authorized_attempt(
            declaration=declaration,
            authorization=authorization,
        )
        ev.validate_d7_authorization_path_absence_receipts(
            declaration=declaration,
            authorization=authorization,
            output_namespace_receipt=output_namespace_receipt,
            terminal_path_receipt=terminal_path_receipt,
        )
        _reject_reserved_subjects(
            store.path,
            key,
            output_namespace_receipt,
            terminal_path_receipt,
        )
        _reobserve_absence(store.path, output_namespace_receipt)
        _reobserve_absence(store.path, terminal_path_receipt)
        evidence = _open_evidence_directory(store, create=True)
        _require_durable(
            _write_receipt(evidence, output_namespace_receipt),
            label="authorization output absence receipt",
        )
        _require_durable(
            _write_receipt(evidence, terminal_path_receipt),
            label="authorization terminal absence receipt",
        )
        _reobserve_absence(store.path, output_namespace_receipt)
        _reobserve_absence(store.path, terminal_path_receipt)
        _envelope, identity = _write_stage_envelope(
            store,
            lane,
            scope=scope,
            stage_kind=_D7PrefixStageKind.LAUNCH_AUTHORIZATION,
            record=authorization,
            previous_envelope_sha256=declaration_envelope.canonical_sha256,
        )
        return identity
    finally:
        if evidence is not None:
            os.close(evidence.descriptor)
        if lane is not None:
            os.close(lane.descriptor)
        os.close(store.descriptor)


def _load_authorized_evidence_prefix(
    store: _DirectoryAnchor,
    lane: _DirectoryAnchor,
    *,
    attempt_key_sha256: str,
    expected_store_identity_sha256: str,
    expected_declaration_sha256: str,
    expected_authorization_sha256: str,
    expected_declaration_envelope_sha256: str,
    expected_authorization_envelope_sha256: str,
) -> tuple[
    _D7PrefixStoreScope,
    r.D7AttemptDeclarationRecord,
    r.D7LaunchAuthorizationRecord,
    e.D7AuthorizationPathAbsenceReceipt,
    e.D7AuthorizationPathAbsenceReceipt,
    _D7PrefixPersistenceEnvelope,
    _D7PrefixPersistenceEnvelope,
    D7PersistedRecordIdentity,
    D7PersistedRecordIdentity,
    D7PersistedRecordIdentity,
]:
    scope, scope_identity = _load_store_scope(
        store,
        lane,
        expected_declared_store_identity_sha256=expected_store_identity_sha256,
    )
    (
        declaration_value,
        declaration_envelope,
        declaration_identity,
    ) = _load_stage_envelope(
        store,
        lane,
        scope=scope,
        attempt_key_sha256=attempt_key_sha256,
        stage_kind=_D7PrefixStageKind.ATTEMPT_DECLARATION,
        expected_envelope_sha256=expected_declaration_envelope_sha256,
        expected_record_sha256=expected_declaration_sha256,
        expected_previous_envelope_sha256=None,
    )
    (
        authorization_value,
        authorization_envelope,
        authorization_identity,
    ) = _load_stage_envelope(
        store,
        lane,
        scope=scope,
        attempt_key_sha256=attempt_key_sha256,
        stage_kind=_D7PrefixStageKind.LAUNCH_AUTHORIZATION,
        expected_envelope_sha256=expected_authorization_envelope_sha256,
        expected_record_sha256=expected_authorization_sha256,
        expected_previous_envelope_sha256=(declaration_envelope.canonical_sha256),
    )
    declaration = declaration_value
    authorization = authorization_value
    assert type(declaration) is r.D7AttemptDeclarationRecord
    assert type(authorization) is r.D7LaunchAuthorizationRecord
    if (
        declaration.attempt_role is not r.D7AttemptRole.PRIMARY_CONFIRMATION
        or declaration.store_identity_sha256 != expected_store_identity_sha256
        or authorization.store_identity_sha256 != expected_store_identity_sha256
        or declaration.attempt_key_sha256 != attempt_key_sha256
        or authorization.attempt_key_sha256 != attempt_key_sha256
    ):
        raise QualificationContractError(
            "persisted D7 attempt key differs from its canonical paths"
        )
    v.validate_d7_authorized_attempt(
        declaration=declaration,
        authorization=authorization,
    )
    evidence = _open_evidence_directory(store, create=False)
    try:
        output = _load_receipt(
            evidence,
            expected_sha256=(
                authorization.authorization_output_namespace_absence_receipt_sha256
            ),
            record_type=e.D7AuthorizationPathAbsenceReceipt,
            label="authorization output absence receipt",
        )
        terminal = _load_receipt(
            evidence,
            expected_sha256=(
                authorization.authorization_terminal_path_absence_receipt_sha256
            ),
            record_type=e.D7AuthorizationPathAbsenceReceipt,
            label="authorization terminal absence receipt",
        )
    finally:
        os.close(evidence.descriptor)
    assert type(output) is e.D7AuthorizationPathAbsenceReceipt
    assert type(terminal) is e.D7AuthorizationPathAbsenceReceipt
    ev.validate_d7_authorization_path_absence_receipts(
        declaration=declaration,
        authorization=authorization,
        output_namespace_receipt=output,
        terminal_path_receipt=terminal,
    )
    _reject_reserved_subjects(
        store.path,
        attempt_key_sha256,
        output,
        terminal,
    )
    _verify_receipt_location(store.path, output)
    _verify_receipt_location(store.path, terminal)
    return (
        scope,
        declaration,
        authorization,
        output,
        terminal,
        declaration_envelope,
        authorization_envelope,
        scope_identity,
        declaration_identity,
        authorization_identity,
    )


def persist_d7_attempt_claim_evidence_no_replace(
    store_directory: str | Path,
    *,
    claim: r.D7AttemptClaimRecord,
    expected_declaration_envelope_sha256: str,
    expected_authorization_envelope_sha256: str,
) -> D7PersistedRecordIdentity:
    """Persist a caller-supplied claim record without acquiring a claim."""

    if type(claim) is not r.D7AttemptClaimRecord:
        raise TypeError("claim must be an exact D7AttemptClaimRecord")
    store = _open_real_directory(store_directory, label="D7 attempt store")
    lane: _DirectoryAnchor | None = None
    try:
        lane = _open_prefix_lane(store, create=False)
        key = claim.attempt_key_sha256
        _require_absent(lane, _claim_leaf(key), label="D7 attempt claim")
        _require_absent(lane, _start_leaf(key), label="D7 execution start")
        (
            scope,
            declaration,
            authorization,
            _authorization_output,
            _authorization_terminal,
            _declaration_envelope,
            authorization_envelope,
            _scope_identity,
            _declaration_identity,
            _authorization_identity,
        ) = _load_authorized_evidence_prefix(
            store,
            lane,
            attempt_key_sha256=key,
            expected_store_identity_sha256=claim.store_identity_sha256,
            expected_declaration_sha256=claim.attempt_declaration_sha256,
            expected_authorization_sha256=claim.launch_authorization_sha256,
            expected_declaration_envelope_sha256=(expected_declaration_envelope_sha256),
            expected_authorization_envelope_sha256=(
                expected_authorization_envelope_sha256
            ),
        )
        v.validate_d7_claimed_attempt(
            declaration=declaration,
            authorization=authorization,
            claim=claim,
        )
        _envelope, identity = _write_stage_envelope(
            store,
            lane,
            scope=scope,
            stage_kind=_D7PrefixStageKind.ATTEMPT_CLAIM,
            record=claim,
            previous_envelope_sha256=authorization_envelope.canonical_sha256,
        )
        return identity
    finally:
        if lane is not None:
            os.close(lane.descriptor)
        os.close(store.descriptor)


def persist_d7_execution_start_evidence_no_replace(
    store_directory: str | Path,
    *,
    start: r.D7ExecutionStartRecord,
    expected_store_identity_sha256: str,
    expected_declaration_envelope_sha256: str,
    expected_authorization_envelope_sha256: str,
    expected_claim_envelope_sha256: str,
    output_namespace_receipt: e.D7PreStartPathAbsenceReceipt,
    terminal_path_receipt: e.D7PreStartPathAbsenceReceipt,
) -> D7PersistedRecordIdentity:
    """Persist a caller-supplied start record after a second absence observation."""

    if type(start) is not r.D7ExecutionStartRecord:
        raise TypeError("start must be an exact D7ExecutionStartRecord")
    store = _open_real_directory(store_directory, label="D7 attempt store")
    lane: _DirectoryAnchor | None = None
    evidence: _DirectoryAnchor | None = None
    try:
        lane = _open_prefix_lane(store, create=False)
        key = start.attempt_key_sha256
        _require_absent(lane, _start_leaf(key), label="D7 execution start")
        (
            scope,
            declaration,
            authorization,
            authorization_output,
            authorization_terminal,
            declaration_envelope,
            authorization_envelope,
            scope_identity,
            declaration_identity,
            authorization_identity,
        ) = _load_authorized_evidence_prefix(
            store,
            lane,
            attempt_key_sha256=key,
            expected_store_identity_sha256=expected_store_identity_sha256,
            expected_declaration_sha256=start.attempt_declaration_sha256,
            expected_authorization_sha256=start.launch_authorization_sha256,
            expected_declaration_envelope_sha256=(expected_declaration_envelope_sha256),
            expected_authorization_envelope_sha256=(
                expected_authorization_envelope_sha256
            ),
        )
        (
            claim_value,
            claim_envelope,
            claim_identity,
        ) = _load_stage_envelope(
            store,
            lane,
            scope=scope,
            attempt_key_sha256=key,
            stage_kind=_D7PrefixStageKind.ATTEMPT_CLAIM,
            expected_envelope_sha256=expected_claim_envelope_sha256,
            expected_record_sha256=start.attempt_claim_sha256,
            expected_previous_envelope_sha256=(authorization_envelope.canonical_sha256),
        )
        claim = claim_value
        assert type(claim) is r.D7AttemptClaimRecord
        v.validate_d7_attempt_prefix(
            declaration=declaration,
            authorization=authorization,
            claim=claim,
            start=start,
        )
        ev.validate_d7_path_absence_receipt_chain(
            declaration=declaration,
            authorization=authorization,
            claim=claim,
            start=start,
            authorization_output_receipt=authorization_output,
            authorization_terminal_receipt=authorization_terminal,
            pre_start_output_receipt=output_namespace_receipt,
            pre_start_terminal_receipt=terminal_path_receipt,
        )
        _reject_reserved_subjects(
            store.path,
            key,
            authorization_output,
            authorization_terminal,
            output_namespace_receipt,
            terminal_path_receipt,
        )
        _reobserve_absence(store.path, output_namespace_receipt)
        _reobserve_absence(store.path, terminal_path_receipt)
        evidence = _open_evidence_directory(store, create=True)
        _require_durable(
            _write_receipt(evidence, output_namespace_receipt),
            label="pre-start output absence receipt",
        )
        _require_durable(
            _write_receipt(evidence, terminal_path_receipt),
            label="pre-start terminal absence receipt",
        )
        _reobserve_absence(store.path, output_namespace_receipt)
        _reobserve_absence(store.path, terminal_path_receipt)
        _start_envelope, identity = _write_stage_envelope(
            store,
            lane,
            scope=scope,
            stage_kind=_D7PrefixStageKind.EXECUTION_START,
            record=start,
            previous_envelope_sha256=claim_envelope.canonical_sha256,
        )
        loaded = load_d7_evidence_only_prefix(
            store.path,
            attempt_key_sha256=key,
            expected_store_identity_sha256=expected_store_identity_sha256,
            expected_declaration_sha256=declaration.canonical_sha256,
            expected_authorization_sha256=authorization.canonical_sha256,
            expected_claim_sha256=claim.canonical_sha256,
            expected_start_sha256=start.canonical_sha256,
            expected_declaration_envelope_sha256=(
                declaration_envelope.canonical_sha256
            ),
            expected_authorization_envelope_sha256=(
                authorization_envelope.canonical_sha256
            ),
            expected_claim_envelope_sha256=claim_envelope.canonical_sha256,
            expected_start_envelope_sha256=identity.canonical_sha256,
        )
        if (
            loaded.store_scope_identity.canonical_sha256
            != scope_identity.canonical_sha256
            or loaded.declaration_identity.canonical_sha256
            != declaration_identity.canonical_sha256
            or loaded.authorization_identity.canonical_sha256
            != authorization_identity.canonical_sha256
            or loaded.claim_identity.canonical_sha256 != claim_identity.canonical_sha256
        ):
            raise QualificationContractError(
                "D7 predecessor identity changed during start publication"
            )
        return identity
    finally:
        if evidence is not None:
            os.close(evidence.descriptor)
        if lane is not None:
            os.close(lane.descriptor)
        os.close(store.descriptor)


def load_d7_evidence_only_prefix(
    store_directory: str | Path,
    *,
    attempt_key_sha256: str,
    expected_store_identity_sha256: str,
    expected_declaration_sha256: str,
    expected_authorization_sha256: str,
    expected_claim_sha256: str,
    expected_start_sha256: str,
    expected_declaration_envelope_sha256: str,
    expected_authorization_envelope_sha256: str,
    expected_claim_envelope_sha256: str,
    expected_start_envelope_sha256: str,
) -> D7LoadedEvidenceOnlyPrefix:
    """Strictly reload one complete caller-supplied evidence prefix."""

    key = _sha256(attempt_key_sha256, "attempt_key_sha256")
    store = _open_real_directory(store_directory, label="D7 attempt store")
    lane: _DirectoryAnchor | None = None
    evidence: _DirectoryAnchor | None = None
    try:
        lane = _open_prefix_lane(store, create=False)
        (
            scope,
            declaration,
            authorization,
            authorization_output,
            authorization_terminal,
            declaration_envelope,
            authorization_envelope,
            scope_identity,
            declaration_identity,
            authorization_identity,
        ) = _load_authorized_evidence_prefix(
            store,
            lane,
            attempt_key_sha256=key,
            expected_store_identity_sha256=expected_store_identity_sha256,
            expected_declaration_sha256=expected_declaration_sha256,
            expected_authorization_sha256=expected_authorization_sha256,
            expected_declaration_envelope_sha256=(expected_declaration_envelope_sha256),
            expected_authorization_envelope_sha256=(
                expected_authorization_envelope_sha256
            ),
        )
        claim_value, claim_envelope, claim_identity = _load_stage_envelope(
            store,
            lane,
            scope=scope,
            attempt_key_sha256=key,
            stage_kind=_D7PrefixStageKind.ATTEMPT_CLAIM,
            expected_envelope_sha256=expected_claim_envelope_sha256,
            expected_record_sha256=expected_claim_sha256,
            expected_previous_envelope_sha256=(authorization_envelope.canonical_sha256),
        )
        start_value, start_envelope, start_identity = _load_stage_envelope(
            store,
            lane,
            scope=scope,
            attempt_key_sha256=key,
            stage_kind=_D7PrefixStageKind.EXECUTION_START,
            expected_envelope_sha256=expected_start_envelope_sha256,
            expected_record_sha256=expected_start_sha256,
            expected_previous_envelope_sha256=claim_envelope.canonical_sha256,
        )
        claim = claim_value
        start = start_value
        assert type(claim) is r.D7AttemptClaimRecord
        assert type(start) is r.D7ExecutionStartRecord
        evidence = _open_evidence_directory(store, create=False)
        pre_start_output = _load_receipt(
            evidence,
            expected_sha256=(start.pre_start_output_namespace_absence_receipt_sha256),
            record_type=e.D7PreStartPathAbsenceReceipt,
            label="pre-start output absence receipt",
        )
        pre_start_terminal = _load_receipt(
            evidence,
            expected_sha256=start.pre_start_terminal_path_absence_receipt_sha256,
            record_type=e.D7PreStartPathAbsenceReceipt,
            label="pre-start terminal absence receipt",
        )
        assert type(pre_start_output) is e.D7PreStartPathAbsenceReceipt
        assert type(pre_start_terminal) is e.D7PreStartPathAbsenceReceipt
        _reject_reserved_subjects(
            store.path,
            key,
            authorization_output,
            authorization_terminal,
            pre_start_output,
            pre_start_terminal,
        )
        _verify_receipt_location(store.path, pre_start_output)
        _verify_receipt_location(store.path, pre_start_terminal)
        return D7LoadedEvidenceOnlyPrefix(
            store_root=store.path,
            declaration=declaration,
            authorization=authorization,
            claim=claim,
            start=start,
            authorization_output_receipt=authorization_output,
            authorization_terminal_receipt=authorization_terminal,
            pre_start_output_receipt=pre_start_output,
            pre_start_terminal_receipt=pre_start_terminal,
            store_scope=scope,
            declaration_envelope=declaration_envelope,
            authorization_envelope=authorization_envelope,
            claim_envelope=claim_envelope,
            start_envelope=start_envelope,
            store_scope_identity=scope_identity,
            declaration_identity=declaration_identity,
            authorization_identity=authorization_identity,
            claim_identity=claim_identity,
            start_identity=start_identity,
        )
    finally:
        if evidence is not None:
            os.close(evidence.descriptor)
        if lane is not None:
            os.close(lane.descriptor)
        os.close(store.descriptor)


def inspect_d7_evidence_only_prefix(
    loaded: D7LoadedEvidenceOnlyPrefix,
) -> D7EvidenceOnlyPrefixInspection:
    """Classify terminal absence/presence without establishing execution.

    A malformed, aliased, or unknown terminal entry is presence, never absence.
    Elapsed time, PID/process absence, and caller assertions are not inputs.
    """

    if type(loaded) is not D7LoadedEvidenceOnlyPrefix:
        raise TypeError("loaded must be an exact D7LoadedEvidenceOnlyPrefix")
    reloaded = load_d7_evidence_only_prefix(
        loaded.store_root,
        attempt_key_sha256=loaded.start.attempt_key_sha256,
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
    if (
        reloaded.declaration != loaded.declaration
        or reloaded.authorization != loaded.authorization
        or reloaded.claim != loaded.claim
        or reloaded.start != loaded.start
    ):
        raise QualificationContractError(
            "D7 persisted prefix changed before state inspection"
        )
    terminal = reloaded.pre_start_terminal_receipt
    parent = _open_real_directory(
        terminal.resolved_parent_realpath,
        label="D7 terminal parent",
    )
    try:
        if (parent.device, parent.inode) != (
            terminal.parent_device,
            terminal.parent_inode,
        ):
            raise QualificationContractError(
                "D7 terminal parent identity changed after start"
            )
        terminal_path = parent.path / terminal.subject_basename
        state = (
            D7EvidenceOnlyPrefixState.CALLER_SUPPLIED_START_RECORD_PRESENT_TERMINAL_ABSENT
            if _relative_stat(parent, terminal.subject_basename) is None
            else D7EvidenceOnlyPrefixState.TERMINAL_PATH_PRESENT_UNVERIFIED
        )
        _verify_anchor(parent, label="D7 terminal parent")
        return D7EvidenceOnlyPrefixInspection(
            state=state,
            terminal_path=terminal_path,
        )
    finally:
        os.close(parent.descriptor)
