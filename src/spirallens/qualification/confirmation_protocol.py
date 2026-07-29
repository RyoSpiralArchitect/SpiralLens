"""Value-blind D7 construction foundation, explicitly not a design freeze.

The only public builder in this module requires the authoritative receipt
returned by ``load_scope_limited_d6_decision``.  It derives every inherited
identity from that receipt; a caller cannot substitute a bare admission spec
or arbitrary digest strings.

This module intentionally stops before the obligations that make a D7 design
frozen: reviewed construction-diversity comparison, committed source closure,
seed and execution inventory, stress translation, full crossed execution,
pre-access lifecycle, namespace claim, and terminal schemas.  Those gaps are
serialized as false rather than implied by a type name.
"""

from __future__ import annotations

from dataclasses import dataclass
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
    SPECTRAL_MOMENT_CONSTRUCTION_FAMILY_ID,
    SPECTRAL_MOMENT_GENERATOR_FAMILY_ID,
    SPECTRAL_MOMENT_IMPLEMENTATION_ID,
    SPECTRAL_MOMENT_IMPLEMENTATION_VERSION,
    SPECTRAL_MOMENT_REQUIRED_CASE_SEMANTICS,
    SPECTRAL_MOMENT_SOURCE_PATH,
)

from .advancement import (
    IndependentConfirmationAdmissionSpec,
    LoadedScopeLimitedD6Decision,
)
from .common import QualificationContractError, require_sha256, require_slug

D7_CONFIRMATION_FOUNDATION_SCHEMA_VERSION = (
    "spirallens.d7-confirmation-foundation.v0.1"
)
D7_CONFIRMATION_CASE_BINDING_SCHEMA_VERSION = (
    "spirallens.d7-confirmation-case-binding.v0.1"
)
D7_PARENT_D6_BINDING_SCHEMA_VERSION = (
    "spirallens.d7-parent-d6-binding.v0.1"
)
D7_CONFIRMATION_FAMILY_PROPOSAL_SCHEMA_VERSION = (
    "spirallens.d7-confirmation-family-proposal.v0.1"
)
D7_LOCKED_INTERFACE_PROPOSAL_SCHEMA_VERSION = (
    "spirallens.d7-locked-interface-proposal.v0.1"
)
D7_FOUNDATION_OBLIGATIONS_SCHEMA_VERSION = (
    "spirallens.d7-foundation-obligations.v0.1"
)
MAX_D7_CONFIRMATION_FOUNDATION_BYTES = 256 * 1024

D6_DECISION_REPOSITORY_PATH = (
    "experiments/qualification/d0_d5_f2_cartesian_selection_v0_1/"
    "d6-surrogate-advancement-decision.json"
)
SPECTRAL_MOMENT_INPUT_ADAPTER_ID = (
    "spectral-moment-confirmation-cartesian-input-v0.1"
)

def _mechanism_descriptor() -> dict[str, object]:
    return {
        "schema_version": "spirallens.construction-mechanism.v0.1",
        "construction": "separable-sine-spectral-moment-grid",
        "matched_domain": "fixed-seven-by-seven-discrete-grid",
        "fit_evaluation_split": "interleaved-even-fit-odd-evaluation",
        "case_recipes": [item[2] for item in SPECTRAL_MOMENT_CASE_REGISTRY],
        "seed_source_or_label_excluded_from_identity": True,
    }


SPECTRAL_MOMENT_MECHANISM_SHA256 = canonical_json_sha256(
    _mechanism_descriptor()
)
SPECTRAL_MOMENT_CASE_REGISTRY_SHA256 = canonical_json_sha256(
    [
        {
            "case_id": item[0],
            "required_semantic": item[1],
            "construction_recipe_id": item[2],
            "core_disposition": item[3],
            "loop_disposition": item[4],
        }
        for item in SPECTRAL_MOMENT_CASE_REGISTRY
    ]
)

_AUTHORITY = {
    "confirmation_family_admitted": False,
    "confirmation_values_accessed": False,
    "d6_d8_advanced": False,
    "d7_execution_authorized": False,
    "d7_result_produced": False,
    "d8_execution_authorized": False,
    "integer_output_authorized": False,
    "localized_core_loop_join_established": False,
    "p0_winner_selected": False,
    "pythia_access_authorized": False,
    "representation_instrument_advanced": False,
    "semantic_authority": False,
    "subject_access_authorized": False,
    "subject_execution_authorized": False,
    "synthetic_qualified": False,
    "topology_claim_authorized": False,
}


