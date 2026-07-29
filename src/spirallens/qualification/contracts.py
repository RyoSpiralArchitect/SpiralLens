"""Canonical evidence and result contracts for synthetic D0--D5 qualification.

Core localization and loop-phase estimation are deliberately represented by
different types.  A fixed-null loop may still contain a localized amplitude
zero, so collapsing both questions into one positive/negative vocabulary
would erase a required control.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, ClassVar

from spirallens.core.canonical import canonical_json_bytes, canonical_json_sha256

from .common import (
    AttemptStatus,
    CoreDisposition,
    CorePredictionClass,
    EvaluationUnit,
    LoopDisposition,
    LoopPredictionClass,
    QualificationContractError,
    QualificationState,
)
from .protocol import (
    BOUNDARY_AXIS_ID,
    QUALIFICATION_PROTOCOL_SCHEMA_VERSION,
    GateClaimScope,
    LoopRole,
    ModuleDigest,
    QualificationProtocol,
    StressAssignment,
    _canonical_unique_slugs,
    _constant,
    _enum,
    _exact_keys,
    _finite_float,
    _mapping,
    _plain_int,
    _sequence,
    _sha256,
    _slug,
    gate_claim_scope_for_gate,
)
from .source_binding import (
    BlindInputGeneratedEventPayload,
    OracleMaterializedEventPayload,
    PredictionSealedEventPayload,
    ProtocolVerifiedEventPayload,
    QualificationEventLedgerReceipt,
    QualificationSourceBindingReceipt,
    QualificationSourceBindingSummary,
    ResultAssembledEventPayload,
    ScoredEventPayload,
    qualification_event_lane_ids,
    qualification_event_payload_sha256,
)

if TYPE_CHECKING:
    from .crossed import FieldGraphPairEffectReceipt

QUALIFICATION_RESULT_SCHEMA_VERSION = "spirallens.qualification-result.v0.10"
QUALIFICATION_RESULT_RECORD_SCOPE = (
    "full-runtime-receipts-normalized-summaries-and-event-chain"
)
# A fully materialized 64-primary D0--D5 envelope contains 1,344 typed
# evidence lanes and 8,064 ledger events.  Sixteen MiB accepts the protocol
# but cannot contain its valid terminal result; keep publication and loading
# aligned with the closed resource envelope.
MAX_QUALIFICATION_RESULT_BYTES = 32 * 1024 * 1024

_GATE_ORDER = ("d0", "d1", "d2", "d3", "d4", "d5")
_REASON = re.compile(r"^[a-z0-9][a-z0-9._-]{0,127}$")


class QualificationGateId(str, Enum):
    """The only gates carried by a D0--D5 result."""

    D0 = "d0"
    D1 = "d1"
    D2 = "d2"
    D3 = "d3"
    D4 = "d4"
    D5 = "d5"


# D0, D1, and D3 do not have a Cartesian cell manifest in the protocol.  Their
# evidence universe is therefore closed here rather than supplied by a runner.
STATIC_REQUIRED_EVIDENCE_IDS: dict[QualificationGateId, tuple[str, ...]] = {
    QualificationGateId.D0: (
        "engine-module-digests-verified",
        "protocol-manifest-verified",
    ),
    QualificationGateId.D1: (
        "cartesian-fourier-family-verified",
        "representation-family-verified",
    ),
    QualificationGateId.D3: (
        "cartesian-gauge-pipeline-rerun-verified",
        "representation-gauge-pipeline-rerun-verified",
    ),
}


def required_gate_evidence_ids(
    gate_id: QualificationGateId,
) -> tuple[str, ...]:
    """Return the closed evidence manifest for one static gate."""

    if not isinstance(gate_id, QualificationGateId):
        raise TypeError("gate_id must be a QualificationGateId")
    try:
        return STATIC_REQUIRED_EVIDENCE_IDS[gate_id]
    except KeyError as error:
        raise QualificationContractError(
            "only D0, D1, and D3 have static gate evidence"
        ) from error


def _optional_sha256(value: object, *, label: str) -> str | None:
    if value is None:
        return None
    return _sha256(value, label=label)


def _launch_authorization_sha256(
    value: object,
    *,
    protocol_id: str,
    label: str,
) -> str | None:
    authorization_sha256 = _optional_sha256(value, label=label)
    from .preparation import CLOSED_D0_D5_PROTOCOL_ID

    if protocol_id == CLOSED_D0_D5_PROTOCOL_ID and authorization_sha256 is None:
        raise QualificationContractError(
            f"{label} is required for the official closed D0-D5 protocol"
        )
    if protocol_id != CLOSED_D0_D5_PROTOCOL_ID and authorization_sha256 is not None:
        raise QualificationContractError(
            f"{label} must be None for custom/development protocols"
        )
    return authorization_sha256


def _optional_finite(
    value: object,
    *,
    label: str,
    minimum: float | None = None,
) -> float | None:
    if value is None:
        return None
    return _finite_float(value, label=label, minimum=minimum)


def _reasons(
    values: tuple[str, ...],
    *,
    state: QualificationState,
    label: str,
) -> tuple[str, ...]:
    for index, value in enumerate(values):
        if not isinstance(value, str) or _REASON.fullmatch(value) is None:
            raise QualificationContractError(
                f"{label}[{index}] must be a portable reason code"
            )
    if len(set(values)) != len(values) or values != tuple(sorted(values)):
        raise QualificationContractError(
            f"{label} must be unique and in canonical order"
        )
    if state is QualificationState.PASS and values:
        raise QualificationContractError(f"{label} must be empty for pass")
    if state is not QualificationState.PASS and not values:
        raise QualificationContractError(f"{label} must identify every non-pass result")
    return values


def _signed_row(value: object, *, label: str) -> int:
    if type(value) is not int or value < -(2**63) or value > 2**63 - 1:
        raise QualificationContractError(f"{label} must be a signed 64-bit integer")
    return value


def _canonical_rows(values: tuple[int, ...], *, label: str) -> tuple[int, ...]:
    for index, value in enumerate(values):
        _signed_row(value, label=f"{label}[{index}]")
    if values != tuple(sorted(set(values))):
        raise QualificationContractError(
            f"{label} must be unique and in canonical order"
        )
    return values


def _expected_state_from_verdict_counts(
    *,
    attempted_count: int,
    fail_graph_dependence_count: int,
    fail_count: int,
    insufficient_count: int,
    not_run_count: int,
) -> QualificationState:
    if attempted_count == 0:
        return QualificationState.NOT_RUN
    if fail_graph_dependence_count:
        return QualificationState.FAIL_GRAPH_DEPENDENCE
    if fail_count:
        return QualificationState.FAIL
    if insufficient_count:
        return QualificationState.INSUFFICIENT
    if not_run_count:
        return QualificationState.NOT_RUN
    return QualificationState.PASS


def _validate_counts(
    *,
    attempted_count: int,
    evaluable_count: int,
    attempt_insufficient_count: int,
    attempt_not_run_count: int,
    pass_count: int,
    fail_count: int,
    fail_graph_dependence_count: int,
    insufficient_count: int,
    not_run_count: int,
    state: QualificationState,
    label: str,
    allow_policy_adjustment: bool = False,
) -> None:
    counts = {
        "attempted_count": attempted_count,
        "evaluable_count": evaluable_count,
        "attempt_insufficient_count": attempt_insufficient_count,
        "attempt_not_run_count": attempt_not_run_count,
        "pass_count": pass_count,
        "fail_count": fail_count,
        "fail_graph_dependence_count": fail_graph_dependence_count,
        "insufficient_count": insufficient_count,
        "not_run_count": not_run_count,
    }
    for name, value in counts.items():
        _plain_int(value, label=f"{label}.{name}", minimum=0)
    if (
        evaluable_count + attempt_insufficient_count + attempt_not_run_count
        != attempted_count
    ):
        raise QualificationContractError(
            f"{label} attempt-status counts must sum to attempted_count"
        )
    if (
        pass_count
        + fail_count
        + fail_graph_dependence_count
        + insufficient_count
        + not_run_count
        != attempted_count
    ):
        raise QualificationContractError(
            f"{label} verdict counts must sum to attempted_count"
        )
    raw_state = _expected_state_from_verdict_counts(
        attempted_count=attempted_count,
        fail_graph_dependence_count=fail_graph_dependence_count,
        fail_count=fail_count,
        insufficient_count=insufficient_count,
        not_run_count=not_run_count,
    )
    if not allow_policy_adjustment and state is not raw_state:
        raise QualificationContractError(
            f"{label} state does not match its raw verdict counts"
        )
    if allow_policy_adjustment:
        allowed = {
            QualificationState.PASS: {
                QualificationState.PASS,
                QualificationState.INSUFFICIENT,
                QualificationState.FAIL,
            },
            QualificationState.NOT_RUN: {
                QualificationState.NOT_RUN,
                QualificationState.INSUFFICIENT,
                QualificationState.FAIL,
            },
            QualificationState.INSUFFICIENT: {
                QualificationState.INSUFFICIENT,
                QualificationState.FAIL,
            },
            QualificationState.FAIL: {QualificationState.FAIL},
            QualificationState.FAIL_GRAPH_DEPENDENCE: {
                QualificationState.FAIL_GRAPH_DEPENDENCE
            },
        }
        if state not in allowed[raw_state]:
            raise QualificationContractError(
                f"{label} policy state is incompatible with raw verdict counts"
            )


@dataclass(frozen=True, slots=True)
class GateResult:
    """One derived gate verdict with attempt status on a separate axis."""

    gate_id: QualificationGateId
    state: QualificationState
    evaluation_unit: EvaluationUnit
    attempted_count: int
    evaluable_count: int
    attempt_insufficient_count: int
    attempt_not_run_count: int
    pass_count: int
    fail_count: int
    fail_graph_dependence_count: int
    insufficient_count: int
    not_run_count: int
    reason_codes: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.gate_id, QualificationGateId):
            raise TypeError("gate_id must be a QualificationGateId")
        if not isinstance(self.state, QualificationState):
            raise TypeError("state must be a QualificationState")
        if not isinstance(self.evaluation_unit, EvaluationUnit):
            raise TypeError("evaluation_unit must be an EvaluationUnit")
        _validate_counts(
            attempted_count=self.attempted_count,
            evaluable_count=self.evaluable_count,
            attempt_insufficient_count=self.attempt_insufficient_count,
            attempt_not_run_count=self.attempt_not_run_count,
            pass_count=self.pass_count,
            fail_count=self.fail_count,
            fail_graph_dependence_count=self.fail_graph_dependence_count,
            insufficient_count=self.insufficient_count,
            not_run_count=self.not_run_count,
            state=self.state,
            label=f"gate_results.{self.gate_id.value}",
            allow_policy_adjustment=(self.gate_id is QualificationGateId.D5),
        )
        _reasons(
            self.reason_codes,
            state=self.state,
            label=f"gate_results.{self.gate_id.value}.reason_codes",
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "gate_id": self.gate_id.value,
            "claim_scope": self.claim_scope.value,
            "state": self.state.value,
            "evaluation_unit": self.evaluation_unit.value,
            "attempted_count": self.attempted_count,
            "evaluable_count": self.evaluable_count,
            "attempt_insufficient_count": self.attempt_insufficient_count,
            "attempt_not_run_count": self.attempt_not_run_count,
            "pass_count": self.pass_count,
            "fail_count": self.fail_count,
            "fail_graph_dependence_count": self.fail_graph_dependence_count,
            "insufficient_count": self.insufficient_count,
            "not_run_count": self.not_run_count,
            "reason_codes": list(self.reason_codes),
        }

    @property
    def claim_scope(self) -> GateClaimScope:
        """Positive scope that this gate is allowed to qualify."""

        return gate_claim_scope_for_gate(self.gate_id.value)

    @classmethod
    def from_dict(cls, value: object) -> GateResult:
        item = _mapping(value, label="gate result")
        expected = {
            "gate_id",
            "claim_scope",
            "state",
            "evaluation_unit",
            "attempted_count",
            "evaluable_count",
            "attempt_insufficient_count",
            "attempt_not_run_count",
            "pass_count",
            "fail_count",
            "fail_graph_dependence_count",
            "insufficient_count",
            "not_run_count",
            "reason_codes",
        }
        _exact_keys(item, expected, label="gate result")
        gate_id = _enum(
            QualificationGateId,
            item["gate_id"],
            label="gate_id",
        )
        claim_scope = _enum(
            GateClaimScope,
            item["claim_scope"],
            label="gate claim_scope",
        )
        if claim_scope is not gate_claim_scope_for_gate(gate_id.value):
            raise QualificationContractError(
                "gate claim_scope differs from its mandatory positive scope"
            )
        return cls(
            gate_id=gate_id,  # type: ignore[arg-type]
            state=_enum(QualificationState, item["state"], label="gate state"),  # type: ignore[arg-type]
            evaluation_unit=_enum(
                EvaluationUnit,
                item["evaluation_unit"],
                label="gate evaluation_unit",
            ),  # type: ignore[arg-type]
            attempted_count=_plain_int(
                item["attempted_count"], label="gate attempted_count"
            ),
            evaluable_count=_plain_int(
                item["evaluable_count"], label="gate evaluable_count"
            ),
            attempt_insufficient_count=_plain_int(
                item["attempt_insufficient_count"],
                label="gate attempt_insufficient_count",
            ),
            attempt_not_run_count=_plain_int(
                item["attempt_not_run_count"],
                label="gate attempt_not_run_count",
            ),
            pass_count=_plain_int(item["pass_count"], label="gate pass_count"),
            fail_count=_plain_int(item["fail_count"], label="gate fail_count"),
            fail_graph_dependence_count=_plain_int(
                item["fail_graph_dependence_count"],
                label="gate fail_graph_dependence_count",
            ),
            insufficient_count=_plain_int(
                item["insufficient_count"],
                label="gate insufficient_count",
            ),
            not_run_count=_plain_int(item["not_run_count"], label="gate not_run_count"),
            reason_codes=tuple(
                _slug(reason, label="gate reason code")
                for reason in _sequence(item["reason_codes"], label="gate reason_codes")
            ),
        )


@dataclass(frozen=True, slots=True)
class GateEvidenceSummary:
    """One member of the closed D0/D1/D3 evidence universe.

    D3 evidence proves an actual estimator-pipeline rerun rather than a
    coordinate-only arithmetic identity, so both estimator fingerprints and
    the explicit rerun flag are mandatory for every attempted D3 item.
    """

    gate_id: QualificationGateId
    evidence_id: str
    attempt_status: AttemptStatus
    verified: bool | None
    evidence_fingerprint_sha256: str | None
    pipeline_rerun_verified: bool | None
    base_estimator_fingerprint_sha256: str | None
    transformed_estimator_fingerprint_sha256: str | None
    reason_codes: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.gate_id not in STATIC_REQUIRED_EVIDENCE_IDS:
            raise QualificationContractError(
                "gate evidence is only defined for D0, D1, and D3"
            )
        _slug(self.evidence_id, label="gate evidence evidence_id")
        if not isinstance(self.attempt_status, AttemptStatus):
            raise TypeError("attempt_status must be an AttemptStatus")
        evidence_fp = _optional_sha256(
            self.evidence_fingerprint_sha256,
            label="gate evidence evidence_fingerprint_sha256",
        )
        base_fp = _optional_sha256(
            self.base_estimator_fingerprint_sha256,
            label="gate evidence base_estimator_fingerprint_sha256",
        )
        transformed_fp = _optional_sha256(
            self.transformed_estimator_fingerprint_sha256,
            label="gate evidence transformed_estimator_fingerprint_sha256",
        )
        if self.verified is not None and type(self.verified) is not bool:
            raise TypeError("verified must be bool or None")
        if (
            self.pipeline_rerun_verified is not None
            and type(self.pipeline_rerun_verified) is not bool
        ):
            raise TypeError("pipeline_rerun_verified must be bool or None")

        if self.attempt_status is AttemptStatus.NOT_RUN:
            if any(
                value is not None
                for value in (
                    self.verified,
                    evidence_fp,
                    self.pipeline_rerun_verified,
                    base_fp,
                    transformed_fp,
                )
            ):
                raise QualificationContractError(
                    "not_run gate evidence cannot claim observations"
                )
            state = QualificationState.NOT_RUN
        else:
            if evidence_fp is None:
                raise QualificationContractError(
                    "attempted gate evidence requires an evidence fingerprint"
                )
            if self.gate_id is QualificationGateId.D3:
                if (
                    self.pipeline_rerun_verified is None
                    or base_fp is None
                    or transformed_fp is None
                ):
                    raise QualificationContractError(
                        "attempted D3 evidence requires pipeline rerun and "
                        "base/transformed estimator fingerprints"
                    )
            elif any(
                value is not None
                for value in (
                    self.pipeline_rerun_verified,
                    base_fp,
                    transformed_fp,
                )
            ):
                raise QualificationContractError(
                    "only D3 evidence may carry pipeline-rerun fingerprints"
                )
            if self.attempt_status is AttemptStatus.INSUFFICIENT:
                if self.verified is not None:
                    raise QualificationContractError(
                        "insufficient gate evidence cannot claim verification"
                    )
                state = QualificationState.INSUFFICIENT
            else:
                if self.verified is None:
                    raise QualificationContractError(
                        "evaluable gate evidence requires a verification verdict"
                    )
                if (
                    self.gate_id is QualificationGateId.D3
                    and self.verified
                    and self.pipeline_rerun_verified is not True
                ):
                    raise QualificationContractError(
                        "passing D3 evidence requires a verified pipeline rerun"
                    )
                state = (
                    QualificationState.PASS
                    if self.verified
                    else QualificationState.FAIL
                )
        _reasons(
            self.reason_codes,
            state=state,
            label=f"gate evidence {self.evidence_id} reason_codes",
        )

    @property
    def state(self) -> QualificationState:
        if self.attempt_status is AttemptStatus.NOT_RUN:
            return QualificationState.NOT_RUN
        if self.attempt_status is AttemptStatus.INSUFFICIENT:
            return QualificationState.INSUFFICIENT
        return QualificationState.PASS if self.verified else QualificationState.FAIL

    def to_dict(self) -> dict[str, object]:
        return {
            "gate_id": self.gate_id.value,
            "evidence_id": self.evidence_id,
            "attempt_status": self.attempt_status.value,
            "verified": self.verified,
            "evidence_fingerprint_sha256": self.evidence_fingerprint_sha256,
            "pipeline_rerun_verified": self.pipeline_rerun_verified,
            "base_estimator_fingerprint_sha256": (
                self.base_estimator_fingerprint_sha256
            ),
            "transformed_estimator_fingerprint_sha256": (
                self.transformed_estimator_fingerprint_sha256
            ),
            "reason_codes": list(self.reason_codes),
        }

    @classmethod
    def from_dict(cls, value: object) -> GateEvidenceSummary:
        item = _mapping(value, label="gate evidence summary")
        expected = {
            "gate_id",
            "evidence_id",
            "attempt_status",
            "verified",
            "evidence_fingerprint_sha256",
            "pipeline_rerun_verified",
            "base_estimator_fingerprint_sha256",
            "transformed_estimator_fingerprint_sha256",
            "reason_codes",
        }
        _exact_keys(item, expected, label="gate evidence summary")
        for name in ("verified", "pipeline_rerun_verified"):
            if item[name] is not None and type(item[name]) is not bool:
                raise QualificationContractError(f"{name} must be bool or null")
        return cls(
            gate_id=_enum(
                QualificationGateId,
                item["gate_id"],
                label="gate evidence gate_id",
            ),  # type: ignore[arg-type]
            evidence_id=_slug(item["evidence_id"], label="gate evidence_id"),
            attempt_status=_enum(
                AttemptStatus,
                item["attempt_status"],
                label="gate evidence attempt_status",
            ),  # type: ignore[arg-type]
            verified=item["verified"],  # type: ignore[arg-type]
            evidence_fingerprint_sha256=_optional_sha256(
                item["evidence_fingerprint_sha256"],
                label="gate evidence_fingerprint_sha256",
            ),
            pipeline_rerun_verified=item["pipeline_rerun_verified"],  # type: ignore[arg-type]
            base_estimator_fingerprint_sha256=_optional_sha256(
                item["base_estimator_fingerprint_sha256"],
                label="gate base_estimator_fingerprint_sha256",
            ),
            transformed_estimator_fingerprint_sha256=_optional_sha256(
                item["transformed_estimator_fingerprint_sha256"],
                label="gate transformed_estimator_fingerprint_sha256",
            ),
            reason_codes=tuple(
                _slug(reason, label="gate evidence reason code")
                for reason in _sequence(item["reason_codes"], label="reason_codes")
            ),
        )


STATIC_EVIDENCE_OBLIGATIONS: dict[
    tuple[QualificationGateId, str],
    tuple[str, ...],
] = {
    (
        QualificationGateId.D1,
        "cartesian-fourier-family-verified",
    ): (
        "cartesian-oracle-numeric-law",
        "estimator-executed",
        "generator-estimator-module-separation",
        "negative-control-executed",
        "positive-control-executed",
        "prerequisite-control-executed",
    ),
    (
        QualificationGateId.D1,
        "representation-family-verified",
    ): (
        "estimator-executed",
        "generator-estimator-module-separation",
        "negative-control-executed",
        "positive-control-executed",
        "representation-oracle-numeric-law",
    ),
    (
        QualificationGateId.D3,
        "cartesian-gauge-pipeline-rerun-verified",
    ): (
        "ambient-signed-permutation",
        "loop-reversal",
        "pipeline-rerun",
        "reference-reflection",
        "reference-rotation",
    ),
    (
        QualificationGateId.D3,
        "representation-gauge-pipeline-rerun-verified",
    ): (
        "ambient-signed-permutation",
        "local-frame-gauge",
        "loop-reversal",
        "nonorientable-control",
        "pipeline-rerun",
        "reference-orientation",
        "spin-two-double-angle",
    ),
}


@dataclass(frozen=True, slots=True)
class StaticEvidenceReceipt:
    """Typed D1/D3 companion whose verdict is mechanically derived.

    This receipt deliberately has no caller-provided ``verified`` field.  A
    passing summary exists only when the exact closed obligation set was
    checked, no obligation failed, implementation modules are source-bound,
    and D3 records a nonidentity pipeline rerun.
    """

    gate_id: QualificationGateId
    evidence_id: str
    attempt_status: AttemptStatus
    underlying_receipt_sha256: str | None
    producer_modules: tuple[ModuleDigest, ...]
    checked_obligation_ids: tuple[str, ...]
    failed_obligation_ids: tuple[str, ...]
    observation_fingerprints_sha256: tuple[str, ...]
    pipeline_rerun_count: int
    base_estimator_fingerprint_sha256: str | None
    transformed_estimator_fingerprint_sha256: str | None
    schema_version: str = "spirallens.qualification-static-evidence-receipt.v0.1"

    _ROOT_KEYS: ClassVar[frozenset[str]] = frozenset(
        {
            "schema_version",
            "gate_id",
            "evidence_id",
            "attempt_status",
            "underlying_receipt_sha256",
            "producer_modules",
            "checked_obligation_ids",
            "failed_obligation_ids",
            "observation_fingerprints_sha256",
            "pipeline_rerun_count",
            "base_estimator_fingerprint_sha256",
            "transformed_estimator_fingerprint_sha256",
        }
    )

    def __post_init__(self) -> None:
        _constant(
            self.schema_version,
            "spirallens.qualification-static-evidence-receipt.v0.1",
            label="static evidence receipt schema_version",
        )
        if self.gate_id not in {QualificationGateId.D1, QualificationGateId.D3}:
            raise QualificationContractError(
                "static evidence receipts are required only for D1 and D3"
            )
        _slug(self.evidence_id, label="static evidence receipt evidence_id")
        try:
            required = STATIC_EVIDENCE_OBLIGATIONS[(self.gate_id, self.evidence_id)]
        except KeyError as error:
            raise QualificationContractError(
                "static evidence receipt is outside the closed D1/D3 universe"
            ) from error
        if not isinstance(self.attempt_status, AttemptStatus):
            raise TypeError("static evidence attempt_status must be AttemptStatus")
        underlying = _optional_sha256(
            self.underlying_receipt_sha256,
            label="static evidence underlying_receipt_sha256",
        )
        module_names = tuple(item.module for item in self.producer_modules)
        if module_names != tuple(sorted(set(module_names))):
            raise QualificationContractError(
                "static evidence producer modules must be unique and canonical"
            )
        _canonical_unique_slugs(
            self.checked_obligation_ids,
            label="static evidence checked_obligation_ids",
            nonempty=False,
        )
        _canonical_unique_slugs(
            self.failed_obligation_ids,
            label="static evidence failed_obligation_ids",
            nonempty=False,
        )
        if not set(self.failed_obligation_ids) <= set(self.checked_obligation_ids):
            raise QualificationContractError(
                "failed static obligations must be a subset of checked obligations"
            )
        if not set(self.checked_obligation_ids) <= set(required):
            raise QualificationContractError(
                "static evidence contains an undeclared obligation"
            )
        for index, fingerprint in enumerate(self.observation_fingerprints_sha256):
            _sha256(
                fingerprint,
                label=f"static evidence observation fingerprint[{index}]",
            )
        if self.observation_fingerprints_sha256 != tuple(
            sorted(set(self.observation_fingerprints_sha256))
        ):
            raise QualificationContractError(
                "static evidence observations must be unique and canonical"
            )
        _plain_int(
            self.pipeline_rerun_count,
            label="static evidence pipeline_rerun_count",
            minimum=0,
        )
        base = _optional_sha256(
            self.base_estimator_fingerprint_sha256,
            label="static evidence base_estimator_fingerprint_sha256",
        )
        transformed = _optional_sha256(
            self.transformed_estimator_fingerprint_sha256,
            label="static evidence transformed_estimator_fingerprint_sha256",
        )
        if self.attempt_status is AttemptStatus.NOT_RUN:
            if (
                underlying is not None
                or self.producer_modules
                or self.checked_obligation_ids
                or self.failed_obligation_ids
                or self.observation_fingerprints_sha256
                or self.pipeline_rerun_count
                or base is not None
                or transformed is not None
            ):
                raise QualificationContractError(
                    "not_run static receipts cannot claim runtime evidence"
                )
            return
        if (
            underlying is None
            or len(self.producer_modules) < 2
            or not self.observation_fingerprints_sha256
        ):
            raise QualificationContractError(
                "attempted static receipts require an underlying receipt, "
                "at least two producer modules, and observations"
            )
        if self.gate_id is QualificationGateId.D1:
            if (
                self.pipeline_rerun_count != 0
                or base is not None
                or transformed is not None
            ):
                raise QualificationContractError(
                    "D1 static receipts cannot claim D3 pipeline fields"
                )
        elif (
            (
                self.pipeline_rerun_count < 2
                or base is None
                or transformed is None
                or base == transformed
            )
            and self.attempt_status is AttemptStatus.EVALUABLE
            and not self.failed_obligation_ids
        ):
            raise QualificationContractError(
                "evaluable D3 receipts without declared failures require "
                "two executions and nonidentity estimator fingerprints"
            )
        if (
            self.attempt_status is AttemptStatus.EVALUABLE
            and not self.failed_obligation_ids
            and self.checked_obligation_ids != required
        ):
            raise QualificationContractError(
                "evaluable passing static receipts must check the exact "
                "closed obligation set"
            )

    @property
    def required_obligation_ids(self) -> tuple[str, ...]:
        return STATIC_EVIDENCE_OBLIGATIONS[(self.gate_id, self.evidence_id)]

    @property
    def verified(self) -> bool | None:
        if self.attempt_status is not AttemptStatus.EVALUABLE:
            return None
        return (
            self.checked_obligation_ids == self.required_obligation_ids
            and not self.failed_obligation_ids
            and (
                self.gate_id is QualificationGateId.D1
                or (
                    self.pipeline_rerun_count >= 2
                    and self.base_estimator_fingerprint_sha256
                    != self.transformed_estimator_fingerprint_sha256
                )
            )
        )

    @property
    def pipeline_rerun_verified(self) -> bool | None:
        if self.gate_id is not QualificationGateId.D3:
            return None
        if self.attempt_status is AttemptStatus.NOT_RUN:
            return None
        return (
            self.pipeline_rerun_count >= 2
            and self.base_estimator_fingerprint_sha256 is not None
            and self.transformed_estimator_fingerprint_sha256 is not None
            and self.base_estimator_fingerprint_sha256
            != self.transformed_estimator_fingerprint_sha256
            and "pipeline-rerun" in self.checked_obligation_ids
            and "pipeline-rerun" not in self.failed_obligation_ids
        )

    @property
    def reason_codes(self) -> tuple[str, ...]:
        if self.attempt_status is AttemptStatus.NOT_RUN:
            return ("static-evidence-not-run",)
        if self.attempt_status is AttemptStatus.INSUFFICIENT:
            return ("static-evidence-insufficient",)
        if self.verified:
            return ()
        return ("static-evidence-obligation-failed",)

    def to_summary(self) -> GateEvidenceSummary:
        return GateEvidenceSummary(
            gate_id=self.gate_id,
            evidence_id=self.evidence_id,
            attempt_status=self.attempt_status,
            verified=self.verified,
            evidence_fingerprint_sha256=(
                None
                if self.attempt_status is AttemptStatus.NOT_RUN
                else self.canonical_sha256
            ),
            pipeline_rerun_verified=self.pipeline_rerun_verified,
            base_estimator_fingerprint_sha256=(self.base_estimator_fingerprint_sha256),
            transformed_estimator_fingerprint_sha256=(
                self.transformed_estimator_fingerprint_sha256
            ),
            reason_codes=self.reason_codes,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "gate_id": self.gate_id.value,
            "evidence_id": self.evidence_id,
            "attempt_status": self.attempt_status.value,
            "underlying_receipt_sha256": self.underlying_receipt_sha256,
            "producer_modules": [item.to_dict() for item in self.producer_modules],
            "checked_obligation_ids": list(self.checked_obligation_ids),
            "failed_obligation_ids": list(self.failed_obligation_ids),
            "observation_fingerprints_sha256": list(
                self.observation_fingerprints_sha256
            ),
            "pipeline_rerun_count": self.pipeline_rerun_count,
            "base_estimator_fingerprint_sha256": (
                self.base_estimator_fingerprint_sha256
            ),
            "transformed_estimator_fingerprint_sha256": (
                self.transformed_estimator_fingerprint_sha256
            ),
        }

    @property
    def canonical_sha256(self) -> str:
        return canonical_json_sha256(self.to_dict())

    @classmethod
    def from_dict(cls, value: object) -> StaticEvidenceReceipt:
        item = _mapping(value, label="static evidence receipt")
        _exact_keys(item, cls._ROOT_KEYS, label="static evidence receipt")
        return cls(
            schema_version=_constant(
                item["schema_version"],
                "spirallens.qualification-static-evidence-receipt.v0.1",
                label="static evidence receipt schema_version",
            ),  # type: ignore[arg-type]
            gate_id=_enum(
                QualificationGateId,
                item["gate_id"],
                label="static evidence receipt gate_id",
            ),  # type: ignore[arg-type]
            evidence_id=_slug(
                item["evidence_id"],
                label="static evidence receipt evidence_id",
            ),
            attempt_status=_enum(
                AttemptStatus,
                item["attempt_status"],
                label="static evidence receipt attempt_status",
            ),  # type: ignore[arg-type]
            underlying_receipt_sha256=_optional_sha256(
                item["underlying_receipt_sha256"],
                label="static evidence underlying_receipt_sha256",
            ),
            producer_modules=tuple(
                ModuleDigest.from_dict(entry)
                for entry in _sequence(
                    item["producer_modules"],
                    label="static evidence producer_modules",
                )
            ),
            checked_obligation_ids=tuple(
                _slug(entry, label="static evidence checked obligation")
                for entry in _sequence(
                    item["checked_obligation_ids"],
                    label="static evidence checked_obligation_ids",
                )
            ),
            failed_obligation_ids=tuple(
                _slug(entry, label="static evidence failed obligation")
                for entry in _sequence(
                    item["failed_obligation_ids"],
                    label="static evidence failed_obligation_ids",
                )
            ),
            observation_fingerprints_sha256=tuple(
                _sha256(entry, label="static evidence observation fingerprint")
                for entry in _sequence(
                    item["observation_fingerprints_sha256"],
                    label="static evidence observation_fingerprints_sha256",
                )
            ),
            pipeline_rerun_count=_plain_int(
                item["pipeline_rerun_count"],
                label="static evidence pipeline_rerun_count",
                minimum=0,
            ),
            base_estimator_fingerprint_sha256=_optional_sha256(
                item["base_estimator_fingerprint_sha256"],
                label="static evidence base_estimator_fingerprint_sha256",
            ),
            transformed_estimator_fingerprint_sha256=_optional_sha256(
                item["transformed_estimator_fingerprint_sha256"],
                label="static evidence transformed_estimator_fingerprint_sha256",
            ),
        )


def derive_static_gate(
    gate_id: QualificationGateId,
    evidence: tuple[GateEvidenceSummary, ...],
) -> GateResult:
    """Derive D0, D1, or D3 from its exact static evidence manifest."""

    required = required_gate_evidence_ids(gate_id)
    matching = tuple(item for item in evidence if item.gate_id is gate_id)
    observed_ids = tuple(item.evidence_id for item in matching)
    if observed_ids != required:
        raise QualificationContractError(
            f"{gate_id.value} evidence IDs must equal the exact static manifest"
        )
    statuses = tuple(item.attempt_status for item in matching)
    states = tuple(item.state for item in matching)
    counts = {
        "attempted_count": len(matching),
        "evaluable_count": statuses.count(AttemptStatus.EVALUABLE),
        "attempt_insufficient_count": statuses.count(AttemptStatus.INSUFFICIENT),
        "attempt_not_run_count": statuses.count(AttemptStatus.NOT_RUN),
        "pass_count": states.count(QualificationState.PASS),
        "fail_count": states.count(QualificationState.FAIL),
        "fail_graph_dependence_count": 0,
        "insufficient_count": states.count(QualificationState.INSUFFICIENT),
        "not_run_count": states.count(QualificationState.NOT_RUN),
    }
    state = _expected_state_from_verdict_counts(
        attempted_count=counts["attempted_count"],
        fail_graph_dependence_count=0,
        fail_count=counts["fail_count"],
        insufficient_count=counts["insufficient_count"],
        not_run_count=counts["not_run_count"],
    )
    reasons = sorted(
        {
            reason
            for item in matching
            if item.state is not QualificationState.PASS
            for reason in item.reason_codes
        }
    )
    if state is not QualificationState.PASS:
        reasons.append(f"{gate_id.value}-evidence-nonpass")
        reasons = sorted(set(reasons))
    return GateResult(
        gate_id=gate_id,
        state=state,
        evaluation_unit=EvaluationUnit.MATCHED_CLASS,
        reason_codes=tuple(reasons),
        **counts,
    )


@dataclass(frozen=True, slots=True)
class CoreCellSummary:
    """One graph-A core-localization observation."""

    core_cell_id: str
    primary_unit_id: str
    field_graph_id: str
    expected_disposition: CoreDisposition
    field_graph_fingerprint_sha256: str | None
    field_estimate_fingerprint_sha256: str | None
    blind_input_fingerprint_sha256: str | None
    prediction_fingerprint_sha256: str | None
    oracle_fingerprint_sha256: str | None
    candidate_fingerprint_sha256: str | None
    oracle_anchor_fingerprint_sha256: str | None
    candidate_anchor_symmetric_difference_rows: tuple[int, ...]
    attempt_status: AttemptStatus
    prediction_class: CorePredictionClass
    state: QualificationState
    reason_codes: tuple[str, ...]

    def __post_init__(self) -> None:
        for name in ("core_cell_id", "primary_unit_id", "field_graph_id"):
            _slug(getattr(self, name), label=f"core cell {name}")
        if not isinstance(self.expected_disposition, CoreDisposition):
            raise TypeError("expected_disposition must be a CoreDisposition")
        if not isinstance(self.attempt_status, AttemptStatus):
            raise TypeError("attempt_status must be an AttemptStatus")
        if not isinstance(self.prediction_class, CorePredictionClass):
            raise TypeError("prediction_class must be a CorePredictionClass")
        if not isinstance(self.state, QualificationState):
            raise TypeError("state must be a QualificationState")
        fingerprint_names = (
            "field_graph_fingerprint_sha256",
            "field_estimate_fingerprint_sha256",
            "blind_input_fingerprint_sha256",
            "prediction_fingerprint_sha256",
            "oracle_fingerprint_sha256",
            "candidate_fingerprint_sha256",
            "oracle_anchor_fingerprint_sha256",
        )
        fingerprints = tuple(
            _optional_sha256(getattr(self, name), label=f"core cell {name}")
            for name in fingerprint_names
        )
        _canonical_rows(
            self.candidate_anchor_symmetric_difference_rows,
            label="core cell candidate_anchor_symmetric_difference_rows",
        )

        if self.attempt_status is AttemptStatus.NOT_RUN:
            expected_state = QualificationState.NOT_RUN
            if any(value is not None for value in fingerprints):
                raise QualificationContractError(
                    "not_run core cells cannot claim fingerprints"
                )
            if (
                self.prediction_class is not CorePredictionClass.NONE
                or self.candidate_anchor_symmetric_difference_rows
            ):
                raise QualificationContractError(
                    "not_run core cells cannot claim a prediction or row difference"
                )
        else:
            if any(value is None for value in fingerprints):
                raise QualificationContractError(
                    "attempted core cells require every evidence fingerprint"
                )
            if self.attempt_status is AttemptStatus.INSUFFICIENT:
                if self.prediction_class is not CorePredictionClass.ABSTAIN:
                    raise QualificationContractError(
                        "insufficient core cells must abstain"
                    )
                expected_state = (
                    QualificationState.PASS
                    if self.expected_disposition is CoreDisposition.PREREQUISITE_FAILURE
                    else QualificationState.INSUFFICIENT
                )
            else:
                if self.prediction_class not in {
                    CorePredictionClass.LOCALIZED_CORE,
                    CorePredictionClass.NO_CORE,
                }:
                    raise QualificationContractError(
                        "evaluable core cells require a typed core prediction"
                    )
                correct_class = {
                    CoreDisposition.LOCALIZED_CORE: (
                        CorePredictionClass.LOCALIZED_CORE
                    ),
                    CoreDisposition.NO_CORE: CorePredictionClass.NO_CORE,
                    CoreDisposition.PREREQUISITE_FAILURE: None,
                }[self.expected_disposition]
                expected_state = (
                    QualificationState.PASS
                    if (
                        self.prediction_class is correct_class
                        and not self.candidate_anchor_symmetric_difference_rows
                    )
                    else QualificationState.FAIL
                )
        if self.state is not expected_state:
            raise QualificationContractError(
                "core cell state differs from its typed prediction and oracle evidence"
            )
        _reasons(
            self.reason_codes,
            state=self.state,
            label=f"core cell {self.core_cell_id} reason_codes",
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "core_cell_id": self.core_cell_id,
            "primary_unit_id": self.primary_unit_id,
            "field_graph_id": self.field_graph_id,
            "expected_disposition": self.expected_disposition.value,
            "field_graph_fingerprint_sha256": (self.field_graph_fingerprint_sha256),
            "field_estimate_fingerprint_sha256": (
                self.field_estimate_fingerprint_sha256
            ),
            "blind_input_fingerprint_sha256": (self.blind_input_fingerprint_sha256),
            "prediction_fingerprint_sha256": self.prediction_fingerprint_sha256,
            "oracle_fingerprint_sha256": self.oracle_fingerprint_sha256,
            "candidate_fingerprint_sha256": self.candidate_fingerprint_sha256,
            "oracle_anchor_fingerprint_sha256": (self.oracle_anchor_fingerprint_sha256),
            "candidate_anchor_symmetric_difference_rows": list(
                self.candidate_anchor_symmetric_difference_rows
            ),
            "attempt_status": self.attempt_status.value,
            "prediction_class": self.prediction_class.value,
            "state": self.state.value,
            "reason_codes": list(self.reason_codes),
        }

    @classmethod
    def from_dict(cls, value: object) -> CoreCellSummary:
        item = _mapping(value, label="core cell summary")
        expected = {
            "core_cell_id",
            "primary_unit_id",
            "field_graph_id",
            "expected_disposition",
            "field_graph_fingerprint_sha256",
            "field_estimate_fingerprint_sha256",
            "blind_input_fingerprint_sha256",
            "prediction_fingerprint_sha256",
            "oracle_fingerprint_sha256",
            "candidate_fingerprint_sha256",
            "oracle_anchor_fingerprint_sha256",
            "candidate_anchor_symmetric_difference_rows",
            "attempt_status",
            "prediction_class",
            "state",
            "reason_codes",
        }
        _exact_keys(item, expected, label="core cell summary")
        return cls(
            core_cell_id=_slug(item["core_cell_id"], label="core_cell_id"),
            primary_unit_id=_slug(item["primary_unit_id"], label="primary_unit_id"),
            field_graph_id=_slug(item["field_graph_id"], label="field_graph_id"),
            expected_disposition=_enum(
                CoreDisposition,
                item["expected_disposition"],
                label="core expected_disposition",
            ),  # type: ignore[arg-type]
            field_graph_fingerprint_sha256=_optional_sha256(
                item["field_graph_fingerprint_sha256"],
                label="core field_graph_fingerprint_sha256",
            ),
            field_estimate_fingerprint_sha256=_optional_sha256(
                item["field_estimate_fingerprint_sha256"],
                label="core field_estimate_fingerprint_sha256",
            ),
            blind_input_fingerprint_sha256=_optional_sha256(
                item["blind_input_fingerprint_sha256"],
                label="core blind_input_fingerprint_sha256",
            ),
            prediction_fingerprint_sha256=_optional_sha256(
                item["prediction_fingerprint_sha256"],
                label="core prediction_fingerprint_sha256",
            ),
            oracle_fingerprint_sha256=_optional_sha256(
                item["oracle_fingerprint_sha256"],
                label="core oracle_fingerprint_sha256",
            ),
            candidate_fingerprint_sha256=_optional_sha256(
                item["candidate_fingerprint_sha256"],
                label="core candidate_fingerprint_sha256",
            ),
            oracle_anchor_fingerprint_sha256=_optional_sha256(
                item["oracle_anchor_fingerprint_sha256"],
                label="core oracle_anchor_fingerprint_sha256",
            ),
            candidate_anchor_symmetric_difference_rows=tuple(
                _signed_row(row, label="candidate-anchor row")
                for row in _sequence(
                    item["candidate_anchor_symmetric_difference_rows"],
                    label="candidate_anchor_symmetric_difference_rows",
                )
            ),
            attempt_status=_enum(
                AttemptStatus,
                item["attempt_status"],
                label="core attempt_status",
            ),  # type: ignore[arg-type]
            prediction_class=_enum(
                CorePredictionClass,
                item["prediction_class"],
                label="core prediction_class",
            ),  # type: ignore[arg-type]
            state=_enum(
                QualificationState,
                item["state"],
                label="core cell state",
            ),  # type: ignore[arg-type]
            reason_codes=tuple(
                _slug(reason, label="core cell reason code")
                for reason in _sequence(item["reason_codes"], label="reason_codes")
            ),
        )


@dataclass(frozen=True, slots=True)
class CorePrimaryUnitSummary:
    """One boundary-execution core summary after graph-A nuisance collapse.

    D2 separately joins repeated boundary executions by the identity-free
    scientific-input fingerprint before assigning one scientific input unit.
    """

    primary_unit_id: str
    selection_seed: int
    control_id: str
    expected_disposition: CoreDisposition
    stress_assignments: tuple[StressAssignment, ...]
    d2_scientific_input_fingerprint_sha256: str | None
    domain_instance_fingerprint_sha256: str | None
    support_instance_fingerprint_sha256: str | None
    attempt_status: AttemptStatus
    prediction_class: CorePredictionClass
    state: QualificationState
    max_candidate_symmetric_difference_rows: int | None
    reason_codes: tuple[str, ...]
    core_cell_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        _slug(self.primary_unit_id, label="core primary primary_unit_id")
        _plain_int(self.selection_seed, label="core primary selection_seed")
        _slug(self.control_id, label="core primary control_id")
        if not isinstance(self.expected_disposition, CoreDisposition):
            raise TypeError("expected_disposition must be a CoreDisposition")
        if not isinstance(self.attempt_status, AttemptStatus):
            raise TypeError("attempt_status must be an AttemptStatus")
        if not isinstance(self.prediction_class, CorePredictionClass):
            raise TypeError("prediction_class must be a CorePredictionClass")
        if not isinstance(self.state, QualificationState):
            raise TypeError("state must be a QualificationState")
        axes = tuple(item.axis_id for item in self.stress_assignments)
        _canonical_unique_slugs(
            axes,
            label="core primary stress assignment axes",
            nonempty=False,
        )
        domain_fp = _optional_sha256(
            self.domain_instance_fingerprint_sha256,
            label="core primary domain_instance_fingerprint_sha256",
        )
        scientific_input_fp = _optional_sha256(
            self.d2_scientific_input_fingerprint_sha256,
            label="core primary d2_scientific_input_fingerprint_sha256",
        )
        support_fp = _optional_sha256(
            self.support_instance_fingerprint_sha256,
            label="core primary support_instance_fingerprint_sha256",
        )
        _canonical_unique_slugs(
            self.core_cell_ids,
            label="core primary core_cell_ids",
        )
        if self.max_candidate_symmetric_difference_rows is not None:
            _plain_int(
                self.max_candidate_symmetric_difference_rows,
                label="core primary max_candidate_symmetric_difference_rows",
                minimum=0,
            )
        if self.attempt_status is AttemptStatus.NOT_RUN:
            if (
                self.prediction_class is not CorePredictionClass.NONE
                or scientific_input_fp is not None
                or domain_fp is not None
                or support_fp is not None
                or self.max_candidate_symmetric_difference_rows is not None
            ):
                raise QualificationContractError(
                    "not_run core primaries cannot claim runtime evidence"
                )
        else:
            if (
                domain_fp is None
                or scientific_input_fp is None
                or support_fp is None
                or self.max_candidate_symmetric_difference_rows is None
            ):
                raise QualificationContractError(
                    "attempted core primaries require runtime fingerprints and "
                    "candidate-set span"
                )
            if (
                self.attempt_status is AttemptStatus.INSUFFICIENT
                and self.prediction_class is not CorePredictionClass.ABSTAIN
            ):
                raise QualificationContractError(
                    "insufficient core primaries must abstain"
                )
            if (
                self.attempt_status is AttemptStatus.EVALUABLE
                and self.prediction_class
                not in {
                    CorePredictionClass.LOCALIZED_CORE,
                    CorePredictionClass.NO_CORE,
                }
            ):
                raise QualificationContractError(
                    "evaluable core primaries require a typed prediction"
                )
        _reasons(
            self.reason_codes,
            state=self.state,
            label=f"core primary {self.primary_unit_id} reason_codes",
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "primary_unit_id": self.primary_unit_id,
            "selection_seed": self.selection_seed,
            "control_id": self.control_id,
            "expected_disposition": self.expected_disposition.value,
            "stress_assignments": [
                assignment.to_dict() for assignment in self.stress_assignments
            ],
            "d2_scientific_input_fingerprint_sha256": (
                self.d2_scientific_input_fingerprint_sha256
            ),
            "domain_instance_fingerprint_sha256": (
                self.domain_instance_fingerprint_sha256
            ),
            "support_instance_fingerprint_sha256": (
                self.support_instance_fingerprint_sha256
            ),
            "attempt_status": self.attempt_status.value,
            "prediction_class": self.prediction_class.value,
            "state": self.state.value,
            "max_candidate_symmetric_difference_rows": (
                self.max_candidate_symmetric_difference_rows
            ),
            "reason_codes": list(self.reason_codes),
            "core_cell_ids": list(self.core_cell_ids),
        }

    @classmethod
    def from_dict(cls, value: object) -> CorePrimaryUnitSummary:
        item = _mapping(value, label="core primary unit summary")
        expected = {
            "primary_unit_id",
            "selection_seed",
            "control_id",
            "expected_disposition",
            "stress_assignments",
            "d2_scientific_input_fingerprint_sha256",
            "domain_instance_fingerprint_sha256",
            "support_instance_fingerprint_sha256",
            "attempt_status",
            "prediction_class",
            "state",
            "max_candidate_symmetric_difference_rows",
            "reason_codes",
            "core_cell_ids",
        }
        _exact_keys(item, expected, label="core primary unit summary")
        span_raw = item["max_candidate_symmetric_difference_rows"]
        span = (
            None
            if span_raw is None
            else _plain_int(
                span_raw,
                label="max_candidate_symmetric_difference_rows",
                minimum=0,
            )
        )
        return cls(
            primary_unit_id=_slug(item["primary_unit_id"], label="primary_unit_id"),
            selection_seed=_plain_int(item["selection_seed"], label="selection_seed"),
            control_id=_slug(item["control_id"], label="control_id"),
            expected_disposition=_enum(
                CoreDisposition,
                item["expected_disposition"],
                label="core primary expected_disposition",
            ),  # type: ignore[arg-type]
            stress_assignments=tuple(
                StressAssignment.from_dict(assignment)
                for assignment in _sequence(
                    item["stress_assignments"], label="stress_assignments"
                )
            ),
            d2_scientific_input_fingerprint_sha256=_optional_sha256(
                item["d2_scientific_input_fingerprint_sha256"],
                label="d2_scientific_input_fingerprint_sha256",
            ),
            domain_instance_fingerprint_sha256=_optional_sha256(
                item["domain_instance_fingerprint_sha256"],
                label="core primary domain_instance_fingerprint_sha256",
            ),
            support_instance_fingerprint_sha256=_optional_sha256(
                item["support_instance_fingerprint_sha256"],
                label="core primary support_instance_fingerprint_sha256",
            ),
            attempt_status=_enum(
                AttemptStatus,
                item["attempt_status"],
                label="core primary attempt_status",
            ),  # type: ignore[arg-type]
            prediction_class=_enum(
                CorePredictionClass,
                item["prediction_class"],
                label="core primary prediction_class",
            ),  # type: ignore[arg-type]
            state=_enum(
                QualificationState,
                item["state"],
                label="core primary state",
            ),  # type: ignore[arg-type]
            max_candidate_symmetric_difference_rows=span,
            reason_codes=tuple(
                _slug(reason, label="core primary reason code")
                for reason in _sequence(item["reason_codes"], label="reason_codes")
            ),
            core_cell_ids=tuple(
                _slug(cell_id, label="core primary core cell ID")
                for cell_id in _sequence(item["core_cell_ids"], label="core_cell_ids")
            ),
        )


@dataclass(frozen=True, slots=True)
class CrossedCellSummary:
    """One loop-only A × B × loop-role observation."""

    cell_id: str
    primary_unit_id: str
    field_graph_id: str
    cycle_graph_id: str
    loop_role: LoopRole
    expected_disposition: LoopDisposition
    field_graph_fingerprint_sha256: str | None
    cycle_graph_fingerprint_sha256: str | None
    field_estimate_fingerprint_sha256: str | None
    cycle_binding_fingerprint_sha256: str | None
    representative_content_sha256: str | None
    blind_input_fingerprint_sha256: str | None
    prediction_fingerprint_sha256: str | None
    oracle_fingerprint_sha256: str | None
    attempt_status: AttemptStatus
    prediction_class: LoopPredictionClass
    state: QualificationState
    continuous_signed_total_cycles: float | None
    oracle_absolute_error_cycles: float | None
    reason_codes: tuple[str, ...]

    def __post_init__(self) -> None:
        for name in (
            "cell_id",
            "primary_unit_id",
            "field_graph_id",
            "cycle_graph_id",
        ):
            _slug(getattr(self, name), label=f"loop cell {name}")
        if not isinstance(self.loop_role, LoopRole):
            raise TypeError("loop_role must be a LoopRole")
        if not isinstance(self.expected_disposition, LoopDisposition):
            raise TypeError("expected_disposition must be a LoopDisposition")
        if not isinstance(self.attempt_status, AttemptStatus):
            raise TypeError("attempt_status must be an AttemptStatus")
        if not isinstance(self.prediction_class, LoopPredictionClass):
            raise TypeError("prediction_class must be a LoopPredictionClass")
        if not isinstance(self.state, QualificationState):
            raise TypeError("state must be a QualificationState")
        fingerprint_names = (
            "field_graph_fingerprint_sha256",
            "cycle_graph_fingerprint_sha256",
            "field_estimate_fingerprint_sha256",
            "cycle_binding_fingerprint_sha256",
            "representative_content_sha256",
            "blind_input_fingerprint_sha256",
            "prediction_fingerprint_sha256",
            "oracle_fingerprint_sha256",
        )
        fingerprints = tuple(
            _optional_sha256(getattr(self, name), label=f"loop cell {name}")
            for name in fingerprint_names
        )
        total = _optional_finite(
            self.continuous_signed_total_cycles,
            label="loop cell continuous_signed_total_cycles",
        )
        error = _optional_finite(
            self.oracle_absolute_error_cycles,
            label="loop cell oracle_absolute_error_cycles",
            minimum=0.0,
        )
        if self.attempt_status is AttemptStatus.NOT_RUN:
            if (
                any(value is not None for value in fingerprints)
                or total is not None
                or error is not None
                or self.prediction_class is not LoopPredictionClass.NONE
                or self.state is not QualificationState.NOT_RUN
            ):
                raise QualificationContractError(
                    "not_run loop cells cannot claim runtime observations"
                )
        else:
            if any(value is None for value in fingerprints):
                raise QualificationContractError(
                    "attempted loop cells require every evidence fingerprint"
                )
            if self.attempt_status is AttemptStatus.INSUFFICIENT:
                if (
                    self.prediction_class is not LoopPredictionClass.ABSTAIN
                    or total is not None
                    or error is not None
                ):
                    raise QualificationContractError(
                        "insufficient loop cells must abstain without totals"
                    )
                allowed_states = (
                    {QualificationState.PASS, QualificationState.FAIL}
                    if self.expected_disposition is LoopDisposition.PREREQUISITE_FAILURE
                    else {QualificationState.INSUFFICIENT}
                )
                if self.state not in allowed_states:
                    raise QualificationContractError(
                        "insufficient loop cell state differs from its disposition"
                    )
            else:
                if (
                    self.prediction_class
                    not in {
                        LoopPredictionClass.NONZERO,
                        LoopPredictionClass.NULL,
                    }
                    or total is None
                    or error is None
                ):
                    raise QualificationContractError(
                        "evaluable loop cells require class, total, and oracle error"
                    )
                expected_class = {
                    LoopDisposition.NONZERO: LoopPredictionClass.NONZERO,
                    LoopDisposition.NULL: LoopPredictionClass.NULL,
                    LoopDisposition.PREREQUISITE_FAILURE: None,
                }[self.expected_disposition]
                if (
                    self.prediction_class is not expected_class
                    and self.state is not QualificationState.FAIL
                ):
                    raise QualificationContractError("incorrect loop classes must fail")
                if self.expected_disposition is LoopDisposition.PREREQUISITE_FAILURE:
                    if self.state is not QualificationState.FAIL:
                        raise QualificationContractError(
                            "forced loop output on a prerequisite control must fail"
                        )
                elif self.state not in {
                    QualificationState.PASS,
                    QualificationState.FAIL,
                }:
                    raise QualificationContractError(
                        "evaluable loop cells must pass or fail"
                    )
        if self.state is QualificationState.FAIL_GRAPH_DEPENDENCE:
            raise QualificationContractError(
                "graph dependence is a cross-cell primary verdict, not a cell verdict"
            )
        _reasons(
            self.reason_codes,
            state=self.state,
            label=f"loop cell {self.cell_id} reason_codes",
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "cell_id": self.cell_id,
            "primary_unit_id": self.primary_unit_id,
            "field_graph_id": self.field_graph_id,
            "cycle_graph_id": self.cycle_graph_id,
            "loop_role": self.loop_role.value,
            "expected_disposition": self.expected_disposition.value,
            "field_graph_fingerprint_sha256": (self.field_graph_fingerprint_sha256),
            "cycle_graph_fingerprint_sha256": (self.cycle_graph_fingerprint_sha256),
            "field_estimate_fingerprint_sha256": (
                self.field_estimate_fingerprint_sha256
            ),
            "cycle_binding_fingerprint_sha256": (self.cycle_binding_fingerprint_sha256),
            "representative_content_sha256": self.representative_content_sha256,
            "blind_input_fingerprint_sha256": self.blind_input_fingerprint_sha256,
            "prediction_fingerprint_sha256": self.prediction_fingerprint_sha256,
            "oracle_fingerprint_sha256": self.oracle_fingerprint_sha256,
            "attempt_status": self.attempt_status.value,
            "prediction_class": self.prediction_class.value,
            "state": self.state.value,
            "continuous_signed_total_cycles": self.continuous_signed_total_cycles,
            "oracle_absolute_error_cycles": self.oracle_absolute_error_cycles,
            "reason_codes": list(self.reason_codes),
        }

    @classmethod
    def from_dict(cls, value: object) -> CrossedCellSummary:
        item = _mapping(value, label="loop crossed cell summary")
        expected = {
            "cell_id",
            "primary_unit_id",
            "field_graph_id",
            "cycle_graph_id",
            "loop_role",
            "expected_disposition",
            "field_graph_fingerprint_sha256",
            "cycle_graph_fingerprint_sha256",
            "field_estimate_fingerprint_sha256",
            "cycle_binding_fingerprint_sha256",
            "representative_content_sha256",
            "blind_input_fingerprint_sha256",
            "prediction_fingerprint_sha256",
            "oracle_fingerprint_sha256",
            "attempt_status",
            "prediction_class",
            "state",
            "continuous_signed_total_cycles",
            "oracle_absolute_error_cycles",
            "reason_codes",
        }
        _exact_keys(item, expected, label="loop crossed cell summary")
        return cls(
            cell_id=_slug(item["cell_id"], label="cell_id"),
            primary_unit_id=_slug(item["primary_unit_id"], label="primary_unit_id"),
            field_graph_id=_slug(item["field_graph_id"], label="field_graph_id"),
            cycle_graph_id=_slug(item["cycle_graph_id"], label="cycle_graph_id"),
            loop_role=_enum(
                LoopRole,
                item["loop_role"],
                label="loop_role",
            ),  # type: ignore[arg-type]
            expected_disposition=_enum(
                LoopDisposition,
                item["expected_disposition"],
                label="loop expected_disposition",
            ),  # type: ignore[arg-type]
            field_graph_fingerprint_sha256=_optional_sha256(
                item["field_graph_fingerprint_sha256"],
                label="field_graph_fingerprint_sha256",
            ),
            cycle_graph_fingerprint_sha256=_optional_sha256(
                item["cycle_graph_fingerprint_sha256"],
                label="cycle_graph_fingerprint_sha256",
            ),
            field_estimate_fingerprint_sha256=_optional_sha256(
                item["field_estimate_fingerprint_sha256"],
                label="field_estimate_fingerprint_sha256",
            ),
            cycle_binding_fingerprint_sha256=_optional_sha256(
                item["cycle_binding_fingerprint_sha256"],
                label="cycle_binding_fingerprint_sha256",
            ),
            representative_content_sha256=_optional_sha256(
                item["representative_content_sha256"],
                label="representative_content_sha256",
            ),
            blind_input_fingerprint_sha256=_optional_sha256(
                item["blind_input_fingerprint_sha256"],
                label="blind_input_fingerprint_sha256",
            ),
            prediction_fingerprint_sha256=_optional_sha256(
                item["prediction_fingerprint_sha256"],
                label="prediction_fingerprint_sha256",
            ),
            oracle_fingerprint_sha256=_optional_sha256(
                item["oracle_fingerprint_sha256"],
                label="oracle_fingerprint_sha256",
            ),
            attempt_status=_enum(
                AttemptStatus,
                item["attempt_status"],
                label="loop attempt_status",
            ),  # type: ignore[arg-type]
            prediction_class=_enum(
                LoopPredictionClass,
                item["prediction_class"],
                label="loop prediction_class",
            ),  # type: ignore[arg-type]
            state=_enum(
                QualificationState,
                item["state"],
                label="loop cell state",
            ),  # type: ignore[arg-type]
            continuous_signed_total_cycles=_optional_finite(
                item["continuous_signed_total_cycles"],
                label="continuous_signed_total_cycles",
            ),
            oracle_absolute_error_cycles=_optional_finite(
                item["oracle_absolute_error_cycles"],
                label="oracle_absolute_error_cycles",
                minimum=0.0,
            ),
            reason_codes=tuple(
                _slug(reason, label="loop cell reason code")
                for reason in _sequence(item["reason_codes"], label="reason_codes")
            ),
        )


@dataclass(frozen=True, slots=True)
class PrimaryUnitSummary:
    """One loop inferential unit after collapsing A × B × role repeats."""

    primary_unit_id: str
    selection_seed: int
    control_id: str
    expected_disposition: LoopDisposition
    stress_assignments: tuple[StressAssignment, ...]
    domain_instance_fingerprint_sha256: str | None
    support_instance_fingerprint_sha256: str | None
    attempt_status: AttemptStatus
    prediction_class: LoopPredictionClass
    state: QualificationState
    continuous_total_span_cycles: float | None
    reason_codes: tuple[str, ...]
    crossed_cell_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        _slug(self.primary_unit_id, label="loop primary primary_unit_id")
        _plain_int(self.selection_seed, label="loop primary selection_seed")
        _slug(self.control_id, label="loop primary control_id")
        if not isinstance(self.expected_disposition, LoopDisposition):
            raise TypeError("expected_disposition must be a LoopDisposition")
        if not isinstance(self.attempt_status, AttemptStatus):
            raise TypeError("attempt_status must be an AttemptStatus")
        if not isinstance(self.prediction_class, LoopPredictionClass):
            raise TypeError("prediction_class must be a LoopPredictionClass")
        if not isinstance(self.state, QualificationState):
            raise TypeError("state must be a QualificationState")
        axes = tuple(item.axis_id for item in self.stress_assignments)
        _canonical_unique_slugs(
            axes,
            label="loop primary stress assignment axes",
            nonempty=False,
        )
        domain_fp = _optional_sha256(
            self.domain_instance_fingerprint_sha256,
            label="loop primary domain_instance_fingerprint_sha256",
        )
        support_fp = _optional_sha256(
            self.support_instance_fingerprint_sha256,
            label="loop primary support_instance_fingerprint_sha256",
        )
        span = _optional_finite(
            self.continuous_total_span_cycles,
            label="loop primary continuous_total_span_cycles",
            minimum=0.0,
        )
        _canonical_unique_slugs(
            self.crossed_cell_ids,
            label="loop primary crossed_cell_ids",
        )
        if self.attempt_status is AttemptStatus.NOT_RUN:
            if (
                self.prediction_class is not LoopPredictionClass.NONE
                or domain_fp is not None
                or support_fp is not None
                or span is not None
            ):
                raise QualificationContractError(
                    "not_run loop primaries cannot claim runtime evidence"
                )
        else:
            if domain_fp is None or support_fp is None or span is None:
                raise QualificationContractError(
                    "attempted loop primaries require runtime fingerprints and "
                    "continuous-total span"
                )
            if (
                self.attempt_status is AttemptStatus.INSUFFICIENT
                and self.prediction_class is not LoopPredictionClass.ABSTAIN
            ):
                raise QualificationContractError(
                    "insufficient loop primaries must abstain"
                )
            if (
                self.attempt_status is AttemptStatus.EVALUABLE
                and self.prediction_class
                not in {
                    LoopPredictionClass.NONZERO,
                    LoopPredictionClass.NULL,
                }
            ):
                raise QualificationContractError(
                    "evaluable loop primaries require a typed prediction"
                )
        _reasons(
            self.reason_codes,
            state=self.state,
            label=f"loop primary {self.primary_unit_id} reason_codes",
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "primary_unit_id": self.primary_unit_id,
            "selection_seed": self.selection_seed,
            "control_id": self.control_id,
            "expected_disposition": self.expected_disposition.value,
            "stress_assignments": [
                assignment.to_dict() for assignment in self.stress_assignments
            ],
            "domain_instance_fingerprint_sha256": (
                self.domain_instance_fingerprint_sha256
            ),
            "support_instance_fingerprint_sha256": (
                self.support_instance_fingerprint_sha256
            ),
            "attempt_status": self.attempt_status.value,
            "prediction_class": self.prediction_class.value,
            "state": self.state.value,
            "continuous_total_span_cycles": self.continuous_total_span_cycles,
            "reason_codes": list(self.reason_codes),
            "crossed_cell_ids": list(self.crossed_cell_ids),
        }

    @classmethod
    def from_dict(cls, value: object) -> PrimaryUnitSummary:
        item = _mapping(value, label="loop primary unit summary")
        expected = {
            "primary_unit_id",
            "selection_seed",
            "control_id",
            "expected_disposition",
            "stress_assignments",
            "domain_instance_fingerprint_sha256",
            "support_instance_fingerprint_sha256",
            "attempt_status",
            "prediction_class",
            "state",
            "continuous_total_span_cycles",
            "reason_codes",
            "crossed_cell_ids",
        }
        _exact_keys(item, expected, label="loop primary unit summary")
        return cls(
            primary_unit_id=_slug(item["primary_unit_id"], label="primary_unit_id"),
            selection_seed=_plain_int(item["selection_seed"], label="selection_seed"),
            control_id=_slug(item["control_id"], label="control_id"),
            expected_disposition=_enum(
                LoopDisposition,
                item["expected_disposition"],
                label="loop primary expected_disposition",
            ),  # type: ignore[arg-type]
            stress_assignments=tuple(
                StressAssignment.from_dict(assignment)
                for assignment in _sequence(
                    item["stress_assignments"], label="stress_assignments"
                )
            ),
            domain_instance_fingerprint_sha256=_optional_sha256(
                item["domain_instance_fingerprint_sha256"],
                label="loop primary domain_instance_fingerprint_sha256",
            ),
            support_instance_fingerprint_sha256=_optional_sha256(
                item["support_instance_fingerprint_sha256"],
                label="loop primary support_instance_fingerprint_sha256",
            ),
            attempt_status=_enum(
                AttemptStatus,
                item["attempt_status"],
                label="loop primary attempt_status",
            ),  # type: ignore[arg-type]
            prediction_class=_enum(
                LoopPredictionClass,
                item["prediction_class"],
                label="loop primary prediction_class",
            ),  # type: ignore[arg-type]
            state=_enum(
                QualificationState,
                item["state"],
                label="loop primary state",
            ),  # type: ignore[arg-type]
            continuous_total_span_cycles=_optional_finite(
                item["continuous_total_span_cycles"],
                label="continuous_total_span_cycles",
                minimum=0.0,
            ),
            reason_codes=tuple(
                _slug(reason, label="loop primary reason code")
                for reason in _sequence(item["reason_codes"], label="reason_codes")
            ),
            crossed_cell_ids=tuple(
                _slug(cell_id, label="loop primary crossed cell ID")
                for cell_id in _sequence(
                    item["crossed_cell_ids"], label="crossed_cell_ids"
                )
            ),
        )


@dataclass(frozen=True, slots=True)
class CrossedNonvacuitySummary:
    """Per-primary normalized view of one CrossedNonvacuityReceipt.

    Output variation is required only for the protocol's frozen
    field-sensitivity sentinel.  Adjacency, consumption, matched-boundary, and
    representative-content evidence remain mandatory for every control.
    """

    primary_unit_id: str
    control_id: str
    attempt_status: AttemptStatus
    receipt_fingerprint_sha256: str | None
    state: QualificationState
    substantive_output_variation_required: bool
    field_adjacency_variant_count: int
    cycle_adjacency_variant_count: int
    field_consumption_variant_count: int
    field_output_variant_count: int
    maximum_pairwise_substantive_output_distance: float | None
    minimum_substantive_output_distance: float
    field_graph_pair_effects: tuple[FieldGraphPairEffectReceipt, ...]
    substantive_response_field_graph_ids: tuple[str, ...]
    substantive_response_field_graph_count: int
    required_substantive_response_field_graph_count: int
    matched_cycle_count: int
    representative_content_variant_count: int
    minimum_representative_content_variants: int
    reason_codes: tuple[str, ...]

    def __post_init__(self) -> None:
        _slug(self.primary_unit_id, label="nonvacuity primary_unit_id")
        _slug(self.control_id, label="nonvacuity control_id")
        if not isinstance(self.attempt_status, AttemptStatus):
            raise TypeError("attempt_status must be an AttemptStatus")
        if not isinstance(self.state, QualificationState):
            raise TypeError("state must be a QualificationState")
        if type(self.substantive_output_variation_required) is not bool:
            raise TypeError("substantive_output_variation_required must be bool")
        receipt_fp = _optional_sha256(
            self.receipt_fingerprint_sha256,
            label="nonvacuity receipt_fingerprint_sha256",
        )
        maximum_distance = _optional_finite(
            self.maximum_pairwise_substantive_output_distance,
            label="nonvacuity maximum_pairwise_substantive_output_distance",
            minimum=0.0,
        )
        minimum_distance = _finite_float(
            self.minimum_substantive_output_distance,
            label="nonvacuity minimum_substantive_output_distance",
            minimum=0.0,
            maximum=1.0,
            minimum_inclusive=False,
        )
        count_names = (
            "field_adjacency_variant_count",
            "cycle_adjacency_variant_count",
            "field_consumption_variant_count",
            "field_output_variant_count",
            "substantive_response_field_graph_count",
            "matched_cycle_count",
            "representative_content_variant_count",
            "minimum_representative_content_variants",
            "required_substantive_response_field_graph_count",
        )
        for name in count_names:
            _plain_int(
                getattr(self, name),
                label=f"nonvacuity {name}",
                minimum=0,
            )
        if self.minimum_representative_content_variants < 2:
            raise QualificationContractError(
                "minimum_representative_content_variants must be at least two"
            )
        if self.required_substantive_response_field_graph_count != 3:
            raise QualificationContractError(
                "required_substantive_response_field_graph_count must equal "
                "the closed three-graph A axis"
            )
        from .crossed import (
            CrossedNonvacuityReceipt,
            FieldGraphPairEffectReceipt,
        )

        if type(self.field_graph_pair_effects) is not tuple or any(
            not isinstance(item, FieldGraphPairEffectReceipt)
            for item in self.field_graph_pair_effects
        ):
            raise QualificationContractError(
                "field_graph_pair_effects must contain typed exact receipts"
            )
        _canonical_unique_slugs(
            self.substantive_response_field_graph_ids,
            label="substantive response field graph IDs",
            nonempty=False,
        )
        if self.attempt_status is AttemptStatus.NOT_RUN:
            if (
                receipt_fp is not None
                or maximum_distance is not None
                or self.field_graph_pair_effects
                or self.substantive_response_field_graph_ids
                or any(
                    getattr(self, name) != 0
                    for name in count_names
                    if name
                    not in {
                        "minimum_representative_content_variants",
                        "required_substantive_response_field_graph_count",
                    }
                )
            ):
                raise QualificationContractError(
                    "not_run nonvacuity summaries cannot claim receipt measurements"
                )
            expected_state = QualificationState.NOT_RUN
            expected_reasons = ("crossed-nonvacuity-not-run",)
        else:
            if receipt_fp is None:
                raise QualificationContractError(
                    "attempted nonvacuity summaries require a receipt fingerprint"
                )
            if maximum_distance is None:
                raise QualificationContractError(
                    "attempted nonvacuity summaries require the measured "
                    "maximum substantive-output distance"
                )
            reconstructed = CrossedNonvacuityReceipt(
                state=self.state,
                substantive_output_variation_required=(
                    self.substantive_output_variation_required
                ),
                field_adjacency_variant_count=(self.field_adjacency_variant_count),
                cycle_adjacency_variant_count=(self.cycle_adjacency_variant_count),
                field_consumption_variant_count=(self.field_consumption_variant_count),
                field_output_variant_count=self.field_output_variant_count,
                maximum_pairwise_substantive_output_distance=maximum_distance,
                minimum_substantive_output_distance=minimum_distance,
                field_graph_pair_effects=self.field_graph_pair_effects,
                substantive_response_field_graph_ids=(
                    self.substantive_response_field_graph_ids
                ),
                substantive_response_field_graph_count=(
                    self.substantive_response_field_graph_count
                ),
                required_substantive_response_field_graph_count=(
                    self.required_substantive_response_field_graph_count
                ),
                matched_cycle_count=self.matched_cycle_count,
                representative_content_variant_count=(
                    self.representative_content_variant_count
                ),
                minimum_representative_content_variants=(
                    self.minimum_representative_content_variants
                ),
                reason_codes=self.reason_codes,
            )
            expected_reasons = reconstructed.reason_codes
            expected_state = reconstructed.state
            expected_status = (
                AttemptStatus.EVALUABLE
                if expected_state is QualificationState.PASS
                else AttemptStatus.INSUFFICIENT
            )
            if self.attempt_status is not expected_status:
                raise QualificationContractError(
                    "nonvacuity attempt status differs from its measured counts"
                )
        if self.state is not expected_state:
            raise QualificationContractError(
                "nonvacuity state differs from its measured counts"
            )
        if self.reason_codes != expected_reasons:
            raise QualificationContractError(
                "nonvacuity reasons differ from its measured counts"
            )
        _reasons(
            self.reason_codes,
            state=self.state,
            label=f"nonvacuity {self.primary_unit_id} reason_codes",
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "primary_unit_id": self.primary_unit_id,
            "control_id": self.control_id,
            "attempt_status": self.attempt_status.value,
            "receipt_fingerprint_sha256": self.receipt_fingerprint_sha256,
            "state": self.state.value,
            "substantive_output_variation_required": (
                self.substantive_output_variation_required
            ),
            "field_adjacency_variant_count": (self.field_adjacency_variant_count),
            "cycle_adjacency_variant_count": (self.cycle_adjacency_variant_count),
            "field_consumption_variant_count": (self.field_consumption_variant_count),
            "field_output_variant_count": self.field_output_variant_count,
            "maximum_pairwise_substantive_output_distance": (
                self.maximum_pairwise_substantive_output_distance
            ),
            "minimum_substantive_output_distance": (
                self.minimum_substantive_output_distance
            ),
            "field_graph_pair_effects": [
                item.to_dict() for item in self.field_graph_pair_effects
            ],
            "substantive_response_field_graph_ids": list(
                self.substantive_response_field_graph_ids
            ),
            "substantive_response_field_graph_count": (
                self.substantive_response_field_graph_count
            ),
            "required_substantive_response_field_graph_count": (
                self.required_substantive_response_field_graph_count
            ),
            "matched_cycle_count": self.matched_cycle_count,
            "representative_content_variant_count": (
                self.representative_content_variant_count
            ),
            "minimum_representative_content_variants": (
                self.minimum_representative_content_variants
            ),
            "reason_codes": list(self.reason_codes),
        }

    @classmethod
    def from_receipt(
        cls,
        *,
        primary_unit_id: str,
        control_id: str,
        receipt: object,
    ) -> CrossedNonvacuitySummary:
        """Normalize one exact in-memory CrossedNonvacuityReceipt."""

        from .crossed import CrossedNonvacuityReceipt

        if not isinstance(receipt, CrossedNonvacuityReceipt):
            raise TypeError("receipt must be a CrossedNonvacuityReceipt")
        status = (
            AttemptStatus.EVALUABLE
            if receipt.state is QualificationState.PASS
            else AttemptStatus.INSUFFICIENT
        )
        return cls(
            primary_unit_id=primary_unit_id,
            control_id=control_id,
            attempt_status=status,
            receipt_fingerprint_sha256=receipt.fingerprint_sha256,
            state=receipt.state,
            substantive_output_variation_required=(
                receipt.substantive_output_variation_required
            ),
            field_adjacency_variant_count=(receipt.field_adjacency_variant_count),
            cycle_adjacency_variant_count=(receipt.cycle_adjacency_variant_count),
            field_consumption_variant_count=(receipt.field_consumption_variant_count),
            field_output_variant_count=receipt.field_output_variant_count,
            maximum_pairwise_substantive_output_distance=(
                receipt.maximum_pairwise_substantive_output_distance
            ),
            minimum_substantive_output_distance=(
                receipt.minimum_substantive_output_distance
            ),
            field_graph_pair_effects=receipt.field_graph_pair_effects,
            substantive_response_field_graph_ids=(
                receipt.substantive_response_field_graph_ids
            ),
            substantive_response_field_graph_count=(
                receipt.substantive_response_field_graph_count
            ),
            required_substantive_response_field_graph_count=(
                receipt.required_substantive_response_field_graph_count
            ),
            matched_cycle_count=receipt.matched_cycle_count,
            representative_content_variant_count=(
                receipt.representative_content_variant_count
            ),
            minimum_representative_content_variants=(
                receipt.minimum_representative_content_variants
            ),
            reason_codes=receipt.reason_codes,
        )

    @classmethod
    def from_dict(cls, value: object) -> CrossedNonvacuitySummary:
        item = _mapping(value, label="crossed nonvacuity summary")
        expected = {
            "primary_unit_id",
            "control_id",
            "attempt_status",
            "receipt_fingerprint_sha256",
            "state",
            "substantive_output_variation_required",
            "field_adjacency_variant_count",
            "cycle_adjacency_variant_count",
            "field_consumption_variant_count",
            "field_output_variant_count",
            "maximum_pairwise_substantive_output_distance",
            "minimum_substantive_output_distance",
            "field_graph_pair_effects",
            "substantive_response_field_graph_ids",
            "substantive_response_field_graph_count",
            "required_substantive_response_field_graph_count",
            "matched_cycle_count",
            "representative_content_variant_count",
            "minimum_representative_content_variants",
            "reason_codes",
        }
        _exact_keys(item, expected, label="crossed nonvacuity summary")
        if type(item["substantive_output_variation_required"]) is not bool:
            raise QualificationContractError(
                "substantive_output_variation_required must be bool"
            )
        from .crossed import FieldGraphPairEffectReceipt

        return cls(
            primary_unit_id=_slug(item["primary_unit_id"], label="primary_unit_id"),
            control_id=_slug(item["control_id"], label="control_id"),
            attempt_status=_enum(
                AttemptStatus,
                item["attempt_status"],
                label="nonvacuity attempt_status",
            ),  # type: ignore[arg-type]
            receipt_fingerprint_sha256=_optional_sha256(
                item["receipt_fingerprint_sha256"],
                label="receipt_fingerprint_sha256",
            ),
            state=_enum(
                QualificationState,
                item["state"],
                label="nonvacuity state",
            ),  # type: ignore[arg-type]
            substantive_output_variation_required=item[
                "substantive_output_variation_required"
            ],
            field_adjacency_variant_count=_plain_int(
                item["field_adjacency_variant_count"],
                label="field_adjacency_variant_count",
            ),
            cycle_adjacency_variant_count=_plain_int(
                item["cycle_adjacency_variant_count"],
                label="cycle_adjacency_variant_count",
            ),
            field_consumption_variant_count=_plain_int(
                item["field_consumption_variant_count"],
                label="field_consumption_variant_count",
            ),
            field_output_variant_count=_plain_int(
                item["field_output_variant_count"],
                label="field_output_variant_count",
            ),
            maximum_pairwise_substantive_output_distance=_optional_finite(
                item["maximum_pairwise_substantive_output_distance"],
                label="maximum_pairwise_substantive_output_distance",
                minimum=0.0,
            ),
            minimum_substantive_output_distance=_finite_float(
                item["minimum_substantive_output_distance"],
                label="minimum_substantive_output_distance",
                minimum=0.0,
                maximum=1.0,
                minimum_inclusive=False,
            ),
            field_graph_pair_effects=tuple(
                FieldGraphPairEffectReceipt.from_dict(entry)
                for entry in _sequence(
                    item["field_graph_pair_effects"],
                    label="field_graph_pair_effects",
                )
            ),
            substantive_response_field_graph_ids=tuple(
                _slug(entry, label="substantive response field graph ID")
                for entry in _sequence(
                    item["substantive_response_field_graph_ids"],
                    label="substantive_response_field_graph_ids",
                )
            ),
            substantive_response_field_graph_count=_plain_int(
                item["substantive_response_field_graph_count"],
                label="substantive_response_field_graph_count",
            ),
            required_substantive_response_field_graph_count=_plain_int(
                item["required_substantive_response_field_graph_count"],
                label="required_substantive_response_field_graph_count",
            ),
            matched_cycle_count=_plain_int(
                item["matched_cycle_count"],
                label="matched_cycle_count",
            ),
            representative_content_variant_count=_plain_int(
                item["representative_content_variant_count"],
                label="representative_content_variant_count",
            ),
            minimum_representative_content_variants=_plain_int(
                item["minimum_representative_content_variants"],
                label="minimum_representative_content_variants",
                minimum=2,
            ),
            reason_codes=tuple(
                _slug(reason, label="nonvacuity reason code")
                for reason in _sequence(item["reason_codes"], label="reason_codes")
            ),
        )


@dataclass(frozen=True, slots=True)
class StratumSummary:
    """Worst-case aggregation over one frozen primary-unit universe.

    Every expected primary remains in the state gate.  Coverage, abstention,
    recall, and specificity use only primaries whose frozen disposition is
    ``nonzero`` or ``null``.  A prerequisite-failure primary is instead a
    required control whose correct insufficient/abstain outcome has state
    ``pass``; counting that designed abstention against coverage would make
    the closed protocol internally contradictory.
    """

    stratum_id: str
    evaluation_unit: EvaluationUnit
    required: bool
    primary_unit_ids: tuple[str, ...]
    state: QualificationState
    attempted_count: int
    evaluable_count: int
    attempt_insufficient_count: int
    attempt_not_run_count: int
    pass_count: int
    fail_count: int
    fail_graph_dependence_count: int
    insufficient_count: int
    not_run_count: int
    rate_eligible_count: int
    rate_evaluable_count: int
    rate_insufficient_count: int
    rate_not_run_count: int
    positive_expected_count: int
    positive_pass_count: int
    negative_expected_count: int
    negative_pass_count: int
    prerequisite_expected_count: int
    prerequisite_pass_count: int
    coverage: float | None
    abstention_fraction: float | None
    recall: float | None
    specificity: float | None
    reason_codes: tuple[str, ...]
    graph_cells_are_repeated_measures: bool = True
    score_denominator: str = "expected_nonprerequisite_primary_units"
    all_expected_primary_units_must_pass: bool = True
    prerequisite_rate_handling: str = "excluded_but_mandatory"

    def __post_init__(self) -> None:
        _slug(self.stratum_id, label="stratum_id")
        if not isinstance(self.evaluation_unit, EvaluationUnit):
            raise TypeError("evaluation_unit must be an EvaluationUnit")
        if type(self.required) is not bool:
            raise TypeError("required must be bool")
        if not isinstance(self.state, QualificationState):
            raise TypeError("state must be a QualificationState")
        _canonical_unique_slugs(
            self.primary_unit_ids,
            label=f"stratum {self.stratum_id} primary_unit_ids",
        )
        _validate_counts(
            attempted_count=self.attempted_count,
            evaluable_count=self.evaluable_count,
            attempt_insufficient_count=self.attempt_insufficient_count,
            attempt_not_run_count=self.attempt_not_run_count,
            pass_count=self.pass_count,
            fail_count=self.fail_count,
            fail_graph_dependence_count=self.fail_graph_dependence_count,
            insufficient_count=self.insufficient_count,
            not_run_count=self.not_run_count,
            state=self.state,
            label=f"strata.{self.stratum_id}",
            allow_policy_adjustment=True,
        )
        if self.attempted_count != len(self.primary_unit_ids):
            raise QualificationContractError(
                "stratum attempted_count must equal expected primary-unit count"
            )
        for name in (
            "rate_eligible_count",
            "rate_evaluable_count",
            "rate_insufficient_count",
            "rate_not_run_count",
            "positive_expected_count",
            "positive_pass_count",
            "negative_expected_count",
            "negative_pass_count",
            "prerequisite_expected_count",
            "prerequisite_pass_count",
        ):
            _plain_int(
                getattr(self, name),
                label=f"stratum {name}",
                minimum=0,
            )
        if self.rate_eligible_count <= 0:
            raise QualificationContractError(
                "stratum score universe must contain an expected nonzero or "
                "null primary"
            )
        if (
            self.rate_eligible_count + self.prerequisite_expected_count
            != self.attempted_count
        ):
            raise QualificationContractError(
                "stratum rate-eligible and prerequisite counts must partition "
                "the all-primary universe"
            )
        if (
            self.rate_evaluable_count
            + self.rate_insufficient_count
            + self.rate_not_run_count
            != self.rate_eligible_count
        ):
            raise QualificationContractError(
                "stratum rate attempt counts must partition the score universe"
            )
        if (
            self.positive_expected_count + self.negative_expected_count
            != self.rate_eligible_count
        ):
            raise QualificationContractError(
                "stratum positive and negative counts must partition the score universe"
            )
        for passed_name, expected_name in (
            ("positive_pass_count", "positive_expected_count"),
            ("negative_pass_count", "negative_expected_count"),
            ("prerequisite_pass_count", "prerequisite_expected_count"),
        ):
            if getattr(self, passed_name) > getattr(self, expected_name):
                raise QualificationContractError(
                    f"stratum {passed_name} exceeds {expected_name}"
                )
        if (
            self.positive_pass_count
            + self.negative_pass_count
            + self.prerequisite_pass_count
            != self.pass_count
        ):
            raise QualificationContractError(
                "stratum class/control pass counts must equal the all-primary "
                "pass count"
            )
        if self.rate_evaluable_count > self.evaluable_count:
            raise QualificationContractError(
                "stratum scored evaluable count exceeds the all-primary count"
            )
        if self.rate_insufficient_count > self.attempt_insufficient_count:
            raise QualificationContractError(
                "stratum scored insufficient count exceeds the all-primary count"
            )
        if self.rate_not_run_count > self.attempt_not_run_count:
            raise QualificationContractError(
                "stratum scored not-run count exceeds the all-primary count"
            )
        expected_coverage = self.rate_evaluable_count / self.rate_eligible_count
        expected_abstention = (
            self.rate_insufficient_count + self.rate_not_run_count
        ) / self.rate_eligible_count
        for name, value, expected in (
            ("coverage", self.coverage, expected_coverage),
            ("abstention_fraction", self.abstention_fraction, expected_abstention),
        ):
            if value is None or not math.isclose(
                _finite_float(
                    value,
                    label=f"stratum {name}",
                    minimum=0.0,
                    maximum=1.0,
                ),
                expected,
                rel_tol=0.0,
                abs_tol=1e-15,
            ):
                raise QualificationContractError(
                    f"stratum {name} differs from its explicit score universe"
                )
        if self.positive_expected_count <= 0 or self.negative_expected_count <= 0:
            raise QualificationContractError(
                "stratum score universe must contain positive and negative "
                "expected primaries"
            )
        expected_recall = self.positive_pass_count / self.positive_expected_count
        expected_specificity = self.negative_pass_count / self.negative_expected_count
        for name, value, expected in (
            ("recall", self.recall, expected_recall),
            ("specificity", self.specificity, expected_specificity),
        ):
            if value is None or not math.isclose(
                _finite_float(
                    value,
                    label=f"stratum {name}",
                    minimum=0.0,
                    maximum=1.0,
                ),
                expected,
                rel_tol=0.0,
                abs_tol=1e-15,
            ):
                raise QualificationContractError(
                    f"stratum {name} differs from its explicit class counts"
                )
        _reasons(
            self.reason_codes,
            state=self.state,
            label=f"strata.{self.stratum_id}.reason_codes",
        )
        _constant(
            self.graph_cells_are_repeated_measures,
            True,
            label="stratum.graph_cells_are_repeated_measures",
        )
        _constant(
            self.score_denominator,
            "expected_nonprerequisite_primary_units",
            label="stratum.score_denominator",
        )
        _constant(
            self.all_expected_primary_units_must_pass,
            True,
            label="stratum.all_expected_primary_units_must_pass",
        )
        _constant(
            self.prerequisite_rate_handling,
            "excluded_but_mandatory",
            label="stratum.prerequisite_rate_handling",
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "stratum_id": self.stratum_id,
            "evaluation_unit": self.evaluation_unit.value,
            "required": self.required,
            "primary_unit_ids": list(self.primary_unit_ids),
            "state": self.state.value,
            "attempted_count": self.attempted_count,
            "evaluable_count": self.evaluable_count,
            "attempt_insufficient_count": self.attempt_insufficient_count,
            "attempt_not_run_count": self.attempt_not_run_count,
            "pass_count": self.pass_count,
            "fail_count": self.fail_count,
            "fail_graph_dependence_count": self.fail_graph_dependence_count,
            "insufficient_count": self.insufficient_count,
            "not_run_count": self.not_run_count,
            "rate_eligible_count": self.rate_eligible_count,
            "rate_evaluable_count": self.rate_evaluable_count,
            "rate_insufficient_count": self.rate_insufficient_count,
            "rate_not_run_count": self.rate_not_run_count,
            "positive_expected_count": self.positive_expected_count,
            "positive_pass_count": self.positive_pass_count,
            "negative_expected_count": self.negative_expected_count,
            "negative_pass_count": self.negative_pass_count,
            "prerequisite_expected_count": self.prerequisite_expected_count,
            "prerequisite_pass_count": self.prerequisite_pass_count,
            "coverage": self.coverage,
            "abstention_fraction": self.abstention_fraction,
            "recall": self.recall,
            "specificity": self.specificity,
            "reason_codes": list(self.reason_codes),
            "graph_cells_are_repeated_measures": (
                self.graph_cells_are_repeated_measures
            ),
            "score_denominator": self.score_denominator,
            "all_expected_primary_units_must_pass": (
                self.all_expected_primary_units_must_pass
            ),
            "prerequisite_rate_handling": self.prerequisite_rate_handling,
        }

    @classmethod
    def from_dict(cls, value: object) -> StratumSummary:
        item = _mapping(value, label="stratum summary")
        expected = {
            "stratum_id",
            "evaluation_unit",
            "required",
            "primary_unit_ids",
            "state",
            "attempted_count",
            "evaluable_count",
            "attempt_insufficient_count",
            "attempt_not_run_count",
            "pass_count",
            "fail_count",
            "fail_graph_dependence_count",
            "insufficient_count",
            "not_run_count",
            "rate_eligible_count",
            "rate_evaluable_count",
            "rate_insufficient_count",
            "rate_not_run_count",
            "positive_expected_count",
            "positive_pass_count",
            "negative_expected_count",
            "negative_pass_count",
            "prerequisite_expected_count",
            "prerequisite_pass_count",
            "coverage",
            "abstention_fraction",
            "recall",
            "specificity",
            "reason_codes",
            "graph_cells_are_repeated_measures",
            "score_denominator",
            "all_expected_primary_units_must_pass",
            "prerequisite_rate_handling",
        }
        _exact_keys(item, expected, label="stratum summary")
        if type(item["required"]) is not bool:
            raise QualificationContractError("stratum required must be bool")

        def optional_rate(name: str) -> float | None:
            raw = item[name]
            if raw is None:
                return None
            return _finite_float(
                raw,
                label=f"stratum {name}",
                minimum=0.0,
                maximum=1.0,
            )

        return cls(
            stratum_id=_slug(item["stratum_id"], label="stratum_id"),
            evaluation_unit=_enum(
                EvaluationUnit,
                item["evaluation_unit"],
                label="stratum evaluation_unit",
            ),  # type: ignore[arg-type]
            required=item["required"],
            primary_unit_ids=tuple(
                _slug(primary_id, label="stratum primary_unit_id")
                for primary_id in _sequence(
                    item["primary_unit_ids"], label="primary_unit_ids"
                )
            ),
            state=_enum(
                QualificationState,
                item["state"],
                label="stratum state",
            ),  # type: ignore[arg-type]
            attempted_count=_plain_int(
                item["attempted_count"], label="stratum attempted_count"
            ),
            evaluable_count=_plain_int(
                item["evaluable_count"], label="stratum evaluable_count"
            ),
            attempt_insufficient_count=_plain_int(
                item["attempt_insufficient_count"],
                label="stratum attempt_insufficient_count",
            ),
            attempt_not_run_count=_plain_int(
                item["attempt_not_run_count"],
                label="stratum attempt_not_run_count",
            ),
            pass_count=_plain_int(item["pass_count"], label="stratum pass_count"),
            fail_count=_plain_int(item["fail_count"], label="stratum fail_count"),
            fail_graph_dependence_count=_plain_int(
                item["fail_graph_dependence_count"],
                label="stratum fail_graph_dependence_count",
            ),
            insufficient_count=_plain_int(
                item["insufficient_count"],
                label="stratum insufficient_count",
            ),
            not_run_count=_plain_int(
                item["not_run_count"], label="stratum not_run_count"
            ),
            rate_eligible_count=_plain_int(
                item["rate_eligible_count"],
                label="stratum rate_eligible_count",
            ),
            rate_evaluable_count=_plain_int(
                item["rate_evaluable_count"],
                label="stratum rate_evaluable_count",
            ),
            rate_insufficient_count=_plain_int(
                item["rate_insufficient_count"],
                label="stratum rate_insufficient_count",
            ),
            rate_not_run_count=_plain_int(
                item["rate_not_run_count"],
                label="stratum rate_not_run_count",
            ),
            positive_expected_count=_plain_int(
                item["positive_expected_count"],
                label="stratum positive_expected_count",
            ),
            positive_pass_count=_plain_int(
                item["positive_pass_count"],
                label="stratum positive_pass_count",
            ),
            negative_expected_count=_plain_int(
                item["negative_expected_count"],
                label="stratum negative_expected_count",
            ),
            negative_pass_count=_plain_int(
                item["negative_pass_count"],
                label="stratum negative_pass_count",
            ),
            prerequisite_expected_count=_plain_int(
                item["prerequisite_expected_count"],
                label="stratum prerequisite_expected_count",
            ),
            prerequisite_pass_count=_plain_int(
                item["prerequisite_pass_count"],
                label="stratum prerequisite_pass_count",
            ),
            coverage=optional_rate("coverage"),
            abstention_fraction=optional_rate("abstention_fraction"),
            recall=optional_rate("recall"),
            specificity=optional_rate("specificity"),
            reason_codes=tuple(
                _slug(reason, label="stratum reason code")
                for reason in _sequence(item["reason_codes"], label="reason_codes")
            ),
            graph_cells_are_repeated_measures=_constant(
                item["graph_cells_are_repeated_measures"],
                True,
                label="graph_cells_are_repeated_measures",
            ),  # type: ignore[arg-type]
            score_denominator=_constant(
                item["score_denominator"],
                "expected_nonprerequisite_primary_units",
                label="score_denominator",
            ),  # type: ignore[arg-type]
            all_expected_primary_units_must_pass=_constant(
                item["all_expected_primary_units_must_pass"],
                True,
                label="all_expected_primary_units_must_pass",
            ),  # type: ignore[arg-type]
            prerequisite_rate_handling=_constant(
                item["prerequisite_rate_handling"],
                "excluded_but_mandatory",
                label="prerequisite_rate_handling",
            ),  # type: ignore[arg-type]
        )


def qualification_strata_projection_sha256(
    primary_unit_id: str,
    strata: tuple[StratumSummary, ...],
) -> str:
    """Hash the exact normalized D5 projection for one repeated-measures unit."""

    _slug(primary_unit_id, label="event primary_unit_id")
    selected = tuple(
        item for item in strata if primary_unit_id in item.primary_unit_ids
    )
    if not selected:
        raise QualificationContractError(
            "every event lane requires at least one normalized stratum projection"
        )
    return canonical_json_sha256(
        {
            "schema_version": ("spirallens.qualification-strata-projection.v0.1"),
            "primary_unit_id": primary_unit_id,
            "strata": [item.to_dict() for item in selected],
        }
    )


def _lane_input_evidence_sha256(
    cell: CoreCellSummary | CrossedCellSummary,
) -> str:
    if isinstance(cell, CoreCellSummary):
        content = {
            "schema_version": "spirallens.core-lane-input-evidence.v0.1",
            "field_graph_fingerprint_sha256": (cell.field_graph_fingerprint_sha256),
            "field_estimate_fingerprint_sha256": (
                cell.field_estimate_fingerprint_sha256
            ),
            "blind_input_fingerprint_sha256": (cell.blind_input_fingerprint_sha256),
        }
    else:
        content = {
            "schema_version": "spirallens.loop-lane-input-evidence.v0.1",
            "field_graph_fingerprint_sha256": (cell.field_graph_fingerprint_sha256),
            "cycle_graph_fingerprint_sha256": (cell.cycle_graph_fingerprint_sha256),
            "field_estimate_fingerprint_sha256": (
                cell.field_estimate_fingerprint_sha256
            ),
            "cycle_binding_fingerprint_sha256": (cell.cycle_binding_fingerprint_sha256),
            "representative_content_sha256": (cell.representative_content_sha256),
            "blind_input_fingerprint_sha256": (cell.blind_input_fingerprint_sha256),
        }
    return canonical_json_sha256(content)


def _lane_prediction_evidence_sha256(
    cell: CoreCellSummary | CrossedCellSummary,
) -> str:
    content: dict[str, object] = {
        "schema_version": "spirallens.lane-prediction-evidence.v0.1",
        "attempt_status": cell.attempt_status.value,
        "prediction_class": cell.prediction_class.value,
        "prediction_fingerprint_sha256": (cell.prediction_fingerprint_sha256),
    }
    if isinstance(cell, CrossedCellSummary):
        content["continuous_signed_total_cycles"] = cell.continuous_signed_total_cycles
    return canonical_json_sha256(content)


def _lane_oracle_evidence_sha256(
    cell: CoreCellSummary | CrossedCellSummary,
) -> str:
    if isinstance(cell, CoreCellSummary):
        content = {
            "schema_version": "spirallens.core-lane-oracle-evidence.v0.1",
            "expected_disposition": cell.expected_disposition.value,
            "oracle_fingerprint_sha256": cell.oracle_fingerprint_sha256,
            "candidate_fingerprint_sha256": (cell.candidate_fingerprint_sha256),
            "oracle_anchor_fingerprint_sha256": (cell.oracle_anchor_fingerprint_sha256),
            "candidate_anchor_symmetric_difference_rows": list(
                cell.candidate_anchor_symmetric_difference_rows
            ),
        }
    else:
        content = {
            "schema_version": "spirallens.loop-lane-oracle-evidence.v0.1",
            "expected_disposition": cell.expected_disposition.value,
            "oracle_fingerprint_sha256": cell.oracle_fingerprint_sha256,
            "oracle_absolute_error_cycles": (cell.oracle_absolute_error_cycles),
        }
    return canonical_json_sha256(content)


def build_qualification_lane_event_payloads(
    *,
    protocol: QualificationProtocol,
    protocol_source_sha256: str,
    source_binding: QualificationSourceBindingSummary,
    selection_freeze_artifact_sha256: str,
    selection_attempt_claim_sha256: str,
    result_id: str,
    result_evidence_root_sha256: str,
    cell: CoreCellSummary | CrossedCellSummary,
    primary: CorePrimaryUnitSummary | PrimaryUnitSummary,
    nonvacuity: CrossedNonvacuitySummary | None,
    strata: tuple[StratumSummary, ...],
) -> tuple[
    ProtocolVerifiedEventPayload,
    BlindInputGeneratedEventPayload,
    PredictionSealedEventPayload,
    OracleMaterializedEventPayload,
    ScoredEventPayload,
    ResultAssembledEventPayload,
]:
    """Build the sole accepted typed event sequence for one normalized lane."""

    if not isinstance(protocol, QualificationProtocol):
        raise TypeError("protocol must be a QualificationProtocol")
    _sha256(protocol_source_sha256, label="event protocol_source_sha256")
    _sha256(
        selection_freeze_artifact_sha256,
        label="event selection_freeze_artifact_sha256",
    )
    _sha256(
        selection_attempt_claim_sha256,
        label="event selection_attempt_claim_sha256",
    )
    _slug(result_id, label="event result_id")
    _sha256(
        result_evidence_root_sha256,
        label="event result_evidence_root_sha256",
    )
    if cell.primary_unit_id != primary.primary_unit_id:
        raise QualificationContractError(
            "event cell and normalized primary identities differ"
        )
    if isinstance(cell, CoreCellSummary):
        if not isinstance(primary, CorePrimaryUnitSummary) or nonvacuity is not None:
            raise QualificationContractError(
                "core event lanes require a core primary and no loop nonvacuity"
            )
        lane_id = f"core.{cell.core_cell_id}"
        expected_by_id = {
            item.core_cell_id: item for item in protocol.expected_core_cells
        }
        try:
            expected = expected_by_id[cell.core_cell_id]
        except KeyError as error:
            raise QualificationContractError(
                "core event lane is absent from the protocol manifest"
            ) from error
    else:
        if not isinstance(primary, PrimaryUnitSummary) or not isinstance(
            nonvacuity, CrossedNonvacuitySummary
        ):
            raise QualificationContractError(
                "loop event lanes require loop primary and nonvacuity summaries"
            )
        if nonvacuity.primary_unit_id != primary.primary_unit_id:
            raise QualificationContractError(
                "loop event nonvacuity identity differs from its primary"
            )
        lane_id = f"loop.{cell.cell_id}"
        expected_by_id = {item.cell_id: item for item in protocol.expected_cells}
        try:
            expected = expected_by_id[cell.cell_id]
        except KeyError as error:
            raise QualificationContractError(
                "loop event lane is absent from the protocol manifest"
            ) from error

    protocol_payload = ProtocolVerifiedEventPayload(
        lane_id=lane_id,
        protocol_id=protocol.protocol_id,
        protocol_source_sha256=protocol_source_sha256,
        protocol_canonical_sha256=protocol.canonical_sha256,
        selection_freeze_artifact_sha256=selection_freeze_artifact_sha256,
        selection_attempt_claim_sha256=selection_attempt_claim_sha256,
        source_binding_receipt_sha256=(source_binding.source_binding_receipt_sha256),
        lane_contract_sha256=canonical_json_sha256(expected.to_dict()),
    )
    blind_payload = BlindInputGeneratedEventPayload(
        lane_id=lane_id,
        protocol_payload_sha256=qualification_event_payload_sha256(protocol_payload),
        attempt_status=cell.attempt_status,
        input_evidence_sha256=_lane_input_evidence_sha256(cell),
        blind_input_fingerprint_sha256=(cell.blind_input_fingerprint_sha256),
    )
    prediction_payload = PredictionSealedEventPayload(
        lane_id=lane_id,
        blind_input_payload_sha256=qualification_event_payload_sha256(blind_payload),
        attempt_status=cell.attempt_status,
        prediction_evidence_sha256=_lane_prediction_evidence_sha256(cell),
        prediction_fingerprint_sha256=cell.prediction_fingerprint_sha256,
        prediction_class=cell.prediction_class.value,
    )
    oracle_payload = OracleMaterializedEventPayload(
        lane_id=lane_id,
        prediction_payload_sha256=qualification_event_payload_sha256(
            prediction_payload
        ),
        attempt_status=cell.attempt_status,
        oracle_evidence_sha256=_lane_oracle_evidence_sha256(cell),
        oracle_fingerprint_sha256=cell.oracle_fingerprint_sha256,
    )
    scored_payload = ScoredEventPayload(
        lane_id=lane_id,
        oracle_payload_sha256=qualification_event_payload_sha256(oracle_payload),
        attempt_status=cell.attempt_status,
        prediction_class=cell.prediction_class.value,
        state=cell.state,
        reason_codes=cell.reason_codes,
        normalized_cell_summary_sha256=canonical_json_sha256(cell.to_dict()),
    )
    result_payload = ResultAssembledEventPayload(
        lane_id=lane_id,
        scored_payload_sha256=qualification_event_payload_sha256(scored_payload),
        result_id=result_id,
        result_evidence_root_sha256=result_evidence_root_sha256,
        selection_freeze_artifact_sha256=selection_freeze_artifact_sha256,
        selection_attempt_claim_sha256=selection_attempt_claim_sha256,
        normalized_primary_summary_sha256=canonical_json_sha256(primary.to_dict()),
        normalized_nonvacuity_summary_sha256=(
            None if nonvacuity is None else canonical_json_sha256(nonvacuity.to_dict())
        ),
        normalized_strata_projection_sha256=(
            qualification_strata_projection_sha256(
                primary.primary_unit_id,
                strata,
            )
        ),
    )
    return (
        protocol_payload,
        blind_payload,
        prediction_payload,
        oracle_payload,
        scored_payload,
        result_payload,
    )


def _exact_dict_tuple(
    observed: tuple[object, ...],
    expected: tuple[object, ...],
    *,
    label: str,
) -> None:
    observed_dicts = tuple(item.to_dict() for item in observed)  # type: ignore[attr-defined]
    expected_dicts = tuple(item.to_dict() for item in expected)  # type: ignore[attr-defined]
    if observed_dicts != expected_dicts:
        raise QualificationContractError(
            f"{label} differs from evidence-derived canonical summaries"
        )


def qualification_result_evidence_root_sha256(
    *,
    result_id: str,
    protocol_id: str,
    protocol_source_sha256: str,
    protocol_canonical_sha256: str,
    selection_freeze_artifact_sha256: str,
    selection_attempt_claim_sha256: str,
    selection_launch_authorization_sha256: str | None = None,
    source_binding: QualificationSourceBindingSummary,
    evidence_bundle: object,
    gate_results: tuple[GateResult, ...],
    gate_evidence: tuple[GateEvidenceSummary, ...],
    static_evidence_receipts: tuple[StaticEvidenceReceipt, ...],
    core_primary_units: tuple[CorePrimaryUnitSummary, ...],
    core_cells: tuple[CoreCellSummary, ...],
    primary_units: tuple[PrimaryUnitSummary, ...],
    crossed_cells: tuple[CrossedCellSummary, ...],
    crossed_nonvacuity: tuple[CrossedNonvacuitySummary, ...],
    strata: tuple[StratumSummary, ...],
) -> str:
    """Hash every pre-ledger result identity without circular self-reference."""

    from .evidence_bundle import QualificationEvidenceBundle

    if not isinstance(evidence_bundle, QualificationEvidenceBundle):
        raise TypeError("evidence_bundle must be a QualificationEvidenceBundle")
    for label, value in (
        ("result_id", result_id),
        ("protocol_id", protocol_id),
    ):
        _slug(value, label=f"evidence root {label}")
    for label, value in (
        ("protocol_source_sha256", protocol_source_sha256),
        ("protocol_canonical_sha256", protocol_canonical_sha256),
        (
            "selection_freeze_artifact_sha256",
            selection_freeze_artifact_sha256,
        ),
        (
            "selection_attempt_claim_sha256",
            selection_attempt_claim_sha256,
        ),
    ):
        _sha256(value, label=f"evidence root {label}")
    authorization_sha256 = _launch_authorization_sha256(
        selection_launch_authorization_sha256,
        protocol_id=protocol_id,
        label="evidence root selection_launch_authorization_sha256",
    )
    return canonical_json_sha256(
        {
            "schema_version": ("spirallens.qualification-result-evidence-root.v0.3"),
            "result_id": result_id,
            "protocol_id": protocol_id,
            "protocol_source_sha256": protocol_source_sha256,
            "protocol_canonical_sha256": protocol_canonical_sha256,
            "selection_freeze_artifact_sha256": (selection_freeze_artifact_sha256),
            "selection_attempt_claim_sha256": (selection_attempt_claim_sha256),
            "selection_launch_authorization_sha256": authorization_sha256,
            "source_binding": source_binding.to_dict(),
            "evidence_bundle": evidence_bundle.to_dict(),
            "gate_results": [item.to_dict() for item in gate_results],
            "gate_evidence": [item.to_dict() for item in gate_evidence],
            "static_evidence_receipts": [
                item.to_dict() for item in static_evidence_receipts
            ],
            "core_primary_units": [item.to_dict() for item in core_primary_units],
            "core_cells": [item.to_dict() for item in core_cells],
            "primary_units": [item.to_dict() for item in primary_units],
            "crossed_cells": [item.to_dict() for item in crossed_cells],
            "crossed_nonvacuity": [item.to_dict() for item in crossed_nonvacuity],
            "strata": [item.to_dict() for item in strata],
            "record_scope": QUALIFICATION_RESULT_RECORD_SCOPE,
            "claim_ceiling": "level_0",
        }
    )


def _parse_qualification_evidence_bundle(value: object) -> object:
    """Parse the evidence companion without an untracked dynamic import."""

    from .evidence_bundle import QualificationEvidenceBundle

    return QualificationEvidenceBundle.from_dict(value)


@dataclass(frozen=True, slots=True)
class QualificationResult:
    """Canonical receipt whose D0--D5 gates are all evidence-derived."""

    result_id: str
    protocol_id: str
    protocol_source_sha256: str
    protocol_canonical_sha256: str
    selection_freeze_artifact_sha256: str
    selection_attempt_claim_sha256: str
    source_binding: QualificationSourceBindingSummary
    evidence_bundle: object
    result_evidence_root_sha256: str
    event_ledger_receipt: QualificationEventLedgerReceipt
    gate_results: tuple[GateResult, ...]
    gate_evidence: tuple[GateEvidenceSummary, ...]
    static_evidence_receipts: tuple[StaticEvidenceReceipt, ...]
    core_primary_units: tuple[CorePrimaryUnitSummary, ...]
    core_cells: tuple[CoreCellSummary, ...]
    primary_units: tuple[PrimaryUnitSummary, ...]
    crossed_cells: tuple[CrossedCellSummary, ...]
    crossed_nonvacuity: tuple[CrossedNonvacuitySummary, ...]
    strata: tuple[StratumSummary, ...]
    selection_launch_authorization_sha256: str | None = None
    schema_version: str = QUALIFICATION_RESULT_SCHEMA_VERSION
    claim_ceiling: str = "level_0"
    record_scope: str = QUALIFICATION_RESULT_RECORD_SCOPE
    pr8_graph_records_persisted: bool = False
    pr8_graph_records_reconstructed: bool = False
    posthoc_logical_dependency_manifest_validated: bool = True
    external_prior_observation_excluded: bool = False
    hidden_confirmation_accessed: bool = False
    d6_d8_advanced: bool = False
    synthetic_qualified: bool = False
    pythia_accessed: bool = False
    subject_accessed: bool = False
    semantic_labels_accessed: bool = False
    integer_claimed: bool = False
    p0_winner_selected: bool = False
    representation_d2_d5_qualified: bool = False
    localized_core_loop_join_established: bool = False

    _ROOT_KEYS: ClassVar[frozenset[str]] = frozenset(
        {
            "schema_version",
            "result_id",
            "protocol_id",
            "protocol_source_sha256",
            "protocol_canonical_sha256",
            "selection_freeze_artifact_sha256",
            "selection_attempt_claim_sha256",
            "selection_launch_authorization_sha256",
            "source_binding",
            "evidence_bundle",
            "result_evidence_root_sha256",
            "event_ledger_receipt",
            "claim_ceiling",
            "record_scope",
            "pr8_graph_records_persisted",
            "pr8_graph_records_reconstructed",
            "gate_results",
            "gate_evidence",
            "static_evidence_receipts",
            "core_primary_units",
            "core_cells",
            "primary_units",
            "crossed_cells",
            "crossed_nonvacuity",
            "strata",
            "posthoc_logical_dependency_manifest_validated",
            "external_prior_observation_excluded",
            "hidden_confirmation_accessed",
            "d6_d8_advanced",
            "synthetic_qualified",
            "pythia_accessed",
            "subject_accessed",
            "semantic_labels_accessed",
            "integer_claimed",
            "p0_winner_selected",
            "representation_d2_d5_qualified",
            "localized_core_loop_join_established",
        }
    )

    def __post_init__(self) -> None:
        _constant(
            self.schema_version,
            QUALIFICATION_RESULT_SCHEMA_VERSION,
            label="result schema_version",
        )
        _slug(self.result_id, label="result_id")
        _slug(self.protocol_id, label="result protocol_id")
        _sha256(self.protocol_source_sha256, label="result protocol_source_sha256")
        _sha256(
            self.protocol_canonical_sha256,
            label="result protocol_canonical_sha256",
        )
        _sha256(
            self.selection_freeze_artifact_sha256,
            label="result selection_freeze_artifact_sha256",
        )
        _sha256(
            self.selection_attempt_claim_sha256,
            label="result selection_attempt_claim_sha256",
        )
        _launch_authorization_sha256(
            self.selection_launch_authorization_sha256,
            protocol_id=self.protocol_id,
            label="result selection_launch_authorization_sha256",
        )
        _sha256(
            self.result_evidence_root_sha256,
            label="result result_evidence_root_sha256",
        )
        if not isinstance(
            self.source_binding,
            QualificationSourceBindingSummary,
        ):
            raise TypeError(
                "source_binding must be a QualificationSourceBindingSummary"
            )
        from .evidence_bundle import QualificationEvidenceBundle

        if not isinstance(self.evidence_bundle, QualificationEvidenceBundle):
            raise TypeError("evidence_bundle must be a QualificationEvidenceBundle")
        if not isinstance(
            self.event_ledger_receipt,
            QualificationEventLedgerReceipt,
        ):
            raise TypeError(
                "event_ledger_receipt must be a QualificationEventLedgerReceipt"
            )
        if (
            self.posthoc_logical_dependency_manifest_validated
            is not self.event_ledger_receipt.posthoc_logical_dependency_manifest_validated
        ):
            raise QualificationContractError(
                "posthoc_logical_dependency_manifest_validated must derive "
                "from the embedded logical dependency manifest"
            )
        expected_evidence_root = qualification_result_evidence_root_sha256(
            result_id=self.result_id,
            protocol_id=self.protocol_id,
            protocol_source_sha256=self.protocol_source_sha256,
            protocol_canonical_sha256=self.protocol_canonical_sha256,
            selection_freeze_artifact_sha256=(self.selection_freeze_artifact_sha256),
            selection_attempt_claim_sha256=(self.selection_attempt_claim_sha256),
            selection_launch_authorization_sha256=(
                self.selection_launch_authorization_sha256
            ),
            source_binding=self.source_binding,
            evidence_bundle=self.evidence_bundle,
            gate_results=self.gate_results,
            gate_evidence=self.gate_evidence,
            static_evidence_receipts=self.static_evidence_receipts,
            core_primary_units=self.core_primary_units,
            core_cells=self.core_cells,
            primary_units=self.primary_units,
            crossed_cells=self.crossed_cells,
            crossed_nonvacuity=self.crossed_nonvacuity,
            strata=self.strata,
        )
        if self.result_evidence_root_sha256 != expected_evidence_root:
            raise QualificationContractError(
                "result evidence root differs from its complete pre-ledger "
                "protocol/source/freeze/evidence/summary content"
            )
        _constant(self.claim_ceiling, "level_0", label="result claim_ceiling")
        _constant(
            self.record_scope,
            QUALIFICATION_RESULT_RECORD_SCOPE,
            label="result record_scope",
        )
        constants = {
            "pr8_graph_records_persisted": False,
            "pr8_graph_records_reconstructed": False,
            "posthoc_logical_dependency_manifest_validated": True,
            "external_prior_observation_excluded": False,
            "hidden_confirmation_accessed": False,
            "d6_d8_advanced": False,
            "synthetic_qualified": False,
            "pythia_accessed": False,
            "subject_accessed": False,
            "semantic_labels_accessed": False,
            "integer_claimed": False,
            "p0_winner_selected": False,
            "representation_d2_d5_qualified": False,
            "localized_core_loop_join_established": False,
        }
        for name, expected in constants.items():
            _constant(getattr(self, name), expected, label=f"result {name}")
        if tuple(gate.gate_id.value for gate in self.gate_results) != _GATE_ORDER:
            raise QualificationContractError(
                "result gate_results must be exactly d0 through d5 in order"
            )
        expected_evidence_pairs = tuple(
            (gate_id, evidence_id)
            for gate_id in (
                QualificationGateId.D0,
                QualificationGateId.D1,
                QualificationGateId.D3,
            )
            for evidence_id in STATIC_REQUIRED_EVIDENCE_IDS[gate_id]
        )
        observed_evidence_pairs = tuple(
            (item.gate_id, item.evidence_id) for item in self.gate_evidence
        )
        if observed_evidence_pairs != expected_evidence_pairs:
            raise QualificationContractError(
                "result gate_evidence must equal the exact D0/D1/D3 manifest"
            )
        expected_static_receipt_pairs = tuple(
            (gate_id, evidence_id)
            for gate_id in (
                QualificationGateId.D1,
                QualificationGateId.D3,
            )
            for evidence_id in STATIC_REQUIRED_EVIDENCE_IDS[gate_id]
        )
        observed_static_receipt_pairs = tuple(
            (item.gate_id, item.evidence_id) for item in self.static_evidence_receipts
        )
        if observed_static_receipt_pairs != expected_static_receipt_pairs:
            raise QualificationContractError(
                "result static evidence receipts must equal the exact D1/D3 "
                "companion manifest"
            )
        summaries_by_pair = {
            (item.gate_id, item.evidence_id): item for item in self.gate_evidence
        }
        for receipt in self.static_evidence_receipts:
            expected_summary = receipt.to_summary()
            actual_summary = summaries_by_pair[(receipt.gate_id, receipt.evidence_id)]
            if actual_summary.to_dict() != expected_summary.to_dict():
                raise QualificationContractError(
                    "D1/D3 normalized gate evidence differs from its typed "
                    "companion receipt"
                )
        gate_by_id = {gate.gate_id: gate for gate in self.gate_results}
        for gate_id in (
            QualificationGateId.D0,
            QualificationGateId.D1,
            QualificationGateId.D3,
        ):
            derived = derive_static_gate(gate_id, self.gate_evidence)
            if gate_by_id[gate_id].to_dict() != derived.to_dict():
                raise QualificationContractError(
                    f"{gate_id.value} gate differs from its typed evidence"
                )
        for values, attribute, label in (
            (self.core_primary_units, "primary_unit_id", "core primary IDs"),
            (self.core_cells, "core_cell_id", "core cell IDs"),
            (self.primary_units, "primary_unit_id", "loop primary IDs"),
            (self.crossed_cells, "cell_id", "loop cell IDs"),
            (
                self.crossed_nonvacuity,
                "primary_unit_id",
                "crossed nonvacuity primary IDs",
            ),
            (self.strata, "stratum_id", "stratum IDs"),
        ):
            identifiers = tuple(getattr(item, attribute) for item in values)
            _canonical_unique_slugs(identifiers, label=f"result {label}")
        expected_event_lanes = tuple(
            sorted(
                (
                    *(f"core.{cell.core_cell_id}" for cell in self.core_cells),
                    *(f"loop.{cell.cell_id}" for cell in self.crossed_cells),
                )
            )
        )
        if self.event_ledger_receipt.expected_lane_ids != expected_event_lanes:
            raise QualificationContractError(
                "event ledger lanes differ from the exact result cell manifest"
            )
        if tuple(unit.primary_unit_id for unit in self.core_primary_units) != tuple(
            unit.primary_unit_id for unit in self.primary_units
        ):
            raise QualificationContractError(
                "core and loop primary manifests must use identical primary IDs"
            )
        self._validate_internal_cell_links()
        from .aggregation import build_d2_gate

        d2_confounder = self.evidence_bundle.d2_confounder_matrix_receipt
        expected_d2 = build_d2_gate(
            self.core_primary_units,
            confounder_state=d2_confounder.state,
            confounder_reason_codes=d2_confounder.reason_codes,
            boundary_axis_id=BOUNDARY_AXIS_ID,
            boundary_levels=tuple(
                sorted(
                    {
                        assignment.level
                        for unit in self.core_primary_units
                        for assignment in unit.stress_assignments
                        if assignment.axis_id == BOUNDARY_AXIS_ID
                    }
                )
            ),
            core_cells=self.core_cells,
        )
        if gate_by_id[QualificationGateId.D2].to_dict() != expected_d2.to_dict():
            raise QualificationContractError(
                "D2 gate differs from core primaries and its false-core "
                "confounder matrix"
            )
        self._validate_primary_gate_projection(
            gate_by_id[QualificationGateId.D4],
            self.primary_units,
            label="D4",
            nonvacuity=self.crossed_nonvacuity,
        )

    @staticmethod
    def _validate_primary_gate_projection(
        gate: GateResult,
        units: tuple[CorePrimaryUnitSummary, ...] | tuple[PrimaryUnitSummary, ...],
        *,
        label: str,
        nonvacuity: tuple[CrossedNonvacuitySummary, ...] = (),
    ) -> None:
        if nonvacuity:
            by_id = {item.primary_unit_id: item for item in nonvacuity}
            if set(by_id) != {unit.primary_unit_id for unit in units}:
                raise QualificationContractError(
                    "D4 nonvacuity evidence must cover every loop primary"
                )
            statuses_list: list[AttemptStatus] = []
            states_list: list[QualificationState] = []
            for unit in units:
                evidence = by_id[unit.primary_unit_id]
                if (
                    unit.attempt_status is AttemptStatus.NOT_RUN
                    and evidence.attempt_status is AttemptStatus.NOT_RUN
                ):
                    statuses_list.append(AttemptStatus.NOT_RUN)
                elif (
                    unit.attempt_status is AttemptStatus.EVALUABLE
                    and evidence.attempt_status is AttemptStatus.EVALUABLE
                ):
                    statuses_list.append(AttemptStatus.EVALUABLE)
                else:
                    statuses_list.append(AttemptStatus.INSUFFICIENT)
                states_list.append(
                    max(
                        (unit.state, evidence.state),
                        key={
                            QualificationState.PASS: 0,
                            QualificationState.NOT_RUN: 1,
                            QualificationState.INSUFFICIENT: 2,
                            QualificationState.FAIL: 3,
                            QualificationState.FAIL_GRAPH_DEPENDENCE: 4,
                        }.__getitem__,
                    )
                )
            statuses = tuple(statuses_list)
            states = tuple(states_list)
        else:
            statuses = tuple(unit.attempt_status for unit in units)
            states = tuple(unit.state for unit in units)
        expected_counts = {
            "attempted_count": len(units),
            "evaluable_count": statuses.count(AttemptStatus.EVALUABLE),
            "attempt_insufficient_count": statuses.count(AttemptStatus.INSUFFICIENT),
            "attempt_not_run_count": statuses.count(AttemptStatus.NOT_RUN),
            "pass_count": states.count(QualificationState.PASS),
            "fail_count": states.count(QualificationState.FAIL),
            "fail_graph_dependence_count": states.count(
                QualificationState.FAIL_GRAPH_DEPENDENCE
            ),
            "insufficient_count": states.count(QualificationState.INSUFFICIENT),
            "not_run_count": states.count(QualificationState.NOT_RUN),
        }
        if any(
            getattr(gate, name) != expected
            for name, expected in expected_counts.items()
        ):
            raise QualificationContractError(
                f"{label} gate counts differ from its primary evidence"
            )
        expected_state = _expected_state_from_verdict_counts(
            attempted_count=expected_counts["attempted_count"],
            fail_graph_dependence_count=expected_counts["fail_graph_dependence_count"],
            fail_count=expected_counts["fail_count"],
            insufficient_count=expected_counts["insufficient_count"],
            not_run_count=expected_counts["not_run_count"],
        )
        if gate.state is not expected_state:
            raise QualificationContractError(
                f"{label} gate state differs from its primary evidence"
            )

    def _validate_internal_cell_links(self) -> None:
        core_inverse: dict[str, set[str]] = {
            unit.primary_unit_id: set() for unit in self.core_primary_units
        }
        for cell in self.core_cells:
            if cell.primary_unit_id not in core_inverse:
                raise QualificationContractError(
                    "core cell references an unknown core primary"
                )
            core_inverse[cell.primary_unit_id].add(cell.core_cell_id)
        for unit in self.core_primary_units:
            if set(unit.core_cell_ids) != core_inverse[unit.primary_unit_id]:
                raise QualificationContractError(
                    "core primary cell IDs differ from result core cells"
                )

        loop_inverse: dict[str, set[str]] = {
            unit.primary_unit_id: set() for unit in self.primary_units
        }
        for cell in self.crossed_cells:
            if cell.primary_unit_id not in loop_inverse:
                raise QualificationContractError(
                    "loop cell references an unknown loop primary"
                )
            loop_inverse[cell.primary_unit_id].add(cell.cell_id)
        for unit in self.primary_units:
            if set(unit.crossed_cell_ids) != loop_inverse[unit.primary_unit_id]:
                raise QualificationContractError(
                    "loop primary cell IDs differ from result loop cells"
                )
        nonvacuity_ids = tuple(item.primary_unit_id for item in self.crossed_nonvacuity)
        if nonvacuity_ids != tuple(sorted(loop_inverse)):
            raise QualificationContractError(
                "crossed nonvacuity evidence must cover the exact primary manifest"
            )
        for item in self.crossed_nonvacuity:
            if item.control_id != next(
                unit.control_id
                for unit in self.primary_units
                if unit.primary_unit_id == item.primary_unit_id
            ):
                raise QualificationContractError(
                    "crossed nonvacuity control differs from its loop primary"
                )
        known_primary_ids = set(loop_inverse)
        for stratum in self.strata:
            if not set(stratum.primary_unit_ids) <= known_primary_ids:
                raise QualificationContractError(
                    "stratum references an unknown loop primary"
                )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "result_id": self.result_id,
            "protocol_id": self.protocol_id,
            "protocol_source_sha256": self.protocol_source_sha256,
            "protocol_canonical_sha256": self.protocol_canonical_sha256,
            "selection_freeze_artifact_sha256": (self.selection_freeze_artifact_sha256),
            "selection_attempt_claim_sha256": (self.selection_attempt_claim_sha256),
            "selection_launch_authorization_sha256": (
                self.selection_launch_authorization_sha256
            ),
            "source_binding": self.source_binding.to_dict(),
            "evidence_bundle": self.evidence_bundle.to_dict(),  # type: ignore[attr-defined]
            "result_evidence_root_sha256": self.result_evidence_root_sha256,
            "event_ledger_receipt": self.event_ledger_receipt.to_dict(),
            "claim_ceiling": self.claim_ceiling,
            "record_scope": self.record_scope,
            "pr8_graph_records_persisted": self.pr8_graph_records_persisted,
            "pr8_graph_records_reconstructed": self.pr8_graph_records_reconstructed,
            "gate_results": [gate.to_dict() for gate in self.gate_results],
            "gate_evidence": [item.to_dict() for item in self.gate_evidence],
            "static_evidence_receipts": [
                item.to_dict() for item in self.static_evidence_receipts
            ],
            "core_primary_units": [unit.to_dict() for unit in self.core_primary_units],
            "core_cells": [cell.to_dict() for cell in self.core_cells],
            "primary_units": [unit.to_dict() for unit in self.primary_units],
            "crossed_cells": [cell.to_dict() for cell in self.crossed_cells],
            "crossed_nonvacuity": [item.to_dict() for item in self.crossed_nonvacuity],
            "strata": [stratum.to_dict() for stratum in self.strata],
            "posthoc_logical_dependency_manifest_validated": (
                self.posthoc_logical_dependency_manifest_validated
            ),
            "external_prior_observation_excluded": (
                self.external_prior_observation_excluded
            ),
            "hidden_confirmation_accessed": self.hidden_confirmation_accessed,
            "d6_d8_advanced": self.d6_d8_advanced,
            "synthetic_qualified": self.synthetic_qualified,
            "pythia_accessed": self.pythia_accessed,
            "subject_accessed": self.subject_accessed,
            "semantic_labels_accessed": self.semantic_labels_accessed,
            "integer_claimed": self.integer_claimed,
            "p0_winner_selected": self.p0_winner_selected,
            "representation_d2_d5_qualified": (self.representation_d2_d5_qualified),
            "localized_core_loop_join_established": (
                self.localized_core_loop_join_established
            ),
        }

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_dict())

    @property
    def canonical_sha256(self) -> str:
        return canonical_json_sha256(self.to_dict())

    def validate_against_protocol(
        self,
        protocol: QualificationProtocol,
        *,
        protocol_source_sha256: str,
        source_binding_receipt: QualificationSourceBindingReceipt | None = None,
        selection_freeze_artifact: object | None = None,
        selection_attempt_claim: object | None = None,
        selection_launch_authorization_sha256: str | None = None,
    ) -> None:
        """Recompute every D0--D5 gate from exact typed evidence."""

        if not isinstance(protocol, QualificationProtocol):
            raise TypeError("protocol must be a QualificationProtocol")
        _sha256(protocol_source_sha256, label="protocol_source_sha256")
        if (
            self.protocol_id != protocol.protocol_id
            or self.protocol_source_sha256 != protocol_source_sha256
            or self.protocol_canonical_sha256 != protocol.canonical_sha256
        ):
            raise QualificationContractError(
                "qualification result does not join the supplied protocol"
            )
        expected_authorization_sha256 = _launch_authorization_sha256(
            selection_launch_authorization_sha256,
            protocol_id=protocol.protocol_id,
            label="expected selection_launch_authorization_sha256",
        )
        if self.selection_launch_authorization_sha256 != expected_authorization_sha256:
            raise QualificationContractError(
                "qualification result launch authorization differs from "
                "the execution companion"
            )
        self.evidence_bundle.d2_confounder_matrix_receipt.validate_protocol(protocol)
        from .freeze import (
            SelectionAttemptClaimArtifact,
            SelectionFreezeArtifact,
            seed_family_commitment_sha256,
        )

        if not isinstance(selection_freeze_artifact, SelectionFreezeArtifact):
            raise QualificationContractError(
                "qualification result validation requires the full pre-run "
                "SelectionFreezeArtifact companion"
            )
        if (
            selection_freeze_artifact.protocol_id != protocol.protocol_id
            or selection_freeze_artifact.protocol_source_sha256
            != protocol_source_sha256
            or selection_freeze_artifact.protocol_canonical_sha256
            != protocol.canonical_sha256
            or selection_freeze_artifact.engine_commit != protocol.engine.commit
            or selection_freeze_artifact.selection_manifest_sha256
            != canonical_json_sha256(protocol.selection.to_dict())
            or selection_freeze_artifact.seed_family_size
            != len(protocol.selection.seeds)
            or selection_freeze_artifact.seed_family_commitment_sha256
            != seed_family_commitment_sha256(
                seed_family_id=selection_freeze_artifact.seed_family_id,
                seeds=protocol.selection.seeds,
            )
        ):
            raise QualificationContractError(
                "selection freeze artifact differs from the exact protocol "
                "source, engine, selection manifest, or seed commitment"
            )
        if (
            self.selection_freeze_artifact_sha256
            != selection_freeze_artifact.canonical_sha256
        ):
            raise QualificationContractError(
                "result selection-freeze digest differs from its full companion"
            )
        if not isinstance(selection_attempt_claim, SelectionAttemptClaimArtifact):
            raise QualificationContractError(
                "qualification result validation requires the full persisted "
                "SelectionAttemptClaimArtifact companion"
            )
        selection_attempt_claim.validate_freeze(selection_freeze_artifact)
        from .preparation import CLOSED_D0_D5_PROTOCOL_ID

        if (
            protocol.protocol_id == CLOSED_D0_D5_PROTOCOL_ID
            and selection_attempt_claim.launch_intent is None
        ):
            raise QualificationContractError(
                "official qualification result requires an intent-bound attempt claim"
            )
        if (
            self.selection_attempt_claim_sha256
            != selection_attempt_claim.canonical_sha256
        ):
            raise QualificationContractError(
                "result selection-attempt-claim digest differs from its full companion"
            )
        if (
            self.source_binding.engine_commit != protocol.engine.commit
            or self.source_binding.module_count != len(protocol.engine.modules)
            or self.source_binding.registry_source_sha256
            != protocol.registry.registry_source_sha256
            or self.source_binding.registry_canonical_sha256
            != protocol.registry.registry_canonical_sha256
            or self.source_binding.referent_canonical_sha256
            != protocol.registry.referent_canonical_sha256
        ):
            raise QualificationContractError(
                "result source binding differs from the protocol declarations"
            )
        if source_binding_receipt is not None:
            self.source_binding.verify_receipt(source_binding_receipt)
        self.evidence_bundle.validate_summaries(  # type: ignore[attr-defined]
            protocol_canonical_sha256=protocol.canonical_sha256,
            source_binding_receipt_sha256=(
                self.source_binding.source_binding_receipt_sha256
            ),
            selection_freeze_artifact_sha256=(self.selection_freeze_artifact_sha256),
            selection_attempt_claim_sha256=(self.selection_attempt_claim_sha256),
            core_cells=self.core_cells,
            loop_cells=self.crossed_cells,
            nonvacuity=self.crossed_nonvacuity,
        )
        self.evidence_bundle.validate_static_receipts(  # type: ignore[attr-defined]
            self.static_evidence_receipts
        )
        attempted_static_receipts = tuple(
            item
            for item in self.static_evidence_receipts
            if item.attempt_status is not AttemptStatus.NOT_RUN
        )
        if attempted_static_receipts and source_binding_receipt is None:
            raise QualificationContractError(
                "attempted D1/D3 evidence requires the full live-verified "
                "source-binding receipt"
            )
        declared_modules = {
            item.module: item.sha256 for item in protocol.engine.modules
        }
        live_modules = (
            {}
            if source_binding_receipt is None
            else {
                item.module: item.declared_sha256
                for item in source_binding_receipt.modules
            }
        )
        for receipt in attempted_static_receipts:
            for module in receipt.producer_modules:
                if (
                    declared_modules.get(module.module) != module.sha256
                    or live_modules.get(module.module) != module.sha256
                ):
                    raise QualificationContractError(
                        "D1/D3 producer module differs from the frozen "
                        "protocol and live source-binding receipt"
                    )
        attempted_d1_receipts = tuple(
            item
            for item in attempted_static_receipts
            if item.gate_id is QualificationGateId.D1
        )
        if attempted_d1_receipts:
            from .runner import recompute_fixed_development_d1

            self.evidence_bundle.validate_d1_receipts_against_protocol(  # type: ignore[attr-defined]
                protocol,
                recomputed_receipts=recompute_fixed_development_d1(protocol),
            )
        if self.event_ledger_receipt.expected_lane_ids != qualification_event_lane_ids(
            protocol
        ):
            raise QualificationContractError(
                "result event ledger differs from the protocol lane manifest"
            )
        event_payloads_by_lane: dict[str, tuple[object, ...]] = {}
        for lane_id in self.event_ledger_receipt.expected_lane_ids:
            event_payloads_by_lane[lane_id] = tuple(
                entry.payload
                for entry in self.event_ledger_receipt.entries
                if entry.lane_id == lane_id
            )
        core_primaries_by_id = {
            item.primary_unit_id: item for item in self.core_primary_units
        }
        loop_primaries_by_id = {
            item.primary_unit_id: item for item in self.primary_units
        }
        nonvacuity_by_id = {
            item.primary_unit_id: item for item in self.crossed_nonvacuity
        }
        for cell in self.core_cells:
            expected_payloads = build_qualification_lane_event_payloads(
                protocol=protocol,
                protocol_source_sha256=protocol_source_sha256,
                source_binding=self.source_binding,
                selection_freeze_artifact_sha256=(
                    self.selection_freeze_artifact_sha256
                ),
                selection_attempt_claim_sha256=(self.selection_attempt_claim_sha256),
                result_id=self.result_id,
                result_evidence_root_sha256=(self.result_evidence_root_sha256),
                cell=cell,
                primary=core_primaries_by_id[cell.primary_unit_id],
                nonvacuity=None,
                strata=self.strata,
            )
            observed_payloads = event_payloads_by_lane[f"core.{cell.core_cell_id}"]
            if tuple(item.to_dict() for item in observed_payloads) != tuple(
                item.to_dict() for item in expected_payloads
            ):
                raise QualificationContractError(
                    f"core lane {cell.core_cell_id!r} event payloads differ "
                    "from exact protocol/source/evidence/result identities"
                )
        for cell in self.crossed_cells:
            expected_payloads = build_qualification_lane_event_payloads(
                protocol=protocol,
                protocol_source_sha256=protocol_source_sha256,
                source_binding=self.source_binding,
                selection_freeze_artifact_sha256=(
                    self.selection_freeze_artifact_sha256
                ),
                selection_attempt_claim_sha256=(self.selection_attempt_claim_sha256),
                result_id=self.result_id,
                result_evidence_root_sha256=(self.result_evidence_root_sha256),
                cell=cell,
                primary=loop_primaries_by_id[cell.primary_unit_id],
                nonvacuity=nonvacuity_by_id[cell.primary_unit_id],
                strata=self.strata,
            )
            observed_payloads = event_payloads_by_lane[f"loop.{cell.cell_id}"]
            if tuple(item.to_dict() for item in observed_payloads) != tuple(
                item.to_dict() for item in expected_payloads
            ):
                raise QualificationContractError(
                    f"loop lane {cell.cell_id!r} event payloads differ from "
                    "exact protocol/source/evidence/result identities"
                )
        evidence_by_pair = {
            (item.gate_id, item.evidence_id): item for item in self.gate_evidence
        }
        source_evidence = evidence_by_pair[
            (
                QualificationGateId.D0,
                "engine-module-digests-verified",
            )
        ]
        protocol_evidence = evidence_by_pair[
            (
                QualificationGateId.D0,
                "protocol-manifest-verified",
            )
        ]
        if (
            source_evidence.attempt_status is AttemptStatus.EVALUABLE
            and source_binding_receipt is None
        ):
            raise QualificationContractError(
                "evaluable D0 source evidence requires its full live-verified "
                "source-binding receipt"
            )
        if (
            source_evidence.attempt_status is AttemptStatus.EVALUABLE
            and source_evidence.evidence_fingerprint_sha256
            != self.source_binding.source_binding_receipt_sha256
        ) or (
            protocol_evidence.attempt_status is AttemptStatus.EVALUABLE
            and protocol_evidence.evidence_fingerprint_sha256
            != protocol.canonical_sha256
        ):
            raise QualificationContractError(
                "D0 evidence fingerprints differ from the source and protocol bindings"
            )

        # Import at validation time to keep aggregation dependent on the record
        # types without creating a module-import cycle.
        from .aggregation import (
            build_d2_gate,
            build_d4_gate,
            build_d5_gate,
            collapse_core_primary_units,
            collapse_primary_units,
            materialize_expected_cells,
            materialize_expected_core_cells,
            summarize_strata,
        )

        materialized_core = materialize_expected_core_cells(
            protocol.expected_core_cells,
            self.core_cells,
        )
        materialized_loop = materialize_expected_cells(
            protocol.expected_cells,
            self.crossed_cells,
        )
        _exact_dict_tuple(
            self.core_cells,
            materialized_core,
            label="core cell manifest",
        )
        _exact_dict_tuple(
            self.crossed_cells,
            materialized_loop,
            label="loop cell manifest",
        )
        for cell in materialized_loop:
            if (
                cell.attempt_status is AttemptStatus.EVALUABLE
                and cell.expected_disposition
                in {LoopDisposition.NONZERO, LoopDisposition.NULL}
            ):
                if cell.continuous_signed_total_cycles is None:
                    raise QualificationContractError(
                        f"loop cell {cell.cell_id!r} lacks its continuous total"
                    )
                derived_class = (
                    LoopPredictionClass.NONZERO
                    if abs(cell.continuous_signed_total_cycles)
                    >= protocol.thresholds.loop_nonzero_floor_cycles
                    else LoopPredictionClass.NULL
                )
                if cell.prediction_class is not derived_class:
                    raise QualificationContractError(
                        f"loop cell {cell.cell_id!r} class differs from its "
                        "continuous total and frozen nonzero floor"
                    )
                expected_class = (
                    LoopPredictionClass.NONZERO
                    if cell.expected_disposition is LoopDisposition.NONZERO
                    else LoopPredictionClass.NULL
                )
                should_pass = (
                    cell.prediction_class is expected_class
                    and cell.oracle_absolute_error_cycles is not None
                    and cell.oracle_absolute_error_cycles
                    <= protocol.thresholds.loop_oracle_tolerance_cycles
                )
                expected_state = (
                    QualificationState.PASS if should_pass else QualificationState.FAIL
                )
                if cell.state is not expected_state:
                    raise QualificationContractError(
                        f"loop cell {cell.cell_id!r} state differs from the "
                        "frozen oracle tolerance"
                    )

        derived_core = collapse_core_primary_units(
            protocol.expected_core_cells,
            materialized_core,
            self.core_primary_units,
            candidate_difference_tolerance_rows=(
                protocol.thresholds.core_candidate_difference_tolerance_rows
            ),
        )
        derived_loop = collapse_primary_units(
            protocol.expected_cells,
            materialized_loop,
            self.primary_units,
            graph_total_tolerance_cycles=(
                protocol.thresholds.graph_total_tolerance_cycles
            ),
        )
        controls = {
            control.control_id: control for control in protocol.selection.controls
        }
        expected_primary_control = {
            cell.primary_unit_id: cell.control_id for cell in protocol.expected_cells
        }
        nonvacuity_by_primary = {
            item.primary_unit_id: item for item in self.crossed_nonvacuity
        }
        if set(nonvacuity_by_primary) != set(expected_primary_control):
            raise QualificationContractError(
                "crossed nonvacuity evidence differs from the expected primary manifest"
            )
        for primary_id, control_id in expected_primary_control.items():
            item = nonvacuity_by_primary[primary_id]
            control = controls[control_id]
            if (
                item.control_id != control_id
                or item.substantive_output_variation_required
                is not control.field_sensitivity_sentinel
                or item.minimum_representative_content_variants
                != protocol.thresholds.minimum_representative_content_variants
                or item.minimum_substantive_output_distance
                != protocol.thresholds.minimum_field_output_effect_size
            ):
                raise QualificationContractError(
                    f"crossed nonvacuity evidence for {primary_id!r} differs "
                    "from the sentinel and threshold protocol"
                )
        derived_strata = summarize_strata(
            protocol.expected_strata,
            derived_loop,
            protocol.coverage_policy,
        )
        _exact_dict_tuple(
            self.core_primary_units,
            derived_core,
            label="core primary summaries",
        )
        _exact_dict_tuple(
            self.primary_units,
            derived_loop,
            label="loop primary summaries",
        )
        _exact_dict_tuple(
            self.strata,
            derived_strata,
            label="stratum summaries",
        )

        derived_gates = (
            derive_static_gate(QualificationGateId.D0, self.gate_evidence),
            derive_static_gate(QualificationGateId.D1, self.gate_evidence),
            build_d2_gate(
                derived_core,
                confounder_state=(
                    self.evidence_bundle.d2_confounder_matrix_receipt.state
                ),
                confounder_reason_codes=(
                    self.evidence_bundle.d2_confounder_matrix_receipt.reason_codes
                ),
                boundary_axis_id=protocol.cartesian.boundary_axis_id,
                boundary_levels=tuple(
                    item.level for item in protocol.cartesian.primary_boundaries
                ),
                core_cells=materialized_core,
            ),
            derive_static_gate(QualificationGateId.D3, self.gate_evidence),
            build_d4_gate(
                derived_loop,
                self.crossed_nonvacuity,
                evaluation_unit=protocol.coverage_policy.evaluation_unit,
            ),
            build_d5_gate(
                derived_loop,
                derived_strata,
                protocol.coverage_policy,
                expected_strata=protocol.expected_strata,
            ),
        )
        _exact_dict_tuple(
            self.gate_results,
            derived_gates,
            label="D0--D5 gate results",
        )

    @classmethod
    def from_dict(cls, value: object) -> QualificationResult:
        document = _mapping(value, label="qualification result")
        _exact_keys(document, cls._ROOT_KEYS, label="qualification result")
        constants = {
            "schema_version": QUALIFICATION_RESULT_SCHEMA_VERSION,
            "claim_ceiling": "level_0",
            "record_scope": QUALIFICATION_RESULT_RECORD_SCOPE,
            "pr8_graph_records_persisted": False,
            "pr8_graph_records_reconstructed": False,
            "posthoc_logical_dependency_manifest_validated": True,
            "external_prior_observation_excluded": False,
            "hidden_confirmation_accessed": False,
            "d6_d8_advanced": False,
            "synthetic_qualified": False,
            "pythia_accessed": False,
            "subject_accessed": False,
            "semantic_labels_accessed": False,
            "integer_claimed": False,
            "p0_winner_selected": False,
            "representation_d2_d5_qualified": False,
            "localized_core_loop_join_established": False,
        }
        for name, expected in constants.items():
            _constant(document[name], expected, label=f"result {name}")
        return cls(
            result_id=_slug(document["result_id"], label="result_id"),
            protocol_id=_slug(document["protocol_id"], label="result protocol_id"),
            protocol_source_sha256=_sha256(
                document["protocol_source_sha256"],
                label="result protocol_source_sha256",
            ),
            protocol_canonical_sha256=_sha256(
                document["protocol_canonical_sha256"],
                label="result protocol_canonical_sha256",
            ),
            selection_freeze_artifact_sha256=_sha256(
                document["selection_freeze_artifact_sha256"],
                label="result selection_freeze_artifact_sha256",
            ),
            selection_attempt_claim_sha256=_sha256(
                document["selection_attempt_claim_sha256"],
                label="result selection_attempt_claim_sha256",
            ),
            selection_launch_authorization_sha256=_launch_authorization_sha256(
                document["selection_launch_authorization_sha256"],
                protocol_id=_slug(
                    document["protocol_id"],
                    label="result protocol_id",
                ),
                label="result selection_launch_authorization_sha256",
            ),
            source_binding=QualificationSourceBindingSummary.from_dict(
                document["source_binding"]
            ),
            evidence_bundle=_parse_qualification_evidence_bundle(
                document["evidence_bundle"]
            ),
            result_evidence_root_sha256=_sha256(
                document["result_evidence_root_sha256"],
                label="result result_evidence_root_sha256",
            ),
            event_ledger_receipt=QualificationEventLedgerReceipt.from_dict(
                document["event_ledger_receipt"]
            ),
            gate_results=tuple(
                GateResult.from_dict(item)
                for item in _sequence(document["gate_results"], label="gate_results")
            ),
            gate_evidence=tuple(
                GateEvidenceSummary.from_dict(item)
                for item in _sequence(document["gate_evidence"], label="gate_evidence")
            ),
            static_evidence_receipts=tuple(
                StaticEvidenceReceipt.from_dict(item)
                for item in _sequence(
                    document["static_evidence_receipts"],
                    label="static_evidence_receipts",
                )
            ),
            core_primary_units=tuple(
                CorePrimaryUnitSummary.from_dict(item)
                for item in _sequence(
                    document["core_primary_units"],
                    label="core_primary_units",
                )
            ),
            core_cells=tuple(
                CoreCellSummary.from_dict(item)
                for item in _sequence(document["core_cells"], label="core_cells")
            ),
            primary_units=tuple(
                PrimaryUnitSummary.from_dict(item)
                for item in _sequence(document["primary_units"], label="primary_units")
            ),
            crossed_cells=tuple(
                CrossedCellSummary.from_dict(item)
                for item in _sequence(document["crossed_cells"], label="crossed_cells")
            ),
            crossed_nonvacuity=tuple(
                CrossedNonvacuitySummary.from_dict(item)
                for item in _sequence(
                    document["crossed_nonvacuity"],
                    label="crossed_nonvacuity",
                )
            ),
            strata=tuple(
                StratumSummary.from_dict(item)
                for item in _sequence(document["strata"], label="strata")
            ),
        )


def qualification_protocol_schema_version() -> str:
    """Expose the exact protocol version joined by this result schema."""

    return QUALIFICATION_PROTOCOL_SCHEMA_VERSION
