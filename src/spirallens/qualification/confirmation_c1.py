"""Canonical C1 seed-free source-set candidate for D7 confirmation.

C1 is one atomic canonical bundle.  It embeds the complete seed-free execution
design, the historical unreviewed rebinding proposal plus a successor-rebinding
review contract, a declared static-bounded construction-diversity review, a
D7-specific implementation registry, a seed-slot aggregation application, and
a commit-free inventory of every project Python source plus ``pyproject.toml``.

The artifact deliberately contains no Git commit.  A commit cannot name bytes
that contain its own identity without self-reference.  Publication here means
only an immutable filesystem candidate.  After this source and candidate have
been reviewed and merged, a separate C2 change must bind the post-merge C1
commit and historical blobs in a choice-free receipt.

No API in this module accepts a confirmation seed, gate value, result, family
admission, launch intent, or execution authorization.  C1 is source-only
Level-0 evidence and leaves D7/D8 ``not_run``.
"""

from __future__ import annotations

import ast
import os
import stat
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import ClassVar

from spirallens.core.canonical import (
    CanonicalJsonError,
    canonical_json_bytes,
    canonical_json_sha256,
    parse_canonical_json,
    sha256_bytes,
)
from spirallens.synthetic.cartesian_fourier_estimator import (
    CARTESIAN_FOURIER_FIELD_ESTIMATOR_ID,
)
from spirallens.synthetic.spectral_moment_confirmation import (
    SPECTRAL_MOMENT_AMBIENT_DIMENSION,
    SPECTRAL_MOMENT_CASE_REGISTRY,
    SPECTRAL_MOMENT_CONSTRUCTION_FAMILY_ID,
    SPECTRAL_MOMENT_GENERATOR_FAMILY_ID,
    SPECTRAL_MOMENT_GRID_SIDE,
    SPECTRAL_MOMENT_IMPLEMENTATION_ID,
    SPECTRAL_MOMENT_IMPLEMENTATION_VERSION,
    SPECTRAL_MOMENT_REQUIRED_CASE_SEMANTICS,
    SPECTRAL_MOMENT_SAMPLES_PER_SPLIT,
    SPECTRAL_MOMENT_SOURCE_PATH,
    SPECTRAL_MOMENT_STATE_NORMALIZATION_ID,
    SPECTRAL_MOMENT_STATE_NORMALIZATION_SCALE,
    SPECTRAL_MOMENT_STRESS_TRANSLATION_ID,
    SpectralMomentConfirmationGenerator,
    spectral_moment_state_geometry_conformance,
)

from .advancement import LoadedScopeLimitedD6Decision
from .common import QualificationContractError, require_sha256
from .confirmation_execution_design import (
    D7_CONFIRMATION_CORE_CELL_COUNT,
    D7_CONFIRMATION_EVENT_LANE_COUNT,
    D7_CONFIRMATION_EXECUTION_DRAFT_SCHEMA_VERSION,
    D7_CONFIRMATION_INVENTORY_SCHEMA_VERSION,
    D7_CONFIRMATION_LOOP_CELL_COUNT,
    D7_CONFIRMATION_PRIMARY_UNIT_COUNT,
    D7_CONFIRMATION_SEED_SLOT_IDS,
    D7_CONFIRMATION_STRESS_TRANSLATION_SCHEMA_VERSION,
    D7_PARENT_MANIFEST_COMPATIBILITY_SCHEMA_VERSION,
    D7_PARENT_PROTOCOL_DESIGN_BINDING_SCHEMA_VERSION,
    D7_STRUCTURAL_PROJECTION_SCHEMA_VERSION,
    D7ConfirmationExecutionDesignDraft,
    build_seed_free_d7_confirmation_execution_design,
)
from .confirmation_execution_kernel import (
    D7_CONFIRMATION_CORE_POLICY_ID,
    D7_CONFIRMATION_LOOP_POLICY_ID,
    D7_SEED_SLOT_PREDICTION_KERNEL_ID,
)
from .confirmation_protocol import D7_PARENT_D6_BINDING_SCHEMA_VERSION
from .confirmation_rebinding import (
    D6_D7_STRUCTURAL_REBINDING_AMENDMENT_SCHEMA_VERSION,
    D7_DEFERRED_SUCCESSOR_OBLIGATIONS_SCHEMA_VERSION,
    D7_EXACT_CARRY_FORWARD_SCHEMA_VERSION,
    D7_SEED_FREE_DESIGN_IDENTITY_SCHEMA_VERSION,
    D7_STRUCTURAL_MANIFEST_REBINDING_SCHEMA_VERSION,
    D6D7StructuralRebindingAmendment,
    build_d6_d7_structural_rebinding_amendment,
)
from .crossed import DOMAIN_CONSTRUCTION_ID, SUPPORT_CONSTRUCTION_ID
from .persistence import (
    LoadedQualificationProtocol,
    PersistedQualificationIdentity,
    _atomic_write_no_overwrite,
)
from .prerequisites import CORE_ESTIMATOR_ID
from .protocol import LoopRole
from .winding import LOOP_PHASE_ESTIMATOR_ID

D7_C1_SEED_FREE_SOURCE_SET_SCHEMA_VERSION = (
    "spirallens.d7-c1-seed-free-source-set.v0.1"
)
D7_C1_STABLE_DESIGN_SCHEMA_VERSION = (
    "spirallens.d7-stable-seed-free-execution-design.v0.1"
)
D7_CONSTRUCTION_DIVERSITY_REVIEW_SCHEMA_VERSION = (
    "spirallens.d7-construction-diversity-review.v0.1"
)
D7_CONFIRMATION_IMPLEMENTATION_REGISTRY_SCHEMA_VERSION = (
    "spirallens.d7-confirmation-implementation-registry.v0.1"
)
D7_CONFIRMATION_EVALUATION_DESIGN_SCHEMA_VERSION = (
    "spirallens.d7-confirmation-evaluation-design.v0.1"
)
D7_LOCKED_CONFIRMATION_AGGREGATION_SCHEMA_VERSION = (
    "spirallens.d7-locked-confirmation-aggregation.v0.1"
)
D7_CONFIRMATION_AGGREGATION_APPLICATION_SCHEMA_VERSION = (
    "spirallens.d7-confirmation-aggregation-application.v0.1"
)
D7_SUCCESSOR_REBINDING_REVIEW_CONTRACT_SCHEMA_VERSION = (
    "spirallens.d7-successor-rebinding-review-contract.v0.1"
)
D7_C1_SOURCE_SET_MANIFEST_SCHEMA_VERSION = (
    "spirallens.d7-c1-source-set-manifest.v0.1"
)

D7_C1_BUNDLE_REPOSITORY_PATH = (
    "experiments/qualification/d7_spectral_moment_confirmation_v0_1/"
    "c1-seed-free-source-set.json"
)
D7_C2_RECEIPT_REPOSITORY_PATH = (
    "experiments/qualification/d7_spectral_moment_confirmation_v0_1/"
    "c2-source-closure-receipt.json"
)
MAX_D7_C1_SEED_FREE_SOURCE_SET_BYTES = 8 * 1024 * 1024
MAX_D7_C1_SOURCE_FILE_COUNT = 8192
MAX_D7_C1_SOURCE_MEMBER_BYTES = 8 * 1024 * 1024
MAX_D7_C1_SOURCE_SET_TOTAL_BYTES = 64 * 1024 * 1024

_CANONICAL_D6_DECISION_ID = "cartesian-surrogate-d6-decision-v0-1"
_CANONICAL_D6_DECISION_SHA256 = (
    "c1c3fbbb9a06e8df120755dcf159e015636d96993bd6ec3a6792312618587a07"
)
_CANONICAL_D6_ADMISSION_SPEC_ID = (
    "cartesian-surrogate-independent-family-admission-v0-1"
)
_CANONICAL_D6_ADMISSION_SPEC_SHA256 = (
    "2e4aa2a272a38ed68b61f612d8a3a261cc6376f3d9a8097f5dce701a2c3f5aa4"
)
_CANONICAL_PARENT_PROTOCOL_ID = "d0-d5-f2-cartesian-selection-v0-1"
_CANONICAL_PARENT_PROTOCOL_SHA256 = (
    "9908bb83bb5ff5642416aa09d9e468e0a9499185cec9305e69a54143f2578bd1"
)
_CANONICAL_SOURCE_DRAFT_SHA256 = (
    "0c5b4c7c7166453051ca21656328c5a6edb6b204e056c412bafd1edc30b86e61"
)
_CANONICAL_HISTORICAL_REBINDING_PROPOSAL_SHA256 = (
    "aa585820371ea3d7f616bccf5bbaebab8e22ad02405b0fd7bbc3233ed7ec834f"
)
_CANONICAL_SELECTION_SOURCE_SHA256 = (
    "25eafb1ccf4c3142e4e05bb3e5d3c7e28835816dc2432a4522510c872ba9e325"
)
_CANONICAL_PARENT_ENGINE_COMMIT = "10c0bbaef3c11eed57662281864e865f6934ef2b"

_BUNDLE_FACTORY_TOKEN = object()
_COMPONENT_SCHEMAS = {
    "aggregation_application": (
        D7_CONFIRMATION_AGGREGATION_APPLICATION_SCHEMA_VERSION
    ),
    "construction_diversity_review": (
        D7_CONSTRUCTION_DIVERSITY_REVIEW_SCHEMA_VERSION
    ),
    "implementation_registry": (
        D7_CONFIRMATION_IMPLEMENTATION_REGISTRY_SCHEMA_VERSION
    ),
    "successor_rebinding_review_contract": (
        D7_SUCCESSOR_REBINDING_REVIEW_CONTRACT_SCHEMA_VERSION
    ),
    "seed_free_execution_design": D7_C1_STABLE_DESIGN_SCHEMA_VERSION,
    "source_set_manifest": D7_C1_SOURCE_SET_MANIFEST_SCHEMA_VERSION,
}

