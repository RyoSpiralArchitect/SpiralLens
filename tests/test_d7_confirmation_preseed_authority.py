from __future__ import annotations

import copy
import inspect
import pickle
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest

from spirallens import qualification
from spirallens.core.canonical import canonical_json_bytes, parse_canonical_json
from spirallens.qualification import confirmation_preseed_authority as preseed
from spirallens.qualification.common import QualificationContractError

REPOSITORY = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class _RepositoryLineage:
    root: Path
    pr26_commit: str
    source_commit: str


@dataclass(frozen=True)
class _PositiveChain:
    root: Path
    pr26_commit: str
    source_commit: str
    receipt_commit: str
    readiness_commit: str
    admission_commit: str
    receipt_source: bytes
    readiness_source: bytes
    admission_source: bytes


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


def _commit(root: Path, message: str, *repository_paths: str) -> str:
    _git(root, "add", *repository_paths)
    _git(root, "commit", "-q", "-m", message)
    return _git(root, "rev-parse", "HEAD")


def _write(root: Path, repository_path: str, source: bytes) -> None:
    destination = root / repository_path
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(source)


def _document(root: Path, repository_path: str) -> dict[str, object]:
    value = parse_canonical_json(
        (root / repository_path).read_bytes(),
        label=repository_path,
    )
    assert type(value) is dict
    return value


def _new_repository(tmp_path: Path) -> _RepositoryLineage:
    root = tmp_path / "repository"
    root.mkdir(parents=True)
    root = root.resolve()
    _git(root, "init", "-q")
    _configure_git(root)

    item21 = root / preseed.D7_ITEM21_DIRECTORY
    item21.mkdir(parents=True)
    (item21 / ".gitkeep").write_text("item-21 directory\n", encoding="utf-8")
    for recorded_path in (
        preseed.c1.D7_C1_BUNDLE_REPOSITORY_PATH,
        preseed.c1.D7_C2_RECEIPT_REPOSITORY_PATH,
    ):
        _write(root, recorded_path, (REPOSITORY / recorded_path).read_bytes())
    (root / ".pr26-anchor").write_text("runtime closure\n", encoding="utf-8")
    pr26_commit = _commit(root, "synthetic PR26", ".")

    package = root / "src" / "spirallens"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text(
        '"""Synthetic source surface for item-21 tests."""\n',
        encoding="utf-8",
    )
    generator_source = root / preseed.spectral_generator.SPECTRAL_MOMENT_SOURCE_PATH
    generator_source.parent.mkdir(parents=True, exist_ok=True)
    generator_source.write_bytes(
        (
            REPOSITORY / preseed.spectral_generator.SPECTRAL_MOMENT_SOURCE_PATH
        ).read_bytes()
    )
    (root / "pyproject.toml").write_text(
        '[project]\nname = "spirallens-item21-test"\nversion = "0.0.0"\n',
        encoding="utf-8",
    )
    (root / preseed.fused_start.D7_RUNTIME_LOCK_REPOSITORY_PATH).write_text(
        "synthetic-runtime==1.0\n",
        encoding="utf-8",
    )
    for repository_path in preseed.fused_start._REPOSITORY_ONLY_SOURCE_PATHS:
        _write(root, repository_path, (REPOSITORY / repository_path).read_bytes())
    source_commit = _commit(
        root,
        "item-21 source anchor",
        "src",
        "pyproject.toml",
        preseed.fused_start.D7_RUNTIME_LOCK_REPOSITORY_PATH,
        *preseed.fused_start._REPOSITORY_ONLY_SOURCE_PATHS,
    )
    return _RepositoryLineage(root, pr26_commit, source_commit)


def _fake_recorded_components(
    source_observation: dict[str, object],
) -> dict[str, object]:
    components = {
        name: {
            "schema_version": schema_version,
            "canonical_sha256": digest,
            "byte_count": byte_count,
        }
        for name, (schema_version, digest, byte_count) in sorted(
            preseed._C1_COMPONENT_BINDINGS.items()
        )
    }
    members = source_observation.get("members")
    assert type(members) is list
    generator_members = [
        member
        for member in members
        if type(member) is dict
        and member.get("repository_path")
        == preseed.spectral_generator.SPECTRAL_MOMENT_SOURCE_PATH
    ]
    assert len(generator_members) == 1
    generator_member = generator_members[0]
    return {
        "recorded_c1": {
            "repository_path": preseed.c1.D7_C1_BUNDLE_REPOSITORY_PATH,
            "schema_version": preseed.authority.D7_RECORDED_C1_SCHEMA_VERSION,
            "canonical_sha256": "1" * 64,
            "byte_count": 1,
        },
        "recorded_c2": {
            "repository_path": preseed.c1.D7_C2_RECEIPT_REPOSITORY_PATH,
            "schema_version": preseed.authority.D7_RECORDED_C2_SCHEMA_VERSION,
            "canonical_sha256": "2" * 64,
            "byte_count": 1,
        },
        "components": components,
        "generator_source": {
            "repository_path": preseed.spectral_generator.SPECTRAL_MOMENT_SOURCE_PATH,
            "canonical_sha256": generator_member["sha256"],
            "byte_count": generator_member["byte_count"],
            "git_mode": generator_member["git_mode"],
            "family_id": preseed.spectral_generator.SPECTRAL_MOMENT_GENERATOR_FAMILY_ID,
            "construction_family_id": (
                preseed.spectral_generator.SPECTRAL_MOMENT_CONSTRUCTION_FAMILY_ID
            ),
            "implementation_id": (
                preseed.spectral_generator.SPECTRAL_MOMENT_IMPLEMENTATION_ID
            ),
            "implementation_version": (
                preseed.spectral_generator.SPECTRAL_MOMENT_IMPLEMENTATION_VERSION
            ),
        },
        "seed_free_design": {
            "schema_version": "spirallens.synthetic-seed-free-design.v0.1",
            "canonical_sha256": "3" * 64,
            "byte_count": 1,
        },
    }


