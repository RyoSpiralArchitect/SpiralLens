"""Structural-only canonical records for the future D7 attempt lifecycle.

These directly constructible values define bytes and local invariants only.
They do not load trusted state, acquire a claim, authorize work, write files,
publish a terminal, or confer D7/D8 authority.  Authoritative construction and
persistence remain intentionally absent.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from typing import ClassVar, Self, TypeAlias, cast

from spirallens.core.canonical import (
    CanonicalJsonError,
    canonical_json_bytes,
    canonical_json_sha256,
    parse_canonical_json,
    sha256_bytes,
)

from .common import QualificationContractError

D7_PRIMARY_ROLE_EVIDENCE_SCHEMA_VERSION = "spirallens.d7-primary-role-evidence.v0.1"
D7_ISOLATED_REPLAY_ROLE_EVIDENCE_SCHEMA_VERSION = (
    "spirallens.d7-isolated-replay-role-evidence.v0.1"
)
D7_ATTEMPT_DECLARATION_SCHEMA_VERSION = "spirallens.d7-attempt-declaration.v0.1"
D7_LAUNCH_AUTHORIZATION_SCHEMA_VERSION = "spirallens.d7-launch-authorization.v0.1"
D7_ATTEMPT_CLAIM_SCHEMA_VERSION = "spirallens.d7-attempt-claim.v0.1"
D7_EXECUTION_START_SCHEMA_VERSION = "spirallens.d7-execution-start.v0.1"
D7_GATE_OUTCOME_SUMMARY_SCHEMA_VERSION = "spirallens.d7-gate-outcome-summary.v0.1"
D7_RESULT_COMPONENT_BINDING_SCHEMA_VERSION = (
    "spirallens.d7-result-component-binding.v0.1"
)
D7_SCIENTIFIC_RESULT_PAYLOAD_SCHEMA_VERSION = (
    "spirallens.d7-scientific-result-payload.v0.1"
)
D7_SCIENTIFIC_RESULT_SCHEMA_VERSION = "spirallens.d7-scientific-result.v0.1"
D7_FAILURE_EVIDENCE_SCHEMA_VERSION = "spirallens.d7-failure-evidence.v0.1"
D7_FAILURE_EVIDENCE_PAYLOAD_CONTRACT_ID = (
    "spirallens.d7-failure-evidence-payload-contract.v0.1"
)
D7_EXTERNAL_ABORT_VERIFICATION_RECEIPT_CONTRACT_ID = (
    "spirallens.d7-external-abort-verification-receipt-contract.v0.1"
)
D7_STARTED_UNRESOLVED_FINALIZATION_SCHEMA_VERSION = (
    "spirallens.d7-started-unresolved-finalization.v0.1"
)
D7_FAILED_ATTEMPT_SCHEMA_VERSION = "spirallens.d7-failed-attempt.v0.1"
D7_TERMINAL_MEMBER_BINDING_SCHEMA_VERSION = "spirallens.d7-terminal-member-binding.v0.1"
D7_TERMINAL_MANIFEST_SCHEMA_VERSION = "spirallens.d7-terminal-manifest.v0.1"
D7_TERMINAL_CONSUMPTION_SCHEMA_VERSION = "spirallens.d7-terminal-consumption.v0.1"

D7_ATTEMPT_KEY_SCHEME = "spirallens.d7-attempt-key.v0.1"
D7_RESULT_EVIDENCE_ROOT_SCHEME = "spirallens.d7-result-evidence-root.v0.1"
D7_RESULT_SCHEMA_DESCRIPTOR_VERSION = "spirallens.d7-result-schema-descriptor.v0.1"
D7_RECORD_CLAIM_CEILING = "level_0"
D7_RESULT_RECORD_SCOPE = "d7-spectral-moment-surrogate-confirmation-only"

MAX_D7_CHRONOLOGY_RECORD_BYTES = 128 * 1024
MAX_D7_RESULT_PAYLOAD_BYTES = 4 * 1024 * 1024
MAX_D7_TERMINAL_MANIFEST_BYTES = 512 * 1024
MAX_D7_RESULT_COMPONENT_BYTES = 32 * 1024 * 1024

D7_TERMINAL_MANIFEST_FILENAME = "terminal-manifest.json"
D7_TERMINAL_CONSUMPTION_FILENAME = "terminal-consumption.json"
D7_SCIENTIFIC_RESULT_FILENAME = "scientific-result.json"
D7_SCIENTIFIC_RESULT_PAYLOAD_FILENAME = "scientific-result-payload.json"
D7_FAILED_ATTEMPT_FILENAME = "failed-attempt.json"
D7_FAILURE_EVIDENCE_FILENAME = "failure-evidence.json"
D7_FAILURE_EVIDENCE_PAYLOAD_FILENAME = "failure-evidence-payload.json"
D7_EXTERNAL_ABORT_VERIFICATION_RECEIPT_FILENAME = (
    "external-abort-verification-receipt.json"
)
D7_STARTED_UNRESOLVED_FINALIZATION_FILENAME = "started-unresolved-finalization.json"

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,127}$")
_SCHEMA_RE = re.compile(r"^spirallens\.[a-z0-9][a-z0-9._-]{0,191}$")
_FILENAME_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,191}\.json$")


class D7AttemptRole(str, Enum):
    PRIMARY_CONFIRMATION = "primary-confirmation"
    ISOLATED_BYTE_REPLAY = "isolated-byte-replay"


class D7GateState(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    INSUFFICIENT = "insufficient"
    NOT_RUN = "not_run"


class D7ScientificResultState(str, Enum):
    """Terminal scientific states; overall ``not_run`` is intentionally absent."""

    PASS = "pass"
    FAIL = "fail"
    INSUFFICIENT = "insufficient"


class D7FailureStage(str, Enum):
    EXECUTION_KERNEL = "execution-kernel"
    AGGREGATION = "aggregation"
    RESULT_VALIDATION = "result-validation"
    TERMINAL_PREPARATION = "terminal-preparation"
    EVIDENCED_ABORT = "evidenced-abort"


class D7FailureEvidenceOrigin(str, Enum):
    IN_PROCESS = "in-process"
    EXTERNAL = "external"


class D7ConfirmationValueAccessState(str, Enum):
    OBSERVED = "observed"
    NOT_OBSERVED = "not-observed"
    UNKNOWN = "unknown"


class D7TerminalArtifactKind(str, Enum):
    SCIENTIFIC_RESULT = "scientific-result"
    FAILED_ATTEMPT = "failed-attempt"


class D7TerminalMemberKind(str, Enum):
    SCIENTIFIC_RESULT = "scientific-result"
    SCIENTIFIC_RESULT_PAYLOAD = "scientific-result-payload"
    RESULT_COMPONENT = "result-component"
    FAILED_ATTEMPT = "failed-attempt"
    FAILURE_EVIDENCE = "failure-evidence"
    FAILURE_EVIDENCE_PAYLOAD = "failure-evidence-payload"
    EXTERNAL_ABORT_VERIFICATION_RECEIPT = "external-abort-verification-receipt"
    STARTED_UNRESOLVED_FINALIZATION = "started-unresolved-finalization"


class D7ResultComponentId(str, Enum):
    EXECUTION_EVENT_LEDGER = "execution-event-ledger"
    CORE_CELL_OUTCOMES = "core-cell-outcomes"
    LOOP_CELL_OUTCOMES = "loop-cell-outcomes"
    PRIMARY_UNIT_OUTCOMES = "primary-unit-outcomes"
    REQUIRED_STRATUM_OUTCOMES = "required-stratum-outcomes"
    AGGREGATE_GATE_OUTCOMES = "aggregate-gate-outcomes"


D7_RESULT_COMPONENT_ORDER = (
    D7ResultComponentId.EXECUTION_EVENT_LEDGER,
    D7ResultComponentId.CORE_CELL_OUTCOMES,
    D7ResultComponentId.LOOP_CELL_OUTCOMES,
    D7ResultComponentId.PRIMARY_UNIT_OUTCOMES,
    D7ResultComponentId.REQUIRED_STRATUM_OUTCOMES,
    D7ResultComponentId.AGGREGATE_GATE_OUTCOMES,
)

D7_RESULT_COMPONENT_CONTRACT_IDS = MappingProxyType(
    {
        component_id: f"spirallens.d7-{component_id.value}-payload-contract.v0.1"
        for component_id in D7_RESULT_COMPONENT_ORDER
    }
)
D7_RESULT_COMPONENT_FIXED_RECORD_COUNTS = MappingProxyType(
    {
        D7ResultComponentId.EXECUTION_EVENT_LEDGER: 1344,
        D7ResultComponentId.CORE_CELL_OUTCOMES: 192,
        D7ResultComponentId.LOOP_CELL_OUTCOMES: 1152,
        D7ResultComponentId.PRIMARY_UNIT_OUTCOMES: 64,
        D7ResultComponentId.REQUIRED_STRATUM_OUTCOMES: 6,
    }
)
_RESULT_COMPONENT_FILENAMES = MappingProxyType(
    {
        component_id: f"result-{component_id.value}.json"
        for component_id in D7_RESULT_COMPONENT_ORDER
    }
)
_RESULT_COMPONENT_BY_FILENAME = MappingProxyType(
    {
        filename: component_id
        for component_id, filename in _RESULT_COMPONENT_FILENAMES.items()
    }
)
_FIXED_TERMINAL_MEMBER_CONTRACTS = MappingProxyType(
    {
        D7TerminalMemberKind.SCIENTIFIC_RESULT: (
            D7_SCIENTIFIC_RESULT_FILENAME,
            D7_SCIENTIFIC_RESULT_SCHEMA_VERSION,
        ),
        D7TerminalMemberKind.SCIENTIFIC_RESULT_PAYLOAD: (
            D7_SCIENTIFIC_RESULT_PAYLOAD_FILENAME,
            D7_SCIENTIFIC_RESULT_PAYLOAD_SCHEMA_VERSION,
        ),
        D7TerminalMemberKind.FAILED_ATTEMPT: (
            D7_FAILED_ATTEMPT_FILENAME,
            D7_FAILED_ATTEMPT_SCHEMA_VERSION,
        ),
        D7TerminalMemberKind.FAILURE_EVIDENCE: (
            D7_FAILURE_EVIDENCE_FILENAME,
            D7_FAILURE_EVIDENCE_SCHEMA_VERSION,
        ),
        D7TerminalMemberKind.FAILURE_EVIDENCE_PAYLOAD: (
            D7_FAILURE_EVIDENCE_PAYLOAD_FILENAME,
            D7_FAILURE_EVIDENCE_PAYLOAD_CONTRACT_ID,
        ),
        D7TerminalMemberKind.EXTERNAL_ABORT_VERIFICATION_RECEIPT: (
            D7_EXTERNAL_ABORT_VERIFICATION_RECEIPT_FILENAME,
            D7_EXTERNAL_ABORT_VERIFICATION_RECEIPT_CONTRACT_ID,
        ),
        D7TerminalMemberKind.STARTED_UNRESOLVED_FINALIZATION: (
            D7_STARTED_UNRESOLVED_FINALIZATION_FILENAME,
            D7_STARTED_UNRESOLVED_FINALIZATION_SCHEMA_VERSION,
        ),
    }
)


def _names(value: str) -> tuple[str, ...]:
    """Keep declarative field inventories readable without reflection."""

    return tuple(value.split())


_ATTEMPT_COORDINATE_FIELDS = _names("replay_target_sha256 attempt_key_sha256")
_STARTED_COORDINATE_FIELDS = _names(
    "replay_target_sha256 attempt_key_sha256 execution_start_sha256 "
    "execution_identity_receipt_sha256"
)
_TERMINAL_COORDINATE_FIELDS = _names(
    "replay_target_sha256 attempt_key_sha256 attempt_claim_sha256 "
    "execution_start_sha256 execution_identity_receipt_sha256"
)


def _mapping(value: object, label: str) -> dict[str, object]:
    if type(value) is not dict or any(type(key) is not str for key in value):
        raise QualificationContractError(f"{label} must be a string-keyed object")
    return value


def _sequence(value: object, label: str) -> list[object]:
    if type(value) is not list:
        raise QualificationContractError(f"{label} must be a JSON array")
    return value


def _string(value: object, label: str) -> str:
    if type(value) is not str or not value or value != value.strip():
        raise QualificationContractError(f"{label} must be a non-empty trimmed string")
    return value


def _slug(value: object, label: str) -> str:
    result = _string(value, label)
    if _SLUG_RE.fullmatch(result) is None:
        raise QualificationContractError(f"{label} must be a portable slug")
    return result


def _schema_version(value: object, label: str) -> str:
    result = _string(value, label)
    if _SCHEMA_RE.fullmatch(result) is None:
        raise QualificationContractError(f"{label} must be a SpiralLens schema version")
    return result


def _contract_id(value: object, label: str) -> str:
    result = _string(value, label)
    if _SCHEMA_RE.fullmatch(result) is None:
        raise QualificationContractError(f"{label} must be a SpiralLens contract ID")
    return result


def _filename(value: object, label: str) -> str:
    result = _string(value, label)
    if _FILENAME_RE.fullmatch(result) is None or "/" in result or "\\" in result:
        raise QualificationContractError(f"{label} must be a safe JSON basename")
    return result


def _sha256(value: object, label: str) -> str:
    if type(value) is not str or _SHA256_RE.fullmatch(value) is None:
        raise QualificationContractError(f"{label} must be a lowercase SHA-256")
    return value


def _commit(value: object, label: str) -> str:
    if type(value) is not str or _COMMIT_RE.fullmatch(value) is None:
        raise QualificationContractError(f"{label} must be a lowercase Git commit")
    return value


def _plain_int(value: object, label: str, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise QualificationContractError(
            f"{label} must be a plain integer of at least {minimum}"
        )
    return value


def _plain_bool(value: object, label: str) -> bool:
    if type(value) is not bool:
        raise QualificationContractError(f"{label} must be a boolean")
    return value


def _enum_value(enum_type: type[Enum], value: object, label: str) -> Enum:
    if type(value) is not str:
        raise QualificationContractError(f"{label} must be a string")
    try:
        return enum_type(value)
    except ValueError as error:
        raise QualificationContractError(f"{label} is not supported") from error


def _pop_enum(values: dict[str, object], name: str, enum_type: type[Enum]) -> Enum:
    return _enum_value(enum_type, values.pop(name), name)


def _freeze_constant(value: object) -> object:
    if type(value) is list:
        return tuple(_freeze_constant(member) for member in value)
    if type(value) is dict:
        return MappingProxyType(
            {key: _freeze_constant(member) for key, member in value.items()}
        )
    return value


def _json_constant(value: object) -> object:
    if type(value) is tuple:
        return [_json_constant(member) for member in value]
    if isinstance(value, Mapping):
        return {key: _json_constant(member) for key, member in value.items()}
    return value


def _json_constants(values: Mapping[str, object]) -> dict[str, object]:
    return {key: _json_constant(value) for key, value in values.items()}


def _record_constants(
    schema_version: str,
    record_kind: str | None = None,
    *,
    claim_ceiling: str | None = None,
    **values: object,
) -> Mapping[str, object]:
    result: dict[str, object] = {"schema_version": schema_version}
    if record_kind is not None:
        result["record_kind"] = record_kind
    if claim_ceiling is not None:
        result["claim_ceiling"] = claim_ceiling
    result.update({key: _freeze_constant(value) for key, value in values.items()})
    return MappingProxyType(result)


def _record_document(
    value: _CanonicalRecord, record_kind: str, fields: tuple[str, ...], **extra: object
) -> dict[str, object]:
    return _json_constants(
        _record_constants(
            value.schema_version,
            record_kind,
            claim_ceiling=value.claim_ceiling,
            **{name: getattr(value, name) for name in fields},
            **extra,
        )
    )


def _decode_record(
    value: object,
    *,
    label: str,
    constants: Mapping[str, object],
    sha_fields: tuple[str, ...] = (),
    commit_fields: tuple[str, ...] = (),
    slug_fields: tuple[str, ...] = (),
    schema_fields: tuple[str, ...] = (),
    contract_fields: tuple[str, ...] = (),
    filename_fields: tuple[str, ...] = (),
    int_fields: tuple[str, ...] = (),
    positive_int_fields: tuple[str, ...] = (),
    bool_fields: tuple[str, ...] = (),
    optional_sha_fields: tuple[str, ...] = (),
    enum_fields: Mapping[str, type[Enum]] | None = None,
    raw_fields: tuple[str, ...] = (),
) -> dict[str, object]:
    """Decode one explicitly declared record without reflection or authority."""

    enums = {} if enum_fields is None else enum_fields
    groups = (
        sha_fields,
        commit_fields,
        slug_fields,
        schema_fields,
        contract_fields,
        filename_fields,
        int_fields,
        positive_int_fields,
        bool_fields,
        optional_sha_fields,
        tuple(enums),
        raw_fields,
    )
    declared = [field for group in groups for field in group]
    if len(declared) != len(set(declared)):
        raise RuntimeError(f"{label} decoder declares a field more than once")
    expected = set(constants).union(declared)
    item = _mapping(value, label)
    if set(item) != expected:
        raise QualificationContractError(
            f"{label} fields differ from the contract: "
            f"missing={sorted(expected - set(item))}, "
            f"unknown={sorted(set(item) - expected)}"
        )
    for name, expected_value in constants.items():
        observed = item[name]
        expected_json = _json_constant(expected_value)
        if type(observed) is not type(expected_json) or observed != expected_json:
            raise QualificationContractError(f"{name} must equal {expected_json!r}")
    decoded: dict[str, object] = {}
    decoders = (
        (sha_fields, _sha256),
        (commit_fields, _commit),
        (slug_fields, _slug),
        (schema_fields, _schema_version),
        (contract_fields, _contract_id),
        (filename_fields, _filename),
        (int_fields, _plain_int),
        (
            positive_int_fields,
            lambda member, member_label: _plain_int(member, member_label, 1),
        ),
        (bool_fields, _plain_bool),
    )
    for fields, decoder in decoders:
        for name in fields:
            decoded[name] = decoder(item[name], name)
    for name in raw_fields:
        decoded[name] = item[name]
    for name in optional_sha_fields:
        member = item[name]
        decoded[name] = None if member is None else _sha256(member, name)
    for name, enum_type in enums.items():
        decoded[name] = _enum_value(enum_type, item[name], name)
    return decoded


def _canonical_mapping(
    source: bytes,
    *,
    expected_sha256: str,
    maximum_bytes: int,
    label: str,
) -> Mapping[str, object]:
    expected = _sha256(expected_sha256, "expected_sha256")
    if type(source) is not bytes or not source or len(source) > maximum_bytes:
        raise QualificationContractError(f"{label} bytes are empty or exceed the cap")
    if sha256_bytes(source) != expected:
        raise QualificationContractError(f"{label} SHA-256 differs")
    try:
        return _mapping(parse_canonical_json(source, label=label), label)
    except CanonicalJsonError as error:
        raise QualificationContractError(str(error)) from error


def _opaque_binding(
    filename: str, contract_id: str, canonical_sha256: str, byte_count: int
) -> dict[str, object]:
    return {
        "filename": filename,
        "contract_id": contract_id,
        "canonical_sha256": canonical_sha256,
        "byte_count": byte_count,
    }


def _decode_opaque_binding(
    value: object, *, filename: str, contract_id: str, label: str
) -> tuple[str, int]:
    item = _decode_record(
        value,
        label=label,
        constants={"filename": filename, "contract_id": contract_id},
        sha_fields=("canonical_sha256",),
        positive_int_fields=("byte_count",),
    )
    return cast(str, item["canonical_sha256"]), cast(int, item["byte_count"])


class _CanonicalRecord:
    _MAX_BYTES: ClassVar[int] = MAX_D7_CHRONOLOGY_RECORD_BYTES
    _LABEL: ClassVar[str] = "D7 structural record"
    _CONSTANTS: ClassVar[Mapping[str, object]] = MappingProxyType({})
    _SHA_FIELDS: ClassVar[tuple[str, ...]] = ()
    _COMMIT_FIELDS: ClassVar[tuple[str, ...]] = ()
    _SLUG_FIELDS: ClassVar[tuple[str, ...]] = ()
    _SCHEMA_FIELDS: ClassVar[tuple[str, ...]] = ()
    _CONTRACT_FIELDS: ClassVar[tuple[str, ...]] = ()
    _FILENAME_FIELDS: ClassVar[tuple[str, ...]] = ()
    _INT_FIELDS: ClassVar[tuple[str, ...]] = ()
    _POSITIVE_INT_FIELDS: ClassVar[tuple[str, ...]] = ()
    _BOOL_FIELDS: ClassVar[tuple[str, ...]] = ()
    _OPTIONAL_SHA_FIELDS: ClassVar[tuple[str, ...]] = ()
    _ENUM_FIELDS: ClassVar[Mapping[str, type[Enum]]] = MappingProxyType({})

    def __post_init__(self) -> None:
        validators = (
            (self._SHA_FIELDS, _sha256),
            (self._COMMIT_FIELDS, _commit),
            (self._SLUG_FIELDS, _slug),
            (self._SCHEMA_FIELDS, _schema_version),
            (self._CONTRACT_FIELDS, _contract_id),
            (self._FILENAME_FIELDS, _filename),
            (self._INT_FIELDS, _plain_int),
            (
                self._POSITIVE_INT_FIELDS,
                lambda value, label: _plain_int(value, label, 1),
            ),
            (self._BOOL_FIELDS, _plain_bool),
        )
        for fields, validator in validators:
            for name in fields:
                validator(getattr(self, name), name)
        for name in self._OPTIONAL_SHA_FIELDS:
            value = getattr(self, name)
            if value is not None:
                _sha256(value, name)
        for name, enum_type in self._ENUM_FIELDS.items():
            if not isinstance(getattr(self, name), enum_type):
                raise TypeError(f"{name} must be a {enum_type.__name__}")

    def to_dict(self) -> dict[str, object]:
        document = _json_constants(self._CONSTANTS)
        groups = (
            self._SHA_FIELDS,
            self._COMMIT_FIELDS,
            self._SLUG_FIELDS,
            self._SCHEMA_FIELDS,
            self._CONTRACT_FIELDS,
            self._FILENAME_FIELDS,
            self._INT_FIELDS,
            self._POSITIVE_INT_FIELDS,
            self._BOOL_FIELDS,
            self._OPTIONAL_SHA_FIELDS,
        )
        for name in (field for group in groups for field in group):
            document[name] = getattr(self, name)
        for name in self._ENUM_FIELDS:
            document[name] = getattr(self, name).value
        return document

    @property
    def canonical_bytes(self) -> bytes:
        payload = canonical_json_bytes(self.to_dict())
        if len(payload) > self._MAX_BYTES:
            raise QualificationContractError(f"{self._LABEL} exceeds its byte cap")
        return payload

    @property
    def canonical_sha256(self) -> str:
        return sha256_bytes(self.canonical_bytes)

    @classmethod
    def from_dict(cls, value: object) -> Self:
        values = _decode_record(
            value,
            label=cls._LABEL,
            constants=cls._CONSTANTS,
            sha_fields=cls._SHA_FIELDS,
            commit_fields=cls._COMMIT_FIELDS,
            slug_fields=cls._SLUG_FIELDS,
            schema_fields=cls._SCHEMA_FIELDS,
            contract_fields=cls._CONTRACT_FIELDS,
            filename_fields=cls._FILENAME_FIELDS,
            int_fields=cls._INT_FIELDS,
            positive_int_fields=cls._POSITIVE_INT_FIELDS,
            bool_fields=cls._BOOL_FIELDS,
            optional_sha_fields=cls._OPTIONAL_SHA_FIELDS,
            enum_fields=cls._ENUM_FIELDS,
        )
        return cls(**values)  # type: ignore[arg-type]

    @classmethod
    def from_canonical_bytes(cls, source: bytes, *, expected_sha256: str) -> Self:
        document = _canonical_mapping(
            source,
            expected_sha256=expected_sha256,
            maximum_bytes=cls._MAX_BYTES,
            label=cls._LABEL,
        )
        result = cls.from_dict(document)
        if result.canonical_bytes != source:
            raise QualificationContractError(
                f"{cls._LABEL} differs from reconstructed canonical bytes"
            )
        return result


def _validate_sha_fields(value: object, *names: str) -> None:
    for name in names:
        _sha256(getattr(value, name), name)


def d7_attempt_key_sha256(
    *, replay_target_sha256: str, attempt_role: D7AttemptRole
) -> str:
    target = _sha256(replay_target_sha256, "replay_target_sha256")
    if not isinstance(attempt_role, D7AttemptRole):
        raise TypeError("attempt_role must be a D7AttemptRole")
    return canonical_json_sha256(
        {
            "scheme": D7_ATTEMPT_KEY_SCHEME,
            "replay_target_sha256": target,
            "attempt_role": attempt_role.value,
        }
    )


@dataclass(frozen=True, slots=True)
class D7PrimaryRoleEvidence(_CanonicalRecord):
    schema_version: ClassVar[str] = D7_PRIMARY_ROLE_EVIDENCE_SCHEMA_VERSION
    attempt_role: ClassVar[D7AttemptRole] = D7AttemptRole.PRIMARY_CONFIRMATION
    _LABEL: ClassVar[str] = "D7 primary role evidence"
    _CONSTANTS = _record_constants(schema_version, attempt_role=attempt_role.value)


@dataclass(frozen=True, slots=True)
class D7IsolatedReplayRoleEvidence(_CanonicalRecord):
    primary_replay_target_sha256: str
    primary_attempt_key_sha256: str
    primary_attempt_declaration_sha256: str
    primary_launch_authorization_sha256: str
    primary_attempt_claim_sha256: str
    primary_execution_start_sha256: str
    primary_result_payload_sha256: str
    primary_scientific_result_sha256: str
    primary_terminal_manifest_sha256: str
    primary_terminal_consumption_sha256: str

    schema_version: ClassVar[str] = D7_ISOLATED_REPLAY_ROLE_EVIDENCE_SCHEMA_VERSION
    attempt_role: ClassVar[D7AttemptRole] = D7AttemptRole.ISOLATED_BYTE_REPLAY
    _LABEL: ClassVar[str] = "D7 isolated replay role evidence"
    _CONSTANTS = _record_constants(schema_version, attempt_role=attempt_role.value)
    _SHA_FIELDS: ClassVar[tuple[str, ...]] = _names(
        "primary_replay_target_sha256 primary_attempt_key_sha256 "
        "primary_attempt_declaration_sha256 primary_launch_authorization_sha256 "
        "primary_attempt_claim_sha256 primary_execution_start_sha256 "
        "primary_result_payload_sha256 primary_scientific_result_sha256 "
        "primary_terminal_manifest_sha256 primary_terminal_consumption_sha256"
    )

    def __post_init__(self) -> None:
        _CanonicalRecord.__post_init__(self)
        expected = d7_attempt_key_sha256(
            replay_target_sha256=self.primary_replay_target_sha256,
            attempt_role=D7AttemptRole.PRIMARY_CONFIRMATION,
        )
        if self.primary_attempt_key_sha256 != expected:
            raise QualificationContractError(
                "primary attempt key differs from target and primary role"
            )


D7AttemptRoleEvidence: TypeAlias = D7PrimaryRoleEvidence | D7IsolatedReplayRoleEvidence


def _role_evidence(value: object) -> D7AttemptRoleEvidence:
    item = _mapping(value, "D7 attempt role evidence")
    role = item.get("attempt_role")
    if role == D7AttemptRole.PRIMARY_CONFIRMATION.value:
        return D7PrimaryRoleEvidence.from_dict(item)
    if role == D7AttemptRole.ISOLATED_BYTE_REPLAY.value:
        return D7IsolatedReplayRoleEvidence.from_dict(item)
    raise QualificationContractError("D7 attempt role evidence is unsupported")


@dataclass(frozen=True, slots=True)
class D7AttemptDeclarationRecord(_CanonicalRecord):
    replay_target_sha256: str
    launch_intent_sha256: str
    role_evidence: D7AttemptRoleEvidence
    store_identity_sha256: str
    output_namespace_identity_sha256: str
    terminal_path_identity_sha256: str
    authorization_commit: str
    execution_identity_receipt_sha256: str

    schema_version: ClassVar[str] = D7_ATTEMPT_DECLARATION_SCHEMA_VERSION
    claim_ceiling: ClassVar[str] = D7_RECORD_CLAIM_CEILING
    _LABEL: ClassVar[str] = "D7 attempt declaration"
    _SHA_FIELDS: ClassVar[tuple[str, ...]] = _names(
        "replay_target_sha256 launch_intent_sha256 store_identity_sha256 "
        "output_namespace_identity_sha256 terminal_path_identity_sha256 "
        "execution_identity_receipt_sha256"
    )
    _COMMIT_FIELDS: ClassVar[tuple[str, ...]] = ("authorization_commit",)

    def __post_init__(self) -> None:
        _CanonicalRecord.__post_init__(self)
        if type(self.role_evidence) not in {
            D7PrimaryRoleEvidence,
            D7IsolatedReplayRoleEvidence,
        }:
            raise TypeError("role_evidence must be typed D7 role evidence")
        if (
            isinstance(self.role_evidence, D7IsolatedReplayRoleEvidence)
            and self.replay_target_sha256
            != self.role_evidence.primary_replay_target_sha256
        ):
            raise QualificationContractError(
                "isolated replay must reuse the consumed primary target"
            )

    @property
    def attempt_role(self) -> D7AttemptRole:
        return self.role_evidence.attempt_role

    @property
    def attempt_key_sha256(self) -> str:
        return d7_attempt_key_sha256(
            replay_target_sha256=self.replay_target_sha256,
            attempt_role=self.attempt_role,
        )

    def to_dict(self) -> dict[str, object]:
        return _record_document(
            self,
            "attempt-declaration",
            self._SHA_FIELDS,
            attempt_role=self.attempt_role.value,
            role_evidence=self.role_evidence.to_dict(),
            attempt_key_sha256=self.attempt_key_sha256,
            authorization_commit=self.authorization_commit,
        )

    @classmethod
    def from_dict(cls, value: object) -> Self:
        values = _decode_record(
            value,
            label=cls._LABEL,
            constants=_record_constants(
                cls.schema_version,
                "attempt-declaration",
                claim_ceiling=cls.claim_ceiling,
            ),
            sha_fields=(*cls._SHA_FIELDS, "attempt_key_sha256"),
            commit_fields=("authorization_commit",),
            raw_fields=("attempt_role", "role_evidence"),
        )
        evidence = _role_evidence(values.pop("role_evidence"))
        role = _enum_value(D7AttemptRole, values.pop("attempt_role"), "attempt_role")
        if role is not evidence.attempt_role:
            raise QualificationContractError("attempt_role differs from role evidence")
        recorded_key = cast(str, values.pop("attempt_key_sha256"))
        result = cls(role_evidence=evidence, **values)  # type: ignore[arg-type]
        if recorded_key != result.attempt_key_sha256:
            raise QualificationContractError("attempt_key_sha256 differs")
        return result


@dataclass(frozen=True, slots=True)
class D7LaunchAuthorizationRecord(_CanonicalRecord):
    attempt_declaration_sha256: str
    replay_target_sha256: str
    attempt_key_sha256: str
    authorization_commit: str
    execution_identity_receipt_sha256: str
    execution_source_runtime_receipt_sha256: str
    runtime_specification_sha256: str
    admission_receipt_sha256: str
    full_design_freeze_receipt_sha256: str
    store_identity_sha256: str
    output_namespace_identity_sha256: str
    terminal_path_identity_sha256: str
    authorization_output_namespace_absence_receipt_sha256: str
    authorization_terminal_path_absence_receipt_sha256: str

    schema_version: ClassVar[str] = D7_LAUNCH_AUTHORIZATION_SCHEMA_VERSION
    claim_ceiling: ClassVar[str] = D7_RECORD_CLAIM_CEILING
    _LABEL: ClassVar[str] = "D7 launch authorization"
    _CONSTANTS = _record_constants(
        schema_version,
        "launch-authorization",
        claim_ceiling=claim_ceiling,
        policy_override_allowed=False,
        post_selection_exclusion_allowed=False,
    )
    _SHA_FIELDS: ClassVar[tuple[str, ...]] = _names(
        "attempt_declaration_sha256 replay_target_sha256 attempt_key_sha256 "
        "execution_identity_receipt_sha256 execution_source_runtime_receipt_sha256 "
        "runtime_specification_sha256 admission_receipt_sha256 "
        "full_design_freeze_receipt_sha256 store_identity_sha256 "
        "output_namespace_identity_sha256 terminal_path_identity_sha256 "
        "authorization_output_namespace_absence_receipt_sha256 "
        "authorization_terminal_path_absence_receipt_sha256"
    )
    _COMMIT_FIELDS: ClassVar[tuple[str, ...]] = ("authorization_commit",)

    def __post_init__(self) -> None:
        _CanonicalRecord.__post_init__(self)
        semantic_receipts = {
            self.execution_identity_receipt_sha256,
            self.execution_source_runtime_receipt_sha256,
            self.runtime_specification_sha256,
        }
        if len(semantic_receipts) != 3:
            raise QualificationContractError(
                "execution identity, source/runtime, and runtime spec must differ"
            )
        if (
            self.authorization_output_namespace_absence_receipt_sha256
            == self.authorization_terminal_path_absence_receipt_sha256
        ):
            raise QualificationContractError(
                "authorization absence receipts must be distinct"
            )


@dataclass(frozen=True, slots=True)
class D7AttemptClaimRecord(_CanonicalRecord):
    attempt_declaration_sha256: str
    launch_authorization_sha256: str
    replay_target_sha256: str
    attempt_key_sha256: str
    execution_identity_receipt_sha256: str
    store_identity_sha256: str

    schema_version: ClassVar[str] = D7_ATTEMPT_CLAIM_SCHEMA_VERSION
    claim_ceiling: ClassVar[str] = D7_RECORD_CLAIM_CEILING
    _LABEL: ClassVar[str] = "D7 attempt claim"
    _CONSTANTS = _record_constants(
        schema_version,
        "exclusive-attempt-claim",
        claim_ceiling=claim_ceiling,
        exclusive_claim_acquired=True,
        reopen_authorized=False,
        retry_authorized=False,
    )
    _SHA_FIELDS: ClassVar[tuple[str, ...]] = _names(
        "attempt_declaration_sha256 launch_authorization_sha256 "
        "replay_target_sha256 attempt_key_sha256 "
        "execution_identity_receipt_sha256 store_identity_sha256"
    )


@dataclass(frozen=True, slots=True)
class D7ExecutionStartRecord(_CanonicalRecord):
    attempt_declaration_sha256: str
    launch_authorization_sha256: str
    attempt_claim_sha256: str
    replay_target_sha256: str
    attempt_key_sha256: str
    authorization_commit: str
    execution_identity_receipt_sha256: str
    observed_execution_identity_receipt_sha256: str
    observed_execution_source_runtime_receipt_sha256: str
    observed_runtime_specification_sha256: str
    output_namespace_identity_sha256: str
    terminal_path_identity_sha256: str
    pre_start_output_namespace_absence_receipt_sha256: str
    pre_start_terminal_path_absence_receipt_sha256: str

    schema_version: ClassVar[str] = D7_EXECUTION_START_SCHEMA_VERSION
    claim_ceiling: ClassVar[str] = D7_RECORD_CLAIM_CEILING
    _LABEL: ClassVar[str] = "D7 execution start"
    _CONSTANTS = _record_constants(
        schema_version,
        "execution-start",
        claim_ceiling=claim_ceiling,
        execution_started=True,
        reopen_authorized=False,
        retry_authorized=False,
    )
    _SHA_FIELDS: ClassVar[tuple[str, ...]] = _names(
        "attempt_declaration_sha256 launch_authorization_sha256 "
        "attempt_claim_sha256 replay_target_sha256 attempt_key_sha256 "
        "execution_identity_receipt_sha256 observed_execution_identity_receipt_sha256 "
        "observed_execution_source_runtime_receipt_sha256 "
        "observed_runtime_specification_sha256 output_namespace_identity_sha256 "
        "terminal_path_identity_sha256 pre_start_output_namespace_absence_receipt_sha256 "
        "pre_start_terminal_path_absence_receipt_sha256"
    )
    _COMMIT_FIELDS: ClassVar[tuple[str, ...]] = ("authorization_commit",)

    def __post_init__(self) -> None:
        _CanonicalRecord.__post_init__(self)
        if (
            self.observed_execution_identity_receipt_sha256
            != self.execution_identity_receipt_sha256
        ):
            raise QualificationContractError(
                "observed execution identity differs from frozen identity"
            )
        if (
            len(
                {
                    self.execution_identity_receipt_sha256,
                    self.observed_execution_source_runtime_receipt_sha256,
                    self.observed_runtime_specification_sha256,
                }
            )
            != 3
        ):
            raise QualificationContractError(
                "execution identity, source/runtime, and runtime spec must differ"
            )
        if (
            self.pre_start_output_namespace_absence_receipt_sha256
            == self.pre_start_terminal_path_absence_receipt_sha256
        ):
            raise QualificationContractError("pre-start absence receipts must differ")


@dataclass(frozen=True, slots=True)
class D7GateOutcomeSummary(_CanonicalRecord):
    gate_manifest_sha256: str
    required_gate_count: int
    pass_count: int
    fail_count: int
    insufficient_count: int
    not_run_count: int
    aggregate_state: D7ScientificResultState
    gate_results_component_sha256: str

    schema_version: ClassVar[str] = D7_GATE_OUTCOME_SUMMARY_SCHEMA_VERSION
    _LABEL: ClassVar[str] = "D7 gate outcome summary"
    _CONSTANTS = _record_constants(
        schema_version, gate_state_vocabulary=[state.value for state in D7GateState]
    )
    _SHA_FIELDS = _names("gate_manifest_sha256 gate_results_component_sha256")
    _INT_FIELDS = _names("pass_count fail_count insufficient_count not_run_count")
    _POSITIVE_INT_FIELDS: ClassVar[tuple[str, ...]] = ("required_gate_count",)
    _ENUM_FIELDS: ClassVar[Mapping[str, type[Enum]]] = MappingProxyType(
        {"aggregate_state": D7ScientificResultState}
    )

    def __post_init__(self) -> None:
        _CanonicalRecord.__post_init__(self)
        counts = (
            self.pass_count,
            self.fail_count,
            self.insufficient_count,
            self.not_run_count,
        )
        if sum(counts) != self.required_gate_count:
            raise QualificationContractError(
                "gate counts must sum to required_gate_count"
            )
        expected = (
            D7ScientificResultState.FAIL
            if self.fail_count
            else D7ScientificResultState.INSUFFICIENT
            if self.insufficient_count or self.not_run_count
            else D7ScientificResultState.PASS
        )
        if self.aggregate_state is not expected:
            raise QualificationContractError(
                "aggregate_state differs from four-valued gate counts"
            )

    @classmethod
    def from_gate_states(
        cls,
        *,
        gate_manifest_sha256: str,
        gate_states: tuple[D7GateState, ...],
        gate_results_component_sha256: str,
    ) -> Self:
        if not gate_states or any(
            type(state) is not D7GateState for state in gate_states
        ):
            raise QualificationContractError(
                "gate_states must contain exact D7GateState values"
            )
        counts = {state: gate_states.count(state) for state in D7GateState}
        aggregate = (
            D7ScientificResultState.FAIL
            if counts[D7GateState.FAIL]
            else D7ScientificResultState.INSUFFICIENT
            if counts[D7GateState.INSUFFICIENT] or counts[D7GateState.NOT_RUN]
            else D7ScientificResultState.PASS
        )
        return cls(
            gate_manifest_sha256=gate_manifest_sha256,
            required_gate_count=len(gate_states),
            pass_count=counts[D7GateState.PASS],
            fail_count=counts[D7GateState.FAIL],
            insufficient_count=counts[D7GateState.INSUFFICIENT],
            not_run_count=counts[D7GateState.NOT_RUN],
            aggregate_state=aggregate,
            gate_results_component_sha256=gate_results_component_sha256,
        )


@dataclass(frozen=True, slots=True)
class D7ResultComponentBinding(_CanonicalRecord):
    component_id: D7ResultComponentId
    component_contract_id: str
    component_canonical_sha256: str
    byte_count: int
    record_count: int

    schema_version: ClassVar[str] = D7_RESULT_COMPONENT_BINDING_SCHEMA_VERSION
    _LABEL: ClassVar[str] = "D7 result component binding"

    def __post_init__(self) -> None:
        if not isinstance(self.component_id, D7ResultComponentId):
            raise TypeError("component_id must be a D7ResultComponentId")
        expected_contract = D7_RESULT_COMPONENT_CONTRACT_IDS[self.component_id]
        if self.component_contract_id != expected_contract:
            raise QualificationContractError(
                "component_contract_id differs from fixed component contract"
            )
        _sha256(self.component_canonical_sha256, "component_canonical_sha256")
        _plain_int(self.byte_count, "byte_count", 1)
        _plain_int(self.record_count, "record_count", 1)
        if self.byte_count > MAX_D7_RESULT_COMPONENT_BYTES:
            raise QualificationContractError("result component exceeds byte cap")
        expected_count = D7_RESULT_COMPONENT_FIXED_RECORD_COUNTS.get(self.component_id)
        if expected_count is not None and self.record_count != expected_count:
            raise QualificationContractError(
                "record_count differs from fixed component inventory"
            )

    @property
    def filename(self) -> str:
        return _RESULT_COMPONENT_FILENAMES[self.component_id]

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "component_id": self.component_id.value,
            "component_contract_id": self.component_contract_id,
            "filename": self.filename,
            "canonical_sha256": self.component_canonical_sha256,
            "byte_count": self.byte_count,
            "record_count": self.record_count,
        }

    @classmethod
    def from_dict(cls, value: object) -> Self:
        values = _decode_record(
            value,
            label=cls._LABEL,
            constants={"schema_version": cls.schema_version},
            contract_fields=("component_contract_id",),
            sha_fields=("canonical_sha256",),
            positive_int_fields=("byte_count", "record_count"),
            raw_fields=("component_id", "filename"),
        )
        component_id = _pop_enum(values, "component_id", D7ResultComponentId)
        filename = values.pop("filename")
        values["component_id"] = component_id
        values["component_canonical_sha256"] = values.pop("canonical_sha256")
        result = cls(**values)  # type: ignore[arg-type]
        if filename != result.filename:
            raise QualificationContractError("filename differs from component_id")
        return result


def _result_schema_descriptor() -> dict[str, object]:
    component_semantics = {
        D7ResultComponentId.EXECUTION_EVENT_LEDGER: "one record per frozen event lane; 1344 lanes, not 8064 events",
        D7ResultComponentId.CORE_CELL_OUTCOMES: "one record per frozen core cell",
        D7ResultComponentId.LOOP_CELL_OUTCOMES: "one record per frozen loop cell",
        D7ResultComponentId.PRIMARY_UNIT_OUTCOMES: "one record per frozen primary unit",
        D7ResultComponentId.REQUIRED_STRATUM_OUTCOMES: "one record per frozen required stratum",
        D7ResultComponentId.AGGREGATE_GATE_OUTCOMES: "one record per required gate in the target-bound gate manifest",
    }
    return {
        "schema_version": D7_RESULT_SCHEMA_DESCRIPTOR_VERSION,
        "payload_schema_version": D7_SCIENTIFIC_RESULT_PAYLOAD_SCHEMA_VERSION,
        "gate_summary_schema_version": D7_GATE_OUTCOME_SUMMARY_SCHEMA_VERSION,
        "component_binding_schema_version": D7_RESULT_COMPONENT_BINDING_SCHEMA_VERSION,
        "record_scope": D7_RESULT_RECORD_SCOPE,
        "claim_ceiling": D7_RECORD_CLAIM_CEILING,
        "payload_fields": [
            "schema_version",
            "record_kind",
            "record_scope",
            "claim_ceiling",
            "replay_target_sha256",
            "full_inventory_sha256",
            "aggregation_sha256",
            "result_schema_sha256",
            "state",
            "reason_codes",
            "gate_summary",
            "component_bindings",
            "result_evidence_root_sha256",
        ],
        "terminal_result_states": ["pass", "fail", "insufficient"],
        "overall_not_run_allowed": False,
        "gate_state_vocabulary": ["pass", "fail", "insufficient", "not_run"],
        "gate_aggregation_precedence": [
            "any-fail-to-fail",
            "else-any-insufficient-or-not-run-to-insufficient",
            "else-pass",
        ],
        "reason_code_policy": {
            "canonical_unique_sorted": True,
            "pass_requires_empty": True,
            "fail_or_insufficient_requires_nonempty": True,
        },
        "component_contracts": [
            {
                "component_id": component_id.value,
                "filename": _RESULT_COMPONENT_FILENAMES[component_id],
                "contract_id": D7_RESULT_COMPONENT_CONTRACT_IDS[component_id],
                "record_count": D7_RESULT_COMPONENT_FIXED_RECORD_COUNTS.get(
                    component_id, "gate_summary.required_gate_count"
                ),
                "record_count_semantics": component_semantics[component_id],
            }
            for component_id in D7_RESULT_COMPONENT_ORDER
        ],
        "component_order": [item.value for item in D7_RESULT_COMPONENT_ORDER],
        "evidence_root_scheme": D7_RESULT_EVIDENCE_ROOT_SCHEME,
        "attempt_independent": True,
        "maximum_payload_bytes": MAX_D7_RESULT_PAYLOAD_BYTES,
        "maximum_component_bytes": MAX_D7_RESULT_COMPONENT_BYTES,
    }


D7_SCIENTIFIC_RESULT_IMPLEMENTATION_SCHEMA_SHA256 = canonical_json_sha256(
    _result_schema_descriptor()
)


def _reason_codes(
    values: tuple[str, ...], state: D7ScientificResultState
) -> tuple[str, ...]:
    if type(values) is not tuple:
        raise TypeError("reason_codes must be a tuple")
    for index, value in enumerate(values):
        _slug(value, f"reason_codes[{index}]")
    if values != tuple(sorted(set(values))):
        raise QualificationContractError("reason_codes must be unique and sorted")
    if state is D7ScientificResultState.PASS and values:
        raise QualificationContractError("pass requires empty reason_codes")
    if state is not D7ScientificResultState.PASS and not values:
        raise QualificationContractError(
            "fail or insufficient requires at least one reason code"
        )
    return values


@dataclass(frozen=True, slots=True)
class D7ScientificResultPayload(_CanonicalRecord):
    replay_target_sha256: str
    full_inventory_sha256: str
    aggregation_sha256: str
    state: D7ScientificResultState
    reason_codes: tuple[str, ...]
    gate_summary: D7GateOutcomeSummary
    component_bindings: tuple[D7ResultComponentBinding, ...]

    schema_version: ClassVar[str] = D7_SCIENTIFIC_RESULT_PAYLOAD_SCHEMA_VERSION
    claim_ceiling: ClassVar[str] = D7_RECORD_CLAIM_CEILING
    record_scope: ClassVar[str] = D7_RESULT_RECORD_SCOPE
    result_schema_sha256: ClassVar[str] = (
        D7_SCIENTIFIC_RESULT_IMPLEMENTATION_SCHEMA_SHA256
    )
    _LABEL: ClassVar[str] = "D7 scientific result payload"
    _MAX_BYTES: ClassVar[int] = MAX_D7_RESULT_PAYLOAD_BYTES
    _SHA_FIELDS = _names(
        "replay_target_sha256 full_inventory_sha256 aggregation_sha256"
    )
    _ENUM_FIELDS: ClassVar[Mapping[str, type[Enum]]] = MappingProxyType(
        {"state": D7ScientificResultState}
    )

    def __post_init__(self) -> None:
        _CanonicalRecord.__post_init__(self)
        _reason_codes(self.reason_codes, self.state)
        if type(self.gate_summary) is not D7GateOutcomeSummary:
            raise TypeError("gate_summary must be a D7GateOutcomeSummary")
        if self.state is not self.gate_summary.aggregate_state:
            raise QualificationContractError("state differs from gate summary")
        if type(self.component_bindings) is not tuple or any(
            type(binding) is not D7ResultComponentBinding
            for binding in self.component_bindings
        ):
            raise TypeError("component_bindings must be typed tuple")
        if (
            tuple(binding.component_id for binding in self.component_bindings)
            != D7_RESULT_COMPONENT_ORDER
        ):
            raise QualificationContractError(
                "component_bindings differ from fixed ordered inventory"
            )
        aggregate = self.component_bindings[-1]
        if (
            aggregate.component_canonical_sha256
            != self.gate_summary.gate_results_component_sha256
            or aggregate.record_count != self.gate_summary.required_gate_count
        ):
            raise QualificationContractError(
                "aggregate-gate component differs from gate summary"
            )

    @property
    def result_evidence_root_sha256(self) -> str:
        return canonical_json_sha256(
            {
                "scheme": D7_RESULT_EVIDENCE_ROOT_SCHEME,
                "record_scope": self.record_scope,
                "claim_ceiling": self.claim_ceiling,
                "replay_target_sha256": self.replay_target_sha256,
                "full_inventory_sha256": self.full_inventory_sha256,
                "aggregation_sha256": self.aggregation_sha256,
                "result_schema_sha256": self.result_schema_sha256,
                "state": self.state.value,
                "reason_codes": list(self.reason_codes),
                "gate_summary": self.gate_summary.to_dict(),
                "component_bindings": [
                    binding.to_dict() for binding in self.component_bindings
                ],
            }
        )

    def to_dict(self) -> dict[str, object]:
        return _record_document(
            self,
            "scientific-result-payload",
            self._SHA_FIELDS,
            record_scope=self.record_scope,
            result_schema_sha256=self.result_schema_sha256,
            state=self.state.value,
            reason_codes=list(self.reason_codes),
            gate_summary=self.gate_summary.to_dict(),
            component_bindings=[item.to_dict() for item in self.component_bindings],
            result_evidence_root_sha256=self.result_evidence_root_sha256,
        )

    @classmethod
    def from_dict(cls, value: object) -> Self:
        values = _decode_record(
            value,
            label=cls._LABEL,
            constants=_record_constants(
                cls.schema_version,
                "scientific-result-payload",
                claim_ceiling=cls.claim_ceiling,
                record_scope=cls.record_scope,
                result_schema_sha256=cls.result_schema_sha256,
            ),
            sha_fields=(
                "replay_target_sha256",
                "full_inventory_sha256",
                "aggregation_sha256",
                "result_evidence_root_sha256",
            ),
            raw_fields=("state", "reason_codes", "gate_summary", "component_bindings"),
        )
        recorded_root = cast(str, values.pop("result_evidence_root_sha256"))
        values["state"] = _pop_enum(values, "state", D7ScientificResultState)
        values["reason_codes"] = tuple(
            _slug(member, "reason code")
            for member in _sequence(values["reason_codes"], "reason_codes")
        )
        values["gate_summary"] = D7GateOutcomeSummary.from_dict(values["gate_summary"])
        values["component_bindings"] = tuple(
            D7ResultComponentBinding.from_dict(member)
            for member in _sequence(values["component_bindings"], "component_bindings")
        )
        result = cls(**values)  # type: ignore[arg-type]
        if recorded_root != result.result_evidence_root_sha256:
            raise QualificationContractError("result_evidence_root_sha256 differs")
        return result


@dataclass(frozen=True, slots=True)
class D7ScientificResultRecord(_CanonicalRecord):
    replay_target_sha256: str
    attempt_key_sha256: str
    execution_start_sha256: str
    execution_identity_receipt_sha256: str
    result_payload_sha256: str
    result_payload_byte_count: int

    schema_version: ClassVar[str] = D7_SCIENTIFIC_RESULT_SCHEMA_VERSION
    claim_ceiling: ClassVar[str] = D7_RECORD_CLAIM_CEILING
    _LABEL: ClassVar[str] = "D7 scientific result"
    _CONSTANTS = _record_constants(
        schema_version,
        "scientific-result",
        claim_ceiling=claim_ceiling,
        terminal_artifact_kind=D7TerminalArtifactKind.SCIENTIFIC_RESULT.value,
    )
    _SHA_FIELDS = (*_STARTED_COORDINATE_FIELDS, "result_payload_sha256")
    _POSITIVE_INT_FIELDS: ClassVar[tuple[str, ...]] = ("result_payload_byte_count",)

    def __post_init__(self) -> None:
        _CanonicalRecord.__post_init__(self)
        if self.result_payload_byte_count > MAX_D7_RESULT_PAYLOAD_BYTES:
            raise QualificationContractError("result payload byte count exceeds cap")


@dataclass(frozen=True, slots=True)
class D7FailureEvidenceRecord(_CanonicalRecord):
    replay_target_sha256: str
    attempt_key_sha256: str
    execution_start_sha256: str
    execution_identity_receipt_sha256: str
    failure_stage: D7FailureStage
    origin: D7FailureEvidenceOrigin
    reason_code: str
    evidence_payload_sha256: str
    evidence_payload_byte_count: int
    external_verification_receipt_sha256: str | None
    external_verification_receipt_byte_count: int | None

    schema_version: ClassVar[str] = D7_FAILURE_EVIDENCE_SCHEMA_VERSION
    claim_ceiling: ClassVar[str] = D7_RECORD_CLAIM_CEILING
    _LABEL: ClassVar[str] = "D7 failure evidence"
    _SHA_FIELDS = (*_STARTED_COORDINATE_FIELDS, "evidence_payload_sha256")
    _OPTIONAL_SHA_FIELDS = ("external_verification_receipt_sha256",)
    _SLUG_FIELDS: ClassVar[tuple[str, ...]] = ("reason_code",)
    _POSITIVE_INT_FIELDS: ClassVar[tuple[str, ...]] = ("evidence_payload_byte_count",)
    _ENUM_FIELDS: ClassVar[Mapping[str, type[Enum]]] = MappingProxyType(
        {
            "failure_stage": D7FailureStage,
            "origin": D7FailureEvidenceOrigin,
        }
    )

    def __post_init__(self) -> None:
        _CanonicalRecord.__post_init__(self)
        is_abort = self.failure_stage is D7FailureStage.EVIDENCED_ABORT
        is_external = self.origin is D7FailureEvidenceOrigin.EXTERNAL
        has_receipt = self.external_verification_receipt_sha256 is not None
        has_receipt_size = self.external_verification_receipt_byte_count is not None
        if not (is_abort == is_external == has_receipt == has_receipt_size):
            raise QualificationContractError(
                "evidenced abort requires external origin and verification receipt"
            )
        if self.evidence_payload_byte_count > MAX_D7_RESULT_COMPONENT_BYTES:
            raise QualificationContractError(
                "failure evidence payload exceeds byte cap"
            )
        if has_receipt:
            receipt = _sha256(
                self.external_verification_receipt_sha256,
                "external_verification_receipt_sha256",
            )
            if receipt == self.evidence_payload_sha256:
                raise QualificationContractError(
                    "external verification receipt must be distinct from evidence"
                )
            receipt_size = _plain_int(
                self.external_verification_receipt_byte_count,
                "external_verification_receipt_byte_count",
                1,
            )
            if receipt_size > MAX_D7_RESULT_COMPONENT_BYTES:
                raise QualificationContractError(
                    "external verification receipt exceeds byte cap"
                )

    def to_dict(self) -> dict[str, object]:
        return _record_document(
            self,
            "failure-evidence",
            _STARTED_COORDINATE_FIELDS,
            failure_stage=self.failure_stage.value,
            origin=self.origin.value,
            reason_code=self.reason_code,
            evidence_payload=_opaque_binding(
                D7_FAILURE_EVIDENCE_PAYLOAD_FILENAME,
                D7_FAILURE_EVIDENCE_PAYLOAD_CONTRACT_ID,
                self.evidence_payload_sha256,
                self.evidence_payload_byte_count,
            ),
            external_verification_receipt=(
                None
                if self.external_verification_receipt_sha256 is None
                else _opaque_binding(
                    D7_EXTERNAL_ABORT_VERIFICATION_RECEIPT_FILENAME,
                    D7_EXTERNAL_ABORT_VERIFICATION_RECEIPT_CONTRACT_ID,
                    self.external_verification_receipt_sha256,
                    cast(int, self.external_verification_receipt_byte_count),
                )
            ),
        )

    @classmethod
    def from_dict(cls, value: object) -> Self:
        values = _decode_record(
            value,
            label=cls._LABEL,
            constants=_record_constants(
                cls.schema_version, "failure-evidence", claim_ceiling=cls.claim_ceiling
            ),
            sha_fields=_STARTED_COORDINATE_FIELDS,
            slug_fields=("reason_code",),
            raw_fields=(
                "failure_stage",
                "origin",
                "evidence_payload",
                "external_verification_receipt",
            ),
        )
        values["failure_stage"] = _pop_enum(values, "failure_stage", D7FailureStage)
        values["origin"] = _pop_enum(values, "origin", D7FailureEvidenceOrigin)
        evidence_sha, evidence_size = _decode_opaque_binding(
            values.pop("evidence_payload"),
            filename=D7_FAILURE_EVIDENCE_PAYLOAD_FILENAME,
            contract_id=D7_FAILURE_EVIDENCE_PAYLOAD_CONTRACT_ID,
            label="evidence_payload",
        )
        values["evidence_payload_sha256"] = evidence_sha
        values["evidence_payload_byte_count"] = evidence_size
        receipt_document = values.pop("external_verification_receipt")
        if receipt_document is None:
            values["external_verification_receipt_sha256"] = None
            values["external_verification_receipt_byte_count"] = None
        else:
            receipt_sha, receipt_size = _decode_opaque_binding(
                receipt_document,
                filename=D7_EXTERNAL_ABORT_VERIFICATION_RECEIPT_FILENAME,
                contract_id=D7_EXTERNAL_ABORT_VERIFICATION_RECEIPT_CONTRACT_ID,
                label="external_verification_receipt",
            )
            values["external_verification_receipt_sha256"] = receipt_sha
            values["external_verification_receipt_byte_count"] = receipt_size
        return cls(**values)  # type: ignore[arg-type]


@dataclass(frozen=True, slots=True)
class D7StartedUnresolvedFinalizationRecord(_CanonicalRecord):
    replay_target_sha256: str
    attempt_key_sha256: str
    execution_start_sha256: str
    execution_identity_receipt_sha256: str
    external_abort_evidence_sha256: str
    external_verification_receipt_sha256: str
    external_verification_receipt_byte_count: int

    schema_version: ClassVar[str] = D7_STARTED_UNRESOLVED_FINALIZATION_SCHEMA_VERSION
    claim_ceiling: ClassVar[str] = D7_RECORD_CLAIM_CEILING
    _LABEL: ClassVar[str] = "D7 started-unresolved finalization"
    _SHA_FIELDS = (
        *_STARTED_COORDINATE_FIELDS,
        *_names("external_abort_evidence_sha256 external_verification_receipt_sha256"),
    )
    _POSITIVE_INT_FIELDS = ("external_verification_receipt_byte_count",)

    def __post_init__(self) -> None:
        _CanonicalRecord.__post_init__(self)
        if (
            self.external_verification_receipt_byte_count
            > MAX_D7_RESULT_COMPONENT_BYTES
        ):
            raise QualificationContractError(
                "external verification receipt exceeds byte cap"
            )
        if (
            self.external_abort_evidence_sha256
            == self.external_verification_receipt_sha256
        ):
            raise QualificationContractError(
                "external evidence and verification receipt must be distinct"
            )

    def to_dict(self) -> dict[str, object]:
        return _record_document(
            self,
            "started-unresolved-finalization",
            self._SHA_FIELDS,
            finalization_kind="externally-evidenced-abort",
            external_verification_receipt_byte_count=self.external_verification_receipt_byte_count,
            verification_receipt_required_assertions={
                "execution_start_sha256": self.execution_start_sha256,
                "execution_identity_receipt_sha256": self.execution_identity_receipt_sha256,
                "aggregate_outcome_observed": False,
            },
            started_unresolved_finalized=True,
            retry_authorized=False,
            replay_authorized=False,
            d8_eligible=False,
        )

    @classmethod
    def from_dict(cls, value: object) -> Self:
        values = _decode_record(
            value,
            label=cls._LABEL,
            constants=_record_constants(
                cls.schema_version,
                "started-unresolved-finalization",
                claim_ceiling=cls.claim_ceiling,
                finalization_kind="externally-evidenced-abort",
                started_unresolved_finalized=True,
                retry_authorized=False,
                replay_authorized=False,
                d8_eligible=False,
            ),
            sha_fields=cls._SHA_FIELDS,
            positive_int_fields=("external_verification_receipt_byte_count",),
            raw_fields=("verification_receipt_required_assertions",),
        )
        assertions = _mapping(
            values.pop("verification_receipt_required_assertions"),
            "verification_receipt_required_assertions",
        )
        expected = {
            "execution_start_sha256": values["execution_start_sha256"],
            "execution_identity_receipt_sha256": values[
                "execution_identity_receipt_sha256"
            ],
            "aggregate_outcome_observed": False,
        }
        if dict(assertions) != expected:
            raise QualificationContractError(
                "verification receipt assertions differ from finalization"
            )
        return cls(**values)  # type: ignore[arg-type]


@dataclass(frozen=True, slots=True)
class D7FailedAttemptRecord(_CanonicalRecord):
    replay_target_sha256: str
    attempt_key_sha256: str
    execution_start_sha256: str
    execution_identity_receipt_sha256: str
    failure_stage: D7FailureStage
    failure_evidence_sha256: str
    started_unresolved_finalization_sha256: str | None
    confirmation_value_access_state: D7ConfirmationValueAccessState

    schema_version: ClassVar[str] = D7_FAILED_ATTEMPT_SCHEMA_VERSION
    claim_ceiling: ClassVar[str] = D7_RECORD_CLAIM_CEILING
    _LABEL: ClassVar[str] = "D7 failed attempt"
    _CONSTANTS = _record_constants(
        schema_version,
        "failed-attempt",
        claim_ceiling=claim_ceiling,
        terminal_artifact_kind=D7TerminalArtifactKind.FAILED_ATTEMPT.value,
        aggregate_outcome_observed=False,
        result_payload_present=False,
        terminally_consumed=False,
        reopen_authorized=False,
        retry_authorized=False,
        replay_authorized=False,
        d8_eligible=False,
    )
    _SHA_FIELDS = (*_STARTED_COORDINATE_FIELDS, "failure_evidence_sha256")
    _OPTIONAL_SHA_FIELDS = ("started_unresolved_finalization_sha256",)
    _ENUM_FIELDS: ClassVar[Mapping[str, type[Enum]]] = MappingProxyType(
        {
            "failure_stage": D7FailureStage,
            "confirmation_value_access_state": D7ConfirmationValueAccessState,
        }
    )

    def __post_init__(self) -> None:
        _CanonicalRecord.__post_init__(self)
        if (self.failure_stage is D7FailureStage.EVIDENCED_ABORT) is not (
            self.started_unresolved_finalization_sha256 is not None
        ):
            raise QualificationContractError(
                "evidenced abort requires exactly one unresolved finalization"
            )


@dataclass(frozen=True, slots=True)
class D7TerminalMemberBinding(_CanonicalRecord):
    filename: str
    member_kind: D7TerminalMemberKind
    member_contract_id: str
    member_canonical_sha256: str
    byte_count: int

    schema_version: ClassVar[str] = D7_TERMINAL_MEMBER_BINDING_SCHEMA_VERSION
    _LABEL: ClassVar[str] = "D7 terminal member binding"

    def __post_init__(self) -> None:
        _filename(self.filename, "filename")
        if not isinstance(self.member_kind, D7TerminalMemberKind):
            raise TypeError("member_kind must be a D7TerminalMemberKind")
        _contract_id(self.member_contract_id, "member_contract_id")
        _sha256(self.member_canonical_sha256, "member_canonical_sha256")
        _plain_int(self.byte_count, "byte_count", 1)
        if self.byte_count > MAX_D7_RESULT_COMPONENT_BYTES:
            raise QualificationContractError("terminal member exceeds byte cap")
        if self.filename in {
            D7_TERMINAL_MANIFEST_FILENAME,
            D7_TERMINAL_CONSUMPTION_FILENAME,
        }:
            raise QualificationContractError(
                "manifest members cannot include manifest or consumption"
            )
        if self.member_kind is D7TerminalMemberKind.RESULT_COMPONENT:
            component = _RESULT_COMPONENT_BY_FILENAME.get(self.filename)
            expected = (
                None
                if component is None
                else (self.filename, D7_RESULT_COMPONENT_CONTRACT_IDS[component])
            )
        else:
            expected = _FIXED_TERMINAL_MEMBER_CONTRACTS.get(self.member_kind)
        if expected != (self.filename, self.member_contract_id):
            raise QualificationContractError(
                "terminal member kind, filename, and contract ID differ"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "filename": self.filename,
            "member_kind": self.member_kind.value,
            "member_contract_id": self.member_contract_id,
            "canonical_sha256": self.member_canonical_sha256,
            "byte_count": self.byte_count,
        }

    @classmethod
    def from_dict(cls, value: object) -> Self:
        values = _decode_record(
            value,
            label=cls._LABEL,
            constants={"schema_version": cls.schema_version},
            filename_fields=("filename",),
            contract_fields=("member_contract_id",),
            sha_fields=("canonical_sha256",),
            positive_int_fields=("byte_count",),
            raw_fields=("member_kind",),
        )
        values["member_kind"] = _pop_enum(values, "member_kind", D7TerminalMemberKind)
        values["member_canonical_sha256"] = values.pop("canonical_sha256")
        return cls(**values)  # type: ignore[arg-type]


@dataclass(frozen=True, slots=True)
class D7TerminalManifestRecord(_CanonicalRecord):
    replay_target_sha256: str
    attempt_key_sha256: str
    attempt_claim_sha256: str
    execution_start_sha256: str
    execution_identity_receipt_sha256: str
    terminal_artifact_kind: D7TerminalArtifactKind
    terminal_artifact_sha256: str
    immutable_members: tuple[D7TerminalMemberBinding, ...]

    schema_version: ClassVar[str] = D7_TERMINAL_MANIFEST_SCHEMA_VERSION
    claim_ceiling: ClassVar[str] = D7_RECORD_CLAIM_CEILING
    _LABEL: ClassVar[str] = "D7 terminal manifest"
    _MAX_BYTES: ClassVar[int] = MAX_D7_TERMINAL_MANIFEST_BYTES
    _SHA_FIELDS = (*_TERMINAL_COORDINATE_FIELDS, "terminal_artifact_sha256")
    _ENUM_FIELDS: ClassVar[Mapping[str, type[Enum]]] = MappingProxyType(
        {"terminal_artifact_kind": D7TerminalArtifactKind}
    )

    def __post_init__(self) -> None:
        _CanonicalRecord.__post_init__(self)
        if type(self.immutable_members) is not tuple or any(
            type(member) is not D7TerminalMemberBinding
            for member in self.immutable_members
        ):
            raise TypeError("immutable_members must be typed tuple")
        filenames = tuple(member.filename for member in self.immutable_members)
        if not filenames or filenames != tuple(sorted(set(filenames))):
            raise QualificationContractError(
                "terminal members must be nonempty, unique, and sorted"
            )
        expected_kind = (
            D7TerminalMemberKind.SCIENTIFIC_RESULT
            if self.terminal_artifact_kind is D7TerminalArtifactKind.SCIENTIFIC_RESULT
            else D7TerminalMemberKind.FAILED_ATTEMPT
        )
        outcomes = [
            member
            for member in self.immutable_members
            if member.member_kind
            in {
                D7TerminalMemberKind.SCIENTIFIC_RESULT,
                D7TerminalMemberKind.FAILED_ATTEMPT,
            }
        ]
        if (
            len(outcomes) != 1
            or outcomes[0].member_kind is not expected_kind
            or outcomes[0].member_canonical_sha256 != self.terminal_artifact_sha256
        ):
            raise QualificationContractError(
                "terminal manifest must contain exactly its declared outcome"
            )

    def to_dict(self) -> dict[str, object]:
        return _record_document(
            self,
            "terminal-manifest",
            self._SHA_FIELDS,
            terminal_artifact_kind=self.terminal_artifact_kind.value,
            immutable_members=[item.to_dict() for item in self.immutable_members],
            required_consumption={
                "filename": D7_TERMINAL_CONSUMPTION_FILENAME,
                "schema_version": D7_TERMINAL_CONSUMPTION_SCHEMA_VERSION,
                "manifest_sha256_must_be_bound": True,
            },
            consumption_sha256_present=False,
        )

    @classmethod
    def from_dict(cls, value: object) -> Self:
        values = _decode_record(
            value,
            label=cls._LABEL,
            constants=_record_constants(
                cls.schema_version,
                "terminal-manifest",
                claim_ceiling=cls.claim_ceiling,
                required_consumption={
                    "filename": D7_TERMINAL_CONSUMPTION_FILENAME,
                    "schema_version": D7_TERMINAL_CONSUMPTION_SCHEMA_VERSION,
                    "manifest_sha256_must_be_bound": True,
                },
                consumption_sha256_present=False,
            ),
            sha_fields=(*_TERMINAL_COORDINATE_FIELDS, "terminal_artifact_sha256"),
            raw_fields=("terminal_artifact_kind", "immutable_members"),
        )
        values["terminal_artifact_kind"] = _pop_enum(
            values, "terminal_artifact_kind", D7TerminalArtifactKind
        )
        values["immutable_members"] = tuple(
            D7TerminalMemberBinding.from_dict(member)
            for member in _sequence(values["immutable_members"], "immutable_members")
        )
        return cls(**values)  # type: ignore[arg-type]


@dataclass(frozen=True, slots=True)
class D7TerminalConsumptionRecord(_CanonicalRecord):
    replay_target_sha256: str
    attempt_key_sha256: str
    attempt_claim_sha256: str
    execution_start_sha256: str
    execution_identity_receipt_sha256: str
    terminal_manifest_sha256: str
    terminal_artifact_kind: D7TerminalArtifactKind
    terminal_artifact_sha256: str
    confirmation_value_access_state: D7ConfirmationValueAccessState

    schema_version: ClassVar[str] = D7_TERMINAL_CONSUMPTION_SCHEMA_VERSION
    claim_ceiling: ClassVar[str] = D7_RECORD_CLAIM_CEILING
    _LABEL: ClassVar[str] = "D7 terminal consumption"
    _SHA_FIELDS = (
        *_TERMINAL_COORDINATE_FIELDS,
        *_names("terminal_manifest_sha256 terminal_artifact_sha256"),
    )
    _ENUM_FIELDS: ClassVar[Mapping[str, type[Enum]]] = MappingProxyType(
        {
            "terminal_artifact_kind": D7TerminalArtifactKind,
            "confirmation_value_access_state": D7ConfirmationValueAccessState,
        }
    )

    def __post_init__(self) -> None:
        _CanonicalRecord.__post_init__(self)
        if (
            self.terminal_artifact_kind is D7TerminalArtifactKind.SCIENTIFIC_RESULT
            and self.confirmation_value_access_state
            is not D7ConfirmationValueAccessState.OBSERVED
        ):
            raise QualificationContractError(
                "scientific result consumption requires observed aggregate"
            )

    def to_dict(self) -> dict[str, object]:
        return _record_document(
            self,
            "terminal-consumption",
            self._SHA_FIELDS,
            terminal_artifact_kind=self.terminal_artifact_kind.value,
            confirmation_value_access_state=self.confirmation_value_access_state.value,
            aggregate_outcome_observed=(
                self.terminal_artifact_kind is D7TerminalArtifactKind.SCIENTIFIC_RESULT
            ),
            terminally_consumed=True,
            reopen_authorized=False,
            retry_authorized=False,
        )

    @classmethod
    def from_dict(cls, value: object) -> Self:
        values = _decode_record(
            value,
            label=cls._LABEL,
            constants=_record_constants(
                cls.schema_version,
                "terminal-consumption",
                claim_ceiling=cls.claim_ceiling,
                terminally_consumed=True,
                reopen_authorized=False,
                retry_authorized=False,
            ),
            sha_fields=cls._SHA_FIELDS,
            raw_fields=(
                "terminal_artifact_kind",
                "confirmation_value_access_state",
                "aggregate_outcome_observed",
            ),
        )
        values["terminal_artifact_kind"] = _pop_enum(
            values, "terminal_artifact_kind", D7TerminalArtifactKind
        )
        values["confirmation_value_access_state"] = _pop_enum(
            values,
            "confirmation_value_access_state",
            D7ConfirmationValueAccessState,
        )
        expected_aggregate = (
            values["terminal_artifact_kind"] is D7TerminalArtifactKind.SCIENTIFIC_RESULT
        )
        if values.pop("aggregate_outcome_observed") is not expected_aggregate:
            raise QualificationContractError(
                "aggregate_outcome_observed differs from terminal kind"
            )
        return cls(**values)  # type: ignore[arg-type]
