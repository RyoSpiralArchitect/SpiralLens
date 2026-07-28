"""Canonical lineage for value-decoding access-policy restrictions.

A policy object is a declaration, not evidence of ancestry.  This module
therefore requires an out-of-band trusted parent digest before constructing or
re-verifying a persisted value-access lineage.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum

from spirallens.core.canonical import (
    canonical_json_bytes,
    canonical_json_sha256,
)

from .contracts import (
    AtlasAccessContractError,
    AtlasAccessPolicy,
    AtlasConsumer,
    ProvenanceTaint,
    require_atlas_consumer,
    restrict_atlas_access,
)

VALUE_ACCESS_LINEAGE_SCHEMA_VERSION = "spirallens.value-access-lineage.v0.1"

_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class ValueAccessTransition(str, Enum):
    """Closed transition kinds that expose persisted numerical values."""

    VALUE_DECODE = "value_decode"


def _sha256(value: object, *, label: str) -> str:
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        raise AtlasAccessContractError(f"{label} must be a lowercase SHA-256 digest")
    return value


def _expected_derived_policy(
    parent_policy: AtlasAccessPolicy,
    *,
    consumer: AtlasConsumer,
) -> AtlasAccessPolicy:
    require_atlas_consumer(parent_policy, consumer)
    return restrict_atlas_access(
        parent_policy,
        allowed_consumers=frozenset({consumer}),
        provenance_taints=parent_policy.provenance_taints
        | {
            ProvenanceTaint.VALUE_DERIVED,
            ProvenanceTaint.OUTCOME_EXPOSED,
        },
    )


@dataclass(frozen=True, slots=True)
class ValueAccessLineage:
    """Persistable, content-addressed child-policy lineage declaration."""

    parent_policy_sha256: str
    derived_policy: AtlasAccessPolicy
    derived_policy_sha256: str
    consumer: AtlasConsumer
    transition: ValueAccessTransition = ValueAccessTransition.VALUE_DECODE
    schema_version: str = VALUE_ACCESS_LINEAGE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != VALUE_ACCESS_LINEAGE_SCHEMA_VERSION:
            raise AtlasAccessContractError("unsupported value-access lineage schema")
        _sha256(self.parent_policy_sha256, label="parent_policy_sha256")
        if not isinstance(self.derived_policy, AtlasAccessPolicy):
            raise TypeError("derived_policy must be an AtlasAccessPolicy")
        _sha256(self.derived_policy_sha256, label="derived_policy_sha256")
        if self.derived_policy_sha256 != self.derived_policy.sha256:
            raise AtlasAccessContractError(
                "derived_policy_sha256 differs from the canonical policy"
            )
        if not isinstance(self.consumer, AtlasConsumer):
            raise TypeError("consumer must be an AtlasConsumer")
        if not isinstance(self.transition, ValueAccessTransition):
            raise TypeError("transition must be a ValueAccessTransition")
        if self.transition is not ValueAccessTransition.VALUE_DECODE:
            raise AtlasAccessContractError(
                "value-access lineage must describe value decoding"
            )
        if self.derived_policy.allowed_consumers != frozenset({self.consumer}):
            raise AtlasAccessContractError(
                "derived value-access policy must authorize exactly its consumer"
            )
        required_taints = {
            ProvenanceTaint.VALUE_DERIVED,
            ProvenanceTaint.OUTCOME_EXPOSED,
        }
        if not required_taints.issubset(self.derived_policy.provenance_taints):
            raise AtlasAccessContractError(
                "derived value-access policy must retain value and outcome taints"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "transition": self.transition.value,
            "consumer": self.consumer.value,
            "parent_policy_sha256": self.parent_policy_sha256,
            "derived_policy": self.derived_policy.to_dict(),
            "derived_policy_sha256": self.derived_policy_sha256,
        }

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_dict())

    @property
    def canonical_sha256(self) -> str:
        return canonical_json_sha256(self.to_dict())

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> ValueAccessLineage:
        if not isinstance(value, Mapping) or any(
            not isinstance(key, str) for key in value
        ):
            raise AtlasAccessContractError(
                "value-access lineage must be a string-keyed mapping"
            )
        fields = {
            "schema_version",
            "transition",
            "consumer",
            "parent_policy_sha256",
            "derived_policy",
            "derived_policy_sha256",
        }
        actual = set(value)
        if actual != fields:
            raise AtlasAccessContractError(
                "value-access lineage fields differ from the contract: "
                f"missing={sorted(fields - actual)}, "
                f"unknown={sorted(actual - fields)}"
            )
        try:
            transition = ValueAccessTransition(value["transition"])
        except (TypeError, ValueError) as error:
            raise AtlasAccessContractError(
                "value-access lineage transition is unsupported"
            ) from error
        try:
            consumer = AtlasConsumer(value["consumer"])
        except (TypeError, ValueError) as error:
            raise AtlasAccessContractError(
                "value-access lineage consumer is unsupported"
            ) from error
        policy_document = value["derived_policy"]
        if not isinstance(policy_document, Mapping) or any(
            not isinstance(key, str) for key in policy_document
        ):
            raise AtlasAccessContractError(
                "derived_policy must be a string-keyed mapping"
            )
        return cls(
            schema_version=value["schema_version"],
            transition=transition,
            consumer=consumer,
            parent_policy_sha256=_sha256(
                value["parent_policy_sha256"],
                label="parent_policy_sha256",
            ),
            derived_policy=AtlasAccessPolicy.from_dict(policy_document),
            derived_policy_sha256=_sha256(
                value["derived_policy_sha256"],
                label="derived_policy_sha256",
            ),
        )


def bind_value_access_lineage(
    parent_policy: AtlasAccessPolicy,
    *,
    expected_parent_policy_sha256: str,
    consumer: AtlasConsumer,
) -> ValueAccessLineage:
    """Bind one exact monotone value-decoding child to a trusted parent digest."""

    if not isinstance(parent_policy, AtlasAccessPolicy):
        raise TypeError("parent_policy must be an AtlasAccessPolicy")
    trusted_digest = _sha256(
        expected_parent_policy_sha256,
        label="expected_parent_policy_sha256",
    )
    if parent_policy.sha256 != trusted_digest:
        raise AtlasAccessContractError(
            "parent policy differs from its trusted out-of-band digest"
        )
    if not isinstance(consumer, AtlasConsumer):
        raise TypeError("consumer must be an AtlasConsumer")
    derived = _expected_derived_policy(parent_policy, consumer=consumer)
    return ValueAccessLineage(
        parent_policy_sha256=trusted_digest,
        derived_policy=derived,
        derived_policy_sha256=derived.sha256,
        consumer=consumer,
    )


def reverify_value_access_lineage(
    lineage: ValueAccessLineage,
    parent_policy: AtlasAccessPolicy,
    *,
    expected_parent_policy_sha256: str,
) -> None:
    """Re-establish persisted lineage from a trusted parent policy identity."""

    if not isinstance(lineage, ValueAccessLineage):
        raise TypeError("lineage must be a ValueAccessLineage")
    rebound = bind_value_access_lineage(
        parent_policy,
        expected_parent_policy_sha256=expected_parent_policy_sha256,
        consumer=lineage.consumer,
    )
    if lineage != rebound:
        raise AtlasAccessContractError(
            "persisted value-access lineage is not the exact trusted derivation"
        )
