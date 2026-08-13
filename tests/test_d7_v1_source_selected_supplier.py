from __future__ import annotations

import ast
import builtins
from collections.abc import Iterator, Mapping
from dataclasses import fields
import importlib.util
import inspect
import json
from pathlib import Path
import shutil
import subprocess
import sys
from types import FunctionType, ModuleType

import pytest

import spirallens
import spirallens.qualification as qualification
from spirallens.core.canonical import canonical_json_bytes, sha256_bytes
from spirallens.qualification import confirmation_v1_materialization as materialization
from spirallens.qualification import confirmation_v1_records as records
from spirallens.qualification import (
    confirmation_v1_source_selected_supplier as selected_supplier,
)
from spirallens.qualification.common import QualificationContractError


REPOSITORY = Path(__file__).resolve().parents[1]
SOURCE_S = "a9b9da21954478e42982e27f9e6b02cbeba5a08d"
MODULE_REPOSITORY_PATH = (
    "src/spirallens/qualification/confirmation_v1_source_selected_supplier.py"
)
DESIGN_REPOSITORY_PATH = "src/spirallens/qualification/confirmation_execution_design.py"
DETERMINISTIC_INPUTS_REPOSITORY_PATH = (
    "src/spirallens/qualification/confirmation_v1_deterministic_inputs.py"
)
PROTOCOL_REPOSITORY_PATH = "protocols/d7_v1_pre_item23_materialization_v0_1.json"
ROUTE_REPOSITORY_PATH = "protocols/voy_v1_v9_strict_successor_route_v0_1.json"
IDENTITY_SCHEMA = "spirallens.d7-v1-source-selected-seed-supplier-identity.v0.1"
IDENTITY_CONTRACT_ID = "d7-v1-source-selected-seed-supplier-identity-v0-1"
REGISTRY_SCHEMA = "spirallens.d7-v1-combined-seed-exclusion-registry.v0.1"
REGISTRY_CONTRACT_ID = "d7-v1-combined-seed-exclusion-registry-v0-1"
EXCLUDED_VALUES = (
    11,
    12,
    9001,
    9002,
    1_111_097_936_516_803_550,
    6_721_142_749_694_866_469,
    6_819_071_872_908_675_098,
    6_838_919_520_062_855_071,
)
TRUE_AXES = frozenset(
    """structural_only source_join_reverified
    executing_source_members_reauthenticated
    deterministic_input_declarations_rederived supplier_source_selected
    supplier_function_fixed supplier_identity_derived
    supplier_identity_bytes_present exclusion_registry_derived
    seed_cardinality_policy_fixed seed_slot_policy_fixed
    full_exclusion_policy_closed""".split()
)
FALSE_AXES = frozenset(
    """source_reviewed source_selected source_closure_established
    source_tree_authenticated runtime_environment_authenticated
    runtime_dependency_closure_verified supplier_identity_authenticated
    supplier_invoked supplier_invocation_authorized cryptographic_unseen_proof
    seed_values_generated seed_values_present seed_cardinality_authorized
    seed_slot_assignment_authorized seed_claim_created seed_claim_persisted
    supplier_identity_persisted exclusion_registry_persisted
    official_seed_inventory_created official_seed_inventory_persisted
    six_full_design_bindings_resolved external_bindings_authenticated
    full_design_created full_design_frozen chronology_orchestrated
    chronology_receipt_created chronology_receipt_persisted
    external_store_observed external_namespace_reserved
    materialization_authorized materialized publication_authorized
    artifacts_published artifact_commit_a_created artifact_commit_a_verified
    result_commit_b_created result_commit_b_verified authority_granted
    official_callable_invoked execution_authorized execution_started
    result_produced scientific_claim_eligible""".split()
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


def _deterministic_helpers() -> ModuleType:
    return _load_test_module(
        "_spirallens_pr53_deterministic_test_helpers",
        "tests/test_d7_v1_deterministic_inputs.py",
    )


def _materialization_helpers() -> ModuleType:
    deterministic = _deterministic_helpers()
    source_closure = deterministic._load_source_closure_test_helpers()
    return source_closure._load_materialization_test_helpers()


@pytest.fixture(autouse=True)
def _remove_test_repository_hardlinks(tmp_path: Path) -> Iterator[None]:
    def restore_authenticated_referent_documents_origin() -> None:
        loaded = sys.modules.get(
            "spirallens.qualification.confirmation_v1_design_referent_documents"
        )
        referents = sys.modules.get(
            "spirallens.qualification.confirmation_v1_full_design_referents"
        )
        authenticated = getattr(
            referents,
            "_AUTHENTICATED_REFERENT_DOCUMENTS_MODULE",
            None,
        )
        if loaded is not None and loaded is authenticated:
            workspace_leaf = REPOSITORY / (
                "src/spirallens/qualification/"
                "confirmation_v1_design_referent_documents.py"
            )
            loaded.__file__ = str(workspace_leaf)
            if loaded.__spec__ is not None:
                loaded.__spec__.origin = str(workspace_leaf)

    restore_authenticated_referent_documents_origin()
    try:
        yield
    finally:
        restore_authenticated_referent_documents_origin()
        shutil.rmtree(tmp_path, ignore_errors=True)


def _git(repository: Path, *arguments: str) -> bytes:
    return subprocess.run(
        ("git", "-C", str(repository), *arguments),
        check=True,
        capture_output=True,
    ).stdout


def _show(repository: Path, commit: str, repository_path: str) -> bytes:
    return _git(repository, "show", f"{commit}:{repository_path}")


def _prepared(tmp_path: Path) -> tuple[object, object]:
    helpers = _deterministic_helpers()
    case = helpers._prepared_case(tmp_path)
    closure = helpers._build_source_closure(case)
    return case, helpers._build(case, closure)


def _binding(
    role: str,
    contract: str,
    source: bytes,
) -> records.D7V1ArtifactBinding:
    return records.D7V1ArtifactBinding(
        artifact_role=role,
        artifact_contract_id=contract,
        canonical_sha256=sha256_bytes(source),
        byte_count=len(source),
    )


def _canonical_document(source: bytes) -> dict[str, object]:
    value = json.loads(source)
    assert type(value) is dict
    assert canonical_json_bytes(value) == source
    return value


def _historical_source(
    case: object,
    entry: Mapping[str, object],
) -> tuple[bytes, dict[str, object]]:
    source = _show(
        case.repository,
        str(entry["source_commit"]),
        str(entry["repository_path"]),
    )
    assert len(source) == entry["byte_count"]
    assert sha256_bytes(source) == entry["canonical_sha256"]
    document = _canonical_document(source)
    assert document["schema_version"] == entry["artifact_contract_id"]
    return source, document


def _literal_assignment(source: bytes, name: str) -> object:
    tree = ast.parse(source)
    matches = [
        node.value
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id == name
            for target in node.targets
        )
    ]
    assert len(matches) == 1
    return ast.literal_eval(matches[0])


