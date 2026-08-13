"""Typed single-terminal execution lifecycle contracts."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
import re
from threading import Lock

from spirallens.core.canonical import (
    canonical_json_bytes,
    canonical_json_sha256,
)

from .contracts import (
    AtlasAccessContractError,
    AtlasAccessPolicy,
    AtlasConsumer,
    AttemptPolicy,
    ProvenanceTaint,
    _enum_value,
    _exact_keys,
    _mapping,
    _sha256,
    restrict_atlas_access,
)


ATTEMPT_TERMINAL_RECORD_SCHEMA_VERSION = "spirallens.execution-attempt-terminal.v0.1"

_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/+-]{0,255}$")


class AttemptLifecycleError(RuntimeError):
    """Raised when an attempt violates its one-terminal lifecycle."""


class AttemptPhase(str, Enum):
    PREFLIGHT = "preflight"
    MODEL_ACCESS = "model_access"
    CAPTURE = "capture"
    ATLAS_FINALIZATION = "atlas_finalization"
    RECEIPT_PUBLICATION = "receipt_publication"
    POSTPUBLICATION_VALIDATION = "postpublication_validation"


class AttemptTerminalState(str, Enum):
    COMPLETED_RECEIPTED = "completed_receipted"
    FAILED_BEFORE_MODEL_ACCESS = "failed_before_model_access"
    FAILED_AFTER_MODEL_BEFORE_PAYLOAD = "failed_after_model_before_payload"
    FAILED_AFTER_PAYLOAD = "failed_after_payload"
    TERMINAL_UNRECEIPTED = "terminal_unreceipted"
    PUBLICATION_VALIDATION_FAILED = "publication_validation_failed"
    INTERRUPTED_UNKNOWN = "interrupted_unknown"


class QuarantineDisposition(str, Enum):
    NOT_REQUIRED = "not_required"
    REQUIRED_RETAIN_FOR_FORENSICS = "required_retain_for_forensics"


def _identifier(value: object, *, label: str) -> str:
    if not isinstance(value, str) or _IDENTIFIER.fullmatch(value) is None:
        raise AtlasAccessContractError(f"{label} must be a portable identifier")
    return value


def _fact(value: object, *, label: str) -> bool | None:
    if value is not None and type(value) is not bool:
        raise AtlasAccessContractError(f"{label} must be boolean or null")
    return value


@dataclass(frozen=True, slots=True)
class AttemptAccessFacts:
    """Access facts may be unknown only for an interrupted attempt."""

    model_accessed: bool | None
    payload_persisted: bool | None
    outcome_observed: bool | None

    def __post_init__(self) -> None:
        for name in (
            "model_accessed",
            "payload_persisted",
            "outcome_observed",
        ):
            _fact(getattr(self, name), label=f"access_facts.{name}")
        if self.payload_persisted is True and self.model_accessed is False:
            raise AtlasAccessContractError(
                "payload cannot be persisted before model access"
            )
        if self.outcome_observed is True and self.payload_persisted is False:
            raise AtlasAccessContractError(
                "an outcome cannot be observed when payload persistence is known false"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "model_accessed": self.model_accessed,
            "payload_persisted": self.payload_persisted,
            "outcome_observed": self.outcome_observed,
        }

    @classmethod
    def from_dict(
        cls,
        value: Mapping[str, object],
    ) -> "AttemptAccessFacts":
        item = _mapping(value, label="access_facts")
        fields = {
            "model_accessed",
            "payload_persisted",
            "outcome_observed",
        }
        _exact_keys(item, fields, label="access_facts")
        return cls(
            model_accessed=_fact(
                item["model_accessed"],
                label="access_facts.model_accessed",
            ),
            payload_persisted=_fact(
                item["payload_persisted"],
                label="access_facts.payload_persisted",
            ),
            outcome_observed=_fact(
                item["outcome_observed"],
                label="access_facts.outcome_observed",
            ),
        )


_QUARANTINE_STATES = frozenset(
    {
        AttemptTerminalState.FAILED_AFTER_PAYLOAD,
        AttemptTerminalState.TERMINAL_UNRECEIPTED,
        AttemptTerminalState.PUBLICATION_VALIDATION_FAILED,
        AttemptTerminalState.INTERRUPTED_UNKNOWN,
    }
)
_UNRECEIPTED_STATES = frozenset(
    {
        AttemptTerminalState.TERMINAL_UNRECEIPTED,
        AttemptTerminalState.PUBLICATION_VALIDATION_FAILED,
    }
)


@dataclass(frozen=True, slots=True)
class AttemptTerminalRecord:
    """One immutable terminal classification for one execution attempt."""

    attempt_id: str
    descriptor_id: str
    descriptor_canonical_sha256: str
    output_id: str
    state: AttemptTerminalState
    phase: AttemptPhase
    access_facts: AttemptAccessFacts
    quarantine: QuarantineDisposition
    reason_code: str
    access_policy: AtlasAccessPolicy
    attempt_policy: AttemptPolicy
    schema_version: str = ATTEMPT_TERMINAL_RECORD_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != ATTEMPT_TERMINAL_RECORD_SCHEMA_VERSION:
            raise AtlasAccessContractError("unsupported terminal attempt record schema")
        for name in (
            "attempt_id",
            "descriptor_id",
            "output_id",
            "reason_code",
        ):
            _identifier(getattr(self, name), label=name)
        _sha256(
            self.descriptor_canonical_sha256,
            label="descriptor_canonical_sha256",
        )
        if not isinstance(self.state, AttemptTerminalState):
            raise TypeError("state must be an AttemptTerminalState")
        if not isinstance(self.phase, AttemptPhase):
            raise TypeError("phase must be an AttemptPhase")
        if not isinstance(self.access_facts, AttemptAccessFacts):
            raise TypeError("access_facts must be an AttemptAccessFacts")
        if not isinstance(self.quarantine, QuarantineDisposition):
            raise TypeError("quarantine must be a QuarantineDisposition")
        if not isinstance(self.access_policy, AtlasAccessPolicy):
            raise TypeError("access_policy must be an AtlasAccessPolicy")
        if not isinstance(self.attempt_policy, AttemptPolicy):
            raise TypeError("attempt_policy must be an AttemptPolicy")

        required_quarantine = self.state in _QUARANTINE_STATES
        if required_quarantine != (
            self.quarantine is QuarantineDisposition.REQUIRED_RETAIN_FOR_FORENSICS
        ):
            raise AtlasAccessContractError(
                "terminal state and quarantine disposition differ"
            )
        facts = self.access_facts
        if self.state is not AttemptTerminalState.INTERRUPTED_UNKNOWN and any(
            value is None for value in facts.to_dict().values()
        ):
            raise AtlasAccessContractError(
                "only interrupted_unknown may retain unknown access facts"
            )
        if self.state is AttemptTerminalState.COMPLETED_RECEIPTED:
            if (
                self.phase is not AttemptPhase.POSTPUBLICATION_VALIDATION
                or facts.model_accessed is not True
                or facts.payload_persisted is not True
            ):
                raise AtlasAccessContractError(
                    "completed_receipted requires validated persisted payload"
                )
        elif self.state is AttemptTerminalState.FAILED_BEFORE_MODEL_ACCESS:
            if self.phase is not AttemptPhase.PREFLIGHT or facts != AttemptAccessFacts(
                model_accessed=False,
                payload_persisted=False,
                outcome_observed=False,
            ):
                raise AtlasAccessContractError(
                    "failed_before_model_access facts are inconsistent"
                )
        elif self.state is AttemptTerminalState.FAILED_AFTER_MODEL_BEFORE_PAYLOAD:
            if (
                self.phase not in {AttemptPhase.MODEL_ACCESS, AttemptPhase.CAPTURE}
                or facts.model_accessed is not True
                or facts.payload_persisted is not False
                or facts.outcome_observed is not False
            ):
                raise AtlasAccessContractError(
                    "failed_after_model_before_payload facts are inconsistent"
                )
        elif self.state is AttemptTerminalState.FAILED_AFTER_PAYLOAD:
            if (
                self.phase
                not in {
                    AttemptPhase.CAPTURE,
                    AttemptPhase.ATLAS_FINALIZATION,
                }
                or facts.model_accessed is not True
                or facts.payload_persisted is not True
            ):
                raise AtlasAccessContractError(
                    "failed_after_payload facts are inconsistent"
                )
        elif self.state is AttemptTerminalState.TERMINAL_UNRECEIPTED:
            if (
                self.phase is not AttemptPhase.RECEIPT_PUBLICATION
                or facts.model_accessed is not True
                or facts.payload_persisted is not True
            ):
                raise AtlasAccessContractError(
                    "terminal_unreceipted requires a complete persisted "
                    "payload at receipt publication"
                )
        elif self.state is AttemptTerminalState.PUBLICATION_VALIDATION_FAILED:
            if (
                self.phase is not AttemptPhase.POSTPUBLICATION_VALIDATION
                or facts.model_accessed is not True
                or facts.payload_persisted is not True
            ):
                raise AtlasAccessContractError(
                    "publication_validation_failed facts are inconsistent"
                )
        elif self.state is AttemptTerminalState.INTERRUPTED_UNKNOWN:
            if not any(value is None for value in facts.to_dict().values()):
                raise AtlasAccessContractError(
                    "interrupted_unknown must retain at least one unknown fact"
                )

        if required_quarantine:
            if (
                ProvenanceTaint.TERMINAL_QUARANTINED
                not in self.access_policy.provenance_taints
                or not self.access_policy.allowed_consumers.issubset(
                    {AtlasConsumer.ATLAS_INTEGRITY_VALIDATION}
                )
            ):
                raise AtlasAccessContractError(
                    "quarantined attempts require terminal_quarantined taint "
                    "and integrity-only access"
                )
        has_unreceipted_taint = (
            ProvenanceTaint.TERMINAL_UNRECEIPTED in self.access_policy.provenance_taints
        )
        if (self.state in _UNRECEIPTED_STATES) != has_unreceipted_taint:
            raise AtlasAccessContractError(
                "terminal_unreceipted taint and receipt-failure state differ"
            )
        if (
            facts.payload_persisted is True
            and ProvenanceTaint.VALUE_DERIVED
            not in self.access_policy.provenance_taints
        ):
            raise AtlasAccessContractError(
                "persisted payload requires value_derived taint"
            )
        if (
            facts.outcome_observed is True
            and ProvenanceTaint.OUTCOME_EXPOSED
            not in self.access_policy.provenance_taints
        ):
            raise AtlasAccessContractError(
                "observed outcome requires outcome_exposed taint"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "attempt_id": self.attempt_id,
            "descriptor_id": self.descriptor_id,
            "descriptor_canonical_sha256": (self.descriptor_canonical_sha256),
            "output_id": self.output_id,
            "state": self.state.value,
            "phase": self.phase.value,
            "access_facts": self.access_facts.to_dict(),
            "quarantine": self.quarantine.value,
            "reason_code": self.reason_code,
            "access_policy": self.access_policy.to_dict(),
            "attempt_policy": self.attempt_policy.to_dict(),
        }

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_dict())

    @property
    def canonical_sha256(self) -> str:
        return canonical_json_sha256(self.to_dict())

    @property
    def fresh_replay_authorized(self) -> bool:
        """A replay is a new attempt, never a second terminal transition."""

        if not self.attempt_policy.fresh_replay_same_protocol_authorized:
            return False
        if (
            self.access_facts.outcome_observed is not False
            and not self.attempt_policy.retry_after_outcome_observation_authorized
        ):
            return False
        return True

    @classmethod
    def from_dict(
        cls,
        value: Mapping[str, object],
    ) -> "AttemptTerminalRecord":
        item = _mapping(value, label="terminal attempt record")
        fields = {
            "schema_version",
            "attempt_id",
            "descriptor_id",
            "descriptor_canonical_sha256",
            "output_id",
            "state",
            "phase",
            "access_facts",
            "quarantine",
            "reason_code",
            "access_policy",
            "attempt_policy",
        }
        _exact_keys(item, fields, label="terminal attempt record")
        state = _enum_value(
            item["state"],
            AttemptTerminalState,
            label="state",
        )
        phase = _enum_value(
            item["phase"],
            AttemptPhase,
            label="phase",
        )
        quarantine = _enum_value(
            item["quarantine"],
            QuarantineDisposition,
            label="quarantine",
        )
        assert isinstance(state, AttemptTerminalState)
        assert isinstance(phase, AttemptPhase)
        assert isinstance(quarantine, QuarantineDisposition)
        return cls(
            schema_version=_identifier(item["schema_version"], label="schema_version"),
            attempt_id=_identifier(item["attempt_id"], label="attempt_id"),
            descriptor_id=_identifier(item["descriptor_id"], label="descriptor_id"),
            descriptor_canonical_sha256=_sha256(
                item["descriptor_canonical_sha256"],
                label="descriptor_canonical_sha256",
            ),
            output_id=_identifier(item["output_id"], label="output_id"),
            state=state,
            phase=phase,
            access_facts=AttemptAccessFacts.from_dict(
                _mapping(item["access_facts"], label="access_facts")
            ),
            quarantine=quarantine,
            reason_code=_identifier(item["reason_code"], label="reason_code"),
            access_policy=AtlasAccessPolicy.from_dict(
                _mapping(item["access_policy"], label="access_policy")
            ),
            attempt_policy=AttemptPolicy.from_dict(
                _mapping(item["attempt_policy"], label="attempt_policy")
            ),
        )


class AttemptLifecycle:
    """In-memory capability that permits exactly one terminal transition."""

    __slots__ = (
        "_access_policy",
        "_attempt_id",
        "_attempt_policy",
        "_descriptor_canonical_sha256",
        "_descriptor_id",
        "_output_id",
        "_terminal_record",
        "_transition_lock",
    )

    def __init__(
        self,
        *,
        attempt_id: str,
        descriptor_id: str,
        descriptor_canonical_sha256: str,
        output_id: str,
        access_policy: AtlasAccessPolicy,
        attempt_policy: AttemptPolicy,
    ) -> None:
        self._attempt_id = _identifier(attempt_id, label="attempt_id")
        self._descriptor_id = _identifier(descriptor_id, label="descriptor_id")
        self._descriptor_canonical_sha256 = _sha256(
            descriptor_canonical_sha256,
            label="descriptor_canonical_sha256",
        )
        self._output_id = _identifier(output_id, label="output_id")
        if not isinstance(access_policy, AtlasAccessPolicy):
            raise TypeError("access_policy must be an AtlasAccessPolicy")
        if not isinstance(attempt_policy, AttemptPolicy):
            raise TypeError("attempt_policy must be an AttemptPolicy")
        if access_policy.provenance_taints.intersection(
            {
                ProvenanceTaint.TERMINAL_QUARANTINED,
                ProvenanceTaint.TERMINAL_UNRECEIPTED,
            }
        ):
            raise AtlasAccessContractError(
                "terminally quarantined provenance cannot start a new attempt"
            )
        self._access_policy = access_policy
        self._attempt_policy = attempt_policy
        self._terminal_record: AttemptTerminalRecord | None = None
        self._transition_lock = Lock()

    @property
    def terminal_record(self) -> AttemptTerminalRecord | None:
        with self._transition_lock:
            return self._terminal_record

    def transition_to_terminal(
        self,
        *,
        state: AttemptTerminalState,
        phase: AttemptPhase,
        access_facts: AttemptAccessFacts,
        reason_code: str,
    ) -> AttemptTerminalRecord:
        """Perform the attempt's first and only terminal transition."""

        if not isinstance(state, AttemptTerminalState):
            raise TypeError("state must be an AttemptTerminalState")
        if not isinstance(phase, AttemptPhase):
            raise TypeError("phase must be an AttemptPhase")
        if not isinstance(access_facts, AttemptAccessFacts):
            raise TypeError("access_facts must be an AttemptAccessFacts")
        validated_reason = _identifier(reason_code, label="reason_code")

        with self._transition_lock:
            if self._terminal_record is not None:
                raise AttemptLifecycleError("attempt already has a terminal record")
            taints = set(self._access_policy.provenance_taints)
            if access_facts.payload_persisted is True:
                taints.add(ProvenanceTaint.VALUE_DERIVED)
            if access_facts.outcome_observed is True:
                taints.add(ProvenanceTaint.OUTCOME_EXPOSED)
            quarantine_required = state in _QUARANTINE_STATES
            consumers = set(self._access_policy.allowed_consumers)
            eligibility = self._access_policy.scientific_claim_eligible
            if quarantine_required:
                taints.add(ProvenanceTaint.TERMINAL_QUARANTINED)
                if state in _UNRECEIPTED_STATES:
                    taints.add(ProvenanceTaint.TERMINAL_UNRECEIPTED)
                consumers.intersection_update(
                    {AtlasConsumer.ATLAS_INTEGRITY_VALIDATION}
                )
                eligibility = False
            derived_policy = restrict_atlas_access(
                self._access_policy,
                allowed_consumers=consumers,
                provenance_taints=taints,
                scientific_claim_eligible=eligibility,
            )
            record = AttemptTerminalRecord(
                attempt_id=self._attempt_id,
                descriptor_id=self._descriptor_id,
                descriptor_canonical_sha256=(self._descriptor_canonical_sha256),
                output_id=self._output_id,
                state=state,
                phase=phase,
                access_facts=access_facts,
                quarantine=(
                    QuarantineDisposition.REQUIRED_RETAIN_FOR_FORENSICS
                    if quarantine_required
                    else QuarantineDisposition.NOT_REQUIRED
                ),
                reason_code=validated_reason,
                access_policy=derived_policy,
                attempt_policy=self._attempt_policy,
            )
            self._terminal_record = record
            return record
