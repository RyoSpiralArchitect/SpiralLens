from __future__ import annotations

import copy
import inspect
import pickle
import subprocess
from collections.abc import Mapping
from pathlib import Path

import pytest

from spirallens import qualification
from spirallens.core.canonical import canonical_json_bytes, sha256_bytes
from spirallens.qualification import confirmation_official_execution as official
from spirallens.qualification import confirmation_preseed_authority as item21
from spirallens.qualification import confirmation_replay_contracts as replay
from spirallens.qualification import (
    confirmation_seed_supply_contracts as contracts_module,
)
from spirallens.qualification import persistence, preparation
from spirallens.qualification.common import QualificationContractError
from spirallens.qualification.confirmation_seed_supply_contracts import (
    D7_ITEM22_ATOMIC_TARGET_DIRECTORY_REPOSITORY_PATH,
    D7_ITEM22_ATOMIC_TARGET_MEMBER_LAYOUT,
    D7_ITEM22_CURRENT_SOURCE_RUNTIME_REANCHOR_REPOSITORY_PATH,
    D7_ITEM22_EXCLUSIVE_SEED_SUPPLY_CLAIM_REPOSITORY_PATH,
    D7_ITEM22_FULL_DESIGN_FREEZE_REPOSITORY_PATH,
    D7_ITEM22_FUTURE_LAUNCH_DESCRIPTOR_REPOSITORY_PATH,
    D7_ITEM22_SEED_SUPPLY_ABORT_EVIDENCE_REPOSITORY_PATH,
    D7_ITEM22_SEED_SUPPLY_DIRECTORY_REPOSITORY_PATH,
    D7_ITEM22_SEED_SUPPLY_TRANSACTION_CONTRACT_SCHEMA_VERSION,
    D7_ITEM22_SINGLE_SUPPLIER_INVOCATION_REPOSITORY_PATH,
    D7Item22SeedSupplyTransactionContractSpec,
    LoadedD7Item22SeedSupplyContractFoundation,
    load_d7_item22_seed_supply_contract_foundation,
)

REPOSITORY = Path(__file__).resolve().parents[1]


def _git(root: Path, *arguments: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(root), *arguments],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _configure_git(root: Path) -> None:
    _git(root, "config", "user.name", "SpiralLens Test")
    _git(root, "config", "user.email", "spirallens@example.invalid")