def _independent_oracle(
    case: object,
    deterministic: object,
) -> dict[str, object]:
    protocol_source = _show(
        case.repository,
        case.source_commit,
        PROTOCOL_REPOSITORY_PATH,
    )
    protocol = _canonical_document(protocol_source)
    policy = protocol["historical_input_policy"]
    assert isinstance(policy, dict)

    negative_entries = policy["negative_exclusion_inputs"]
    assert isinstance(negative_entries, list) and len(negative_entries) == 1
    negative = negative_entries[0]
    assert isinstance(negative, dict)
    _negative_source, predecessor_document = _historical_source(case, negative)
    predecessor_values = tuple(
        int(item["seed"]) for item in predecessor_document["seeds"]
    )
    assert predecessor_values == tuple(negative["pinned_predecessor_seed_values"])
    predecessor_binding = records.D7V1ArtifactBinding(
        artifact_role=str(negative["artifact_binding_role"]),
        artifact_contract_id=str(negative["artifact_contract_id"]),
        canonical_sha256=str(negative["canonical_sha256"]),
        byte_count=int(negative["byte_count"]),
    )

    parents = policy["permitted_historical_scientific_parents"]
    assert isinstance(parents, list)
    parent_entry = tuple(
        item
        for item in parents
        if isinstance(item, dict)
        and item.get("artifact_binding_role") == "parent-protocol"
    )
    assert len(parent_entry) == 1
    _parent_source, parent_document = _historical_source(case, parent_entry[0])
    selection = parent_document["selection"]
    assert isinstance(selection, dict) and set(selection) == {
        "controls",
        "seeds",
        "stress_axes",
    }
    parent_values = tuple(int(value) for value in selection["seeds"])
    parent_binding = records.D7V1ArtifactBinding(
        artifact_role="parent-protocol",
        artifact_contract_id=str(parent_entry[0]["artifact_contract_id"]),
        canonical_sha256=str(parent_entry[0]["canonical_sha256"]),
        byte_count=int(parent_entry[0]["byte_count"]),
    )

    design_source = _show(case.repository, case.source_commit, DESIGN_REPOSITORY_PATH)
    development_entries = _literal_assignment(
        design_source,
        "_DEVELOPMENT_SEED_EXCLUSION_ENTRIES",
    )
    assert isinstance(development_entries, tuple)
    development_values = tuple(int(seed) for seed, _reason in development_entries)
    development_registry = canonical_json_bytes(
        {
            "schema_version": "spirallens.d7-development-seed-exclusion.v0.1",
            "entries": [
                {"seed": seed, "reason": reason} for seed, reason in development_entries
            ],
        }
    )
    assert sha256_bytes(development_registry) == (
        "20803b40c5fc6903e1d1a64ae41c0eb3dcbb3c4a859d7a482971088346fcb54a"
    )
    excluded = tuple(sorted((*predecessor_values, *parent_values, *development_values)))
    assert excluded == EXCLUDED_VALUES
    assert len(set(excluded)) == 8

    members = {
        member.repository_path: member
        for member in deterministic.source_closure.source_members
    }
    supplier_member = members[MODULE_REPOSITORY_PATH]
    design_member = members[DESIGN_REPOSITORY_PATH]
    route = protocol["route_binding"]
    assert isinstance(route, dict)
    route_source = _show(
        case.repository,
        str(route["merge_commit"]),
        str(route["repository_path"]),
    )
    route_document = _canonical_document(route_source)
    c1_binding = records.D7V1ArtifactBinding.from_record(
        deterministic.source_closure.c1
    )
    c2_binding = records.D7V1ArtifactBinding.from_record(
        deterministic.source_closure.c2
    )
    protocol_binding = _binding(
        "v1-materialization-protocol",
        str(protocol["schema_version"]),
        protocol_source,
    )
    route_binding = _binding(
        "navigation-route",
        str(route_document["schema_version"]),
        route_source,
    )

    registry_document = {
        "schema_version": REGISTRY_SCHEMA,
        "contract_id": REGISTRY_CONTRACT_ID,
        "artifact_role": "seed-exclusion-registry",
        "successor_lineage_id": "d7-spectral-moment-confirmation-v1",
        "source_commit": case.source_commit,
        "predecessor_inventory": {
            "binding": predecessor_binding.to_dict(),
            "seed_values": list(predecessor_values),
        },
        "parent_selection": {
            "binding": parent_binding.to_dict(),
            "seed_values": list(parent_values),
        },
        "development": {
            "approved_design_source_member": design_member.to_dict(),
            "source_registry_schema": ("spirallens.d7-development-seed-exclusion.v0.1"),
            "source_registry_sha256": sha256_bytes(development_registry),
            "entries": [
                {"seed": seed, "reason": reason} for seed, reason in development_entries
            ],
        },
        "combined_seed_values": list(excluded),
        "policy": {
            "categories_pairwise_disjoint": True,
            "combined_values_sorted_unique": True,
            "successor_values_must_exclude_all_combined_values": True,
            "registry_persisted": False,
            "registry_is_execution_authority": False,
        },
    }
    registry_source = canonical_json_bytes(registry_document)
    registry_binding = _binding(
        "seed-exclusion-registry",
        REGISTRY_SCHEMA,
        registry_source,
    )
    callable_contract = {
        "function_type": "types.FunctionType",
        "module": selected_supplier.__name__,
        "qualname": "_supply_d7_v1_official_seed_values",
        "module_global_fixed": True,
        "positional_parameter_count": 0,
        "positional_only_parameter_count": 0,
        "keyword_only_parameter_count": 0,
        "varargs_present": False,
        "varkw_present": False,
        "defaults_present": False,
        "keyword_defaults_present": False,
        "closure_present": False,
    }
    identity_core = {
        "successor_lineage_id": "d7-spectral-moment-confirmation-v1",
        "source_commit": case.source_commit,
        "c1_binding": c1_binding.to_dict(),
        "c2_binding": c2_binding.to_dict(),
        "materialization_protocol_binding": protocol_binding.to_dict(),
        "route_binding": route_binding.to_dict(),
        "supplier_source_member": supplier_member.to_dict(),
        "approved_design_source_member": design_member.to_dict(),
        "exclusion_registry_binding": registry_binding.to_dict(),
        "callable_contract": callable_contract,
        "entropy_contract": {
            "source_declared_api": "secrets.randbits",
            "bit_count_per_draw": 63,
            "operating_system_csprng_required": True,
            "maximum_draw_count": 256,
            "live_entropy_callable_authenticated": False,
        },
        "output_contract": {
            "container": "tuple",
            "required_seed_count": 2,
            "values_nonnegative_signed_int64": True,
            "values_unique": True,
            "values_canonically_sorted_ascending": True,
            "ordinal_slot_assignments": [
                {"ordinal": 0, "seed_slot_id": "confirmation-seed-slot-00"},
                {"ordinal": 1, "seed_slot_id": "confirmation-seed-slot-01"},
            ],
            "combined_exclusion_registry_required": True,
        },
    }
    supplier_id = (
        "d7-v1-source-selected-os-csprng-"
        f"{sha256_bytes(canonical_json_bytes(identity_core))[:24]}"
    )
    identity_source = canonical_json_bytes(
        {
            "schema_version": IDENTITY_SCHEMA,
            "contract_id": IDENTITY_CONTRACT_ID,
            "artifact_role": "supplier-identity",
            "supplier_id": supplier_id,
            "identity_core": identity_core,
            "observations": {
                "supplier_invoked": False,
                "seed_values_present": False,
                "cryptographic_unseen_proof": False,
                "runtime_environment_authenticated": False,
                "identity_authenticated": False,
            },
            "authority": {
                "supplier_invocation_authorized": False,
                "seed_claim_authorized": False,
                "materialization_authorized": False,
                "execution_authorized": False,
                "scientific_claim_eligible": False,
            },
        }
    )
    return {
        "c1_binding": c1_binding,
        "c2_binding": c2_binding,
        "excluded": excluded,
        "registry_source": registry_source,
        "registry_binding": registry_binding,
        "supplier_id": supplier_id,
        "identity_source": identity_source,
        "identity_binding": _binding(
            "supplier-identity",
            IDENTITY_SCHEMA,
            identity_source,
        ),
    }


