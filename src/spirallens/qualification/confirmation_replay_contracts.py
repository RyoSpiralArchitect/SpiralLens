"""Level-0 contracts separating a D7 replay target from attempt chronology.

This module defines two closed, canonical contract specifications:

* the future immutable, seed-bearing replay target that says *what* is run;
* the future append-only attempt envelope that records *one execution*.

Neither specification is an instance of those future records.  In particular,
this module accepts no seed, result, gate, namespace, authorization, source
digest, or preconstructed source-closure wrapper.  The choice-free loader
reruns the pinned committed-C2 verifier internally and returns only an
in-memory foundation.  It publishes no artifact and grants no D7 or D8
authority.

The recorded C2 receipt closes the historical C1 source set only.  It does not
cover this module or any later lifecycle, result, terminal, or runner code.
Issuing an official replay target therefore remains blocked on a later exact
execution-source and runtime closure after those surfaces are complete.
"""

from __future__ import annotations

import re
import subprocess
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from spirallens.core.canonical import (
    CanonicalJsonError,
    canonical_json_bytes,
    parse_canonical_json,
    sha256_bytes,
)

from .common import QualificationContractError, require_sha256
from .confirmation_c1 import (
    D7_C2_RECEIPT_REPOSITORY_PATH,
    MAX_D7_C1_SEED_FREE_SOURCE_SET_BYTES,
    D7C1SeedFreeSourceSet,
)
from .confirmation_source_closure import load_committed_d7_source_closure

D7_REPLAY_TARGET_CONTRACT_SCHEMA_VERSION = (
    "spirallens.d7-replay-target-contract-spec.v0.1"
)
D7_ATTEMPT_ENVELOPE_CONTRACT_SCHEMA_VERSION = (
    "spirallens.d7-attempt-envelope-contract-spec.v0.1"
)
MAX_D7_REPLAY_CONTRACT_BYTES = 512 * 1024

D7_RECORDED_C1_CANONICAL_SHA256 = (
    "b7b3b416738c9d02ed76764e35bb131f6bcc6df2948bff200b51df83aee33a5d"
)
D7_RECORDED_C1_COMPONENT_SET_SHA256 = (
    "7f03664b335ebbce8fb2436a31d9526adaf3afab0b2f93657af3aee4efdaaca5"
)
D7_RECORDED_C1_POST_MERGE_COMMIT = "e58a8169b41be688628ab7dda583e68088d3affc"
D7_RECORDED_C2_CANONICAL_SHA256 = (
    "d28a87bce5ec80c3388df1e21bccbc052f34beb637ff86f81f4f502d9fdd71a3"
)
D7_RECORDED_C2_INTRODUCTION_COMMIT = "2f4e715a951211af8ca0ca4f6b2f7473134bf92b"

_RECORDED_C1_REPOSITORY_PATH = (
    "experiments/qualification/d7_spectral_moment_confirmation_v0_1/"
    "c1-seed-free-source-set.json"
)
_RECORDED_C2_REPOSITORY_PATH = (
    "experiments/qualification/d7_spectral_moment_confirmation_v0_1/"
    "c2-source-closure-receipt.json"
)
_RECORDED_SEED_FREE_DESIGN_ID = "d7-spectral-moment-stable-seed-free-design-v0-1"
_RECORDED_SEED_FREE_DESIGN_SHA256 = (
    "936df4835d398ae5f839da4ad4dace097997388a15643de440d7a4a582b13a4e"
)
_RECORDED_INVENTORY_SHA256 = (
    "938350eb70390f246e96e8fcb477fc191c345bdfebb16a56d17555763744dda4"
)
_RECORDED_IMPLEMENTATION_REGISTRY_SHA256 = (
    "f73f0945ad59430ad75bde932acb2822e164140e06cd12428ef8b6167e1dca18"
)
_RECORDED_AGGREGATION_APPLICATION_SHA256 = (
    "d616cd063a87103c558fa33ce23514dab70abb59483d3d303ba1f475a6881435"
)
_RECORDED_EVALUATION_PROJECTION_SHA256 = (
    "51aa351c38c0b4ad28c1bf432bc7e1bcf9b94ab9099d3f14cf1bdde9812118f8"
)
_RECORDED_SEED_SLOT_IDS = (
    "confirmation-seed-slot-00",
    "confirmation-seed-slot-01",
)

_TARGET_FACTORY_TOKEN = object()
_ENVELOPE_FACTORY_TOKEN = object()
_FOUNDATION_FACTORY_TOKEN = object()
_COMMIT = re.compile(r"^[0-9a-f]{40}$")

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


def _commit(value: object, *, label: str) -> str:
    if not isinstance(value, str) or _COMMIT.fullmatch(value) is None:
        raise QualificationContractError(f"{label} must be a full Git commit")
    return value


