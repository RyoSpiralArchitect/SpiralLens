from __future__ import annotations

import multiprocessing
import os
import shutil
import subprocess
from collections.abc import Callable, Iterator
from pathlib import Path
from types import SimpleNamespace

import pytest

from spirallens.core.canonical import canonical_json_bytes, parse_canonical_json
from spirallens.qualification import confirmation_attempt_authority as authority
from spirallens.qualification import confirmation_fused_authority as fused_authority
from spirallens.qualification import confirmation_official_execution as official
from spirallens.qualification import confirmation_runtime_observation as runtime_observation
from spirallens.qualification import confirmation_seed_supply_contracts as item22
from spirallens.qualification.common import QualificationContractError

REPOSITORY = Path(__file__).resolve().parents[1]
MODULE_PATH = "src/spirallens/qualification/confirmation_seed_supply_contracts.py"


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


def _clone(source: Path, destination: Path) -> Path:
    subprocess.run(
        ["git", "clone", "--quiet", "--no-hardlinks", str(source), str(destination)],
        check=True,
        capture_output=True,
        text=True,
    )
    _configure_git(destination)
    return destination


def _commit(root: Path, message: str, *paths: str) -> str:
    _git(root, "add", *paths)
    _git(root, "commit", "--quiet", "-m", message)
    return _git(root, "rev-parse", "HEAD")


@pytest.fixture(scope="module", autouse=True)
def exact_locked_test_runtime() -> Iterator[None]:
    patcher = pytest.MonkeyPatch()
    original = runtime_observation._verify_exact_dependency_lock

    def verify(source: bytes):
        pins = runtime_observation._parse_exact_dependency_lock(source)
        distributions = tuple(SimpleNamespace(metadata={"Name": pin.name}, version=pin.version) for pin in pins)
        return original(source, distributions=distributions)

    patcher.setattr(runtime_observation, "_verify_exact_dependency_lock", verify)
    yield
    patcher.undo()


@pytest.fixture(scope="module")
def prepared_repository(tmp_path_factory: pytest.TempPathFactory) -> Path:
    root = _clone(REPOSITORY, tmp_path_factory.mktemp("item22-prepared") / "repository")
    shutil.copyfile(REPOSITORY / MODULE_PATH, root / MODULE_PATH)
    if _git(root, "status", "--short", MODULE_PATH):
        source_commit = _commit(root, "item22 final source", MODULE_PATH)
    else:
        _git(root, "commit", "--quiet", "--allow-empty", "-m", "item22 final source marker")
        source_commit = _git(root, "rev-parse", "HEAD")
    identity = item22.issue_d7_item22_current_source_runtime_reanchor(root)
    assert identity.path == root / item22.D7_ITEM22_CURRENT_SOURCE_RUNTIME_REANCHOR_REPOSITORY_PATH
    reanchor_commit = _commit(
        root,
        "item22 reviewed source runtime reanchor",
        item22.D7_ITEM22_CURRENT_SOURCE_RUNTIME_REANCHOR_REPOSITORY_PATH,
    )
    assert _git(root, "rev-parse", f"{reanchor_commit}^") == source_commit
    assert _git(root, "status", "--short") == ""
    return root


@pytest.fixture
def ready_repository(prepared_repository: Path, tmp_path: Path) -> Path:
    return _clone(prepared_repository, tmp_path / "repository")


@pytest.fixture(scope="module")
def verified_foundation(prepared_repository: Path) -> tuple[object, dict[str, object]]:
    reanchor = item22._verify_reanchor_live(prepared_repository)
    return reanchor, item22._foundation(prepared_repository, reanchor)


@pytest.fixture
def fast_repository(
    ready_repository: Path,
    verified_foundation: tuple[object, dict[str, object]],
    monkeypatch: pytest.MonkeyPatch,
) -> Path:
    reanchor, context = verified_foundation
    monkeypatch.setattr(item22, "_verify_reanchor_live", lambda _root: reanchor)
    monkeypatch.setattr(item22, "_foundation", lambda _root, _reanchor: context)
    return ready_repository


def _sequence_supplier(values: Iterator[int]) -> Callable[[int], int]:
    def supply(bits: int) -> int:
        assert bits == 63
        return next(values)

    return supply


