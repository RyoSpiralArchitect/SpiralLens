from __future__ import annotations

import ast
import runpy
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


REPOSITORY = Path(__file__).resolve().parents[1]
PREPARER = REPOSITORY / "scripts" / "prepare_d7_item24_launch.py"
RUNNER = REPOSITORY / "scripts" / "run_d7_item24.py"


def _call_names(path: Path) -> tuple[str, ...]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    result: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Name):
            result.append(node.func.id)
        elif isinstance(node.func, ast.Attribute):
            result.append(node.func.attr)
    return tuple(result)


def _file_identity(path: Path) -> tuple[int, int, int, int, int]:
    observed = path.lstat()
    return (
        observed.st_dev,
        observed.st_ino,
        observed.st_mode,
        observed.st_size,
        observed.st_mtime_ns,
    )


@pytest.fixture(scope="module")
def preparer_module() -> dict[str, object]:
    return runpy.run_path(str(PREPARER), run_name="d7_item24_preparer_test")


def _dummy_material(
    preparer: dict[str, object],
    physical: object | None = None,
) -> object:
    item22 = preparer["item22"]
    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(
            item22,
            "observe_d7_item22_seed_supply_state",
            lambda _root: "full-design-frozen",
        )
        frozen = preparer["_load_frozen_item22_inputs"](REPOSITORY)  # type: ignore[operator]
    authority = preparer["authority"]
    binding = preparer["_binding"]
    execution = authority.D7ExecutionIdentityInputRecord(
        execution_identity_id="test-item24-execution-identity-v0-1",
        source_runtime_closure_binding=binding(
            "execution-source-runtime-closure",
            frozen.source_runtime_closure,
        ),
        runtime_specification_binding=binding(
            "runtime-specification",
            frozen.runtime_specification,
        ),
        executable_sha256="1" * 64,
        callable_identity_sha256="2" * 64,
        process_identity_sha256="3" * 64,
    )
    attempts = preparer["attempt_records"]
    attempt_key = attempts.d7_attempt_key_sha256(
        replay_target_sha256=frozen.replay_target.canonical_sha256,
        attempt_role=attempts.D7AttemptRole.PRIMARY_CONFIRMATION,
    )
    if physical is None:
        physical = authority.D7PhysicalStoreLaneIdentityRecord(
            physical_identity_id="test-item24-physical-identity-v0-1",
            attempt_key_sha256=attempt_key,
            store_path="/var/tmp/spirallens-d7-item24-test",
            store_device=101,
            store_inode=202,
            lane_path=("/var/tmp/spirallens-d7-item24-test/d7-authoritative-start-v0"),
            lane_device=101,
            lane_inode=303,
            lane_parent_device=101,
            lane_parent_inode=202,
            output_namespace_path=(
                "/var/tmp/spirallens-d7-item24-test/d7-official-output-v0-1"
            ),
            output_parent_device=101,
            output_parent_inode=202,
            terminal_path=(
                "/var/tmp/spirallens-d7-item24-test/d7-official-terminal-v0-1"
            ),
            terminal_parent_device=101,
            terminal_parent_inode=202,
        )
    return preparer["_build_launch_material"](  # type: ignore[operator]
        frozen,
        execution,
        physical,
    )


def _materialize_reused_members(root: Path, material: object) -> None:
    for role, repository_path, source in material.member_sources:
        if role not in {"replay-target", "full-design-freeze"}:
            continue
        destination = root / repository_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(source)


def test_preparer_never_enters_the_producer_or_fused_start() -> None:
    calls = _call_names(PREPARER)

    for forbidden in (
        "produce_d7_official_result",
        "run_d7_fused_verify_start_and_terminal_no_replace",
        "_execute_official_context",
        "_load_official_producer_context",
        "_execute_d7_seed_slot_primary_runtime",
        "generate",
        "persist_d7_authoritative_start_transaction_no_replace",
        "persist_d7_prepared_terminal_no_replace",
        "_supply_official_seed_values",
        "_publish_target",
    ):
        assert forbidden not in calls
    assert calls.count("_publish_launch_members") == 1
    assert calls.count("_promote_physical_store") == 1
    assert calls.count("_publish_launch_descriptor") == 1
    assert calls.count("_create_physical_store") == 1
    source = PREPARER.read_text(encoding="utf-8")
    for forbidden_option in (
        "--descriptor-output",
        "--replay-target",
        "--freeze",
        "--source-root",
        "--runtime-lock",
        "--producer",
        "--seed",
    ):
        assert forbidden_option not in source


