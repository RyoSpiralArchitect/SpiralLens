from __future__ import annotations

import ast
from collections.abc import Iterator
import copy
from dataclasses import fields
import importlib.util
import inspect
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from types import MappingProxyType, ModuleType

import pytest

import spirallens
import spirallens.qualification as qualification
from spirallens.core.canonical import canonical_json_bytes, sha256_bytes
from spirallens.qualification import confirmation_execution_design as execution_design
from spirallens.qualification import (
    confirmation_v1_deterministic_inputs as deterministic_inputs,
)
from spirallens.qualification import confirmation_v1_records as records
from spirallens.qualification import (
    confirmation_v1_source_closure as source_closure,
)
from spirallens.qualification.common import QualificationContractError


REPOSITORY = Path(__file__).resolve().parents[1]
MODULE_REPOSITORY_PATH = (
    "src/spirallens/qualification/confirmation_v1_deterministic_inputs.py"
)
EXECUTION_DESIGN_REPOSITORY_PATH = (
    "src/spirallens/qualification/confirmation_execution_design.py"
)
PROTOCOL_REPOSITORY_PATH = "protocols/d7_v1_pre_item23_materialization_v0_1.json"
EXPECTED_ROOT_ALL_SHA256 = (
    "a67ce5620fe4a53824cc2b3e0e0b4d46a452298a72fdaa8974ace14e97f13b7c"
)
EXPECTED_QUALIFICATION_ALL_SHA256 = (
    "4dab13d8a847400280682f61fcf0b03fdd9ad51c68d8909ab63a463d07579023"
)
EXPECTED_SEED_SLOTS = (
    "confirmation-seed-slot-00",
    "confirmation-seed-slot-01",
)
EXPECTED_FULL_DESIGN_ROLES = {
    "admission_binding": "family-admission",
    "family_binding": "confirmation-family",
    "graph_case_stress_aggregation_binding": "graph-case-stress-aggregation",
    "inventory_binding": "official-seed-inventory",
    "lifecycle_binding": "lifecycle",
    "protocol_binding": "confirmation-protocol",
    "source_graph_binding": "source-graph",
}
TRUE_AXES = frozenset(
    """structural_only source_closure_rebuilt source_closure_rejoined
    executing_source_members_reauthenticated supplier_role_contract_observed
    seed_slot_contract_observed full_design_field_role_contract_observed""".split()
)
FALSE_AXES = frozenset(
    """source_reviewed source_selected source_closure_established
    source_tree_authenticated runtime_environment_authenticated
    runtime_dependency_closure_verified supplier_selected supplier_fixed
    supplier_identity_authenticated supplier_invoked seed_values_present
    seed_claim_created seed_claim_persisted official_seed_inventory_created
    official_seed_inventory_persisted seed_cardinality_authorized
    seed_slot_assignment_authorized binding_bytes_present
    binding_resolution_completed external_bindings_authenticated
    full_design_created full_design_frozen chronology_orchestrated
    chronology_receipt_created chronology_receipt_persisted
    external_store_observed external_namespace_reserved
    materialization_authorized materialized publication_authorized
    artifacts_published artifact_commit_a_created artifact_commit_a_verified
    result_commit_b_created result_commit_b_verified authority_granted
    official_callable_invoked execution_authorized execution_started
    result_produced scientific_claim_eligible""".split()
)


def _load_source_closure_test_helpers() -> ModuleType:
    name = "_spirallens_pr51_source_closure_test_helpers"
    existing = sys.modules.get(name)
    if existing is not None:
        return existing
    path = REPOSITORY / "tests/test_d7_v1_source_closure_candidate.py"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AssertionError("cannot load D7 v1 source-closure test helpers")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        sys.modules.pop(name, None)
        raise
    return module


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


def _prepared_case(tmp_path: Path) -> object:
    helpers = _load_source_closure_test_helpers()
    case = helpers._case(tmp_path)
    for repository_path, imported_path in (
        (MODULE_REPOSITORY_PATH, deterministic_inputs.__file__),
        (EXECUTION_DESIGN_REPOSITORY_PATH, execution_design.__file__),
    ):
        assert imported_path is not None
        target = case.repository.joinpath(*repository_path.split("/"))
        target.parent.mkdir(parents=True, exist_ok=True)
        target.unlink(missing_ok=True)
        os.link(imported_path, target)
    _run(case.repository, "add", MODULE_REPOSITORY_PATH)
    _run(
        case.repository,
        "commit",
        "--allow-empty",
        "--quiet",
        "-m",
        "test deterministic inputs S",
    )
    case.source_commit = _run(case.repository, "rev-parse", "HEAD")
    assert _git(case.repository, "status", "--porcelain=v1", "-z") == b""
    return case