def _run_with_values(
    root: Path,
    monkeypatch: pytest.MonkeyPatch,
    values: tuple[int, int] = (8_001_001, 8_001_002),
) -> None:
    monkeypatch.setattr(item22.secrets, "randbits", _sequence_supplier(iter(values)))
    item22.run_d7_item22_seed_supply_transaction_no_replace(root)


def _matching_freeze(
    root: Path,
    *,
    freeze_commit: str,
    authorization_commit: str,
) -> authority.D7FullDesignFreezeInputRecord:
    target = root / item22.D7_ITEM22_ATOMIC_TARGET_DIRECTORY_REPOSITORY_PATH
    replay = authority.D7ReplayTargetInputRecord.from_dict(
        parse_canonical_json((target / "replay-target.json").read_bytes())
    )
    manifest = parse_canonical_json((target / "transaction-manifest.json").read_bytes())
    assert isinstance(manifest, dict)
    chronology = tuple(
        authority.D7ChronologyInputRecord.from_dict(value)
        for value in manifest["chronology"]
    )
    return authority.D7FullDesignFreezeInputRecord(
        freeze_id="test-item22-full-design-freeze",
        full_design_binding=replay.full_design_binding.design_binding,
        replay_target_binding=item22._binding(
            "replay-target", replay.schema_version, replay.canonical_bytes
        ),
        atomic_publication_binding=chronology[-1].artifact_binding,
        freeze_commit=freeze_commit,
        authorization_commit=authorization_commit,
    )


def test_contract_tables_are_small_closed_and_freeze_descriptor_are_separate() -> None:
    assert item22.__all__ == ()
    assert item22.D7_ITEM22_ATOMIC_TARGET_MEMBER_LAYOUT == (
        ("official-seed-inventory", "official-seed-inventory.json"),
        ("full-inventory", "full-inventory.json"),
        ("full-design", "full-design.json"),
        ("replay-target", "replay-target.json"),
        ("single-supplier-invocation", "single-supplier-invocation.json"),
        ("transaction-manifest", "transaction-manifest.json"),
    )
    assert item22.D7_ITEM22_TARGET_DIGEST_EDGES == (
        ("full-inventory", "official-seed-inventory"),
        ("full-design", "official-seed-inventory"),
        ("full-design", "full-inventory"),
        ("replay-target", "official-seed-inventory"),
        ("replay-target", "full-design"),
        ("single-supplier-invocation", "official-seed-inventory"),
    )
    assert tuple(row[0] for row in item22.D7_ITEM22_STATE_ROWS) == (
        "preclaim",
        "claim-present-publication-absent-nonretryable",
        "seed-supply-aborted-established",
        "publication-complete-unfrozen",
        "full-design-frozen",
        "launch-intent-present",
    )
    assert item22.D7_ITEM22_FULL_DESIGN_FREEZE_REPOSITORY_PATH not in {
        f"{item22.D7_ITEM22_ATOMIC_TARGET_DIRECTORY_REPOSITORY_PATH}/{name}"
        for _role, name in item22.D7_ITEM22_ATOMIC_TARGET_MEMBER_LAYOUT
    }
    assert item22.D7_ITEM22_FUTURE_LAUNCH_DESCRIPTOR_REPOSITORY_PATH == official.D7_OFFICIAL_FUSED_DESCRIPTOR_REPOSITORY_PATH
    assert tuple(spec[0] for spec in fused_authority._MEMBER_SPECS) == (
        "launch-authority-input-bundle",
        "replay-target",
        "launch-intent",
        "execution-source-runtime-closure",
        "runtime-specification",
        "family-admission",
        "execution-identity",
        "physical-store-lane-identity",
        "full-design-freeze",
    )


def test_versioned_reanchor_reconstructs_and_verifies_live_source(
    prepared_repository: Path,
    verified_foundation: tuple[object, dict[str, object]],
) -> None:
    verified, _context = verified_foundation
    loaded = verified
    document = loaded.document

    assert verified.source == loaded.source
    assert document["schema_version"] == item22.D7_ITEM22_CURRENT_SOURCE_RUNTIME_REANCHOR_SCHEMA_VERSION
    assert document["repository_path"] == item22.D7_ITEM22_CURRENT_SOURCE_RUNTIME_REANCHOR_REPOSITORY_PATH
    assert document["state"]["seed_free_readiness_present"] is True
    assert document["state"]["family_admission_present"] is True
    assert len(document["lineage"]["historical_item21_chain"]) == 3
    assert item22.observe_d7_item22_seed_supply_state(prepared_repository) == "preclaim"


