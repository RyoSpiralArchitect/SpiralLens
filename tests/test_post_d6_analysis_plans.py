from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

from spirallens import qualification
from spirallens.core.canonical import (
    canonical_json_bytes,
    parse_canonical_json,
)

REPOSITORY = Path(__file__).resolve().parents[1]
DESCRIPTIVE_PATH = (
    REPOSITORY / "protocols" / "post_d6_descriptive_analysis_v0_1.json"
)
GAP_PATH = REPOSITORY / "protocols" / "d7_structural_gap_matrix_v0_1.json"
DESCRIPTIVE_SHA256 = (
    "fe5dad073cca8c671d3fee5feb46001b6a22303e5aa7d9667cbf50816daabb40"
)
GAP_SHA256 = "e91236e4a28367f43ec23fc86228657d488ca933e364b2b9f8c1ec9993504758"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _git_blob(commit: str, repository_path: str) -> bytes:
    completed = subprocess.run(
        ["git", "-C", str(REPOSITORY), "show", f"{commit}:{repository_path}"],
        check=False,
        capture_output=True,
    )
    assert completed.returncode == 0, completed.stderr.decode(
        "utf-8",
        errors="replace",
    )
    return completed.stdout


def _load(path: Path, *, expected_sha256: str) -> dict[str, object]:
    source = path.read_bytes()
    assert hashlib.sha256(source).hexdigest() == expected_sha256
    document = parse_canonical_json(source, label=path.name)
    assert isinstance(document, dict)
    assert canonical_json_bytes(document) == source
    return document


def _mapping(value: object) -> dict[str, object]:
    assert isinstance(value, dict)
    assert all(isinstance(key, str) for key in value)
    return value


def _sequence(value: object) -> list[object]:
    assert isinstance(value, list)
    return value


def test_frozen_plan_files_have_exact_canonical_identities() -> None:
    descriptive = _load(
        DESCRIPTIVE_PATH,
        expected_sha256=DESCRIPTIVE_SHA256,
    )
    gap = _load(GAP_PATH, expected_sha256=GAP_SHA256)

    assert descriptive["schema_version"] == (
        "spirallens.postselection-descriptive-analysis-plan.v0.1"
    )
    assert gap["schema_version"] == (
        "spirallens.d7-structural-gap-matrix.v0.1"
    )


def test_descriptive_plan_is_explicitly_postselection_and_nonpromotional() -> None:
    plan = _load(DESCRIPTIVE_PATH, expected_sha256=DESCRIPTIVE_SHA256)

    assert set(plan) == {
        "analysis_class",
        "chronology",
        "claim_boundary",
        "input_policy",
        "parent_evidence",
        "plan_id",
        "publication_contract",
        "schema_version",
        "scientific_units",
        "status",
        "work_packages",
    }
    assert plan["analysis_class"] == "postselection_descriptive_only"
    assert plan["status"] == "frozen_not_run"

    chronology = _mapping(plan["chronology"])
    assert chronology == {
        "analysis_result_produced": False,
        "analysis_runner_execution_started": False,
        "d7_design_frozen_before_future_analysis_execution_required": True,
        "d7_design_use_authorized": False,
        "frozen_after_outcome_exposure": True,
        "planning_used_opened_outcome_values": True,
        "postselection_descriptive_only": True,
        "preregistration_claimed": False,
        "prior_outcome_exposure": True,
    }

    boundary = _mapping(plan["claim_boundary"])
    assert boundary["claim_ceiling"] == "level_0"
    assert boundary["claim_delta"] == "none"
    assert boundary["scientific_claim_eligible"] is False
    assert boundary["synthetic_qualified"] is False
    for name, value in boundary.items():
        if name not in {"claim_ceiling", "claim_delta"}:
            assert value is False, name

    policy = _mapping(plan["input_policy"])
    assert policy["confirmation_value_access_authorized"] is False
    assert policy["model_access_authorized"] is False
    assert policy["pythia_engineering_value_access_authorized"] is False
    assert policy["subject_value_access_authorized"] is False
    forbidden = set(_sequence(policy["forbidden_input_classes"]))
    assert {
        "unopened-confirmation-values",
        "pythia-engineering-manifest-or-payload",
        "subject-descriptor-or-values",
        "model-or-network-access",
    }.issubset(forbidden)

    publication = _mapping(plan["publication_contract"])
    assert publication["result_status"] == "not_run"
    assert publication["runner_implemented"] is False
    assert publication["writer_implemented"] is False
    assert publication["d7_use_forbidden"] is True
    assert publication["d7_full_design_freeze_receipt_required"] is True
    assert (
        publication["d7_full_design_frozen_before_execution_required"] is True
    )
    assert publication["claim_delta"] == "none"