def _loaded_d6(
    value: object,
) -> LoadedScopeLimitedD6Decision:
    if not isinstance(value, LoadedScopeLimitedD6Decision):
        raise TypeError(
            "loaded_d6 must be the authoritative LoadedScopeLimitedD6Decision "
            "returned by load_scope_limited_d6_decision"
        )
    return value


def _admission(
    loaded_d6: LoadedScopeLimitedD6Decision,
) -> IndependentConfirmationAdmissionSpec:
    spec = loaded_d6.decision.confirmation_admission_spec
    if not isinstance(spec, IndependentConfirmationAdmissionSpec):
        raise QualificationContractError(
            "authoritative D6 receipt does not contain the typed admission spec"
        )
    return spec


@dataclass(frozen=True, slots=True, init=False)
class D7ParentD6Binding:
    """Canonical identity of the authoritative committed D6 parent."""

    d6_decision_id: str
    d6_decision_source_sha256: str
    d6_decision_canonical_sha256: str
    d6_decision_source_commit: str
    current_loader_source_commit: str
    current_loader_source_binding_sha256: str
    admission_spec_id: str
    admission_spec_sha256: str
    selection_terminal_binding_sha256: str
    selection_generator_family_id: str
    selection_construction_family_id: str
    selection_implementation_registry_sha256: str
    required_surrogate_estimator_id: str
    required_surrogate_trivialization_id: str
    required_graph_axes_sha256: str
    required_stress_strata_sha256: str
    required_cells_manifest_sha256: str
    locked_thresholds_sha256: str
    locked_aggregation_sha256: str

    schema_version: ClassVar[str] = D7_PARENT_D6_BINDING_SCHEMA_VERSION
    repository_path: ClassVar[str] = D6_DECISION_REPOSITORY_PATH
    committed_artifact_verified: ClassVar[bool] = True
    historical_terminal_companions_verified: ClassVar[bool] = True
    current_loader_source_surface_verified: ClassVar[bool] = True

    def __post_init__(self) -> None:
        for name in (
            "d6_decision_id",
            "admission_spec_id",
            "selection_generator_family_id",
            "selection_construction_family_id",
            "required_surrogate_estimator_id",
            "required_surrogate_trivialization_id",
        ):
            require_slug(getattr(self, name), label=name)
        for name in (
            "d6_decision_source_sha256",
            "d6_decision_canonical_sha256",
            "current_loader_source_binding_sha256",
            "admission_spec_sha256",
            "selection_terminal_binding_sha256",
            "selection_implementation_registry_sha256",
            "required_graph_axes_sha256",
            "required_stress_strata_sha256",
            "required_cells_manifest_sha256",
            "locked_thresholds_sha256",
            "locked_aggregation_sha256",
        ):
            require_sha256(getattr(self, name), label=name)
        for name in (
            "d6_decision_source_commit",
            "current_loader_source_commit",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, str)
                or len(value) != 40
                or any(char not in "0123456789abcdef" for char in value)
            ):
                raise QualificationContractError(
                    f"{name} must be a lowercase 40-character Git commit"
                )

    @classmethod
    def from_loaded(
        cls,
        loaded_d6: LoadedScopeLimitedD6Decision,
    ) -> D7ParentD6Binding:
        loaded = _loaded_d6(loaded_d6)
        decision = loaded.decision
        spec = _admission(loaded)
        path = loaded.identity.path.as_posix()
        if not path.endswith(f"/{D6_DECISION_REPOSITORY_PATH}"):
            raise QualificationContractError(
                "authoritative D6 artifact path differs from the closed "
                "repository path"
            )
        values = {
            "d6_decision_id": decision.decision_id,
            "d6_decision_source_sha256": loaded.identity.source_sha256,
            "d6_decision_canonical_sha256": loaded.identity.canonical_sha256,
            "d6_decision_source_commit": decision.decision_source_commit,
            "current_loader_source_commit": loaded.current_loader_source_commit,
            "current_loader_source_binding_sha256": (
                loaded.current_loader_source_binding_sha256
            ),
            "admission_spec_id": spec.admission_spec_id,
            "admission_spec_sha256": spec.canonical_sha256,
            "selection_terminal_binding_sha256": (
                spec.selection_terminal_binding_sha256
            ),
            "selection_generator_family_id": (
                spec.selection_generator_family_id
            ),
            "selection_construction_family_id": (
                spec.selection_construction_family_id
            ),
            "selection_implementation_registry_sha256": (
                spec.selection_implementation_registry_sha256
            ),
            "required_surrogate_estimator_id": (
                spec.required_surrogate_estimator_id
            ),
            "required_surrogate_trivialization_id": (
                spec.required_surrogate_trivialization_id
            ),
            "required_graph_axes_sha256": spec.required_graph_axes_sha256,
            "required_stress_strata_sha256": (
                spec.required_stress_strata_sha256
            ),
            "required_cells_manifest_sha256": (
                spec.required_cells_manifest_sha256
            ),
            "locked_thresholds_sha256": spec.locked_thresholds_sha256,
            "locked_aggregation_sha256": spec.locked_aggregation_sha256,
        }
        result = object.__new__(cls)
        for name, value in values.items():
            object.__setattr__(result, name, value)
        result.__post_init__()
        return result

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "repository_path": self.repository_path,
            "d6_decision_id": self.d6_decision_id,
            "d6_decision_source_sha256": self.d6_decision_source_sha256,
            "d6_decision_canonical_sha256": (
                self.d6_decision_canonical_sha256
            ),
            "d6_decision_source_commit": self.d6_decision_source_commit,
            "current_loader_source_commit": self.current_loader_source_commit,
            "current_loader_source_binding_sha256": (
                self.current_loader_source_binding_sha256
            ),
            "admission_spec_id": self.admission_spec_id,
            "admission_spec_sha256": self.admission_spec_sha256,
            "selection_terminal_binding_sha256": (
                self.selection_terminal_binding_sha256
            ),
            "selection_generator_family_id": (
                self.selection_generator_family_id
            ),
            "selection_construction_family_id": (
                self.selection_construction_family_id
            ),
            "selection_implementation_registry_sha256": (
                self.selection_implementation_registry_sha256
            ),
            "required_surrogate_estimator_id": (
                self.required_surrogate_estimator_id
            ),
            "required_surrogate_trivialization_id": (
                self.required_surrogate_trivialization_id
            ),
            "required_graph_axes_sha256": self.required_graph_axes_sha256,
            "required_stress_strata_sha256": (
                self.required_stress_strata_sha256
            ),
            "required_cells_manifest_sha256": (
                self.required_cells_manifest_sha256
            ),
            "locked_thresholds_sha256": self.locked_thresholds_sha256,
            "locked_aggregation_sha256": self.locked_aggregation_sha256,
            "committed_artifact_verified": self.committed_artifact_verified,
            "historical_terminal_companions_verified": (
                self.historical_terminal_companions_verified
            ),
            "current_loader_source_surface_verified": (
                self.current_loader_source_surface_verified
            ),
        }