def _actual_official_states(case: object) -> dict[Path, tuple[object, ...]]:
    helpers = _materialization_helpers()
    paths = {
        REPOSITORY.joinpath(*path.split("/"))
        for path in helpers._coordinate_paths(case.protocol).values()
    }
    layout = case.protocol["coordinate_and_member_layout"]
    paths.add(REPOSITORY.joinpath(*str(layout["descriptive_result"]).split("/")))
    external = case.protocol["external_durable_chronology_contract"]
    route = external["route_future_external_coordinates"]
    paths.update(
        {
            Path(str(route["external_staging_path"])),
            Path(str(route["external_store_path"])),
        }
    )

    def path_state(path: Path) -> tuple[object, ...]:
        try:
            observed = path.lstat()
        except FileNotFoundError:
            return ("absent",)
        return (
            "present",
            observed.st_dev,
            observed.st_ino,
            observed.st_mode,
            observed.st_size,
            observed.st_mtime_ns,
        )

    return {path: path_state(path) for path in paths}


def test_clean_s_candidate_is_exact_uninvoked_and_non_authorizing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case, deterministic = _prepared(tmp_path / "exact")
    before = _actual_official_states(case)
    entropy_calls = 0

    def forbidden_entropy(_bits: int) -> int:
        nonlocal entropy_calls
        entropy_calls += 1
        raise AssertionError("supplier entropy must not be accessed")

    monkeypatch.setattr(selected_supplier.secrets, "randbits", forbidden_entropy)
    first = selected_supplier._build_d7_v1_source_selected_seed_supplier_candidate(
        case.context,
        deterministic_inputs=deterministic,
    )
    second = selected_supplier._build_d7_v1_source_selected_seed_supplier_candidate(
        case.context,
        deterministic_inputs=deterministic,
    )
    expected = _independent_oracle(case, deterministic)

    assert entropy_calls == 0
    assert first.source_commit == case.source_commit
    assert first.c1_binding == expected["c1_binding"]
    assert first.c2_binding == expected["c2_binding"]
    assert first.seed_slot_ids == (
        "confirmation-seed-slot-00",
        "confirmation-seed-slot-01",
    )
    assert first.required_seed_count == 2
    assert first.excluded_seed_values == expected["excluded"] == EXCLUDED_VALUES
    assert first.exclusion_registry_source == expected["registry_source"]
    assert first.exclusion_registry_binding == expected["registry_binding"]
    assert first.supplier_id == expected["supplier_id"]
    assert first.supplier_identity_source == expected["identity_source"]
    assert first.supplier_identity_binding == expected["identity_binding"]
    assert first.supplier_identity_source == second.supplier_identity_source
    assert first.exclusion_registry_source == second.exclusion_registry_source
    assert _canonical_document(first.supplier_identity_source)["supplier_id"] == (
        first.supplier_id
    )

    boolean_axes = {
        name: value
        for name, value in vars(
            selected_supplier.D7V1SourceSelectedSeedSupplierCandidate
        ).items()
        if type(value) is bool
    }
    assert boolean_axes == {
        **{name: True for name in TRUE_AXES},
        **{name: False for name in FALSE_AXES},
    }
    for absent in """family_binding admission_binding protocol_binding
        source_graph_binding graph_case_stress_aggregation_binding
        lifecycle_binding seed_values seed_claim official_seed_inventory""".split():
        assert not hasattr(first, absent)

    alternate = _canonical_document(first.supplier_identity_source)
    alternate["supplier_id"] = "caller-self-consistent-supplier"
    alternate_source = canonical_json_bytes(alternate)
    with pytest.raises(QualificationContractError, match="factory-produced"):
        selected_supplier.D7V1SourceSelectedSeedSupplierCandidate(
            source_commit=first.source_commit,
            c1_binding=first.c1_binding,
            c2_binding=first.c2_binding,
            seed_slot_ids=first.seed_slot_ids,
            supplier_id="caller-self-consistent-supplier",
            supplier_identity_source=alternate_source,
            supplier_identity_binding=_binding(
                "supplier-identity",
                IDENTITY_SCHEMA,
                alternate_source,
            ),
            exclusion_registry_source=first.exclusion_registry_source,
            exclusion_registry_binding=first.exclusion_registry_binding,
            excluded_seed_values=first.excluded_seed_values,
        )
    assert _git(case.repository, "status", "--porcelain=v1", "-z") == b""
    assert _actual_official_states(case) == before