def _patch_bounded_dependencies(
    monkeypatch: pytest.MonkeyPatch,
) -> dict[str, dict[str, object]]:
    runtime = {
        "runtime_specification": {
            "schema_version": "spirallens.synthetic-runtime.v0.1",
            "runtime_id": "bounded-test-runtime",
        },
        "native_runtime": {
            "executable_sha256": "4" * 64,
            "executable_byte_count": 1,
        },
        "complete_installed_inventory_equality_observed_at_issuance": True,
    }
    state = {"live": copy.deepcopy(runtime), "recorded": copy.deepcopy(runtime)}

    def recorded_components(
        _root: Path,
        *,
        source_observation: dict[str, object],
        verify_current_implementation: bool,
    ) -> dict[str, object]:
        del verify_current_implementation
        return copy.deepcopy(_fake_recorded_components(source_observation))

    def runtime_document(
        _root: Path,
        *,
        require_installed_equality: bool,
        source_commit: str | None = None,
        recorded_runtime: dict[str, object] | None = None,
    ) -> dict[str, object]:
        del recorded_runtime, source_commit
        selected = state["live"] if require_installed_equality else state["recorded"]
        return copy.deepcopy(selected)

    monkeypatch.setattr(preseed, "_recorded_components", recorded_components)
    monkeypatch.setattr(preseed, "_runtime_document", runtime_document)
    return state


def _install_execution_traps(monkeypatch: pytest.MonkeyPatch) -> None:
    def unexpected(*_args: object, **_kwargs: object) -> None:
        pytest.fail("item-21 issuance crossed into seed-bearing execution")

    for name in (
        "_load_official_producer_context",
        "_execute_official_context",
        "build_core_oracle_truth",
        "build_loop_oracle_truth",
        "evaluate_oracle_sampled_response",
    ):
        monkeypatch.setattr(preseed.official, name, unexpected)
    monkeypatch.setattr(
        preseed.official.SpectralMomentConfirmationGenerator,
        "generate",
        unexpected,
    )