@dataclass(frozen=True, slots=True)
class D7ConfirmationCaseBinding:
    """One generator case joined to the shared canonical case registry."""

    case_id: str
    required_semantic: str
    construction_recipe_id: str
    core_disposition: str
    loop_disposition: str

    schema_version: ClassVar[str] = (
        D7_CONFIRMATION_CASE_BINDING_SCHEMA_VERSION
    )

    def __post_init__(self) -> None:
        if (
            self.case_id,
            self.required_semantic,
            self.construction_recipe_id,
            self.core_disposition,
            self.loop_disposition,
        ) not in SPECTRAL_MOMENT_CASE_REGISTRY:
            raise QualificationContractError(
                "confirmation case differs from the shared generator registry"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "case_id": self.case_id,
            "required_semantic": self.required_semantic,
            "construction_recipe_id": self.construction_recipe_id,
            "core_disposition": self.core_disposition,
            "loop_disposition": self.loop_disposition,
            "oracle_separated_from_estimator_input": True,
        }


def _case_bindings() -> tuple[D7ConfirmationCaseBinding, ...]:
    return tuple(
        D7ConfirmationCaseBinding(
            case_id=item[0],
            required_semantic=item[1],
            construction_recipe_id=item[2],
            core_disposition=item[3],
            loop_disposition=item[4],
        )
        for item in SPECTRAL_MOMENT_CASE_REGISTRY
    )


