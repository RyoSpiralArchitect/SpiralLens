"""Metadata-only canonical artifacts for the P0 instrument boundary.

The records in this module contain identities and content-addressed
references only.  They do not open payloads, run estimators, construct graphs,
or authorize subject access.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import re
from typing import ClassVar, Protocol, TypeAlias

from .canonical import canonical_json_bytes, canonical_json_sha256
from .common import (
    ARTIFACT_SCHEMA_VERSION_BY_TYPE,
    SYNTHETIC_LATTICE_SUBSTRATE_BINDING_SCHEMA_VERSION,
    ArtifactRef,
    ArtifactType,
    ClaimLevel,
    ContractValidationError,
    EvolutionAxis,
    FitRole,
    GateState,
    HypothesisDisposition,
    HypothesisId,
    NeighborhoodMode,
    PayloadKind,
    PayloadRef,
    ResolutionState,
    RuleChoice,
    ScientificBranch,
    enum_from_value,
    exact_keys,
    require_bool,
    require_mapping,
    require_plain_int,
    require_sha256,
    require_slug,
    require_string,
    string_tuple_from_list,
)


SUBSTRATE_BINDING_SCHEMA = ARTIFACT_SCHEMA_VERSION_BY_TYPE[
    ArtifactType.SUBSTRATE_BINDING
]
GRAPH_CONSTRUCTION_SPEC_SCHEMA = ARTIFACT_SCHEMA_VERSION_BY_TYPE[
    ArtifactType.GRAPH_CONSTRUCTION_SPEC
]
CANDIDATE_GRAPH_SCHEMA = ARTIFACT_SCHEMA_VERSION_BY_TYPE[
    ArtifactType.CANDIDATE_GRAPH
]
SUPPORT_DIAGNOSTIC_SCHEMA = ARTIFACT_SCHEMA_VERSION_BY_TYPE[
    ArtifactType.SUPPORT_DIAGNOSTIC
]
GEOMETRIC_FIELD_ESTIMATE_SCHEMA = ARTIFACT_SCHEMA_VERSION_BY_TYPE[
    ArtifactType.GEOMETRIC_FIELD_ESTIMATE
]
ORDER_PARAMETER_SPEC_SCHEMA = ARTIFACT_SCHEMA_VERSION_BY_TYPE[
    ArtifactType.ORDER_PARAMETER_SPEC
]
ORDER_PARAMETER_FIELD_SCHEMA = ARTIFACT_SCHEMA_VERSION_BY_TYPE[
    ArtifactType.ORDER_PARAMETER_FIELD
]
CORE_SCORE_SCHEMA = ARTIFACT_SCHEMA_VERSION_BY_TYPE[
    ArtifactType.CORE_SCORE
]
CORE_CANDIDATE_SCHEMA = ARTIFACT_SCHEMA_VERSION_BY_TYPE[
    ArtifactType.CORE_CANDIDATE
]
GROUND_TRUTH_ANCHOR_SCHEMA = ARTIFACT_SCHEMA_VERSION_BY_TYPE[
    ArtifactType.GROUND_TRUTH_ANCHOR
]
EDGE_CONNECTION_SCHEMA = ARTIFACT_SCHEMA_VERSION_BY_TYPE[
    ArtifactType.EDGE_CONNECTION
]
GEOMETRY_LOOP_ESTIMATE_SCHEMA = ARTIFACT_SCHEMA_VERSION_BY_TYPE[
    ArtifactType.GEOMETRY_LOOP_ESTIMATE
]
DEFECT_LOOP_ESTIMATE_SCHEMA = ARTIFACT_SCHEMA_VERSION_BY_TYPE[
    ArtifactType.DEFECT_LOOP_ESTIMATE
]
CALIBRATION_SELECTION_DECISION_SCHEMA = ARTIFACT_SCHEMA_VERSION_BY_TYPE[
    ArtifactType.CALIBRATION_SELECTION_DECISION
]
CALIBRATION_CONFIRMATION_RESULT_SCHEMA = ARTIFACT_SCHEMA_VERSION_BY_TYPE[
    ArtifactType.CALIBRATION_CONFIRMATION_RESULT
]


_GRAPH_PURPOSES = {
    "field_estimation",
    "cycle_construction",
    "core_localization",
}
_ORIENTATION_STATES = {"so2", "o2_reflection", "unresolved"}
_COORDINATE_MODES = {"global_frame", "local_frames"}
_LOCALIZATION_MODES = {
    "unlocalized",
    "inferred_core",
    "supplied_anchor",
}
_SYNTHETIC_LATTICE_BOUNDARY_RULES = {"open"}
_GIT_SHA1 = re.compile(r"^[0-9a-f]{40}$")
_CALIBRATION_EVIDENCE_TYPES = {
    ArtifactType.SUBSTRATE_BINDING,
    ArtifactType.GRAPH_CONSTRUCTION_SPEC,
    ArtifactType.CANDIDATE_GRAPH,
    ArtifactType.SUPPORT_DIAGNOSTIC,
    ArtifactType.GEOMETRIC_FIELD_ESTIMATE,
    ArtifactType.ORDER_PARAMETER_SPEC,
    ArtifactType.ORDER_PARAMETER_FIELD,
    ArtifactType.CORE_SCORE,
    ArtifactType.CORE_CANDIDATE,
    ArtifactType.GROUND_TRUTH_ANCHOR,
    ArtifactType.EDGE_CONNECTION,
    ArtifactType.GEOMETRY_LOOP_ESTIMATE,
    ArtifactType.DEFECT_LOOP_ESTIMATE,
}
_CALIBRATION_INPUT_TYPES = {
    ArtifactType.HYPOTHESIS_REGISTRY,
    ArtifactType.CONTEXT_BANK,
    *_CALIBRATION_EVIDENCE_TYPES,
}
_CONFIRMATION_EVIDENCE_TYPES = {
    *_CALIBRATION_EVIDENCE_TYPES,
}
_ORDER_PARAMETER_HYPOTHESES = {
    HypothesisId.F2_LOCAL_COVARIANT_SECTION,
    HypothesisId.F3_GLOBAL_PLANE_SECTION,
    HypothesisId.F4_SPIN_TWO_ANISOTROPY,
}
_DEFECT_CLAIMS_BY_HYPOTHESIS = {
    HypothesisId.F2_LOCAL_COVARIANT_SECTION: {
        ClaimLevel.LEVEL_0,
        ClaimLevel.LEVEL_1D,
        ClaimLevel.LEVEL_2T,
    },
    HypothesisId.F3_GLOBAL_PLANE_SECTION: {
        ClaimLevel.LEVEL_0,
        ClaimLevel.LEVEL_1D,
    },
    HypothesisId.F4_SPIN_TWO_ANISOTROPY: {
        ClaimLevel.LEVEL_0,
        ClaimLevel.LEVEL_1D,
        ClaimLevel.LEVEL_2T,
    },
}
_SELECTION_CLAIMS_BY_HYPOTHESIS = {
    HypothesisId.F0_SUPPORT: {
        ClaimLevel.LEVEL_0,
        ClaimLevel.LEVEL_1G,
    },
    HypothesisId.F1_PROJECTOR_CONNECTION: {
        ClaimLevel.LEVEL_0,
        ClaimLevel.LEVEL_1G,
        ClaimLevel.LEVEL_2G,
    },
    **_DEFECT_CLAIMS_BY_HYPOTHESIS,
}
_P0_COMMON_CALIBRATION_SELECTIONS = {
    "architecture_accounting_rule": {
        "explicit_component_accounting",
        "identity_no_subtraction",
    },
    "centering_rule": {
        "global_centering",
        "local_centering",
        "no_centering",
    },
    "fit_role": {
        "calibration_selection",
        "instrument_dev",
    },
    "input_tensor": {
        "accounted_response",
        "raw_state",
    },
    "observation_axis": {
        "layer_index",
        "token_position",
        "training_step",
    },
    "residual_rule": {
        "architecture_accounted_response",
        "centered_state",
        "raw_state",
    },
}
_P0_CALIBRATION_SELECTIONS_BY_HYPOTHESIS = {
    HypothesisId.F0_SUPPORT: {
        **_P0_COMMON_CALIBRATION_SELECTIONS,
        "estimator": {
            "entropy_effective_rank",
            "local_covariance_eigenvalues",
            "spectral_gap",
            "top_two_concentration",
        },
    },
    HypothesisId.F1_PROJECTOR_CONNECTION: {
        **_P0_COMMON_CALIBRATION_SELECTIONS,
        "estimator": {
            "local_rank_two_projector",
            "weighted_rank_two_projector",
        },
    },
    HypothesisId.F2_LOCAL_COVARIANT_SECTION: {
        **_P0_COMMON_CALIBRATION_SELECTIONS,
        "estimator": {
            "cross_fitted_local_frame",
            "weighted_local_frame",
        },
        "interpolation_rule": {
            "connection_transport_interpolation",
            "piecewise_geodesic_interpolation",
        },
        "lift_rule": {
            "connection_corrected_lift",
            "global_trivialization_lift",
        },
        "reference_rule": {
            "connection_defined_reference",
            "frozen_global_reference",
        },
        "trivialization_rule": {
            "frozen_global_trivialization",
            "local_frame_with_connection",
        },
    },
    HypothesisId.F3_GLOBAL_PLANE_SECTION: {
        **_P0_COMMON_CALIBRATION_SELECTIONS,
        "estimator": {
            "fit_split_global_plane",
            "predeclared_fixed_plane",
        },
        "interpolation_rule": {
            "piecewise_linear_projection",
            "projection_geodesic",
        },
    },
    HypothesisId.F4_SPIN_TWO_ANISOTROPY: {
        **_P0_COMMON_CALIBRATION_SELECTIONS,
        "estimator": {
            "local_traceless_tensor",
            "weighted_traceless_tensor",
        },
        "interpolation_rule": {
            "doubled_angle_geodesic",
            "piecewise_director",
        },
        "reference_rule": {
            "doubled_angle_reference",
            "reflection_accounted_reference",
        },
        "trivialization_rule": {
            "director_bundle_trivialization",
            "spin_two_connection_trivialization",
        },
    },
}
_P0_FIXED_SELECTIONS_BY_HYPOTHESIS = {
    HypothesisId.F0_SUPPORT: {},
    HypothesisId.F1_PROJECTOR_CONNECTION: {},
    HypothesisId.F2_LOCAL_COVARIANT_SECTION: {},
    HypothesisId.F3_GLOBAL_PLANE_SECTION: {
        "lift_rule": {"global_plane_direct_lift"},
        "reference_rule": {"fit_split_orientation_reference"},
        "trivialization_rule": {
            "global_or_fixed_plane_trivialization"
        },
    },
    HypothesisId.F4_SPIN_TWO_ANISOTROPY: {
        "lift_rule": {"spin_two_doubled_angle_lift"},
    },
}


class InstrumentArtifact(Protocol):
    """Structural protocol shared by every canonical artifact record."""

    artifact_id: str
    schema_version: ClassVar[str]
    artifact_type: ClassVar[ArtifactType]

    def to_dict(self) -> dict[str, object]: ...

    @property
    def canonical_bytes(self) -> bytes: ...

    @property
    def canonical_sha256(self) -> str: ...


class _CanonicalArtifact:
    schema_version: ClassVar[str]
    artifact_type: ClassVar[ArtifactType]

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_dict())

    @property
    def canonical_sha256(self) -> str:
        return canonical_json_sha256(self.to_dict())

    def _header(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "artifact_type": self.artifact_type.value,
            "artifact_id": self.artifact_id,
        }


def _validate_id(value: object, *, label: str = "artifact_id") -> str:
    return require_slug(value, label=label)


def _require_git_sha1(value: object, *, label: str) -> str:
    text = require_string(value, label=label)
    if _GIT_SHA1.fullmatch(text) is None:
        raise ContractValidationError(
            f"{label} must be a lowercase 40-character Git SHA-1"
        )
    return text


def _validate_claim(
    value: object,
    *,
    allowed: set[ClaimLevel],
    label: str = "claim_ceiling",
) -> ClaimLevel:
    if not isinstance(value, ClaimLevel):
        raise TypeError(f"{label} must be a ClaimLevel")
    if value not in allowed:
        raise ContractValidationError(
            f"{label} {value.value!r} exceeds this artifact contract"
        )
    return value


def _parse_claim(
    value: object,
    *,
    allowed: set[ClaimLevel],
    label: str = "claim_ceiling",
) -> ClaimLevel:
    claim = enum_from_value(ClaimLevel, value, label=label)
    return _validate_claim(claim, allowed=allowed, label=label)


def _validate_defect_claim(
    hypothesis_id: object,
    claim_ceiling: object,
) -> ClaimLevel:
    if not isinstance(hypothesis_id, HypothesisId):
        raise TypeError("hypothesis_id must be a HypothesisId")
    if hypothesis_id not in _ORDER_PARAMETER_HYPOTHESES:
        raise ContractValidationError(
            "defect artifacts require F2, F3, or F4"
        )
    return _validate_claim(
        claim_ceiling,
        allowed=_DEFECT_CLAIMS_BY_HYPOTHESIS[hypothesis_id],
    )


def _ref(
    value: object,
    *,
    expected: ArtifactType | set[ArtifactType],
    label: str,
) -> ArtifactRef:
    reference = (
        value
        if isinstance(value, ArtifactRef)
        else ArtifactRef.from_dict(require_mapping(value, label=label))
    )
    allowed = {expected} if isinstance(expected, ArtifactType) else expected
    if reference.artifact_type not in allowed:
        raise ContractValidationError(
            f"{label} must reference one of "
            f"{sorted(item.value for item in allowed)!r}"
        )
    return reference


def _payload(
    value: object,
    *,
    label: str,
    allowed_kinds: set[PayloadKind] | None = None,
) -> PayloadRef:
    payload = (
        value
        if isinstance(value, PayloadRef)
        else PayloadRef.from_dict(require_mapping(value, label=label))
    )
    if allowed_kinds is not None and payload.kind not in allowed_kinds:
        raise ContractValidationError(
            f"{label} payload kind must be one of "
            f"{sorted(item.value for item in allowed_kinds)!r}"
        )
    return payload


def _choice(value: object, *, label: str) -> RuleChoice:
    if isinstance(value, RuleChoice):
        return value
    return RuleChoice.from_dict(require_mapping(value, label=label))


def _header_from_dict(
    value: Mapping[str, object],
    *,
    schema_version: str,
    artifact_type: ArtifactType,
    fields: set[str],
    label: str,
) -> str:
    document = require_mapping(value, label=label)
    exact_keys(
        document,
        {"schema_version", "artifact_type", "artifact_id", *fields},
        label=label,
    )
    if document["schema_version"] != schema_version:
        raise ContractValidationError(
            f"{label} schema_version is unsupported"
        )
    if document["artifact_type"] != artifact_type.value:
        raise ContractValidationError(
            f"{label} artifact_type differs from its schema"
        )
    return _validate_id(document["artifact_id"])


def _sorted_strings(
    values: tuple[str, ...],
    *,
    label: str,
    nonempty: bool = False,
) -> tuple[str, ...]:
    if not isinstance(values, tuple):
        raise TypeError(f"{label} must be a tuple")
    checked = tuple(
        require_slug(value, label=f"{label}[{index}]")
        for index, value in enumerate(values)
    )
    if nonempty and not checked:
        raise ContractValidationError(f"{label} must not be empty")
    if tuple(sorted(set(checked))) != checked:
        raise ContractValidationError(
            f"{label} must be unique and sorted"
        )
    return checked


def _parse_sorted_strings(
    value: object,
    *,
    label: str,
    nonempty: bool = False,
) -> tuple[str, ...]:
    return string_tuple_from_list(
        value,
        label=label,
        require_nonempty=nonempty,
        require_canonical_order=True,
        require_slugs=True,
    )


def _sorted_refs(
    values: tuple[ArtifactRef, ...],
    *,
    label: str,
    allowed: set[ArtifactType],
) -> tuple[ArtifactRef, ...]:
    if not isinstance(values, tuple):
        raise TypeError(f"{label} must be a tuple")
    checked: list[ArtifactRef] = []
    for index, value in enumerate(values):
        checked.append(
            _ref(
                value,
                expected=allowed,
                label=f"{label}[{index}]",
            )
        )
    keys = [
        (
            value.artifact_type.value,
            value.schema_version,
            value.artifact_id,
            value.canonical_sha256,
        )
        for value in checked
    ]
    if keys != sorted(set(keys)):
        raise ContractValidationError(
            f"{label} must be unique and canonically sorted"
        )
    return tuple(checked)


def _parse_sorted_refs(
    value: object,
    *,
    label: str,
    allowed: set[ArtifactType],
) -> tuple[ArtifactRef, ...]:
    if not isinstance(value, list):
        raise ContractValidationError(f"{label} must be a list")
    refs = tuple(
        _ref(
            item,
            expected=allowed,
            label=f"{label}[{index}]",
        )
        for index, item in enumerate(value)
    )
    return _sorted_refs(refs, label=label, allowed=allowed)


def _reason_codes(values: tuple[str, ...]) -> tuple[str, ...]:
    return _sorted_strings(values, label="reason_codes")


def _parse_reason_codes(value: object) -> tuple[str, ...]:
    return _parse_sorted_strings(value, label="reason_codes")


def _require_payload_rows(
    payloads: tuple[PayloadRef, ...],
    *,
    row_identity_sha256: str,
    label: str,
    allowed_kinds: set[PayloadKind] | None = None,
) -> None:
    kinds = (
        {PayloadKind.ARRAY}
        if allowed_kinds is None
        else allowed_kinds
    )
    row_counts: list[int] = []
    for index, payload_ref in enumerate(payloads):
        if not isinstance(payload_ref, PayloadRef):
            raise TypeError(f"{label}[{index}] must be a PayloadRef")
        _payload(
            payload_ref,
            label=f"{label}[{index}]",
            allowed_kinds=kinds,
        )
        if payload_ref.row_identity_sha256 != row_identity_sha256:
            raise ContractValidationError(
                f"{label}[{index}] must bind the artifact row identity"
            )
        if payload_ref.kind is PayloadKind.ARRAY:
            assert payload_ref.shape is not None
            row_counts.append(payload_ref.shape[0])
        else:
            assert payload_ref.record_count is not None
            row_counts.append(payload_ref.record_count)
    if row_counts and len(set(row_counts)) != 1:
        raise ContractValidationError(
            f"{label} must declare one shared row count"
        )


@dataclass(frozen=True, slots=True)
class SyntheticLatticeContextBinding:
    """Model-free provenance and row identity for one synthetic lattice."""

    context_id: str
    source_id: str
    generator_revision: str
    generator_module_sha256: str
    generator_spec_sha256: str
    protocol_source_sha256: str
    protocol_canonical_sha256: str
    row_identity_sha256: str
    lattice_shape: tuple[int, int]
    boundary_rule: str
    claim_eligible: bool = False

    schema_version: ClassVar[str] = (
        "spirallens.instrument.synthetic-lattice-context-binding.v0.1"
    )
    context_kind: ClassVar[str] = "synthetic_lattice"

    def __post_init__(self) -> None:
        require_slug(self.context_id, label="context_id")
        require_slug(self.source_id, label="source_id")
        _require_git_sha1(
            self.generator_revision,
            label="generator_revision",
        )
        for label, digest in (
            ("generator_module_sha256", self.generator_module_sha256),
            ("generator_spec_sha256", self.generator_spec_sha256),
            ("protocol_source_sha256", self.protocol_source_sha256),
            ("protocol_canonical_sha256", self.protocol_canonical_sha256),
            ("row_identity_sha256", self.row_identity_sha256),
        ):
            require_sha256(digest, label=label)
        if (
            not isinstance(self.lattice_shape, tuple)
            or len(self.lattice_shape) != 2
        ):
            raise ContractValidationError(
                "lattice_shape must be a two-dimensional tuple"
            )
        for index, extent in enumerate(self.lattice_shape):
            require_plain_int(
                extent,
                label=f"lattice_shape[{index}]",
                minimum=1,
            )
        if self.boundary_rule not in _SYNTHETIC_LATTICE_BOUNDARY_RULES:
            raise ContractValidationError(
                "boundary_rule must be an explicitly supported synthetic "
                "lattice boundary rule"
            )
        if self.claim_eligible is not False:
            raise ContractValidationError(
                "synthetic lattice contexts cannot be claim eligible"
            )

    @property
    def site_count(self) -> int:
        return self.lattice_shape[0] * self.lattice_shape[1]

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "context_kind": self.context_kind,
            "context_id": self.context_id,
            "source_id": self.source_id,
            "generator_revision": self.generator_revision,
            "generator_module_sha256": self.generator_module_sha256,
            "generator_spec_sha256": self.generator_spec_sha256,
            "protocol_source_sha256": self.protocol_source_sha256,
            "protocol_canonical_sha256": self.protocol_canonical_sha256,
            "row_identity_sha256": self.row_identity_sha256,
            "lattice_shape": list(self.lattice_shape),
            "boundary_rule": self.boundary_rule,
            "claim_eligible": self.claim_eligible,
        }

    @classmethod
    def from_dict(
        cls,
        value: Mapping[str, object],
    ) -> "SyntheticLatticeContextBinding":
        document = require_mapping(
            value,
            label="SyntheticLatticeContextBinding",
        )
        exact_keys(
            document,
            {
                "schema_version",
                "context_kind",
                "context_id",
                "source_id",
                "generator_revision",
                "generator_module_sha256",
                "generator_spec_sha256",
                "protocol_source_sha256",
                "protocol_canonical_sha256",
                "row_identity_sha256",
                "lattice_shape",
                "boundary_rule",
                "claim_eligible",
            },
            label="SyntheticLatticeContextBinding",
        )
        if document["schema_version"] != cls.schema_version:
            raise ContractValidationError(
                "SyntheticLatticeContextBinding schema_version is unsupported"
            )
        if document["context_kind"] != cls.context_kind:
            raise ContractValidationError(
                "SyntheticLatticeContextBinding context_kind is unsupported"
            )
        lattice_shape = document["lattice_shape"]
        if not isinstance(lattice_shape, list) or len(lattice_shape) != 2:
            raise ContractValidationError(
                "lattice_shape must be a two-dimensional list"
            )
        return cls(
            context_id=require_slug(
                document["context_id"],
                label="context_id",
            ),
            source_id=require_slug(
                document["source_id"],
                label="source_id",
            ),
            generator_revision=_require_git_sha1(
                document["generator_revision"],
                label="generator_revision",
            ),
            generator_module_sha256=require_sha256(
                document["generator_module_sha256"],
                label="generator_module_sha256",
            ),
            generator_spec_sha256=require_sha256(
                document["generator_spec_sha256"],
                label="generator_spec_sha256",
            ),
            protocol_source_sha256=require_sha256(
                document["protocol_source_sha256"],
                label="protocol_source_sha256",
            ),
            protocol_canonical_sha256=require_sha256(
                document["protocol_canonical_sha256"],
                label="protocol_canonical_sha256",
            ),
            row_identity_sha256=require_sha256(
                document["row_identity_sha256"],
                label="row_identity_sha256",
            ),
            lattice_shape=tuple(
                require_plain_int(
                    extent,
                    label=f"lattice_shape[{index}]",
                    minimum=1,
                )
                for index, extent in enumerate(lattice_shape)
            ),
            boundary_rule=require_slug(
                document["boundary_rule"],
                label="boundary_rule",
            ),
            claim_eligible=require_bool(
                document["claim_eligible"],
                label="claim_eligible",
            ),
        )


@dataclass(frozen=True, slots=True)
class SubstrateBinding(_CanonicalArtifact):
    artifact_id: str
    role: FitRole
    evolution_axis: EvolutionAxis
    row_identity_sha256: str
    context_bank: ArtifactRef
    vertex_identities: PayloadRef
    observation_identities: PayloadRef
    states: PayloadRef
    accounted_response: PayloadRef
    mask: PayloadRef
    preprocessing_fit: PayloadRef

    schema_version: ClassVar[str] = SUBSTRATE_BINDING_SCHEMA
    artifact_type: ClassVar[ArtifactType] = ArtifactType.SUBSTRATE_BINDING

    def __post_init__(self) -> None:
        _validate_id(self.artifact_id)
        if not isinstance(self.role, FitRole):
            raise TypeError("role must be a FitRole")
        if not isinstance(self.evolution_axis, EvolutionAxis):
            raise TypeError("evolution_axis must be an EvolutionAxis")
        if self.evolution_axis is EvolutionAxis.SYNTHETIC_LATTICE:
            raise ContractValidationError(
                "synthetic_lattice requires SyntheticLatticeSubstrateBinding"
            )
        require_sha256(
            self.row_identity_sha256,
            label="row_identity_sha256",
        )
        _ref(
            self.context_bank,
            expected=ArtifactType.CONTEXT_BANK,
            label="context_bank",
        )
        _payload(self.preprocessing_fit, label="preprocessing_fit")
        _require_payload_rows(
            (
                self.vertex_identities,
                self.observation_identities,
                self.states,
                self.accounted_response,
                self.mask,
            ),
            row_identity_sha256=self.row_identity_sha256,
            label="substrate payloads",
        )

    def to_dict(self) -> dict[str, object]:
        return {
            **self._header(),
            "role": self.role.value,
            "evolution_axis": self.evolution_axis.value,
            "row_identity_sha256": self.row_identity_sha256,
            "context_bank": self.context_bank.to_dict(),
            "vertex_identities": self.vertex_identities.to_dict(),
            "observation_identities": self.observation_identities.to_dict(),
            "states": self.states.to_dict(),
            "accounted_response": self.accounted_response.to_dict(),
            "mask": self.mask.to_dict(),
            "preprocessing_fit": self.preprocessing_fit.to_dict(),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> "SubstrateBinding":
        document = require_mapping(value, label="SubstrateBinding")
        artifact_id = _header_from_dict(
            document,
            schema_version=cls.schema_version,
            artifact_type=cls.artifact_type,
            fields={
                "role",
                "evolution_axis",
                "row_identity_sha256",
                "context_bank",
                "vertex_identities",
                "observation_identities",
                "states",
                "accounted_response",
                "mask",
                "preprocessing_fit",
            },
            label="SubstrateBinding",
        )
        return cls(
            artifact_id=artifact_id,
            role=enum_from_value(FitRole, document["role"], label="role"),
            evolution_axis=enum_from_value(
                EvolutionAxis,
                document["evolution_axis"],
                label="evolution_axis",
            ),
            row_identity_sha256=require_sha256(
                document["row_identity_sha256"],
                label="row_identity_sha256",
            ),
            context_bank=_ref(
                document["context_bank"],
                expected=ArtifactType.CONTEXT_BANK,
                label="context_bank",
            ),
            vertex_identities=_payload(
                document["vertex_identities"],
                label="vertex_identities",
            ),
            observation_identities=_payload(
                document["observation_identities"],
                label="observation_identities",
            ),
            states=_payload(document["states"], label="states"),
            accounted_response=_payload(
                document["accounted_response"],
                label="accounted_response",
            ),
            mask=_payload(document["mask"], label="mask"),
            preprocessing_fit=_payload(
                document["preprocessing_fit"],
                label="preprocessing_fit",
            ),
        )


@dataclass(frozen=True, slots=True)
class SyntheticLatticeSubstrateBinding(_CanonicalArtifact):
    """Instrument-development substrate with no model or tokenizer binding."""

    artifact_id: str
    role: FitRole
    evolution_axis: EvolutionAxis
    row_identity_sha256: str
    synthetic_context: SyntheticLatticeContextBinding
    vertex_identities: PayloadRef
    observation_identities: PayloadRef
    states: PayloadRef
    accounted_response: PayloadRef
    mask: PayloadRef
    preprocessing_fit: PayloadRef

    schema_version: ClassVar[str] = (
        SYNTHETIC_LATTICE_SUBSTRATE_BINDING_SCHEMA_VERSION
    )
    artifact_type: ClassVar[ArtifactType] = ArtifactType.SUBSTRATE_BINDING

    def __post_init__(self) -> None:
        _validate_id(self.artifact_id)
        if self.role is not FitRole.INSTRUMENT_DEV:
            raise ContractValidationError(
                "synthetic lattice substrates require role=instrument_dev"
            )
        if self.evolution_axis is not EvolutionAxis.SYNTHETIC_LATTICE:
            raise ContractValidationError(
                "synthetic lattice substrates require "
                "evolution_axis=synthetic_lattice"
            )
        require_sha256(
            self.row_identity_sha256,
            label="row_identity_sha256",
        )
        if not isinstance(
            self.synthetic_context,
            SyntheticLatticeContextBinding,
        ):
            raise TypeError(
                "synthetic_context must be a "
                "SyntheticLatticeContextBinding"
            )
        if (
            self.synthetic_context.row_identity_sha256
            != self.row_identity_sha256
        ):
            raise ContractValidationError(
                "synthetic_context must bind the substrate row identity"
            )
        _payload(self.preprocessing_fit, label="preprocessing_fit")
        _require_payload_rows(
            (
                self.vertex_identities,
                self.observation_identities,
                self.states,
                self.accounted_response,
                self.mask,
            ),
            row_identity_sha256=self.row_identity_sha256,
            label="substrate payloads",
        )
        assert self.states.shape is not None
        if self.states.shape[0] != self.synthetic_context.site_count:
            raise ContractValidationError(
                "synthetic lattice site count must equal substrate row count"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            **self._header(),
            "role": self.role.value,
            "evolution_axis": self.evolution_axis.value,
            "row_identity_sha256": self.row_identity_sha256,
            "synthetic_context": self.synthetic_context.to_dict(),
            "vertex_identities": self.vertex_identities.to_dict(),
            "observation_identities": self.observation_identities.to_dict(),
            "states": self.states.to_dict(),
            "accounted_response": self.accounted_response.to_dict(),
            "mask": self.mask.to_dict(),
            "preprocessing_fit": self.preprocessing_fit.to_dict(),
        }

    @classmethod
    def from_dict(
        cls,
        value: Mapping[str, object],
    ) -> "SyntheticLatticeSubstrateBinding":
        document = require_mapping(
            value,
            label="SyntheticLatticeSubstrateBinding",
        )
        artifact_id = _header_from_dict(
            document,
            schema_version=cls.schema_version,
            artifact_type=cls.artifact_type,
            fields={
                "role",
                "evolution_axis",
                "row_identity_sha256",
                "synthetic_context",
                "vertex_identities",
                "observation_identities",
                "states",
                "accounted_response",
                "mask",
                "preprocessing_fit",
            },
            label="SyntheticLatticeSubstrateBinding",
        )
        return cls(
            artifact_id=artifact_id,
            role=enum_from_value(FitRole, document["role"], label="role"),
            evolution_axis=enum_from_value(
                EvolutionAxis,
                document["evolution_axis"],
                label="evolution_axis",
            ),
            row_identity_sha256=require_sha256(
                document["row_identity_sha256"],
                label="row_identity_sha256",
            ),
            synthetic_context=SyntheticLatticeContextBinding.from_dict(
                require_mapping(
                    document["synthetic_context"],
                    label="synthetic_context",
                )
            ),
            vertex_identities=_payload(
                document["vertex_identities"],
                label="vertex_identities",
            ),
            observation_identities=_payload(
                document["observation_identities"],
                label="observation_identities",
            ),
            states=_payload(document["states"], label="states"),
            accounted_response=_payload(
                document["accounted_response"],
                label="accounted_response",
            ),
            mask=_payload(document["mask"], label="mask"),
            preprocessing_fit=_payload(
                document["preprocessing_fit"],
                label="preprocessing_fit",
            ),
        )


SubstrateBindingValue: TypeAlias = (
    SubstrateBinding | SyntheticLatticeSubstrateBinding
)


@dataclass(frozen=True, slots=True)
class GraphConstructionSpec(_CanonicalArtifact):
    artifact_id: str
    substrate: ArtifactRef
    purpose: str
    family: RuleChoice
    metric: RuleChoice
    scale: RuleChoice
    constructor_id: str
    deterministic_tie_policy: str
    allowed_role: FitRole

    schema_version: ClassVar[str] = GRAPH_CONSTRUCTION_SPEC_SCHEMA
    artifact_type: ClassVar[ArtifactType] = (
        ArtifactType.GRAPH_CONSTRUCTION_SPEC
    )

    def __post_init__(self) -> None:
        _validate_id(self.artifact_id)
        _ref(
            self.substrate,
            expected=ArtifactType.SUBSTRATE_BINDING,
            label="substrate",
        )
        if self.purpose not in _GRAPH_PURPOSES:
            raise ContractValidationError("purpose is not a graph purpose")
        for label, choice in (
            ("family", self.family),
            ("metric", self.metric),
            ("scale", self.scale),
        ):
            if not isinstance(choice, RuleChoice):
                raise TypeError(f"{label} must be a RuleChoice")
        for choice, expected_family_id in (
            (self.family, "graph_family"),
            (self.metric, "graph_metric"),
            (self.scale, "graph_scale"),
        ):
            if choice.family_id != expected_family_id:
                raise ContractValidationError(
                    f"{expected_family_id} choice has the wrong family_id"
                )
        require_slug(self.constructor_id, label="constructor_id")
        require_slug(
            self.deterministic_tie_policy,
            label="deterministic_tie_policy",
        )
        if not isinstance(self.allowed_role, FitRole):
            raise TypeError("allowed_role must be a FitRole")
        development_resolutions = tuple(
            choice.resolution is ResolutionState.INSTRUMENT_DEV_EXECUTED
            for choice in (self.family, self.metric, self.scale)
        )
        if any(development_resolutions) and (
            not all(development_resolutions)
            or self.allowed_role is not FitRole.INSTRUMENT_DEV
        ):
            raise ContractValidationError(
                "instrument_dev_executed graph choices must cover family, "
                "metric, and scale on an instrument_dev graph"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            **self._header(),
            "substrate": self.substrate.to_dict(),
            "purpose": self.purpose,
            "family": self.family.to_dict(),
            "metric": self.metric.to_dict(),
            "scale": self.scale.to_dict(),
            "constructor_id": self.constructor_id,
            "deterministic_tie_policy": self.deterministic_tie_policy,
            "allowed_role": self.allowed_role.value,
        }

    @classmethod
    def from_dict(
        cls,
        value: Mapping[str, object],
    ) -> "GraphConstructionSpec":
        document = require_mapping(value, label="GraphConstructionSpec")
        artifact_id = _header_from_dict(
            document,
            schema_version=cls.schema_version,
            artifact_type=cls.artifact_type,
            fields={
                "substrate",
                "purpose",
                "family",
                "metric",
                "scale",
                "constructor_id",
                "deterministic_tie_policy",
                "allowed_role",
            },
            label="GraphConstructionSpec",
        )
        return cls(
            artifact_id=artifact_id,
            substrate=_ref(
                document["substrate"],
                expected=ArtifactType.SUBSTRATE_BINDING,
                label="substrate",
            ),
            purpose=require_string(document["purpose"], label="purpose"),
            family=_choice(document["family"], label="family"),
            metric=_choice(document["metric"], label="metric"),
            scale=_choice(document["scale"], label="scale"),
            constructor_id=require_slug(
                document["constructor_id"],
                label="constructor_id",
            ),
            deterministic_tie_policy=require_slug(
                document["deterministic_tie_policy"],
                label="deterministic_tie_policy",
            ),
            allowed_role=enum_from_value(
                FitRole,
                document["allowed_role"],
                label="allowed_role",
            ),
        )


@dataclass(frozen=True, slots=True)
class CandidateGraph(_CanonicalArtifact):
    artifact_id: str
    substrate: ArtifactRef
    specification: ArtifactRef
    vertex_order_sha256: str
    edge_order_sha256: str
    cycle_order_sha256: str
    vertices: PayloadRef
    canonical_edges: PayloadRef
    weights: PayloadRef
    connected_components: PayloadRef
    degree_distribution: PayloadRef
    two_core: PayloadRef
    cycle_support: PayloadRef

    schema_version: ClassVar[str] = CANDIDATE_GRAPH_SCHEMA
    artifact_type: ClassVar[ArtifactType] = ArtifactType.CANDIDATE_GRAPH

    def __post_init__(self) -> None:
        _validate_id(self.artifact_id)
        _ref(
            self.substrate,
            expected=ArtifactType.SUBSTRATE_BINDING,
            label="substrate",
        )
        _ref(
            self.specification,
            expected=ArtifactType.GRAPH_CONSTRUCTION_SPEC,
            label="specification",
        )
        require_sha256(
            self.vertex_order_sha256,
            label="vertex_order_sha256",
        )
        require_sha256(
            self.edge_order_sha256,
            label="edge_order_sha256",
        )
        require_sha256(
            self.cycle_order_sha256,
            label="cycle_order_sha256",
        )
        _require_payload_rows(
            (
                self.vertices,
                self.connected_components,
                self.degree_distribution,
                self.two_core,
            ),
            row_identity_sha256=self.vertex_order_sha256,
            label="vertex-ordered graph payloads",
        )
        _require_payload_rows(
            (self.canonical_edges, self.weights),
            row_identity_sha256=self.edge_order_sha256,
            label="edge-ordered graph payloads",
        )
        _require_payload_rows(
            (self.cycle_support,),
            row_identity_sha256=self.cycle_order_sha256,
            label="cycle-ordered graph payloads",
        )

    def to_dict(self) -> dict[str, object]:
        return {
            **self._header(),
            "substrate": self.substrate.to_dict(),
            "specification": self.specification.to_dict(),
            "vertex_order_sha256": self.vertex_order_sha256,
            "edge_order_sha256": self.edge_order_sha256,
            "cycle_order_sha256": self.cycle_order_sha256,
            "vertices": self.vertices.to_dict(),
            "canonical_edges": self.canonical_edges.to_dict(),
            "weights": self.weights.to_dict(),
            "connected_components": self.connected_components.to_dict(),
            "degree_distribution": self.degree_distribution.to_dict(),
            "two_core": self.two_core.to_dict(),
            "cycle_support": self.cycle_support.to_dict(),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> "CandidateGraph":
        document = require_mapping(value, label="CandidateGraph")
        payload_fields = {
            "vertices",
            "canonical_edges",
            "weights",
            "connected_components",
            "degree_distribution",
            "two_core",
            "cycle_support",
        }
        artifact_id = _header_from_dict(
            document,
            schema_version=cls.schema_version,
            artifact_type=cls.artifact_type,
            fields={
                "substrate",
                "specification",
                "vertex_order_sha256",
                "edge_order_sha256",
                "cycle_order_sha256",
                *payload_fields,
            },
            label="CandidateGraph",
        )
        parsed = {
            name: _payload(document[name], label=name)
            for name in payload_fields
        }
        return cls(
            artifact_id=artifact_id,
            substrate=_ref(
                document["substrate"],
                expected=ArtifactType.SUBSTRATE_BINDING,
                label="substrate",
            ),
            specification=_ref(
                document["specification"],
                expected=ArtifactType.GRAPH_CONSTRUCTION_SPEC,
                label="specification",
            ),
            vertex_order_sha256=require_sha256(
                document["vertex_order_sha256"],
                label="vertex_order_sha256",
            ),
            edge_order_sha256=require_sha256(
                document["edge_order_sha256"],
                label="edge_order_sha256",
            ),
            cycle_order_sha256=require_sha256(
                document["cycle_order_sha256"],
                label="cycle_order_sha256",
            ),
            **parsed,
        )


@dataclass(frozen=True, slots=True)
class SupportDiagnostic(_CanonicalArtifact):
    artifact_id: str
    substrate: ArtifactRef
    row_identity_sha256: str
    scalar_definition_id: str
    neighborhood_specification: ArtifactRef
    fit_role: FitRole
    values: PayloadRef
    uncertainty: PayloadRef
    support: PayloadRef
    pointwise_reason_codes: PayloadRef
    claim_ceiling: ClaimLevel

    schema_version: ClassVar[str] = SUPPORT_DIAGNOSTIC_SCHEMA
    artifact_type: ClassVar[ArtifactType] = ArtifactType.SUPPORT_DIAGNOSTIC

    def __post_init__(self) -> None:
        _validate_id(self.artifact_id)
        _ref(
            self.substrate,
            expected=ArtifactType.SUBSTRATE_BINDING,
            label="substrate",
        )
        require_sha256(
            self.row_identity_sha256,
            label="row_identity_sha256",
        )
        require_slug(
            self.scalar_definition_id,
            label="scalar_definition_id",
        )
        _ref(
            self.neighborhood_specification,
            expected={
                ArtifactType.GRAPH_CONSTRUCTION_SPEC,
                ArtifactType.CANDIDATE_GRAPH,
            },
            label="neighborhood_specification",
        )
        if not isinstance(self.fit_role, FitRole):
            raise TypeError("fit_role must be a FitRole")
        _require_payload_rows(
            (
                self.values,
                self.uncertainty,
                self.support,
                self.pointwise_reason_codes,
            ),
            row_identity_sha256=self.row_identity_sha256,
            label="support-diagnostic payloads",
        )
        _validate_claim(
            self.claim_ceiling,
            allowed={ClaimLevel.LEVEL_0, ClaimLevel.LEVEL_1G},
        )

    def to_dict(self) -> dict[str, object]:
        return {
            **self._header(),
            "substrate": self.substrate.to_dict(),
            "row_identity_sha256": self.row_identity_sha256,
            "scalar_definition_id": self.scalar_definition_id,
            "neighborhood_specification": (
                self.neighborhood_specification.to_dict()
            ),
            "fit_role": self.fit_role.value,
            "values": self.values.to_dict(),
            "uncertainty": self.uncertainty.to_dict(),
            "support": self.support.to_dict(),
            "pointwise_reason_codes": self.pointwise_reason_codes.to_dict(),
            "claim_ceiling": self.claim_ceiling.value,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> "SupportDiagnostic":
        document = require_mapping(value, label="SupportDiagnostic")
        artifact_id = _header_from_dict(
            document,
            schema_version=cls.schema_version,
            artifact_type=cls.artifact_type,
            fields={
                "substrate",
                "row_identity_sha256",
                "scalar_definition_id",
                "neighborhood_specification",
                "fit_role",
                "values",
                "uncertainty",
                "support",
                "pointwise_reason_codes",
                "claim_ceiling",
            },
            label="SupportDiagnostic",
        )
        return cls(
            artifact_id=artifact_id,
            substrate=_ref(
                document["substrate"],
                expected=ArtifactType.SUBSTRATE_BINDING,
                label="substrate",
            ),
            row_identity_sha256=require_sha256(
                document["row_identity_sha256"],
                label="row_identity_sha256",
            ),
            scalar_definition_id=require_slug(
                document["scalar_definition_id"],
                label="scalar_definition_id",
            ),
            neighborhood_specification=_ref(
                document["neighborhood_specification"],
                expected={
                    ArtifactType.GRAPH_CONSTRUCTION_SPEC,
                    ArtifactType.CANDIDATE_GRAPH,
                },
                label="neighborhood_specification",
            ),
            fit_role=enum_from_value(
                FitRole,
                document["fit_role"],
                label="fit_role",
            ),
            values=_payload(document["values"], label="values"),
            uncertainty=_payload(
                document["uncertainty"],
                label="uncertainty",
            ),
            support=_payload(document["support"], label="support"),
            pointwise_reason_codes=_payload(
                document["pointwise_reason_codes"],
                label="pointwise_reason_codes",
            ),
            claim_ceiling=_parse_claim(
                document["claim_ceiling"],
                allowed={ClaimLevel.LEVEL_0, ClaimLevel.LEVEL_1G},
            ),
        )


@dataclass(frozen=True, slots=True)
class GeometricFieldEstimate(_CanonicalArtifact):
    artifact_id: str
    hypothesis_registry: ArtifactRef
    substrate: ArtifactRef
    estimation_graph: ArtifactRef
    hypothesis_id: HypothesisId
    fit_receipt: PayloadRef
    row_identity_sha256: str
    projector_or_frame: PayloadRef
    eigenspectrum: PayloadRef
    support: PayloadRef
    gauge_law_id: str
    claim_ceiling: ClaimLevel

    schema_version: ClassVar[str] = GEOMETRIC_FIELD_ESTIMATE_SCHEMA
    artifact_type: ClassVar[ArtifactType] = (
        ArtifactType.GEOMETRIC_FIELD_ESTIMATE
    )

    def __post_init__(self) -> None:
        _validate_id(self.artifact_id)
        _ref(
            self.hypothesis_registry,
            expected=ArtifactType.HYPOTHESIS_REGISTRY,
            label="hypothesis_registry",
        )
        _ref(
            self.substrate,
            expected=ArtifactType.SUBSTRATE_BINDING,
            label="substrate",
        )
        _ref(
            self.estimation_graph,
            expected=ArtifactType.CANDIDATE_GRAPH,
            label="estimation_graph",
        )
        if self.hypothesis_id is not HypothesisId.F1_PROJECTOR_CONNECTION:
            raise ContractValidationError(
                "geometric fields require the F1 hypothesis"
            )
        _payload(self.fit_receipt, label="fit_receipt")
        require_sha256(
            self.row_identity_sha256,
            label="row_identity_sha256",
        )
        _require_payload_rows(
            (
                self.projector_or_frame,
                self.eigenspectrum,
                self.support,
            ),
            row_identity_sha256=self.row_identity_sha256,
            label="geometric-field payloads",
        )
        require_slug(self.gauge_law_id, label="gauge_law_id")
        _validate_claim(
            self.claim_ceiling,
            allowed={
                ClaimLevel.LEVEL_0,
                ClaimLevel.LEVEL_1G,
                ClaimLevel.LEVEL_2G,
            },
        )

    def to_dict(self) -> dict[str, object]:
        return {
            **self._header(),
            "branch": ScientificBranch.GEOMETRY.value,
            "hypothesis_registry": self.hypothesis_registry.to_dict(),
            "substrate": self.substrate.to_dict(),
            "estimation_graph": self.estimation_graph.to_dict(),
            "hypothesis_id": self.hypothesis_id.value,
            "fit_receipt": self.fit_receipt.to_dict(),
            "row_identity_sha256": self.row_identity_sha256,
            "projector_or_frame": self.projector_or_frame.to_dict(),
            "eigenspectrum": self.eigenspectrum.to_dict(),
            "support": self.support.to_dict(),
            "gauge_law_id": self.gauge_law_id,
            "claim_ceiling": self.claim_ceiling.value,
        }

    @classmethod
    def from_dict(
        cls,
        value: Mapping[str, object],
    ) -> "GeometricFieldEstimate":
        document = require_mapping(value, label="GeometricFieldEstimate")
        artifact_id = _header_from_dict(
            document,
            schema_version=cls.schema_version,
            artifact_type=cls.artifact_type,
            fields={
                "branch",
                "hypothesis_registry",
                "substrate",
                "estimation_graph",
                "hypothesis_id",
                "fit_receipt",
                "row_identity_sha256",
                "projector_or_frame",
                "eigenspectrum",
                "support",
                "gauge_law_id",
                "claim_ceiling",
            },
            label="GeometricFieldEstimate",
        )
        if document["branch"] != ScientificBranch.GEOMETRY.value:
            raise ContractValidationError(
                "GeometricFieldEstimate branch must be geometry"
            )
        return cls(
            artifact_id=artifact_id,
            hypothesis_registry=_ref(
                document["hypothesis_registry"],
                expected=ArtifactType.HYPOTHESIS_REGISTRY,
                label="hypothesis_registry",
            ),
            substrate=_ref(
                document["substrate"],
                expected=ArtifactType.SUBSTRATE_BINDING,
                label="substrate",
            ),
            estimation_graph=_ref(
                document["estimation_graph"],
                expected=ArtifactType.CANDIDATE_GRAPH,
                label="estimation_graph",
            ),
            hypothesis_id=enum_from_value(
                HypothesisId,
                document["hypothesis_id"],
                label="hypothesis_id",
            ),
            fit_receipt=_payload(
                document["fit_receipt"],
                label="fit_receipt",
            ),
            row_identity_sha256=require_sha256(
                document["row_identity_sha256"],
                label="row_identity_sha256",
            ),
            projector_or_frame=_payload(
                document["projector_or_frame"],
                label="projector_or_frame",
            ),
            eigenspectrum=_payload(
                document["eigenspectrum"],
                label="eigenspectrum",
            ),
            support=_payload(document["support"], label="support"),
            gauge_law_id=require_slug(
                document["gauge_law_id"],
                label="gauge_law_id",
            ),
            claim_ceiling=_parse_claim(
                document["claim_ceiling"],
                allowed={
                    ClaimLevel.LEVEL_0,
                    ClaimLevel.LEVEL_1G,
                    ClaimLevel.LEVEL_2G,
                },
            ),
        )


@dataclass(frozen=True, slots=True)
class OrderParameterSpec(_CanonicalArtifact):
    artifact_id: str
    hypothesis_registry: ArtifactRef
    substrate: ArtifactRef
    estimation_graph: ArtifactRef
    hypothesis_id: HypothesisId
    input_binding: PayloadRef
    fit_receipt: PayloadRef
    target_manifold_id: str
    gauge_law_id: str
    charge_group: RuleChoice
    amplitude_rule: RuleChoice
    identifiability_rule: RuleChoice
    interpolation_rule: RuleChoice
    lift_rule: RuleChoice
    trivialization_rule: RuleChoice
    reference_rule: RuleChoice
    forbidden_labels: tuple[str, ...]
    claim_ceiling: ClaimLevel

    schema_version: ClassVar[str] = ORDER_PARAMETER_SPEC_SCHEMA
    artifact_type: ClassVar[ArtifactType] = ArtifactType.ORDER_PARAMETER_SPEC

    def __post_init__(self) -> None:
        _validate_id(self.artifact_id)
        _ref(
            self.hypothesis_registry,
            expected=ArtifactType.HYPOTHESIS_REGISTRY,
            label="hypothesis_registry",
        )
        _ref(
            self.substrate,
            expected=ArtifactType.SUBSTRATE_BINDING,
            label="substrate",
        )
        _ref(
            self.estimation_graph,
            expected=ArtifactType.CANDIDATE_GRAPH,
            label="estimation_graph",
        )
        if self.hypothesis_id not in _ORDER_PARAMETER_HYPOTHESES:
            raise ContractValidationError(
                "order-parameter specs require F2, F3, or F4"
            )
        _payload(self.input_binding, label="input_binding")
        _payload(self.fit_receipt, label="fit_receipt")
        require_slug(self.target_manifold_id, label="target_manifold_id")
        require_slug(self.gauge_law_id, label="gauge_law_id")
        for label, choice in (
            ("charge_group", self.charge_group),
            ("amplitude_rule", self.amplitude_rule),
            ("identifiability_rule", self.identifiability_rule),
            ("interpolation_rule", self.interpolation_rule),
            ("lift_rule", self.lift_rule),
            ("trivialization_rule", self.trivialization_rule),
            ("reference_rule", self.reference_rule),
        ):
            if not isinstance(choice, RuleChoice):
                raise TypeError(f"{label} must be a RuleChoice")
            if choice.family_id != label:
                raise ContractValidationError(
                    f"{label} choice must use family_id={label!r}"
                )
            if (
                choice.resolution
                is ResolutionState.INSTRUMENT_DEV_EXECUTED
            ):
                raise ContractValidationError(
                    "instrument_dev_executed is reserved for "
                    "GraphConstructionSpec"
                )
        _sorted_strings(
            self.forbidden_labels,
            label="forbidden_labels",
            nonempty=True,
        )
        _validate_defect_claim(self.hypothesis_id, self.claim_ceiling)

    def to_dict(self) -> dict[str, object]:
        return {
            **self._header(),
            "branch": ScientificBranch.DEFECT.value,
            "hypothesis_registry": self.hypothesis_registry.to_dict(),
            "substrate": self.substrate.to_dict(),
            "estimation_graph": self.estimation_graph.to_dict(),
            "hypothesis_id": self.hypothesis_id.value,
            "input_binding": self.input_binding.to_dict(),
            "fit_receipt": self.fit_receipt.to_dict(),
            "target_manifold_id": self.target_manifold_id,
            "gauge_law_id": self.gauge_law_id,
            "charge_group": self.charge_group.to_dict(),
            "amplitude_rule": self.amplitude_rule.to_dict(),
            "identifiability_rule": self.identifiability_rule.to_dict(),
            "interpolation_rule": self.interpolation_rule.to_dict(),
            "lift_rule": self.lift_rule.to_dict(),
            "trivialization_rule": self.trivialization_rule.to_dict(),
            "reference_rule": self.reference_rule.to_dict(),
            "forbidden_labels": list(self.forbidden_labels),
            "claim_ceiling": self.claim_ceiling.value,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> "OrderParameterSpec":
        document = require_mapping(value, label="OrderParameterSpec")
        artifact_id = _header_from_dict(
            document,
            schema_version=cls.schema_version,
            artifact_type=cls.artifact_type,
            fields={
                "branch",
                "hypothesis_registry",
                "substrate",
                "estimation_graph",
                "hypothesis_id",
                "input_binding",
                "fit_receipt",
                "target_manifold_id",
                "gauge_law_id",
                "charge_group",
                "amplitude_rule",
                "identifiability_rule",
                "interpolation_rule",
                "lift_rule",
                "trivialization_rule",
                "reference_rule",
                "forbidden_labels",
                "claim_ceiling",
            },
            label="OrderParameterSpec",
        )
        if document["branch"] != ScientificBranch.DEFECT.value:
            raise ContractValidationError(
                "OrderParameterSpec branch must be defect"
            )
        return cls(
            artifact_id=artifact_id,
            hypothesis_registry=_ref(
                document["hypothesis_registry"],
                expected=ArtifactType.HYPOTHESIS_REGISTRY,
                label="hypothesis_registry",
            ),
            substrate=_ref(
                document["substrate"],
                expected=ArtifactType.SUBSTRATE_BINDING,
                label="substrate",
            ),
            estimation_graph=_ref(
                document["estimation_graph"],
                expected=ArtifactType.CANDIDATE_GRAPH,
                label="estimation_graph",
            ),
            hypothesis_id=enum_from_value(
                HypothesisId,
                document["hypothesis_id"],
                label="hypothesis_id",
            ),
            input_binding=_payload(
                document["input_binding"],
                label="input_binding",
            ),
            fit_receipt=_payload(
                document["fit_receipt"],
                label="fit_receipt",
            ),
            target_manifold_id=require_slug(
                document["target_manifold_id"],
                label="target_manifold_id",
            ),
            gauge_law_id=require_slug(
                document["gauge_law_id"],
                label="gauge_law_id",
            ),
            charge_group=_choice(
                document["charge_group"],
                label="charge_group",
            ),
            amplitude_rule=_choice(
                document["amplitude_rule"],
                label="amplitude_rule",
            ),
            identifiability_rule=_choice(
                document["identifiability_rule"],
                label="identifiability_rule",
            ),
            interpolation_rule=_choice(
                document["interpolation_rule"],
                label="interpolation_rule",
            ),
            lift_rule=_choice(document["lift_rule"], label="lift_rule"),
            trivialization_rule=_choice(
                document["trivialization_rule"],
                label="trivialization_rule",
            ),
            reference_rule=_choice(
                document["reference_rule"],
                label="reference_rule",
            ),
            forbidden_labels=_parse_sorted_strings(
                document["forbidden_labels"],
                label="forbidden_labels",
                nonempty=True,
            ),
            claim_ceiling=_parse_claim(
                document["claim_ceiling"],
                allowed={
                    ClaimLevel.LEVEL_0,
                    ClaimLevel.LEVEL_1D,
                    ClaimLevel.LEVEL_2T,
                },
            ),
        )


@dataclass(frozen=True, slots=True)
class OrderParameterField(_CanonicalArtifact):
    artifact_id: str
    specification: ArtifactRef
    hypothesis_id: HypothesisId
    substrate: ArtifactRef
    estimation_graph: ArtifactRef
    row_identity_sha256: str
    values: PayloadRef
    amplitude: PayloadRef
    frame_or_tensor: PayloadRef
    eigenspectrum: PayloadRef
    support: PayloadRef
    pointwise_reason_codes: PayloadRef
    claim_ceiling: ClaimLevel

    schema_version: ClassVar[str] = ORDER_PARAMETER_FIELD_SCHEMA
    artifact_type: ClassVar[ArtifactType] = ArtifactType.ORDER_PARAMETER_FIELD

    def __post_init__(self) -> None:
        _validate_id(self.artifact_id)
        _ref(
            self.specification,
            expected=ArtifactType.ORDER_PARAMETER_SPEC,
            label="specification",
        )
        if self.hypothesis_id not in _ORDER_PARAMETER_HYPOTHESES:
            raise ContractValidationError(
                "order-parameter fields require F2, F3, or F4"
            )
        _ref(
            self.substrate,
            expected=ArtifactType.SUBSTRATE_BINDING,
            label="substrate",
        )
        _ref(
            self.estimation_graph,
            expected=ArtifactType.CANDIDATE_GRAPH,
            label="estimation_graph",
        )
        require_sha256(
            self.row_identity_sha256,
            label="row_identity_sha256",
        )
        _require_payload_rows(
            (
                self.values,
                self.amplitude,
                self.frame_or_tensor,
                self.eigenspectrum,
                self.support,
                self.pointwise_reason_codes,
            ),
            row_identity_sha256=self.row_identity_sha256,
            label="order-parameter payloads",
        )
        _validate_defect_claim(self.hypothesis_id, self.claim_ceiling)

    def to_dict(self) -> dict[str, object]:
        return {
            **self._header(),
            "branch": ScientificBranch.DEFECT.value,
            "specification": self.specification.to_dict(),
            "hypothesis_id": self.hypothesis_id.value,
            "substrate": self.substrate.to_dict(),
            "estimation_graph": self.estimation_graph.to_dict(),
            "row_identity_sha256": self.row_identity_sha256,
            "values": self.values.to_dict(),
            "amplitude": self.amplitude.to_dict(),
            "frame_or_tensor": self.frame_or_tensor.to_dict(),
            "eigenspectrum": self.eigenspectrum.to_dict(),
            "support": self.support.to_dict(),
            "pointwise_reason_codes": self.pointwise_reason_codes.to_dict(),
            "claim_ceiling": self.claim_ceiling.value,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> "OrderParameterField":
        document = require_mapping(value, label="OrderParameterField")
        payload_fields = {
            "values",
            "amplitude",
            "frame_or_tensor",
            "eigenspectrum",
            "support",
            "pointwise_reason_codes",
        }
        artifact_id = _header_from_dict(
            document,
            schema_version=cls.schema_version,
            artifact_type=cls.artifact_type,
            fields={
                "branch",
                "specification",
                "hypothesis_id",
                "substrate",
                "estimation_graph",
                "row_identity_sha256",
                "claim_ceiling",
                *payload_fields,
            },
            label="OrderParameterField",
        )
        if document["branch"] != ScientificBranch.DEFECT.value:
            raise ContractValidationError(
                "OrderParameterField branch must be defect"
            )
        parsed = {
            name: _payload(document[name], label=name)
            for name in payload_fields
        }
        return cls(
            artifact_id=artifact_id,
            specification=_ref(
                document["specification"],
                expected=ArtifactType.ORDER_PARAMETER_SPEC,
                label="specification",
            ),
            hypothesis_id=enum_from_value(
                HypothesisId,
                document["hypothesis_id"],
                label="hypothesis_id",
            ),
            substrate=_ref(
                document["substrate"],
                expected=ArtifactType.SUBSTRATE_BINDING,
                label="substrate",
            ),
            estimation_graph=_ref(
                document["estimation_graph"],
                expected=ArtifactType.CANDIDATE_GRAPH,
                label="estimation_graph",
            ),
            row_identity_sha256=require_sha256(
                document["row_identity_sha256"],
                label="row_identity_sha256",
            ),
            claim_ceiling=enum_from_value(
                ClaimLevel,
                document["claim_ceiling"],
                label="claim_ceiling",
            ),
            **parsed,
        )


@dataclass(frozen=True, slots=True)
class GraphFreeBinding:
    mode: ClassVar[NeighborhoodMode] = NeighborhoodMode.GRAPH_FREE

    def to_dict(self) -> dict[str, object]:
        return {"mode": self.mode.value}


@dataclass(frozen=True, slots=True)
class InheritedFieldGraphBinding:
    candidate_graph: ArtifactRef
    mode: ClassVar[NeighborhoodMode] = (
        NeighborhoodMode.INHERIT_FIELD_ESTIMATION_GRAPH
    )

    def __post_init__(self) -> None:
        _ref(
            self.candidate_graph,
            expected=ArtifactType.CANDIDATE_GRAPH,
            label="candidate_graph",
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "mode": self.mode.value,
            "candidate_graph": self.candidate_graph.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class ExplicitCoreGraphBinding:
    graph_specification: ArtifactRef
    candidate_graph: ArtifactRef
    mode: ClassVar[NeighborhoodMode] = NeighborhoodMode.EXPLICIT_CORE_GRAPH

    def __post_init__(self) -> None:
        _ref(
            self.graph_specification,
            expected=ArtifactType.GRAPH_CONSTRUCTION_SPEC,
            label="graph_specification",
        )
        _ref(
            self.candidate_graph,
            expected=ArtifactType.CANDIDATE_GRAPH,
            label="candidate_graph",
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "mode": self.mode.value,
            "graph_specification": self.graph_specification.to_dict(),
            "candidate_graph": self.candidate_graph.to_dict(),
        }


CoreGraphBinding: TypeAlias = (
    GraphFreeBinding
    | InheritedFieldGraphBinding
    | ExplicitCoreGraphBinding
)


def core_graph_binding_from_dict(value: object) -> CoreGraphBinding:
    document = require_mapping(value, label="graph_binding")
    mode = enum_from_value(
        NeighborhoodMode,
        document.get("mode"),
        label="graph_binding.mode",
    )
    if mode is NeighborhoodMode.GRAPH_FREE:
        exact_keys(document, {"mode"}, label="graph_binding")
        return GraphFreeBinding()
    if mode is NeighborhoodMode.INHERIT_FIELD_ESTIMATION_GRAPH:
        exact_keys(
            document,
            {"mode", "candidate_graph"},
            label="graph_binding",
        )
        return InheritedFieldGraphBinding(
            candidate_graph=_ref(
                document["candidate_graph"],
                expected=ArtifactType.CANDIDATE_GRAPH,
                label="candidate_graph",
            )
        )
    exact_keys(
        document,
        {"mode", "graph_specification", "candidate_graph"},
        label="graph_binding",
    )
    return ExplicitCoreGraphBinding(
        graph_specification=_ref(
            document["graph_specification"],
            expected=ArtifactType.GRAPH_CONSTRUCTION_SPEC,
            label="graph_specification",
        ),
        candidate_graph=_ref(
            document["candidate_graph"],
            expected=ArtifactType.CANDIDATE_GRAPH,
            label="candidate_graph",
        ),
    )


@dataclass(frozen=True, slots=True)
class CoreScore(_CanonicalArtifact):
    artifact_id: str
    substrate: ArtifactRef
    order_parameter_spec: ArtifactRef
    order_parameter_field: ArtifactRef
    field_estimation_graph: ArtifactRef
    row_identity_sha256: str
    scalar_definition_id: str
    fit_role: FitRole
    singularity_rule_id: str
    graph_binding: CoreGraphBinding
    values: PayloadRef
    uncertainty: PayloadRef
    support: PayloadRef
    pointwise_reason_codes: PayloadRef
    charge_blind: bool
    claim_ceiling: ClaimLevel

    schema_version: ClassVar[str] = CORE_SCORE_SCHEMA
    artifact_type: ClassVar[ArtifactType] = ArtifactType.CORE_SCORE

    def __post_init__(self) -> None:
        _validate_id(self.artifact_id)
        _ref(
            self.substrate,
            expected=ArtifactType.SUBSTRATE_BINDING,
            label="substrate",
        )
        _ref(
            self.order_parameter_spec,
            expected=ArtifactType.ORDER_PARAMETER_SPEC,
            label="order_parameter_spec",
        )
        _ref(
            self.order_parameter_field,
            expected=ArtifactType.ORDER_PARAMETER_FIELD,
            label="order_parameter_field",
        )
        _ref(
            self.field_estimation_graph,
            expected=ArtifactType.CANDIDATE_GRAPH,
            label="field_estimation_graph",
        )
        require_sha256(
            self.row_identity_sha256,
            label="row_identity_sha256",
        )
        require_slug(
            self.scalar_definition_id,
            label="scalar_definition_id",
        )
        if not isinstance(self.fit_role, FitRole):
            raise TypeError("fit_role must be a FitRole")
        require_slug(self.singularity_rule_id, label="singularity_rule_id")
        if not isinstance(
            self.graph_binding,
            (
                GraphFreeBinding,
                InheritedFieldGraphBinding,
                ExplicitCoreGraphBinding,
            ),
        ):
            raise TypeError("graph_binding is invalid")
        if (
            isinstance(self.graph_binding, InheritedFieldGraphBinding)
            and self.graph_binding.candidate_graph
            != self.field_estimation_graph
        ):
            raise ContractValidationError(
                "inherited graph binding must equal "
                "field_estimation_graph"
            )
        _require_payload_rows(
            (
                self.values,
                self.uncertainty,
                self.support,
                self.pointwise_reason_codes,
            ),
            row_identity_sha256=self.row_identity_sha256,
            label="core-score payloads",
        )
        if self.charge_blind is not True:
            raise ContractValidationError("CoreScore must be charge-blind")
        _validate_claim(
            self.claim_ceiling,
            allowed={ClaimLevel.LEVEL_0, ClaimLevel.LEVEL_1D},
        )

    def to_dict(self) -> dict[str, object]:
        return {
            **self._header(),
            "branch": ScientificBranch.DEFECT.value,
            "substrate": self.substrate.to_dict(),
            "order_parameter_spec": self.order_parameter_spec.to_dict(),
            "order_parameter_field": self.order_parameter_field.to_dict(),
            "field_estimation_graph": self.field_estimation_graph.to_dict(),
            "row_identity_sha256": self.row_identity_sha256,
            "scalar_definition_id": self.scalar_definition_id,
            "fit_role": self.fit_role.value,
            "singularity_rule_id": self.singularity_rule_id,
            "graph_binding": self.graph_binding.to_dict(),
            "values": self.values.to_dict(),
            "uncertainty": self.uncertainty.to_dict(),
            "support": self.support.to_dict(),
            "pointwise_reason_codes": self.pointwise_reason_codes.to_dict(),
            "charge_blind": self.charge_blind,
            "claim_ceiling": self.claim_ceiling.value,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> "CoreScore":
        document = require_mapping(value, label="CoreScore")
        artifact_id = _header_from_dict(
            document,
            schema_version=cls.schema_version,
            artifact_type=cls.artifact_type,
            fields={
                "branch",
                "substrate",
                "order_parameter_spec",
                "order_parameter_field",
                "field_estimation_graph",
                "row_identity_sha256",
                "scalar_definition_id",
                "fit_role",
                "singularity_rule_id",
                "graph_binding",
                "values",
                "uncertainty",
                "support",
                "pointwise_reason_codes",
                "charge_blind",
                "claim_ceiling",
            },
            label="CoreScore",
        )
        if document["branch"] != ScientificBranch.DEFECT.value:
            raise ContractValidationError("CoreScore branch must be defect")
        return cls(
            artifact_id=artifact_id,
            substrate=_ref(
                document["substrate"],
                expected=ArtifactType.SUBSTRATE_BINDING,
                label="substrate",
            ),
            order_parameter_spec=_ref(
                document["order_parameter_spec"],
                expected=ArtifactType.ORDER_PARAMETER_SPEC,
                label="order_parameter_spec",
            ),
            order_parameter_field=_ref(
                document["order_parameter_field"],
                expected=ArtifactType.ORDER_PARAMETER_FIELD,
                label="order_parameter_field",
            ),
            field_estimation_graph=_ref(
                document["field_estimation_graph"],
                expected=ArtifactType.CANDIDATE_GRAPH,
                label="field_estimation_graph",
            ),
            row_identity_sha256=require_sha256(
                document["row_identity_sha256"],
                label="row_identity_sha256",
            ),
            scalar_definition_id=require_slug(
                document["scalar_definition_id"],
                label="scalar_definition_id",
            ),
            fit_role=enum_from_value(
                FitRole,
                document["fit_role"],
                label="fit_role",
            ),
            singularity_rule_id=require_slug(
                document["singularity_rule_id"],
                label="singularity_rule_id",
            ),
            graph_binding=core_graph_binding_from_dict(
                document["graph_binding"]
            ),
            values=_payload(document["values"], label="values"),
            uncertainty=_payload(
                document["uncertainty"],
                label="uncertainty",
            ),
            support=_payload(document["support"], label="support"),
            pointwise_reason_codes=_payload(
                document["pointwise_reason_codes"],
                label="pointwise_reason_codes",
            ),
            charge_blind=require_bool(
                document["charge_blind"],
                label="charge_blind",
            ),
            claim_ceiling=_parse_claim(
                document["claim_ceiling"],
                allowed={ClaimLevel.LEVEL_0, ClaimLevel.LEVEL_1D},
            ),
        )


@dataclass(frozen=True, slots=True)
class CoreCandidate(_CanonicalArtifact):
    artifact_id: str
    substrate: ArtifactRef
    core_score: ArtifactRef
    order_parameter_field: ArtifactRef
    field_estimation_graph: ArtifactRef
    row_identity_sha256: str
    localization_algorithm_id: str
    singularity_rule_id: str
    graph_binding: CoreGraphBinding
    localized_support: PayloadRef
    uncertainty: PayloadRef
    charge_blind: bool
    sealed_without_loop_observable_input: bool
    claim_ceiling: ClaimLevel

    schema_version: ClassVar[str] = CORE_CANDIDATE_SCHEMA
    artifact_type: ClassVar[ArtifactType] = ArtifactType.CORE_CANDIDATE

    def __post_init__(self) -> None:
        _validate_id(self.artifact_id)
        _ref(
            self.substrate,
            expected=ArtifactType.SUBSTRATE_BINDING,
            label="substrate",
        )
        _ref(
            self.core_score,
            expected=ArtifactType.CORE_SCORE,
            label="core_score",
        )
        _ref(
            self.order_parameter_field,
            expected=ArtifactType.ORDER_PARAMETER_FIELD,
            label="order_parameter_field",
        )
        _ref(
            self.field_estimation_graph,
            expected=ArtifactType.CANDIDATE_GRAPH,
            label="field_estimation_graph",
        )
        require_sha256(
            self.row_identity_sha256,
            label="row_identity_sha256",
        )
        require_slug(
            self.localization_algorithm_id,
            label="localization_algorithm_id",
        )
        require_slug(self.singularity_rule_id, label="singularity_rule_id")
        if not isinstance(
            self.graph_binding,
            (
                GraphFreeBinding,
                InheritedFieldGraphBinding,
                ExplicitCoreGraphBinding,
            ),
        ):
            raise TypeError("graph_binding is invalid")
        if (
            isinstance(self.graph_binding, InheritedFieldGraphBinding)
            and self.graph_binding.candidate_graph
            != self.field_estimation_graph
        ):
            raise ContractValidationError(
                "inherited graph binding must equal "
                "field_estimation_graph"
            )
        _require_payload_rows(
            (self.localized_support, self.uncertainty),
            row_identity_sha256=self.row_identity_sha256,
            label="core-candidate payloads",
        )
        if self.charge_blind is not True:
            raise ContractValidationError(
                "CoreCandidate must be charge-blind"
            )
        if self.sealed_without_loop_observable_input is not True:
            raise ContractValidationError(
                "CoreCandidate must be sealed without loop input"
            )
        _validate_claim(
            self.claim_ceiling,
            allowed={ClaimLevel.LEVEL_0, ClaimLevel.LEVEL_1D},
        )

    def to_dict(self) -> dict[str, object]:
        return {
            **self._header(),
            "branch": ScientificBranch.DEFECT.value,
            "provenance": "inferred_charge_blind",
            "substrate": self.substrate.to_dict(),
            "core_score": self.core_score.to_dict(),
            "order_parameter_field": self.order_parameter_field.to_dict(),
            "field_estimation_graph": self.field_estimation_graph.to_dict(),
            "row_identity_sha256": self.row_identity_sha256,
            "localization_algorithm_id": self.localization_algorithm_id,
            "singularity_rule_id": self.singularity_rule_id,
            "graph_binding": self.graph_binding.to_dict(),
            "localized_support": self.localized_support.to_dict(),
            "uncertainty": self.uncertainty.to_dict(),
            "charge_blind": self.charge_blind,
            "sealed_without_loop_observable_input": (
                self.sealed_without_loop_observable_input
            ),
            "claim_ceiling": self.claim_ceiling.value,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> "CoreCandidate":
        document = require_mapping(value, label="CoreCandidate")
        artifact_id = _header_from_dict(
            document,
            schema_version=cls.schema_version,
            artifact_type=cls.artifact_type,
            fields={
                "branch",
                "provenance",
                "substrate",
                "core_score",
                "order_parameter_field",
                "field_estimation_graph",
                "row_identity_sha256",
                "localization_algorithm_id",
                "singularity_rule_id",
                "graph_binding",
                "localized_support",
                "uncertainty",
                "charge_blind",
                "sealed_without_loop_observable_input",
                "claim_ceiling",
            },
            label="CoreCandidate",
        )
        if (
            document["branch"] != ScientificBranch.DEFECT.value
            or document["provenance"] != "inferred_charge_blind"
        ):
            raise ContractValidationError(
                "CoreCandidate branch or provenance is invalid"
            )
        return cls(
            artifact_id=artifact_id,
            substrate=_ref(
                document["substrate"],
                expected=ArtifactType.SUBSTRATE_BINDING,
                label="substrate",
            ),
            core_score=_ref(
                document["core_score"],
                expected=ArtifactType.CORE_SCORE,
                label="core_score",
            ),
            order_parameter_field=_ref(
                document["order_parameter_field"],
                expected=ArtifactType.ORDER_PARAMETER_FIELD,
                label="order_parameter_field",
            ),
            field_estimation_graph=_ref(
                document["field_estimation_graph"],
                expected=ArtifactType.CANDIDATE_GRAPH,
                label="field_estimation_graph",
            ),
            row_identity_sha256=require_sha256(
                document["row_identity_sha256"],
                label="row_identity_sha256",
            ),
            localization_algorithm_id=require_slug(
                document["localization_algorithm_id"],
                label="localization_algorithm_id",
            ),
            singularity_rule_id=require_slug(
                document["singularity_rule_id"],
                label="singularity_rule_id",
            ),
            graph_binding=core_graph_binding_from_dict(
                document["graph_binding"]
            ),
            localized_support=_payload(
                document["localized_support"],
                label="localized_support",
            ),
            uncertainty=_payload(
                document["uncertainty"],
                label="uncertainty",
            ),
            charge_blind=require_bool(
                document["charge_blind"],
                label="charge_blind",
            ),
            sealed_without_loop_observable_input=require_bool(
                document["sealed_without_loop_observable_input"],
                label="sealed_without_loop_observable_input",
            ),
            claim_ceiling=_parse_claim(
                document["claim_ceiling"],
                allowed={ClaimLevel.LEVEL_0, ClaimLevel.LEVEL_1D},
            ),
        )


@dataclass(frozen=True, slots=True)
class GroundTruthAnchor(_CanonicalArtifact):
    artifact_id: str
    substrate: ArtifactRef
    generator_id: str
    generator_sha256: str
    role: FitRole
    anchor_kind: str
    row_identity_sha256: str
    supplied_support: PayloadRef
    estimator_input_allowed: bool
    localization_gate_eligible: bool
    claim_ceiling: ClaimLevel

    schema_version: ClassVar[str] = GROUND_TRUTH_ANCHOR_SCHEMA
    artifact_type: ClassVar[ArtifactType] = ArtifactType.GROUND_TRUTH_ANCHOR

    def __post_init__(self) -> None:
        _validate_id(self.artifact_id)
        _ref(
            self.substrate,
            expected=ArtifactType.SUBSTRATE_BINDING,
            label="substrate",
        )
        require_slug(self.generator_id, label="generator_id")
        require_sha256(self.generator_sha256, label="generator_sha256")
        if self.role not in {
            FitRole.INSTRUMENT_DEV,
            FitRole.CALIBRATION_SELECTION,
            FitRole.CALIBRATION_CONFIRMATION,
        }:
            raise ContractValidationError(
                "GroundTruthAnchor is calibration-only"
            )
        require_slug(self.anchor_kind, label="anchor_kind")
        require_sha256(
            self.row_identity_sha256,
            label="row_identity_sha256",
        )
        _require_payload_rows(
            (self.supplied_support,),
            row_identity_sha256=self.row_identity_sha256,
            label="ground-truth anchor support",
        )
        if self.estimator_input_allowed is not False:
            raise ContractValidationError(
                "GroundTruthAnchor cannot be estimator input"
            )
        if self.localization_gate_eligible is not False:
            raise ContractValidationError(
                "GroundTruthAnchor cannot satisfy localization"
            )
        _validate_claim(
            self.claim_ceiling,
            allowed={ClaimLevel.LEVEL_0},
        )

    def to_dict(self) -> dict[str, object]:
        return {
            **self._header(),
            "provenance": "supplied_synthetic",
            "substrate": self.substrate.to_dict(),
            "generator_id": self.generator_id,
            "generator_sha256": self.generator_sha256,
            "role": self.role.value,
            "anchor_kind": self.anchor_kind,
            "row_identity_sha256": self.row_identity_sha256,
            "supplied_support": self.supplied_support.to_dict(),
            "estimator_input_allowed": self.estimator_input_allowed,
            "localization_gate_eligible": self.localization_gate_eligible,
            "claim_ceiling": self.claim_ceiling.value,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> "GroundTruthAnchor":
        document = require_mapping(value, label="GroundTruthAnchor")
        artifact_id = _header_from_dict(
            document,
            schema_version=cls.schema_version,
            artifact_type=cls.artifact_type,
            fields={
                "provenance",
                "substrate",
                "generator_id",
                "generator_sha256",
                "role",
                "anchor_kind",
                "row_identity_sha256",
                "supplied_support",
                "estimator_input_allowed",
                "localization_gate_eligible",
                "claim_ceiling",
            },
            label="GroundTruthAnchor",
        )
        if document["provenance"] != "supplied_synthetic":
            raise ContractValidationError(
                "GroundTruthAnchor provenance must be supplied_synthetic"
            )
        return cls(
            artifact_id=artifact_id,
            substrate=_ref(
                document["substrate"],
                expected=ArtifactType.SUBSTRATE_BINDING,
                label="substrate",
            ),
            generator_id=require_slug(
                document["generator_id"],
                label="generator_id",
            ),
            generator_sha256=require_sha256(
                document["generator_sha256"],
                label="generator_sha256",
            ),
            role=enum_from_value(
                FitRole,
                document["role"],
                label="role",
            ),
            anchor_kind=require_slug(
                document["anchor_kind"],
                label="anchor_kind",
            ),
            row_identity_sha256=require_sha256(
                document["row_identity_sha256"],
                label="row_identity_sha256",
            ),
            supplied_support=_payload(
                document["supplied_support"],
                label="supplied_support",
                allowed_kinds={PayloadKind.ARRAY},
            ),
            estimator_input_allowed=require_bool(
                document["estimator_input_allowed"],
                label="estimator_input_allowed",
            ),
            localization_gate_eligible=require_bool(
                document["localization_gate_eligible"],
                label="localization_gate_eligible",
            ),
            claim_ceiling=_parse_claim(
                document["claim_ceiling"],
                allowed={ClaimLevel.LEVEL_0},
            ),
        )


@dataclass(frozen=True, slots=True)
class EdgeConnection(_CanonicalArtifact):
    artifact_id: str
    substrate: ArtifactRef
    field: ArtifactRef
    field_branch: ScientificBranch
    graph: ArtifactRef
    edge_order_sha256: str
    endpoint_identities: PayloadRef
    principal_angles: PayloadRef
    procrustes_singular_values: PayloadRef
    coherence: PayloadRef
    orientation_state: str
    transport_convention_id: str
    claim_ceiling: ClaimLevel

    schema_version: ClassVar[str] = EDGE_CONNECTION_SCHEMA
    artifact_type: ClassVar[ArtifactType] = ArtifactType.EDGE_CONNECTION

    def __post_init__(self) -> None:
        _validate_id(self.artifact_id)
        _ref(
            self.substrate,
            expected=ArtifactType.SUBSTRATE_BINDING,
            label="substrate",
        )
        if self.field_branch is ScientificBranch.GEOMETRY:
            expected = ArtifactType.GEOMETRIC_FIELD_ESTIMATE
        elif self.field_branch is ScientificBranch.DEFECT:
            expected = ArtifactType.ORDER_PARAMETER_FIELD
        else:
            raise ContractValidationError(
                "EdgeConnection field branch must be geometry or defect"
            )
        _ref(self.field, expected=expected, label="field")
        _ref(
            self.graph,
            expected=ArtifactType.CANDIDATE_GRAPH,
            label="graph",
        )
        require_sha256(
            self.edge_order_sha256,
            label="edge_order_sha256",
        )
        _require_payload_rows(
            (
                self.endpoint_identities,
                self.principal_angles,
                self.procrustes_singular_values,
                self.coherence,
            ),
            row_identity_sha256=self.edge_order_sha256,
            label="edge-connection payloads",
        )
        if self.orientation_state not in _ORIENTATION_STATES:
            raise ContractValidationError("orientation_state is invalid")
        require_slug(
            self.transport_convention_id,
            label="transport_convention_id",
        )
        _validate_claim(
            self.claim_ceiling,
            allowed={
                ClaimLevel.LEVEL_0,
                ClaimLevel.LEVEL_1G,
                ClaimLevel.LEVEL_2G,
            },
        )

    def to_dict(self) -> dict[str, object]:
        return {
            **self._header(),
            "substrate": self.substrate.to_dict(),
            "field": self.field.to_dict(),
            "field_branch": self.field_branch.value,
            "graph": self.graph.to_dict(),
            "edge_order_sha256": self.edge_order_sha256,
            "endpoint_identities": self.endpoint_identities.to_dict(),
            "principal_angles": self.principal_angles.to_dict(),
            "procrustes_singular_values": (
                self.procrustes_singular_values.to_dict()
            ),
            "coherence": self.coherence.to_dict(),
            "orientation_state": self.orientation_state,
            "transport_convention_id": self.transport_convention_id,
            "claim_ceiling": self.claim_ceiling.value,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> "EdgeConnection":
        document = require_mapping(value, label="EdgeConnection")
        artifact_id = _header_from_dict(
            document,
            schema_version=cls.schema_version,
            artifact_type=cls.artifact_type,
            fields={
                "substrate",
                "field",
                "field_branch",
                "graph",
                "edge_order_sha256",
                "endpoint_identities",
                "principal_angles",
                "procrustes_singular_values",
                "coherence",
                "orientation_state",
                "transport_convention_id",
                "claim_ceiling",
            },
            label="EdgeConnection",
        )
        branch = enum_from_value(
            ScientificBranch,
            document["field_branch"],
            label="field_branch",
        )
        expected = (
            ArtifactType.GEOMETRIC_FIELD_ESTIMATE
            if branch is ScientificBranch.GEOMETRY
            else ArtifactType.ORDER_PARAMETER_FIELD
        )
        return cls(
            artifact_id=artifact_id,
            substrate=_ref(
                document["substrate"],
                expected=ArtifactType.SUBSTRATE_BINDING,
                label="substrate",
            ),
            field=_ref(document["field"], expected=expected, label="field"),
            field_branch=branch,
            graph=_ref(
                document["graph"],
                expected=ArtifactType.CANDIDATE_GRAPH,
                label="graph",
            ),
            edge_order_sha256=require_sha256(
                document["edge_order_sha256"],
                label="edge_order_sha256",
            ),
            endpoint_identities=_payload(
                document["endpoint_identities"],
                label="endpoint_identities",
            ),
            principal_angles=_payload(
                document["principal_angles"],
                label="principal_angles",
            ),
            procrustes_singular_values=_payload(
                document["procrustes_singular_values"],
                label="procrustes_singular_values",
            ),
            coherence=_payload(
                document["coherence"],
                label="coherence",
            ),
            orientation_state=require_string(
                document["orientation_state"],
                label="orientation_state",
            ),
            transport_convention_id=require_slug(
                document["transport_convention_id"],
                label="transport_convention_id",
            ),
            claim_ceiling=_parse_claim(
                document["claim_ceiling"],
                allowed={
                    ClaimLevel.LEVEL_0,
                    ClaimLevel.LEVEL_1G,
                    ClaimLevel.LEVEL_2G,
                },
            ),
        )


@dataclass(frozen=True, slots=True)
class GeometryLoopEstimate(_CanonicalArtifact):
    artifact_id: str
    substrate: ArtifactRef
    geometric_field: ArtifactRef
    edge_connection: ArtifactRef
    cycle_graph: ArtifactRef
    loop_order_sha256: str
    ordered_support: PayloadRef
    matched_class_or_anchor: PayloadRef
    sampling_specification: PayloadRef
    support_evidence: PayloadRef
    continuous_holonomy: PayloadRef
    gate_state: GateState
    reason_codes: tuple[str, ...]
    claim_ceiling: ClaimLevel

    schema_version: ClassVar[str] = GEOMETRY_LOOP_ESTIMATE_SCHEMA
    artifact_type: ClassVar[ArtifactType] = (
        ArtifactType.GEOMETRY_LOOP_ESTIMATE
    )

    def __post_init__(self) -> None:
        _validate_id(self.artifact_id)
        _ref(
            self.substrate,
            expected=ArtifactType.SUBSTRATE_BINDING,
            label="substrate",
        )
        _ref(
            self.geometric_field,
            expected=ArtifactType.GEOMETRIC_FIELD_ESTIMATE,
            label="geometric_field",
        )
        _ref(
            self.edge_connection,
            expected=ArtifactType.EDGE_CONNECTION,
            label="edge_connection",
        )
        _ref(
            self.cycle_graph,
            expected=ArtifactType.CANDIDATE_GRAPH,
            label="cycle_graph",
        )
        require_sha256(
            self.loop_order_sha256,
            label="loop_order_sha256",
        )
        _require_payload_rows(
            (
                self.ordered_support,
                self.matched_class_or_anchor,
                self.support_evidence,
                self.continuous_holonomy,
            ),
            row_identity_sha256=self.loop_order_sha256,
            label="geometry-loop payloads",
        )
        _payload(
            self.sampling_specification,
            label="sampling_specification",
        )
        if not isinstance(self.gate_state, GateState):
            raise TypeError("gate_state must be a GateState")
        _reason_codes(self.reason_codes)
        _validate_claim(
            self.claim_ceiling,
            allowed={
                ClaimLevel.LEVEL_0,
                ClaimLevel.LEVEL_1G,
                ClaimLevel.LEVEL_2G,
            },
        )

    def to_dict(self) -> dict[str, object]:
        return {
            **self._header(),
            "branch": ScientificBranch.GEOMETRY.value,
            "substrate": self.substrate.to_dict(),
            "geometric_field": self.geometric_field.to_dict(),
            "edge_connection": self.edge_connection.to_dict(),
            "cycle_graph": self.cycle_graph.to_dict(),
            "loop_order_sha256": self.loop_order_sha256,
            "ordered_support": self.ordered_support.to_dict(),
            "matched_class_or_anchor": (
                self.matched_class_or_anchor.to_dict()
            ),
            "sampling_specification": self.sampling_specification.to_dict(),
            "support_evidence": self.support_evidence.to_dict(),
            "continuous_holonomy": self.continuous_holonomy.to_dict(),
            "gate_state": self.gate_state.value,
            "reason_codes": list(self.reason_codes),
            "claim_ceiling": self.claim_ceiling.value,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> "GeometryLoopEstimate":
        document = require_mapping(value, label="GeometryLoopEstimate")
        artifact_id = _header_from_dict(
            document,
            schema_version=cls.schema_version,
            artifact_type=cls.artifact_type,
            fields={
                "branch",
                "substrate",
                "geometric_field",
                "edge_connection",
                "cycle_graph",
                "loop_order_sha256",
                "ordered_support",
                "matched_class_or_anchor",
                "sampling_specification",
                "support_evidence",
                "continuous_holonomy",
                "gate_state",
                "reason_codes",
                "claim_ceiling",
            },
            label="GeometryLoopEstimate",
        )
        if document["branch"] != ScientificBranch.GEOMETRY.value:
            raise ContractValidationError(
                "GeometryLoopEstimate branch must be geometry"
            )
        return cls(
            artifact_id=artifact_id,
            substrate=_ref(
                document["substrate"],
                expected=ArtifactType.SUBSTRATE_BINDING,
                label="substrate",
            ),
            geometric_field=_ref(
                document["geometric_field"],
                expected=ArtifactType.GEOMETRIC_FIELD_ESTIMATE,
                label="geometric_field",
            ),
            edge_connection=_ref(
                document["edge_connection"],
                expected=ArtifactType.EDGE_CONNECTION,
                label="edge_connection",
            ),
            cycle_graph=_ref(
                document["cycle_graph"],
                expected=ArtifactType.CANDIDATE_GRAPH,
                label="cycle_graph",
            ),
            loop_order_sha256=require_sha256(
                document["loop_order_sha256"],
                label="loop_order_sha256",
            ),
            ordered_support=_payload(
                document["ordered_support"],
                label="ordered_support",
            ),
            matched_class_or_anchor=_payload(
                document["matched_class_or_anchor"],
                label="matched_class_or_anchor",
            ),
            sampling_specification=_payload(
                document["sampling_specification"],
                label="sampling_specification",
            ),
            support_evidence=_payload(
                document["support_evidence"],
                label="support_evidence",
            ),
            continuous_holonomy=_payload(
                document["continuous_holonomy"],
                label="continuous_holonomy",
            ),
            gate_state=enum_from_value(
                GateState,
                document["gate_state"],
                label="gate_state",
            ),
            reason_codes=_parse_reason_codes(document["reason_codes"]),
            claim_ceiling=_parse_claim(
                document["claim_ceiling"],
                allowed={
                    ClaimLevel.LEVEL_0,
                    ClaimLevel.LEVEL_1G,
                    ClaimLevel.LEVEL_2G,
                },
            ),
        )


@dataclass(frozen=True, slots=True)
class DefectCoordinateBinding:
    mode: str
    edge_connection: ArtifactRef | None = None

    def __post_init__(self) -> None:
        if self.mode not in _COORDINATE_MODES:
            raise ContractValidationError("coordinate mode is invalid")
        if self.mode == "global_frame":
            if self.edge_connection is not None:
                raise ContractValidationError(
                    "global_frame forbids edge_connection"
                )
        else:
            if self.edge_connection is None:
                raise ContractValidationError(
                    "local_frames requires edge_connection"
                )
            _ref(
                self.edge_connection,
                expected=ArtifactType.EDGE_CONNECTION,
                label="edge_connection",
            )

    def to_dict(self) -> dict[str, object]:
        if self.mode == "global_frame":
            return {"mode": self.mode}
        assert self.edge_connection is not None
        return {
            "mode": self.mode,
            "edge_connection": self.edge_connection.to_dict(),
        }

    @classmethod
    def from_dict(
        cls,
        value: Mapping[str, object],
    ) -> "DefectCoordinateBinding":
        document = require_mapping(value, label="coordinate_binding")
        mode = require_string(document.get("mode"), label="coordinate mode")
        if mode == "global_frame":
            exact_keys(document, {"mode"}, label="coordinate_binding")
            return cls(mode=mode)
        if mode != "local_frames":
            raise ContractValidationError("coordinate mode is invalid")
        exact_keys(
            document,
            {"mode", "edge_connection"},
            label="coordinate_binding",
        )
        return cls(
            mode=mode,
            edge_connection=_ref(
                document["edge_connection"],
                expected=ArtifactType.EDGE_CONNECTION,
                label="edge_connection",
            ),
        )


@dataclass(frozen=True, slots=True)
class DefectLocalizationBinding:
    mode: str
    core_candidate: ArtifactRef | None = None
    ground_truth_anchor: ArtifactRef | None = None

    def __post_init__(self) -> None:
        if self.mode not in _LOCALIZATION_MODES:
            raise ContractValidationError("localization mode is invalid")
        if self.mode == "unlocalized":
            if (
                self.core_candidate is not None
                or self.ground_truth_anchor is not None
            ):
                raise ContractValidationError(
                    "unlocalized loops forbid core and anchor references"
                )
        elif self.mode == "inferred_core":
            if (
                self.core_candidate is None
                or self.ground_truth_anchor is not None
            ):
                raise ContractValidationError(
                    "inferred_core requires only CoreCandidate"
                )
            _ref(
                self.core_candidate,
                expected=ArtifactType.CORE_CANDIDATE,
                label="core_candidate",
            )
        else:
            if (
                self.ground_truth_anchor is None
                or self.core_candidate is not None
            ):
                raise ContractValidationError(
                    "supplied_anchor requires only GroundTruthAnchor"
                )
            _ref(
                self.ground_truth_anchor,
                expected=ArtifactType.GROUND_TRUTH_ANCHOR,
                label="ground_truth_anchor",
            )

    def to_dict(self) -> dict[str, object]:
        if self.mode == "unlocalized":
            return {"mode": self.mode}
        if self.mode == "inferred_core":
            assert self.core_candidate is not None
            return {
                "mode": self.mode,
                "core_candidate": self.core_candidate.to_dict(),
            }
        assert self.ground_truth_anchor is not None
        return {
            "mode": self.mode,
            "ground_truth_anchor": self.ground_truth_anchor.to_dict(),
        }

    @classmethod
    def from_dict(
        cls,
        value: Mapping[str, object],
    ) -> "DefectLocalizationBinding":
        document = require_mapping(value, label="localization_binding")
        mode = require_string(
            document.get("mode"),
            label="localization mode",
        )
        if mode == "unlocalized":
            exact_keys(document, {"mode"}, label="localization_binding")
            return cls(mode=mode)
        if mode == "inferred_core":
            exact_keys(
                document,
                {"mode", "core_candidate"},
                label="localization_binding",
            )
            return cls(
                mode=mode,
                core_candidate=_ref(
                    document["core_candidate"],
                    expected=ArtifactType.CORE_CANDIDATE,
                    label="core_candidate",
                ),
            )
        if mode == "supplied_anchor":
            exact_keys(
                document,
                {"mode", "ground_truth_anchor"},
                label="localization_binding",
            )
            return cls(
                mode=mode,
                ground_truth_anchor=_ref(
                    document["ground_truth_anchor"],
                    expected=ArtifactType.GROUND_TRUTH_ANCHOR,
                    label="ground_truth_anchor",
                ),
            )
        raise ContractValidationError("localization mode is invalid")


@dataclass(frozen=True, slots=True)
class DefectLoopEstimate(_CanonicalArtifact):
    artifact_id: str
    substrate: ArtifactRef
    order_parameter_field: ArtifactRef
    hypothesis_id: HypothesisId
    cycle_graph: ArtifactRef
    loop_order_sha256: str
    ordered_support: PayloadRef
    matched_class: PayloadRef
    interpolation_evidence: PayloadRef
    lift_or_reference_evidence: PayloadRef
    boundary_identifiability_evidence: PayloadRef
    branch_and_sampling_evidence: PayloadRef
    coordinate_binding: DefectCoordinateBinding
    localization_binding: DefectLocalizationBinding
    sampled_winding: PayloadRef
    integer_output_authorization: ArtifactRef | None
    gate_state: GateState
    reason_codes: tuple[str, ...]
    claim_ceiling: ClaimLevel

    schema_version: ClassVar[str] = DEFECT_LOOP_ESTIMATE_SCHEMA
    artifact_type: ClassVar[ArtifactType] = ArtifactType.DEFECT_LOOP_ESTIMATE

    def __post_init__(self) -> None:
        _validate_id(self.artifact_id)
        _ref(
            self.substrate,
            expected=ArtifactType.SUBSTRATE_BINDING,
            label="substrate",
        )
        _ref(
            self.order_parameter_field,
            expected=ArtifactType.ORDER_PARAMETER_FIELD,
            label="order_parameter_field",
        )
        if self.hypothesis_id not in _ORDER_PARAMETER_HYPOTHESES:
            raise ContractValidationError(
                "defect loops require F2, F3, or F4"
            )
        _ref(
            self.cycle_graph,
            expected=ArtifactType.CANDIDATE_GRAPH,
            label="cycle_graph",
        )
        require_sha256(
            self.loop_order_sha256,
            label="loop_order_sha256",
        )
        _require_payload_rows(
            (
                self.ordered_support,
                self.matched_class,
                self.interpolation_evidence,
                self.lift_or_reference_evidence,
                self.boundary_identifiability_evidence,
                self.branch_and_sampling_evidence,
                self.sampled_winding,
            ),
            row_identity_sha256=self.loop_order_sha256,
            label="defect-loop payloads",
        )
        if not isinstance(self.coordinate_binding, DefectCoordinateBinding):
            raise TypeError("coordinate_binding is invalid")
        if not isinstance(
            self.localization_binding,
            DefectLocalizationBinding,
        ):
            raise TypeError("localization_binding is invalid")
        if not isinstance(self.gate_state, GateState):
            raise TypeError("gate_state must be a GateState")
        _reason_codes(self.reason_codes)
        allowed = {
            ClaimLevel.LEVEL_0,
            ClaimLevel.LEVEL_1D,
            ClaimLevel.LEVEL_2T,
        }
        if self.localization_binding.mode != "inferred_core":
            allowed.remove(ClaimLevel.LEVEL_2T)
        allowed &= _DEFECT_CLAIMS_BY_HYPOTHESIS[self.hypothesis_id]
        _validate_claim(self.claim_ceiling, allowed=allowed)
        if self.claim_ceiling is ClaimLevel.LEVEL_2T:
            if self.integer_output_authorization is None:
                raise ContractValidationError(
                    "Level 2T requires a calibration-selection "
                    "authorization reference"
                )
            _ref(
                self.integer_output_authorization,
                expected=ArtifactType.CALIBRATION_SELECTION_DECISION,
                label="integer_output_authorization",
            )
        elif self.integer_output_authorization is not None:
            raise ContractValidationError(
                "integer_output_authorization is only valid at Level 2T"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            **self._header(),
            "branch": ScientificBranch.DEFECT.value,
            "substrate": self.substrate.to_dict(),
            "order_parameter_field": self.order_parameter_field.to_dict(),
            "hypothesis_id": self.hypothesis_id.value,
            "cycle_graph": self.cycle_graph.to_dict(),
            "loop_order_sha256": self.loop_order_sha256,
            "ordered_support": self.ordered_support.to_dict(),
            "matched_class": self.matched_class.to_dict(),
            "interpolation_evidence": self.interpolation_evidence.to_dict(),
            "lift_or_reference_evidence": (
                self.lift_or_reference_evidence.to_dict()
            ),
            "boundary_identifiability_evidence": (
                self.boundary_identifiability_evidence.to_dict()
            ),
            "branch_and_sampling_evidence": (
                self.branch_and_sampling_evidence.to_dict()
            ),
            "coordinate_binding": self.coordinate_binding.to_dict(),
            "localization_binding": self.localization_binding.to_dict(),
            "sampled_winding": self.sampled_winding.to_dict(),
            "integer_output_authorization": (
                None
                if self.integer_output_authorization is None
                else self.integer_output_authorization.to_dict()
            ),
            "gate_state": self.gate_state.value,
            "reason_codes": list(self.reason_codes),
            "claim_ceiling": self.claim_ceiling.value,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> "DefectLoopEstimate":
        document = require_mapping(value, label="DefectLoopEstimate")
        artifact_id = _header_from_dict(
            document,
            schema_version=cls.schema_version,
            artifact_type=cls.artifact_type,
            fields={
                "branch",
                "substrate",
                "order_parameter_field",
                "hypothesis_id",
                "cycle_graph",
                "loop_order_sha256",
                "ordered_support",
                "matched_class",
                "interpolation_evidence",
                "lift_or_reference_evidence",
                "boundary_identifiability_evidence",
                "branch_and_sampling_evidence",
                "coordinate_binding",
                "localization_binding",
                "sampled_winding",
                "integer_output_authorization",
                "gate_state",
                "reason_codes",
                "claim_ceiling",
            },
            label="DefectLoopEstimate",
        )
        if document["branch"] != ScientificBranch.DEFECT.value:
            raise ContractValidationError(
                "DefectLoopEstimate branch must be defect"
            )
        localization = DefectLocalizationBinding.from_dict(
            require_mapping(
                document["localization_binding"],
                label="localization_binding",
            )
        )
        allowed = {
            ClaimLevel.LEVEL_0,
            ClaimLevel.LEVEL_1D,
            ClaimLevel.LEVEL_2T,
        }
        if localization.mode != "inferred_core":
            allowed.remove(ClaimLevel.LEVEL_2T)
        hypothesis_id = enum_from_value(
            HypothesisId,
            document["hypothesis_id"],
            label="hypothesis_id",
        )
        if hypothesis_id not in _ORDER_PARAMETER_HYPOTHESES:
            raise ContractValidationError(
                "defect loops require F2, F3, or F4"
            )
        allowed &= _DEFECT_CLAIMS_BY_HYPOTHESIS[hypothesis_id]
        authorization_value = document["integer_output_authorization"]
        authorization = (
            None
            if authorization_value is None
            else _ref(
                authorization_value,
                expected=ArtifactType.CALIBRATION_SELECTION_DECISION,
                label="integer_output_authorization",
            )
        )
        return cls(
            artifact_id=artifact_id,
            substrate=_ref(
                document["substrate"],
                expected=ArtifactType.SUBSTRATE_BINDING,
                label="substrate",
            ),
            order_parameter_field=_ref(
                document["order_parameter_field"],
                expected=ArtifactType.ORDER_PARAMETER_FIELD,
                label="order_parameter_field",
            ),
            hypothesis_id=hypothesis_id,
            cycle_graph=_ref(
                document["cycle_graph"],
                expected=ArtifactType.CANDIDATE_GRAPH,
                label="cycle_graph",
            ),
            loop_order_sha256=require_sha256(
                document["loop_order_sha256"],
                label="loop_order_sha256",
            ),
            ordered_support=_payload(
                document["ordered_support"],
                label="ordered_support",
            ),
            matched_class=_payload(
                document["matched_class"],
                label="matched_class",
            ),
            interpolation_evidence=_payload(
                document["interpolation_evidence"],
                label="interpolation_evidence",
            ),
            lift_or_reference_evidence=_payload(
                document["lift_or_reference_evidence"],
                label="lift_or_reference_evidence",
            ),
            boundary_identifiability_evidence=_payload(
                document["boundary_identifiability_evidence"],
                label="boundary_identifiability_evidence",
            ),
            branch_and_sampling_evidence=_payload(
                document["branch_and_sampling_evidence"],
                label="branch_and_sampling_evidence",
            ),
            coordinate_binding=DefectCoordinateBinding.from_dict(
                require_mapping(
                    document["coordinate_binding"],
                    label="coordinate_binding",
                )
            ),
            localization_binding=localization,
            sampled_winding=_payload(
                document["sampled_winding"],
                label="sampled_winding",
            ),
            integer_output_authorization=authorization,
            gate_state=enum_from_value(
                GateState,
                document["gate_state"],
                label="gate_state",
            ),
            reason_codes=_parse_reason_codes(document["reason_codes"]),
            claim_ceiling=_parse_claim(
                document["claim_ceiling"],
                allowed=allowed,
            ),
        )


@dataclass(frozen=True, slots=True)
class HypothesisDecision:
    hypothesis_id: HypothesisId
    disposition: HypothesisDisposition
    reason_codes: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.hypothesis_id, HypothesisId):
            raise TypeError("hypothesis_id must be a HypothesisId")
        if not isinstance(self.disposition, HypothesisDisposition):
            raise TypeError("disposition must be a HypothesisDisposition")
        _reason_codes(self.reason_codes)

    def to_dict(self) -> dict[str, object]:
        return {
            "hypothesis_id": self.hypothesis_id.value,
            "disposition": self.disposition.value,
            "reason_codes": list(self.reason_codes),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> "HypothesisDecision":
        document = require_mapping(value, label="hypothesis decision")
        exact_keys(
            document,
            {"hypothesis_id", "disposition", "reason_codes"},
            label="hypothesis decision",
        )
        return cls(
            hypothesis_id=enum_from_value(
                HypothesisId,
                document["hypothesis_id"],
                label="hypothesis_id",
            ),
            disposition=enum_from_value(
                HypothesisDisposition,
                document["disposition"],
                label="disposition",
            ),
            reason_codes=_parse_reason_codes(document["reason_codes"]),
        )


@dataclass(frozen=True, slots=True)
class HypothesisRuleChoice:
    """One still-unresolved registry choice keyed by hypothesis and family."""

    hypothesis_id: HypothesisId
    choice: RuleChoice

    def __post_init__(self) -> None:
        if not isinstance(self.hypothesis_id, HypothesisId):
            raise TypeError("hypothesis_id must be a HypothesisId")
        if not isinstance(self.choice, RuleChoice):
            raise TypeError("choice must be a RuleChoice")
        if self.choice.resolution is not ResolutionState.CALIBRATION_SELECTION:
            raise ContractValidationError(
                "an unresolved choice must remain calibration_selection"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "hypothesis_id": self.hypothesis_id.value,
            "choice": self.choice.to_dict(),
        }

    @classmethod
    def from_dict(
        cls,
        value: Mapping[str, object],
    ) -> "HypothesisRuleChoice":
        document = require_mapping(value, label="hypothesis rule choice")
        exact_keys(
            document,
            {"hypothesis_id", "choice"},
            label="hypothesis rule choice",
        )
        return cls(
            hypothesis_id=enum_from_value(
                HypothesisId,
                document["hypothesis_id"],
                label="hypothesis_id",
            ),
            choice=RuleChoice.from_dict(
                require_mapping(
                    document["choice"],
                    label="choice",
                )
            ),
        )


@dataclass(frozen=True, slots=True)
class HypothesisResolvedChoice:
    """One selected rule keyed by hypothesis and frozen family."""

    hypothesis_id: HypothesisId
    choice: RuleChoice

    def __post_init__(self) -> None:
        if not isinstance(self.hypothesis_id, HypothesisId):
            raise TypeError("hypothesis_id must be a HypothesisId")
        if not isinstance(self.choice, RuleChoice):
            raise TypeError("choice must be a RuleChoice")
        if self.choice.resolution is not ResolutionState.CALIBRATION_RESOLVED:
            raise ContractValidationError(
                "a resolved choice must be calibration_resolved"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "hypothesis_id": self.hypothesis_id.value,
            "choice": self.choice.to_dict(),
        }

    @classmethod
    def from_dict(
        cls,
        value: Mapping[str, object],
    ) -> "HypothesisResolvedChoice":
        document = require_mapping(value, label="hypothesis resolved choice")
        exact_keys(
            document,
            {"hypothesis_id", "choice"},
            label="hypothesis resolved choice",
        )
        return cls(
            hypothesis_id=enum_from_value(
                HypothesisId,
                document["hypothesis_id"],
                label="hypothesis_id",
            ),
            choice=RuleChoice.from_dict(
                require_mapping(
                    document["choice"],
                    label="choice",
                )
            ),
        )


@dataclass(frozen=True, slots=True)
class HypothesisFixedChoice:
    """One registry rule fixed by the hypothesis rather than calibration."""

    hypothesis_id: HypothesisId
    choice: RuleChoice

    def __post_init__(self) -> None:
        if not isinstance(self.hypothesis_id, HypothesisId):
            raise TypeError("hypothesis_id must be a HypothesisId")
        if not isinstance(self.choice, RuleChoice):
            raise TypeError("choice must be a RuleChoice")
        if self.choice.resolution is not ResolutionState.FIXED_BY_HYPOTHESIS:
            raise ContractValidationError(
                "a hypothesis-fixed choice must be fixed_by_hypothesis"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "hypothesis_id": self.hypothesis_id.value,
            "choice": self.choice.to_dict(),
        }

    @classmethod
    def from_dict(
        cls,
        value: Mapping[str, object],
    ) -> "HypothesisFixedChoice":
        document = require_mapping(value, label="hypothesis fixed choice")
        exact_keys(
            document,
            {"hypothesis_id", "choice"},
            label="hypothesis fixed choice",
        )
        return cls(
            hypothesis_id=enum_from_value(
                HypothesisId,
                document["hypothesis_id"],
                label="hypothesis_id",
            ),
            choice=RuleChoice.from_dict(
                require_mapping(
                    document["choice"],
                    label="choice",
                )
            ),
        )


def _validate_decisions(
    values: tuple[HypothesisDecision, ...],
) -> tuple[HypothesisDecision, ...]:
    if not isinstance(values, tuple):
        raise TypeError("hypothesis_decisions must be a tuple")
    if any(not isinstance(value, HypothesisDecision) for value in values):
        raise TypeError(
            "hypothesis_decisions must contain HypothesisDecision values"
        )
    identifiers = tuple(value.hypothesis_id.value for value in values)
    expected = tuple(sorted(item.value for item in HypothesisId))
    if identifiers != expected:
        raise ContractValidationError(
            "hypothesis_decisions must contain every F0-F4 hypothesis "
            "exactly once in canonical order"
        )
    return values


def _validate_choices(
    values: tuple[HypothesisRuleChoice, ...],
) -> tuple[HypothesisRuleChoice, ...]:
    if not isinstance(values, tuple):
        raise TypeError("unresolved_choices must be a tuple")
    if any(not isinstance(value, HypothesisRuleChoice) for value in values):
        raise TypeError(
            "unresolved_choices must contain HypothesisRuleChoice values"
        )
    keys = tuple(
        (value.hypothesis_id.value, value.choice.family_id)
        for value in values
    )
    if keys != tuple(sorted(set(keys))):
        raise ContractValidationError(
            "unresolved_choices must be unique and sorted by "
            "(hypothesis_id, family_id)"
        )
    return values


def _validate_resolved_choices(
    values: tuple[HypothesisResolvedChoice, ...],
) -> tuple[HypothesisResolvedChoice, ...]:
    if not isinstance(values, tuple):
        raise TypeError("resolved_choices must be a tuple")
    if any(not isinstance(value, HypothesisResolvedChoice) for value in values):
        raise TypeError(
            "resolved_choices must contain HypothesisResolvedChoice values"
        )
    keys = tuple(
        (value.hypothesis_id.value, value.choice.family_id)
        for value in values
    )
    if keys != tuple(sorted(set(keys))):
        raise ContractValidationError(
            "resolved_choices must be unique and sorted by "
            "(hypothesis_id, family_id)"
        )
    return values


def _validate_fixed_choices(
    values: tuple[HypothesisFixedChoice, ...],
) -> tuple[HypothesisFixedChoice, ...]:
    if not isinstance(values, tuple):
        raise TypeError("fixed_choices must be a tuple")
    if any(not isinstance(value, HypothesisFixedChoice) for value in values):
        raise TypeError(
            "fixed_choices must contain HypothesisFixedChoice values"
        )
    keys = tuple(
        (value.hypothesis_id.value, value.choice.family_id)
        for value in values
    )
    if keys != tuple(sorted(set(keys))):
        raise ContractValidationError(
            "fixed_choices must be unique and sorted by "
            "(hypothesis_id, family_id)"
        )
    return values


def _validate_hypothesis_ids(
    values: tuple[HypothesisId, ...],
) -> tuple[HypothesisId, ...]:
    if not isinstance(values, tuple):
        raise TypeError("unresolved_hypotheses must be a tuple")
    if any(not isinstance(value, HypothesisId) for value in values):
        raise TypeError(
            "unresolved_hypotheses must contain HypothesisId values"
        )
    identifiers = tuple(value.value for value in values)
    if identifiers != tuple(sorted(set(identifiers))):
        raise ContractValidationError(
            "unresolved_hypotheses must be unique and canonically sorted"
        )
    return values


def _validate_choice_closure(
    *,
    decisions: tuple[HypothesisDecision, ...],
    fixed_choices: tuple[HypothesisFixedChoice, ...],
    resolved_choices: tuple[HypothesisResolvedChoice, ...],
    unresolved_choices: tuple[HypothesisRuleChoice, ...],
) -> None:
    advanced = {
        decision.hypothesis_id
        for decision in decisions
        if decision.disposition is HypothesisDisposition.ADVANCE
    }
    for hypothesis_id in HypothesisId:
        resolved_by_family = {
            value.choice.family_id: value.choice.selected_id
            for value in resolved_choices
            if value.hypothesis_id is hypothesis_id
        }
        unresolved_by_family = {
            value.choice.family_id: value.choice.candidate_ids
            for value in unresolved_choices
            if value.hypothesis_id is hypothesis_id
        }
        allowed_selections = _P0_CALIBRATION_SELECTIONS_BY_HYPOTHESIS[
            hypothesis_id
        ]
        unexpected_resolved = set(resolved_by_family) - set(
            allowed_selections
        )
        if unexpected_resolved:
            raise ContractValidationError(
                f"{hypothesis_id.value} has unexpected resolved choices: "
                f"{sorted(unexpected_resolved)}"
            )
        unexpected_unresolved = set(unresolved_by_family) - set(
            allowed_selections
        )
        if unexpected_unresolved:
            raise ContractValidationError(
                f"{hypothesis_id.value} has unexpected unresolved choices: "
                f"{sorted(unexpected_unresolved)}"
            )
        observed_selection_families = set(resolved_by_family) | set(
            unresolved_by_family
        )
        missing = set(allowed_selections) - observed_selection_families
        if missing:
            raise ContractValidationError(
                f"{hypothesis_id.value} is missing choice receipts: "
                f"{sorted(missing)}"
            )
        if hypothesis_id in advanced and unresolved_by_family:
            raise ContractValidationError(
                f"{hypothesis_id.value} cannot advance with unresolved "
                f"choices: {sorted(unresolved_by_family)}"
            )
        for family_id, selected_id in resolved_by_family.items():
            allowed_selected_ids = allowed_selections[family_id]
            if selected_id not in allowed_selected_ids:
                raise ContractValidationError(
                    f"{hypothesis_id.value}.{family_id} selected_id "
                    "differs from the P0 registry candidate set"
                )
        for family_id, candidate_ids in unresolved_by_family.items():
            if set(candidate_ids) != allowed_selections[family_id]:
                raise ContractValidationError(
                    f"{hypothesis_id.value}.{family_id} unresolved "
                    "candidate_ids differ from the P0 registry candidate set"
                )
        fixed_by_family = {
            value.choice.family_id: value.choice.selected_id
            for value in fixed_choices
            if value.hypothesis_id is hypothesis_id
        }
        allowed_fixed = _P0_FIXED_SELECTIONS_BY_HYPOTHESIS[hypothesis_id]
        missing_fixed = set(allowed_fixed) - set(fixed_by_family)
        if missing_fixed:
            raise ContractValidationError(
                f"{hypothesis_id.value} is missing hypothesis-fixed choices: "
                f"{sorted(missing_fixed)}"
            )
        unexpected_fixed = set(fixed_by_family) - set(allowed_fixed)
        if unexpected_fixed:
            raise ContractValidationError(
                f"{hypothesis_id.value} has unexpected hypothesis-fixed "
                "choices: "
                f"{sorted(unexpected_fixed)}"
            )
        for family_id, allowed_selected_ids in allowed_fixed.items():
            selected_id = fixed_by_family[family_id]
            if selected_id not in allowed_selected_ids:
                raise ContractValidationError(
                    f"{hypothesis_id.value}.{family_id} hypothesis-fixed "
                    "selected_id differs from the P0 registry"
                )


def _validate_integer_authorizations(
    values: tuple[HypothesisId, ...],
    *,
    decisions: tuple[HypothesisDecision, ...],
    unresolved_choices: tuple[HypothesisRuleChoice, ...],
    claim_ceiling: ClaimLevel,
) -> tuple[HypothesisId, ...]:
    authorized = _validate_hypothesis_ids(values)
    allowed = {
        HypothesisId.F2_LOCAL_COVARIANT_SECTION,
        HypothesisId.F4_SPIN_TWO_ANISOTROPY,
    }
    if any(value not in allowed for value in authorized):
        raise ContractValidationError(
            "integer output can be authorized only for F2 or F4"
        )
    advanced = {
        decision.hypothesis_id
        for decision in decisions
        if decision.disposition is HypothesisDisposition.ADVANCE
    }
    if not set(authorized).issubset(advanced):
        raise ContractValidationError(
            "integer output authorization requires an advanced hypothesis"
        )
    unresolved_hypotheses = {
        value.hypothesis_id for value in unresolved_choices
    }
    if set(authorized) & unresolved_hypotheses:
        raise ContractValidationError(
            "integer output authorization cannot retain an unresolved "
            "choice for the same hypothesis"
        )
    if bool(authorized) != (claim_ceiling is ClaimLevel.LEVEL_2T):
        raise ContractValidationError(
            "Level 2T selection ceiling and integer output authorization "
            "must be declared together"
        )
    return authorized


def _validate_selection_claim(
    decisions: tuple[HypothesisDecision, ...],
    *,
    claim_ceiling: ClaimLevel,
) -> ClaimLevel:
    allowed = {ClaimLevel.LEVEL_0}
    for decision in decisions:
        if decision.disposition is HypothesisDisposition.ADVANCE:
            allowed.update(
                _SELECTION_CLAIMS_BY_HYPOTHESIS[decision.hypothesis_id]
            )
    if claim_ceiling not in allowed:
        raise ContractValidationError(
            f"advanced hypotheses do not support selection claim ceiling "
            f"{claim_ceiling.value!r}"
        )
    return claim_ceiling


def _parse_hypothesis_ids(value: object) -> tuple[HypothesisId, ...]:
    if not isinstance(value, list):
        raise ContractValidationError(
            "unresolved_hypotheses must be a list"
        )
    parsed = tuple(
        enum_from_value(
            HypothesisId,
            item,
            label=f"unresolved_hypotheses[{index}]",
        )
        for index, item in enumerate(value)
    )
    return _validate_hypothesis_ids(parsed)


@dataclass(frozen=True, slots=True)
class CalibrationSelectionDecision(_CanonicalArtifact):
    artifact_id: str
    hypothesis_registry: ArtifactRef
    hypothesis_decisions: tuple[HypothesisDecision, ...]
    crossed_cell_order_sha256: str
    crossed_cell_manifest: PayloadRef
    selected_artifacts: tuple[ArtifactRef, ...]
    locked_policy_bundle: PayloadRef
    selection_inputs: tuple[ArtifactRef, ...]
    selection_outputs: tuple[ArtifactRef, ...]
    source_commit_sha1: str
    source_tree_sha256: str
    fixed_choices: tuple[HypothesisFixedChoice, ...]
    resolved_choices: tuple[HypothesisResolvedChoice, ...]
    unresolved_choices: tuple[HypothesisRuleChoice, ...]
    integer_output_authorizations: tuple[HypothesisId, ...]
    confirmation_access_commitment: PayloadRef
    sealed_before_confirmation_access: bool
    claim_ceiling: ClaimLevel

    schema_version: ClassVar[str] = (
        CALIBRATION_SELECTION_DECISION_SCHEMA
    )
    artifact_type: ClassVar[ArtifactType] = (
        ArtifactType.CALIBRATION_SELECTION_DECISION
    )

    def __post_init__(self) -> None:
        _validate_id(self.artifact_id)
        _ref(
            self.hypothesis_registry,
            expected=ArtifactType.HYPOTHESIS_REGISTRY,
            label="hypothesis_registry",
        )
        _validate_decisions(self.hypothesis_decisions)
        require_sha256(
            self.crossed_cell_order_sha256,
            label="crossed_cell_order_sha256",
        )
        _require_payload_rows(
            (self.crossed_cell_manifest,),
            row_identity_sha256=self.crossed_cell_order_sha256,
            label="crossed calibration cells",
            allowed_kinds={
                PayloadKind.TABLE,
                PayloadKind.JSON_RECORDS,
            },
        )
        _sorted_refs(
            self.selected_artifacts,
            label="selected_artifacts",
            allowed=_CALIBRATION_EVIDENCE_TYPES,
        )
        _sorted_refs(
            self.selection_inputs,
            label="selection_inputs",
            allowed=_CALIBRATION_INPUT_TYPES,
        )
        _sorted_refs(
            self.selection_outputs,
            label="selection_outputs",
            allowed=_CALIBRATION_EVIDENCE_TYPES,
        )
        _require_git_sha1(
            self.source_commit_sha1,
            label="source_commit_sha1",
        )
        require_sha256(
            self.source_tree_sha256,
            label="source_tree_sha256",
        )
        _validate_fixed_choices(self.fixed_choices)
        _validate_resolved_choices(self.resolved_choices)
        _validate_choices(self.unresolved_choices)
        resolved_keys = {
            (value.hypothesis_id, value.choice.family_id)
            for value in self.resolved_choices
        }
        unresolved_keys = {
            (value.hypothesis_id, value.choice.family_id)
            for value in self.unresolved_choices
        }
        fixed_keys = {
            (value.hypothesis_id, value.choice.family_id)
            for value in self.fixed_choices
        }
        if (
            fixed_keys & resolved_keys
            or fixed_keys & unresolved_keys
            or resolved_keys & unresolved_keys
        ):
            raise ContractValidationError(
                "a hypothesis rule cannot be fixed, resolved, or unresolved "
                "more than once"
            )
        _validate_choice_closure(
            decisions=self.hypothesis_decisions,
            fixed_choices=self.fixed_choices,
            resolved_choices=self.resolved_choices,
            unresolved_choices=self.unresolved_choices,
        )
        if self.sealed_before_confirmation_access is not True:
            raise ContractValidationError(
                "selection must be sealed before confirmation access"
            )
        _validate_claim(
            self.claim_ceiling,
            allowed={
                ClaimLevel.LEVEL_0,
                ClaimLevel.LEVEL_1G,
                ClaimLevel.LEVEL_1D,
                ClaimLevel.LEVEL_2G,
                ClaimLevel.LEVEL_2T,
            },
        )
        _validate_selection_claim(
            self.hypothesis_decisions,
            claim_ceiling=self.claim_ceiling,
        )
        _validate_integer_authorizations(
            self.integer_output_authorizations,
            decisions=self.hypothesis_decisions,
            unresolved_choices=self.unresolved_choices,
            claim_ceiling=self.claim_ceiling,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            **self._header(),
            "role": FitRole.CALIBRATION_SELECTION.value,
            "hypothesis_registry": self.hypothesis_registry.to_dict(),
            "hypothesis_decisions": [
                value.to_dict() for value in self.hypothesis_decisions
            ],
            "crossed_cell_order_sha256": (
                self.crossed_cell_order_sha256
            ),
            "crossed_cell_manifest": self.crossed_cell_manifest.to_dict(),
            "selected_artifacts": [
                value.to_dict() for value in self.selected_artifacts
            ],
            "locked_policy_bundle": self.locked_policy_bundle.to_dict(),
            "selection_inputs": [
                value.to_dict() for value in self.selection_inputs
            ],
            "selection_outputs": [
                value.to_dict() for value in self.selection_outputs
            ],
            "source_commit_sha1": self.source_commit_sha1,
            "source_tree_sha256": self.source_tree_sha256,
            "fixed_choices": [
                value.to_dict() for value in self.fixed_choices
            ],
            "resolved_choices": [
                value.to_dict() for value in self.resolved_choices
            ],
            "unresolved_choices": [
                value.to_dict() for value in self.unresolved_choices
            ],
            "integer_output_authorizations": [
                value.value
                for value in self.integer_output_authorizations
            ],
            "confirmation_access_commitment": (
                self.confirmation_access_commitment.to_dict()
            ),
            "sealed_before_confirmation_access": (
                self.sealed_before_confirmation_access
            ),
            "claim_ceiling": self.claim_ceiling.value,
        }

    @classmethod
    def from_dict(
        cls,
        value: Mapping[str, object],
    ) -> "CalibrationSelectionDecision":
        document = require_mapping(value, label="CalibrationSelectionDecision")
        artifact_id = _header_from_dict(
            document,
            schema_version=cls.schema_version,
            artifact_type=cls.artifact_type,
            fields={
                "role",
                "hypothesis_registry",
                "hypothesis_decisions",
                "crossed_cell_order_sha256",
                "crossed_cell_manifest",
                "selected_artifacts",
                "locked_policy_bundle",
                "selection_inputs",
                "selection_outputs",
                "source_commit_sha1",
                "source_tree_sha256",
                "fixed_choices",
                "resolved_choices",
                "unresolved_choices",
                "integer_output_authorizations",
                "confirmation_access_commitment",
                "sealed_before_confirmation_access",
                "claim_ceiling",
            },
            label="CalibrationSelectionDecision",
        )
        if document["role"] != FitRole.CALIBRATION_SELECTION.value:
            raise ContractValidationError(
                "CalibrationSelectionDecision role is invalid"
            )
        raw_decisions = document["hypothesis_decisions"]
        raw_fixed_choices = document["fixed_choices"]
        raw_resolved_choices = document["resolved_choices"]
        raw_choices = document["unresolved_choices"]
        if not isinstance(raw_decisions, list):
            raise ContractValidationError(
                "hypothesis_decisions must be a list"
            )
        if not isinstance(raw_choices, list):
            raise ContractValidationError(
                "unresolved_choices must be a list"
            )
        if not isinstance(raw_resolved_choices, list):
            raise ContractValidationError(
                "resolved_choices must be a list"
            )
        if not isinstance(raw_fixed_choices, list):
            raise ContractValidationError(
                "fixed_choices must be a list"
            )
        return cls(
            artifact_id=artifact_id,
            hypothesis_registry=_ref(
                document["hypothesis_registry"],
                expected=ArtifactType.HYPOTHESIS_REGISTRY,
                label="hypothesis_registry",
            ),
            hypothesis_decisions=tuple(
                HypothesisDecision.from_dict(
                    require_mapping(
                        item,
                        label=f"hypothesis_decisions[{index}]",
                    )
                )
                for index, item in enumerate(raw_decisions)
            ),
            crossed_cell_order_sha256=require_sha256(
                document["crossed_cell_order_sha256"],
                label="crossed_cell_order_sha256",
            ),
            crossed_cell_manifest=_payload(
                document["crossed_cell_manifest"],
                label="crossed_cell_manifest",
                allowed_kinds={
                    PayloadKind.TABLE,
                    PayloadKind.JSON_RECORDS,
                },
            ),
            selected_artifacts=_parse_sorted_refs(
                document["selected_artifacts"],
                label="selected_artifacts",
                allowed=_CALIBRATION_EVIDENCE_TYPES,
            ),
            locked_policy_bundle=_payload(
                document["locked_policy_bundle"],
                label="locked_policy_bundle",
            ),
            selection_inputs=_parse_sorted_refs(
                document["selection_inputs"],
                label="selection_inputs",
                allowed=_CALIBRATION_INPUT_TYPES,
            ),
            selection_outputs=_parse_sorted_refs(
                document["selection_outputs"],
                label="selection_outputs",
                allowed=_CALIBRATION_EVIDENCE_TYPES,
            ),
            source_commit_sha1=_require_git_sha1(
                document["source_commit_sha1"],
                label="source_commit_sha1",
            ),
            source_tree_sha256=require_sha256(
                document["source_tree_sha256"],
                label="source_tree_sha256",
            ),
            fixed_choices=tuple(
                HypothesisFixedChoice.from_dict(
                    require_mapping(
                        item,
                        label=f"fixed_choices[{index}]",
                    )
                )
                for index, item in enumerate(raw_fixed_choices)
            ),
            resolved_choices=tuple(
                HypothesisResolvedChoice.from_dict(
                    require_mapping(
                        item,
                        label=f"resolved_choices[{index}]",
                    )
                )
                for index, item in enumerate(raw_resolved_choices)
            ),
            unresolved_choices=tuple(
                HypothesisRuleChoice.from_dict(
                    require_mapping(
                        item,
                        label=f"unresolved_choices[{index}]",
                    )
                )
                for index, item in enumerate(raw_choices)
            ),
            integer_output_authorizations=_parse_hypothesis_ids(
                document["integer_output_authorizations"],
            ),
            confirmation_access_commitment=_payload(
                document["confirmation_access_commitment"],
                label="confirmation_access_commitment",
            ),
            sealed_before_confirmation_access=require_bool(
                document["sealed_before_confirmation_access"],
                label="sealed_before_confirmation_access",
            ),
            claim_ceiling=_parse_claim(
                document["claim_ceiling"],
                allowed={
                    ClaimLevel.LEVEL_0,
                    ClaimLevel.LEVEL_1G,
                    ClaimLevel.LEVEL_1D,
                    ClaimLevel.LEVEL_2G,
                    ClaimLevel.LEVEL_2T,
                },
            ),
        )


@dataclass(frozen=True, slots=True)
class CalibrationConfirmationResult(_CanonicalArtifact):
    artifact_id: str
    selection_decision: ArtifactRef
    confirmation_cell_order_sha256: str
    confirmation_cells: PayloadRef
    evidence_artifacts: tuple[ArtifactRef, ...]
    locked_result: GateState
    unresolved_hypotheses: tuple[HypothesisId, ...]
    source_commit_sha1: str
    source_tree_sha256: str
    claim_ceiling: ClaimLevel

    schema_version: ClassVar[str] = (
        CALIBRATION_CONFIRMATION_RESULT_SCHEMA
    )
    artifact_type: ClassVar[ArtifactType] = (
        ArtifactType.CALIBRATION_CONFIRMATION_RESULT
    )

    def __post_init__(self) -> None:
        _validate_id(self.artifact_id)
        _ref(
            self.selection_decision,
            expected=ArtifactType.CALIBRATION_SELECTION_DECISION,
            label="selection_decision",
        )
        require_sha256(
            self.confirmation_cell_order_sha256,
            label="confirmation_cell_order_sha256",
        )
        _require_payload_rows(
            (self.confirmation_cells,),
            row_identity_sha256=self.confirmation_cell_order_sha256,
            label="confirmation cells",
            allowed_kinds={
                PayloadKind.TABLE,
                PayloadKind.JSON_RECORDS,
            },
        )
        _sorted_refs(
            self.evidence_artifacts,
            label="evidence_artifacts",
            allowed=_CONFIRMATION_EVIDENCE_TYPES,
        )
        if not isinstance(self.locked_result, GateState):
            raise TypeError("locked_result must be a GateState")
        _validate_hypothesis_ids(self.unresolved_hypotheses)
        _require_git_sha1(
            self.source_commit_sha1,
            label="source_commit_sha1",
        )
        require_sha256(
            self.source_tree_sha256,
            label="source_tree_sha256",
        )
        _validate_claim(
            self.claim_ceiling,
            allowed={
                ClaimLevel.LEVEL_0,
                ClaimLevel.LEVEL_1G,
                ClaimLevel.LEVEL_1D,
                ClaimLevel.LEVEL_2G,
                ClaimLevel.LEVEL_2T,
            },
        )

    def to_dict(self) -> dict[str, object]:
        return {
            **self._header(),
            "role": FitRole.CALIBRATION_CONFIRMATION.value,
            "selection_decision": self.selection_decision.to_dict(),
            "confirmation_cell_order_sha256": (
                self.confirmation_cell_order_sha256
            ),
            "confirmation_cells": self.confirmation_cells.to_dict(),
            "evidence_artifacts": [
                value.to_dict() for value in self.evidence_artifacts
            ],
            "locked_result": self.locked_result.value,
            "unresolved_hypotheses": [
                value.value for value in self.unresolved_hypotheses
            ],
            "source_commit_sha1": self.source_commit_sha1,
            "source_tree_sha256": self.source_tree_sha256,
            "claim_ceiling": self.claim_ceiling.value,
        }

    @classmethod
    def from_dict(
        cls,
        value: Mapping[str, object],
    ) -> "CalibrationConfirmationResult":
        document = require_mapping(
            value,
            label="CalibrationConfirmationResult",
        )
        artifact_id = _header_from_dict(
            document,
            schema_version=cls.schema_version,
            artifact_type=cls.artifact_type,
            fields={
                "role",
                "selection_decision",
                "confirmation_cell_order_sha256",
                "confirmation_cells",
                "evidence_artifacts",
                "locked_result",
                "unresolved_hypotheses",
                "source_commit_sha1",
                "source_tree_sha256",
                "claim_ceiling",
            },
            label="CalibrationConfirmationResult",
        )
        if document["role"] != FitRole.CALIBRATION_CONFIRMATION.value:
            raise ContractValidationError(
                "CalibrationConfirmationResult role is invalid"
            )
        return cls(
            artifact_id=artifact_id,
            selection_decision=_ref(
                document["selection_decision"],
                expected=ArtifactType.CALIBRATION_SELECTION_DECISION,
                label="selection_decision",
            ),
            confirmation_cell_order_sha256=require_sha256(
                document["confirmation_cell_order_sha256"],
                label="confirmation_cell_order_sha256",
            ),
            confirmation_cells=_payload(
                document["confirmation_cells"],
                label="confirmation_cells",
                allowed_kinds={
                    PayloadKind.TABLE,
                    PayloadKind.JSON_RECORDS,
                },
            ),
            evidence_artifacts=_parse_sorted_refs(
                document["evidence_artifacts"],
                label="evidence_artifacts",
                allowed=_CONFIRMATION_EVIDENCE_TYPES,
            ),
            locked_result=enum_from_value(
                GateState,
                document["locked_result"],
                label="locked_result",
            ),
            unresolved_hypotheses=_parse_hypothesis_ids(
                document["unresolved_hypotheses"],
            ),
            source_commit_sha1=_require_git_sha1(
                document["source_commit_sha1"],
                label="source_commit_sha1",
            ),
            source_tree_sha256=require_sha256(
                document["source_tree_sha256"],
                label="source_tree_sha256",
            ),
            claim_ceiling=_parse_claim(
                document["claim_ceiling"],
                allowed={
                    ClaimLevel.LEVEL_0,
                    ClaimLevel.LEVEL_1G,
                    ClaimLevel.LEVEL_1D,
                    ClaimLevel.LEVEL_2G,
                    ClaimLevel.LEVEL_2T,
                },
            ),
        )


InstrumentArtifactValue: TypeAlias = (
    SubstrateBinding
    | SyntheticLatticeSubstrateBinding
    | GraphConstructionSpec
    | CandidateGraph
    | SupportDiagnostic
    | GeometricFieldEstimate
    | OrderParameterSpec
    | OrderParameterField
    | CoreScore
    | CoreCandidate
    | GroundTruthAnchor
    | EdgeConnection
    | GeometryLoopEstimate
    | DefectLoopEstimate
    | CalibrationSelectionDecision
    | CalibrationConfirmationResult
)


_SCHEMA_LOADERS = {
    artifact_type.schema_version: artifact_type.from_dict
    for artifact_type in (
        SubstrateBinding,
        SyntheticLatticeSubstrateBinding,
        GraphConstructionSpec,
        CandidateGraph,
        SupportDiagnostic,
        GeometricFieldEstimate,
        OrderParameterSpec,
        OrderParameterField,
        CoreScore,
        CoreCandidate,
        GroundTruthAnchor,
        EdgeConnection,
        GeometryLoopEstimate,
        DefectLoopEstimate,
        CalibrationSelectionDecision,
        CalibrationConfirmationResult,
    )
}


def instrument_artifact_from_dict(
    value: Mapping[str, object],
) -> InstrumentArtifactValue:
    """Reconstruct exactly one supported instrument artifact."""

    document = require_mapping(value, label="instrument artifact")
    schema_version = document.get("schema_version")
    if not isinstance(schema_version, str):
        raise ContractValidationError(
            "instrument artifact schema_version must be a string"
        )
    loader = _SCHEMA_LOADERS.get(schema_version)
    if loader is None:
        raise ContractValidationError(
            f"unsupported instrument artifact schema {schema_version!r}"
        )
    artifact = loader(document)
    if artifact.to_dict() != dict(document):
        raise ContractValidationError(
            "instrument artifact nested field or canonical value differs"
        )
    return artifact
