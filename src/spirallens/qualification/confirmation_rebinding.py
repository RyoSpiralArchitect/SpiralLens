"""Append-only D6-to-D7 structural rebinding contract.

The historical D6 v0.1 admission requires exact cells and stress-manifest
hashes.  A construction-diverse, new-seed D7 design cannot satisfy those
hashes because the parent bodies contain selection-specific identities.  This
module records the narrower successor rule discovered by the seed-free D7
design: graph axes and thresholds carry forward exactly, while cells and
stress bodies must be rebound through one declared structural projection.

The record does not mutate or reinterpret D6, publish an artifact, admit the
spectral-moment family, freeze seeds, authorize execution, or produce a D7
result.  Its builder and strict loader require authoritative typed parents and
reconstruct the seed-free design instead of accepting caller-supplied digests.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar

from spirallens.core.canonical import (
    CanonicalJsonError,
    canonical_json_bytes,
    canonical_json_sha256,
    parse_canonical_json,
    sha256_bytes,
)
from spirallens.synthetic.spectral_moment_confirmation import (
    SPECTRAL_MOMENT_CASE_REGISTRY,
    SPECTRAL_MOMENT_REQUIRED_CASE_SEMANTICS,
)

from .advancement import (
    IndependentConfirmationAdmissionSpec,
    LoadedScopeLimitedD6Decision,
)
from .common import QualificationContractError, require_sha256, require_slug
from .confirmation_execution_design import (
    D7_CONFIRMATION_EXECUTION_DRAFT_SCHEMA_VERSION,
    D7_CONFIRMATION_SEED_SLOT_IDS,
    D7_STRUCTURAL_PROJECTION_SCHEMA_VERSION,
    D7ConfirmationExecutionDesignDraft,
    D7ParentManifestCompatibility,
    D7ParentProtocolDesignBinding,
    build_seed_free_d7_confirmation_execution_design,
)
from .confirmation_protocol import D7ParentD6Binding
from .persistence import LoadedQualificationProtocol

D6_D7_STRUCTURAL_REBINDING_AMENDMENT_SCHEMA_VERSION = (
    "spirallens.d6-d7-structural-rebinding-amendment.v0.1"
)
D7_SEED_FREE_DESIGN_IDENTITY_SCHEMA_VERSION = (
    "spirallens.d7-seed-free-design-identity.v0.1"
)
D7_EXACT_CARRY_FORWARD_SCHEMA_VERSION = "spirallens.d7-exact-carry-forward.v0.1"
D7_STRUCTURAL_MANIFEST_REBINDING_SCHEMA_VERSION = (
    "spirallens.d7-structural-manifest-rebinding.v0.1"
)
D7_DEFERRED_SUCCESSOR_OBLIGATIONS_SCHEMA_VERSION = (
    "spirallens.d7-deferred-successor-obligations.v0.1"
)
MAX_D6_D7_STRUCTURAL_REBINDING_AMENDMENT_BYTES = 1024 * 1024

_AMENDMENT_FACTORY_TOKEN = object()
_AUTHORITY = {
    "confirmation_family_admitted": False,
    "confirmation_values_accessed": False,
    "d6_admission_spec_satisfied": False,
    "d7_execution_authorized": False,
    "d7_result_produced": False,
    "d8_execution_authorized": False,
    "integer_output_authorized": False,
    "localized_core_loop_join_established": False,
    "model_access_authorized": False,
    "p0_winner_selected": False,
    "pythia_access_authorized": False,
    "representation_instrument_advanced": False,
    "semantic_authority": False,
    "subject_access_authorized": False,
    "synthetic_qualified": False,
    "topology_claim_authorized": False,
}


def _loaded_d6(value: object) -> LoadedScopeLimitedD6Decision:
    if not isinstance(value, LoadedScopeLimitedD6Decision):
        raise TypeError(
            "loaded_d6 must be the authoritative LoadedScopeLimitedD6Decision"
        )
    return value


def _loaded_parent(value: object) -> LoadedQualificationProtocol:
    if not isinstance(value, LoadedQualificationProtocol):
        raise TypeError("parent_protocol must be a strict LoadedQualificationProtocol")
    return value


def _seed_free_design(
    value: object,
) -> D7ConfirmationExecutionDesignDraft:
    if not isinstance(value, D7ConfirmationExecutionDesignDraft):
        raise TypeError(
            "seed_free_design must be a factory-built "
            "D7ConfirmationExecutionDesignDraft"
        )
    return value


@dataclass(frozen=True, slots=True)
class D7SeedFreeDesignIdentity:
    """Exact identity of the factory-reconstructed seed-free design."""

    design_schema_version: str
    draft_id: str
    canonical_sha256: str
    byte_count: int
    manifest_compatibility_sha256: str

    schema_version: ClassVar[str] = D7_SEED_FREE_DESIGN_IDENTITY_SCHEMA_VERSION

    def __post_init__(self) -> None:
        require_slug(self.draft_id, label="draft_id")
        require_sha256(self.canonical_sha256, label="canonical_sha256")
        require_sha256(
            self.manifest_compatibility_sha256,
            label="manifest_compatibility_sha256",
        )
        if self.design_schema_version != (
            D7_CONFIRMATION_EXECUTION_DRAFT_SCHEMA_VERSION
        ):
            raise QualificationContractError(
                "design_schema_version differs from the current D7 draft"
            )
        if self.draft_id != D7ConfirmationExecutionDesignDraft.draft_id:
            raise QualificationContractError(
                "draft_id differs from the current D7 draft"
            )
        if (
            isinstance(self.byte_count, bool)
            or not isinstance(self.byte_count, int)
            or self.byte_count <= 0
        ):
            raise QualificationContractError(
                "seed-free design byte_count must be positive"
            )

    @classmethod
    def from_design(
        cls,
        design: D7ConfirmationExecutionDesignDraft,
    ) -> D7SeedFreeDesignIdentity:
        checked = _seed_free_design(design)
        return cls(
            design_schema_version=checked.schema_version,
            draft_id=checked.draft_id,
            canonical_sha256=checked.canonical_sha256,
            byte_count=len(checked.canonical_bytes),
            manifest_compatibility_sha256=canonical_json_sha256(
                checked.manifest_compatibility.to_dict()
            ),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "design_schema_version": self.design_schema_version,
            "draft_id": self.draft_id,
            "canonical_sha256": self.canonical_sha256,
            "byte_count": self.byte_count,
            "manifest_compatibility_sha256": (
                self.manifest_compatibility_sha256
            ),
            "factory_reconstruction_required": True,
            "canonical_artifact_published": False,
        }


@dataclass(frozen=True, slots=True)
class D7ExactCarryForward:
    """D6 obligations that remain byte-exact in the D7 successor."""

    parent_graph_axes_sha256: str
    successor_graph_axes_sha256: str
    parent_thresholds_sha256: str
    successor_thresholds_sha256: str
    required_surrogate_estimator_id: str
    required_surrogate_trivialization_id: str
    required_case_semantics: tuple[str, ...]
    required_core_and_loop_separation: bool
    selection_evidence_disjointness_required: bool
    policy_override_allowed: bool
    post_selection_exclusion_allowed: bool

    schema_version: ClassVar[str] = D7_EXACT_CARRY_FORWARD_SCHEMA_VERSION

    def __post_init__(self) -> None:
        for name in (
            "parent_graph_axes_sha256",
            "successor_graph_axes_sha256",
            "parent_thresholds_sha256",
            "successor_thresholds_sha256",
        ):
            require_sha256(getattr(self, name), label=name)
        if self.parent_graph_axes_sha256 != self.successor_graph_axes_sha256:
            raise QualificationContractError(
                "D7 graph axes must retain exact D6 byte identity"
            )
        if self.parent_thresholds_sha256 != self.successor_thresholds_sha256:
            raise QualificationContractError(
                "D7 thresholds must retain exact D6 byte identity"
            )
        require_slug(
            self.required_surrogate_estimator_id,
            label="required_surrogate_estimator_id",
        )
        require_slug(
            self.required_surrogate_trivialization_id,
            label="required_surrogate_trivialization_id",
        )
        if self.required_case_semantics != (SPECTRAL_MOMENT_REQUIRED_CASE_SEMANTICS):
            raise QualificationContractError(
                "D7 case semantics differ from the D6-required vocabulary"
            )
        expected_policy = (True, True, False, False)
        observed_policy = (
            self.required_core_and_loop_separation,
            self.selection_evidence_disjointness_required,
            self.policy_override_allowed,
            self.post_selection_exclusion_allowed,
        )
        if observed_policy != expected_policy:
            raise QualificationContractError(
                "D7 retained policy differs from the D6 admission boundary"
            )

    @classmethod
    def from_design(
        cls,
        design: D7ConfirmationExecutionDesignDraft,
        admission: IndependentConfirmationAdmissionSpec,
    ) -> D7ExactCarryForward:
        checked = _seed_free_design(design)
        if not isinstance(admission, IndependentConfirmationAdmissionSpec):
            raise TypeError(
                "admission must be IndependentConfirmationAdmissionSpec"
            )
        admission.__post_init__()
        return cls(
            parent_graph_axes_sha256=(checked.parent_d6.required_graph_axes_sha256),
            successor_graph_axes_sha256=canonical_json_sha256(
                checked.graph_axes.to_dict()
            ),
            parent_thresholds_sha256=(checked.parent_d6.locked_thresholds_sha256),
            successor_thresholds_sha256=canonical_json_sha256(
                checked.thresholds.to_dict()
            ),
            required_surrogate_estimator_id=(
                checked.parent_d6.required_surrogate_estimator_id
            ),
            required_surrogate_trivialization_id=(
                checked.parent_d6.required_surrogate_trivialization_id
            ),
            required_case_semantics=tuple(admission.required_case_semantics),
            required_core_and_loop_separation=(
                admission.required_core_and_loop_separation
            ),
            selection_evidence_disjointness_required=(
                admission.selection_evidence_disjointness_required
            ),
            policy_override_allowed=admission.policy_override_allowed,
            post_selection_exclusion_allowed=(
                admission.post_selection_exclusion_allowed
            ),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "parent_graph_axes_sha256": self.parent_graph_axes_sha256,
            "successor_graph_axes_sha256": (self.successor_graph_axes_sha256),
            "graph_axes_exact_match": True,
            "parent_thresholds_sha256": self.parent_thresholds_sha256,
            "successor_thresholds_sha256": (self.successor_thresholds_sha256),
            "thresholds_exact_match": True,
            "required_surrogate_estimator_id": (self.required_surrogate_estimator_id),
            "required_surrogate_trivialization_id": (
                self.required_surrogate_trivialization_id
            ),
            "required_case_semantics": list(self.required_case_semantics),
            "required_core_and_loop_separation": (
                self.required_core_and_loop_separation
            ),
            "selection_evidence_disjointness_required": (
                self.selection_evidence_disjointness_required
            ),
            "policy_override_allowed": self.policy_override_allowed,
            "post_selection_exclusion_allowed": (
                self.post_selection_exclusion_allowed
            ),
        }


@dataclass(frozen=True, slots=True)
class D7StructuralManifestRebinding:
    """Cells/stress successor identity with an exact structural projection."""

    parent_cells_manifest_sha256: str
    successor_cells_manifest_sha256: str
    parent_stress_manifest_sha256: str
    successor_stress_manifest_sha256: str
    parent_structural_projection_sha256: str
    successor_structural_projection_sha256: str
    structural_projection_schema_version: str
    manifest_compatibility_sha256: str

    schema_version: ClassVar[str] = D7_STRUCTURAL_MANIFEST_REBINDING_SCHEMA_VERSION

    def __post_init__(self) -> None:
        for name in (
            "parent_cells_manifest_sha256",
            "successor_cells_manifest_sha256",
            "parent_stress_manifest_sha256",
            "successor_stress_manifest_sha256",
            "parent_structural_projection_sha256",
            "successor_structural_projection_sha256",
            "manifest_compatibility_sha256",
        ):
            require_sha256(getattr(self, name), label=name)
        if self.parent_cells_manifest_sha256 == (self.successor_cells_manifest_sha256):
            raise QualificationContractError(
                "successor cells manifest must not reuse parent identity"
            )
        if self.parent_stress_manifest_sha256 == (
            self.successor_stress_manifest_sha256
        ):
            raise QualificationContractError(
                "successor stress manifest must not reuse parent identity"
            )
        if self.parent_structural_projection_sha256 != (
            self.successor_structural_projection_sha256
        ):
            raise QualificationContractError(
                "successor structural projection must match the parent"
            )
        if self.structural_projection_schema_version != (
            D7_STRUCTURAL_PROJECTION_SCHEMA_VERSION
        ):
            raise QualificationContractError(
                "structural projection schema differs from the D7 projection"
            )

    @classmethod
    def from_compatibility(
        cls,
        compatibility: D7ParentManifestCompatibility,
    ) -> D7StructuralManifestRebinding:
        if not isinstance(compatibility, D7ParentManifestCompatibility):
            raise TypeError("compatibility must be D7ParentManifestCompatibility")
        document = compatibility.to_dict()
        return cls(
            parent_cells_manifest_sha256=(
                compatibility.parent_required_cells_manifest_sha256
            ),
            successor_cells_manifest_sha256=(
                compatibility.confirmation_cells_manifest_sha256
            ),
            parent_stress_manifest_sha256=(
                compatibility.parent_required_stress_strata_sha256
            ),
            successor_stress_manifest_sha256=(
                compatibility.confirmation_stress_strata_sha256
            ),
            parent_structural_projection_sha256=(
                compatibility.parent_structural_projection_sha256
            ),
            successor_structural_projection_sha256=(
                compatibility.confirmation_structural_projection_sha256
            ),
            structural_projection_schema_version=str(
                document["structural_projection_schema_version"]
            ),
            manifest_compatibility_sha256=canonical_json_sha256(document),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "structural_projection_schema_version": (
                self.structural_projection_schema_version
            ),
            "parent_cells_manifest_sha256": (self.parent_cells_manifest_sha256),
            "successor_cells_manifest_sha256": (self.successor_cells_manifest_sha256),
            "cells_exact_match": False,
            "parent_stress_manifest_sha256": (self.parent_stress_manifest_sha256),
            "successor_stress_manifest_sha256": (self.successor_stress_manifest_sha256),
            "stress_exact_match": False,
            "parent_structural_projection_sha256": (
                self.parent_structural_projection_sha256
            ),
            "successor_structural_projection_sha256": (
                self.successor_structural_projection_sha256
            ),
            "manifest_compatibility_sha256": (
                self.manifest_compatibility_sha256
            ),
            "structural_projection_match": True,
            "selection_identity_reuse_allowed": False,
            "rebinding_satisfies_historical_exact_hashes": False,
            "successor_fulfillment_rule_encoded": True,
            "successor_fulfillment_rule_reviewed": False,
            "successor_fulfillment_rule_published": False,
            "effective_for_admission": False,
        }


@dataclass(frozen=True, slots=True)
class D7DeferredSuccessorObligations:
    """Parent identities retained while successor-specific bodies stay open."""

    parent_selection_implementation_registry_sha256: str
    parent_locked_aggregation_sha256: str

    schema_version: ClassVar[str] = D7_DEFERRED_SUCCESSOR_OBLIGATIONS_SCHEMA_VERSION

    def __post_init__(self) -> None:
        require_sha256(
            self.parent_selection_implementation_registry_sha256,
            label="parent_selection_implementation_registry_sha256",
        )
        require_sha256(
            self.parent_locked_aggregation_sha256,
            label="parent_locked_aggregation_sha256",
        )

    @classmethod
    def from_parent(
        cls,
        parent: D7ParentD6Binding,
    ) -> D7DeferredSuccessorObligations:
        if not isinstance(parent, D7ParentD6Binding):
            raise TypeError("parent must be D7ParentD6Binding")
        return cls(
            parent_selection_implementation_registry_sha256=(
                parent.selection_implementation_registry_sha256
            ),
            parent_locked_aggregation_sha256=(parent.locked_aggregation_sha256),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "parent_selection_implementation_registry_sha256": (
                self.parent_selection_implementation_registry_sha256
            ),
            "parent_locked_aggregation_sha256": (self.parent_locked_aggregation_sha256),
            "d7_implementation_registry_bound": False,
            "d7_aggregation_application_bound": False,
            "construction_diversity_reviewed": False,
            "source_closure_verified": False,
            "family_admitted": False,
            "terminal_schema_and_writer_present": False,
            "full_design_frozen": False,
        }


@dataclass(frozen=True, slots=True, init=False)
class D6D7StructuralRebindingAmendment:
    """Canonical successor-rule proposal; never a historical D6 migration."""

    _source_design: D7ConfirmationExecutionDesignDraft = field(repr=False)
    _source_admission: IndependentConfirmationAdmissionSpec = field(
        repr=False
    )
    parent_d6: D7ParentD6Binding
    parent_protocol: D7ParentProtocolDesignBinding
    seed_free_design: D7SeedFreeDesignIdentity
    exact_carry_forward: D7ExactCarryForward
    structural_rebinding: D7StructuralManifestRebinding
    deferred: D7DeferredSuccessorObligations

    schema_version: ClassVar[str] = D6_D7_STRUCTURAL_REBINDING_AMENDMENT_SCHEMA_VERSION
    amendment_id: ClassVar[str] = (
        "d6-v0-1-to-d7-spectral-moment-structural-rebinding-v0-1"
    )
    status: ClassVar[str] = (
        "structural-rebinding-proposal-encoded-not-reviewed-or-published"
    )
    record_scope: ClassVar[str] = "d7-spectral-moment-cells-and-stress-only"
    claim_ceiling: ClassVar[str] = "level_0"

    def __init__(
        self,
        *,
        _factory_token: object = None,
        source_design: D7ConfirmationExecutionDesignDraft,
        source_admission: IndependentConfirmationAdmissionSpec,
    ) -> None:
        if _factory_token is not _AMENDMENT_FACTORY_TOKEN:
            raise QualificationContractError(
                "D6D7StructuralRebindingAmendment must be produced by the "
                "authoritative builder or strict canonical loader"
            )
        design = _seed_free_design(source_design)
        if not isinstance(
            source_admission,
            IndependentConfirmationAdmissionSpec,
        ):
            raise TypeError(
                "source_admission must be "
                "IndependentConfirmationAdmissionSpec"
            )
        source_admission.__post_init__()
        if source_admission.canonical_sha256 != (
            design.parent_d6.admission_spec_sha256
        ):
            raise QualificationContractError(
                "source admission differs from the D7 parent binding"
            )
        for name, value in (
            ("_source_design", design),
            ("_source_admission", source_admission),
            ("parent_d6", design.parent_d6),
            ("parent_protocol", design.parent),
            (
                "seed_free_design",
                D7SeedFreeDesignIdentity.from_design(design),
            ),
            (
                "exact_carry_forward",
                D7ExactCarryForward.from_design(
                    design,
                    source_admission,
                ),
            ),
            (
                "structural_rebinding",
                D7StructuralManifestRebinding.from_compatibility(
                    design.manifest_compatibility
                ),
            ),
            (
                "deferred",
                D7DeferredSuccessorObligations.from_parent(
                    design.parent_d6
                ),
            ),
        ):
            object.__setattr__(self, name, value)
        self.__post_init__()

    def __post_init__(self) -> None:
        if not isinstance(
            self._source_design,
            D7ConfirmationExecutionDesignDraft,
        ):
            raise TypeError(
                "_source_design must be D7ConfirmationExecutionDesignDraft"
            )
        if not isinstance(
            self._source_admission,
            IndependentConfirmationAdmissionSpec,
        ):
            raise TypeError(
                "_source_admission must be "
                "IndependentConfirmationAdmissionSpec"
            )
        self._source_admission.__post_init__()
        if self._source_admission.canonical_sha256 != (
            self._source_design.parent_d6.admission_spec_sha256
        ):
            raise QualificationContractError(
                "source admission differs from the source design parent"
            )
        if not isinstance(self.parent_d6, D7ParentD6Binding):
            raise TypeError("parent_d6 must be D7ParentD6Binding")
        if not isinstance(
            self.parent_protocol,
            D7ParentProtocolDesignBinding,
        ):
            raise TypeError("parent_protocol must be D7ParentProtocolDesignBinding")
        if not isinstance(
            self.seed_free_design,
            D7SeedFreeDesignIdentity,
        ):
            raise TypeError("seed_free_design must be D7SeedFreeDesignIdentity")
        if not isinstance(
            self.exact_carry_forward,
            D7ExactCarryForward,
        ):
            raise TypeError("exact_carry_forward must be D7ExactCarryForward")
        if not isinstance(
            self.structural_rebinding,
            D7StructuralManifestRebinding,
        ):
            raise TypeError(
                "structural_rebinding must be D7StructuralManifestRebinding"
            )
        if not isinstance(
            self.deferred,
            D7DeferredSuccessorObligations,
        ):
            raise TypeError("deferred must be D7DeferredSuccessorObligations")
        expected = (
            self._source_design.parent_d6,
            self._source_design.parent,
            D7SeedFreeDesignIdentity.from_design(self._source_design),
            D7ExactCarryForward.from_design(
                self._source_design,
                self._source_admission,
            ),
            D7StructuralManifestRebinding.from_compatibility(
                self._source_design.manifest_compatibility
            ),
            D7DeferredSuccessorObligations.from_parent(
                self._source_design.parent_d6
            ),
        )
        observed = (
            self.parent_d6,
            self.parent_protocol,
            self.seed_free_design,
            self.exact_carry_forward,
            self.structural_rebinding,
            self.deferred,
        )
        if observed != expected:
            raise QualificationContractError(
                "D6-D7 rebinding members differ from the source design"
            )
        if self.seed_free_design.manifest_compatibility_sha256 != (
            self.structural_rebinding.manifest_compatibility_sha256
        ):
            raise QualificationContractError(
                "design identity and structural rebinding differ on "
                "manifest compatibility"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "amendment_id": self.amendment_id,
            "status": self.status,
            "record_scope": self.record_scope,
            "claim_ceiling": self.claim_ceiling,
            "parent_d6": self.parent_d6.to_dict(),
            "parent_protocol": self.parent_protocol.to_dict(),
            "seed_free_design": self.seed_free_design.to_dict(),
            "historical_d6": {
                "admission_spec_id": self.parent_d6.admission_spec_id,
                "admission_spec_sha256": (self.parent_d6.admission_spec_sha256),
                "decision_bytes_mutated": False,
                "admission_bytes_mutated": False,
                "historical_admission_reinterpreted": False,
                "exact_parent_cells_manifest_satisfied": False,
                "exact_parent_stress_manifest_satisfied": False,
                "d6_admission_spec_satisfied": False,
            },
            "exact_carry_forward": self.exact_carry_forward.to_dict(),
            "structural_rebinding": self.structural_rebinding.to_dict(),
            "mapping_rules": {
                "parent_seed_identity": ("canonical-parent-selection-seed-ordinal"),
                "successor_seed_identity": "confirmation-seed-slot-index",
                "seed_mapping": [
                    {
                        "parent_seed_ordinal": index,
                        "successor_seed_slot_id": seed_slot_id,
                    }
                    for index, seed_slot_id in enumerate(D7_CONFIRMATION_SEED_SLOT_IDS)
                ],
                "case_mapping": [
                    {
                        "parent_control_semantic": required_semantic,
                        "successor_case_id": case_id,
                    }
                    for (
                        case_id,
                        required_semantic,
                        _recipe,
                        _core,
                        _loop,
                    ) in SPECTRAL_MOMENT_CASE_REGISTRY
                ],
                "numeric_parent_seed_values_retained": False,
                "mapping_is_admission_or_execution_authority": False,
            },
            "deferred": self.deferred.to_dict(),
            "seed_and_execution": {
                "concrete_seed_inventory_present": False,
                "seed_inventory_frozen": False,
                "confirmation_values_accessed": False,
                "launch_authorized": False,
                "execution_authorized": False,
                "result_authorized": False,
            },
            "canonical_artifact_published": False,
            "d7_successor_admission_complete": False,
            "d7_state": "not_run",
            "d8_state": "not_run",
            "authority": dict(sorted(_AUTHORITY.items())),
        }

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_dict())

    @property
    def canonical_sha256(self) -> str:
        return canonical_json_sha256(self.to_dict())

    @classmethod
    def from_canonical_bytes(
        cls,
        source: bytes,
        *,
        expected_sha256: str,
        loaded_d6: LoadedScopeLimitedD6Decision,
        parent_protocol: LoadedQualificationProtocol,
        seed_free_design: D7ConfirmationExecutionDesignDraft,
    ) -> D6D7StructuralRebindingAmendment:
        expected = require_sha256(
            expected_sha256,
            label="expected_sha256",
        )
        if (
            not isinstance(source, bytes)
            or not source
            or len(source) > MAX_D6_D7_STRUCTURAL_REBINDING_AMENDMENT_BYTES
        ):
            raise QualificationContractError(
                "D6-D7 structural rebinding amendment must be nonempty "
                "bytes within the cap"
            )
        if sha256_bytes(source) != expected:
            raise QualificationContractError(
                "D6-D7 structural rebinding amendment source SHA-256 differs"
            )
        try:
            document = parse_canonical_json(
                source,
                label="D6-D7 structural rebinding amendment",
            )
        except CanonicalJsonError as error:
            raise QualificationContractError(str(error)) from error
        rebuilt = build_d6_d7_structural_rebinding_amendment(
            loaded_d6=loaded_d6,
            parent_protocol=parent_protocol,
            seed_free_design=seed_free_design,
        )
        if document != rebuilt.to_dict() or source != rebuilt.canonical_bytes:
            raise QualificationContractError(
                "D6-D7 structural rebinding amendment differs from "
                "authoritative reconstruction"
            )
        return rebuilt


def build_d6_d7_structural_rebinding_amendment(
    *,
    loaded_d6: LoadedScopeLimitedD6Decision,
    parent_protocol: LoadedQualificationProtocol,
    seed_free_design: D7ConfirmationExecutionDesignDraft,
) -> D6D7StructuralRebindingAmendment:
    """Build the successor-only rule from exact authoritative inputs."""

    d6 = _loaded_d6(loaded_d6)
    parent = _loaded_parent(parent_protocol)
    supplied = _seed_free_design(seed_free_design)
    admission = d6.decision.confirmation_admission_spec
    if not isinstance(admission, IndependentConfirmationAdmissionSpec):
        raise QualificationContractError(
            "authoritative D6 receipt lacks the typed admission spec"
        )
    admission.__post_init__()
    expected_design = build_seed_free_d7_confirmation_execution_design(
        loaded_d6=d6,
        parent_protocol=parent,
    )
    if supplied != expected_design:
        raise QualificationContractError(
            "seed-free design differs from authoritative reconstruction"
        )
    return D6D7StructuralRebindingAmendment(
        _factory_token=_AMENDMENT_FACTORY_TOKEN,
        source_design=expected_design,
        source_admission=admission,
    )


__all__ = [
    "D6_D7_STRUCTURAL_REBINDING_AMENDMENT_SCHEMA_VERSION",
    "D7_DEFERRED_SUCCESSOR_OBLIGATIONS_SCHEMA_VERSION",
    "D7_EXACT_CARRY_FORWARD_SCHEMA_VERSION",
    "D7_SEED_FREE_DESIGN_IDENTITY_SCHEMA_VERSION",
    "D7_STRUCTURAL_MANIFEST_REBINDING_SCHEMA_VERSION",
    "MAX_D6_D7_STRUCTURAL_REBINDING_AMENDMENT_BYTES",
    "D6D7StructuralRebindingAmendment",
    "build_d6_d7_structural_rebinding_amendment",
]
