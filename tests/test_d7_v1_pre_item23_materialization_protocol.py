from __future__ import annotations

import ast
import hashlib
import os
import subprocess
from collections.abc import Iterator
from pathlib import Path, PurePosixPath

from spirallens.core.canonical import canonical_json_bytes, parse_canonical_json
from spirallens.qualification import confirmation_v1_records as v1_records


REPOSITORY = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = REPOSITORY / "protocols/d7_v1_pre_item23_materialization_v0_1.json"
PROTOCOL_SHA256 = "13d013e007fa30775abb4cd092b264482207dcad23f772aecd966a51cbafbaad"
PROTOCOL_BYTE_COUNT = 43_288
ROUTE_PATH = REPOSITORY / "protocols/voy_v1_v9_strict_successor_route_v0_1.json"
ROUTE_SHA256 = "c8d28138c95d16ab96f508c2386de1d62360e1659057e0b8f7cbe8a380a90e35"
ROUTE_BYTE_COUNT = 13_806
ROUTE_MERGE_COMMIT = "2645ab360598c9ff4f1d9e628b9a9fe1857aedf6"

SCHEMA_ROLES = [
    "c1-seed-free-source-set",
    "c2-source-closure-receipt",
    "exclusive-seed-supply-claim",
    "official-seed-inventory",
    "embedded-full-design",
    "replay-target",
    "full-design-freeze",
    "launch-intent",
    "official-execution-attempt-reservation",
    "pre-item23-chronology-receipt",
    "postselection-descriptive-result",
]
SCHEMA_VERSIONS = [
    "spirallens.d7-v1-c1-seed-free-source-set.v0.1",
    "spirallens.d7-v1-c2-source-closure-receipt.v0.1",
    "spirallens.d7-v1-exclusive-seed-supply-claim.v0.1",
    "spirallens.d7-v1-official-seed-inventory.v0.1",
    "spirallens.d7-v1-embedded-full-design.v0.1",
    "spirallens.d7-v1-replay-target.v0.1",
    "spirallens.d7-v1-full-design-freeze.v0.1",
    "spirallens.d7-v1-launch-intent.v0.1",
    "spirallens.d7-v1-official-execution-attempt-reservation.v0.1",
    "spirallens.d7-v1-pre-item23-chronology-receipt.v0.1",
    "spirallens.d7-v1-postselection-descriptive-result.v0.1",
]
PRE_ITEM23_COORDINATE_KEYS = [
    "c1_source_set",
    "c2_source_closure_receipt",
    "exclusive_seed_supply_claim",
    "official_seed_inventory",
    "replay_target",
    "full_design_freeze",
    "launch_intent",
    "official_execution_attempt_envelope",
    "pre_item23_chronology_receipt",
]
PRE_RECEIPT_COORDINATE_KEYS = PRE_ITEM23_COORDINATE_KEYS[:-1]
GENERIC_REUSE_SHA256 = {
    "src/spirallens/graphs/common.py": "ad5b2db05272dd56f9c53ca29a99116fe1aa1e279c929fa62e24d9868facb26b",
    "src/spirallens/graphs/constructors.py": "4e75253321944bb3fe41b0fbdb624e14e32a056ed9bd7e8c49a8196d348afc3f",
    "src/spirallens/qualification/blind.py": "29d9ef688a85e78acbb07da35b36ee727115be25446f0f670f27d8428d31557d",
    "src/spirallens/qualification/crossed.py": "57d13b834d4ce7b666b9a0c52a4cc81cb1a71b94c329819045af5627279a95a1",
    "src/spirallens/qualification/metamorphic.py": "8a716a7605af9e52cf00efd0fec05ba1b6f17526e8fdc5bb9b9b6f9731c6454c",
    "src/spirallens/qualification/prerequisites.py": "8335e4782ad20f160c8118cc18ea0bd6cfdb03385ed7b4a8cd2a4cbc340c54fa",
    "src/spirallens/qualification/protocol.py": "e4cab4cbd9c1e1dae0e94f37486c80e62979c47dbf294de5776dcc813068ca67",
    "src/spirallens/qualification/winding.py": "36abba8919f518b5095b8c6f84bd2a3da17d4120dcb7a0c82df6335d7a20a379",
    "src/spirallens/synthetic/cartesian_fourier_domain_phantom.py": "a874e534cd9a3bbbcaacf8c37274874993578434ae5648eee80afd8192a6c3b3",
    "src/spirallens/synthetic/cartesian_fourier_estimator.py": "41cc0a9dcfc52ad8edde96118dd47e1a163a37dbfe1c603b57381bb60251abb7",
    "src/spirallens/synthetic/generators.py": "e8065087de65b526570cb8b0f1880898f290797a8701c48656ad6338a13b584b",
    "src/spirallens/synthetic/spectral_moment_confirmation.py": "6fd52c03c35ba8de6227b8583dfa6ff58ad913de7b85f0b38ccb7122f7dcc252",
}
HISTORICAL_BINDINGS = [
    (
        "historical_template_evidence_only",
        "protocols/post_d6_descriptive_analysis_v0_1.json",
        "9b1a8d9c3857fd18fff7b4dfb20a75eade2f56f4933e05126830669cd8ccb981",
        "4838cef49997a70f1d6281b8097905510e7ec351",
    ),
    (
        "parent-protocol",
        "protocols/d0_d5_f2_cartesian_selection_v0_1.json",
        "9908bb83bb5ff5642416aa09d9e468e0a9499185cec9305e69a54143f2578bd1",
        "22eb9bd6bcd447f9a9afde0a7c26b8a1aef42993",
    ),
    (
        "parent-result",
        "experiments/qualification/d0_d5_f2_cartesian_selection_v0_1/attempt/f63dcc162a896d0957cb7a8d437eace87eeadfc2574921819e7f98a27a704d58.selection-terminal/terminal-artifact.json",
        "44749d8d237b8b35874099c605f8de3d76130691ce8beb92e1ccf80fa368c13a",
        "22eb9bd6bcd447f9a9afde0a7c26b8a1aef42993",
    ),
    (
        "parent-manifest",
        "experiments/qualification/d0_d5_f2_cartesian_selection_v0_1/attempt/f63dcc162a896d0957cb7a8d437eace87eeadfc2574921819e7f98a27a704d58.selection-terminal/terminal-manifest.json",
        "518b66d715cf9bd05e12de62cb5681ec63ec7f978fd4d2538ba3c2594deed4b1",
        "22eb9bd6bcd447f9a9afde0a7c26b8a1aef42993",
    ),
    (
        "parent-consumption",
        "experiments/qualification/d0_d5_f2_cartesian_selection_v0_1/attempt/f63dcc162a896d0957cb7a8d437eace87eeadfc2574921819e7f98a27a704d58.selection-terminal/selection-consumption.json",
        "a42ae9cffb6a2c87de6ed645e0982e85b09046a4ed5ad3f815a8a8ce38c0cadb",
        "22eb9bd6bcd447f9a9afde0a7c26b8a1aef42993",
    ),
    (
        "parent-d6-decision",
        "experiments/qualification/d0_d5_f2_cartesian_selection_v0_1/d6-surrogate-advancement-decision.json",
        "c1c3fbbb9a06e8df120755dcf159e015636d96993bd6ec3a6792312618587a07",
        "f869d53d890ae35b43c3dbca2ce6363c78fea367",
    ),
]


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
    assert completed.returncode == 0, completed.stderr.decode(errors="replace")
    return completed.stdout