def _build_source_closure(case: object) -> source_closure.D7V1SourceClosureCandidate:
    return source_closure._build_d7_v1_source_closure_candidate(
        case.context,
        source_commit=case.source_commit,
    )


def _build(
    case: object,
    candidate_source_closure: source_closure.D7V1SourceClosureCandidate,
) -> deterministic_inputs.D7V1DeterministicInputContractCandidate:
    return deterministic_inputs._build_d7_v1_deterministic_input_contract_candidate(
        case.context,
        source_closure=candidate_source_closure,
    )


def test_candidate_is_exact_deterministic_and_non_authorizing(tmp_path: Path) -> None:
    helpers = _load_source_closure_test_helpers()
    case = _prepared_case(tmp_path / "exact")
    before = helpers._official_states(case)
    supplied = _build_source_closure(case)

    first = _build(case, supplied)
    second = _build(case, supplied)

    protocol = json.loads(
        _git(
            case.repository,
            "show",
            f"{case.source_commit}:{PROTOCOL_REPOSITORY_PATH}",
        )
    )
    joins = protocol["future_authoritative_verification_contract"][
        "cross_record_join_requirements"
    ]
    claim = joins["exclusive_seed_claim"]
    joined_roles = joins["embedded_full_design"]["binding_roles_exact"]
    replay_roles = protocol["replay_target_contract"][
        "embedded_full_design_inventory_field_roles"
    ]
    approved = tuple(
        entry
        for entry in protocol["source_contract"][
            "approved_exact_function_runtime_reuse"
        ]
        if entry.get("allowed_symbol")
        == "build_seed_free_d7_confirmation_execution_design"
    )

    assert first.source_commit == case.source_commit
    assert first.source_closure is not supplied
    assert first.source_closure.c1.canonical_bytes == supplied.c1.canonical_bytes
    assert first.source_closure.c2.canonical_bytes == supplied.c2.canonical_bytes
    assert first.source_closure.source_members == supplied.source_members
    assert first.source_closure.c1.canonical_bytes == (
        second.source_closure.c1.canonical_bytes
    )
    assert first.source_closure.c2.canonical_bytes == (
        second.source_closure.c2.canonical_bytes
    )
    assert {
        MODULE_REPOSITORY_PATH,
        EXECUTION_DESIGN_REPOSITORY_PATH,
    } <= {member.repository_path for member in first.source_closure.source_members}

    assert first.supplier_identity_role == claim["supplier_identity_role"]
    assert first.supplier_identity_role == "supplier-identity"
    assert first.required_seed_count == len(EXPECTED_SEED_SLOTS) == 2
    assert first.seed_slot_ids == execution_design.D7_CONFIRMATION_SEED_SLOT_IDS
    assert first.seed_slot_ids == EXPECTED_SEED_SLOTS
    assert joined_roles == replay_roles == records._DESIGN_INVENTORY_ROLES
    assert dict(first.full_design_field_roles) == joined_roles
    assert dict(first.full_design_field_roles) == EXPECTED_FULL_DESIGN_ROLES
    assert type(first.full_design_field_roles) is MappingProxyType
    with pytest.raises(TypeError):
        first.full_design_field_roles["family_binding"] = "caller-role"  # type: ignore[index]

    assert len(approved) == 1
    assert approved[0] == {
        "allowed_symbol": "build_seed_free_d7_confirmation_execution_design",
        "authority_transfer_allowed": False,
        "future_c1_must_bind_transitive_dependency_closure": True,
        "persistence_transfer_allowed": False,
        "repository_path": EXECUTION_DESIGN_REPOSITORY_PATH,
        "reuse_scope": "runtime_function_only",
        "runtime_purpose": "fresh_five_parent_seed_free_scientific_projection_only",
        "schema_transfer_allowed": False,
        "source_commit": "2645ab360598c9ff4f1d9e628b9a9fe1857aedf6",
        "source_sha256": (
            "824553e20b29e74f29959755079d9b0d87b4f244d95d6988a97e94dc52889d13"
        ),
    }

    boolean_axes = {
        name: value
        for name, value in vars(
            deterministic_inputs.D7V1DeterministicInputContractCandidate
        ).items()
        if type(value) is bool
    }
    assert boolean_axes == {
        **{name: True for name in TRUE_AXES},
        **{name: False for name in FALSE_AXES},
    }
    for absent in """supplier_id supplier_identity_binding seed_values seed_claim
        official_seed_inventory bindings full_design chronology_receipt""".split():
        assert not hasattr(first, absent)
    with pytest.raises(QualificationContractError, match="closed builder"):
        deterministic_inputs.D7V1DeterministicInputContractCandidate(
            source_closure=supplied,
            supplier_identity_role="supplier-identity",
            required_seed_count=2,
            seed_slot_ids=EXPECTED_SEED_SLOTS,
            full_design_field_roles=EXPECTED_FULL_DESIGN_ROLES,
        )

    assert _git(case.repository, "status", "--porcelain=v1", "-z") == b""
    assert helpers._official_states(case) == before


