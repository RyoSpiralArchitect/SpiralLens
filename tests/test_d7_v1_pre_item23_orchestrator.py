from __future__ import annotations

import ast
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
import importlib.util
import inspect
import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import sys
from types import FunctionType, ModuleType

import pytest

import spirallens
import spirallens.qualification as qualification
from spirallens.core.canonical import sha256_bytes
from spirallens.qualification import (
    confirmation_v1_deterministic_inputs as deterministic_inputs,
)
from spirallens.qualification import (
    confirmation_v1_materialization as materialization,
)
from spirallens.qualification import (
    confirmation_v1_pre_item23_orchestrator as orchestrator,
)
from spirallens.qualification import (
    confirmation_v1_private_publication as private_publication,
)
from spirallens.qualification import confirmation_v1_records as records
from spirallens.qualification import (
    confirmation_v1_source_selected_supplier as selected_supplier,
)
from spirallens.qualification.common import QualificationContractError


REPOSITORY = Path(__file__).resolve().parents[1]
MODULE_REPOSITORY_PATH = (
    "src/spirallens/qualification/confirmation_v1_pre_item23_orchestrator.py"
)
MODULE_PATH = REPOSITORY.joinpath(*MODULE_REPOSITORY_PATH.split("/"))
PREPARER_PATH = REPOSITORY / "scripts/prepare_d7_v1_launch.py"
DETERMINISTIC_INPUTS_REPOSITORY_PATH = (
    "src/spirallens/qualification/confirmation_v1_deterministic_inputs.py"
)
OFFICIAL_STAGE = Path("/Users/ryohiga/SpiralReality/.spirallens-d7-v1-store.staging")
OFFICIAL_STORE = Path("/Users/ryohiga/SpiralReality/spirallens-d7-v1-store")


def _load_materialization_helpers() -> ModuleType:
    name = "_spirallens_pr57_materialization_test_helpers"
    existing = sys.modules.get(name)
    if existing is not None:
        return existing
    path = REPOSITORY / "tests/test_d7_v1_materialization.py"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AssertionError("cannot load D7 v1 materialization test helpers")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        sys.modules.pop(name, None)
        raise
    return module