def _clean_clone(destination: Path) -> Path:
    assert not destination.exists()
    subprocess.run(
        [
            "git",
            "clone",
            "--quiet",
            "--no-hardlinks",
            str(REPOSITORY),
            str(destination),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    _configure_git(destination)
    assert _git(destination, "status", "--short") == ""
    return destination


def _commit(root: Path, message: str, *repository_paths: str) -> str:
    _git(root, "add", *repository_paths)
    _git(root, "commit", "--quiet", "-m", message)
    return _git(root, "rev-parse", "HEAD")


def _mapping_keys(value: object) -> set[str]:
    if isinstance(value, Mapping):
        return set(value).union(
            *(_mapping_keys(item) for item in value.values()),
            set(),
        )
    if isinstance(value, list):
        return set().union(*(_mapping_keys(item) for item in value), set())
    return set()


@pytest.fixture(scope="module")
def clean_repository(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return _clean_clone(
        tmp_path_factory.mktemp("d7-item22-seed-supply-contract") / "repository"
    )


@pytest.fixture(scope="module")
def loaded_foundation(
    clean_repository: Path,
) -> LoadedD7Item22SeedSupplyContractFoundation:
    return load_d7_item22_seed_supply_contract_foundation(
        repository_root=clean_repository
    )


def test_loader_is_choice_free_deep_internal_and_non_operational(
    loaded_foundation: LoadedD7Item22SeedSupplyContractFoundation,
) -> None:
    signature = inspect.signature(load_d7_item22_seed_supply_contract_foundation)

    assert tuple(signature.parameters) == ("repository_root",)
    assert signature.parameters["repository_root"].kind is (
        inspect.Parameter.KEYWORD_ONLY
    )
    assert contracts_module.__all__ == ()
    assert not hasattr(qualification, "load_d7_item22_seed_supply_contract_foundation")
    public_functions = {
        name
        for name, value in vars(contracts_module).items()
        if inspect.isfunction(value) and not name.startswith("_")
    }
    assert public_functions == {"load_d7_item22_seed_supply_contract_foundation"}

    assert {
        name
        for name in dir(loaded_foundation)
        if not name.startswith("_") and callable(getattr(loaded_foundation, name))
    } == set()
    for forbidden_surface in (
        "claim",
        "claim_token",
        "transition",
        "transition_token",
        "acquire_claim",
        "invoke_supplier",
        "publish_target",
        "persist",
    ):
        assert not hasattr(loaded_foundation, forbidden_surface)

    assert loaded_foundation.historical_item21_chain_verified is True
    assert loaded_foundation.historical_family_admission_evidence_verified is True
    assert loaded_foundation.historical_family_admission_promoted_to_authority is False
    for name in (
        "current_source_runtime_verified",
        "current_source_runtime_reanchor_present",
        "concrete_supplier_identity_present",
        "concrete_supplier_identity_verified",
        "seed_supply_claim_acquired",
        "supplier_invoked",
        "official_seed_inventory_present",
        "atomic_target_present",
        "seed_supply_aborted",
        "full_design_freeze_present",
        "launch_intent_present",
        "reusable_authorization_capability_present",
        "execution_observed",
        "scientific_claim_eligible",
        "d7_execution_authorized",
        "d8_execution_authorized",
    ):
        assert getattr(loaded_foundation, name) is False


def test_contract_roundtrips_only_as_the_exact_closed_specification(
    loaded_foundation: LoadedD7Item22SeedSupplyContractFoundation,
) -> None:
    contract = loaded_foundation.transaction_contract
    restored = D7Item22SeedSupplyTransactionContractSpec.from_canonical_bytes(
        contract.canonical_bytes,
        expected_sha256=contract.canonical_sha256,
    )

    assert restored.schema_version == (
        D7_ITEM22_SEED_SUPPLY_TRANSACTION_CONTRACT_SCHEMA_VERSION
    )
    assert restored.canonical_bytes == contract.canonical_bytes
    assert restored.canonical_sha256 == contract.canonical_sha256
    assert restored.to_dict() == contract.to_dict()

    mutable = restored.to_dict()
    mutable["status"] = "forged"
    assert restored.to_dict()["status"] == (
        "contract-defined-operational-instance-absent"
    )


def test_contract_and_foundation_are_sealed_against_direct_construction_copy_pickle(
    loaded_foundation: LoadedD7Item22SeedSupplyContractFoundation,
) -> None:
    contract = loaded_foundation.transaction_contract

    with pytest.raises(QualificationContractError, match="closed factory"):
        D7Item22SeedSupplyTransactionContractSpec(
            canonical_bytes=contract.canonical_bytes
        )
    with pytest.raises(QualificationContractError, match="strict historical"):
        LoadedD7Item22SeedSupplyContractFoundation(
            transaction_contract=contract,
            source_runtime_receipt_commit=(
                loaded_foundation.source_runtime_receipt_commit
            ),
            seed_free_readiness_commit=loaded_foundation.seed_free_readiness_commit,
            reviewed_family_admission_commit=(
                loaded_foundation.reviewed_family_admission_commit
            ),
            validation_current_head=loaded_foundation.validation_current_head,
        )

    for value in (contract, loaded_foundation):
        with pytest.raises(TypeError, match="cannot be copied"):
            copy.copy(value)
        with pytest.raises(TypeError, match="cannot be copied"):
            copy.deepcopy(value)
        with pytest.raises(TypeError, match="not pickleable"):
            pickle.dumps(value)


def test_layout_freezes_exact_six_member_durable_publication_bundle(
    loaded_foundation: LoadedD7Item22SeedSupplyContractFoundation,
) -> None:
    document = loaded_foundation.transaction_contract.to_dict()
    layout = document["fixed_repository_layout"]

    assert layout["preclaim_current_source_runtime_reanchor"] == (
        D7_ITEM22_CURRENT_SOURCE_RUNTIME_REANCHOR_REPOSITORY_PATH
    )
    assert layout["seed_supply_namespace"] == (
        D7_ITEM22_SEED_SUPPLY_DIRECTORY_REPOSITORY_PATH
    )
    assert layout["exclusive_claim"] == (
        D7_ITEM22_EXCLUSIVE_SEED_SUPPLY_CLAIM_REPOSITORY_PATH
    )
    assert layout["atomic_target_directory"] == (
        D7_ITEM22_ATOMIC_TARGET_DIRECTORY_REPOSITORY_PATH
    )
    assert layout["single_supplier_invocation"] == (
        D7_ITEM22_SINGLE_SUPPLIER_INVOCATION_REPOSITORY_PATH
    )
    assert layout["seed_supply_abort_evidence"] == (
        D7_ITEM22_SEED_SUPPLY_ABORT_EVIDENCE_REPOSITORY_PATH
    )
    assert layout["full_design_freeze"] == (
        D7_ITEM22_FULL_DESIGN_FREEZE_REPOSITORY_PATH
    )
    assert layout["future_launch_descriptor"] == (
        D7_ITEM22_FUTURE_LAUNCH_DESCRIPTOR_REPOSITORY_PATH
    )
    assert layout["closed_member_count"] == 6
    assert layout["unknown_atomic_target_members_allowed"] is False
    assert layout["alternate_repository_paths_allowed"] is False

    expected_layout = [
        ("official-seed-inventory", "official-seed-inventory.json"),
        ("full-inventory", "full-inventory.json"),
        ("full-design", "full-design.json"),
        ("replay-target", "replay-target.json"),
        ("single-supplier-invocation", "single-supplier-invocation.json"),
        ("transaction-manifest", "transaction-manifest.json"),
    ]
    assert list(D7_ITEM22_ATOMIC_TARGET_MEMBER_LAYOUT) == expected_layout
    members = layout["atomic_target_members"]
    assert [
        (member["artifact_role"], member["filename"]) for member in members
    ] == expected_layout
    assert [member["ordinal"] for member in members] == list(range(6))
    assert all(
        member["repository_path"].startswith(
            f"{D7_ITEM22_ATOMIC_TARGET_DIRECTORY_REPOSITORY_PATH}/"
        )
        for member in members
    )

    assert not D7_ITEM22_CURRENT_SOURCE_RUNTIME_REANCHOR_REPOSITORY_PATH.startswith(
        f"{D7_ITEM22_SEED_SUPPLY_DIRECTORY_REPOSITORY_PATH}/"
    )
    assert not D7_ITEM22_FUTURE_LAUNCH_DESCRIPTOR_REPOSITORY_PATH.startswith(
        f"{D7_ITEM22_SEED_SUPPLY_DIRECTORY_REPOSITORY_PATH}/"
    )


def test_durable_bundle_and_three_role_chronology_core_remain_distinct(
    loaded_foundation: LoadedD7Item22SeedSupplyContractFoundation,
) -> None:
    target = loaded_foundation.transaction_contract.to_dict()["atomic_target_contract"]

    assert target["member_roles_in_order"] == [
        "official-seed-inventory",
        "full-inventory",
        "full-design",
        "replay-target",
        "single-supplier-invocation",
        "transaction-manifest",
    ]
    assert target["chronology_publication_subject_roles"] == [
        "official-seed-inventory",
        "full-design",
        "replay-target",
    ]
    assert (
        target["durable_members_and_chronology_subjects_are_distinct_surfaces"] is True
    )
    assert target["manifest_binds_every_other_member"] is True
    assert target["manifest_may_bind_itself"] is False
    assert target["atomic_no_replace_directory_publication_required"] is True
    assert target["partial_target_visibility_allowed"] is False
    assert target["target_member_replacement_allowed"] is False


def test_claim_is_precall_reservation_and_invocation_receipt_is_postcall_evidence(
    loaded_foundation: LoadedD7Item22SeedSupplyContractFoundation,
) -> None:
    target = loaded_foundation.transaction_contract.to_dict()["atomic_target_contract"]

    assert target["exclusive_claim_is_durable_pre_call_reservation"] is True
    assert target["single_supplier_invocation_member_is_post_call_evidence"] is True
    assert target["single_supplier_invocation_member_binds_claim"] is True
    assert target["single_supplier_invocation_member_binds_supplier_identity"] is True
    assert target["single_supplier_invocation_member_binds_official_inventory"] is True
    assert target["single_supplier_invocation_member_is_inside_atomic_target"] is True


def test_atomic_bundle_rejoins_exact_internal_member_bytes(
    loaded_foundation: LoadedD7Item22SeedSupplyContractFoundation,
) -> None:
    target = loaded_foundation.transaction_contract.to_dict()["atomic_target_contract"]

    assert target["required_internal_digest_edges"] == [
        {
            "subject_role": "full-inventory",
            "binding_field": "official_seed_inventory_sha256",
            "object_role": "official-seed-inventory",
        },
        {
            "subject_role": "full-design",
            "binding_field": "official_seed_inventory_sha256",
            "object_role": "official-seed-inventory",
        },
        {
            "subject_role": "full-design",
            "binding_field": "full_inventory_sha256",
            "object_role": "full-inventory",
        },
        {
            "subject_role": "replay-target",
            "binding_field": "official_seed_inventory_binding",
            "object_role": "official-seed-inventory",
        },
        {
            "subject_role": "replay-target",
            "binding_field": "full_design_binding.design_binding",
            "object_role": "full-design",
        },
        {
            "subject_role": "replay-target",
            "binding_field": "full_design_binding.inventory_binding",
            "object_role": "full-inventory",
        },
        {
            "subject_role": "replay-target",
            "binding_field": "full_design_binding.inventory_sha256",
            "object_role": "full-inventory",
        },
        {
            "subject_role": "replay-target",
            "binding_field": "full_design_binding.official_seed_inventory_sha256",
            "object_role": "official-seed-inventory",
        },
        {
            "subject_role": "single-supplier-invocation",
            "binding_field": "official_seed_inventory_binding",
            "object_role": "official-seed-inventory",
        },
    ]
    for field in (
        "all_required_internal_edges_must_rejoin_exact_member_bytes",
        "member_bytes_must_reconstruct_existing_exact_record_contracts",
        "reconstruction_must_equal_canonical_member_bytes",
        "chronology_subject_bindings_must_equal_member_bytes",
        "manifest_binds_other_member_digest_and_byte_count",
    ):
        assert target[field] is True
    assert target["unknown_internal_binding_edges_allowed"] is False
    assert target["existing_caller_constructible_records_supply_authority"] is False


def test_future_durability_requires_fsync_but_proves_no_power_loss_semantics(
    loaded_foundation: LoadedD7Item22SeedSupplyContractFoundation,
) -> None:
    durability = loaded_foundation.transaction_contract.to_dict()["durability_contract"]

    for field in (
        "requirements_apply_only_to_future_operational_code",
        "seed_supply_namespace_created_before_claim",
        "seed_supply_namespace_parent_fsync_after_creation_before_claim",
        "claim_file_data_and_metadata_fsync_before_supplier_call",
        "claim_parent_directory_fsync_before_supplier_call",
        "target_staging_directory_must_share_publication_parent_filesystem",
        "each_target_member_data_and_metadata_fsync_before_publication",
        "target_staging_directory_fsync_before_publication",
        "no_replace_directory_rename_required",
        "publication_parent_directory_fsync_before_success_return",
        "abort_file_data_and_metadata_fsync_before_established_state",
        "abort_parent_directory_fsync_before_established_state",
        "abort_established_success_not_returned_before_parent_fsync",
        "crash_recovery_uses_exact_state_observation_table",
    ):
        assert durability[field] is True
    assert durability["invalid_recovery_state_authorizes_supplier_retry"] is False
    assert durability["crash_recovery_authorizes_supplier_retry"] is False
    assert durability["power_loss_survival_proved_by_this_specification"] is False
    assert durability["filesystem_fsync_semantics_authenticated"] is False


def test_state_machine_freezes_nonretryable_and_abort_evidence_boundaries(
    loaded_foundation: LoadedD7Item22SeedSupplyContractFoundation,
) -> None:
    document = loaded_foundation.transaction_contract.to_dict()
    chronology = document["chronology_contract"]
    transitions = document["state_transition_contract"]
    observations = transitions["state_observation_contract"]
    abort = document["claim_and_abort_contract"]

    assert chronology["closed_state_vocabulary"] == [
        "preclaim",
        "claim-present-publication-absent-nonretryable",
        "seed-supply-aborted-established",
        "publication-complete-unfrozen",
        "full-design-frozen",
        "launch-intent-present",
    ]
    assert chronology["ordered_transitions"] == [
        "final-lifecycle-result-terminal-runner-code-reviewed",
        "exact-execution-source-runtime-closure",
        "seed-free-readiness",
        "reviewed-family-admission",
        "exclusive-seed-supply-claim",
        "single-supplier-invocation",
        "atomic-seed-bearing-full-design-and-target-publication",
        "committed-full-design-freeze-receipt",
        "launch-intent",
    ]
    assert chronology["applicable_live_check_internal_immediately_before_claim"] is True
    assert chronology["cached_live_check_accepted_from_caller"] is False
    assert chronology["durable_pre_call_claim_interval_required"] is True
    assert chronology["durable_claim_waiting_state_is_restart_resumable"] is False
    assert chronology["persisted_claim_alone_authorizes_continuation"] is False

    table = transitions["transitions"]
    assert [(row["from"], row["to"]) for row in table] == [
        ("preclaim", "claim-present-publication-absent-nonretryable"),
        (
            "claim-present-publication-absent-nonretryable",
            "publication-complete-unfrozen",
        ),
        (
            "claim-present-publication-absent-nonretryable",
            "seed-supply-aborted-established",
        ),
        ("publication-complete-unfrozen", "full-design-frozen"),
        ("full-design-frozen", "launch-intent-present"),
    ]
    assert table[0]["originating_operation_only"] is True
    assert table[1]["originating_operation_only"] is True
    assert table[2]["originating_operation_only"] is True
    assert transitions["restart_entrant_from_claim_state_allowed"] is False
    assert transitions["restart_entrant_may_invoke_supplier"] is False
    assert (
        transitions["claim_state_successor_success_requires_same_originating_operation"]
        is True
    )
    assert transitions["abort_established_is_terminal"] is True
    assert transitions["abort_established_outgoing_transitions"] == []
    assert transitions["failure_to_persist_abort_restores_retry"] is False
    assert transitions[
        "abort_persistence_failure_before_established_return_retains_state"
    ] == ("claim-present-publication-absent-nonretryable")
    assert transitions["post_publication_failure_state"] == (
        "publication-complete-unfrozen"
    )
    assert transitions["post_publication_failure_is_seed_supply_abort"] is False
    assert transitions["post_publication_supplier_retry_authorized"] is False

    presence_fields = observations["presence_fields_in_order"]
    assert presence_fields == [
        "exclusive_claim_present",
        "atomic_target_present",
        "abort_evidence_present",
        "full_design_freeze_present",
        "launch_intent_present",
    ]
    rows = observations["rows"]
    assert [row["state"] for row in rows] == chronology["closed_state_vocabulary"]
    observed_presence = {
        tuple(row[field] for field in presence_fields): row["state"] for row in rows
    }
    assert observed_presence == {
        (False, False, False, False, False): "preclaim",
        (True, False, False, False, False): (
            "claim-present-publication-absent-nonretryable"
        ),
        (True, False, True, False, False): "seed-supply-aborted-established",
        (True, True, False, False, False): "publication-complete-unfrozen",
        (True, True, False, True, False): "full-design-frozen",
        (True, True, False, True, True): "launch-intent-present",
    }
    assert len(observed_presence) == len(rows) == 6
    assert (True, True, True, False, False) not in observed_presence
    assert (
        observations["all_present_artifacts_require_valid_canonical_strict_reload"]
        is True
    )
    assert observations["unlisted_presence_combination_is_contract_error"] is True
    assert observations["invalid_or_partial_artifact_is_contract_error"] is True
    assert (
        observations["claim_missing_with_downstream_artifact_is_contract_error"] is True
    )
    assert (
        observations["atomic_target_and_abort_evidence_are_mutually_exclusive"] is True
    )
    assert (
        observations["atomic_target_and_abort_evidence_coexistence_is_contract_error"]
        is True
    )
    assert observations["recovery_precedence_rule_present"] is False
    assert observations["recovery_contract_error_authorizes_supplier_retry"] is False

    assert abort["claim_without_atomic_target_state"] == (
        "claim-present-publication-absent-nonretryable"
    )
    assert abort["claim_without_atomic_target_retry_authorized"] is False
    assert abort["claim_state_may_be_active_same_origin_or_orphaned"] is True
    assert (
        abort["active_originating_operation_claim_without_target_is_semantic_abort"]
        is False
    )
    assert abort["ended_originating_operation_without_target_is_semantic_abort"] is True
    assert abort["restart_observation_claim_without_target_is_semantic_abort"] is True
    assert abort["semantic_seed_supply_abort_is_durable_abort_evidence"] is False
    assert abort["claim_deletion_authorizes_retry"] is False
    assert abort["target_absence_proves_supplier_invoked"] is False
    assert abort["target_absence_proves_supplier_not_invoked"] is False
    assert abort["claim_without_target_establishes_abort_evidence"] is False
    assert abort["abort_evidence_established_state"] == (
        "seed-supply-aborted-established"
    )
    assert abort["abort_evidence_is_a_separate_record"] is True
    assert abort["separate_abort_evidence_authorizes_retry"] is False


def test_later_item22_spec_explicitly_refines_the_historical_blanket_abort_phrase(
    loaded_foundation: LoadedD7Item22SeedSupplyContractFoundation,
    clean_repository: Path,
) -> None:
    refinement = loaded_foundation.transaction_contract.to_dict()[
        "historical_replay_target_contract_refinement"
    ]

    assert refinement == {
        "earlier_source_repository_path": (
            "src/spirallens/qualification/confirmation_replay_contracts.py"
        ),
        "earlier_schema_version": "spirallens.d7-replay-target-contract-spec.v0.1",
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
        "this_later_specification_refines_future_item22_operational_semantics": True,
        "refinement_kind": (
            "active-versus-ended-origin-and-durable-evidence-separation"
        ),
        "active_originating_operation_claim_without_target_is_semantic_abort": False,
        "ended_originating_operation_without_target_is_semantic_abort": True,
        "restart_observation_claim_without_target_is_semantic_abort": True,
        "semantic_abort_is_durable_abort_evidence": False,
        "durable_state_without_valid_abort_receipt": (
            "claim-present-publication-absent-nonretryable"
        ),
        "future_item22_operational_code_must_use_refined_semantics": True,
        "earlier_unqualified_phrase_may_authorize_future_behavior": False,
    }

    earlier = replay.load_d7_replay_attempt_contract_foundation(
        repository_root=clean_repository
    ).replay_target_contract
    earlier_document = earlier.to_dict()
    assert earlier_document["schema_version"] == refinement["earlier_schema_version"]
    assert earlier_document["contract_id"] == refinement["earlier_contract_id"]
    assert earlier.canonical_sha256 == refinement["earlier_canonical_sha256"]
    assert len(earlier.canonical_bytes) == refinement["earlier_canonical_byte_count"]
    assert (
        earlier_document["seed_supply_chronology_contract"][
            "claim_without_target_is_seed_supply_aborted"
        ]
        is refinement["earlier_field_value"]
    )


def test_future_claim_key_scheme_is_fixed_but_no_identity_or_key_exists(
    loaded_foundation: LoadedD7Item22SeedSupplyContractFoundation,
) -> None:
    document = loaded_foundation.transaction_contract.to_dict()
    boundary = document["transaction_boundary"]
    derivation = document["future_exclusive_claim_key_derivation"]

    assert boundary["concrete_supplier_identity_present"] is False
    assert (
        boundary["concrete_supplier_identity_mandatory_before_exclusive_claim"] is True
    )
    assert boundary["concrete_exclusive_claim_key_value_present"] is False
    assert (
        boundary["concrete_exclusive_claim_key_value_mandatory_before_exclusive_claim"]
        is True
    )
    assert boundary["opaque_caller_supplier_binding_sufficient"] is False
    assert boundary["existing_caller_constructible_claim_input_promotable"] is False
    assert (
        boundary["existing_caller_constructible_invocation_input_promotable"] is False
    )

    assert derivation["scheme_schema_version"] == (
        "spirallens.d7-item22-exclusive-seed-supply-claim-key.v0.1"
    )
    assert derivation["digest_algorithm"] == "sha256"
    assert derivation["canonical_json_input_required"] is True
    assert derivation["exclusive_claim_repository_path"] == (
        D7_ITEM22_EXCLUSIVE_SEED_SUPPLY_CLAIM_REPOSITORY_PATH
    )
    assert derivation["input_roles_in_order"] == [
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
    ]
    assert derivation["preimage_is_one_exact_top_level_object"] is True
    assert derivation["preimage_exact_keys"] == [
        "schema_version",
        "domain_separator",
        "exclusive_claim_repository_path",
        "historical_item21_bindings",
        "reviewed_current_source_runtime_reanchor_binding",
        "supplier_identity_binding",
        "development_seed_exclusion_registry_binding",
        "parent_selection_seed_exclusion_registry_binding",
    ]
    assert derivation["unknown_preimage_fields_allowed"] is False
    assert derivation["alternate_array_or_role_keyed_encoding_allowed"] is False
    assert derivation["historical_item21_bindings_must_equal_exact_pinned_list"] is True
    assert derivation["historical_item21_binding_exact_keys"] == [
        "artifact_role",
        "repository_path",
        "schema_version",
        "canonical_sha256",
        "byte_count",
        "introduction_commit",
    ]
    assert derivation["dynamic_binding_projection_schema_version"] == (
        "spirallens.d7-item22-claim-key-binding-projection.v0.1"
    )
    assert derivation["dynamic_binding_projection_exact_keys"] == [
        "schema_version",
        "artifact_role",
        "artifact_contract_id",
        "canonical_sha256",
        "byte_count",
    ]
    assert derivation["dynamic_binding_roles_by_preimage_field"] == {
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
    }
    assert derivation["authority_or_provenance_flags_part_of_key"] is False
    assert derivation["reviewed_reanchor_repository_path"] == (
        D7_ITEM22_CURRENT_SOURCE_RUNTIME_REANCHOR_REPOSITORY_PATH
    )
    assert derivation["supplier_identity_artifact_role"] == ("seed-supplier-identity")
    for name in (
        "concrete_reanchor_binding_present",
        "concrete_supplier_identity_present",
        "concrete_claim_key_value_present",
        "claim_key_derived_by_this_specification",
        "caller_supplied_claim_key_accepted",
    ):
        assert derivation[name] is False


def test_cross_host_ceiling_requires_future_idempotency_or_coordination(
    loaded_foundation: LoadedD7Item22SeedSupplyContractFoundation,
) -> None:
    scope = loaded_foundation.transaction_contract.to_dict()["exclusivity_scope"]

    assert scope["repository_local_no_replace_reservation_required"] is True
    assert scope["cross_process_same_filesystem_exclusivity_contract_required"] is True
    assert scope["cross_host_global_exclusivity_proved"] is False
    assert scope["distributed_filesystem_exclusivity_proved"] is False
    assert scope["supplier_global_idempotency_proved"] is False
    assert (
        scope["future_supplier_idempotency_or_external_coordination_required"] is True
    )
    assert scope["local_claim_bytes_alone_are_global_authority"] is False


def test_foundation_keeps_historical_admission_separate_from_all_false_authority(
    loaded_foundation: LoadedD7Item22SeedSupplyContractFoundation,
) -> None:
    document = loaded_foundation.transaction_contract.to_dict()
    historical = document["historical_item21_foundation"]

    assert [artifact["artifact_role"] for artifact in historical["artifacts"]] == [
        "execution-source-runtime-receipt",
        "seed-free-readiness",
        "family-admission-receipt",
    ]
    assert historical["complete_non_shallow_history_required"] is True
    assert historical["historical_reload_required_for_loaded_foundation"] is True
    assert historical["canonical_contract_bytes_alone_prove_historical_reload"] is False
    assert (
        historical["historical_family_admission_evidence_may_be_recorded_separately"]
        is True
    )
    assert (
        historical["historical_family_admission_evidence_is_current_authority"] is False
    )
    assert historical["current_live_readiness_inherited_from_item21"] is False
    assert historical["caller_supplied_item21_snapshot_accepted"] is False

    assert set(document["authority"].values()) == {False}
    assert document["authority"]["confirmation_family_admitted"] is False
    assert set(document["current_instance_state"].values()) == {False}
    assert document["d7_state"] == "not_run"
    assert document["d8_state"] == "not_run"
    assert loaded_foundation.historical_family_admission_evidence_verified is True
    assert loaded_foundation.historical_family_admission_promoted_to_authority is False


def test_contract_contains_no_instance_values_callback_or_persistence_surface(
    loaded_foundation: LoadedD7Item22SeedSupplyContractFoundation,
) -> None:
    document = loaded_foundation.transaction_contract.to_dict()
    boundary = document["transaction_boundary"]

    assert boundary["foundation_loader_parameters"] == ["repository_root"]
    assert boundary["choice_bearing_parameters_accepted"] is False
    assert boundary["standalone_claim_api_present"] is False
    assert boundary["supplier_callback_accepted"] is False
    assert boundary["seed_values_accepted"] is False
    assert boundary["readiness_snapshot_accepted"] is False
    assert boundary["persistence_performed"] is False
    assert boundary["claim_acquired"] is False
    assert boundary["supplier_invoked"] is False
    assert boundary["atomic_target_published"] is False

    assert {
        "seed",
        "seeds",
        "official_seed",
        "supplier_callback",
        "claim_key_value",
        "target_document",
        "persistence_destination",
    }.isdisjoint(_mapping_keys(document))
    honest = document["honest_local_scope"]
    assert honest["historical_item21_repository_history_only"] is True
    assert set(
        value
        for key, value in honest.items()
        if key != ("historical_item21_repository_history_only")
    ) == {False}


def test_loader_reads_history_without_operational_calls_or_filesystem_writes(
    clean_repository: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbidden_operation(*args: object, **kwargs: object) -> None:
        del args, kwargs
        pytest.fail("item-22 foundation loader reached an operational surface")

    for name in (
        "verify_current_d7_item21_ready_for_seed_supply",
        "build_d7_item21_source_runtime_receipt",
        "issue_d7_item21_source_runtime_receipt",
        "build_d7_item21_seed_free_readiness",
        "issue_d7_item21_seed_free_readiness",
        "build_d7_item21_reviewed_family_admission",
        "issue_d7_item21_reviewed_family_admission",
        "_atomic_write_no_overwrite",
    ):
        monkeypatch.setattr(item21, name, forbidden_operation)
    for name in (
        "produce_d7_official_result",
        "build_d7_official_full_inventory_document",
        "build_d7_official_aggregation_document",
        "build_d7_official_full_design_document",
    ):
        monkeypatch.setattr(official, name, forbidden_operation)
    for name in (
        "_atomic_write_no_overwrite",
        "write_qualification_protocol",
        "write_qualification_result",
    ):
        monkeypatch.setattr(persistence, name, forbidden_operation)
    monkeypatch.setattr(
        preparation,
        "prepare_closed_d0_d5_selection_protocol",
        forbidden_operation,
    )

    reserved_paths = (
        clean_repository / D7_ITEM22_CURRENT_SOURCE_RUNTIME_REANCHOR_REPOSITORY_PATH,
        clean_repository / D7_ITEM22_SEED_SUPPLY_DIRECTORY_REPOSITORY_PATH,
        clean_repository / D7_ITEM22_FUTURE_LAUNCH_DESCRIPTOR_REPOSITORY_PATH,
    )
    assert all(not path.exists() for path in reserved_paths)
    status_before = _git(clean_repository, "status", "--short")
    paths_before = {
        path.relative_to(clean_repository).as_posix()
        for path in clean_repository.rglob("*")
    }

    loaded = load_d7_item22_seed_supply_contract_foundation(
        repository_root=clean_repository
    )

    assert loaded.historical_item21_chain_verified is True
    assert all(not path.exists() for path in reserved_paths)
    assert _git(clean_repository, "status", "--short") == status_before == ""
    assert {
        path.relative_to(clean_repository).as_posix()
        for path in clean_repository.rglob("*")
    } == paths_before


def test_rehashed_mutation_bool_integer_and_noncanonical_bytes_are_rejected(
    loaded_foundation: LoadedD7Item22SeedSupplyContractFoundation,
) -> None:
    contract = loaded_foundation.transaction_contract

    mutated = contract.to_dict()
    mutated["claim_and_abort_contract"][
        "claim_without_atomic_target_retry_authorized"
    ] = True
    mutated_source = canonical_json_bytes(mutated)
    with pytest.raises(QualificationContractError, match="closed specification"):
        D7Item22SeedSupplyTransactionContractSpec.from_canonical_bytes(
            mutated_source,
            expected_sha256=sha256_bytes(mutated_source),
        )

    integer_laundered = contract.to_dict()
    integer_laundered["transaction_boundary"]["claim_acquired"] = 0
    integer_source = canonical_json_bytes(integer_laundered)
    with pytest.raises(QualificationContractError, match="closed specification"):
        D7Item22SeedSupplyTransactionContractSpec.from_canonical_bytes(
            integer_source,
            expected_sha256=sha256_bytes(integer_source),
        )

    extended = contract.to_dict()
    extended["unreviewed_extension"] = False
    extended_source = canonical_json_bytes(extended)
    with pytest.raises(QualificationContractError, match="closed specification"):
        D7Item22SeedSupplyTransactionContractSpec.from_canonical_bytes(
            extended_source,
            expected_sha256=sha256_bytes(extended_source),
        )

    with pytest.raises(QualificationContractError, match="SHA-256 differs"):
        D7Item22SeedSupplyTransactionContractSpec.from_canonical_bytes(
            contract.canonical_bytes,
            expected_sha256="0" * 64,
        )

    noncanonical = contract.canonical_bytes.replace(b"{", b"{ ", 1)
    with pytest.raises(QualificationContractError):
        D7Item22SeedSupplyTransactionContractSpec.from_canonical_bytes(
            noncanonical,
            expected_sha256=sha256_bytes(noncanonical),
        )


def test_loader_rejoins_every_pinned_item21_artifact(
    clean_repository: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pins = list(contracts_module._ITEM21_ARTIFACT_PINS)
    first = list(pins[0])
    first[3] = "f" * 64
    pins[0] = tuple(first)
    monkeypatch.setattr(contracts_module, "_ITEM21_ARTIFACT_PINS", tuple(pins))

    with pytest.raises(QualificationContractError, match="item-22 contract pins"):
        load_d7_item22_seed_supply_contract_foundation(repository_root=clean_repository)


def test_loader_rejoins_fixed_paths_to_the_item21_owner(
    clean_repository: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        item21,
        "D7_ITEM22_SEED_SUPPLY_DIRECTORY_REPOSITORY_PATH",
        "wrong/item22-seed-supply",
    )
    with pytest.raises(QualificationContractError, match="item-21 owner"):
        load_d7_item22_seed_supply_contract_foundation(repository_root=clean_repository)


def test_descendant_source_change_preserves_history_only_contract_and_no_authority(
    tmp_path: Path,
) -> None:
    root = _clean_clone(tmp_path / "descendant-source")
    before = load_d7_item22_seed_supply_contract_foundation(repository_root=root)

    probe = root / "src" / "spirallens" / "qualification" / "item22_probe.py"
    probe.write_text(
        '"""A descendant source change requiring a later reviewed re-anchor."""\n',
        encoding="utf-8",
    )
    _commit(root, "test descendant source", str(probe.relative_to(root)))

    with pytest.raises(
        QualificationContractError,
        match="current execution-source inventory differs from the frozen source commit",
    ):
        item21.verify_current_d7_item21_ready_for_seed_supply(root)

    after = load_d7_item22_seed_supply_contract_foundation(repository_root=root)
    assert after.validation_current_head != before.validation_current_head
    assert (
        after.transaction_contract.canonical_bytes
        == before.transaction_contract.canonical_bytes
    )
    assert after.historical_item21_chain_verified is True
    assert after.current_source_runtime_verified is False
    assert after.current_source_runtime_reanchor_present is False
    assert after.seed_supply_claim_acquired is False


def test_hidden_inherited_item21_mutation_is_rejected_even_when_head_bytes_match(
    tmp_path: Path,
) -> None:
    root = _clean_clone(tmp_path / "hidden-history")
    base = _git(root, "rev-parse", "HEAD")
    repository_path = item21.D7_ITEM21_SOURCE_RUNTIME_RECEIPT_REPOSITORY_PATH
    artifact_path = root / repository_path
    expected = artifact_path.read_bytes()

    _git(root, "checkout", "--quiet", "-b", "hidden-item21-mutation")
    artifact_path.write_bytes(expected + b" ")
    _commit(root, "hidden item-21 mutation", repository_path)

    _git(root, "checkout", "--quiet", "-b", "honest-tip", base)
    _git(
        root,
        "merge",
        "--quiet",
        "--no-ff",
        "--no-commit",
        "hidden-item21-mutation",
    )
    artifact_path.write_bytes(expected)
    _commit(root, "merge while restoring item-21 bytes", repository_path)
    assert artifact_path.read_bytes() == expected

    with pytest.raises(QualificationContractError, match="reachable full Git history"):
        load_d7_item22_seed_supply_contract_foundation(repository_root=root)


def test_shallow_repository_is_rejected_by_inherited_item21_loader(
    tmp_path: Path,
) -> None:
    root = _clean_clone(tmp_path / "shallow-history")
    shallow_path = Path(_git(root, "rev-parse", "--git-path", "shallow"))
    if not shallow_path.is_absolute():
        shallow_path = root / shallow_path
    shallow_path.write_text(
        f"{contracts_module._ITEM21_ARTIFACT_PINS[0][5]}\n",
        encoding="ascii",
    )
    assert _git(root, "rev-parse", "--is-shallow-repository") == "true"

    with pytest.raises(
        QualificationContractError,
        match="complete non-shallow Git history",
    ):
        load_d7_item22_seed_supply_contract_foundation(repository_root=root)