def test_private_surface_dependencies_exports_and_docs_retain_the_boundary() -> None:
    assert deterministic_inputs.__all__ == ()
    signature = inspect.signature(
        deterministic_inputs._build_d7_v1_deterministic_input_contract_candidate
    ).parameters
    assert tuple(signature) == ("repository", "source_closure")
    assert signature["repository"].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
    assert signature["source_closure"].kind is inspect.Parameter.KEYWORD_ONLY
    assert tuple(
        field.name
        for field in fields(
            deterministic_inputs.D7V1DeterministicInputContractCandidate
        )
    ) == (
        "source_closure",
        "supplier_identity_role",
        "required_seed_count",
        "seed_slot_ids",
        "full_design_field_roles",
        "_factory_token",
    )
    assert sha256_bytes(canonical_json_bytes(spirallens.__all__)) == (
        EXPECTED_ROOT_ALL_SHA256
    )
    assert sha256_bytes(canonical_json_bytes(qualification.__all__)) == (
        EXPECTED_QUALIFICATION_ALL_SHA256
    )

    tree = ast.parse(
        REPOSITORY.joinpath(*MODULE_REPOSITORY_PATH.split("/")).read_text(
            encoding="utf-8"
        )
    )
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
        """__future__ collections.abc dataclasses types typing spirallens
        spirallens._repository_context spirallens.core.canonical common
        confirmation_execution_design confirmation_v1_materialization
        confirmation_v1_records confirmation_v1_source_closure""".split()
    )
    assert set(
        """open mkdir write_bytes write_text unlink remove rename replace rmtree
        supplier from_pretrained load_model produce_d7_v1_official_result
        _publish_d7_v1_pre_item23_records_no_replace
        _publish_d7_v1_result_no_replace""".split()
    ).isdisjoint(calls)
    assert not hasattr(deterministic_inputs, "publish")
    assert not hasattr(deterministic_inputs, "materialize")

    documents = {
        name: " ".join((REPOSITORY / name).read_text(encoding="utf-8").split())
        for name in (
            "README.md",
            "docs/ROADMAP.md",
            "docs/EXPERIMENT_INTERPRETATION_LEDGER.md",
            "docs/SCHEMA_CHANGELOG.md",
        )
    }
    assert (
        "does not choose a supplier, define supplier identity bytes, authorize the "
        "two-seed cardinality, resolve any of the six non-inventory design bindings"
        in documents["README.md"]
    )
    assert (
        "It returns no supplier identity, binding bytes, seed, claim, inventory, "
        "full design, or chronology." in documents["docs/ROADMAP.md"]
    )
    assert (
        "Required seed count and slot order are observed source facts, not "
        "authorization to persist values."
        in documents["docs/EXPERIMENT_INTERPRETATION_LEDGER.md"]
    )
    assert (
        "Observing count and slot order does not authorize their use in a persisted "
        "record; the six non-inventory binding referents remain unresolved."
        in documents["docs/SCHEMA_CHANGELOG.md"]
    )


