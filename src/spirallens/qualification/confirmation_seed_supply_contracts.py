"""Choice-free, non-authorizing contracts for the future D7 item-22 transaction.

This deep-internal module freezes one canonical contract specification for the
future seed-supply transaction.  It is deliberately not operational: it accepts
no seed, supplier callback, claim input, readiness snapshot, target instance, or
filesystem destination, and it publishes nothing.  Its sole repository loader
strictly reloads the complete historical item-21 chain before returning an
in-memory foundation.

The historical reviewed family-admission artifact may be recorded as evidence
on that loaded foundation.  It is kept separate from the closed all-false
authority map and does not authorize a claim, supplier invocation, publication,
launch, execution, or scientific conclusion.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass as _dataclass
from pathlib import Path
from typing import ClassVar, NoReturn

from spirallens.core.canonical import (
    CanonicalJsonError,
    canonical_json_bytes as _canonical_json_bytes,
    parse_canonical_json as _parse_canonical_json,
    sha256_bytes as _sha256_bytes,
)

from . import confirmation_preseed_authority as item21
from .common import QualificationContractError, require_sha256 as _require_sha256

__all__: tuple[str, ...] = ()

D7_ITEM22_SEED_SUPPLY_TRANSACTION_CONTRACT_SCHEMA_VERSION = (
    "spirallens.d7-item22-seed-supply-transaction-contract-spec.v0.1"
)
MAX_D7_ITEM22_SEED_SUPPLY_TRANSACTION_CONTRACT_BYTES = 256 * 1024

D7_ITEM22_DIRECTORY_REPOSITORY_PATH = (
    "experiments/qualification/d7_spectral_moment_confirmation_v0_1"
)
D7_ITEM22_CURRENT_SOURCE_RUNTIME_REANCHOR_REPOSITORY_PATH = (
    f"{D7_ITEM22_DIRECTORY_REPOSITORY_PATH}/item22-current-source-runtime-reanchor.json"
)
D7_ITEM22_SEED_SUPPLY_DIRECTORY_REPOSITORY_PATH = (
    f"{D7_ITEM22_DIRECTORY_REPOSITORY_PATH}/item22-seed-supply"
)
D7_ITEM22_EXCLUSIVE_SEED_SUPPLY_CLAIM_REPOSITORY_PATH = (
    f"{D7_ITEM22_SEED_SUPPLY_DIRECTORY_REPOSITORY_PATH}/"
    "exclusive-seed-supply-claim.json"
)
D7_ITEM22_ATOMIC_TARGET_DIRECTORY_REPOSITORY_PATH = (
    f"{D7_ITEM22_SEED_SUPPLY_DIRECTORY_REPOSITORY_PATH}/published-target"
)
D7_ITEM22_SINGLE_SUPPLIER_INVOCATION_REPOSITORY_PATH = (
    f"{D7_ITEM22_ATOMIC_TARGET_DIRECTORY_REPOSITORY_PATH}/"
    "single-supplier-invocation.json"
)
D7_ITEM22_FULL_DESIGN_FREEZE_REPOSITORY_PATH = (
    f"{D7_ITEM22_SEED_SUPPLY_DIRECTORY_REPOSITORY_PATH}/full-design-freeze.json"
)
D7_ITEM22_SEED_SUPPLY_ABORT_EVIDENCE_REPOSITORY_PATH = (
    f"{D7_ITEM22_SEED_SUPPLY_DIRECTORY_REPOSITORY_PATH}/seed-supply-abort.json"
)
D7_ITEM22_FUTURE_LAUNCH_DESCRIPTOR_REPOSITORY_PATH = (
    f"{D7_ITEM22_DIRECTORY_REPOSITORY_PATH}/launch.json"
)

D7_ITEM22_ATOMIC_TARGET_MEMBER_LAYOUT = (
    ("official-seed-inventory", "official-seed-inventory.json"),
    ("full-inventory", "full-inventory.json"),
    ("full-design", "full-design.json"),
    ("replay-target", "replay-target.json"),
    ("single-supplier-invocation", "single-supplier-invocation.json"),
    ("transaction-manifest", "transaction-manifest.json"),
)

_ATOMIC_PUBLICATION_CHRONOLOGY_SUBJECT_ROLES = (
    "official-seed-inventory",
    "full-design",
    "replay-target",
)

_ITEM21_ARTIFACT_PINS = (
    (
        "execution-source-runtime-receipt",
        (
            "experiments/qualification/"
            "d7_spectral_moment_confirmation_v0_1/"
            "item21-execution-source-runtime-receipt.json"
        ),
        "spirallens.d7-exact-current-execution-source-runtime-receipt.v0.1",
        "b725e911931b7d9f8c3016c025c29d1a44c55374c63aa7879155411b6ee2f07d",
        33_940,
        "d558b91bd8f8250052705794ba8eb39b55eb1f45",
    ),
    (
        "seed-free-readiness",
        (
            "experiments/qualification/"
            "d7_spectral_moment_confirmation_v0_1/"
            "item21-seed-free-readiness.json"
        ),
        "spirallens.d7-seed-free-readiness.v0.1",
        "b96c54e99850af73b1a938354ddc0b247918c75a13d456e11273b79e4c935bb8",
        6_591,
        "a3651c38f1085e551c6696635f1f3ccfc023da7d",
    ),
    (
        "family-admission-receipt",
        (
            "experiments/qualification/"
            "d7_spectral_moment_confirmation_v0_1/"
            "item21-reviewed-family-admission.json"
        ),
        "spirallens.d7-reviewed-successor-family-admission.v0.1",
        "4fa4e7bf70cdf4ef9f14c27b3a036279ce3d83951c376812c1294697301d863c",
        5_304,
        "9b5e1f4957bd353a942493564a7b408ff15874b9",
    ),
)

_TRANSITION_ORDER = (
    "final-lifecycle-result-terminal-runner-code-reviewed",
    "exact-execution-source-runtime-closure",
    "seed-free-readiness",
    "reviewed-family-admission",
    "exclusive-seed-supply-claim",
    "single-supplier-invocation",
    "atomic-seed-bearing-full-design-and-target-publication",
    "committed-full-design-freeze-receipt",
    "launch-intent",
)

_STATE_VOCABULARY = (
    "preclaim",
    "claim-present-publication-absent-nonretryable",
    "seed-supply-aborted-established",
    "publication-complete-unfrozen",
    "full-design-frozen",
    "launch-intent-present",
)

_STATE_OBSERVATION_ROWS = (
    ("preclaim", False, False, False, False, False),
    (
        "claim-present-publication-absent-nonretryable",
        True,
        False,
        False,
        False,
        False,
    ),
    ("seed-supply-aborted-established", True, False, True, False, False),
    ("publication-complete-unfrozen", True, True, False, False, False),
    ("full-design-frozen", True, True, False, True, False),
    ("launch-intent-present", True, True, False, True, True),
)

_CLAIM_KEY_DERIVATION_INPUT_ROLES = (
    "claim-key-domain-separator",
    "claim-key-schema-version",
    "exclusive-claim-repository-path",
    "historical-item21-source-runtime-receipt-binding",
    "historical-item21-seed-free-readiness-binding",
    "historical-item21-family-admission-receipt-binding",
    "reviewed-item22-current-source-runtime-reanchor-binding",
    "seed-supplier-identity-binding",
    "development-seed-exclusion-registry-binding",
    "parent-selection-seed-exclusion-registry-binding",
)

_CLAIM_KEY_PREIMAGE_EXACT_KEYS = (
    "schema_version",
    "domain_separator",
    "exclusive_claim_repository_path",
    "historical_item21_bindings",
    "reviewed_current_source_runtime_reanchor_binding",
    "supplier_identity_binding",
    "development_seed_exclusion_registry_binding",
    "parent_selection_seed_exclusion_registry_binding",
)

_CLAIM_KEY_BINDING_PROJECTION_EXACT_KEYS = (
    "schema_version",
    "artifact_role",
    "artifact_contract_id",
    "canonical_sha256",
    "byte_count",
)

_ATOMIC_TARGET_INTERNAL_BINDING_EDGES = (
    (
        "full-inventory",
        "official_seed_inventory_sha256",
        "official-seed-inventory",
    ),
    (
        "full-design",
        "official_seed_inventory_sha256",
        "official-seed-inventory",
    ),
    ("full-design", "full_inventory_sha256", "full-inventory"),
    (
        "replay-target",
        "official_seed_inventory_binding",
        "official-seed-inventory",
    ),
    (
        "replay-target",
        "full_design_binding.design_binding",
        "full-design",
    ),
    (
        "replay-target",
        "full_design_binding.inventory_binding",
        "full-inventory",
    ),
    (
        "replay-target",
        "full_design_binding.inventory_sha256",
        "full-inventory",
    ),
    (
        "replay-target",
        "full_design_binding.official_seed_inventory_sha256",
        "official-seed-inventory",
    ),
    (
        "single-supplier-invocation",
        "official_seed_inventory_binding",
        "official-seed-inventory",
    ),
)

_AUTHORITY = {
    key: False
    for key in (
        "confirmation_family_admitted",
        "confirmation_values_accessed",
        "d7_execution_authorized",
        "d7_result_produced",
        "d8_execution_authorized",
        "exclusive_seed_supply_claim_authorized",
        "integer_output_authorized",
        "launch_authorized",
        "localized_core_loop_join_established",
        "model_access_authorized",
        "p0_winner_selected",
        "pythia_access_authorized",
        "representation_instrument_advanced",
        "reusable_authorization_capability_present",
        "scientific_claim_eligible",
        "seed_supply_persistence_authorized",
        "semantic_authority",
        "subject_access_authorized",
        "supplier_invocation_authorized",
        "synthetic_qualified",
        "target_publication_authorized",
        "topology_claim_authorized",
    )
}

_SPEC_FACTORY_TOKEN = object()
_FOUNDATION_FACTORY_TOKEN = object()
_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")


def _commit(value: object, *, label: str) -> str:
    if type(value) is not str or _COMMIT_RE.fullmatch(value) is None:
        raise QualificationContractError(f"{label} must be one full Git commit")
    return value


def _artifact_pin_document(
    pin: tuple[str, str, str, str, int, str],
) -> dict[str, object]:
    role, repository_path, schema_version, digest, byte_count, introduction = pin
    return {
        "artifact_role": role,
        "repository_path": repository_path,
        "schema_version": schema_version,
        "canonical_sha256": digest,
        "byte_count": byte_count,
        "introduction_commit": introduction,
    }


def _target_member_document(
    ordinal: int,
    role: str,
    filename: str,
) -> dict[str, object]:
    return {
        "ordinal": ordinal,
        "artifact_role": role,
        "filename": filename,
        "repository_path": (
            f"{D7_ITEM22_ATOMIC_TARGET_DIRECTORY_REPOSITORY_PATH}/{filename}"
        ),
    }


def _contract_document() -> dict[str, object]:
    target_members = [
        _target_member_document(ordinal, role, filename)
        for ordinal, (role, filename) in enumerate(
            D7_ITEM22_ATOMIC_TARGET_MEMBER_LAYOUT
        )
    ]
    return {
        "schema_version": (D7_ITEM22_SEED_SUPPLY_TRANSACTION_CONTRACT_SCHEMA_VERSION),
        "contract_id": "d7-item22-seed-supply-transaction-contract-v0-1",
        "status": "contract-defined-operational-instance-absent",
        "claim_ceiling": "level_0",
        "historical_item21_foundation": {
            "strict_loader": (
                "spirallens.qualification.confirmation_preseed_authority."
                "load_committed_d7_item21_positive_chain"
            ),
            "complete_non_shallow_history_required": True,
            "artifacts": [_artifact_pin_document(pin) for pin in _ITEM21_ARTIFACT_PINS],
            "historical_reload_required_for_loaded_foundation": True,
            "canonical_contract_bytes_alone_prove_historical_reload": False,
            "historical_family_admission_evidence_may_be_recorded_separately": True,
            "historical_family_admission_evidence_is_current_authority": False,
            "current_live_readiness_inherited_from_item21": False,
            "caller_supplied_item21_snapshot_accepted": False,
        },
        "historical_replay_target_contract_refinement": {
            "earlier_source_repository_path": (
                "src/spirallens/qualification/confirmation_replay_contracts.py"
            ),
            "earlier_schema_version": (
                "spirallens.d7-replay-target-contract-spec.v0.1"
            ),
            "earlier_contract_id": "d7-spectral-moment-replay-target-contract-v0-1",
            "earlier_canonical_sha256": (
                "d8387e29601a85df54513669919c591964b8fc99f3c8ec1126d527a854763ffa"
            ),
            "earlier_canonical_byte_count": 6_550,
            "refined_field_path": (
                "seed_supply_chronology_contract."
                "claim_without_target_is_seed_supply_aborted"
            ),
            "earlier_field_value": True,
            "earlier_contract_bytes_are_mutated_by_this_specification": False,
            "this_later_specification_refines_future_item22_operational_semantics": (
                True
            ),
            "refinement_kind": (
                "active-versus-ended-origin-and-durable-evidence-separation"
            ),
            "active_originating_operation_claim_without_target_is_semantic_abort": (
                False
            ),
            "ended_originating_operation_without_target_is_semantic_abort": True,
            "restart_observation_claim_without_target_is_semantic_abort": True,
            "semantic_abort_is_durable_abort_evidence": False,
            "durable_state_without_valid_abort_receipt": (
                "claim-present-publication-absent-nonretryable"
            ),
            "future_item22_operational_code_must_use_refined_semantics": True,
            "earlier_unqualified_phrase_may_authorize_future_behavior": False,
        },
        "fixed_repository_layout": {
            "preclaim_current_source_runtime_reanchor": (
                D7_ITEM22_CURRENT_SOURCE_RUNTIME_REANCHOR_REPOSITORY_PATH
            ),
            "seed_supply_namespace": (D7_ITEM22_SEED_SUPPLY_DIRECTORY_REPOSITORY_PATH),
            "exclusive_claim": (D7_ITEM22_EXCLUSIVE_SEED_SUPPLY_CLAIM_REPOSITORY_PATH),
            "single_supplier_invocation": (
                D7_ITEM22_SINGLE_SUPPLIER_INVOCATION_REPOSITORY_PATH
            ),
            "atomic_target_directory": (
                D7_ITEM22_ATOMIC_TARGET_DIRECTORY_REPOSITORY_PATH
            ),
            "atomic_target_members": target_members,
            "full_design_freeze": (D7_ITEM22_FULL_DESIGN_FREEZE_REPOSITORY_PATH),
            "seed_supply_abort_evidence": (
                D7_ITEM22_SEED_SUPPLY_ABORT_EVIDENCE_REPOSITORY_PATH
            ),
            "future_launch_descriptor": (
                D7_ITEM22_FUTURE_LAUNCH_DESCRIPTOR_REPOSITORY_PATH
            ),
            "reanchor_is_outside_seed_supply_namespace": True,
            "launch_descriptor_is_outside_seed_supply_namespace": True,
            "closed_member_count": len(D7_ITEM22_ATOMIC_TARGET_MEMBER_LAYOUT),
            "unknown_atomic_target_members_allowed": False,
            "alternate_repository_paths_allowed": False,
        },
        "transaction_boundary": {
            "foundation_loader_parameters": ["repository_root"],
            "choice_bearing_parameters_accepted": False,
            "standalone_claim_api_present": False,
            "supplier_callback_accepted": False,
            "seed_values_accepted": False,
            "readiness_snapshot_accepted": False,
            "persistence_performed": False,
            "claim_acquired": False,
            "supplier_invoked": False,
            "atomic_target_published": False,
            "concrete_supplier_identity_present": False,
            "concrete_supplier_identity_mandatory_before_exclusive_claim": True,
            "concrete_exclusive_claim_key_value_present": False,
            "concrete_exclusive_claim_key_value_mandatory_before_exclusive_claim": (
                True
            ),
            "opaque_caller_supplier_binding_sufficient": False,
            "existing_caller_constructible_claim_input_promotable": False,
            "existing_caller_constructible_invocation_input_promotable": False,
        },
        "future_exclusive_claim_key_derivation": {
            "scheme_id": ("d7-item22-exclusive-seed-supply-claim-key-derivation-v0-1"),
            "scheme_schema_version": (
                "spirallens.d7-item22-exclusive-seed-supply-claim-key.v0.1"
            ),
            "domain_separator": (
                "spirallens:d7:item22:exclusive-seed-supply-claim:v0.1"
            ),
            "exclusive_claim_repository_path": (
                D7_ITEM22_EXCLUSIVE_SEED_SUPPLY_CLAIM_REPOSITORY_PATH
            ),
            "digest_algorithm": "sha256",
            "canonical_json_input_required": True,
            "input_roles_in_order": list(_CLAIM_KEY_DERIVATION_INPUT_ROLES),
            "preimage_is_one_exact_top_level_object": True,
            "preimage_exact_keys": list(_CLAIM_KEY_PREIMAGE_EXACT_KEYS),
            "unknown_preimage_fields_allowed": False,
            "alternate_array_or_role_keyed_encoding_allowed": False,
            "historical_item21_bindings_must_equal_exact_pinned_list": True,
            "historical_item21_binding_exact_keys": [
                "artifact_role",
                "repository_path",
                "schema_version",
                "canonical_sha256",
                "byte_count",
                "introduction_commit",
            ],
            "dynamic_binding_projection_schema_version": (
                "spirallens.d7-item22-claim-key-binding-projection.v0.1"
            ),
            "dynamic_binding_projection_exact_keys": list(
                _CLAIM_KEY_BINDING_PROJECTION_EXACT_KEYS
            ),
            "dynamic_binding_roles_by_preimage_field": {
                "reviewed_current_source_runtime_reanchor_binding": (
                    "current-source-runtime-reanchor"
                ),
                "supplier_identity_binding": "seed-supplier-identity",
                "development_seed_exclusion_registry_binding": (
                    "development-seed-exclusion-registry"
                ),
                "parent_selection_seed_exclusion_registry_binding": (
                    "parent-selection-seed-exclusion-registry"
                ),
            },
            "authority_or_provenance_flags_part_of_key": False,
            "historical_item21_bindings": [
                _artifact_pin_document(pin) for pin in _ITEM21_ARTIFACT_PINS
            ],
            "reviewed_reanchor_repository_path": (
                D7_ITEM22_CURRENT_SOURCE_RUNTIME_REANCHOR_REPOSITORY_PATH
            ),
            "supplier_identity_artifact_role": "seed-supplier-identity",
            "development_exclusion_contract_id": (
                "spirallens.d7-development-seed-exclusion.v0.1"
            ),
            "parent_selection_exclusion_contract_id": (
                "spirallens.d7-parent-selection-seed-exclusion.v0.1"
            ),
            "concrete_reanchor_binding_present": False,
            "concrete_supplier_identity_present": False,
            "concrete_claim_key_value_present": False,
            "claim_key_derived_by_this_specification": False,
            "caller_supplied_claim_key_accepted": False,
        },
        "chronology_contract": {
            "ordered_transitions": list(_TRANSITION_ORDER),
            "closed_state_vocabulary": list(_STATE_VOCABULARY),
            "preclaim_reanchor_is_conditional_gate_not_transition": True,
            "applicable_live_check_internal_immediately_before_claim": True,
            "cached_live_check_accepted_from_caller": False,
            "supplier_invocation_must_follow_claim": True,
            "supplier_invocation_count_maximum": 1,
            "durable_pre_call_claim_interval_required": True,
            "durable_claim_waiting_state_is_restart_resumable": False,
            "persisted_claim_alone_authorizes_continuation": False,
            "atomic_target_must_follow_the_single_invocation": True,
            "full_design_freeze_must_follow_atomic_target": True,
            "launch_intent_must_follow_committed_freeze": True,
        },
        "state_transition_contract": {
            "transitions": [
                {
                    "from": "preclaim",
                    "to": "claim-present-publication-absent-nonretryable",
                    "conditions": [
                        "concrete-supplier-identity-verified",
                        "concrete-claim-key-derived",
                        "reviewed-reanchor-live-verified-internally",
                        "exclusive-claim-durably-published-before-supplier-call",
                    ],
                    "originating_operation_only": True,
                },
                {
                    "from": "claim-present-publication-absent-nonretryable",
                    "to": "publication-complete-unfrozen",
                    "conditions": [
                        "same-originating-operation-retains-claim-ownership",
                        "supplier-called-at-most-once-after-durable-claim",
                        "post-call-invocation-receipt-binds-claim-supplier-and-inventory",
                        "six-member-published-target-atomically-visible-no-replace",
                    ],
                    "originating_operation_only": True,
                },
                {
                    "from": "claim-present-publication-absent-nonretryable",
                    "to": "seed-supply-aborted-established",
                    "conditions": [
                        "same-originating-operation-did-not-publish-target",
                        "separate-abort-evidence-durably-published",
                    ],
                    "originating_operation_only": True,
                },
                {
                    "from": "publication-complete-unfrozen",
                    "to": "full-design-frozen",
                    "conditions": [
                        "committed-full-design-freeze-receipt-rejoins-target"
                    ],
                    "originating_operation_only": False,
                },
                {
                    "from": "full-design-frozen",
                    "to": "launch-intent-present",
                    "conditions": ["launch-intent-rejoins-committed-freeze"],
                    "originating_operation_only": False,
                },
            ],
            "restart_entrant_from_claim_state_allowed": False,
            "restart_entrant_may_invoke_supplier": False,
            "claim_state_successor_success_requires_same_originating_operation": True,
            "abort_established_is_terminal": True,
            "abort_established_outgoing_transitions": [],
            "failure_to_persist_abort_restores_retry": False,
            "abort_persistence_failure_before_established_return_retains_state": (
                "claim-present-publication-absent-nonretryable"
            ),
            "post_publication_failure_state": "publication-complete-unfrozen",
            "post_publication_failure_is_seed_supply_abort": False,
            "post_publication_supplier_retry_authorized": False,
            "state_observation_contract": {
                "presence_fields_in_order": [
                    "exclusive_claim_present",
                    "atomic_target_present",
                    "abort_evidence_present",
                    "full_design_freeze_present",
                    "launch_intent_present",
                ],
                "rows": [
                    {
                        "state": state,
                        "exclusive_claim_present": claim,
                        "atomic_target_present": target,
                        "abort_evidence_present": abort,
                        "full_design_freeze_present": freeze,
                        "launch_intent_present": launch,
                    }
                    for state, claim, target, abort, freeze, launch in (
                        _STATE_OBSERVATION_ROWS
                    )
                ],
                "all_present_artifacts_require_valid_canonical_strict_reload": True,
                "unlisted_presence_combination_is_contract_error": True,
                "invalid_or_partial_artifact_is_contract_error": True,
                "claim_missing_with_downstream_artifact_is_contract_error": True,
                "atomic_target_and_abort_evidence_are_mutually_exclusive": True,
                "atomic_target_and_abort_evidence_coexistence_is_contract_error": (
                    True
                ),
                "recovery_precedence_rule_present": False,
                "recovery_contract_error_authorizes_supplier_retry": False,
            },
        },
        "atomic_target_contract": {
            "member_count": len(target_members),
            "member_roles_in_order": [item["artifact_role"] for item in target_members],
            "chronology_publication_subject_roles": list(
                _ATOMIC_PUBLICATION_CHRONOLOGY_SUBJECT_ROLES
            ),
            "durable_members_and_chronology_subjects_are_distinct_surfaces": True,
            "all_members_must_be_canonical": True,
            "all_members_must_be_regular_unaliased_files": True,
            "manifest_binds_every_other_member": True,
            "manifest_may_bind_itself": False,
            "atomic_no_replace_directory_publication_required": True,
            "partial_target_visibility_allowed": False,
            "target_member_replacement_allowed": False,
            "target_publication_retry_allowed": False,
            "exclusive_claim_is_durable_pre_call_reservation": True,
            "single_supplier_invocation_member_is_post_call_evidence": True,
            "single_supplier_invocation_member_binds_claim": True,
            "single_supplier_invocation_member_binds_supplier_identity": True,
            "single_supplier_invocation_member_binds_official_inventory": True,
            "single_supplier_invocation_member_is_inside_atomic_target": True,
            "required_internal_digest_edges": [
                {
                    "subject_role": subject_role,
                    "binding_field": binding_field,
                    "object_role": object_role,
                }
                for subject_role, binding_field, object_role in (
                    _ATOMIC_TARGET_INTERNAL_BINDING_EDGES
                )
            ],
            "all_required_internal_edges_must_rejoin_exact_member_bytes": True,
            "unknown_internal_binding_edges_allowed": False,
            "member_bytes_must_reconstruct_existing_exact_record_contracts": True,
            "reconstruction_must_equal_canonical_member_bytes": True,
            "chronology_subject_bindings_must_equal_member_bytes": True,
            "existing_caller_constructible_records_supply_authority": False,
            "manifest_binds_other_member_digest_and_byte_count": True,
        },
        "durability_contract": {
            "requirements_apply_only_to_future_operational_code": True,
            "seed_supply_namespace_created_before_claim": True,
            "seed_supply_namespace_parent_fsync_after_creation_before_claim": True,
            "claim_file_data_and_metadata_fsync_before_supplier_call": True,
            "claim_parent_directory_fsync_before_supplier_call": True,
            "target_staging_directory_must_share_publication_parent_filesystem": True,
            "each_target_member_data_and_metadata_fsync_before_publication": True,
            "target_staging_directory_fsync_before_publication": True,
            "no_replace_directory_rename_required": True,
            "publication_parent_directory_fsync_before_success_return": True,
            "abort_file_data_and_metadata_fsync_before_established_state": True,
            "abort_parent_directory_fsync_before_established_state": True,
            "abort_established_success_not_returned_before_parent_fsync": True,
            "crash_recovery_uses_exact_state_observation_table": True,
            "invalid_recovery_state_authorizes_supplier_retry": False,
            "crash_recovery_authorizes_supplier_retry": False,
            "power_loss_survival_proved_by_this_specification": False,
            "filesystem_fsync_semantics_authenticated": False,
        },
        "claim_and_abort_contract": {
            "claim_without_atomic_target_state": (
                "claim-present-publication-absent-nonretryable"
            ),
            "claim_without_atomic_target_retry_authorized": False,
            "claim_state_may_be_active_same_origin_or_orphaned": True,
            "active_originating_operation_claim_without_target_is_semantic_abort": (
                False
            ),
            "ended_originating_operation_without_target_is_semantic_abort": True,
            "restart_observation_claim_without_target_is_semantic_abort": True,
            "semantic_seed_supply_abort_is_durable_abort_evidence": False,
            "claim_deletion_authorizes_retry": False,
            "target_absence_proves_supplier_invoked": False,
            "target_absence_proves_supplier_not_invoked": False,
            "claim_without_target_establishes_abort_evidence": False,
            "abort_evidence_established_state": "seed-supply-aborted-established",
            "abort_evidence_establishes_supplier_invocation": False,
            "abort_evidence_establishes_abort_cause_only_as_recorded": True,
            "abort_evidence_is_a_separate_record": True,
            "abort_evidence_path": (
                D7_ITEM22_SEED_SUPPLY_ABORT_EVIDENCE_REPOSITORY_PATH
            ),
            "separate_abort_evidence_authorizes_retry": False,
            "supplier_invocation_status_requires_separate_evidence": True,
        },
        "exclusivity_scope": {
            "repository_local_no_replace_reservation_required": True,
            "cross_process_same_filesystem_exclusivity_contract_required": True,
            "cross_host_global_exclusivity_proved": False,
            "distributed_filesystem_exclusivity_proved": False,
            "supplier_global_idempotency_proved": False,
            "future_supplier_idempotency_or_external_coordination_required": True,
            "local_claim_bytes_alone_are_global_authority": False,
        },
        "current_instance_state": {
            "current_source_runtime_reanchor_present": False,
            "concrete_supplier_identity_present": False,
            "concrete_exclusive_claim_key_value_present": False,
            "exclusive_seed_supply_claim_present": False,
            "supplier_invocation_present": False,
            "official_seed_inventory_present": False,
            "atomic_target_present": False,
            "seed_supply_abort_evidence_present": False,
            "full_design_freeze_present": False,
            "launch_intent_present": False,
            "execution_observed": False,
        },
        "honest_local_scope": {
            "historical_item21_repository_history_only": True,
            "canonical_origin_main_verified": False,
            "current_source_runtime_verified": False,
            "external_reviewer_identity_authenticated": False,
            "signed_external_timestamp_present": False,
            "hostile_local_operator_resistance_proved": False,
            "installed_package_files_closed": False,
            "loaded_native_libraries_closed": False,
            "mutable_module_state_closed": False,
            "unrecorded_environment_closed": False,
            "model_or_data_state_closed": False,
            "supplier_identity_authenticated": False,
            "supplier_invocation_observed": False,
            "target_publication_observed": False,
            "execution_observed": False,
            "scientific_claim_eligible": False,
        },
        "d7_state": "not_run",
        "d8_state": "not_run",
        "authority": dict(sorted(_AUTHORITY.items())),
    }


def _checked_document(
    source: bytes,
    *,
    expected_sha256: str,
) -> Mapping[str, object]:
    expected = _require_sha256(expected_sha256, label="expected_sha256")
    if (
        type(source) is not bytes
        or not source
        or len(source) > MAX_D7_ITEM22_SEED_SUPPLY_TRANSACTION_CONTRACT_BYTES
    ):
        raise QualificationContractError(
            "D7 item-22 seed-supply contract must be nonempty bytes within the cap"
        )
    if _sha256_bytes(source) != expected:
        raise QualificationContractError(
            "D7 item-22 seed-supply contract source SHA-256 differs"
        )
    try:
        document = _parse_canonical_json(
            source,
            label="D7 item-22 seed-supply transaction contract",
        )
    except CanonicalJsonError as error:
        raise QualificationContractError(str(error)) from error
    if not isinstance(document, Mapping):
        raise QualificationContractError(
            "D7 item-22 seed-supply contract must be a JSON object"
        )
    return document


def _owner_path_contract_is_current() -> None:
    expected = (
        (
            D7_ITEM22_DIRECTORY_REPOSITORY_PATH,
            item21.D7_ITEM21_DIRECTORY,
            "item-21 directory",
        ),
        (
            D7_ITEM22_CURRENT_SOURCE_RUNTIME_REANCHOR_REPOSITORY_PATH,
            item21.D7_ITEM22_CURRENT_SOURCE_REANCHOR_REPOSITORY_PATH,
            "item-22 reanchor path",
        ),
        (
            D7_ITEM22_SEED_SUPPLY_DIRECTORY_REPOSITORY_PATH,
            item21.D7_ITEM22_SEED_SUPPLY_DIRECTORY_REPOSITORY_PATH,
            "item-22 seed-supply path",
        ),
        (
            D7_ITEM22_FUTURE_LAUNCH_DESCRIPTOR_REPOSITORY_PATH,
            item21.D7_FUTURE_LAUNCH_DESCRIPTOR_REPOSITORY_PATH,
            "future launch-descriptor path",
        ),
    )
    for pinned, owned, label in expected:
        if pinned != owned:
            raise QualificationContractError(f"{label} differs from its item-21 owner")


def _observed_item21_artifact_pins(
    chain: item21._LoadedD7Item21PositiveChain,
) -> tuple[tuple[str, str, str, str, int, str], ...]:
    if type(chain) is not item21._LoadedD7Item21PositiveChain:
        raise TypeError("chain must be the exact strict historical item-21 type")
    return (
        (
            "execution-source-runtime-receipt",
            chain.source_runtime_receipt.repository_path,
            item21.D7_ITEM21_SOURCE_RUNTIME_RECEIPT_SCHEMA_VERSION,
            chain.source_runtime_receipt.canonical_sha256,
            chain.source_runtime_receipt.byte_count,
            chain.source_runtime_receipt.introduction_commit,
        ),
        (
            "seed-free-readiness",
            chain.seed_free_readiness.repository_path,
            item21.D7_ITEM21_SEED_FREE_READINESS_SCHEMA_VERSION,
            chain.seed_free_readiness.canonical_sha256,
            chain.seed_free_readiness.byte_count,
            chain.seed_free_readiness.introduction_commit,
        ),
        (
            "family-admission-receipt",
            chain.reviewed_family_admission.repository_path,
            item21.D7_ITEM21_REVIEWED_FAMILY_ADMISSION_SCHEMA_VERSION,
            chain.reviewed_family_admission.canonical_sha256,
            chain.reviewed_family_admission.byte_count,
            chain.reviewed_family_admission.introduction_commit,
        ),
    )


@_dataclass(frozen=True, slots=True, init=False)
class D7Item22SeedSupplyTransactionContractSpec:
    """Sealed canonical specification; never an operational transaction."""

    _canonical_bytes: bytes

    schema_version: ClassVar[str] = (
        D7_ITEM22_SEED_SUPPLY_TRANSACTION_CONTRACT_SCHEMA_VERSION
    )

    def __init__(
        self,
        *,
        canonical_bytes: bytes,
        _factory_token: object = None,
    ) -> None:
        if _factory_token is not _SPEC_FACTORY_TOKEN:
            raise QualificationContractError(
                "D7Item22SeedSupplyTransactionContractSpec requires its closed "
                "factory or canonical reader"
            )
        expected = _contract_document()
        document = _checked_document(
            canonical_bytes,
            expected_sha256=_sha256_bytes(canonical_bytes),
        )
        if document != expected or canonical_bytes != _canonical_json_bytes(expected):
            raise QualificationContractError(
                "D7 item-22 seed-supply contract differs from the closed specification"
            )
        object.__setattr__(self, "_canonical_bytes", canonical_bytes)

    @classmethod
    def from_canonical_bytes(
        cls,
        source: bytes,
        *,
        expected_sha256: str,
    ) -> D7Item22SeedSupplyTransactionContractSpec:
        _checked_document(source, expected_sha256=expected_sha256)
        return cls(
            canonical_bytes=source,
            _factory_token=_SPEC_FACTORY_TOKEN,
        )

    @property
    def canonical_bytes(self) -> bytes:
        return self._canonical_bytes

    @property
    def canonical_sha256(self) -> str:
        return _sha256_bytes(self._canonical_bytes)

    def to_dict(self) -> dict[str, object]:
        document = _parse_canonical_json(
            self._canonical_bytes,
            label="D7 item-22 seed-supply transaction contract",
        )
        if type(document) is not dict:
            raise TypeError("validated item-22 contract must remain a JSON object")
        return document

    def __copy__(self) -> NoReturn:
        raise TypeError("D7 item-22 seed-supply contract cannot be copied")

    def __deepcopy__(self, memo: object) -> NoReturn:
        del memo
        raise TypeError("D7 item-22 seed-supply contract cannot be copied")

    def __reduce__(self) -> NoReturn:
        raise TypeError("D7 item-22 seed-supply contract is not pickleable")

    def __reduce_ex__(self, protocol: int) -> NoReturn:
        del protocol
        raise TypeError("D7 item-22 seed-supply contract is not pickleable")


@_dataclass(frozen=True, slots=True, init=False)
class LoadedD7Item22SeedSupplyContractFoundation:
    """Sealed evidence that the strict historical item-21 chain was reloaded."""

    transaction_contract: D7Item22SeedSupplyTransactionContractSpec
    source_runtime_receipt_commit: str
    seed_free_readiness_commit: str
    reviewed_family_admission_commit: str
    validation_current_head: str

    historical_item21_chain_verified: ClassVar[bool] = True
    historical_family_admission_evidence_verified: ClassVar[bool] = True
    historical_family_admission_promoted_to_authority: ClassVar[bool] = False
    current_source_runtime_verified: ClassVar[bool] = False
    current_source_runtime_reanchor_present: ClassVar[bool] = False
    concrete_supplier_identity_present: ClassVar[bool] = False
    concrete_supplier_identity_verified: ClassVar[bool] = False
    seed_supply_claim_acquired: ClassVar[bool] = False
    supplier_invoked: ClassVar[bool] = False
    official_seed_inventory_present: ClassVar[bool] = False
    atomic_target_present: ClassVar[bool] = False
    seed_supply_aborted: ClassVar[bool] = False
    full_design_freeze_present: ClassVar[bool] = False
    launch_intent_present: ClassVar[bool] = False
    reusable_authorization_capability_present: ClassVar[bool] = False
    execution_observed: ClassVar[bool] = False
    scientific_claim_eligible: ClassVar[bool] = False
    d7_execution_authorized: ClassVar[bool] = False
    d8_execution_authorized: ClassVar[bool] = False

    def __init__(
        self,
        *,
        transaction_contract: D7Item22SeedSupplyTransactionContractSpec,
        source_runtime_receipt_commit: str,
        seed_free_readiness_commit: str,
        reviewed_family_admission_commit: str,
        validation_current_head: str,
        _factory_token: object = None,
    ) -> None:
        if _factory_token is not _FOUNDATION_FACTORY_TOKEN:
            raise QualificationContractError(
                "LoadedD7Item22SeedSupplyContractFoundation requires the strict "
                "historical item-21 loader"
            )
        if type(transaction_contract) is not D7Item22SeedSupplyTransactionContractSpec:
            raise TypeError("transaction_contract must be the exact sealed spec")
        receipt_commit = _commit(
            source_runtime_receipt_commit,
            label="source_runtime_receipt_commit",
        )
        readiness_commit = _commit(
            seed_free_readiness_commit,
            label="seed_free_readiness_commit",
        )
        admission_commit = _commit(
            reviewed_family_admission_commit,
            label="reviewed_family_admission_commit",
        )
        current_head = _commit(
            validation_current_head,
            label="validation_current_head",
        )
        expected_commits = tuple(pin[5] for pin in _ITEM21_ARTIFACT_PINS)
        if (
            receipt_commit,
            readiness_commit,
            admission_commit,
        ) != expected_commits:
            raise QualificationContractError(
                "loaded item-22 contract foundation differs from item-21 pins"
            )
        object.__setattr__(self, "transaction_contract", transaction_contract)
        object.__setattr__(
            self,
            "source_runtime_receipt_commit",
            receipt_commit,
        )
        object.__setattr__(self, "seed_free_readiness_commit", readiness_commit)
        object.__setattr__(
            self,
            "reviewed_family_admission_commit",
            admission_commit,
        )
        object.__setattr__(self, "validation_current_head", current_head)

    def __copy__(self) -> NoReturn:
        raise TypeError("loaded item-22 contract foundation cannot be copied")

    def __deepcopy__(self, memo: object) -> NoReturn:
        del memo
        raise TypeError("loaded item-22 contract foundation cannot be copied")

    def __reduce__(self) -> NoReturn:
        raise TypeError("loaded item-22 contract foundation is not pickleable")

    def __reduce_ex__(self, protocol: int) -> NoReturn:
        del protocol
        raise TypeError("loaded item-22 contract foundation is not pickleable")


def load_d7_item22_seed_supply_contract_foundation(
    *,
    repository_root: str | Path,
) -> LoadedD7Item22SeedSupplyContractFoundation:
    """Strictly reload item 21 and reconstruct one non-authorizing contract."""

    _owner_path_contract_is_current()
    chain = item21.load_committed_d7_item21_positive_chain(repository_root)
    observed = _observed_item21_artifact_pins(chain)
    if observed != _ITEM21_ARTIFACT_PINS:
        raise QualificationContractError(
            "strict historical item-21 chain differs from the item-22 contract pins"
        )
    source = _canonical_json_bytes(_contract_document())
    contract = D7Item22SeedSupplyTransactionContractSpec(
        canonical_bytes=source,
        _factory_token=_SPEC_FACTORY_TOKEN,
    )
    return LoadedD7Item22SeedSupplyContractFoundation(
        transaction_contract=contract,
        source_runtime_receipt_commit=observed[0][5],
        seed_free_readiness_commit=observed[1][5],
        reviewed_family_admission_commit=observed[2][5],
        validation_current_head=item21._head(chain.repository_root),
        _factory_token=_FOUNDATION_FACTORY_TOKEN,
    )
