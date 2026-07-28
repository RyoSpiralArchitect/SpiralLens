from __future__ import annotations

from dataclasses import FrozenInstanceError, replace

import pytest

from access_fixtures import preparation_descriptor
from spirallens.access import (
    AtlasAccessContractError,
    AtlasAccessPolicy,
    AtlasConsumer,
    AtlasConsumerDenied,
    AtlasPreparationDescriptor,
    AttemptPolicy,
    ProvenanceEscalationError,
    ProvenanceTaint,
    require_atlas_consumer,
    restrict_atlas_access,
)


def test_access_policy_is_immutable_and_uses_closed_enums() -> None:
    consumers = {AtlasConsumer.SUBJECT_PROTOCOL_PREPARATION}
    taints = {ProvenanceTaint.VALUE_DERIVED}
    policy = AtlasAccessPolicy(
        origin_execution_class="subject_preparation",
        claim_ceiling="level_0",
        scientific_claim_eligible=False,
        allowed_consumers=consumers,
        provenance_taints=taints,
    )
    consumers.clear()
    taints.clear()

    assert policy.allowed_consumers == frozenset(
        {AtlasConsumer.SUBJECT_PROTOCOL_PREPARATION}
    )
    assert policy.provenance_taints == frozenset({ProvenanceTaint.VALUE_DERIVED})
    with pytest.raises(FrozenInstanceError):
        policy.claim_ceiling = "level_3"  # type: ignore[misc]
    with pytest.raises(
        AtlasAccessContractError,
        match="only AtlasConsumer",
    ):
        AtlasAccessPolicy(
            origin_execution_class="subject_preparation",
            claim_ceiling="level_0",
            scientific_claim_eligible=False,
            allowed_consumers=frozenset({"candidate_search"}),  # type: ignore[arg-type]
            provenance_taints=frozenset(),
        )
    with pytest.raises(ValueError):
        AtlasConsumer("candidate_extraction")
    with pytest.raises(ValueError):
        ProvenanceTaint("clean")


def test_public_example_policy_is_integrity_only_and_never_claim_eligible() -> None:
    policy = AtlasAccessPolicy(
        origin_execution_class="public_example_engineering",
        claim_ceiling="level_0",
        scientific_claim_eligible=False,
        allowed_consumers=frozenset({AtlasConsumer.ATLAS_INTEGRITY_VALIDATION}),
        provenance_taints=frozenset(
            {
                ProvenanceTaint.PUBLIC_EXAMPLE_ENGINEERING,
                ProvenanceTaint.CLAIM_INELIGIBLE_CONTEXT,
                ProvenanceTaint.INSTRUMENT_UNQUALIFIED,
            }
        ),
    )

    require_atlas_consumer(
        policy,
        AtlasConsumer.ATLAS_INTEGRITY_VALIDATION,
    )
    for consumer in AtlasConsumer:
        if consumer is AtlasConsumer.ATLAS_INTEGRITY_VALIDATION:
            continue
        with pytest.raises(AtlasConsumerDenied):
            require_atlas_consumer(policy, consumer)
    with pytest.raises(TypeError, match="AtlasConsumer"):
        require_atlas_consumer(policy, "candidate_search")  # type: ignore[arg-type]

    with pytest.raises(
        AtlasAccessContractError,
        match="cannot be scientifically claim-eligible",
    ):
        replace(policy, scientific_claim_eligible=True)
    with pytest.raises(
        AtlasAccessContractError,
        match="only atlas integrity validation",
    ):
        replace(
            policy,
            allowed_consumers=frozenset(
                {
                    AtlasConsumer.ATLAS_INTEGRITY_VALIDATION,
                    AtlasConsumer.CANDIDATE_SEARCH,
                }
            ),
        )