def test_descriptive_plan_binds_the_exact_existing_parent_bytes() -> None:
    plan = _load(DESCRIPTIVE_PATH, expected_sha256=DESCRIPTIVE_SHA256)
    parent = _mapping(plan["parent_evidence"])

    for path_key, digest_key, merge_commit_key in (
        ("protocol_path", "protocol_source_sha256", "pr9_merge_commit"),
        (
            "terminal_result_path",
            "terminal_result_sha256",
            "pr9_merge_commit",
        ),
        (
            "terminal_manifest_path",
            "terminal_manifest_sha256",
            "pr9_merge_commit",
        ),
        (
            "terminal_consumption_path",
            "terminal_consumption_sha256",
            "pr9_merge_commit",
        ),
        ("d6_decision_path", "d6_decision_sha256", "pr10_merge_commit"),
    ):
        relative = parent[path_key]
        expected = parent[digest_key]
        merge_commit = parent[merge_commit_key]
        assert isinstance(relative, str)
        assert isinstance(expected, str)
        assert isinstance(merge_commit, str)
        assert not Path(relative).is_absolute()
        current_source = (REPOSITORY / relative).read_bytes()
        committed_source = _git_blob(merge_commit, relative)
        assert current_source == committed_source
        assert hashlib.sha256(committed_source).hexdigest() == expected

    result_source = (
        REPOSITORY / str(parent["terminal_result_path"])
    ).read_bytes()
    result = parse_canonical_json(result_source, label="selection result")
    result_mapping = _mapping(result)
    assert result_mapping["result_id"] == parent["terminal_result_id"]
    assert (
        result_mapping["result_evidence_root_sha256"]
        == parent["result_evidence_root_sha256"]
    )
    assert (
        result_mapping["selection_launch_authorization_sha256"]
        == parent["selection_launch_authorization_sha256"]
    )
    assert result_mapping["d6_d8_advanced"] is False
    assert result_mapping["synthetic_qualified"] is False

    decision_source = (
        REPOSITORY / str(parent["d6_decision_path"])
    ).read_bytes()
    decision = _mapping(
        parse_canonical_json(decision_source, label="D6 decision")
    )
    assert decision["decision_id"] == parent["d6_decision_id"]
    assert decision["decision_source_commit"] == (
        parent["d6_decision_source_commit"]
    )
    assert _mapping(decision["d6"])["state"] == "pass"
    assert _mapping(decision["d7"])["state"] == "not_run"
    assert _mapping(decision["d8"])["state"] == "not_run"
    assert decision["confirmation_family_admitted"] is False


def test_descriptive_plan_declares_grains_without_iid_laundering() -> None:
    plan = _load(DESCRIPTIVE_PATH, expected_sha256=DESCRIPTIVE_SHA256)
    units = {
        str(_mapping(item)["unit_id"]): _mapping(item)
        for item in _sequence(plan["scientific_units"])
    }

    assert units["d2-scientific-input-unit"]["declared_count"] == 32
    assert units["d2-scientific-input-unit"][
        "boundary_repeat_collapsed"
    ] is True
    assert units["d2-scientific-input-unit"][
        "seed_block_independence_proved"
    ] is False
    assert units["d4-d5-loop-execution-unit"]["declared_count"] == 64
    assert units["d4-d5-loop-execution-unit"][
        "graph_pair_repeats_per_execution"
    ] == 9
    assert units["d4-d5-loop-execution-unit"][
        "graph_pairs_are_independent_samples"
    ] is False
    assert units["construction-family-unit"]["declared_count"] == 1
    assert all(
        unit["inferential_sample_size_claimed"] is False
        for unit in units.values()
    )

    packages = [_mapping(item) for item in _sequence(plan["work_packages"])]
    assert [item["sequence"] for item in packages] == list(range(1, 9))
    assert [item["analysis_id"] for item in packages] == [
        "identity-lineage-and-claim-boundary",
        "d1-frozen-threshold-margin-atlas",
        "d2-core-case-and-prerequisite-matrix",
        "d3-transformation-law-audit",
        "d4-crossed-graph-descriptive-matrix",
        "d5-worst-case-stress-and-coverage",
        "nonvacuity-abstention-and-failure-ledger",
        "evidence-independence-map",
    ]
    assert all(item["status"] == "planned" for item in packages)