def _is_ancestor(ancestor: str, descendant: str = "HEAD") -> bool:
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


def _load_canonical(path: Path, *, sha256: str, byte_count: int) -> dict[str, object]:
    source = path.read_bytes()
    assert len(source) == byte_count
    assert hashlib.sha256(source).hexdigest() == sha256
    value = parse_canonical_json(source, label=path.name)
    assert isinstance(value, dict)
    assert canonical_json_bytes(value) == source
    return value


def _load_protocol() -> dict[str, object]:
    return _load_canonical(
        PROTOCOL_PATH,
        sha256=PROTOCOL_SHA256,
        byte_count=PROTOCOL_BYTE_COUNT,
    )


def _load_route() -> dict[str, object]:
    return _load_canonical(ROUTE_PATH, sha256=ROUTE_SHA256, byte_count=ROUTE_BYTE_COUNT)


def _strings(value: object) -> Iterator[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _strings(item)


def _path_state(path: Path) -> tuple[object, ...]:
    try:
        stat = os.lstat(path)
    except FileNotFoundError:
        return ("absent",)
    return ("present", stat.st_mode, stat.st_ino, stat.st_size, stat.st_mtime_ns)


def test_protocol_is_canonical_structural_candidate_without_authority() -> None:
    protocol = _load_protocol()
    assert set(protocol) == {
        "artifact_role",
        "attempt_reservation_contract",
        "authority",
        "claim_boundary",
        "coordinate_and_member_layout",
        "domain_separated_derivation_contracts",
        "external_durable_chronology_contract",
        "facts_at_protocol_issue",
        "future_authoritative_verification_contract",
        "future_chronology",
        "historical_input_policy",
        "materialization_boundary",
        "navigation_projection",
        "postselection_result_contract",
        "protocol_id",
        "receipt_contract",
        "record_byte_cap_contract",
        "replay_target_contract",
        "route_binding",
        "schema_inventory",
        "schema_inventory_contract",
        "schema_version",
        "seed_supply_and_replacement_contract",
        "source_contract",
        "status",
        "successor_lineage_id",
    }
    assert protocol["schema_version"] == (
        "spirallens.d7-v1-pre-item23-materialization-protocol.v0.1"
    )
    assert protocol["protocol_id"] == "d7-v1-pre-item23-materialization-v0-1"
    assert protocol["successor_lineage_id"] == "d7-spectral-moment-confirmation-v1"
    assert protocol["status"] == "frozen_not_run"
    assert all(value is False for value in _mapping(protocol["authority"]).values())
    assert all(
        value is False
        for value in _mapping(protocol["facts_at_protocol_issue"]).values()
    )
    schema_boundary = _mapping(protocol["schema_inventory_contract"])
    assert schema_boundary == {
        "materialization_authority": False,
        "persistence_implementation_claimed_at_protocol_issue": False,
        "primary_schemas_are_structural_candidates_only": True,
        "runtime_implementation_claimed_at_protocol_issue": False,
    }
    boundary = _mapping(protocol["materialization_boundary"])
    assert boundary["artifact_generation_in_this_protocol_change"] is False
    assert boundary["protocol_import_or_parse_may_create_files"] is False
    assert boundary["route_snapshot_modified"] is False
    claim = _mapping(protocol["claim_boundary"])
    assert claim["claim_ceiling"] == "level_0"
    assert claim["claim_delta"] == claim["library_lane_effect"] == "none"


def test_route_bytes_ancestry_and_voy_v3_projection_are_exact() -> None:
    protocol = _load_protocol()
    route = _load_route()
    binding = _mapping(protocol["route_binding"])
    assert binding == {
        "byte_count": ROUTE_BYTE_COUNT,
        "canonical_sha256": ROUTE_SHA256,
        "merge_commit": ROUTE_MERGE_COMMIT,
        "repository_path": "protocols/voy_v1_v9_strict_successor_route_v0_1.json",
        "route_id": "voy-v1-v9-strict-successor-route-v0-1",
    }
    assert _git_blob(ROUTE_MERGE_COMMIT, str(binding["repository_path"])) == (
        ROUTE_PATH.read_bytes()
    )
    assert _is_ancestor(ROUTE_MERGE_COMMIT)
    projection = _mapping(protocol["navigation_projection"])
    assert projection == {
        "canonical_ids": ["D7-OPS-22", "D7-OPS-23"],
        "completion_credit_added": False,
        "navigation_predecessor_id": "VOY-V2",
        "route_stage_id": "VOY-V3",
        "voy_id_is_navigation_alias_only": True,
    }
    stage = next(
        _mapping(item)
        for item in _sequence(route["stages"])
        if _mapping(item)["stage_id"] == "VOY-V3"
    )
    assert stage["canonical_ids"] == projection["canonical_ids"]
    assert stage["navigation_predecessor_ids"] == ["VOY-V2"]
    declaration = _mapping(route["strict_successor_declaration"])
    assert declaration["successor_lineage_id"] == protocol["successor_lineage_id"]
    route_coordinates = _mapping(declaration["future_repository_coordinates"])
    coordinates = _mapping(protocol["coordinate_and_member_layout"])
    for key in (*PRE_ITEM23_COORDINATE_KEYS, "descriptive_result", "repository_root"):
        assert coordinates[key] == route_coordinates[key]
    external = _mapping(protocol["external_durable_chronology_contract"])
    assert (
        external["route_future_external_coordinates"]
        == declaration["future_external_coordinates"]
    )


def test_record_byte_caps_are_frozen_by_role_before_any_parse() -> None:
    cap = _mapping(_load_protocol()["record_byte_cap_contract"])
    assert cap["default_max_record_bytes"] == 4 * 1024 * 1024
    assert cap["postselection_result_max_record_bytes"] == 16 * 1024 * 1024
    assert cap["postselection_result_role"] == "postselection-descriptive-result"
    assert cap["default_primary_schema_roles"] == SCHEMA_ROLES[:-1]
    assert cap["structural_contract_only"] is True
    constants = _mapping(cap["loader_constant_bindings"])
    assert constants == {
        "default_constant_name": "D7_V1_DEFAULT_MAX_RECORD_BYTES",
        "module_path": "src/spirallens/qualification/confirmation_v1_records.py",
        "postselection_result_constant_name": (
            "D7_V1_POSTSELECTION_RESULT_MAX_RECORD_BYTES"
        ),
    }
    assert (
        getattr(v1_records, str(constants["default_constant_name"])) == 4 * 1024 * 1024
    )
    assert (
        getattr(v1_records, str(constants["postselection_result_constant_name"]))
        == 16 * 1024 * 1024
    )
    default_classes = (
        v1_records.D7V1C1SourceSetRecord,
        v1_records.D7V1C2SourceClosureReceipt,
        v1_records.D7V1ExclusiveSeedSupplyClaim,
        v1_records.D7V1OfficialSeedInventory,
        v1_records.D7V1EmbeddedFullDesign,
        v1_records.D7V1ReplayTarget,
        v1_records.D7V1FullDesignFreeze,
        v1_records.D7V1LaunchIntent,
        v1_records.D7V1OfficialExecutionAttemptReservation,
        v1_records.D7V1PreItem23ChronologyReceipt,
    )
    assert all(cls.max_record_bytes == 4 * 1024 * 1024 for cls in default_classes)
    assert (
        v1_records.D7V1PostselectionDescriptiveResult.max_record_bytes
        == 16 * 1024 * 1024
    )
    assert cap["sizing_evidence"] == {
        "historical_result_binding_reference": (
            "historical_input_policy.predecessor_result_forbidden"
        ),
        "historical_result_byte_count": 5_293_662,
        "historical_outputs_array_canonical_byte_count": 5_282_369,
    }


def test_eleven_schema_candidates_close_nine_pre_item23_files() -> None:
    protocol = _load_protocol()
    inventory = [_mapping(item) for item in _sequence(protocol["schema_inventory"])]
    assert [item["artifact_role"] for item in inventory] == SCHEMA_ROLES
    assert [item["schema_version"] for item in inventory] == SCHEMA_VERSIONS
    assert len(set(SCHEMA_VERSIONS)) == 11
    assert all(version.startswith("spirallens.d7-v1-") for version in SCHEMA_VERSIONS)
    assert [item["storage_kind"] for item in inventory].count(
        "embedded_canonical_subdocument"
    ) == 1

    coordinates = _mapping(protocol["coordinate_and_member_layout"])
    roles = _mapping(coordinates["v3_exact_pre_item23_file_coordinate_roles"])
    assert list(roles) == sorted(PRE_ITEM23_COORDINATE_KEYS)
    paths = [str(coordinates[key]) for key in PRE_ITEM23_COORDINATE_KEYS]
    assert len(set(paths)) == 9
    root = PurePosixPath(str(coordinates["repository_root"]))
    assert all(root in PurePosixPath(path).parents for path in paths)
    full_design = _mapping(coordinates["full_design_storage"])
    assert full_design == {
        "container_file_coordinate_key": "replay_target",
        "instance_id": "d7-v1-spectral-moment-official-full-design",
        "json_pointer": "/full_design",
        "repository_reference": (
            "experiments/qualification/d7_spectral_moment_confirmation_v1/"
            "seed-supply/published-target/replay-target.json#/full_design"
        ),
        "storage_kind": "embedded_canonical_subdocument",
    }
    future_strings = list(_strings({"coordinates": coordinates, "schemas": inventory}))
    assert all(
        "d7_spectral_moment_confirmation_v0_1" not in item for item in future_strings
    )
    assert all("/full-design.json" not in item for item in future_strings)
    assert (
        _mapping(protocol["source_contract"])[
            "existing_persisted_record_schema_may_be_used_for_v1"
        ]
        is False
    )


def test_source_contract_binds_fresh_paths_and_exact_reuse_bytes() -> None:
    source = _mapping(_load_protocol()["source_contract"])
    required = [str(item) for item in _sequence(source["required_new_source_paths"])]
    assert required == [
        "protocols/d7_v1_pre_item23_materialization_v0_1.json",
        "src/spirallens/qualification/confirmation_v1_records.py",
        "src/spirallens/qualification/confirmation_v1_materialization.py",
        "src/spirallens/qualification/confirmation_v1_post_d6_descriptive.py",
        "src/spirallens/qualification/confirmation_v1_official_execution.py",
        "scripts/prepare_d7_v1_launch.py",
        "scripts/run_d7_v1.py",
    ]
    assert len([item for item in required if item.startswith("src/")]) == 4
    assert len([item for item in required if item.startswith("scripts/")]) == 2

    exceptions = [
        _mapping(item)
        for item in _sequence(source["approved_exact_function_runtime_reuse"])
    ]
    expected_symbols = {
        "build_seed_free_d7_confirmation_execution_design": (
            "src/spirallens/qualification/confirmation_execution_design.py",
            "824553e20b29e74f29959755079d9b0d87b4f244d95d6988a97e94dc52889d13",
            "fresh_five_parent_seed_free_scientific_projection_only",
        ),
        "_execute_d7_seed_slot_primary_runtime": (
            "src/spirallens/qualification/confirmation_execution_kernel.py",
            "e271ebb70ef59f2de7c9df45e15eebc9a1e00b6457d9ad735f6f3284d1e68cea",
            "oracle_free_prediction_only",
        ),
    }
    assert {str(item["allowed_symbol"]) for item in exceptions} == set(expected_symbols)
    for item in exceptions:
        symbol = str(item["allowed_symbol"])
        path, digest, purpose = expected_symbols[symbol]
        assert item["repository_path"] == path
        assert item["source_commit"] == ROUTE_MERGE_COMMIT
        assert item["source_sha256"] == digest
        assert item["runtime_purpose"] == purpose
        assert item["reuse_scope"] == "runtime_function_only"
        for key in (
            "authority_transfer_allowed",
            "persistence_transfer_allowed",
            "schema_transfer_allowed",
        ):
            assert item[key] is False
        blob = _git_blob(ROUTE_MERGE_COMMIT, path)
        assert hashlib.sha256(blob).hexdigest() == digest
        functions = {
            node.name
            for node in ast.parse(blob).body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        assert symbol in functions

    tiers = _mapping(source["reuse_tiers"])
    assert _mapping(tiers["unconditional_foundation"])["python_modules"] == [
        "python_standard_library",
        "spirallens._repository_context",
        "spirallens.core.canonical",
        "spirallens.qualification.common",
    ]
    conditional = _mapping(tiers["conditional_exact_digest_review"])
    assert conditional["review_status_at_protocol_issue"] == (
        "exact_digest_bound_transitive_review_pending"
    )
    candidates = [_mapping(item) for item in _sequence(conditional["sources"])]
    assert {
        str(item["repository_path"]): str(item["source_sha256"]) for item in candidates
    } == (GENERIC_REUSE_SHA256)
    for item in candidates:
        assert item["source_commit"] == ROUTE_MERGE_COMMIT
        assert item["reuse_scope"] == "scientific_math_only"
        for key in (
            "authority_transfer_allowed",
            "persistence_transfer_allowed",
            "schema_transfer_allowed",
        ):
            assert item[key] is False
        blob = _git_blob(ROUTE_MERGE_COMMIT, str(item["repository_path"]))
        assert hashlib.sha256(blob).hexdigest() == item["source_sha256"]
    forbidden = _mapping(tiers["forbidden_legacy_reuse"])
    assert forbidden["reuse_authorized"] is False
    forbidden_paths = [
        str(item) for item in _sequence(forbidden["module_path_patterns"])
    ]
    assert (
        "src/spirallens/qualification/confirmation_official_execution.py"
        in forbidden_paths
    )
    assert "src/spirallens/qualification/confirmation_attempt_*.py" in forbidden_paths
    assert (
        "src/spirallens/qualification/confirmation_seed_supply_contracts.py"
        in forbidden_paths
    )


def test_historical_inputs_and_descriptive_read_surface_are_closed() -> None:
    policy = _mapping(_load_protocol()["historical_input_policy"])
    plan = _mapping(policy["historical_plan_binding"])
    parents = [
        _mapping(item)
        for item in _sequence(policy["permitted_historical_scientific_parents"])
    ]
    actual = [plan, *parents]
    assert [item["role"] for item in actual] == [
        item[0] for item in HISTORICAL_BINDINGS
    ]
    for binding, (_, path, digest, commit) in zip(
        actual, HISTORICAL_BINDINGS, strict=True
    ):
        assert binding["repository_path"] == path
        assert binding["canonical_sha256"] == digest
        assert binding["source_commit"] == commit
        assert binding["authority_for_v1"] is False
        assert binding["descriptive_input_allowed"] is True
        blob = _git_blob(commit, path)
        assert hashlib.sha256(blob).hexdigest() == digest
        assert canonical_json_bytes(parse_canonical_json(blob, label=path)) == blob
        assert binding["byte_count"] == len(blob)
        assert _is_ancestor(commit, ROUTE_MERGE_COMMIT)
    assert [item["artifact_binding_role"] for item in actual] == [
        "historical-post-d6-plan",
        "parent-protocol",
        "parent-result",
        "parent-manifest",
        "parent-consumption",
        "parent-d6-decision",
    ]
    assert policy["historical_plan_role_projection"] == {
        "artifact_binding_role": "historical-post-d6-plan",
        "policy_role": "historical_template_evidence_only",
    }

    negative = _mapping(_sequence(policy["negative_exclusion_inputs"])[0])
    assert negative == {
        "artifact_binding_role": "historical-predecessor-seed-inventory",
        "artifact_contract_id": "spirallens.d7-official-seed-inventory-input.v0.1",
        "authority_for_v1": False,
        "byte_count": 1_250,
        "canonical_sha256": "63c0a8cba725895e6ab524da6f4a515e1c713a241d6f76c45a9ac04ff2e5c3b8",
        "descriptive_input_allowed": False,
        "permitted_use": "supplier_only_negative_seed_exclusion",
        "repository_path": (
            "experiments/qualification/d7_spectral_moment_confirmation_v0_1/"
            "item22-seed-supply/published-target/official-seed-inventory.json"
        ),
        "source_commit": "aa5364da5478c4ebe782cfd382f4a18725a50e04",
        "pinned_predecessor_seed_values": [
            6_721_142_749_694_866_469,
            6_838_919_520_062_855_071,
        ],
        "successor_instance_allowed": False,
        "supplier_values_may_be_read_for_exclusion": True,
    }
    assert (
        hashlib.sha256(
            _git_blob(str(negative["source_commit"]), str(negative["repository_path"]))
        ).hexdigest()
        == negative["canonical_sha256"]
    )

    old_result = _mapping(policy["predecessor_result_forbidden"])
    assert old_result["repository_path"].endswith(
        "d7_spectral_moment_confirmation_v0_1/post-d6-descriptive-analysis-result.json"
    )
    assert old_result["canonical_sha256"] == (
        "d0d498b4fb62b38b31de063010516eb17323a4f5b96f44b3ba1f8e7d5680cf4a"
    )
    assert old_result["byte_count"] == 5_293_662
    assert old_result["read_allowed"] is False
    assert old_result["descriptive_input_allowed"] is False
    assert policy["predecessor_value_bearing_code_allowed"] is False
    assert policy["predecessor_value_bearing_code_paths"] == [
        "experiments/qualification/d7_spectral_moment_confirmation_v0_1/post_d6_code/_post_d6_outputs_01_12.py",
        "experiments/qualification/d7_spectral_moment_confirmation_v0_1/post_d6_code/_post_d6_outputs_13_27.py",
        "experiments/qualification/d7_spectral_moment_confirmation_v0_1/post_d6_code/confirmation_post_d6_descriptive.py",
    ]

    reads = _mapping(policy["descriptive_read_policy"])
    assert reads["allowed_binding_roles_exact"] == [
        "historical-post-d6-plan",
        "parent-protocol",
        "parent-result",
        "parent-manifest",
        "parent-consumption",
        "parent-d6-decision",
    ]
    historical_plan = parse_canonical_json(
        _git_blob(HISTORICAL_BINDINGS[0][3], HISTORICAL_BINDINGS[0][1]),
        label="historical post-D6 plan",
    )
    assert isinstance(historical_plan, dict)
    expected_outputs = [
        "post-d6-output-" + str(output)
        for package in _sequence(historical_plan["work_packages"])
        for output in _sequence(_mapping(package)["required_outputs"])
    ]
    assert len(expected_outputs) == 27
    assert reads["required_output_roles_exact"] == expected_outputs
    assert reads["required_output_ids_exact"] == [
        role.removeprefix("post-d6-output-") for role in expected_outputs
    ]
    assert reads["required_output_role_count"] == 27
    result_contract = _mapping(_load_protocol()["postselection_result_contract"])
    assert result_contract["external_output_artifact_bindings_allowed"] is False
    assert result_contract["output_storage_kind"] == (
        "embedded_canonical_subdocuments_keyed_by_bare_output_id"
    )
    assert result_contract["output_subdocument_container_field"] == "/payload/outputs"
    assert result_contract["output_binding_container_field"] == (
        "/payload/output_bindings"
    )
    assert result_contract["output_subdocument_schema_version"] == (
        "spirallens.d7-v1-post-d6-descriptive-output.v0.1"
    )
    verification = _mapping(result_contract["per_output_verification"])
    assert verification["binding_json_pointer_rule"] == (
        "/payload/outputs/{bare_output_id}"
    )
    for key in (
        "binding_byte_count_must_equal_canonical_subdocument_bytes",
        "binding_digest_must_equal_sha256_canonical_subdocument_bytes",
        "binding_target_schema_must_equal_output_schema",
        "output_id_field_must_equal_container_key",
    ):
        assert verification[key] is True
    assert result_contract["status_keyset_contract"] == {
        "complete": "exact_27_output_ids",
        "failed": "subset_of_27_output_ids",
        "insufficient": "exact_27_output_ids",
        "invalid_protocol": "subset_of_27_output_ids",
    }
    for key in (
        "item23_outcome_values_may_select_inputs",
        "negative_seed_inventory_is_descriptive_input",
        "predecessor_result_read_allowed",
        "predecessor_value_bearing_code_read_or_import_allowed",
        "successor_replay_values_read_allowed",
        "successor_seed_values_read_allowed",
    ):
        assert reads[key] is False
    statuses = _mapping(reads["status_conditional_closure"])
    for status in ("complete", "insufficient"):
        assert statuses[status] == {
            "output_role_mode": "exact_keyset",
            "read_role_mode": "exact_full_ordered_list",
        }
    for status in ("failed", "invalid_protocol"):
        assert statuses[status] == {
            "output_role_mode": "allowed_subset_keyset",
            "read_role_mode": "ordered_prefix_only",
        }
    assert statuses["forbidden_input_rules_apply_to_every_status"] is True


def test_external_chronology_attempt_and_receipt_have_one_order() -> None:
    protocol = _load_protocol()
    external = _mapping(protocol["external_durable_chronology_contract"])
    route_external = _mapping(external["route_future_external_coordinates"])
    assert route_external["external_staging_path"] == (
        "/Users/ryohiga/SpiralReality/.spirallens-d7-v1-store.staging"
    )
    assert route_external["external_store_path"] == external["external_store_path"]
    assert external["failure_contract"] == {
        "cleanup_authorized": False,
        "failure_is_nonretryable": True,
        "resume_authorized": False,
        "same_identity_rescue_authorized": False,
    }
    claim = _mapping(external["seed_supply_claim"])
    attempt = _mapping(external["attempt_reservation"])
    store = PurePosixPath(str(external["external_store_path"]))
    assert PurePosixPath(str(claim["external_store_path"])).parent == (
        store / str(route_external["evidence_only_name"])
    )
    assert PurePosixPath(str(attempt["external_store_path"])).parent == (
        store / str(route_external["attempt_evidence_name"])
    )
    assert (
        claim["persistence"]
        == attempt["persistence"]
        == ("durable_exclusive_no_replace")
    )

    reservation = _mapping(protocol["attempt_reservation_contract"])
    assert reservation["execution_started"] is False
    assert reservation["retry_authorized"] is False
    assert reservation["reservation_is_execution_authority"] is False
    assert reservation["sole_later_start_is_continuation_not_rescue"] is True
    assert reservation["planned_next_transition"] == (
        "execution-start-after-conforming-descriptive-result"
    )
    receipt = _mapping(protocol["receipt_contract"])
    assert receipt["required_bindings"] == [
        "replay_target",
        "full_design_freeze",
        "launch_intent",
        "official_execution_attempt_envelope",
        "descriptive_result_namespace_absence",
    ]
    assert receipt["predecessor_file_binding_count"] == 8
    assert receipt["co_published_path_inventory_count"] == 9
    assert receipt["repository_receipt_is_part_of_artifact_only_commit_a"] is True
    assert receipt["descriptive_result_must_follow_committed_receipt"] is True

    chronology = _mapping(protocol["future_chronology"])
    stages = [_mapping(item) for item in _sequence(chronology["stages"])]
    assert [item["sequence"] for item in stages] == list(range(1, 20))
    assert [item["stage_id"] for item in stages] == [
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
    ]
    assert chronology["receipt_only_git_commit_used"] is False
    assert chronology["pre_item23_repository_publication_mode"] == (
        "one_atomic_no_replace_nine_file_set"
    )
    commits = [_mapping(item) for item in _sequence(chronology["git_commit_sequence"])]
    assert [item["commit_role"] for item in commits] == [
        "reviewed-source-commit-s",
        "pre-item23-artifact-only-commit-a",
        "descriptive-result-only-commit-b",
    ]
    assert commits[1]["required_parent_role"] == commits[0]["commit_role"]
    assert commits[2]["required_parent_role"] == commits[1]["commit_role"]
    assert commits[1]["exact_artifact_only"] is True
    assert commits[2]["exact_artifact_only"] is True


def test_future_joined_loader_and_commit_verifier_are_closed_but_absent() -> None:
    protocol = _load_protocol()
    facts = _mapping(protocol["facts_at_protocol_issue"])
    assert facts["authoritative_joined_loader_exists"] is False
    assert facts["post_commit_verifier_exists"] is False
    contract = _mapping(protocol["future_authoritative_verification_contract"])
    assert contract["authoritative_at_protocol_issue"] is False
    joined = _mapping(contract["joined_loader_requirements"])
    assert joined["git_source_tree_reenumeration_against_c1_and_c2_required"] is True
    assert joined["record_byte_cap_contract_reference"] == "record_byte_cap_contract"
    assert joined["validation_order_exact"] == [
        "select_class_cap_from_expected_coordinate_role",
        "enforce_class_byte_cap",
        "verify_expected_sha256",
        "parse_canonical_json",
        "validate_internal_role_schema_and_cross_record_joins",
    ]
    assert joined["v1_internal_artifact_checks"] == [
        "artifact_role_matches_closed_coordinate_role",
        "schema_version_matches_schema_inventory",
        "canonical_bytes_match_persisted_digest_and_byte_count",
    ]
    assert joined["pre_item23_path_digest_join_coordinate_keys"] == (
        PRE_RECEIPT_COORDINATE_KEYS
    )
    assert joined["pre_item23_path_digest_join_count"] == 8
    assert joined[
        "external_durable_repository_projection_byte_equality_coordinate_keys"
    ] == ["exclusive_seed_supply_claim", "official_execution_attempt_envelope"]
    assert joined["supplier_claim_identity_join_required"] is True
    old_seed = _mapping(joined["predecessor_seed_inventory_reauthentication"])
    assert old_seed["binding_reference"] == (
        "historical_input_policy.negative_exclusion_inputs[0]"
    )
    assert old_seed["git_blob_digest_required"] is True
    assert old_seed["canonical_parse_required"] is True

    cross = _mapping(contract["cross_record_join_requirements"])
    assert set(cross) == {
        "attempt_reservation",
        "c1_source_set",
        "c2_source_closure",
        "embedded_full_design",
        "exclusive_seed_claim",
        "full_design_freeze",
        "future_values_embedded_at_protocol_issue",
        "launch_intent",
        "official_seed_inventory",
        "postselection_result",
        "pre_item23_receipt",
        "replay_target",
        "reviewed_source_commit_symbol",
    }
    assert cross["reviewed_source_commit_symbol"] == "S"
    assert cross["future_values_embedded_at_protocol_issue"] is False
    c1 = _mapping(cross["c1_source_set"])
    assert c1["route_binding_must_equal_route_binding"] is True
    assert c1["required_source_paths_and_route_must_be_present"] is True
    assert c1["source_member_tuple_must_equal_live_git_blob_at_s"] is True
    c2 = _mapping(cross["c2_source_closure"])
    assert c2["c1_binding_must_equal_actual_c1_bytes"] is True
    assert c2["derivation_source_members_must_equal_c1_members"] is True
    assert c2["merged_source_commit_must_equal_s"] is True
    claim_join = _mapping(cross["exclusive_seed_claim"])
    assert claim_join["supplier_identity_binding_digest_must_equal_derivation"] is True
    assert claim_join["external_claim_path_must_equal_declared_durable_path"] is True
    seed_join = _mapping(cross["official_seed_inventory"])
    assert seed_join["pinned_predecessor_seed_values"] == [
        6_721_142_749_694_866_469,
        6_838_919_520_062_855_071,
    ]
    assert (
        seed_join["new_seeds_must_be_disjoint_from_pinned_predecessor_values"] is True
    )

    replay = _mapping(cross["replay_target"])
    assert replay["transitive_binding_count"] == 13
    assert replay["transitive_binding_roles_exact"] == {
        "c1_binding": "c1-seed-free-source-set",
        "c2_binding": "c2-source-closure-receipt",
        "embedded_full_design_binding": "embedded-full-design",
        "historical_plan_binding": "historical-post-d6-plan",
        "materialization_protocol_binding": "v1-materialization-protocol",
        "parent_consumption_binding": "parent-consumption",
        "parent_d6_decision_binding": "parent-d6-decision",
        "parent_manifest_binding": "parent-manifest",
        "parent_protocol_binding": "parent-protocol",
        "parent_result_binding": "parent-result",
        "route_binding": "navigation-route",
        "seed_claim_binding": "exclusive-seed-supply-claim",
        "seed_inventory_binding": "official-seed-inventory",
    }
    freeze = _mapping(cross["full_design_freeze"])
    assert freeze["full_design_pointer_value"] == "/full_design"
    assert freeze["full_design_pointer_must_equal_replay_pointer"] is True
    launch = _mapping(cross["launch_intent"])
    assert all(
        launch[key] is True
        for key in (
            "external_staging_path_must_equal_route_coordinate",
            "external_store_path_must_equal_route_coordinate",
            "official_callable_must_equal_route_coordinate",
            "runner_script_must_equal_route_coordinate",
        )
    )
    attempt_join = _mapping(cross["attempt_reservation"])
    assert attempt_join["reviewed_source_commit_must_equal_s"] is True
    assert attempt_join["seed_claim_binding_must_equal_actual_claim_bytes"] is True
    receipt_join = _mapping(cross["pre_item23_receipt"])
    assert receipt_join["predecessor_tuple_count"] == 8
    assert (
        receipt_join[
            "each_predecessor_record_internal_repository_path_must_equal_tuple_path"
        ]
        is True
    )
    assert receipt_join["actual_predecessor_tuple_fields"] == [
        "repository_path",
        "artifact_role",
        "artifact_contract_id",
        "canonical_sha256",
        "byte_count",
    ]
    assert receipt_join["actual_predecessor_tuple_roles_exact"] == SCHEMA_ROLES[:4] + [
        "replay-target",
        "full-design-freeze",
        "launch-intent",
        "official-execution-attempt-reservation",
    ]
    assert receipt_join["absence_observation_source_commit_must_equal_s"] is True
    assert (
        receipt_join[
            "absence_observation_path_must_equal_descriptive_result_coordinate"
        ]
        is True
    )
    frozen_map = _mapping(receipt_join["frozen_nine_role_path_map_exact"])
    assert set(frozen_map) == {
        "c1-seed-free-source-set",
        "c2-source-closure-receipt",
        "exclusive-seed-supply-claim",
        "official-seed-inventory",
        "replay-target",
        "full-design-freeze",
        "launch-intent",
        "official-execution-attempt-reservation",
        "pre-item23-chronology-receipt",
    }
    assert len(set(map(str, frozen_map.values()))) == 9
    result_join = _mapping(cross["postselection_result"])
    assert result_join["attempt_parent_binding_must_equal_actual_attempt_bytes"] is True
    assert (
        result_join["chronology_receipt_binding_must_equal_actual_receipt_bytes"]
        is True
    )
    assert len(_sequence(result_join["read_binding_references_exact"])) == 6
    assert result_join["read_trace_bindings_must_equal_pinned_historical_bytes"] is True

    commit_a = _mapping(contract["post_commit_a_requirements"])
    assert commit_a["artifact_only_delta_coordinate_keys"] == PRE_ITEM23_COORDINATE_KEYS
    assert commit_a["artifact_only_delta_count"] == 9
    assert commit_a["all_pre_item23_paths_have_one_unique_introduction_commit"] is True
    assert commit_a["direct_parent_role"] == "reviewed-source-commit-s"
    assert commit_a["descriptive_result_absent_in_commit_a_tree"] is True
    commit_b = _mapping(contract["post_commit_b_requirements"])
    assert commit_b["exact_delta_coordinate_keys"] == ["descriptive_result"]
    assert commit_b["exact_delta_count"] == 1
    assert commit_b["direct_parent_role"] == "pre-item23-artifact-only-commit-a"
    assert commit_b["all_commit_a_member_bytes_unchanged"] is True
    assert commit_b["descriptive_result_has_one_unique_introduction_commit"] is True


def test_domain_separated_derivations_bind_exact_fields_without_values() -> None:
    derivations = _mapping(_load_protocol()["domain_separated_derivation_contracts"])
    assert derivations["algorithm"] == "sha256_of_spirallens_canonical_json_bytes"
    assert derivations["derived_values_embedded_at_protocol_issue"] is False
    expected = {
        "source_tree": (
            "spirallens.d7-v1-source-tree.v0.1",
            ["domain", "merged_source_commit", "source_members"],
            "source_tree_sha256",
        ),
        "seed_supply_claim_key": (
            "spirallens.d7-v1-exclusive-seed-supply-claim-key.v0.1",
            [
                "c2_sha256",
                "domain",
                "external_claim_path",
                "source_tree_sha256",
                "supplier_id",
                "supplier_identity_sha256",
            ],
            "claim_key_sha256",
        ),
        "official_attempt_key": (
            "spirallens.d7-v1-official-attempt-key.v0.1",
            [
                "domain",
                "external_attempt_path",
                "launch_intent_sha256",
                "replay_target_sha256",
                "reviewed_source_commit",
                "seed_claim_sha256",
            ],
            "attempt_key_sha256",
        ),
    }
    domains: set[str] = set()
    for name, (domain, fields, output) in expected.items():
        item = _mapping(derivations[name])
        assert item["domain"] == domain
        assert item["canonical_object_fields"] == fields
        assert item["future_output_field"] == output
        assert item["future_output_value_embedded"] is False
        domains.add(domain)
    assert len(domains) == 3


def test_parsing_protocol_has_no_materialization_side_effects() -> None:
    protocol = _load_protocol()
    coordinates = _mapping(protocol["coordinate_and_member_layout"])
    external = _mapping(protocol["external_durable_chronology_contract"])
    route_external = _mapping(external["route_future_external_coordinates"])
    watched = [
        *(REPOSITORY / str(coordinates[key]) for key in PRE_ITEM23_COORDINATE_KEYS),
        REPOSITORY / str(coordinates["descriptive_result"]),
        Path(str(route_external["external_store_path"])),
        Path(str(route_external["external_staging_path"])),
        Path(str(_mapping(external["seed_supply_claim"])["external_store_path"])),
        Path(str(_mapping(external["attempt_reservation"])["external_store_path"])),
    ]
    before = {str(path): _path_state(path) for path in watched}
    assert _load_protocol() == protocol
    after = {str(path): _path_state(path) for path in watched}
    assert after == before
    assert hashlib.sha256(ROUTE_PATH.read_bytes()).hexdigest() == ROUTE_SHA256
    assert _git_blob(
        ROUTE_MERGE_COMMIT, ROUTE_PATH.relative_to(REPOSITORY).as_posix()
    ) == (ROUTE_PATH.read_bytes())


def test_living_docs_project_only_the_structural_non_api_boundary() -> None:
    readme = (REPOSITORY / "README.md").read_text(encoding="utf-8")
    roadmap = (REPOSITORY / "docs" / "ROADMAP.md").read_text(encoding="utf-8")
    changelog = (REPOSITORY / "docs" / "SCHEMA_CHANGELOG.md").read_text(
        encoding="utf-8"
    )
    ledger = (REPOSITORY / "docs" / "EXPERIMENT_INTERPRETATION_LEDGER.md").read_text(
        encoding="utf-8"
    )
    api_status = (REPOSITORY / "docs" / "API_STATUS.md").read_text(encoding="utf-8")

    assert "d7_v1_pre_item23_materialization_v0_1.json" in readme
    assert "internal, structural, and unauthenticated" in readme
    assert "not a completed VOY stage" in roadmap
    assert PROTOCOL_SHA256 in changelog
    assert "The protocol remains `frozen_not_run`" in changelog
    assert "### 3.16 D7 v1 pre-item-23 structural contract" in ledger
    assert PROTOCOL_SHA256 in ledger
    assert "record kernel is structural and unauthenticated" in ledger
    assert "d7-v1-pre-item23-materialization-v0-1" not in api_status
    assert "spirallens.d7-v1-pre-item23-materialization-protocol.v0.1" not in api_status