def test_commit_a_and_b_verifiers_rederive_without_supplier_entry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    helpers = _materialization_helpers()
    case = helpers._build_case(tmp_path / "commit-verifiers")
    before = _actual_official_states(case)
    entropy_calls = 0

    def forbidden_entropy(_bits: int) -> int:
        nonlocal entropy_calls
        entropy_calls += 1
        raise AssertionError("joined verification must not enter the supplier")

    monkeypatch.setattr(selected_supplier.secrets, "randbits", forbidden_entropy)
    assert isinstance(helpers._load_stage(case), materialization.D7V1JoinedRecords)
    commit_a = helpers._commit_a(case)
    assert helpers._verify_commit_a(case, commit_a).artifact_commit == commit_a
    commit_b = helpers._commit_b(case, exact_result=True)
    assert helpers._verify_commit_b(case, commit_a, commit_b).result_commit == commit_b
    assert entropy_calls == 0
    assert _actual_official_states(case) == before


def test_callable_monkeypatch_is_rejected_without_entry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case, deterministic = _prepared(tmp_path / "callable")
    called = False

    def replacement() -> tuple[int, int]:
        nonlocal called
        called = True
        return 101, 202

    replacement.__module__ = selected_supplier.__name__
    replacement.__qualname__ = "_supply_d7_v1_official_seed_values"
    monkeypatch.setattr(
        selected_supplier,
        "_supply_d7_v1_official_seed_values",
        replacement,
    )
    with pytest.raises(QualificationContractError, match="supplier identity differs"):
        selected_supplier._build_d7_v1_source_selected_seed_supplier_candidate(
            case.context,
            deterministic_inputs=deterministic,
        )
    assert called is False


