"""Framework-neutral access and pre-observation provenance contracts.

The contracts in this module describe what a persisted observation may be
used for.  They do not load an atlas, inspect a model, or authorize execution.
Provenance restrictions are monotone: derivation may remove consumers and add
taints, but it may not broaden access or relabel the origin.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import Enum

from spirallens.core.canonical import (
    canonical_json_bytes,
    canonical_json_sha256,
)

ATLAS_PREPARATION_DESCRIPTOR_SCHEMA_VERSION = (
    "spirallens.atlas-preparation-descriptor.v0.1"
)

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/+-]{0,255}$")


class AtlasAccessContractError(ValueError):
    """Raised when an access artifact violates its closed contract."""


class AtlasConsumerDenied(PermissionError):
    """Raised when a provenance policy does not authorize a consumer."""


class ProvenanceEscalationError(AtlasAccessContractError):
    """Raised when a derivation broadens or relabels provenance."""


class AtlasConsumer(str, Enum):
    """Closed identifiers for consumers of persisted atlas observations."""

    ATLAS_INTEGRITY_VALIDATION = "atlas_integrity_validation"
    NUMERIC_PAYLOAD_VALIDATION = "numeric_payload_validation"
    SUBJECT_PROTOCOL_PREPARATION = "subject_protocol_preparation"
    SUBJECT_EXECUTION = "subject_execution"
    INSTRUMENT_BUNDLE_CONVERSION = "instrument_bundle_conversion"
    CANDIDATE_SEARCH = "candidate_search"
    NEIGHBOR_AUDIT = "neighbor_audit"
    GRAPH_CONSTRUCTION = "graph_construction"
    FIELD_ESTIMATION = "field_estimation"
    CORE_DETECTION = "core_detection"
    LOOP_CONSTRUCTION = "loop_construction"
    HOLONOMY_ANALYSIS = "holonomy_analysis"
    WINDING_ANALYSIS = "winding_analysis"
    SEMANTIC_ANALYSIS = "semantic_analysis"
    SAE_ANALYSIS = "sae_analysis"
    CAUSAL_ANALYSIS = "causal_analysis"
    INTEGER_OUTPUT = "integer_output"


class ProvenanceTaint(str, Enum):
    """Append-only restrictions inherited by every derived artifact."""

    PUBLIC_EXAMPLE_ENGINEERING = "public_example_engineering"
    CLAIM_INELIGIBLE_CONTEXT = "claim_ineligible_context"
    INSTRUMENT_UNQUALIFIED = "instrument_unqualified"
    VALUE_DERIVED = "value_derived"
    OUTCOME_EXPOSED = "outcome_exposed"
    TERMINAL_QUARANTINED = "terminal_quarantined"
    TERMINAL_UNRECEIPTED = "terminal_unreceipted"


def _exact_keys(
    value: Mapping[str, object],
    expected: set[str] | frozenset[str],
    *,
    label: str,
) -> None:
    actual = set(value)
    if actual != set(expected):
        raise AtlasAccessContractError(
            f"{label} fields differ from the contract: "
            f"missing={sorted(set(expected) - actual)}, "
            f"unknown={sorted(actual - set(expected))}"
        )


def _mapping(value: object, *, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping) or any(not isinstance(key, str) for key in value):
        raise AtlasAccessContractError(f"{label} must be a string-keyed mapping")
    return value


def _string(value: object, *, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise AtlasAccessContractError(f"{label} must be a non-empty string")
    return value


def _identifier(value: object, *, label: str) -> str:
    text = _string(value, label=label)
    if _IDENTIFIER.fullmatch(text) is None:
        raise AtlasAccessContractError(f"{label} must be a portable identifier")
    return text


def _sha256(value: object, *, label: str) -> str:
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        raise AtlasAccessContractError(f"{label} must be a lowercase SHA-256 digest")
    return value


def _plain_bool(value: object, *, label: str) -> bool:
    if type(value) is not bool:
        raise AtlasAccessContractError(f"{label} must be a boolean")
    return value


def _plain_positive_int(value: object, *, label: str) -> int:
    if type(value) is not int or value <= 0:
        raise AtlasAccessContractError(f"{label} must be a positive integer")
    return value


def _enum_value(
    value: object,
    enum_type: type[Enum],
    *,
    label: str,
) -> Enum:
    if not isinstance(value, str):
        raise AtlasAccessContractError(f"{label} must be a string")
    try:
        return enum_type(value)
    except ValueError as error:
        raise AtlasAccessContractError(
            f"{label} is not a supported {enum_type.__name__}"
        ) from error


def _enum_set(
    values: object,
    enum_type: type[Enum],
    *,
    label: str,
) -> frozenset[Enum]:
    if not isinstance(values, list):
        raise AtlasAccessContractError(f"{label} must be a list")
    parsed = tuple(
        _enum_value(value, enum_type, label=f"{label}[{index}]")
        for index, value in enumerate(values)
    )
    serialized = tuple(item.value for item in parsed)
    if serialized != tuple(sorted(set(serialized))):
        raise AtlasAccessContractError(f"{label} must be strictly sorted and unique")
    return frozenset(parsed)


@dataclass(frozen=True, slots=True)
class AtlasAccessPolicy:
    """Immutable origin, claim ceiling, allowlist, and append-only taints."""

    origin_execution_class: str
    claim_ceiling: str
    scientific_claim_eligible: bool
    allowed_consumers: frozenset[AtlasConsumer]
    provenance_taints: frozenset[ProvenanceTaint]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "origin_execution_class",
            _identifier(
                self.origin_execution_class,
                label="origin_execution_class",
            ),
        )
        object.__setattr__(
            self,
            "claim_ceiling",
            _identifier(self.claim_ceiling, label="claim_ceiling"),
        )
        _plain_bool(
            self.scientific_claim_eligible,
            label="scientific_claim_eligible",
        )
        consumers = frozenset(self.allowed_consumers)
        taints = frozenset(self.provenance_taints)
        if any(not isinstance(item, AtlasConsumer) for item in consumers):
            raise AtlasAccessContractError(
                "allowed_consumers must contain only AtlasConsumer values"
            )
        if any(not isinstance(item, ProvenanceTaint) for item in taints):
            raise AtlasAccessContractError(
                "provenance_taints must contain only ProvenanceTaint values"
            )
        object.__setattr__(self, "allowed_consumers", consumers)
        object.__setattr__(self, "provenance_taints", taints)

        engineering = (
            ProvenanceTaint.PUBLIC_EXAMPLE_ENGINEERING in taints
            or self.origin_execution_class == "public_example_engineering"
        )
        if engineering:
            if (
                self.origin_execution_class != "public_example_engineering"
                or ProvenanceTaint.PUBLIC_EXAMPLE_ENGINEERING not in taints
            ):
                raise AtlasAccessContractError(
                    "public-example engineering origin and taint must agree"
                )
            if self.scientific_claim_eligible:
                raise AtlasAccessContractError(
                    "public-example engineering provenance cannot be "
                    "scientifically claim-eligible"
                )
            if not consumers.issubset({AtlasConsumer.ATLAS_INTEGRITY_VALIDATION}):
                raise AtlasAccessContractError(
                    "public-example engineering provenance can authorize "
                    "only atlas integrity validation"
                )
        if (
            self.scientific_claim_eligible
            and ProvenanceTaint.CLAIM_INELIGIBLE_CONTEXT in taints
        ):
            raise AtlasAccessContractError(
                "a claim-ineligible context cannot become claim-eligible"
            )
        if (
            self.scientific_claim_eligible
            and ProvenanceTaint.INSTRUMENT_UNQUALIFIED in taints
        ):
            raise AtlasAccessContractError(
                "an unqualified instrument cannot become claim-eligible"
            )
        if (
            ProvenanceTaint.TERMINAL_UNRECEIPTED in taints
            and ProvenanceTaint.TERMINAL_QUARANTINED not in taints
        ):
            raise AtlasAccessContractError(
                "terminal_unreceipted provenance must also be terminally quarantined"
            )
        if ProvenanceTaint.TERMINAL_QUARANTINED in taints:
            if self.scientific_claim_eligible:
                raise AtlasAccessContractError(
                    "terminally quarantined provenance cannot be claim-eligible"
                )
            if not consumers.issubset({AtlasConsumer.ATLAS_INTEGRITY_VALIDATION}):
                raise AtlasAccessContractError(
                    "terminally quarantined provenance is integrity-only"
                )

    def to_dict(self) -> dict[str, object]:
        return {
            "origin_execution_class": self.origin_execution_class,
            "claim_ceiling": self.claim_ceiling,
            "scientific_claim_eligible": self.scientific_claim_eligible,
            "allowed_consumers": sorted(item.value for item in self.allowed_consumers),
            "provenance_taints": sorted(item.value for item in self.provenance_taints),
        }

    @property
    def sha256(self) -> str:
        return canonical_json_sha256(self.to_dict())

    @classmethod
    def from_dict(
        cls,
        value: Mapping[str, object],
    ) -> AtlasAccessPolicy:
        item = _mapping(value, label="access_policy")
        _exact_keys(
            item,
            {
                "origin_execution_class",
                "claim_ceiling",
                "scientific_claim_eligible",
                "allowed_consumers",
                "provenance_taints",
            },
            label="access_policy",
        )
        consumers = _enum_set(
            item["allowed_consumers"],
            AtlasConsumer,
            label="access_policy.allowed_consumers",
        )
        taints = _enum_set(
            item["provenance_taints"],
            ProvenanceTaint,
            label="access_policy.provenance_taints",
        )
        return cls(
            origin_execution_class=_identifier(
                item["origin_execution_class"],
                label="access_policy.origin_execution_class",
            ),
            claim_ceiling=_identifier(
                item["claim_ceiling"],
                label="access_policy.claim_ceiling",
            ),
            scientific_claim_eligible=_plain_bool(
                item["scientific_claim_eligible"],
                label="access_policy.scientific_claim_eligible",
            ),
            allowed_consumers=frozenset(
                item for item in consumers if isinstance(item, AtlasConsumer)
            ),
            provenance_taints=frozenset(
                item for item in taints if isinstance(item, ProvenanceTaint)
            ),
        )


def require_atlas_consumer(
    policy: AtlasAccessPolicy,
    consumer: AtlasConsumer,
) -> None:
    """Require one typed consumer without accepting string lookalikes."""

    if not isinstance(policy, AtlasAccessPolicy):
        raise TypeError("policy must be an AtlasAccessPolicy")
    if not isinstance(consumer, AtlasConsumer):
        raise TypeError("consumer must be an AtlasConsumer")
    if consumer not in policy.allowed_consumers:
        raise AtlasConsumerDenied(
            f"{policy.origin_execution_class!r} does not authorize {consumer.value!r}"
        )


def restrict_atlas_access(
    parent: AtlasAccessPolicy,
    *,
    allowed_consumers: Iterable[AtlasConsumer] | None = None,
    provenance_taints: Iterable[ProvenanceTaint] | None = None,
    origin_execution_class: str | None = None,
    claim_ceiling: str | None = None,
    scientific_claim_eligible: bool | None = None,
) -> AtlasAccessPolicy:
    """Create a monotone restriction of ``parent``.

    Consumers may only be removed and taints may only be added.  Origin labels
    and claim ceilings are immutable.  Claim eligibility may be disabled but
    never enabled.
    """

    if not isinstance(parent, AtlasAccessPolicy):
        raise TypeError("parent must be an AtlasAccessPolicy")
    consumers = (
        parent.allowed_consumers
        if allowed_consumers is None
        else frozenset(allowed_consumers)
    )
    taints = (
        parent.provenance_taints
        if provenance_taints is None
        else frozenset(provenance_taints)
    )
    if any(not isinstance(item, AtlasConsumer) for item in consumers):
        raise TypeError("allowed_consumers must contain only AtlasConsumer values")
    if any(not isinstance(item, ProvenanceTaint) for item in taints):
        raise TypeError("provenance_taints must contain only ProvenanceTaint values")
    if not consumers.issubset(parent.allowed_consumers):
        raise ProvenanceEscalationError("derived access policy cannot add consumers")
    if not taints.issuperset(parent.provenance_taints):
        raise ProvenanceEscalationError(
            "derived access policy cannot remove provenance taints"
        )
    requested_origin = (
        parent.origin_execution_class
        if origin_execution_class is None
        else _identifier(
            origin_execution_class,
            label="origin_execution_class",
        )
    )
    if requested_origin != parent.origin_execution_class:
        if (
            ProvenanceTaint.VALUE_DERIVED in parent.provenance_taints
            or ProvenanceTaint.OUTCOME_EXPOSED in parent.provenance_taints
        ):
            raise ProvenanceEscalationError(
                "value-derived provenance cannot be relabelled"
            )
        raise ProvenanceEscalationError(
            "derived access policy cannot relabel its origin"
        )
    requested_ceiling = (
        parent.claim_ceiling
        if claim_ceiling is None
        else _identifier(claim_ceiling, label="claim_ceiling")
    )
    if requested_ceiling != parent.claim_ceiling:
        raise ProvenanceEscalationError(
            "derived access policy cannot change its claim ceiling"
        )
    requested_eligibility = (
        parent.scientific_claim_eligible
        if scientific_claim_eligible is None
        else _plain_bool(
            scientific_claim_eligible,
            label="scientific_claim_eligible",
        )
    )
    if requested_eligibility and not parent.scientific_claim_eligible:
        raise ProvenanceEscalationError(
            "derived access policy cannot gain scientific claim eligibility"
        )
    return AtlasAccessPolicy(
        origin_execution_class=parent.origin_execution_class,
        claim_ceiling=parent.claim_ceiling,
        scientific_claim_eligible=requested_eligibility,
        allowed_consumers=frozenset(consumers),
        provenance_taints=frozenset(taints),
    )


@dataclass(frozen=True, slots=True)
class AttemptPolicy:
    """Explicitly separate retry-like operations that are often conflated."""

    resume_same_attempt_authorized: bool
    reuse_output_authorized: bool
    fresh_replay_same_protocol_authorized: bool
    retry_after_outcome_observation_authorized: bool
    relabel_authorized: bool

    def __post_init__(self) -> None:
        for name in (
            "resume_same_attempt_authorized",
            "reuse_output_authorized",
            "fresh_replay_same_protocol_authorized",
            "retry_after_outcome_observation_authorized",
            "relabel_authorized",
        ):
            _plain_bool(getattr(self, name), label=name)

    def to_dict(self) -> dict[str, object]:
        return {
            "resume_same_attempt_authorized": (self.resume_same_attempt_authorized),
            "reuse_output_authorized": self.reuse_output_authorized,
            "fresh_replay_same_protocol_authorized": (
                self.fresh_replay_same_protocol_authorized
            ),
            "retry_after_outcome_observation_authorized": (
                self.retry_after_outcome_observation_authorized
            ),
            "relabel_authorized": self.relabel_authorized,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> AttemptPolicy:
        item = _mapping(value, label="attempt_policy")
        fields = {
            "resume_same_attempt_authorized",
            "reuse_output_authorized",
            "fresh_replay_same_protocol_authorized",
            "retry_after_outcome_observation_authorized",
            "relabel_authorized",
        }
        _exact_keys(item, fields, label="attempt_policy")
        return cls(
            **{
                name: _plain_bool(
                    item[name],
                    label=f"attempt_policy.{name}",
                )
                for name in fields
            }
        )


@dataclass(frozen=True, slots=True)
class ProtocolIdentity:
    schema_version: str
    protocol_id: str
    source_sha256: str
    canonical_sha256: str

    def __post_init__(self) -> None:
        _identifier(self.schema_version, label="protocol.schema_version")
        _identifier(self.protocol_id, label="protocol.protocol_id")
        _sha256(self.source_sha256, label="protocol.source_sha256")
        _sha256(self.canonical_sha256, label="protocol.canonical_sha256")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "protocol_id": self.protocol_id,
            "source_sha256": self.source_sha256,
            "canonical_sha256": self.canonical_sha256,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> ProtocolIdentity:
        item = _mapping(value, label="protocol")
        fields = {
            "schema_version",
            "protocol_id",
            "source_sha256",
            "canonical_sha256",
        }
        _exact_keys(item, fields, label="protocol")
        return cls(
            schema_version=_identifier(
                item["schema_version"],
                label="protocol.schema_version",
            ),
            protocol_id=_identifier(
                item["protocol_id"],
                label="protocol.protocol_id",
            ),
            source_sha256=_sha256(
                item["source_sha256"],
                label="protocol.source_sha256",
            ),
            canonical_sha256=_sha256(
                item["canonical_sha256"],
                label="protocol.canonical_sha256",
            ),
        )


@dataclass(frozen=True, slots=True)
class ModelIdentity:
    model_id: str
    revision: str
    architecture: str
    files: tuple[tuple[str, str], ...]

    def __post_init__(self) -> None:
        _identifier(self.model_id, label="model.model_id")
        _identifier(self.revision, label="model.revision")
        _identifier(self.architecture, label="model.architecture")
        parsed: list[tuple[str, str]] = []
        for index, pair in enumerate(self.files):
            if (
                not isinstance(pair, tuple)
                or len(pair) != 2
                or not isinstance(pair[0], str)
            ):
                raise AtlasAccessContractError(
                    f"model.files[{index}] must be a name/digest pair"
                )
            parsed.append(
                (
                    _identifier(
                        pair[0],
                        label=f"model.files[{index}].name",
                    ),
                    _sha256(
                        pair[1],
                        label=f"model.files[{index}].sha256",
                    ),
                )
            )
        normalized = tuple(sorted(parsed))
        if not normalized or len({name for name, _ in normalized}) != len(normalized):
            raise AtlasAccessContractError(
                "model.files must be non-empty with unique names"
            )
        object.__setattr__(self, "files", normalized)

    def to_dict(self) -> dict[str, object]:
        return {
            "model_id": self.model_id,
            "revision": self.revision,
            "architecture": self.architecture,
            "files": dict(self.files),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> ModelIdentity:
        item = _mapping(value, label="model")
        _exact_keys(
            item,
            {"model_id", "revision", "architecture", "files"},
            label="model",
        )
        files = _mapping(item["files"], label="model.files")
        if not files:
            raise AtlasAccessContractError("model.files must not be empty")
        return cls(
            model_id=_identifier(item["model_id"], label="model.model_id"),
            revision=_identifier(item["revision"], label="model.revision"),
            architecture=_identifier(item["architecture"], label="model.architecture"),
            files=tuple(
                (
                    _identifier(name, label=f"model.files[{name!r}].name"),
                    _sha256(
                        digest,
                        label=f"model.files[{name!r}].sha256",
                    ),
                )
                for name, digest in files.items()
            ),
        )


@dataclass(frozen=True, slots=True)
class ContextIdentity:
    binding_sha256: str
    context_id: str
    role: str
    claim_eligible: bool

    def __post_init__(self) -> None:
        _sha256(self.binding_sha256, label="context.binding_sha256")
        _identifier(self.context_id, label="context.context_id")
        _identifier(self.role, label="context.role")
        _plain_bool(self.claim_eligible, label="context.claim_eligible")

    def to_dict(self) -> dict[str, object]:
        return {
            "binding_sha256": self.binding_sha256,
            "context_id": self.context_id,
            "role": self.role,
            "claim_eligible": self.claim_eligible,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> ContextIdentity:
        item = _mapping(value, label="context")
        _exact_keys(
            item,
            {"binding_sha256", "context_id", "role", "claim_eligible"},
            label="context",
        )
        return cls(
            binding_sha256=_sha256(
                item["binding_sha256"],
                label="context.binding_sha256",
            ),
            context_id=_identifier(item["context_id"], label="context.context_id"),
            role=_identifier(item["role"], label="context.role"),
            claim_eligible=_plain_bool(
                item["claim_eligible"],
                label="context.claim_eligible",
            ),
        )


@dataclass(frozen=True, slots=True)
class RowDomainIdentity:
    selection_kind: str
    row_count: int
    row_ids_sha256: str

    def __post_init__(self) -> None:
        _identifier(self.selection_kind, label="row_domain.selection_kind")
        _plain_positive_int(self.row_count, label="row_domain.row_count")
        _sha256(self.row_ids_sha256, label="row_domain.row_ids_sha256")

    def to_dict(self) -> dict[str, object]:
        return {
            "selection_kind": self.selection_kind,
            "row_count": self.row_count,
            "row_ids_sha256": self.row_ids_sha256,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> RowDomainIdentity:
        item = _mapping(value, label="row_domain")
        _exact_keys(
            item,
            {"selection_kind", "row_count", "row_ids_sha256"},
            label="row_domain",
        )
        return cls(
            selection_kind=_identifier(
                item["selection_kind"],
                label="row_domain.selection_kind",
            ),
            row_count=_plain_positive_int(
                item["row_count"], label="row_domain.row_count"
            ),
            row_ids_sha256=_sha256(
                item["row_ids_sha256"],
                label="row_domain.row_ids_sha256",
            ),
        )


@dataclass(frozen=True, slots=True)
class CaptureDeclaration:
    output_id: str
    device: str
    dtype: str
    observation_contract: str

    def __post_init__(self) -> None:
        _identifier(self.output_id, label="capture.output_id")
        _identifier(self.device, label="capture.device")
        _identifier(self.dtype, label="capture.dtype")
        _identifier(
            self.observation_contract,
            label="capture.observation_contract",
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "output_id": self.output_id,
            "device": self.device,
            "dtype": self.dtype,
            "observation_contract": self.observation_contract,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> CaptureDeclaration:
        item = _mapping(value, label="capture")
        fields = {"output_id", "device", "dtype", "observation_contract"}
        _exact_keys(item, fields, label="capture")
        return cls(
            output_id=_identifier(item["output_id"], label="capture.output_id"),
            device=_identifier(item["device"], label="capture.device"),
            dtype=_identifier(item["dtype"], label="capture.dtype"),
            observation_contract=_identifier(
                item["observation_contract"],
                label="capture.observation_contract",
            ),
        )


@dataclass(frozen=True, slots=True)
class InterpretationContract:
    language_space_atlas: bool
    semantic_unit: bool
    p1_instrument_consumed: bool
    tokenizer_runtime_verified: bool

    def __post_init__(self) -> None:
        for name in (
            "language_space_atlas",
            "semantic_unit",
            "p1_instrument_consumed",
            "tokenizer_runtime_verified",
        ):
            _plain_bool(
                getattr(self, name),
                label=f"interpretation_contract.{name}",
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "language_space_atlas": self.language_space_atlas,
            "semantic_unit": self.semantic_unit,
            "p1_instrument_consumed": self.p1_instrument_consumed,
            "tokenizer_runtime_verified": self.tokenizer_runtime_verified,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> InterpretationContract:
        item = _mapping(value, label="interpretation_contract")
        fields = {
            "language_space_atlas",
            "semantic_unit",
            "p1_instrument_consumed",
            "tokenizer_runtime_verified",
        }
        _exact_keys(item, fields, label="interpretation_contract")
        return cls(
            **{
                name: _plain_bool(
                    item[name],
                    label=f"interpretation_contract.{name}",
                )
                for name in fields
            }
        )


@dataclass(frozen=True, slots=True)
class AtlasPreparationDescriptor:
    """Canonical pre-observation input to metadata-only preparation."""

    descriptor_id: str
    protocol: ProtocolIdentity
    access_policy: AtlasAccessPolicy
    model: ModelIdentity
    context: ContextIdentity
    row_domain: RowDomainIdentity
    capture: CaptureDeclaration
    attempt_policy: AttemptPolicy
    interpretation_contract: InterpretationContract
    schema_version: str = ATLAS_PREPARATION_DESCRIPTOR_SCHEMA_VERSION
    status: str = "frozen_preobservation"

    def __post_init__(self) -> None:
        _identifier(self.descriptor_id, label="descriptor_id")
        if self.schema_version != (ATLAS_PREPARATION_DESCRIPTOR_SCHEMA_VERSION):
            raise AtlasAccessContractError(
                "unsupported atlas preparation descriptor schema"
            )
        if self.status != "frozen_preobservation":
            raise AtlasAccessContractError(
                "atlas preparation descriptor must be frozen preobservation"
            )
        for name, expected_type in (
            ("protocol", ProtocolIdentity),
            ("access_policy", AtlasAccessPolicy),
            ("model", ModelIdentity),
            ("context", ContextIdentity),
            ("row_domain", RowDomainIdentity),
            ("capture", CaptureDeclaration),
            ("attempt_policy", AttemptPolicy),
            ("interpretation_contract", InterpretationContract),
        ):
            if not isinstance(getattr(self, name), expected_type):
                raise TypeError(f"{name} must be a {expected_type.__name__}")
        if (
            self.context.claim_eligible is False
            and self.access_policy.scientific_claim_eligible
        ):
            raise AtlasAccessContractError(
                "claim-ineligible context cannot produce a claim-eligible "
                "preparation descriptor"
            )
        if (
            self.context.claim_eligible is False
            and ProvenanceTaint.CLAIM_INELIGIBLE_CONTEXT
            not in self.access_policy.provenance_taints
        ):
            raise AtlasAccessContractError(
                "claim-ineligible context must remain an explicit provenance taint"
            )
        if self.attempt_policy.relabel_authorized:
            raise AtlasAccessContractError(
                "preobservation descriptors cannot authorize relabelling"
            )
        if self.access_policy.provenance_taints.intersection(
            {
                ProvenanceTaint.TERMINAL_QUARANTINED,
                ProvenanceTaint.TERMINAL_UNRECEIPTED,
            }
        ):
            raise AtlasAccessContractError(
                "terminally quarantined provenance cannot become a new "
                "preobservation descriptor"
            )
        if (
            ProvenanceTaint.VALUE_DERIVED in self.access_policy.provenance_taints
            or ProvenanceTaint.OUTCOME_EXPOSED in self.access_policy.provenance_taints
        ) and self.attempt_policy.retry_after_outcome_observation_authorized:
            raise AtlasAccessContractError(
                "value-derived provenance cannot authorize an observed outcome retry"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "descriptor_id": self.descriptor_id,
            "status": self.status,
            "protocol": self.protocol.to_dict(),
            "access_policy": self.access_policy.to_dict(),
            "model": self.model.to_dict(),
            "context": self.context.to_dict(),
            "row_domain": self.row_domain.to_dict(),
            "capture": self.capture.to_dict(),
            "attempt_policy": self.attempt_policy.to_dict(),
            "interpretation_contract": (self.interpretation_contract.to_dict()),
        }

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_dict())

    @property
    def canonical_sha256(self) -> str:
        return canonical_json_sha256(self.to_dict())

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> AtlasPreparationDescriptor:
        item = _mapping(value, label="atlas preparation descriptor")
        fields = {
            "schema_version",
            "descriptor_id",
            "status",
            "protocol",
            "access_policy",
            "model",
            "context",
            "row_domain",
            "capture",
            "attempt_policy",
            "interpretation_contract",
        }
        _exact_keys(item, fields, label="atlas preparation descriptor")
        return cls(
            schema_version=_string(item["schema_version"], label="schema_version"),
            descriptor_id=_identifier(item["descriptor_id"], label="descriptor_id"),
            status=_string(item["status"], label="status"),
            protocol=ProtocolIdentity.from_dict(
                _mapping(item["protocol"], label="protocol")
            ),
            access_policy=AtlasAccessPolicy.from_dict(
                _mapping(item["access_policy"], label="access_policy")
            ),
            model=ModelIdentity.from_dict(_mapping(item["model"], label="model")),
            context=ContextIdentity.from_dict(
                _mapping(item["context"], label="context")
            ),
            row_domain=RowDomainIdentity.from_dict(
                _mapping(item["row_domain"], label="row_domain")
            ),
            capture=CaptureDeclaration.from_dict(
                _mapping(item["capture"], label="capture")
            ),
            attempt_policy=AttemptPolicy.from_dict(
                _mapping(item["attempt_policy"], label="attempt_policy")
            ),
            interpretation_contract=InterpretationContract.from_dict(
                _mapping(
                    item["interpretation_contract"],
                    label="interpretation_contract",
                )
            ),
        )