_AUTHORITY = {
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

_EMBEDDED_DRAFT_AUTHORITY = {
    key: False
    for key in (
        "confirmation_family_admitted",
        "confirmation_values_accessed",
        "d6_admission_spec_satisfied",
        "d7_execution_authorized",
        "d7_result_produced",
        "d8_execution_authorized",
        "integer_output_authorized",
        "localized_core_loop_join_established",
        "model_access_authorized",
        "p0_winner_selected",
        "pythia_access_authorized",
        "representation_instrument_advanced",
        "semantic_authority",
        "subject_access_authorized",
        "synthetic_qualified",
        "topology_claim_authorized",
    )
}

_SOURCE_ENUMERATION_RULE = {
    "python_root": "src/spirallens",
    "python_glob": "**/*.py",
    "additional_paths": ["pyproject.toml"],
    "excluded_paths": [],
    "enumeration_applied_to": "working-tree-candidate",
    "future_c2_git_tree_reenumeration_required": True,
}

_CONSTRUCTION_MECHANISM_COMPARISON = {
    "selection_state_embedding": "warped-cartesian-coordinate-lattice",
    "confirmation_state_embedding": (
        "normalized-separable-trigonometric-state-embedding"
    ),
    "selection_first_moment": (
        "radial-tanh-amplitude-with-cartesian-angular-orientation"
    ),
    "confirmation_first_moment": (
        "separable-sine-moment-with-spectral-null-controls"
    ),
    "selection_second_moment": "cartesian-fourier-domain-local-covariance",
    "confirmation_second_moment": "fixed-separable-spectral-second-moment",
    "state_embedding_distinct": True,
    "first_moment_construction_distinct": True,
    "second_moment_construction_distinct": True,
    "construction_family_distinct": True,
    "implementation_distinct": True,
    "source_distinct": True,
    "seed_or_label_only_difference": False,
    "selection_implementation_id_comparison_available": False,
}

_CONSTRUCTION_SHARED_INTERFACE = {
    "estimator_input_schema_shared": True,
    "field_estimator_shared": True,
    "graph_axes_shared": True,
    "thresholds_shared": True,
    "blind_core_kernel_shared": True,
    "blind_loop_kernel_shared": True,
    "downstream_path_shared_for_matched_confirmation": True,
}

_REGISTRY_OPERATIONS = {
    "seed_slot_prediction_kernel_id": D7_SEED_SLOT_PREDICTION_KERNEL_ID,
    "crossed_graph_execution_id": (
        "three-a-by-three-b-primary-and-offcore-crossed-execution-v0-1"
    ),
    "core_policy_id": D7_CONFIRMATION_CORE_POLICY_ID,
    "loop_policy_id": D7_CONFIRMATION_LOOP_POLICY_ID,
    "core_and_loop_separate": True,
    "core_and_loop_share_graph_input": True,
    "core_and_loop_share_a_bound_field_estimate": True,
    "oracle_truth_record_is_not_kernel_input": True,
}

_REPEATED_MEASURE_SEMANTICS = {
    "seed_slot_independence_proved": False,
    "graph_cells_are_repeated_measures": True,
    "three_a_repeats_per_primary": True,
    "three_a_by_three_b_by_two_roles": True,
    "loop_roles": [
        LoopRole.OFFCORE_CONTROL.value,
        LoopRole.PRIMARY_BOUNDARY.value,
    ],
    "inferential_sample_size_claimed": False,
}

_AGGREGATION_APPLICATION_POLICY = {
    "worst_case_required_strata": True,
    "full_coverage_required": True,
    "zero_abstention_required": True,
    "all_expected_primary_units_must_pass": True,
    "prerequisite_failures_mandatory_and_not_excluded": True,
    "policy_override_allowed": False,
    "post_selection_exclusion_allowed": False,
}

_COVERAGE_POLICY = {
    "aggregation": "worst_case_required_strata",
    "all_expected_primary_units_must_pass": True,
    "evaluation_unit": "phantom_instance",
    "graph_cells_are_repeated_measures": True,
    "insufficient_counts_as_success": False,
    "maximum_abstention_fraction": 0.0,
    "minimum_coverage": 1.0,
    "minimum_recall": 1.0,
    "minimum_specificity": 1.0,
    "score_denominator": "expected_nonprerequisite_primary_units",
}

_GRAPH_AXES = {
    "field_estimation": [
        {
            "graph_id": "a-mutual",
            "family": "mutual-knn",
            "purpose": "field-estimation",
            "parameters": {"neighbor_count": 4},
        },
        {
            "graph_id": "a-radius",
            "family": "fixed-radius",
            "purpose": "field-estimation",
            "parameters": {"radius": 0.48},
        },
        {
            "graph_id": "a-shared",
            "family": "shared-neighbor",
            "purpose": "field-estimation",
            "parameters": {
                "neighbor_count": 4,
                "minimum_shared_neighbors": 2,
            },
        },
    ],
    "cycle_construction": [
        {
            "graph_id": "b-mutual",
            "family": "mutual-knn",
            "purpose": "cycle-construction",
            "parameters": {"neighbor_count": 4},
        },
        {
            "graph_id": "b-radius",
            "family": "fixed-radius",
            "purpose": "cycle-construction",
            "parameters": {"radius": 0.48},
        },
        {
            "graph_id": "b-shared",
            "family": "shared-neighbor",
            "purpose": "cycle-construction",
            "parameters": {
                "neighbor_count": 4,
                "minimum_shared_neighbors": 1,
            },
        },
    ],
}

_DOMAIN = {
    "domain_id": "cartesian-grid-v0-1",
    "domain_construction_sha256": (
        "378fc615e5beeb016fa512fb56275ad26ee9ef6d06ddc4c287cbcf7c318f0d3a"
    ),
    "support_id": "rectangular-face-support-v0-1",
    "support_construction_sha256": (
        "2f31fec788dcba68889e1683048e6b5a057722526d6ce3a66ed5a3998c8f3533"
    ),
    "boundary_class_id": "same-induced-boundary-v0-1",
    "refinement_rule_id": "forward-span-four-v0-1",
    "max_domain_edges_per_graph_edge": 4,
}

_THRESHOLDS = {
    "branch_margin_rad": 0.05,
    "coherence_floor": 0.3,
    "core_amplitude_ceiling": 0.05,
    "core_candidate_difference_tolerance_rows": 0,
    "d1_cartesian_direction_cosine_floor": 0.99,
    "d1_numeric_tolerance": 1e-10,
    "d1_representation_phase_coherence_floor": 0.99,
    "graph_total_tolerance_cycles": 1e-08,
    "identifiability_floor": 0.2,
    "loop_nonzero_floor_cycles": 0.5,
    "loop_oracle_tolerance_cycles": 1e-08,
    "max_localized_core_fraction": 0.05,
    "minimum_core_contrast_ratio": 2.0,
    "minimum_field_output_effect_size": 1e-06,
    "minimum_representative_content_variants": 2,
    "minimum_support_count": 2,
}

_CONFIRMATION_EVALUATION_DESIGN = {
    "schema_version": D7_CONFIRMATION_EVALUATION_DESIGN_SCHEMA_VERSION,
    "declared_seed_block_count": 2,
    "matched_control_count": 4,
    "paired_stress_variant_count_per_seed_control": 8,
    "execution_variant_count": 64,
    "loop_execution_variant_count": 64,
    "d2_unique_scientific_input_unit_count": 32,
    "paired_repeated_measure_block_unit": "confirmation-seed-slot-block",
    "seed_block_independence_proved": False,
    "stress_variants_are_paired_repeated_measures": True,
    "boundary_variants_are_d2_repeated_measures": True,
    "controls_are_matched": True,
    "execution_variants_are_independent_replicates": False,
    "inferential_sample_size_claimed": False,
}

_SUCCESSOR_FULFILLMENT_RULE = {
    "graph_axes_byte_exact": True,
    "thresholds_byte_exact": True,
    "cells_and_stress_require_distinct_successor_identities": True,
    "cells_and_stress_require_exact_structural_projection": True,
    "aggregation_requires_distinct_successor_identity": True,
    "aggregation_only_identity_delta": (
        "selection-seed-block-to-confirmation-seed-slot-block"
    ),
    "implementation_registry_requires_distinct_construction": True,
    "surrogate_estimator_and_trivialization_byte_exact": True,
    "case_semantics_exact": True,
    "selection_evidence_disjointness_required": True,
    "overrides_or_postselection_exclusions_allowed": False,
}

_C1_DEFERRED = {
    "post_merge_c1_commit_binding": True,
    "choice_free_c2_receipt": True,
    "family_admission": True,
    "official_seed_inventory": True,
    "full_design_freeze": True,
    "launch_and_attempt_lifecycle": True,
    "replay_target": True,
    "result_and_failure_schemas": True,
    "terminal_writer": True,
    "isolated_replay": True,
}


def _c1_chronology_document() -> dict[str, object]:
    return {
        "artifact_knowledge": {
            "candidate_atomically_publishable": True,
            "c1_commit_identity_embedded": False,
            "repository_review_attestation_embedded": False,
            "c2_receipt_embedded": False,
            "source_closure_attestation_embedded": False,
            "official_seed_inventory_embedded": False,
            "confirmation_values_embedded": False,
        },
        "ordering_requirements": {
            "repository_review_required_before_c1_merge": True,
            "c2_must_bind_post_merge_c1": True,
            "official_seed_supplier_must_follow_c2": True,
            "launch_must_follow_seed_free_design_freeze": True,
        },
    }


def _expected_stress_translation_document() -> dict[str, object]:
    conformance = []
    for level, value in (("nominal", 0.0), ("stressed", 0.1)):
        receipt = spectral_moment_state_geometry_conformance(value)
        maximum = float(receipt["maximum_axis_adjacent_distance"])
        conformance.append(
            {
                **receipt,
                "stress_level": level,
                "locked_radius_graph_value": 0.48,
                "adjacent_distance_margin_below_locked_radius": 0.48 - maximum,
                "axis_adjacent_distance_below_locked_radius": maximum < 0.48,
            }
        )
    return {
        "schema_version": D7_CONFIRMATION_STRESS_TRANSLATION_SCHEMA_VERSION,
        "translation_id": SPECTRAL_MOMENT_STRESS_TRANSLATION_ID,
        "stress_axes": [
            {"axis_id": "boundary", "levels": ["central", "wide"]},
            {
                "axis_id": "state-geometry-warp",
                "levels": ["nominal", "stressed"],
            },
            {
                "axis_id": "structured-observation-perturbation",
                "levels": ["nominal", "stressed"],
            },
        ],
        "state_geometry_warp": {
            "levels": [
                {"level": "nominal", "value": 0.0},
                {"level": "stressed", "value": 0.1},
            ],
            "formula": "q-plus-w-sin-pi-q-over-pi",
            "changes_states": True,
            "changes_site_coordinates": False,
            "changes_oracle_field": False,
        },
        "structured_observation_perturbation": {
            "levels": [
                {"level": "nominal", "value": 0.0},
                {"level": "stressed", "value": 0.01},
            ],
            "formula": "a-cos-sqrt-two-alpha-plus-row-seed-phase-37-1009",
            "reuses_d6_nuisance_operator": True,
            "changes_fit_and_evaluation_values": True,
            "changes_states": False,
            "changes_oracle_field": False,
            "prerequisite_requested_assignment_retained": True,
            "prerequisite_effective_scale_zero": True,
        },
        "boundary": {
            "primary": [
                {
                    "level": "central",
                    "x_min": 2,
                    "y_min": 2,
                    "x_max": 4,
                    "y_max": 4,
                },
                {
                    "level": "wide",
                    "x_min": 1,
                    "y_min": 1,
                    "x_max": 5,
                    "y_max": 5,
                },
            ],
            "offcore": {
                "level": "offcore",
                "x_min": 0,
                "y_min": 0,
                "x_max": 1,
                "y_max": 1,
            },
            "selects_matched_cycle_support": True,
            "changes_generator_inputs": False,
        },
        "state_normalization": {
            "normalization_id": SPECTRAL_MOMENT_STATE_NORMALIZATION_ID,
            "rule": "one-over-square-root-of-ambient-dimension",
            "ambient_dimension": SPECTRAL_MOMENT_AMBIENT_DIMENSION,
            "scale": SPECTRAL_MOMENT_STATE_NORMALIZATION_SCALE,
            "seed_free_distance_conformance": conformance,
            "development_result_tuned_threshold": False,
        },
        "grid_side": SPECTRAL_MOMENT_GRID_SIDE,
        "samples_per_split": SPECTRAL_MOMENT_SAMPLES_PER_SPLIT,
        "stress_translation_implemented": True,
        "stress_translation_frozen": False,
    }


def _exact_keys(
    value: Mapping[str, object],
    expected: set[str],
    *,
    label: str,
) -> None:
    if set(value) != expected:
        raise QualificationContractError(f"{label} fields differ")


def _require_exact_json_value(
    value: object,
    expected: object,
    *,
    label: str,
) -> None:
    """Require recursive JSON value and type identity, including bool vs int."""

    if isinstance(expected, Mapping):
        if not isinstance(value, Mapping) or set(value) != set(expected):
            raise QualificationContractError(f"{label} fields differ")
        for key, expected_item in expected.items():
            _require_exact_json_value(
                value[key],
                expected_item,
                label=f"{label}.{key}",
            )
        return
    if isinstance(expected, list):
        if not isinstance(value, list) or len(value) != len(expected):
            raise QualificationContractError(f"{label} list differs")
        for index, (item, expected_item) in enumerate(
            zip(value, expected, strict=True)
        ):
            _require_exact_json_value(
                item,
                expected_item,
                label=f"{label}[{index}]",
            )
        return
    if type(value) is not type(expected) or value != expected:
        raise QualificationContractError(f"{label} differs")


def _canonical_repository_path(value: object, *, label: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value.startswith("/")
        or "\\" in value
        or any(ord(character) < 32 or ord(character) == 127 for character in value)
    ):
        raise QualificationContractError(
            f"{label} must be a canonical relative POSIX path"
        )
    path = PurePosixPath(value)
    if (
        path.as_posix() != value
        or not path.parts
        or any(part in {"", ".", ".."} for part in path.parts)
    ):
        raise QualificationContractError(
            f"{label} must be a canonical relative POSIX path"
        )
    return value


def _mapping(value: object, *, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise QualificationContractError(f"{label} must be an object")
    return value


def _inventory_identities(
    value: object,
) -> dict[str, str]:
    inventory = _mapping(value, label="D7 C1 embedded inventory")
    _exact_keys(
        inventory,
        {
            "schema_version",
            "primary_units",
            "core_cells",
            "loop_cells",
            "expected_strata",
            "counts",
            "repeated_measures",
            "concrete_seed_inventory_present",
            "execution_inventory_frozen",
        },
        label="D7 C1 embedded inventory",
    )
    expected_counts = {
        "seed_slots": 2,
        "cases": 4,
        "stress_variants_per_seed_case": 8,
        "primary_units": D7_CONFIRMATION_PRIMARY_UNIT_COUNT,
        "core_cells": D7_CONFIRMATION_CORE_CELL_COUNT,
        "loop_cells": D7_CONFIRMATION_LOOP_CELL_COUNT,
        "event_lanes": D7_CONFIRMATION_EVENT_LANE_COUNT,
        "d2_boundary_collapsed_scientific_units": 32,
        "d2_boundary_collapsed_evaluable_units": 24,
        "d2_boundary_collapsed_prerequisite_units": 8,
        "d4_d5_scientific_execution_units": 64,
        "nonprerequisite_primary_denominator": 48,
        "prerequisite_primary_units": 16,
    }
    expected_repeated = {
        "core_graphs": True,
        "graph_pairs": True,
        "loop_roles": True,
        "stress_variants": True,
        "seed_blocks_proved_independent": False,
        "event_lanes_are_iid_samples": False,
    }
    _require_exact_json_value(
        inventory["counts"],
        expected_counts,
        label="D7 C1 inventory counts",
    )
    _require_exact_json_value(
        inventory["repeated_measures"],
        expected_repeated,
        label="D7 C1 inventory repeated measures",
    )
    primary_units = inventory["primary_units"]
    core_cells = inventory["core_cells"]
    loop_cells = inventory["loop_cells"]
    expected_strata = inventory["expected_strata"]
    if (
        inventory["schema_version"] != D7_CONFIRMATION_INVENTORY_SCHEMA_VERSION
        or inventory["counts"] != expected_counts
        or inventory["repeated_measures"] != expected_repeated
        or inventory["concrete_seed_inventory_present"] is not False
        or inventory["execution_inventory_frozen"] is not False
        or not isinstance(primary_units, list)
        or not isinstance(core_cells, list)
        or not isinstance(loop_cells, list)
        or not isinstance(expected_strata, list)
        or len(primary_units) != D7_CONFIRMATION_PRIMARY_UNIT_COUNT
        or len(core_cells) != D7_CONFIRMATION_CORE_CELL_COUNT
        or len(loop_cells) != D7_CONFIRMATION_LOOP_CELL_COUNT
        or len(expected_strata) != 6
    ):
        raise QualificationContractError(
            "D7 C1 embedded inventory state or counts differ"
        )
    case_by_semantic = {
        semantic: {
            "case_id": case_id,
            "core_disposition": core,
            "loop_disposition": loop,
        }
        for case_id, semantic, _recipe, core, loop in SPECTRAL_MOMENT_CASE_REGISTRY
    }
    primary_by_id: dict[str, Mapping[str, object]] = {}
    control_by_semantic: dict[str, str] = {}
    observed_combinations: set[tuple[str, str, str, str, str]] = set()
    for item in primary_units:
        unit = _mapping(item, label="D7 C1 primary unit")
        _exact_keys(
            unit,
            {
                "primary_unit_id",
                "seed_slot_id",
                "parent_control_id",
                "case_id",
                "case_semantics",
                "core_disposition",
                "loop_disposition",
                "stress_assignments",
            },
            label="D7 C1 primary unit",
        )
        primary_id = unit["primary_unit_id"]
        semantic = unit["case_semantics"]
        control_id = unit["parent_control_id"]
        assignments = unit["stress_assignments"]
        if (
            not isinstance(primary_id, str)
            or not isinstance(semantic, str)
            or not isinstance(control_id, str)
            or semantic not in case_by_semantic
            or unit["seed_slot_id"] not in D7_CONFIRMATION_SEED_SLOT_IDS
            or not isinstance(assignments, list)
            or len(assignments) != 3
            or primary_id in primary_by_id
        ):
            raise QualificationContractError(
                "D7 C1 primary-unit identity or axes differ"
            )
        expected_case = case_by_semantic[semantic]
        if any(unit[name] != expected_case[name] for name in expected_case):
            raise QualificationContractError(
                "D7 C1 primary-unit case semantics differ"
            )
        prior_control = control_by_semantic.setdefault(semantic, control_id)
        if prior_control != control_id:
            raise QualificationContractError(
                "D7 C1 case semantic maps to multiple parent controls"
            )
        expected_axes = (
            ("boundary", {"central", "wide"}),
            ("state-geometry-warp", {"nominal", "stressed"}),
            (
                "structured-observation-perturbation",
                {"nominal", "stressed"},
            ),
        )
        levels: list[str] = []
        for assignment, (axis_id, allowed_levels) in zip(
            assignments,
            expected_axes,
            strict=True,
        ):
            record = _mapping(
                assignment,
                label="D7 C1 primary stress assignment",
            )
            _exact_keys(
                record,
                {"axis_id", "level"},
                label="D7 C1 primary stress assignment",
            )
            if (
                record["axis_id"] != axis_id
                or record["level"] not in allowed_levels
                or not isinstance(record["level"], str)
            ):
                raise QualificationContractError(
                    "D7 C1 primary stress assignment differs"
                )
            levels.append(record["level"])
        combination = (
            str(unit["seed_slot_id"]),
            semantic,
            levels[0],
            levels[1],
            levels[2],
        )
        if combination in observed_combinations:
            raise QualificationContractError(
                "D7 C1 primary-unit structural combination is duplicated"
            )
        observed_combinations.add(combination)
        primary_by_id[primary_id] = unit
    if (
        tuple(primary_by_id) != tuple(sorted(primary_by_id))
        or len(control_by_semantic) != 4
    ):
        raise QualificationContractError(
            "D7 C1 primary units are not canonical or complete"
        )
    expected_combinations = {
        (slot, semantic, boundary, warp, perturbation)
        for slot in D7_CONFIRMATION_SEED_SLOT_IDS
        for semantic in SPECTRAL_MOMENT_REQUIRED_CASE_SEMANTICS
        for boundary in ("central", "wide")
        for warp in ("nominal", "stressed")
        for perturbation in ("nominal", "stressed")
    }
    if observed_combinations != expected_combinations:
        raise QualificationContractError(
            "D7 C1 primary-unit crossed inventory differs"
        )

    field_ids = tuple(item["graph_id"] for item in _GRAPH_AXES["field_estimation"])
    cycle_ids = tuple(
        item["graph_id"] for item in _GRAPH_AXES["cycle_construction"]
    )
    observed_core: set[tuple[str, str]] = set()
    core_ids: list[str] = []
    for item in core_cells:
        cell = _mapping(item, label="D7 C1 core cell")
        _exact_keys(
            cell,
            {
                "core_cell_id",
                "primary_unit_id",
                "field_graph_id",
                "expected_core_disposition",
            },
            label="D7 C1 core cell",
        )
        primary = primary_by_id.get(cell["primary_unit_id"])  # type: ignore[arg-type]
        pair = (str(cell["primary_unit_id"]), str(cell["field_graph_id"]))
        if (
            primary is None
            or cell["field_graph_id"] not in field_ids
            or cell["expected_core_disposition"]
            != primary["core_disposition"]
            or pair in observed_core
            or not isinstance(cell["core_cell_id"], str)
        ):
            raise QualificationContractError("D7 C1 core-cell relation differs")
        observed_core.add(pair)
        core_ids.append(cell["core_cell_id"])
    if (
        observed_core
        != {
            (primary_id, field_id)
            for primary_id in primary_by_id
            for field_id in field_ids
        }
        or core_ids != sorted(set(core_ids))
    ):
        raise QualificationContractError(
            "D7 C1 core-cell inventory is not canonical or complete"
        )

    loop_roles = (
        LoopRole.OFFCORE_CONTROL.value,
        LoopRole.PRIMARY_BOUNDARY.value,
    )
    observed_loop: set[tuple[str, str, str, str]] = set()
    loop_ids: list[str] = []
    for item in loop_cells:
        cell = _mapping(item, label="D7 C1 loop cell")
        _exact_keys(
            cell,
            {
                "loop_cell_id",
                "primary_unit_id",
                "field_graph_id",
                "cycle_graph_id",
                "loop_role",
                "expected_loop_disposition",
            },
            label="D7 C1 loop cell",
        )
        primary = primary_by_id.get(cell["primary_unit_id"])  # type: ignore[arg-type]
        relation = (
            str(cell["primary_unit_id"]),
            str(cell["field_graph_id"]),
            str(cell["cycle_graph_id"]),
            str(cell["loop_role"]),
        )
        expected_disposition = (
            primary["loop_disposition"]
            if primary is not None
            and cell["loop_role"] == LoopRole.PRIMARY_BOUNDARY.value
            else (
                "prerequisite_failure"
                if primary is not None
                and primary["loop_disposition"] == "prerequisite_failure"
                else "null"
            )
        )
        if (
            primary is None
            or cell["field_graph_id"] not in field_ids
            or cell["cycle_graph_id"] not in cycle_ids
            or cell["loop_role"] not in loop_roles
            or cell["expected_loop_disposition"] != expected_disposition
            or relation in observed_loop
            or not isinstance(cell["loop_cell_id"], str)
        ):
            raise QualificationContractError("D7 C1 loop-cell relation differs")
        observed_loop.add(relation)
        loop_ids.append(cell["loop_cell_id"])
    if (
        observed_loop
        != {
            (primary_id, field_id, cycle_id, role)
            for primary_id in primary_by_id
            for field_id in field_ids
            for cycle_id in cycle_ids
            for role in loop_roles
        }
        or loop_ids != sorted(set(loop_ids))
    ):
        raise QualificationContractError(
            "D7 C1 loop-cell inventory is not canonical or complete"
        )

    expected_strata_records = []
    for axis_id, levels in (
        ("boundary", ("central", "wide")),
        ("state-geometry-warp", ("nominal", "stressed")),
        (
            "structured-observation-perturbation",
            ("nominal", "stressed"),
        ),
    ):
        for level in levels:
            members = sorted(
                primary_id
                for primary_id, unit in primary_by_id.items()
                if any(
                    assignment["axis_id"] == axis_id
                    and assignment["level"] == level
                    for assignment in unit["stress_assignments"]  # type: ignore[union-attr]
                )
            )
            expected_strata_records.append(
                {
                    "stratum_id": f"stress.{axis_id}.{level}",
                    "evaluation_unit": "phantom_instance",
                    "required": True,
                    "primary_unit_ids": members,
                }
            )
    if expected_strata != sorted(
        expected_strata_records,
        key=lambda item: item["stratum_id"],
    ):
        raise QualificationContractError(
            "D7 C1 required stress strata differ"
        )

    cells_manifest = {
        "schema_version": "spirallens.d7-required-confirmation-cells.v0.1",
        "core_cells": core_cells,
        "loop_cells": loop_cells,
    }
    stress_manifest = {
        "schema_version": "spirallens.d7-required-confirmation-stress.v0.1",
        "stress_axes": _expected_stress_translation_document()["stress_axes"],
        "expected_strata": expected_strata,
    }
    unit_projection = {
        primary_id: {
            "seed_slot_id": unit["seed_slot_id"],
            "case_semantics": unit["case_semantics"],
            "stress_assignments": unit["stress_assignments"],
        }
        for primary_id, unit in primary_by_id.items()
    }
    projected_by_id = {
        primary_id: canonical_json_sha256(projection)
        for primary_id, projection in unit_projection.items()
    }
    structural_projection = {
        "schema_version": D7_STRUCTURAL_PROJECTION_SCHEMA_VERSION,
        "seed_slot_count": 2,
        "stress_axes": _expected_stress_translation_document()["stress_axes"],
        "primary_units": sorted(
            unit_projection.values(),
            key=canonical_json_bytes,
        ),
        "core_cells": sorted(
            [
                {
                    **unit_projection[str(cell["primary_unit_id"])],
                    "field_graph_id": cell["field_graph_id"],
                    "expected_core_disposition": (
                        cell["expected_core_disposition"]
                    ),
                }
                for cell in core_cells
            ],
            key=canonical_json_bytes,
        ),
        "loop_cells": sorted(
            [
                {
                    **unit_projection[str(cell["primary_unit_id"])],
                    "field_graph_id": cell["field_graph_id"],
                    "cycle_graph_id": cell["cycle_graph_id"],
                    "loop_role": cell["loop_role"],
                    "expected_loop_disposition": (
                        cell["expected_loop_disposition"]
                    ),
                }
                for cell in loop_cells
            ],
            key=canonical_json_bytes,
        ),
        "expected_strata": sorted(
            [
                {
                    "stratum_id": item["stratum_id"],
                    "evaluation_unit": "phantom_instance",
                    "required": True,
                    "projected_primary_units": sorted(
                        projected_by_id[str(primary_id)]
                        for primary_id in item["primary_unit_ids"]  # type: ignore[union-attr]
                    ),
                }
                for item in expected_strata
            ],
            key=canonical_json_bytes,
        ),
    }
    return {
        "inventory_sha256": canonical_json_sha256(inventory),
        "successor_cells_sha256": canonical_json_sha256(cells_manifest),
        "successor_stress_sha256": canonical_json_sha256(stress_manifest),
        "structural_projection_sha256": canonical_json_sha256(
            structural_projection
        ),
    }


def _source_manifest_entries(
    value: object,
) -> dict[str, Mapping[str, object]]:
    manifest = _mapping(value, label="D7 C1 source-set manifest")
    _require_exact_json_value(
        manifest.get("enumeration_rule"),
        _SOURCE_ENUMERATION_RULE,
        label="D7 C1 source-set enumeration",
    )
    if (
        manifest.get("manifest_id")
        != "d7-spectral-moment-c1-complete-python-source-set-v0-1"
        or manifest.get("status") != "commit-free-source-set-candidate"
        or manifest.get("bundle_repository_path")
        != D7_C1_BUNDLE_REPOSITORY_PATH
        or manifest.get("bundle_self_included") is not False
        or manifest.get("bundle_self_digest_deferred_to_c2") is not True
        or manifest.get("c2_receipt_repository_path")
        != D7_C2_RECEIPT_REPOSITORY_PATH
        or manifest.get("c2_receipt_present") is not False
        or manifest.get("git_commit_bound") is not False
        or manifest.get("source_closure_verified") is not False
        or manifest.get("python_runtime_dependency_closure_attested") is not False
        or manifest.get("native_runtime_attested") is not False
        or manifest.get("in_process_callable_identity_verified") is not False
        or manifest.get("hostile_local_mutation_resistant") is not False
    ):
        raise QualificationContractError(
            "D7 C1 source-set identity, flags, or enumeration differ"
        )
    entries = manifest.get("entries")
    if not isinstance(entries, list) or not entries:
        raise QualificationContractError("D7 C1 source entries must be nonempty")
    declared: dict[str, Mapping[str, object]] = {}
    total_bytes = 0
    role_counts = {
        "packaging_contract": 0,
        "project_python_source": 0,
    }
    for item in entries:
        entry = _mapping(item, label="D7 C1 source entry")
        _exact_keys(
            entry,
            {
                "repository_path",
                "role",
                "source_sha256",
                "byte_count",
                "git_mode",
            },
            label="D7 C1 source entry",
        )
        repository_path = _canonical_repository_path(
            entry["repository_path"],
            label="D7 C1 source entry path",
        )
        if (
            repository_path in declared
        ):
            raise QualificationContractError(
                "D7 C1 source paths must be unique safe strings"
            )
        expected_role = (
            "packaging_contract"
            if repository_path == "pyproject.toml"
            else "project_python_source"
        )
        if (
            (
                repository_path != "pyproject.toml"
                and (
                    not repository_path.startswith("src/spirallens/")
                    or not repository_path.endswith(".py")
                )
            )
            or entry["role"] != expected_role
            or type(entry["byte_count"]) is not int
            or int(entry["byte_count"]) <= 0
            or int(entry["byte_count"]) > MAX_D7_C1_SOURCE_MEMBER_BYTES
            or entry["git_mode"] not in {"100644", "100755"}
        ):
            raise QualificationContractError(
                "D7 C1 source entry path, role, size, or mode differs"
            )
        require_sha256(
            entry["source_sha256"],
            label=f"D7 C1 source {repository_path}",
        )
        declared[repository_path] = entry
        role_counts[expected_role] += 1
        total_bytes += int(entry["byte_count"])
    expected_role_counts = {
        "packaging_contract": 1,
        "project_python_source": len(declared) - 1,
    }
    if not isinstance(manifest.get("role_counts"), Mapping):
        raise QualificationContractError(
            "D7 C1 source-set role counts must be an object"
        )
    _require_exact_json_value(
        manifest["role_counts"],
        expected_role_counts,
        label="D7 C1 source-set role counts",
    )
    if (
        tuple(declared) != tuple(sorted(declared))
        or len(declared) > MAX_D7_C1_SOURCE_FILE_COUNT
        or type(manifest.get("file_count")) is not int
        or manifest.get("file_count") != len(declared)
        or role_counts != expected_role_counts
        or type(manifest.get("total_bytes")) is not int
        or manifest.get("total_bytes") != total_bytes
        or total_bytes > MAX_D7_C1_SOURCE_SET_TOTAL_BYTES
        or role_counts["packaging_contract"] != 1
    ):
        raise QualificationContractError(
            "D7 C1 source-set ordering or aggregates differ"
        )
    required_paths = {
        "pyproject.toml",
        SPECTRAL_MOMENT_SOURCE_PATH,
        "src/spirallens/qualification/confirmation_c1.py",
        "src/spirallens/qualification/confirmation_execution_kernel.py",
        "src/spirallens/qualification/confirmation_source_closure.py",
    }
    if not required_paths.issubset(declared):
        raise QualificationContractError(
            "D7 C1 source-set lacks a required C1 execution or closure source"
        )
    return declared


def _loaded_d6(value: object) -> LoadedScopeLimitedD6Decision:
    if not isinstance(value, LoadedScopeLimitedD6Decision):
        raise TypeError(
            "loaded_d6 must be an authoritative LoadedScopeLimitedD6Decision"
        )
    value.__post_init__()
    decision = value.decision
    admission = decision.confirmation_admission_spec
    if (
        value.identity.source_sha256 != _CANONICAL_D6_DECISION_SHA256
        or value.identity.canonical_sha256 != _CANONICAL_D6_DECISION_SHA256
        or decision.decision_id != _CANONICAL_D6_DECISION_ID
        or admission.admission_spec_id != _CANONICAL_D6_ADMISSION_SPEC_ID
        or admission.canonical_sha256 != _CANONICAL_D6_ADMISSION_SPEC_SHA256
    ):
        raise QualificationContractError(
            "C1 requires the one pinned D6 decision and admission identity"
        )
    return value


def _loaded_parent(value: object) -> LoadedQualificationProtocol:
    if not isinstance(value, LoadedQualificationProtocol):
        raise TypeError("parent_protocol must be a strict LoadedQualificationProtocol")
    value.__post_init__()
    if (
        value.source_sha256 != _CANONICAL_PARENT_PROTOCOL_SHA256
        or value.canonical_sha256 != _CANONICAL_PARENT_PROTOCOL_SHA256
        or value.protocol.protocol_id != _CANONICAL_PARENT_PROTOCOL_ID
    ):
        raise QualificationContractError(
            "C1 requires the one pinned parent protocol identity"
        )
    return value


def _repository_root(value: str | Path) -> Path:
    root = Path(os.path.abspath(value))
    if not root.is_dir() or root.is_symlink():
        raise QualificationContractError(
            "repository_root must be one real existing directory"
        )
    if not (root / "src" / "spirallens").is_dir():
        raise QualificationContractError(
            "repository_root lacks src/spirallens"
        )
    imported_root = Path(__file__).resolve().parents[3]
    if root.resolve() != imported_root:
        raise QualificationContractError(
            "C1 construction requires repository_root to equal the source "
            "checkout that loaded confirmation_c1"
        )
    return root


def _regular_source(root: Path, relative: str) -> tuple[bytes, str]:
    path = root / relative
    try:
        path.relative_to(root)
    except ValueError as error:
        raise QualificationContractError(
            "source-set path escapes repository_root"
        ) from error
    if path.is_symlink() or not path.is_file():
        raise QualificationContractError(
            f"source-set member must be one regular file: {relative}"
        )
    with path.open("rb") as handle:
        source = handle.read(MAX_D7_C1_SOURCE_MEMBER_BYTES + 1)
    if not source or len(source) > MAX_D7_C1_SOURCE_MEMBER_BYTES:
        raise QualificationContractError(
            f"source-set member must be nonempty and bounded: {relative}"
        )
    mode = path.stat().st_mode
    git_mode = "100755" if mode & stat.S_IXUSR else "100644"
    return source, git_mode


def _source_set_document(root: Path) -> dict[str, object]:
    source_root = root / "src" / "spirallens"
    bounded_paths = ["pyproject.toml"]
    for path in source_root.rglob("*.py"):
        bounded_paths.append(path.relative_to(root).as_posix())
        if len(bounded_paths) > MAX_D7_C1_SOURCE_FILE_COUNT:
            raise QualificationContractError(
                "C1 source-set enumeration exceeds the file-count cap"
            )
    paths = tuple(sorted(bounded_paths))
    if not paths or paths != tuple(sorted(set(paths))):
        raise QualificationContractError(
            "C1 source-set enumeration must be unique and canonical"
        )
    entries: list[dict[str, object]] = []
    total_bytes = 0
    for relative in paths:
        source, git_mode = _regular_source(root, relative)
        total_bytes += len(source)
        if total_bytes > MAX_D7_C1_SOURCE_SET_TOTAL_BYTES:
            raise QualificationContractError(
                "C1 source-set enumeration exceeds the total-byte cap"
            )
        entries.append(
            {
                "repository_path": relative,
                "role": (
                    "packaging_contract"
                    if relative == "pyproject.toml"
                    else "project_python_source"
                ),
                "source_sha256": sha256_bytes(source),
                "byte_count": len(source),
                "git_mode": git_mode,
            }
        )
    role_counts = {
        "packaging_contract": sum(
            item["role"] == "packaging_contract" for item in entries
        ),
        "project_python_source": sum(
            item["role"] == "project_python_source" for item in entries
        ),
    }
    return {
        "schema_version": D7_C1_SOURCE_SET_MANIFEST_SCHEMA_VERSION,
        "manifest_id": "d7-spectral-moment-c1-complete-python-source-set-v0-1",
        "status": "commit-free-source-set-candidate",
        "enumeration_rule": dict(_SOURCE_ENUMERATION_RULE),
        "entries": entries,
        "file_count": len(entries),
        "role_counts": role_counts,
        "total_bytes": total_bytes,
        "bundle_repository_path": D7_C1_BUNDLE_REPOSITORY_PATH,
        "bundle_self_included": False,
        "bundle_self_digest_deferred_to_c2": True,
        "c2_receipt_repository_path": D7_C2_RECEIPT_REPOSITORY_PATH,
        "c2_receipt_present": False,
        "git_commit_bound": False,
        "source_closure_verified": False,
        "python_runtime_dependency_closure_attested": False,
        "native_runtime_attested": False,
        "in_process_callable_identity_verified": False,
        "hostile_local_mutation_resistant": False,
    }


def _component(body: Mapping[str, object]) -> dict[str, object]:
    return {
        "canonical_sha256": canonical_json_sha256(body),
        "body": dict(body),
    }


def _stable_design_document(
    design: D7ConfirmationExecutionDesignDraft,
) -> dict[str, object]:
    if design.stress_translation.to_dict() != (
        _expected_stress_translation_document()
    ):
        raise QualificationContractError(
            "D7 stress translation differs from the stable C1 contract"
        )
    if (
        design.graph_axes.to_dict() != _GRAPH_AXES
        or design.domain.to_dict() != _DOMAIN
        or design.thresholds.to_dict() != _THRESHOLDS
        or design.coverage_policy.to_dict() != _COVERAGE_POLICY
    ):
        raise QualificationContractError(
            "D7 parent interface differs from the stable C1 contract"
        )
    return {
        "schema_version": D7_C1_STABLE_DESIGN_SCHEMA_VERSION,
        "design_id": "d7-spectral-moment-stable-seed-free-design-v0-1",
        "status": "seed-free-design-embedded-in-c1-candidate",
        "claim_ceiling": "level_0",
        "source_draft_schema_version": design.schema_version,
        "source_draft_id": design.draft_id,
        "source_draft_canonical_sha256": design.canonical_sha256,
        "seed_free_execution_design": design.to_dict(),
        "invariant_identities": {
            "parent_d6_sha256": design.parent_d6.d6_decision_canonical_sha256,
            "parent_protocol_sha256": design.parent.protocol_canonical_sha256,
            "graph_axes_sha256": canonical_json_sha256(design.graph_axes.to_dict()),
            "thresholds_sha256": canonical_json_sha256(design.thresholds.to_dict()),
            "stress_translation_sha256": canonical_json_sha256(
                design.stress_translation.to_dict()
            ),
            "inventory_sha256": canonical_json_sha256(design.inventory.to_dict()),
            "successor_cells_sha256": (
                design.manifest_compatibility.confirmation_cells_manifest_sha256
            ),
            "successor_stress_sha256": (
                design.manifest_compatibility.confirmation_stress_strata_sha256
            ),
            "structural_projection_sha256": (
                design.manifest_compatibility.parent_structural_projection_sha256
            ),
        },
        "counts": {
            "seed_slots": len(D7_CONFIRMATION_SEED_SLOT_IDS),
            "primary_units": D7_CONFIRMATION_PRIMARY_UNIT_COUNT,
            "core_cells": D7_CONFIRMATION_CORE_CELL_COUNT,
            "loop_cells": D7_CONFIRMATION_LOOP_CELL_COUNT,
            "event_lanes": D7_CONFIRMATION_EVENT_LANE_COUNT,
        },
        "source_draft_status_is_embedded_historical_body": True,
        "embedded_in_c1_candidate": True,
        "committed_c1_verified": False,
        "concrete_seed_inventory_present": False,
        "full_design_frozen": False,
        "execution_authorized": False,
        "result_schema_present": False,
        "terminal_writer_present": False,
        "d7_state": "not_run",
        "d8_state": "not_run",
    }


def _engine_module_sha256(
    parent: LoadedQualificationProtocol,
    module: str,
) -> str:
    matches = tuple(
        item.sha256 for item in parent.protocol.engine.modules if item.module == module
    )
    if len(matches) != 1:
        raise QualificationContractError(
            f"parent engine must bind exactly one {module} module"
        )
    return matches[0]


def _spectral_import_review(root: Path) -> dict[str, object]:
    source, _mode = _regular_source(root, SPECTRAL_MOMENT_SOURCE_PATH)
    try:
        tree = ast.parse(source, filename=SPECTRAL_MOMENT_SOURCE_PATH)
    except SyntaxError as error:
        raise QualificationContractError(
            "spectral confirmation source is not valid Python"
        ) from error
    target_module = "cartesian_fourier_domain_phantom"
    allowed_shared_count = 0
    direct_module_imports: list[str] = []
    forbidden_symbol_imports: list[str] = []
    forbidden = {
        "CartesianFourierDomainGenerator",
        "CartesianFourierDomainSpec",
        "CartesianFourierDomainPhantom",
    }
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for item in node.names:
                if item.name.rsplit(".", 1)[-1] == target_module:
                    direct_module_imports.append(f"import:{item.name}")
        elif isinstance(node, ast.ImportFrom):
            module = "." * node.level + (node.module or "")
            module_targets_cartesian = (
                (node.module or "").rsplit(".", 1)[-1] == target_module
            )
            imported_module_by_name = any(
                item.name.rsplit(".", 1)[-1] == target_module
                for item in node.names
            )
            if not module_targets_cartesian and not imported_module_by_name:
                continue
            if (
                node.level == 1
                and node.module == target_module
                and len(node.names) == 1
                and node.names[0].name == "CartesianFourierEstimatorInputs"
                and node.names[0].asname is None
            ):
                allowed_shared_count += 1
            else:
                direct_module_imports.append(f"from:{module}")
                forbidden_symbol_imports.extend(
                    item.name for item in node.names
                )
    if (
        direct_module_imports
        or forbidden_symbol_imports
        or allowed_shared_count != 1
    ):
        raise QualificationContractError(
            "spectral confirmation dependency review differs from the "
            "allowed shared estimator-input boundary"
        )
    return {
        "source_sha256": sha256_bytes(source),
        "allowed_shared_cartesian_input_type": "CartesianFourierEstimatorInputs",
        "allowed_shared_input_type_import_count": allowed_shared_count,
        "forbidden_cartesian_generator_symbols": sorted(forbidden),
        "forbidden_cartesian_generator_symbols_imported": sorted(
            forbidden_symbol_imports
        ),
        "direct_cartesian_module_imports_observed": sorted(
            direct_module_imports
        ),
        "static_direct_import_review_only": True,
        "dynamic_or_transitive_dependency_absence_proved": False,
    }


def _construction_review_document(
    *,
    loaded_d6: LoadedScopeLimitedD6Decision,
    parent: LoadedQualificationProtocol,
    design: D7ConfirmationExecutionDesignDraft,
    stable_design_sha256: str,
    source_set_sha256: str,
    root: Path,
) -> dict[str, object]:
    terminal = loaded_d6.decision.selection_terminal
    historical_selection_source_sha256 = _engine_module_sha256(
        parent,
        "spirallens.synthetic.cartesian_fourier_domain_phantom",
    )
    spectral = SpectralMomentConfirmationGenerator().family_identity
    if (
        spectral.family_id != SPECTRAL_MOMENT_GENERATOR_FAMILY_ID
        or spectral.construction_family_id
        != SPECTRAL_MOMENT_CONSTRUCTION_FAMILY_ID
        or spectral.implementation_id != SPECTRAL_MOMENT_IMPLEMENTATION_ID
    ):
        raise QualificationContractError(
            "spectral family identity differs from the closed C1 construction"
        )
    if (
        terminal.selection_generator_family_id == spectral.family_id
        or terminal.selection_construction_family_id
        == spectral.construction_family_id
        or historical_selection_source_sha256 == spectral.source_sha256
    ):
        raise QualificationContractError(
            "D7 construction differs only by a label, seed, or implementation tag"
        )
    case_body = [
        {
            "case_id": case_id,
            "semantic": semantic,
            "construction_recipe": recipe,
            "core_disposition": core,
            "loop_disposition": loop,
        }
        for case_id, semantic, recipe, core, loop in SPECTRAL_MOMENT_CASE_REGISTRY
    ]
    import_review = _spectral_import_review(root)
    if import_review["source_sha256"] != spectral.source_sha256:
        raise QualificationContractError(
            "spectral family identity differs from the source-set checkout"
        )
    return {
        "schema_version": D7_CONSTRUCTION_DIVERSITY_REVIEW_SCHEMA_VERSION,
        "review_id": "d7-spectral-moment-construction-diversity-review-v0-1",
        "status": "declared-construction-diversity-review-pass-not-admission",
        "claim_ceiling": "level_0",
        "parent_bindings": {
            "d6_decision_sha256": loaded_d6.identity.canonical_sha256,
            "admission_spec_sha256": (
                loaded_d6.decision.confirmation_admission_spec.canonical_sha256
            ),
            "parent_protocol_sha256": parent.canonical_sha256,
            "selection_implementation_registry_sha256": (
                terminal.selection_implementation_registry_sha256
            ),
            "stable_seed_free_design_sha256": stable_design_sha256,
            "source_set_manifest_sha256": source_set_sha256,
        },
        "selection_construction": {
            "generator_family_id": terminal.selection_generator_family_id,
            "construction_family_id": terminal.selection_construction_family_id,
            "source_module": (
                "spirallens.synthetic.cartesian_fourier_domain_phantom"
            ),
            "source_sha256": historical_selection_source_sha256,
            "source_commit": parent.protocol.engine.commit,
            "implementation_id_persisted_in_d6": False,
            "implementation_version_persisted_in_d6": False,
            "current_checkout_identity_substituted": False,
        },
        "confirmation_construction": spectral.to_dict(),
        "confirmation_case_registry": case_body,
        "confirmation_case_registry_sha256": canonical_json_sha256(case_body),
        "required_case_semantics": list(SPECTRAL_MOMENT_REQUIRED_CASE_SEMANTICS),
        "mechanism_comparison": dict(_CONSTRUCTION_MECHANISM_COMPARISON),
        "intentional_shared_interface": dict(_CONSTRUCTION_SHARED_INTERFACE),
        "source_dependency_review": import_review,
        "declared_construction_diversity_review_passed": True,
        "declared_implementation_distinctness_review_passed": True,
        "static_dependency_review_only": True,
        "dynamic_or_transitive_independence_proved": False,
        "epistemic_independence_proved": False,
        "family_admitted": False,
        "source_closure_verified": False,
        "confirmation_values_accessed": False,
    }


def _implementation_registry_document(
    *,
    loaded_d6: LoadedScopeLimitedD6Decision,
    parent: LoadedQualificationProtocol,
    design: D7ConfirmationExecutionDesignDraft,
    stable_design_sha256: str,
    construction_review_sha256: str,
    source_set_sha256: str,
) -> dict[str, object]:
    terminal = loaded_d6.decision.selection_terminal
    admission = loaded_d6.decision.confirmation_admission_spec
    spectral = SpectralMomentConfirmationGenerator().family_identity
    case_bindings = [
        {
            "generator_case_id": case_id,
            "semantic": semantic,
            "construction_recipe": recipe,
            "core_disposition": core,
            "loop_disposition": loop,
        }
        for case_id, semantic, recipe, core, loop in SPECTRAL_MOMENT_CASE_REGISTRY
    ]
    return {
        "schema_version": D7_CONFIRMATION_IMPLEMENTATION_REGISTRY_SCHEMA_VERSION,
        "registry_id": "d7-spectral-moment-confirmation-implementation-v0-1",
        "status": "seed-free-implementation-registered-source-closure-pending",
        "claim_ceiling": "level_0",
        "parent_bindings": {
            "d6_decision_sha256": loaded_d6.identity.canonical_sha256,
            "admission_spec_sha256": admission.canonical_sha256,
            "parent_protocol_sha256": parent.canonical_sha256,
            "parent_selection_implementation_registry_sha256": (
                terminal.selection_implementation_registry_sha256
            ),
            "selection_implementation_registry_reused": False,
        },
        "design_bindings": {
            "stable_seed_free_design_sha256": stable_design_sha256,
            "source_draft_sha256": design.canonical_sha256,
            "inventory_sha256": canonical_json_sha256(design.inventory.to_dict()),
            "successor_cells_sha256": (
                design.manifest_compatibility.confirmation_cells_manifest_sha256
            ),
            "successor_stress_sha256": (
                design.manifest_compatibility.confirmation_stress_strata_sha256
            ),
            "graph_axes_sha256": canonical_json_sha256(design.graph_axes.to_dict()),
            "thresholds_sha256": canonical_json_sha256(design.thresholds.to_dict()),
            "construction_review_sha256": construction_review_sha256,
            "source_set_manifest_sha256": source_set_sha256,
        },
        "generator": {
            "family_identity": spectral.to_dict(),
            "case_bindings": case_bindings,
            "case_registry_sha256": canonical_json_sha256(case_bindings),
            "input_adapter_id": (
                "spectral-moment-to-cartesian-fourier-estimator-input-v0-1"
            ),
            "stress_translation_id": SPECTRAL_MOMENT_STRESS_TRANSLATION_ID,
            "state_normalization_id": SPECTRAL_MOMENT_STATE_NORMALIZATION_ID,
            "preparation_operation_id": (
                "spectral-moment-oracle-free-estimator-input-preparation-v0-1"
            ),
        },
        "inherited_interface": {
            "surrogate_estimator_id": admission.required_surrogate_estimator_id,
            "surrogate_trivialization_id": (
                admission.required_surrogate_trivialization_id
            ),
            "field_estimator_id": CARTESIAN_FOURIER_FIELD_ESTIMATOR_ID,
            "domain_construction_id": DOMAIN_CONSTRUCTION_ID,
            "support_construction_id": SUPPORT_CONSTRUCTION_ID,
            "core_estimator_id": CORE_ESTIMATOR_ID,
            "loop_estimator_id": LOOP_PHASE_ESTIMATOR_ID,
        },
        "operations": dict(_REGISTRY_OPERATIONS),
        "policy": {
            "required_case_semantics": list(admission.required_case_semantics),
            "selection_evidence_disjointness_required": (
                admission.selection_evidence_disjointness_required
            ),
            "policy_override_allowed": admission.policy_override_allowed,
            "post_selection_exclusion_allowed": (
                admission.post_selection_exclusion_allowed
            ),
        },
        "source_set_declared": True,
        "source_closure_verified": False,
        "official_seed_inventory_present": False,
        "execution_authorized": False,
        "result_produced": False,
        "family_admitted": False,
        "d7_state": "not_run",
        "d8_state": "not_run",
        "authority": dict(sorted(_AUTHORITY.items())),
    }


def _aggregation_application_document(
    *,
    loaded_d6: LoadedScopeLimitedD6Decision,
    parent: LoadedQualificationProtocol,
    design: D7ConfirmationExecutionDesignDraft,
    stable_design_sha256: str,
    implementation_registry_sha256: str,
) -> dict[str, object]:
    parent_evaluation = parent.protocol.evaluation_design.to_dict()
    if parent_evaluation["paired_repeated_measure_block_unit"] != (
        "selection-seed-block"
    ):
        raise QualificationContractError(
            "parent aggregation lacks the historical selection seed-block identity"
        )
    successor_evaluation = {
        "schema_version": D7_CONFIRMATION_EVALUATION_DESIGN_SCHEMA_VERSION,
        **parent_evaluation,
        "paired_repeated_measure_block_unit": "confirmation-seed-slot-block",
    }
    parent_projection = {
        key: value
        for key, value in parent_evaluation.items()
        if key != "paired_repeated_measure_block_unit"
    }
    successor_projection = {
        key: value
        for key, value in successor_evaluation.items()
        if key not in {"schema_version", "paired_repeated_measure_block_unit"}
    }
    if parent_projection != successor_projection:
        raise QualificationContractError(
            "D7 evaluation design differs beyond the seed-block identity"
        )
    coverage = parent.protocol.coverage_policy.to_dict()
    if (
        coverage != _COVERAGE_POLICY
        or successor_evaluation != _CONFIRMATION_EVALUATION_DESIGN
    ):
        raise QualificationContractError(
            "D7 coverage or evaluation design differs from the reviewed "
            "seed-slot aggregation contract"
        )
    successor_body = {
        "schema_version": D7_LOCKED_CONFIRMATION_AGGREGATION_SCHEMA_VERSION,
        "coverage_policy": coverage,
        "evaluation_design": successor_evaluation,
    }
    parent_aggregation_sha256 = (
        loaded_d6.decision.selection_terminal.locked_aggregation_sha256
    )
    successor_aggregation_sha256 = canonical_json_sha256(successor_body)
    if parent_aggregation_sha256 == successor_aggregation_sha256:
        raise QualificationContractError(
            "D7 aggregation must not reuse the selection-specific body"
        )
    inventory = design.inventory
    required_strata = inventory.expected_strata
    prerequisite_primary_count = sum(
        item.case_semantics == "prerequisite-failure|prerequisite-failure"
        for item in inventory.primary_units
    )
    return {
        "schema_version": (
            D7_CONFIRMATION_AGGREGATION_APPLICATION_SCHEMA_VERSION
        ),
        "application_id": "d7-spectral-moment-seed-slot-aggregation-v0-1",
        "status": "seed-free-aggregation-application-source-closure-pending",
        "claim_ceiling": "level_0",
        "bindings": {
            "stable_seed_free_design_sha256": stable_design_sha256,
            "implementation_registry_sha256": implementation_registry_sha256,
            "inventory_sha256": canonical_json_sha256(inventory.to_dict()),
            "successor_cells_sha256": (
                design.manifest_compatibility.confirmation_cells_manifest_sha256
            ),
            "successor_stress_sha256": (
                design.manifest_compatibility.confirmation_stress_strata_sha256
            ),
            "parent_locked_aggregation_sha256": parent_aggregation_sha256,
            "successor_locked_aggregation_sha256": successor_aggregation_sha256,
            "parent_and_successor_aggregation_differ": True,
        },
        "coverage_policy": {
            "canonical_sha256": canonical_json_sha256(coverage),
            "body": coverage,
            "exact_parent_policy_retained": True,
        },
        "evaluation_design": successor_evaluation,
        "identity_free_evaluation_projection_sha256": canonical_json_sha256(
            successor_projection
        ),
        "locked_aggregation": successor_body,
        "seed_slot_ordinal_mapping": [
            {"ordinal": index, "seed_slot_id": slot_id}
            for index, slot_id in enumerate(D7_CONFIRMATION_SEED_SLOT_IDS)
        ],
        "numeric_seed_values_present": False,
        "counts": {
            "seed_slot_blocks": len(D7_CONFIRMATION_SEED_SLOT_IDS),
            "primary_units": len(inventory.primary_units),
            "core_cells": len(inventory.core_cells),
            "loop_cells": len(inventory.loop_cells),
            "required_strata": len(required_strata),
            "d2_boundary_collapsed_units": int(
                successor_evaluation["d2_unique_scientific_input_unit_count"]
            ),
            "rate_eligible_primary_units": (
                len(inventory.primary_units) - prerequisite_primary_count
            ),
            "mandatory_prerequisite_primary_units": prerequisite_primary_count,
            "field_graph_repeats_per_primary": 3,
            "loop_repeats_per_primary": 18,
        },
        "repeated_measure_semantics": dict(_REPEATED_MEASURE_SEMANTICS),
        "application_policy": dict(_AGGREGATION_APPLICATION_POLICY),
        "aggregation_applied_to_result": False,
        "result_present": False,
        "d7_state": "not_run",
        "d8_state": "not_run",
        "authority": dict(sorted(_AUTHORITY.items())),
    }


def _successor_rebinding_review_contract_document(
    *,
    proposal: D6D7StructuralRebindingAmendment,
    stable_design_sha256: str,
    construction_review_sha256: str,
    implementation_registry_sha256: str,
    aggregation_application_sha256: str,
    source_set_sha256: str,
) -> dict[str, object]:
    proposal_document = proposal.to_dict()
    return {
        "schema_version": (
            D7_SUCCESSOR_REBINDING_REVIEW_CONTRACT_SCHEMA_VERSION
        ),
        "review_contract_id": "d7-successor-rebinding-review-contract-v0-1",
        "status": "successor-rebinding-review-contract-encoded",
        "claim_ceiling": "level_0",
        "historical_proposal": {
            "schema_version": proposal.schema_version,
            "canonical_sha256": proposal.canonical_sha256,
            "status": proposal_document["status"],
            "body": proposal_document,
            "historical_proposal_mutated": False,
            "historical_d6_reinterpreted": False,
        },
        "successor_bindings": {
            "stable_seed_free_design_sha256": stable_design_sha256,
            "construction_diversity_review_sha256": (
                construction_review_sha256
            ),
            "implementation_registry_sha256": implementation_registry_sha256,
            "aggregation_application_sha256": aggregation_application_sha256,
            "source_set_manifest_sha256": source_set_sha256,
        },
        "declared_fulfillment_rule": dict(_SUCCESSOR_FULFILLMENT_RULE),
        "review_contract_encoded": True,
        "encoded_in_c1_candidate": True,
        "repository_review_attestation_embedded": False,
        "effective_for_admission": False,
        "family_admitted": False,
        "source_closure_verified": False,
        "official_seed_inventory_present": False,
        "confirmation_values_accessed": False,
        "historical_d6_exact_admission_satisfied": False,
        "d7_state": "not_run",
        "d8_state": "not_run",
        "authority": dict(sorted(_AUTHORITY.items())),
    }


@dataclass(frozen=True, slots=True, init=False)
class D7C1SeedFreeSourceSet:
    """Factory-built canonical C1 candidate; not committed source authority."""

    _canonical_bytes: bytes

    schema_version: ClassVar[str] = D7_C1_SEED_FREE_SOURCE_SET_SCHEMA_VERSION
    bundle_id: ClassVar[str] = "d7-spectral-moment-c1-seed-free-source-set-v0-1"

    def __init__(
        self,
        *,
        _factory_token: object = None,
        canonical_bytes: bytes,
    ) -> None:
        if _factory_token is not _BUNDLE_FACTORY_TOKEN:
            raise QualificationContractError(
                "D7C1SeedFreeSourceSet must be produced by its authoritative builder"
            )
        if (
            not isinstance(canonical_bytes, bytes)
            or not canonical_bytes
            or len(canonical_bytes) > MAX_D7_C1_SEED_FREE_SOURCE_SET_BYTES
        ):
            raise QualificationContractError(
                "C1 seed-free source set must be nonempty canonical bytes "
                "within the cap"
            )
        try:
            document = parse_canonical_json(
                canonical_bytes,
                label="D7 C1 seed-free source set",
            )
        except CanonicalJsonError as error:
            raise QualificationContractError(str(error)) from error
        if not isinstance(document, Mapping):
            raise QualificationContractError(
                "D7 C1 seed-free source set must be a canonical object"
            )
        if (
            document.get("schema_version") != self.schema_version
            or document.get("bundle_id") != self.bundle_id
        ):
            raise QualificationContractError(
                "D7 C1 seed-free source-set identity differs"
            )
        self._validate_document(document)
        object.__setattr__(self, "_canonical_bytes", canonical_bytes)

    @classmethod
    def _validate_document(cls, document: Mapping[str, object]) -> None:
        expected_root = {
            "schema_version",
            "bundle_id",
            "status",
            "claim_ceiling",
            "repository_path",
            "parent_bindings",
            "component_order",
            "component_hashes",
            "component_set_sha256",
            "components",
            "chronology",
            "deferred",
            "d7_state",
            "d8_state",
            "authority",
        }
        if set(document) != expected_root:
            raise QualificationContractError(
                "D7 C1 seed-free source-set root fields differ"
            )
        _require_exact_json_value(
            document["authority"],
            dict(sorted(_AUTHORITY.items())),
            label="D7 C1 authority",
        )
        _require_exact_json_value(
            document["deferred"],
            _C1_DEFERRED,
            label="D7 C1 deferred obligations",
        )
        _require_exact_json_value(
            document["chronology"],
            _c1_chronology_document(),
            label="D7 C1 chronology",
        )
        if (
            document["status"] != "seed-free-source-set-candidate"
            or document["claim_ceiling"] != "level_0"
            or document["repository_path"] != D7_C1_BUNDLE_REPOSITORY_PATH
            or document["d7_state"] != "not_run"
            or document["d8_state"] != "not_run"
        ):
            raise QualificationContractError(
                "D7 C1 seed-free source-set state or authority differs"
            )
        expected_names = tuple(sorted(_COMPONENT_SCHEMAS))
        component_order = document["component_order"]
        components = document["components"]
        component_hashes = document["component_hashes"]
        if (
            component_order != list(expected_names)
            or not isinstance(components, Mapping)
            or not isinstance(component_hashes, Mapping)
            or set(components) != set(expected_names)
            or set(component_hashes) != set(expected_names)
        ):
            raise QualificationContractError(
                "D7 C1 component inventory differs"
            )
        observed_hashes: dict[str, str] = {}
        for name in expected_names:
            component = components[name]
            if (
                not isinstance(component, Mapping)
                or set(component) != {"canonical_sha256", "body"}
                or not isinstance(component["body"], Mapping)
            ):
                raise QualificationContractError(
                    f"D7 C1 component {name} shape differs"
                )
            body = component["body"]
            digest = canonical_json_sha256(body)
            require_sha256(
                component["canonical_sha256"],
                label=f"{name} canonical_sha256",
            )
            if (
                component["canonical_sha256"] != digest
                or component_hashes[name] != digest
                or body.get("schema_version") != _COMPONENT_SCHEMAS[name]
            ):
                raise QualificationContractError(
                    f"D7 C1 component {name} identity differs"
                )
            observed_hashes[name] = digest
        if (
            document["component_set_sha256"]
            != canonical_json_sha256(observed_hashes)
        ):
            raise QualificationContractError(
                "D7 C1 component-set digest differs"
            )
        root_parent = document["parent_bindings"]
        if not isinstance(root_parent, Mapping):
            raise QualificationContractError("D7 C1 parent bindings are malformed")
        _exact_keys(
            root_parent,
            {
                "d6_decision_sha256",
                "d6_admission_spec_sha256",
                "parent_protocol_sha256",
                "source_draft_sha256",
                "historical_rebinding_proposal_sha256",
            },
            label="D7 C1 parent bindings",
        )
        for name in (
            "d6_decision_sha256",
            "d6_admission_spec_sha256",
            "parent_protocol_sha256",
            "source_draft_sha256",
            "historical_rebinding_proposal_sha256",
        ):
            require_sha256(root_parent.get(name), label=f"C1 parent {name}")
        if (
            root_parent["d6_decision_sha256"]
            != _CANONICAL_D6_DECISION_SHA256
            or root_parent["d6_admission_spec_sha256"]
            != _CANONICAL_D6_ADMISSION_SPEC_SHA256
            or root_parent["parent_protocol_sha256"]
            != _CANONICAL_PARENT_PROTOCOL_SHA256
            or root_parent["source_draft_sha256"]
            != _CANONICAL_SOURCE_DRAFT_SHA256
            or root_parent["historical_rebinding_proposal_sha256"]
            != _CANONICAL_HISTORICAL_REBINDING_PROPOSAL_SHA256
        ):
            raise QualificationContractError(
                "D7 C1 parent bindings differ from the pinned lineage"
            )
        stable = components["seed_free_execution_design"]["body"]
        construction = components["construction_diversity_review"]["body"]
        registry = components["implementation_registry"]["body"]
        aggregation = components["aggregation_application"]["body"]
        review_contract = components["successor_rebinding_review_contract"]["body"]
        source_manifest = components["source_set_manifest"]["body"]
        if not all(
            isinstance(value, Mapping)
            for value in (
                stable,
                construction,
                registry,
                aggregation,
                review_contract,
                source_manifest,
            )
        ):
            raise QualificationContractError("D7 C1 component bodies are malformed")
        _exact_keys(
            stable,
            {
                "schema_version",
                "design_id",
                "status",
                "claim_ceiling",
                "source_draft_schema_version",
                "source_draft_id",
                "source_draft_canonical_sha256",
                "seed_free_execution_design",
                "invariant_identities",
                "counts",
                "source_draft_status_is_embedded_historical_body",
                "embedded_in_c1_candidate",
                "committed_c1_verified",
                "concrete_seed_inventory_present",
                "full_design_frozen",
                "execution_authorized",
                "result_schema_present",
                "terminal_writer_present",
                "d7_state",
                "d8_state",
            },
            label="D7 C1 stable design",
        )
        _exact_keys(
            construction,
            {
                "schema_version",
                "review_id",
                "status",
                "claim_ceiling",
                "parent_bindings",
                "selection_construction",
                "confirmation_construction",
                "confirmation_case_registry",
                "confirmation_case_registry_sha256",
                "required_case_semantics",
                "mechanism_comparison",
                "intentional_shared_interface",
                "source_dependency_review",
                "declared_construction_diversity_review_passed",
                "declared_implementation_distinctness_review_passed",
                "static_dependency_review_only",
                "dynamic_or_transitive_independence_proved",
                "epistemic_independence_proved",
                "family_admitted",
                "source_closure_verified",
                "confirmation_values_accessed",
            },
            label="D7 C1 construction review",
        )
        _exact_keys(
            registry,
            {
                "schema_version",
                "registry_id",
                "status",
                "claim_ceiling",
                "parent_bindings",
                "design_bindings",
                "generator",
                "inherited_interface",
                "operations",
                "policy",
                "source_set_declared",
                "source_closure_verified",
                "official_seed_inventory_present",
                "execution_authorized",
                "result_produced",
                "family_admitted",
                "d7_state",
                "d8_state",
                "authority",
            },
            label="D7 C1 implementation registry",
        )
        _exact_keys(
            aggregation,
            {
                "schema_version",
                "application_id",
                "status",
                "claim_ceiling",
                "bindings",
                "coverage_policy",
                "evaluation_design",
                "identity_free_evaluation_projection_sha256",
                "locked_aggregation",
                "seed_slot_ordinal_mapping",
                "numeric_seed_values_present",
                "counts",
                "repeated_measure_semantics",
                "application_policy",
                "aggregation_applied_to_result",
                "result_present",
                "d7_state",
                "d8_state",
                "authority",
            },
            label="D7 C1 aggregation application",
        )
        _exact_keys(
            review_contract,
            {
                "schema_version",
                "review_contract_id",
                "status",
                "claim_ceiling",
                "historical_proposal",
                "successor_bindings",
                "declared_fulfillment_rule",
                "review_contract_encoded",
                "encoded_in_c1_candidate",
                "repository_review_attestation_embedded",
                "effective_for_admission",
                "family_admitted",
                "source_closure_verified",
                "official_seed_inventory_present",
                "confirmation_values_accessed",
                "historical_d6_exact_admission_satisfied",
                "d7_state",
                "d8_state",
                "authority",
            },
            label="D7 C1 successor rebinding review contract",
        )
        _exact_keys(
            source_manifest,
            {
                "schema_version",
                "manifest_id",
                "status",
                "enumeration_rule",
                "entries",
                "file_count",
                "role_counts",
                "total_bytes",
                "bundle_repository_path",
                "bundle_self_included",
                "bundle_self_digest_deferred_to_c2",
                "c2_receipt_repository_path",
                "c2_receipt_present",
                "git_commit_bound",
                "source_closure_verified",
                "python_runtime_dependency_closure_attested",
                "native_runtime_attested",
                "in_process_callable_identity_verified",
                "hostile_local_mutation_resistant",
            },
            label="D7 C1 source-set manifest",
        )
        if any(
            component.get("claim_ceiling") != "level_0"
            for component in (
                stable,
                construction,
                registry,
                aggregation,
                review_contract,
            )
        ):
            raise QualificationContractError(
                "D7 C1 component claim ceiling differs from Level 0"
            )
        source_entries = _source_manifest_entries(source_manifest)
        stable_invariants = stable.get("invariant_identities")
        stable_source_draft = stable.get("seed_free_execution_design")
        stable_parent_d6 = (
            stable_source_draft.get("parent_d6")
            if isinstance(stable_source_draft, Mapping)
            else None
        )
        stable_parent = (
            stable_source_draft.get("parent")
            if isinstance(stable_source_draft, Mapping)
            else None
        )
        seed_policy = (
            stable_source_draft.get("seed_policy")
            if isinstance(stable_source_draft, Mapping)
            else None
        )
        draft_family = (
            stable_source_draft.get("confirmation_family")
            if isinstance(stable_source_draft, Mapping)
            else None
        )
        locked_interface = (
            stable_source_draft.get("locked_parent_interface")
            if isinstance(stable_source_draft, Mapping)
            else None
        )
        stress_translation = (
            stable_source_draft.get("stress_translation")
            if isinstance(stable_source_draft, Mapping)
            else None
        )
        inventory = (
            stable_source_draft.get("inventory")
            if isinstance(stable_source_draft, Mapping)
            else None
        )
        manifest_compatibility = (
            stable_source_draft.get("manifest_compatibility")
            if isinstance(stable_source_draft, Mapping)
            else None
        )
        draft_implementation = (
            stable_source_draft.get("implementation_status")
            if isinstance(stable_source_draft, Mapping)
            else None
        )
        if (
            stable.get("design_id")
            != "d7-spectral-moment-stable-seed-free-design-v0-1"
            or stable.get("status")
            != "seed-free-design-embedded-in-c1-candidate"
            or stable.get("source_draft_schema_version")
            != D7_CONFIRMATION_EXECUTION_DRAFT_SCHEMA_VERSION
            or stable.get("source_draft_id")
            != "d7-spectral-moment-seed-free-execution-design-v0-2"
            or not isinstance(stable_invariants, Mapping)
            or not isinstance(stable_source_draft, Mapping)
            or stable.get("source_draft_canonical_sha256")
            != canonical_json_sha256(stable_source_draft)
            or stable.get("source_draft_canonical_sha256")
            != root_parent["source_draft_sha256"]
            or stable_invariants.get("parent_d6_sha256")
            != root_parent["d6_decision_sha256"]
            or stable_invariants.get("parent_protocol_sha256")
            != root_parent["parent_protocol_sha256"]
            or stable.get("source_draft_status_is_embedded_historical_body")
            is not True
            or stable.get("embedded_in_c1_candidate") is not True
            or stable.get("committed_c1_verified") is not False
            or stable.get("concrete_seed_inventory_present") is not False
            or stable.get("full_design_frozen") is not False
            or stable.get("execution_authorized") is not False
            or stable.get("result_schema_present") is not False
            or stable.get("terminal_writer_present") is not False
            or stable.get("d7_state") != "not_run"
            or stable.get("d8_state") != "not_run"
        ):
            raise QualificationContractError(
                "D7 C1 stable seed-free design state or joins differ"
            )
        _exact_keys(
            stable_invariants,
            {
                "parent_d6_sha256",
                "parent_protocol_sha256",
                "graph_axes_sha256",
                "thresholds_sha256",
                "stress_translation_sha256",
                "inventory_sha256",
                "successor_cells_sha256",
                "successor_stress_sha256",
                "structural_projection_sha256",
            },
            label="D7 C1 stable design invariants",
        )
        _exact_keys(
            stable_source_draft,
            {
                "schema_version",
                "draft_id",
                "status",
                "claim_ceiling",
                "parent_d6",
                "parent",
                "seed_policy",
                "confirmation_family",
                "locked_parent_interface",
                "stress_translation",
                "inventory",
                "manifest_compatibility",
                "implementation_status",
                "d7_state",
                "d8_state",
                "authority",
            },
            label="D7 C1 embedded source draft",
        )
        if not all(
            isinstance(value, Mapping)
            for value in (
                stable_parent_d6,
                stable_parent,
                seed_policy,
                draft_family,
                locked_interface,
                stress_translation,
                inventory,
                manifest_compatibility,
                draft_implementation,
            )
        ):
            raise QualificationContractError(
                "D7 C1 embedded source draft nested records are malformed"
            )
        expected_stable_counts = {
            "seed_slots": 2,
            "primary_units": D7_CONFIRMATION_PRIMARY_UNIT_COUNT,
            "core_cells": D7_CONFIRMATION_CORE_CELL_COUNT,
            "loop_cells": D7_CONFIRMATION_LOOP_CELL_COUNT,
            "event_lanes": D7_CONFIRMATION_EVENT_LANE_COUNT,
        }
        _require_exact_json_value(
            stable.get("counts"),
            expected_stable_counts,
            label="D7 C1 stable design counts",
        )
        _exact_keys(
            stable_parent_d6,
            {
                "schema_version",
                "d6_decision_id",
                "d6_decision_source_sha256",
                "d6_decision_canonical_sha256",
                "d6_decision_source_commit",
                "admission_spec_id",
                "admission_spec_sha256",
                "selection_terminal_binding_sha256",
                "selection_generator_family_id",
                "selection_construction_family_id",
                "required_surrogate_estimator_id",
                "required_surrogate_trivialization_id",
                "required_graph_axes_sha256",
                "required_cells_manifest_sha256",
                "required_stress_strata_sha256",
                "locked_thresholds_sha256",
                "locked_aggregation_sha256",
                "selection_implementation_registry_sha256",
                "repository_path",
                "committed_artifact_verified",
                "historical_terminal_companions_verified",
            },
            label="D7 C1 embedded D6 parent",
        )
        _exact_keys(
            stable_parent,
            {
                "schema_version",
                "protocol_id",
                "protocol_source_sha256",
                "protocol_canonical_sha256",
                "graph_axes_sha256",
                "required_cells_manifest_sha256",
                "required_stress_strata_sha256",
                "locked_thresholds_sha256",
                "locked_aggregation_sha256",
                "selection_implementation_registry_sha256",
                "selection_seed_count",
                "full_parent_protocol_bytes_loaded",
                "terminal_manifest_bytes_direct_design_argument",
                "terminal_result_bytes_direct_design_argument",
                "terminal_consumption_bytes_direct_design_argument",
                "terminal_manifest_bytes_retained_by_design",
                "terminal_result_bytes_retained_by_design",
                "terminal_consumption_bytes_retained_by_design",
                "historical_terminal_companions_verified_upstream",
            },
            label="D7 C1 embedded parent protocol",
        )
        parent_hash_joins = (
            (
                "required_graph_axes_sha256",
                "graph_axes_sha256",
            ),
            (
                "required_cells_manifest_sha256",
                "required_cells_manifest_sha256",
            ),
            (
                "required_stress_strata_sha256",
                "required_stress_strata_sha256",
            ),
            ("locked_thresholds_sha256", "locked_thresholds_sha256"),
            ("locked_aggregation_sha256", "locked_aggregation_sha256"),
            (
                "selection_implementation_registry_sha256",
                "selection_implementation_registry_sha256",
            ),
        )
        _require_exact_json_value(
            stable_source_draft.get("authority"),
            dict(sorted(_EMBEDDED_DRAFT_AUTHORITY.items())),
            label="D7 C1 embedded draft authority",
        )
        if (
            stable_source_draft.get("schema_version")
            != D7_CONFIRMATION_EXECUTION_DRAFT_SCHEMA_VERSION
            or stable_source_draft.get("draft_id")
            != "d7-spectral-moment-seed-free-execution-design-v0-2"
            or stable_source_draft.get("status")
            != "seed-free-execution-design-not-frozen"
            or stable_source_draft.get("claim_ceiling") != "level_0"
            or stable_source_draft.get("d7_state") != "not_run"
            or stable_source_draft.get("d8_state") != "not_run"
            or stable_parent_d6.get("schema_version")
            != D7_PARENT_D6_BINDING_SCHEMA_VERSION
            or stable_parent_d6.get("d6_decision_id")
            != _CANONICAL_D6_DECISION_ID
            or stable_parent_d6.get("admission_spec_id")
            != _CANONICAL_D6_ADMISSION_SPEC_ID
            or stable_parent_d6.get("d6_decision_canonical_sha256")
            != root_parent["d6_decision_sha256"]
            or stable_parent_d6.get("d6_decision_source_sha256")
            != root_parent["d6_decision_sha256"]
            or stable_parent_d6.get("admission_spec_sha256")
            != root_parent["d6_admission_spec_sha256"]
            or stable_parent_d6.get("committed_artifact_verified") is not True
            or stable_parent_d6.get("historical_terminal_companions_verified")
            is not True
            or stable_parent.get("schema_version")
            != D7_PARENT_PROTOCOL_DESIGN_BINDING_SCHEMA_VERSION
            or stable_parent.get("protocol_id")
            != _CANONICAL_PARENT_PROTOCOL_ID
            or stable_parent.get("protocol_source_sha256")
            != root_parent["parent_protocol_sha256"]
            or stable_parent.get("protocol_canonical_sha256")
            != root_parent["parent_protocol_sha256"]
            or stable_parent.get("selection_seed_count") != 2
            or stable_parent.get("full_parent_protocol_bytes_loaded") is not True
            or stable_parent.get(
                "historical_terminal_companions_verified_upstream"
            )
            is not True
            or any(
                stable_parent.get(parent_name)
                != stable_parent_d6.get(d6_name)
                for d6_name, parent_name in parent_hash_joins
            )
            or any(
                stable_parent.get(name) is not False
                for name in (
                    "terminal_manifest_bytes_direct_design_argument",
                    "terminal_result_bytes_direct_design_argument",
                    "terminal_consumption_bytes_direct_design_argument",
                    "terminal_manifest_bytes_retained_by_design",
                    "terminal_result_bytes_retained_by_design",
                    "terminal_consumption_bytes_retained_by_design",
                )
            )
        ):
            raise QualificationContractError(
                "D7 C1 embedded source-draft parent bindings differ"
            )
        for name in (
            "d6_decision_source_sha256",
            "d6_decision_canonical_sha256",
            "admission_spec_sha256",
            "selection_terminal_binding_sha256",
            "required_graph_axes_sha256",
            "required_cells_manifest_sha256",
            "required_stress_strata_sha256",
            "locked_thresholds_sha256",
            "locked_aggregation_sha256",
            "selection_implementation_registry_sha256",
        ):
            require_sha256(
                stable_parent_d6.get(name),
                label=f"D7 C1 embedded D6 {name}",
            )
        _exact_keys(
            seed_policy,
            {
                "schema_version",
                "seed_slot_ids",
                "required_seed_count",
                "concrete_seed_inventory_present",
                "seed_values_are_nonnegative_signed_int64",
                "seed_values_must_be_unique_and_canonically_sorted",
                "parent_selection_seeds_must_be_excluded",
                "development_exclusion_registry_sha256",
                "unseen_status",
                "cryptographic_unseen_proof",
                "seed_supplier_must_follow_seed_free_source_readiness",
                "seed_inventory_frozen",
            },
            label="D7 C1 embedded seed policy",
        )
        if (
            seed_policy.get("schema_version")
            != "spirallens.d7-confirmation-seed-policy.v0.1"
            or seed_policy.get("seed_slot_ids")
            != list(D7_CONFIRMATION_SEED_SLOT_IDS)
            or seed_policy.get("required_seed_count") != 2
            or seed_policy.get("concrete_seed_inventory_present") is not False
            or seed_policy.get("seed_values_are_nonnegative_signed_int64")
            is not True
            or seed_policy.get(
                "seed_values_must_be_unique_and_canonically_sorted"
            )
            is not True
            or seed_policy.get("parent_selection_seeds_must_be_excluded")
            is not True
            or seed_policy.get("unseen_status")
            != "external-attestation-required"
            or seed_policy.get("cryptographic_unseen_proof") is not False
            or seed_policy.get(
                "seed_supplier_must_follow_seed_free_source_readiness"
            )
            is not True
            or seed_policy.get("seed_inventory_frozen") is not False
        ):
            raise QualificationContractError(
                "D7 C1 embedded seed policy differs"
            )
        require_sha256(
            seed_policy.get("development_exclusion_registry_sha256"),
            label="D7 C1 development exclusion registry",
        )
        expected_draft_family = {
            "generator_family_id": SPECTRAL_MOMENT_GENERATOR_FAMILY_ID,
            "family_admitted": False,
            "construction_diversity_reviewed": False,
            "committed_source_closure_verified": False,
        }
        _require_exact_json_value(
            draft_family,
            expected_draft_family,
            label="D7 C1 embedded confirmation family",
        )
        _exact_keys(
            locked_interface,
            {
                "graph_axes",
                "domain",
                "thresholds",
                "coverage_policy",
                "graph_axes_byte_identity_verified",
                "thresholds_byte_identity_verified",
                "parent_aggregation_application_rebinding_reviewed",
                "selection_implementation_registry_reused_as_d7_registry",
            },
            label="D7 C1 embedded parent interface",
        )
        _require_exact_json_value(
            locked_interface.get("graph_axes"),
            _GRAPH_AXES,
            label="D7 C1 locked graph axes",
        )
        _require_exact_json_value(
            locked_interface.get("domain"),
            _DOMAIN,
            label="D7 C1 locked domain",
        )
        _require_exact_json_value(
            locked_interface.get("thresholds"),
            _THRESHOLDS,
            label="D7 C1 locked thresholds",
        )
        _require_exact_json_value(
            locked_interface.get("coverage_policy"),
            _COVERAGE_POLICY,
            label="D7 C1 locked coverage policy",
        )
        if (
            locked_interface.get("graph_axes_byte_identity_verified")
            is not True
            or locked_interface.get("thresholds_byte_identity_verified")
            is not True
            or locked_interface.get(
                "parent_aggregation_application_rebinding_reviewed"
            )
            is not False
            or locked_interface.get(
                "selection_implementation_registry_reused_as_d7_registry"
            )
            is not False
        ):
            raise QualificationContractError(
                "D7 C1 embedded parent interface differs"
            )
        _require_exact_json_value(
            stress_translation,
            _expected_stress_translation_document(),
            label="D7 C1 embedded stress translation",
        )
        inventory_identities = _inventory_identities(inventory)
        _exact_keys(
            manifest_compatibility,
            {
                "schema_version",
                "parent_required_cells_manifest_sha256",
                "parent_required_stress_strata_sha256",
                "confirmation_cells_manifest_sha256",
                "confirmation_stress_strata_sha256",
                "structural_projection_schema_version",
                "parent_structural_projection_sha256",
                "confirmation_structural_projection_sha256",
                "parent_manifests_contain_selection_specific_identities",
                "confirmation_manifests_use_seed_slots_and_spectral_cases",
                "exact_parent_cells_manifest_satisfied",
                "exact_parent_stress_manifest_satisfied",
                "structural_template_match_observed",
                "structural_match_is_exact_parent_hash_satisfaction",
                "silent_reinterpretation_allowed",
                "reviewed_structural_rebinding_amendment_published",
                "d6_admission_spec_satisfied",
                "resolution_required",
            },
            label="D7 C1 embedded manifest compatibility",
        )
        if (
            manifest_compatibility.get("schema_version")
            != D7_PARENT_MANIFEST_COMPATIBILITY_SCHEMA_VERSION
            or manifest_compatibility.get(
                "parent_required_cells_manifest_sha256"
            )
            != stable_parent["required_cells_manifest_sha256"]
            or manifest_compatibility.get(
                "parent_required_stress_strata_sha256"
            )
            != stable_parent["required_stress_strata_sha256"]
            or manifest_compatibility.get(
                "confirmation_cells_manifest_sha256"
            )
            != inventory_identities["successor_cells_sha256"]
            or manifest_compatibility.get(
                "confirmation_stress_strata_sha256"
            )
            != inventory_identities["successor_stress_sha256"]
            or manifest_compatibility.get(
                "structural_projection_schema_version"
            )
            != D7_STRUCTURAL_PROJECTION_SCHEMA_VERSION
            or manifest_compatibility.get(
                "parent_structural_projection_sha256"
            )
            != inventory_identities["structural_projection_sha256"]
            or manifest_compatibility.get(
                "confirmation_structural_projection_sha256"
            )
            != inventory_identities["structural_projection_sha256"]
            or manifest_compatibility.get(
                "parent_manifests_contain_selection_specific_identities"
            )
            is not True
            or manifest_compatibility.get(
                "confirmation_manifests_use_seed_slots_and_spectral_cases"
            )
            is not True
            or manifest_compatibility.get("exact_parent_cells_manifest_satisfied")
            is not False
            or manifest_compatibility.get("exact_parent_stress_manifest_satisfied")
            is not False
            or manifest_compatibility.get("structural_template_match_observed")
            is not True
            or manifest_compatibility.get(
                "structural_match_is_exact_parent_hash_satisfaction"
            )
            is not False
            or manifest_compatibility.get("silent_reinterpretation_allowed")
            is not False
            or manifest_compatibility.get(
                "reviewed_structural_rebinding_amendment_published"
            )
            is not False
            or manifest_compatibility.get("d6_admission_spec_satisfied")
            is not False
            or manifest_compatibility.get("resolution_required")
            != "reviewed-successor-admission-contract"
        ):
            raise QualificationContractError(
                "D7 C1 embedded manifest compatibility differs"
            )
        if stable_invariants != {
            "parent_d6_sha256": root_parent["d6_decision_sha256"],
            "parent_protocol_sha256": root_parent["parent_protocol_sha256"],
            "graph_axes_sha256": canonical_json_sha256(_GRAPH_AXES),
            "thresholds_sha256": canonical_json_sha256(_THRESHOLDS),
            "stress_translation_sha256": canonical_json_sha256(
                _expected_stress_translation_document()
            ),
            **inventory_identities,
        }:
            raise QualificationContractError(
                "D7 C1 stable invariant identities differ"
            )
        expected_implementation = {
            "seed_free_inventory_implemented": True,
            "boundary_translation_implemented": True,
            "state_geometry_warp_translation_implemented": True,
            "structured_observation_perturbation_implemented": True,
            "offcore_loop_control_implemented": True,
            "all_graph_pairs_and_loop_roles_implemented": True,
            "oracle_truth_record_free_blind_kernels_implemented": True,
            "core_and_loop_same_primary_support_join_implemented": True,
            "concrete_seed_inventory_frozen": False,
            "source_readiness_receipt_present": False,
            "launch_intent_present": False,
            "exclusive_attempt_claim_present": False,
            "output_namespace_absence_verified": False,
            "terminal_result_and_failure_schemas_present": False,
            "atomic_terminal_writer_present": False,
            "canonical_full_design_artifact_published": False,
            "pre_access_design_freeze_receipt_issued": False,
        }
        _require_exact_json_value(
            draft_implementation,
            expected_implementation,
            label="D7 C1 embedded implementation state",
        )
        construction_parent = construction.get("parent_bindings")
        selection_construction = construction.get("selection_construction")
        confirmation_construction = construction.get("confirmation_construction")
        mechanism_comparison = construction.get("mechanism_comparison")
        shared_interface = construction.get("intentional_shared_interface")
        source_review = construction.get("source_dependency_review")
        expected_case_registry = [
            {
                "case_id": case_id,
                "semantic": semantic,
                "construction_recipe": recipe,
                "core_disposition": core,
                "loop_disposition": loop,
            }
            for case_id, semantic, recipe, core, loop in SPECTRAL_MOMENT_CASE_REGISTRY
        ]
        _require_exact_json_value(
            construction.get("confirmation_case_registry"),
            expected_case_registry,
            label="D7 C1 construction case registry",
        )
        if (
            construction.get("review_id")
            != "d7-spectral-moment-construction-diversity-review-v0-1"
            or construction.get("status")
            != "declared-construction-diversity-review-pass-not-admission"
            or not isinstance(construction_parent, Mapping)
            or not isinstance(selection_construction, Mapping)
            or not isinstance(confirmation_construction, Mapping)
            or not isinstance(mechanism_comparison, Mapping)
            or not isinstance(shared_interface, Mapping)
            or not isinstance(source_review, Mapping)
            or construction_parent.get("d6_decision_sha256")
            != root_parent["d6_decision_sha256"]
            or construction_parent.get("admission_spec_sha256")
            != root_parent["d6_admission_spec_sha256"]
            or construction_parent.get("parent_protocol_sha256")
            != root_parent["parent_protocol_sha256"]
            or construction_parent.get("stable_seed_free_design_sha256")
            != observed_hashes["seed_free_execution_design"]
            or construction_parent.get("source_set_manifest_sha256")
            != observed_hashes["source_set_manifest"]
            or construction_parent.get(
                "selection_implementation_registry_sha256"
            )
            != stable_parent["selection_implementation_registry_sha256"]
            or construction.get("confirmation_case_registry_sha256")
            != canonical_json_sha256(expected_case_registry)
            or construction.get("required_case_semantics")
            != list(SPECTRAL_MOMENT_REQUIRED_CASE_SEMANTICS)
            or construction.get(
                "declared_construction_diversity_review_passed"
            )
            is not True
            or construction.get(
                "declared_implementation_distinctness_review_passed"
            )
            is not True
            or construction.get("static_dependency_review_only") is not True
            or construction.get(
                "dynamic_or_transitive_independence_proved"
            )
            is not False
            or construction.get("epistemic_independence_proved") is not False
            or construction.get("family_admitted") is not False
            or construction.get("source_closure_verified") is not False
            or construction.get("confirmation_values_accessed") is not False
        ):
            raise QualificationContractError(
                "D7 C1 construction review state or joins differ"
            )
        _exact_keys(
            construction_parent,
            {
                "d6_decision_sha256",
                "admission_spec_sha256",
                "parent_protocol_sha256",
                "selection_implementation_registry_sha256",
                "stable_seed_free_design_sha256",
                "source_set_manifest_sha256",
            },
            label="D7 C1 construction parent bindings",
        )
        _exact_keys(
            selection_construction,
            {
                "generator_family_id",
                "construction_family_id",
                "source_module",
                "source_sha256",
                "source_commit",
                "implementation_id_persisted_in_d6",
                "implementation_version_persisted_in_d6",
                "current_checkout_identity_substituted",
            },
            label="D7 C1 selection construction",
        )
        _exact_keys(
            confirmation_construction,
            {
                "schema_version",
                "family_id",
                "construction_family_id",
                "implementation_id",
                "implementation_version",
                "source_sha256",
            },
            label="D7 C1 confirmation construction",
        )
        confirmation_source = source_entries[SPECTRAL_MOMENT_SOURCE_PATH]
        expected_confirmation_identity = {
            "schema_version": (
                "spirallens.synthetic-generator-family-identity.v0.1"
            ),
            "family_id": SPECTRAL_MOMENT_GENERATOR_FAMILY_ID,
            "construction_family_id": SPECTRAL_MOMENT_CONSTRUCTION_FAMILY_ID,
            "implementation_id": SPECTRAL_MOMENT_IMPLEMENTATION_ID,
            "implementation_version": SPECTRAL_MOMENT_IMPLEMENTATION_VERSION,
            "source_sha256": confirmation_source["source_sha256"],
        }
        if (
            selection_construction.get("generator_family_id")
            != stable_parent_d6["selection_generator_family_id"]
            or selection_construction.get("construction_family_id")
            != stable_parent_d6["selection_construction_family_id"]
            or selection_construction.get("source_module")
            != "spirallens.synthetic.cartesian_fourier_domain_phantom"
            or selection_construction.get("source_sha256")
            != _CANONICAL_SELECTION_SOURCE_SHA256
            or selection_construction.get("source_commit")
            != _CANONICAL_PARENT_ENGINE_COMMIT
            or selection_construction.get(
                "implementation_id_persisted_in_d6"
            )
            is not False
            or selection_construction.get(
                "implementation_version_persisted_in_d6"
            )
            is not False
            or selection_construction.get(
                "current_checkout_identity_substituted"
            )
            is not False
            or confirmation_construction.get("family_id")
            == selection_construction.get("generator_family_id")
            or confirmation_construction.get("construction_family_id")
            == selection_construction.get("construction_family_id")
            or confirmation_construction.get("source_sha256")
            == selection_construction.get("source_sha256")
        ):
            raise QualificationContractError(
                "D7 C1 construction-family identities differ"
            )
        _require_exact_json_value(
            confirmation_construction,
            expected_confirmation_identity,
            label="D7 C1 confirmation construction identity",
        )
        _require_exact_json_value(
            mechanism_comparison,
            _CONSTRUCTION_MECHANISM_COMPARISON,
            label="D7 C1 construction mechanism comparison",
        )
        _require_exact_json_value(
            shared_interface,
            _CONSTRUCTION_SHARED_INTERFACE,
            label="D7 C1 construction shared interface",
        )
        _exact_keys(
            source_review,
            {
                "source_sha256",
                "allowed_shared_cartesian_input_type",
                "allowed_shared_input_type_import_count",
                "forbidden_cartesian_generator_symbols",
                "forbidden_cartesian_generator_symbols_imported",
                "direct_cartesian_module_imports_observed",
                "static_direct_import_review_only",
                "dynamic_or_transitive_dependency_absence_proved",
            },
            label="D7 C1 construction source review",
        )
        expected_source_review = {
            "source_sha256": confirmation_construction.get("source_sha256"),
            "allowed_shared_cartesian_input_type": (
                "CartesianFourierEstimatorInputs"
            ),
            "allowed_shared_input_type_import_count": 1,
            "forbidden_cartesian_generator_symbols_imported": [],
            "forbidden_cartesian_generator_symbols": sorted(
                {
                    "CartesianFourierDomainGenerator",
                    "CartesianFourierDomainSpec",
                    "CartesianFourierDomainPhantom",
                }
            ),
            "direct_cartesian_module_imports_observed": [],
            "static_direct_import_review_only": True,
            "dynamic_or_transitive_dependency_absence_proved": False,
        }
        _require_exact_json_value(
            source_review,
            expected_source_review,
            label="D7 C1 construction source-dependency review",
        )
        registry_parent = registry.get("parent_bindings")
        registry_design = registry.get("design_bindings")
        registry_generator = registry.get("generator")
        registry_interface = registry.get("inherited_interface")
        registry_operations = registry.get("operations")
        registry_policy = registry.get("policy")
        registry_authority = registry.get("authority")
        if not all(
            isinstance(value, Mapping)
            for value in (
                registry_parent,
                registry_design,
                registry_generator,
                registry_interface,
                registry_operations,
                registry_policy,
            )
        ):
            raise QualificationContractError(
                "D7 C1 implementation registry nested records are malformed"
            )
        _exact_keys(
            registry_parent,
            {
                "d6_decision_sha256",
                "admission_spec_sha256",
                "parent_protocol_sha256",
                "parent_selection_implementation_registry_sha256",
                "selection_implementation_registry_reused",
            },
            label="D7 C1 registry parent bindings",
        )
        _exact_keys(
            registry_design,
            {
                "stable_seed_free_design_sha256",
                "source_draft_sha256",
                "inventory_sha256",
                "successor_cells_sha256",
                "successor_stress_sha256",
                "graph_axes_sha256",
                "thresholds_sha256",
                "construction_review_sha256",
                "source_set_manifest_sha256",
            },
            label="D7 C1 registry design bindings",
        )
        _exact_keys(
            registry_generator,
            {
                "family_identity",
                "case_bindings",
                "case_registry_sha256",
                "input_adapter_id",
                "stress_translation_id",
                "state_normalization_id",
                "preparation_operation_id",
            },
            label="D7 C1 registry generator",
        )
        _exact_keys(
            registry_interface,
            {
                "surrogate_estimator_id",
                "surrogate_trivialization_id",
                "field_estimator_id",
                "domain_construction_id",
                "support_construction_id",
                "core_estimator_id",
                "loop_estimator_id",
            },
            label="D7 C1 registry inherited interface",
        )
        _exact_keys(
            registry_operations,
            set(_REGISTRY_OPERATIONS),
            label="D7 C1 registry operations",
        )
        _exact_keys(
            registry_policy,
            {
                "required_case_semantics",
                "selection_evidence_disjointness_required",
                "policy_override_allowed",
                "post_selection_exclusion_allowed",
            },
            label="D7 C1 registry policy",
        )
        expected_case_bindings = [
            {
                "generator_case_id": case_id,
                "semantic": semantic,
                "construction_recipe": recipe,
                "core_disposition": core,
                "loop_disposition": loop,
            }
            for case_id, semantic, recipe, core, loop in SPECTRAL_MOMENT_CASE_REGISTRY
        ]
        expected_registry_interface = {
            "surrogate_estimator_id": (
                stable_parent_d6["required_surrogate_estimator_id"]
            ),
            "surrogate_trivialization_id": (
                stable_parent_d6["required_surrogate_trivialization_id"]
            ),
            "field_estimator_id": CARTESIAN_FOURIER_FIELD_ESTIMATOR_ID,
            "domain_construction_id": DOMAIN_CONSTRUCTION_ID,
            "support_construction_id": SUPPORT_CONSTRUCTION_ID,
            "core_estimator_id": CORE_ESTIMATOR_ID,
            "loop_estimator_id": LOOP_PHASE_ESTIMATOR_ID,
        }
        expected_registry_policy = {
            "required_case_semantics": list(
                SPECTRAL_MOMENT_REQUIRED_CASE_SEMANTICS
            ),
            "selection_evidence_disjointness_required": True,
            "policy_override_allowed": False,
            "post_selection_exclusion_allowed": False,
        }
        _require_exact_json_value(
            registry_generator.get("case_bindings"),
            expected_case_bindings,
            label="D7 C1 registry case bindings",
        )
        _require_exact_json_value(
            registry_interface,
            expected_registry_interface,
            label="D7 C1 registry inherited interface",
        )
        _require_exact_json_value(
            registry_operations,
            _REGISTRY_OPERATIONS,
            label="D7 C1 registry operations",
        )
        _require_exact_json_value(
            registry_policy,
            expected_registry_policy,
            label="D7 C1 registry policy",
        )
        _require_exact_json_value(
            registry_authority,
            dict(sorted(_AUTHORITY.items())),
            label="D7 C1 registry authority",
        )
        if (
            registry.get("registry_id")
            != "d7-spectral-moment-confirmation-implementation-v0-1"
            or registry.get("status")
            != "seed-free-implementation-registered-source-closure-pending"
            or registry_parent.get("d6_decision_sha256")
            != root_parent["d6_decision_sha256"]
            or registry_parent.get("admission_spec_sha256")
            != root_parent["d6_admission_spec_sha256"]
            or registry_parent.get("parent_protocol_sha256")
            != root_parent["parent_protocol_sha256"]
            or registry_parent.get(
                "parent_selection_implementation_registry_sha256"
            )
            != construction_parent.get(
                "selection_implementation_registry_sha256"
            )
            or registry_parent.get("selection_implementation_registry_reused")
            is not False
            or registry_design.get("stable_seed_free_design_sha256")
            != observed_hashes["seed_free_execution_design"]
            or registry_design.get("source_draft_sha256")
            != root_parent["source_draft_sha256"]
            or registry_design.get("construction_review_sha256")
            != observed_hashes["construction_diversity_review"]
            or registry_design.get("source_set_manifest_sha256")
            != observed_hashes["source_set_manifest"]
            or registry_design.get("inventory_sha256")
            != stable_invariants["inventory_sha256"]
            or registry_design.get("successor_cells_sha256")
            != stable_invariants["successor_cells_sha256"]
            or registry_design.get("successor_stress_sha256")
            != stable_invariants["successor_stress_sha256"]
            or registry_design.get("graph_axes_sha256")
            != stable_invariants["graph_axes_sha256"]
            or registry_design.get("thresholds_sha256")
            != stable_invariants["thresholds_sha256"]
            or registry_generator.get("family_identity")
            != confirmation_construction
            or registry_generator.get("case_bindings")
            != expected_case_bindings
            or registry_generator.get("case_registry_sha256")
            != canonical_json_sha256(expected_case_bindings)
            or registry_generator.get("input_adapter_id")
            != "spectral-moment-to-cartesian-fourier-estimator-input-v0-1"
            or registry_generator.get("stress_translation_id")
            != SPECTRAL_MOMENT_STRESS_TRANSLATION_ID
            or registry_generator.get("state_normalization_id")
            != SPECTRAL_MOMENT_STATE_NORMALIZATION_ID
            or registry_generator.get("preparation_operation_id")
            != "spectral-moment-oracle-free-estimator-input-preparation-v0-1"
            or registry_interface
            != {
                "surrogate_estimator_id": (
                    stable_parent_d6["required_surrogate_estimator_id"]
                ),
                "surrogate_trivialization_id": (
                    stable_parent_d6["required_surrogate_trivialization_id"]
                ),
                "field_estimator_id": CARTESIAN_FOURIER_FIELD_ESTIMATOR_ID,
                "domain_construction_id": DOMAIN_CONSTRUCTION_ID,
                "support_construction_id": SUPPORT_CONSTRUCTION_ID,
                "core_estimator_id": CORE_ESTIMATOR_ID,
                "loop_estimator_id": LOOP_PHASE_ESTIMATOR_ID,
            }
            or registry_operations != _REGISTRY_OPERATIONS
            or registry_policy
            != {
                "required_case_semantics": list(
                    SPECTRAL_MOMENT_REQUIRED_CASE_SEMANTICS
                ),
                "selection_evidence_disjointness_required": True,
                "policy_override_allowed": False,
                "post_selection_exclusion_allowed": False,
            }
            or registry.get("source_set_declared") is not True
            or registry.get("source_closure_verified") is not False
            or registry.get("official_seed_inventory_present") is not False
            or registry.get("execution_authorized") is not False
            or registry.get("result_produced") is not False
            or registry.get("family_admitted") is not False
            or registry.get("d7_state") != "not_run"
            or registry.get("d8_state") != "not_run"
            or registry_authority != dict(sorted(_AUTHORITY.items()))
        ):
            raise QualificationContractError(
                "D7 C1 implementation registry state, authority, or joins differ"
            )
        aggregation_bindings = aggregation.get("bindings")
        aggregation_coverage = aggregation.get("coverage_policy")
        aggregation_evaluation = aggregation.get("evaluation_design")
        aggregation_locked = aggregation.get("locked_aggregation")
        aggregation_counts = aggregation.get("counts")
        aggregation_repeated = aggregation.get("repeated_measure_semantics")
        aggregation_policy = aggregation.get("application_policy")
        aggregation_authority = aggregation.get("authority")
        if not all(
            isinstance(value, Mapping)
            for value in (
                aggregation_bindings,
                aggregation_coverage,
                aggregation_evaluation,
                aggregation_locked,
                aggregation_counts,
                aggregation_repeated,
                aggregation_policy,
            )
        ):
            raise QualificationContractError(
                "D7 C1 aggregation nested records are malformed"
            )
        _exact_keys(
            aggregation_bindings,
            {
                "stable_seed_free_design_sha256",
                "implementation_registry_sha256",
                "inventory_sha256",
                "successor_cells_sha256",
                "successor_stress_sha256",
                "parent_locked_aggregation_sha256",
                "successor_locked_aggregation_sha256",
                "parent_and_successor_aggregation_differ",
            },
            label="D7 C1 aggregation bindings",
        )
        _exact_keys(
            aggregation_coverage,
            {"canonical_sha256", "body", "exact_parent_policy_retained"},
            label="D7 C1 aggregation coverage",
        )
        _exact_keys(
            aggregation_evaluation,
            set(_CONFIRMATION_EVALUATION_DESIGN),
            label="D7 C1 aggregation evaluation design",
        )
        _exact_keys(
            aggregation_locked,
            {"schema_version", "coverage_policy", "evaluation_design"},
            label="D7 C1 locked aggregation",
        )
        _exact_keys(
            aggregation_counts,
            {
                "seed_slot_blocks",
                "primary_units",
                "core_cells",
                "loop_cells",
                "required_strata",
                "d2_boundary_collapsed_units",
                "rate_eligible_primary_units",
                "mandatory_prerequisite_primary_units",
                "field_graph_repeats_per_primary",
                "loop_repeats_per_primary",
            },
            label="D7 C1 aggregation counts",
        )
        _exact_keys(
            aggregation_repeated,
            set(_REPEATED_MEASURE_SEMANTICS),
            label="D7 C1 repeated-measure semantics",
        )
        _exact_keys(
            aggregation_policy,
            set(_AGGREGATION_APPLICATION_POLICY),
            label="D7 C1 aggregation policy",
        )
        expected_locked = {
            "schema_version": D7_LOCKED_CONFIRMATION_AGGREGATION_SCHEMA_VERSION,
            "coverage_policy": dict(_COVERAGE_POLICY),
            "evaluation_design": dict(_CONFIRMATION_EVALUATION_DESIGN),
        }
        evaluation_projection = {
            key: value
            for key, value in _CONFIRMATION_EVALUATION_DESIGN.items()
            if key
            not in {
                "schema_version",
                "paired_repeated_measure_block_unit",
            }
        }
        expected_aggregation_counts = {
            "seed_slot_blocks": 2,
            "primary_units": D7_CONFIRMATION_PRIMARY_UNIT_COUNT,
            "core_cells": D7_CONFIRMATION_CORE_CELL_COUNT,
            "loop_cells": D7_CONFIRMATION_LOOP_CELL_COUNT,
            "required_strata": 6,
            "d2_boundary_collapsed_units": 32,
            "rate_eligible_primary_units": 48,
            "mandatory_prerequisite_primary_units": 16,
            "field_graph_repeats_per_primary": 3,
            "loop_repeats_per_primary": 18,
        }
        expected_aggregation_coverage = {
            "canonical_sha256": canonical_json_sha256(_COVERAGE_POLICY),
            "body": dict(_COVERAGE_POLICY),
            "exact_parent_policy_retained": True,
        }
        expected_seed_slot_mapping = [
            {"ordinal": index, "seed_slot_id": slot_id}
            for index, slot_id in enumerate(D7_CONFIRMATION_SEED_SLOT_IDS)
        ]
        for value, expected, label in (
            (
                aggregation_coverage,
                expected_aggregation_coverage,
                "D7 C1 aggregation coverage",
            ),
            (
                aggregation_evaluation,
                _CONFIRMATION_EVALUATION_DESIGN,
                "D7 C1 aggregation evaluation design",
            ),
            (
                aggregation_locked,
                expected_locked,
                "D7 C1 locked aggregation",
            ),
            (
                aggregation_counts,
                expected_aggregation_counts,
                "D7 C1 aggregation counts",
            ),
            (
                aggregation_repeated,
                _REPEATED_MEASURE_SEMANTICS,
                "D7 C1 aggregation repeated measures",
            ),
            (
                aggregation_policy,
                _AGGREGATION_APPLICATION_POLICY,
                "D7 C1 aggregation policy",
            ),
            (
                aggregation_authority,
                dict(sorted(_AUTHORITY.items())),
                "D7 C1 aggregation authority",
            ),
            (
                aggregation.get("seed_slot_ordinal_mapping"),
                expected_seed_slot_mapping,
                "D7 C1 aggregation seed-slot mapping",
            ),
        ):
            _require_exact_json_value(value, expected, label=label)
        if (
            aggregation.get("application_id")
            != "d7-spectral-moment-seed-slot-aggregation-v0-1"
            or aggregation.get("status")
            != "seed-free-aggregation-application-source-closure-pending"
            or aggregation_bindings.get("stable_seed_free_design_sha256")
            != observed_hashes["seed_free_execution_design"]
            or aggregation_bindings.get("implementation_registry_sha256")
            != observed_hashes["implementation_registry"]
            or aggregation_bindings.get("inventory_sha256")
            != stable_invariants["inventory_sha256"]
            or aggregation_bindings.get("successor_cells_sha256")
            != stable_invariants["successor_cells_sha256"]
            or aggregation_bindings.get("successor_stress_sha256")
            != stable_invariants["successor_stress_sha256"]
            or aggregation_bindings.get("parent_locked_aggregation_sha256")
            != stable_parent["locked_aggregation_sha256"]
            or aggregation_bindings.get("successor_locked_aggregation_sha256")
            != canonical_json_sha256(expected_locked)
            or aggregation_bindings.get("parent_and_successor_aggregation_differ")
            is not True
            or aggregation_bindings.get("parent_locked_aggregation_sha256")
            == aggregation_bindings.get("successor_locked_aggregation_sha256")
            or aggregation_coverage
            != {
                "canonical_sha256": canonical_json_sha256(_COVERAGE_POLICY),
                "body": dict(_COVERAGE_POLICY),
                "exact_parent_policy_retained": True,
            }
            or aggregation_evaluation != _CONFIRMATION_EVALUATION_DESIGN
            or aggregation.get("identity_free_evaluation_projection_sha256")
            != canonical_json_sha256(evaluation_projection)
            or aggregation_locked != expected_locked
            or aggregation.get("seed_slot_ordinal_mapping")
            != [
                {"ordinal": index, "seed_slot_id": slot_id}
                for index, slot_id in enumerate(D7_CONFIRMATION_SEED_SLOT_IDS)
            ]
            or aggregation_counts != expected_aggregation_counts
            or aggregation_repeated != _REPEATED_MEASURE_SEMANTICS
            or aggregation_policy != _AGGREGATION_APPLICATION_POLICY
            or aggregation.get("numeric_seed_values_present") is not False
            or aggregation.get("aggregation_applied_to_result") is not False
            or aggregation.get("result_present") is not False
            or aggregation.get("d7_state") != "not_run"
            or aggregation.get("d8_state") != "not_run"
            or aggregation_authority != dict(sorted(_AUTHORITY.items()))
        ):
            raise QualificationContractError(
                "D7 C1 aggregation state, authority, or joins differ"
            )
        reviewed_historical = review_contract.get("historical_proposal")
        reviewed_successor = review_contract.get("successor_bindings")
        reviewed_rule = review_contract.get("declared_fulfillment_rule")
        reviewed_authority = review_contract.get("authority")
        if not all(
            isinstance(value, Mapping)
            for value in (
                reviewed_historical,
                reviewed_successor,
                reviewed_rule,
            )
        ) or not isinstance(reviewed_historical.get("body"), Mapping):
            raise QualificationContractError(
                "D7 C1 successor review-contract records are malformed"
            )
        _exact_keys(
            reviewed_historical,
            {
                "schema_version",
                "canonical_sha256",
                "status",
                "body",
                "historical_proposal_mutated",
                "historical_d6_reinterpreted",
            },
            label="D7 C1 historical rebinding proposal",
        )
        _exact_keys(
            reviewed_successor,
            {
                "stable_seed_free_design_sha256",
                "construction_diversity_review_sha256",
                "implementation_registry_sha256",
                "aggregation_application_sha256",
                "source_set_manifest_sha256",
            },
            label="D7 C1 successor review bindings",
        )
        _exact_keys(
            reviewed_rule,
            set(_SUCCESSOR_FULFILLMENT_RULE),
            label="D7 C1 successor fulfillment rule",
        )
        historical_body = reviewed_historical["body"]
        _exact_keys(
            historical_body,
            {
                "schema_version",
                "amendment_id",
                "status",
                "record_scope",
                "claim_ceiling",
                "parent_d6",
                "parent_protocol",
                "seed_free_design",
                "historical_d6",
                "exact_carry_forward",
                "structural_rebinding",
                "mapping_rules",
                "deferred",
                "seed_and_execution",
                "canonical_artifact_published",
                "d7_successor_admission_complete",
                "d7_state",
                "d8_state",
                "authority",
            },
            label="D7 C1 historical rebinding body",
        )
        historical_design = _mapping(
            historical_body["seed_free_design"],
            label="D7 C1 historical seed-free design",
        )
        historical_d6 = _mapping(
            historical_body["historical_d6"],
            label="D7 C1 historical D6 state",
        )
        exact_carry = _mapping(
            historical_body["exact_carry_forward"],
            label="D7 C1 historical exact carry-forward",
        )
        structural_rebinding = _mapping(
            historical_body["structural_rebinding"],
            label="D7 C1 historical structural rebinding",
        )
        mapping_rules = _mapping(
            historical_body["mapping_rules"],
            label="D7 C1 historical mapping rules",
        )
        historical_deferred = _mapping(
            historical_body["deferred"],
            label="D7 C1 historical deferred obligations",
        )
        seed_and_execution = _mapping(
            historical_body["seed_and_execution"],
            label="D7 C1 historical seed and execution state",
        )
        _exact_keys(
            historical_design,
            {
                "schema_version",
                "design_schema_version",
                "draft_id",
                "canonical_sha256",
                "byte_count",
                "manifest_compatibility_sha256",
                "factory_reconstruction_required",
                "canonical_artifact_published",
            },
            label="D7 C1 historical seed-free design",
        )
        _exact_keys(
            historical_d6,
            {
                "admission_spec_id",
                "admission_spec_sha256",
                "decision_bytes_mutated",
                "admission_bytes_mutated",
                "historical_admission_reinterpreted",
                "d6_admission_spec_satisfied",
                "exact_parent_cells_manifest_satisfied",
                "exact_parent_stress_manifest_satisfied",
            },
            label="D7 C1 historical D6 state",
        )
        _exact_keys(
            exact_carry,
            {
                "schema_version",
                "parent_graph_axes_sha256",
                "successor_graph_axes_sha256",
                "graph_axes_exact_match",
                "parent_thresholds_sha256",
                "successor_thresholds_sha256",
                "thresholds_exact_match",
                "required_surrogate_estimator_id",
                "required_surrogate_trivialization_id",
                "required_case_semantics",
                "required_core_and_loop_separation",
                "selection_evidence_disjointness_required",
                "policy_override_allowed",
                "post_selection_exclusion_allowed",
            },
            label="D7 C1 historical exact carry-forward",
        )
        _exact_keys(
            structural_rebinding,
            {
                "schema_version",
                "parent_cells_manifest_sha256",
                "successor_cells_manifest_sha256",
                "cells_exact_match",
                "parent_stress_manifest_sha256",
                "successor_stress_manifest_sha256",
                "stress_exact_match",
                "structural_projection_schema_version",
                "parent_structural_projection_sha256",
                "successor_structural_projection_sha256",
                "structural_projection_match",
                "selection_identity_reuse_allowed",
                "successor_fulfillment_rule_encoded",
                "successor_fulfillment_rule_reviewed",
                "successor_fulfillment_rule_published",
                "effective_for_admission",
                "rebinding_satisfies_historical_exact_hashes",
                "manifest_compatibility_sha256",
            },
            label="D7 C1 historical structural rebinding",
        )
        _exact_keys(
            mapping_rules,
            {
                "parent_seed_identity",
                "successor_seed_identity",
                "seed_mapping",
                "case_mapping",
                "numeric_parent_seed_values_retained",
                "mapping_is_admission_or_execution_authority",
            },
            label="D7 C1 historical mapping rules",
        )
        _exact_keys(
            historical_deferred,
            {
                "schema_version",
                "construction_diversity_reviewed",
                "source_closure_verified",
                "d7_implementation_registry_bound",
                "d7_aggregation_application_bound",
                "family_admitted",
                "full_design_frozen",
                "terminal_schema_and_writer_present",
                "parent_selection_implementation_registry_sha256",
                "parent_locked_aggregation_sha256",
            },
            label="D7 C1 historical deferred obligations",
        )
        _exact_keys(
            seed_and_execution,
            {
                "concrete_seed_inventory_present",
                "seed_inventory_frozen",
                "confirmation_values_accessed",
                "launch_authorized",
                "execution_authorized",
                "result_authorized",
            },
            label="D7 C1 historical seed and execution state",
        )
        expected_case_mapping = [
            {
                "parent_control_semantic": semantic,
                "successor_case_id": case_id,
            }
            for case_id, semantic, _recipe, _core, _loop in (
                SPECTRAL_MOMENT_CASE_REGISTRY
            )
        ]
        expected_seed_mapping = [
            {
                "parent_seed_ordinal": index,
                "successor_seed_slot_id": slot_id,
            }
            for index, slot_id in enumerate(D7_CONFIRMATION_SEED_SLOT_IDS)
        ]
        expected_exact_carry = {
            "schema_version": D7_EXACT_CARRY_FORWARD_SCHEMA_VERSION,
            "parent_graph_axes_sha256": stable_invariants["graph_axes_sha256"],
            "successor_graph_axes_sha256": (
                stable_invariants["graph_axes_sha256"]
            ),
            "graph_axes_exact_match": True,
            "parent_thresholds_sha256": stable_invariants["thresholds_sha256"],
            "successor_thresholds_sha256": (
                stable_invariants["thresholds_sha256"]
            ),
            "thresholds_exact_match": True,
            "required_surrogate_estimator_id": (
                stable_parent_d6["required_surrogate_estimator_id"]
            ),
            "required_surrogate_trivialization_id": (
                stable_parent_d6["required_surrogate_trivialization_id"]
            ),
            "required_case_semantics": list(
                SPECTRAL_MOMENT_REQUIRED_CASE_SEMANTICS
            ),
            "required_core_and_loop_separation": True,
            "selection_evidence_disjointness_required": True,
            "policy_override_allowed": False,
            "post_selection_exclusion_allowed": False,
        }
        expected_structural_rebinding = {
            "schema_version": D7_STRUCTURAL_MANIFEST_REBINDING_SCHEMA_VERSION,
            "parent_cells_manifest_sha256": (
                stable_parent["required_cells_manifest_sha256"]
            ),
            "successor_cells_manifest_sha256": (
                stable_invariants["successor_cells_sha256"]
            ),
            "cells_exact_match": False,
            "parent_stress_manifest_sha256": (
                stable_parent["required_stress_strata_sha256"]
            ),
            "successor_stress_manifest_sha256": (
                stable_invariants["successor_stress_sha256"]
            ),
            "stress_exact_match": False,
            "structural_projection_schema_version": (
                D7_STRUCTURAL_PROJECTION_SCHEMA_VERSION
            ),
            "parent_structural_projection_sha256": (
                stable_invariants["structural_projection_sha256"]
            ),
            "successor_structural_projection_sha256": (
                stable_invariants["structural_projection_sha256"]
            ),
            "structural_projection_match": True,
            "selection_identity_reuse_allowed": False,
            "successor_fulfillment_rule_encoded": True,
            "successor_fulfillment_rule_reviewed": False,
            "successor_fulfillment_rule_published": False,
            "effective_for_admission": False,
            "rebinding_satisfies_historical_exact_hashes": False,
            "manifest_compatibility_sha256": canonical_json_sha256(
                manifest_compatibility
            ),
        }
        expected_mapping_rules = {
            "parent_seed_identity": "canonical-parent-selection-seed-ordinal",
            "successor_seed_identity": "confirmation-seed-slot-index",
            "seed_mapping": expected_seed_mapping,
            "case_mapping": expected_case_mapping,
            "numeric_parent_seed_values_retained": False,
            "mapping_is_admission_or_execution_authority": False,
        }
        expected_historical_deferred = {
            "schema_version": D7_DEFERRED_SUCCESSOR_OBLIGATIONS_SCHEMA_VERSION,
            "construction_diversity_reviewed": False,
            "source_closure_verified": False,
            "d7_implementation_registry_bound": False,
            "d7_aggregation_application_bound": False,
            "family_admitted": False,
            "full_design_frozen": False,
            "terminal_schema_and_writer_present": False,
            "parent_selection_implementation_registry_sha256": (
                stable_parent["selection_implementation_registry_sha256"]
            ),
            "parent_locked_aggregation_sha256": (
                stable_parent["locked_aggregation_sha256"]
            ),
        }
        expected_seed_and_execution = {
            "concrete_seed_inventory_present": False,
            "seed_inventory_frozen": False,
            "confirmation_values_accessed": False,
            "launch_authorized": False,
            "execution_authorized": False,
            "result_authorized": False,
        }
        for value, expected, label in (
            (
                reviewed_rule,
                _SUCCESSOR_FULFILLMENT_RULE,
                "D7 C1 successor fulfillment rule",
            ),
            (
                reviewed_authority,
                dict(sorted(_AUTHORITY.items())),
                "D7 C1 successor review authority",
            ),
            (
                historical_body.get("authority"),
                dict(sorted(_EMBEDDED_DRAFT_AUTHORITY.items())),
                "D7 C1 historical proposal authority",
            ),
            (
                exact_carry,
                expected_exact_carry,
                "D7 C1 historical exact carry-forward",
            ),
            (
                structural_rebinding,
                expected_structural_rebinding,
                "D7 C1 historical structural rebinding",
            ),
            (
                mapping_rules,
                expected_mapping_rules,
                "D7 C1 historical mapping rules",
            ),
            (
                historical_deferred,
                expected_historical_deferred,
                "D7 C1 historical deferred obligations",
            ),
            (
                seed_and_execution,
                expected_seed_and_execution,
                "D7 C1 historical seed and execution state",
            ),
        ):
            _require_exact_json_value(value, expected, label=label)
        if (
            review_contract.get("review_contract_id")
            != "d7-successor-rebinding-review-contract-v0-1"
            or review_contract.get("status")
            != "successor-rebinding-review-contract-encoded"
            or reviewed_historical.get("schema_version")
            != D6_D7_STRUCTURAL_REBINDING_AMENDMENT_SCHEMA_VERSION
            or reviewed_historical.get("canonical_sha256")
            != canonical_json_sha256(historical_body)
            or reviewed_historical.get("canonical_sha256")
            != root_parent["historical_rebinding_proposal_sha256"]
            or reviewed_historical.get("status")
            != historical_body["status"]
            or reviewed_historical.get("historical_proposal_mutated") is not False
            or reviewed_historical.get("historical_d6_reinterpreted") is not False
            or reviewed_successor.get("stable_seed_free_design_sha256")
            != observed_hashes["seed_free_execution_design"]
            or reviewed_successor.get("construction_diversity_review_sha256")
            != observed_hashes["construction_diversity_review"]
            or reviewed_successor.get("implementation_registry_sha256")
            != observed_hashes["implementation_registry"]
            or reviewed_successor.get("aggregation_application_sha256")
            != observed_hashes["aggregation_application"]
            or reviewed_successor.get("source_set_manifest_sha256")
            != observed_hashes["source_set_manifest"]
            or reviewed_rule != _SUCCESSOR_FULFILLMENT_RULE
            or review_contract.get("review_contract_encoded") is not True
            or review_contract.get("encoded_in_c1_candidate") is not True
            or review_contract.get("repository_review_attestation_embedded")
            is not False
            or review_contract.get("effective_for_admission") is not False
            or review_contract.get("family_admitted") is not False
            or review_contract.get("source_closure_verified") is not False
            or review_contract.get("official_seed_inventory_present") is not False
            or review_contract.get("confirmation_values_accessed") is not False
            or review_contract.get("historical_d6_exact_admission_satisfied")
            is not False
            or review_contract.get("d7_state") != "not_run"
            or review_contract.get("d8_state") != "not_run"
            or reviewed_authority != dict(sorted(_AUTHORITY.items()))
            or historical_body.get("schema_version")
            != D6_D7_STRUCTURAL_REBINDING_AMENDMENT_SCHEMA_VERSION
            or historical_body.get("amendment_id")
            != "d6-v0-1-to-d7-spectral-moment-structural-rebinding-v0-1"
            or historical_body.get("status")
            != "structural-rebinding-proposal-encoded-not-reviewed-or-published"
            or historical_body.get("record_scope")
            != "d7-spectral-moment-cells-and-stress-only"
            or historical_body.get("claim_ceiling") != "level_0"
            or historical_body.get("parent_d6") != stable_parent_d6
            or historical_body.get("parent_protocol") != stable_parent
            or historical_body.get("canonical_artifact_published") is not False
            or historical_body.get("d7_successor_admission_complete") is not False
            or historical_body.get("d7_state") != "not_run"
            or historical_body.get("d8_state") != "not_run"
            or historical_body.get("authority")
            != dict(sorted(_EMBEDDED_DRAFT_AUTHORITY.items()))
            or historical_design.get("schema_version")
            != D7_SEED_FREE_DESIGN_IDENTITY_SCHEMA_VERSION
            or historical_design.get("design_schema_version")
            != D7_CONFIRMATION_EXECUTION_DRAFT_SCHEMA_VERSION
            or historical_design.get("draft_id")
            != stable["source_draft_id"]
            or historical_design.get("canonical_sha256")
            != root_parent["source_draft_sha256"]
            or type(historical_design.get("byte_count")) is not int
            or int(historical_design["byte_count"]) <= 0
            or historical_design.get("byte_count")
            != len(canonical_json_bytes(stable_source_draft))
            or historical_design.get("manifest_compatibility_sha256")
            != canonical_json_sha256(manifest_compatibility)
            or historical_design.get("factory_reconstruction_required") is not True
            or historical_design.get("canonical_artifact_published") is not False
            or historical_d6.get("admission_spec_id")
            != stable_parent_d6["admission_spec_id"]
            or historical_d6.get("admission_spec_sha256")
            != root_parent["d6_admission_spec_sha256"]
            or any(
                historical_d6.get(name) is not False
                for name in (
                    "decision_bytes_mutated",
                    "admission_bytes_mutated",
                    "historical_admission_reinterpreted",
                    "d6_admission_spec_satisfied",
                    "exact_parent_cells_manifest_satisfied",
                    "exact_parent_stress_manifest_satisfied",
                )
            )
            or exact_carry
            != {
                "schema_version": D7_EXACT_CARRY_FORWARD_SCHEMA_VERSION,
                "parent_graph_axes_sha256": (
                    stable_invariants["graph_axes_sha256"]
                ),
                "successor_graph_axes_sha256": (
                    stable_invariants["graph_axes_sha256"]
                ),
                "graph_axes_exact_match": True,
                "parent_thresholds_sha256": (
                    stable_invariants["thresholds_sha256"]
                ),
                "successor_thresholds_sha256": (
                    stable_invariants["thresholds_sha256"]
                ),
                "thresholds_exact_match": True,
                "required_surrogate_estimator_id": (
                    stable_parent_d6["required_surrogate_estimator_id"]
                ),
                "required_surrogate_trivialization_id": (
                    stable_parent_d6["required_surrogate_trivialization_id"]
                ),
                "required_case_semantics": list(
                    SPECTRAL_MOMENT_REQUIRED_CASE_SEMANTICS
                ),
                "required_core_and_loop_separation": True,
                "selection_evidence_disjointness_required": True,
                "policy_override_allowed": False,
                "post_selection_exclusion_allowed": False,
            }
            or structural_rebinding
            != {
                "schema_version": D7_STRUCTURAL_MANIFEST_REBINDING_SCHEMA_VERSION,
                "parent_cells_manifest_sha256": (
                    stable_parent["required_cells_manifest_sha256"]
                ),
                "successor_cells_manifest_sha256": (
                    stable_invariants["successor_cells_sha256"]
                ),
                "cells_exact_match": False,
                "parent_stress_manifest_sha256": (
                    stable_parent["required_stress_strata_sha256"]
                ),
                "successor_stress_manifest_sha256": (
                    stable_invariants["successor_stress_sha256"]
                ),
                "stress_exact_match": False,
                "structural_projection_schema_version": (
                    D7_STRUCTURAL_PROJECTION_SCHEMA_VERSION
                ),
                "parent_structural_projection_sha256": (
                    stable_invariants["structural_projection_sha256"]
                ),
                "successor_structural_projection_sha256": (
                    stable_invariants["structural_projection_sha256"]
                ),
                "structural_projection_match": True,
                "selection_identity_reuse_allowed": False,
                "successor_fulfillment_rule_encoded": True,
                "successor_fulfillment_rule_reviewed": False,
                "successor_fulfillment_rule_published": False,
                "effective_for_admission": False,
                "rebinding_satisfies_historical_exact_hashes": False,
                "manifest_compatibility_sha256": canonical_json_sha256(
                    manifest_compatibility
                ),
            }
            or mapping_rules
            != {
                "parent_seed_identity": (
                    "canonical-parent-selection-seed-ordinal"
                ),
                "successor_seed_identity": "confirmation-seed-slot-index",
                "seed_mapping": expected_seed_mapping,
                "case_mapping": expected_case_mapping,
                "numeric_parent_seed_values_retained": False,
                "mapping_is_admission_or_execution_authority": False,
            }
            or historical_deferred
            != {
                "schema_version": D7_DEFERRED_SUCCESSOR_OBLIGATIONS_SCHEMA_VERSION,
                "construction_diversity_reviewed": False,
                "source_closure_verified": False,
                "d7_implementation_registry_bound": False,
                "d7_aggregation_application_bound": False,
                "family_admitted": False,
                "full_design_frozen": False,
                "terminal_schema_and_writer_present": False,
                "parent_selection_implementation_registry_sha256": (
                    stable_parent["selection_implementation_registry_sha256"]
                ),
                "parent_locked_aggregation_sha256": (
                    stable_parent["locked_aggregation_sha256"]
                ),
            }
            or seed_and_execution
            != {
                "concrete_seed_inventory_present": False,
                "seed_inventory_frozen": False,
                "confirmation_values_accessed": False,
                "launch_authorized": False,
                "execution_authorized": False,
                "result_authorized": False,
            }
        ):
            raise QualificationContractError(
                "D7 C1 successor rebinding review contract differs"
            )
        chronology = document["chronology"]
        if (
            not isinstance(chronology, Mapping)
            or chronology != _c1_chronology_document()
        ):
            raise QualificationContractError(
                "D7 C1 artifact knowledge or ordering requirements differ"
            )

    @classmethod
    def from_canonical_bytes(
        cls,
        source: bytes,
        *,
        expected_sha256: str,
    ) -> D7C1SeedFreeSourceSet:
        """Validate the self-contained C1 envelope without current-source replay."""

        expected = require_sha256(expected_sha256, label="expected_sha256")
        if sha256_bytes(source) != expected:
            raise QualificationContractError(
                "D7 C1 seed-free source-set SHA-256 differs"
            )
        return cls(
            _factory_token=_BUNDLE_FACTORY_TOKEN,
            canonical_bytes=source,
        )

    @property
    def canonical_bytes(self) -> bytes:
        return self._canonical_bytes

    @property
    def canonical_sha256(self) -> str:
        return sha256_bytes(self._canonical_bytes)

    def to_dict(self) -> dict[str, object]:
        document = parse_canonical_json(
            self._canonical_bytes,
            label="D7 C1 seed-free source set",
        )
        if not isinstance(document, Mapping):
            raise TypeError("validated C1 document must remain a mapping")
        return dict(document)


@dataclass(frozen=True, slots=True)
class PublishedD7C1SeedFreeSourceSet:
    """Filesystem publication receipt; a Git C1 commit is still required."""

    bundle: D7C1SeedFreeSourceSet
    identity: PersistedQualificationIdentity
    committed_c1_verified: bool = False
    source_closure_verified: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.bundle, D7C1SeedFreeSourceSet):
            raise TypeError("bundle must be D7C1SeedFreeSourceSet")
        if not isinstance(self.identity, PersistedQualificationIdentity):
            raise TypeError("identity must be PersistedQualificationIdentity")
        if (
            self.identity.source_sha256 != self.bundle.canonical_sha256
            or self.identity.canonical_sha256 != self.bundle.canonical_sha256
            or self.identity.byte_count != len(self.bundle.canonical_bytes)
        ):
            raise QualificationContractError(
                "published C1 identity differs from canonical bundle"
            )
        if self.committed_c1_verified is not False:
            raise QualificationContractError(
                "C1 publication cannot attest its future Git commit"
            )
        if self.source_closure_verified is not False:
            raise QualificationContractError(
                "C1 publication cannot attest the future C2 closure"
            )


def build_d7_c1_seed_free_source_set(
    *,
    loaded_d6: LoadedScopeLimitedD6Decision,
    parent_protocol: LoadedQualificationProtocol,
    repository_root: str | Path,
) -> D7C1SeedFreeSourceSet:
    """Build the choice-free C1 candidate from typed parents and local source."""

    d6 = _loaded_d6(loaded_d6)
    parent = _loaded_parent(parent_protocol)
    root = _repository_root(repository_root)
    design = build_seed_free_d7_confirmation_execution_design(
        loaded_d6=d6,
        parent_protocol=parent,
    )
    proposal = build_d6_d7_structural_rebinding_amendment(
        loaded_d6=d6,
        parent_protocol=parent,
        seed_free_design=design,
    )
    source_set = _source_set_document(root)
    source_set_sha256 = canonical_json_sha256(source_set)
    stable_design = _stable_design_document(design)
    stable_design_sha256 = canonical_json_sha256(stable_design)
    construction_review = _construction_review_document(
        loaded_d6=d6,
        parent=parent,
        design=design,
        stable_design_sha256=stable_design_sha256,
        source_set_sha256=source_set_sha256,
        root=root,
    )
    construction_review_sha256 = canonical_json_sha256(construction_review)
    implementation_registry = _implementation_registry_document(
        loaded_d6=d6,
        parent=parent,
        design=design,
        stable_design_sha256=stable_design_sha256,
        construction_review_sha256=construction_review_sha256,
        source_set_sha256=source_set_sha256,
    )
    implementation_registry_sha256 = canonical_json_sha256(
        implementation_registry
    )
    aggregation_application = _aggregation_application_document(
        loaded_d6=d6,
        parent=parent,
        design=design,
        stable_design_sha256=stable_design_sha256,
        implementation_registry_sha256=implementation_registry_sha256,
    )
    aggregation_application_sha256 = canonical_json_sha256(
        aggregation_application
    )
    review_contract = _successor_rebinding_review_contract_document(
        proposal=proposal,
        stable_design_sha256=stable_design_sha256,
        construction_review_sha256=construction_review_sha256,
        implementation_registry_sha256=implementation_registry_sha256,
        aggregation_application_sha256=aggregation_application_sha256,
        source_set_sha256=source_set_sha256,
    )
    components = {
        "aggregation_application": _component(aggregation_application),
        "construction_diversity_review": _component(construction_review),
        "implementation_registry": _component(implementation_registry),
        "successor_rebinding_review_contract": _component(review_contract),
        "seed_free_execution_design": _component(stable_design),
        "source_set_manifest": _component(source_set),
    }
    component_hashes = {
        key: str(value["canonical_sha256"])
        for key, value in sorted(components.items())
    }
    document = {
        "schema_version": D7_C1_SEED_FREE_SOURCE_SET_SCHEMA_VERSION,
        "bundle_id": D7C1SeedFreeSourceSet.bundle_id,
        "status": "seed-free-source-set-candidate",
        "claim_ceiling": "level_0",
        "repository_path": D7_C1_BUNDLE_REPOSITORY_PATH,
        "parent_bindings": {
            "d6_decision_sha256": d6.identity.canonical_sha256,
            "d6_admission_spec_sha256": (
                d6.decision.confirmation_admission_spec.canonical_sha256
            ),
            "parent_protocol_sha256": parent.canonical_sha256,
            "source_draft_sha256": design.canonical_sha256,
            "historical_rebinding_proposal_sha256": proposal.canonical_sha256,
        },
        "component_order": sorted(components),
        "component_hashes": component_hashes,
        "component_set_sha256": canonical_json_sha256(component_hashes),
        "components": dict(sorted(components.items())),
        "chronology": _c1_chronology_document(),
        "deferred": dict(_C1_DEFERRED),
        "d7_state": "not_run",
        "d8_state": "not_run",
        "authority": dict(sorted(_AUTHORITY.items())),
    }
    canonical = canonical_json_bytes(document)
    return D7C1SeedFreeSourceSet(
        _factory_token=_BUNDLE_FACTORY_TOKEN,
        canonical_bytes=canonical,
    )


def load_d7_c1_seed_free_source_set(
    path: str | Path,
    *,
    expected_source_sha256: str,
    expected_canonical_sha256: str,
    loaded_d6: LoadedScopeLimitedD6Decision,
    parent_protocol: LoadedQualificationProtocol,
    repository_root: str | Path,
) -> D7C1SeedFreeSourceSet:
    """Strictly reload C1 by whole-document authoritative reconstruction."""

    expected_source = require_sha256(
        expected_source_sha256,
        label="expected_source_sha256",
    )
    expected_canonical = require_sha256(
        expected_canonical_sha256,
        label="expected_canonical_sha256",
    )
    source_path = Path(os.path.abspath(path))
    if source_path.is_symlink() or not source_path.is_file():
        raise QualificationContractError(
            "C1 seed-free source set must be one regular file"
        )
    with source_path.open("rb") as handle:
        source = handle.read(MAX_D7_C1_SEED_FREE_SOURCE_SET_BYTES + 1)
    if not source or len(source) > MAX_D7_C1_SEED_FREE_SOURCE_SET_BYTES:
        raise QualificationContractError(
            "C1 seed-free source-set bytes are empty or exceed the cap"
        )
    source_sha256 = sha256_bytes(source)
    if source_sha256 != expected_source:
        raise QualificationContractError(
            "C1 seed-free source-set source SHA-256 differs"
        )
    rebuilt = build_d7_c1_seed_free_source_set(
        loaded_d6=loaded_d6,
        parent_protocol=parent_protocol,
        repository_root=repository_root,
    )
    if rebuilt.canonical_sha256 != expected_canonical:
        raise QualificationContractError(
            "C1 seed-free source-set canonical SHA-256 differs"
        )
    try:
        document = parse_canonical_json(
            source,
            label="D7 C1 seed-free source set",
        )
    except CanonicalJsonError as error:
        raise QualificationContractError(str(error)) from error
    if document != rebuilt.to_dict() or source != rebuilt.canonical_bytes:
        raise QualificationContractError(
            "C1 seed-free source set differs from authoritative reconstruction"
        )
    return rebuilt


def write_d7_c1_seed_free_source_set(
    path: str | Path,
    bundle: D7C1SeedFreeSourceSet,
) -> PublishedD7C1SeedFreeSourceSet:
    """Atomically publish one C1 candidate without overwrite."""

    if not isinstance(bundle, D7C1SeedFreeSourceSet):
        raise TypeError("bundle must be D7C1SeedFreeSourceSet")
    destination = Path(os.path.abspath(path))
    identity = _atomic_write_no_overwrite(
        destination,
        bundle.canonical_bytes,
        maximum_bytes=MAX_D7_C1_SEED_FREE_SOURCE_SET_BYTES,
        label="D7 C1 seed-free source set",
    )
    return PublishedD7C1SeedFreeSourceSet(
        bundle=bundle,
        identity=identity,
    )


__all__ = [
    "D7_C1_BUNDLE_REPOSITORY_PATH",
    "D7_C1_SEED_FREE_SOURCE_SET_SCHEMA_VERSION",
    "D7_C1_SOURCE_SET_MANIFEST_SCHEMA_VERSION",
    "D7_C1_STABLE_DESIGN_SCHEMA_VERSION",
    "D7_C2_RECEIPT_REPOSITORY_PATH",
    "D7_CONFIRMATION_AGGREGATION_APPLICATION_SCHEMA_VERSION",
    "D7_CONFIRMATION_EVALUATION_DESIGN_SCHEMA_VERSION",
    "D7_CONFIRMATION_IMPLEMENTATION_REGISTRY_SCHEMA_VERSION",
    "D7_CONSTRUCTION_DIVERSITY_REVIEW_SCHEMA_VERSION",
    "D7_LOCKED_CONFIRMATION_AGGREGATION_SCHEMA_VERSION",
    "D7_SUCCESSOR_REBINDING_REVIEW_CONTRACT_SCHEMA_VERSION",
    "MAX_D7_C1_SEED_FREE_SOURCE_SET_BYTES",
    "MAX_D7_C1_SOURCE_FILE_COUNT",
    "MAX_D7_C1_SOURCE_MEMBER_BYTES",
    "MAX_D7_C1_SOURCE_SET_TOTAL_BYTES",
    "D7C1SeedFreeSourceSet",
    "PublishedD7C1SeedFreeSourceSet",
    "build_d7_c1_seed_free_source_set",
    "load_d7_c1_seed_free_source_set",
    "write_d7_c1_seed_free_source_set",
]
