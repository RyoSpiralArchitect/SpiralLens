from __future__ import annotations

import hashlib
import re
import subprocess
from pathlib import Path, PurePosixPath

from spirallens.core.canonical import canonical_json_bytes, parse_canonical_json


REPOSITORY = Path(__file__).resolve().parents[1]
ROUTE_PATH = REPOSITORY / "protocols" / "voy_v1_v9_strict_successor_route_v0_1.json"
ROUTE_SHA256 = "c8d28138c95d16ab96f508c2386de1d62360e1659057e0b8f7cbe8a380a90e35"
PR42_MERGE_COMMIT = "aa5364da5478c4ebe782cfd382f4a18725a50e04"


def _mapping(value: object) -> dict[str, object]:
    assert isinstance(value, dict)
    assert all(isinstance(key, str) for key in value)
    return value


def _sequence(value: object) -> list[object]:
    assert isinstance(value, list)
    return value


def _git_blob(commit: str, repository_path: str) -> bytes:
    completed = subprocess.run(
        ["git", "-C", str(REPOSITORY), "show", f"{commit}:{repository_path}"],
        check=False,
        capture_output=True,
    )
    assert completed.returncode == 0, completed.stderr.decode("utf-8", errors="replace")
    return completed.stdout


def _git_head() -> str:
    completed = subprocess.run(
        ["git", "-C", str(REPOSITORY), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _is_ancestor(ancestor: str, descendant: str) -> bool:
    return (
        subprocess.run(
            [
                "git",
                "-C",
                str(REPOSITORY),
                "merge-base",
                "--is-ancestor",
                ancestor,
                descendant,
            ],
            check=False,
            capture_output=True,
        ).returncode
        == 0
    )


def _load_route() -> dict[str, object]:
    source = ROUTE_PATH.read_bytes()
    assert len(source) == 13_806
    assert hashlib.sha256(source).hexdigest() == ROUTE_SHA256
    document = parse_canonical_json(source, label=ROUTE_PATH.name)
    assert isinstance(document, dict)
    assert canonical_json_bytes(document) == source
    return document


def _iter_strings(value: object):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _iter_strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _iter_strings(item)


def test_route_is_one_closed_non_authorizing_navigation_snapshot() -> None:
    route = _load_route()
    assert set(route) == {
        "artifact_role",
        "canonical_roadmap_binding",
        "claim_boundary",
        "historical_boundary_binding",
        "library_guard",
        "navigation_contract",
        "psi_guard",
        "route_id",
        "route_namespace",
        "route_selection",
        "schema_version",
        "stages",
        "strict_successor_declaration",
        "v9_branch_contract",
    }
    assert route["schema_version"] == "spirallens.voy-navigation-route.v0.1"
    assert route["route_id"] == "voy-v1-v9-strict-successor-route-v0-1"
    assert route["route_namespace"] == "VOY"
    assert route["artifact_role"] == "navigation_and_coordinate_declaration_only"
    assert _mapping(route["route_selection"]) == {
        "decision_date": "2026-08-09",
        "exploratory_label_may_bypass_subject_gate": False,
        "model_free_exploratory_only_selected": False,
        "selected_route": "strict_versioned_successor",
    }
    ledger = (REPOSITORY / "docs" / "EXPERIMENT_INTERPRETATION_LEDGER.md").read_text()
    assert "### 3.15 Strict-successor route selection and V1–V9 navigation" in ledger
    assert route["route_id"] in ledger
    assert ROUTE_SHA256 in ledger


def test_route_reauthenticates_pr42_and_the_f2_f4_registry() -> None:
    route = _load_route()
    roadmap = _mapping(route["canonical_roadmap_binding"])
    assert roadmap == {
        "repository_path": "docs/ROADMAP.md",
        "source_commit": PR42_MERGE_COMMIT,
        "source_sha256": "c2aac3eca19c35eab86a794ef13f2e1269e435b7c09d7108505e5547c149ab6c",
    }
    assert (
        hashlib.sha256(
            _git_blob(str(roadmap["source_commit"]), str(roadmap["repository_path"]))
        ).hexdigest()
        == roadmap["source_sha256"]
    )
    assert _is_ancestor(PR42_MERGE_COMMIT, _git_head())

    boundary = _mapping(route["historical_boundary_binding"])
    assert boundary["pr42_merge_commit"] == PR42_MERGE_COMMIT
    for name in ("fundamental_frame", "interpretation_ledger"):
        binding = _mapping(boundary[name])
        source = _git_blob(
            str(binding["source_commit"]), str(binding["repository_path"])
        )
        assert hashlib.sha256(source).hexdigest() == binding["source_sha256"]
        assert _is_ancestor(str(binding["source_commit"]), PR42_MERGE_COMMIT)

    disposition_binding = _mapping(boundary["chronology_disposition"])
    disposition_source = _git_blob(
        str(disposition_binding["introduction_commit"]),
        str(disposition_binding["repository_path"]),
    )
    assert (
        hashlib.sha256(disposition_source).hexdigest() == disposition_binding["sha256"]
    )
    disposition = _mapping(
        parse_canonical_json(disposition_source, label="v0.1 disposition")
    )
    decision = _mapping(disposition["disposition"])
    chronology = _mapping(disposition["chronology_observation"])
    assert disposition["disposition_id"] == disposition_binding["disposition_id"]
    assert decision["item23_chronology_conformance"] == "deviated"
    assert decision["item23_d7_ops_completion_credit_allowed"] is False
    assert decision["official_item24_v0_1_invocation_eligible"] is False
    assert decision["requires_versioned_successor_before_execution"] is True
    assert decision["retroactive_protocol_conformance_claimed"] is False
    assert chronology["later_descriptor_retroactively_cures_deviation"] is False

    registry = _mapping(_mapping(route["psi_guard"])["registry_binding"])
    registry_source = _git_blob(
        str(registry["source_commit"]), str(registry["repository_path"])
    )
    assert hashlib.sha256(registry_source).hexdigest() == registry["source_sha256"]
    assert registry_source == _git_blob(
        str(registry["introduction_commit"]), str(registry["repository_path"])
    )
    assert _is_ancestor(str(registry["introduction_commit"]), PR42_MERGE_COMMIT)


def test_voy_chain_references_existing_roadmap_anchors_and_keeps_v9_branched() -> None:
    route = _load_route()
    stages = [_mapping(item) for item in _sequence(route["stages"])]
    assert [stage["stage_id"] for stage in stages] == [
        f"VOY-V{index}" for index in range(1, 10)
    ]
    assert [stage["sequence"] for stage in stages] == list(range(1, 10))
    for index, stage in enumerate(stages):
        assert set(stage) == {
            "canonical_ids",
            "navigation_predecessor_ids",
            "purpose_id",
            "reference_relation",
            "sequence",
            "stage_id",
        }
        assert stage["navigation_predecessor_ids"] == (
            [] if index == 0 else [f"VOY-V{index}"]
        )

    assert [stage["purpose_id"] for stage in stages] == [
        "close-d7-v0-1-chronology",
        "fresh-successor-contract-and-coordinates",
        "prospective-receipt-and-conforming-descriptive-artifact",
        "one-d7-terminal",
        "conditional-isolated-d8",
        "outcome-blind-f2-f4-psi-admissibility",
        "same-substrate-field-core-loop-and-detection-limit",
        "frozen-pythia-160m-structural-subject-run",
        "held-out-semantic-sae-causal-checkpoint-handoff",
    ]
    assert stages[3]["canonical_ids"] == ["D7-OPS-19", "D7-OPS-20", "D7-OPS-24"]
    assert stages[4]["canonical_ids"] == ["D7-OPS-17", "D7-OPS-24"]

    roadmap = _mapping(route["canonical_roadmap_binding"])
    roadmap_text = _git_blob(
        str(roadmap["source_commit"]), str(roadmap["repository_path"])
    ).decode()
    refs = [str(ref) for stage in stages for ref in _sequence(stage["canonical_ids"])]
    assert not any(ref.startswith("LIB-") for ref in refs)
    assert all(
        re.fullmatch(r"(?:D7-OPS-\d{2}|SCI-S[1-4](?:-R\d{2})?)", ref) for ref in refs
    )
    for ref in set(refs):
        assert f'id="{ref.lower()}"' in roadmap_text

    branches = {
        name: _mapping(value)
        for name, value in _mapping(route["v9_branch_contract"]).items()
    }
    assert set(branches) == {
        "positive",
        "qualified_zero",
        "qualified_null",
        "fail",
        "insufficient",
        "invalid_protocol",
    }
    assert branches["positive"]["sci_s3_navigation_allowed"] is True
    for name in set(branches) - {"positive"}:
        assert branches[name]["sci_s3_navigation_allowed"] is False
    for name in ("positive", "qualified_zero", "qualified_null"):
        assert branches[name]["sci_s4_navigation_allowed"] is True
    for name in ("fail", "insufficient", "invalid_protocol"):
        assert branches[name]["sci_s4_navigation_allowed"] is False
    assert branches["positive"]["sci_s4_condition"] == "eligible_quantity_only"
    for name in ("qualified_zero", "qualified_null"):
        assert (
            branches[name]["sci_s4_condition"] == "qualified_endpoint_replication_only"
        )


def test_route_preserves_falsifiability_without_gating_the_library_lane() -> None:
    route = _load_route()
    navigation = _mapping(route["navigation_contract"])
    for name in (
        "future_route_change_requires_dated_ledger_entry_before_affected_input_consumption",
        "future_route_change_requires_new_version_and_review",
        "future_route_version_may_change_future_stages",
        "voy_ids_are_navigation_aliases",
    ):
        assert navigation[name] is True
    for name, value in navigation.items():
        if name not in {
            "future_route_change_requires_dated_ledger_entry_before_affected_input_consumption",
            "future_route_change_requires_new_version_and_review",
            "future_route_version_may_change_future_stages",
            "voy_ids_are_navigation_aliases",
        }:
            assert value is False, name

    boundary = _mapping(route["claim_boundary"])
    assert boundary["claim_ceiling"] == "level_0"
    assert boundary["claim_delta"] == "none"
    for name, value in boundary.items():
        if name not in {"claim_ceiling", "claim_delta"}:
            assert value is False, name

    library = _mapping(route["library_guard"])
    assert library["claim_level_effect"] == library["library_lane_effect"] == "none"
    assert library["maturity_promotion_by_route"] == "none"
    assert library["library_lane_independent"] is True
    assert library["two_independent_consumers_rule_retained"] is True
    for name, value in library.items():
        if name.startswith("route_") and name.endswith("_allowed"):
            assert value is False, name

    psi = _mapping(route["psi_guard"])
    assert psi["candidate_families"] == ["F2", "F4"]
    assert psi["control_roles"] == {
        "F0": "support_diagnostic",
        "F1": "geometry_branch",
        "F3": "projection_dependent_baseline",
    }
    assert psi["winner_selected_at_issue"] is False
    assert psi["defect_observables_may_select_family"] is False
    assert psi["subject_outcomes_may_select_family"] is False
    assert psi["same_object_amplitude_direction_required"] is True
    assert psi["model_native_derivation_must_be_frozen_before_subject_access"] is True


def test_v1_declaration_is_fresh_and_closes_the_pre_item23_obligations() -> None:
    route = _load_route()
    declaration = _mapping(route["strict_successor_declaration"])
    assert set(declaration) == {
        "coordinate_scope",
        "facts_at_issue",
        "forbidden_predecessor_coordinates",
        "forbidden_predecessor_identity_evidence",
        "future_entrypoint_coordinates",
        "future_external_coordinates",
        "future_instance_ids",
        "future_repository_coordinates",
        "prospective_chronology_contract",
        "source_closure_policy",
        "successor_lineage_id",
    }
    facts = _mapping(declaration["facts_at_issue"])
    assert facts["absolute_store_coordinate_declared_only"] is True
    for name, value in facts.items():
        if name != "absolute_store_coordinate_declared_only":
            assert value is False, name
    scope = _mapping(declaration["coordinate_scope"])
    assert scope["single_host_lexical_template"] is True
    for name, value in scope.items():
        if name != "single_host_lexical_template":
            assert value is False, name

    predecessor = _mapping(declaration["forbidden_predecessor_coordinates"])
    future_repo = _mapping(declaration["future_repository_coordinates"])
    future_external = _mapping(declaration["future_external_coordinates"])
    future_entrypoint = _mapping(declaration["future_entrypoint_coordinates"])
    assert len(set(map(str, future_external.values()))) == len(future_external)
    assert set(map(str, future_external.values())).isdisjoint(
        {
            "d7-prefix-evidence-only-v0",
            "d7-authoritative-start-v0",
            "d7-attempt-evidence",
            "d7-official-output-v0-1",
            "d7-official-terminal-v0-1",
        }
    )
    assert len(set(map(str, _sequence(declaration["future_instance_ids"])))) == len(
        _sequence(declaration["future_instance_ids"])
    )
    old_repo_root = PurePosixPath(str(predecessor["repository_root"]))
    new_repo_root = PurePosixPath(str(future_repo["repository_root"]))
    assert old_repo_root != new_repo_root
    assert old_repo_root not in new_repo_root.parents
    assert new_repo_root not in old_repo_root.parents
    assert len(set(map(str, future_repo.values()))) == len(future_repo)
    for value in future_repo.values():
        path = PurePosixPath(str(value))
        assert ".." not in path.parts
        assert path == new_repo_root or new_repo_root in path.parents

    old_store = Path(str(predecessor["external_store_path"]))
    new_store = Path(str(future_external["external_store_path"]))
    assert old_store.is_absolute() and new_store.is_absolute()
    assert old_store != new_store
    assert old_store not in new_store.parents
    assert new_store not in old_store.parents
    assert predecessor["preparation_script"] != future_entrypoint["preparation_script"]
    assert predecessor["runner_script"] != future_entrypoint["runner_script"]

    chronology = _mapping(declaration["prospective_chronology_contract"])
    assert chronology["receipt_required_bindings"] == [
        "replay_target",
        "full_design_freeze",
        "launch_intent",
        "official_execution_attempt_envelope",
        "descriptive_result_namespace_absence",
    ]
    for name in (
        "descriptive_result_must_follow_receipt",
        "launch_intent_must_be_receipt_bound",
        "official_execution_attempt_must_be_exclusive_no_replace",
        "descriptive_output_namespace_absence_must_be_receipt_bound",
        "replay_target_must_transitively_bind_complete_design_family_admission_protocol_source_graph_and_lifecycle",
        "successor_seed_values_must_be_fresh_and_exclude_predecessor_inventory",
    ):
        assert chronology[name] is True
    assert chronology["later_descriptor_may_cure_missing_pre_item23_binding"] is False
    assert chronology["item23_values_may_select_contract"] is False
    assert future_repo["launch_intent"].endswith("/launch-members/launch-intent.json")
    assert future_repo["official_execution_attempt_envelope"].endswith(
        "/pre-item23/official-execution-attempt-envelope.json"
    )
    assert future_repo["descriptive_result"].endswith(
        "/post-d6-descriptive-analysis-result.json"
    )

    future_strings = list(
        _iter_strings(
            {
                "repo": future_repo,
                "external": future_external,
                "entrypoint": future_entrypoint,
                "ids": declaration["future_instance_ids"],
            }
        )
    )
    assert all(
        "d7_spectral_moment_confirmation_v0_1" not in value for value in future_strings
    )
    assert all("d7-item24" not in value for value in future_strings)
    assert all(re.fullmatch(r"[0-9a-f]{64}", value) is None for value in future_strings)

    predecessor_evidence = _mapping(
        declaration["forbidden_predecessor_identity_evidence"]
    )
    for name in (
        "bound_root_instance_bytes_forbidden_as_successor_instances",
        "attempt_seed_physical_and_source_runtime_descendants_forbidden",
        "unchanged_scientific_parent_identities_may_be_referenced_as_historical_predecessor_evidence_only",
    ):
        assert predecessor_evidence[name] is True
    assert (
        predecessor_evidence["historical_predecessor_evidence_grants_authority"]
        is False
    )
    source_commit = str(predecessor_evidence["source_commit"])
    bindings = [_mapping(item) for item in _sequence(predecessor_evidence["bindings"])]
    assert {str(binding["role"]) for binding in bindings} == {
        "full_design",
        "launch_descriptor",
        "official_seed_inventory",
        "physical_store_lane_identity",
        "replay_target",
        "source_reanchor",
    }
    for binding in bindings:
        source = _git_blob(source_commit, str(binding["repository_path"]))
        assert hashlib.sha256(source).hexdigest() == binding["sha256"]

    physical_binding = next(
        binding
        for binding in bindings
        if binding["role"] == "physical_store_lane_identity"
    )
    physical = _mapping(
        parse_canonical_json(
            _git_blob(source_commit, str(physical_binding["repository_path"])),
            label="v0.1 physical identity",
        )
    )
    assert physical["store_path"] == predecessor["external_store_path"]
    assert str(physical["lane_path"]).endswith("/d7-authoritative-start-v0")

    closure = _mapping(declaration["source_closure_policy"])
    assert closure["generic_record_schema_reuse_authorized_at_issue"] is False
    assert closure["predecessor_artifact_as_successor_authority_input_allowed"] is False
    assert (
        closure["any_preexisting_d7_execution_module_reuse_authorized_at_issue"]
        is False
    )
    assert closure["new_entrypoint_and_context_required"] is True
    assert closure["predecessor_value_bearing_post_d6_code_allowed"] is False
    assert closure["successor_source_closure_bound_at_issue"] is False
    assert len(_sequence(closure["predecessor_value_bearing_post_d6_code_paths"])) == 3
