from __future__ import annotations

import json
from dataclasses import replace

import pytest

from spirallens.access import (
    AtlasAccessContractError,
    AtlasAccessPolicy,
    AtlasConsumer,
    AtlasConsumerDenied,
    ProvenanceTaint,
    ValueAccessLineage,
    ValueAccessTransition,
    bind_value_access_lineage,
    reverify_value_access_lineage,
)


def _parent_policy(
    *,
    consumers: frozenset[AtlasConsumer] = frozenset(
        {AtlasConsumer.NUMERIC_PAYLOAD_VALIDATION}
    ),
) -> AtlasAccessPolicy:
    return AtlasAccessPolicy(
        origin_execution_class="synthetic_calibration",
        claim_ceiling="level_0",
        scientific_claim_eligible=False,
        allowed_consumers=consumers,
        provenance_taints=frozenset({ProvenanceTaint.INSTRUMENT_UNQUALIFIED}),
    )


def test_value_access_lineage_round_trips_and_reverifies() -> None:
    parent = _parent_policy()

    lineage = bind_value_access_lineage(
        parent,
        expected_parent_policy_sha256=parent.sha256,
        consumer=AtlasConsumer.NUMERIC_PAYLOAD_VALIDATION,
    )
    restored = ValueAccessLineage.from_dict(json.loads(lineage.canonical_bytes))

    assert restored == lineage
    assert restored.canonical_bytes == lineage.canonical_bytes
    assert restored.transition is ValueAccessTransition.VALUE_DECODE
    assert restored.derived_policy.allowed_consumers == frozenset(
        {AtlasConsumer.NUMERIC_PAYLOAD_VALIDATION}
    )
    assert restored.derived_policy.provenance_taints == (
        parent.provenance_taints
        | {
            ProvenanceTaint.VALUE_DERIVED,
            ProvenanceTaint.OUTCOME_EXPOSED,
        }
    )
    reverify_value_access_lineage(
        restored,
        parent,
        expected_parent_policy_sha256=parent.sha256,
    )


def test_value_access_lineage_requires_trusted_parent_digest() -> None:
    parent = _parent_policy()

    with pytest.raises(
        AtlasAccessContractError,
        match="trusted out-of-band digest",
    ):
        bind_value_access_lineage(
            parent,
            expected_parent_policy_sha256="0" * 64,
            consumer=AtlasConsumer.NUMERIC_PAYLOAD_VALIDATION,
        )


def test_value_access_lineage_denies_consumer_before_derivation() -> None:
    parent = _parent_policy(consumers=frozenset())

    with pytest.raises(AtlasConsumerDenied):
        bind_value_access_lineage(
            parent,
            expected_parent_policy_sha256=parent.sha256,
            consumer=AtlasConsumer.NUMERIC_PAYLOAD_VALIDATION,
        )


def test_persisted_lineage_cannot_broaden_or_remove_required_taints() -> None:
    parent = _parent_policy(
        consumers=frozenset(
            {
                AtlasConsumer.NUMERIC_PAYLOAD_VALIDATION,
                AtlasConsumer.GRAPH_CONSTRUCTION,
            }
        )
    )
    lineage = bind_value_access_lineage(
        parent,
        expected_parent_policy_sha256=parent.sha256,
        consumer=AtlasConsumer.NUMERIC_PAYLOAD_VALIDATION,
    )
    broadened_policy = replace(
        lineage.derived_policy,
        allowed_consumers=frozenset(
            {
                AtlasConsumer.NUMERIC_PAYLOAD_VALIDATION,
                AtlasConsumer.GRAPH_CONSTRUCTION,
            }
        ),
    )
    with pytest.raises(
        AtlasAccessContractError,
        match="authorize exactly",
    ):
        replace(
            lineage,
            derived_policy=broadened_policy,
            derived_policy_sha256=broadened_policy.sha256,
        )

    missing_taint_policy = replace(
        lineage.derived_policy,
        provenance_taints=frozenset(
            taint
            for taint in lineage.derived_policy.provenance_taints
            if taint is not ProvenanceTaint.OUTCOME_EXPOSED
        ),
    )
    with pytest.raises(
        AtlasAccessContractError,
        match="value and outcome taints",
    ):
        replace(
            lineage,
            derived_policy=missing_taint_policy,
            derived_policy_sha256=missing_taint_policy.sha256,
        )


def test_reverification_rejects_conservative_but_noncanonical_child() -> None:
    parent = _parent_policy()
    lineage = bind_value_access_lineage(
        parent,
        expected_parent_policy_sha256=parent.sha256,
        consumer=AtlasConsumer.NUMERIC_PAYLOAD_VALIDATION,
    )
    extra_taint_policy = replace(
        lineage.derived_policy,
        provenance_taints=lineage.derived_policy.provenance_taints
        | {ProvenanceTaint.CLAIM_INELIGIBLE_CONTEXT},
    )
    forged = replace(
        lineage,
        derived_policy=extra_taint_policy,
        derived_policy_sha256=extra_taint_policy.sha256,
    )

    with pytest.raises(
        AtlasAccessContractError,
        match="exact trusted derivation",
    ):
        reverify_value_access_lineage(
            forged,
            parent,
            expected_parent_policy_sha256=parent.sha256,
        )
