"""Common closed vocabularies and value objects for instrument contracts."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
import math
import re
from typing import TypeVar

import numpy as np

from .canonical import canonical_json_bytes, canonical_json_sha256


_SLUG = re.compile(r"^[a-z0-9][a-z0-9._-]{0,127}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class ContractValidationError(ValueError):
    """Raised when an instrument-contract value violates its schema."""


class HypothesisId(str, Enum):
    F0_SUPPORT = "f0_support"
    F1_PROJECTOR_CONNECTION = "f1_projector_connection"
    F2_LOCAL_COVARIANT_SECTION = "f2_local_covariant_section"
    F3_GLOBAL_PLANE_SECTION = "f3_global_plane_section"
    F4_SPIN_TWO_ANISOTROPY = "f4_spin_two_anisotropy"


class ScientificBranch(str, Enum):
    SUPPORT = "support"
    GEOMETRY = "geometry"
    DEFECT = "defect"


class ClaimLevel(str, Enum):
    LEVEL_0 = "level_0"
    LEVEL_1G = "level_1g"
    LEVEL_1D = "level_1d"
    LEVEL_2G = "level_2g"
    LEVEL_2T = "level_2t"
    LEVEL_3 = "level_3"


class EvolutionAxis(str, Enum):
    SYNTHETIC_LATTICE = "synthetic_lattice"
    TOKEN_POSITION = "token_position"
    LAYER_INDEX = "layer_index"
    TRAINING_STEP = "training_step"


class FitRole(str, Enum):
    INSTRUMENT_DEV = "instrument_dev"
    CALIBRATION_SELECTION = "calibration_selection"
    CALIBRATION_CONFIRMATION = "calibration_confirmation"
    SUBJECT_DISCOVERY = "subject_discovery"
    SUBJECT_CONFIRMATION = "subject_confirmation"


class ResolutionState(str, Enum):
    FIXED_BY_HYPOTHESIS = "fixed_by_hypothesis"
    INSTRUMENT_DEV_EXECUTED = "instrument_dev_executed"
    CALIBRATION_SELECTION = "calibration_selection"
    CALIBRATION_RESOLVED = "calibration_resolved"
    DISABLED = "disabled"
    NOT_APPLICABLE = "not_applicable"


class ArtifactType(str, Enum):
    HYPOTHESIS_REGISTRY = "hypothesis_registry"
    CONTEXT_BANK = "context_bank"
    SUBSTRATE_BINDING = "substrate_binding"
    GRAPH_CONSTRUCTION_SPEC = "graph_construction_spec"
    CANDIDATE_GRAPH = "candidate_graph"
    SUPPORT_DIAGNOSTIC = "support_diagnostic"
    GEOMETRIC_FIELD_ESTIMATE = "geometric_field_estimate"
    CORE_SCORE = "core_score"
    ORDER_PARAMETER_SPEC = "order_parameter_spec"
    ORDER_PARAMETER_FIELD = "order_parameter_field"
    CORE_CANDIDATE = "core_candidate"
    GROUND_TRUTH_ANCHOR = "ground_truth_anchor"
    EDGE_CONNECTION = "edge_connection"
    GEOMETRY_LOOP_ESTIMATE = "geometry_loop_estimate"
    DEFECT_LOOP_ESTIMATE = "defect_loop_estimate"
    CALIBRATION_SELECTION_DECISION = "calibration_selection_decision"
    CALIBRATION_CONFIRMATION_RESULT = "calibration_confirmation_result"


SYNTHETIC_LATTICE_SUBSTRATE_BINDING_SCHEMA_VERSION = (
    "spirallens.instrument.synthetic-lattice-substrate-binding.v0.1"
)


ARTIFACT_SCHEMA_VERSION_BY_TYPE: Mapping[ArtifactType, str] = {
    ArtifactType.HYPOTHESIS_REGISTRY: (
        "spirallens.hypothesis-registry.v0.1"
    ),
    ArtifactType.CONTEXT_BANK: "spirallens.context-bank.v1",
    ArtifactType.SUBSTRATE_BINDING: (
        "spirallens.instrument.substrate-binding.v0.1"
    ),
    ArtifactType.GRAPH_CONSTRUCTION_SPEC: (
        "spirallens.instrument.graph-construction-spec.v0.1"
    ),
    ArtifactType.CANDIDATE_GRAPH: (
        "spirallens.instrument.candidate-graph.v0.1"
    ),
    ArtifactType.SUPPORT_DIAGNOSTIC: (
        "spirallens.instrument.support-diagnostic.v0.1"
    ),
    ArtifactType.GEOMETRIC_FIELD_ESTIMATE: (
        "spirallens.instrument.geometric-field-estimate.v0.1"
    ),
    ArtifactType.CORE_SCORE: "spirallens.instrument.core-score.v0.1",
    ArtifactType.ORDER_PARAMETER_SPEC: (
        "spirallens.instrument.order-parameter-spec.v0.1"
    ),
    ArtifactType.ORDER_PARAMETER_FIELD: (
        "spirallens.instrument.order-parameter-field.v0.1"
    ),
    ArtifactType.CORE_CANDIDATE: (
        "spirallens.instrument.core-candidate.v0.1"
    ),
    ArtifactType.GROUND_TRUTH_ANCHOR: (
        "spirallens.instrument.ground-truth-anchor.v0.1"
    ),
    ArtifactType.EDGE_CONNECTION: (
        "spirallens.instrument.edge-connection.v0.1"
    ),
    ArtifactType.GEOMETRY_LOOP_ESTIMATE: (
        "spirallens.instrument.geometry-loop-estimate.v0.1"
    ),
    ArtifactType.DEFECT_LOOP_ESTIMATE: (
        "spirallens.instrument.defect-loop-estimate.v0.1"
    ),
    ArtifactType.CALIBRATION_SELECTION_DECISION: (
        "spirallens.instrument.calibration-selection-decision.v0.1"
    ),
    ArtifactType.CALIBRATION_CONFIRMATION_RESULT: (
        "spirallens.instrument.calibration-confirmation-result.v0.1"
    ),
}

ARTIFACT_SCHEMA_VERSIONS_BY_TYPE: Mapping[
    ArtifactType,
    frozenset[str],
] = {
    artifact_type: (
        frozenset(
            {
                schema_version,
                SYNTHETIC_LATTICE_SUBSTRATE_BINDING_SCHEMA_VERSION,
            }
        )
        if artifact_type is ArtifactType.SUBSTRATE_BINDING
        else frozenset({schema_version})
    )
    for artifact_type, schema_version in (
        ARTIFACT_SCHEMA_VERSION_BY_TYPE.items()
    )
}


class PayloadKind(str, Enum):
    ARRAY = "array"
    TABLE = "table"
    JSON_RECORDS = "json_records"
    OPAQUE = "opaque"


class NeighborhoodMode(str, Enum):
    GRAPH_FREE = "graph_free"
    INHERIT_FIELD_ESTIMATION_GRAPH = (
        "inherit_field_estimation_graph"
    )
    EXPLICIT_CORE_GRAPH = "explicit_core_graph"


class HypothesisDisposition(str, Enum):
    ADVANCE = "advance"
    RETAIN_DIAGNOSTIC = "retain_diagnostic"
    REJECT = "reject"


class GateState(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    INSUFFICIENT = "insufficient"
    NOT_RUN = "not_run"


EnumType = TypeVar("EnumType", bound=Enum)


def require_mapping(
    value: object,
    *,
    label: str,
) -> Mapping[str, object]:
    """Require a mapping with string field names."""

    if not isinstance(value, Mapping):
        raise ContractValidationError(f"{label} must be a mapping")
    if any(not isinstance(key, str) for key in value):
        raise ContractValidationError(f"{label} keys must be strings")
    return value


def exact_keys(
    value: Mapping[str, object],
    expected: set[str] | frozenset[str],
    *,
    label: str,
) -> None:
    """Reject both missing and unknown fields."""

    actual = set(value)
    if actual != set(expected):
        raise ContractValidationError(
            f"{label} fields differ from the contract: "
            f"missing={sorted(set(expected) - actual)}, "
            f"unknown={sorted(actual - set(expected))}"
        )


def require_string(value: object, *, label: str) -> str:
    """Require a non-empty string without surrounding whitespace."""

    if not isinstance(value, str) or not value:
        raise ContractValidationError(f"{label} must be a non-empty string")
    if value != value.strip():
        raise ContractValidationError(
            f"{label} must not have surrounding whitespace"
        )
    return value


def require_slug(value: object, *, label: str) -> str:
    """Require a stable machine-readable identifier."""

    text = require_string(value, label=label)
    if _SLUG.fullmatch(text) is None:
        raise ContractValidationError(
            f"{label} must match {_SLUG.pattern!r}"
        )
    return text


def require_sha256(value: object, *, label: str) -> str:
    """Require one lowercase SHA-256 digest."""

    text = require_string(value, label=label)
    if _SHA256.fullmatch(text) is None:
        raise ContractValidationError(
            f"{label} must be a lowercase SHA-256 digest"
        )
    return text


def require_plain_int(
    value: object,
    *,
    label: str,
    minimum: int = 0,
) -> int:
    """Require an integer while rejecting booleans."""

    if isinstance(value, bool) or not isinstance(value, int):
        raise ContractValidationError(f"{label} must be an integer")
    if value < minimum:
        raise ContractValidationError(
            f"{label} must be >= {minimum}"
        )
    return value


def require_bool(value: object, *, label: str) -> bool:
    """Require an actual boolean rather than an integer alias."""

    if type(value) is not bool:
        raise ContractValidationError(f"{label} must be a boolean")
    return value


def enum_from_value(
    enum_type: type[EnumType],
    value: object,
    *,
    label: str,
) -> EnumType:
    """Parse one member of a closed string enum."""

    if not isinstance(value, str):
        raise ContractValidationError(f"{label} must be a string")
    try:
        return enum_type(value)
    except ValueError as error:
        allowed = ", ".join(member.value for member in enum_type)
        raise ContractValidationError(
            f"{label} must be one of: {allowed}"
        ) from error


def string_tuple_from_list(
    value: object,
    *,
    label: str,
    require_nonempty: bool = False,
    require_canonical_order: bool = False,
    require_slugs: bool = False,
) -> tuple[str, ...]:
    """Parse a JSON list into an optionally canonical tuple of strings."""

    if not isinstance(value, list):
        raise ContractValidationError(f"{label} must be a list")
    result = tuple(
        (
            require_slug(item, label=f"{label}[{index}]")
            if require_slugs
            else require_string(item, label=f"{label}[{index}]")
        )
        for index, item in enumerate(value)
    )
    if require_nonempty and not result:
        raise ContractValidationError(f"{label} must not be empty")
    if require_canonical_order and tuple(sorted(set(result))) != result:
        raise ContractValidationError(
            f"{label} must be unique and sorted"
        )
    return result


def _require_optional_string(
    value: object,
    *,
    label: str,
    slug: bool = False,
) -> str | None:
    if value is None:
        return None
    return (
        require_slug(value, label=label)
        if slug
        else require_string(value, label=label)
    )


def _require_canonical_dtype(value: object, *, label: str) -> str:
    text = require_string(value, label=label)
    try:
        dtype = np.dtype(text)
    except TypeError as error:
        raise ContractValidationError(
            f"{label} must be a valid NumPy dtype string"
        ) from error
    if (
        dtype.hasobject
        or dtype.str != text
        or not text
        or text[0] not in {"<", ">", "|"}
    ):
        raise ContractValidationError(
            f"{label} must be a canonical explicit-endian NumPy "
            "dtype.str value"
        )
    return text


def _canonical_candidate_ids(
    values: tuple[str, ...],
) -> tuple[str, ...]:
    if not isinstance(values, tuple):
        raise TypeError("candidate_ids must be a tuple")
    validated = tuple(
        require_slug(value, label=f"candidate_ids[{index}]")
        for index, value in enumerate(values)
    )
    if tuple(sorted(set(validated))) != validated:
        raise ContractValidationError(
            "candidate_ids must be unique and sorted"
        )
    return validated


@dataclass(frozen=True, slots=True)
class RuleChoice:
    """A rule fixed now, delegated to calibration, or explicitly absent."""

    family_id: str
    resolution: ResolutionState
    selected_id: str | None = None
    candidate_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        require_slug(self.family_id, label="family_id")
        if not isinstance(self.resolution, ResolutionState):
            raise TypeError("resolution must be a ResolutionState")
        _require_optional_string(
            self.selected_id,
            label="selected_id",
            slug=True,
        )
        candidates = _canonical_candidate_ids(self.candidate_ids)

        has_selected = self.selected_id is not None
        has_candidates = bool(candidates)
        if has_selected and has_candidates:
            raise ContractValidationError(
                "selected_id and candidate_ids are mutually exclusive"
            )
        if self.resolution in {
            ResolutionState.FIXED_BY_HYPOTHESIS,
            ResolutionState.INSTRUMENT_DEV_EXECUTED,
            ResolutionState.CALIBRATION_RESOLVED,
        }:
            if not has_selected:
                raise ContractValidationError(
                    f"{self.resolution.value} requires selected_id"
                )
        elif self.resolution is ResolutionState.CALIBRATION_SELECTION:
            if not has_candidates:
                raise ContractValidationError(
                    "calibration_selection requires candidate_ids"
                )
        elif has_selected or has_candidates:
            raise ContractValidationError(
                "disabled and not_applicable choices cannot select candidates"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "family_id": self.family_id,
            "resolution": self.resolution.value,
            "selected_id": self.selected_id,
            "candidate_ids": list(self.candidate_ids),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> "RuleChoice":
        document = require_mapping(value, label="rule choice")
        exact_keys(
            document,
            {
                "family_id",
                "resolution",
                "selected_id",
                "candidate_ids",
            },
            label="rule choice",
        )
        return cls(
            family_id=require_slug(
                document["family_id"],
                label="family_id",
            ),
            resolution=enum_from_value(
                ResolutionState,
                document["resolution"],
                label="resolution",
            ),
            selected_id=_require_optional_string(
                document["selected_id"],
                label="selected_id",
                slug=True,
            ),
            candidate_ids=string_tuple_from_list(
                document["candidate_ids"],
                label="candidate_ids",
                require_canonical_order=True,
                require_slugs=True,
            ),
        )

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_dict())

    @property
    def identity_sha256(self) -> str:
        return canonical_json_sha256(self.to_dict())


@dataclass(frozen=True, slots=True)
class ArtifactRef:
    """Content-addressed reference to one canonical artifact."""

    artifact_type: ArtifactType
    schema_version: str
    artifact_id: str
    canonical_sha256: str

    def __post_init__(self) -> None:
        if not isinstance(self.artifact_type, ArtifactType):
            raise TypeError("artifact_type must be an ArtifactType")
        require_slug(self.schema_version, label="schema_version")
        expected_schema_versions = ARTIFACT_SCHEMA_VERSIONS_BY_TYPE[
            self.artifact_type
        ]
        if self.schema_version not in expected_schema_versions:
            raise ContractValidationError(
                "schema_version does not match artifact_type: "
                f"expected one of {sorted(expected_schema_versions)!r}"
            )
        require_slug(self.artifact_id, label="artifact_id")
        require_sha256(
            self.canonical_sha256,
            label="canonical_sha256",
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "artifact_type": self.artifact_type.value,
            "schema_version": self.schema_version,
            "artifact_id": self.artifact_id,
            "canonical_sha256": self.canonical_sha256,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> "ArtifactRef":
        document = require_mapping(value, label="artifact reference")
        exact_keys(
            document,
            {
                "artifact_type",
                "schema_version",
                "artifact_id",
                "canonical_sha256",
            },
            label="artifact reference",
        )
        return cls(
            artifact_type=enum_from_value(
                ArtifactType,
                document["artifact_type"],
                label="artifact_type",
            ),
            schema_version=require_slug(
                document["schema_version"],
                label="schema_version",
            ),
            artifact_id=require_slug(
                document["artifact_id"],
                label="artifact_id",
            ),
            canonical_sha256=require_sha256(
                document["canonical_sha256"],
                label="canonical_sha256",
            ),
        )

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_dict())

    @property
    def identity_sha256(self) -> str:
        return canonical_json_sha256(self.to_dict())


def _optional_shape(value: object, *, label: str) -> tuple[int, ...] | None:
    if value is None:
        return None
    if not isinstance(value, list):
        raise ContractValidationError(f"{label} must be a list or null")
    if not value:
        raise ContractValidationError(f"{label} must not be empty")
    return tuple(
        require_plain_int(
            dimension,
            label=f"{label}[{index}]",
            minimum=0,
        )
        for index, dimension in enumerate(value)
    )


def _validate_shape_tuple(
    value: tuple[int, ...] | None,
) -> tuple[int, ...] | None:
    if value is None:
        return None
    if not isinstance(value, tuple):
        raise TypeError("shape must be a tuple or None")
    if not value:
        raise ContractValidationError("shape must not be empty")
    return tuple(
        require_plain_int(
            dimension,
            label=f"shape[{index}]",
            minimum=0,
        )
        for index, dimension in enumerate(value)
    )


@dataclass(frozen=True, slots=True)
class PayloadRef:
    """Content-addressed reference to one external artifact payload."""

    kind: PayloadKind
    sha256: str
    byte_length: int
    media_type: str
    dtype: str | None = None
    shape: tuple[int, ...] | None = None
    record_count: int | None = None
    row_identity_sha256: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.kind, PayloadKind):
            raise TypeError("kind must be a PayloadKind")
        require_sha256(self.sha256, label="sha256")
        require_plain_int(
            self.byte_length,
            label="byte_length",
            minimum=1,
        )
        require_string(self.media_type, label="media_type")
        if self.dtype is not None:
            _require_canonical_dtype(self.dtype, label="dtype")
        shape = _validate_shape_tuple(self.shape)
        if self.record_count is not None:
            require_plain_int(
                self.record_count,
                label="record_count",
                minimum=0,
            )
        if self.row_identity_sha256 is not None:
            require_sha256(
                self.row_identity_sha256,
                label="row_identity_sha256",
            )

        has_array_metadata = self.dtype is not None or shape is not None
        if (self.dtype is None) != (shape is None):
            raise ContractValidationError(
                "dtype and shape must be present or absent together"
            )
        if self.kind is PayloadKind.ARRAY:
            if (
                not has_array_metadata
                or self.record_count is not None
                or self.row_identity_sha256 is None
            ):
                raise ContractValidationError(
                    "array payloads require dtype, shape, and "
                    "row_identity_sha256, and forbid record_count"
                )
            if self.media_type != "application/x-npy":
                raise ContractValidationError(
                    "array payloads require media_type application/x-npy"
                )
            assert shape is not None
            assert self.dtype is not None
            minimum_bytes = math.prod(shape) * np.dtype(self.dtype).itemsize
            if self.byte_length < minimum_bytes:
                raise ContractValidationError(
                    "array payload byte_length is smaller than its "
                    "declared uncompressed values"
                )
        elif self.kind in {
            PayloadKind.TABLE,
            PayloadKind.JSON_RECORDS,
        }:
            if (
                has_array_metadata
                or self.record_count is None
                or (
                    self.record_count > 0
                    and self.row_identity_sha256 is None
                )
            ):
                raise ContractValidationError(
                    "table and json_records payloads require record_count "
                    "and row_identity_sha256 for non-empty records, and "
                    "forbid dtype and shape"
                )
            expected_media_type = (
                "application/vnd.apache.parquet"
                if self.kind is PayloadKind.TABLE
                else "application/x-ndjson"
            )
            if self.media_type != expected_media_type:
                raise ContractValidationError(
                    f"{self.kind.value} payloads require media_type "
                    f"{expected_media_type}"
                )
        elif (
            has_array_metadata
            or self.record_count is not None
            or self.row_identity_sha256 is not None
        ):
            raise ContractValidationError(
                "opaque payloads cannot carry structured row metadata"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": self.kind.value,
            "sha256": self.sha256,
            "byte_length": self.byte_length,
            "media_type": self.media_type,
            "dtype": self.dtype,
            "shape": (
                None if self.shape is None else list(self.shape)
            ),
            "record_count": self.record_count,
            "row_identity_sha256": self.row_identity_sha256,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> "PayloadRef":
        document = require_mapping(value, label="payload reference")
        exact_keys(
            document,
            {
                "kind",
                "sha256",
                "byte_length",
                "media_type",
                "dtype",
                "shape",
                "record_count",
                "row_identity_sha256",
            },
            label="payload reference",
        )
        record_count = document["record_count"]
        row_identity = document["row_identity_sha256"]
        return cls(
            kind=enum_from_value(
                PayloadKind,
                document["kind"],
                label="kind",
            ),
            sha256=require_sha256(
                document["sha256"],
                label="sha256",
            ),
            byte_length=require_plain_int(
                document["byte_length"],
                label="byte_length",
                minimum=1,
            ),
            media_type=require_string(
                document["media_type"],
                label="media_type",
            ),
            dtype=(
                None
                if document["dtype"] is None
                else _require_canonical_dtype(
                    document["dtype"],
                    label="dtype",
                )
            ),
            shape=_optional_shape(
                document["shape"],
                label="shape",
            ),
            record_count=(
                None
                if record_count is None
                else require_plain_int(
                    record_count,
                    label="record_count",
                    minimum=0,
                )
            ),
            row_identity_sha256=(
                None
                if row_identity is None
                else require_sha256(
                    row_identity,
                    label="row_identity_sha256",
                )
            ),
        )

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_dict())

    @property
    def identity_sha256(self) -> str:
        return canonical_json_sha256(self.to_dict())