def test_d7_gap_matrix_is_value_blind_and_has_no_progress_score() -> None:
    matrix = _load(GAP_PATH, expected_sha256=GAP_SHA256)

    assert set(matrix) == {
        "analysis_class",
        "chronology",
        "claim_boundary",
        "gap_entries",
        "gap_vocabulary",
        "input_policy",
        "matrix_id",
        "next_step_contract",
        "noncredit_rules",
        "parent_contract",
        "reviewed_source_surface",
        "schema_version",
        "status",
    }
    assert matrix["analysis_class"] == "value_blind_structural_gap_matrix"
    assert matrix["status"] == "frozen_review_only"
    chronology = _mapping(matrix["chronology"])
    assert chronology["prior_outcome_exists"] is True
    assert chronology["operator_prior_outcome_exposure"] is True
    assert chronology["outcome_values_used_as_matrix_input"] is False
    assert chronology["terminal_artifact_used_as_matrix_input"] is False
    assert (
        chronology["value_blindness_is_input_policy_not_operator_blinding"]
        is True
    )
    assert chronology["family_admission_performed"] is False
    assert chronology["confirmation_execution_started"] is False

    policy = _mapping(matrix["input_policy"])
    allowed = set(_sequence(policy["allowed_input_paths"]))
    assert all(".selection-terminal" not in str(item) for item in allowed)
    assert all("pythia" not in str(item) for item in allowed)
    assert policy["label_only_family_admission_allowed"] is False
    assert (
        policy["same_family_reseed_counts_as_independent_confirmation"]
        is False
    )

    vocabulary = set(_sequence(matrix["gap_vocabulary"]))
    assert vocabulary == {
        "absent",
        "blocked",
        "contract_only",
        "evidence_present_but_ineligible",
        "implementation_foundation_only",
    }
    entries = [_mapping(item) for item in _sequence(matrix["gap_entries"])]
    assert all(item["status"] in vocabulary for item in entries)
    assert all(
        item["claim_effect"] == "none_until_all_requirements_complete"
        for item in entries
    )
    assert len({item["requirement_id"] for item in entries}) == len(entries)

    boundary = _mapping(matrix["claim_boundary"])
    assert boundary["claim_ceiling"] == "level_0"
    assert boundary["claim_delta"] == "none"
    assert boundary["gap_completion_score_authorized"] is False
    assert boundary["gap_percentage_authorized"] is False
    assert boundary["family_candidate_named"] is False
    assert boundary["family_admission_authorized"] is False
    for name, value in boundary.items():
        if name not in {"claim_ceiling", "claim_delta"}:
            assert value is False, name


