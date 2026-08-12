from __future__ import annotations

import ast
import builtins
from collections import Counter
from collections.abc import Iterator
import copy
from functools import wraps
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import patch

import pytest

import spirallens
import spirallens.qualification as qualification
from spirallens.core.canonical import canonical_json_bytes, sha256_bytes
from spirallens.qualification import advancement
from spirallens.qualification import confirmation_execution_design as execution_design
from spirallens.qualification import confirmation_protocol
from spirallens.qualification import contracts, freeze, persistence
from spirallens.qualification import (
    confirmation_v1_full_design_referents as referents,
)
from spirallens.qualification import confirmation_v1_materialization as materialization
from spirallens.qualification import confirmation_v1_records as records
from spirallens.qualification import (
    confirmation_v1_source_selected_supplier as selected_supplier,
)
from spirallens.qualification import protocol as qualification_protocol
from spirallens.qualification.common import QualificationContractError


REPOSITORY = Path(__file__).resolve().parents[1]
MODULE_REPOSITORY_PATH = (
    "src/spirallens/qualification/confirmation_v1_full_design_referents.py"
)
MATERIALIZATION_REPOSITORY_PATH = (
    "src/spirallens/qualification/confirmation_v1_materialization.py"
)
PROTOCOL_REPOSITORY_PATH = "protocols/d7_v1_pre_item23_materialization_v0_1.json"
ROUTE_REPOSITORY_PATH = "protocols/voy_v1_v9_strict_successor_route_v0_1.json"
ROOT_KEYS = {
    "schema_version",
    "contract_id",
    "artifact_role",
    "successor_lineage_id",
    "derivation",
    "payload",
    "typestate",
    "claim_boundary",
}
DERIVATION_KEYS = {
    "derivation_id",
    "source_commit",
    "c1_binding",
    "c2_binding",
    "scientific_parent_bindings",
    "scientific_parent_join_sha256",
    "approved_callable",
    "read_contract",
}
ROLE_SPECS = {
    "confirmation-family": (
        "spirallens.d7-v1-confirmation-family-descriptor.v0.1",
        "d7-v1-confirmation-family-descriptor-v0-1",
        {
            "descriptor_id",
            "generator_family_id",
            "case_ids",
            "case_count",
            "seed_slot_ids",
            "identifier_difference_observed",
            "identifier_difference_proves_construction_diversity",
            "source_derived_family_proposal",
            "execution_design_confirmation_family",
        },
    ),
    "family-admission": (
        "spirallens.d7-v1-family-admission-candidate.v0.1",
        "d7-v1-family-admission-candidate-v0-1",
        {
            "admission_candidate_id",
            "status",
            "parent_d6_binding",
            "fresh_confirmation_admission_spec",
            "admission_issued",
            "all_requirements_reviewed",
            "policy_override_allowed",
            "post_selection_exclusion_allowed",
        },
    ),
    "confirmation-protocol": (
        "spirallens.d7-v1-confirmation-protocol-candidate.v0.1",
        "d7-v1-confirmation-protocol-candidate-v0-1",
        {
            "protocol_candidate_id",
            "status",
            "execution_design_schema_version",
            "execution_design_sha256",
            "seed_policy",
            "graph_axes",
            "domain",
            "thresholds",
            "coverage_policy",
            "stress_translation",
            "manifest_compatibility",
            "execution_design",
            "protocol_frozen",
        },
    ),
    "source-graph": (
        "spirallens.d7-v1-source-graph.v0.1",
        "d7-v1-source-graph-v0-1",
        {
            "source_graph_id",
            "source_commit",
            "source_members",
            "source_member_count",
            "source_member_set_sha256",
            "git_declared_source_members_only",
            "runtime_dependency_closure_verified",
            "source_graph_authenticated",
        },
    ),
    "graph-case-stress-aggregation": (
        "spirallens.d7-v1-graph-case-stress-aggregation.v0.1",
        "d7-v1-graph-case-stress-aggregation-v0-1",
        {
            "aggregation_id",
            "inventory",
            "locked_parent_interface",
            "parent_locked_aggregation_sha256",
            "scientific_inventory_counts",
            "field_graph_count",
            "cycle_graph_count",
            "loop_role_count",
            "core_cells_per_primary_unit",
            "loop_cells_per_primary_unit",
            "graph_case_stress_cells_are_repeated_measures",
            "repeated_measures",
            "event_lanes_are_independent_samples",
            "aggregation_rebinding_reviewed",
            "aggregation_rebinding_applied",
        },
    ),
    "lifecycle": (
        "spirallens.d7-v1-lifecycle-policy.v0.1",
        "d7-v1-lifecycle-policy-v0-1",
        {
            "lifecycle_id",
            "status",
            "protocol_future_chronology",
            "ordering_is_policy_only",
            "external_store_observed",
            "external_namespace_reserved",
            "seed_claim_created",
            "official_seed_inventory_created",
            "official_embedded_full_design_created",
            "official_embedded_full_design_frozen",
            "launch_intent_created",
            "attempt_reserved",
            "chronology_receipt_created",
            "official_execution_started",
            "lifecycle_instantiated",
        },
    ),
}
INVENTORY_FIELDS = {
    "family_binding": "confirmation-family",
    "admission_binding": "family-admission",
    "protocol_binding": "confirmation-protocol",
    "source_graph_binding": "source-graph",
    "graph_case_stress_aggregation_binding": "graph-case-stress-aggregation",
    "lifecycle_binding": "lifecycle",
}
TYPESTATE = {
    "virtual_referent_derived": True,
    "binding_resolved": True,
    "binding_authenticated": False,
    "admitted": False,
    "frozen": False,
    "reviewed": False,
    "applied": False,
    "instantiated": False,
    "persisted": False,
}
CLAIM_BOUNDARY = {
    "claim_ceiling": "level_0",
    "claim_delta": "none",
    "authority_granted": False,
    "execution_authorized": False,
    "scientific_claim_eligible": False,
}
FALSE_AXES = {
    "source_reviewed",
    "source_selected",
    "source_closure_established",
    "source_tree_authenticated",
    "runtime_environment_authenticated",
    "runtime_dependency_closure_verified",
    "external_bindings_authenticated",
    "confirmation_family_admitted",
    "confirmation_protocol_frozen",
    "aggregation_rebinding_reviewed",
    "aggregation_rebinding_applied",
    "lifecycle_instantiated",
    "official_embedded_full_design_created",
    "official_embedded_full_design_frozen",
    "materialization_authorized",
    "materialized",
    "publication_authorized",
    "artifacts_published",
    "authority_granted",
    "execution_authorized",
    "execution_started",
    "supplier_invoked",
    "seed_values_present",
    "official_callable_invoked",
    "result_produced",
    "chronology_orchestrated",
    "chronology_receipt_created",
    "chronology_receipt_persisted",
    "scientific_claim_eligible",
}
CHRONOLOGY_KEYS = (
    "artifact_only_commit_a_file_set_reference",
    "design_change_after_receipt_requires_new_version",
    "git_commit_sequence",
    "item23_values_may_select_contract",
    "later_descriptor_may_cure_missing_binding",
    "pre_item23_repository_publication_mode",
    "receipt_generated_last_within_pre_item23_set",
    "receipt_only_git_commit_used",
    "result_only_commit_b_file_reference",
    "same_identity_rescue_retry_allowed",
    "source_change_after_c2_invalidates_current_identity",
    "stages",
)
STAGE_IDS = (
    "reviewed-source-commit",
    "stage-c1-seed-free-source-set-off-repository",
    "stage-c2-source-closure-receipt-off-repository",
    "open-external-staging-root-o-excl-and-fsync",
    "persist-external-exclusive-seed-supply-claim-and-fsync",
    "invoke-fresh-seed-supplier-exactly-once",
    "build-official-seed-inventory-and-embedded-full-design",
    "build-replay-target-and-full-design-freeze",
    "build-launch-intent",
    "persist-separate-domain-pre-start-attempt-reservation-and-fsync",
    "promote-external-store-no-replace-and-reverify-durable-bytes",
    "build-pre-item23-chronology-receipt-last",
    "run-staged-authoritative-joined-loader-hard-gate",
    "atomically-publish-exact-nine-file-repository-set-no-replace",
    "commit-pre-item23-artifact-only-a",
    "run-commit-a-verifier-and-authoritative-joined-loader-hard-gate",
    "fresh-descriptive-result-no-replace-publication",
    "commit-descriptive-result-only-b",
    "run-commit-b-verifier-after-commit-b",
)
EXPECTED_STATIC_FILES = {
    "pyproject.toml": (
        1_698,
        "2e1b8c37167a811c1cee82450700cfe39e13dff64f7cd0c0c6b02fba0d2550ec",
    ),
    "requirements-d7-runtime-lock.txt": (
        119,
        "e9f4dc2380e4729c9e86cd38a1d48bd15efda9304b0cbfa42bd8367fa6575ef7",
    ),
    PROTOCOL_REPOSITORY_PATH: (
        43_288,
        "13d013e007fa30775abb4cd092b264482207dcad23f772aecd966a51cbafbaad",
    ),
    ROUTE_REPOSITORY_PATH: (
        13_806,
        "c8d28138c95d16ab96f508c2386de1d62360e1659057e0b8f7cbe8a380a90e35",
    ),
    "src/spirallens/qualification/confirmation_v1_records.py": (
        80_884,
        "8c0d2b6741e92223b2823245c906ecee0032e267c2730409f96f2cb245a72fa2",
    ),
}
DOCUMENT_BOUNDARY_MARKERS = {
    "README.md": (
        "resolves those six bindings only as canonical virtual referents",
        "exact 19-stage, three-commit future chronology",
        "private, in-memory, and nonpersisted",
        "`external_bindings_authenticated=false`",
        "Claim delta remains `none`; S remains unreviewed and unselected",
    ),
    "docs/ROADMAP.md": (
        "resolves the six non-inventory design bindings only as source-derived virtual referents",
        "exact 19-stage, three-commit future chronology policy",
        "private, in-memory, and nonpersisted",
        "External-binding authentication",
        "S remains unreviewed and unselected; claim delta is `none`",
    ),
    "docs/EXPERIMENT_INTERPRETATION_LEDGER.md": (
        "Six virtual bindings are resolved, but `external_bindings_authenticated=false`",
        "exact 19 ordered stages and three-commit sequence",
        "private, in-memory, and nonpersisted",
        "`none`. Six virtual bindings",
        "S remains unreviewed and unselected",
    ),
    "docs/SCHEMA_CHANGELOG.md": (
        "derives six canonical virtual referents",
        "exact 19-stage, three-commit future chronology",
        "private, in-memory, and nonpersisted",
        "External-binding and runtime authentication",
        "Claim delta is `none`; S remains unselected",
    ),
}


