"""Deep-internal post-start orchestration for one future D7 confirmation.

This module begins strictly after a future fused verifier/start issuer has
transferred a private ownership object.  That issuer is intentionally absent
here.  The runner accepts neither a supplier, a seed, nor an execution-start
record as an independent argument: the only scientific boundary is one
zero-argument callback.

The callback may keep the exact scientific executor and aggregator separately
auditable.  Its returned six-component bundle is checked by the existing
complete-bundle validator before a typed, in-memory terminal handoff is
prepared.  An ordinary Python exception is re-raised unchanged after a
conservative in-process failed-attempt handoff is attached to it when that
exception object permits diagnostic mutation.  Attachment is best effort and
never replaces the original exception.

This slice does not load or persist evidence, issue ownership, authenticate a
caller, authorize execution, publish or consume a terminal, infer a hard-crash
abort, establish a scientific claim, or set D7/D8 state.  In particular,
``BaseException`` outcomes such as process-exit and interrupt signals are not
converted into abort evidence.
"""

from __future__ import annotations

import re
import traceback
from collections.abc import Callable
from dataclasses import dataclass
from typing import Final, NoReturn

from spirallens.core.canonical import sha256_bytes

from . import confirmation_attempt_evidence as e
from . import confirmation_attempt_evidence_validation as ev
from . import confirmation_attempt_records as r
from . import confirmation_attempt_validation as av
from . import confirmation_result_component_validation as cv
from . import confirmation_result_components as c
from .common import QualificationContractError

__all__: tuple[str, ...] = ()

D7_PREPARED_FAILED_TERMINAL_ATTRIBUTE: Final[str] = (
    "_spirallens_d7_prepared_failed_terminal"
)

_POST_START_OWNERSHIP_FACTORY_TOKEN: Final[object] = object()
_PREPARED_TERMINAL_FACTORY_TOKEN: Final[object] = object()
_QUALIFIED_EXCEPTION_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_.]{0,255}$")


class _NonSerializable:
    """Reject object serialization for private, identity-bearing handoffs."""

    __slots__ = ()

    def __setattr__(self, name: str, value: object) -> None:
        if getattr(self, "_sealed", False):
            raise AttributeError(f"{type(self).__name__} is immutable")
        object.__setattr__(self, name, value)

    def __delattr__(self, name: str) -> None:
        if getattr(self, "_sealed", False):
            raise AttributeError(f"{type(self).__name__} is immutable")
        object.__delattr__(self, name)

    def __reduce__(self) -> NoReturn:
        raise TypeError(f"{type(self).__name__} is an in-process handoff")

    def __reduce_ex__(self, protocol: int) -> NoReturn:
        del protocol
        raise TypeError(f"{type(self).__name__} is an in-process handoff")

    def __getstate__(self) -> NoReturn:
        raise TypeError(f"{type(self).__name__} is an in-process handoff")