def test_wrong_origin_s_c1_or_live_source_cannot_be_laundered(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    origin_case, origin_inputs = _prepared(tmp_path / "origin")
    origin_target = origin_case.repository.joinpath(*MODULE_REPOSITORY_PATH.split("/"))
    imported = Path(selected_supplier.__file__)
    assert origin_target.samefile(imported)
    source = origin_target.read_bytes()
    origin_target.unlink()
    origin_target.write_bytes(source)
    assert _git(origin_case.repository, "status", "--porcelain=v1", "-z") == b""
    with pytest.raises(QualificationContractError, match="import origin"):
        selected_supplier._build_d7_v1_source_selected_seed_supplier_candidate(
            origin_case.context,
            deterministic_inputs=origin_inputs,
        )

    case, deterministic = _prepared(tmp_path / "source-chain")
    protocol = materialization._protocol_at_commit(case.context, case.source_commit)
    c1 = deterministic.source_closure.c1
    c2 = deterministic.source_closure.c2
    with pytest.raises(QualificationContractError):
        selected_supplier._derive_d7_v1_source_selected_seed_supplier_candidate(
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
            member
            for member in deterministic.source_closure.source_members
            if member.repository_path != MODULE_REPOSITORY_PATH
        ),
    )
    c2_document = c2.to_dict()
    forged_c2 = records.D7V1C2SourceClosureReceipt.create(
        record_id=str(c2_document["record_id"]),
        repository_path=str(c2_document["payload"]["repository_path"]),
        c1=forged_c1,
        source_commit=case.source_commit,
    )
    with pytest.raises(QualificationContractError):
        selected_supplier._derive_d7_v1_source_selected_seed_supplier_candidate(
            case.context,
            protocol=protocol,
            source_commit=case.source_commit,
            c1=forged_c1,
            c2=forged_c2,
        )

    expected = _independent_oracle(case, deterministic)
    adjacent = case.repository.joinpath(
        *DETERMINISTIC_INPUTS_REPOSITORY_PATH.split("/")
    )
    adjacent_source = adjacent.read_bytes()
    adjacent.unlink()
    adjacent.write_bytes(adjacent_source + b"\n# adjacent PR51 live drift\n")
    assert DETERMINISTIC_INPUTS_REPOSITORY_PATH.encode() in _git(
        case.repository,
        "status",
        "--porcelain=v1",
        "-z",
    )
    real_import = builtins.__import__

    def import_without_clean_convenience_dependencies(
        name: str,
        globals: object = None,
        locals: object = None,
        fromlist: tuple[str, ...] = (),
        level: int = 0,
    ) -> object:
        forbidden = {
            "confirmation_v1_deterministic_inputs",
            "confirmation_v1_source_closure",
        }
        if name in {
            f"spirallens.qualification.{item}" for item in forbidden
        } or forbidden.intersection(fromlist):
            raise AssertionError(
                "pure supplier derivation imported a clean-only dependency"
            )
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(
        builtins,
        "__import__",
        import_without_clean_convenience_dependencies,
    )
    pure = selected_supplier._derive_d7_v1_source_selected_seed_supplier_candidate(
        case.context,
        protocol=protocol,
        source_commit=case.source_commit,
        c1=c1,
        c2=c2,
    )
    assert pure.supplier_identity_source == expected["identity_source"]
    assert pure.exclusion_registry_source == expected["registry_source"]

    target = case.repository.joinpath(*MODULE_REPOSITORY_PATH.split("/"))
    source = target.read_bytes()
    target.unlink()
    target.write_bytes(source + b"\n# live drift\n")
    with pytest.raises(QualificationContractError, match="differs from Git S or C1"):
        selected_supplier._require_exact_source_member(
            case.context,
            source_commit=case.source_commit,
            c1=c1,
            repository_path=MODULE_REPOSITORY_PATH,
        )