@dataclass(frozen=True, slots=True)
class D7ConfirmationFamilyProposal:
    """Proposed distinct construction; review and admission remain false."""

    selection_generator_family_id: str
    selection_construction_family_id: str

    schema_version: ClassVar[str] = (
        D7_CONFIRMATION_FAMILY_PROPOSAL_SCHEMA_VERSION
    )

    def __post_init__(self) -> None:
        require_slug(
            self.selection_generator_family_id,
            label="selection_generator_family_id",
        )
        require_slug(
            self.selection_construction_family_id,
            label="selection_construction_family_id",
        )
        if self.selection_generator_family_id == (
            SPECTRAL_MOMENT_GENERATOR_FAMILY_ID
        ):
            raise QualificationContractError(
                "confirmation generator ID must differ from selection"
            )
        if self.selection_construction_family_id == (
            SPECTRAL_MOMENT_CONSTRUCTION_FAMILY_ID
        ):
            raise QualificationContractError(
                "confirmation construction ID must differ from selection"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "selection_generator_family_id": (
                self.selection_generator_family_id
            ),
            "selection_construction_family_id": (
                self.selection_construction_family_id
            ),
            "confirmation_generator_family_id": (
                SPECTRAL_MOMENT_GENERATOR_FAMILY_ID
            ),
            "confirmation_construction_family_id": (
                SPECTRAL_MOMENT_CONSTRUCTION_FAMILY_ID
            ),
            "confirmation_implementation_id": (
                SPECTRAL_MOMENT_IMPLEMENTATION_ID
            ),
            "confirmation_implementation_version": (
                SPECTRAL_MOMENT_IMPLEMENTATION_VERSION
            ),
            "confirmation_source_path": SPECTRAL_MOMENT_SOURCE_PATH,
            "mechanism_descriptor": _mechanism_descriptor(),
            "mechanism_sha256": SPECTRAL_MOMENT_MECHANISM_SHA256,
            "case_registry_sha256": (
                SPECTRAL_MOMENT_CASE_REGISTRY_SHA256
            ),
            "identifier_difference_observed": True,
            "identifier_difference_proves_construction_diversity": False,
            "same_schema_mechanism_comparison_reviewed": False,
            "committed_source_closure_verified": False,
            "epistemic_independence_proved": False,
            "seed_change_alone_sufficient": False,
            "source_or_label_change_alone_sufficient": False,
            "family_admitted": False,
        }


@dataclass(frozen=True, slots=True)
class D7LockedInterfaceProposal:
    """D6 hashes copied exactly; their full design bytes are not yet rebound."""

    required_surrogate_estimator_id: str
    required_surrogate_trivialization_id: str
    required_graph_axes_sha256: str
    required_stress_strata_sha256: str
    required_cells_manifest_sha256: str
    locked_thresholds_sha256: str
    locked_aggregation_sha256: str

    schema_version: ClassVar[str] = (
        D7_LOCKED_INTERFACE_PROPOSAL_SCHEMA_VERSION
    )

    def __post_init__(self) -> None:
        require_slug(
            self.required_surrogate_estimator_id,
            label="required_surrogate_estimator_id",
        )
        require_slug(
            self.required_surrogate_trivialization_id,
            label="required_surrogate_trivialization_id",
        )
        for name in (
            "required_graph_axes_sha256",
            "required_stress_strata_sha256",
            "required_cells_manifest_sha256",
            "locked_thresholds_sha256",
            "locked_aggregation_sha256",
        ):
            require_sha256(getattr(self, name), label=name)

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "required_surrogate_estimator_id": (
                self.required_surrogate_estimator_id
            ),
            "required_surrogate_trivialization_id": (
                self.required_surrogate_trivialization_id
            ),
            "input_adapter_id": SPECTRAL_MOMENT_INPUT_ADAPTER_ID,
            "required_graph_axes_sha256": self.required_graph_axes_sha256,
            "required_stress_strata_sha256": (
                self.required_stress_strata_sha256
            ),
            "required_cells_manifest_sha256": (
                self.required_cells_manifest_sha256
            ),
            "locked_thresholds_sha256": self.locked_thresholds_sha256,
            "locked_aggregation_sha256": self.locked_aggregation_sha256,
            "estimator_override_allowed": False,
            "trivialization_override_allowed": False,
            "full_parent_design_bytes_reconstructed": False,
            "stress_translation_implemented": False,
            "full_crossed_path_implemented": False,
        }