def _prepare_repository(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[_RepositoryLineage, dict[str, dict[str, object]]]:
    lineage = _new_repository(tmp_path)
    monkeypatch.setattr(
        preseed,
        "D7_PR26_RUNTIME_CLOSURE_MERGE_COMMIT",
        lineage.pr26_commit,
    )
    state = _patch_bounded_dependencies(monkeypatch)
    _install_execution_traps(monkeypatch)
    return lineage, state


def _issue_positive_chain(lineage: _RepositoryLineage) -> _PositiveChain:
    root = lineage.root
    issued_receipt = preseed.issue_d7_item21_source_runtime_receipt(root)
    receipt_source = issued_receipt.path.read_bytes()
    receipt_commit = _commit(
        root,
        "item-21 source/runtime receipt",
        preseed.D7_ITEM21_SOURCE_RUNTIME_RECEIPT_REPOSITORY_PATH,
    )

    issued_readiness = preseed.issue_d7_item21_seed_free_readiness(root)
    readiness_source = issued_readiness.path.read_bytes()
    readiness_commit = _commit(
        root,
        "item-21 seed-free readiness",
        preseed.D7_ITEM21_SEED_FREE_READINESS_REPOSITORY_PATH,
    )

    issued_admission = preseed.issue_d7_item21_reviewed_family_admission(root)
    admission_source = issued_admission.path.read_bytes()
    admission_commit = _commit(
        root,
        "item-21 reviewed family admission",
        preseed.D7_ITEM21_REVIEWED_FAMILY_ADMISSION_REPOSITORY_PATH,
    )
    return _PositiveChain(
        root=root,
        pr26_commit=lineage.pr26_commit,
        source_commit=lineage.source_commit,
        receipt_commit=receipt_commit,
        readiness_commit=readiness_commit,
        admission_commit=admission_commit,
        receipt_source=receipt_source,
        readiness_source=readiness_source,
        admission_source=admission_source,
    )


def _clone(chain: _PositiveChain, destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["git", "clone", "-q", str(chain.root), str(destination)],
        check=True,
        capture_output=True,
    )
    root = destination.resolve()
    _configure_git(root)
    return root


def _checkout(root: Path, commit: str) -> None:
    _git(root, "checkout", "-q", "--detach", commit)


def _merge_hidden_mutation_while_retaining_base(
    root: Path,
    *,
    base_commit: str,
    repository_path: str,
    mutated_source: bytes,
) -> None:
    _git(root, "checkout", "-q", "-b", "honest", base_commit)
    _git(root, "checkout", "-q", "-b", "hidden-mutation")
    _write(root, repository_path, mutated_source)
    _commit(root, "hidden side-branch mutation", repository_path)
    _git(root, "checkout", "-q", "honest")
    _git(root, "merge", "--no-ff", "--no-commit", "hidden-mutation")
    _git(
        root,
        "restore",
        "--source=HEAD",
        "--staged",
        "--worktree",
        "--",
        repository_path,
    )
    _git(root, "commit", "-q", "-m", "retain honest bytes across side merge")


def test_item21_surface_is_private_and_choice_free() -> None:
    callables = (
        preseed.build_d7_item21_source_runtime_receipt,
        preseed.issue_d7_item21_source_runtime_receipt,
        preseed.build_d7_item21_seed_free_readiness,
        preseed.issue_d7_item21_seed_free_readiness,
        preseed.build_d7_item21_reviewed_family_admission,
        preseed.issue_d7_item21_reviewed_family_admission,
        preseed.load_committed_d7_item21_positive_chain,
        preseed.verify_current_d7_item21_ready_for_seed_supply,
    )
    forbidden_fragments = (
        "seed",
        "supplier",
        "callback",
        "generator",
        "oracle",
        "target",
        "design",
        "freeze",
        "launch",
        "result",
    )
    for candidate in callables:
        parameters = inspect.signature(candidate).parameters
        assert tuple(parameters) == ("repository_root",)
        parameter = parameters["repository_root"]
        assert parameter.kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
        assert parameter.default is inspect.Parameter.empty
        assert not any(
            fragment in name.lower()
            for name in parameters
            for fragment in forbidden_fragments
        )

    assert preseed.__all__ == ()
    for candidate in callables:
        assert not hasattr(qualification, candidate.__name__)


def test_three_issuances_are_receipt_only_direct_children_and_preseed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lineage, _state = _prepare_repository(tmp_path, monkeypatch)
    chain = _issue_positive_chain(lineage)

    expected = (
        (
            chain.receipt_commit,
            chain.source_commit,
            preseed.D7_ITEM21_SOURCE_RUNTIME_RECEIPT_REPOSITORY_PATH,
        ),
        (
            chain.readiness_commit,
            chain.receipt_commit,
            preseed.D7_ITEM21_SEED_FREE_READINESS_REPOSITORY_PATH,
        ),
        (
            chain.admission_commit,
            chain.readiness_commit,
            preseed.D7_ITEM21_REVIEWED_FAMILY_ADMISSION_REPOSITORY_PATH,
        ),
    )
    for commit, parent, repository_path in expected:
        assert _git(chain.root, "rev-list", "--parents", "-n", "1", commit) == (
            f"{commit} {parent}"
        )
        assert (
            _git(
                chain.root,
                "diff-tree",
                "--no-commit-id",
                "--name-status",
                "-r",
                commit,
            )
            == f"A\t{repository_path}"
        )

    receipt = _document(
        chain.root,
        preseed.D7_ITEM21_SOURCE_RUNTIME_RECEIPT_REPOSITORY_PATH,
    )
    readiness = _document(
        chain.root,
        preseed.D7_ITEM21_SEED_FREE_READINESS_REPOSITORY_PATH,
    )
    admission = _document(
        chain.root,
        preseed.D7_ITEM21_REVIEWED_FAMILY_ADMISSION_REPOSITORY_PATH,
    )
    assert receipt["state"]["supplier_invoked"] is False
    assert receipt["state"]["official_seed_inventory_present"] is False
    assert readiness["readiness"]["supplier_invoked"] is False
    assert readiness["readiness"]["official_seed_inventory_present"] is False
    assert admission["decision"]["family_admitted"] is True
    assert admission["decision"]["seed_supply_claim_acquired"] is False
    assert admission["decision"]["supplier_invoked"] is False
    assert admission["decision"]["official_seed_inventory_present"] is False
    assert readiness["predecessor"]["introduction_commit"] == chain.receipt_commit
    assert (
        admission["source_runtime_predecessor"]["introduction_commit"]
        == chain.receipt_commit
    )
    assert (
        admission["readiness_predecessor"]["introduction_commit"]
        == chain.readiness_commit
    )
    generator_members = [
        member
        for member in receipt["source_observation"]["members"]
        if member["repository_path"]
        == preseed.spectral_generator.SPECTRAL_MOMENT_SOURCE_PATH
    ]
    assert len(generator_members) == 1
    recorded_generator = readiness["recorded_inputs"]["generator_source"]
    assert recorded_generator == {
        "repository_path": preseed.spectral_generator.SPECTRAL_MOMENT_SOURCE_PATH,
        "canonical_sha256": generator_members[0]["sha256"],
        "byte_count": generator_members[0]["byte_count"],
        "git_mode": generator_members[0]["git_mode"],
        "family_id": preseed.spectral_generator.SPECTRAL_MOMENT_GENERATOR_FAMILY_ID,
        "construction_family_id": (
            preseed.spectral_generator.SPECTRAL_MOMENT_CONSTRUCTION_FAMILY_ID
        ),
        "implementation_id": preseed.spectral_generator.SPECTRAL_MOMENT_IMPLEMENTATION_ID,
        "implementation_version": (
            preseed.spectral_generator.SPECTRAL_MOMENT_IMPLEMENTATION_VERSION
        ),
    }

    loaded = preseed.load_committed_d7_item21_positive_chain(chain.root)
    verified = preseed.verify_current_d7_item21_ready_for_seed_supply(chain.root)
    assert (
        loaded.reviewed_family_admission.introduction_commit == chain.admission_commit
    )
    assert loaded.anchor_to_admission_source_tree_continuity_verified is True
    assert loaded.current_source_tree_verified is False
    assert verified.chain.reviewed_family_admission.introduction_commit == (
        chain.admission_commit
    )
    assert verified.current_source_tree_verified is True
    assert verified.confirmation_family_admitted is True
    assert verified.seed_supply_claim_acquired is False
    assert verified.supplier_invoked is False


def test_readiness_rejects_rebound_fixed_builders_before_invocation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lineage, _state = _prepare_repository(tmp_path, monkeypatch)
    preseed.issue_d7_item21_source_runtime_receipt(lineage.root)
    _commit(
        lineage.root,
        "item-21 source/runtime receipt",
        preseed.D7_ITEM21_SOURCE_RUNTIME_RECEIPT_REPOSITORY_PATH,
    )
    invoked: list[str] = []

    def rebound_full_inventory(
        *,
        design: object,
        official_seed_inventory: object,
    ) -> dict[str, object]:
        del design, official_seed_inventory
        invoked.append("full-inventory")
        return {}

    def rebound_full_design(
        *,
        design: object,
        official_seed_inventory: object,
        full_inventory_sha256: str,
        implementation_registry_sha256: str,
        aggregation_sha256: str,
    ) -> dict[str, object]:
        del (
            design,
            official_seed_inventory,
            full_inventory_sha256,
            implementation_registry_sha256,
            aggregation_sha256,
        )
        invoked.append("full-design")
        return {}

    for name, replacement in (
        ("build_d7_official_full_inventory_document", rebound_full_inventory),
        ("build_d7_official_full_design_document", rebound_full_design),
    ):
        original = getattr(preseed.official, name)
        monkeypatch.setattr(preseed.official, name, replacement)
        with pytest.raises(QualificationContractError, match="identity differs"):
            preseed.build_d7_item21_seed_free_readiness(lineage.root)
        assert invoked == []
        monkeypatch.setattr(preseed.official, name, original)


def test_historical_chain_survives_builder_refactor_but_live_readiness_rejects(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lineage, _state = _prepare_repository(tmp_path, monkeypatch)
    chain = _issue_positive_chain(lineage)

    def successor_full_inventory(
        *,
        design: object,
        official_seed_inventory: object,
    ) -> dict[str, object]:
        del design, official_seed_inventory
        return {}

    monkeypatch.setattr(
        preseed.official,
        "build_d7_official_full_inventory_document",
        successor_full_inventory,
    )
    loaded = preseed.load_committed_d7_item21_positive_chain(chain.root)
    assert loaded.current_source_tree_verified is False
    with pytest.raises(QualificationContractError, match="identity differs"):
        preseed.verify_current_d7_item21_ready_for_seed_supply(chain.root)


def test_recorded_generator_source_joins_one_unique_source_member(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recorded_components = preseed._recorded_components
    lineage, _state = _prepare_repository(tmp_path, monkeypatch)
    source_observation = preseed._source_inventory(
        lineage.root,
        lineage.source_commit,
        require_current_equality=True,
    )
    recorded = recorded_components(
        lineage.root,
        source_observation=source_observation,
        verify_current_implementation=False,
    )
    generator_members = [
        member
        for member in source_observation["members"]
        if member["repository_path"]
        == preseed.spectral_generator.SPECTRAL_MOMENT_SOURCE_PATH
    ]
    assert len(generator_members) == 1
    assert recorded["generator_source"] == {
        "repository_path": preseed.spectral_generator.SPECTRAL_MOMENT_SOURCE_PATH,
        "canonical_sha256": generator_members[0]["sha256"],
        "byte_count": generator_members[0]["byte_count"],
        "git_mode": generator_members[0]["git_mode"],
        "family_id": preseed.spectral_generator.SPECTRAL_MOMENT_GENERATOR_FAMILY_ID,
        "construction_family_id": (
            preseed.spectral_generator.SPECTRAL_MOMENT_CONSTRUCTION_FAMILY_ID
        ),
        "implementation_id": preseed.spectral_generator.SPECTRAL_MOMENT_IMPLEMENTATION_ID,
        "implementation_version": (
            preseed.spectral_generator.SPECTRAL_MOMENT_IMPLEMENTATION_VERSION
        ),
    }

    duplicate = copy.deepcopy(source_observation)
    duplicate["members"].append(copy.deepcopy(generator_members[0]))
    with pytest.raises(QualificationContractError, match="one unique"):
        recorded_components(
            lineage.root,
            source_observation=duplicate,
            verify_current_implementation=False,
        )

    wrong_digest = copy.deepcopy(source_observation)
    wrong_member = next(
        member
        for member in wrong_digest["members"]
        if member["repository_path"]
        == preseed.spectral_generator.SPECTRAL_MOMENT_SOURCE_PATH
    )
    wrong_member["sha256"] = "0" * 64
    with pytest.raises(QualificationContractError, match="source anchor"):
        recorded_components(
            lineage.root,
            source_observation=wrong_digest,
            verify_current_implementation=False,
        )


def test_source_receipt_rejects_an_executable_runtime_lock(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lineage, _state = _prepare_repository(tmp_path, monkeypatch)
    lock_path = lineage.root / preseed.fused_start.D7_RUNTIME_LOCK_REPOSITORY_PATH
    lock_path.chmod(0o755)
    _commit(
        lineage.root,
        "make runtime lock executable",
        preseed.fused_start.D7_RUNTIME_LOCK_REPOSITORY_PATH,
    )

    with pytest.raises(QualificationContractError, match="requires a 100644"):
        preseed.build_d7_item21_source_runtime_receipt(lineage.root)


def test_all_three_records_reject_canonical_nested_laundering(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lineage, _state = _prepare_repository(tmp_path, monkeypatch)
    chain = _issue_positive_chain(lineage)

    receipt_root = _clone(chain, tmp_path / "mutations" / "receipt")
    _checkout(receipt_root, chain.source_commit)
    receipt = parse_canonical_json(chain.receipt_source)
    assert type(receipt) is dict
    receipt["state"]["supplier_invoked"] = 0
    _write(
        receipt_root,
        preseed.D7_ITEM21_SOURCE_RUNTIME_RECEIPT_REPOSITORY_PATH,
        canonical_json_bytes(receipt),
    )
    _commit(
        receipt_root,
        "boolean integer laundering",
        preseed.D7_ITEM21_SOURCE_RUNTIME_RECEIPT_REPOSITORY_PATH,
    )
    with pytest.raises(QualificationContractError, match="exact reconstruction"):
        preseed._load_source_receipt(receipt_root)

    readiness_root = _clone(chain, tmp_path / "mutations" / "readiness")
    _checkout(readiness_root, chain.receipt_commit)
    readiness = parse_canonical_json(chain.readiness_source)
    assert type(readiness) is dict
    readiness["readiness"]["unreviewed_extension"] = False
    _write(
        readiness_root,
        preseed.D7_ITEM21_SEED_FREE_READINESS_REPOSITORY_PATH,
        canonical_json_bytes(readiness),
    )
    _commit(
        readiness_root,
        "nested readiness extension",
        preseed.D7_ITEM21_SEED_FREE_READINESS_REPOSITORY_PATH,
    )
    loaded_receipt = preseed._load_source_receipt(readiness_root)
    with pytest.raises(QualificationContractError, match="exact reconstruction"):
        preseed._load_readiness(readiness_root, loaded_receipt)

    admission_root = _clone(chain, tmp_path / "mutations" / "admission")
    _checkout(admission_root, chain.readiness_commit)
    admission = parse_canonical_json(chain.admission_source)
    assert type(admission) is dict
    del admission["decision"]["family_admitted"]
    _write(
        admission_root,
        preseed.D7_ITEM21_REVIEWED_FAMILY_ADMISSION_REPOSITORY_PATH,
        canonical_json_bytes(admission),
    )
    _commit(
        admission_root,
        "missing admission decision",
        preseed.D7_ITEM21_REVIEWED_FAMILY_ADMISSION_REPOSITORY_PATH,
    )
    loaded_receipt = preseed._load_source_receipt(admission_root)
    loaded_readiness = preseed._load_readiness(admission_root, loaded_receipt)
    with pytest.raises(QualificationContractError, match="exact reconstruction"):
        preseed._load_admission(
            admission_root,
            loaded_receipt,
            loaded_readiness,
        )

    for source in (b'{"b":1,"a":2}', b'{"a":1,"a":1}'):
        with pytest.raises(QualificationContractError):
            preseed._parse_canonical_artifact(source, label="mutated item-21")


def test_loader_rejects_collapsed_reversed_sibling_and_drifted_history(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lineage, _state = _prepare_repository(tmp_path, monkeypatch)
    chain = _issue_positive_chain(lineage)
    variants = tmp_path / "chronology"

    collapsed = _clone(chain, variants / "collapsed")
    _checkout(collapsed, chain.source_commit)
    for path, source in (
        (
            preseed.D7_ITEM21_SOURCE_RUNTIME_RECEIPT_REPOSITORY_PATH,
            chain.receipt_source,
        ),
        (preseed.D7_ITEM21_SEED_FREE_READINESS_REPOSITORY_PATH, chain.readiness_source),
        (
            preseed.D7_ITEM21_REVIEWED_FAMILY_ADMISSION_REPOSITORY_PATH,
            chain.admission_source,
        ),
    ):
        _write(collapsed, path, source)
    _commit(collapsed, "collapsed item-21", *preseed._ARTIFACT_PATHS)
    with pytest.raises(
        QualificationContractError, match="more than its one added file"
    ):
        preseed.load_committed_d7_item21_positive_chain(collapsed)

    reversed_root = _clone(chain, variants / "reversed")
    _checkout(reversed_root, chain.source_commit)
    _write(
        reversed_root,
        preseed.D7_ITEM21_SEED_FREE_READINESS_REPOSITORY_PATH,
        chain.readiness_source,
    )
    _commit(
        reversed_root,
        "readiness before receipt",
        preseed.D7_ITEM21_SEED_FREE_READINESS_REPOSITORY_PATH,
    )
    _write(
        reversed_root,
        preseed.D7_ITEM21_SOURCE_RUNTIME_RECEIPT_REPOSITORY_PATH,
        chain.receipt_source,
    )
    _commit(
        reversed_root,
        "receipt after readiness",
        preseed.D7_ITEM21_SOURCE_RUNTIME_RECEIPT_REPOSITORY_PATH,
    )
    with pytest.raises(QualificationContractError, match="required direct child"):
        preseed._load_source_receipt(reversed_root)

    sibling = _clone(chain, variants / "sibling")
    _checkout(sibling, chain.source_commit)
    _write(
        sibling,
        preseed.D7_ITEM21_SEED_FREE_READINESS_REPOSITORY_PATH,
        chain.readiness_source,
    )
    _commit(
        sibling,
        "sibling readiness",
        preseed.D7_ITEM21_SEED_FREE_READINESS_REPOSITORY_PATH,
    )
    _git(
        sibling,
        "merge",
        "-q",
        "--no-ff",
        chain.receipt_commit,
        "-m",
        "merge sibling receipt",
    )
    with pytest.raises(QualificationContractError, match="required direct child"):
        preseed.load_committed_d7_item21_positive_chain(sibling)

    extra_delta = _clone(chain, variants / "extra-delta")
    _checkout(extra_delta, chain.source_commit)
    _write(
        extra_delta,
        preseed.D7_ITEM21_SOURCE_RUNTIME_RECEIPT_REPOSITORY_PATH,
        chain.receipt_source,
    )
    (extra_delta / "unreviewed.txt").write_text("extra delta\n", encoding="utf-8")
    _commit(
        extra_delta,
        "receipt plus extra delta",
        preseed.D7_ITEM21_SOURCE_RUNTIME_RECEIPT_REPOSITORY_PATH,
        "unreviewed.txt",
    )
    with pytest.raises(
        QualificationContractError, match="more than its one added file"
    ):
        preseed._load_source_receipt(extra_delta)

    blob_mutation = _clone(chain, variants / "blob-mutation")
    receipt = parse_canonical_json(chain.receipt_source)
    assert type(receipt) is dict
    receipt["limitations"]["external_timestamp_proved"] = True
    _write(
        blob_mutation,
        preseed.D7_ITEM21_SOURCE_RUNTIME_RECEIPT_REPOSITORY_PATH,
        canonical_json_bytes(receipt),
    )
    _commit(
        blob_mutation,
        "mutate receipt blob",
        preseed.D7_ITEM21_SOURCE_RUNTIME_RECEIPT_REPOSITORY_PATH,
    )
    with pytest.raises(QualificationContractError):
        preseed.load_committed_d7_item21_positive_chain(blob_mutation)

    source_drift = _clone(chain, variants / "source-drift")
    (source_drift / "src" / "spirallens" / "__init__.py").write_text(
        '"""Drifted after the item-21 source receipt."""\n',
        encoding="utf-8",
    )
    _commit(source_drift, "drift execution source", "src/spirallens/__init__.py")
    historically_loaded = preseed.load_committed_d7_item21_positive_chain(source_drift)
    assert (
        historically_loaded.anchor_to_admission_source_tree_continuity_verified is True
    )
    assert historically_loaded.current_source_tree_verified is False
    with pytest.raises(
        QualificationContractError,
        match="current execution-source inventory differs",
    ):
        preseed.verify_current_d7_item21_ready_for_seed_supply(source_drift)

    lock_drift = _clone(chain, variants / "lock-drift")
    lock_path = lock_drift / preseed.fused_start.D7_RUNTIME_LOCK_REPOSITORY_PATH
    lock_path.write_text("synthetic-runtime==2.0\n", encoding="utf-8")
    _commit(
        lock_drift,
        "drift runtime lock after receipt",
        preseed.fused_start.D7_RUNTIME_LOCK_REPOSITORY_PATH,
    )
    historically_loaded = preseed.load_committed_d7_item21_positive_chain(lock_drift)
    assert (
        historically_loaded.anchor_to_admission_source_tree_continuity_verified is True
    )
    assert historically_loaded.current_source_tree_verified is False
    with pytest.raises(
        QualificationContractError,
        match="current execution-source inventory differs",
    ):
        preseed.verify_current_d7_item21_ready_for_seed_supply(lock_drift)


def test_preserving_merge_commit_retains_the_exact_positive_chain(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lineage, _state = _prepare_repository(tmp_path, monkeypatch)
    chain = _issue_positive_chain(lineage)
    merged = _clone(chain, tmp_path / "preserving-merge")
    _checkout(merged, chain.pr26_commit)
    _git(merged, "checkout", "-q", "-b", "integration")
    (merged / "integration-note.txt").write_text(
        "unrelated sibling first-parent history\n",
        encoding="utf-8",
    )
    _commit(merged, "unrelated first-parent commit", "integration-note.txt")
    _git(
        merged,
        "merge",
        "-q",
        "--no-ff",
        chain.admission_commit,
        "-m",
        "preserve item-21 chain",
    )

    loaded = preseed.load_committed_d7_item21_positive_chain(merged)
    assert loaded.source_runtime_receipt.introduction_commit == chain.receipt_commit
    assert loaded.seed_free_readiness.introduction_commit == chain.readiness_commit
    assert (
        loaded.reviewed_family_admission.introduction_commit == chain.admission_commit
    )
    ready = preseed.verify_current_d7_item21_ready_for_seed_supply(merged)
    assert ready.current_source_tree_verified is True


@pytest.mark.parametrize(
    ("repository_path", "source_attribute"),
    (
        (
            preseed.D7_ITEM21_SOURCE_RUNTIME_RECEIPT_REPOSITORY_PATH,
            "receipt_source",
        ),
        (
            preseed.D7_ITEM21_SEED_FREE_READINESS_REPOSITORY_PATH,
            "readiness_source",
        ),
        (
            preseed.D7_ITEM21_REVIEWED_FAMILY_ADMISSION_REPOSITORY_PATH,
            "admission_source",
        ),
    ),
)
def test_hidden_side_branch_artifact_mutation_is_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    repository_path: str,
    source_attribute: str,
) -> None:
    lineage, _state = _prepare_repository(tmp_path, monkeypatch)
    chain = _issue_positive_chain(lineage)
    hidden = _clone(chain, tmp_path / "hidden-artifact-mutation")
    expected_source = getattr(chain, source_attribute)
    _merge_hidden_mutation_while_retaining_base(
        hidden,
        base_commit=chain.admission_commit,
        repository_path=repository_path,
        mutated_source=expected_source + b" ",
    )

    assert (hidden / repository_path).read_bytes() == expected_source
    assert _git(hidden, "log", "--format=%H", "--", repository_path) in {
        chain.receipt_commit,
        chain.readiness_commit,
        chain.admission_commit,
    }
    with pytest.raises(
        QualificationContractError,
        match="reachable full Git history",
    ):
        preseed.load_committed_d7_item21_positive_chain(hidden)


def test_parallel_artifact_introduction_is_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lineage, _state = _prepare_repository(tmp_path, monkeypatch)
    chain = _issue_positive_chain(lineage)
    parallel = _clone(chain, tmp_path / "parallel-introduction")
    path = preseed.D7_ITEM21_SOURCE_RUNTIME_RECEIPT_REPOSITORY_PATH
    _git(parallel, "checkout", "-q", "-b", "honest", chain.admission_commit)
    _git(parallel, "checkout", "-q", "-b", "parallel", chain.source_commit)
    _write(parallel, path, chain.receipt_source)
    _commit(parallel, "parallel receipt introduction", path)
    _git(parallel, "checkout", "-q", "honest")
    _git(parallel, "merge", "-q", "--no-ff", "parallel", "-m", "merge parallel")

    with pytest.raises(
        QualificationContractError,
        match="one unique immutable introduction",
    ):
        preseed.load_committed_d7_item21_positive_chain(parallel)


def test_parallel_exact_blob_with_extra_delta_is_outside_introduction_lineage(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lineage, _state = _prepare_repository(tmp_path, monkeypatch)
    chain = _issue_positive_chain(lineage)
    parallel = _clone(chain, tmp_path / "parallel-extra-delta")
    path = preseed.D7_ITEM21_SOURCE_RUNTIME_RECEIPT_REPOSITORY_PATH
    _git(parallel, "checkout", "-q", "-b", "honest", chain.admission_commit)
    _git(parallel, "checkout", "-q", "-b", "parallel", chain.source_commit)
    _write(parallel, path, chain.receipt_source)
    (parallel / "parallel-extra.txt").write_text(
        "must not widen the artifact lineage\n",
        encoding="utf-8",
    )
    _commit(
        parallel,
        "parallel exact receipt plus extra delta",
        path,
        "parallel-extra.txt",
    )
    _git(parallel, "checkout", "-q", "honest")
    _git(parallel, "merge", "-q", "--no-ff", "parallel", "-m", "merge parallel")

    with pytest.raises(
        QualificationContractError,
        match="unique introduction lineage",
    ):
        preseed.load_committed_d7_item21_positive_chain(parallel)


def test_full_path_history_cap_fails_closed_before_truncation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lineage, _state = _prepare_repository(tmp_path, monkeypatch)
    chain = _issue_positive_chain(lineage)
    capped = _clone(chain, tmp_path / "capped-history")
    path = preseed.D7_ITEM21_SOURCE_RUNTIME_RECEIPT_REPOSITORY_PATH
    _merge_hidden_mutation_while_retaining_base(
        capped,
        base_commit=chain.admission_commit,
        repository_path=path,
        mutated_source=chain.receipt_source + b" ",
    )
    monkeypatch.setattr(preseed, "MAX_D7_ITEM21_HISTORY_COMMITS", 1)

    with pytest.raises(
        QualificationContractError,
        match="exceeds its commit cap",
    ):
        preseed.load_committed_d7_item21_positive_chain(capped)


def test_shallow_repository_is_rejected_before_history_verification(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lineage, _state = _prepare_repository(tmp_path, monkeypatch)
    chain = _issue_positive_chain(lineage)
    shallow = _clone(chain, tmp_path / "shallow-history")
    shallow_path = Path(_git(shallow, "rev-parse", "--git-path", "shallow"))
    if not shallow_path.is_absolute():
        shallow_path = shallow / shallow_path
    shallow_path.write_text(f"{chain.source_commit}\n", encoding="ascii")
    assert _git(shallow, "rev-parse", "--is-shallow-repository") == "true"

    with pytest.raises(
        QualificationContractError,
        match="complete non-shallow Git history",
    ):
        preseed.load_committed_d7_item21_positive_chain(shallow)


def test_descendant_artifact_delete_and_readd_is_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lineage, _state = _prepare_repository(tmp_path, monkeypatch)
    chain = _issue_positive_chain(lineage)
    rewritten = _clone(chain, tmp_path / "delete-readd")
    path = preseed.D7_ITEM21_SOURCE_RUNTIME_RECEIPT_REPOSITORY_PATH
    _git(rewritten, "rm", "-q", "--", path)
    _git(rewritten, "commit", "-q", "-m", "delete receipt")
    _write(rewritten, path, chain.receipt_source)
    _commit(rewritten, "re-add receipt", path)

    with pytest.raises(
        QualificationContractError,
        match="reachable full Git history",
    ):
        preseed.load_committed_d7_item21_positive_chain(rewritten)


@pytest.mark.parametrize("history_shape", ("revert", "hidden-merge"))
def test_descendant_source_history_change_requires_reanchor(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    history_shape: str,
) -> None:
    lineage, _state = _prepare_repository(tmp_path, monkeypatch)
    chain = _issue_positive_chain(lineage)
    changed = _clone(chain, tmp_path / f"source-{history_shape}")
    path = "src/spirallens/__init__.py"
    original_source = (changed / path).read_bytes()
    mutated_source = original_source + b"# transient source change\n"

    if history_shape == "revert":
        _write(changed, path, mutated_source)
        _commit(changed, "change execution source", path)
        _write(changed, path, original_source)
        _commit(changed, "revert execution source", path)
    else:
        _merge_hidden_mutation_while_retaining_base(
            changed,
            base_commit=chain.admission_commit,
            repository_path=path,
            mutated_source=mutated_source,
        )

    assert (changed / path).read_bytes() == original_source
    historically_loaded = preseed.load_committed_d7_item21_positive_chain(changed)
    assert historically_loaded.current_source_tree_verified is False
    with pytest.raises(
        QualificationContractError,
        match="execution-source history changed",
    ):
        preseed.verify_current_d7_item21_ready_for_seed_supply(changed)


def test_historical_source_inventory_enforces_live_member_cap(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lineage, _state = _prepare_repository(tmp_path, monkeypatch)
    existing_members = [
        path
        for path in (lineage.root / "src" / "spirallens").rglob("*")
        if path.is_file()
    ]
    existing_members.extend(
        (
            lineage.root / "pyproject.toml",
            lineage.root / preseed.fused_start.D7_RUNTIME_LOCK_REPOSITORY_PATH,
        )
    )
    member_cap = max(path.stat().st_size for path in existing_members)
    monkeypatch.setattr(preseed, "MAX_D7_ITEM21_SOURCE_MEMBER_BYTES", member_cap)
    monkeypatch.setattr(
        preseed.fused_start,
        "MAX_D7_SOURCE_RUNTIME_MEMBER_BYTES",
        member_cap,
    )
    path = "src/spirallens/oversized.py"
    _write(lineage.root, path, b"x" * (member_cap + 1))
    oversized_commit = _commit(lineage.root, "oversized source member", path)

    with pytest.raises(
        QualificationContractError,
        match="bounded unaliased regular file",
    ):
        preseed.build_d7_item21_source_runtime_receipt(lineage.root)
    with pytest.raises(QualificationContractError, match="fixed byte cap"):
        preseed._source_inventory(
            lineage.root,
            oversized_commit,
            require_current_equality=False,
        )


def test_repository_only_members_are_live_required_but_not_retroactive(
    tmp_path: Path,
) -> None:
    lineage = _new_repository(tmp_path)
    for repository_path in preseed.fused_start._REPOSITORY_ONLY_SOURCE_PATHS:
        (lineage.root / repository_path).unlink()
    without_item23 = _commit(
        lineage.root,
        "historical source without future item23 modules",
        *preseed.fused_start._REPOSITORY_ONLY_SOURCE_PATHS,
    )

    historical = preseed._source_inventory(
        lineage.root,
        without_item23,
        require_current_equality=False,
    )
    historical_paths = {
        str(member["repository_path"]) for member in historical["members"]
    }
    assert not set(preseed.fused_start._REPOSITORY_ONLY_SOURCE_PATHS).intersection(
        historical_paths
    )
    with pytest.raises(
        QualificationContractError,
        match="lacks its fixed code or dependency-lock surface",
    ):
        preseed._source_inventory(
            lineage.root,
            without_item23,
            require_current_equality=True,
        )


def test_c2_bytes_cannot_substitute_for_the_positive_source_receipt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lineage, _state = _prepare_repository(tmp_path, monkeypatch)
    c2_source = (REPOSITORY / preseed.c1.D7_C2_RECEIPT_REPOSITORY_PATH).read_bytes()
    _write(
        lineage.root,
        preseed.D7_ITEM21_SOURCE_RUNTIME_RECEIPT_REPOSITORY_PATH,
        c2_source,
    )
    _commit(
        lineage.root,
        "misplaced C2 receipt",
        preseed.D7_ITEM21_SOURCE_RUNTIME_RECEIPT_REPOSITORY_PATH,
    )

    with pytest.raises(QualificationContractError, match="fields differ"):
        preseed._load_source_receipt(lineage.root)


@pytest.mark.parametrize(
    "future_path",
    (
        f"{preseed.D7_ITEM22_SEED_SUPPLY_DIRECTORY_REPOSITORY_PATH}/seed.json",
        preseed.D7_ITEM22_CURRENT_SOURCE_REANCHOR_REPOSITORY_PATH,
        preseed.D7_FUTURE_LAUNCH_DESCRIPTOR_REPOSITORY_PATH,
    ),
)
def test_future_item22_paths_are_rejected_before_and_after_item21(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    future_path: str,
) -> None:
    lineage, _state = _prepare_repository(tmp_path, monkeypatch)
    chain = _issue_positive_chain(lineage)

    before = _clone(chain, tmp_path / "absence" / "before")
    _checkout(before, chain.source_commit)
    _write(before, future_path, b"{}")
    _commit(before, "future path too early", future_path)
    with pytest.raises(QualificationContractError, match="preseed path"):
        preseed.issue_d7_item21_source_runtime_receipt(before)

    after = _clone(chain, tmp_path / "absence" / "after")
    _write(after, future_path, b"{}")
    _commit(after, "future path before reobservation", future_path)
    historically_loaded = preseed.load_committed_d7_item21_positive_chain(after)
    assert historically_loaded.current_preseed_absence_verified is False
    with pytest.raises(QualificationContractError, match="preseed path"):
        preseed.verify_current_d7_item21_ready_for_seed_supply(after)


def test_handoffs_reject_wrong_factory_token_and_cannot_be_copied_or_pickled(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lineage, _state = _prepare_repository(tmp_path, monkeypatch)
    chain = _issue_positive_chain(lineage)
    loaded = preseed.load_committed_d7_item21_positive_chain(chain.root)
    verified = preseed.verify_current_d7_item21_ready_for_seed_supply(chain.root)
    assert verified.point_in_time_observation_only is True
    assert verified.freshness_retained_after_return is False
    assert verified.reusable_authorization_capability_present is False

    with pytest.raises(QualificationContractError, match="strict repository loader"):
        preseed._LoadedD7Item21PositiveChain(
            repository_root=loaded.repository_root,
            source_runtime_receipt=loaded.source_runtime_receipt,
            seed_free_readiness=loaded.seed_free_readiness,
            reviewed_family_admission=loaded.reviewed_family_admission,
            _factory_token=object(),
        )
    with pytest.raises(QualificationContractError, match="live reobservation"):
        preseed._VerifiedD7Item21ReadyForSeedSupply(
            loaded,
            _factory_token=object(),
        )

    for value in (loaded, verified):
        with pytest.raises(TypeError):
            copy.copy(value)
        with pytest.raises(TypeError):
            copy.deepcopy(value)
        with pytest.raises(TypeError):
            pickle.dumps(value)
    with pytest.raises(AttributeError, match="immutable"):
        verified._chain = loaded


def test_current_helper_rejects_an_exact_runtime_mismatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lineage, state = _prepare_repository(tmp_path, monkeypatch)
    chain = _issue_positive_chain(lineage)

    state["live"] = {
        **state["live"],
        "runtime_specification": {
            "schema_version": "spirallens.synthetic-runtime.v0.1",
            "runtime_id": "different-live-runtime",
        },
    }
    loaded = preseed.load_committed_d7_item21_positive_chain(chain.root)
    assert loaded.current_live_runtime_verified is False
    with pytest.raises(QualificationContractError, match="current runtime differs"):
        preseed.verify_current_d7_item21_ready_for_seed_supply(chain.root)


def test_recorded_current_item21_chain_when_artifacts_exist() -> None:
    paths = tuple(REPOSITORY / path for path in preseed._ARTIFACT_PATHS)
    tracked = tuple(
        subprocess.run(
            ["git", "-C", str(REPOSITORY), "ls-files", "--error-unmatch", str(path)],
            check=False,
            capture_output=True,
        ).returncode
        == 0
        for path in preseed._ARTIFACT_PATHS
    )
    if not all(tracked):
        pytest.skip("recorded item-21 positive-chain artifacts are not committed yet")

    assert all(path.is_file() and not path.is_symlink() for path in paths)
    loaded = preseed.load_committed_d7_item21_positive_chain(REPOSITORY)
    assert loaded.git_chronology_verified is True
    assert loaded.anchor_to_admission_source_tree_continuity_verified is True
    assert loaded.current_source_tree_verified is False
    assert loaded.current_live_runtime_verified is False
    assert loaded.seed_supply_claim_acquired is False
    assert loaded.supplier_invoked is False
    assert loaded.scientific_claim_eligible is False
