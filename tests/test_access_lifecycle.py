from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest

from access_fixtures import preparation_descriptor
from spirallens.access import (
    AtlasAccessContractError,
    AtlasConsumer,
    AttemptAccessFacts,
    AttemptLifecycle,
    AttemptLifecycleError,
    AttemptPhase,
    AttemptPolicy,
    AttemptTerminalRecord,
    AttemptTerminalState,
    ProvenanceTaint,
    QuarantineDisposition,
)


def _lifecycle(
    *,
    policy: AttemptPolicy | None = None,
) -> AttemptLifecycle:
    descriptor = preparation_descriptor(
        allowed_consumers=frozenset(
            {
                AtlasConsumer.ATLAS_INTEGRITY_VALIDATION,
                AtlasConsumer.SUBJECT_PROTOCOL_PREPARATION,
            }
        ),
        attempt_policy=policy,
    )
    return AttemptLifecycle(
        attempt_id="attempt-001",
        descriptor_id=descriptor.descriptor_id,
        descriptor_canonical_sha256=descriptor.canonical_sha256,
        output_id=descriptor.capture.output_id,
        access_policy=descriptor.access_policy,
        attempt_policy=descriptor.attempt_policy,
    )


def test_attempt_policy_keeps_retry_scopes_independent() -> None:
    policy = AttemptPolicy(
        resume_same_attempt_authorized=True,
        reuse_output_authorized=False,
        fresh_replay_same_protocol_authorized=True,
        retry_after_outcome_observation_authorized=False,
        relabel_authorized=False,
    )

    assert policy.to_dict() == {
        "resume_same_attempt_authorized": True,
        "reuse_output_authorized": False,
        "fresh_replay_same_protocol_authorized": True,
        "retry_after_outcome_observation_authorized": False,
        "relabel_authorized": False,
    }
    assert AttemptPolicy.from_dict(policy.to_dict()) == policy
    with pytest.raises(
        AtlasAccessContractError,
        match="must be a boolean",
    ):
        AttemptPolicy.from_dict(
            {
                **policy.to_dict(),
                "reuse_output_authorized": 0,
            }
        )


def test_attempt_permits_exactly_one_terminal_transition() -> None:
    lifecycle = _lifecycle()
    facts = AttemptAccessFacts(
        model_accessed=True,
        payload_persisted=True,
        outcome_observed=False,
    )

    record = lifecycle.transition_to_terminal(
        state=AttemptTerminalState.COMPLETED_RECEIPTED,
        phase=AttemptPhase.POSTPUBLICATION_VALIDATION,
        access_facts=facts,
        reason_code="completed",
    )

    assert lifecycle.terminal_record is record
    assert record.state is AttemptTerminalState.COMPLETED_RECEIPTED
    assert record.quarantine is QuarantineDisposition.NOT_REQUIRED
    assert ProvenanceTaint.VALUE_DERIVED in record.access_policy.provenance_taints
    assert (
        ProvenanceTaint.TERMINAL_UNRECEIPTED
        not in record.access_policy.provenance_taints
    )
    assert (
        ProvenanceTaint.TERMINAL_QUARANTINED
        not in record.access_policy.provenance_taints
    )
    assert (
        AttemptTerminalRecord(
            **{
                "attempt_id": record.attempt_id,
                "descriptor_id": record.descriptor_id,
                "descriptor_canonical_sha256": (record.descriptor_canonical_sha256),
                "output_id": record.output_id,
                "state": record.state,
                "phase": record.phase,
                "access_facts": record.access_facts,
                "quarantine": record.quarantine,
                "reason_code": record.reason_code,
                "access_policy": record.access_policy,
                "attempt_policy": record.attempt_policy,
            }
        ).canonical_bytes
        == record.canonical_bytes
    )
    assert AttemptTerminalRecord.from_dict(record.to_dict()) == record
    unknown = record.to_dict()
    unknown["retry"] = True
    with pytest.raises(
        AtlasAccessContractError,
        match="unknown=.*retry",
    ):
        AttemptTerminalRecord.from_dict(unknown)
    with pytest.raises(
        AttemptLifecycleError,
        match="already has a terminal record",
    ):
        lifecycle.transition_to_terminal(
            state=AttemptTerminalState.COMPLETED_RECEIPTED,
            phase=AttemptPhase.POSTPUBLICATION_VALIDATION,
            access_facts=facts,
            reason_code="second-terminal",
        )


def test_attempt_terminal_transition_is_atomic_across_threads() -> None:
    lifecycle = _lifecycle()
    barrier = Barrier(3)

    def transition(index: int):
        barrier.wait()
        try:
            record = lifecycle.transition_to_terminal(
                state=AttemptTerminalState.COMPLETED_RECEIPTED,
                phase=AttemptPhase.POSTPUBLICATION_VALIDATION,
                access_facts=AttemptAccessFacts(
                    model_accessed=True,
                    payload_persisted=True,
                    outcome_observed=False,
                ),
                reason_code=f"thread-{index}",
            )
        except AttemptLifecycleError:
            return "denied", None
        return "completed", record

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(transition, index) for index in range(2)]
        barrier.wait()
        results = [future.result() for future in futures]

    assert sorted(status for status, _ in results) == [
        "completed",
        "denied",
    ]
    completed = next(record for status, record in results if status == "completed")
    assert lifecycle.terminal_record is completed