@dataclass(frozen=True, slots=True)
class D7FoundationObligations:
    """Every missing full-freeze obligation remains machine-visible."""

    schema_version: ClassVar[str] = (
        D7_FOUNDATION_OBLIGATIONS_SCHEMA_VERSION
    )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "construction_diversity_reviewed": False,
            "committed_seed_free_source_closure_verified": False,
            "confirmation_seed_inventory_frozen": False,
            "required_execution_inventory_frozen": False,
            "required_execution_count_frozen": False,
            "attempted_and_evaluable_universes_frozen": False,
            "boundary_translation_implemented": False,
            "state_geometry_warp_translation_implemented": False,
            "structured_observation_perturbation_translation_implemented": (
                False
            ),
            "offcore_loop_control_implemented": False,
            "all_graph_pairs_and_loop_roles_implemented": False,
            "core_and_loop_path_join_implemented": False,
            "threshold_and_aggregation_path_implemented": False,
            "readiness_receipt_implemented": False,
            "launch_intent_implemented": False,
            "exclusive_attempt_claim_implemented": False,
            "output_namespace_absence_verified": False,
            "terminal_result_and_failure_schemas_implemented": False,
            "runner_and_atomic_terminal_writer_implemented": False,
            "canonical_design_artifact_published": False,
            "pre_access_design_freeze_receipt_issued": False,
        }


@dataclass(frozen=True, slots=True)
class D7ConfirmationFoundation:
    """Canonical implementation foundation, never a freeze or admission."""

    parent_d6: D7ParentD6Binding
    family: D7ConfirmationFamilyProposal
    cases: tuple[D7ConfirmationCaseBinding, ...]
    locked_interface: D7LockedInterfaceProposal
    obligations: D7FoundationObligations

    schema_version: ClassVar[str] = D7_CONFIRMATION_FOUNDATION_SCHEMA_VERSION
    foundation_id: ClassVar[str] = (
        "d7-spectral-moment-confirmation-foundation-v0-1"
    )
    status: ClassVar[str] = "implementation-foundation-not-frozen"
    claim_ceiling: ClassVar[str] = "level_0"
    record_scope: ClassVar[str] = "canonical-draft-contract-only"

    def __post_init__(self) -> None:
        if not isinstance(self.parent_d6, D7ParentD6Binding):
            raise TypeError("parent_d6 must be a D7ParentD6Binding")
        if not isinstance(self.family, D7ConfirmationFamilyProposal):
            raise TypeError(
                "family must be a D7ConfirmationFamilyProposal"
            )
        if self.cases != _case_bindings():
            raise QualificationContractError(
                "foundation must bind the exact shared four-case registry"
            )
        if not isinstance(
            self.locked_interface,
            D7LockedInterfaceProposal,
        ):
            raise TypeError(
                "locked_interface must be a D7LockedInterfaceProposal"
            )
        if not isinstance(self.obligations, D7FoundationObligations):
            raise TypeError(
                "obligations must be a D7FoundationObligations"
            )
        if (
            self.family.selection_generator_family_id
            != self.parent_d6.selection_generator_family_id
            or self.family.selection_construction_family_id
            != self.parent_d6.selection_construction_family_id
        ):
            raise QualificationContractError(
                "family proposal differs from the authoritative D6 parent"
            )
        expected_interface = _interface_from_parent(self.parent_d6)
        if self.locked_interface != expected_interface:
            raise QualificationContractError(
                "locked interface differs from the authoritative D6 parent"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "foundation_id": self.foundation_id,
            "status": self.status,
            "record_scope": self.record_scope,
            "claim_ceiling": self.claim_ceiling,
            "parent_d6": self.parent_d6.to_dict(),
            "family": self.family.to_dict(),
            "cases": [item.to_dict() for item in self.cases],
            "locked_interface": self.locked_interface.to_dict(),
            "obligations": self.obligations.to_dict(),
            "d7_state": "not_run",
            "d8_state": "not_run",
            "confirmation_values_accessed": False,
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
    ) -> D7ConfirmationFoundation:
        """Strictly reload exact canonical bytes against authoritative D6."""

        expected_digest = require_sha256(
            expected_sha256,
            label="expected_sha256",
        )
        if (
            not isinstance(source, bytes)
            or not source
            or len(source) > MAX_D7_CONFIRMATION_FOUNDATION_BYTES
        ):
            raise QualificationContractError(
                "D7 foundation must be nonempty bytes within the fixed cap"
            )
        if sha256_bytes(source) != expected_digest:
            raise QualificationContractError(
                "D7 foundation source SHA-256 differs"
            )
        try:
            document = parse_canonical_json(
                source,
                label="D7 confirmation foundation",
            )
        except CanonicalJsonError as error:
            raise QualificationContractError(str(error)) from error
        expected = build_spectral_moment_d7_confirmation_foundation(
            loaded_d6
        )
        if document != expected.to_dict() or source != expected.canonical_bytes:
            raise QualificationContractError(
                "D7 foundation differs from its authoritative reconstruction"
            )
        return expected