def test_runner_gives_the_bare_official_producer_to_one_fused_call() -> None:
    tree = ast.parse(RUNNER.read_text(encoding="utf-8"), filename=str(RUNNER))
    fused_calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "run_d7_fused_verify_start_and_terminal_no_replace"
    ]
    direct_producer_calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "produce_d7_official_result"
    ]

    assert len(fused_calls) == 1
    assert len(fused_calls[0].args) == 2
    producer = fused_calls[0].args[1]
    assert isinstance(producer, ast.Attribute)
    assert producer.attr == "produce_d7_official_result"
    assert direct_producer_calls == []
    source = RUNNER.read_text(encoding="utf-8")
    for forbidden_option in (
        "--descriptor",
        "--store",
        "--seed",
        "--target",
        "--freeze",
        "--runtime",
        "--callback",
    ):
        assert forbidden_option not in source


def test_runner_dispatches_once_without_entering_the_producer(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = runpy.run_path(str(RUNNER), run_name="d7_item24_runner_test")
    calls: list[tuple[object, object]] = []
    producer_calls = 0

    def producer() -> object:
        nonlocal producer_calls
        producer_calls += 1
        raise AssertionError("the dispatch test must not enter the producer")

    terminal = SimpleNamespace(
        atomic_no_replace=True,
        created_by_call=True,
        parent_directory_fsync_proved=True,
        path=Path("/var/tmp/spirallens-d7-terminal"),
        terminal_artifact_kind=SimpleNamespace(value="result"),
        terminal_artifact_sha256="1" * 64,
        terminal_consumption_sha256="2" * 64,
        terminal_manifest_sha256="3" * 64,
    )

    def fused(descriptor: object, callback: object) -> object:
        calls.append((descriptor, callback))
        return terminal

    with monkeypatch.context() as context:
        context.setattr(
            module["official"],
            "produce_d7_official_result",
            producer,
        )
        context.setattr(
            module["fused_start"],
            "run_d7_fused_verify_start_and_terminal_no_replace",
            fused,
        )
        context.setattr(sys, "argv", [str(RUNNER.resolve())])
        assert module["main"]() == 0  # type: ignore[operator]

    assert calls == [
        (
            REPOSITORY
            / module["official"].D7_OFFICIAL_FUSED_DESCRIPTOR_REPOSITORY_PATH,
            producer,
        )
    ]
    assert producer_calls == 0
    assert '"terminal_artifact_kind":"result"' in capsys.readouterr().out


def test_script_bootstraps_restore_the_original_import_path() -> None:
    before = tuple(sys.path)

    runpy.run_path(str(PREPARER), run_name="d7_item24_preparer_path_test")
    assert tuple(sys.path) == before
    runpy.run_path(str(RUNNER), run_name="d7_item24_runner_path_test")
    assert tuple(sys.path) == before


def test_launch_material_is_closed_all_false_and_reuses_frozen_members(
    preparer_module: dict[str, object],
) -> None:
    material = _dummy_material(preparer_module)
    roles = tuple(item.artifact_role for item in material.descriptor.inventory)
    paths = {
        item.artifact_role: item.repository_path
        for item in material.descriptor.inventory
    }

    assert roles == (
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
    assert paths["replay-target"].endswith(
        "/item22-seed-supply/published-target/replay-target.json"
    )
    assert paths["full-design-freeze"].endswith(
        "/item22-seed-supply/full-design-freeze.json"
    )
    assert paths["launch-intent"].endswith("/launch-members/launch-intent.json")
    assert material.descriptor.descriptor_repository_path.endswith("/launch.json")
    descriptor_document = material.descriptor.to_dict()
    for key in (
        "authority_authenticated",
        "repository_trust_root_authenticated",
        "launch_authorized",
        "execution_authorized",
        "scientific_claim_eligible",
        "reusable_authorization_capability_present",
    ):
        assert descriptor_document[key] is False
    assert not any(material.bundle.to_dict()["authority"].values())
    assert material.bundle.launch_intent.to_dict()["launch_authorized"] is False


def test_item24_scripts_remain_outside_frozen_execution_source_surface(
    preparer_module: dict[str, object],
) -> None:
    fused_start = preparer_module["fused_start"]

    official_paths = {
        PREPARER.relative_to(REPOSITORY).as_posix(),
        RUNNER.relative_to(REPOSITORY).as_posix(),
    }
    assert official_paths.isdisjoint(fused_start._SOURCE_PATHS)
    assert fused_start._REPOSITORY_ONLY_SOURCE_PATHS == (
        "experiments/qualification/d7_spectral_moment_confirmation_v0_1/"
        "post_d6_code/_post_d6_outputs_01_12.py",
        "experiments/qualification/d7_spectral_moment_confirmation_v0_1/"
        "post_d6_code/_post_d6_outputs_13_27.py",
        "experiments/qualification/d7_spectral_moment_confirmation_v0_1/"
        "post_d6_code/confirmation_post_d6_descriptive.py",
    )


def test_launch_publication_is_no_replace(
    preparer_module: dict[str, object],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    descriptor_relative = Path(
        preparer_module["LAUNCH_DESCRIPTOR_REPOSITORY_PATH"]  # type: ignore[arg-type]
    )
    experiment = tmp_path / descriptor_relative.parent
    experiment.mkdir(parents=True)
    store = tmp_path / "external-store"
    staged_store = tmp_path / ".external-store.staging"
    script_globals = preparer_module[  # type: ignore[index]
        "_publish_launch_descriptor"
    ].__globals__
    with monkeypatch.context() as context:
        context.setitem(script_globals, "OFFICIAL_STORE_PATH", store)
        context.setitem(
            script_globals,
            "OFFICIAL_STORE_STAGING_PATH",
            staged_store,
        )
        seed_material = _dummy_material(preparer_module)
        staged = preparer_module["_create_physical_store"](  # type: ignore[operator]
            seed_material.bundle.replay_target
        )
        material = _dummy_material(preparer_module, staged.record)
        _materialize_reused_members(tmp_path, material)
        preparer_module["_publish_launch_members"](  # type: ignore[operator]
            tmp_path,
            material,
        )
        promoted = preparer_module["_promote_physical_store"](  # type: ignore[operator]
            staged
        )
        preparer_module["_publish_launch_descriptor"](  # type: ignore[operator]
            tmp_path,
            material,
            promoted,
        )
        descriptor = tmp_path / descriptor_relative
        member_directory = tmp_path / Path(
            preparer_module[  # type: ignore[arg-type]
                "LAUNCH_MEMBER_DIRECTORY_REPOSITORY_PATH"
            ]
        )
        original_descriptor = (_file_identity(descriptor), descriptor.read_bytes())
        original_members = {
            path.name: (_file_identity(path), path.read_bytes())
            for path in member_directory.iterdir()
        }
        contract_error = preparer_module["QualificationContractError"]
        with pytest.raises(contract_error):  # type: ignore[arg-type]
            preparer_module["_publish_launch_members"](  # type: ignore[operator]
                tmp_path,
                material,
            )
        with pytest.raises(contract_error):  # type: ignore[arg-type]
            preparer_module["_publish_launch_descriptor"](  # type: ignore[operator]
                tmp_path,
                material,
                promoted,
            )
        assert original_descriptor == (
            _file_identity(descriptor),
            descriptor.read_bytes(),
        )
        assert original_members == {
            path.name: (_file_identity(path), path.read_bytes())
            for path in member_directory.iterdir()
        }
        assert not (
            experiment / preparer_module["_STAGING_DIRECTORY_BASENAME"]
        ).exists()

    assert descriptor.read_bytes() == material.descriptor.canonical_bytes
    assert set(path.name for path in member_directory.iterdir()) == {
        filename for filename, _source in material.new_member_sources
    }
    with pytest.raises(contract_error):  # type: ignore[arg-type]
        preparer_module["_require_absent_launch_outputs"](tmp_path)  # type: ignore[operator]


def test_physical_store_is_staged_then_exclusively_promoted(
    preparer_module: dict[str, object],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    material = _dummy_material(preparer_module)
    store = tmp_path / "fixed-store"
    staged_store = tmp_path / ".fixed-store.staging"
    create = preparer_module["_create_physical_store"]
    script_globals = create.__globals__  # type: ignore[attr-defined]
    with monkeypatch.context() as context:
        context.setitem(script_globals, "OFFICIAL_STORE_PATH", store)
        context.setitem(script_globals, "OFFICIAL_STORE_STAGING_PATH", staged_store)
        staged = create(material.bundle.replay_target)  # type: ignore[operator]

        assert staged_store.is_dir()
        assert not store.exists()
        assert (
            preparer_module["classify_d7_item24_preparation_state"](tmp_path)  # type: ignore[operator]
            == "external-store-staged"
        )
        promoted = preparer_module["_promote_physical_store"](  # type: ignore[operator]
            staged
        )

        lane = store / "d7-authoritative-start-v0"
        assert store.is_dir()
        assert lane.is_dir()
        assert list(lane.iterdir()) == []
        assert not staged_store.exists()
        assert _file_identity(store)[:2] == (
            staged.record.store_device,
            staged.record.store_inode,
        )
        assert _file_identity(lane)[:2] == (
            staged.record.lane_device,
            staged.record.lane_inode,
        )
        material = _dummy_material(preparer_module, staged.record)
        preparer_module["_verify_promoted_physical_store"](  # type: ignore[operator]
            material,
            promoted,
        )
        preparer_module["_close_promoted_physical_store"](  # type: ignore[operator]
            promoted
        )


def test_descriptor_rejects_store_material_mismatch(
    preparer_module: dict[str, object],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    descriptor_relative = Path(
        preparer_module["LAUNCH_DESCRIPTOR_REPOSITORY_PATH"]  # type: ignore[arg-type]
    )
    (tmp_path / descriptor_relative.parent).mkdir(parents=True)
    store = tmp_path / "fixed-store"
    staged_store = tmp_path / ".fixed-store.staging"
    create = preparer_module["_create_physical_store"]
    script_globals = create.__globals__  # type: ignore[attr-defined]
    with monkeypatch.context() as context:
        context.setitem(script_globals, "OFFICIAL_STORE_PATH", store)
        context.setitem(script_globals, "OFFICIAL_STORE_STAGING_PATH", staged_store)
        mismatched_material = _dummy_material(preparer_module)
        _materialize_reused_members(tmp_path, mismatched_material)
        staged = create(  # type: ignore[operator]
            mismatched_material.bundle.replay_target
        )
        preparer_module["_publish_launch_members"](  # type: ignore[operator]
            tmp_path,
            mismatched_material,
        )
        promoted = preparer_module["_promote_physical_store"](  # type: ignore[operator]
            staged
        )
        contract_error = preparer_module["QualificationContractError"]
        with pytest.raises(contract_error, match="differs from launch material"):  # type: ignore[arg-type]
            preparer_module["_publish_launch_descriptor"](  # type: ignore[operator]
                tmp_path,
                mismatched_material,
                promoted,
            )

    assert not (tmp_path / descriptor_relative).exists()


def test_descriptor_rejects_replaced_member_and_consumes_witness(
    preparer_module: dict[str, object],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    descriptor_relative = Path(
        preparer_module["LAUNCH_DESCRIPTOR_REPOSITORY_PATH"]  # type: ignore[arg-type]
    )
    (tmp_path / descriptor_relative.parent).mkdir(parents=True)
    store = tmp_path / "fixed-store"
    staged_store = tmp_path / ".fixed-store.staging"
    create = preparer_module["_create_physical_store"]
    script_globals = create.__globals__  # type: ignore[attr-defined]
    with monkeypatch.context() as context:
        context.setitem(script_globals, "OFFICIAL_STORE_PATH", store)
        context.setitem(script_globals, "OFFICIAL_STORE_STAGING_PATH", staged_store)
        seed_material = _dummy_material(preparer_module)
        staged = create(seed_material.bundle.replay_target)  # type: ignore[operator]
        material = _dummy_material(preparer_module, staged.record)
        _materialize_reused_members(tmp_path, material)
        preparer_module["_publish_launch_members"](  # type: ignore[operator]
            tmp_path,
            material,
        )
        member = (
            tmp_path
            / preparer_module[  # type: ignore[arg-type]
                "LAUNCH_MEMBER_DIRECTORY_REPOSITORY_PATH"
            ]
            / "launch-intent.json"
        )
        member.write_bytes(b"{}")
        promoted = preparer_module["_promote_physical_store"](  # type: ignore[operator]
            staged
        )
        contract_error = preparer_module["QualificationContractError"]
        with pytest.raises(contract_error, match="source SHA-256 differs"):  # type: ignore[arg-type]
            preparer_module["_publish_launch_descriptor"](  # type: ignore[operator]
                tmp_path,
                material,
                promoted,
            )
        assert promoted._consumed is True
        preparer_module["_close_promoted_physical_store"](  # type: ignore[operator]
            promoted
        )

    assert not (tmp_path / descriptor_relative).exists()


def test_promoted_witness_close_attempts_every_descriptor_after_error(
    preparer_module: dict[str, object],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    material = _dummy_material(preparer_module)
    store = tmp_path / "fixed-store"
    staged_store = tmp_path / ".fixed-store.staging"
    create = preparer_module["_create_physical_store"]
    script_globals = create.__globals__  # type: ignore[attr-defined]
    with monkeypatch.context() as context:
        context.setitem(script_globals, "OFFICIAL_STORE_PATH", store)
        context.setitem(script_globals, "OFFICIAL_STORE_STAGING_PATH", staged_store)
        staged = create(material.bundle.replay_target)  # type: ignore[operator]
        promoted = preparer_module["_promote_physical_store"](  # type: ignore[operator]
            staged
        )
        descriptors = (
            promoted.lane.descriptor,
            promoted.store.descriptor,
            promoted.parent.descriptor,
        )
        original_close = script_globals["os"].close
        attempted: list[int] = []

        def close_then_report_first_error(descriptor: int) -> None:
            original_close(descriptor)
            attempted.append(descriptor)
            if descriptor == descriptors[0]:
                raise OSError("injected close report")

        context.setattr(script_globals["os"], "close", close_then_report_first_error)
        contract_error = preparer_module["QualificationContractError"]
        with pytest.raises(contract_error, match="cannot close every"):  # type: ignore[arg-type]
            preparer_module["_close_promoted_physical_store"](  # type: ignore[operator]
                promoted
            )

    assert attempted == list(descriptors)
    assert promoted._consumed is True
    for descriptor in descriptors:
        with pytest.raises(OSError):
            script_globals["os"].fstat(descriptor)
    preparer_module["_close_promoted_physical_store"](promoted)  # type: ignore[operator]


def test_descriptor_temporary_file_is_an_invalid_partial_state(
    preparer_module: dict[str, object],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    descriptor_relative = Path(
        preparer_module["LAUNCH_DESCRIPTOR_REPOSITORY_PATH"]  # type: ignore[arg-type]
    )
    experiment = tmp_path / descriptor_relative.parent
    experiment.mkdir(parents=True)
    temporary = experiment / f".{descriptor_relative.name}.0123456789abcdef.tmp"
    temporary.write_bytes(b"incomplete")
    classifier = preparer_module["classify_d7_item24_preparation_state"]
    script_globals = classifier.__globals__  # type: ignore[attr-defined]
    with monkeypatch.context() as context:
        context.setitem(
            script_globals,
            "OFFICIAL_STORE_PATH",
            tmp_path / "fixed-store",
        )
        context.setitem(
            script_globals,
            "OFFICIAL_STORE_STAGING_PATH",
            tmp_path / ".fixed-store.staging",
        )
        assert classifier(tmp_path) == "invalid-partial-state"  # type: ignore[operator]
        contract_error = preparer_module["QualificationContractError"]
        with pytest.raises(contract_error, match="temporary file"):  # type: ignore[arg-type]
            preparer_module["_require_absent_launch_outputs"](  # type: ignore[operator]
                tmp_path
            )


def test_runner_rejects_wrong_cwd_and_argv(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = runpy.run_path(str(RUNNER), run_name="d7_item24_envelope_test")
    with monkeypatch.context() as context:
        context.chdir(tmp_path)
        context.setattr(sys, "argv", [str(RUNNER.resolve())])
        with pytest.raises(RuntimeError, match="exact repository cwd"):
            module["_require_exact_process_envelope"]()  # type: ignore[operator]
    with monkeypatch.context() as context:
        context.setattr(sys, "argv", ["run_d7_item24.py"])
        with pytest.raises(RuntimeError, match="alternate argv"):
            module["_require_exact_process_envelope"]()  # type: ignore[operator]


def test_preparer_help_has_no_external_store_side_effect(
    preparer_module: dict[str, object],
) -> None:
    store = preparer_module["OFFICIAL_STORE_PATH"]
    before = store.lstat() if store.exists() or store.is_symlink() else None

    completed = subprocess.run(
        [sys.executable, str(PREPARER), "--help"],
        cwd=REPOSITORY,
        check=False,
        capture_output=True,
        text=True,
    )

    after = store.lstat() if store.exists() or store.is_symlink() else None
    assert completed.returncode == 0, completed.stderr
    assert "usage:" in completed.stdout
    assert before == after
