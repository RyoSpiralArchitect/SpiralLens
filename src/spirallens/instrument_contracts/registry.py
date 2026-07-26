"""Typed, metadata-only contracts for the P0 F0--F4 hypothesis registry."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Mapping

from .canonical import canonical_json_sha256
from .common import (
    ClaimLevel,
    EvolutionAxis,
    FitRole,
    HypothesisId,
    ResolutionState,
    RuleChoice,
    ScientificBranch,
)


HYPOTHESIS_REGISTRY_SCHEMA_VERSION = "spirallens.hypothesis-registry.v0.1"
P0_REGISTRY_POLICY_VERSION = "spirallens.p0-registry-policy.v0.1"
P0_HISTORICAL_SNAPSHOT_ID = (
    "pythia70_slot_only_001_layer0_subject_audit_v0_4"
)
P0_HISTORICAL_CUTOFF_COMMIT = (
    "23480d16f86f4e5616fa77c5b7ff93b2d6a5469d"
)
P0_HISTORICAL_OUTCOME_INTEGRATION_COMMIT = (
    "403638bee75d87010b5f897392feb126c3911148"
)
P0_HISTORICAL_OUTCOME_RECORD_PATH = (
    "protocols/"
    "pythia70_slot_only_001_layer0_subject_audit_v0_4_"
    "outcome_observation.yaml"
)
P0_HISTORICAL_OUTCOME_RECORD_SOURCE_SHA256 = (
    "7ac964b55fe226a1b2c4deaf757c96b14d5a1fe36f42363ca739dfe50fab44f5"
)
P0_HISTORICAL_OUTCOME_ARTIFACT_SOURCE_SHA256 = (
    "eaad9dfd6652e854570edc8aaa5282d239d3c218a924a4498d480539bb02ee06"
)
_GIT_COMMIT = re.compile(r"^[0-9a-f]{40}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class HypothesisRegistryError(ValueError):
    """Base error for structurally invalid hypothesis-registry contracts."""


class HypothesisRegistryPolicyError(HypothesisRegistryError):
    """Raised when a valid registry violates the frozen P0 policy."""


def _require_text(value: object, *, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise HypothesisRegistryError(f"{label} must be a non-empty string")
    if value != value.strip():
        raise HypothesisRegistryError(
            f"{label} must not have surrounding whitespace"
        )
    return value


def _require_bool(value: object, *, label: str) -> bool:
    if type(value) is not bool:
        raise HypothesisRegistryError(f"{label} must be a boolean")
    return value


def _require_identifier_tuple(
    values: object,
    *,
    label: str,
    allow_empty: bool = False,
) -> tuple[str, ...]:
    if not isinstance(values, tuple):
        raise HypothesisRegistryError(f"{label} must be a tuple")
    if not values and not allow_empty:
        raise HypothesisRegistryError(f"{label} must not be empty")
    normalized = tuple(
        _require_text(value, label=f"{label}[{index}]")
        for index, value in enumerate(values)
    )
    if len(normalized) != len(set(normalized)):
        raise HypothesisRegistryError(f"{label} must not contain duplicates")
    if normalized != tuple(sorted(normalized)):
        raise HypothesisRegistryError(f"{label} must be sorted")
    return normalized


def _choice_to_dict(choice: RuleChoice) -> dict[str, object]:
    return {
        "family_id": choice.family_id,
        "resolution": choice.resolution.value,
        "selected_id": choice.selected_id,
        "candidate_ids": list(choice.candidate_ids),
    }


@dataclass(frozen=True, slots=True)
class HistoricalSelectionBoundary:
    """Chronology and evidence firewall without any observed outcome value."""

    historical_snapshot_id: str
    historical_cutoff_commit: str
    historical_outcome_integration_commit: str
    historical_outcome_record_path: str
    historical_outcome_record_source_sha256: str
    historical_outcome_artifact_source_sha256: str
    registry_postdates_prior_outcome: bool
    prior_outcome_allowed_for_selection: bool
    allowed_selection_evidence: tuple[str, ...]
    forbidden_selection_inputs: tuple[str, ...]

    def __post_init__(self) -> None:
        _require_text(
            self.historical_snapshot_id, label="historical_snapshot_id"
        )
        cutoff = _require_text(
            self.historical_cutoff_commit,
            label="historical_cutoff_commit",
        )
        if _GIT_COMMIT.fullmatch(cutoff) is None:
            raise HypothesisRegistryError(
                "historical_cutoff_commit must be a lowercase 40-character "
                "git commit"
            )
        integration_commit = _require_text(
            self.historical_outcome_integration_commit,
            label="historical_outcome_integration_commit",
        )
        if _GIT_COMMIT.fullmatch(integration_commit) is None:
            raise HypothesisRegistryError(
                "historical_outcome_integration_commit must be a lowercase "
                "40-character git commit"
            )
        _require_text(
            self.historical_outcome_record_path,
            label="historical_outcome_record_path",
        )
        for name in (
            "historical_outcome_record_source_sha256",
            "historical_outcome_artifact_source_sha256",
        ):
            digest = _require_text(getattr(self, name), label=name)
            if _SHA256.fullmatch(digest) is None:
                raise HypothesisRegistryError(
                    f"{name} must be a lowercase SHA-256 digest"
                )
        _require_bool(
            self.registry_postdates_prior_outcome,
            label="registry_postdates_prior_outcome",
        )
        _require_bool(
            self.prior_outcome_allowed_for_selection,
            label="prior_outcome_allowed_for_selection",
        )
        _require_identifier_tuple(
            self.allowed_selection_evidence,
            label="allowed_selection_evidence",
        )
        _require_identifier_tuple(
            self.forbidden_selection_inputs,
            label="forbidden_selection_inputs",
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "historical_snapshot_id": self.historical_snapshot_id,
            "historical_cutoff_commit": self.historical_cutoff_commit,
            "historical_outcome_integration_commit": (
                self.historical_outcome_integration_commit
            ),
            "historical_outcome_record_path": (
                self.historical_outcome_record_path
            ),
            "historical_outcome_record_source_sha256": (
                self.historical_outcome_record_source_sha256
            ),
            "historical_outcome_artifact_source_sha256": (
                self.historical_outcome_artifact_source_sha256
            ),
            "registry_postdates_prior_outcome": (
                self.registry_postdates_prior_outcome
            ),
            "prior_outcome_allowed_for_selection": (
                self.prior_outcome_allowed_for_selection
            ),
            "allowed_selection_evidence": list(self.allowed_selection_evidence),
            "forbidden_selection_inputs": list(
                self.forbidden_selection_inputs
            ),
        }


@dataclass(frozen=True, slots=True)
class HypothesisSpec:
    """One structural hypothesis, with choices explicit and outcome-free."""

    hypothesis_id: HypothesisId
    branch: ScientificBranch
    current_claim_level: ClaimLevel
    claim_ceiling: ClaimLevel
    input_tensor: RuleChoice
    observation_axis: RuleChoice
    centering_rule: RuleChoice
    residual_rule: RuleChoice
    architecture_accounting_rule: RuleChoice
    estimator: RuleChoice
    fit_role: RuleChoice
    domain_binding: str
    substrate_binding: str
    rank_convention: str
    gauge_law: str
    target_manifold: str
    charge_group: str
    amplitude_quantity: str
    support_quantities: tuple[str, ...]
    identifiability_quantities: tuple[str, ...]
    interpolation_rule: RuleChoice
    lift_rule: RuleChoice
    trivialization_rule: RuleChoice
    reference_rule: RuleChoice
    edge_connection_rule: str
    allowed_observables: tuple[str, ...]
    forbidden_labels: tuple[str, ...]
    required_controls: tuple[str, ...]
    winding_prerequisites: tuple[str, ...]
    failure_reasons: tuple[str, ...]
    integer_output_authorized: bool

    def __post_init__(self) -> None:
        if not isinstance(self.hypothesis_id, HypothesisId):
            raise HypothesisRegistryError(
                "hypothesis_id must be a HypothesisId"
            )
        if not isinstance(self.branch, ScientificBranch):
            raise HypothesisRegistryError("branch must be a ScientificBranch")
        if not isinstance(self.current_claim_level, ClaimLevel):
            raise HypothesisRegistryError(
                "current_claim_level must be a ClaimLevel"
            )
        if not isinstance(self.claim_ceiling, ClaimLevel):
            raise HypothesisRegistryError(
                "claim_ceiling must be a ClaimLevel"
            )
        for name in (
            "input_tensor",
            "observation_axis",
            "centering_rule",
            "residual_rule",
            "architecture_accounting_rule",
            "estimator",
            "fit_role",
            "interpolation_rule",
            "lift_rule",
            "trivialization_rule",
            "reference_rule",
        ):
            if not isinstance(getattr(self, name), RuleChoice):
                raise HypothesisRegistryError(
                    f"{name} must be a RuleChoice"
                )
        for name in (
            "domain_binding",
            "substrate_binding",
            "rank_convention",
            "gauge_law",
            "target_manifold",
            "charge_group",
            "amplitude_quantity",
            "edge_connection_rule",
        ):
            _require_text(getattr(self, name), label=name)
        for name in (
            "support_quantities",
            "identifiability_quantities",
            "allowed_observables",
            "forbidden_labels",
            "required_controls",
            "failure_reasons",
        ):
            _require_identifier_tuple(getattr(self, name), label=name)
        _require_identifier_tuple(
            self.winding_prerequisites,
            label="winding_prerequisites",
            allow_empty=True,
        )
        _require_bool(
            self.integer_output_authorized,
            label="integer_output_authorized",
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "hypothesis_id": self.hypothesis_id.value,
            "branch": self.branch.value,
            "current_claim_level": self.current_claim_level.value,
            "claim_ceiling": self.claim_ceiling.value,
            "input_tensor": _choice_to_dict(self.input_tensor),
            "observation_axis": _choice_to_dict(self.observation_axis),
            "centering_rule": _choice_to_dict(self.centering_rule),
            "residual_rule": _choice_to_dict(self.residual_rule),
            "architecture_accounting_rule": _choice_to_dict(
                self.architecture_accounting_rule
            ),
            "estimator": _choice_to_dict(self.estimator),
            "fit_role": _choice_to_dict(self.fit_role),
            "domain_binding": self.domain_binding,
            "substrate_binding": self.substrate_binding,
            "rank_convention": self.rank_convention,
            "gauge_law": self.gauge_law,
            "target_manifold": self.target_manifold,
            "charge_group": self.charge_group,
            "amplitude_quantity": self.amplitude_quantity,
            "support_quantities": list(self.support_quantities),
            "identifiability_quantities": list(
                self.identifiability_quantities
            ),
            "interpolation_rule": _choice_to_dict(self.interpolation_rule),
            "lift_rule": _choice_to_dict(self.lift_rule),
            "trivialization_rule": _choice_to_dict(
                self.trivialization_rule
            ),
            "reference_rule": _choice_to_dict(self.reference_rule),
            "edge_connection_rule": self.edge_connection_rule,
            "allowed_observables": list(self.allowed_observables),
            "forbidden_labels": list(self.forbidden_labels),
            "required_controls": list(self.required_controls),
            "winding_prerequisites": list(self.winding_prerequisites),
            "failure_reasons": list(self.failure_reasons),
            "integer_output_authorized": self.integer_output_authorized,
        }


@dataclass(frozen=True, slots=True)
class HypothesisRegistry:
    """A structurally valid registry; P0 policy is checked separately."""

    registry_id: str
    status: str
    policy_version: str
    historical_boundary: HistoricalSelectionBoundary
    real_model_claim_state: ClaimLevel
    winner_selected: bool
    primary_integer_output_authorized: bool
    subject_data_access_authorized: bool
    hypotheses: tuple[HypothesisSpec, ...]
    schema_version: str = HYPOTHESIS_REGISTRY_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != HYPOTHESIS_REGISTRY_SCHEMA_VERSION:
            raise HypothesisRegistryError(
                f"unsupported hypothesis-registry schema "
                f"{self.schema_version!r}"
            )
        _require_text(self.registry_id, label="registry_id")
        _require_text(self.status, label="status")
        _require_text(self.policy_version, label="policy_version")
        if not isinstance(
            self.historical_boundary, HistoricalSelectionBoundary
        ):
            raise HypothesisRegistryError(
                "historical_boundary must be a HistoricalSelectionBoundary"
            )
        if not isinstance(self.real_model_claim_state, ClaimLevel):
            raise HypothesisRegistryError(
                "real_model_claim_state must be a ClaimLevel"
            )
        _require_bool(self.winner_selected, label="winner_selected")
        _require_bool(
            self.primary_integer_output_authorized,
            label="primary_integer_output_authorized",
        )
        _require_bool(
            self.subject_data_access_authorized,
            label="subject_data_access_authorized",
        )
        if not isinstance(self.hypotheses, tuple) or not self.hypotheses:
            raise HypothesisRegistryError(
                "hypotheses must be a non-empty tuple"
            )
        if any(
            not isinstance(hypothesis, HypothesisSpec)
            for hypothesis in self.hypotheses
        ):
            raise HypothesisRegistryError(
                "hypotheses must contain only HypothesisSpec values"
            )
        ids = tuple(item.hypothesis_id for item in self.hypotheses)
        if len(ids) != len(set(ids)):
            raise HypothesisRegistryError(
                "hypothesis IDs must be unique"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "registry_id": self.registry_id,
            "status": self.status,
            "policy_version": self.policy_version,
            "historical_boundary": self.historical_boundary.to_dict(),
            "real_model_claim_state": self.real_model_claim_state.value,
            "winner_selected": self.winner_selected,
            "primary_integer_output_authorized": (
                self.primary_integer_output_authorized
            ),
            "subject_data_access_authorized": (
                self.subject_data_access_authorized
            ),
            "hypotheses": [
                hypothesis.to_dict() for hypothesis in self.hypotheses
            ],
        }

    @property
    def sha256(self) -> str:
        """Canonical semantic identity, independent of YAML formatting."""

        return canonical_json_sha256(self.to_dict())

    @property
    def canonical_sha256(self) -> str:
        """Alias making the identity name explicit at registry boundaries."""

        return self.sha256

    @property
    def real_model_claim_level(self) -> ClaimLevel:
        """Compatibility spelling for callers that describe a claim level."""

        return self.real_model_claim_state

    def require(self, hypothesis_id: HypothesisId | str) -> HypothesisSpec:
        wanted = (
            hypothesis_id
            if isinstance(hypothesis_id, HypothesisId)
            else HypothesisId(hypothesis_id)
        )
        for hypothesis in self.hypotheses:
            if hypothesis.hypothesis_id is wanted:
                return hypothesis
        raise KeyError(wanted.value)


_EXPECTED_IDS = tuple(HypothesisId)
_ALLOWED_SELECTION_EVIDENCE = frozenset(
    {
        "independent_synthetic_calibration_selection",
        "mathematical_coherence",
        "prespecified_nuisance_coverage",
    }
)
_FORBIDDEN_SELECTION_INPUTS = frozenset(
    {
        "prior_subject_candidate_values",
        "prior_subject_status",
        "prior_subject_support_counts",
        "retrospective_subject_analyses",
    }
)
_P0_FIT_ROLES = frozenset(
    {FitRole.INSTRUMENT_DEV.value, FitRole.CALIBRATION_SELECTION.value}
)
_P0_OBSERVATION_AXES = frozenset(
    axis.value
    for axis in EvolutionAxis
    if axis is not EvolutionAxis.SYNTHETIC_LATTICE
)
_COMMON_CHOICE_CANDIDATES: Mapping[str, frozenset[str]] = {
    "input_tensor": frozenset({"accounted_response", "raw_state"}),
    "observation_axis": _P0_OBSERVATION_AXES,
    "centering_rule": frozenset(
        {"global_centering", "local_centering", "no_centering"}
    ),
    "residual_rule": frozenset(
        {"architecture_accounted_response", "centered_state", "raw_state"}
    ),
    "architecture_accounting_rule": frozenset(
        {"explicit_component_accounting", "identity_no_subtraction"}
    ),
    "fit_role": _P0_FIT_ROLES,
}


def _policy_error(message: str) -> None:
    raise HypothesisRegistryPolicyError(message)


def _choice_candidates(
    choice: RuleChoice,
    *,
    family_id: str,
) -> frozenset[str]:
    if choice.family_id != family_id:
        _policy_error(
            f"{family_id} choice must use family_id={family_id!r}"
        )
    if choice.resolution is not ResolutionState.CALIBRATION_SELECTION:
        _policy_error(
            f"{family_id} must remain calibration_selection at P0"
        )
    return frozenset(choice.candidate_ids)


def _require_exact_policy_values(
    actual: tuple[str, ...],
    expected: frozenset[str],
    *,
    label: str,
) -> None:
    actual_set = frozenset(actual)
    if actual_set != expected:
        _policy_error(
            f"{label} differs from P0 policy: "
            f"missing={sorted(expected - actual_set)}, "
            f"extra={sorted(actual_set - expected)}"
        )


_FAMILY_POLICY: Mapping[HypothesisId, Mapping[str, object]] = {
    HypothesisId.F0_SUPPORT: {
        "branch": ScientificBranch.SUPPORT,
        "ceiling": ClaimLevel.LEVEL_1G,
        "rank": "not_applicable",
        "gauge": "basis_invariant_scalar_diagnostic",
        "domain": "vertex_neighborhood",
        "substrate": "representation_shaped_discrete_substrate",
        "target": "nonnegative_scalar_diagnostics",
        "charge": "none",
        "amplitude": "not_applicable",
        "edge_connection": "not_applicable",
        "estimator_candidates": frozenset(
            {
                "entropy_effective_rank",
                "local_covariance_eigenvalues",
                "spectral_gap",
                "top_two_concentration",
            }
        ),
        "support": frozenset(
            {"local_neighborhood_count", "local_weight_mass"}
        ),
        "identifiability": frozenset(
            {"covariance_rank_stability", "spectrum_resolution"}
        ),
        "failures": frozenset(
            {
                "insufficient_support",
                "invalid_accounting",
                "unresolved_spectrum",
            }
        ),
        "required_observables": frozenset({"support_diagnostic"}),
        "forbidden": frozenset({"defect", "phase", "winding"}),
        "required_controls": frozenset(
            {"density_control", "neighborhood_support_control"}
        ),
        "winding": frozenset(),
        "rule_resolutions": {
            "interpolation_rule": (
                ResolutionState.NOT_APPLICABLE,
                None,
                frozenset(),
            ),
            "lift_rule": (
                ResolutionState.NOT_APPLICABLE,
                None,
                frozenset(),
            ),
            "trivialization_rule": (
                ResolutionState.NOT_APPLICABLE,
                None,
                frozenset(),
            ),
            "reference_rule": (
                ResolutionState.NOT_APPLICABLE,
                None,
                frozenset(),
            ),
        },
    },
    HypothesisId.F1_PROJECTOR_CONNECTION: {
        "branch": ScientificBranch.GEOMETRY,
        "ceiling": ClaimLevel.LEVEL_2G,
        "rank": "rank_two",
        "gauge": "rank_two_projector_local_o2_frame",
        "domain": "vertex_neighborhood",
        "substrate": "representation_shaped_discrete_substrate",
        "target": "grassmannian_rank_two",
        "charge": "none",
        "amplitude": "not_applicable",
        "edge_connection": "procrustes_links_required",
        "estimator_candidates": frozenset(
            {"local_rank_two_projector", "weighted_rank_two_projector"}
        ),
        "support": frozenset(
            {"edge_support", "local_neighborhood_count"}
        ),
        "identifiability": frozenset(
            {"edge_coherence", "lambda2_lambda3_gap", "subspace_overlap"}
        ),
        "failures": frozenset(
            {
                "disconnected_support",
                "insufficient_support",
                "low_subspace_overlap",
                "unresolved_lambda2_lambda3_gap",
            }
        ),
        "required_observables": frozenset(
            {
                "continuous_connection",
                "continuous_holonomy",
                "principal_angle_coherence",
                "projector_field",
            }
        ),
        "forbidden": frozenset(
            {"defect", "integer_charge_from_matrix_holonomy"}
        ),
        "required_controls": frozenset(
            {
                "ambient_basis_control",
                "edge_coherence_control",
                "rank_identifiability_control",
            }
        ),
        "winding": frozenset(),
        "rule_resolutions": {
            "interpolation_rule": (
                ResolutionState.NOT_APPLICABLE,
                None,
                frozenset(),
            ),
            "lift_rule": (
                ResolutionState.NOT_APPLICABLE,
                None,
                frozenset(),
            ),
            "trivialization_rule": (
                ResolutionState.NOT_APPLICABLE,
                None,
                frozenset(),
            ),
            "reference_rule": (
                ResolutionState.NOT_APPLICABLE,
                None,
                frozenset(),
            ),
        },
    },
    HypothesisId.F2_LOCAL_COVARIANT_SECTION: {
        "branch": ScientificBranch.DEFECT,
        "ceiling": ClaimLevel.LEVEL_2T,
        "rank": "rank_two",
        "gauge": "local_o2_covariant_two_channel_section",
        "domain": "vertexwise_local_coordinates",
        "substrate": "representation_shaped_discrete_substrate",
        "target": "gauge_covariant_two_channel_section",
        "charge": "conditional_integer_z",
        "amplitude": "section_norm",
        "edge_connection": "required_for_vertex_local_coordinates",
        "estimator_candidates": frozenset(
            {"cross_fitted_local_frame", "weighted_local_frame"}
        ),
        "support": frozenset({"edge_support", "loop_support"}),
        "identifiability": frozenset(
            {"frame_overlap", "orientation", "spectral_gap"}
        ),
        "failures": frozenset(
            {
                "branch_alias",
                "connection_gate_failed",
                "loop_section_zero",
                "non_orientable_bundle",
                "sampling_gate_failed",
            }
        ),
        "required_observables": frozenset(
            {
                "conditional_sampled_winding",
                "continuous_connection",
                "gauge_covariant_section",
                "section_amplitude",
            }
        ),
        "forbidden": frozenset(
            {
                "integer_without_eligibility_gates",
                "matrix_holonomy_as_integer_charge",
            }
        ),
        "required_controls": frozenset(
            {
                "branch_control",
                "gauge_metamorph_control",
                "sampling_control",
            }
        ),
        "winding": frozenset(
            {
                "branch_gate_pass",
                "connection_gate_pass",
                "global_trivialization_reference_or_proven_connection_corrected_lift",
                "loop_section_nonzero",
                "orientable_bundle",
                "sampling_gate_pass",
            }
        ),
        "rule_resolutions": {
            "interpolation_rule": (
                ResolutionState.CALIBRATION_SELECTION,
                None,
                frozenset(
                    {
                        "connection_transport_interpolation",
                        "piecewise_geodesic_interpolation",
                    }
                ),
            ),
            "lift_rule": (
                ResolutionState.CALIBRATION_SELECTION,
                None,
                frozenset(
                    {"connection_corrected_lift", "global_trivialization_lift"}
                ),
            ),
            "trivialization_rule": (
                ResolutionState.CALIBRATION_SELECTION,
                None,
                frozenset(
                    {
                        "frozen_global_trivialization",
                        "local_frame_with_connection",
                    }
                ),
            ),
            "reference_rule": (
                ResolutionState.CALIBRATION_SELECTION,
                None,
                frozenset(
                    {"connection_defined_reference", "frozen_global_reference"}
                ),
            ),
        },
    },
    HypothesisId.F3_GLOBAL_PLANE_SECTION: {
        "branch": ScientificBranch.DEFECT,
        "ceiling": ClaimLevel.LEVEL_1D,
        "rank": "oriented_two_channel_global_plane",
        "gauge": "projection_dependent_global_plane_coordinates",
        "domain": "fit_split_global_coordinates",
        "substrate": "representation_shaped_discrete_substrate",
        "target": "oriented_global_plane_section",
        "charge": "projection_dependent_candidate",
        "amplitude": "projected_section_norm",
        "edge_connection": "global_coordinates_no_local_edge_connection",
        "estimator_candidates": frozenset(
            {"fit_split_global_plane", "predeclared_fixed_plane"}
        ),
        "support": frozenset({"fit_split_support", "loop_support"}),
        "identifiability": frozenset(
            {"held_out_projection_stability", "plane_orientation_stability"}
        ),
        "failures": frozenset(
            {
                "fit_leakage_detected",
                "held_out_projection_failed",
                "loop_section_zero",
                "projection_instability",
                "sampling_gate_failed",
            }
        ),
        "required_observables": frozenset(
            {
                "exploratory_sampled_winding_after_bound_field_observation",
                "projected_section",
                "section_amplitude",
            }
        ),
        "forbidden": frozenset(
            {"basis_invariant_charge", "level_2t_without_new_contract"}
        ),
        "required_controls": frozenset(
            {
                "ambient_basis_control",
                "fit_leakage_control",
                "held_out_projection_control",
                "random_plane_ensemble_control",
                "reflection_control",
            }
        ),
        "winding": frozenset(
            {
                "bound_replayed_field_observation",
                "loop_section_nonzero",
                "sampling_gate_pass",
            }
        ),
        "rule_resolutions": {
            "interpolation_rule": (
                ResolutionState.CALIBRATION_SELECTION,
                None,
                frozenset(
                    {"piecewise_linear_projection", "projection_geodesic"}
                ),
            ),
            "lift_rule": (
                ResolutionState.FIXED_BY_HYPOTHESIS,
                "global_plane_direct_lift",
                frozenset(),
            ),
            "trivialization_rule": (
                ResolutionState.FIXED_BY_HYPOTHESIS,
                "global_or_fixed_plane_trivialization",
                frozenset(),
            ),
            "reference_rule": (
                ResolutionState.FIXED_BY_HYPOTHESIS,
                "fit_split_orientation_reference",
                frozenset(),
            ),
        },
    },
    HypothesisId.F4_SPIN_TWO_ANISOTROPY: {
        "branch": ScientificBranch.DEFECT,
        "ceiling": ClaimLevel.LEVEL_2T,
        "rank": "in_plane_traceless_symmetric_tensor",
        "gauge": "spin_two_doubled_angle",
        "domain": "in_plane_symmetric_tensor",
        "substrate": "representation_shaped_discrete_substrate",
        "target": "director_like_complex_section",
        "charge": "director_charge_convention",
        "amplitude": "anisotropy_amplitude",
        "edge_connection": "spin_two_connection_required",
        "estimator_candidates": frozenset(
            {"local_traceless_tensor", "weighted_traceless_tensor"}
        ),
        "support": frozenset(
            {"in_plane_tensor_support", "loop_support"}
        ),
        "identifiability": frozenset(
            {"in_plane_anisotropy_gap", "reflection_behavior"}
        ),
        "failures": frozenset(
            {
                "anisotropy_zero_on_loop",
                "director_reference_unresolved",
                "reflection_convention_failed",
                "sampling_gate_failed",
            }
        ),
        "required_observables": frozenset(
            {
                "anisotropy_amplitude",
                "conditional_director_winding",
                "doubled_angle_direction",
            }
        ),
        "forbidden": frozenset(
            {
                "ordinary_vector_charge_convention",
                "undoubled_angle_direction",
            }
        ),
        "required_controls": frozenset(
            {
                "conjugation_control",
                "reflection_control",
                "spin_two_gauge_control",
            }
        ),
        "winding": frozenset(
            {
                "director_charge_convention_frozen",
                "loop_anisotropy_nonzero",
                "sampling_gate_pass",
            }
        ),
        "rule_resolutions": {
            "interpolation_rule": (
                ResolutionState.CALIBRATION_SELECTION,
                None,
                frozenset({"doubled_angle_geodesic", "piecewise_director"}),
            ),
            "lift_rule": (
                ResolutionState.FIXED_BY_HYPOTHESIS,
                "spin_two_doubled_angle_lift",
                frozenset(),
            ),
            "trivialization_rule": (
                ResolutionState.CALIBRATION_SELECTION,
                None,
                frozenset(
                    {
                        "director_bundle_trivialization",
                        "spin_two_connection_trivialization",
                    }
                ),
            ),
            "reference_rule": (
                ResolutionState.CALIBRATION_SELECTION,
                None,
                frozenset(
                    {
                        "doubled_angle_reference",
                        "reflection_accounted_reference",
                    }
                ),
            ),
        },
    },
}


def validate_p0_registry(registry: HypothesisRegistry) -> HypothesisRegistry:
    """Enforce the exact outcome-excluded policy for the initial F0--F4 set."""

    if registry.policy_version != P0_REGISTRY_POLICY_VERSION:
        _policy_error(
            f"unsupported P0 registry policy {registry.policy_version!r}"
        )
    if registry.status != "preparation":
        _policy_error("P0 registry status must be 'preparation'")
    boundary = registry.historical_boundary
    if boundary.historical_snapshot_id != P0_HISTORICAL_SNAPSHOT_ID:
        _policy_error("P0 registry binds the wrong historical snapshot")
    if boundary.historical_cutoff_commit != P0_HISTORICAL_CUTOFF_COMMIT:
        _policy_error("P0 registry binds the wrong historical cutoff commit")
    if (
        boundary.historical_outcome_integration_commit
        != P0_HISTORICAL_OUTCOME_INTEGRATION_COMMIT
    ):
        _policy_error(
            "P0 registry binds the wrong historical outcome integration commit"
        )
    if (
        boundary.historical_outcome_record_path
        != P0_HISTORICAL_OUTCOME_RECORD_PATH
    ):
        _policy_error("P0 registry binds the wrong historical outcome record")
    if (
        boundary.historical_outcome_record_source_sha256
        != P0_HISTORICAL_OUTCOME_RECORD_SOURCE_SHA256
    ):
        _policy_error(
            "P0 registry binds the wrong historical outcome record digest"
        )
    if (
        boundary.historical_outcome_artifact_source_sha256
        != P0_HISTORICAL_OUTCOME_ARTIFACT_SOURCE_SHA256
    ):
        _policy_error(
            "P0 registry binds the wrong historical outcome artifact digest"
        )
    if not boundary.registry_postdates_prior_outcome:
        _policy_error("P0 registry must declare post-outcome chronology")
    if boundary.prior_outcome_allowed_for_selection:
        _policy_error("prior subject outcome must not select the P0 instrument")
    if (
        frozenset(boundary.allowed_selection_evidence)
        != _ALLOWED_SELECTION_EVIDENCE
    ):
        _policy_error("allowed selection evidence differs from P0 policy")
    if (
        frozenset(boundary.forbidden_selection_inputs)
        != _FORBIDDEN_SELECTION_INPUTS
    ):
        _policy_error("forbidden selection inputs differ from P0 policy")
    if registry.real_model_claim_state is not ClaimLevel.LEVEL_0:
        _policy_error("real-model claim state must remain level_0 at P0")
    if registry.winner_selected:
        _policy_error("P0 must not select a winning hypothesis")
    if registry.primary_integer_output_authorized:
        _policy_error("P0 must not authorize a primary integer output")
    if registry.subject_data_access_authorized:
        _policy_error("P0 must not authorize subject-data access")

    ids = tuple(item.hypothesis_id for item in registry.hypotheses)
    if ids != _EXPECTED_IDS:
        _policy_error(
            "P0 registry hypotheses must be exactly F0--F4 in canonical order"
        )
    for hypothesis in registry.hypotheses:
        policy = _FAMILY_POLICY[hypothesis.hypothesis_id]
        prefix = hypothesis.hypothesis_id.value
        if hypothesis.branch is not policy["branch"]:
            _policy_error(f"{prefix} has the wrong scientific branch")
        if hypothesis.current_claim_level is not ClaimLevel.LEVEL_0:
            _policy_error(f"{prefix} must remain at level_0")
        if hypothesis.claim_ceiling is not policy["ceiling"]:
            _policy_error(f"{prefix} has the wrong claim ceiling")
        if hypothesis.integer_output_authorized:
            _policy_error(f"{prefix} must not authorize an integer at P0")
        if hypothesis.rank_convention != policy["rank"]:
            _policy_error(f"{prefix} has the wrong fixed rank convention")
        if hypothesis.gauge_law != policy["gauge"]:
            _policy_error(f"{prefix} has the wrong gauge law")
        if hypothesis.charge_group != policy["charge"]:
            _policy_error(f"{prefix} has the wrong charge convention")
        for field_name, policy_name in (
            ("domain_binding", "domain"),
            ("substrate_binding", "substrate"),
            ("target_manifold", "target"),
            ("amplitude_quantity", "amplitude"),
            ("edge_connection_rule", "edge_connection"),
        ):
            if getattr(hypothesis, field_name) != policy[policy_name]:
                _policy_error(f"{prefix} has the wrong {field_name}")

        for field_name, expected_candidates in (
            (
                "input_tensor",
                _COMMON_CHOICE_CANDIDATES["input_tensor"],
            ),
            (
                "observation_axis",
                _COMMON_CHOICE_CANDIDATES["observation_axis"],
            ),
            (
                "centering_rule",
                _COMMON_CHOICE_CANDIDATES["centering_rule"],
            ),
            (
                "residual_rule",
                _COMMON_CHOICE_CANDIDATES["residual_rule"],
            ),
            (
                "architecture_accounting_rule",
                _COMMON_CHOICE_CANDIDATES[
                    "architecture_accounting_rule"
                ],
            ),
            ("fit_role", _COMMON_CHOICE_CANDIDATES["fit_role"]),
        ):
            if (
                _choice_candidates(
                    getattr(hypothesis, field_name),
                    family_id=field_name,
                )
                != expected_candidates
            ):
                _policy_error(
                    f"{prefix}.{field_name} candidates differ from P0 policy"
                )
        if (
            _choice_candidates(hypothesis.estimator, family_id="estimator")
            != policy["estimator_candidates"]
        ):
            _policy_error(
                f"{prefix}.estimator candidates differ from P0 policy"
            )

        for field_name, policy_name in (
            ("support_quantities", "support"),
            ("identifiability_quantities", "identifiability"),
            ("allowed_observables", "required_observables"),
            ("forbidden_labels", "forbidden"),
            ("required_controls", "required_controls"),
            ("failure_reasons", "failures"),
        ):
            expected_values = policy[policy_name]
            assert isinstance(expected_values, frozenset)
            _require_exact_policy_values(
                getattr(hypothesis, field_name),
                expected_values,
                label=f"{prefix}.{field_name}",
            )
        if frozenset(hypothesis.winding_prerequisites) != policy["winding"]:
            _policy_error(f"{prefix} has the wrong winding prerequisites")
        expected_resolutions = policy["rule_resolutions"]
        assert isinstance(expected_resolutions, Mapping)
        for field_name, expected_rule in expected_resolutions.items():
            assert isinstance(expected_rule, tuple)
            expected_resolution, expected_selected, expected_candidates = (
                expected_rule
            )
            choice = getattr(hypothesis, field_name)
            if choice.family_id != field_name:
                _policy_error(
                    f"{prefix}.{field_name} has the wrong family_id"
                )
            if choice.resolution is not expected_resolution:
                _policy_error(
                    f"{prefix}.{field_name} has the wrong P0 resolution"
                )
            if choice.selected_id != expected_selected:
                _policy_error(
                    f"{prefix}.{field_name} has the wrong fixed selection"
                )
            if frozenset(choice.candidate_ids) != expected_candidates:
                _policy_error(
                    f"{prefix}.{field_name} has the wrong candidate set"
                )

    return registry


validate_p0_hypothesis_registry = validate_p0_registry