def test_happy_path_claim_precedes_supplier_and_publishes_exact_target(
    ready_repository: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[int] = []
    values = iter((8_002_001, 8_002_002))

    def observed_supplier(bits: int) -> int:
        claim = ready_repository / item22.D7_ITEM22_EXCLUSIVE_SEED_SUPPLY_CLAIM_REPOSITORY_PATH
        assert claim.is_file()
        assert item22.observe_d7_item22_seed_supply_state(ready_repository) == "claim-present-publication-absent-nonretryable"
        if not calls:
            _commit(
                ready_repository,
                "test: commit item22 claim interval",
                item22.D7_ITEM22_EXCLUSIVE_SEED_SUPPLY_CLAIM_REPOSITORY_PATH,
            )
            assert item22.observe_d7_item22_seed_supply_state(ready_repository) == "claim-present-publication-absent-nonretryable"
        calls.append(bits)
        return next(values)

    monkeypatch.setattr(item22.secrets, "randbits", observed_supplier)
    identity = item22.run_d7_item22_seed_supply_transaction_no_replace(ready_repository)
    target = ready_repository / item22.D7_ITEM22_ATOMIC_TARGET_DIRECTORY_REPOSITORY_PATH

    assert calls == [63, 63]
    assert identity.path == target / "transaction-manifest.json"
    assert {path.name for path in target.iterdir()} == {name for _role, name in item22.D7_ITEM22_ATOMIC_TARGET_MEMBER_LAYOUT}
    assert item22.observe_d7_item22_seed_supply_state(ready_repository) == "publication-complete-unfrozen"
    inventory = authority.D7OfficialSeedInventoryRecord.from_dict(
        parse_canonical_json((target / "official-seed-inventory.json").read_bytes(), label="test inventory")
    )
    assert tuple(seed.seed for seed in inventory.seeds) == (8_002_001, 8_002_002)


def test_supplier_exception_establishes_abort_and_restart_never_retries(
    fast_repository: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ready_repository = fast_repository
    calls = 0

    def explode(bits: int) -> int:
        nonlocal calls
        calls += 1
        assert bits == 63
        assert (ready_repository / item22.D7_ITEM22_EXCLUSIVE_SEED_SUPPLY_CLAIM_REPOSITORY_PATH).is_file()
        raise RuntimeError("supplier failed")

    monkeypatch.setattr(item22.secrets, "randbits", explode)
    with pytest.raises(RuntimeError, match="supplier failed"):
        item22.run_d7_item22_seed_supply_transaction_no_replace(ready_repository)
    assert calls == 1
    assert item22.observe_d7_item22_seed_supply_state(ready_repository) == "seed-supply-aborted-established"
    assert not (ready_repository / item22.D7_ITEM22_ATOMIC_TARGET_DIRECTORY_REPOSITORY_PATH).exists()
    _commit(
        ready_repository,
        "test: commit item22 abort",
        item22.D7_ITEM22_SEED_SUPPLY_DIRECTORY_REPOSITORY_PATH,
    )
    assert item22.observe_d7_item22_seed_supply_state(ready_repository) == "seed-supply-aborted-established"

    monkeypatch.setattr(item22.secrets, "randbits", lambda _bits: pytest.fail("restart entered supplier"))
    with pytest.raises(QualificationContractError, match="already consumed"):
        item22.run_d7_item22_seed_supply_transaction_no_replace(ready_repository)
    assert item22.observe_d7_item22_seed_supply_state(ready_repository) == "seed-supply-aborted-established"

    abort_path = ready_repository / item22.D7_ITEM22_SEED_SUPPLY_ABORT_EVIDENCE_REPOSITORY_PATH
    abort_source = abort_path.read_bytes()
    for field, value in (("failed_phase", []), ("supplier_entry_possible", "yes")):
        abort = parse_canonical_json(abort_source)
        assert isinstance(abort, dict)
        abort[field] = value
        abort_path.write_bytes(canonical_json_bytes(abort))
        with pytest.raises(QualificationContractError, match="abort evidence differs"):
            item22.observe_d7_item22_seed_supply_state(ready_repository)


def test_supplier_entry_requires_a_durable_claim(
    fast_repository: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ready_repository = fast_repository
    original_write = item22.durable._write_canonical_file_no_replace

    def visible_without_durability(anchor: object, leaf: str, source: bytes, **kwargs: object):
        identity = original_write(anchor, leaf, source, **kwargs)
        if leaf == "exclusive-seed-supply-claim.json":
            return SimpleNamespace(parent_directory_fsync_proved=False)
        return identity

    monkeypatch.setattr(item22.durable, "_write_canonical_file_no_replace", visible_without_durability)
    monkeypatch.setattr(item22.secrets, "randbits", lambda _bits: pytest.fail("undurable claim entered supplier"))
    with pytest.raises(QualificationContractError, match="durability is unproved"):
        item22.run_d7_item22_seed_supply_transaction_no_replace(ready_repository)
    assert item22.observe_d7_item22_seed_supply_state(ready_repository) == "claim-present-publication-absent-nonretryable"


def test_two_processes_have_one_claim_winner_and_one_supplier_call(
    fast_repository: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ready_repository = fast_repository
    context = multiprocessing.get_context("fork")
    barrier = context.Barrier(2)
    original_write = item22.durable._write_canonical_file_no_replace
    supplier_lock = context.Lock()
    randbit_calls = context.Value("i", 0)
    outcomes = context.Queue()

    def racing_write(anchor: object, leaf: str, source: bytes, **kwargs: object):
        if leaf == "exclusive-seed-supply-claim.json":
            barrier.wait(timeout=30)
        return original_write(anchor, leaf, source, **kwargs)

    def counted_supplier(bits: int) -> int:
        assert bits == 63
        with supplier_lock:
            randbit_calls.value += 1
            return 8_003_000 + randbit_calls.value

    monkeypatch.setattr(item22.durable, "_write_canonical_file_no_replace", racing_write)
    monkeypatch.setattr(item22.secrets, "randbits", counted_supplier)
    def invoke() -> None:
        try:
            item22.run_d7_item22_seed_supply_transaction_no_replace(ready_repository)
            outcomes.put("success")
        except BaseException as error:
            outcomes.put(type(error).__name__)

    processes = [context.Process(target=invoke) for _ in range(2)]
    for process in processes:
        process.start()
    for process in processes:
        process.join(timeout=60)

    assert all(not process.is_alive() and process.exitcode == 0 for process in processes)
    observed = sorted(outcomes.get(timeout=5) for _ in processes)
    assert observed == ["QualificationContractError", "success"]
    assert randbit_calls.value == 2
    assert item22.observe_d7_item22_seed_supply_state(ready_repository) == "publication-complete-unfrozen"


def test_observer_rejects_unknown_and_partial_atomic_targets(
    fast_repository: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ready_repository = fast_repository
    _run_with_values(ready_repository, monkeypatch, (8_004_001, 8_004_002))
    target = ready_repository / item22.D7_ITEM22_ATOMIC_TARGET_DIRECTORY_REPOSITORY_PATH
    unknown = target / "unknown.json"
    unknown.write_bytes(canonical_json_bytes({"unknown": True}))
    with pytest.raises(QualificationContractError, match="member set differs"):
        item22.observe_d7_item22_seed_supply_state(ready_repository)
    unknown.unlink()

    missing = target / "full-design.json"
    source = missing.read_bytes()
    missing.unlink()
    with pytest.raises(QualificationContractError, match="member set differs"):
        item22.observe_d7_item22_seed_supply_state(ready_repository)
    missing.write_bytes(source)
    assert item22.observe_d7_item22_seed_supply_state(ready_repository) == "publication-complete-unfrozen"

    manifest = target / "transaction-manifest.json"
    manifest_source = manifest.read_bytes()
    manifest.write_bytes(b"x" * (item22.MAX_D7_ITEM22_ARTIFACT_BYTES + 1))
    with pytest.raises(QualificationContractError, match="bounded"):
        item22.observe_d7_item22_seed_supply_state(ready_repository)
    manifest.write_bytes(manifest_source)

    full_design = target / "full-design.json"
    full_design_source = full_design.read_bytes()
    hardlink_source = ready_repository / "hardlinked-full-design.json"
    hardlink_source.write_bytes(full_design_source)
    full_design.unlink()
    os.link(hardlink_source, full_design)
    with pytest.raises(QualificationContractError, match="unaliased"):
        item22.observe_d7_item22_seed_supply_state(ready_repository)


def test_observer_reconstructs_claim_and_every_target_member(
    fast_repository: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ready_repository = fast_repository
    _run_with_values(ready_repository, monkeypatch, (8_006_001, 8_006_002))
    claim_path = ready_repository / item22.D7_ITEM22_EXCLUSIVE_SEED_SUPPLY_CLAIM_REPOSITORY_PATH
    claim_source = claim_path.read_bytes()
    claim = parse_canonical_json(claim_source)
    assert isinstance(claim, dict)
    claim["claim_id"] = "forged-item22-claim"
    claim_path.write_bytes(canonical_json_bytes(claim))
    with pytest.raises(QualificationContractError, match="claim differs"):
        item22.observe_d7_item22_seed_supply_state(ready_repository)

    claim_path.write_bytes(claim_source)
    target = ready_repository / item22.D7_ITEM22_ATOMIC_TARGET_DIRECTORY_REPOSITORY_PATH
    manifest_path = target / "transaction-manifest.json"
    manifest = parse_canonical_json(manifest_path.read_bytes())
    assert isinstance(manifest, dict)
    manifest["transaction_id"] = "forged-item22-transaction"
    manifest_path.write_bytes(canonical_json_bytes(manifest))
    with pytest.raises(QualificationContractError, match="target differs"):
        item22.observe_d7_item22_seed_supply_state(ready_repository)


def test_observer_rejects_a_target_directory_swap_during_reload(
    fast_repository: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ready_repository = fast_repository
    _run_with_values(ready_repository, monkeypatch, (8_006_101, 8_006_102))
    target = ready_repository / item22.D7_ITEM22_ATOMIC_TARGET_DIRECTORY_REPOSITORY_PATH
    detached = target.with_name("detached-target")
    original_parse = item22._parse_record
    swapped = False

    def swap_once(*args: object, **kwargs: object):
        nonlocal swapped
        if not swapped and kwargs.get("label") == "official seed inventory":
            target.rename(detached)
            shutil.copytree(detached, target)
            swapped = True
        return original_parse(*args, **kwargs)

    monkeypatch.setattr(item22, "_parse_record", swap_once)
    with pytest.raises(QualificationContractError, match="directory identity changed"):
        item22.observe_d7_item22_seed_supply_state(ready_repository)


def test_observer_rejects_a_same_byte_target_member_inode_replacement(
    fast_repository: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ready_repository = fast_repository
    _run_with_values(ready_repository, monkeypatch, (8_006_201, 8_006_202))
    target = ready_repository / item22.D7_ITEM22_ATOMIC_TARGET_DIRECTORY_REPOSITORY_PATH
    member = target / "full-design.json"
    target_identity = target.stat().st_dev, target.stat().st_ino
    original_identity = member.stat().st_dev, member.stat().st_ino
    original_parse = item22._parse_record
    replaced = False

    def replace_once(*args: object, **kwargs: object):
        nonlocal replaced
        if not replaced and kwargs.get("label") == "official seed inventory":
            replacement = target / ".same-byte-full-design"
            replacement.write_bytes(member.read_bytes())
            os.replace(replacement, member)
            replaced = True
            assert (target.stat().st_dev, target.stat().st_ino) == target_identity
            assert (member.stat().st_dev, member.stat().st_ino) != original_identity
        return original_parse(*args, **kwargs)

    monkeypatch.setattr(item22, "_parse_record", replace_once)
    with pytest.raises(QualificationContractError, match="target member identity or bytes changed"):
        item22.observe_d7_item22_seed_supply_state(ready_repository)


def test_freeze_and_descriptor_must_rejoin_the_published_target(
    fast_repository: Path,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    ready_repository = fast_repository
    _run_with_values(ready_repository, monkeypatch, (8_007_001, 8_007_002))
    freeze_path = ready_repository / item22.D7_ITEM22_FULL_DESIGN_FREEZE_REPOSITORY_PATH
    nonexistent = _matching_freeze(
        ready_repository,
        freeze_commit="a" * 40,
        authorization_commit="b" * 40,
    )
    freeze_path.write_bytes(nonexistent.canonical_bytes)
    with pytest.raises(QualificationContractError, match="commit|Git"):
        item22.observe_d7_item22_seed_supply_state(ready_repository)
    freeze_path.unlink()

    freeze_commit = _commit(
        ready_repository,
        "test: commit item22 target",
        item22.D7_ITEM22_SEED_SUPPLY_DIRECTORY_REPOSITORY_PATH,
    )
    assert item22.observe_d7_item22_seed_supply_state(ready_repository) == "publication-complete-unfrozen"
    authorization_marker = (
        ready_repository
        / item22.D7_ITEM22_DIRECTORY_REPOSITORY_PATH
        / "test-launch-authorization.json"
    )
    authorization_marker.write_bytes(canonical_json_bytes({"authorized": True}))
    authorization_commit = _commit(
        ready_repository,
        "test: authorize item22 freeze",
        authorization_marker.relative_to(ready_repository).as_posix(),
    )
    freeze = _matching_freeze(
        ready_repository,
        freeze_commit=freeze_commit,
        authorization_commit=authorization_commit,
    )
    reversed_freeze = _matching_freeze(
        ready_repository,
        freeze_commit=authorization_commit,
        authorization_commit=freeze_commit,
    )
    freeze_path.write_bytes(reversed_freeze.canonical_bytes)
    with pytest.raises(QualificationContractError, match="ancestry"):
        item22.observe_d7_item22_seed_supply_state(ready_repository)

    wrong = authority.D7FullDesignFreezeInputRecord(
        freeze_id=freeze.freeze_id,
        full_design_binding=authority.D7AuthorityArtifactBinding(
            artifact_role="full-design",
            artifact_contract_id=freeze.full_design_binding.artifact_contract_id,
            canonical_sha256="f" * 64,
            byte_count=freeze.full_design_binding.byte_count,
        ),
        replay_target_binding=freeze.replay_target_binding,
        atomic_publication_binding=freeze.atomic_publication_binding,
        freeze_commit=freeze.freeze_commit,
        authorization_commit=freeze.authorization_commit,
    )
    freeze_path.write_bytes(wrong.canonical_bytes)
    with pytest.raises(QualificationContractError, match="freeze differs"):
        item22.observe_d7_item22_seed_supply_state(ready_repository)

    freeze_path.write_bytes(freeze.canonical_bytes)
    _commit(
        ready_repository,
        "test: commit item22 freeze receipt",
        item22.D7_ITEM22_FULL_DESIGN_FREEZE_REPOSITORY_PATH,
    )
    assert item22.observe_d7_item22_seed_supply_state(ready_repository) == "full-design-frozen"
    tampered = _clone(ready_repository, tmp_path / "tampered-history")
    tampered_design = tampered / item22.D7_ITEM22_ATOMIC_TARGET_DIRECTORY_REPOSITORY_PATH / "full-design.json"
    design_source = tampered_design.read_bytes()
    tampered_design.write_bytes(canonical_json_bytes({"tampered": True}))
    _commit(tampered, "test: mutate frozen target", tampered_design.relative_to(tampered).as_posix())
    tampered_design.write_bytes(design_source)
    _commit(tampered, "test: revert frozen target", tampered_design.relative_to(tampered).as_posix())
    with pytest.raises(QualificationContractError, match="changed after introduction"):
        item22.observe_d7_item22_seed_supply_state(tampered)
    launch_path = ready_repository / item22.D7_ITEM22_FUTURE_LAUNCH_DESCRIPTOR_REPOSITORY_PATH
    launch_path.write_bytes(canonical_json_bytes({"placeholder": True}))
    descriptor = SimpleNamespace(
        inventory=(
            SimpleNamespace(
                artifact_role="replay-target",
                repository_path=(
                    f"{item22.D7_ITEM22_ATOMIC_TARGET_DIRECTORY_REPOSITORY_PATH}/"
                    "replay-target.json"
                ),
            ),
            SimpleNamespace(
                artifact_role="full-design-freeze",
                repository_path=item22.D7_ITEM22_FULL_DESIGN_FREEZE_REPOSITORY_PATH,
            ),
        )
    )
    monkeypatch.setattr(
        fused_authority,
        "load_d7_fused_authority_snapshot",
        lambda _path: SimpleNamespace(
            replay_target=object(),
            full_design_freeze=freeze,
            descriptor=descriptor,
        ),
    )
    with pytest.raises(QualificationContractError, match="descriptor differs"):
        item22.observe_d7_item22_seed_supply_state(ready_repository)

    target = ready_repository / item22.D7_ITEM22_ATOMIC_TARGET_DIRECTORY_REPOSITORY_PATH
    replay = authority.D7ReplayTargetInputRecord.from_dict(
        parse_canonical_json((target / "replay-target.json").read_bytes())
    )
    descriptor.inventory[0].repository_path = "copied-replay-target.json"
    monkeypatch.setattr(
        fused_authority,
        "load_d7_fused_authority_snapshot",
        lambda _path: SimpleNamespace(
            replay_target=replay,
            full_design_freeze=freeze,
            descriptor=descriptor,
        ),
    )
    with pytest.raises(QualificationContractError, match="descriptor differs"):
        item22.observe_d7_item22_seed_supply_state(ready_repository)


def test_freeze_rejects_claim_and_target_introduced_on_a_pre_reanchor_sibling(
    ready_repository: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reanchor_commit = _git(ready_repository, "rev-parse", "HEAD")
    source_commit = _git(ready_repository, "rev-parse", f"{reanchor_commit}^")
    _git(ready_repository, "switch", "-c", "test-valid-target")
    _run_with_values(ready_repository, monkeypatch, (8_007_201, 8_007_202))
    target_commit = _commit(
        ready_repository,
        "test: produce valid post-reanchor target",
        item22.D7_ITEM22_SEED_SUPPLY_DIRECTORY_REPOSITORY_PATH,
    )
    _git(ready_repository, "switch", "-c", "test-target-first", source_commit)
    _git(ready_repository, "cherry-pick", target_commit)
    _git(ready_repository, "switch", "-c", "test-reviewed-lineage", reanchor_commit)
    _git(ready_repository, "merge", "--no-ff", "--no-edit", "test-target-first")
    freeze_commit = _git(ready_repository, "rev-parse", "HEAD")
    authorization_marker = (
        ready_repository
        / item22.D7_ITEM22_DIRECTORY_REPOSITORY_PATH
        / "test-launch-authorization.json"
    )
    authorization_marker.write_bytes(canonical_json_bytes({"authorized": True}))
    authorization_commit = _commit(
        ready_repository,
        "test: authorize sibling-history freeze",
        authorization_marker.relative_to(ready_repository).as_posix(),
    )
    freeze = _matching_freeze(
        ready_repository,
        freeze_commit=freeze_commit,
        authorization_commit=authorization_commit,
    )
    freeze_path = ready_repository / item22.D7_ITEM22_FULL_DESIGN_FREEZE_REPOSITORY_PATH
    freeze_path.write_bytes(freeze.canonical_bytes)
    _commit(
        ready_repository,
        "test: commit sibling-history freeze receipt",
        item22.D7_ITEM22_FULL_DESIGN_FREEZE_REPOSITORY_PATH,
    )

    with pytest.raises(QualificationContractError, match="ancestry"):
        item22.observe_d7_item22_seed_supply_state(ready_repository)


@pytest.mark.parametrize("commit_drift", [False, True])
def test_reanchor_drift_is_rejected_before_claim_or_supplier_entry(
    ready_repository: Path,
    monkeypatch: pytest.MonkeyPatch,
    commit_drift: bool,
) -> None:
    source = ready_repository / MODULE_PATH
    source.write_text(source.read_text() + "\n# post-reanchor drift\n")
    if commit_drift:
        _commit(ready_repository, "post reanchor source drift", MODULE_PATH)
    monkeypatch.setattr(item22.secrets, "randbits", lambda _bits: pytest.fail("drift entered supplier"))

    with pytest.raises(QualificationContractError):
        item22.run_d7_item22_seed_supply_transaction_no_replace(ready_repository)
    assert not (ready_repository / item22.D7_ITEM22_EXCLUSIVE_SEED_SUPPLY_CLAIM_REPOSITORY_PATH).exists()
    assert item22.observe_d7_item22_seed_supply_state(ready_repository) == "preclaim"


def test_fixed_supplier_rejects_excluded_and_duplicate_draws(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    excluded = authority.D7DevelopmentSeedExclusionRegistryRecord.exact().entries[0].seed
    monkeypatch.setattr(item22.secrets, "randbits", _sequence_supplier(iter((excluded, 8_005_001, 8_005_001, 8_005_002))))
    assert item22._supply_official_seed_values() == (8_005_001, 8_005_002)


def test_unknown_transaction_member_and_bare_launch_file_fail_closed(
    ready_repository: Path,
) -> None:
    transaction = ready_repository / item22.D7_ITEM22_SEED_SUPPLY_DIRECTORY_REPOSITORY_PATH
    transaction.mkdir()
    (transaction / "surprise.json").write_bytes(canonical_json_bytes({"surprise": True}))
    with pytest.raises(QualificationContractError, match="unknown members"):
        item22.observe_d7_item22_seed_supply_state(ready_repository)
    shutil.rmtree(transaction)

    launch = ready_repository / item22.D7_ITEM22_FUTURE_LAUNCH_DESCRIPTOR_REPOSITORY_PATH
    launch.write_bytes(canonical_json_bytes({"launch_intent": True}))
    with pytest.raises(QualificationContractError, match="presence state is invalid"):
        item22.observe_d7_item22_seed_supply_state(ready_repository)


def test_observer_rejects_a_symlinked_experiment_ancestor(
    ready_repository: Path,
    tmp_path: Path,
) -> None:
    experiment = ready_repository / item22.D7_ITEM22_DIRECTORY_REPOSITORY_PATH
    external = tmp_path / "external-experiment"
    shutil.copytree(experiment, external)
    experiment.rename(tmp_path / "original-experiment")
    experiment.symlink_to(external, target_is_directory=True)

    with pytest.raises(QualificationContractError, match="symbolic-link|alias"):
        item22.observe_d7_item22_seed_supply_state(ready_repository)


def test_claim_rejoin_rejects_an_ancestor_swap_before_supplier_entry(
    fast_repository: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ready_repository = fast_repository
    experiment = ready_repository / item22.D7_ITEM22_DIRECTORY_REPOSITORY_PATH
    external = tmp_path / "external-experiment"
    original = tmp_path / "original-experiment"
    original_write = item22.durable._write_canonical_file_no_replace
    swapped = False

    def write_then_swap(anchor: object, leaf: str, source: bytes, **kwargs: object):
        nonlocal swapped
        identity = original_write(anchor, leaf, source, **kwargs)
        if leaf == "exclusive-seed-supply-claim.json" and not swapped:
            shutil.copytree(experiment, external)
            experiment.rename(original)
            experiment.symlink_to(external, target_is_directory=True)
            swapped = True
        return identity

    monkeypatch.setattr(
        item22.durable,
        "_write_canonical_file_no_replace",
        write_then_swap,
    )
    monkeypatch.setattr(
        item22.secrets,
        "randbits",
        lambda _bits: pytest.fail("ancestor swap entered supplier"),
    )
    with pytest.raises(QualificationContractError, match="identity changed"):
        item22.run_d7_item22_seed_supply_transaction_no_replace(ready_repository)

    assert (external / "item22-seed-supply/exclusive-seed-supply-claim.json").is_file()
    assert (original / "item22-seed-supply/exclusive-seed-supply-claim.json").is_file()


def test_claim_rejoin_rejects_a_same_byte_leaf_inode_replacement(
    fast_repository: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ready_repository = fast_repository
    original_write = item22.durable._write_canonical_file_no_replace
    replaced = False

    def write_then_replace(
        anchor: item22.durable._DirectoryAnchor,
        leaf: str,
        source: bytes,
        **kwargs: object,
    ):
        nonlocal replaced
        identity = original_write(anchor, leaf, source, **kwargs)
        if leaf == "exclusive-seed-supply-claim.json" and not replaced:
            replacement = anchor.path / ".same-byte-claim"
            replacement.write_bytes(source)
            os.replace(replacement, anchor.path / leaf)
            replaced = True
            assert (anchor.path / leaf).read_bytes() == source
            assert ((anchor.path / leaf).stat().st_dev, (anchor.path / leaf).stat().st_ino) != (
                identity.device,
                identity.inode,
            )
        return identity

    monkeypatch.setattr(item22.durable, "_write_canonical_file_no_replace", write_then_replace)
    monkeypatch.setattr(
        item22.secrets,
        "randbits",
        lambda _bits: pytest.fail("same-byte claim replacement entered supplier"),
    )
    with pytest.raises(QualificationContractError, match="claim identity or bytes differ"):
        item22.run_d7_item22_seed_supply_transaction_no_replace(ready_repository)
    assert item22.observe_d7_item22_seed_supply_state(ready_repository) == "claim-present-publication-absent-nonretryable"
