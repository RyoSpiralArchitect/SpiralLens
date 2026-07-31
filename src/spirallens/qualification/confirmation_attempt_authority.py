"""Non-authorizing structural inputs for a future D7 launch boundary.

Every value in this module is directly caller-constructible.  Canonical bytes,
content digests, and exact structural joins make malformed or internally
inconsistent input rejectable; they do not authenticate an issuer, observe a
runtime or filesystem, reserve a namespace, invoke a seed supplier, authorize
execution, or mint a reusable capability.

The only loader accepts one bounded byte string and its expected digest.  It
checks that digest before parsing and performs no callbacks or external I/O.
The separate fused path reopens a Git-rooted inventory and joins its declared
live observation surface directly to an exclusive start transition; this
module's caller-constructible records remain non-authorizing.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from pathlib import PurePosixPath
from typing import ClassVar, Protocol, Self

from spirallens.core.canonical import (
    canonical_json_bytes,
    canonical_json_sha256,
    parse_canonical_json,
    sha256_bytes,
)

from . import confirmation_attempt_records as attempt_records

__all__: tuple[str, ...] = ()

MAX_D7_LAUNCH_AUTHORITY_INPUT_BYTES = 2 * 1024 * 1024
MAX_D7_DECLARED_PATH_BYTES = 4096
D7_LAUNCH_AUTHORITY_INPUT_BUNDLE_SCHEMA_VERSION = (
    "spirallens.d7-launch-authority-input-bundle.v0.2"
)
D7_AUTHORITY_ARTIFACT_BINDING_SCHEMA_VERSION = (
    "spirallens.d7-authority-artifact-binding.v0.1"
)
D7_PARENT_SELECTION_SEED_EXCLUSION_SCHEMA_VERSION = (
    "spirallens.d7-parent-selection-seed-exclusion.v0.1"
)
D7_OFFICIAL_SEED_INVENTORY_INPUT_SCHEMA_VERSION = (
    "spirallens.d7-official-seed-inventory-input.v0.1"
)
D7_RUNTIME_SPECIFICATION_INPUT_SCHEMA_VERSION = (
    "spirallens.d7-runtime-specification-input.v0.1"
)
D7_SOURCE_RUNTIME_CLOSURE_INPUT_SCHEMA_VERSION = (
    "spirallens.d7-source-runtime-closure-input.v0.1"
)
D7_FAMILY_ADMISSION_INPUT_SCHEMA_VERSION = "spirallens.d7-family-admission-input.v0.1"
D7_EXECUTION_IDENTITY_INPUT_SCHEMA_VERSION = (
    "spirallens.d7-execution-identity-input.v0.1"
)
D7_PHYSICAL_STORE_LANE_IDENTITY_SCHEMA_VERSION = (
    "spirallens.d7-physical-store-lane-identity.v0.2"
)
D7_REPLAY_TARGET_INPUT_SCHEMA_VERSION = (
    "spirallens.d7-spectral-moment-replay-target.v0.1"
)
D7_FULL_DESIGN_FREEZE_INPUT_SCHEMA_VERSION = (
    "spirallens.d7-full-design-freeze-input.v0.1"
)
D7_LAUNCH_INTENT_INPUT_SCHEMA_VERSION = "spirallens.d7-launch-intent-input.v0.1"
D7_CHRONOLOGY_INPUT_SCHEMA_VERSION = "spirallens.d7-seed-supply-chronology-input.v0.1"
D7_TARGET_ADMISSION_BINDING_SCHEMA_VERSION = (
    "spirallens.d7-target-admission-binding-candidate.v0.1"
)
D7_TARGET_FULL_DESIGN_BINDING_SCHEMA_VERSION = (
    "spirallens.d7-target-full-design-binding-candidate.v0.1"
)
D7_TARGET_SOURCE_RUNTIME_BINDING_SCHEMA_VERSION = (
    "spirallens.d7-target-source-runtime-binding-candidate.v0.1"
)
D7_EXCLUSIVE_SEED_SUPPLY_CLAIM_INPUT_SCHEMA_VERSION = (
    "spirallens.d7-exclusive-seed-supply-claim-input.v0.1"
)
D7_SINGLE_SUPPLIER_INVOCATION_INPUT_SCHEMA_VERSION = (
    "spirallens.d7-single-supplier-invocation-input.v0.1"
)
D7_RECORD_CLAIM_CEILING = "level_0"

D7_DEVELOPMENT_SEED_EXCLUSION_SCHEMA_VERSION = (
    "spirallens.d7-development-seed-exclusion.v0.1"
)
D7_DEVELOPMENT_SEED_EXCLUSION_SHA256 = (
    "20803b40c5fc6903e1d1a64ae41c0eb3dcbb3c4a859d7a482971088346fcb54a"
)
D7_PARENT_PROTOCOL_CANONICAL_SHA256 = (
    "9908bb83bb5ff5642416aa09d9e468e0a9499185cec9305e69a54143f2578bd1"
)
D7_PARENT_PROTOCOL_BYTE_COUNT = 969_147
D7_PARENT_SELECTION_MANIFEST_SHA256 = (
    "d398ef1e962708563b4f9e7ad7b4f3213395ec888b83affda791a387bf2c2ee8"
)
D7_PARENT_SEED_FAMILY_COMMITMENT_SHA256 = (
    "e0bfc362249f98851c0583535884f21ab7aab7c4b429b0b3cc80106db8d4ca31"
)
D7_PARENT_SEED_FAMILY_ID = "d0-d5-f2-cartesian-selection-family-v0-1"
D7_PARENT_PROTOCOL_SCHEMA_VERSION = "spirallens.qualification-protocol.v0.8"
D7_RECORDED_C1_SCHEMA_VERSION = "spirallens.d7-c1-seed-free-source-set.v0.1"
D7_RECORDED_C1_CANONICAL_SHA256 = (
    "b7b3b416738c9d02ed76764e35bb131f6bcc6df2948bff200b51df83aee33a5d"
)
D7_RECORDED_C1_BYTE_COUNT = 539_310
D7_RECORDED_C2_SCHEMA_VERSION = "spirallens.d7-c2-source-closure-receipt.v0.1"
D7_RECORDED_C2_CANONICAL_SHA256 = (
    "d28a87bce5ec80c3388df1e21bccbc052f34beb637ff86f81f4f502d9fdd71a3"
)
D7_RECORDED_C2_BYTE_COUNT = 2_745
D7_PARENT_SELECTION_SEEDS = (
    1_111_097_936_516_803_550,
    6_819_071_872_908_675_098,
)
D7_CONFIRMATION_SEED_SLOT_IDS = (
    "confirmation-seed-slot-00",
    "confirmation-seed-slot-01",
)
D7_EVIDENCE_LANE_BASENAME = "d7-prefix-evidence-only-v0"
D7_AUTHORITATIVE_START_LANE_BASENAME = "d7-authoritative-start-v0"
D7_EVIDENCE_DIRECTORY_BASENAME = "d7-attempt-evidence"
D7_CONFIRMATION_GENERATOR_FAMILY_ID = "spectral-moment-confirmation-grid-v0.1"

_DEVELOPMENT_EXCLUSION_ENTRIES = (
    (11, "spectral generator family-identity development test"),
    (12, "spectral generator family-identity development test"),
    (9001, "spectral confirmation crossed-path development test"),
    (9002, "spectral confirmation full-inventory development test"),
)

_TARGET_AUTHORITY = {
    "confirmation_family_admitted": False,
    "confirmation_values_accessed": False,
    "d7_execution_authorized": False,
    "d7_result_produced": False,
    "d8_execution_authorized": False,
    "integer_output_authorized": False,
    "localized_core_loop_join_established": False,
    "model_access_authorized": False,
    "p0_winner_selected": False,
    "pythia_access_authorized": False,
    "representation_instrument_advanced": False,
    "scientific_claim_eligible": False,
    "semantic_authority": False,
    "subject_access_authorized": False,
    "synthetic_qualified": False,
    "topology_claim_authorized": False,
}

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,191}$")
_SCHEMA_RE = re.compile(r"^spirallens\.[a-z0-9][a-z0-9._-]{0,255}$")
_BASENAME_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,191}$")
_PERSISTENCE_CHRONOLOGY_LEAF_RE = re.compile(
    r"^[0-9a-f]{64}\."
    r"(?:attempt-declaration|launch-authorization|attempt-claim|execution-start)"
    r"(?:\.envelope)?\.json$"
)
_MAX_SIGNED_INT64 = (1 << 63) - 1


class D7AuthorityInputError(ValueError):
    """Raised when caller-supplied authority input is structurally invalid."""


class _CanonicalRecord(Protocol):
    @property
    def canonical_bytes(self) -> bytes: ...

    @property
    def canonical_sha256(self) -> str: ...

    @property
    def byte_count(self) -> int: ...

    def to_dict(self) -> dict[str, object]: ...


class _CanonicalRecordMixin:
    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_dict())  # type: ignore[attr-defined]

    @property
    def canonical_sha256(self) -> str:
        return sha256_bytes(self.canonical_bytes)

    @property
    def byte_count(self) -> int:
        return len(self.canonical_bytes)


def _mapping(value: object, *, label: str) -> dict[str, object]:
    if type(value) is not dict or any(type(key) is not str for key in value):
        raise D7AuthorityInputError(f"{label} must be a string-keyed object")
    return value


def _sequence(value: object, *, label: str) -> list[object]:
    if type(value) is not list:
        raise D7AuthorityInputError(f"{label} must be an array")
    return value


def _exact_keys(
    value: dict[str, object],
    expected: set[str],
    *,
    label: str,
) -> None:
    if set(value) != expected:
        raise D7AuthorityInputError(
            f"{label} fields differ: expected {sorted(expected)}, "
            f"observed {sorted(value)}"
        )


def _string(value: object, *, label: str) -> str:
    if type(value) is not str or not value or value != value.strip():
        raise D7AuthorityInputError(f"{label} must be a non-empty trimmed string")
    return value


def _slug(value: object, *, label: str) -> str:
    text = _string(value, label=label)
    if _SLUG_RE.fullmatch(text) is None:
        raise D7AuthorityInputError(f"{label} must be a portable lowercase slug")
    return text


def _schema(value: object, *, label: str) -> str:
    text = _string(value, label=label)
    if _SCHEMA_RE.fullmatch(text) is None:
        raise D7AuthorityInputError(f"{label} must be a SpiralLens schema id")
    return text


def _sha256(value: object, *, label: str) -> str:
    if type(value) is not str or _SHA256_RE.fullmatch(value) is None:
        raise D7AuthorityInputError(f"{label} must be a lowercase SHA-256")
    return value


def _commit(value: object, *, label: str) -> str:
    if type(value) is not str or _COMMIT_RE.fullmatch(value) is None:
        raise D7AuthorityInputError(f"{label} must be a full Git commit")
    return value


def _plain_int(
    value: object,
    *,
    label: str,
    minimum: int = 0,
    maximum: int = _MAX_SIGNED_INT64,
) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        raise D7AuthorityInputError(
            f"{label} must be a plain integer in [{minimum}, {maximum}]"
        )
    return value


def _false(value: object, *, label: str) -> bool:
    if value is not False:
        raise D7AuthorityInputError(f"{label} must be false")
    return False


def _true(value: object, *, label: str) -> bool:
    if value is not True:
        raise D7AuthorityInputError(f"{label} must be true")
    return True


def _absolute_posix(value: object, *, label: str) -> str:
    text = _string(value, label=label)
    if (
        text.startswith("//")
        or "\x00" in text
        or len(text.encode("utf-8")) > MAX_D7_DECLARED_PATH_BYTES
    ):
        raise D7AuthorityInputError(
            f"{label} contains an unsupported alias, NUL, or overlong path"
        )
    path = PurePosixPath(text)
    if (
        not path.is_absolute()
        or text != path.as_posix()
        or any(part in {"", ".", ".."} for part in path.parts)
    ):
        raise D7AuthorityInputError(f"{label} must be a normalized absolute POSIX path")
    return text


def _is_descendant(path: str, parent: str) -> bool:
    return PurePosixPath(parent) in PurePosixPath(path).parents


def _paths_overlap(left: str, right: str) -> bool:
    return (
        left == right
        or PurePosixPath(left) in PurePosixPath(right).parents
        or PurePosixPath(right) in PurePosixPath(left).parents
    )


def _reserved_persistence_paths(
    store_path: str,
    attempt_key_sha256: str,
) -> tuple[str, ...]:
    store = PurePosixPath(store_path)
    return (
        (store / D7_EVIDENCE_LANE_BASENAME).as_posix(),
        (store / D7_AUTHORITATIVE_START_LANE_BASENAME).as_posix(),
        (store / D7_EVIDENCE_DIRECTORY_BASENAME).as_posix(),
        (store / f"{attempt_key_sha256}.attempt-declaration.envelope.json").as_posix(),
        (store / f"{attempt_key_sha256}.launch-authorization.envelope.json").as_posix(),
        (store / f"{attempt_key_sha256}.attempt-claim.envelope.json").as_posix(),
        (store / f"{attempt_key_sha256}.execution-start.envelope.json").as_posix(),
    )


def _require_record_binding(
    binding: "D7AuthorityArtifactBinding",
    record: _CanonicalRecord,
    *,
    role: str,
    contract_id: str,
    label: str,
) -> None:
    if (
        binding.artifact_role != role
        or binding.artifact_contract_id != contract_id
        or binding.canonical_sha256 != record.canonical_sha256
        or binding.byte_count != record.byte_count
    ):
        raise D7AuthorityInputError(f"{label} does not bind the exact record")


@dataclass(frozen=True, slots=True)
class D7AuthorityArtifactBinding:
    artifact_role: str
    artifact_contract_id: str
    canonical_sha256: str
    byte_count: int

    schema_version: ClassVar[str] = D7_AUTHORITY_ARTIFACT_BINDING_SCHEMA_VERSION

    def __post_init__(self) -> None:
        _slug(self.artifact_role, label="artifact_role")
        _schema(self.artifact_contract_id, label="artifact_contract_id")
        _sha256(self.canonical_sha256, label="canonical_sha256")
        _plain_int(self.byte_count, label="byte_count", minimum=1)

    @classmethod
    def from_record(
        cls,
        *,
        artifact_role: str,
        artifact_contract_id: str,
        record: _CanonicalRecord,
    ) -> Self:
        if not isinstance(record.canonical_bytes, bytes):
            raise TypeError("record must expose canonical bytes")
        return cls(
            artifact_role=artifact_role,
            artifact_contract_id=artifact_contract_id,
            canonical_sha256=record.canonical_sha256,
            byte_count=record.byte_count,
        )

    @classmethod
    def from_dict(cls, value: object) -> Self:
        item = _mapping(value, label="artifact binding")
        _exact_keys(
            item,
            {
                "schema_version",
                "artifact_role",
                "artifact_contract_id",
                "canonical_sha256",
                "byte_count",
                "authoritative_source_loaded",
                "identity_authenticated",
            },
            label="artifact binding",
        )
        if item["schema_version"] != cls.schema_version:
            raise D7AuthorityInputError("artifact binding schema differs")
        _false(
            item["authoritative_source_loaded"],
            label="authoritative_source_loaded",
        )
        _false(
            item["identity_authenticated"],
            label="identity_authenticated",
        )
        return cls(
            artifact_role=_slug(item["artifact_role"], label="artifact_role"),
            artifact_contract_id=_schema(
                item["artifact_contract_id"],
                label="artifact_contract_id",
            ),
            canonical_sha256=_sha256(
                item["canonical_sha256"],
                label="canonical_sha256",
            ),
            byte_count=_plain_int(
                item["byte_count"],
                label="byte_count",
                minimum=1,
            ),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "artifact_role": self.artifact_role,
            "artifact_contract_id": self.artifact_contract_id,
            "canonical_sha256": self.canonical_sha256,
            "byte_count": self.byte_count,
            "authoritative_source_loaded": False,
            "identity_authenticated": False,
        }


@dataclass(frozen=True, slots=True)
class D7TargetAdmissionBindingCandidate:
    receipt_binding: D7AuthorityArtifactBinding
    generator_family_id: str
    construction_review_binding: D7AuthorityArtifactBinding
    admission_spec_binding: D7AuthorityArtifactBinding
    source_runtime_receipt_sha256: str

    schema_version: ClassVar[str] = D7_TARGET_ADMISSION_BINDING_SCHEMA_VERSION

    def __post_init__(self) -> None:
        bindings = (
            self.receipt_binding,
            self.construction_review_binding,
            self.admission_spec_binding,
        )
        if any(
            not isinstance(binding, D7AuthorityArtifactBinding) for binding in bindings
        ):
            raise TypeError("target admission bindings must be artifact bindings")
        if tuple(binding.artifact_role for binding in bindings) != (
            "family-admission-receipt",
            "construction-review",
            "admission-spec",
        ):
            raise D7AuthorityInputError("target admission binding roles differ")
        if (
            _slug(self.generator_family_id, label="generator_family_id")
            != D7_CONFIRMATION_GENERATOR_FAMILY_ID
        ):
            raise D7AuthorityInputError(
                "target admission family differs from spectral confirmation"
            )
        _sha256(
            self.source_runtime_receipt_sha256,
            label="source_runtime_receipt_sha256",
        )

    @property
    def construction_review_sha256(self) -> str:
        return self.construction_review_binding.canonical_sha256

    @property
    def admission_spec_sha256(self) -> str:
        return self.admission_spec_binding.canonical_sha256

    @classmethod
    def from_dict(cls, value: object) -> Self:
        item = _mapping(value, label="target admission binding candidate")
        _exact_keys(
            item,
            {
                "schema_version",
                "receipt_binding",
                "generator_family_id",
                "construction_review_binding",
                "construction_review_sha256",
                "admission_spec_binding",
                "admission_spec_sha256",
                "source_runtime_receipt_sha256",
                "caller_claimed_family_admitted",
                "identity_authenticated",
            },
            label="target admission binding candidate",
        )
        if item["schema_version"] != cls.schema_version:
            raise D7AuthorityInputError("target admission binding schema differs")
        _true(
            item["caller_claimed_family_admitted"],
            label="caller_claimed_family_admitted",
        )
        _false(
            item["identity_authenticated"],
            label="identity_authenticated",
        )
        result = cls(
            receipt_binding=D7AuthorityArtifactBinding.from_dict(
                item["receipt_binding"]
            ),
            generator_family_id=_slug(
                item["generator_family_id"],
                label="generator_family_id",
            ),
            construction_review_binding=D7AuthorityArtifactBinding.from_dict(
                item["construction_review_binding"]
            ),
            admission_spec_binding=D7AuthorityArtifactBinding.from_dict(
                item["admission_spec_binding"]
            ),
            source_runtime_receipt_sha256=_sha256(
                item["source_runtime_receipt_sha256"],
                label="source_runtime_receipt_sha256",
            ),
        )
        if (
            _sha256(
                item["construction_review_sha256"],
                label="construction_review_sha256",
            )
            != result.construction_review_sha256
            or _sha256(
                item["admission_spec_sha256"],
                label="admission_spec_sha256",
            )
            != result.admission_spec_sha256
        ):
            raise D7AuthorityInputError(
                "target admission semantic digest differs from its full binding"
            )
        return result

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "receipt_binding": self.receipt_binding.to_dict(),
            "generator_family_id": self.generator_family_id,
            "construction_review_binding": (self.construction_review_binding.to_dict()),
            "construction_review_sha256": self.construction_review_sha256,
            "admission_spec_binding": self.admission_spec_binding.to_dict(),
            "admission_spec_sha256": self.admission_spec_sha256,
            "source_runtime_receipt_sha256": (self.source_runtime_receipt_sha256),
            "caller_claimed_family_admitted": True,
            "identity_authenticated": False,
        }


@dataclass(frozen=True, slots=True)
class D7TargetSourceRuntimeBindingCandidate:
    receipt_binding: D7AuthorityArtifactBinding
    runtime_specification_sha256: str

    schema_version: ClassVar[str] = D7_TARGET_SOURCE_RUNTIME_BINDING_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not isinstance(self.receipt_binding, D7AuthorityArtifactBinding):
            raise TypeError("receipt_binding must be D7AuthorityArtifactBinding")
        if self.receipt_binding.artifact_role != "execution-source-runtime-receipt":
            raise D7AuthorityInputError("source/runtime receipt role differs")
        _sha256(
            self.runtime_specification_sha256,
            label="runtime_specification_sha256",
        )

    @property
    def receipt_sha256(self) -> str:
        return self.receipt_binding.canonical_sha256

    @classmethod
    def from_dict(cls, value: object) -> Self:
        item = _mapping(value, label="target source/runtime binding candidate")
        _exact_keys(
            item,
            {
                "schema_version",
                "receipt_binding",
                "receipt_sha256",
                "runtime_specification_sha256",
                "caller_claimed_exact_closure",
                "identity_authenticated",
            },
            label="target source/runtime binding candidate",
        )
        if item["schema_version"] != cls.schema_version:
            raise D7AuthorityInputError("target source/runtime binding schema differs")
        _true(
            item["caller_claimed_exact_closure"],
            label="caller_claimed_exact_closure",
        )
        _false(
            item["identity_authenticated"],
            label="identity_authenticated",
        )
        result = cls(
            receipt_binding=D7AuthorityArtifactBinding.from_dict(
                item["receipt_binding"]
            ),
            runtime_specification_sha256=_sha256(
                item["runtime_specification_sha256"],
                label="runtime_specification_sha256",
            ),
        )
        if (
            _sha256(item["receipt_sha256"], label="receipt_sha256")
            != result.receipt_sha256
        ):
            raise D7AuthorityInputError("target source/runtime receipt digest differs")
        return result

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "receipt_binding": self.receipt_binding.to_dict(),
            "receipt_sha256": self.receipt_sha256,
            "runtime_specification_sha256": (self.runtime_specification_sha256),
            "caller_claimed_exact_closure": True,
            "identity_authenticated": False,
        }


@dataclass(frozen=True, slots=True)
class D7TargetFullDesignBindingCandidate:
    design_binding: D7AuthorityArtifactBinding
    inventory_binding: D7AuthorityArtifactBinding
    inventory_sha256: str
    official_seed_inventory_sha256: str
    implementation_registry_sha256: str
    aggregation_sha256: str
    result_payload_schema_sha256: str

    schema_version: ClassVar[str] = D7_TARGET_FULL_DESIGN_BINDING_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not isinstance(self.design_binding, D7AuthorityArtifactBinding):
            raise TypeError("design_binding must be D7AuthorityArtifactBinding")
        if self.design_binding.artifact_role != "full-design":
            raise D7AuthorityInputError("full-design role differs")
        if not isinstance(self.inventory_binding, D7AuthorityArtifactBinding):
            raise TypeError("inventory_binding must be D7AuthorityArtifactBinding")
        if self.inventory_binding.artifact_role != "full-inventory":
            raise D7AuthorityInputError("full-inventory role differs")
        for name in (
            "inventory_sha256",
            "official_seed_inventory_sha256",
            "implementation_registry_sha256",
            "aggregation_sha256",
            "result_payload_schema_sha256",
        ):
            _sha256(getattr(self, name), label=name)
        if self.inventory_sha256 != self.inventory_binding.canonical_sha256:
            raise D7AuthorityInputError(
                "full-design inventory digest differs from inventory binding"
            )

    @property
    def canonical_sha256(self) -> str:
        return self.design_binding.canonical_sha256

    @classmethod
    def from_dict(cls, value: object) -> Self:
        item = _mapping(value, label="target full-design binding candidate")
        _exact_keys(
            item,
            {
                "schema_version",
                "design_binding",
                "inventory_binding",
                "canonical_sha256",
                "inventory_sha256",
                "official_seed_inventory_sha256",
                "implementation_registry_sha256",
                "aggregation_sha256",
                "result_payload_schema_sha256",
                "caller_claimed_exact_design",
                "identity_authenticated",
            },
            label="target full-design binding candidate",
        )
        if item["schema_version"] != cls.schema_version:
            raise D7AuthorityInputError("target full-design binding schema differs")
        _true(
            item["caller_claimed_exact_design"],
            label="caller_claimed_exact_design",
        )
        _false(
            item["identity_authenticated"],
            label="identity_authenticated",
        )
        result = cls(
            design_binding=D7AuthorityArtifactBinding.from_dict(item["design_binding"]),
            inventory_binding=D7AuthorityArtifactBinding.from_dict(
                item["inventory_binding"]
            ),
            inventory_sha256=_sha256(
                item["inventory_sha256"],
                label="inventory_sha256",
            ),
            official_seed_inventory_sha256=_sha256(
                item["official_seed_inventory_sha256"],
                label="official_seed_inventory_sha256",
            ),
            implementation_registry_sha256=_sha256(
                item["implementation_registry_sha256"],
                label="implementation_registry_sha256",
            ),
            aggregation_sha256=_sha256(
                item["aggregation_sha256"],
                label="aggregation_sha256",
            ),
            result_payload_schema_sha256=_sha256(
                item["result_payload_schema_sha256"],
                label="result_payload_schema_sha256",
            ),
        )
        if (
            _sha256(item["canonical_sha256"], label="canonical_sha256")
            != result.canonical_sha256
        ):
            raise D7AuthorityInputError("target full-design canonical digest differs")
        return result

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "design_binding": self.design_binding.to_dict(),
            "inventory_binding": self.inventory_binding.to_dict(),
            "canonical_sha256": self.canonical_sha256,
            "inventory_sha256": self.inventory_sha256,
            "official_seed_inventory_sha256": (self.official_seed_inventory_sha256),
            "implementation_registry_sha256": (self.implementation_registry_sha256),
            "aggregation_sha256": self.aggregation_sha256,
            "result_payload_schema_sha256": (self.result_payload_schema_sha256),
            "caller_claimed_exact_design": True,
            "identity_authenticated": False,
        }


@dataclass(frozen=True, slots=True)
class D7ExcludedSeed:
    seed: int
    reason: str

    def __post_init__(self) -> None:
        _plain_int(self.seed, label="excluded seed")
        _string(self.reason, label="excluded seed reason")

    @classmethod
    def from_dict(cls, value: object) -> Self:
        item = _mapping(value, label="excluded seed")
        _exact_keys(item, {"seed", "reason"}, label="excluded seed")
        return cls(
            seed=_plain_int(item["seed"], label="excluded seed"),
            reason=_string(item["reason"], label="excluded seed reason"),
        )

    def to_dict(self) -> dict[str, object]:
        return {"seed": self.seed, "reason": self.reason}


@dataclass(frozen=True, slots=True)
class D7DevelopmentSeedExclusionRegistryRecord(_CanonicalRecordMixin):
    entries: tuple[D7ExcludedSeed, ...]

    schema_version: ClassVar[str] = D7_DEVELOPMENT_SEED_EXCLUSION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if type(self.entries) is not tuple or self.entries != tuple(
            D7ExcludedSeed(seed=seed, reason=reason)
            for seed, reason in _DEVELOPMENT_EXCLUSION_ENTRIES
        ):
            raise D7AuthorityInputError(
                "development exclusion registry must equal the exact frozen body"
            )
        if canonical_json_sha256(self.to_dict()) != (
            D7_DEVELOPMENT_SEED_EXCLUSION_SHA256
        ):
            raise D7AuthorityInputError("development exclusion registry digest differs")

    @classmethod
    def exact(cls) -> Self:
        return cls(
            entries=tuple(
                D7ExcludedSeed(seed=seed, reason=reason)
                for seed, reason in _DEVELOPMENT_EXCLUSION_ENTRIES
            )
        )

    @classmethod
    def from_dict(cls, value: object) -> Self:
        item = _mapping(value, label="development exclusion registry")
        _exact_keys(
            item,
            {"schema_version", "entries"},
            label="development exclusion registry",
        )
        if item["schema_version"] != cls.schema_version:
            raise D7AuthorityInputError("development exclusion registry schema differs")
        return cls(
            entries=tuple(
                D7ExcludedSeed.from_dict(entry)
                for entry in _sequence(
                    item["entries"],
                    label="development exclusion entries",
                )
            )
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "entries": [entry.to_dict() for entry in self.entries],
        }


@dataclass(frozen=True, slots=True)
class D7ParentSelectionSeedExclusionRegistryRecord(_CanonicalRecordMixin):
    parent_protocol_binding: D7AuthorityArtifactBinding
    selection_manifest_sha256: str
    seed_family_commitment_sha256: str
    seed_family_id: str
    entries: tuple[D7ExcludedSeed, ...]

    schema_version: ClassVar[str] = D7_PARENT_SELECTION_SEED_EXCLUSION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        binding = self.parent_protocol_binding
        if not isinstance(binding, D7AuthorityArtifactBinding):
            raise TypeError(
                "parent_protocol_binding must be D7AuthorityArtifactBinding"
            )
        if (
            binding.artifact_role != "parent-selection-protocol"
            or binding.artifact_contract_id != D7_PARENT_PROTOCOL_SCHEMA_VERSION
            or binding.canonical_sha256 != D7_PARENT_PROTOCOL_CANONICAL_SHA256
            or binding.byte_count != D7_PARENT_PROTOCOL_BYTE_COUNT
        ):
            raise D7AuthorityInputError(
                "parent protocol binding differs from the exact frozen protocol"
            )
        if (
            _sha256(
                self.selection_manifest_sha256,
                label="selection_manifest_sha256",
            )
            != D7_PARENT_SELECTION_MANIFEST_SHA256
            or _sha256(
                self.seed_family_commitment_sha256,
                label="seed_family_commitment_sha256",
            )
            != D7_PARENT_SEED_FAMILY_COMMITMENT_SHA256
            or _slug(self.seed_family_id, label="seed_family_id")
            != D7_PARENT_SEED_FAMILY_ID
        ):
            raise D7AuthorityInputError(
                "parent selection identity differs from the frozen selection"
            )
        expected = tuple(
            D7ExcludedSeed(
                seed=seed,
                reason="frozen parent D0-D5 selection seed",
            )
            for seed in D7_PARENT_SELECTION_SEEDS
        )
        if type(self.entries) is not tuple or self.entries != expected:
            raise D7AuthorityInputError(
                "parent selection exclusions must equal both exact parent seeds"
            )

    @classmethod
    def exact(cls) -> Self:
        return cls(
            parent_protocol_binding=D7AuthorityArtifactBinding(
                artifact_role="parent-selection-protocol",
                artifact_contract_id=D7_PARENT_PROTOCOL_SCHEMA_VERSION,
                canonical_sha256=D7_PARENT_PROTOCOL_CANONICAL_SHA256,
                byte_count=D7_PARENT_PROTOCOL_BYTE_COUNT,
            ),
            selection_manifest_sha256=D7_PARENT_SELECTION_MANIFEST_SHA256,
            seed_family_commitment_sha256=(D7_PARENT_SEED_FAMILY_COMMITMENT_SHA256),
            seed_family_id=D7_PARENT_SEED_FAMILY_ID,
            entries=tuple(
                D7ExcludedSeed(
                    seed=seed,
                    reason="frozen parent D0-D5 selection seed",
                )
                for seed in D7_PARENT_SELECTION_SEEDS
            ),
        )

    @classmethod
    def from_dict(cls, value: object) -> Self:
        item = _mapping(value, label="parent selection exclusion registry")
        _exact_keys(
            item,
            {
                "schema_version",
                "parent_protocol_binding",
                "selection_manifest_sha256",
                "seed_family_commitment_sha256",
                "seed_family_id",
                "entries",
            },
            label="parent selection exclusion registry",
        )
        if item["schema_version"] != cls.schema_version:
            raise D7AuthorityInputError(
                "parent selection exclusion registry schema differs"
            )
        return cls(
            parent_protocol_binding=D7AuthorityArtifactBinding.from_dict(
                item["parent_protocol_binding"]
            ),
            selection_manifest_sha256=_sha256(
                item["selection_manifest_sha256"],
                label="selection_manifest_sha256",
            ),
            seed_family_commitment_sha256=_sha256(
                item["seed_family_commitment_sha256"],
                label="seed_family_commitment_sha256",
            ),
            seed_family_id=_slug(
                item["seed_family_id"],
                label="seed_family_id",
            ),
            entries=tuple(
                D7ExcludedSeed.from_dict(entry)
                for entry in _sequence(
                    item["entries"],
                    label="parent selection exclusion entries",
                )
            ),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "parent_protocol_binding": self.parent_protocol_binding.to_dict(),
            "selection_manifest_sha256": self.selection_manifest_sha256,
            "seed_family_commitment_sha256": (self.seed_family_commitment_sha256),
            "seed_family_id": self.seed_family_id,
            "entries": [entry.to_dict() for entry in self.entries],
        }


@dataclass(frozen=True, slots=True)
class D7OfficialSeed:
    seed_slot_id: str
    seed: int

    def __post_init__(self) -> None:
        _slug(self.seed_slot_id, label="seed_slot_id")
        _plain_int(self.seed, label="official seed")

    @classmethod
    def from_dict(cls, value: object) -> Self:
        item = _mapping(value, label="official seed")
        _exact_keys(item, {"seed_slot_id", "seed"}, label="official seed")
        return cls(
            seed_slot_id=_slug(item["seed_slot_id"], label="seed_slot_id"),
            seed=_plain_int(item["seed"], label="official seed"),
        )

    def to_dict(self) -> dict[str, object]:
        return {"seed_slot_id": self.seed_slot_id, "seed": self.seed}


@dataclass(frozen=True, slots=True)
class D7OfficialSeedInventoryRecord(_CanonicalRecordMixin):
    inventory_id: str
    development_exclusion_registry_binding: D7AuthorityArtifactBinding
    parent_selection_exclusion_registry_binding: D7AuthorityArtifactBinding
    seeds: tuple[D7OfficialSeed, ...]

    schema_version: ClassVar[str] = D7_OFFICIAL_SEED_INVENTORY_INPUT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        _slug(self.inventory_id, label="inventory_id")
        for name, binding in (
            (
                "development_exclusion_registry_binding",
                self.development_exclusion_registry_binding,
            ),
            (
                "parent_selection_exclusion_registry_binding",
                self.parent_selection_exclusion_registry_binding,
            ),
        ):
            if not isinstance(binding, D7AuthorityArtifactBinding):
                raise TypeError(f"{name} must be D7AuthorityArtifactBinding")
        if type(self.seeds) is not tuple or len(self.seeds) != 2:
            raise D7AuthorityInputError(
                "official seed inventory must contain exactly two seeds"
            )
        observed_slots = tuple(item.seed_slot_id for item in self.seeds)
        observed_seeds = tuple(item.seed for item in self.seeds)
        if observed_slots != D7_CONFIRMATION_SEED_SLOT_IDS:
            raise D7AuthorityInputError(
                "official seed slots differ from the frozen ordinal mapping"
            )
        if observed_seeds != tuple(sorted(set(observed_seeds))):
            raise D7AuthorityInputError(
                "official seeds must be unique and canonically sorted"
            )
        excluded = {
            *(seed for seed, _reason in _DEVELOPMENT_EXCLUSION_ENTRIES),
            *D7_PARENT_SELECTION_SEEDS,
        }
        if excluded.intersection(observed_seeds):
            raise D7AuthorityInputError(
                "official seeds overlap development or parent selection seeds"
            )

    @classmethod
    def from_dict(cls, value: object) -> Self:
        item = _mapping(value, label="official seed inventory")
        _exact_keys(
            item,
            {
                "schema_version",
                "inventory_id",
                "development_exclusion_registry_binding",
                "parent_selection_exclusion_registry_binding",
                "seeds",
                "unseen_status",
                "seed_inventory_frozen",
                "supplier_chronology_verified",
                "cryptographic_unseen_proof",
            },
            label="official seed inventory",
        )
        if item["schema_version"] != cls.schema_version:
            raise D7AuthorityInputError("official seed inventory schema differs")
        _false(
            item["supplier_chronology_verified"],
            label="supplier_chronology_verified",
        )
        _false(
            item["cryptographic_unseen_proof"],
            label="cryptographic_unseen_proof",
        )
        if item["unseen_status"] != "external-attestation-required":
            raise D7AuthorityInputError(
                "official seed unseen status must require external attestation"
            )
        _false(
            item["seed_inventory_frozen"],
            label="seed_inventory_frozen",
        )
        return cls(
            inventory_id=_slug(item["inventory_id"], label="inventory_id"),
            development_exclusion_registry_binding=(
                D7AuthorityArtifactBinding.from_dict(
                    item["development_exclusion_registry_binding"]
                )
            ),
            parent_selection_exclusion_registry_binding=(
                D7AuthorityArtifactBinding.from_dict(
                    item["parent_selection_exclusion_registry_binding"]
                )
            ),
            seeds=tuple(
                D7OfficialSeed.from_dict(entry)
                for entry in _sequence(item["seeds"], label="official seeds")
            ),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "inventory_id": self.inventory_id,
            "development_exclusion_registry_binding": (
                self.development_exclusion_registry_binding.to_dict()
            ),
            "parent_selection_exclusion_registry_binding": (
                self.parent_selection_exclusion_registry_binding.to_dict()
            ),
            "seeds": [seed.to_dict() for seed in self.seeds],
            "unseen_status": "external-attestation-required",
            "seed_inventory_frozen": False,
            "supplier_chronology_verified": False,
            "cryptographic_unseen_proof": False,
        }


@dataclass(frozen=True, slots=True)
class D7RuntimeSpecificationInputRecord(_CanonicalRecordMixin):
    runtime_specification_id: str
    python_implementation: str
    python_version: str
    platform: str
    machine: str
    dependency_lock_sha256: str
    native_runtime_sha256: str

    schema_version: ClassVar[str] = D7_RUNTIME_SPECIFICATION_INPUT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        _slug(self.runtime_specification_id, label="runtime_specification_id")
        _slug(self.python_implementation, label="python_implementation")
        _string(self.python_version, label="python_version")
        _slug(self.platform, label="platform")
        _slug(self.machine, label="machine")
        _sha256(self.dependency_lock_sha256, label="dependency_lock_sha256")
        _sha256(self.native_runtime_sha256, label="native_runtime_sha256")

    @classmethod
    def from_dict(cls, value: object) -> Self:
        item = _mapping(value, label="runtime specification input")
        _exact_keys(
            item,
            {
                "schema_version",
                "runtime_specification_id",
                "python_implementation",
                "python_version",
                "platform",
                "machine",
                "dependency_lock_sha256",
                "native_runtime_sha256",
                "runtime_attested",
            },
            label="runtime specification input",
        )
        if item["schema_version"] != cls.schema_version:
            raise D7AuthorityInputError("runtime specification schema differs")
        _false(item["runtime_attested"], label="runtime_attested")
        return cls(
            runtime_specification_id=_slug(
                item["runtime_specification_id"],
                label="runtime_specification_id",
            ),
            python_implementation=_slug(
                item["python_implementation"],
                label="python_implementation",
            ),
            python_version=_string(
                item["python_version"],
                label="python_version",
            ),
            platform=_slug(item["platform"], label="platform"),
            machine=_slug(item["machine"], label="machine"),
            dependency_lock_sha256=_sha256(
                item["dependency_lock_sha256"],
                label="dependency_lock_sha256",
            ),
            native_runtime_sha256=_sha256(
                item["native_runtime_sha256"],
                label="native_runtime_sha256",
            ),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "runtime_specification_id": self.runtime_specification_id,
            "python_implementation": self.python_implementation,
            "python_version": self.python_version,
            "platform": self.platform,
            "machine": self.machine,
            "dependency_lock_sha256": self.dependency_lock_sha256,
            "native_runtime_sha256": self.native_runtime_sha256,
            "runtime_attested": False,
        }


@dataclass(frozen=True, slots=True)
class D7SourceRuntimeClosureInputRecord(_CanonicalRecordMixin):
    closure_id: str
    receipt_binding: D7AuthorityArtifactBinding
    final_code_review_binding: D7AuthorityArtifactBinding
    runtime_specification_binding: D7AuthorityArtifactBinding
    source_commit: str
    source_tree_sha256: str
    transitive_dependency_set_sha256: str

    schema_version: ClassVar[str] = D7_SOURCE_RUNTIME_CLOSURE_INPUT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        _slug(self.closure_id, label="closure_id")
        for name, binding in (
            ("receipt_binding", self.receipt_binding),
            ("final_code_review_binding", self.final_code_review_binding),
            (
                "runtime_specification_binding",
                self.runtime_specification_binding,
            ),
        ):
            if not isinstance(binding, D7AuthorityArtifactBinding):
                raise TypeError(f"{name} must be D7AuthorityArtifactBinding")
        if self.receipt_binding.artifact_role != ("execution-source-runtime-receipt"):
            raise D7AuthorityInputError("source/runtime receipt binding role differs")
        _commit(self.source_commit, label="source_commit")
        _sha256(self.source_tree_sha256, label="source_tree_sha256")
        _sha256(
            self.transitive_dependency_set_sha256,
            label="transitive_dependency_set_sha256",
        )

    @classmethod
    def from_dict(cls, value: object) -> Self:
        item = _mapping(value, label="source/runtime closure input")
        _exact_keys(
            item,
            {
                "schema_version",
                "closure_id",
                "receipt_binding",
                "final_code_review_binding",
                "runtime_specification_binding",
                "source_commit",
                "source_tree_sha256",
                "transitive_dependency_set_sha256",
                "closure_verified",
            },
            label="source/runtime closure input",
        )
        if item["schema_version"] != cls.schema_version:
            raise D7AuthorityInputError("source/runtime closure schema differs")
        _false(item["closure_verified"], label="closure_verified")
        return cls(
            closure_id=_slug(item["closure_id"], label="closure_id"),
            receipt_binding=D7AuthorityArtifactBinding.from_dict(
                item["receipt_binding"]
            ),
            final_code_review_binding=D7AuthorityArtifactBinding.from_dict(
                item["final_code_review_binding"]
            ),
            runtime_specification_binding=(
                D7AuthorityArtifactBinding.from_dict(
                    item["runtime_specification_binding"]
                )
            ),
            source_commit=_commit(item["source_commit"], label="source_commit"),
            source_tree_sha256=_sha256(
                item["source_tree_sha256"],
                label="source_tree_sha256",
            ),
            transitive_dependency_set_sha256=_sha256(
                item["transitive_dependency_set_sha256"],
                label="transitive_dependency_set_sha256",
            ),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "closure_id": self.closure_id,
            "receipt_binding": self.receipt_binding.to_dict(),
            "final_code_review_binding": self.final_code_review_binding.to_dict(),
            "runtime_specification_binding": (
                self.runtime_specification_binding.to_dict()
            ),
            "source_commit": self.source_commit,
            "source_tree_sha256": self.source_tree_sha256,
            "transitive_dependency_set_sha256": (self.transitive_dependency_set_sha256),
            "closure_verified": False,
        }


@dataclass(frozen=True, slots=True)
class D7FamilyAdmissionInputRecord(_CanonicalRecordMixin):
    admission_id: str
    generator_family_id: str
    admission_receipt_binding: D7AuthorityArtifactBinding
    source_runtime_closure_binding: D7AuthorityArtifactBinding
    seed_free_readiness_binding: D7AuthorityArtifactBinding
    construction_review_binding: D7AuthorityArtifactBinding
    admission_spec_binding: D7AuthorityArtifactBinding

    schema_version: ClassVar[str] = D7_FAMILY_ADMISSION_INPUT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        _slug(self.admission_id, label="admission_id")
        if (
            _slug(self.generator_family_id, label="generator_family_id")
            != D7_CONFIRMATION_GENERATOR_FAMILY_ID
        ):
            raise D7AuthorityInputError(
                "admission family differs from spectral confirmation"
            )
        for name, binding in (
            ("admission_receipt_binding", self.admission_receipt_binding),
            (
                "source_runtime_closure_binding",
                self.source_runtime_closure_binding,
            ),
            ("seed_free_readiness_binding", self.seed_free_readiness_binding),
            ("construction_review_binding", self.construction_review_binding),
            ("admission_spec_binding", self.admission_spec_binding),
        ):
            if not isinstance(binding, D7AuthorityArtifactBinding):
                raise TypeError(f"{name} must be D7AuthorityArtifactBinding")
        if tuple(
            binding.artifact_role
            for binding in (
                self.admission_receipt_binding,
                self.source_runtime_closure_binding,
                self.seed_free_readiness_binding,
                self.construction_review_binding,
                self.admission_spec_binding,
            )
        ) != (
            "family-admission-receipt",
            "execution-source-runtime-closure",
            "seed-free-readiness",
            "construction-review",
            "admission-spec",
        ):
            raise D7AuthorityInputError("family admission binding roles differ")

    @classmethod
    def from_dict(cls, value: object) -> Self:
        item = _mapping(value, label="family admission input")
        _exact_keys(
            item,
            {
                "schema_version",
                "admission_id",
                "generator_family_id",
                "admission_receipt_binding",
                "source_runtime_closure_binding",
                "seed_free_readiness_binding",
                "construction_review_binding",
                "admission_spec_binding",
                "family_admitted",
            },
            label="family admission input",
        )
        if item["schema_version"] != cls.schema_version:
            raise D7AuthorityInputError("family admission schema differs")
        _false(item["family_admitted"], label="family_admitted")
        return cls(
            admission_id=_slug(item["admission_id"], label="admission_id"),
            generator_family_id=_slug(
                item["generator_family_id"],
                label="generator_family_id",
            ),
            admission_receipt_binding=D7AuthorityArtifactBinding.from_dict(
                item["admission_receipt_binding"]
            ),
            source_runtime_closure_binding=(
                D7AuthorityArtifactBinding.from_dict(
                    item["source_runtime_closure_binding"]
                )
            ),
            seed_free_readiness_binding=(
                D7AuthorityArtifactBinding.from_dict(
                    item["seed_free_readiness_binding"]
                )
            ),
            construction_review_binding=(
                D7AuthorityArtifactBinding.from_dict(
                    item["construction_review_binding"]
                )
            ),
            admission_spec_binding=D7AuthorityArtifactBinding.from_dict(
                item["admission_spec_binding"]
            ),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "admission_id": self.admission_id,
            "generator_family_id": self.generator_family_id,
            "admission_receipt_binding": (self.admission_receipt_binding.to_dict()),
            "source_runtime_closure_binding": (
                self.source_runtime_closure_binding.to_dict()
            ),
            "seed_free_readiness_binding": (self.seed_free_readiness_binding.to_dict()),
            "construction_review_binding": (self.construction_review_binding.to_dict()),
            "admission_spec_binding": self.admission_spec_binding.to_dict(),
            "family_admitted": False,
        }


@dataclass(frozen=True, slots=True)
class D7ExclusiveSeedSupplyClaimInputRecord(_CanonicalRecordMixin):
    claim_id: str
    supplier_identity_binding: D7AuthorityArtifactBinding
    development_exclusion_registry_binding: D7AuthorityArtifactBinding
    parent_selection_exclusion_registry_binding: D7AuthorityArtifactBinding
    seed_free_readiness_binding: D7AuthorityArtifactBinding
    admission_receipt_binding: D7AuthorityArtifactBinding
    source_runtime_receipt_binding: D7AuthorityArtifactBinding

    schema_version: ClassVar[str] = D7_EXCLUSIVE_SEED_SUPPLY_CLAIM_INPUT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        _slug(self.claim_id, label="claim_id")
        bindings = (
            self.supplier_identity_binding,
            self.development_exclusion_registry_binding,
            self.parent_selection_exclusion_registry_binding,
            self.seed_free_readiness_binding,
            self.admission_receipt_binding,
            self.source_runtime_receipt_binding,
        )
        if any(
            not isinstance(binding, D7AuthorityArtifactBinding) for binding in bindings
        ):
            raise TypeError("exclusive seed-supply claim bindings must be artifacts")
        if tuple(binding.artifact_role for binding in bindings) != (
            "seed-supplier-identity",
            "development-seed-exclusion-registry",
            "parent-selection-seed-exclusion-registry",
            "seed-free-readiness",
            "family-admission-receipt",
            "execution-source-runtime-receipt",
        ):
            raise D7AuthorityInputError(
                "exclusive seed-supply claim binding roles differ"
            )

    @property
    def artifact_binding(self) -> D7AuthorityArtifactBinding:
        return D7AuthorityArtifactBinding.from_record(
            artifact_role="exclusive-seed-supply-claim",
            artifact_contract_id=self.schema_version,
            record=self,
        )

    @classmethod
    def from_dict(cls, value: object) -> Self:
        item = _mapping(value, label="exclusive seed-supply claim input")
        _exact_keys(
            item,
            {
                "schema_version",
                "claim_id",
                "supplier_identity_binding",
                "development_exclusion_registry_binding",
                "parent_selection_exclusion_registry_binding",
                "seed_free_readiness_binding",
                "admission_receipt_binding",
                "source_runtime_receipt_binding",
                "claim_verified",
                "seed_supply_aborted_established",
                "retry_authorized",
            },
            label="exclusive seed-supply claim input",
        )
        if item["schema_version"] != cls.schema_version:
            raise D7AuthorityInputError("exclusive seed-supply claim schema differs")
        _false(item["claim_verified"], label="claim_verified")
        _false(
            item["seed_supply_aborted_established"],
            label="seed_supply_aborted_established",
        )
        _false(item["retry_authorized"], label="retry_authorized")
        return cls(
            claim_id=_slug(item["claim_id"], label="claim_id"),
            supplier_identity_binding=D7AuthorityArtifactBinding.from_dict(
                item["supplier_identity_binding"]
            ),
            development_exclusion_registry_binding=(
                D7AuthorityArtifactBinding.from_dict(
                    item["development_exclusion_registry_binding"]
                )
            ),
            parent_selection_exclusion_registry_binding=(
                D7AuthorityArtifactBinding.from_dict(
                    item["parent_selection_exclusion_registry_binding"]
                )
            ),
            seed_free_readiness_binding=D7AuthorityArtifactBinding.from_dict(
                item["seed_free_readiness_binding"]
            ),
            admission_receipt_binding=D7AuthorityArtifactBinding.from_dict(
                item["admission_receipt_binding"]
            ),
            source_runtime_receipt_binding=D7AuthorityArtifactBinding.from_dict(
                item["source_runtime_receipt_binding"]
            ),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "claim_id": self.claim_id,
            "supplier_identity_binding": self.supplier_identity_binding.to_dict(),
            "development_exclusion_registry_binding": (
                self.development_exclusion_registry_binding.to_dict()
            ),
            "parent_selection_exclusion_registry_binding": (
                self.parent_selection_exclusion_registry_binding.to_dict()
            ),
            "seed_free_readiness_binding": (self.seed_free_readiness_binding.to_dict()),
            "admission_receipt_binding": self.admission_receipt_binding.to_dict(),
            "source_runtime_receipt_binding": (
                self.source_runtime_receipt_binding.to_dict()
            ),
            "claim_verified": False,
            "seed_supply_aborted_established": False,
            "retry_authorized": False,
        }


@dataclass(frozen=True, slots=True)
class D7SingleSupplierInvocationInputRecord(_CanonicalRecordMixin):
    invocation_id: str
    claim_binding: D7AuthorityArtifactBinding
    supplier_identity_binding: D7AuthorityArtifactBinding
    official_seed_inventory_binding: D7AuthorityArtifactBinding

    schema_version: ClassVar[str] = D7_SINGLE_SUPPLIER_INVOCATION_INPUT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        _slug(self.invocation_id, label="invocation_id")
        bindings = (
            self.claim_binding,
            self.supplier_identity_binding,
            self.official_seed_inventory_binding,
        )
        if any(
            not isinstance(binding, D7AuthorityArtifactBinding) for binding in bindings
        ):
            raise TypeError("supplier invocation bindings must be artifacts")
        if tuple(binding.artifact_role for binding in bindings) != (
            "exclusive-seed-supply-claim",
            "seed-supplier-identity",
            "official-seed-inventory",
        ):
            raise D7AuthorityInputError(
                "single supplier invocation binding roles differ"
            )

    @property
    def artifact_binding(self) -> D7AuthorityArtifactBinding:
        return D7AuthorityArtifactBinding.from_record(
            artifact_role="single-supplier-invocation",
            artifact_contract_id=self.schema_version,
            record=self,
        )

    @classmethod
    def from_dict(cls, value: object) -> Self:
        item = _mapping(value, label="single supplier invocation input")
        _exact_keys(
            item,
            {
                "schema_version",
                "invocation_id",
                "claim_binding",
                "supplier_identity_binding",
                "official_seed_inventory_binding",
                "supplier_invocation_count_claimed",
                "single_invocation_verified",
                "inventory_output_verified",
            },
            label="single supplier invocation input",
        )
        if item["schema_version"] != cls.schema_version:
            raise D7AuthorityInputError("single supplier invocation schema differs")
        if (
            _plain_int(
                item["supplier_invocation_count_claimed"],
                label="supplier_invocation_count_claimed",
                minimum=1,
                maximum=1,
            )
            != 1
        ):
            raise D7AuthorityInputError("supplier invocation count must equal one")
        _false(
            item["single_invocation_verified"],
            label="single_invocation_verified",
        )
        _false(
            item["inventory_output_verified"],
            label="inventory_output_verified",
        )
        return cls(
            invocation_id=_slug(item["invocation_id"], label="invocation_id"),
            claim_binding=D7AuthorityArtifactBinding.from_dict(item["claim_binding"]),
            supplier_identity_binding=D7AuthorityArtifactBinding.from_dict(
                item["supplier_identity_binding"]
            ),
            official_seed_inventory_binding=(
                D7AuthorityArtifactBinding.from_dict(
                    item["official_seed_inventory_binding"]
                )
            ),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "invocation_id": self.invocation_id,
            "claim_binding": self.claim_binding.to_dict(),
            "supplier_identity_binding": self.supplier_identity_binding.to_dict(),
            "official_seed_inventory_binding": (
                self.official_seed_inventory_binding.to_dict()
            ),
            "supplier_invocation_count_claimed": 1,
            "single_invocation_verified": False,
            "inventory_output_verified": False,
        }


@dataclass(frozen=True, slots=True)
class D7ExecutionIdentityInputRecord(_CanonicalRecordMixin):
    execution_identity_id: str
    source_runtime_closure_binding: D7AuthorityArtifactBinding
    runtime_specification_binding: D7AuthorityArtifactBinding
    executable_sha256: str
    callable_identity_sha256: str
    process_identity_sha256: str

    schema_version: ClassVar[str] = D7_EXECUTION_IDENTITY_INPUT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        _slug(self.execution_identity_id, label="execution_identity_id")
        for name, binding in (
            (
                "source_runtime_closure_binding",
                self.source_runtime_closure_binding,
            ),
            (
                "runtime_specification_binding",
                self.runtime_specification_binding,
            ),
        ):
            if not isinstance(binding, D7AuthorityArtifactBinding):
                raise TypeError(f"{name} must be D7AuthorityArtifactBinding")
        _sha256(self.executable_sha256, label="executable_sha256")
        _sha256(
            self.callable_identity_sha256,
            label="callable_identity_sha256",
        )
        _sha256(self.process_identity_sha256, label="process_identity_sha256")

    @classmethod
    def from_dict(cls, value: object) -> Self:
        item = _mapping(value, label="execution identity input")
        _exact_keys(
            item,
            {
                "schema_version",
                "execution_identity_id",
                "source_runtime_closure_binding",
                "runtime_specification_binding",
                "executable_sha256",
                "callable_identity_sha256",
                "process_identity_sha256",
                "identity_verified",
            },
            label="execution identity input",
        )
        if item["schema_version"] != cls.schema_version:
            raise D7AuthorityInputError("execution identity schema differs")
        _false(item["identity_verified"], label="identity_verified")
        return cls(
            execution_identity_id=_slug(
                item["execution_identity_id"],
                label="execution_identity_id",
            ),
            source_runtime_closure_binding=(
                D7AuthorityArtifactBinding.from_dict(
                    item["source_runtime_closure_binding"]
                )
            ),
            runtime_specification_binding=(
                D7AuthorityArtifactBinding.from_dict(
                    item["runtime_specification_binding"]
                )
            ),
            executable_sha256=_sha256(
                item["executable_sha256"],
                label="executable_sha256",
            ),
            callable_identity_sha256=_sha256(
                item["callable_identity_sha256"],
                label="callable_identity_sha256",
            ),
            process_identity_sha256=_sha256(
                item["process_identity_sha256"],
                label="process_identity_sha256",
            ),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "execution_identity_id": self.execution_identity_id,
            "source_runtime_closure_binding": (
                self.source_runtime_closure_binding.to_dict()
            ),
            "runtime_specification_binding": (
                self.runtime_specification_binding.to_dict()
            ),
            "executable_sha256": self.executable_sha256,
            "callable_identity_sha256": self.callable_identity_sha256,
            "process_identity_sha256": self.process_identity_sha256,
            "identity_verified": False,
        }


@dataclass(frozen=True, slots=True)
class D7PhysicalStoreLaneIdentityRecord(_CanonicalRecordMixin):
    physical_identity_id: str
    attempt_key_sha256: str
    store_path: str
    store_device: int
    store_inode: int
    lane_path: str
    lane_device: int
    lane_inode: int
    lane_parent_device: int
    lane_parent_inode: int
    output_namespace_path: str
    output_parent_device: int
    output_parent_inode: int
    terminal_path: str
    terminal_parent_device: int
    terminal_parent_inode: int

    schema_version: ClassVar[str] = D7_PHYSICAL_STORE_LANE_IDENTITY_SCHEMA_VERSION
    attempt_role: ClassVar[str] = (
        attempt_records.D7AttemptRole.PRIMARY_CONFIRMATION.value
    )

    def __post_init__(self) -> None:
        _slug(self.physical_identity_id, label="physical_identity_id")
        attempt_key = _sha256(
            self.attempt_key_sha256,
            label="attempt_key_sha256",
        )
        store = _absolute_posix(self.store_path, label="store_path")
        lane = _absolute_posix(self.lane_path, label="lane_path")
        output = _absolute_posix(
            self.output_namespace_path,
            label="output_namespace_path",
        )
        terminal = _absolute_posix(self.terminal_path, label="terminal_path")
        for name, value in (
            ("store_device", self.store_device),
            ("store_inode", self.store_inode),
            ("lane_device", self.lane_device),
            ("lane_inode", self.lane_inode),
            ("lane_parent_device", self.lane_parent_device),
            ("lane_parent_inode", self.lane_parent_inode),
            ("output_parent_device", self.output_parent_device),
            ("output_parent_inode", self.output_parent_inode),
            ("terminal_parent_device", self.terminal_parent_device),
            ("terminal_parent_inode", self.terminal_parent_inode),
        ):
            _plain_int(value, label=name, minimum=1)
        if (
            lane
            != (PurePosixPath(store) / D7_AUTHORITATIVE_START_LANE_BASENAME).as_posix()
        ):
            raise D7AuthorityInputError(
                "lane_path must be the exact authoritative-start child of store_path"
            )
        if (
            self.lane_parent_device,
            self.lane_parent_inode,
        ) != (
            self.store_device,
            self.store_inode,
        ):
            raise D7AuthorityInputError(
                "lane parent physical coordinates must equal the store"
            )
        if (self.lane_device, self.lane_inode) == (
            self.store_device,
            self.store_inode,
        ):
            raise D7AuthorityInputError(
                "authoritative-start lane physical identity must differ from the store"
            )
        if not _is_descendant(output, store) or not _is_descendant(
            terminal,
            store,
        ):
            raise D7AuthorityInputError(
                "output and terminal subjects must remain inside the store"
            )
        if _paths_overlap(output, terminal):
            raise D7AuthorityInputError(
                "output namespace and terminal subject paths overlap"
            )
        reserved_paths = _reserved_persistence_paths(store, attempt_key)
        for label, subject in (
            ("output namespace", output),
            ("terminal subject", terminal),
        ):
            if (
                PurePosixPath(subject).parent == PurePosixPath(store)
                and _PERSISTENCE_CHRONOLOGY_LEAF_RE.fullmatch(
                    PurePosixPath(subject).name
                )
                is not None
            ) or any(_paths_overlap(subject, reserved) for reserved in reserved_paths):
                raise D7AuthorityInputError(
                    f"{label} overlaps persistence-reserved paths"
                )
        output_key = (
            self.output_parent_device,
            self.output_parent_inode,
            PurePosixPath(output).name,
        )
        terminal_key = (
            self.terminal_parent_device,
            self.terminal_parent_inode,
            PurePosixPath(terminal).name,
        )
        reserved_top_level_basenames = {
            PurePosixPath(path).name
            for path in _reserved_persistence_paths(store, attempt_key)
        }
        for label, subject_key in (
            ("output namespace", output_key),
            ("terminal subject", terminal_key),
        ):
            parent_coordinates = subject_key[:2]
            basename = subject_key[2]
            if parent_coordinates == (self.lane_device, self.lane_inode):
                raise D7AuthorityInputError(
                    f"{label} parent aliases the reserved authoritative-start lane"
                )
            if parent_coordinates == (
                self.store_device,
                self.store_inode,
            ) and (
                basename in reserved_top_level_basenames
                or _PERSISTENCE_CHRONOLOGY_LEAF_RE.fullmatch(basename) is not None
            ):
                raise D7AuthorityInputError(
                    f"{label} physical key aliases a persistence-reserved path"
                )
        if output_key == terminal_key:
            raise D7AuthorityInputError(
                "output and terminal resolve to the same physical subject key"
            )
        for label, path in (
            ("lane basename", lane),
            ("output basename", output),
            ("terminal basename", terminal),
        ):
            if _BASENAME_RE.fullmatch(PurePosixPath(path).name) is None:
                raise D7AuthorityInputError(f"{label} must be lowercase portable ASCII")

    @property
    def store_identity_sha256(self) -> str:
        return canonical_json_sha256(
            {
                "schema_version": "spirallens.d7-physical-store-key.v0.1",
                "path": self.store_path,
                "device": self.store_device,
                "inode": self.store_inode,
            }
        )

    @property
    def lane_identity_sha256(self) -> str:
        return canonical_json_sha256(
            {
                "schema_version": "spirallens.d7-physical-lane-key.v0.1",
                "path": self.lane_path,
                "device": self.lane_device,
                "inode": self.lane_inode,
                "parent_device": self.lane_parent_device,
                "parent_inode": self.lane_parent_inode,
            }
        )

    @property
    def output_subject_identity_sha256(self) -> str:
        return canonical_json_sha256(
            {
                "schema_version": "spirallens.d7-physical-subject-key.v0.1",
                "parent_device": self.output_parent_device,
                "parent_inode": self.output_parent_inode,
                "basename": PurePosixPath(self.output_namespace_path).name,
            }
        )

    @property
    def terminal_subject_identity_sha256(self) -> str:
        return canonical_json_sha256(
            {
                "schema_version": "spirallens.d7-physical-subject-key.v0.1",
                "parent_device": self.terminal_parent_device,
                "parent_inode": self.terminal_parent_inode,
                "basename": PurePosixPath(self.terminal_path).name,
            }
        )

    @classmethod
    def from_dict(cls, value: object) -> Self:
        item = _mapping(value, label="physical store/lane identity")
        fields = {
            "schema_version",
            "physical_identity_id",
            "attempt_key_sha256",
            "attempt_role",
            "store_path",
            "store_device",
            "store_inode",
            "lane_path",
            "lane_device",
            "lane_inode",
            "lane_parent_device",
            "lane_parent_inode",
            "output_namespace_path",
            "output_parent_device",
            "output_parent_inode",
            "terminal_path",
            "terminal_parent_device",
            "terminal_parent_inode",
            "store_identity_sha256",
            "lane_identity_sha256",
            "output_subject_identity_sha256",
            "terminal_subject_identity_sha256",
            "live_reobserved",
            "path_absence_observed",
        }
        _exact_keys(item, fields, label="physical store/lane identity")
        if item["schema_version"] != cls.schema_version:
            raise D7AuthorityInputError("physical identity schema differs")
        if item["attempt_role"] != cls.attempt_role:
            raise D7AuthorityInputError("physical attempt role differs")
        _false(item["live_reobserved"], label="live_reobserved")
        _false(item["path_absence_observed"], label="path_absence_observed")
        result = cls(
            physical_identity_id=_slug(
                item["physical_identity_id"],
                label="physical_identity_id",
            ),
            attempt_key_sha256=_sha256(
                item["attempt_key_sha256"],
                label="attempt_key_sha256",
            ),
            store_path=_absolute_posix(item["store_path"], label="store_path"),
            store_device=_plain_int(
                item["store_device"],
                label="store_device",
                minimum=1,
            ),
            store_inode=_plain_int(
                item["store_inode"],
                label="store_inode",
                minimum=1,
            ),
            lane_path=_absolute_posix(item["lane_path"], label="lane_path"),
            lane_device=_plain_int(
                item["lane_device"],
                label="lane_device",
                minimum=1,
            ),
            lane_inode=_plain_int(
                item["lane_inode"],
                label="lane_inode",
                minimum=1,
            ),
            lane_parent_device=_plain_int(
                item["lane_parent_device"],
                label="lane_parent_device",
                minimum=1,
            ),
            lane_parent_inode=_plain_int(
                item["lane_parent_inode"],
                label="lane_parent_inode",
                minimum=1,
            ),
            output_namespace_path=_absolute_posix(
                item["output_namespace_path"],
                label="output_namespace_path",
            ),
            output_parent_device=_plain_int(
                item["output_parent_device"],
                label="output_parent_device",
                minimum=1,
            ),
            output_parent_inode=_plain_int(
                item["output_parent_inode"],
                label="output_parent_inode",
                minimum=1,
            ),
            terminal_path=_absolute_posix(
                item["terminal_path"],
                label="terminal_path",
            ),
            terminal_parent_device=_plain_int(
                item["terminal_parent_device"],
                label="terminal_parent_device",
                minimum=1,
            ),
            terminal_parent_inode=_plain_int(
                item["terminal_parent_inode"],
                label="terminal_parent_inode",
                minimum=1,
            ),
        )
        for name, observed, expected in (
            (
                "store_identity_sha256",
                item["store_identity_sha256"],
                result.store_identity_sha256,
            ),
            (
                "lane_identity_sha256",
                item["lane_identity_sha256"],
                result.lane_identity_sha256,
            ),
            (
                "output_subject_identity_sha256",
                item["output_subject_identity_sha256"],
                result.output_subject_identity_sha256,
            ),
            (
                "terminal_subject_identity_sha256",
                item["terminal_subject_identity_sha256"],
                result.terminal_subject_identity_sha256,
            ),
        ):
            if _sha256(observed, label=name) != expected:
                raise D7AuthorityInputError(f"{name} differs from coordinates")
        return result

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "physical_identity_id": self.physical_identity_id,
            "attempt_key_sha256": self.attempt_key_sha256,
            "attempt_role": self.attempt_role,
            "store_path": self.store_path,
            "store_device": self.store_device,
            "store_inode": self.store_inode,
            "lane_path": self.lane_path,
            "lane_device": self.lane_device,
            "lane_inode": self.lane_inode,
            "lane_parent_device": self.lane_parent_device,
            "lane_parent_inode": self.lane_parent_inode,
            "output_namespace_path": self.output_namespace_path,
            "output_parent_device": self.output_parent_device,
            "output_parent_inode": self.output_parent_inode,
            "terminal_path": self.terminal_path,
            "terminal_parent_device": self.terminal_parent_device,
            "terminal_parent_inode": self.terminal_parent_inode,
            "store_identity_sha256": self.store_identity_sha256,
            "lane_identity_sha256": self.lane_identity_sha256,
            "output_subject_identity_sha256": (self.output_subject_identity_sha256),
            "terminal_subject_identity_sha256": (self.terminal_subject_identity_sha256),
            "live_reobserved": False,
            "path_absence_observed": False,
        }


_D7_TARGET_REQUIRED_FIELDS = (
    "schema_version",
    "replay_target_id",
    "claim_ceiling",
    "parent_bindings",
    "admission_receipt_binding",
    "official_seed_inventory_binding",
    "full_design_binding",
    "implementation_registry_binding",
    "aggregation_binding",
    "result_payload_schema_binding",
    "execution_source_runtime_closure_binding",
    "authority",
)
_D7_TARGET_PARENT_ROLES = (
    "recorded-c1",
    "recorded-c2",
    "parent-selection-protocol",
)


@dataclass(frozen=True, slots=True)
class D7ReplayTargetInputRecord(_CanonicalRecordMixin):
    replay_target_id: str
    parent_bindings: tuple[D7AuthorityArtifactBinding, ...]
    admission_receipt_binding: D7TargetAdmissionBindingCandidate
    official_seed_inventory_binding: D7AuthorityArtifactBinding
    full_design_binding: D7TargetFullDesignBindingCandidate
    implementation_registry_binding: D7AuthorityArtifactBinding
    aggregation_binding: D7AuthorityArtifactBinding
    result_payload_schema_binding: D7AuthorityArtifactBinding
    execution_source_runtime_closure_binding: D7TargetSourceRuntimeBindingCandidate

    schema_version: ClassVar[str] = D7_REPLAY_TARGET_INPUT_SCHEMA_VERSION
    claim_ceiling: ClassVar[str] = D7_RECORD_CLAIM_CEILING

    def __post_init__(self) -> None:
        _slug(self.replay_target_id, label="replay_target_id")
        if (
            type(self.parent_bindings) is not tuple
            or tuple(binding.artifact_role for binding in self.parent_bindings)
            != _D7_TARGET_PARENT_ROLES
        ):
            raise D7AuthorityInputError(
                "target parent bindings must have the exact frozen role order"
            )
        expected_parents = (
            (
                D7_RECORDED_C1_SCHEMA_VERSION,
                D7_RECORDED_C1_CANONICAL_SHA256,
                D7_RECORDED_C1_BYTE_COUNT,
            ),
            (
                D7_RECORDED_C2_SCHEMA_VERSION,
                D7_RECORDED_C2_CANONICAL_SHA256,
                D7_RECORDED_C2_BYTE_COUNT,
            ),
            (
                D7_PARENT_PROTOCOL_SCHEMA_VERSION,
                D7_PARENT_PROTOCOL_CANONICAL_SHA256,
                D7_PARENT_PROTOCOL_BYTE_COUNT,
            ),
        )
        if any(
            (
                binding.artifact_contract_id,
                binding.canonical_sha256,
                binding.byte_count,
            )
            != expected
            for binding, expected in zip(
                self.parent_bindings,
                expected_parents,
                strict=True,
            )
        ):
            raise D7AuthorityInputError(
                "target parent bindings differ from the exact recorded parents"
            )
        generic_bindings = (
            *self.parent_bindings,
            self.official_seed_inventory_binding,
            self.implementation_registry_binding,
            self.aggregation_binding,
            self.result_payload_schema_binding,
        )
        if any(
            not isinstance(binding, D7AuthorityArtifactBinding)
            for binding in generic_bindings
        ):
            raise TypeError("generic target bindings must be artifact bindings")
        if not isinstance(
            self.admission_receipt_binding,
            D7TargetAdmissionBindingCandidate,
        ):
            raise TypeError(
                "admission_receipt_binding must be a target admission candidate"
            )
        if not isinstance(
            self.full_design_binding,
            D7TargetFullDesignBindingCandidate,
        ):
            raise TypeError(
                "full_design_binding must be a target full-design candidate"
            )
        if not isinstance(
            self.execution_source_runtime_closure_binding,
            D7TargetSourceRuntimeBindingCandidate,
        ):
            raise TypeError(
                "execution source/runtime binding must be a target closure candidate"
            )
        expected_roles = (
            "official-seed-inventory",
            "implementation-registry",
            "aggregation",
            "result-payload-schema",
        )
        observed_roles = tuple(
            binding.artifact_role
            for binding in (
                self.official_seed_inventory_binding,
                self.implementation_registry_binding,
                self.aggregation_binding,
                self.result_payload_schema_binding,
            )
        )
        if observed_roles != expected_roles:
            raise D7AuthorityInputError("target binding roles differ")

    @classmethod
    def from_dict(cls, value: object) -> Self:
        item = _mapping(value, label="replay target input")
        _exact_keys(
            item,
            set(_D7_TARGET_REQUIRED_FIELDS),
            label="replay target input",
        )
        if item["schema_version"] != cls.schema_version:
            raise D7AuthorityInputError("replay target input schema differs")
        if item["claim_ceiling"] != cls.claim_ceiling:
            raise D7AuthorityInputError("replay target claim ceiling differs")
        authority = _mapping(item["authority"], label="target authority")
        if authority != _TARGET_AUTHORITY:
            raise D7AuthorityInputError(
                "target authority must equal the exact closed all-false map"
            )
        return cls(
            replay_target_id=_slug(
                item["replay_target_id"],
                label="replay_target_id",
            ),
            parent_bindings=tuple(
                D7AuthorityArtifactBinding.from_dict(binding)
                for binding in _sequence(
                    item["parent_bindings"],
                    label="parent_bindings",
                )
            ),
            admission_receipt_binding=D7TargetAdmissionBindingCandidate.from_dict(
                item["admission_receipt_binding"]
            ),
            official_seed_inventory_binding=(
                D7AuthorityArtifactBinding.from_dict(
                    item["official_seed_inventory_binding"]
                )
            ),
            full_design_binding=D7TargetFullDesignBindingCandidate.from_dict(
                item["full_design_binding"]
            ),
            implementation_registry_binding=(
                D7AuthorityArtifactBinding.from_dict(
                    item["implementation_registry_binding"]
                )
            ),
            aggregation_binding=D7AuthorityArtifactBinding.from_dict(
                item["aggregation_binding"]
            ),
            result_payload_schema_binding=(
                D7AuthorityArtifactBinding.from_dict(
                    item["result_payload_schema_binding"]
                )
            ),
            execution_source_runtime_closure_binding=(
                D7TargetSourceRuntimeBindingCandidate.from_dict(
                    item["execution_source_runtime_closure_binding"]
                )
            ),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "replay_target_id": self.replay_target_id,
            "claim_ceiling": self.claim_ceiling,
            "parent_bindings": [binding.to_dict() for binding in self.parent_bindings],
            "admission_receipt_binding": (self.admission_receipt_binding.to_dict()),
            "official_seed_inventory_binding": (
                self.official_seed_inventory_binding.to_dict()
            ),
            "full_design_binding": self.full_design_binding.to_dict(),
            "implementation_registry_binding": (
                self.implementation_registry_binding.to_dict()
            ),
            "aggregation_binding": self.aggregation_binding.to_dict(),
            "result_payload_schema_binding": (
                self.result_payload_schema_binding.to_dict()
            ),
            "execution_source_runtime_closure_binding": (
                self.execution_source_runtime_closure_binding.to_dict()
            ),
            "authority": dict(_TARGET_AUTHORITY),
        }


@dataclass(frozen=True, slots=True)
class D7FullDesignFreezeInputRecord(_CanonicalRecordMixin):
    freeze_id: str
    full_design_binding: D7AuthorityArtifactBinding
    replay_target_binding: D7AuthorityArtifactBinding
    atomic_publication_binding: D7AuthorityArtifactBinding
    freeze_commit: str
    authorization_commit: str

    schema_version: ClassVar[str] = D7_FULL_DESIGN_FREEZE_INPUT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        _slug(self.freeze_id, label="freeze_id")
        expected_roles = (
            "full-design",
            "replay-target",
            "chronology-atomic-seed-bearing-full-design-and-target-publication",
        )
        bindings = (
            self.full_design_binding,
            self.replay_target_binding,
            self.atomic_publication_binding,
        )
        if any(
            not isinstance(binding, D7AuthorityArtifactBinding) for binding in bindings
        ):
            raise TypeError("freeze bindings must be D7AuthorityArtifactBinding")
        if tuple(binding.artifact_role for binding in bindings) != expected_roles:
            raise D7AuthorityInputError("full-design freeze binding roles differ")
        freeze_commit = _commit(self.freeze_commit, label="freeze_commit")
        authorization_commit = _commit(
            self.authorization_commit,
            label="authorization_commit",
        )
        if freeze_commit == authorization_commit:
            raise D7AuthorityInputError(
                "freeze_commit must differ from authorization_commit"
            )

    @classmethod
    def from_dict(cls, value: object) -> Self:
        item = _mapping(value, label="full-design freeze input")
        _exact_keys(
            item,
            {
                "schema_version",
                "freeze_id",
                "full_design_binding",
                "replay_target_binding",
                "atomic_publication_binding",
                "freeze_commit",
                "authorization_commit",
                "freeze_verified",
            },
            label="full-design freeze input",
        )
        if item["schema_version"] != cls.schema_version:
            raise D7AuthorityInputError("full-design freeze schema differs")
        _false(item["freeze_verified"], label="freeze_verified")
        return cls(
            freeze_id=_slug(item["freeze_id"], label="freeze_id"),
            full_design_binding=D7AuthorityArtifactBinding.from_dict(
                item["full_design_binding"]
            ),
            replay_target_binding=D7AuthorityArtifactBinding.from_dict(
                item["replay_target_binding"]
            ),
            atomic_publication_binding=D7AuthorityArtifactBinding.from_dict(
                item["atomic_publication_binding"]
            ),
            freeze_commit=_commit(
                item["freeze_commit"],
                label="freeze_commit",
            ),
            authorization_commit=_commit(
                item["authorization_commit"],
                label="authorization_commit",
            ),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "freeze_id": self.freeze_id,
            "full_design_binding": self.full_design_binding.to_dict(),
            "replay_target_binding": self.replay_target_binding.to_dict(),
            "atomic_publication_binding": (self.atomic_publication_binding.to_dict()),
            "freeze_commit": self.freeze_commit,
            "authorization_commit": self.authorization_commit,
            "freeze_verified": False,
        }


@dataclass(frozen=True, slots=True)
class D7LaunchIntentInputRecord(_CanonicalRecordMixin):
    launch_intent_id: str
    replay_target_binding: D7AuthorityArtifactBinding
    full_design_freeze_binding: D7AuthorityArtifactBinding
    execution_identity_binding: D7AuthorityArtifactBinding
    physical_identity_binding: D7AuthorityArtifactBinding
    freeze_commit: str
    authorization_commit: str

    schema_version: ClassVar[str] = D7_LAUNCH_INTENT_INPUT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        _slug(self.launch_intent_id, label="launch_intent_id")
        bindings = (
            self.replay_target_binding,
            self.full_design_freeze_binding,
            self.execution_identity_binding,
            self.physical_identity_binding,
        )
        if any(
            not isinstance(binding, D7AuthorityArtifactBinding) for binding in bindings
        ):
            raise TypeError("launch intent bindings must be artifact bindings")
        if tuple(binding.artifact_role for binding in bindings) != (
            "replay-target",
            "full-design-freeze",
            "execution-identity",
            "physical-store-lane-identity",
        ):
            raise D7AuthorityInputError("launch intent binding roles differ")
        freeze_commit = _commit(self.freeze_commit, label="freeze_commit")
        authorization_commit = _commit(
            self.authorization_commit,
            label="authorization_commit",
        )
        if freeze_commit == authorization_commit:
            raise D7AuthorityInputError(
                "launch freeze_commit must differ from authorization_commit"
            )

    @classmethod
    def from_dict(cls, value: object) -> Self:
        item = _mapping(value, label="launch intent input")
        _exact_keys(
            item,
            {
                "schema_version",
                "launch_intent_id",
                "replay_target_binding",
                "full_design_freeze_binding",
                "execution_identity_binding",
                "physical_identity_binding",
                "freeze_commit",
                "authorization_commit",
                "launch_authorized",
            },
            label="launch intent input",
        )
        if item["schema_version"] != cls.schema_version:
            raise D7AuthorityInputError("launch intent input schema differs")
        _false(item["launch_authorized"], label="launch_authorized")
        return cls(
            launch_intent_id=_slug(
                item["launch_intent_id"],
                label="launch_intent_id",
            ),
            replay_target_binding=D7AuthorityArtifactBinding.from_dict(
                item["replay_target_binding"]
            ),
            full_design_freeze_binding=D7AuthorityArtifactBinding.from_dict(
                item["full_design_freeze_binding"]
            ),
            execution_identity_binding=D7AuthorityArtifactBinding.from_dict(
                item["execution_identity_binding"]
            ),
            physical_identity_binding=D7AuthorityArtifactBinding.from_dict(
                item["physical_identity_binding"]
            ),
            freeze_commit=_commit(
                item["freeze_commit"],
                label="freeze_commit",
            ),
            authorization_commit=_commit(
                item["authorization_commit"],
                label="authorization_commit",
            ),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "launch_intent_id": self.launch_intent_id,
            "replay_target_binding": self.replay_target_binding.to_dict(),
            "full_design_freeze_binding": (self.full_design_freeze_binding.to_dict()),
            "execution_identity_binding": (self.execution_identity_binding.to_dict()),
            "physical_identity_binding": (self.physical_identity_binding.to_dict()),
            "freeze_commit": self.freeze_commit,
            "authorization_commit": self.authorization_commit,
            "launch_authorized": False,
        }


class D7SeedSupplyTransition(str, Enum):
    FINAL_CODE_REVIEWED = "final-lifecycle-result-terminal-runner-code-reviewed"
    EXACT_SOURCE_RUNTIME_CLOSURE = "exact-execution-source-runtime-closure"
    SEED_FREE_READINESS = "seed-free-readiness"
    REVIEWED_FAMILY_ADMISSION = "reviewed-family-admission"
    EXCLUSIVE_SEED_SUPPLY_CLAIM = "exclusive-seed-supply-claim"
    SINGLE_SUPPLIER_INVOCATION = "single-supplier-invocation"
    ATOMIC_DESIGN_TARGET_PUBLICATION = (
        "atomic-seed-bearing-full-design-and-target-publication"
    )
    COMMITTED_FULL_DESIGN_FREEZE = "committed-full-design-freeze-receipt"
    LAUNCH_INTENT = "launch-intent"


D7_SEED_SUPPLY_TRANSITION_ORDER = tuple(D7SeedSupplyTransition)

_CHRONOLOGY_SUBJECT_ROLES = {
    D7SeedSupplyTransition.FINAL_CODE_REVIEWED: (
        "lifecycle-code",
        "result-code",
        "terminal-code",
        "witness-code",
        "runner-code",
    ),
    D7SeedSupplyTransition.EXACT_SOURCE_RUNTIME_CLOSURE: (
        "execution-source-runtime-receipt",
    ),
    D7SeedSupplyTransition.SEED_FREE_READINESS: ("seed-free-readiness",),
    D7SeedSupplyTransition.REVIEWED_FAMILY_ADMISSION: ("family-admission-receipt",),
    D7SeedSupplyTransition.EXCLUSIVE_SEED_SUPPLY_CLAIM: (
        "exclusive-seed-supply-claim",
    ),
    D7SeedSupplyTransition.SINGLE_SUPPLIER_INVOCATION: ("single-supplier-invocation",),
    D7SeedSupplyTransition.ATOMIC_DESIGN_TARGET_PUBLICATION: (
        "official-seed-inventory",
        "full-design",
        "replay-target",
    ),
    D7SeedSupplyTransition.COMMITTED_FULL_DESIGN_FREEZE: ("full-design-freeze",),
    D7SeedSupplyTransition.LAUNCH_INTENT: ("launch-intent",),
}


@dataclass(frozen=True, slots=True)
class D7ChronologyInputRecord(_CanonicalRecordMixin):
    transition: D7SeedSupplyTransition
    ordinal: int
    record_id: str
    predecessor_binding: D7AuthorityArtifactBinding | None
    subject_bindings: tuple[D7AuthorityArtifactBinding, ...]

    schema_version: ClassVar[str] = D7_CHRONOLOGY_INPUT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not isinstance(self.transition, D7SeedSupplyTransition):
            raise TypeError("transition must be D7SeedSupplyTransition")
        expected_ordinal = D7_SEED_SUPPLY_TRANSITION_ORDER.index(self.transition)
        if (
            _plain_int(self.ordinal, label="chronology ordinal", maximum=8)
            != expected_ordinal
        ):
            raise D7AuthorityInputError(
                "chronology ordinal differs from the frozen transition order"
            )
        _slug(self.record_id, label="chronology record_id")
        if self.ordinal == 0:
            if self.predecessor_binding is not None:
                raise D7AuthorityInputError(
                    "first chronology record must not have a predecessor"
                )
        elif not isinstance(
            self.predecessor_binding,
            D7AuthorityArtifactBinding,
        ):
            raise D7AuthorityInputError(
                "non-first chronology record requires a predecessor binding"
            )
        if type(self.subject_bindings) is not tuple or any(
            not isinstance(binding, D7AuthorityArtifactBinding)
            for binding in self.subject_bindings
        ):
            raise TypeError("subject_bindings must be artifact bindings")
        observed_roles = tuple(
            binding.artifact_role for binding in self.subject_bindings
        )
        if observed_roles != _CHRONOLOGY_SUBJECT_ROLES[self.transition]:
            raise D7AuthorityInputError(
                "chronology subject roles differ for the transition"
            )

    @property
    def binding_role(self) -> str:
        return f"chronology-{self.transition.value}"

    @property
    def artifact_binding(self) -> D7AuthorityArtifactBinding:
        return D7AuthorityArtifactBinding.from_record(
            artifact_role=self.binding_role,
            artifact_contract_id=self.schema_version,
            record=self,
        )

    @classmethod
    def from_dict(cls, value: object) -> Self:
        item = _mapping(value, label="chronology input record")
        _exact_keys(
            item,
            {
                "schema_version",
                "transition",
                "ordinal",
                "record_id",
                "predecessor_binding",
                "subject_bindings",
                "transition_verified",
            },
            label="chronology input record",
        )
        if item["schema_version"] != cls.schema_version:
            raise D7AuthorityInputError("chronology input schema differs")
        _false(item["transition_verified"], label="transition_verified")
        try:
            transition = D7SeedSupplyTransition(
                _string(item["transition"], label="transition")
            )
        except ValueError as error:
            raise D7AuthorityInputError(
                "chronology transition is not frozen"
            ) from error
        predecessor_value = item["predecessor_binding"]
        predecessor = (
            None
            if predecessor_value is None
            else D7AuthorityArtifactBinding.from_dict(predecessor_value)
        )
        return cls(
            transition=transition,
            ordinal=_plain_int(
                item["ordinal"],
                label="chronology ordinal",
                maximum=8,
            ),
            record_id=_slug(item["record_id"], label="chronology record_id"),
            predecessor_binding=predecessor,
            subject_bindings=tuple(
                D7AuthorityArtifactBinding.from_dict(binding)
                for binding in _sequence(
                    item["subject_bindings"],
                    label="chronology subject_bindings",
                )
            ),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "transition": self.transition.value,
            "ordinal": self.ordinal,
            "record_id": self.record_id,
            "predecessor_binding": (
                None
                if self.predecessor_binding is None
                else self.predecessor_binding.to_dict()
            ),
            "subject_bindings": [
                binding.to_dict() for binding in self.subject_bindings
            ],
            "transition_verified": False,
        }


@dataclass(frozen=True, slots=True)
class D7LaunchAuthorityInputBundle(_CanonicalRecordMixin):
    bundle_id: str
    development_seed_exclusion_registry: D7DevelopmentSeedExclusionRegistryRecord
    parent_selection_seed_exclusion_registry: (
        D7ParentSelectionSeedExclusionRegistryRecord
    )
    official_seed_inventory: D7OfficialSeedInventoryRecord
    runtime_specification: D7RuntimeSpecificationInputRecord
    source_runtime_closure: D7SourceRuntimeClosureInputRecord
    family_admission: D7FamilyAdmissionInputRecord
    exclusive_seed_supply_claim: D7ExclusiveSeedSupplyClaimInputRecord
    single_supplier_invocation: D7SingleSupplierInvocationInputRecord
    execution_identity: D7ExecutionIdentityInputRecord
    physical_store_lane_identity: D7PhysicalStoreLaneIdentityRecord
    replay_target: D7ReplayTargetInputRecord
    full_design_freeze: D7FullDesignFreezeInputRecord
    launch_intent: D7LaunchIntentInputRecord
    chronology: tuple[D7ChronologyInputRecord, ...]

    schema_version: ClassVar[str] = D7_LAUNCH_AUTHORITY_INPUT_BUNDLE_SCHEMA_VERSION
    claim_ceiling: ClassVar[str] = D7_RECORD_CLAIM_CEILING

    def __post_init__(self) -> None:
        _slug(self.bundle_id, label="bundle_id")
        record_types = (
            (
                self.development_seed_exclusion_registry,
                D7DevelopmentSeedExclusionRegistryRecord,
                "development_seed_exclusion_registry",
            ),
            (
                self.parent_selection_seed_exclusion_registry,
                D7ParentSelectionSeedExclusionRegistryRecord,
                "parent_selection_seed_exclusion_registry",
            ),
            (
                self.official_seed_inventory,
                D7OfficialSeedInventoryRecord,
                "official_seed_inventory",
            ),
            (
                self.runtime_specification,
                D7RuntimeSpecificationInputRecord,
                "runtime_specification",
            ),
            (
                self.source_runtime_closure,
                D7SourceRuntimeClosureInputRecord,
                "source_runtime_closure",
            ),
            (
                self.family_admission,
                D7FamilyAdmissionInputRecord,
                "family_admission",
            ),
            (
                self.exclusive_seed_supply_claim,
                D7ExclusiveSeedSupplyClaimInputRecord,
                "exclusive_seed_supply_claim",
            ),
            (
                self.single_supplier_invocation,
                D7SingleSupplierInvocationInputRecord,
                "single_supplier_invocation",
            ),
            (
                self.execution_identity,
                D7ExecutionIdentityInputRecord,
                "execution_identity",
            ),
            (
                self.physical_store_lane_identity,
                D7PhysicalStoreLaneIdentityRecord,
                "physical_store_lane_identity",
            ),
            (
                self.replay_target,
                D7ReplayTargetInputRecord,
                "replay_target",
            ),
            (
                self.full_design_freeze,
                D7FullDesignFreezeInputRecord,
                "full_design_freeze",
            ),
            (
                self.launch_intent,
                D7LaunchIntentInputRecord,
                "launch_intent",
            ),
        )
        for record, expected_type, label in record_types:
            if not isinstance(record, expected_type):
                raise TypeError(f"{label} must be {expected_type.__name__}")

        _require_record_binding(
            self.official_seed_inventory.development_exclusion_registry_binding,
            self.development_seed_exclusion_registry,
            role="development-seed-exclusion-registry",
            contract_id=self.development_seed_exclusion_registry.schema_version,
            label="official inventory development registry binding",
        )
        _require_record_binding(
            self.official_seed_inventory.parent_selection_exclusion_registry_binding,
            self.parent_selection_seed_exclusion_registry,
            role="parent-selection-seed-exclusion-registry",
            contract_id=(self.parent_selection_seed_exclusion_registry.schema_version),
            label="official inventory parent registry binding",
        )
        _require_record_binding(
            self.source_runtime_closure.runtime_specification_binding,
            self.runtime_specification,
            role="runtime-specification",
            contract_id=self.runtime_specification.schema_version,
            label="source closure runtime binding",
        )
        _require_record_binding(
            self.family_admission.source_runtime_closure_binding,
            self.source_runtime_closure,
            role="execution-source-runtime-closure",
            contract_id=self.source_runtime_closure.schema_version,
            label="family admission source/runtime binding",
        )
        _require_record_binding(
            self.execution_identity.source_runtime_closure_binding,
            self.source_runtime_closure,
            role="execution-source-runtime-closure",
            contract_id=self.source_runtime_closure.schema_version,
            label="execution identity source/runtime binding",
        )
        _require_record_binding(
            self.execution_identity.runtime_specification_binding,
            self.runtime_specification,
            role="runtime-specification",
            contract_id=self.runtime_specification.schema_version,
            label="execution identity runtime binding",
        )
        target_admission = self.replay_target.admission_receipt_binding
        if (
            target_admission.receipt_binding
            != self.family_admission.admission_receipt_binding
            or target_admission.generator_family_id
            != self.family_admission.generator_family_id
            or target_admission.construction_review_binding
            != self.family_admission.construction_review_binding
            or target_admission.admission_spec_binding
            != self.family_admission.admission_spec_binding
            or target_admission.source_runtime_receipt_sha256
            != self.source_runtime_closure.receipt_binding.canonical_sha256
        ):
            raise D7AuthorityInputError(
                "target admission candidate leaves differ from admission inputs"
            )
        _require_record_binding(
            self.replay_target.official_seed_inventory_binding,
            self.official_seed_inventory,
            role="official-seed-inventory",
            contract_id=self.official_seed_inventory.schema_version,
            label="target official seed inventory binding",
        )
        target_source_runtime = (
            self.replay_target.execution_source_runtime_closure_binding
        )
        if (
            target_source_runtime.receipt_binding
            != self.source_runtime_closure.receipt_binding
            or target_source_runtime.runtime_specification_sha256
            != self.runtime_specification.canonical_sha256
        ):
            raise D7AuthorityInputError(
                "target source/runtime candidate leaves differ from closure inputs"
            )
        target_design = self.replay_target.full_design_binding
        if (
            target_design.official_seed_inventory_sha256
            != self.official_seed_inventory.canonical_sha256
            or target_design.implementation_registry_sha256
            != self.replay_target.implementation_registry_binding.canonical_sha256
            or target_design.aggregation_sha256
            != self.replay_target.aggregation_binding.canonical_sha256
            or target_design.result_payload_schema_sha256
            != self.replay_target.result_payload_schema_binding.canonical_sha256
        ):
            raise D7AuthorityInputError(
                "target full-design candidate leaves differ from target inputs"
            )
        if (
            self.replay_target.parent_bindings[2]
            != self.parent_selection_seed_exclusion_registry.parent_protocol_binding
        ):
            raise D7AuthorityInputError(
                "target parent protocol binding differs from exclusion source"
            )
        expected_attempt_key = attempt_records.d7_attempt_key_sha256(
            replay_target_sha256=self.replay_target.canonical_sha256,
            attempt_role=attempt_records.D7AttemptRole.PRIMARY_CONFIRMATION,
        )
        if self.physical_store_lane_identity.attempt_key_sha256 != expected_attempt_key:
            raise D7AuthorityInputError(
                "physical attempt key differs from replay target and primary role"
            )

        _require_record_binding(
            self.full_design_freeze.replay_target_binding,
            self.replay_target,
            role="replay-target",
            contract_id=self.replay_target.schema_version,
            label="freeze replay target binding",
        )
        if (
            self.full_design_freeze.full_design_binding
            != self.replay_target.full_design_binding.design_binding
        ):
            raise D7AuthorityInputError("freeze and target full-design bindings differ")
        _require_record_binding(
            self.launch_intent.replay_target_binding,
            self.replay_target,
            role="replay-target",
            contract_id=self.replay_target.schema_version,
            label="launch intent replay target binding",
        )
        _require_record_binding(
            self.launch_intent.full_design_freeze_binding,
            self.full_design_freeze,
            role="full-design-freeze",
            contract_id=self.full_design_freeze.schema_version,
            label="launch intent freeze binding",
        )
        _require_record_binding(
            self.launch_intent.execution_identity_binding,
            self.execution_identity,
            role="execution-identity",
            contract_id=self.execution_identity.schema_version,
            label="launch intent execution identity binding",
        )
        _require_record_binding(
            self.launch_intent.physical_identity_binding,
            self.physical_store_lane_identity,
            role="physical-store-lane-identity",
            contract_id=self.physical_store_lane_identity.schema_version,
            label="launch intent physical identity binding",
        )
        if (
            self.launch_intent.freeze_commit != self.full_design_freeze.freeze_commit
            or self.launch_intent.authorization_commit
            != self.full_design_freeze.authorization_commit
        ):
            raise D7AuthorityInputError(
                "launch intent and freeze commit identities differ"
            )

        _require_record_binding(
            self.exclusive_seed_supply_claim.development_exclusion_registry_binding,
            self.development_seed_exclusion_registry,
            role="development-seed-exclusion-registry",
            contract_id=self.development_seed_exclusion_registry.schema_version,
            label="exclusive claim development registry binding",
        )
        _require_record_binding(
            self.exclusive_seed_supply_claim.parent_selection_exclusion_registry_binding,
            self.parent_selection_seed_exclusion_registry,
            role="parent-selection-seed-exclusion-registry",
            contract_id=self.parent_selection_seed_exclusion_registry.schema_version,
            label="exclusive claim parent registry binding",
        )
        if (
            self.exclusive_seed_supply_claim.admission_receipt_binding
            != self.family_admission.admission_receipt_binding
            or self.exclusive_seed_supply_claim.source_runtime_receipt_binding
            != self.source_runtime_closure.receipt_binding
        ):
            raise D7AuthorityInputError(
                "exclusive claim receipt bindings differ from reviewed inputs"
            )
        _require_record_binding(
            self.single_supplier_invocation.claim_binding,
            self.exclusive_seed_supply_claim,
            role="exclusive-seed-supply-claim",
            contract_id=self.exclusive_seed_supply_claim.schema_version,
            label="supplier invocation exclusive claim binding",
        )
        if (
            self.single_supplier_invocation.supplier_identity_binding
            != self.exclusive_seed_supply_claim.supplier_identity_binding
        ):
            raise D7AuthorityInputError(
                "supplier invocation identity differs from exclusive claim"
            )
        _require_record_binding(
            self.single_supplier_invocation.official_seed_inventory_binding,
            self.official_seed_inventory,
            role="official-seed-inventory",
            contract_id=self.official_seed_inventory.schema_version,
            label="supplier invocation official inventory binding",
        )

        if (
            type(self.chronology) is not tuple
            or tuple(record.transition for record in self.chronology)
            != D7_SEED_SUPPLY_TRANSITION_ORDER
            or tuple(record.ordinal for record in self.chronology)
            != tuple(range(len(D7_SEED_SUPPLY_TRANSITION_ORDER)))
        ):
            raise D7AuthorityInputError(
                "chronology must contain every frozen transition exactly once"
            )
        for index, record in enumerate(self.chronology):
            if not isinstance(record, D7ChronologyInputRecord):
                raise TypeError("chronology entries must be D7ChronologyInputRecord")
            if index == 0:
                continue
            if (
                record.predecessor_binding
                != self.chronology[index - 1].artifact_binding
            ):
                raise D7AuthorityInputError("chronology predecessor binding differs")

        (
            final_code,
            closure,
            readiness,
            admission,
            claim,
            invocation,
            publication,
            freeze,
            intent,
        ) = self.chronology
        _require_record_binding(
            self.source_runtime_closure.final_code_review_binding,
            final_code,
            role=final_code.binding_role,
            contract_id=final_code.schema_version,
            label="source closure final-code review binding",
        )
        if closure.subject_bindings[0] != self.source_runtime_closure.receipt_binding:
            raise D7AuthorityInputError(
                "closure chronology receipt differs from closure input"
            )
        if (
            self.family_admission.seed_free_readiness_binding
            != readiness.subject_bindings[0]
            or self.exclusive_seed_supply_claim.seed_free_readiness_binding
            != readiness.subject_bindings[0]
        ):
            raise D7AuthorityInputError("seed-free readiness bindings differ")
        if (
            admission.subject_bindings[0]
            != self.family_admission.admission_receipt_binding
        ):
            raise D7AuthorityInputError(
                "admission chronology receipt differs from admission input"
            )
        _require_record_binding(
            claim.subject_bindings[0],
            self.exclusive_seed_supply_claim,
            role="exclusive-seed-supply-claim",
            contract_id=self.exclusive_seed_supply_claim.schema_version,
            label="exclusive claim chronology subject",
        )
        _require_record_binding(
            invocation.subject_bindings[0],
            self.single_supplier_invocation,
            role="single-supplier-invocation",
            contract_id=self.single_supplier_invocation.schema_version,
            label="supplier invocation chronology subject",
        )
        _require_record_binding(
            publication.subject_bindings[0],
            self.official_seed_inventory,
            role="official-seed-inventory",
            contract_id=self.official_seed_inventory.schema_version,
            label="publication chronology official inventory",
        )
        if (
            publication.subject_bindings[0]
            != self.single_supplier_invocation.official_seed_inventory_binding
        ):
            raise D7AuthorityInputError(
                "publication inventory differs from supplier invocation output"
            )
        if (
            publication.subject_bindings[1]
            != self.replay_target.full_design_binding.design_binding
        ):
            raise D7AuthorityInputError(
                "publication chronology full-design binding differs"
            )
        _require_record_binding(
            publication.subject_bindings[2],
            self.replay_target,
            role="replay-target",
            contract_id=self.replay_target.schema_version,
            label="publication chronology replay target",
        )
        if self.full_design_freeze.atomic_publication_binding != (
            publication.artifact_binding
        ):
            raise D7AuthorityInputError("freeze atomic-publication binding differs")
        _require_record_binding(
            freeze.subject_bindings[0],
            self.full_design_freeze,
            role="full-design-freeze",
            contract_id=self.full_design_freeze.schema_version,
            label="freeze chronology subject",
        )
        _require_record_binding(
            intent.subject_bindings[0],
            self.launch_intent,
            role="launch-intent",
            contract_id=self.launch_intent.schema_version,
            label="intent chronology subject",
        )

    @classmethod
    def from_dict(cls, value: object) -> Self:
        item = _mapping(value, label="launch authority input bundle")
        _exact_keys(
            item,
            {
                "schema_version",
                "bundle_id",
                "claim_ceiling",
                "development_seed_exclusion_registry",
                "parent_selection_seed_exclusion_registry",
                "official_seed_inventory",
                "runtime_specification",
                "source_runtime_closure",
                "family_admission",
                "exclusive_seed_supply_claim",
                "single_supplier_invocation",
                "execution_identity",
                "physical_store_lane_identity",
                "replay_target",
                "full_design_freeze",
                "launch_intent",
                "chronology",
                "authority",
            },
            label="launch authority input bundle",
        )
        if item["schema_version"] != cls.schema_version:
            raise D7AuthorityInputError("launch authority bundle schema differs")
        if item["claim_ceiling"] != cls.claim_ceiling:
            raise D7AuthorityInputError("launch authority claim ceiling differs")
        authority = _mapping(item["authority"], label="bundle authority")
        if authority != _TARGET_AUTHORITY:
            raise D7AuthorityInputError(
                "bundle authority must equal the closed all-false map"
            )
        return cls(
            bundle_id=_slug(item["bundle_id"], label="bundle_id"),
            development_seed_exclusion_registry=(
                D7DevelopmentSeedExclusionRegistryRecord.from_dict(
                    item["development_seed_exclusion_registry"]
                )
            ),
            parent_selection_seed_exclusion_registry=(
                D7ParentSelectionSeedExclusionRegistryRecord.from_dict(
                    item["parent_selection_seed_exclusion_registry"]
                )
            ),
            official_seed_inventory=D7OfficialSeedInventoryRecord.from_dict(
                item["official_seed_inventory"]
            ),
            runtime_specification=D7RuntimeSpecificationInputRecord.from_dict(
                item["runtime_specification"]
            ),
            source_runtime_closure=(
                D7SourceRuntimeClosureInputRecord.from_dict(
                    item["source_runtime_closure"]
                )
            ),
            family_admission=D7FamilyAdmissionInputRecord.from_dict(
                item["family_admission"]
            ),
            exclusive_seed_supply_claim=(
                D7ExclusiveSeedSupplyClaimInputRecord.from_dict(
                    item["exclusive_seed_supply_claim"]
                )
            ),
            single_supplier_invocation=(
                D7SingleSupplierInvocationInputRecord.from_dict(
                    item["single_supplier_invocation"]
                )
            ),
            execution_identity=D7ExecutionIdentityInputRecord.from_dict(
                item["execution_identity"]
            ),
            physical_store_lane_identity=(
                D7PhysicalStoreLaneIdentityRecord.from_dict(
                    item["physical_store_lane_identity"]
                )
            ),
            replay_target=D7ReplayTargetInputRecord.from_dict(item["replay_target"]),
            full_design_freeze=D7FullDesignFreezeInputRecord.from_dict(
                item["full_design_freeze"]
            ),
            launch_intent=D7LaunchIntentInputRecord.from_dict(item["launch_intent"]),
            chronology=tuple(
                D7ChronologyInputRecord.from_dict(record)
                for record in _sequence(
                    item["chronology"],
                    label="chronology",
                )
            ),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "bundle_id": self.bundle_id,
            "claim_ceiling": self.claim_ceiling,
            "development_seed_exclusion_registry": (
                self.development_seed_exclusion_registry.to_dict()
            ),
            "parent_selection_seed_exclusion_registry": (
                self.parent_selection_seed_exclusion_registry.to_dict()
            ),
            "official_seed_inventory": self.official_seed_inventory.to_dict(),
            "runtime_specification": self.runtime_specification.to_dict(),
            "source_runtime_closure": self.source_runtime_closure.to_dict(),
            "family_admission": self.family_admission.to_dict(),
            "exclusive_seed_supply_claim": (self.exclusive_seed_supply_claim.to_dict()),
            "single_supplier_invocation": (self.single_supplier_invocation.to_dict()),
            "execution_identity": self.execution_identity.to_dict(),
            "physical_store_lane_identity": (
                self.physical_store_lane_identity.to_dict()
            ),
            "replay_target": self.replay_target.to_dict(),
            "full_design_freeze": self.full_design_freeze.to_dict(),
            "launch_intent": self.launch_intent.to_dict(),
            "chronology": [record.to_dict() for record in self.chronology],
            "authority": dict(_TARGET_AUTHORITY),
        }


@dataclass(frozen=True, slots=True)
class LoadedD7LaunchAuthorityStructuralCandidate:
    bundle: D7LaunchAuthorityInputBundle
    source_sha256: str
    byte_count: int

    authority_authenticated: ClassVar[bool] = False
    target_authoritative: ClassVar[bool] = False
    source_runtime_verified: ClassVar[bool] = False
    family_admission_verified: ClassVar[bool] = False
    seed_free_readiness_verified: ClassVar[bool] = False
    official_seed_chronology_verified: ClassVar[bool] = False
    seed_supply_claim_verified: ClassVar[bool] = False
    supplier_invocation_verified: ClassVar[bool] = False
    inventory_output_verified: ClassVar[bool] = False
    atomic_publication_verified: ClassVar[bool] = False
    full_design_freeze_verified: ClassVar[bool] = False
    launch_intent_verified: ClassVar[bool] = False
    physical_identity_reobserved: ClassVar[bool] = False
    path_absence_observed: ClassVar[bool] = False
    alternate_store_exclusivity_proved: ClassVar[bool] = False
    hostile_mutation_resistant: ClassVar[bool] = False
    exclusive_start_authorized: ClassVar[bool] = False
    launch_authorization_derived: ClassVar[bool] = False
    authoritative_lifecycle_eligible: ClassVar[bool] = False
    in_place_promotion_allowed: ClassVar[bool] = False
    terminal_publication_authorized: ClassVar[bool] = False
    finalization_authorized: ClassVar[bool] = False
    unresolved_finalization_authorized: ClassVar[bool] = False
    isolated_replay_authorized: ClassVar[bool] = False
    d7_execution_authorized: ClassVar[bool] = False
    d8_execution_authorized: ClassVar[bool] = False
    d7_result_produced: ClassVar[bool] = False
    execution_observed: ClassVar[bool] = False
    scientific_claim_eligible: ClassVar[bool] = False

    def __post_init__(self) -> None:
        if not isinstance(self.bundle, D7LaunchAuthorityInputBundle):
            raise TypeError("bundle must be D7LaunchAuthorityInputBundle")
        _sha256(self.source_sha256, label="source_sha256")
        _plain_int(self.byte_count, label="byte_count", minimum=1)
        if (
            self.source_sha256 != self.bundle.canonical_sha256
            or self.byte_count != self.bundle.byte_count
        ):
            raise D7AuthorityInputError("loaded identity differs from canonical bundle")


def load_d7_launch_authority_structural_candidate(
    source: bytes,
    *,
    expected_sha256: str,
) -> LoadedD7LaunchAuthorityStructuralCandidate:
    """Load one digest-bound structural candidate without external I/O."""

    if type(source) is not bytes:
        raise TypeError("source must be bytes")
    expected = _sha256(expected_sha256, label="expected_sha256")
    if not source or len(source) > MAX_D7_LAUNCH_AUTHORITY_INPUT_BYTES:
        raise D7AuthorityInputError(
            "launch authority input bundle byte count is out of bounds"
        )
    observed = sha256_bytes(source)
    if observed != expected:
        raise D7AuthorityInputError(
            "launch authority input bundle digest differs before parse"
        )
    try:
        parsed = parse_canonical_json(
            source,
            label="D7 launch authority input bundle",
        )
    except (ValueError, RecursionError) as error:
        raise D7AuthorityInputError(
            "D7 launch authority input bundle is not canonical JSON"
        ) from error
    bundle = D7LaunchAuthorityInputBundle.from_dict(parsed)
    if bundle.canonical_bytes != source:
        raise D7AuthorityInputError(
            "launch authority input bundle canonical bytes differ"
        )
    return LoadedD7LaunchAuthorityStructuralCandidate(
        bundle=bundle,
        source_sha256=observed,
        byte_count=len(source),
    )