def test_rejects_caller_fabrication_wrong_s_and_wrong_c1_c2(tmp_path: Path) -> None:
    helpers = _load_source_closure_test_helpers()
    case = _prepared_case(tmp_path / "fabrication")
    before = helpers._official_states(case)
    genuine = _build_source_closure(case)

    with pytest.raises(TypeError, match="source_closure"):
        deterministic_inputs._build_d7_v1_deterministic_input_contract_candidate(
            case.context,
            source_closure=object(),  # type: ignore[arg-type]
        )

    wrong_s = copy.copy(genuine)
    object.__setattr__(wrong_s, "source_commit", "0" * 40)
    with pytest.raises(QualificationContractError, match="current repository HEAD"):
        _build(case, wrong_s)

    c1_document = genuine.c1.to_dict()
    c1_payload = c1_document["payload"]
    omitted_members = tuple(
        member
        for member in genuine.source_members
        if member.repository_path != MODULE_REPOSITORY_PATH
    )
    forged_c1 = records.D7V1C1SourceSetRecord.create(
        record_id=c1_document["record_id"],
        repository_path=c1_payload["repository_path"],
        route_binding=records.D7V1ArtifactBinding.from_dict(
            c1_payload["route_binding"]
        ),
        source_members=omitted_members,
    )
    c2_document = genuine.c2.to_dict()
    forged_c2 = records.D7V1C2SourceClosureReceipt.create(
        record_id=c2_document["record_id"],
        repository_path=c2_document["payload"]["repository_path"],
        c1=forged_c1,
        source_commit=genuine.source_commit,
    )
    forged = copy.copy(genuine)
    object.__setattr__(forged, "c1", forged_c1)
    object.__setattr__(forged, "c2", forged_c2)
    with pytest.raises(QualificationContractError, match="fresh choice-free rebuild"):
        _build(case, forged)

    assert helpers._official_states(case) == before
    assert _git(case.repository, "status", "--porcelain=v1", "-z") == b""


@pytest.mark.parametrize(
    ("repository_path", "imported_module"),
    (
        (MODULE_REPOSITORY_PATH, deterministic_inputs),
        (EXECUTION_DESIGN_REPOSITORY_PATH, execution_design),
    ),
    ids=("candidate", "approved-design"),
)
def test_rejects_same_bytes_from_an_adjacent_import_origin(
    tmp_path: Path,
    repository_path: str,
    imported_module: ModuleType,
) -> None:
    helpers = _load_source_closure_test_helpers()
    case = _prepared_case(tmp_path / repository_path.rsplit("/", 1)[-1])
    before = helpers._official_states(case)
    supplied = _build_source_closure(case)
    target = case.repository.joinpath(*repository_path.split("/"))
    assert imported_module.__file__ is not None
    imported = Path(imported_module.__file__)
    assert target.samefile(imported)
    source = target.read_bytes()
    target.unlink()
    target.write_bytes(source)
    assert not target.samefile(imported)
    assert _git(case.repository, "status", "--porcelain=v1", "-z") == b""

    with pytest.raises(QualificationContractError, match="import origin"):
        _build(case, supplied)
    assert helpers._official_states(case) == before


@pytest.mark.parametrize("drift", ("executing-source", "protocol"))
def test_rejects_source_or_protocol_drift(tmp_path: Path, drift: str) -> None:
    helpers = _load_source_closure_test_helpers()
    case = _prepared_case(tmp_path / drift)
    before = helpers._official_states(case)
    supplied = _build_source_closure(case)

    if drift == "executing-source":
        target = case.repository.joinpath(*MODULE_REPOSITORY_PATH.split("/"))
        source = target.read_bytes()
        target.unlink()
        target.write_bytes(source + b"\n# live source drift\n")
        with pytest.raises(
            QualificationContractError, match="differs from Git S or C1"
        ):
            deterministic_inputs._require_exact_source_member(
                case.context,
                supplied,
                MODULE_REPOSITORY_PATH,
            )
    else:
        target = case.repository.joinpath(*PROTOCOL_REPOSITORY_PATH.split("/"))
        target.write_bytes(target.read_bytes() + b"\n")
        _run(case.repository, "add", PROTOCOL_REPOSITORY_PATH)
        _run(case.repository, "commit", "--quiet", "-m", "protocol drift")
        with pytest.raises(QualificationContractError, match="current repository HEAD"):
            _build(case, supplied)

    assert helpers._official_states(case) == before
