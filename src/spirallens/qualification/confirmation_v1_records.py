"""Strict source-only records for the fresh D7 v1 successor.

This module defines canonical in-memory record types.  It performs no
persistence, seed generation, supplier invocation, model access, subject
access, execution, or publication.  The records are deliberately unrelated to
the historical ``confirmation_*`` record classes: v1 has a fresh schema and
fresh chronology.

Every loader verifies the caller-provided SHA-256 before parsing, accepts only
canonical JSON below a fixed byte cap, rejects unknown fields recursively, and
round-trips the exact input bytes.  Constructors are factory-only and retain
only immutable canonical bytes.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import PurePosixPath
import re
from typing import ClassVar, Self

from spirallens.core.canonical import (
    CanonicalJsonError,
    canonical_json_bytes,
    parse_canonical_json,
    sha256_bytes,
)

from .common import (
    QualificationContractError,
    require_plain_int,
    require_sha256,
    require_slug,
)

__all__: tuple[str, ...] = ()

D7_V1_SUCCESSOR_LINEAGE_ID = "d7-spectral-moment-confirmation-v1"
D7_V1_DEFAULT_MAX_RECORD_BYTES = 4 * 1024 * 1024
D7_V1_POSTSELECTION_RESULT_MAX_RECORD_BYTES = 16 * 1024 * 1024
# Compatibility name for the default cap; record classes bind their own cap.
D7_V1_MAX_RECORD_BYTES = D7_V1_DEFAULT_MAX_RECORD_BYTES

D7_V1_ARTIFACT_BINDING_SCHEMA_VERSION = "spirallens.d7-v1-artifact-binding.v0.1"
D7_V1_JSON_POINTER_BINDING_SCHEMA_VERSION = "spirallens.d7-v1-json-pointer-binding.v0.1"
D7_V1_FULL_DESIGN_INVENTORY_SCHEMA_VERSION = (
    "spirallens.d7-v1-full-design-inventory.v0.1"
)
D7_V1_NAMESPACE_ABSENCE_SCHEMA_VERSION = (
    "spirallens.d7-v1-namespace-absence-observation.v0.1"
)
D7_V1_READ_TRACE_ENTRY_SCHEMA_VERSION = "spirallens.d7-v1-read-trace-entry.v0.1"
D7_V1_DESCRIPTIVE_OUTPUT_SCHEMA_VERSION = (
    "spirallens.d7-v1-post-d6-descriptive-output.v0.1"
)
D7_V1_SOURCE_MEMBER_SCHEMA_VERSION = "spirallens.d7-v1-source-member.v0.1"
D7_V1_SOURCE_INVENTORY_SCHEMA_VERSION = "spirallens.d7-v1-source-member-inventory.v0.1"
D7_V1_REPOSITORY_ARTIFACT_BINDING_SCHEMA_VERSION = (
    "spirallens.d7-v1-repository-artifact-binding.v0.1"
)

D7_V1_C1_SOURCE_SET_SCHEMA_VERSION = "spirallens.d7-v1-c1-seed-free-source-set.v0.1"
D7_V1_C2_SOURCE_CLOSURE_SCHEMA_VERSION = (
    "spirallens.d7-v1-c2-source-closure-receipt.v0.1"
)
D7_V1_EXCLUSIVE_SEED_SUPPLY_CLAIM_SCHEMA_VERSION = (
    "spirallens.d7-v1-exclusive-seed-supply-claim.v0.1"
)
D7_V1_OFFICIAL_SEED_INVENTORY_SCHEMA_VERSION = (
    "spirallens.d7-v1-official-seed-inventory.v0.1"
)
D7_V1_EMBEDDED_FULL_DESIGN_SCHEMA_VERSION = "spirallens.d7-v1-embedded-full-design.v0.1"
D7_V1_REPLAY_TARGET_SCHEMA_VERSION = "spirallens.d7-v1-replay-target.v0.1"
D7_V1_FULL_DESIGN_FREEZE_SCHEMA_VERSION = "spirallens.d7-v1-full-design-freeze.v0.1"
D7_V1_LAUNCH_INTENT_SCHEMA_VERSION = "spirallens.d7-v1-launch-intent.v0.1"
D7_V1_ATTEMPT_RESERVATION_SCHEMA_VERSION = (
    "spirallens.d7-v1-official-execution-attempt-reservation.v0.1"
)
D7_V1_PRE_ITEM23_RECEIPT_SCHEMA_VERSION = (
    "spirallens.d7-v1-pre-item23-chronology-receipt.v0.1"
)
D7_V1_POSTSELECTION_RESULT_SCHEMA_VERSION = (
    "spirallens.d7-v1-postselection-descriptive-result.v0.1"
)

D7_V1_SOURCE_TREE_DOMAIN = "spirallens.d7-v1-source-tree.v0.1"
D7_V1_SEED_CLAIM_KEY_DOMAIN = "spirallens.d7-v1-exclusive-seed-supply-claim-key.v0.1"
D7_V1_ATTEMPT_KEY_DOMAIN = "spirallens.d7-v1-official-attempt-key.v0.1"

_FACTORY_TOKEN = object()
_COMMIT = re.compile(r"^[0-9a-f]{40}$")
_SCHEMA = re.compile(r"^spirallens\.[a-z0-9][a-z0-9._-]{0,255}$")
_JSON_POINTER = re.compile(r"^(?:/(?:[^~/]|~[01])*)*$")
_MAX_SIGNED_INT64 = (1 << 63) - 1

_CLAIM_BOUNDARY = {
    "attempt_issued": False,
    "claim_ceiling": "level_0",
    "claim_delta": "none",
    "confirmation_values_accessed": False,
    "d7_execution_authorized": False,
    "d7_result_produced": False,
    "d8_execution_authorized": False,
    "integer_output_authorized": False,
    "model_access_authorized": False,
    "pythia_access_authorized": False,
    "scientific_claim_eligible": False,
    "semantic_authority": False,
    "subject_access_authorized": False,
    "subject_preparation_authorized": False,
    "synthetic_qualified": False,
    "topology_claim_authorized": False,
}

_PRE_ITEM23_FILE_ROLES = (
    "c1-seed-free-source-set",
    "c2-source-closure-receipt",
    "exclusive-seed-supply-claim",
    "official-seed-inventory",
    "replay-target",
    "full-design-freeze",
    "launch-intent",
    "official-execution-attempt-reservation",
    "pre-item23-chronology-receipt",
)

_INTERNAL_ROLE_SCHEMAS = {
    "c1-seed-free-source-set": D7_V1_C1_SOURCE_SET_SCHEMA_VERSION,
    "c2-source-closure-receipt": D7_V1_C2_SOURCE_CLOSURE_SCHEMA_VERSION,
    "exclusive-seed-supply-claim": (D7_V1_EXCLUSIVE_SEED_SUPPLY_CLAIM_SCHEMA_VERSION),
    "official-seed-inventory": D7_V1_OFFICIAL_SEED_INVENTORY_SCHEMA_VERSION,
    "embedded-full-design": D7_V1_EMBEDDED_FULL_DESIGN_SCHEMA_VERSION,
    "replay-target": D7_V1_REPLAY_TARGET_SCHEMA_VERSION,
    "full-design-freeze": D7_V1_FULL_DESIGN_FREEZE_SCHEMA_VERSION,
    "launch-intent": D7_V1_LAUNCH_INTENT_SCHEMA_VERSION,
    "official-execution-attempt-reservation": (
        D7_V1_ATTEMPT_RESERVATION_SCHEMA_VERSION
    ),
    "pre-item23-chronology-receipt": D7_V1_PRE_ITEM23_RECEIPT_SCHEMA_VERSION,
    "postselection-descriptive-result": D7_V1_POSTSELECTION_RESULT_SCHEMA_VERSION,
}


def _mapping(value: object, *, label: str) -> dict[str, object]:
    if type(value) is not dict or any(type(key) is not str for key in value):
        raise QualificationContractError(f"{label} must be a JSON object")
    return value


def _sequence(value: object, *, label: str) -> list[object]:
    if type(value) is not list:
        raise QualificationContractError(f"{label} must be a JSON array")
    return value


def _exact_keys(
    value: Mapping[str, object],
    expected: set[str],
    *,
    label: str,
) -> None:
    if set(value) != expected:
        raise QualificationContractError(
            f"{label} fields differ: expected {sorted(expected)}, "
            f"observed {sorted(value)}"
        )


def _string(value: object, *, label: str) -> str:
    if type(value) is not str or not value or value != value.strip():
        raise QualificationContractError(f"{label} must be a non-empty trimmed string")
    return value


def _schema(value: object, *, label: str) -> str:
    text = _string(value, label=label)
    if _SCHEMA.fullmatch(text) is None:
        raise QualificationContractError(f"{label} must be a SpiralLens schema id")
    return text


def _commit(value: object, *, label: str) -> str:
    if type(value) is not str or _COMMIT.fullmatch(value) is None:
        raise QualificationContractError(f"{label} must be a full lowercase Git commit")
    return value


def _relative_repository_path(value: object, *, label: str) -> str:
    text = _string(value, label=label)
    path = PurePosixPath(text)
    if (
        path.is_absolute()
        or text != path.as_posix()
        or any(part in {"", ".", ".."} for part in path.parts)
    ):
        raise QualificationContractError(
            f"{label} must be a normalized relative repository path"
        )
    return text


def _absolute_posix_path(value: object, *, label: str) -> str:
    text = _string(value, label=label)
    path = PurePosixPath(text)
    if (
        not path.is_absolute()
        or text.startswith("//")
        or text != path.as_posix()
        or any(part in {"", ".", ".."} for part in path.parts)
    ):
        raise QualificationContractError(
            f"{label} must be a normalized absolute POSIX path"
        )
    return text


def _false(value: object, *, label: str) -> bool:
    if value is not False:
        raise QualificationContractError(f"{label} must be false")
    return False


def _true(value: object, *, label: str) -> bool:
    if value is not True:
        raise QualificationContractError(f"{label} must be true")
    return True


def _validate_claim_boundary(value: object) -> None:
    boundary = _mapping(value, label="claim_boundary")
    _exact_keys(boundary, set(_CLAIM_BOUNDARY), label="claim_boundary")
    if boundary != _CLAIM_BOUNDARY:
        raise QualificationContractError(
            "claim_boundary must retain the Level-0 no-authority boundary"
        )


def _canonical_subdocument(value: object, *, label: str) -> bytes:
    document = _mapping(value, label=label)
    try:
        return canonical_json_bytes(document)
    except CanonicalJsonError as error:
        raise QualificationContractError(str(error)) from error


def _load_canonical_document(
    source: bytes,
    *,
    expected_sha256: str,
    label: str,
    max_record_bytes: int,
) -> dict[str, object]:
    if type(source) is not bytes or not source or len(source) > max_record_bytes:
        raise QualificationContractError(f"{label} exceeds its byte contract")
    expected = require_sha256(expected_sha256, label=f"{label} expected_sha256")
    observed = sha256_bytes(source)
    if observed != expected:
        raise QualificationContractError(f"{label} digest differs before parse")
    try:
        value = parse_canonical_json(source, label=label)
    except CanonicalJsonError as error:
        raise QualificationContractError(str(error)) from error
    return _mapping(value, label=label)


@dataclass(frozen=True, slots=True)
class D7V1ArtifactBinding:
    artifact_role: str
    artifact_contract_id: str
    canonical_sha256: str
    byte_count: int

    schema_version: ClassVar[str] = D7_V1_ARTIFACT_BINDING_SCHEMA_VERSION

    def __post_init__(self) -> None:
        require_slug(self.artifact_role, label="artifact_role")
        _schema(self.artifact_contract_id, label="artifact_contract_id")
        require_sha256(self.canonical_sha256, label="canonical_sha256")
        require_plain_int(self.byte_count, label="byte_count", minimum=1)

    @classmethod
    def from_record(
        cls,
        record: "_D7V1CanonicalRecord",
    ) -> Self:
        if not isinstance(record, _D7V1CanonicalRecord):
            raise TypeError("record must be a D7 v1 canonical record")
        return cls(
            artifact_role=record.artifact_role,
            artifact_contract_id=record.schema_version,
            canonical_sha256=record.canonical_sha256,
            byte_count=record.byte_count,
        )

    @classmethod
    def from_dict(cls, value: object) -> Self:
        item = _mapping(value, label="artifact binding")
        _exact_keys(
            item,
            {
                "schema_version",
                "artifact_role",
                "artifact_contract_id",
                "canonical_sha256",
                "byte_count",
                "authoritative_source_loaded",
                "identity_authenticated",
            },
            label="artifact binding",
        )
        if item["schema_version"] != cls.schema_version:
            raise QualificationContractError("artifact binding schema differs")
        _false(item["authoritative_source_loaded"], label="authoritative_source_loaded")
        _false(item["identity_authenticated"], label="identity_authenticated")
        return cls(
            artifact_role=require_slug(item["artifact_role"], label="artifact_role"),
            artifact_contract_id=_schema(
                item["artifact_contract_id"], label="artifact_contract_id"
            ),
            canonical_sha256=require_sha256(
                item["canonical_sha256"], label="canonical_sha256"
            ),
            byte_count=require_plain_int(
                item["byte_count"], label="byte_count", minimum=1
            ),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "artifact_role": self.artifact_role,
            "artifact_contract_id": self.artifact_contract_id,
            "canonical_sha256": self.canonical_sha256,
            "byte_count": self.byte_count,
            "authoritative_source_loaded": False,
            "identity_authenticated": False,
        }


@dataclass(frozen=True, slots=True)
class D7V1JsonPointerBinding:
    json_pointer: str
    target_schema_version: str
    canonical_sha256: str
    byte_count: int

    schema_version: ClassVar[str] = D7_V1_JSON_POINTER_BINDING_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if (
            type(self.json_pointer) is not str
            or _JSON_POINTER.fullmatch(self.json_pointer) is None
        ):
            raise QualificationContractError("json_pointer must be an RFC 6901 pointer")
        _schema(self.target_schema_version, label="target_schema_version")
        require_sha256(self.canonical_sha256, label="canonical_sha256")
        require_plain_int(self.byte_count, label="byte_count", minimum=1)

    @classmethod
    def from_subdocument(
        cls,
        value: object,
        *,
        json_pointer: str,
        target_schema_version: str,
    ) -> Self:
        source = _canonical_subdocument(value, label=f"subdocument at {json_pointer}")
        return cls(
            json_pointer=json_pointer,
            target_schema_version=target_schema_version,
            canonical_sha256=sha256_bytes(source),
            byte_count=len(source),
        )

    @classmethod
    def from_dict(cls, value: object) -> Self:
        item = _mapping(value, label="JSON pointer binding")
        _exact_keys(
            item,
            {
                "schema_version",
                "json_pointer",
                "target_schema_version",
                "canonical_sha256",
                "byte_count",
                "identity_authenticated",
            },
            label="JSON pointer binding",
        )
        if item["schema_version"] != cls.schema_version:
            raise QualificationContractError("JSON pointer binding schema differs")
        _false(item["identity_authenticated"], label="identity_authenticated")
        return cls(
            json_pointer=_string(item["json_pointer"], label="json_pointer"),
            target_schema_version=_schema(
                item["target_schema_version"], label="target_schema_version"
            ),
            canonical_sha256=require_sha256(
                item["canonical_sha256"], label="canonical_sha256"
            ),
            byte_count=require_plain_int(
                item["byte_count"], label="byte_count", minimum=1
            ),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "json_pointer": self.json_pointer,
            "target_schema_version": self.target_schema_version,
            "canonical_sha256": self.canonical_sha256,
            "byte_count": self.byte_count,
            "identity_authenticated": False,
        }


@dataclass(frozen=True, slots=True)
class D7V1NamespaceAbsenceObservation:
    repository_path: str
    observed_at_reviewed_source_commit: str

    schema_version: ClassVar[str] = D7_V1_NAMESPACE_ABSENCE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        _relative_repository_path(self.repository_path, label="repository_path")
        _commit(
            self.observed_at_reviewed_source_commit,
            label="observed_at_reviewed_source_commit",
        )

    @classmethod
    def from_dict(cls, value: object) -> Self:
        item = _mapping(value, label="namespace absence observation")
        _exact_keys(
            item,
            {
                "schema_version",
                "repository_path",
                "observed_at_reviewed_source_commit",
                "path_absent",
                "observation_authorizes_future_write",
            },
            label="namespace absence observation",
        )
        if item["schema_version"] != cls.schema_version:
            raise QualificationContractError("namespace absence schema differs")
        _true(item["path_absent"], label="path_absent")
        _false(
            item["observation_authorizes_future_write"],
            label="observation_authorizes_future_write",
        )
        return cls(
            repository_path=_relative_repository_path(
                item["repository_path"], label="repository_path"
            ),
            observed_at_reviewed_source_commit=_commit(
                item["observed_at_reviewed_source_commit"],
                label="observed_at_reviewed_source_commit",
            ),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "repository_path": self.repository_path,
            "observed_at_reviewed_source_commit": (
                self.observed_at_reviewed_source_commit
            ),
            "path_absent": True,
            "observation_authorizes_future_write": False,
        }


@dataclass(frozen=True, slots=True)
class D7V1ReadTraceEntry:
    sequence: int
    artifact_binding: D7V1ArtifactBinding

    schema_version: ClassVar[str] = D7_V1_READ_TRACE_ENTRY_SCHEMA_VERSION

    def __post_init__(self) -> None:
        require_plain_int(self.sequence, label="read trace sequence", minimum=1)
        if not isinstance(self.artifact_binding, D7V1ArtifactBinding):
            raise TypeError("artifact_binding must be D7V1ArtifactBinding")

    @classmethod
    def from_dict(cls, value: object) -> Self:
        item = _mapping(value, label="read trace entry")
        _exact_keys(
            item,
            {"schema_version", "sequence", "artifact_binding"},
            label="read trace entry",
        )
        if item["schema_version"] != cls.schema_version:
            raise QualificationContractError("read trace entry schema differs")
        return cls(
            sequence=require_plain_int(
                item["sequence"], label="read trace sequence", minimum=1
            ),
            artifact_binding=D7V1ArtifactBinding.from_dict(item["artifact_binding"]),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "sequence": self.sequence,
            "artifact_binding": self.artifact_binding.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class D7V1SourceMember:
    repository_path: str
    git_mode: str
    sha256: str
    byte_count: int

    schema_version: ClassVar[str] = D7_V1_SOURCE_MEMBER_SCHEMA_VERSION

    def __post_init__(self) -> None:
        _relative_repository_path(self.repository_path, label="source repository_path")
        if self.git_mode not in {"100644", "100755"}:
            raise QualificationContractError("source git_mode must be 100644 or 100755")
        require_sha256(self.sha256, label="source sha256")
        require_plain_int(self.byte_count, label="source byte_count", minimum=0)

    @classmethod
    def from_dict(cls, value: object) -> Self:
        item = _mapping(value, label="source member")
        _exact_keys(
            item,
            {
                "schema_version",
                "repository_path",
                "git_mode",
                "sha256",
                "byte_count",
            },
            label="source member",
        )
        if item["schema_version"] != cls.schema_version:
            raise QualificationContractError("source member schema differs")
        return cls(
            repository_path=_relative_repository_path(
                item["repository_path"], label="source repository_path"
            ),
            git_mode=_string(item["git_mode"], label="source git_mode"),
            sha256=require_sha256(item["sha256"], label="source sha256"),
            byte_count=require_plain_int(
                item["byte_count"], label="source byte_count", minimum=0
            ),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "repository_path": self.repository_path,
            "git_mode": self.git_mode,
            "sha256": self.sha256,
            "byte_count": self.byte_count,
        }


def _source_inventory_document(
    members: Sequence[D7V1SourceMember],
) -> dict[str, object]:
    return {
        "schema_version": D7_V1_SOURCE_INVENTORY_SCHEMA_VERSION,
        "source_members": [member.to_dict() for member in members],
    }


@dataclass(frozen=True, slots=True)
class D7V1RepositoryArtifactBinding:
    repository_path: str
    artifact_binding: D7V1ArtifactBinding

    schema_version: ClassVar[str] = D7_V1_REPOSITORY_ARTIFACT_BINDING_SCHEMA_VERSION

    def __post_init__(self) -> None:
        _relative_repository_path(self.repository_path, label="repository_path")
        if not isinstance(self.artifact_binding, D7V1ArtifactBinding):
            raise TypeError("artifact_binding must be D7V1ArtifactBinding")

    @classmethod
    def from_dict(cls, value: object) -> Self:
        item = _mapping(value, label="repository artifact binding")
        _exact_keys(
            item,
            {"schema_version", "repository_path", "artifact_binding"},
            label="repository artifact binding",
        )
        if item["schema_version"] != cls.schema_version:
            raise QualificationContractError(
                "repository artifact binding schema differs"
            )
        return cls(
            repository_path=_relative_repository_path(
                item["repository_path"], label="repository_path"
            ),
            artifact_binding=D7V1ArtifactBinding.from_dict(item["artifact_binding"]),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "repository_path": self.repository_path,
            "artifact_binding": self.artifact_binding.to_dict(),
        }


class _FactoryCanonicalBytes:
    __slots__ = ("_canonical_source",)

    schema_version: ClassVar[str]
    artifact_role: ClassVar[str]
    max_record_bytes: ClassVar[int] = D7_V1_DEFAULT_MAX_RECORD_BYTES

    def __init__(self, source: bytes, *, _factory_token: object) -> None:
        if _factory_token is not _FACTORY_TOKEN:
            raise TypeError("D7 v1 records must be constructed by a validated factory")
        object.__setattr__(self, "_canonical_source", source)

    def __setattr__(self, name: str, value: object) -> None:
        del name, value
        raise AttributeError("D7 v1 records are immutable")

    @classmethod
    def _validate_document(cls, value: object) -> dict[str, object]:
        raise NotImplementedError

    @classmethod
    def from_dict(cls, value: object) -> Self:
        document = cls._validate_document(value)
        try:
            source = canonical_json_bytes(document)
        except CanonicalJsonError as error:
            raise QualificationContractError(str(error)) from error
        return cls.from_canonical_bytes(source, expected_sha256=sha256_bytes(source))

    @classmethod
    def from_canonical_bytes(cls, source: bytes, *, expected_sha256: str) -> Self:
        document = _load_canonical_document(
            source,
            expected_sha256=expected_sha256,
            label=cls.artifact_role,
            max_record_bytes=cls.max_record_bytes,
        )
        cls._validate_document(document)
        if canonical_json_bytes(document) != source:
            raise QualificationContractError(
                f"{cls.artifact_role} canonical round-trip differs"
            )
        return cls(source, _factory_token=_FACTORY_TOKEN)

    @property
    def canonical_bytes(self) -> bytes:
        return self._canonical_source

    @property
    def canonical_sha256(self) -> str:
        return sha256_bytes(self._canonical_source)

    @property
    def byte_count(self) -> int:
        return len(self._canonical_source)

    def to_dict(self) -> dict[str, object]:
        value = parse_canonical_json(self._canonical_source, label=self.artifact_role)
        return _mapping(value, label=self.artifact_role)


class _D7V1CanonicalRecord(_FactoryCanonicalBytes):
    """Immutable canonical record with a factory-only constructor."""

    __slots__ = ()

    typestate: ClassVar[tuple[tuple[str, object], ...]]

    @classmethod
    def _validate_payload(cls, value: object) -> None:
        raise NotImplementedError

    @classmethod
    def _validate_document(cls, value: object) -> dict[str, object]:
        item = _mapping(value, label=cls.artifact_role)
        _exact_keys(
            item,
            {
                "schema_version",
                "record_id",
                "artifact_role",
                "successor_lineage_id",
                "payload",
                "typestate",
                "claim_boundary",
            },
            label=cls.artifact_role,
        )
        if item["schema_version"] != cls.schema_version:
            raise QualificationContractError(f"{cls.artifact_role} schema differs")
        require_slug(item["record_id"], label="record_id")
        if item["artifact_role"] != cls.artifact_role:
            raise QualificationContractError(f"{cls.artifact_role} role differs")
        if item["successor_lineage_id"] != D7_V1_SUCCESSOR_LINEAGE_ID:
            raise QualificationContractError("successor lineage differs")
        cls._validate_payload(item["payload"])
        state = _mapping(item["typestate"], label="typestate")
        expected_state = dict(cls.typestate)
        _exact_keys(state, set(expected_state), label="typestate")
        if state != expected_state:
            raise QualificationContractError(f"{cls.artifact_role} typestate differs")
        _validate_claim_boundary(item["claim_boundary"])
        return item

    @classmethod
    def _create(cls, *, record_id: str, payload: dict[str, object]) -> Self:
        document = {
            "schema_version": cls.schema_version,
            "record_id": record_id,
            "artifact_role": cls.artifact_role,
            "successor_lineage_id": D7_V1_SUCCESSOR_LINEAGE_ID,
            "payload": payload,
            "typestate": dict(cls.typestate),
            "claim_boundary": dict(_CLAIM_BOUNDARY),
        }
        return cls.from_dict(document)


def _binding(
    value: object,
    *,
    role: str,
    label: str,
) -> D7V1ArtifactBinding:
    binding = D7V1ArtifactBinding.from_dict(value)
    if binding.artifact_role != role:
        raise QualificationContractError(f"{label} role must be {role}")
    expected_schema = _INTERNAL_ROLE_SCHEMAS.get(role)
    if expected_schema is not None and binding.artifact_contract_id != expected_schema:
        raise QualificationContractError(f"{label} schema must be {expected_schema}")
    return binding


def _pointer_binding(
    value: object,
    *,
    pointer: str,
    schema_version: str,
    subdocument: object,
    label: str,
) -> D7V1JsonPointerBinding:
    binding = D7V1JsonPointerBinding.from_dict(value)
    expected = D7V1JsonPointerBinding.from_subdocument(
        subdocument,
        json_pointer=pointer,
        target_schema_version=schema_version,
    )
    if binding != expected:
        raise QualificationContractError(f"{label} does not bind the exact subdocument")
    return binding


def _record_path_payload(
    value: object,
    *,
    expected: set[str],
    label: str,
) -> dict[str, object]:
    payload = _mapping(value, label=label)
    _exact_keys(payload, expected | {"repository_path"}, label=label)
    _relative_repository_path(payload["repository_path"], label="repository_path")
    return payload


class D7V1C1SourceSetRecord(_D7V1CanonicalRecord):
    __slots__ = ()

    schema_version = D7_V1_C1_SOURCE_SET_SCHEMA_VERSION
    artifact_role = "c1-seed-free-source-set"
    typestate = (
        ("seed_free_source_set_present", True),
        ("source_closure_established", False),
        ("seed_values_present", False),
    )

    @classmethod
    def create(
        cls,
        *,
        record_id: str,
        repository_path: str,
        route_binding: D7V1ArtifactBinding,
        source_members: Sequence[D7V1SourceMember],
    ) -> Self:
        if not source_members or any(
            not isinstance(member, D7V1SourceMember) for member in source_members
        ):
            raise TypeError("source_members must be a non-empty source-member sequence")
        ordered = tuple(
            sorted(source_members, key=lambda member: member.repository_path)
        )
        inventory = _source_inventory_document(ordered)
        return cls._create(
            record_id=record_id,
            payload={
                "repository_path": repository_path,
                "route_binding": route_binding.to_dict(),
                "source_members": [member.to_dict() for member in ordered],
                "source_manifest_sha256": sha256_bytes(canonical_json_bytes(inventory)),
                "source_member_count": len(ordered),
            },
        )

    @classmethod
    def _validate_payload(cls, value: object) -> None:
        payload = _record_path_payload(
            value,
            expected={
                "route_binding",
                "source_members",
                "source_manifest_sha256",
                "source_member_count",
            },
            label="C1 payload",
        )
        _binding(
            payload["route_binding"], role="navigation-route", label="route binding"
        )
        member_items = _sequence(payload["source_members"], label="source_members")
        if not member_items:
            raise QualificationContractError("source_members must be non-empty")
        members = tuple(D7V1SourceMember.from_dict(item) for item in member_items)
        paths = tuple(member.repository_path for member in members)
        if paths != tuple(sorted(paths)) or len(set(paths)) != len(paths):
            raise QualificationContractError(
                "source_members must have sorted unique repository paths"
            )
        count = require_plain_int(
            payload["source_member_count"],
            label="source_member_count",
            minimum=1,
        )
        if count != len(members):
            raise QualificationContractError("source_member_count differs")
        expected_manifest = sha256_bytes(
            canonical_json_bytes(_source_inventory_document(members))
        )
        if (
            require_sha256(
                payload["source_manifest_sha256"], label="source_manifest_sha256"
            )
            != expected_manifest
        ):
            raise QualificationContractError(
                "source_manifest_sha256 does not bind source_members"
            )


class D7V1C2SourceClosureReceipt(_D7V1CanonicalRecord):
    __slots__ = ()

    schema_version = D7_V1_C2_SOURCE_CLOSURE_SCHEMA_VERSION
    artifact_role = "c2-source-closure-receipt"
    typestate = (
        ("source_closure_declared", True),
        ("source_closure_record_formed", True),
        ("source_tree_authenticated", False),
        ("seed_values_present", False),
    )

    @classmethod
    def create(
        cls,
        *,
        record_id: str,
        repository_path: str,
        c1: D7V1C1SourceSetRecord,
        source_commit: str,
    ) -> Self:
        if not isinstance(c1, D7V1C1SourceSetRecord):
            raise TypeError("c1 must be D7V1C1SourceSetRecord")
        c1_payload = _mapping(c1.to_dict()["payload"], label="C1 payload")
        derivation = {
            "domain": D7_V1_SOURCE_TREE_DOMAIN,
            "merged_source_commit": source_commit,
            "source_members": c1_payload["source_members"],
        }
        return cls._create(
            record_id=record_id,
            payload={
                "repository_path": repository_path,
                "c1_binding": D7V1ArtifactBinding.from_record(c1).to_dict(),
                "source_tree_derivation": derivation,
                "source_tree_sha256": sha256_bytes(canonical_json_bytes(derivation)),
            },
        )

    @classmethod
    def _validate_payload(cls, value: object) -> None:
        payload = _record_path_payload(
            value,
            expected={
                "c1_binding",
                "source_tree_derivation",
                "source_tree_sha256",
            },
            label="C2 payload",
        )
        _binding(
            payload["c1_binding"],
            role=D7V1C1SourceSetRecord.artifact_role,
            label="C1 binding",
        )
        derivation = _mapping(
            payload["source_tree_derivation"], label="source-tree derivation"
        )
        _exact_keys(
            derivation,
            {"domain", "merged_source_commit", "source_members"},
            label="source-tree derivation",
        )
        if derivation["domain"] != D7_V1_SOURCE_TREE_DOMAIN:
            raise QualificationContractError("source-tree derivation domain differs")
        _commit(derivation["merged_source_commit"], label="merged_source_commit")
        member_items = _sequence(
            derivation["source_members"], label="source-tree source_members"
        )
        if not member_items:
            raise QualificationContractError(
                "source-tree source_members must be non-empty"
            )
        members = tuple(D7V1SourceMember.from_dict(item) for item in member_items)
        paths = tuple(member.repository_path for member in members)
        if paths != tuple(sorted(paths)) or len(set(paths)) != len(paths):
            raise QualificationContractError(
                "source-tree source_members must be sorted and unique"
            )
        expected = sha256_bytes(canonical_json_bytes(derivation))
        if (
            require_sha256(payload["source_tree_sha256"], label="source_tree_sha256")
            != expected
        ):
            raise QualificationContractError("source_tree_sha256 derivation differs")


class D7V1ExclusiveSeedSupplyClaim(_D7V1CanonicalRecord):
    __slots__ = ()

    schema_version = D7_V1_EXCLUSIVE_SEED_SUPPLY_CLAIM_SCHEMA_VERSION
    artifact_role = "exclusive-seed-supply-claim"
    typestate = (
        ("claim_persisted", True),
        ("supplier_entered", False),
        ("seed_values_present", False),
    )

    @classmethod
    def create(
        cls,
        *,
        record_id: str,
        repository_path: str,
        c2: D7V1C2SourceClosureReceipt,
        supplier_identity_binding: D7V1ArtifactBinding,
        supplier_id: str,
        external_claim_path: str,
    ) -> Self:
        if not isinstance(c2, D7V1C2SourceClosureReceipt):
            raise TypeError("c2 must be D7V1C2SourceClosureReceipt")
        c2_payload = _mapping(c2.to_dict()["payload"], label="C2 payload")
        derivation = {
            "c2_sha256": c2.canonical_sha256,
            "domain": D7_V1_SEED_CLAIM_KEY_DOMAIN,
            "external_claim_path": external_claim_path,
            "source_tree_sha256": c2_payload["source_tree_sha256"],
            "supplier_id": supplier_id,
            "supplier_identity_sha256": (supplier_identity_binding.canonical_sha256),
        }
        return cls._create(
            record_id=record_id,
            payload={
                "repository_path": repository_path,
                "c2_binding": D7V1ArtifactBinding.from_record(c2).to_dict(),
                "supplier_identity_binding": supplier_identity_binding.to_dict(),
                "claim_key_derivation": derivation,
                "claim_key_sha256": sha256_bytes(canonical_json_bytes(derivation)),
            },
        )

    @classmethod
    def _validate_payload(cls, value: object) -> None:
        payload = _record_path_payload(
            value,
            expected={
                "c2_binding",
                "supplier_identity_binding",
                "claim_key_derivation",
                "claim_key_sha256",
            },
            label="exclusive seed-supply claim payload",
        )
        c2_binding = _binding(
            payload["c2_binding"],
            role=D7V1C2SourceClosureReceipt.artifact_role,
            label="C2 binding",
        )
        supplier_binding = _binding(
            payload["supplier_identity_binding"],
            role="supplier-identity",
            label="supplier identity binding",
        )
        derivation = _mapping(
            payload["claim_key_derivation"], label="claim-key derivation"
        )
        _exact_keys(
            derivation,
            {
                "c2_sha256",
                "domain",
                "external_claim_path",
                "source_tree_sha256",
                "supplier_id",
                "supplier_identity_sha256",
            },
            label="claim-key derivation",
        )
        if derivation["domain"] != D7_V1_SEED_CLAIM_KEY_DOMAIN:
            raise QualificationContractError("claim-key derivation domain differs")
        if (
            require_sha256(derivation["c2_sha256"], label="c2_sha256")
            != c2_binding.canonical_sha256
        ):
            raise QualificationContractError("claim-key C2 digest differs")
        _absolute_posix_path(
            derivation["external_claim_path"], label="external_claim_path"
        )
        require_sha256(derivation["source_tree_sha256"], label="source_tree_sha256")
        require_slug(derivation["supplier_id"], label="supplier_id")
        if (
            require_sha256(
                derivation["supplier_identity_sha256"],
                label="supplier_identity_sha256",
            )
            != supplier_binding.canonical_sha256
        ):
            raise QualificationContractError(
                "claim-key supplier identity digest differs"
            )
        expected = sha256_bytes(canonical_json_bytes(derivation))
        if (
            require_sha256(payload["claim_key_sha256"], label="claim_key_sha256")
            != expected
        ):
            raise QualificationContractError("claim_key_sha256 derivation differs")


def _seed_values(value: object, *, label: str, nonempty: bool) -> tuple[int, ...]:
    items = _sequence(value, label=label)
    if nonempty and not items:
        raise QualificationContractError(f"{label} must be non-empty")
    result = tuple(
        require_plain_int(item, label=f"{label}[{index}]", minimum=0)
        for index, item in enumerate(items)
    )
    if any(item > _MAX_SIGNED_INT64 for item in result):
        raise QualificationContractError(f"{label} values must fit signed int64")
    if len(set(result)) != len(result):
        raise QualificationContractError(f"{label} values must be unique")
    return result


class D7V1OfficialSeedInventory(_D7V1CanonicalRecord):
    __slots__ = ()

    schema_version = D7_V1_OFFICIAL_SEED_INVENTORY_SCHEMA_VERSION
    artifact_role = "official-seed-inventory"
    typestate = (
        ("claim_persisted", True),
        ("supplier_entered", True),
        ("seed_values_present", True),
        ("disjoint_from_embedded_predecessor_seed_values", True),
        ("predecessor_inventory_authenticated", False),
    )

    @classmethod
    def create(
        cls,
        *,
        record_id: str,
        repository_path: str,
        claim: D7V1ExclusiveSeedSupplyClaim,
        supplier_identity_binding: D7V1ArtifactBinding,
        supplier_id: str,
        seeds: Sequence[int],
        predecessor_inventory_binding: D7V1ArtifactBinding,
        predecessor_seed_values: Sequence[int],
    ) -> Self:
        if not isinstance(claim, D7V1ExclusiveSeedSupplyClaim):
            raise TypeError("claim must be D7V1ExclusiveSeedSupplyClaim")
        claim_payload = _mapping(claim.to_dict()["payload"], label="seed claim payload")
        claim_supplier = D7V1ArtifactBinding.from_dict(
            claim_payload["supplier_identity_binding"]
        )
        claim_derivation = _mapping(
            claim_payload["claim_key_derivation"], label="claim-key derivation"
        )
        if (
            claim_supplier != supplier_identity_binding
            or claim_derivation["supplier_id"] != supplier_id
        ):
            raise QualificationContractError(
                "inventory supplier identity must match the seed claim"
            )
        return cls._create(
            record_id=record_id,
            payload={
                "repository_path": repository_path,
                "claim_binding": D7V1ArtifactBinding.from_record(claim).to_dict(),
                "supplier_identity_binding": supplier_identity_binding.to_dict(),
                "supplier_id": supplier_id,
                "seeds": list(seeds),
                "predecessor_inventory_binding": (
                    predecessor_inventory_binding.to_dict()
                ),
                "predecessor_seed_values": list(predecessor_seed_values),
                "observations": {
                    "supplier_invocation_observed": True,
                    "supplier_invocation_count_claimed": 1,
                    "independent_single_invocation_proof": False,
                },
            },
        )

    @classmethod
    def _validate_payload(cls, value: object) -> None:
        payload = _record_path_payload(
            value,
            expected={
                "claim_binding",
                "supplier_identity_binding",
                "supplier_id",
                "seeds",
                "predecessor_inventory_binding",
                "predecessor_seed_values",
                "observations",
            },
            label="official seed inventory payload",
        )
        _binding(
            payload["claim_binding"],
            role=D7V1ExclusiveSeedSupplyClaim.artifact_role,
            label="seed claim binding",
        )
        _binding(
            payload["supplier_identity_binding"],
            role="supplier-identity",
            label="supplier identity binding",
        )
        _binding(
            payload["predecessor_inventory_binding"],
            role="historical-predecessor-seed-inventory",
            label="predecessor inventory binding",
        )
        require_slug(payload["supplier_id"], label="supplier_id")
        seeds = _seed_values(payload["seeds"], label="seeds", nonempty=True)
        predecessor = _seed_values(
            payload["predecessor_seed_values"],
            label="predecessor_seed_values",
            nonempty=True,
        )
        if set(seeds) & set(predecessor):
            raise QualificationContractError(
                "successor seeds overlap the declared predecessor inventory"
            )
        observations = _mapping(payload["observations"], label="supplier observations")
        _exact_keys(
            observations,
            {
                "supplier_invocation_observed",
                "supplier_invocation_count_claimed",
                "independent_single_invocation_proof",
            },
            label="supplier observations",
        )
        _true(
            observations["supplier_invocation_observed"],
            label="supplier_invocation_observed",
        )
        if observations["supplier_invocation_count_claimed"] != 1:
            raise QualificationContractError(
                "supplier_invocation_count_claimed must be exactly one"
            )
        _false(
            observations["independent_single_invocation_proof"],
            label="independent_single_invocation_proof",
        )


_DESIGN_INVENTORY_ROLES = {
    "family_binding": "confirmation-family",
    "admission_binding": "family-admission",
    "protocol_binding": "confirmation-protocol",
    "source_graph_binding": "source-graph",
    "inventory_binding": D7V1OfficialSeedInventory.artifact_role,
    "graph_case_stress_aggregation_binding": "graph-case-stress-aggregation",
    "lifecycle_binding": "lifecycle",
}

_REPLAY_TRANSITIVE_ROLES = {
    "route_binding": "navigation-route",
    "materialization_protocol_binding": "v1-materialization-protocol",
    "c1_binding": D7V1C1SourceSetRecord.artifact_role,
    "c2_binding": D7V1C2SourceClosureReceipt.artifact_role,
    "seed_claim_binding": D7V1ExclusiveSeedSupplyClaim.artifact_role,
    "seed_inventory_binding": D7V1OfficialSeedInventory.artifact_role,
    "historical_plan_binding": "historical-post-d6-plan",
    "parent_protocol_binding": "parent-protocol",
    "parent_result_binding": "parent-result",
    "parent_manifest_binding": "parent-manifest",
    "parent_consumption_binding": "parent-consumption",
    "parent_d6_decision_binding": "parent-d6-decision",
    "embedded_full_design_binding": "embedded-full-design",
}


class D7V1EmbeddedFullDesign(_FactoryCanonicalBytes):
    """One canonical embedded subdocument, not a persisted record wrapper."""

    __slots__ = ()

    schema_version = D7_V1_EMBEDDED_FULL_DESIGN_SCHEMA_VERSION
    artifact_role = "embedded-full-design"
    typestate = (
        ("required_inventory_slots_populated", True),
        ("external_bindings_authenticated", False),
    )

    @classmethod
    def create(
        cls,
        *,
        design_id: str,
        family_binding: D7V1ArtifactBinding,
        admission_binding: D7V1ArtifactBinding,
        protocol_binding: D7V1ArtifactBinding,
        source_graph_binding: D7V1ArtifactBinding,
        inventory_binding: D7V1ArtifactBinding,
        graph_case_stress_aggregation_binding: D7V1ArtifactBinding,
        lifecycle_binding: D7V1ArtifactBinding,
    ) -> Self:
        inventory = {
            "schema_version": D7_V1_FULL_DESIGN_INVENTORY_SCHEMA_VERSION,
            "family_binding": family_binding.to_dict(),
            "admission_binding": admission_binding.to_dict(),
            "protocol_binding": protocol_binding.to_dict(),
            "source_graph_binding": source_graph_binding.to_dict(),
            "inventory_binding": inventory_binding.to_dict(),
            "graph_case_stress_aggregation_binding": (
                graph_case_stress_aggregation_binding.to_dict()
            ),
            "lifecycle_binding": lifecycle_binding.to_dict(),
        }
        return cls.from_dict(
            {
                "schema_version": cls.schema_version,
                "design_id": design_id,
                "inventory": inventory,
                "typestate": dict(cls.typestate),
                "claim_boundary": dict(_CLAIM_BOUNDARY),
            }
        )

    @classmethod
    def _validate_document(cls, value: object) -> dict[str, object]:
        document = _mapping(value, label="embedded full design")
        _exact_keys(
            document,
            {
                "schema_version",
                "design_id",
                "inventory",
                "typestate",
                "claim_boundary",
            },
            label="embedded full design",
        )
        if document["schema_version"] != cls.schema_version:
            raise QualificationContractError("embedded full-design schema differs")
        require_slug(document["design_id"], label="design_id")
        inventory = _mapping(document["inventory"], label="full-design inventory")
        _exact_keys(
            inventory,
            set(_DESIGN_INVENTORY_ROLES) | {"schema_version"},
            label="full-design inventory",
        )
        if inventory["schema_version"] != D7_V1_FULL_DESIGN_INVENTORY_SCHEMA_VERSION:
            raise QualificationContractError("full-design inventory schema differs")
        for key, role in _DESIGN_INVENTORY_ROLES.items():
            _binding(inventory[key], role=role, label=key)
        state = _mapping(document["typestate"], label="embedded full-design typestate")
        expected_state = dict(cls.typestate)
        _exact_keys(state, set(expected_state), label="embedded full-design typestate")
        if state != expected_state:
            raise QualificationContractError("embedded full-design typestate differs")
        _validate_claim_boundary(document["claim_boundary"])
        return document

    @property
    def embedded_payload(self) -> dict[str, object]:
        return self.to_dict()

    @classmethod
    def validate_embedded_payload(cls, value: object) -> dict[str, object]:
        return cls._validate_document(value)

    @property
    def inventory(self) -> dict[str, object]:
        return _mapping(self.to_dict()["inventory"], label="full-design inventory")


class D7V1ReplayTarget(_D7V1CanonicalRecord):
    """Replay target with payload-root JSON pointers for the embedded design."""

    __slots__ = ()

    schema_version = D7_V1_REPLAY_TARGET_SCHEMA_VERSION
    artifact_role = "replay-target"
    typestate = (
        ("complete_design_embedded", True),
        ("external_bindings_authenticated", False),
    )

    @classmethod
    def create(
        cls,
        *,
        record_id: str,
        repository_path: str,
        official_seed_inventory_binding: D7V1ArtifactBinding,
        full_design: D7V1EmbeddedFullDesign,
        transitive_bindings: Mapping[str, D7V1ArtifactBinding],
    ) -> Self:
        if not isinstance(full_design, D7V1EmbeddedFullDesign):
            raise TypeError("full_design must be D7V1EmbeddedFullDesign")
        embedded = full_design.embedded_payload
        inventory = _mapping(embedded["inventory"], label="full-design inventory")
        embedded_source = canonical_json_bytes(embedded)
        embedded_binding = D7V1ArtifactBinding(
            artifact_role=D7V1EmbeddedFullDesign.artifact_role,
            artifact_contract_id=D7V1EmbeddedFullDesign.schema_version,
            canonical_sha256=sha256_bytes(embedded_source),
            byte_count=len(embedded_source),
        )
        expected_caller_keys = set(_REPLAY_TRANSITIVE_ROLES) - {
            "embedded_full_design_binding"
        }
        if set(transitive_bindings) != expected_caller_keys or any(
            not isinstance(binding, D7V1ArtifactBinding)
            for binding in transitive_bindings.values()
        ):
            raise QualificationContractError(
                "transitive_bindings must provide the exact non-design lineage"
            )
        closed_transitive = dict(transitive_bindings)
        closed_transitive["embedded_full_design_binding"] = embedded_binding
        document = {
            "schema_version": cls.schema_version,
            "record_id": record_id,
            "artifact_role": cls.artifact_role,
            "successor_lineage_id": D7_V1_SUCCESSOR_LINEAGE_ID,
            "repository_path": repository_path,
            "official_seed_inventory_binding": (
                official_seed_inventory_binding.to_dict()
            ),
            "embedded_full_design_binding": embedded_binding.to_dict(),
            "transitive_bindings": {
                key: closed_transitive[key].to_dict()
                for key in _REPLAY_TRANSITIVE_ROLES
            },
            "full_design": embedded,
            "full_design_binding": D7V1JsonPointerBinding.from_subdocument(
                embedded,
                json_pointer="/full_design",
                target_schema_version=D7V1EmbeddedFullDesign.schema_version,
            ).to_dict(),
            "full_design_inventory_binding": (
                D7V1JsonPointerBinding.from_subdocument(
                    inventory,
                    json_pointer="/full_design/inventory",
                    target_schema_version=D7_V1_FULL_DESIGN_INVENTORY_SCHEMA_VERSION,
                ).to_dict()
            ),
            "typestate": dict(cls.typestate),
            "claim_boundary": dict(_CLAIM_BOUNDARY),
        }
        return cls.from_dict(document)

    @classmethod
    def _validate_payload(cls, value: object) -> None:
        del value
        raise QualificationContractError("replay target has no payload wrapper")

    @classmethod
    def _validate_document(cls, value: object) -> dict[str, object]:
        item = _mapping(value, label=cls.artifact_role)
        _exact_keys(
            item,
            {
                "schema_version",
                "record_id",
                "artifact_role",
                "successor_lineage_id",
                "repository_path",
                "official_seed_inventory_binding",
                "embedded_full_design_binding",
                "transitive_bindings",
                "full_design",
                "full_design_binding",
                "full_design_inventory_binding",
                "typestate",
                "claim_boundary",
            },
            label=cls.artifact_role,
        )
        if item["schema_version"] != cls.schema_version:
            raise QualificationContractError("replay-target schema differs")
        require_slug(item["record_id"], label="record_id")
        if item["artifact_role"] != cls.artifact_role:
            raise QualificationContractError("replay-target role differs")
        if item["successor_lineage_id"] != D7_V1_SUCCESSOR_LINEAGE_ID:
            raise QualificationContractError("successor lineage differs")
        _relative_repository_path(item["repository_path"], label="repository_path")
        official = _binding(
            item["official_seed_inventory_binding"],
            role=D7V1OfficialSeedInventory.artifact_role,
            label="official seed inventory binding",
        )
        embedded = D7V1EmbeddedFullDesign.validate_embedded_payload(item["full_design"])
        embedded_source = canonical_json_bytes(embedded)
        embedded_binding = _binding(
            item["embedded_full_design_binding"],
            role=D7V1EmbeddedFullDesign.artifact_role,
            label="embedded full-design artifact binding",
        )
        if (
            embedded_binding.artifact_contract_id
            != D7V1EmbeddedFullDesign.schema_version
            or embedded_binding.canonical_sha256 != sha256_bytes(embedded_source)
            or embedded_binding.byte_count != len(embedded_source)
        ):
            raise QualificationContractError(
                "embedded full-design artifact binding differs from the subdocument"
            )
        inventory = _mapping(embedded["inventory"], label="full-design inventory")
        design_inventory = _binding(
            inventory["inventory_binding"],
            role=D7V1OfficialSeedInventory.artifact_role,
            label="embedded official seed inventory binding",
        )
        if design_inventory != official:
            raise QualificationContractError(
                "replay target and embedded design bind different seed inventories"
            )
        transitive = _mapping(
            item["transitive_bindings"], label="replay transitive bindings"
        )
        _exact_keys(
            transitive,
            set(_REPLAY_TRANSITIVE_ROLES),
            label="replay transitive bindings",
        )
        validated_transitive = {
            key: _binding(transitive[key], role=role, label=key)
            for key, role in _REPLAY_TRANSITIVE_ROLES.items()
        }
        if validated_transitive["seed_inventory_binding"] != official:
            raise QualificationContractError(
                "replay transitive inventory differs from the direct inventory"
            )
        if validated_transitive["embedded_full_design_binding"] != embedded_binding:
            raise QualificationContractError(
                "replay transitive design differs from the direct embedded design"
            )
        _pointer_binding(
            item["full_design_binding"],
            pointer="/full_design",
            schema_version=D7V1EmbeddedFullDesign.schema_version,
            subdocument=embedded,
            label="full-design pointer binding",
        )
        _pointer_binding(
            item["full_design_inventory_binding"],
            pointer="/full_design/inventory",
            schema_version=D7_V1_FULL_DESIGN_INVENTORY_SCHEMA_VERSION,
            subdocument=inventory,
            label="full-design inventory pointer binding",
        )
        state = _mapping(item["typestate"], label="typestate")
        expected_state = dict(cls.typestate)
        _exact_keys(state, set(expected_state), label="typestate")
        if state != expected_state:
            raise QualificationContractError("replay-target typestate differs")
        _validate_claim_boundary(item["claim_boundary"])
        return item


class D7V1FullDesignFreeze(_D7V1CanonicalRecord):
    __slots__ = ()

    schema_version = D7_V1_FULL_DESIGN_FREEZE_SCHEMA_VERSION
    artifact_role = "full-design-freeze"
    typestate = (
        ("full_design_frozen", True),
        ("execution_started", False),
    )

    @classmethod
    def create(
        cls,
        *,
        record_id: str,
        repository_path: str,
        replay_target_binding: D7V1ArtifactBinding,
        full_design_binding: D7V1JsonPointerBinding,
        reviewed_source_commit: str,
    ) -> Self:
        return cls._create(
            record_id=record_id,
            payload={
                "repository_path": repository_path,
                "replay_target_binding": replay_target_binding.to_dict(),
                "full_design_binding": full_design_binding.to_dict(),
                "reviewed_source_commit": reviewed_source_commit,
            },
        )

    @classmethod
    def _validate_payload(cls, value: object) -> None:
        payload = _record_path_payload(
            value,
            expected={
                "replay_target_binding",
                "full_design_binding",
                "reviewed_source_commit",
            },
            label="full-design freeze payload",
        )
        _binding(
            payload["replay_target_binding"],
            role=D7V1ReplayTarget.artifact_role,
            label="replay target binding",
        )
        pointer = D7V1JsonPointerBinding.from_dict(payload["full_design_binding"])
        if (
            pointer.json_pointer != "/full_design"
            or pointer.target_schema_version != D7V1EmbeddedFullDesign.schema_version
        ):
            raise QualificationContractError("freeze full-design pointer differs")
        _commit(payload["reviewed_source_commit"], label="reviewed_source_commit")


class D7V1LaunchIntent(_D7V1CanonicalRecord):
    __slots__ = ()

    schema_version = D7_V1_LAUNCH_INTENT_SCHEMA_VERSION
    artifact_role = "launch-intent"
    typestate = (
        ("launch_intent_persisted", True),
        ("execution_authorized", False),
        ("execution_started", False),
    )

    @classmethod
    def create(
        cls,
        *,
        record_id: str,
        repository_path: str,
        replay_target_binding: D7V1ArtifactBinding,
        full_design_freeze_binding: D7V1ArtifactBinding,
        external_store_path: str,
        external_staging_path: str,
        runner_script: str,
        official_callable: str,
    ) -> Self:
        return cls._create(
            record_id=record_id,
            payload={
                "repository_path": repository_path,
                "replay_target_binding": replay_target_binding.to_dict(),
                "full_design_freeze_binding": (full_design_freeze_binding.to_dict()),
                "external_store_path": external_store_path,
                "external_staging_path": external_staging_path,
                "runner_script": runner_script,
                "official_callable": official_callable,
            },
        )

    @classmethod
    def _validate_payload(cls, value: object) -> None:
        payload = _record_path_payload(
            value,
            expected={
                "replay_target_binding",
                "full_design_freeze_binding",
                "external_store_path",
                "external_staging_path",
                "runner_script",
                "official_callable",
            },
            label="launch intent payload",
        )
        _binding(
            payload["replay_target_binding"],
            role=D7V1ReplayTarget.artifact_role,
            label="replay target binding",
        )
        _binding(
            payload["full_design_freeze_binding"],
            role=D7V1FullDesignFreeze.artifact_role,
            label="full-design freeze binding",
        )
        store = _absolute_posix_path(
            payload["external_store_path"], label="external_store_path"
        )
        staging = _absolute_posix_path(
            payload["external_staging_path"], label="external_staging_path"
        )
        if store == staging:
            raise QualificationContractError("store and staging paths must differ")
        _relative_repository_path(payload["runner_script"], label="runner_script")
        _string(payload["official_callable"], label="official_callable")


class D7V1OfficialExecutionAttemptReservation(_D7V1CanonicalRecord):
    __slots__ = ()

    schema_version = D7_V1_ATTEMPT_RESERVATION_SCHEMA_VERSION
    artifact_role = "official-execution-attempt-reservation"
    typestate = (
        ("attempt_state", "reserved_not_started"),
        ("execution_started", False),
        ("retry", False),
        ("exclusive_no_replace", True),
    )

    @classmethod
    def create(
        cls,
        *,
        record_id: str,
        repository_path: str,
        launch_intent: D7V1LaunchIntent,
        replay_target: D7V1ReplayTarget,
        seed_claim: D7V1ExclusiveSeedSupplyClaim,
        external_attempt_path: str,
        external_store_path: str,
        reviewed_source_commit: str,
    ) -> Self:
        if not isinstance(launch_intent, D7V1LaunchIntent):
            raise TypeError("launch_intent must be D7V1LaunchIntent")
        if not isinstance(replay_target, D7V1ReplayTarget):
            raise TypeError("replay_target must be D7V1ReplayTarget")
        if not isinstance(seed_claim, D7V1ExclusiveSeedSupplyClaim):
            raise TypeError("seed_claim must be D7V1ExclusiveSeedSupplyClaim")
        derivation = {
            "domain": D7_V1_ATTEMPT_KEY_DOMAIN,
            "external_attempt_path": external_attempt_path,
            "launch_intent_sha256": launch_intent.canonical_sha256,
            "replay_target_sha256": replay_target.canonical_sha256,
            "reviewed_source_commit": reviewed_source_commit,
            "seed_claim_sha256": seed_claim.canonical_sha256,
        }
        return cls._create(
            record_id=record_id,
            payload={
                "repository_path": repository_path,
                "launch_intent_binding": D7V1ArtifactBinding.from_record(
                    launch_intent
                ).to_dict(),
                "replay_target_binding": D7V1ArtifactBinding.from_record(
                    replay_target
                ).to_dict(),
                "seed_claim_binding": D7V1ArtifactBinding.from_record(
                    seed_claim
                ).to_dict(),
                "attempt_key_derivation": derivation,
                "attempt_key_sha256": sha256_bytes(canonical_json_bytes(derivation)),
                "external_store_path": external_store_path,
            },
        )

    @classmethod
    def _validate_payload(cls, value: object) -> None:
        payload = _record_path_payload(
            value,
            expected={
                "launch_intent_binding",
                "replay_target_binding",
                "seed_claim_binding",
                "attempt_key_derivation",
                "attempt_key_sha256",
                "external_store_path",
            },
            label="attempt reservation payload",
        )
        launch_binding = _binding(
            payload["launch_intent_binding"],
            role=D7V1LaunchIntent.artifact_role,
            label="launch intent binding",
        )
        replay_binding = _binding(
            payload["replay_target_binding"],
            role=D7V1ReplayTarget.artifact_role,
            label="replay target binding",
        )
        claim_binding = _binding(
            payload["seed_claim_binding"],
            role=D7V1ExclusiveSeedSupplyClaim.artifact_role,
            label="seed claim binding",
        )
        derivation = _mapping(
            payload["attempt_key_derivation"], label="attempt-key derivation"
        )
        _exact_keys(
            derivation,
            {
                "domain",
                "external_attempt_path",
                "launch_intent_sha256",
                "replay_target_sha256",
                "reviewed_source_commit",
                "seed_claim_sha256",
            },
            label="attempt-key derivation",
        )
        if derivation["domain"] != D7_V1_ATTEMPT_KEY_DOMAIN:
            raise QualificationContractError("attempt-key derivation domain differs")
        _absolute_posix_path(
            derivation["external_attempt_path"], label="external_attempt_path"
        )
        digest_joins = (
            ("launch_intent_sha256", launch_binding.canonical_sha256),
            ("replay_target_sha256", replay_binding.canonical_sha256),
            ("seed_claim_sha256", claim_binding.canonical_sha256),
        )
        for field, expected_digest in digest_joins:
            if require_sha256(derivation[field], label=field) != expected_digest:
                raise QualificationContractError(f"attempt-key {field} differs")
        _commit(
            derivation["reviewed_source_commit"],
            label="reviewed_source_commit",
        )
        expected = sha256_bytes(canonical_json_bytes(derivation))
        if (
            require_sha256(payload["attempt_key_sha256"], label="attempt_key_sha256")
            != expected
        ):
            raise QualificationContractError("attempt_key_sha256 derivation differs")
        _absolute_posix_path(
            payload["external_store_path"], label="external_store_path"
        )


class D7V1PreItem23ChronologyReceipt(_D7V1CanonicalRecord):
    """Closed pre-item23 chronology without a recursive self digest."""

    __slots__ = ()

    schema_version = D7_V1_PRE_ITEM23_RECEIPT_SCHEMA_VERSION
    artifact_role = "pre-item23-chronology-receipt"
    typestate = (
        ("pre_item23_receipt_formed", True),
        ("predecessor_binding_slots_complete", True),
        ("descriptive_result_namespace_absence_observed", True),
        ("external_predecessor_bytes_authenticated", False),
        ("atomic_publication_authenticated", False),
        ("artifact_commit_authenticated", False),
        ("item23_values_accessed", False),
    )

    @classmethod
    def create(
        cls,
        *,
        record_id: str,
        repository_path: str,
        predecessor_bindings: Mapping[str, D7V1ArtifactBinding],
        pre_item23_file_inventory: Mapping[str, str],
        descriptive_result_namespace_absence: D7V1NamespaceAbsenceObservation,
    ) -> Self:
        if not isinstance(
            descriptive_result_namespace_absence,
            D7V1NamespaceAbsenceObservation,
        ):
            raise TypeError(
                "descriptive_result_namespace_absence must be "
                "D7V1NamespaceAbsenceObservation"
            )
        predecessor_roles = set(_PRE_ITEM23_FILE_ROLES) - {cls.artifact_role}
        if set(predecessor_bindings) != predecessor_roles or any(
            not isinstance(binding, D7V1ArtifactBinding)
            for binding in predecessor_bindings.values()
        ):
            raise QualificationContractError(
                "predecessor_bindings must contain the exact eight predecessor roles"
            )
        if set(pre_item23_file_inventory) != set(_PRE_ITEM23_FILE_ROLES):
            raise QualificationContractError(
                "pre_item23_file_inventory must contain the exact nine roles"
            )
        predecessor_files = {
            role: D7V1RepositoryArtifactBinding(
                repository_path=pre_item23_file_inventory[role],
                artifact_binding=predecessor_bindings[role],
            ).to_dict()
            for role in _PRE_ITEM23_FILE_ROLES
            if role != cls.artifact_role
        }
        return cls._create(
            record_id=record_id,
            payload={
                "repository_path": repository_path,
                "predecessor_files": predecessor_files,
                "pre_item23_file_inventory": dict(pre_item23_file_inventory),
                "descriptive_result_namespace_absence": (
                    descriptive_result_namespace_absence.to_dict()
                ),
            },
        )

    @classmethod
    def _validate_payload(cls, value: object) -> None:
        payload = _record_path_payload(
            value,
            expected={
                "predecessor_files",
                "pre_item23_file_inventory",
                "descriptive_result_namespace_absence",
            },
            label="pre-item23 chronology receipt payload",
        )
        inventory = _mapping(
            payload["pre_item23_file_inventory"],
            label="pre-item23 file inventory",
        )
        _exact_keys(
            inventory,
            set(_PRE_ITEM23_FILE_ROLES),
            label="pre-item23 file inventory",
        )
        normalized_paths = tuple(
            _relative_repository_path(inventory[role], label=f"{role} path")
            for role in _PRE_ITEM23_FILE_ROLES
        )
        if len(set(normalized_paths)) != len(normalized_paths):
            raise QualificationContractError(
                "pre-item23 file inventory paths must be unique"
            )
        if inventory[cls.artifact_role] != payload["repository_path"]:
            raise QualificationContractError(
                "receipt path differs from its nine-member file inventory"
            )
        predecessor_files = _mapping(
            payload["predecessor_files"], label="predecessor files"
        )
        predecessor_roles = set(_PRE_ITEM23_FILE_ROLES) - {cls.artifact_role}
        _exact_keys(
            predecessor_files,
            predecessor_roles,
            label="predecessor files",
        )
        for role in _PRE_ITEM23_FILE_ROLES:
            if role == cls.artifact_role:
                continue
            joined = D7V1RepositoryArtifactBinding.from_dict(predecessor_files[role])
            _binding(joined.artifact_binding.to_dict(), role=role, label=role)
            if joined.repository_path != inventory[role]:
                raise QualificationContractError(
                    f"{role} path differs between binding and inventory"
                )
        absence = D7V1NamespaceAbsenceObservation.from_dict(
            payload["descriptive_result_namespace_absence"]
        )
        if absence.repository_path in set(normalized_paths):
            raise QualificationContractError(
                "descriptive result path must be outside the pre-item23 inventory"
            )


_POSTSELECTION_STATUSES = {
    "complete",
    "insufficient",
    "failed",
    "invalid_protocol",
}

_DESCRIPTIVE_READ_TRACE_ROLES = (
    "historical-post-d6-plan",
    "parent-protocol",
    "parent-result",
    "parent-manifest",
    "parent-consumption",
    "parent-d6-decision",
)

_POST_D6_OUTPUT_IDS = (
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
_POST_D6_OUTPUT_ROLES = tuple(
    f"post-d6-output-{output_id}" for output_id in _POST_D6_OUTPUT_IDS
)
_DESCRIPTIVE_OUTPUT_STATUSES = {"available", "blocked"}


class D7V1DescriptiveOutput(_FactoryCanonicalBytes):
    """Canonical embedded output; it is not a separately persisted artifact."""

    __slots__ = ()

    schema_version = D7_V1_DESCRIPTIVE_OUTPUT_SCHEMA_VERSION
    artifact_role = "descriptive-output"

    @classmethod
    def create(
        cls,
        *,
        output_id: str,
        status: str,
        data: Mapping[str, object],
    ) -> Self:
        return cls.from_dict(
            {
                "schema_version": cls.schema_version,
                "output_id": output_id,
                "status": status,
                "data": dict(data),
                "claim_boundary": dict(_CLAIM_BOUNDARY),
            }
        )

    @classmethod
    def _validate_document(cls, value: object) -> dict[str, object]:
        document = _mapping(value, label="descriptive output")
        _exact_keys(
            document,
            {"schema_version", "output_id", "status", "data", "claim_boundary"},
            label="descriptive output",
        )
        if document["schema_version"] != cls.schema_version:
            raise QualificationContractError("descriptive output schema differs")
        output_id = _string(document["output_id"], label="output_id")
        if output_id not in _POST_D6_OUTPUT_IDS:
            raise QualificationContractError("descriptive output_id is not closed")
        status = _string(document["status"], label="descriptive output status")
        if status not in _DESCRIPTIVE_OUTPUT_STATUSES:
            raise QualificationContractError("descriptive output status is not closed")
        _canonical_subdocument(document["data"], label="descriptive output data")
        _validate_claim_boundary(document["claim_boundary"])
        return document

    @property
    def output_id(self) -> str:
        return _string(self.to_dict()["output_id"], label="output_id")


def _descriptive_output_binding(
    output: D7V1DescriptiveOutput,
) -> D7V1JsonPointerBinding:
    return D7V1JsonPointerBinding.from_subdocument(
        output.to_dict(),
        json_pointer=f"/payload/outputs/{output.output_id}",
        target_schema_version=D7V1DescriptiveOutput.schema_version,
    )


class D7V1PostselectionDescriptiveResult(_D7V1CanonicalRecord):
    __slots__ = ()

    schema_version = D7_V1_POSTSELECTION_RESULT_SCHEMA_VERSION
    artifact_role = "postselection-descriptive-result"
    max_record_bytes = D7_V1_POSTSELECTION_RESULT_MAX_RECORD_BYTES
    typestate = (
        ("postselection_record_formed", True),
        ("scientific_result_issued", False),
    )

    @classmethod
    def create(
        cls,
        *,
        record_id: str,
        repository_path: str,
        parent_binding: D7V1ArtifactBinding,
        chronology_receipt_binding: D7V1ArtifactBinding,
        read_trace: Sequence[D7V1ReadTraceEntry],
        status: str,
        outputs: Sequence[D7V1DescriptiveOutput],
    ) -> Self:
        if any(not isinstance(output, D7V1DescriptiveOutput) for output in outputs):
            raise TypeError("outputs must contain D7V1DescriptiveOutput values")
        output_documents = {output.output_id: output.to_dict() for output in outputs}
        if len(output_documents) != len(outputs):
            raise QualificationContractError("outputs must have unique output_ids")
        return cls._create(
            record_id=record_id,
            payload={
                "repository_path": repository_path,
                "parent_binding": parent_binding.to_dict(),
                "chronology_receipt_binding": chronology_receipt_binding.to_dict(),
                "read_trace": [entry.to_dict() for entry in read_trace],
                "status": status,
                "outputs": output_documents,
                "output_bindings": {
                    output.output_id: _descriptive_output_binding(output).to_dict()
                    for output in outputs
                },
                "observations": {
                    "read_trace_recorded": True,
                    "any_input_read": bool(read_trace),
                    "status_recorded": True,
                },
            },
        )

    @classmethod
    def _validate_payload(cls, value: object) -> None:
        payload = _record_path_payload(
            value,
            expected={
                "parent_binding",
                "chronology_receipt_binding",
                "read_trace",
                "status",
                "outputs",
                "output_bindings",
                "observations",
            },
            label="postselection descriptive result payload",
        )
        _binding(
            payload["parent_binding"],
            role=D7V1OfficialExecutionAttemptReservation.artifact_role,
            label="parent binding",
        )
        _binding(
            payload["chronology_receipt_binding"],
            role=D7V1PreItem23ChronologyReceipt.artifact_role,
            label="chronology receipt binding",
        )
        status = _string(payload["status"], label="status")
        if status not in _POSTSELECTION_STATUSES:
            raise QualificationContractError("postselection status is not closed")
        trace_items = _sequence(payload["read_trace"], label="read_trace")
        trace = tuple(D7V1ReadTraceEntry.from_dict(item) for item in trace_items)
        if tuple(entry.sequence for entry in trace) != tuple(range(1, len(trace) + 1)):
            raise QualificationContractError(
                "read_trace sequences must be contiguous from one"
            )
        if len({entry.artifact_binding.canonical_sha256 for entry in trace}) != len(
            trace
        ):
            raise QualificationContractError("read_trace bindings must be unique")
        trace_roles = tuple(entry.artifact_binding.artifact_role for entry in trace)
        if trace_roles != _DESCRIPTIVE_READ_TRACE_ROLES[: len(trace_roles)]:
            raise QualificationContractError(
                "read_trace must be an ordered prefix of the six allowed roles"
            )
        if status in {"complete", "insufficient"} and (
            trace_roles != _DESCRIPTIVE_READ_TRACE_ROLES
        ):
            raise QualificationContractError(
                "complete and insufficient results require the exact six-input trace"
            )
        output_items = _mapping(payload["outputs"], label="outputs")
        outputs = {
            output_id: D7V1DescriptiveOutput.from_dict(item)
            for output_id, item in output_items.items()
        }
        output_ids = set(outputs)
        if not output_ids <= set(_POST_D6_OUTPUT_IDS):
            raise QualificationContractError("outputs contain a forbidden output_id")
        if any(output_id != output.output_id for output_id, output in outputs.items()):
            raise QualificationContractError(
                "embedded output_id must equal its outputs map key"
            )
        if status in {"complete", "insufficient"} and output_ids != set(
            _POST_D6_OUTPUT_IDS
        ):
            raise QualificationContractError(
                "complete and insufficient results require all 27 outputs"
            )
        binding_items = _mapping(payload["output_bindings"], label="output_bindings")
        bindings = {
            output_id: D7V1JsonPointerBinding.from_dict(item)
            for output_id, item in binding_items.items()
        }
        expected_bindings = {
            output_id: _descriptive_output_binding(output)
            for output_id, output in outputs.items()
        }
        if bindings != expected_bindings:
            raise QualificationContractError(
                "output_bindings must exactly bind the embedded output bytes"
            )
        observations = _mapping(payload["observations"], label="result observations")
        _exact_keys(
            observations,
            {"read_trace_recorded", "any_input_read", "status_recorded"},
            label="result observations",
        )
        _true(observations["read_trace_recorded"], label="read_trace_recorded")
        if observations["any_input_read"] is not bool(trace):
            raise QualificationContractError(
                "any_input_read must equal bool(read_trace)"
            )
        _true(observations["status_recorded"], label="status_recorded")