@pytest.mark.parametrize("tamper", ("binding", "supplier-id"))
def test_joined_verifier_rejects_source_selected_identity_tamper(
    tmp_path: Path,
    tamper: str,
) -> None:
    helpers = _materialization_helpers()
    options: dict[str, object] = {}
    if tamper == "binding":
        options["supplier_identity_override"] = records.D7V1ArtifactBinding(
            artifact_role="supplier-identity",
            artifact_contract_id=IDENTITY_SCHEMA,
            canonical_sha256="f" * 64,
            byte_count=1,
        )
    else:
        options["supplier_id_override"] = "caller-self-consistent-csprng"
    case = helpers._build_case(tmp_path / tamper, **options)
    with pytest.raises(QualificationContractError, match="source-selected supplier"):
        helpers._load_stage(case)


@pytest.mark.parametrize(
    ("label", "seed_values"),
    (
        ("one", (8_100_001,)),
        ("three", (8_100_001, 8_100_002, 8_100_003)),
        ("descending", (8_100_002, 8_100_001)),
        ("duplicate", (8_100_001, 8_100_001)),
        ("development", (11, 8_100_001)),
        ("parent", (8_100_001, 1_111_097_936_516_803_550)),
        ("predecessor", (8_100_001, 6_721_142_749_694_866_469)),
    ),
)
def test_seed_count_order_uniqueness_and_full_exclusion_are_closed(
    tmp_path: Path,
    label: str,
    seed_values: tuple[int, ...],
) -> None:
    helpers = _materialization_helpers()
    with pytest.raises(QualificationContractError):
        case = helpers._build_case(
            tmp_path / label,
            seed_values=seed_values,
        )
        helpers._load_stage(case)