def _target_document() -> dict[str, object]:
    return {
        "schema_version": D7_REPLAY_TARGET_CONTRACT_SCHEMA_VERSION,
        "contract_id": "d7-spectral-moment-replay-target-contract-v0-1",
        "status": "schema-defined-instance-absent",
        "claim_ceiling": "level_0",
        "recorded_parent_bindings": {
            "c1": {
                "repository_path": _RECORDED_C1_REPOSITORY_PATH,
                "canonical_sha256": D7_RECORDED_C1_CANONICAL_SHA256,
                "component_set_sha256": D7_RECORDED_C1_COMPONENT_SET_SHA256,
                "post_merge_commit": D7_RECORDED_C1_POST_MERGE_COMMIT,
            },
            "c2": {
                "repository_path": _RECORDED_C2_REPOSITORY_PATH,
                "canonical_sha256": D7_RECORDED_C2_CANONICAL_SHA256,
                "introduction_commit": D7_RECORDED_C2_INTRODUCTION_COMMIT,
            },
            "validation_boundary": {
                "committed_c2_must_be_reloaded_internally": True,
                "caller_supplied_loaded_source_closure_accepted": False,
                "caller_supplied_expected_digest_accepted": False,
                "validation_current_head_in_canonical_identity": False,
            },
        },
        "seed_free_projection": {
            "design_id": _RECORDED_SEED_FREE_DESIGN_ID,
            "design_sha256": _RECORDED_SEED_FREE_DESIGN_SHA256,
            "inventory_sha256": _RECORDED_INVENTORY_SHA256,
            "implementation_registry_sha256": (
                _RECORDED_IMPLEMENTATION_REGISTRY_SHA256
            ),
            "aggregation_application_sha256": (
                _RECORDED_AGGREGATION_APPLICATION_SHA256
            ),
            "identity_free_evaluation_projection_sha256": (
                _RECORDED_EVALUATION_PROJECTION_SHA256
            ),
            "seed_slot_ids": list(_RECORDED_SEED_SLOT_IDS),
            "numeric_seed_values_present": False,
        },
        "future_replay_target": {
            "required_fields": [
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
            ],
            "required_properties": {
                "claim_ceiling_must_equal": "level_0",
                "target_local_authority_must_equal": dict(sorted(_AUTHORITY.items())),
                "nested_or_extended_authority_allowed": False,
                "content_addressed": True,
                "attempt_path_independent": True,
                "outcome_free": True,
                "exact_concrete_seed_binding_required": True,
                "exact_full_design_binding_required": True,
                "admitted_family_binding_required": True,
                "exact_execution_source_runtime_closure_required": True,
                "primary_and_isolated_replay_bytes_must_match": True,
                "seed_substitution_allowed": False,
            },
            "forbidden_fields": [
                "attempt_role",
                "attempt_slot",
                "absolute_repository_path",
                "store_path",
                "output_namespace",
                "terminal_path",
                "host",
                "process_id",
                "wall_clock_timestamp",
                "launch_authorization",
                "attempt_claim",
                "execution_start",
                "result_payload",
                "result_payload_sha256",
                "failed_attempt",
                "terminal_lineage",
                "gate_verdict",
                "expected_output",
            ],
        },
        "future_official_seed_binding": {
            "required_seed_count": 2,
            "seed_values_must_be_plain_integers": True,
            "seed_values_must_be_nonnegative_signed_int64": True,
            "seed_values_must_be_unique_and_canonically_sorted": True,
            "development_seeds_must_be_excluded": True,
            "parent_selection_seeds_must_be_excluded": True,
            "frozen_exclusion_registry_binding_required": True,
            "seed_slot_ordinal_mapping": [
                {
                    "ordinal": 0,
                    "seed_slot_id": _RECORDED_SEED_SLOT_IDS[0],
                },
                {
                    "ordinal": 1,
                    "seed_slot_id": _RECORDED_SEED_SLOT_IDS[1],
                },
            ],
            "full_design_must_be_canonically_reconstructed_from_exact_inventory": (
                True
            ),
            "separate_seed_argument_to_runner_allowed": False,
        },
        "seed_supply_chronology_contract": {
            "ordered_transitions": [
                "final-lifecycle-result-terminal-runner-code-reviewed",
                "exact-execution-source-runtime-closure",
                "seed-free-readiness",
                "reviewed-family-admission",
                "exclusive-seed-supply-claim",
                "single-supplier-invocation",
                "atomic-seed-bearing-full-design-and-target-publication",
                "committed-full-design-freeze-receipt",
                "launch-intent",
            ],
            "supplier_invocation_must_follow_exclusive_claim": True,
            "supplier_may_be_invoked_more_than_once": False,
            "claim_without_target_is_seed_supply_aborted": True,
            "seed_supply_aborted_retry_authorized": False,
            "target_publication_must_be_no_replace": True,
            "target_absence_proves_supplier_not_invoked": False,
            "published_target_without_freeze_receipt_allows_supplier_retry": False,
            "published_target_freeze_metadata_must_be_exactly_recoverable": True,
        },
        "source_and_runtime_ceiling": {
            "historical_c1_git_source_set_requirement_recorded": True,
            "historical_c1_code_execution_attested": False,
            "current_contract_source_closed_by_c2": False,
            "current_execution_source_compatibility_verified": False,
            "python_runtime_attested": False,
            "native_runtime_attested": False,
            "transitive_dependencies_attested": False,
            "in_process_callable_identity_verified": False,
            "later_exact_execution_source_runtime_receipt_required": True,
            "that_receipt_must_follow_final_lifecycle_result_terminal_runner_code": (
                True
            ),
        },
        "current_instance_state": {
            "replay_target_present": False,
            "official_seed_inventory_present": False,
            "full_design_frozen": False,
            "family_admitted": False,
            "execution_source_runtime_closure_present": False,
            "placeholder_result_present": False,
        },
        "deferred": [
            "concrete-replay-target-schema-and-instance",
            "official-seed-supply-lifecycle",
            "family-admission-receipt",
            "full-design-freeze-receipt",
            "exact-current-execution-source-runtime-closure",
            "launch-and-attempt-chronology",
            "typed-result-or-failed-attempt",
            "terminal-transaction",
            "isolated-replay-comparison",
        ],
        "d7_state": "not_run",
        "d8_state": "not_run",
        "authority": dict(sorted(_AUTHORITY.items())),
    }