class _D7PostStartOwnership(_NonSerializable):
    """Private proof-carrying handoff expected from a future fused issuer.

    Possession of this object is not itself a public authority claim.  The
    constructor token exists only to make accidental direct construction fail;
    this module deliberately provides no issuer function.
    """

    __slots__ = (
        "_aggregation_sha256",
        "_authorization",
        "_claim",
        "_declaration",
        "_full_inventory_sha256",
        "_result_schema_sha256",
        "_sealed",
        "_start",
    )

    def __init__(
        self,
        declaration: r.D7AttemptDeclarationRecord,
        authorization: r.D7LaunchAuthorizationRecord,
        claim: r.D7AttemptClaimRecord,
        start: r.D7ExecutionStartRecord,
        *,
        full_inventory_sha256: str,
        aggregation_sha256: str,
        result_schema_sha256: str,
        _factory_token: object,
    ) -> None:
        if _factory_token is not _POST_START_OWNERSHIP_FACTORY_TOKEN:
            raise TypeError("D7 post-start ownership requires its private issuer")
        if type(declaration) is not r.D7AttemptDeclarationRecord:
            raise TypeError("declaration must be an exact D7AttemptDeclarationRecord")
        if type(authorization) is not r.D7LaunchAuthorizationRecord:
            raise TypeError(
                "authorization must be an exact D7LaunchAuthorizationRecord"
            )
        if type(claim) is not r.D7AttemptClaimRecord:
            raise TypeError("claim must be an exact D7AttemptClaimRecord")
        if type(start) is not r.D7ExecutionStartRecord:
            raise TypeError("start must be an exact D7ExecutionStartRecord")
        av.validate_d7_attempt_prefix(
            declaration=declaration,
            authorization=authorization,
            claim=claim,
            start=start,
        )
        if declaration.attempt_role is not r.D7AttemptRole.PRIMARY_CONFIRMATION:
            raise QualificationContractError(
                "post-start runner currently requires a primary confirmation attempt"
            )
        for name, value in (
            ("full_inventory_sha256", full_inventory_sha256),
            ("aggregation_sha256", aggregation_sha256),
            ("result_schema_sha256", result_schema_sha256),
        ):
            if type(value) is not str or re.fullmatch(r"[0-9a-f]{64}", value) is None:
                raise QualificationContractError(
                    f"post-start ownership {name} must be a lowercase SHA-256"
                )
        if result_schema_sha256 != r.D7_SCIENTIFIC_RESULT_IMPLEMENTATION_SCHEMA_SHA256:
            raise QualificationContractError(
                "post-start ownership requires the current result implementation schema"
            )
        self._declaration = declaration
        self._authorization = authorization
        self._claim = claim
        self._start = start
        self._full_inventory_sha256 = full_inventory_sha256
        self._aggregation_sha256 = aggregation_sha256
        self._result_schema_sha256 = result_schema_sha256
        self._sealed = True

    @property
    def declaration(self) -> r.D7AttemptDeclarationRecord:
        return self._declaration

    @property
    def authorization(self) -> r.D7LaunchAuthorizationRecord:
        return self._authorization

    @property
    def claim(self) -> r.D7AttemptClaimRecord:
        return self._claim

    @property
    def start(self) -> r.D7ExecutionStartRecord:
        return self._start

    @property
    def full_inventory_sha256(self) -> str:
        return self._full_inventory_sha256

    @property
    def aggregation_sha256(self) -> str:
        return self._aggregation_sha256

    @property
    def result_schema_sha256(self) -> str:
        return self._result_schema_sha256


@dataclass(frozen=True, slots=True)
class D7ScientificProducerOutput:
    """Typed callback output; validation and authority remain separate."""

    event_ledger: c.D7ExecutionEventLedgerPayload
    core_cells: c.D7CoreCellOutcomesPayload
    loop_cells: c.D7LoopCellOutcomesPayload
    primary_units: c.D7PrimaryUnitOutcomesPayload
    required_strata: c.D7RequiredStratumOutcomesPayload
    aggregate_gates: c.D7AggregateGateOutcomesPayload
    result_payload: r.D7ScientificResultPayload

    def __post_init__(self) -> None:
        expected = (
            c.D7ExecutionEventLedgerPayload,
            c.D7CoreCellOutcomesPayload,
            c.D7LoopCellOutcomesPayload,
            c.D7PrimaryUnitOutcomesPayload,
            c.D7RequiredStratumOutcomesPayload,
            c.D7AggregateGateOutcomesPayload,
            r.D7ScientificResultPayload,
        )
        if tuple(type(value) for value in self.ordered_values) != expected:
            raise TypeError("scientific producer output has the wrong exact types")

    @property
    def ordered_values(
        self,
    ) -> tuple[
        c.D7ExecutionEventLedgerPayload,
        c.D7CoreCellOutcomesPayload,
        c.D7LoopCellOutcomesPayload,
        c.D7PrimaryUnitOutcomesPayload,
        c.D7RequiredStratumOutcomesPayload,
        c.D7AggregateGateOutcomesPayload,
        r.D7ScientificResultPayload,
    ]:
        return (
            self.event_ledger,
            self.core_cells,
            self.loop_cells,
            self.primary_units,
            self.required_strata,
            self.aggregate_gates,
            self.result_payload,
        )


