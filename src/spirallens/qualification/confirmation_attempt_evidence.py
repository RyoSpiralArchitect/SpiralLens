"""Canonical evidence bytes referenced by the structural D7 attempt records.

These directly constructible values define byte shapes and local invariants
only.  They do not inspect a filesystem, authenticate an observer, verify an
abort, write a record, finalize an attempt, or confer D7/D8 authority.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from pathlib import PurePosixPath
from typing import ClassVar, Protocol, Self, TypeAlias

from spirallens.core.canonical import (
    CanonicalJsonError,
    canonical_json_bytes,
    canonical_json_sha256,
    parse_canonical_json,
    sha256_bytes,
)

from . import confirmation_attempt_records as r
from .common import QualificationContractError

__all__: tuple[str, ...] = ()

D7_AUTHORIZATION_PATH_ABSENCE_RECEIPT_SCHEMA_VERSION = (
    "spirallens.d7-authorization-path-absence-receipt.v0.1"
)
D7_PRE_START_PATH_ABSENCE_RECEIPT_SCHEMA_VERSION = (
    "spirallens.d7-pre-start-path-absence-receipt.v0.1"
)
D7_FAILURE_EVIDENCE_PAYLOAD_SCHEMA_VERSION = (
    "spirallens.d7-failure-evidence-payload.v0.1"
)
D7_EXTERNAL_ABORT_VERIFICATION_RECEIPT_SCHEMA_VERSION = (
    "spirallens.d7-external-abort-verification-receipt.v0.1"
)
D7_EXTERNAL_ABORT_WITNESS_STATEMENT_SCHEMA_VERSION = (
    "spirallens.d7-external-abort-witness-statement.v0.1"
)
D7_SIGNED_EXTERNAL_ABORT_WITNESS_ENVELOPE_SCHEMA_VERSION = (
    "spirallens.d7-signed-external-abort-witness-envelope.v0.1"
)
D7_EXTERNAL_WITNESS_RUNTIME_TRUST_ROOT_SCHEMA_VERSION = (
    "spirallens.d7-external-witness-runtime-trust-root.v0.1"
)

D7_AUTHORIZATION_PATH_ABSENCE_RECEIPT_CONTRACT_ID = (
    "spirallens.d7-authorization-path-absence-receipt-contract.v0.1"
)
D7_PRE_START_PATH_ABSENCE_RECEIPT_CONTRACT_ID = (
    "spirallens.d7-pre-start-path-absence-receipt-contract.v0.1"
)
D7_EXTERNAL_ABORT_VERIFIER_CONTRACT_ID = (
    "spirallens.d7-external-abort-verifier-contract.v0.1"
)
D7_EXTERNAL_ABORT_OBSERVER_SIGNATURE_CONTEXT = (
    "spirallens.d7-external-abort-observer-signature.v0.1"
)
D7_EXTERNAL_ABORT_VERIFIER_SIGNATURE_CONTEXT = (
    "spirallens.d7-external-abort-verifier-signature.v0.1"
)
D7_PATH_IDENTITY_SCHEME = "spirallens.d7-path-identity.v0.1"
D7_FAILURE_RECORD_SCOPE = "d7-spectral-moment-confirmation-attempt-failure-only"

MAX_D7_ATTEMPT_EVIDENCE_BYTES = 128 * 1024

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,127}$")
_PATH_LEAF_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,254}$")
_EXCEPTION_CLASS_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_.]{0,255}$")
_ED25519_SIGNATURE_RE = re.compile(r"^[0-9a-f]{128}$")


class D7AbsentPathSubject(str, Enum):
    OUTPUT_NAMESPACE = "output-namespace"
    TERMINAL_PATH = "terminal-path"


class D7ExternalAbortObservationKind(str, Enum):
    PROCESS_EXIT_WITHOUT_TERMINAL = "process-exit-without-terminal"
    HOST_RESTART_WITHOUT_TERMINAL = "host-restart-without-terminal"
    EXTERNAL_EXECUTOR_ABORT = "external-executor-abort"


class D7ExternalAbortVerificationMethod(str, Enum):
    EXECUTION_IDENTITY_AND_TERMINAL_INSPECTION = (
        "execution-identity-and-terminal-inspection-v0.1"
    )


def _mapping(value: object, label: str) -> dict[str, object]:
    if type(value) is not dict or any(type(key) is not str for key in value):
        raise QualificationContractError(f"{label} must be an exact JSON object")
    return dict(value)


def _exact_keys(
    value: dict[str, object], expected: set[str] | frozenset[str], label: str
) -> None:
    if set(value) != set(expected):
        raise QualificationContractError(f"{label} fields differ from the exact schema")


def _constant(value: object, expected: object, label: str) -> None:
    if type(value) is not type(expected) or value != expected:
        raise QualificationContractError(f"{label} must equal {expected!r}")


def _string(value: object, label: str) -> str:
    if type(value) is not str:
        raise QualificationContractError(f"{label} must be an exact string")
    return value


def _sha256(value: object, label: str) -> str:
    result = _string(value, label)
    if _SHA256_RE.fullmatch(result) is None:
        raise QualificationContractError(f"{label} must be a lowercase SHA-256")
    return result


def _ed25519_signature(value: object, label: str) -> str:
    result = _string(value, label)
    if _ED25519_SIGNATURE_RE.fullmatch(result) is None:
        raise QualificationContractError(
            f"{label} must be one lowercase 64-byte Ed25519 signature"
        )
    return result


def _commit(value: object, label: str) -> str:
    result = _string(value, label)
    if _COMMIT_RE.fullmatch(result) is None:
        raise QualificationContractError(f"{label} must be a lowercase Git commit")
    return result


def _slug(value: object, label: str) -> str:
    result = _string(value, label)
    if _SLUG_RE.fullmatch(result) is None:
        raise QualificationContractError(f"{label} must be a portable lowercase slug")
    return result


def _plain_int(value: object, label: str, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise QualificationContractError(
            f"{label} must be an exact integer at least {minimum}"
        )
    return value


def _enum(enum_type: type[Enum], value: object, label: str) -> Enum:
    raw = _string(value, label)
    try:
        return enum_type(raw)
    except ValueError as error:
        raise QualificationContractError(f"{label} is unsupported") from error


def _realpath(value: object, label: str) -> str:
    result = _string(value, label)
    path = PurePosixPath(result)
    if (
        not result.startswith("/")
        or (result != "/" and result.startswith("//"))
        or "\x00" in result
        or len(result.encode("utf-8")) > 4096
        or ".." in path.parts
        or str(path) != result
    ):
        raise QualificationContractError(
            f"{label} must be a normalized absolute POSIX realpath"
        )
    return result


def _basename(value: object, label: str) -> str:
    result = _string(value, label)
    if (
        not result
        or result in {".", ".."}
        or "/" in result
        or "\x00" in result
        or len(result.encode("utf-8")) > 255
        or _PATH_LEAF_RE.fullmatch(result) is None
    ):
        raise QualificationContractError(
            f"{label} must be one lowercase portable ASCII path leaf"
        )
    return result


def _subject_path(parent: str, basename: str) -> str:
    return str(PurePosixPath(parent) / basename)


def _path_is_within(root: str, parent: str) -> bool:
    root_path = PurePosixPath(root)
    parent_path = PurePosixPath(parent)
    return parent_path == root_path or root_path in parent_path.parents


def d7_path_identity_sha256(
    *,
    store_identity_sha256: str,
    resolved_parent_realpath: str,
    subject_basename: str,
) -> str:
    """Derive the frozen identity of one absent destination path."""

    store = _sha256(store_identity_sha256, "store_identity_sha256")
    parent = _realpath(resolved_parent_realpath, "resolved_parent_realpath")
    basename = _basename(subject_basename, "subject_basename")
    return canonical_json_sha256(
        {
            "scheme": D7_PATH_IDENTITY_SCHEME,
            "store_identity_sha256": store,
            "resolved_parent_realpath": parent,
            "subject_basename": basename,
        }
    )


def d7_external_witness_runtime_trust_root_sha256(
    *,
    execution_principal_id: str,
    execution_identity_receipt_sha256: str,
    observer_principal_id: str,
    observer_identity_receipt_sha256: str,
    observer_public_key_sha256: str,
    verifier_principal_id: str,
    verifier_source_runtime_receipt_sha256: str,
    verifier_public_key_sha256: str,
) -> str:
    """Hash one explicit runtime pin set without granting D7 authority."""

    execution_principal = _slug(execution_principal_id, "execution_principal_id")
    observer_principal = _slug(observer_principal_id, "observer_principal_id")
    verifier_principal = _slug(verifier_principal_id, "verifier_principal_id")
    if len({execution_principal, observer_principal, verifier_principal}) != 3:
        raise QualificationContractError(
            "execution, observer, and verifier principals must differ"
        )
    execution_identity = _sha256(
        execution_identity_receipt_sha256,
        "execution_identity_receipt_sha256",
    )
    observer_identity = _sha256(
        observer_identity_receipt_sha256,
        "observer_identity_receipt_sha256",
    )
    observer_key = _sha256(
        observer_public_key_sha256,
        "observer_public_key_sha256",
    )
    verifier_runtime = _sha256(
        verifier_source_runtime_receipt_sha256,
        "verifier_source_runtime_receipt_sha256",
    )
    verifier_key = _sha256(
        verifier_public_key_sha256,
        "verifier_public_key_sha256",
    )
    if len({execution_identity, observer_identity, verifier_runtime}) != 3:
        raise QualificationContractError(
            "execution, observer, and verifier receipts must differ"
        )
    if observer_key == verifier_key:
        raise QualificationContractError(
            "observer and verifier public keys must differ"
        )
    return canonical_json_sha256(
        {
            "schema_version": (D7_EXTERNAL_WITNESS_RUNTIME_TRUST_ROOT_SCHEMA_VERSION),
            "signature_algorithm": "ed25519",
            "execution_principal": {
                "principal_id": execution_principal,
                "identity_receipt_sha256": execution_identity,
            },
            "observer_principal": {
                "principal_id": observer_principal,
                "identity_receipt_sha256": observer_identity,
                "public_key_sha256": observer_key,
            },
            "verifier_principal": {
                "principal_id": verifier_principal,
                "source_runtime_receipt_sha256": verifier_runtime,
                "public_key_sha256": verifier_key,
            },
            "authenticated_principal_separation_required": True,
        }
    )


class _CanonicalEvidence:
    _LABEL: ClassVar[str] = "D7 attempt evidence"
    _MAX_BYTES: ClassVar[int] = MAX_D7_ATTEMPT_EVIDENCE_BYTES

    def to_dict(self) -> dict[str, object]:
        raise NotImplementedError

    @property
    def canonical_bytes(self) -> bytes:
        result = canonical_json_bytes(self.to_dict())
        if not result or len(result) > self._MAX_BYTES:
            raise QualificationContractError(f"{self._LABEL} exceeds its byte cap")
        return result

    @property
    def canonical_sha256(self) -> str:
        return sha256_bytes(self.canonical_bytes)

    @classmethod
    def from_dict(cls, value: object) -> Self:
        raise NotImplementedError

    @classmethod
    def from_canonical_bytes(cls, source: bytes, *, expected_sha256: str) -> Self:
        expected = _sha256(expected_sha256, "expected_sha256")
        if type(source) is not bytes or not source or len(source) > cls._MAX_BYTES:
            raise QualificationContractError(f"{cls._LABEL} bytes exceed the cap")
        if sha256_bytes(source) != expected:
            raise QualificationContractError(f"{cls._LABEL} SHA-256 differs")
        try:
            document = parse_canonical_json(source, label=cls._LABEL)
        except CanonicalJsonError as error:
            raise QualificationContractError(str(error)) from error
        result = cls.from_dict(document)
        if result.canonical_bytes != source:
            raise QualificationContractError(
                f"{cls._LABEL} differs from reconstructed canonical bytes"
            )
        return result


class _PathAbsenceReceipt(Protocol):
    subject_kind: D7AbsentPathSubject
    replay_target_sha256: str
    attempt_key_sha256: str
    attempt_declaration_sha256: str
    authorization_commit: str
    execution_identity_receipt_sha256: str
    store_identity_sha256: str
    subject_path_identity_sha256: str
    store_root_realpath: str
    resolved_parent_realpath: str
    subject_basename: str
    parent_device: int
    parent_inode: int


_PATH_COMMON_KEYS = frozenset(
    {
        "subject_kind",
        "replay_target_sha256",
        "attempt_key_sha256",
        "attempt_declaration_sha256",
        "authorization_commit",
        "execution_identity_receipt_sha256",
        "store_identity_sha256",
        "subject_path_identity_sha256",
        "store_root_realpath",
        "resolved_parent_realpath",
        "subject_basename",
        "parent_device",
        "parent_inode",
    }
)
_PATH_OBSERVATION_CONSTANTS = {
    "observation_method": "descriptor-relative-parent-lstat-no-follow-v0.1",
    "directory_entry_absent": True,
    "symlink_ancestors_rejected": True,
    "absence_is_point_in_time_observation": True,
    "reservation_acquired": False,
    "cryptographic_absence_proof": False,
    "hostile_mutation_resistance_proved": False,
}


def _validate_path_absence_receipt(value: _PathAbsenceReceipt) -> None:
    if type(value.subject_kind) is not D7AbsentPathSubject:
        raise TypeError("subject_kind must be an exact D7AbsentPathSubject")
    for name in (
        "replay_target_sha256",
        "attempt_key_sha256",
        "attempt_declaration_sha256",
        "execution_identity_receipt_sha256",
        "store_identity_sha256",
        "subject_path_identity_sha256",
    ):
        _sha256(getattr(value, name), name)
    _commit(value.authorization_commit, "authorization_commit")
    root = _realpath(value.store_root_realpath, "store_root_realpath")
    parent = _realpath(value.resolved_parent_realpath, "resolved_parent_realpath")
    basename = _basename(value.subject_basename, "subject_basename")
    _plain_int(value.parent_device, "parent_device")
    _plain_int(value.parent_inode, "parent_inode", 1)
    if not _path_is_within(root, parent):
        raise QualificationContractError(
            "resolved parent must remain within the store root"
        )
    expected = d7_path_identity_sha256(
        store_identity_sha256=value.store_identity_sha256,
        resolved_parent_realpath=parent,
        subject_basename=basename,
    )
    if value.subject_path_identity_sha256 != expected:
        raise QualificationContractError(
            "subject_path_identity_sha256 differs from the canonical path identity"
        )


def _path_common_document(value: _PathAbsenceReceipt) -> dict[str, object]:
    return {
        "subject_kind": value.subject_kind.value,
        "replay_target_sha256": value.replay_target_sha256,
        "attempt_key_sha256": value.attempt_key_sha256,
        "attempt_declaration_sha256": value.attempt_declaration_sha256,
        "authorization_commit": value.authorization_commit,
        "execution_identity_receipt_sha256": (value.execution_identity_receipt_sha256),
        "store_identity_sha256": value.store_identity_sha256,
        "subject_path_identity_sha256": value.subject_path_identity_sha256,
        "store_root_realpath": value.store_root_realpath,
        "resolved_parent_realpath": value.resolved_parent_realpath,
        "subject_basename": value.subject_basename,
        "parent_device": value.parent_device,
        "parent_inode": value.parent_inode,
        **_PATH_OBSERVATION_CONSTANTS,
    }


def _decode_path_common(
    document: dict[str, object], *, label: str
) -> dict[str, object]:
    for name, expected in _PATH_OBSERVATION_CONSTANTS.items():
        _constant(document[name], expected, f"{label} {name}")
    return {
        "subject_kind": _enum(
            D7AbsentPathSubject, document["subject_kind"], "subject_kind"
        ),
        "replay_target_sha256": _sha256(
            document["replay_target_sha256"], "replay_target_sha256"
        ),
        "attempt_key_sha256": _sha256(
            document["attempt_key_sha256"], "attempt_key_sha256"
        ),
        "attempt_declaration_sha256": _sha256(
            document["attempt_declaration_sha256"],
            "attempt_declaration_sha256",
        ),
        "authorization_commit": _commit(
            document["authorization_commit"], "authorization_commit"
        ),
        "execution_identity_receipt_sha256": _sha256(
            document["execution_identity_receipt_sha256"],
            "execution_identity_receipt_sha256",
        ),
        "store_identity_sha256": _sha256(
            document["store_identity_sha256"], "store_identity_sha256"
        ),
        "subject_path_identity_sha256": _sha256(
            document["subject_path_identity_sha256"],
            "subject_path_identity_sha256",
        ),
        "store_root_realpath": _realpath(
            document["store_root_realpath"], "store_root_realpath"
        ),
        "resolved_parent_realpath": _realpath(
            document["resolved_parent_realpath"], "resolved_parent_realpath"
        ),
        "subject_basename": _basename(document["subject_basename"], "subject_basename"),
        "parent_device": _plain_int(document["parent_device"], "parent_device"),
        "parent_inode": _plain_int(document["parent_inode"], "parent_inode", minimum=1),
    }


@dataclass(frozen=True, slots=True)
class D7AuthorizationPathAbsenceReceipt(_CanonicalEvidence):
    subject_kind: D7AbsentPathSubject
    replay_target_sha256: str
    attempt_key_sha256: str
    attempt_declaration_sha256: str
    authorization_commit: str
    execution_identity_receipt_sha256: str
    store_identity_sha256: str
    subject_path_identity_sha256: str
    store_root_realpath: str
    resolved_parent_realpath: str
    subject_basename: str
    parent_device: int
    parent_inode: int

    _LABEL: ClassVar[str] = "D7 authorization path-absence receipt"

    def __post_init__(self) -> None:
        _validate_path_absence_receipt(self)

    @property
    def subject_path(self) -> str:
        return _subject_path(self.resolved_parent_realpath, self.subject_basename)

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": D7_AUTHORIZATION_PATH_ABSENCE_RECEIPT_SCHEMA_VERSION,
            "contract_id": D7_AUTHORIZATION_PATH_ABSENCE_RECEIPT_CONTRACT_ID,
            "record_kind": "authorization-path-absence-receipt",
            "claim_ceiling": r.D7_RECORD_CLAIM_CEILING,
            "observation_stage": "launch-authorization",
            **_path_common_document(self),
        }

    @classmethod
    def from_dict(cls, value: object) -> Self:
        document = _mapping(value, cls._LABEL)
        constants = {
            "schema_version": D7_AUTHORIZATION_PATH_ABSENCE_RECEIPT_SCHEMA_VERSION,
            "contract_id": D7_AUTHORIZATION_PATH_ABSENCE_RECEIPT_CONTRACT_ID,
            "record_kind": "authorization-path-absence-receipt",
            "claim_ceiling": r.D7_RECORD_CLAIM_CEILING,
            "observation_stage": "launch-authorization",
        }
        _exact_keys(
            document,
            set(constants) | set(_PATH_COMMON_KEYS) | set(_PATH_OBSERVATION_CONSTANTS),
            cls._LABEL,
        )
        for name, expected in constants.items():
            _constant(document[name], expected, f"{cls._LABEL} {name}")
        return cls(**_decode_path_common(document, label=cls._LABEL))  # type: ignore[arg-type]


@dataclass(frozen=True, slots=True)
class D7PreStartPathAbsenceReceipt(_CanonicalEvidence):
    subject_kind: D7AbsentPathSubject
    replay_target_sha256: str
    attempt_key_sha256: str
    attempt_declaration_sha256: str
    launch_authorization_sha256: str
    attempt_claim_sha256: str
    authorization_commit: str
    execution_identity_receipt_sha256: str
    store_identity_sha256: str
    subject_path_identity_sha256: str
    store_root_realpath: str
    resolved_parent_realpath: str
    subject_basename: str
    parent_device: int
    parent_inode: int

    _LABEL: ClassVar[str] = "D7 pre-start path-absence receipt"

    def __post_init__(self) -> None:
        _validate_path_absence_receipt(self)
        _sha256(self.launch_authorization_sha256, "launch_authorization_sha256")
        _sha256(self.attempt_claim_sha256, "attempt_claim_sha256")

    @property
    def subject_path(self) -> str:
        return _subject_path(self.resolved_parent_realpath, self.subject_basename)

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": D7_PRE_START_PATH_ABSENCE_RECEIPT_SCHEMA_VERSION,
            "contract_id": D7_PRE_START_PATH_ABSENCE_RECEIPT_CONTRACT_ID,
            "record_kind": "pre-start-path-absence-receipt",
            "claim_ceiling": r.D7_RECORD_CLAIM_CEILING,
            "observation_stage": "execution-pre-start",
            **_path_common_document(self),
            "launch_authorization_sha256": self.launch_authorization_sha256,
            "attempt_claim_sha256": self.attempt_claim_sha256,
        }

    @classmethod
    def from_dict(cls, value: object) -> Self:
        document = _mapping(value, cls._LABEL)
        constants = {
            "schema_version": D7_PRE_START_PATH_ABSENCE_RECEIPT_SCHEMA_VERSION,
            "contract_id": D7_PRE_START_PATH_ABSENCE_RECEIPT_CONTRACT_ID,
            "record_kind": "pre-start-path-absence-receipt",
            "claim_ceiling": r.D7_RECORD_CLAIM_CEILING,
            "observation_stage": "execution-pre-start",
        }
        _exact_keys(
            document,
            set(constants)
            | set(_PATH_COMMON_KEYS)
            | set(_PATH_OBSERVATION_CONSTANTS)
            | {"launch_authorization_sha256", "attempt_claim_sha256"},
            cls._LABEL,
        )
        for name, expected in constants.items():
            _constant(document[name], expected, f"{cls._LABEL} {name}")
        decoded = _decode_path_common(document, label=cls._LABEL)
        decoded["launch_authorization_sha256"] = _sha256(
            document["launch_authorization_sha256"],
            "launch_authorization_sha256",
        )
        decoded["attempt_claim_sha256"] = _sha256(
            document["attempt_claim_sha256"], "attempt_claim_sha256"
        )
        return cls(**decoded)  # type: ignore[arg-type]


@dataclass(frozen=True, slots=True)
class D7InProcessFailureDetail:
    exception_class: str
    exception_message_sha256: str
    traceback_sha256: str

    def __post_init__(self) -> None:
        if (
            type(self.exception_class) is not str
            or _EXCEPTION_CLASS_RE.fullmatch(self.exception_class) is None
        ):
            raise QualificationContractError(
                "exception_class must be one bounded qualified identifier"
            )
        _sha256(self.exception_message_sha256, "exception_message_sha256")
        _sha256(self.traceback_sha256, "traceback_sha256")

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": "in-process-exception",
            "exception_class": self.exception_class,
            "exception_message_sha256": self.exception_message_sha256,
            "traceback_sha256": self.traceback_sha256,
            "diagnostic_text_persisted": False,
            "environment_dump_persisted": False,
            "credential_material_persisted": False,
        }

    @classmethod
    def from_dict(cls, value: object) -> Self:
        document = _mapping(value, "D7 in-process failure detail")
        constants = {
            "kind": "in-process-exception",
            "diagnostic_text_persisted": False,
            "environment_dump_persisted": False,
            "credential_material_persisted": False,
        }
        _exact_keys(
            document,
            set(constants)
            | {
                "exception_class",
                "exception_message_sha256",
                "traceback_sha256",
            },
            "D7 in-process failure detail",
        )
        for name, expected in constants.items():
            _constant(document[name], expected, f"in-process detail {name}")
        return cls(
            exception_class=_string(document["exception_class"], "exception_class"),
            exception_message_sha256=_sha256(
                document["exception_message_sha256"],
                "exception_message_sha256",
            ),
            traceback_sha256=_sha256(document["traceback_sha256"], "traceback_sha256"),
        )


@dataclass(frozen=True, slots=True)
class D7ExternalAbortObservationDetail:
    observer_identity_receipt_sha256: str
    observation_kind: D7ExternalAbortObservationKind
    observation_payload_sha256: str

    def __post_init__(self) -> None:
        _sha256(
            self.observer_identity_receipt_sha256,
            "observer_identity_receipt_sha256",
        )
        if type(self.observation_kind) is not D7ExternalAbortObservationKind:
            raise TypeError(
                "observation_kind must be an exact D7ExternalAbortObservationKind"
            )
        _sha256(self.observation_payload_sha256, "observation_payload_sha256")

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": "external-abort-observation",
            "observer_identity_receipt_sha256": (self.observer_identity_receipt_sha256),
            "observation_kind": self.observation_kind.value,
            "observation_payload_sha256": self.observation_payload_sha256,
            "caller_assertion_only": False,
        }

    @classmethod
    def from_dict(cls, value: object) -> Self:
        document = _mapping(value, "D7 external abort observation detail")
        _exact_keys(
            document,
            {
                "kind",
                "observer_identity_receipt_sha256",
                "observation_kind",
                "observation_payload_sha256",
                "caller_assertion_only",
            },
            "D7 external abort observation detail",
        )
        _constant(
            document["kind"],
            "external-abort-observation",
            "external detail kind",
        )
        _constant(
            document["caller_assertion_only"],
            False,
            "external detail caller_assertion_only",
        )
        return cls(
            observer_identity_receipt_sha256=_sha256(
                document["observer_identity_receipt_sha256"],
                "observer_identity_receipt_sha256",
            ),
            observation_kind=_enum(
                D7ExternalAbortObservationKind,
                document["observation_kind"],
                "observation_kind",
            ),  # type: ignore[arg-type]
            observation_payload_sha256=_sha256(
                document["observation_payload_sha256"],
                "observation_payload_sha256",
            ),
        )


D7FailureDetail: TypeAlias = D7InProcessFailureDetail | D7ExternalAbortObservationDetail


def _failure_detail(value: object) -> D7FailureDetail:
    document = _mapping(value, "D7 failure detail")
    kind = document.get("kind")
    if kind == "in-process-exception":
        return D7InProcessFailureDetail.from_dict(document)
    if kind == "external-abort-observation":
        return D7ExternalAbortObservationDetail.from_dict(document)
    raise QualificationContractError("D7 failure detail kind is unsupported")


@dataclass(frozen=True, slots=True)
class D7FailureEvidencePayload(_CanonicalEvidence):
    replay_target_sha256: str
    attempt_key_sha256: str
    execution_start_sha256: str
    execution_identity_receipt_sha256: str
    failure_stage: r.D7FailureStage
    origin: r.D7FailureEvidenceOrigin
    reason_code: str
    confirmation_value_access_state: r.D7ConfirmationValueAccessState
    detail: D7FailureDetail

    _LABEL: ClassVar[str] = "D7 failure-evidence payload"

    def __post_init__(self) -> None:
        for name in (
            "replay_target_sha256",
            "attempt_key_sha256",
            "execution_start_sha256",
            "execution_identity_receipt_sha256",
        ):
            _sha256(getattr(self, name), name)
        if type(self.failure_stage) is not r.D7FailureStage:
            raise TypeError("failure_stage must be an exact D7FailureStage")
        if type(self.origin) is not r.D7FailureEvidenceOrigin:
            raise TypeError("origin must be an exact D7FailureEvidenceOrigin")
        _slug(self.reason_code, "reason_code")
        if (
            type(self.confirmation_value_access_state)
            is not r.D7ConfirmationValueAccessState
        ):
            raise TypeError("confirmation_value_access_state must be an exact D7 state")
        external = type(self.detail) is D7ExternalAbortObservationDetail
        external_coordinates = (
            self.origin is r.D7FailureEvidenceOrigin.EXTERNAL
            and self.failure_stage is r.D7FailureStage.EVIDENCED_ABORT
        )
        in_process_coordinates = (
            self.origin is r.D7FailureEvidenceOrigin.IN_PROCESS
            and self.failure_stage is not r.D7FailureStage.EVIDENCED_ABORT
        )
        if not (
            (external and external_coordinates)
            or (not external and in_process_coordinates)
        ):
            raise QualificationContractError(
                "failure detail, origin, and failure stage differ"
            )
        if not external and type(self.detail) is not D7InProcessFailureDetail:
            raise TypeError("detail must be one exact D7 failure detail")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": D7_FAILURE_EVIDENCE_PAYLOAD_SCHEMA_VERSION,
            "contract_id": r.D7_FAILURE_EVIDENCE_PAYLOAD_CONTRACT_ID,
            "record_kind": "failure-evidence-payload",
            "record_scope": D7_FAILURE_RECORD_SCOPE,
            "claim_ceiling": r.D7_RECORD_CLAIM_CEILING,
            "replay_target_sha256": self.replay_target_sha256,
            "attempt_key_sha256": self.attempt_key_sha256,
            "execution_start_sha256": self.execution_start_sha256,
            "execution_identity_receipt_sha256": (
                self.execution_identity_receipt_sha256
            ),
            "failure_stage": self.failure_stage.value,
            "origin": self.origin.value,
            "reason_code": self.reason_code,
            "confirmation_value_access_state": (
                self.confirmation_value_access_state.value
            ),
            "aggregate_outcome_observed": False,
            "scientific_result_present": False,
            "detail": self.detail.to_dict(),
        }

    @classmethod
    def from_dict(cls, value: object) -> Self:
        document = _mapping(value, cls._LABEL)
        constants = {
            "schema_version": D7_FAILURE_EVIDENCE_PAYLOAD_SCHEMA_VERSION,
            "contract_id": r.D7_FAILURE_EVIDENCE_PAYLOAD_CONTRACT_ID,
            "record_kind": "failure-evidence-payload",
            "record_scope": D7_FAILURE_RECORD_SCOPE,
            "claim_ceiling": r.D7_RECORD_CLAIM_CEILING,
            "aggregate_outcome_observed": False,
            "scientific_result_present": False,
        }
        _exact_keys(
            document,
            set(constants)
            | {
                "replay_target_sha256",
                "attempt_key_sha256",
                "execution_start_sha256",
                "execution_identity_receipt_sha256",
                "failure_stage",
                "origin",
                "reason_code",
                "confirmation_value_access_state",
                "detail",
            },
            cls._LABEL,
        )
        for name, expected in constants.items():
            _constant(document[name], expected, f"{cls._LABEL} {name}")
        return cls(
            replay_target_sha256=_sha256(
                document["replay_target_sha256"], "replay_target_sha256"
            ),
            attempt_key_sha256=_sha256(
                document["attempt_key_sha256"], "attempt_key_sha256"
            ),
            execution_start_sha256=_sha256(
                document["execution_start_sha256"], "execution_start_sha256"
            ),
            execution_identity_receipt_sha256=_sha256(
                document["execution_identity_receipt_sha256"],
                "execution_identity_receipt_sha256",
            ),
            failure_stage=_enum(
                r.D7FailureStage, document["failure_stage"], "failure_stage"
            ),  # type: ignore[arg-type]
            origin=_enum(r.D7FailureEvidenceOrigin, document["origin"], "origin"),  # type: ignore[arg-type]
            reason_code=_slug(document["reason_code"], "reason_code"),
            confirmation_value_access_state=_enum(
                r.D7ConfirmationValueAccessState,
                document["confirmation_value_access_state"],
                "confirmation_value_access_state",
            ),  # type: ignore[arg-type]
            detail=_failure_detail(document["detail"]),
        )


@dataclass(frozen=True, slots=True)
class D7ExternalAbortVerificationReceipt(_CanonicalEvidence):
    replay_target_sha256: str
    attempt_key_sha256: str
    execution_start_sha256: str
    execution_identity_receipt_sha256: str
    failure_evidence_payload_sha256: str
    failure_evidence_payload_byte_count: int
    observer_identity_receipt_sha256: str
    verifier_source_runtime_receipt_sha256: str
    observation_payload_sha256: str
    verification_method: D7ExternalAbortVerificationMethod

    _LABEL: ClassVar[str] = "D7 external-abort verification receipt"

    def __post_init__(self) -> None:
        for name in (
            "replay_target_sha256",
            "attempt_key_sha256",
            "execution_start_sha256",
            "execution_identity_receipt_sha256",
            "failure_evidence_payload_sha256",
            "observer_identity_receipt_sha256",
            "verifier_source_runtime_receipt_sha256",
            "observation_payload_sha256",
        ):
            _sha256(getattr(self, name), name)
        _plain_int(
            self.failure_evidence_payload_byte_count,
            "failure_evidence_payload_byte_count",
            1,
        )
        if self.failure_evidence_payload_byte_count > MAX_D7_ATTEMPT_EVIDENCE_BYTES:
            raise QualificationContractError(
                "failure evidence payload exceeds the external receipt cap"
            )
        if type(self.verification_method) is not D7ExternalAbortVerificationMethod:
            raise TypeError(
                "verification_method must be an exact D7 verification method"
            )
        if (
            len(
                {
                    self.execution_identity_receipt_sha256,
                    self.observer_identity_receipt_sha256,
                    self.verifier_source_runtime_receipt_sha256,
                }
            )
            != 3
        ):
            raise QualificationContractError(
                "failed execution, observer, and verifier identities must differ"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": (D7_EXTERNAL_ABORT_VERIFICATION_RECEIPT_SCHEMA_VERSION),
            "contract_id": r.D7_EXTERNAL_ABORT_VERIFICATION_RECEIPT_CONTRACT_ID,
            "record_kind": "external-abort-verification-receipt",
            "claim_ceiling": r.D7_RECORD_CLAIM_CEILING,
            "replay_target_sha256": self.replay_target_sha256,
            "attempt_key_sha256": self.attempt_key_sha256,
            "execution_start_sha256": self.execution_start_sha256,
            "execution_identity_receipt_sha256": (
                self.execution_identity_receipt_sha256
            ),
            "failure_evidence_payload_sha256": (self.failure_evidence_payload_sha256),
            "failure_evidence_payload_byte_count": (
                self.failure_evidence_payload_byte_count
            ),
            "observer_identity_receipt_sha256": (self.observer_identity_receipt_sha256),
            "verifier_contract_id": D7_EXTERNAL_ABORT_VERIFIER_CONTRACT_ID,
            "verifier_source_runtime_receipt_sha256": (
                self.verifier_source_runtime_receipt_sha256
            ),
            "observation_payload_sha256": self.observation_payload_sha256,
            "verification_method": self.verification_method.value,
            "verification_state": "pass",
            "finalization_assertions": {
                "execution_start_sha256": self.execution_start_sha256,
                "execution_identity_receipt_sha256": (
                    self.execution_identity_receipt_sha256
                ),
                "aggregate_outcome_observed": False,
            },
            "elapsed_time_alone_sufficient": False,
            "process_absence_alone_sufficient": False,
            "caller_assertion_alone_sufficient": False,
            "cryptographic_abort_proof": False,
            "external_attestation": True,
        }

    @classmethod
    def from_dict(cls, value: object) -> Self:
        document = _mapping(value, cls._LABEL)
        constants = {
            "schema_version": (D7_EXTERNAL_ABORT_VERIFICATION_RECEIPT_SCHEMA_VERSION),
            "contract_id": r.D7_EXTERNAL_ABORT_VERIFICATION_RECEIPT_CONTRACT_ID,
            "record_kind": "external-abort-verification-receipt",
            "claim_ceiling": r.D7_RECORD_CLAIM_CEILING,
            "verifier_contract_id": D7_EXTERNAL_ABORT_VERIFIER_CONTRACT_ID,
            "verification_state": "pass",
            "elapsed_time_alone_sufficient": False,
            "process_absence_alone_sufficient": False,
            "caller_assertion_alone_sufficient": False,
            "cryptographic_abort_proof": False,
            "external_attestation": True,
        }
        _exact_keys(
            document,
            set(constants)
            | {
                "replay_target_sha256",
                "attempt_key_sha256",
                "execution_start_sha256",
                "execution_identity_receipt_sha256",
                "failure_evidence_payload_sha256",
                "failure_evidence_payload_byte_count",
                "observer_identity_receipt_sha256",
                "verifier_source_runtime_receipt_sha256",
                "observation_payload_sha256",
                "verification_method",
                "finalization_assertions",
            },
            cls._LABEL,
        )
        for name, expected in constants.items():
            _constant(document[name], expected, f"{cls._LABEL} {name}")
        assertions = _mapping(
            document["finalization_assertions"], "finalization_assertions"
        )
        _exact_keys(
            assertions,
            {
                "execution_start_sha256",
                "execution_identity_receipt_sha256",
                "aggregate_outcome_observed",
            },
            "finalization_assertions",
        )
        _constant(
            assertions["aggregate_outcome_observed"],
            False,
            "aggregate_outcome_observed",
        )
        start = _sha256(document["execution_start_sha256"], "execution_start_sha256")
        identity = _sha256(
            document["execution_identity_receipt_sha256"],
            "execution_identity_receipt_sha256",
        )
        asserted_start = _sha256(
            assertions["execution_start_sha256"],
            "finalization_assertions execution_start_sha256",
        )
        asserted_identity = _sha256(
            assertions["execution_identity_receipt_sha256"],
            "finalization_assertions execution_identity_receipt_sha256",
        )
        if asserted_start != start or asserted_identity != identity:
            raise QualificationContractError(
                "finalization assertions differ from the external receipt"
            )
        return cls(
            replay_target_sha256=_sha256(
                document["replay_target_sha256"], "replay_target_sha256"
            ),
            attempt_key_sha256=_sha256(
                document["attempt_key_sha256"], "attempt_key_sha256"
            ),
            execution_start_sha256=start,
            execution_identity_receipt_sha256=identity,
            failure_evidence_payload_sha256=_sha256(
                document["failure_evidence_payload_sha256"],
                "failure_evidence_payload_sha256",
            ),
            failure_evidence_payload_byte_count=_plain_int(
                document["failure_evidence_payload_byte_count"],
                "failure_evidence_payload_byte_count",
                1,
            ),
            observer_identity_receipt_sha256=_sha256(
                document["observer_identity_receipt_sha256"],
                "observer_identity_receipt_sha256",
            ),
            verifier_source_runtime_receipt_sha256=_sha256(
                document["verifier_source_runtime_receipt_sha256"],
                "verifier_source_runtime_receipt_sha256",
            ),
            observation_payload_sha256=_sha256(
                document["observation_payload_sha256"],
                "observation_payload_sha256",
            ),
            verification_method=_enum(
                D7ExternalAbortVerificationMethod,
                document["verification_method"],
                "verification_method",
            ),  # type: ignore[arg-type]
        )


@dataclass(frozen=True, slots=True)
class D7ExternalAbortWitnessStatement(_CanonicalEvidence):
    """Caller-serializable statement; authenticated status is runtime-only."""

    replay_target_sha256: str
    attempt_key_sha256: str
    execution_start_sha256: str
    execution_identity_receipt_sha256: str
    failure_evidence_payload_sha256: str
    failure_evidence_payload_byte_count: int
    structural_verification_receipt_sha256: str
    structural_verification_receipt_byte_count: int
    observer_identity_receipt_sha256: str
    verifier_source_runtime_receipt_sha256: str
    observation_kind: D7ExternalAbortObservationKind
    observation_payload_sha256: str
    store_identity_sha256: str
    terminal_path_identity_sha256: str
    store_root_realpath: str
    terminal_parent_realpath: str
    terminal_basename: str
    terminal_parent_device: int
    terminal_parent_inode: int
    execution_principal_id: str
    observer_principal_id: str
    verifier_principal_id: str
    observer_public_key_sha256: str
    verifier_public_key_sha256: str
    runtime_trust_root_sha256: str

    _LABEL: ClassVar[str] = "D7 external-abort witness statement"

    def __post_init__(self) -> None:
        for name in (
            "replay_target_sha256",
            "attempt_key_sha256",
            "execution_start_sha256",
            "execution_identity_receipt_sha256",
            "failure_evidence_payload_sha256",
            "structural_verification_receipt_sha256",
            "observer_identity_receipt_sha256",
            "verifier_source_runtime_receipt_sha256",
            "observation_payload_sha256",
            "store_identity_sha256",
            "terminal_path_identity_sha256",
            "observer_public_key_sha256",
            "verifier_public_key_sha256",
            "runtime_trust_root_sha256",
        ):
            _sha256(getattr(self, name), name)
        for name in (
            "failure_evidence_payload_byte_count",
            "structural_verification_receipt_byte_count",
        ):
            value = _plain_int(getattr(self, name), name, 1)
            if value > MAX_D7_ATTEMPT_EVIDENCE_BYTES:
                raise QualificationContractError(f"{name} exceeds the witness cap")
        if type(self.observation_kind) is not D7ExternalAbortObservationKind:
            raise TypeError(
                "observation_kind must be an exact D7ExternalAbortObservationKind"
            )
        root = _realpath(self.store_root_realpath, "store_root_realpath")
        parent = _realpath(self.terminal_parent_realpath, "terminal_parent_realpath")
        basename = _basename(self.terminal_basename, "terminal_basename")
        _plain_int(self.terminal_parent_device, "terminal_parent_device")
        _plain_int(self.terminal_parent_inode, "terminal_parent_inode", 1)
        if not _path_is_within(root, parent):
            raise QualificationContractError(
                "terminal parent must remain within the store root"
            )
        expected_path_identity = d7_path_identity_sha256(
            store_identity_sha256=self.store_identity_sha256,
            resolved_parent_realpath=parent,
            subject_basename=basename,
        )
        if self.terminal_path_identity_sha256 != expected_path_identity:
            raise QualificationContractError(
                "terminal_path_identity_sha256 differs from witness coordinates"
            )
        principals = tuple(
            _slug(getattr(self, name), name)
            for name in (
                "execution_principal_id",
                "observer_principal_id",
                "verifier_principal_id",
            )
        )
        if len(set(principals)) != 3:
            raise QualificationContractError(
                "execution, observer, and verifier principals must differ"
            )
        if self.observer_public_key_sha256 == self.verifier_public_key_sha256:
            raise QualificationContractError(
                "observer and verifier public keys must differ"
            )
        expected_trust_root = d7_external_witness_runtime_trust_root_sha256(
            execution_principal_id=self.execution_principal_id,
            execution_identity_receipt_sha256=(self.execution_identity_receipt_sha256),
            observer_principal_id=self.observer_principal_id,
            observer_identity_receipt_sha256=(self.observer_identity_receipt_sha256),
            observer_public_key_sha256=self.observer_public_key_sha256,
            verifier_principal_id=self.verifier_principal_id,
            verifier_source_runtime_receipt_sha256=(
                self.verifier_source_runtime_receipt_sha256
            ),
            verifier_public_key_sha256=self.verifier_public_key_sha256,
        )
        if self.runtime_trust_root_sha256 != expected_trust_root:
            raise QualificationContractError(
                "runtime_trust_root_sha256 differs from authenticated principals"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": D7_EXTERNAL_ABORT_WITNESS_STATEMENT_SCHEMA_VERSION,
            "record_kind": "external-abort-witness-statement",
            "record_scope": D7_FAILURE_RECORD_SCOPE,
            "claim_ceiling": r.D7_RECORD_CLAIM_CEILING,
            "witness_claim": "authenticated-external-observation-only",
            "replay_target_sha256": self.replay_target_sha256,
            "attempt_key_sha256": self.attempt_key_sha256,
            "execution_start_sha256": self.execution_start_sha256,
            "execution_identity_receipt_sha256": (
                self.execution_identity_receipt_sha256
            ),
            "failure_evidence_payload_sha256": (self.failure_evidence_payload_sha256),
            "failure_evidence_payload_byte_count": (
                self.failure_evidence_payload_byte_count
            ),
            "structural_verification_receipt_sha256": (
                self.structural_verification_receipt_sha256
            ),
            "structural_verification_receipt_byte_count": (
                self.structural_verification_receipt_byte_count
            ),
            "observer_identity_receipt_sha256": (self.observer_identity_receipt_sha256),
            "verifier_source_runtime_receipt_sha256": (
                self.verifier_source_runtime_receipt_sha256
            ),
            "observation_kind": self.observation_kind.value,
            "observation_payload_sha256": self.observation_payload_sha256,
            "store_identity_sha256": self.store_identity_sha256,
            "terminal_path_identity_sha256": self.terminal_path_identity_sha256,
            "store_root_realpath": self.store_root_realpath,
            "terminal_parent_realpath": self.terminal_parent_realpath,
            "terminal_basename": self.terminal_basename,
            "terminal_parent_device": self.terminal_parent_device,
            "terminal_parent_inode": self.terminal_parent_inode,
            "execution_principal_id": self.execution_principal_id,
            "observer_principal_id": self.observer_principal_id,
            "verifier_principal_id": self.verifier_principal_id,
            "observer_public_key_sha256": self.observer_public_key_sha256,
            "verifier_public_key_sha256": self.verifier_public_key_sha256,
            "runtime_trust_root_sha256": self.runtime_trust_root_sha256,
            "observation_method": (
                "authenticated-external-event-plus-terminal-inspection-v0.1"
            ),
            "external_event_evidenced": True,
            "terminal_directory_entry_absent": True,
            "elapsed_time_alone_sufficient": False,
            "process_absence_alone_sufficient": False,
            "caller_assertion_alone_sufficient": False,
            "official_d7_authority_granted": False,
            "execution_authority_granted": False,
            "finalization_authority_granted": False,
        }

    @classmethod
    def from_dict(cls, value: object) -> Self:
        document = _mapping(value, cls._LABEL)
        constants = {
            "schema_version": D7_EXTERNAL_ABORT_WITNESS_STATEMENT_SCHEMA_VERSION,
            "record_kind": "external-abort-witness-statement",
            "record_scope": D7_FAILURE_RECORD_SCOPE,
            "claim_ceiling": r.D7_RECORD_CLAIM_CEILING,
            "witness_claim": "authenticated-external-observation-only",
            "observation_method": (
                "authenticated-external-event-plus-terminal-inspection-v0.1"
            ),
            "external_event_evidenced": True,
            "terminal_directory_entry_absent": True,
            "elapsed_time_alone_sufficient": False,
            "process_absence_alone_sufficient": False,
            "caller_assertion_alone_sufficient": False,
            "official_d7_authority_granted": False,
            "execution_authority_granted": False,
            "finalization_authority_granted": False,
        }
        sha_fields = {
            "replay_target_sha256",
            "attempt_key_sha256",
            "execution_start_sha256",
            "execution_identity_receipt_sha256",
            "failure_evidence_payload_sha256",
            "structural_verification_receipt_sha256",
            "observer_identity_receipt_sha256",
            "verifier_source_runtime_receipt_sha256",
            "observation_payload_sha256",
            "store_identity_sha256",
            "terminal_path_identity_sha256",
            "observer_public_key_sha256",
            "verifier_public_key_sha256",
            "runtime_trust_root_sha256",
        }
        integer_fields = {
            "failure_evidence_payload_byte_count",
            "structural_verification_receipt_byte_count",
            "terminal_parent_device",
            "terminal_parent_inode",
        }
        string_fields = {
            "store_root_realpath",
            "terminal_parent_realpath",
            "terminal_basename",
            "execution_principal_id",
            "observer_principal_id",
            "verifier_principal_id",
        }
        _exact_keys(
            document,
            set(constants)
            | sha_fields
            | integer_fields
            | string_fields
            | {"observation_kind"},
            cls._LABEL,
        )
        for name, expected in constants.items():
            _constant(document[name], expected, f"{cls._LABEL} {name}")
        values: dict[str, object] = {
            name: _sha256(document[name], name) for name in sha_fields
        }
        values.update(
            {
                "failure_evidence_payload_byte_count": _plain_int(
                    document["failure_evidence_payload_byte_count"],
                    "failure_evidence_payload_byte_count",
                    1,
                ),
                "structural_verification_receipt_byte_count": _plain_int(
                    document["structural_verification_receipt_byte_count"],
                    "structural_verification_receipt_byte_count",
                    1,
                ),
                "terminal_parent_device": _plain_int(
                    document["terminal_parent_device"],
                    "terminal_parent_device",
                ),
                "terminal_parent_inode": _plain_int(
                    document["terminal_parent_inode"],
                    "terminal_parent_inode",
                    1,
                ),
                "store_root_realpath": _realpath(
                    document["store_root_realpath"],
                    "store_root_realpath",
                ),
                "terminal_parent_realpath": _realpath(
                    document["terminal_parent_realpath"],
                    "terminal_parent_realpath",
                ),
                "terminal_basename": _basename(
                    document["terminal_basename"],
                    "terminal_basename",
                ),
                "execution_principal_id": _slug(
                    document["execution_principal_id"],
                    "execution_principal_id",
                ),
                "observer_principal_id": _slug(
                    document["observer_principal_id"],
                    "observer_principal_id",
                ),
                "verifier_principal_id": _slug(
                    document["verifier_principal_id"],
                    "verifier_principal_id",
                ),
                "observation_kind": _enum(
                    D7ExternalAbortObservationKind,
                    document["observation_kind"],
                    "observation_kind",
                ),
            }
        )
        return cls(**values)  # type: ignore[arg-type]


@dataclass(frozen=True, slots=True)
class D7SignedExternalAbortWitnessEnvelope(_CanonicalEvidence):
    """Canonical signed bytes; verification creates a separate runtime value."""

    statement: D7ExternalAbortWitnessStatement
    observer_signature: str
    verifier_signature: str

    _LABEL: ClassVar[str] = "D7 signed external-abort witness envelope"

    def __post_init__(self) -> None:
        if type(self.statement) is not D7ExternalAbortWitnessStatement:
            raise TypeError(
                "statement must be an exact D7ExternalAbortWitnessStatement"
            )
        _ed25519_signature(self.observer_signature, "observer_signature")
        _ed25519_signature(self.verifier_signature, "verifier_signature")

    @property
    def observer_signed_bytes(self) -> bytes:
        return canonical_json_bytes(
            {
                "signature_context": D7_EXTERNAL_ABORT_OBSERVER_SIGNATURE_CONTEXT,
                "statement_sha256": self.statement.canonical_sha256,
                "statement": self.statement.to_dict(),
            }
        )

    @property
    def verifier_signed_bytes(self) -> bytes:
        return canonical_json_bytes(
            {
                "signature_context": D7_EXTERNAL_ABORT_VERIFIER_SIGNATURE_CONTEXT,
                "statement_sha256": self.statement.canonical_sha256,
                "runtime_trust_root_sha256": (self.statement.runtime_trust_root_sha256),
                "observer_public_key_sha256": (
                    self.statement.observer_public_key_sha256
                ),
                "verifier_public_key_sha256": (
                    self.statement.verifier_public_key_sha256
                ),
                "observer_signature": self.observer_signature,
            }
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": (
                D7_SIGNED_EXTERNAL_ABORT_WITNESS_ENVELOPE_SCHEMA_VERSION
            ),
            "record_kind": "signed-external-abort-witness-envelope",
            "claim_ceiling": r.D7_RECORD_CLAIM_CEILING,
            "signature_algorithm": "ed25519",
            "statement": self.statement.to_dict(),
            "statement_sha256": self.statement.canonical_sha256,
            "observer_signed_payload_sha256": sha256_bytes(self.observer_signed_bytes),
            "observer_signature": self.observer_signature,
            "verifier_signed_payload_sha256": sha256_bytes(self.verifier_signed_bytes),
            "verifier_signature": self.verifier_signature,
            "serialized_capability": False,
            "official_d7_authority_granted": False,
            "execution_authority_granted": False,
            "finalization_authority_granted": False,
        }

    @classmethod
    def from_dict(cls, value: object) -> Self:
        document = _mapping(value, cls._LABEL)
        constants = {
            "schema_version": (
                D7_SIGNED_EXTERNAL_ABORT_WITNESS_ENVELOPE_SCHEMA_VERSION
            ),
            "record_kind": "signed-external-abort-witness-envelope",
            "claim_ceiling": r.D7_RECORD_CLAIM_CEILING,
            "signature_algorithm": "ed25519",
            "serialized_capability": False,
            "official_d7_authority_granted": False,
            "execution_authority_granted": False,
            "finalization_authority_granted": False,
        }
        _exact_keys(
            document,
            set(constants)
            | {
                "statement",
                "statement_sha256",
                "observer_signed_payload_sha256",
                "observer_signature",
                "verifier_signed_payload_sha256",
                "verifier_signature",
            },
            cls._LABEL,
        )
        for name, expected in constants.items():
            _constant(document[name], expected, f"{cls._LABEL} {name}")
        statement = D7ExternalAbortWitnessStatement.from_dict(document["statement"])
        result = cls(
            statement=statement,
            observer_signature=_ed25519_signature(
                document["observer_signature"],
                "observer_signature",
            ),
            verifier_signature=_ed25519_signature(
                document["verifier_signature"],
                "verifier_signature",
            ),
        )
        for label, expected, observed in (
            (
                "statement_sha256",
                statement.canonical_sha256,
                _sha256(document["statement_sha256"], "statement_sha256"),
            ),
            (
                "observer_signed_payload_sha256",
                sha256_bytes(result.observer_signed_bytes),
                _sha256(
                    document["observer_signed_payload_sha256"],
                    "observer_signed_payload_sha256",
                ),
            ),
            (
                "verifier_signed_payload_sha256",
                sha256_bytes(result.verifier_signed_bytes),
                _sha256(
                    document["verifier_signed_payload_sha256"],
                    "verifier_signed_payload_sha256",
                ),
            ),
        ):
            if observed != expected:
                raise QualificationContractError(f"{label} differs")
        return result