def test_private_surface_keeps_protocol_schema_route_dependencies_and_api() -> None:
    assert selected_supplier.__all__ == ()
    assert materialization.__all__ == ()
    signature = inspect.signature(
        selected_supplier._build_d7_v1_source_selected_seed_supplier_candidate
    ).parameters
    assert tuple(signature) == ("repository", "deterministic_inputs")
    assert signature["repository"].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
    assert signature["deterministic_inputs"].kind is inspect.Parameter.KEYWORD_ONLY
    assert tuple(
        field.name
        for field in fields(selected_supplier.D7V1SourceSelectedSeedSupplierCandidate)
    ) == (
        "source_commit",
        "c1_binding",
        "c2_binding",
        "seed_slot_ids",
        "supplier_id",
        "supplier_identity_source",
        "supplier_identity_binding",
        "exclusion_registry_source",
        "exclusion_registry_binding",
        "excluded_seed_values",
        "_factory_token",
    )
    assert sha256_bytes(canonical_json_bytes(spirallens.__all__)) == (
        "a67ce5620fe4a53824cc2b3e0e0b4d46a452298a72fdaa8974ace14e97f13b7c"
    )
    assert sha256_bytes(canonical_json_bytes(qualification.__all__)) == (
        "4dab13d8a847400280682f61fcf0b03fdd9ad51c68d8909ab63a463d07579023"
    )
    for repository_path, (byte_count, digest) in EXPECTED_STATIC_FILES.items():
        source = (
            _show(REPOSITORY, SOURCE_S, repository_path)
            if repository_path == "pyproject.toml"
            else REPOSITORY.joinpath(*repository_path.split("/")).read_bytes()
        )
        assert len(source) == byte_count
        assert sha256_bytes(source) == digest

    source = REPOSITORY.joinpath(*MODULE_REPOSITORY_PATH.split("/")).read_text(
        encoding="utf-8"
    )
    tree = ast.parse(source)
    imported: set[str] = set()
    calls: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imported.add(node.module)
            elif node.level:
                imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                calls.add(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                calls.add(node.func.attr)
    assert imported == set(
        """__future__ dataclasses inspect secrets types typing spirallens
        spirallens._repository_context spirallens.core.canonical common
        confirmation_execution_design confirmation_v1_deterministic_inputs
        confirmation_v1_materialization confirmation_v1_records
        confirmation_v1_source_closure""".split()
    )
    top_level_relative_imports = {
        alias.name
        for node in tree.body
        if isinstance(node, ast.ImportFrom) and node.level
        for alias in node.names
    }
    assert {
        "confirmation_v1_deterministic_inputs",
        "confirmation_v1_source_closure",
    }.isdisjoint(top_level_relative_imports)
    assert set(
        """open mkdir write_bytes write_text unlink remove rename replace rmtree
        from_pretrained load_model produce_d7_v1_official_result
        _publish_d7_v1_pre_item23_records_no_replace
        _publish_d7_v1_result_no_replace""".split()
    ).isdisjoint(calls)
    supplier_functions = tuple(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name == "_supply_d7_v1_official_seed_values"
    )
    assert len(supplier_functions) == 1
    assert (
        sum(
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "randbits"
            for node in ast.walk(tree)
        )
        == 1
    )
    assert any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "randbits"
        for node in ast.walk(supplier_functions[0])
    )
    fixed = selected_supplier._supply_d7_v1_official_seed_values
    assert type(fixed) is FunctionType
    assert inspect.signature(fixed).parameters == {}
    assert not hasattr(selected_supplier, "publish")
    assert not hasattr(selected_supplier, "materialize")