class D7PreparedScientificTerminal(_NonSerializable):
    """Validated scientific bytes prepared for, but not published by, a terminal."""

    __slots__ = ("_ownership", "_producer_output", "_scientific_result", "_sealed")

    def __init__(
        self,
        ownership: _D7PostStartOwnership,
        producer_output: D7ScientificProducerOutput,
        scientific_result: r.D7ScientificResultRecord,
        *,
        _factory_token: object,
    ) -> None:
        if _factory_token is not _PREPARED_TERMINAL_FACTORY_TOKEN:
            raise TypeError("prepared D7 terminal requires the private runner")
        if type(ownership) is not _D7PostStartOwnership:
            raise TypeError("ownership must be an exact private D7 handoff")
        if type(producer_output) is not D7ScientificProducerOutput:
            raise TypeError("producer_output has the wrong D7 type")
        if type(scientific_result) is not r.D7ScientificResultRecord:
            raise TypeError("scientific_result has the wrong D7 record type")
        _validate_prepared_scientific_result(
            ownership=ownership,
            producer_output=producer_output,
            scientific_result=scientific_result,
        )
        self._ownership = ownership
        self._producer_output = producer_output
        self._scientific_result = scientific_result
        self._sealed = True

    @property
    def ownership(self) -> _D7PostStartOwnership:
        return self._ownership

    @property
    def producer_output(self) -> D7ScientificProducerOutput:
        return self._producer_output

    @property
    def scientific_result(self) -> r.D7ScientificResultRecord:
        return self._scientific_result


class D7PreparedFailedTerminal(_NonSerializable):
    """Conservative in-process failure bytes prepared for a terminal layer."""

    __slots__ = (
        "_failed_attempt",
        "_failure_evidence",
        "_failure_payload",
        "_ownership",
        "_sealed",
    )

    def __init__(
        self,
        ownership: _D7PostStartOwnership,
        failure_payload: e.D7FailureEvidencePayload,
        failure_evidence: r.D7FailureEvidenceRecord,
        failed_attempt: r.D7FailedAttemptRecord,
        *,
        _factory_token: object,
    ) -> None:
        if _factory_token is not _PREPARED_TERMINAL_FACTORY_TOKEN:
            raise TypeError("prepared D7 terminal requires the private runner")
        if type(ownership) is not _D7PostStartOwnership:
            raise TypeError("ownership must be an exact private D7 handoff")
        ev.validate_d7_failure_evidence_payload_chain(
            start=ownership.start,
            payload=failure_payload,
            evidence=failure_evidence,
            failed_attempt=failed_attempt,
        )
        self._ownership = ownership
        self._failure_payload = failure_payload
        self._failure_evidence = failure_evidence
        self._failed_attempt = failed_attempt
        self._sealed = True

    @property
    def ownership(self) -> _D7PostStartOwnership:
        return self._ownership

    @property
    def failure_payload(self) -> e.D7FailureEvidencePayload:
        return self._failure_payload

    @property
    def failure_evidence(self) -> r.D7FailureEvidenceRecord:
        return self._failure_evidence

    @property
    def failed_attempt(self) -> r.D7FailedAttemptRecord:
        return self._failed_attempt


def _validate_scientific_output(
    *,
    ownership: _D7PostStartOwnership,
    producer_output: D7ScientificProducerOutput,
) -> None:
    if type(producer_output) is not D7ScientificProducerOutput:
        raise TypeError(
            "scientific_producer must return an exact D7ScientificProducerOutput"
        )
    cv.validate_d7_result_component_bundle(
        event_ledger=producer_output.event_ledger,
        core_cells=producer_output.core_cells,
        loop_cells=producer_output.loop_cells,
        primary_units=producer_output.primary_units,
        required_strata=producer_output.required_strata,
        aggregate_gates=producer_output.aggregate_gates,
        result_payload=producer_output.result_payload,
    )
    expected_projection = (
        ("replay target", ownership.start.replay_target_sha256),
        ("full inventory", ownership.full_inventory_sha256),
        ("aggregation", ownership.aggregation_sha256),
        ("result schema", ownership.result_schema_sha256),
    )
    payload = producer_output.result_payload
    observed_projection = (
        payload.replay_target_sha256,
        payload.full_inventory_sha256,
        payload.aggregation_sha256,
        payload.result_schema_sha256,
    )
    for (label, expected), observed in zip(
        expected_projection,
        observed_projection,
        strict=True,
    ):
        if observed != expected:
            raise QualificationContractError(
                f"scientific result {label} differs from post-start ownership"
            )
    if payload.result_schema_sha256 != (
        r.D7_SCIENTIFIC_RESULT_IMPLEMENTATION_SCHEMA_SHA256
    ):
        raise QualificationContractError(
            "scientific result does not use the current implementation schema"
        )