def _interface_from_parent(
    parent: D7ParentD6Binding,
) -> D7LockedInterfaceProposal:
    return D7LockedInterfaceProposal(
        required_surrogate_estimator_id=(
            parent.required_surrogate_estimator_id
        ),
        required_surrogate_trivialization_id=(
            parent.required_surrogate_trivialization_id
        ),
        required_graph_axes_sha256=parent.required_graph_axes_sha256,
        required_stress_strata_sha256=parent.required_stress_strata_sha256,
        required_cells_manifest_sha256=(
            parent.required_cells_manifest_sha256
        ),
        locked_thresholds_sha256=parent.locked_thresholds_sha256,
        locked_aggregation_sha256=parent.locked_aggregation_sha256,
    )


def build_spectral_moment_d7_confirmation_foundation(
    loaded_d6: LoadedScopeLimitedD6Decision,
) -> D7ConfirmationFoundation:
    """Build the value-blind foundation from one authoritative D6 receipt."""

    loaded = _loaded_d6(loaded_d6)
    spec = _admission(loaded)
    if tuple(spec.required_case_semantics) != (
        SPECTRAL_MOMENT_REQUIRED_CASE_SEMANTICS
    ):
        raise QualificationContractError(
            "D6 case semantics differ from the shared generator registry"
        )
    parent = D7ParentD6Binding.from_loaded(loaded)
    return D7ConfirmationFoundation(
        parent_d6=parent,
        family=D7ConfirmationFamilyProposal(
            selection_generator_family_id=(
                parent.selection_generator_family_id
            ),
            selection_construction_family_id=(
                parent.selection_construction_family_id
            ),
        ),
        cases=_case_bindings(),
        locked_interface=_interface_from_parent(parent),
        obligations=D7FoundationObligations(),
    )


__all__ = [
    "D6_DECISION_REPOSITORY_PATH",
    "D7_CONFIRMATION_CASE_BINDING_SCHEMA_VERSION",
    "D7_CONFIRMATION_FAMILY_PROPOSAL_SCHEMA_VERSION",
    "D7_CONFIRMATION_FOUNDATION_SCHEMA_VERSION",
    "D7_FOUNDATION_OBLIGATIONS_SCHEMA_VERSION",
    "D7_LOCKED_INTERFACE_PROPOSAL_SCHEMA_VERSION",
    "D7_PARENT_D6_BINDING_SCHEMA_VERSION",
    "MAX_D7_CONFIRMATION_FOUNDATION_BYTES",
    "SPECTRAL_MOMENT_CASE_REGISTRY_SHA256",
    "SPECTRAL_MOMENT_CONSTRUCTION_FAMILY_ID",
    "SPECTRAL_MOMENT_GENERATOR_FAMILY_ID",
    "SPECTRAL_MOMENT_INPUT_ADAPTER_ID",
    "SPECTRAL_MOMENT_MECHANISM_SHA256",
    "D7ConfirmationCaseBinding",
    "D7ConfirmationFamilyProposal",
    "D7ConfirmationFoundation",
    "D7FoundationObligations",
    "D7LockedInterfaceProposal",
    "D7ParentD6Binding",
    "build_spectral_moment_d7_confirmation_foundation",
]