def _attempt_document(
    target_contract: D7ReplayTargetContractSpec,
) -> dict[str, object]:
    return {
        "schema_version": D7_ATTEMPT_ENVELOPE_CONTRACT_SCHEMA_VERSION,
        "contract_id": "d7-spectral-moment-attempt-envelope-contract-v0-1",
        "status": "schema-defined-instance-absent",
        "claim_ceiling": "level_0",
        "replay_target_contract_binding": {
            "schema_version": target_contract.schema_version,
            "contract_id": target_contract.to_dict()["contract_id"],
            "canonical_sha256": target_contract.canonical_sha256,
            "byte_count": len(target_contract.canonical_bytes),
            "future_concrete_target_sha256_required": True,
            "target_body_may_be_duplicated_in_attempt_records": False,
        },
        "record_model": {
            "persisted_as_one_mutable_nullable_object": False,
            "derived_loaded_envelope_is_read_only": True,
            "append_only_stage_order": [
                "attempt-declaration",
                "launch-authorization",
                "exclusive-attempt-claim",
                "execution-start",
                "scientific-result-or-failed-attempt",
                "terminal-manifest",
                "terminal-consumption",
            ],
            "attempt_roles": [
                "primary-confirmation",
                "isolated-byte-replay",
            ],
            "stage_contracts": [
                {
                    "stage": "attempt-declaration",
                    "binds": [
                        "launch-intent-sha256",
                        "concrete-replay-target-sha256",
                        "frozen-attempt-role",
                        "role-evidence-binding",
                        "store-identity",
                        "output-namespace-identity",
                        "terminal-path-identity",
                        "authorization-commit",
                    ],
                },
                {
                    "stage": "launch-authorization",
                    "binds": [
                        "attempt-declaration-sha256",
                        "concrete-replay-target-sha256",
                        "admission-receipt-sha256",
                        "full-design-freeze-receipt-sha256",
                        "execution-source-runtime-receipt-sha256",
                        "namespace-absence-at-authorization-commit",
                        "terminal-path-absence-at-authorization-commit",
                    ],
                },
                {
                    "stage": "exclusive-attempt-claim",
                    "binds": [
                        "launch-authorization-sha256",
                        "label-independent-attempt-key",
                    ],
                },
                {
                    "stage": "execution-start",
                    "binds": [
                        "exclusive-attempt-claim-sha256",
                        "concrete-replay-target-sha256",
                        "observed-execution-source-runtime-receipt-sha256",
                        "observed-runtime-specification-sha256",
                    ],
                },
                {
                    "stage": "scientific-result-or-failed-attempt",
                    "binds": [
                        "execution-start-sha256",
                        "concrete-replay-target-sha256",
                        "exactly-one-terminal-variant",
                    ],
                },
                {
                    "stage": "terminal-manifest",
                    "binds": [
                        "scientific-result-or-failed-attempt-sha256",
                        "closed-world-file-inventory",
                    ],
                },
                {
                    "stage": "terminal-consumption",
                    "binds": [
                        "terminal-manifest-sha256",
                        "consumed-attempt-key",
                    ],
                },
            ],
            "attempt_records_forbidden_to_redefine": [
                "official-seed-inventory",
                "thresholds",
                "graph-or-cycle-inventory",
                "aggregation-policy",
                "result-payload-schema",
                "construction-family",
                "replay-target-identity",
            ],
            "launch_intent_is_persisted_predecessor": True,
            "attempt_declaration_must_bind_exact_launch_intent": True,
            "untracked_launch_intent_allowed": False,
        },
        "canonical_equality_constraints": [
            {
                "left": ("attempt-declaration.concrete-replay-target-sha256"),
                "relation": "byte-equal",
                "right": "loaded-replay-target.canonical-sha256",
            },
            {
                "left": ("launch-authorization.concrete-replay-target-sha256"),
                "relation": "byte-equal",
                "right": ("attempt-declaration.concrete-replay-target-sha256"),
            },
            {
                "left": (
                    "launch-authorization.execution-source-runtime-receipt-sha256"
                ),
                "relation": "byte-equal",
                "right": (
                    "loaded-replay-target."
                    "execution-source-runtime-closure-binding."
                    "receipt-sha256"
                ),
            },
            {
                "left": "execution-start.concrete-replay-target-sha256",
                "relation": "byte-equal",
                "right": ("launch-authorization.concrete-replay-target-sha256"),
            },
            {
                "left": (
                    "execution-start.observed-execution-source-runtime-receipt-sha256"
                ),
                "relation": "byte-equal",
                "right": (
                    "loaded-replay-target."
                    "execution-source-runtime-closure-binding."
                    "receipt-sha256"
                ),
            },
            {
                "left": ("execution-start.observed-runtime-specification-sha256"),
                "relation": "byte-equal",
                "right": (
                    "loaded-replay-target."
                    "execution-source-runtime-closure-binding."
                    "runtime-specification-sha256"
                ),
            },
            {
                "left": ("scientific-result-payload.concrete-replay-target-sha256"),
                "relation": "byte-equal",
                "right": "loaded-replay-target.canonical-sha256",
            },
            {
                "left": ("scientific-result-payload.full-inventory-sha256"),
                "relation": "byte-equal",
                "right": ("loaded-replay-target.full-design-binding.inventory-sha256"),
            },
            {
                "left": ("scientific-result-payload.aggregation-sha256"),
                "relation": "byte-equal",
                "right": ("loaded-replay-target.aggregation-binding.canonical-sha256"),
            },
            {
                "left": ("scientific-result-payload.result-schema-sha256"),
                "relation": "byte-equal",
                "right": (
                    "loaded-replay-target.result-payload-schema-binding."
                    "canonical-sha256"
                ),
            },
        ],
        "execution_start_contract": {
            "target_authorization_claim_join_must_be_exact": True,
            "observed_execution_source_must_match_frozen_target_receipt": True,
            "observed_runtime_must_match_frozen_target_runtime_specification": True,
            "output_namespace_absence_rechecked_immediately_before_start": True,
            "terminal_path_absence_rechecked_immediately_before_start": True,
            "placeholder_output_before_start_allowed": False,
        },
        "outcome_contract": {
            "scientific_result_payload_attempt_independent": True,
            "scientific_result_payload_binds_concrete_target_sha256": True,
            "scientific_result_payload_binds_full_execution_inventory_sha256": True,
            "scientific_result_payload_binds_aggregation_and_result_schema": True,
            "payload_validator_reconstructs_exact_target_semantic_join": True,
            "payload_from_different_target_allowed": False,
            "scientific_result_wrapper_binds_result_payload_sha256": True,
            "scientific_result_wrapper_binds_concrete_target_sha256": True,
            "failed_attempt_is_distinct_type": True,
            "scientific_result_and_failed_attempt_mutually_exclusive": True,
            "empty_or_nullable_result_allowed": False,
            "not_run_placeholder_allowed": False,
            "fail_or_insufficient_scientific_result_consumes_attempt": True,
            "post_start_infrastructure_error_requires_failed_terminal": True,
        },
        "failure_and_retry_contract": {
            "before_claim_correction_allowed_without_target_change": True,
            "claim_without_start_may_continue_only_from_same_claim": True,
            "visible_start_without_terminal_state": "started_unresolved",
            "started_unresolved_is_terminal_aborted": False,
            "started_unresolved_retry_authorized": False,
            "started_unresolved_replay_authorized": False,
            "started_unresolved_d8_eligible": False,
            "started_unresolved_may_remain_indefinitely": True,
            "started_unresolved_finalization_requires_append_only_record": True,
            "abort_finalization_requires_external_evidence": True,
            "abort_finalization_binds_start_and_evidence": True,
            "evidenced_abort_produces_failed_terminal_transaction": True,
            "hard_crash_can_publish_in_process_failure": False,
            "terminal_visible_attempt_consumed": True,
            "ordinary_post_start_exception_must_publish_failure_then_reraise": True,
            "partial_records_may_be_deleted_on_process_failure": False,
            "attempt_may_be_reopened": False,
            "failed_attempt_may_be_relabelled_as_isolated_replay": False,
            "namespace_or_terminal_path_may_be_reused": False,
            "alternate_store_global_one_shot_proved": False,
            "hostile_deletion_resistance_proved": False,
        },
        "terminal_transaction_contract": {
            "contains_exactly_one_scientific_result_or_failed_attempt": True,
            "contains_terminal_manifest": True,
            "contains_terminal_consumption": True,
            "staged_complete_tree_required_before_visibility": True,
            "published_by_atomic_no_replace_directory_rename": True,
            "partial_terminal_transaction_may_be_published": False,
        },
        "attempt_role_evidence_contract": {
            "primary_confirmation": {
                "prior_primary_terminal_required": False,
            },
            "isolated_byte_replay": {
                "persisted_passed_primary_terminal_sha256_required": True,
                "persisted_primary_terminal_consumption_sha256_required": True,
                "primary_target_sha256_must_equal_replay_target_sha256": True,
                "replay_declaration_must_follow_primary_consumption": True,
                "role_derived_from_typed_primary_receipts": True,
                "caller_role_label_sufficient": False,
            },
        },
        "isolated_replay_contract": {
            "same_concrete_replay_target_sha256_required": True,
            "distinct_attempt_role_required": True,
            "distinct_namespace_claim_and_start_required": True,
            "complete_terminal_transactions_loaded_internally": True,
            "caller_supplied_result_bytes_or_hashes_sufficient": False,
            "canonical_result_payload_bytes_must_match": True,
            "attempt_envelope_bytes_must_match": False,
            "passed_primary_d7_result_required_before_d8": True,
            "output_namespaces_must_be_realpath_disjoint": True,
            "terminal_trees_must_be_inode_disjoint": True,
            "symlink_or_hardlink_aliases_allowed": False,
            "replay_is_independent_confirmation": False,
        },
        "current_instance_state": {
            "attempt_envelope_present": False,
            "attempt_declaration_present": False,
            "launch_authorization_present": False,
            "exclusive_attempt_claim_present": False,
            "execution_start_present": False,
            "result_payload_present": False,
            "failed_attempt_present": False,
            "terminal_manifest_present": False,
            "terminal_consumption_present": False,
            "placeholder_result_present": False,
        },
        "d7_state": "not_run",
        "d8_state": "not_run",
        "authority": dict(sorted(_AUTHORITY.items())),
    }