def _validate_prepared_scientific_result(
    *,
    ownership: _D7PostStartOwnership,
    producer_output: D7ScientificProducerOutput,
    scientific_result: r.D7ScientificResultRecord,
) -> None:
    start = ownership.start
    expected = (
        ("replay_target_sha256", start.replay_target_sha256),
        ("attempt_key_sha256", start.attempt_key_sha256),
        ("execution_start_sha256", start.canonical_sha256),
        (
            "execution_identity_receipt_sha256",
            start.execution_identity_receipt_sha256,
        ),
        (
            "result_payload_sha256",
            producer_output.result_payload.canonical_sha256,
        ),
        (
            "result_payload_byte_count",
            len(producer_output.result_payload.canonical_bytes),
        ),
    )
    for field, expected_value in expected:
        observed = getattr(scientific_result, field)
        if type(observed) is not type(expected_value) or observed != expected_value:
            raise QualificationContractError(
                f"prepared scientific result {field} differs"
            )


def _prepare_scientific_terminal(
    *,
    ownership: _D7PostStartOwnership,
    producer_output: D7ScientificProducerOutput,
) -> D7PreparedScientificTerminal:
    start = ownership.start
    result_payload = producer_output.result_payload
    scientific_result = r.D7ScientificResultRecord(
        replay_target_sha256=start.replay_target_sha256,
        attempt_key_sha256=start.attempt_key_sha256,
        execution_start_sha256=start.canonical_sha256,
        execution_identity_receipt_sha256=(start.execution_identity_receipt_sha256),
        result_payload_sha256=result_payload.canonical_sha256,
        result_payload_byte_count=len(result_payload.canonical_bytes),
    )
    return D7PreparedScientificTerminal(
        ownership,
        producer_output,
        scientific_result,
        _factory_token=_PREPARED_TERMINAL_FACTORY_TOKEN,
    )


def _safe_utf8(value: str) -> bytes:
    return value.encode("utf-8", errors="backslashreplace")


def _exception_message_sha256(error: Exception) -> str:
    try:
        message = str(error)
    except Exception:  # noqa: BLE001 - diagnostics must not replace the original error.
        message = "<exception-message-unavailable>"
    return sha256_bytes(_safe_utf8(message))


def _traceback_sha256(error: Exception) -> str:
    try:
        rendered = "".join(traceback.format_tb(error.__traceback__))
    except Exception:  # noqa: BLE001 - diagnostics must not replace the original error.
        rendered = "<traceback-unavailable>"
    return sha256_bytes(_safe_utf8(rendered))


def _exception_class(error: Exception) -> str:
    error_type = type(error)
    candidate = f"{error_type.__module__}.{error_type.__name__}"
    if _QUALIFIED_EXCEPTION_RE.fullmatch(candidate) is None:
        return "builtins.Exception"
    return candidate