def test_d7_gap_rows_cover_the_locked_obligations_without_admission() -> None:
    matrix = _load(GAP_PATH, expected_sha256=GAP_SHA256)
    entries = {
        str(_mapping(item)["requirement_id"]): _mapping(item)
        for item in _sequence(matrix["gap_entries"])
    }
    assert set(entries) == {
        "charge-blind-core-path",
        "confirmation-implementation-registry-binding",
        "confirmation-store-durability",
        "distinct-construction-family",
        "distinct-generator-family",
        "exclusive-attempt-and-terminal-lineage",
        "isolated-byte-identical-d8-replay",
        "locked-graph-axes-consumption",
        "locked-surrogate-estimator-and-trivialization",
        "locked-thresholds-and-aggregation",
        "no-override-no-exclusion-chronology",
        "pre-access-family-admission-receipt",
        "required-case-semantics",
        "required-cells-and-stress-strata",
        "sealed-before-confirmation-access",
        "selection-confirmation-evidence-disjointness",
        "separate-loop-path",
        "typed-d7-result-and-evidence-root",
    }
    assert entries["distinct-construction-family"]["status"] == (
        "implementation_foundation_only"
    )
    assert entries["distinct-generator-family"]["status"] == (
        "implementation_foundation_only"
    )
    assert entries["typed-d7-result-and-evidence-root"]["status"] == "absent"
    assert entries["isolated-byte-identical-d8-replay"]["status"] == "blocked"

    next_step = _mapping(matrix["next_step_contract"])
    assert (
        next_step[
            "full_d7_design_freeze_required_before_descriptive_analysis_execution"
        ]
        is True
    )

    parent = _mapping(matrix["parent_contract"])
    assert _sha256(REPOSITORY / str(parent["d6_decision_path"])) == (
        parent["d6_decision_sha256"]
    )
    assert parent["d6_state"] == "pass"
    assert parent["d7_state"] == "not_run"
    assert parent["d7_reason_codes"] == [
        "full-d2-d5-confirmation-path-not-implemented",
        "independent-construction-family-not-admitted",
    ]
    assert parent["d8_state"] == "not_run"
    assert parent["d8_reason_codes"] == [
        "d7-not-pass",
        "replay-not-run",
    ]
    assert parent["confirmation_family_admitted"] is False


def test_gap_matrix_source_snapshot_and_pythia_boundary_are_unchanged() -> None:
    matrix = _load(GAP_PATH, expected_sha256=GAP_SHA256)
    surface = _mapping(matrix["reviewed_source_surface"])

    assert surface["commit"] == "f869d53d890ae35b43c3dbca2ce6363c78fea367"
    assert surface["outcome_model_or_subject_values_used"] is False
    for item in _sequence(surface["files"]):
        entry = _mapping(item)
        repository_path = entry["repository_path"]
        assert isinstance(repository_path, str)
        assert hashlib.sha256(
            _git_blob(str(surface["commit"]), repository_path)
        ).hexdigest() == entry["sha256"]

    assert _sha256(
        REPOSITORY / "protocols" / "pythia70_public_example_plumbing_v0_1.yaml"
    ) == "ef93891c7450ef13cc2c5da54bf1a80d4a0b679df2df04964f2cc505e00aaf4c"
    assert _sha256(
        REPOSITORY
        / "experiments"
        / "pythia"
        / "receipts"
        / "pythia70_public_example_plumbing_v0_1.json"
    ) == "4ab51c1e01992dc63f9bea18a7f53e00293a0ec11617f4970abf2a400723ce82"


def test_pr11_adds_no_analysis_runner_writer_or_promotion_api() -> None:
    forbidden = {
        "PostD6AnalysisPlan",
        "D7GapMatrix",
        "load_post_d6_analysis_plan",
        "run_post_d6_analysis",
        "write_post_d6_analysis",
        "admit_d7_family",
        "promote_d7",
        "promote_d8",
    }

    assert forbidden.isdisjoint(qualification.__all__)
    assert all(not hasattr(qualification, name) for name in forbidden)


def test_surrogate_d8_does_not_unlock_subject_or_model_topology() -> None:
    roadmap = " ".join(
        (REPOSITORY / "docs" / "ROADMAP.md").read_text().split()
    )
    preparation = " ".join(
        (
            REPOSITORY / "docs" / "NEXT_EXPERIMENT_PREPARATION.md"
        ).read_text().split()
    )
    anchor = " ".join(
        (
            REPOSITORY / "docs" / "POST_D6_ANALYSIS_AND_D7_GAPS.md"
        ).read_text().split()
    )

    assert (
        "begin the separate representation-native F0-F4 selection lane"
        in roadmap
    )
    assert (
        "current surrogate-engine D7/D8 lane is not sufficient and grants no "
        "subject authority"
    ) in preparation
    assert "not unlocked by surrogate D8 alone" in preparation
    assert (
        "this is an instrument gate, not a model-topology observation"
        in anchor
    )
