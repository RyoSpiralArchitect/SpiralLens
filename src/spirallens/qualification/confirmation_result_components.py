"""Canonical, attempt-independent payload contracts for future D7 results.

The six payload types in this module are deliberately distinct.  Existing
D0--D5 row validators are reused only inside D7-specific enclosing contracts;
no D0--D5 result, event ledger, or gate can be relabelled as D7 evidence.

These types define bytes and local invariants only.  They do not load a replay
target, authorize an attempt, persist files, execute a runner, publish a
terminal, supply seeds, or create an official D7 instance.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from enum import Enum
from typing import ClassVar, Protocol, Self, cast

from spirallens.core.canonical import (
    CanonicalJsonError,
    canonical_json_bytes,
    canonical_json_sha256,
    parse_canonical_json,
    sha256_bytes,
)

from . import confirmation_attempt_records as ar
from .common import (
    AttemptStatus,
    CoreDisposition,
    LoopDisposition,
    QualificationContractError,
    QualificationState,
)
from .confirmation_execution_design import D7_CONFIRMATION_SEED_SLOT_IDS
from .contracts import (
    CoreCellSummary,
    CorePrimaryUnitSummary,
    CrossedCellSummary,
    PrimaryUnitSummary,
    StratumSummary,
)

__all__: tuple[str, ...] = ()

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,127}$")
_SIGNED_INT64_MAX = 2**63 - 1
_GENESIS_STAGE_BINDING_SHA256 = "0" * 64
_COMPONENT_ROOT_SCHEME = "spirallens.d7-result-component-root.v0.1"
_LANE_ROOT_SCHEME = "spirallens.d7-event-lane-root.v0.1"
_STAGE_BINDING_SCHEME = "spirallens.d7-event-stage-binding.v0.1"
_JOINED_PRIMARY_ROOT_SCHEME = "spirallens.d7-joined-primary-root.v0.1"
_GATE_ROW_ROOT_SCHEME = "spirallens.d7-four-state-gate-root.v0.1"
_RECORD_KIND = "d7-result-component-payload"


class _ToDict(Protocol):
    def to_dict(self) -> dict[str, object]: ...


class D7ExecutionLaneKind(str, Enum):
    CORE = "core"
    LOOP = "loop"


class D7ExecutionStage(str, Enum):
    PROTOCOL_VERIFIED = "protocol-verified"
    BLIND_INPUT_GENERATED = "blind-input-generated"
    PREDICTION_SEALED = "prediction-sealed"
    ORACLE_MATERIALIZED = "oracle-materialized"
    SCORED = "scored"
    RESULT_ASSEMBLED = "result-assembled"


_D7_EXECUTION_STAGE_ORDER = tuple(D7ExecutionStage)


def _mapping(value: object, label: str) -> dict[str, object]:
    if type(value) is not dict or any(type(key) is not str for key in value):
        raise QualificationContractError(f"{label} must be a built-in JSON object")
    return value


def _sequence(value: object, label: str) -> list[object]:
    if type(value) is not list:
        raise QualificationContractError(f"{label} must be a built-in JSON array")
    return value


def _strict_json(
    value: object,
    label: str = "value",
    *,
    _ancestors: frozenset[int] = frozenset(),
) -> None:
    if value is None or type(value) in {str, bool, int}:
        return
    if type(value) is float:
        if not math.isfinite(value):
            raise QualificationContractError(f"{label} must be finite")
        if value == 0.0 and math.copysign(1.0, value) < 0.0:
            raise QualificationContractError(f"{label} must not be negative zero")
        return
    if type(value) is list:
        identity = id(value)
        if identity in _ancestors:
            raise QualificationContractError(
                f"{label} contains a recursive JSON container"
            )
        descendants = _ancestors | {identity}
        for index, member in enumerate(value):
            _strict_json(
                member,
                f"{label}[{index}]",
                _ancestors=descendants,
            )
        return
    if type(value) is dict:
        if any(type(key) is not str for key in value):
            raise QualificationContractError(f"{label} keys must be built-in strings")
        identity = id(value)
        if identity in _ancestors:
            raise QualificationContractError(
                f"{label} contains a recursive JSON container"
            )
        descendants = _ancestors | {identity}
        for key, member in value.items():
            _strict_json(
                member,
                f"{label}.{key}",
                _ancestors=descendants,
            )
        return
    raise QualificationContractError(
        f"{label} contains non-built-in JSON type {type(value).__name__}"
    )


def _exact_keys(
    value: dict[str, object], expected: set[str] | frozenset[str], label: str
) -> None:
    if set(value) != set(expected):
        raise QualificationContractError(
            f"{label} fields differ: "
            f"missing={sorted(set(expected) - set(value))}, "
            f"unknown={sorted(set(value) - set(expected))}"
        )


def _string(value: object, label: str) -> str:
    if type(value) is not str or not value or value != value.strip():
        raise QualificationContractError(f"{label} must be a non-empty trimmed string")
    return value


def _slug(value: object, label: str) -> str:
    result = _string(value, label)
    if _SLUG_RE.fullmatch(result) is None:
        raise QualificationContractError(f"{label} must be a portable slug")
    return result


def _sha256(value: object, label: str) -> str:
    if type(value) is not str or _SHA256_RE.fullmatch(value) is None:
        raise QualificationContractError(f"{label} must be a lowercase SHA-256")
    return value


def _plain_int(value: object, label: str, *, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise QualificationContractError(
            f"{label} must be a plain integer of at least {minimum}"
        )
    return value


def _enum(enum_type: type[Enum], value: object, label: str) -> Enum:
    if type(value) is not str:
        raise QualificationContractError(f"{label} must be a string")
    try:
        return enum_type(value)
    except ValueError as error:
        raise QualificationContractError(f"{label} is not supported") from error


def _reason_codes(
    values: tuple[str, ...], state: ar.D7GateState, *, label: str
) -> tuple[str, ...]:
    if type(values) is not tuple:
        raise TypeError(f"{label} must be an immutable tuple")
    for index, value in enumerate(values):
        _slug(value, f"{label}[{index}]")
    if values != tuple(sorted(set(values))):
        raise QualificationContractError(f"{label} must be unique and canonical")
    if state is ar.D7GateState.PASS and values:
        raise QualificationContractError(f"{label} must be empty for pass")
    if state is not ar.D7GateState.PASS and not values:
        raise QualificationContractError(f"{label} must identify every non-pass")
    return values


def _row_dict(value: _ToDict) -> dict[str, object]:
    document = value.to_dict()
    _strict_json(document, "row")
    return document


def _bounded_bytes(document: dict[str, object], *, label: str) -> bytes:
    result = canonical_json_bytes(document)
    if len(result) > ar.MAX_D7_RESULT_COMPONENT_BYTES:
        raise QualificationContractError(f"{label} exceeds the D7 component byte cap")
    return result


def _parse_component_bytes(
    source: bytes, *, expected_sha256: str, label: str
) -> object:
    expected = _sha256(expected_sha256, "expected_sha256")
    if type(source) is not bytes:
        raise TypeError(f"{label} source must be built-in bytes")
    if not source or len(source) > ar.MAX_D7_RESULT_COMPONENT_BYTES:
        raise QualificationContractError(f"{label} source violates the byte cap")
    if sha256_bytes(source) != expected:
        raise QualificationContractError(f"{label} SHA-256 differs")
    try:
        return parse_canonical_json(source, label=label)
    except CanonicalJsonError as error:
        raise QualificationContractError(str(error)) from error


@dataclass(frozen=True, slots=True)
class D7ExecutionEventStageBinding:
    stage: D7ExecutionStage
    payload_sha256: str
    previous_stage_binding_sha256: str

    def __post_init__(self) -> None:
        if type(self) is not D7ExecutionEventStageBinding:
            raise TypeError("D7 event stage binding subclasses are forbidden")
        if type(self.stage) is not D7ExecutionStage:
            raise TypeError("stage must be an exact D7ExecutionStage")
        _sha256(self.payload_sha256, "stage payload_sha256")
        _sha256(
            self.previous_stage_binding_sha256,
            "stage previous_stage_binding_sha256",
        )

    @property
    def binding_sha256(self) -> str:
        return canonical_json_sha256(
            {
                "scheme": _STAGE_BINDING_SCHEME,
                "stage": self.stage.value,
                "payload_sha256": self.payload_sha256,
                "previous_stage_binding_sha256": (self.previous_stage_binding_sha256),
            }
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "stage": self.stage.value,
            "payload_sha256": self.payload_sha256,
            "previous_stage_binding_sha256": self.previous_stage_binding_sha256,
            "binding_sha256": self.binding_sha256,
        }

    @classmethod
    def from_dict(cls, value: object) -> Self:
        if cls is not D7ExecutionEventStageBinding:
            raise TypeError("D7 event stage binding subclasses are forbidden")
        _strict_json(value, "D7 event stage binding")
        item = _mapping(value, "D7 event stage binding")
        _exact_keys(
            item,
            {
                "stage",
                "payload_sha256",
                "previous_stage_binding_sha256",
                "binding_sha256",
            },
            "D7 event stage binding",
        )
        recorded = _sha256(item["binding_sha256"], "binding_sha256")
        result = cls(
            stage=cast(
                D7ExecutionStage,
                _enum(D7ExecutionStage, item["stage"], "stage"),
            ),
            payload_sha256=_sha256(item["payload_sha256"], "payload_sha256"),
            previous_stage_binding_sha256=_sha256(
                item["previous_stage_binding_sha256"],
                "previous_stage_binding_sha256",
            ),
        )
        if recorded != result.binding_sha256:
            raise QualificationContractError("stage binding_sha256 differs")
        return result


@dataclass(frozen=True, slots=True)
class D7ExecutionEventLaneOutcome:
    lane_id: str
    lane_kind: D7ExecutionLaneKind
    cell_id: str
    stage_bindings: tuple[D7ExecutionEventStageBinding, ...]

    def __post_init__(self) -> None:
        if type(self) is not D7ExecutionEventLaneOutcome:
            raise TypeError("D7 event lane subclasses are forbidden")
        _slug(self.lane_id, "lane_id")
        if type(self.lane_kind) is not D7ExecutionLaneKind:
            raise TypeError("lane_kind must be an exact D7ExecutionLaneKind")
        _slug(self.cell_id, "cell_id")
        if self.lane_id != f"{self.lane_kind.value}.{self.cell_id}":
            raise QualificationContractError("lane_id differs from lane kind and cell")
        if type(self.stage_bindings) is not tuple or any(
            type(item) is not D7ExecutionEventStageBinding
            for item in self.stage_bindings
        ):
            raise TypeError("stage_bindings must be an exact typed tuple")
        if tuple(item.stage for item in self.stage_bindings) != (
            _D7_EXECUTION_STAGE_ORDER
        ):
            raise QualificationContractError(
                "event lane must bind the exact six semantic stages in order"
            )
        previous = _GENESIS_STAGE_BINDING_SHA256
        for item in self.stage_bindings:
            if item.previous_stage_binding_sha256 != previous:
                raise QualificationContractError("event lane stage chain is broken")
            previous = item.binding_sha256
        payloads = tuple(item.payload_sha256 for item in self.stage_bindings)
        if len(set(payloads)) != len(payloads):
            raise QualificationContractError(
                "event lane semantic stages must bind distinct payloads"
            )

    @property
    def lane_root_sha256(self) -> str:
        return canonical_json_sha256(
            {
                "scheme": _LANE_ROOT_SCHEME,
                "lane_id": self.lane_id,
                "lane_kind": self.lane_kind.value,
                "cell_id": self.cell_id,
                "stage_bindings": [item.to_dict() for item in self.stage_bindings],
            }
        )

    @property
    def result_outcome_sha256(self) -> str:
        return self.stage_bindings[-1].payload_sha256

    def to_dict(self) -> dict[str, object]:
        return {
            "lane_id": self.lane_id,
            "lane_kind": self.lane_kind.value,
            "cell_id": self.cell_id,
            "stage_bindings": [item.to_dict() for item in self.stage_bindings],
            "lane_root_sha256": self.lane_root_sha256,
        }

    @classmethod
    def from_dict(cls, value: object) -> Self:
        if cls is not D7ExecutionEventLaneOutcome:
            raise TypeError("D7 event lane subclasses are forbidden")
        _strict_json(value, "D7 event lane")
        item = _mapping(value, "D7 event lane")
        _exact_keys(
            item,
            {
                "lane_id",
                "lane_kind",
                "cell_id",
                "stage_bindings",
                "lane_root_sha256",
            },
            "D7 event lane",
        )
        recorded = _sha256(item["lane_root_sha256"], "lane_root_sha256")
        result = cls(
            lane_id=_slug(item["lane_id"], "lane_id"),
            lane_kind=cast(
                D7ExecutionLaneKind,
                _enum(D7ExecutionLaneKind, item["lane_kind"], "lane_kind"),
            ),
            cell_id=_slug(item["cell_id"], "cell_id"),
            stage_bindings=tuple(
                D7ExecutionEventStageBinding.from_dict(member)
                for member in _sequence(item["stage_bindings"], "stage_bindings")
            ),
        )
        if recorded != result.lane_root_sha256:
            raise QualificationContractError("lane_root_sha256 differs")
        return result


_CASE_SEMANTICS = {
    (
        CoreDisposition.LOCALIZED_CORE,
        LoopDisposition.NONZERO,
    ): "localized-core|nonzero",
    (
        CoreDisposition.LOCALIZED_CORE,
        LoopDisposition.NULL,
    ): "localized-core|null",
    (
        CoreDisposition.NO_CORE,
        LoopDisposition.NULL,
    ): "no-core|null",
    (
        CoreDisposition.PREREQUISITE_FAILURE,
        LoopDisposition.PREREQUISITE_FAILURE,
    ): "prerequisite-failure|prerequisite-failure",
}


def _joined_attempt_status(
    core: CorePrimaryUnitSummary, loop: PrimaryUnitSummary
) -> AttemptStatus:
    if (
        core.attempt_status is AttemptStatus.NOT_RUN
        and loop.attempt_status is AttemptStatus.NOT_RUN
    ):
        return AttemptStatus.NOT_RUN
    if (
        core.attempt_status is AttemptStatus.EVALUABLE
        and loop.attempt_status is AttemptStatus.EVALUABLE
    ):
        return AttemptStatus.EVALUABLE
    return AttemptStatus.INSUFFICIENT


def _joined_state(
    core: CorePrimaryUnitSummary, loop: PrimaryUnitSummary
) -> ar.D7GateState:
    states = (core.state, loop.state)
    if any(
        state
        in {
            QualificationState.FAIL,
            QualificationState.FAIL_GRAPH_DEPENDENCE,
        }
        for state in states
    ):
        return ar.D7GateState.FAIL
    if all(state is QualificationState.PASS for state in states):
        return ar.D7GateState.PASS
    if all(state is QualificationState.NOT_RUN for state in states):
        return ar.D7GateState.NOT_RUN
    return ar.D7GateState.INSUFFICIENT


@dataclass(frozen=True, slots=True)
class D7JoinedPrimaryUnitOutcome:
    primary_unit_id: str
    seed_slot_id: str
    official_seed: int
    case_id: str
    case_semantics: str
    core_summary: CorePrimaryUnitSummary
    loop_summary: PrimaryUnitSummary
    attempt_status: AttemptStatus
    state: ar.D7GateState
    reason_codes: tuple[str, ...]

    def __post_init__(self) -> None:
        if type(self) is not D7JoinedPrimaryUnitOutcome:
            raise TypeError("D7 joined-primary subclasses are forbidden")
        _slug(self.primary_unit_id, "primary_unit_id")
        _slug(self.seed_slot_id, "seed_slot_id")
        if self.seed_slot_id not in D7_CONFIRMATION_SEED_SLOT_IDS:
            raise QualificationContractError("seed_slot_id is outside the D7 inventory")
        seed = _plain_int(self.official_seed, "official_seed")
        if seed > _SIGNED_INT64_MAX:
            raise QualificationContractError("official_seed exceeds signed int64")
        _slug(self.case_id, "case_id")
        _string(self.case_semantics, "case_semantics")
        if type(self.core_summary) is not CorePrimaryUnitSummary:
            raise TypeError("core_summary must be an exact CorePrimaryUnitSummary")
        if type(self.loop_summary) is not PrimaryUnitSummary:
            raise TypeError("loop_summary must be an exact PrimaryUnitSummary")
        core = self.core_summary
        loop = self.loop_summary
        if (
            self.primary_unit_id != core.primary_unit_id
            or self.primary_unit_id != loop.primary_unit_id
        ):
            raise QualificationContractError("joined primary IDs differ")
        if (
            self.official_seed != core.selection_seed
            or self.official_seed != loop.selection_seed
        ):
            raise QualificationContractError("joined primary seed values differ")
        if (
            core.control_id != loop.control_id
            or core.stress_assignments != loop.stress_assignments
        ):
            raise QualificationContractError(
                "joined primary control or stress assignments differ"
            )
        if (
            core.domain_instance_fingerprint_sha256
            != loop.domain_instance_fingerprint_sha256
            or core.support_instance_fingerprint_sha256
            != loop.support_instance_fingerprint_sha256
        ):
            raise QualificationContractError(
                "joined primary domain or support identities differ"
            )
        expected_semantics = _CASE_SEMANTICS.get(
            (core.expected_disposition, loop.expected_disposition)
        )
        if self.case_semantics != expected_semantics:
            raise QualificationContractError(
                "case_semantics differs from core/loop dispositions"
            )
        if (
            len(core.core_cell_ids) != 3
            or core.core_cell_ids != tuple(sorted(set(core.core_cell_ids)))
            or len(loop.crossed_cell_ids) != 18
            or loop.crossed_cell_ids != tuple(sorted(set(loop.crossed_cell_ids)))
        ):
            raise QualificationContractError(
                "joined primary requires exact 3 core and 18 loop cell IDs"
            )
        if type(self.attempt_status) is not AttemptStatus:
            raise TypeError("attempt_status must be an exact AttemptStatus")
        if self.attempt_status is not _joined_attempt_status(core, loop):
            raise QualificationContractError(
                "joined attempt_status differs from core/loop projections"
            )
        if type(self.state) is not ar.D7GateState:
            raise TypeError("state must be an exact D7GateState")
        if self.state is not _joined_state(core, loop):
            raise QualificationContractError(
                "joined state differs from the four-state projection"
            )
        expected_reasons = tuple(
            sorted(
                {
                    reason
                    for summary in (core, loop)
                    if summary.state is not QualificationState.PASS
                    for reason in summary.reason_codes
                }
            )
        )
        _reason_codes(self.reason_codes, self.state, label="joined reason_codes")
        if self.reason_codes != expected_reasons:
            raise QualificationContractError(
                "joined reason_codes differ from core/loop projections"
            )

    @property
    def joined_root_sha256(self) -> str:
        return canonical_json_sha256(
            {
                "scheme": _JOINED_PRIMARY_ROOT_SCHEME,
                "primary_unit_id": self.primary_unit_id,
                "seed_slot_id": self.seed_slot_id,
                "official_seed": self.official_seed,
                "case_id": self.case_id,
                "case_semantics": self.case_semantics,
                "core_summary": self.core_summary.to_dict(),
                "loop_summary": self.loop_summary.to_dict(),
                "attempt_status": self.attempt_status.value,
                "state": self.state.value,
                "reason_codes": list(self.reason_codes),
            }
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "primary_unit_id": self.primary_unit_id,
            "seed_slot_id": self.seed_slot_id,
            "official_seed": self.official_seed,
            "case_id": self.case_id,
            "case_semantics": self.case_semantics,
            "core_summary": self.core_summary.to_dict(),
            "loop_summary": self.loop_summary.to_dict(),
            "attempt_status": self.attempt_status.value,
            "state": self.state.value,
            "reason_codes": list(self.reason_codes),
            "joined_root_sha256": self.joined_root_sha256,
        }

    @classmethod
    def from_dict(cls, value: object) -> Self:
        if cls is not D7JoinedPrimaryUnitOutcome:
            raise TypeError("D7 joined-primary subclasses are forbidden")
        _strict_json(value, "D7 joined primary")
        item = _mapping(value, "D7 joined primary")
        _exact_keys(
            item,
            {
                "primary_unit_id",
                "seed_slot_id",
                "official_seed",
                "case_id",
                "case_semantics",
                "core_summary",
                "loop_summary",
                "attempt_status",
                "state",
                "reason_codes",
                "joined_root_sha256",
            },
            "D7 joined primary",
        )
        recorded = _sha256(item["joined_root_sha256"], "joined_root_sha256")
        result = cls(
            primary_unit_id=_slug(item["primary_unit_id"], "primary_unit_id"),
            seed_slot_id=_slug(item["seed_slot_id"], "seed_slot_id"),
            official_seed=_plain_int(item["official_seed"], "official_seed"),
            case_id=_slug(item["case_id"], "case_id"),
            case_semantics=_string(item["case_semantics"], "case_semantics"),
            core_summary=CorePrimaryUnitSummary.from_dict(item["core_summary"]),
            loop_summary=PrimaryUnitSummary.from_dict(item["loop_summary"]),
            attempt_status=cast(
                AttemptStatus,
                _enum(AttemptStatus, item["attempt_status"], "attempt_status"),
            ),
            state=cast(
                ar.D7GateState,
                _enum(ar.D7GateState, item["state"], "state"),
            ),
            reason_codes=tuple(
                _slug(member, "reason_code")
                for member in _sequence(item["reason_codes"], "reason_codes")
            ),
        )
        if recorded != result.joined_root_sha256:
            raise QualificationContractError("joined_root_sha256 differs")
        return result


@dataclass(frozen=True, slots=True)
class D7AggregateGateOutcome:
    gate_id: str
    gate_definition_sha256: str
    state: ar.D7GateState
    reason_codes: tuple[str, ...]
    evidence_sha256: str

    def __post_init__(self) -> None:
        if type(self) is not D7AggregateGateOutcome:
            raise TypeError("D7 gate outcome subclasses are forbidden")
        _slug(self.gate_id, "gate_id")
        _sha256(self.gate_definition_sha256, "gate_definition_sha256")
        if type(self.state) is not ar.D7GateState:
            raise TypeError("state must be an exact D7GateState")
        _reason_codes(self.reason_codes, self.state, label="gate reason_codes")
        _sha256(self.evidence_sha256, "evidence_sha256")
        if self.evidence_sha256 == self.gate_definition_sha256:
            raise QualificationContractError(
                "gate definition and evidence identities must differ"
            )

    @property
    def gate_root_sha256(self) -> str:
        return canonical_json_sha256(
            {
                "scheme": _GATE_ROW_ROOT_SCHEME,
                "gate_id": self.gate_id,
                "gate_definition_sha256": self.gate_definition_sha256,
                "state": self.state.value,
                "reason_codes": list(self.reason_codes),
                "evidence_sha256": self.evidence_sha256,
            }
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "gate_id": self.gate_id,
            "gate_definition_sha256": self.gate_definition_sha256,
            "state": self.state.value,
            "reason_codes": list(self.reason_codes),
            "evidence_sha256": self.evidence_sha256,
            "gate_root_sha256": self.gate_root_sha256,
        }

    @classmethod
    def from_dict(cls, value: object) -> Self:
        if cls is not D7AggregateGateOutcome:
            raise TypeError("D7 gate outcome subclasses are forbidden")
        _strict_json(value, "D7 gate outcome")
        item = _mapping(value, "D7 gate outcome")
        _exact_keys(
            item,
            {
                "gate_id",
                "gate_definition_sha256",
                "state",
                "reason_codes",
                "evidence_sha256",
                "gate_root_sha256",
            },
            "D7 gate outcome",
        )
        recorded = _sha256(item["gate_root_sha256"], "gate_root_sha256")
        result = cls(
            gate_id=_slug(item["gate_id"], "gate_id"),
            gate_definition_sha256=_sha256(
                item["gate_definition_sha256"], "gate_definition_sha256"
            ),
            state=cast(
                ar.D7GateState,
                _enum(ar.D7GateState, item["state"], "state"),
            ),
            reason_codes=tuple(
                _slug(member, "reason_code")
                for member in _sequence(item["reason_codes"], "reason_codes")
            ),
            evidence_sha256=_sha256(item["evidence_sha256"], "evidence_sha256"),
        )
        if recorded != result.gate_root_sha256:
            raise QualificationContractError("gate_root_sha256 differs")
        return result


class _D7Payload(Protocol):
    schema_version: ClassVar[str]
    component_id: ClassVar[ar.D7ResultComponentId]
    component_contract_id: ClassVar[str]
    replay_target_sha256: str
    full_inventory_sha256: str
    aggregation_sha256: str
    records: tuple[_ToDict, ...]


def _payload_root(value: _D7Payload, *, extra: dict[str, object] | None = None) -> str:
    return canonical_json_sha256(
        {
            "scheme": _COMPONENT_ROOT_SCHEME,
            "schema_version": value.schema_version,
            "component_id": value.component_id.value,
            "component_contract_id": value.component_contract_id,
            "record_scope": ar.D7_RESULT_RECORD_SCOPE,
            "claim_ceiling": ar.D7_RECORD_CLAIM_CEILING,
            "attempt_independent": True,
            "replay_target_sha256": value.replay_target_sha256,
            "full_inventory_sha256": value.full_inventory_sha256,
            "aggregation_sha256": value.aggregation_sha256,
            "result_schema_sha256": (
                ar.D7_SCIENTIFIC_RESULT_IMPLEMENTATION_SCHEMA_SHA256
            ),
            "record_count": len(value.records),
            "records": [_row_dict(item) for item in value.records],
            **({} if extra is None else extra),
        }
    )


def _payload_document(
    value: _D7Payload, *, extra: dict[str, object] | None = None
) -> dict[str, object]:
    root_extra = {} if extra is None else extra
    return {
        "schema_version": value.schema_version,
        "record_kind": _RECORD_KIND,
        "component_id": value.component_id.value,
        "component_contract_id": value.component_contract_id,
        "record_scope": ar.D7_RESULT_RECORD_SCOPE,
        "claim_ceiling": ar.D7_RECORD_CLAIM_CEILING,
        "attempt_independent": True,
        "replay_target_sha256": value.replay_target_sha256,
        "full_inventory_sha256": value.full_inventory_sha256,
        "aggregation_sha256": value.aggregation_sha256,
        "result_schema_sha256": (ar.D7_SCIENTIFIC_RESULT_IMPLEMENTATION_SCHEMA_SHA256),
        "record_count": len(value.records),
        "records": [_row_dict(item) for item in value.records],
        **root_extra,
        "component_root_sha256": _payload_root(value, extra=root_extra),
    }


def _validate_payload(
    value: _D7Payload,
    *,
    exact_type: type[object],
    row_type: type[object],
    id_attribute: str,
    fixed_count: int | None,
) -> None:
    if type(value) is not exact_type:
        raise TypeError(f"{exact_type.__name__} subclasses are forbidden")
    for name in (
        "replay_target_sha256",
        "full_inventory_sha256",
        "aggregation_sha256",
    ):
        _sha256(getattr(value, name), name)
    if (
        len(
            {
                value.replay_target_sha256,
                value.full_inventory_sha256,
                value.aggregation_sha256,
                ar.D7_SCIENTIFIC_RESULT_IMPLEMENTATION_SCHEMA_SHA256,
            }
        )
        != 4
    ):
        raise QualificationContractError(
            "target, inventory, aggregation, and result-schema identities must differ"
        )
    if type(value.records) is not tuple or any(
        type(item) is not row_type for item in value.records
    ):
        raise TypeError("records must be an exact typed tuple")
    for item in value.records:
        document = _row_dict(item)
        rebuilt = type(item).from_dict(document)
        if type(rebuilt) is not type(item) or canonical_json_bytes(
            rebuilt.to_dict()
        ) != canonical_json_bytes(document):
            raise QualificationContractError(
                "component row is not canonically self-reconstructing"
            )
    if not value.records:
        raise QualificationContractError("component records must not be empty")
    if fixed_count is not None and len(value.records) != fixed_count:
        raise QualificationContractError(
            "component record count differs from its fixed inventory"
        )
    identifiers = tuple(getattr(item, id_attribute) for item in value.records)
    if identifiers != tuple(sorted(set(identifiers))):
        raise QualificationContractError(
            "component record identifiers must be unique and canonical"
        )
    _bounded_bytes(_payload_document(value), label=value.component_id.value)


_PAYLOAD_BASE_KEYS = {
    "schema_version",
    "record_kind",
    "component_id",
    "component_contract_id",
    "record_scope",
    "claim_ceiling",
    "attempt_independent",
    "replay_target_sha256",
    "full_inventory_sha256",
    "aggregation_sha256",
    "result_schema_sha256",
    "record_count",
    "records",
    "component_root_sha256",
}


def _decode_payload(
    value: object,
    *,
    label: str,
    schema_version: str,
    component_id: ar.D7ResultComponentId,
    component_contract_id: str,
    row_parser: object,
    extra_keys: frozenset[str] = frozenset(),
) -> tuple[dict[str, object], tuple[object, ...], str]:
    _strict_json(value, label)
    item = _mapping(value, label)
    _exact_keys(item, _PAYLOAD_BASE_KEYS | set(extra_keys), label)
    constants = {
        "schema_version": schema_version,
        "record_kind": _RECORD_KIND,
        "component_id": component_id.value,
        "component_contract_id": component_contract_id,
        "record_scope": ar.D7_RESULT_RECORD_SCOPE,
        "claim_ceiling": ar.D7_RECORD_CLAIM_CEILING,
        "attempt_independent": True,
        "result_schema_sha256": (ar.D7_SCIENTIFIC_RESULT_IMPLEMENTATION_SCHEMA_SHA256),
    }
    for name, expected in constants.items():
        if type(item[name]) is not type(expected) or item[name] != expected:
            raise QualificationContractError(f"{label} {name} differs")
    raw_records = _sequence(item["records"], f"{label} records")
    record_count = _plain_int(item["record_count"], f"{label} record_count", minimum=1)
    if record_count != len(raw_records):
        raise QualificationContractError(f"{label} record_count differs")
    parser = cast(type[D7ExecutionEventLaneOutcome], row_parser)
    records = tuple(parser.from_dict(member) for member in raw_records)
    common = {
        "replay_target_sha256": _sha256(
            item["replay_target_sha256"], "replay_target_sha256"
        ),
        "full_inventory_sha256": _sha256(
            item["full_inventory_sha256"], "full_inventory_sha256"
        ),
        "aggregation_sha256": _sha256(item["aggregation_sha256"], "aggregation_sha256"),
    }
    root = _sha256(item["component_root_sha256"], "component_root_sha256")
    return common, records, root


class _CanonicalPayloadMixin:
    def to_dict(self) -> dict[str, object]:
        raise NotImplementedError

    @property
    def canonical_bytes(self) -> bytes:
        return _bounded_bytes(self.to_dict(), label=type(self).__name__)

    @property
    def canonical_sha256(self) -> str:
        return canonical_json_sha256(self.to_dict())

    @classmethod
    def from_canonical_bytes(cls, source: bytes, *, expected_sha256: str) -> Self:
        value = _parse_component_bytes(
            source,
            expected_sha256=expected_sha256,
            label=cls.__name__,
        )
        result = cls.from_dict(value)  # type: ignore[attr-defined]
        if result.canonical_bytes != source:
            raise QualificationContractError(f"{cls.__name__} bytes differ")
        return result


@dataclass(frozen=True, slots=True)
class D7ExecutionEventLedgerPayload(_CanonicalPayloadMixin):
    replay_target_sha256: str
    full_inventory_sha256: str
    aggregation_sha256: str
    records: tuple[D7ExecutionEventLaneOutcome, ...]

    component_id: ClassVar[ar.D7ResultComponentId] = (
        ar.D7ResultComponentId.EXECUTION_EVENT_LEDGER
    )
    schema_version: ClassVar[str] = "spirallens.d7-execution-event-ledger-payload.v0.1"
    component_contract_id: ClassVar[str] = ar.D7_RESULT_COMPONENT_CONTRACT_IDS[
        component_id
    ]

    def __post_init__(self) -> None:
        _validate_payload(
            self,
            exact_type=D7ExecutionEventLedgerPayload,
            row_type=D7ExecutionEventLaneOutcome,
            id_attribute="lane_id",
            fixed_count=ar.D7_RESULT_COMPONENT_FIXED_RECORD_COUNTS[self.component_id],
        )

    @property
    def component_root_sha256(self) -> str:
        return _payload_root(self)

    def to_dict(self) -> dict[str, object]:
        return _payload_document(self)

    @classmethod
    def from_dict(cls, value: object) -> Self:
        if cls is not D7ExecutionEventLedgerPayload:
            raise TypeError("D7 event-ledger payload subclasses are forbidden")
        common, records, root = _decode_payload(
            value,
            label="D7 execution-event-ledger payload",
            schema_version=cls.schema_version,
            component_id=cls.component_id,
            component_contract_id=cls.component_contract_id,
            row_parser=D7ExecutionEventLaneOutcome,
        )
        result = cls(
            records=cast(tuple[D7ExecutionEventLaneOutcome, ...], records), **common
        )
        if root != result.component_root_sha256:
            raise QualificationContractError("component_root_sha256 differs")
        return result


@dataclass(frozen=True, slots=True)
class D7CoreCellOutcomesPayload(_CanonicalPayloadMixin):
    replay_target_sha256: str
    full_inventory_sha256: str
    aggregation_sha256: str
    records: tuple[CoreCellSummary, ...]

    component_id: ClassVar[ar.D7ResultComponentId] = (
        ar.D7ResultComponentId.CORE_CELL_OUTCOMES
    )
    schema_version: ClassVar[str] = "spirallens.d7-core-cell-outcomes-payload.v0.1"
    component_contract_id: ClassVar[str] = ar.D7_RESULT_COMPONENT_CONTRACT_IDS[
        component_id
    ]

    def __post_init__(self) -> None:
        _validate_payload(
            self,
            exact_type=D7CoreCellOutcomesPayload,
            row_type=CoreCellSummary,
            id_attribute="core_cell_id",
            fixed_count=ar.D7_RESULT_COMPONENT_FIXED_RECORD_COUNTS[self.component_id],
        )

    @property
    def component_root_sha256(self) -> str:
        return _payload_root(self)

    def to_dict(self) -> dict[str, object]:
        return _payload_document(self)

    @classmethod
    def from_dict(cls, value: object) -> Self:
        if cls is not D7CoreCellOutcomesPayload:
            raise TypeError("D7 core payload subclasses are forbidden")
        common, records, root = _decode_payload(
            value,
            label="D7 core-cell-outcomes payload",
            schema_version=cls.schema_version,
            component_id=cls.component_id,
            component_contract_id=cls.component_contract_id,
            row_parser=CoreCellSummary,
        )
        result = cls(records=cast(tuple[CoreCellSummary, ...], records), **common)
        if root != result.component_root_sha256:
            raise QualificationContractError("component_root_sha256 differs")
        return result


@dataclass(frozen=True, slots=True)
class D7LoopCellOutcomesPayload(_CanonicalPayloadMixin):
    replay_target_sha256: str
    full_inventory_sha256: str
    aggregation_sha256: str
    records: tuple[CrossedCellSummary, ...]

    component_id: ClassVar[ar.D7ResultComponentId] = (
        ar.D7ResultComponentId.LOOP_CELL_OUTCOMES
    )
    schema_version: ClassVar[str] = "spirallens.d7-loop-cell-outcomes-payload.v0.1"
    component_contract_id: ClassVar[str] = ar.D7_RESULT_COMPONENT_CONTRACT_IDS[
        component_id
    ]

    def __post_init__(self) -> None:
        _validate_payload(
            self,
            exact_type=D7LoopCellOutcomesPayload,
            row_type=CrossedCellSummary,
            id_attribute="cell_id",
            fixed_count=ar.D7_RESULT_COMPONENT_FIXED_RECORD_COUNTS[self.component_id],
        )

    @property
    def component_root_sha256(self) -> str:
        return _payload_root(self)

    def to_dict(self) -> dict[str, object]:
        return _payload_document(self)

    @classmethod
    def from_dict(cls, value: object) -> Self:
        if cls is not D7LoopCellOutcomesPayload:
            raise TypeError("D7 loop payload subclasses are forbidden")
        common, records, root = _decode_payload(
            value,
            label="D7 loop-cell-outcomes payload",
            schema_version=cls.schema_version,
            component_id=cls.component_id,
            component_contract_id=cls.component_contract_id,
            row_parser=CrossedCellSummary,
        )
        result = cls(records=cast(tuple[CrossedCellSummary, ...], records), **common)
        if root != result.component_root_sha256:
            raise QualificationContractError("component_root_sha256 differs")
        return result


@dataclass(frozen=True, slots=True)
class D7PrimaryUnitOutcomesPayload(_CanonicalPayloadMixin):
    replay_target_sha256: str
    full_inventory_sha256: str
    aggregation_sha256: str
    records: tuple[D7JoinedPrimaryUnitOutcome, ...]

    component_id: ClassVar[ar.D7ResultComponentId] = (
        ar.D7ResultComponentId.PRIMARY_UNIT_OUTCOMES
    )
    schema_version: ClassVar[str] = "spirallens.d7-primary-unit-outcomes-payload.v0.1"
    component_contract_id: ClassVar[str] = ar.D7_RESULT_COMPONENT_CONTRACT_IDS[
        component_id
    ]

    def __post_init__(self) -> None:
        _validate_payload(
            self,
            exact_type=D7PrimaryUnitOutcomesPayload,
            row_type=D7JoinedPrimaryUnitOutcome,
            id_attribute="primary_unit_id",
            fixed_count=ar.D7_RESULT_COMPONENT_FIXED_RECORD_COUNTS[self.component_id],
        )

    @property
    def component_root_sha256(self) -> str:
        return _payload_root(self)

    def to_dict(self) -> dict[str, object]:
        return _payload_document(self)

    @classmethod
    def from_dict(cls, value: object) -> Self:
        if cls is not D7PrimaryUnitOutcomesPayload:
            raise TypeError("D7 primary payload subclasses are forbidden")
        common, records, root = _decode_payload(
            value,
            label="D7 primary-unit-outcomes payload",
            schema_version=cls.schema_version,
            component_id=cls.component_id,
            component_contract_id=cls.component_contract_id,
            row_parser=D7JoinedPrimaryUnitOutcome,
        )
        result = cls(
            records=cast(tuple[D7JoinedPrimaryUnitOutcome, ...], records),
            **common,
        )
        if root != result.component_root_sha256:
            raise QualificationContractError("component_root_sha256 differs")
        return result


@dataclass(frozen=True, slots=True)
class D7RequiredStratumOutcomesPayload(_CanonicalPayloadMixin):
    replay_target_sha256: str
    full_inventory_sha256: str
    aggregation_sha256: str
    records: tuple[StratumSummary, ...]

    component_id: ClassVar[ar.D7ResultComponentId] = (
        ar.D7ResultComponentId.REQUIRED_STRATUM_OUTCOMES
    )
    schema_version: ClassVar[str] = (
        "spirallens.d7-required-stratum-outcomes-payload.v0.1"
    )
    component_contract_id: ClassVar[str] = ar.D7_RESULT_COMPONENT_CONTRACT_IDS[
        component_id
    ]

    def __post_init__(self) -> None:
        _validate_payload(
            self,
            exact_type=D7RequiredStratumOutcomesPayload,
            row_type=StratumSummary,
            id_attribute="stratum_id",
            fixed_count=ar.D7_RESULT_COMPONENT_FIXED_RECORD_COUNTS[self.component_id],
        )

    @property
    def component_root_sha256(self) -> str:
        return _payload_root(self)

    def to_dict(self) -> dict[str, object]:
        return _payload_document(self)

    @classmethod
    def from_dict(cls, value: object) -> Self:
        if cls is not D7RequiredStratumOutcomesPayload:
            raise TypeError("D7 stratum payload subclasses are forbidden")
        common, records, root = _decode_payload(
            value,
            label="D7 required-stratum-outcomes payload",
            schema_version=cls.schema_version,
            component_id=cls.component_id,
            component_contract_id=cls.component_contract_id,
            row_parser=StratumSummary,
        )
        result = cls(records=cast(tuple[StratumSummary, ...], records), **common)
        if root != result.component_root_sha256:
            raise QualificationContractError("component_root_sha256 differs")
        return result


@dataclass(frozen=True, slots=True)
class D7AggregateGateOutcomesPayload(_CanonicalPayloadMixin):
    replay_target_sha256: str
    full_inventory_sha256: str
    aggregation_sha256: str
    gate_manifest_sha256: str
    records: tuple[D7AggregateGateOutcome, ...]

    component_id: ClassVar[ar.D7ResultComponentId] = (
        ar.D7ResultComponentId.AGGREGATE_GATE_OUTCOMES
    )
    schema_version: ClassVar[str] = "spirallens.d7-aggregate-gate-outcomes-payload.v0.1"
    component_contract_id: ClassVar[str] = ar.D7_RESULT_COMPONENT_CONTRACT_IDS[
        component_id
    ]

    def __post_init__(self) -> None:
        _sha256(self.gate_manifest_sha256, "gate_manifest_sha256")
        _validate_payload(
            self,
            exact_type=D7AggregateGateOutcomesPayload,
            row_type=D7AggregateGateOutcome,
            id_attribute="gate_id",
            fixed_count=None,
        )
        if self.gate_manifest_sha256 in {
            self.replay_target_sha256,
            self.full_inventory_sha256,
            self.aggregation_sha256,
        }:
            raise QualificationContractError(
                "gate manifest identity must differ from component roots"
            )

    @property
    def component_root_sha256(self) -> str:
        return _payload_root(
            self, extra={"gate_manifest_sha256": self.gate_manifest_sha256}
        )

    def to_dict(self) -> dict[str, object]:
        return _payload_document(
            self, extra={"gate_manifest_sha256": self.gate_manifest_sha256}
        )

    @classmethod
    def from_dict(cls, value: object) -> Self:
        if cls is not D7AggregateGateOutcomesPayload:
            raise TypeError("D7 gate payload subclasses are forbidden")
        common, records, root = _decode_payload(
            value,
            label="D7 aggregate-gate-outcomes payload",
            schema_version=cls.schema_version,
            component_id=cls.component_id,
            component_contract_id=cls.component_contract_id,
            row_parser=D7AggregateGateOutcome,
            extra_keys=frozenset({"gate_manifest_sha256"}),
        )
        item = _mapping(value, "D7 aggregate-gate-outcomes payload")
        result = cls(
            gate_manifest_sha256=_sha256(
                item["gate_manifest_sha256"], "gate_manifest_sha256"
            ),
            records=cast(tuple[D7AggregateGateOutcome, ...], records),
            **common,
        )
        if root != result.component_root_sha256:
            raise QualificationContractError("component_root_sha256 differs")
        return result


D7ResultComponentPayload = (
    D7ExecutionEventLedgerPayload
    | D7CoreCellOutcomesPayload
    | D7LoopCellOutcomesPayload
    | D7PrimaryUnitOutcomesPayload
    | D7RequiredStratumOutcomesPayload
    | D7AggregateGateOutcomesPayload
)