def _prepare_failed_terminal(
    *,
    ownership: _D7PostStartOwnership,
    error: Exception,
    failure_stage: r.D7FailureStage,
    reason_code: str,
) -> D7PreparedFailedTerminal:
    start = ownership.start
    detail = e.D7InProcessFailureDetail(
        exception_class=_exception_class(error),
        exception_message_sha256=_exception_message_sha256(error),
        traceback_sha256=_traceback_sha256(error),
    )
    failure_payload = e.D7FailureEvidencePayload(
        replay_target_sha256=start.replay_target_sha256,
        attempt_key_sha256=start.attempt_key_sha256,
        execution_start_sha256=start.canonical_sha256,
        execution_identity_receipt_sha256=(start.execution_identity_receipt_sha256),
        failure_stage=failure_stage,
        origin=r.D7FailureEvidenceOrigin.IN_PROCESS,
        reason_code=reason_code,
        confirmation_value_access_state=(r.D7ConfirmationValueAccessState.UNKNOWN),
        detail=detail,
    )
    failure_evidence = r.D7FailureEvidenceRecord(
        replay_target_sha256=start.replay_target_sha256,
        attempt_key_sha256=start.attempt_key_sha256,
        execution_start_sha256=start.canonical_sha256,
        execution_identity_receipt_sha256=(start.execution_identity_receipt_sha256),
        failure_stage=failure_stage,
        origin=r.D7FailureEvidenceOrigin.IN_PROCESS,
        reason_code=reason_code,
        evidence_payload_sha256=failure_payload.canonical_sha256,
        evidence_payload_byte_count=len(failure_payload.canonical_bytes),
        external_verification_receipt_sha256=None,
        external_verification_receipt_byte_count=None,
    )
    failed_attempt = r.D7FailedAttemptRecord(
        replay_target_sha256=start.replay_target_sha256,
        attempt_key_sha256=start.attempt_key_sha256,
        execution_start_sha256=start.canonical_sha256,
        execution_identity_receipt_sha256=(start.execution_identity_receipt_sha256),
        failure_stage=failure_stage,
        failure_evidence_sha256=failure_evidence.canonical_sha256,
        started_unresolved_finalization_sha256=None,
        confirmation_value_access_state=(r.D7ConfirmationValueAccessState.UNKNOWN),
    )
    return D7PreparedFailedTerminal(
        ownership,
        failure_payload,
        failure_evidence,
        failed_attempt,
        _factory_token=_PREPARED_TERMINAL_FACTORY_TOKEN,
    )


def _attach_failed_terminal(
    error: Exception,
    prepared: D7PreparedFailedTerminal,
) -> None:
    try:
        setattr(error, D7_PREPARED_FAILED_TERMINAL_ATTRIBUTE, prepared)
    except BaseException:  # noqa: BLE001 - diagnostics must preserve the original.
        return
    try:
        error.add_note(
            "spirallens_d7_prepared_failed_terminal="
            f"{prepared.failure_evidence.canonical_sha256};"
            f"failed_attempt={prepared.failed_attempt.canonical_sha256}"
        )
    except BaseException:  # noqa: BLE001 - attachment remains valid without a note.
        return


def prepare_d7_post_start_terminal(
    ownership: _D7PostStartOwnership,
    scientific_producer: Callable[[], D7ScientificProducerOutput],
    /,
) -> D7PreparedScientificTerminal:
    """Run the zero-argument callback and prepare, but never publish, a terminal.

    The ownership object must already represent a structurally valid post-start
    prefix.  Ordinary exceptions are re-raised as the same objects.  When an
    exception permits mutation, a typed failed-terminal handoff is attached
    under :data:`D7_PREPARED_FAILED_TERMINAL_ATTRIBUTE`; mutation-resistant
    exceptions remain unattached rather than replacing the original error.
    """

    if type(ownership) is not _D7PostStartOwnership:
        raise TypeError("ownership must be an exact private D7 post-start handoff")
    if not callable(scientific_producer):
        raise TypeError("scientific_producer must be callable")

    failure_stage = r.D7FailureStage.EXECUTION_KERNEL
    reason_code = "scientific-producer-exception"
    try:
        producer_output = scientific_producer()
        failure_stage = r.D7FailureStage.RESULT_VALIDATION
        reason_code = "scientific-result-validation-exception"
        _validate_scientific_output(
            ownership=ownership,
            producer_output=producer_output,
        )
        failure_stage = r.D7FailureStage.TERMINAL_PREPARATION
        reason_code = "scientific-terminal-preparation-exception"
        return _prepare_scientific_terminal(
            ownership=ownership,
            producer_output=producer_output,
        )
    except Exception as error:
        prepared_failure = _prepare_failed_terminal(
            ownership=ownership,
            error=error,
            failure_stage=failure_stage,
            reason_code=reason_code,
        )
        _attach_failed_terminal(error, prepared_failure)
        raise