def _load_test_module(name: str, repository_path: str) -> ModuleType:
    existing = sys.modules.get(name)
    if existing is not None:
        return existing
    spec = importlib.util.spec_from_file_location(name, REPOSITORY / repository_path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"cannot load test helpers: {repository_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        sys.modules.pop(name, None)
        raise
    return module


def _materialization_helpers() -> ModuleType:
    return _load_test_module(
        "_spirallens_pr54_materialization_test_helpers",
        "tests/test_d7_v1_materialization.py",
    )


def _deterministic_helpers() -> ModuleType:
    return _load_test_module(
        "_spirallens_pr54_deterministic_test_helpers",
        "tests/test_d7_v1_deterministic_inputs.py",
    )


@pytest.fixture(autouse=True)
def _remove_test_repository_hardlinks(tmp_path: Path) -> Iterator[None]:
    yield
    shutil.rmtree(tmp_path, ignore_errors=True)


def _git(repository: Path, *arguments: str) -> bytes:
    return subprocess.run(
        ("git", "-C", str(repository), *arguments),
        check=True,
        capture_output=True,
    ).stdout


def _run(repository: Path, *arguments: str) -> str:
    return _git(repository, *arguments).decode("utf-8").strip()


def _show(repository: Path, commit: str, repository_path: str) -> bytes:
    return _git(repository, "show", f"{commit}:{repository_path}")


def _canonical(source: bytes) -> dict[str, object]:
    value = json.loads(source)
    assert type(value) is dict
    assert canonical_json_bytes(value) == source
    return value


def _case(tmp_path: Path) -> object:
    return _materialization_helpers()._build_case(tmp_path)


def _bound(record: object) -> records.D7V1ArtifactBinding:
    assert isinstance(record, records._D7V1CanonicalRecord)
    return records.D7V1ArtifactBinding.from_record(record)


def _independent_five_parent_oracle(case: object) -> dict[str, object]:
    policy = case.protocol["historical_input_policy"]
    assert type(policy) is dict
    entries = policy["permitted_historical_scientific_parents"]
    assert type(entries) is list
    roles = tuple(str(entry["artifact_binding_role"]) for entry in entries)
    assert roles == tuple(ROLE_SPECS)[:0] + (
        "parent-protocol",
        "parent-result",
        "parent-manifest",
        "parent-consumption",
        "parent-d6-decision",
    )

    sources: dict[str, bytes] = {}
    documents: dict[str, dict[str, object]] = {}
    bindings: dict[str, records.D7V1ArtifactBinding] = {}
    for entry, role in zip(entries, roles, strict=True):
        assert set(entry) == {
            "artifact_binding_role",
            "artifact_contract_id",
            "authority_for_v1",
            "byte_count",
            "canonical_sha256",
            "descriptive_input_allowed",
            "repository_path",
            "role",
            "source_commit",
        }
        assert entry["role"] == role
        assert entry["authority_for_v1"] is False
        assert entry["descriptive_input_allowed"] is True
        assert (
            subprocess.run(
                (
                    "git",
                    "-C",
                    str(case.repository),
                    "merge-base",
                    "--is-ancestor",
                    str(entry["source_commit"]),
                    case.source_commit,
                ),
                check=False,
                capture_output=True,
            ).returncode
            == 0
        )
        source = _show(
            case.repository,
            str(entry["source_commit"]),
            str(entry["repository_path"]),
        )
        assert len(source) == entry["byte_count"]
        assert sha256_bytes(source) == entry["canonical_sha256"]
        document = _canonical(source)
        assert document["schema_version"] == entry["artifact_contract_id"]
        sources[role] = source
        documents[role] = document
        bindings[role] = records.D7V1ArtifactBinding(
            artifact_role=role,
            artifact_contract_id=str(entry["artifact_contract_id"]),
            canonical_sha256=str(entry["canonical_sha256"]),
            byte_count=int(entry["byte_count"]),
        )

    parent_protocol = qualification_protocol.QualificationProtocol.from_dict(
        documents["parent-protocol"]
    )
    parent_result = contracts.QualificationResult.from_dict(documents["parent-result"])
    parent_manifest = freeze.SelectionTerminalManifestArtifact.from_dict(
        documents["parent-manifest"]
    )
    parent_consumption = freeze.SelectionConsumptionArtifact.from_dict(
        documents["parent-consumption"]
    )
    parent_d6 = advancement.SurrogateAdvancementDecision.from_dict(
        documents["parent-d6-decision"]
    )
    assert parent_protocol.canonical_bytes == sources["parent-protocol"]
    assert parent_result.canonical_bytes == sources["parent-result"]
    assert parent_manifest.canonical_bytes == sources["parent-manifest"]
    assert parent_consumption.canonical_bytes == sources["parent-consumption"]
    assert parent_d6.canonical_bytes == sources["parent-d6-decision"]

    loaded_protocol = persistence.LoadedQualificationProtocol(
        protocol=parent_protocol,
        source_path=(case.repository / str(entries[0]["repository_path"])).resolve(),
        source_bytes=sources["parent-protocol"],
        source_sha256=bindings["parent-protocol"].canonical_sha256,
        canonical_sha256=bindings["parent-protocol"].canonical_sha256,
    )
    terminal_identity = freeze.PersistedSelectionTerminalIdentity(
        path=(case.repository / ".git" / "independent-parent-terminal").resolve(),
        manifest_sha256=bindings["parent-manifest"].canonical_sha256,
        terminal_artifact_sha256=bindings["parent-result"].canonical_sha256,
        consumption_sha256=bindings["parent-consumption"].canonical_sha256,
    )
    terminal = advancement.build_selection_terminal_binding(
        result=parent_result,
        protocol=parent_protocol,
        terminal_identity=terminal_identity,
        consumption=parent_consumption,
    )
    admission = advancement.IndependentConfirmationAdmissionSpec.from_selection(
        terminal,
        admission_spec_id=parent_d6.confirmation_admission_spec.admission_spec_id,
    )
    assert terminal == parent_d6.selection_terminal
    assert admission == parent_d6.confirmation_admission_spec
    resealed = advancement.SurrogateAdvancementDecision.seal(
        decision_id=parent_d6.decision_id,
        decision_source_commit=parent_d6.decision_source_commit,
        decision_source_binding_sha256=parent_d6.decision_source_binding_sha256,
        selection_terminal=terminal,
        admission_spec=admission,
    )
    assert resealed.canonical_bytes == sources["parent-d6-decision"]
    advancement.validate_advancement_decision_source(
        resealed,
        repository_root=case.repository,
    )
    d6_identity = advancement.PersistedAdvancementIdentity(
        path=(case.repository / str(entries[-1]["repository_path"])).resolve(),
        source_sha256=bindings["parent-d6-decision"].canonical_sha256,
        canonical_sha256=bindings["parent-d6-decision"].canonical_sha256,
        byte_count=bindings["parent-d6-decision"].byte_count,
        parent_directory_fsync_verified=False,
    )
    loaded_d6 = advancement._build_authoritative_loaded_d6_decision(
        advancement.LoadedAdvancementArtifact(
            artifact=resealed,
            identity=d6_identity,
            source_bytes=sources["parent-d6-decision"],
        ),
        current_loader_source_commit=case.source_commit,
        current_loader_source_binding_sha256=(
            advancement.advancement_source_binding_sha256(
                repository_root=case.repository,
                commit=case.source_commit,
                require_clean_current_sources=False,
            )
        ),
    )
    design = execution_design.build_seed_free_d7_confirmation_execution_design(
        loaded_d6=loaded_d6,
        parent_protocol=loaded_protocol,
    )
    join_sha256 = sha256_bytes(
        canonical_json_bytes(
            {
                "schema_version": "spirallens.d7-v1-five-parent-join.v0.1",
                "parent_bindings": [bindings[role].to_dict() for role in roles],
                "confirmation_admission_sha256": admission.canonical_sha256,
                "execution_design_sha256": design.canonical_sha256,
            }
        )
    )
    return {
        "roles": roles,
        "bindings": bindings,
        "admission": admission,
        "design": design,
        "join_sha256": join_sha256,
    }


def test_exact_six_referents_match_independent_five_parent_typed_oracle(
    tmp_path: Path,
) -> None:
    approved = execution_design.build_seed_free_d7_confirmation_execution_design
    call_count = 0

    @wraps(approved)
    def counted(*, loaded_d6: object, parent_protocol: object) -> object:
        nonlocal call_count
        call_count += 1
        return approved(loaded_d6=loaded_d6, parent_protocol=parent_protocol)

    with patch.object(
        execution_design,
        "build_seed_free_d7_confirmation_execution_design",
        counted,
    ):
        case = _case(tmp_path)
    assert call_count == 1
    candidate = case.full_design_referents
    oracle = _independent_five_parent_oracle(case)
    assert candidate.source_commit == case.source_commit
    assert tuple(candidate.referents_by_role) == tuple(ROLE_SPECS)
    assert tuple(candidate.bindings_by_inventory_field) == tuple(INVENTORY_FIELDS)
    assert tuple(candidate.parent_adapter.parent_bindings) == oracle["roles"]
    assert dict(candidate.parent_adapter.parent_bindings) == oracle["bindings"]
    assert (
        dict(candidate.parent_adapter.confirmation_admission)
        == oracle["admission"].to_dict()
    )
    assert (
        candidate.parent_adapter.execution_design.to_dict()
        == oracle["design"].to_dict()
    )
    assert candidate.parent_adapter.parent_join_sha256 == oracle["join_sha256"]

    common_derivation: dict[str, object] | None = None
    for field, role in INVENTORY_FIELDS.items():
        referent = candidate.referents_by_role[role]
        document = referent.document
        schema, contract_id, payload_keys = ROLE_SPECS[role]
        assert set(document) == ROOT_KEYS
        assert document["schema_version"] == schema
        assert document["contract_id"] == contract_id
        assert document["artifact_role"] == role
        assert document["successor_lineage_id"] == "d7-spectral-moment-confirmation-v1"
        assert document["typestate"] == TYPESTATE
        assert document["claim_boundary"] == CLAIM_BOUNDARY
        assert type(document["derivation"]) is dict
        assert set(document["derivation"]) == DERIVATION_KEYS
        assert type(document["payload"]) is dict
        assert set(document["payload"]) == payload_keys
        assert canonical_json_bytes(document) == referent.canonical_bytes
        assert len(referent.canonical_bytes) == referent.byte_count
        assert sha256_bytes(referent.canonical_bytes) == referent.canonical_sha256
        assert referent.binding == candidate.bindings_by_inventory_field[field]
        assert referent.binding.artifact_contract_id == schema
        if common_derivation is None:
            common_derivation = document["derivation"]
        else:
            assert document["derivation"] == common_derivation

    assert common_derivation is not None
    assert common_derivation["source_commit"] == case.source_commit
    assert common_derivation["scientific_parent_join_sha256"] == oracle["join_sha256"]
    assert [
        binding["artifact_role"]
        for binding in common_derivation["scientific_parent_bindings"]
    ] == list(oracle["roles"])
    assert common_derivation["approved_callable"] == {
        "module": execution_design.__name__,
        "qualname": "build_seed_free_d7_confirmation_execution_design",
        "repository_path": (
            "src/spirallens/qualification/confirmation_execution_design.py"
        ),
        "five_parent_seed_free_scientific_projection_only": True,
        "authority_transfer_allowed": False,
        "persistence_transfer_allowed": False,
        "schema_transfer_allowed": False,
    }
    assert common_derivation["read_contract"] == {
        "exact_scientific_parent_count": 5,
        "historical_plan_read": False,
        "negative_or_predecessor_d7_read": False,
        "launch_artifact_read": False,
        "parent_result_values_retained": False,
    }

    family = candidate.referents_by_role["confirmation-family"].document["payload"]
    admission = candidate.referents_by_role["family-admission"].document["payload"]
    protocol = candidate.referents_by_role["confirmation-protocol"].document["payload"]
    source_graph = candidate.referents_by_role["source-graph"].document["payload"]
    aggregation = candidate.referents_by_role["graph-case-stress-aggregation"].document[
        "payload"
    ]
    lifecycle = candidate.referents_by_role["lifecycle"].document["payload"]
    assert all(
        type(value) is dict
        for value in (
            family,
            admission,
            protocol,
            source_graph,
            aggregation,
            lifecycle,
        )
    )

    typed_admission = advancement.IndependentConfirmationAdmissionSpec.from_dict(
        admission["fresh_confirmation_admission_spec"]
    )
    assert typed_admission == oracle["admission"]
    design = oracle["design"]
    design_document = design.to_dict()
    assert admission["parent_d6_binding"] == design_document["parent_d6"]
    assert admission["status"] == "candidate-not-issued"
    assert admission["admission_issued"] is False
    assert admission["all_requirements_reviewed"] is False
    assert admission["policy_override_allowed"] is False
    assert admission["post_selection_exclusion_allowed"] is False

    proposal = confirmation_protocol.D7ConfirmationFamilyProposal(
        selection_generator_family_id=typed_admission.selection_generator_family_id,
        selection_construction_family_id=(
            typed_admission.selection_construction_family_id
        ),
    ).to_dict()
    assert family["source_derived_family_proposal"] == proposal
    assert "source_selected_family_proposal" not in family
    assert (
        family["execution_design_confirmation_family"]
        == design_document["confirmation_family"]
    )
    assert family["case_count"] == len(family["case_ids"]) == 4
    assert family["seed_slot_ids"] == [
        "confirmation-seed-slot-00",
        "confirmation-seed-slot-01",
    ]
    assert (
        proposal["confirmation_generator_family_id"]
        != proposal["selection_generator_family_id"]
    )
    assert (
        proposal["confirmation_construction_family_id"]
        != proposal["selection_construction_family_id"]
    )
    assert proposal["identifier_difference_observed"] is True
    assert proposal["identifier_difference_proves_construction_diversity"] is False
    assert proposal["same_schema_mechanism_comparison_reviewed"] is False
    assert proposal["family_admitted"] is False

    assert protocol["execution_design"] == design_document
    assert protocol["execution_design_schema_version"] == design.schema_version
    assert protocol["execution_design_sha256"] == design.canonical_sha256
    assert protocol["seed_policy"] == design_document["seed_policy"]
    for key in ("graph_axes", "domain", "thresholds", "coverage_policy"):
        assert protocol[key] == design_document["locked_parent_interface"][key]
    for key in ("stress_translation", "manifest_compatibility"):
        assert protocol[key] == design_document[key]
    assert protocol["status"] == "seed-free-execution-design-not-frozen"
    assert protocol["protocol_frozen"] is False

    inventory = aggregation["inventory"]
    assert inventory == design.inventory.to_dict()
    assert aggregation["scientific_inventory_counts"] == {
        "seed_slots": 2,
        "cases": 4,
        "primary_units": 64,
        "core_cells": 192,
        "loop_cells": 1152,
        "event_lanes": 1344,
        "required_strata": 6,
    }
    assert len(inventory["primary_units"]) == 64
    assert len(inventory["core_cells"]) == 192
    assert len(inventory["loop_cells"]) == 1152
    assert len(inventory["expected_strata"]) == 6
    assert {item["case_id"] for item in inventory["primary_units"]} == set(
        family["case_ids"]
    )
    assert {item["seed_slot_id"] for item in inventory["primary_units"]} == set(
        family["seed_slot_ids"]
    )
    core_counts = Counter(item["primary_unit_id"] for item in inventory["core_cells"])
    loop_counts = Counter(item["primary_unit_id"] for item in inventory["loop_cells"])
    assert set(core_counts.values()) == {3}
    assert set(loop_counts.values()) == {18}
    assert aggregation["field_graph_count"] == 3
    assert aggregation["cycle_graph_count"] == 3
    assert aggregation["loop_role_count"] == 2
    assert aggregation["core_cells_per_primary_unit"] == 3
    assert aggregation["loop_cells_per_primary_unit"] == 18
    assert aggregation["graph_case_stress_cells_are_repeated_measures"] is True
    assert aggregation["repeated_measures"] == inventory["repeated_measures"]
    assert aggregation["event_lanes_are_independent_samples"] is False
    assert aggregation["aggregation_rebinding_reviewed"] is False
    assert aggregation["aggregation_rebinding_applied"] is False

    c1 = case.records_by_role[records.D7V1C1SourceSetRecord.artifact_role]
    assert isinstance(c1, records.D7V1C1SourceSetRecord)
    c1_members = c1.to_dict()["payload"]["source_members"]
    assert source_graph["source_members"] == c1_members
    assert source_graph["source_member_count"] == len(c1_members)
    assert source_graph["source_member_set_sha256"] == sha256_bytes(
        canonical_json_bytes(
            {
                "schema_version": "spirallens.d7-v1-source-member-set.v0.1",
                "source_members": c1_members,
            }
        )
    )
    assert all(
        records.D7V1SourceMember.from_dict(item).repository_path
        for item in source_graph["source_members"]
    )
    assert source_graph["git_declared_source_members_only"] is True
    assert source_graph["runtime_dependency_closure_verified"] is False
    assert source_graph["source_graph_authenticated"] is False

    chronology = lifecycle["protocol_future_chronology"]
    assert chronology == case.protocol["future_chronology"]
    assert tuple(chronology) == CHRONOLOGY_KEYS
    assert chronology["stages"] == [
        {"sequence": sequence, "stage_id": stage_id}
        for sequence, stage_id in enumerate(STAGE_IDS, start=1)
    ]
    assert chronology["git_commit_sequence"] == [
        {
            "commit_role": "reviewed-source-commit-s",
            "exact_artifact_only": False,
            "required_parent_role": None,
            "sequence": 1,
        },
        {
            "commit_role": "pre-item23-artifact-only-commit-a",
            "direct_parent_required": True,
            "exact_artifact_only": True,
            "required_parent_role": "reviewed-source-commit-s",
            "sequence": 2,
        },
        {
            "commit_role": "descriptive-result-only-commit-b",
            "direct_parent_required": True,
            "exact_artifact_only": True,
            "required_parent_role": "pre-item23-artifact-only-commit-a",
            "sequence": 3,
        },
    ]
    assert lifecycle["status"] == "prospective-not-instantiated"
    assert lifecycle["ordering_is_policy_only"] is True
    assert all(
        lifecycle[name] is False
        for name in ROLE_SPECS["lifecycle"][2]
        if name.endswith(("_created", "_frozen", "_observed", "_reserved"))
        or name in {"external_namespace_reserved", "lifecycle_instantiated"}
    )

    boolean_axes = {
        name: value
        for name, value in vars(referents.D7V1FullDesignReferentSetCandidate).items()
        if type(value) is bool
    }
    assert boolean_axes == {name: False for name in FALSE_AXES}
    assert candidate.resolution_status == "six-virtual-bindings-resolved"
    assert candidate.parent_adapter.exact_five_parent_read is True
    assert candidate.parent_adapter.parent_byte_identities_verified is True
    assert candidate.parent_adapter.parent_cross_joins_verified is True
    assert candidate.parent_adapter.parent_result_values_retained is False
    assert candidate.parent_adapter.historical_plan_read is False
    assert candidate.parent_adapter.negative_or_predecessor_d7_read is False
    assert candidate.parent_adapter.launch_artifact_read is False


def test_parent_reader_is_exact_five_and_rejects_wrong_shapes_or_bytes(
    tmp_path: Path,
) -> None:
    case = _case(tmp_path)
    protocol = materialization._protocol_at_commit(case.context, case.source_commit)
    expected_entries = case.protocol["historical_input_policy"][
        "permitted_historical_scientific_parents"
    ]
    expected_paths = tuple(str(entry["repository_path"]) for entry in expected_entries)
    observed: list[str] = []
    original_git_blob = materialization._git_blob

    def traced_git_blob(*args: object, **kwargs: object) -> tuple[str, bytes]:
        observed.append(str(args[2]))
        return original_git_blob(*args, **kwargs)

    with patch.object(materialization, "_git_blob", traced_git_blob):
        parents = referents._load_scientific_parents(
            case.context,
            protocol,
            source_commit=case.source_commit,
        )
    assert tuple(observed) == expected_paths
    forbidden_paths = {
        str(
            case.protocol["historical_input_policy"]["historical_plan_binding"][
                "repository_path"
            ]
        ),
        str(
            case.protocol["historical_input_policy"]["negative_exclusion_inputs"][0][
                "repository_path"
            ]
        ),
        str(
            case.protocol["historical_input_policy"]["predecessor_result_forbidden"][
                "repository_path"
            ]
        ),
        *map(
            str,
            case.protocol["historical_input_policy"][
                "predecessor_value_bearing_code_paths"
            ],
        ),
        str(case.protocol["coordinate_and_member_layout"]["launch_intent"]),
    }
    assert not forbidden_paths.intersection(observed)

    with pytest.raises(QualificationContractError, match="ordered exact five"):
        referents._require_parent_joins(parents[:-1])
    with pytest.raises(QualificationContractError, match="ordered exact five"):
        referents._require_parent_joins(tuple(reversed(parents)))
    tampered = dict(parents[1].document)
    tampered["protocol_canonical_sha256"] = "f" * 64
    tampered_parent = referents._PinnedScientificParent(
        role=parents[1].role,
        repository_path=parents[1].repository_path,
        source_commit=parents[1].source_commit,
        binding=parents[1].binding,
        source=parents[1].source,
        document=tampered,
    )
    with pytest.raises(QualificationContractError, match="identity join differs"):
        referents._require_parent_joins((parents[0], tampered_parent, *parents[2:]))

    for mutation in ("missing", "reordered", "extra-key"):
        document = copy.deepcopy(protocol.document)
        entries = document["historical_input_policy"][
            "permitted_historical_scientific_parents"
        ]
        if mutation == "missing":
            entries.pop()
        elif mutation == "reordered":
            entries.reverse()
        else:
            entries[0]["caller_extra"] = False
        with pytest.raises(QualificationContractError):
            referents._load_scientific_parents(
                case.context,
                SimpleNamespace(document=document),
                source_commit=case.source_commit,
            )

    first_path = expected_paths[0]

    def tampered_git_blob(*args: object, **kwargs: object) -> tuple[str, bytes]:
        mode, source = original_git_blob(*args, **kwargs)
        if args[2] == first_path:
            source = source[:-1] + bytes([source[-1] ^ 1])
        return mode, source

    with patch.object(materialization, "_git_blob", tampered_git_blob):
        with pytest.raises(QualificationContractError, match="historical bytes differ"):
            referents._load_scientific_parents(
                case.context,
                protocol,
                source_commit=case.source_commit,
            )


def test_direct_derive_rejects_wrong_s_c1_c2_origin_and_live_drift(
    tmp_path: Path,
) -> None:
    case = _case(tmp_path)
    protocol = materialization._protocol_at_commit(case.context, case.source_commit)
    c1 = case.records_by_role[records.D7V1C1SourceSetRecord.artifact_role]
    c2 = case.records_by_role[records.D7V1C2SourceClosureReceipt.artifact_role]
    assert isinstance(c1, records.D7V1C1SourceSetRecord)
    assert isinstance(c2, records.D7V1C2SourceClosureReceipt)

    with pytest.raises(QualificationContractError):
        referents._derive_d7_v1_full_design_referent_set_candidate(
            case.context,
            protocol=protocol,
            source_commit="0" * 40,
            c1=c1,
            c2=c2,
        )

    c1_document = c1.to_dict()
    c1_payload = c1_document["payload"]
    forged_c1 = records.D7V1C1SourceSetRecord.create(
        record_id=str(c1_document["record_id"]),
        repository_path=str(c1_payload["repository_path"]),
        route_binding=records.D7V1ArtifactBinding.from_dict(
            c1_payload["route_binding"]
        ),
        source_members=tuple(
            records.D7V1SourceMember.from_dict(item)
            for item in c1_payload["source_members"]
            if item["repository_path"] != MODULE_REPOSITORY_PATH
        ),
    )
    forged_c2 = records.D7V1C2SourceClosureReceipt.create(
        record_id="d7-v1-forged-c2",
        repository_path=str(c2.to_dict()["payload"]["repository_path"]),
        c1=forged_c1,
        source_commit=case.source_commit,
    )
    with pytest.raises(QualificationContractError, match="omits executed"):
        referents._derive_d7_v1_full_design_referent_set_candidate(
            case.context,
            protocol=protocol,
            source_commit=case.source_commit,
            c1=forged_c1,
            c2=forged_c2,
        )

    parent_commit = _run(case.repository, "rev-parse", f"{case.source_commit}^")
    wrong_c2 = records.D7V1C2SourceClosureReceipt.create(
        record_id="d7-v1-wrong-s-c2",
        repository_path=str(c2.to_dict()["payload"]["repository_path"]),
        c1=c1,
        source_commit=parent_commit,
    )
    with pytest.raises(QualificationContractError):
        referents._derive_d7_v1_full_design_referent_set_candidate(
            case.context,
            protocol=protocol,
            source_commit=case.source_commit,
            c1=c1,
            c2=wrong_c2,
        )

    materialization_target = case.repository.joinpath(
        *MATERIALIZATION_REPOSITORY_PATH.split("/")
    )
    imported_materialization = Path(materialization.__file__)
    assert materialization_target.samefile(imported_materialization)
    source = materialization_target.read_bytes()
    materialization_target.unlink()
    materialization_target.write_bytes(source)
    assert not materialization_target.samefile(imported_materialization)
    assert _git(case.repository, "status", "--porcelain=v1", "-z") == b""
    with pytest.raises(
        QualificationContractError, match="materialization module import origin"
    ):
        referents._derive_d7_v1_full_design_referent_set_candidate(
            case.context,
            protocol=protocol,
            source_commit=case.source_commit,
            c1=c1,
            c2=c2,
        )
    materialization_target.unlink()
    os.link(imported_materialization, materialization_target)

    drift_path = case.repository / "src/spirallens/__init__.py"
    drift_path.write_bytes(drift_path.read_bytes() + b"\n# live drift\n")
    with pytest.raises(QualificationContractError):
        referents._derive_d7_v1_full_design_referent_set_candidate(
            case.context,
            protocol=protocol,
            source_commit=case.source_commit,
            c1=c1,
            c2=c2,
        )


def _alternate_binding_case(
    base: object,
    stage_root: Path,
    field: str,
) -> object:
    helpers = _materialization_helpers()
    c1 = base.records_by_role[records.D7V1C1SourceSetRecord.artifact_role]
    assert isinstance(c1, records.D7V1C1SourceSetRecord)
    members = tuple(
        records.D7V1SourceMember.from_dict(item)
        for item in c1.to_dict()["payload"]["source_members"]
    )
    expected = base.full_design_referents.bindings_by_inventory_field[field]
    alternate = records.D7V1ArtifactBinding(
        artifact_role=expected.artifact_role,
        artifact_contract_id=expected.artifact_contract_id,
        canonical_sha256=sha256_bytes(
            canonical_json_bytes(
                {"field": field, "alternate": True, "locally_schema_valid": True}
            )
        ),
        byte_count=expected.byte_count + 1,
    )
    loaded_protocol = materialization._protocol_at_commit(
        base.context,
        base.source_commit,
    )
    route = json.loads((REPOSITORY / ROUTE_REPOSITORY_PATH).read_text(encoding="utf-8"))
    built, supplier, derived = helpers._build_records(
        repository=base.context,
        materialization_protocol=loaded_protocol,
        protocol=base.protocol,
        route=route,
        source_commit=base.source_commit,
        source_members=members,
        supplier_candidate=base.supplier_candidate,
        full_design_referent_candidate=base.full_design_referents,
        full_design_binding_overrides={field: alternate},
    )
    assert derived is base.full_design_referents
    paths = helpers._coordinate_paths(base.protocol)
    for role, repository_path in paths.items():
        helpers._write(
            stage_root,
            helpers._stage_relative(base.protocol, repository_path),
            built[role].canonical_bytes,
        )
    external = base.protocol["external_durable_chronology_contract"]
    claim_path = Path(str(external["seed_supply_claim"]["external_store_path"]))
    attempt_path = Path(str(external["attempt_reservation"]["external_store_path"]))
    return helpers._Case(
        repository=base.repository,
        context=base.context,
        source_commit=base.source_commit,
        stage_root=stage_root,
        protocol=base.protocol,
        records_by_role=built,
        external_bytes={
            claim_path: built[
                records.D7V1ExclusiveSeedSupplyClaim.artifact_role
            ].canonical_bytes,
            attempt_path: built[
                records.D7V1OfficialExecutionAttemptReservation.artifact_role
            ].canonical_bytes,
        },
        supplier_candidate=supplier,
        full_design_referents=derived,
    )


def test_joined_loader_rejects_each_self_consistent_alternate_virtual_binding(
    tmp_path: Path,
) -> None:
    helpers = _materialization_helpers()
    base = _case(tmp_path / "base")
    for field in INVENTORY_FIELDS:
        alternate = _alternate_binding_case(
            base,
            tmp_path / f"stage-{field}",
            field,
        )
        with (
            patch.object(
                materialization,
                "_derive_full_design_referent_set_candidate",
                return_value=base.full_design_referents,
            ),
            patch.object(
                materialization,
                "_derive_source_selected_seed_supplier_candidate",
                return_value=base.supplier_candidate,
            ),
            pytest.raises(
                QualificationContractError,
                match=f"{field} virtual referent",
            ),
        ):
            helpers._load_stage(alternate)


def test_clean_builder_does_not_import_or_enter_source_selected_supplier(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    helpers = _deterministic_helpers()
    case = helpers._prepared_case(tmp_path)
    closure = helpers._build_source_closure(case)
    deterministic = helpers._build(case, closure)
    supplier_called = False
    entropy_called = False

    def forbidden_supplier() -> tuple[int, int]:
        nonlocal supplier_called
        supplier_called = True
        raise AssertionError("full-design referent build must not enter the supplier")

    def forbidden_entropy(_bits: int) -> int:
        nonlocal entropy_called
        entropy_called = True
        raise AssertionError("full-design referent build must not access entropy")

    forbidden_supplier.__module__ = selected_supplier.__name__
    forbidden_supplier.__qualname__ = "_supply_d7_v1_official_seed_values"
    monkeypatch.setattr(
        selected_supplier,
        "_supply_d7_v1_official_seed_values",
        forbidden_supplier,
    )
    monkeypatch.setattr(selected_supplier.secrets, "randbits", forbidden_entropy)
    real_import = builtins.__import__

    def import_without_supplier(
        name: str,
        globals: object = None,
        locals: object = None,
        fromlist: tuple[str, ...] = (),
        level: int = 0,
    ) -> object:
        forbidden = "confirmation_v1_source_selected_supplier"
        if forbidden in name or (fromlist is not None and forbidden in fromlist):
            raise AssertionError("clean referent builder imported the seed supplier")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", import_without_supplier)
    candidate = referents._build_d7_v1_full_design_referent_set_candidate(
        case.context,
        deterministic_inputs=deterministic,
    )
    assert isinstance(candidate, referents.D7V1FullDesignReferentSetCandidate)
    assert supplier_called is False
    assert entropy_called is False
    assert _git(case.repository, "status", "--porcelain=v1", "-z") == b""


def test_private_surface_keeps_protocol_route_records_api_and_dependencies() -> None:
    assert referents.__all__ == ()
    assert materialization.__all__ == ()
    assert sha256_bytes(canonical_json_bytes(spirallens.__all__)) == (
        "a67ce5620fe4a53824cc2b3e0e0b4d46a452298a72fdaa8974ace14e97f13b7c"
    )
    assert sha256_bytes(canonical_json_bytes(qualification.__all__)) == (
        "4dab13d8a847400280682f61fcf0b03fdd9ad51c68d8909ab63a463d07579023"
    )
    for repository_path, (byte_count, digest) in EXPECTED_STATIC_FILES.items():
        source = REPOSITORY.joinpath(*repository_path.split("/")).read_bytes()
        assert len(source) == byte_count
        assert sha256_bytes(source) == digest
    for repository_path, markers in DOCUMENT_BOUNDARY_MARKERS.items():
        document = " ".join(
            REPOSITORY.joinpath(*repository_path.split("/"))
            .read_text(encoding="utf-8")
            .split()
        )
        assert all(marker in document for marker in markers)
        assert "VOY-V3 remains `frozen_not_run`" in document
        assert "D7/D8 remain `not_run`" in document

    source = (REPOSITORY / MODULE_REPOSITORY_PATH).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported: set[str] = set()
    calls: set[str] = set()
    literals = {
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and type(node.value) is str
    }
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported.add(node.module)
        elif isinstance(node, ast.Call):
            name = node.func
            parts: list[str] = []
            while isinstance(name, ast.Attribute):
                parts.append(name.attr)
                name = name.value
            if isinstance(name, ast.Name):
                parts.append(name.id)
            calls.add(".".join(reversed(parts)))
    assert not imported & {"secrets", "torch", "transformers"}
    assert not any("source_selected_supplier" in name for name in imported)
    forbidden_calls = {
        "_supply_d7_v1_official_seed_values",
        "randbits",
        "produce_d7_v1_official_result",
        "from_pretrained",
        "load_model",
        "write_bytes",
        "write_text",
        "mkdir",
        "rename",
        "replace",
        "unlink",
    }
    assert not any(call.rsplit(".", 1)[-1] in forbidden_calls for call in calls)
    protocol = json.loads(
        (REPOSITORY / PROTOCOL_REPOSITORY_PATH).read_text(encoding="utf-8")
    )
    forbidden_coordinates = {
        str(
            protocol["historical_input_policy"]["historical_plan_binding"][
                "repository_path"
            ]
        ),
        str(
            protocol["historical_input_policy"]["negative_exclusion_inputs"][0][
                "repository_path"
            ]
        ),
        str(
            protocol["historical_input_policy"]["predecessor_result_forbidden"][
                "repository_path"
            ]
        ),
        *map(
            str,
            protocol["historical_input_policy"]["predecessor_value_bearing_code_paths"],
        ),
        str(protocol["coordinate_and_member_layout"]["launch_intent"]),
    }
    assert not forbidden_coordinates.intersection(literals)