def test_restriction_can_only_remove_consumers_and_add_taints() -> None:
    parent = AtlasAccessPolicy(
        origin_execution_class="subject_discovery",
        claim_ceiling="level_1d",
        scientific_claim_eligible=True,
        allowed_consumers=frozenset(
            {
                AtlasConsumer.CANDIDATE_SEARCH,
                AtlasConsumer.GRAPH_CONSTRUCTION,
            }
        ),
        provenance_taints=frozenset({ProvenanceTaint.VALUE_DERIVED}),
    )

    child = restrict_atlas_access(
        parent,
        allowed_consumers={AtlasConsumer.CANDIDATE_SEARCH},
        provenance_taints={
            ProvenanceTaint.VALUE_DERIVED,
            ProvenanceTaint.OUTCOME_EXPOSED,
        },
        scientific_claim_eligible=False,
    )
    assert child.origin_execution_class == parent.origin_execution_class
    assert child.claim_ceiling == parent.claim_ceiling
    assert child.allowed_consumers == frozenset({AtlasConsumer.CANDIDATE_SEARCH})
    assert child.provenance_taints.issuperset(parent.provenance_taints)
    assert child.scientific_claim_eligible is False

    with pytest.raises(
        ProvenanceEscalationError,
        match="cannot add consumers",
    ):
        restrict_atlas_access(
            parent,
            allowed_consumers={
                *parent.allowed_consumers,
                AtlasConsumer.SEMANTIC_ANALYSIS,
            },
        )
    with pytest.raises(
        ProvenanceEscalationError,
        match="cannot remove provenance taints",
    ):
        restrict_atlas_access(parent, provenance_taints=set())
    with pytest.raises(
        ProvenanceEscalationError,
        match="value-derived provenance cannot be relabelled",
    ):
        restrict_atlas_access(
            parent,
            origin_execution_class="subject_confirmation",
        )
    with pytest.raises(
        ProvenanceEscalationError,
        match="claim ceiling",
    ):
        restrict_atlas_access(parent, claim_ceiling="level_2t")

    ineligible = replace(parent, scientific_claim_eligible=False)
    with pytest.raises(
        ProvenanceEscalationError,
        match="cannot gain scientific claim eligibility",
    ):
        restrict_atlas_access(
            ineligible,
            scientific_claim_eligible=True,
        )


def test_terminal_quarantine_and_unreceipted_taints_remain_distinct() -> None:
    with pytest.raises(
        AtlasAccessContractError,
        match="must also be terminally quarantined",
    ):
        AtlasAccessPolicy(
            origin_execution_class="subject_capture",
            claim_ceiling="level_0",
            scientific_claim_eligible=False,
            allowed_consumers=frozenset({AtlasConsumer.ATLAS_INTEGRITY_VALIDATION}),
            provenance_taints=frozenset({ProvenanceTaint.TERMINAL_UNRECEIPTED}),
        )

    quarantined = AtlasAccessPolicy(
        origin_execution_class="subject_capture",
        claim_ceiling="level_0",
        scientific_claim_eligible=False,
        allowed_consumers=frozenset({AtlasConsumer.ATLAS_INTEGRITY_VALIDATION}),
        provenance_taints=frozenset({ProvenanceTaint.TERMINAL_QUARANTINED}),
    )
    assert ProvenanceTaint.TERMINAL_UNRECEIPTED not in quarantined.provenance_taints


def test_descriptor_schema_is_exact_and_typed_round_trip_is_canonical() -> None:
    descriptor = preparation_descriptor()
    payload = descriptor.to_dict()

    assert (
        AtlasPreparationDescriptor.from_dict(payload).canonical_bytes
        == descriptor.canonical_bytes
    )
    unknown = dict(payload)
    unknown["summaries"] = {"outcome": 1}
    with pytest.raises(
        AtlasAccessContractError,
        match="unknown=.*summaries",
    ):
        AtlasPreparationDescriptor.from_dict(unknown)

    missing = dict(payload)
    missing.pop("attempt_policy")
    with pytest.raises(
        AtlasAccessContractError,
        match="missing=.*attempt_policy",
    ):
        AtlasPreparationDescriptor.from_dict(missing)

    bad_rows = descriptor.row_domain.to_dict()
    bad_rows["row_count"] = True
    bad_payload = dict(payload)
    bad_payload["row_domain"] = bad_rows
    with pytest.raises(
        AtlasAccessContractError,
        match="positive integer",
    ):
        AtlasPreparationDescriptor.from_dict(bad_payload)


def test_descriptor_rejects_relabel_and_value_derived_observed_retry() -> None:
    relabel = AttemptPolicy(
        resume_same_attempt_authorized=False,
        reuse_output_authorized=False,
        fresh_replay_same_protocol_authorized=False,
        retry_after_outcome_observation_authorized=False,
        relabel_authorized=True,
    )
    with pytest.raises(
        AtlasAccessContractError,
        match="cannot authorize relabelling",
    ):
        preparation_descriptor(attempt_policy=relabel)

    retry = replace(
        relabel,
        relabel_authorized=False,
        retry_after_outcome_observation_authorized=True,
    )
    with pytest.raises(
        AtlasAccessContractError,
        match="cannot authorize an observed outcome retry",
    ):
        preparation_descriptor(
            provenance_taints=frozenset({ProvenanceTaint.VALUE_DERIVED}),
            attempt_policy=retry,
        )


def test_claim_ineligible_context_requires_append_only_taint() -> None:
    with pytest.raises(
        AtlasAccessContractError,
        match="must remain an explicit provenance taint",
    ):
        preparation_descriptor(context_claim_eligible=False)

    descriptor = preparation_descriptor(
        context_claim_eligible=False,
        provenance_taints=frozenset({ProvenanceTaint.CLAIM_INELIGIBLE_CONTEXT}),
    )
    assert (
        ProvenanceTaint.CLAIM_INELIGIBLE_CONTEXT
        in descriptor.access_policy.provenance_taints
    )