def _checked_document(
    source: bytes,
    *,
    expected_sha256: str,
    maximum_bytes: int,
    label: str,
) -> Mapping[str, object]:
    expected = require_sha256(expected_sha256, label="expected_sha256")
    if not isinstance(source, bytes) or not source or len(source) > maximum_bytes:
        raise QualificationContractError(
            f"{label} must be nonempty bytes within the cap"
        )
    if sha256_bytes(source) != expected:
        raise QualificationContractError(f"{label} source SHA-256 differs")
    try:
        document = parse_canonical_json(source, label=label)
    except CanonicalJsonError as error:
        raise QualificationContractError(str(error)) from error
    if not isinstance(document, Mapping):
        raise QualificationContractError(f"{label} must be a JSON object")
    return document


def _require_mapping(value: object, *, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise QualificationContractError(f"{label} must be an object")
    return value


def _read_git_blob_bounded(
    *,
    repository_root: str | Path,
    commit: str,
    repository_path: str,
    maximum_bytes: int,
) -> bytes:
    process = subprocess.Popen(
        [
            "git",
            "-C",
            str(repository_root),
            "show",
            f"{commit}:{repository_path}",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    if process.stdout is None:
        process.kill()
        process.wait()
        raise QualificationContractError("cannot read the recorded D7 C1 Git blob")
    try:
        source = process.stdout.read(maximum_bytes + 1)
        if len(source) > maximum_bytes:
            process.kill()
            process.wait()
            raise QualificationContractError(
                "recorded D7 C1 Git blob exceeds its byte cap"
            )
        if process.wait() != 0:
            raise QualificationContractError(
                "recorded D7 C1 Git blob cannot be resolved"
            )
        return source
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()


def _verify_recorded_c1_projection(
    *,
    repository_root: str | Path,
) -> None:
    """Join every copied target subpin back to the exact recorded C1 bytes."""

    source = _read_git_blob_bounded(
        repository_root=repository_root,
        commit=D7_RECORDED_C1_POST_MERGE_COMMIT,
        repository_path=_RECORDED_C1_REPOSITORY_PATH,
        maximum_bytes=MAX_D7_C1_SEED_FREE_SOURCE_SET_BYTES,
    )
    if not source or len(source) > MAX_D7_C1_SEED_FREE_SOURCE_SET_BYTES:
        raise QualificationContractError(
            "recorded D7 C1 candidate exceeds its byte cap"
        )
    bundle = D7C1SeedFreeSourceSet.from_canonical_bytes(
        source,
        expected_sha256=D7_RECORDED_C1_CANONICAL_SHA256,
    )
    document = bundle.to_dict()
    components = _require_mapping(
        document.get("components"),
        label="recorded D7 C1 components",
    )
    design = _require_mapping(
        components.get("seed_free_execution_design"),
        label="recorded seed-free execution-design component",
    )
    design_body = _require_mapping(
        design.get("body"),
        label="recorded seed-free execution-design body",
    )
    invariant_identities = _require_mapping(
        design_body.get("invariant_identities"),
        label="recorded seed-free invariant identities",
    )
    registry = _require_mapping(
        components.get("implementation_registry"),
        label="recorded implementation-registry component",
    )
    aggregation = _require_mapping(
        components.get("aggregation_application"),
        label="recorded aggregation-application component",
    )
    aggregation_body = _require_mapping(
        aggregation.get("body"),
        label="recorded aggregation-application body",
    )
    observed = {
        "component_set_sha256": document.get("component_set_sha256"),
        "design_id": design_body.get("design_id"),
        "design_sha256": design.get("canonical_sha256"),
        "inventory_sha256": invariant_identities.get("inventory_sha256"),
        "implementation_registry_sha256": registry.get("canonical_sha256"),
        "aggregation_application_sha256": aggregation.get("canonical_sha256"),
        "identity_free_evaluation_projection_sha256": aggregation_body.get(
            "identity_free_evaluation_projection_sha256"
        ),
        "seed_slot_ordinal_mapping": aggregation_body.get("seed_slot_ordinal_mapping"),
    }
    expected = {
        "component_set_sha256": D7_RECORDED_C1_COMPONENT_SET_SHA256,
        "design_id": _RECORDED_SEED_FREE_DESIGN_ID,
        "design_sha256": _RECORDED_SEED_FREE_DESIGN_SHA256,
        "inventory_sha256": _RECORDED_INVENTORY_SHA256,
        "implementation_registry_sha256": (_RECORDED_IMPLEMENTATION_REGISTRY_SHA256),
        "aggregation_application_sha256": (_RECORDED_AGGREGATION_APPLICATION_SHA256),
        "identity_free_evaluation_projection_sha256": (
            _RECORDED_EVALUATION_PROJECTION_SHA256
        ),
        "seed_slot_ordinal_mapping": [
            {
                "ordinal": 0,
                "seed_slot_id": _RECORDED_SEED_SLOT_IDS[0],
            },
            {
                "ordinal": 1,
                "seed_slot_id": _RECORDED_SEED_SLOT_IDS[1],
            },
        ],
    }
    if observed != expected:
        raise QualificationContractError(
            "recorded D7 C1 target projection differs from the pinned subcomponents"
        )


@dataclass(frozen=True, slots=True, init=False)
class D7ReplayTargetContractSpec:
    """Canonical schema contract; not a seed-bearing replay-target instance."""

    _canonical_bytes: bytes

    schema_version: ClassVar[str] = D7_REPLAY_TARGET_CONTRACT_SCHEMA_VERSION

    def __init__(
        self,
        *,
        _factory_token: object = None,
        canonical_bytes: bytes,
    ) -> None:
        if _factory_token is not _TARGET_FACTORY_TOKEN:
            raise QualificationContractError(
                "D7ReplayTargetContractSpec must be reconstructed by its "
                "closed factory or reader"
            )
        expected = _target_document()
        document = _checked_document(
            canonical_bytes,
            expected_sha256=sha256_bytes(canonical_bytes),
            maximum_bytes=MAX_D7_REPLAY_CONTRACT_BYTES,
            label="D7 replay-target contract specification",
        )
        if document != expected or canonical_bytes != canonical_json_bytes(expected):
            raise QualificationContractError(
                "D7 replay-target contract differs from the closed specification"
            )
        object.__setattr__(self, "_canonical_bytes", canonical_bytes)

    @classmethod
    def from_canonical_bytes(
        cls,
        source: bytes,
        *,
        expected_sha256: str,
    ) -> D7ReplayTargetContractSpec:
        _checked_document(
            source,
            expected_sha256=expected_sha256,
            maximum_bytes=MAX_D7_REPLAY_CONTRACT_BYTES,
            label="D7 replay-target contract specification",
        )
        return cls(
            _factory_token=_TARGET_FACTORY_TOKEN,
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
            label="D7 replay-target contract specification",
        )
        if not isinstance(document, Mapping):
            raise TypeError("validated replay-target contract must remain a mapping")
        return dict(document)


@dataclass(frozen=True, slots=True, init=False)
class D7AttemptEnvelopeContractSpec:
    """Canonical append-only chronology contract; not an attempt instance."""

    _canonical_bytes: bytes
    target_contract_sha256: str

    schema_version: ClassVar[str] = D7_ATTEMPT_ENVELOPE_CONTRACT_SCHEMA_VERSION

    def __init__(
        self,
        *,
        _factory_token: object = None,
        canonical_bytes: bytes,
        target_contract: D7ReplayTargetContractSpec,
    ) -> None:
        if _factory_token is not _ENVELOPE_FACTORY_TOKEN:
            raise QualificationContractError(
                "D7AttemptEnvelopeContractSpec must be reconstructed by its "
                "closed factory or reader"
            )
        if not isinstance(target_contract, D7ReplayTargetContractSpec):
            raise TypeError("target_contract must be a D7ReplayTargetContractSpec")
        expected = _attempt_document(target_contract)
        document = _checked_document(
            canonical_bytes,
            expected_sha256=sha256_bytes(canonical_bytes),
            maximum_bytes=MAX_D7_REPLAY_CONTRACT_BYTES,
            label="D7 attempt-envelope contract specification",
        )
        if document != expected or canonical_bytes != canonical_json_bytes(expected):
            raise QualificationContractError(
                "D7 attempt-envelope contract differs from the closed specification"
            )
        object.__setattr__(self, "_canonical_bytes", canonical_bytes)
        object.__setattr__(
            self,
            "target_contract_sha256",
            target_contract.canonical_sha256,
        )

    @classmethod
    def from_canonical_bytes(
        cls,
        source: bytes,
        *,
        expected_sha256: str,
        target_contract: D7ReplayTargetContractSpec,
    ) -> D7AttemptEnvelopeContractSpec:
        _checked_document(
            source,
            expected_sha256=expected_sha256,
            maximum_bytes=MAX_D7_REPLAY_CONTRACT_BYTES,
            label="D7 attempt-envelope contract specification",
        )
        return cls(
            _factory_token=_ENVELOPE_FACTORY_TOKEN,
            canonical_bytes=source,
            target_contract=target_contract,
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
            label="D7 attempt-envelope contract specification",
        )
        if not isinstance(document, Mapping):
            raise TypeError("validated attempt-envelope contract must remain a mapping")
        return dict(document)


@dataclass(frozen=True, slots=True, init=False)
class LoadedD7ReplayAttemptContractFoundation:
    """In-memory proof that fixed specs were rebuilt after pinned C2 loading."""

    replay_target_contract: D7ReplayTargetContractSpec
    attempt_envelope_contract: D7AttemptEnvelopeContractSpec
    c1_commit: str
    c2_commit: str
    validation_current_head: str
    historical_c1_git_source_set_verified: bool
    current_contract_source_compatibility_verified: bool
    current_execution_source_runtime_closure_verified: bool
    replay_target_present: bool
    attempt_envelope_present: bool
    official_seed_inventory_present: bool
    launch_authorized: bool

    def __init__(
        self,
        *,
        _factory_token: object = None,
        replay_target_contract: D7ReplayTargetContractSpec,
        attempt_envelope_contract: D7AttemptEnvelopeContractSpec,
        c1_commit: str,
        c2_commit: str,
        validation_current_head: str,
    ) -> None:
        if _factory_token is not _FOUNDATION_FACTORY_TOKEN:
            raise QualificationContractError(
                "LoadedD7ReplayAttemptContractFoundation must be produced by "
                "the pinned repository loader"
            )
        if not isinstance(replay_target_contract, D7ReplayTargetContractSpec):
            raise TypeError("replay_target_contract must be D7ReplayTargetContractSpec")
        if not isinstance(
            attempt_envelope_contract,
            D7AttemptEnvelopeContractSpec,
        ):
            raise TypeError(
                "attempt_envelope_contract must be D7AttemptEnvelopeContractSpec"
            )
        observed_c1 = _commit(c1_commit, label="c1_commit")
        observed_c2 = _commit(c2_commit, label="c2_commit")
        observed_head = _commit(
            validation_current_head,
            label="validation_current_head",
        )
        if (
            observed_c1 != D7_RECORDED_C1_POST_MERGE_COMMIT
            or observed_c2 != D7_RECORDED_C2_INTRODUCTION_COMMIT
            or attempt_envelope_contract.target_contract_sha256
            != replay_target_contract.canonical_sha256
        ):
            raise QualificationContractError(
                "loaded D7 replay/attempt contract lineage differs"
            )
        object.__setattr__(
            self,
            "replay_target_contract",
            replay_target_contract,
        )
        object.__setattr__(
            self,
            "attempt_envelope_contract",
            attempt_envelope_contract,
        )
        object.__setattr__(self, "c1_commit", observed_c1)
        object.__setattr__(self, "c2_commit", observed_c2)
        object.__setattr__(self, "validation_current_head", observed_head)
        object.__setattr__(
            self,
            "historical_c1_git_source_set_verified",
            True,
        )
        object.__setattr__(
            self,
            "current_contract_source_compatibility_verified",
            False,
        )
        object.__setattr__(
            self,
            "current_execution_source_runtime_closure_verified",
            False,
        )
        object.__setattr__(self, "replay_target_present", False)
        object.__setattr__(self, "attempt_envelope_present", False)
        object.__setattr__(self, "official_seed_inventory_present", False)
        object.__setattr__(self, "launch_authorized", False)


def load_d7_replay_attempt_contract_foundation(
    *,
    repository_root: str | Path,
) -> LoadedD7ReplayAttemptContractFoundation:
    """Verify pinned C1/C2 lineage and reconstruct both non-authorizing specs."""

    if _RECORDED_C2_REPOSITORY_PATH != D7_C2_RECEIPT_REPOSITORY_PATH:
        raise QualificationContractError(
            "recorded D7 C2 repository-path pin differs from the verifier"
        )
    loaded = load_committed_d7_source_closure(
        repository_root=repository_root,
        expected_source_sha256=D7_RECORDED_C2_CANONICAL_SHA256,
        expected_canonical_sha256=D7_RECORDED_C2_CANONICAL_SHA256,
    )
    if (
        loaded.c1_commit != D7_RECORDED_C1_POST_MERGE_COMMIT
        or loaded.c2_commit != D7_RECORDED_C2_INTRODUCTION_COMMIT
    ):
        raise QualificationContractError(
            "committed D7 C1/C2 lineage differs from the recorded pins"
        )
    receipt = loaded.receipt.to_dict()
    c1_binding = receipt.get("c1_bundle")
    if (
        not isinstance(c1_binding, Mapping)
        or c1_binding.get("repository_path") != _RECORDED_C1_REPOSITORY_PATH
        or c1_binding.get("canonical_sha256") != D7_RECORDED_C1_CANONICAL_SHA256
        or c1_binding.get("component_set_sha256") != D7_RECORDED_C1_COMPONENT_SET_SHA256
    ):
        raise QualificationContractError(
            "recorded C2 does not bind the pinned D7 C1 candidate"
        )
    _verify_recorded_c1_projection(repository_root=repository_root)
    target_source = canonical_json_bytes(_target_document())
    target = D7ReplayTargetContractSpec(
        _factory_token=_TARGET_FACTORY_TOKEN,
        canonical_bytes=target_source,
    )
    attempt_source = canonical_json_bytes(_attempt_document(target))
    attempt = D7AttemptEnvelopeContractSpec(
        _factory_token=_ENVELOPE_FACTORY_TOKEN,
        canonical_bytes=attempt_source,
        target_contract=target,
    )
    return LoadedD7ReplayAttemptContractFoundation(
        _factory_token=_FOUNDATION_FACTORY_TOKEN,
        replay_target_contract=target,
        attempt_envelope_contract=attempt,
        c1_commit=loaded.c1_commit,
        c2_commit=loaded.c2_commit,
        validation_current_head=loaded.current_head,
    )


__all__ = [
    "D7_ATTEMPT_ENVELOPE_CONTRACT_SCHEMA_VERSION",
    "D7_RECORDED_C1_CANONICAL_SHA256",
    "D7_RECORDED_C1_COMPONENT_SET_SHA256",
    "D7_RECORDED_C1_POST_MERGE_COMMIT",
    "D7_RECORDED_C2_CANONICAL_SHA256",
    "D7_RECORDED_C2_INTRODUCTION_COMMIT",
    "D7_REPLAY_TARGET_CONTRACT_SCHEMA_VERSION",
    "MAX_D7_REPLAY_CONTRACT_BYTES",
    "D7AttemptEnvelopeContractSpec",
    "D7ReplayTargetContractSpec",
    "LoadedD7ReplayAttemptContractFoundation",
    "load_d7_replay_attempt_contract_foundation",
]