def _run(repository: Path, *arguments: str) -> str:
    return subprocess.run(
        ("git", "-C", str(repository), *arguments),
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


@pytest.fixture(scope="module")
def case(tmp_path_factory: pytest.TempPathFactory) -> Iterator[object]:
    """One clean disposable S shared by tests that do not publish until last."""

    root = tmp_path_factory.mktemp("d7-v1-pre-item23-orchestrator")
    helpers = _load_materialization_helpers()
    value = helpers._build_case(
        root / "case",
        isolated_clone=True,
        sparse_checkout=False,
    )
    target = value.repository.joinpath(*MODULE_REPOSITORY_PATH.split("/"))
    target.parent.mkdir(parents=True, exist_ok=True)
    target.unlink(missing_ok=True)
    os.link(MODULE_PATH, target)
    deterministic_target = value.repository.joinpath(
        *DETERMINISTIC_INPUTS_REPOSITORY_PATH.split("/")
    )
    deterministic_target.unlink(missing_ok=True)
    assert deterministic_inputs.__file__ is not None
    os.link(deterministic_inputs.__file__, deterministic_target)
    preparer_target = value.repository / "scripts/prepare_d7_v1_launch.py"
    preparer_target.unlink(missing_ok=True)
    os.link(PREPARER_PATH, preparer_target)
    _run(
        value.repository,
        "add",
        MODULE_REPOSITORY_PATH,
        DETERMINISTIC_INPUTS_REPOSITORY_PATH,
        "scripts/prepare_d7_v1_launch.py",
    )
    _run(
        value.repository,
        "commit",
        "--quiet",
        "--allow-empty",
        "-m",
        "test pre-item23 orchestrator source S",
    )
    value.source_commit = _run(value.repository, "rev-parse", "HEAD")
    assert _run(value.repository, "status", "--porcelain=v1", "-z") == ""
    try:
        yield value
    finally:
        loaded = sys.modules.get(
            "spirallens.qualification.confirmation_v1_design_referent_documents"
        )
        authenticated = getattr(
            sys.modules.get(
                "spirallens.qualification.confirmation_v1_full_design_referents"
            ),
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
        shutil.rmtree(root, ignore_errors=True)


def _path_state(path: Path) -> tuple[bool, int | None, int | None, int | None]:
    try:
        observed = path.lstat()
    except FileNotFoundError:
        return False, None, None, None
    return True, observed.st_mode, observed.st_size, observed.st_mtime_ns


@contextmanager
def _external_sandbox(
    root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[tuple[Path, Path, Path]]:
    """Redirect only closed low-level I/O; record coordinates stay frozen."""

    parent = root / "external-parent"
    parent.mkdir(parents=True)
    physical_stage = parent / OFFICIAL_STAGE.name
    physical_store = parent / OFFICIAL_STORE.name
    real_reader = materialization._default_external_reader

    def open_parent(_coordinates: object) -> int:
        return os.open(parent, private_publication._directory_open_flags())

    def open_live_parent(
        _evidence: private_publication._D7V1AnchoredExternalEvidence,
    ) -> int:
        return os.open(parent, private_publication._directory_open_flags())

    def external_reader(path: Path, maximum_bytes: int) -> bytes:
        try:
            path.relative_to(OFFICIAL_STORE)
        except ValueError:
            return real_reader(path, maximum_bytes)
        raise AssertionError(
            "closed orchestrator and publisher must use sealed external evidence"
        )

    with monkeypatch.context() as scoped:
        scoped.setattr(orchestrator, "_open_external_parent", open_parent)
        scoped.setattr(
            private_publication._D7V1AnchoredExternalEvidence,
            "_open_live_parent",
            open_live_parent,
        )
        scoped.setattr(materialization, "_default_external_reader", external_reader)
        yield parent, physical_stage, physical_store


def _replacement_supplier(
    values: tuple[int, int],
    calls: list[tuple[int, int]],
) -> FunctionType:
    namespace: dict[str, object] = {
        "__name__": selected_supplier.__name__,
        "_test_values": values,
        "_test_calls": calls,
    }
    exec(
        "def _supply_d7_v1_official_seed_values():\n"
        "    _test_calls.append(_test_values)\n"
        "    return _test_values\n",
        namespace,
    )
    result = namespace["_supply_d7_v1_official_seed_values"]
    assert type(result) is FunctionType
    return result


def _hooked_supplier(
    values: tuple[int, int],
    calls: list[tuple[int, int]],
    hook: Callable[[], None],
) -> FunctionType:
    namespace: dict[str, object] = {
        "__name__": selected_supplier.__name__,
        "_test_values": values,
        "_test_calls": calls,
        "_test_hook": hook,
    }
    exec(
        "def _supply_d7_v1_official_seed_values():\n"
        "    _test_hook()\n"
        "    _test_calls.append(_test_values)\n"
        "    return _test_values\n",
        namespace,
    )
    result = namespace["_supply_d7_v1_official_seed_values"]
    assert type(result) is FunctionType
    return result


def _observed_supplier(
    callee: FunctionType,
    events: list[str],
) -> FunctionType:
    namespace: dict[str, object] = {
        "__name__": selected_supplier.__name__,
        "_test_callee": callee,
        "_test_events": events,
    }
    exec(
        "def _supply_d7_v1_official_seed_values():\n"
        "    result = _test_callee()\n"
        "    _test_events.append('supplier')\n"
        "    return result\n",
        namespace,
    )
    result = namespace["_supply_d7_v1_official_seed_values"]
    assert type(result) is FunctionType
    return result


def _install_supplier(
    monkeypatch: pytest.MonkeyPatch,
    values: tuple[int, int],
    calls: list[tuple[int, int]],
) -> FunctionType:
    replacement = _replacement_supplier(values, calls)
    monkeypatch.setattr(
        selected_supplier,
        "_supply_d7_v1_official_seed_values",
        replacement,
    )
    monkeypatch.setattr(selected_supplier, "_FIXED_SUPPLIER", replacement)
    return replacement


def _external_files(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def _external_entries(root: Path) -> tuple[tuple[str, str], ...]:
    return tuple(
        (
            path.relative_to(root).as_posix(),
            "directory" if path.is_dir() else "file",
        )
        for path in sorted(root.rglob("*"))
    )


def _promoted_external_evidence(
    case: object,
) -> tuple[
    orchestrator._OwnedExternalStage,
    orchestrator._ExternalCoordinates,
    dict[str, bytes],
    private_publication._D7V1AnchoredExternalEvidence,
]:
    protocol = materialization._protocol_at_commit(case.context, case.source_commit)
    _route_source, route = materialization._route_source(case.context, protocol)
    coordinates = orchestrator._external_coordinates(protocol, route)
    stage = orchestrator._create_external_stage(coordinates)
    claim = case.records_by_role[records.D7V1ExclusiveSeedSupplyClaim.artifact_role]
    attempt = case.records_by_role[
        records.D7V1OfficialExecutionAttemptReservation.artifact_role
    ]
    durable_claim = orchestrator._persist_external_record(stage, claim)
    durable_attempt = orchestrator._persist_external_record(stage, attempt)
    sources = {
        durable_claim.artifact_role: durable_claim.canonical_bytes,
        durable_attempt.artifact_role: durable_attempt.canonical_bytes,
    }
    orchestrator._promote_external_store_no_replace(stage, sources)
    evidence = private_publication._build_d7_v1_anchored_external_evidence(
        case.context,
        parent_fd=stage.parent_fd,
        root_fd=stage.root_fd,
        directory_fd_by_path={
            coordinates.store / relative: descriptor
            for relative, descriptor in stage.directory_fds.items()
            if relative
        },
        file_fd_by_path={
            coordinates.store / relative: descriptor
            for relative, descriptor in stage.file_fds.items()
        },
        source_by_path={
            coordinates.store / coordinates.relative_by_role[role]: source
            for role, source in sources.items()
        },
    )
    return stage, coordinates, sources, evidence


def _swap_external_namespace(
    attack: str,
    parent: Path,
    physical_store: Path,
    evidence: private_publication._D7V1AnchoredExternalEvidence,
) -> None:
    if attack == "ancestor":
        held = parent.with_name(f"{parent.name}.held")
        parent.rename(held)
        shutil.copytree(held, parent)
        return
    if attack == "store":
        held = parent / f".{physical_store.name}.held"
        physical_store.rename(held)
        shutil.copytree(held, physical_store)
        return

    role = (
        records.D7V1ExclusiveSeedSupplyClaim.artifact_role
        if attack.startswith("claim-")
        else records.D7V1OfficialExecutionAttemptReservation.artifact_role
    )
    official = next(
        path
        for path in evidence.source_by_path
        if materialization._ROLE_CLASSES[role].artifact_role in str(path)
        or (
            role == records.D7V1ExclusiveSeedSupplyClaim.artifact_role
            and "exclusive-seed-supply-claim" in path.name
        )
        or (
            role == records.D7V1OfficialExecutionAttemptReservation.artifact_role
            and "official-execution-attempt-reservation" in path.name
        )
    )
    relative = official.relative_to(evidence.store_path)
    physical_file = physical_store / relative
    physical_directory = physical_file.parent
    if attack.endswith("directory"):
        held = parent / f".{physical_directory.name}.held"
        physical_directory.rename(held)
        shutil.copytree(held, physical_directory)
        os.utime(
            physical_store,
            ns=(physical_store.stat().st_atime_ns, evidence.root_stat[2]),
        )
        return

    held = parent / f".{physical_directory.name}-{physical_file.name}.held"
    physical_file.rename(held)
    shutil.copy2(held, physical_file)
    os.chmod(physical_file, 0o600)
    official_directory = official.parent
    os.utime(
        physical_directory,
        ns=(
            physical_directory.stat().st_atime_ns,
            evidence.directory_stat_by_path[official_directory][2],
        ),
    )


def test_private_surface_import_is_inert_and_preparer_stays_unwired() -> None:
    signature = inspect.signature(orchestrator._materialize_d7_v1_pre_item23_no_replace)
    assert tuple(signature.parameters) == ("repository", "source_commit")
    assert signature.parameters["source_commit"].kind is inspect.Parameter.KEYWORD_ONLY
    assert orchestrator.__all__ == ()
    assert "_materialize_d7_v1_pre_item23_no_replace" not in spirallens.__all__
    assert "_materialize_d7_v1_pre_item23_no_replace" not in qualification.__all__
    assert not hasattr(qualification, "_materialize_d7_v1_pre_item23_no_replace")

    publisher_signature = inspect.signature(
        private_publication._publish_d7_v1_pre_item23_records_no_replace
    )
    assert tuple(publisher_signature.parameters) == (
        "repository",
        "sources_by_role",
        "expected_receipt_sha256",
        "_anchored_external_evidence",
    )
    capability_parameter = publisher_signature.parameters["_anchored_external_evidence"]
    assert capability_parameter.kind is inspect.Parameter.KEYWORD_ONLY
    assert capability_parameter.default is None
    assert "external_reader" not in publisher_signature.parameters
    with pytest.raises(QualificationContractError, match="factory-produced"):
        private_publication._D7V1AnchoredExternalEvidence(
            parent_fd=-1,
            root_fd=-1,
            store_path=OFFICIAL_STORE,
            root_stat=(0, 0, 0),
            source_by_path={},
            directory_fd_by_path={},
            directory_identity_by_path={},
            directory_stat_by_path={},
            file_fd_by_path={},
            file_identity_by_path={},
            file_stat_by_path={},
            _factory_token=None,
        )

    preparer_source = PREPARER_PATH.read_text(encoding="utf-8")
    preparer_tree = ast.parse(preparer_source)
    imported = {
        alias.name
        for node in ast.walk(preparer_tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    assert "confirmation_v1_pre_item23_orchestrator" not in imported
    assert "_materialize_d7_v1_pre_item23_no_replace" not in preparer_source
    assert "source-selection-runtime-closure-and-invocation-authority-absent" in (
        preparer_source
    )

    readme = (REPOSITORY / "README.md").read_text(encoding="utf-8")
    roadmap = (REPOSITORY / "docs/ROADMAP.md").read_text(encoding="utf-8")
    ledger = (REPOSITORY / "docs/EXPERIMENT_INTERPRETATION_LEDGER.md").read_text(
        encoding="utf-8"
    )
    changelog = (REPOSITORY / "docs/SCHEMA_CHANGELOG.md").read_text(encoding="utf-8")
    assert "The complete pre-item-23 chronology is now implemented" in readme
    assert "This source has not been invoked" in readme
    assert "entrypoint remains unwired" in roadmap
    assert "### 3.27 D7 v1 closed pre-item-23 chronology source" in ledger
    assert "source is uninvoked" in ledger
    assert "Private D7 v1 pre-item-23 chronology source" in changelog
    for document in (readme, roadmap, ledger, changelog):
        assert "S remains unreviewed and unselected" in document
        assert "VOY-V3 remains `frozen_not_run`" in document
        assert "D7/D8 remain `not_run`" in document
    assert "Claim delta remains `none`" in readme
    assert "claim delta is `none`" in roadmap
    assert "`none`. The source is uninvoked" in ledger
    assert "Claim delta is\n  `none`" in changelog
    assert "public API, dependency, or library milestone changes" in " ".join(
        ledger.split()
    )
    assert "No instance was created and no schema, protocol, route" in changelog

    before = (_path_state(OFFICIAL_STAGE), _path_state(OFFICIAL_STORE))
    environment = dict(os.environ)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment["PYTHONPATH"] = str(REPOSITORY / "src")
    subprocess.run(
        (
            sys.executable,
            "-c",
            "import spirallens.qualification.confirmation_v1_pre_item23_orchestrator",
        ),
        cwd=REPOSITORY,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )
    assert (_path_state(OFFICIAL_STAGE), _path_state(OFFICIAL_STORE)) == before


def test_wrong_s_and_wrong_orchestrator_origin_reject_before_external_io(
    case: object,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    entered_external = False

    def forbidden_external(_coordinates: object) -> int:
        nonlocal entered_external
        entered_external = True
        raise AssertionError("external chronology must not be entered")

    monkeypatch.setattr(orchestrator, "_open_external_parent", forbidden_external)
    with pytest.raises(
        QualificationContractError, match="exact current repository HEAD"
    ):
        orchestrator._materialize_d7_v1_pre_item23_no_replace(
            case.context,
            source_commit=_run(case.repository, "rev-parse", "HEAD^"),
        )
    assert entered_external is False

    copied = tmp_path / "adjacent-orchestrator.py"
    copied.write_bytes(MODULE_PATH.read_bytes())
    monkeypatch.setattr(orchestrator, "__file__", str(copied))
    with pytest.raises(QualificationContractError, match="import origin differs"):
        orchestrator._materialize_d7_v1_pre_item23_no_replace(
            case.context,
            source_commit=case.source_commit,
        )
    assert entered_external is False


def test_repository_collision_preflight_precedes_supplier_and_external_entry(
    case: object,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    sources = {
        role: case.records_by_role[role].canonical_bytes
        for role in materialization._ROLE_CLASSES
    }
    receipt = case.records_by_role[records.D7V1PreItem23ChronologyReceipt.artifact_role]
    with pytest.raises(TypeError, match="sealed publisher evidence"):
        private_publication._publish_d7_v1_pre_item23_records_no_replace(
            case.context,
            sources,
            expected_receipt_sha256=receipt.canonical_sha256,
            _anchored_external_evidence=object(),
        )

    fake_parent = tmp_path / "repository-parent"
    fake_parent.mkdir()
    (fake_parent / "d7_spectral_moment_confirmation_v1").mkdir()
    supplier_calls: list[tuple[int, int]] = []
    _install_supplier(monkeypatch, (8_100_001, 8_100_002), supplier_calls)
    external_entered = False

    def open_fake_parent(_repository: object, _parts: object) -> int:
        return os.open(fake_parent, private_publication._directory_open_flags())

    def forbidden_external(_coordinates: object) -> int:
        nonlocal external_entered
        external_entered = True
        raise AssertionError("external preflight must follow repository preflight")

    monkeypatch.setattr(
        private_publication,
        "_open_publication_parent",
        open_fake_parent,
    )
    monkeypatch.setattr(orchestrator, "_open_external_parent", forbidden_external)
    with pytest.raises(
        QualificationContractError,
        match="repository destination already exists",
    ):
        orchestrator._materialize_d7_v1_pre_item23_no_replace(
            case.context,
            source_commit=case.source_commit,
        )
    assert supplier_calls == []
    assert external_entered is False


@pytest.mark.parametrize(
    "invalid_values",
    (
        (8_100_001, 8_100_001),
        (8_100_002, 8_100_001),
    ),
)
def test_claim_precedes_captured_supplier_and_invalid_output_is_retained(
    case: object,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    invalid_values: tuple[int, int],
) -> None:
    with _external_sandbox(tmp_path / "captured", monkeypatch) as (
        _parent,
        physical_stage,
        _physical_store,
    ):
        first_calls: list[tuple[int, int]] = []
        second_calls: list[tuple[int, int]] = []

        def assert_claim_only_at_supplier_entry() -> None:
            assert _external_entries(physical_stage) == (
                ("d7-v1-attempt-evidence", "directory"),
                ("d7-v1-prefix-evidence-only", "directory"),
                (
                    "d7-v1-prefix-evidence-only/exclusive-seed-supply-claim.json",
                    "file",
                ),
            )

        first = _hooked_supplier(
            (8_100_001, 8_100_002),
            first_calls,
            assert_claim_only_at_supplier_entry,
        )
        monkeypatch.setattr(
            selected_supplier,
            "_supply_d7_v1_official_seed_values",
            first,
        )
        monkeypatch.setattr(selected_supplier, "_FIXED_SUPPLIER", first)
        second = _replacement_supplier((8_200_001, 8_200_002), second_calls)
        real_persist = orchestrator._persist_external_record

        def persist_then_rebind(stage: object, record: object) -> object:
            durable = real_persist(stage, record)
            if (
                record.artifact_role
                == records.D7V1ExclusiveSeedSupplyClaim.artifact_role
            ):
                monkeypatch.setattr(
                    selected_supplier,
                    "_supply_d7_v1_official_seed_values",
                    second,
                )
                monkeypatch.setattr(selected_supplier, "_FIXED_SUPPLIER", second)
            return durable

        monkeypatch.setattr(
            orchestrator,
            "_persist_external_record",
            persist_then_rebind,
        )
        monkeypatch.setattr(
            orchestrator,
            "_build_post_supplier_records",
            lambda *args, **kwargs: (_ for _ in ()).throw(
                RuntimeError("stop after captured supplier")
            ),
        )
        with pytest.raises(
            orchestrator._D7V1ExternalChronologyFailure,
            match="external_stage_retained",
        ) as caught:
            orchestrator._materialize_d7_v1_pre_item23_no_replace(
                case.context,
                source_commit=case.source_commit,
            )
        assert first_calls == [(8_100_001, 8_100_002)]
        assert second_calls == []
        assert caught.value.retry_authorized is False
        assert caught.value.cleanup_authorized is False
        assert caught.value.resume_authorized is False
        files = _external_files(physical_stage)
        assert tuple(files) == (
            "d7-v1-prefix-evidence-only/exclusive-seed-supply-claim.json",
        )

    with _external_sandbox(tmp_path / "invalid", monkeypatch) as (
        _parent,
        physical_stage,
        _physical_store,
    ):
        calls: list[tuple[int, int]] = []
        _install_supplier(monkeypatch, invalid_values, calls)
        with pytest.raises(
            orchestrator._D7V1ExternalChronologyFailure,
            match="external_stage_retained",
        ) as caught:
            orchestrator._materialize_d7_v1_pre_item23_no_replace(
                case.context,
                source_commit=case.source_commit,
            )
        assert calls == [invalid_values]
        assert caught.value.retry_authorized is False
        assert physical_stage.is_dir()
        assert len(_external_files(physical_stage)) == 1


def test_external_fault_is_retained_and_reentry_preflight_refuses_it(
    case: object,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    with _external_sandbox(tmp_path, monkeypatch) as (
        _parent,
        physical_stage,
        physical_store,
    ):
        calls: list[tuple[int, int]] = []
        _install_supplier(monkeypatch, (8_100_001, 8_100_002), calls)
        monkeypatch.setattr(
            orchestrator,
            "_promote_external_store_no_replace",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(
                OSError("injected pre-promotion fault")
            ),
        )
        with pytest.raises(
            orchestrator._D7V1ExternalChronologyFailure,
            match="external_stage_retained",
        ) as caught:
            orchestrator._materialize_d7_v1_pre_item23_no_replace(
                case.context,
                source_commit=case.source_commit,
            )
        assert calls == [(8_100_001, 8_100_002)]
        assert caught.value.disposition == "external_stage_retained"
        assert caught.value.stage_retained is True
        assert caught.value.store_visible is False
        assert physical_stage.is_dir()
        assert not physical_store.exists()
        assert len(_external_files(physical_stage)) == 2

        with pytest.raises(
            QualificationContractError,
            match="external staging root already exists",
        ):
            orchestrator._materialize_d7_v1_pre_item23_no_replace(
                case.context,
                source_commit=case.source_commit,
            )
        assert calls == [(8_100_001, 8_100_002)]
        assert physical_stage.is_dir()
        assert not physical_store.exists()
        assert len(_external_files(physical_stage)) == 2


def test_post_attempt_source_rejoin_failure_retains_exact_two_file_stage(
    case: object,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    with _external_sandbox(tmp_path, monkeypatch) as (
        _parent,
        physical_stage,
        physical_store,
    ):
        calls: list[tuple[int, int]] = []
        _install_supplier(monkeypatch, (8_100_001, 8_100_002), calls)
        real_rejoin = materialization._verify_source_join
        post_attempt_rejoin_failed = False
        promotion_calls = 0
        publication_calls = 0

        def fail_final_rejoin(*args: object, **kwargs: object) -> str:
            nonlocal post_attempt_rejoin_failed
            if len(_external_files(physical_stage)) == 2:
                post_attempt_rejoin_failed = True
                raise QualificationContractError(
                    "injected post-attempt source rejoin failure"
                )
            return real_rejoin(*args, **kwargs)

        def forbidden_promotion(*_args: object, **_kwargs: object) -> None:
            nonlocal promotion_calls
            promotion_calls += 1
            raise AssertionError("promotion must follow the final source rejoin")

        def forbidden_publication(*_args: object, **_kwargs: object) -> object:
            nonlocal publication_calls
            publication_calls += 1
            raise AssertionError("repository publication must follow promotion")

        monkeypatch.setattr(materialization, "_verify_source_join", fail_final_rejoin)
        monkeypatch.setattr(
            orchestrator,
            "_promote_external_store_no_replace",
            forbidden_promotion,
        )
        monkeypatch.setattr(
            private_publication,
            "_publish_d7_v1_pre_item23_records_no_replace",
            forbidden_publication,
        )
        with pytest.raises(
            orchestrator._D7V1ExternalChronologyFailure,
            match="external_stage_retained",
        ) as caught:
            orchestrator._materialize_d7_v1_pre_item23_no_replace(
                case.context,
                source_commit=case.source_commit,
            )
        assert calls == [(8_100_001, 8_100_002)]
        assert post_attempt_rejoin_failed is True
        assert promotion_calls == 0
        assert publication_calls == 0
        assert caught.value.stage_retained is True
        assert caught.value.store_visible is False
        assert physical_stage.is_dir()
        assert not physical_store.exists()
        assert len(_external_files(physical_stage)) == 2


@pytest.mark.parametrize(
    ("fault", "expected"),
    (
        ("fsync", "external_published_durability_unknown"),
        ("reverify", "external_published_verification_unknown"),
    ),
)
def test_promotion_fsync_and_reverification_have_exact_retained_dispositions(
    case: object,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    fault: str,
    expected: str,
) -> None:
    with _external_sandbox(tmp_path, monkeypatch) as (
        parent,
        physical_stage,
        physical_store,
    ):
        protocol = materialization._protocol_at_commit(case.context, case.source_commit)
        _route_source, route = materialization._route_source(case.context, protocol)
        coordinates = orchestrator._external_coordinates(protocol, route)
        stage = orchestrator._create_external_stage(coordinates)
        claim = case.records_by_role[records.D7V1ExclusiveSeedSupplyClaim.artifact_role]
        attempt = case.records_by_role[
            records.D7V1OfficialExecutionAttemptReservation.artifact_role
        ]
        durable_claim = orchestrator._persist_external_record(stage, claim)
        durable_attempt = orchestrator._persist_external_record(stage, attempt)
        sources = {
            durable_claim.artifact_role: durable_claim.canonical_bytes,
            durable_attempt.artifact_role: durable_attempt.canonical_bytes,
        }
        if fault == "fsync":
            real_fsync = orchestrator.os.fsync
            parent_identity = orchestrator._stat_identity(parent.stat())

            def fail_published_parent_fsync(descriptor: int) -> None:
                if (
                    physical_store.exists()
                    and orchestrator._stat_identity(os.fstat(descriptor))
                    == parent_identity
                ):
                    raise OSError("injected post-rename parent fsync failure")
                real_fsync(descriptor)

            monkeypatch.setattr(orchestrator.os, "fsync", fail_published_parent_fsync)
        else:
            real_reverify = orchestrator._reverify_external_stage

            def fail_promoted_reverification(
                owned: object,
                observed_sources: Mapping[str, bytes],
                *,
                promoted: bool,
            ) -> None:
                if promoted:
                    raise QualificationContractError(
                        "injected promoted-store reverification failure"
                    )
                real_reverify(owned, observed_sources, promoted=promoted)

            monkeypatch.setattr(
                orchestrator,
                "_reverify_external_stage",
                fail_promoted_reverification,
            )
        try:
            with pytest.raises(
                orchestrator._D7V1ExternalChronologyFailure,
                match=expected,
            ) as caught:
                orchestrator._promote_external_store_no_replace(stage, sources)
            assert caught.value.disposition == expected
            assert caught.value.retry_authorized is False
            assert caught.value.cleanup_authorized is False
            assert caught.value.resume_authorized is False
            assert not physical_stage.exists()
            assert physical_store.is_dir()
            assert len(_external_files(physical_store)) == 2
        finally:
            stage.close()


@pytest.mark.parametrize(
    ("attack", "expected"),
    (
        ("ancestor", "live external parent differs"),
        ("store", "live external store differs"),
        ("claim-directory", "evidence directory differs"),
        ("attempt-directory", "evidence directory differs"),
        ("claim-file", "live external evidence file differs"),
        ("attempt-file", "live external evidence file differs"),
    ),
)
def test_sealed_external_evidence_rejects_same_looking_namespace_swaps(
    case: object,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    attack: str,
    expected: str,
) -> None:
    with _external_sandbox(tmp_path, monkeypatch) as (
        parent,
        _physical_stage,
        physical_store,
    ):
        stage, coordinates, sources, evidence = _promoted_external_evidence(case)
        try:
            for path, source in evidence.source_by_path.items():
                assert (
                    evidence.read(path, records.D7_V1_DEFAULT_MAX_RECORD_BYTES)
                    == source
                )
            if attack == "ancestor":
                bad_sources = dict(evidence.source_by_path)
                source = bad_sources.pop(coordinates.claim)
                bad_sources[coordinates.store / "wrong" / "claim.json"] = source
                with pytest.raises(
                    QualificationContractError,
                    match="differs from exact frozen paths",
                ):
                    private_publication._build_d7_v1_anchored_external_evidence(
                        case.context,
                        parent_fd=stage.parent_fd,
                        root_fd=stage.root_fd,
                        directory_fd_by_path=evidence.directory_fd_by_path,
                        file_fd_by_path=evidence.file_fd_by_path,
                        source_by_path=bad_sources,
                    )

            _swap_external_namespace(attack, parent, physical_store, evidence)
            target = coordinates.claim
            with pytest.raises(QualificationContractError, match=expected):
                evidence.read(target, records.D7_V1_DEFAULT_MAX_RECORD_BYTES)

            for role, relative in coordinates.relative_by_role.items():
                assert (
                    orchestrator._read_descriptor(
                        stage.file_fds[relative],
                        maximum_bytes=materialization._ROLE_CLASSES[
                            role
                        ].max_record_bytes,
                    )
                    == sources[role]
                )
        finally:
            stage.close()


@pytest.mark.parametrize("boundary", ("joined", "publisher"))
def test_joined_and_publisher_gates_reject_rebound_external_file(
    case: object,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    boundary: str,
) -> None:
    supplier_calls: list[tuple[int, int]] = []
    captured_descriptors: tuple[int, ...] = ()
    joined_completed = 0
    publisher_calls = 0
    with _external_sandbox(tmp_path, monkeypatch) as (
        parent,
        physical_stage,
        physical_store,
    ):
        _install_supplier(
            monkeypatch,
            (8_100_001, 8_100_002),
            supplier_calls,
        )
        real_join = materialization._load_joined_sources
        real_publish = private_publication._publish_d7_v1_pre_item23_records_no_replace

        def joined(*args: object, **kwargs: object) -> object:
            nonlocal captured_descriptors, joined_completed
            sources = args[2] if len(args) > 2 else kwargs.get("sources_by_role")
            is_complete = isinstance(sources, Mapping) and (
                records.D7V1PreItem23ChronologyReceipt.artifact_role in sources
            )
            if is_complete and boundary == "joined":
                reader = kwargs.get("external_reader")
                evidence = getattr(reader, "__self__", None)
                assert (
                    type(evidence) is private_publication._D7V1AnchoredExternalEvidence
                )
                captured_descriptors = tuple(evidence.file_fd_by_path.values())
                for descriptor in captured_descriptors:
                    os.fstat(descriptor)
                _swap_external_namespace("claim-file", parent, physical_store, evidence)
            result = real_join(*args, **kwargs)
            if is_complete:
                joined_completed += 1
            return result

        def publish(*args: object, **kwargs: object) -> object:
            nonlocal captured_descriptors, publisher_calls
            publisher_calls += 1
            evidence = kwargs.get("_anchored_external_evidence")
            assert type(evidence) is private_publication._D7V1AnchoredExternalEvidence
            captured_descriptors = tuple(evidence.file_fd_by_path.values())
            for descriptor in captured_descriptors:
                os.fstat(descriptor)
            assert joined_completed == 1
            if boundary == "publisher":
                _swap_external_namespace("claim-file", parent, physical_store, evidence)
            return real_publish(*args, **kwargs)

        monkeypatch.setattr(materialization, "_load_joined_sources", joined)
        monkeypatch.setattr(
            private_publication,
            "_publish_d7_v1_pre_item23_records_no_replace",
            publish,
        )
        with pytest.raises(
            orchestrator._D7V1ExternalChronologyFailure,
            match="external_published_verification_unknown",
        ) as caught:
            orchestrator._materialize_d7_v1_pre_item23_no_replace(
                case.context,
                source_commit=case.source_commit,
            )
        assert supplier_calls == [(8_100_001, 8_100_002)]
        assert joined_completed == (0 if boundary == "joined" else 1)
        assert publisher_calls == (0 if boundary == "joined" else 1)
        assert caught.value.disposition == "external_published_verification_unknown"
        assert caught.value.stage_retained is False
        assert caught.value.store_visible is True
        assert caught.value.external_store_verified is None
        assert caught.value.repository_disposition is None
        assert caught.value.repository_destination is None
        assert caught.value.repository_stage_path is None
        assert caught.value.repository_stage_retained is None
        assert caught.value.repository_publication_visible is None
        assert isinstance(caught.value.__cause__, QualificationContractError)
        assert not physical_stage.exists()
        assert physical_store.is_dir()
    for descriptor in captured_descriptors:
        with pytest.raises(OSError):
            os.fstat(descriptor)


def test_repository_stage_fault_preserves_verified_external_state(
    case: object,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    supplier_calls: list[tuple[int, int]] = []
    retained_stage: Path | None = None
    with _external_sandbox(tmp_path, monkeypatch) as (
        _parent,
        physical_stage,
        physical_store,
    ):
        _install_supplier(
            monkeypatch,
            (8_100_001, 8_100_002),
            supplier_calls,
        )

        def fail_repository_stage(*_args: object, **_kwargs: object) -> object:
            raise QualificationContractError("injected repository stage fault")

        monkeypatch.setattr(
            private_publication,
            "_revalidate_owned_stage",
            fail_repository_stage,
        )
        try:
            with pytest.raises(
                orchestrator._D7V1ExternalChronologyFailure,
                match="repository_publication_failed_external_store_verified",
            ) as caught:
                orchestrator._materialize_d7_v1_pre_item23_no_replace(
                    case.context,
                    source_commit=case.source_commit,
                )
            retained_stage = caught.value.repository_stage_path
            assert supplier_calls == [(8_100_001, 8_100_002)]
            assert caught.value.stage_retained is False
            assert caught.value.store_visible is True
            assert caught.value.external_store_verified is True
            assert caught.value.repository_disposition == "stage_partial_retained"
            assert caught.value.repository_stage_retained is True
            assert caught.value.repository_publication_visible is False
            assert isinstance(retained_stage, Path) and retained_stage.is_dir()
            assert type(caught.value.__cause__) is (
                private_publication.D7V1PrivatePublicationFailure
            )
            assert not physical_stage.exists()
            assert len(_external_files(physical_store)) == 2
        finally:
            if retained_stage is not None:
                shutil.rmtree(retained_stage, ignore_errors=True)


def test_post_repository_rename_external_fault_preserves_both_namespaces(
    case: object,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    supplier_calls: list[tuple[int, int]] = []
    published_join_complete = False
    published_destination: Path | None = None
    with _external_sandbox(tmp_path, monkeypatch) as (
        _parent,
        physical_stage,
        physical_store,
    ):
        _install_supplier(
            monkeypatch,
            (8_100_001, 8_100_002),
            supplier_calls,
        )
        real_join = materialization._load_joined_sources
        real_read = private_publication._D7V1AnchoredExternalEvidence.read

        def joined(*args: object, **kwargs: object) -> object:
            nonlocal published_join_complete
            result = real_join(*args, **kwargs)
            stage_root = kwargs.get("stage_root")
            if isinstance(stage_root, Path) and not stage_root.name.startswith("."):
                published_join_complete = True
            return result

        def fail_final_external_reload(
            evidence: private_publication._D7V1AnchoredExternalEvidence,
            path: Path,
            maximum_bytes: int,
        ) -> bytes:
            if published_join_complete:
                raise QualificationContractError(
                    "injected final anchored external reload failure"
                )
            return real_read(evidence, path, maximum_bytes)

        monkeypatch.setattr(materialization, "_load_joined_sources", joined)
        monkeypatch.setattr(
            private_publication._D7V1AnchoredExternalEvidence,
            "read",
            fail_final_external_reload,
        )
        try:
            with pytest.raises(
                orchestrator._D7V1ExternalChronologyFailure,
                match="repository_publication_failed_external_store_unverified",
            ) as caught:
                orchestrator._materialize_d7_v1_pre_item23_no_replace(
                    case.context,
                    source_commit=case.source_commit,
                )
            published_destination = caught.value.repository_destination
            assert supplier_calls == [(8_100_001, 8_100_002)]
            assert published_join_complete is True
            assert caught.value.stage_retained is False
            assert caught.value.store_visible is True
            assert caught.value.external_store_verified is False
            assert caught.value.repository_disposition == (
                "published_verification_unknown"
            )
            assert caught.value.repository_stage_retained is False
            assert caught.value.repository_publication_visible is True
            assert (
                isinstance(published_destination, Path)
                and published_destination.is_dir()
            )
            assert type(caught.value.__cause__) is (
                private_publication.D7V1PrivatePublicationFailure
            )
            assert not physical_stage.exists()
            assert len(_external_files(physical_store)) == 2
        finally:
            if published_destination is not None:
                shutil.rmtree(published_destination, ignore_errors=True)


def test_success_has_exact_order_two_external_files_and_nine_private_records(
    case: object,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    events: list[str] = []
    supplier_calls: list[tuple[int, int]] = []
    captured_descriptors: tuple[int, ...] = ()
    with _external_sandbox(tmp_path, monkeypatch) as (
        _parent,
        physical_stage,
        physical_store,
    ):
        _install_supplier(
            monkeypatch,
            (8_100_001, 8_100_002),
            supplier_calls,
        )
        observed_supplier = _observed_supplier(
            selected_supplier._FIXED_SUPPLIER,
            events,
        )
        monkeypatch.setattr(
            selected_supplier,
            "_supply_d7_v1_official_seed_values",
            observed_supplier,
        )
        monkeypatch.setattr(selected_supplier, "_FIXED_SUPPLIER", observed_supplier)

        real_create = orchestrator._create_external_stage
        real_persist = orchestrator._persist_external_record
        real_promote = orchestrator._promote_external_store_no_replace
        real_receipt = orchestrator._build_receipt_last
        real_join = materialization._load_joined_sources
        real_publish = private_publication._publish_d7_v1_pre_item23_records_no_replace

        def create(*args: object, **kwargs: object) -> object:
            result = real_create(*args, **kwargs)
            events.append("external-stage")
            return result

        def persist(stage: object, record: object) -> object:
            result = real_persist(stage, record)
            events.append(f"durable-{record.artifact_role}")
            return result

        def promote(*args: object, **kwargs: object) -> object:
            result = real_promote(*args, **kwargs)
            events.append("external-promoted-and-reverified")
            return result

        def receipt(*args: object, **kwargs: object) -> object:
            result = real_receipt(*args, **kwargs)
            events.append("receipt-last")
            return result

        def joined(*args: object, **kwargs: object) -> object:
            result = real_join(*args, **kwargs)
            sources = args[2] if len(args) > 2 else kwargs.get("sources_by_role")
            if isinstance(sources, Mapping) and (
                records.D7V1PreItem23ChronologyReceipt.artifact_role in sources
            ):
                events.append("joined-hard-gate")
            return result

        def publish(*args: object, **kwargs: object) -> object:
            nonlocal captured_descriptors
            evidence = kwargs.get("_anchored_external_evidence")
            assert type(evidence) is private_publication._D7V1AnchoredExternalEvidence
            captured_descriptors = tuple(
                (
                    evidence.parent_fd,
                    evidence.root_fd,
                    *evidence.directory_fd_by_path.values(),
                    *evidence.file_fd_by_path.values(),
                )
            )
            for descriptor in captured_descriptors:
                os.fstat(descriptor)
            result = real_publish(*args, **kwargs)
            events.append("repository-published")
            return result

        monkeypatch.setattr(orchestrator, "_create_external_stage", create)
        monkeypatch.setattr(orchestrator, "_persist_external_record", persist)
        monkeypatch.setattr(
            orchestrator,
            "_promote_external_store_no_replace",
            promote,
        )
        monkeypatch.setattr(orchestrator, "_build_receipt_last", receipt)
        monkeypatch.setattr(materialization, "_load_joined_sources", joined)
        monkeypatch.setattr(
            private_publication,
            "_publish_d7_v1_pre_item23_records_no_replace",
            publish,
        )

        publication_receipt = orchestrator._materialize_d7_v1_pre_item23_no_replace(
            case.context,
            source_commit=case.source_commit,
        )

        for descriptor in captured_descriptors:
            with pytest.raises(OSError):
                os.fstat(descriptor)
        assert supplier_calls == [(8_100_001, 8_100_002)]
        expected_order = (
            "external-stage",
            "durable-exclusive-seed-supply-claim",
            "supplier",
            "durable-official-execution-attempt-reservation",
            "external-promoted-and-reverified",
            "receipt-last",
            "joined-hard-gate",
            "repository-published",
        )
        positions = [events.index(item) for item in expected_order]
        assert positions == sorted(positions)
        assert not physical_stage.exists()
        external = _external_files(physical_store)
        assert set(external) == {
            "d7-v1-prefix-evidence-only/exclusive-seed-supply-claim.json",
            ("d7-v1-attempt-evidence/official-execution-attempt-reservation.json"),
        }

        destination = publication_receipt.destination
        protocol = materialization._protocol_at_commit(case.context, case.source_commit)
        expected_paths = materialization._expected_stage_files(protocol)
        repository_sources = {
            role: destination.joinpath(*PurePosixPath(relative).parts).read_bytes()
            for role, relative in expected_paths.items()
        }
        assert len(repository_sources) == 9
        assert (
            external["d7-v1-prefix-evidence-only/exclusive-seed-supply-claim.json"]
            == repository_sources[records.D7V1ExclusiveSeedSupplyClaim.artifact_role]
        )
        assert (
            external[
                "d7-v1-attempt-evidence/official-execution-attempt-reservation.json"
            ]
            == repository_sources[
                records.D7V1OfficialExecutionAttemptReservation.artifact_role
            ]
        )
        assert publication_receipt.source_commit == case.source_commit
        assert publication_receipt.authority_granted is False
        assert publication_receipt.materialization_authorized is False
        assert publication_receipt.execution_authorized is False
        assert publication_receipt.scientific_claim_eligible is False
        assert {
            role: sha256_bytes(source) for role, source in repository_sources.items()
        } == dict(publication_receipt.member_sha256_by_role)