def test_terminal_unreceipted_is_quarantine_only_and_nonpromotable() -> None:
    lifecycle = _lifecycle()

    record = lifecycle.transition_to_terminal(
        state=AttemptTerminalState.TERMINAL_UNRECEIPTED,
        phase=AttemptPhase.RECEIPT_PUBLICATION,
        access_facts=AttemptAccessFacts(
            model_accessed=True,
            payload_persisted=True,
            outcome_observed=False,
        ),
        reason_code="receipt-publication-failed",
    )

    assert record.quarantine is QuarantineDisposition.REQUIRED_RETAIN_FOR_FORENSICS
    assert record.access_policy.scientific_claim_eligible is False
    assert record.access_policy.allowed_consumers == frozenset(
        {AtlasConsumer.ATLAS_INTEGRITY_VALIDATION}
    )
    assert record.access_policy.provenance_taints.issuperset(
        {
            ProvenanceTaint.VALUE_DERIVED,
            ProvenanceTaint.TERMINAL_QUARANTINED,
            ProvenanceTaint.TERMINAL_UNRECEIPTED,
        }
    )
    assert record.to_dict()["state"] == "terminal_unreceipted"
    assert record.to_dict()["quarantine"] == ("required_retain_for_forensics")


def test_partial_payload_is_quarantined_but_not_unreceipted() -> None:
    record = _lifecycle().transition_to_terminal(
        state=AttemptTerminalState.FAILED_AFTER_PAYLOAD,
        phase=AttemptPhase.ATLAS_FINALIZATION,
        access_facts=AttemptAccessFacts(
            model_accessed=True,
            payload_persisted=True,
            outcome_observed=True,
        ),
        reason_code="array-validation-failed",
    )

    assert record.quarantine is (QuarantineDisposition.REQUIRED_RETAIN_FOR_FORENSICS)
    assert record.access_policy.provenance_taints.issuperset(
        {
            ProvenanceTaint.VALUE_DERIVED,
            ProvenanceTaint.OUTCOME_EXPOSED,
            ProvenanceTaint.TERMINAL_QUARANTINED,
        }
    )
    assert (
        ProvenanceTaint.TERMINAL_UNRECEIPTED
        not in record.access_policy.provenance_taints
    )
    assert record.fresh_replay_authorized is False


def test_fresh_replay_is_new_attempt_and_respects_outcome_policy() -> None:
    no_observed_retry = AttemptPolicy(
        resume_same_attempt_authorized=False,
        reuse_output_authorized=False,
        fresh_replay_same_protocol_authorized=True,
        retry_after_outcome_observation_authorized=False,
        relabel_authorized=False,
    )
    unobserved = _lifecycle(policy=no_observed_retry).transition_to_terminal(
        state=AttemptTerminalState.FAILED_AFTER_MODEL_BEFORE_PAYLOAD,
        phase=AttemptPhase.MODEL_ACCESS,
        access_facts=AttemptAccessFacts(
            model_accessed=True,
            payload_persisted=False,
            outcome_observed=False,
        ),
        reason_code="model-layout-mismatch",
    )
    observed = _lifecycle(policy=no_observed_retry).transition_to_terminal(
        state=AttemptTerminalState.FAILED_AFTER_PAYLOAD,
        phase=AttemptPhase.CAPTURE,
        access_facts=AttemptAccessFacts(
            model_accessed=True,
            payload_persisted=True,
            outcome_observed=True,
        ),
        reason_code="capture-failed",
    )

    assert unobserved.fresh_replay_authorized is True
    assert observed.fresh_replay_authorized is False
    assert no_observed_retry.resume_same_attempt_authorized is False
    assert no_observed_retry.reuse_output_authorized is False


def test_terminal_state_rejects_inconsistent_access_facts() -> None:
    with pytest.raises(
        AtlasAccessContractError,
        match="payload cannot be persisted before model access",
    ):
        AttemptAccessFacts(
            model_accessed=False,
            payload_persisted=True,
            outcome_observed=False,
        )

    lifecycle = _lifecycle()
    with pytest.raises(
        AtlasAccessContractError,
        match="terminal_unreceipted requires",
    ):
        lifecycle.transition_to_terminal(
            state=AttemptTerminalState.TERMINAL_UNRECEIPTED,
            phase=AttemptPhase.RECEIPT_PUBLICATION,
            access_facts=AttemptAccessFacts(
                model_accessed=True,
                payload_persisted=False,
                outcome_observed=False,
            ),
            reason_code="invalid-terminal",
        )
    assert lifecycle.terminal_record is None


def test_only_interrupted_terminal_may_retain_unknown_access_facts() -> None:
    lifecycle = _lifecycle()

    with pytest.raises(
        AtlasAccessContractError,
        match="only interrupted_unknown",
    ):
        lifecycle.transition_to_terminal(
            state=AttemptTerminalState.COMPLETED_RECEIPTED,
            phase=AttemptPhase.POSTPUBLICATION_VALIDATION,
            access_facts=AttemptAccessFacts(
                model_accessed=True,
                payload_persisted=True,
                outcome_observed=None,
            ),
            reason_code="unknown-outcome",
        )
    assert lifecycle.terminal_record is None


def test_interrupted_unknown_retains_unknown_facts_and_quarantine() -> None:
    record = _lifecycle().transition_to_terminal(
        state=AttemptTerminalState.INTERRUPTED_UNKNOWN,
        phase=AttemptPhase.CAPTURE,
        access_facts=AttemptAccessFacts(
            model_accessed=True,
            payload_persisted=None,
            outcome_observed=None,
        ),
        reason_code="process-interrupted",
    )

    assert record.quarantine is (QuarantineDisposition.REQUIRED_RETAIN_FOR_FORENSICS)
    assert (
        ProvenanceTaint.TERMINAL_QUARANTINED in record.access_policy.provenance_taints
    )
    assert (
        ProvenanceTaint.TERMINAL_UNRECEIPTED
        not in record.access_policy.provenance_taints
    )
    assert record.to_dict()["access_facts"]["payload_persisted"] is None
    assert record.fresh_replay_authorized is False
