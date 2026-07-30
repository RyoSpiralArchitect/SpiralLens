from __future__ import annotations

import inspect
import subprocess
from collections.abc import Mapping
from pathlib import Path

import pytest

from spirallens.core.canonical import canonical_json_bytes, sha256_bytes
from spirallens.qualification import (
    confirmation_replay_contracts as replay_contract_module,
)
from spirallens.qualification.common import QualificationContractError
from spirallens.qualification.confirmation_replay_contracts import (
    D7_RECORDED_C1_POST_MERGE_COMMIT,
    D7_RECORDED_C2_INTRODUCTION_COMMIT,
    D7AttemptEnvelopeContractSpec,
    D7ReplayTargetContractSpec,
    LoadedD7ReplayAttemptContractFoundation,
    load_d7_replay_attempt_contract_foundation,
)

REPOSITORY = Path(__file__).resolve().parents[1]


def _git(root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


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
    assert _git(destination, "status", "--short") == ""
    return destination


@pytest.fixture(scope="module")
def clean_repository(
    tmp_path_factory: pytest.TempPathFactory,
) -> Path:
    return _clean_clone(tmp_path_factory.mktemp("d7-replay-contract") / "repository")


@pytest.fixture(scope="module")
def loaded_foundation(
    clean_repository: Path,
) -> LoadedD7ReplayAttemptContractFoundation:
    return load_d7_replay_attempt_contract_foundation(repository_root=clean_repository)


def _mapping_keys(value: object) -> set[str]:
    if isinstance(value, Mapping):
        return set(value).union(
            *(_mapping_keys(item) for item in value.values()),
            set(),
        )
    if isinstance(value, list):
        return set().union(*(_mapping_keys(item) for item in value), set())
    return set()


def test_loader_is_choice_free_and_rebuilds_from_pinned_clean_history(
    loaded_foundation: LoadedD7ReplayAttemptContractFoundation,
) -> None:
    signature = inspect.signature(load_d7_replay_attempt_contract_foundation)

    assert tuple(signature.parameters) == ("repository_root",)
    assert signature.parameters["repository_root"].kind is (
        inspect.Parameter.KEYWORD_ONLY
    )
    assert loaded_foundation.c1_commit == D7_RECORDED_C1_POST_MERGE_COMMIT
    assert loaded_foundation.c2_commit == D7_RECORDED_C2_INTRODUCTION_COMMIT
    assert loaded_foundation.historical_c1_git_source_set_verified is True
    assert loaded_foundation.current_contract_source_compatibility_verified is False
    assert loaded_foundation.current_execution_source_runtime_closure_verified is False
    assert loaded_foundation.launch_authorized is False


def test_both_closed_specs_round_trip_canonical_bytes(
    loaded_foundation: LoadedD7ReplayAttemptContractFoundation,
) -> None:
    target = loaded_foundation.replay_target_contract
    restored_target = D7ReplayTargetContractSpec.from_canonical_bytes(
        target.canonical_bytes,
        expected_sha256=target.canonical_sha256,
    )
    assert restored_target.canonical_bytes == target.canonical_bytes
    assert restored_target.to_dict() == target.to_dict()

    envelope = loaded_foundation.attempt_envelope_contract
    restored_envelope = D7AttemptEnvelopeContractSpec.from_canonical_bytes(
        envelope.canonical_bytes,
        expected_sha256=envelope.canonical_sha256,
        target_contract=restored_target,
    )
    assert restored_envelope.canonical_bytes == envelope.canonical_bytes
    assert restored_envelope.to_dict() == envelope.to_dict()
    assert restored_envelope.target_contract_sha256 == target.canonical_sha256


def test_target_and_attempt_envelope_are_separate_closed_stage_models(
    loaded_foundation: LoadedD7ReplayAttemptContractFoundation,
) -> None:
    target = loaded_foundation.replay_target_contract
    envelope = loaded_foundation.attempt_envelope_contract
    target_document = target.to_dict()
    envelope_document = envelope.to_dict()

    forbidden_target_fields = set(
        target_document["future_replay_target"]["forbidden_fields"]
    )
    assert {
        "attempt_role",
        "output_namespace",
        "launch_authorization",
        "attempt_claim",
        "execution_start",
        "result_payload",
        "failed_attempt",
        "terminal_lineage",
    } <= forbidden_target_fields
    assert forbidden_target_fields.isdisjoint(_mapping_keys(target_document))

    record_model = envelope_document["record_model"]
    expected_stages = [
        "attempt-declaration",
        "launch-authorization",
        "exclusive-attempt-claim",
        "execution-start",
        "scientific-result-or-failed-attempt",
        "terminal-manifest",
        "terminal-consumption",
    ]
    assert record_model["append_only_stage_order"] == expected_stages
    assert [
        stage["stage"] for stage in record_model["stage_contracts"]
    ] == expected_stages
    assert (
        envelope_document["replay_target_contract_binding"]["canonical_sha256"]
        == target.canonical_sha256
    )
    assert (
        envelope_document["replay_target_contract_binding"][
            "target_body_may_be_duplicated_in_attempt_records"
        ]
        is False
    )
    assert {
        "official-seed-inventory",
        "thresholds",
        "graph-or-cycle-inventory",
        "aggregation-policy",
        "result-payload-schema",
        "replay-target-identity",
    } <= set(record_model["attempt_records_forbidden_to_redefine"])
    assert "launch-intent-sha256" in record_model["stage_contracts"][0]["binds"]
    assert record_model["untracked_launch_intent_allowed"] is False

    seed_binding = target_document["future_official_seed_binding"]
    assert seed_binding["required_seed_count"] == 2
    assert seed_binding["seed_values_must_be_plain_integers"] is True
    assert (
        seed_binding[
            "full_design_must_be_canonically_reconstructed_from_exact_inventory"
        ]
        is True
    )
    assert [
        item["seed_slot_id"] for item in seed_binding["seed_slot_ordinal_mapping"]
    ] == [
        "confirmation-seed-slot-00",
        "confirmation-seed-slot-01",
    ]
    target_properties = target_document["future_replay_target"]["required_properties"]
    assert target_properties["claim_ceiling_must_equal"] == "level_0"
    assert set(target_properties["target_local_authority_must_equal"].values()) == {
        False
    }
    assert target_properties["nested_or_extended_authority_allowed"] is False

    seed_chronology = target_document["seed_supply_chronology_contract"]
    assert seed_chronology["ordered_transitions"] == [
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

    equality_constraints = envelope_document["canonical_equality_constraints"]
    assert len(equality_constraints) == 10
    assert {item["relation"] for item in equality_constraints} == {"byte-equal"}
    assert {(item["left"], item["right"]) for item in equality_constraints} >= {
        (
            "launch-authorization.execution-source-runtime-receipt-sha256",
            (
                "loaded-replay-target."
                "execution-source-runtime-closure-binding.receipt-sha256"
            ),
        ),
        (
            "execution-start.observed-runtime-specification-sha256",
            (
                "loaded-replay-target."
                "execution-source-runtime-closure-binding."
                "runtime-specification-sha256"
            ),
        ),
        (
            "scientific-result-payload.full-inventory-sha256",
            "loaded-replay-target.full-design-binding.inventory-sha256",
        ),
    }

    start_contract = envelope_document["execution_start_contract"]
    assert set(start_contract.values()) == {True, False}
    assert (
        start_contract["observed_execution_source_must_match_frozen_target_receipt"]
        is True
    )
    assert (
        start_contract[
            "observed_runtime_must_match_frozen_target_runtime_specification"
        ]
        is True
    )
    assert (
        start_contract["output_namespace_absence_rechecked_immediately_before_start"]
        is True
    )
    assert start_contract["placeholder_output_before_start_allowed"] is False

    failure = envelope_document["failure_and_retry_contract"]
    assert failure["visible_start_without_terminal_state"] == "started_unresolved"
    assert failure["started_unresolved_is_terminal_aborted"] is False
    assert failure["started_unresolved_retry_authorized"] is False
    assert failure["started_unresolved_replay_authorized"] is False
    assert (
        failure["started_unresolved_finalization_requires_append_only_record"] is True
    )
    assert failure["abort_finalization_requires_external_evidence"] is True
    assert failure["hard_crash_can_publish_in_process_failure"] is False

    outcome = envelope_document["outcome_contract"]
    assert outcome["scientific_result_payload_binds_concrete_target_sha256"] is True
    assert outcome["payload_validator_reconstructs_exact_target_semantic_join"] is True
    assert outcome["payload_from_different_target_allowed"] is False

    replay_role = envelope_document["attempt_role_evidence_contract"][
        "isolated_byte_replay"
    ]
    assert replay_role["persisted_passed_primary_terminal_sha256_required"] is True
    assert replay_role["role_derived_from_typed_primary_receipts"] is True
    assert replay_role["caller_role_label_sufficient"] is False

    terminal = envelope_document["terminal_transaction_contract"]
    assert terminal["published_by_atomic_no_replace_directory_rename"] is True
    assert terminal["partial_terminal_transaction_may_be_published"] is False
    isolated = envelope_document["isolated_replay_contract"]
    assert isolated["output_namespaces_must_be_realpath_disjoint"] is True
    assert isolated["terminal_trees_must_be_inode_disjoint"] is True
    assert isolated["symlink_or_hardlink_aliases_allowed"] is False


def test_foundation_contains_no_instance_seed_result_or_authority(
    loaded_foundation: LoadedD7ReplayAttemptContractFoundation,
) -> None:
    target_document = loaded_foundation.replay_target_contract.to_dict()
    envelope_document = loaded_foundation.attempt_envelope_contract.to_dict()

    assert target_document["status"] == "schema-defined-instance-absent"
    assert envelope_document["status"] == "schema-defined-instance-absent"
    assert (
        target_document["seed_free_projection"]["numeric_seed_values_present"] is False
    )
    assert set(target_document["current_instance_state"].values()) == {False}
    assert set(envelope_document["current_instance_state"].values()) == {False}
    assert set(target_document["authority"].values()) == {False}
    assert set(envelope_document["authority"].values()) == {False}
    assert target_document["d7_state"] == "not_run"
    assert envelope_document["d7_state"] == "not_run"
    assert {
        "seed_values",
        "seeds",
        "result",
        "result_payload",
        "launch_authority",
    }.isdisjoint(_mapping_keys(target_document))
    assert {
        "seed_values",
        "seeds",
        "result",
        "result_payload",
        "launch_authority",
    }.isdisjoint(_mapping_keys(envelope_document))

    assert loaded_foundation.replay_target_present is False
    assert loaded_foundation.attempt_envelope_present is False
    assert loaded_foundation.official_seed_inventory_present is False
    assert loaded_foundation.launch_authorized is False


def test_closed_readers_reject_bool_integer_and_extra_field_laundering(
    loaded_foundation: LoadedD7ReplayAttemptContractFoundation,
) -> None:
    target = loaded_foundation.replay_target_contract
    target_document = target.to_dict()
    target_document["current_instance_state"]["replay_target_present"] = 0
    target_source = canonical_json_bytes(target_document)
    with pytest.raises(QualificationContractError, match="closed specification"):
        D7ReplayTargetContractSpec.from_canonical_bytes(
            target_source,
            expected_sha256=sha256_bytes(target_source),
        )

    envelope = loaded_foundation.attempt_envelope_contract
    envelope_document = envelope.to_dict()
    envelope_document["current_instance_state"]["attempt_envelope_present"] = 0
    envelope_source = canonical_json_bytes(envelope_document)
    with pytest.raises(QualificationContractError, match="closed specification"):
        D7AttemptEnvelopeContractSpec.from_canonical_bytes(
            envelope_source,
            expected_sha256=sha256_bytes(envelope_source),
            target_contract=target,
        )

    for contract_name in ("target", "envelope"):
        if contract_name == "target":
            document = target.to_dict()
            document["unreviewed_extension"] = False
            source = canonical_json_bytes(document)
            with pytest.raises(
                QualificationContractError,
                match="closed specification",
            ):
                D7ReplayTargetContractSpec.from_canonical_bytes(
                    source,
                    expected_sha256=sha256_bytes(source),
                )
        else:
            document = envelope.to_dict()
            document["record_model"]["unreviewed_extension"] = False
            source = canonical_json_bytes(document)
            with pytest.raises(
                QualificationContractError,
                match="closed specification",
            ):
                D7AttemptEnvelopeContractSpec.from_canonical_bytes(
                    source,
                    expected_sha256=sha256_bytes(source),
                    target_contract=target,
                )


def test_full_rehash_does_not_authorize_mutated_closed_documents(
    loaded_foundation: LoadedD7ReplayAttemptContractFoundation,
) -> None:
    target = loaded_foundation.replay_target_contract
    target_document = target.to_dict()
    target_document["recorded_parent_bindings"]["c2"]["canonical_sha256"] = "0" * 64
    mutated_target_source = canonical_json_bytes(target_document)
    mutated_target_sha256 = sha256_bytes(mutated_target_source)

    with pytest.raises(QualificationContractError, match="closed specification"):
        D7ReplayTargetContractSpec.from_canonical_bytes(
            mutated_target_source,
            expected_sha256=mutated_target_sha256,
        )

    envelope = loaded_foundation.attempt_envelope_contract
    envelope_document = envelope.to_dict()
    envelope_document["replay_target_contract_binding"]["canonical_sha256"] = (
        mutated_target_sha256
    )
    mutated_envelope_source = canonical_json_bytes(envelope_document)
    mutated_envelope_sha256 = sha256_bytes(mutated_envelope_source)

    with pytest.raises(QualificationContractError, match="closed specification"):
        D7AttemptEnvelopeContractSpec.from_canonical_bytes(
            mutated_envelope_source,
            expected_sha256=mutated_envelope_sha256,
            target_contract=target,
        )

    contradictory_envelope = envelope.to_dict()
    contradictory_envelope["canonical_equality_constraints"][0]["right"] = (
        "different-target.canonical-sha256"
    )
    contradictory_source = canonical_json_bytes(contradictory_envelope)
    with pytest.raises(QualificationContractError, match="closed specification"):
        D7AttemptEnvelopeContractSpec.from_canonical_bytes(
            contradictory_source,
            expected_sha256=sha256_bytes(contradictory_source),
            target_contract=target,
        )


def test_direct_construction_cannot_forge_closed_contracts_or_foundation(
    loaded_foundation: LoadedD7ReplayAttemptContractFoundation,
) -> None:
    target = loaded_foundation.replay_target_contract
    envelope = loaded_foundation.attempt_envelope_contract

    with pytest.raises(QualificationContractError, match="closed factory"):
        D7ReplayTargetContractSpec(canonical_bytes=target.canonical_bytes)
    with pytest.raises(QualificationContractError, match="closed factory"):
        D7AttemptEnvelopeContractSpec(
            canonical_bytes=envelope.canonical_bytes,
            target_contract=target,
        )
    with pytest.raises(QualificationContractError, match="pinned repository loader"):
        LoadedD7ReplayAttemptContractFoundation(
            replay_target_contract=target,
            attempt_envelope_contract=envelope,
            c1_commit=loaded_foundation.c1_commit,
            c2_commit=loaded_foundation.c2_commit,
            validation_current_head=loaded_foundation.validation_current_head,
        )


@pytest.mark.parametrize(
    ("constant_name", "replacement"),
    (
        ("_RECORDED_SEED_FREE_DESIGN_ID", "wrong-design-id"),
        ("_RECORDED_SEED_FREE_DESIGN_SHA256", "f" * 64),
        ("_RECORDED_INVENTORY_SHA256", "f" * 64),
        ("_RECORDED_IMPLEMENTATION_REGISTRY_SHA256", "f" * 64),
        ("_RECORDED_AGGREGATION_APPLICATION_SHA256", "f" * 64),
        ("_RECORDED_EVALUATION_PROJECTION_SHA256", "f" * 64),
        (
            "_RECORDED_SEED_SLOT_IDS",
            ("wrong-seed-slot-00", "wrong-seed-slot-01"),
        ),
    ),
)
def test_loader_rejoins_every_target_subpin_to_exact_recorded_c1(
    clean_repository: Path,
    monkeypatch: pytest.MonkeyPatch,
    constant_name: str,
    replacement: object,
) -> None:
    monkeypatch.setattr(replay_contract_module, constant_name, replacement)
    with pytest.raises(QualificationContractError, match="pinned subcomponents"):
        load_d7_replay_attempt_contract_foundation(repository_root=clean_repository)


def test_loader_rejoins_c2_repository_path_to_the_actual_verifier(
    clean_repository: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        replay_contract_module,
        "_RECORDED_C2_REPOSITORY_PATH",
        "wrong/c2.json",
    )
    with pytest.raises(
        QualificationContractError,
        match="repository-path pin differs",
    ):
        load_d7_replay_attempt_contract_foundation(repository_root=clean_repository)


def test_descendant_source_change_leaves_target_stable_and_never_authorizes_launch(
    tmp_path: Path,
) -> None:
    root = _clean_clone(tmp_path / "repository")
    before = load_d7_replay_attempt_contract_foundation(repository_root=root)

    probe = root / "src" / "spirallens" / "qualification" / "post_c2_probe.py"
    probe.write_text(
        '"""A descendant source change outside the historical C1 closure."""\n',
        encoding="utf-8",
    )
    _git(root, "config", "user.name", "SpiralLens Test")
    _git(root, "config", "user.email", "spirallens@example.invalid")
    _git(root, "add", str(probe.relative_to(root)))
    _git(root, "commit", "--quiet", "-m", "test descendant source change")
    assert _git(root, "status", "--short") == ""

    after = load_d7_replay_attempt_contract_foundation(repository_root=root)

    assert after.validation_current_head != before.validation_current_head
    assert (
        after.replay_target_contract.canonical_bytes
        == before.replay_target_contract.canonical_bytes
    )
    assert (
        after.attempt_envelope_contract.canonical_bytes
        == before.attempt_envelope_contract.canonical_bytes
    )
    assert after.current_contract_source_compatibility_verified is False
    assert after.current_execution_source_runtime_closure_verified is False
    assert after.launch_authorized is False
