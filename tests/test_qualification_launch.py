from __future__ import annotations

import inspect
import runpy
import subprocess
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

import spirallens.qualification.contracts as qualification_contracts
import spirallens.qualification.freeze as qualification_freeze
import spirallens.qualification.launch as qualification_launch
import spirallens.qualification.runner as qualification_runner
from spirallens.core.canonical import parse_canonical_json, sha256_bytes
from spirallens.qualification.common import QualificationContractError
from spirallens.qualification.freeze import (
    SelectionFailedAttemptArtifact,
    SelectionFreezeArtifact,
    TerminalAttemptArtifactKind,
    begin_selection_execution,
    claim_selection_attempt,
    load_terminal_selection_consumption,
    publish_terminal_selection_consumption,
    selection_attempt_claim_path,
    selection_execution_start_path,
    selection_freeze_store_path,
    terminal_selection_transaction_path,
    write_selection_freeze,
)
from spirallens.qualification.launch import (
    ExclusiveTerminalPublicationCapability,
    LoadedCommittedSelectionTerminal,
    PreparedSelectionLaunchDescriptor,
    load_committed_selection_terminal,
    load_prepared_selection_launch,
    load_prepared_selection_launch_descriptor,
    prepare_selection_launch,
    probe_exclusive_terminal_publication_capability,
    selection_launch_intent_path,
    write_prepared_selection_launch_descriptor,
)
from spirallens.qualification.persistence import (
    load_qualification_protocol,
    write_qualification_protocol,
)
from spirallens.qualification.preparation import (
    CLOSED_D0_D5_OFFICIAL_EXECUTABLE_PATHS,
    build_closed_d0_d5_selection_protocol,
    publish_closed_d0_d5_preseed_readiness_artifact,
)
from spirallens.qualification.protocol import RepositoryFileDigest
from spirallens.qualification.source_binding import (
    QualificationSourceBindingSummary,
    verify_source_binding,
)


def _git(repository: Path, *arguments: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repository), *arguments],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _launch_fixture(tmp_path: Path) -> SimpleNamespace:
    source_namespace = runpy.run_path(
        Path(__file__).with_name("test_qualification_source_binding.py")
    )
    source_fixture = source_namespace["_source_fixture"](tmp_path)
    repository, engine, registry, registry_path, referent_path = source_fixture
    for repository_path in CLOSED_D0_D5_OFFICIAL_EXECUTABLE_PATHS:
        script_path = repository / repository_path
        script_path.parent.mkdir(parents=True, exist_ok=True)
        script_path.write_bytes(
            f'#!/usr/bin/env python3\n"""Test {repository_path}."""\n'.encode()
        )
    _git(repository, "add", "scripts")
    _git(repository, "commit", "-m", "bind official selection scripts")
    engine = replace(
        engine,
        commit=_git(repository, "rev-parse", "HEAD"),
        official_executables=tuple(
            RepositoryFileDigest(
                repository_path=repository_path,
                sha256=sha256_bytes((repository / repository_path).read_bytes()),
            )
            for repository_path in CLOSED_D0_D5_OFFICIAL_EXECUTABLE_PATHS
        ),
    )
    artifacts = repository / "artifacts"
    artifacts.mkdir()
    source_receipt = verify_source_binding(
        engine=engine,
        registry=registry,
        repository_root=repository,
        registry_path=registry_path,
        referent_path=referent_path,
    )
    loaded_preseed = publish_closed_d0_d5_preseed_readiness_artifact(
        artifacts / "preseed-readiness.json",
        repository_root=repository,
        registry_path=registry_path,
        referent_path=referent_path,
        source_readiness_receipt=source_receipt,
    )
    protocol = build_closed_d0_d5_selection_protocol(
        engine=engine,
        registry=registry,
        selection_seeds=(910_001, 910_002),
        preseed_readiness=loaded_preseed.binding,
    )

    protocol_path = artifacts / "protocol.json"
    protocol_identity = write_qualification_protocol(protocol_path, protocol)
    loaded_protocol = load_qualification_protocol(
        protocol_path,
        expected_source_sha256=protocol_identity.source_sha256,
        expected_canonical_sha256=protocol_identity.canonical_sha256,
    )
    freeze = SelectionFreezeArtifact.from_loaded_protocol(
        freeze_id="launch-test-freeze",
        loaded_protocol=loaded_protocol,
        seed_family_id="launch-test-family",
    )
    freeze_path = artifacts / "freeze.json"
    freeze_identity = write_selection_freeze(freeze_path, freeze)
    _git(repository, "add", "artifacts")
    _git(repository, "commit", "-m", "freeze prepared selection artifacts")
    attempt_store = artifacts / "attempt-store"
    attempt_store.mkdir()
    return SimpleNamespace(
        repository=repository,
        registry_path=registry_path,
        referent_path=referent_path,
        protocol_path=protocol_path,
        protocol_identity=protocol_identity,
        freeze=freeze,
        freeze_path=freeze_path,
        freeze_identity=freeze_identity,
        attempt_store=attempt_store,
    )


def _prepare(fixture: SimpleNamespace):
    return prepare_selection_launch(
        descriptor_id="launch-test",
        repository_root=fixture.repository,
        registry_path=fixture.registry_path,
        referent_path=fixture.referent_path,
        protocol_path=fixture.protocol_path,
        protocol_source_sha256=fixture.protocol_identity.source_sha256,
        protocol_canonical_sha256=fixture.protocol_identity.canonical_sha256,
        freeze_path=fixture.freeze_path,
        freeze_source_sha256=fixture.freeze_identity.source_sha256,
        freeze_canonical_sha256=fixture.freeze_identity.canonical_sha256,
        attempt_store_path=fixture.attempt_store,
        claim_id="launch-test-claim",
    )


def _write_and_commit_g(
    fixture: SimpleNamespace,
    prepared: object,
):
    descriptor_path = fixture.repository / "artifacts" / "launch.json"
    loaded_descriptor = write_prepared_selection_launch_descriptor(
        descriptor_path,
        prepared.descriptor,
    )
    _git(
        fixture.repository,
        "add",
        "artifacts/launch.json",
        "artifacts/attempt-store",
    )
    _git(fixture.repository, "commit", "-m", "record committed G launch")
    return descriptor_path, loaded_descriptor


def test_capability_probe_is_read_only_for_mocked_darwin_and_linux(
    tmp_path: Path,
) -> None:
    calls: list[str] = []

    def renameatx_np(*_arguments: object) -> int:
        calls.append("darwin")
        return 0

    def renameat2(*_arguments: object) -> int:
        calls.append("linux")
        return 0

    before = tuple(tmp_path.iterdir())
    darwin = probe_exclusive_terminal_publication_capability(
        platform_id="darwin",
        libc=SimpleNamespace(renameatx_np=renameatx_np),
    )
    linux = probe_exclusive_terminal_publication_capability(
        platform_id="linux-gnu",
        libc=SimpleNamespace(renameat2=renameat2),
    )

    assert calls == []
    assert tuple(tmp_path.iterdir()) == before
    assert darwin.platform_id == "darwin"
    assert darwin.primitive_id == "renameatx_np"
    assert darwin.no_replace_flag == 4
    assert linux.platform_id == "linux"
    assert linux.primitive_id == "renameat2"
    assert linux.no_replace_flag == 1
    assert darwin.read_only_probe is True
    assert darwin.primitive_invoked is False
    assert darwin.filesystem_mutated is False
    assert darwin.operational_publication_proved is False
    assert (
        ExclusiveTerminalPublicationCapability.from_dict(
            parse_canonical_json(darwin.canonical_bytes)
        )
        == darwin
    )


def test_capability_probe_fails_closed_without_exact_callable_symbol() -> None:
    with pytest.raises(QualificationContractError, match="unsupported"):
        probe_exclusive_terminal_publication_capability(
            platform_id="win32",
            libc=object(),
        )
    with pytest.raises(QualificationContractError, match="unavailable"):
        probe_exclusive_terminal_publication_capability(
            platform_id="darwin",
            libc=object(),
        )
    with pytest.raises(QualificationContractError, match="not callable"):
        probe_exclusive_terminal_publication_capability(
            platform_id="linux",
            libc=SimpleNamespace(renameat2=3),
        )


def test_real_host_capability_probe_never_mutates_the_filesystem(
    tmp_path: Path,
) -> None:
    before = tuple(tmp_path.iterdir())

    capability = probe_exclusive_terminal_publication_capability()

    assert capability.platform_id in {"darwin", "linux"}
    assert capability.symbol_resolved is True
    assert capability.primitive_invoked is False
    assert tuple(tmp_path.iterdir()) == before


def test_prepare_claims_only_after_sources_and_capability_then_round_trips(
    tmp_path: Path,
) -> None:
    fixture = _launch_fixture(tmp_path)

    prepared = _prepare(fixture)

    descriptor = prepared.descriptor
    expected_claim_path = selection_attempt_claim_path(
        fixture.attempt_store,
        fixture.freeze,
    )
    assert Path(descriptor.attempt_claim_path) == expected_claim_path
    assert expected_claim_path.is_file()
    intent_path = selection_launch_intent_path(
        fixture.attempt_store,
        fixture.freeze,
    )
    assert intent_path.is_file()
    assert descriptor.launch_intent.path == str(intent_path)
    assert prepared.attempt_claim.launch_intent == descriptor.launch_intent
    assert prepared.attempt_claim.canonical_bytes == expected_claim_path.read_bytes()
    assert descriptor.attempt_claim_preacquired is True
    assert descriptor.execution_may_create_attempt_claim is False
    assert descriptor.attempt_store_override_authorized is False
    assert descriptor.uniqueness_scope == "descriptor_bound_store_only"
    assert descriptor.path_binding_scope == "absolute_local_paths"
    assert descriptor.global_one_shot_proved is False
    assert descriptor.cross_store_uniqueness_proved is False
    assert descriptor.multi_host_uniqueness_proved is False
    assert descriptor.cross_worktree_portable is False
    assert descriptor.cross_machine_portable is False
    assert descriptor.trusted_store_operator_required is True
    assert descriptor.hostile_local_mutation_resistant is False
    assert descriptor.selection_execution_started is False
    assert descriptor.selection_values_observed is False
    assert not selection_execution_start_path(
        fixture.attempt_store,
        fixture.freeze,
    ).exists()
    assert not terminal_selection_transaction_path(
        fixture.attempt_store,
        fixture.freeze,
    ).exists()
    assert prepared.source_readiness_receipt == prepared.source_binding_receipt
    descriptor.source_readiness.verify_receipt(prepared.source_readiness_receipt)


def test_prepare_rejects_raw_preexisting_claim_without_launch_intent(
    tmp_path: Path,
) -> None:
    fixture = _launch_fixture(tmp_path)
    claim_selection_attempt(
        fixture.attempt_store,
        claim_id="launch-test-claim",
        freeze=fixture.freeze,
    )

    with pytest.raises(
        QualificationContractError,
        match="no earlier persisted launch intent",
    ):
        _prepare(fixture)

    assert not selection_launch_intent_path(
        fixture.attempt_store,
        fixture.freeze,
    ).exists()


def test_prepare_fails_before_claim_when_source_readiness_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _launch_fixture(tmp_path)
    claim_called = False

    def fail_source(*_arguments: object, **_keywords: object) -> object:
        raise QualificationContractError("injected source failure")

    def forbidden_claim(*_arguments: object, **_keywords: object) -> object:
        nonlocal claim_called
        claim_called = True
        raise AssertionError("claim must not be reached")

    monkeypatch.setattr(
        qualification_launch,
        "verify_protocol_source_binding",
        fail_source,
    )
    monkeypatch.setattr(
        qualification_launch,
        "claim_selection_attempt",
        forbidden_claim,
    )

    with pytest.raises(QualificationContractError, match="source failure"):
        _prepare(fixture)

    assert claim_called is False
    assert tuple(fixture.attempt_store.iterdir()) == ()


def test_prepare_rejects_noncanonical_profile_before_claim(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _launch_fixture(tmp_path)
    claim_called = False

    def fail_profile(_protocol: object, **_keywords: object) -> object:
        raise QualificationContractError("injected closed-profile failure")

    def forbidden_claim(*_arguments: object, **_keywords: object) -> object:
        nonlocal claim_called
        claim_called = True
        raise AssertionError("claim must not be reached")

    monkeypatch.setattr(
        qualification_launch,
        "validate_closed_d0_d5_selection_protocol",
        fail_profile,
    )
    monkeypatch.setattr(
        qualification_launch,
        "claim_selection_attempt",
        forbidden_claim,
    )

    with pytest.raises(QualificationContractError, match="closed-profile failure"):
        _prepare(fixture)

    assert claim_called is False
    assert tuple(fixture.attempt_store.iterdir()) == ()


def test_prepare_fails_before_claim_when_terminal_capability_is_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _launch_fixture(tmp_path)
    claim_called = False

    def fail_capability() -> object:
        raise QualificationContractError("injected capability failure")

    def forbidden_claim(*_arguments: object, **_keywords: object) -> object:
        nonlocal claim_called
        claim_called = True
        raise AssertionError("claim must not be reached")

    monkeypatch.setattr(
        qualification_launch,
        "probe_exclusive_terminal_publication_capability",
        fail_capability,
    )
    monkeypatch.setattr(
        qualification_launch,
        "claim_selection_attempt",
        forbidden_claim,
    )

    with pytest.raises(QualificationContractError, match="capability failure"):
        _prepare(fixture)

    assert claim_called is False
    assert tuple(fixture.attempt_store.iterdir()) == ()


def test_prepare_rejects_historical_preseed_tamper_before_claim(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _launch_fixture(tmp_path)
    preseed_path = Path(
        load_qualification_protocol(
            fixture.protocol_path,
            expected_source_sha256=fixture.protocol_identity.source_sha256,
            expected_canonical_sha256=fixture.protocol_identity.canonical_sha256,
        ).protocol.preseed_readiness.artifact_path  # type: ignore[union-attr]
    )
    preseed_path.write_bytes(preseed_path.read_bytes() + b" ")

    def forbidden_claim(*_arguments: object, **_keywords: object) -> object:
        raise AssertionError("claim must not be reached after preseed tamper")

    monkeypatch.setattr(
        qualification_launch,
        "claim_selection_attempt",
        forbidden_claim,
    )
    with pytest.raises(
        QualificationContractError,
        match="preseed readiness artifact source SHA-256 differs",
    ):
        _prepare(fixture)
    assert tuple(fixture.attempt_store.iterdir()) == ()


def test_prepare_rejects_official_script_drift_before_claim(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _launch_fixture(tmp_path)
    script_path = fixture.repository / CLOSED_D0_D5_OFFICIAL_EXECUTABLE_PATHS[0]
    script_path.write_bytes(script_path.read_bytes() + b"\n# drift\n")

    def forbidden_claim(*_arguments: object, **_keywords: object) -> object:
        raise AssertionError("claim must not be reached after script drift")

    monkeypatch.setattr(
        qualification_launch,
        "claim_selection_attempt",
        forbidden_claim,
    )
    with pytest.raises(
        QualificationContractError,
        match="official executable",
    ):
        _prepare(fixture)
    assert tuple(fixture.attempt_store.iterdir()) == ()


def test_claim_to_descriptor_failure_recovers_exact_claim_without_reclaim(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _launch_fixture(tmp_path)
    prepared = _prepare(fixture)
    claim_path = Path(prepared.descriptor.attempt_claim_path)
    initial_identity = (
        claim_path.stat().st_dev,
        claim_path.stat().st_ino,
        claim_path.read_bytes(),
    )

    def injected_descriptor_failure(*_args: object, **_kwargs: object) -> object:
        raise QualificationContractError("injected descriptor publication failure")

    original_write = qualification_launch.write_prepared_selection_launch_descriptor
    monkeypatch.setattr(
        qualification_launch,
        "write_prepared_selection_launch_descriptor",
        injected_descriptor_failure,
    )
    with pytest.raises(
        QualificationContractError,
        match="descriptor publication failure",
    ):
        qualification_launch.write_prepared_selection_launch_descriptor(
            tmp_path / "launch.json",
            prepared.descriptor,
        )
    monkeypatch.setattr(
        qualification_launch,
        "write_prepared_selection_launch_descriptor",
        original_write,
    )

    def forbidden_second_claim(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("recovery must not acquire a second claim")

    monkeypatch.setattr(
        qualification_launch,
        "claim_selection_attempt",
        forbidden_second_claim,
    )
    recovered = _prepare(fixture)
    recovered_identity = (
        claim_path.stat().st_dev,
        claim_path.stat().st_ino,
        claim_path.read_bytes(),
    )
    assert recovered.descriptor == prepared.descriptor
    assert recovered_identity == initial_identity
    assert tuple(
        path
        for path in fixture.attempt_store.iterdir()
        if path.name.endswith(".selection-attempt-claim.json")
    ) == (claim_path,)

    loaded = original_write(tmp_path / "launch.json", recovered.descriptor)
    assert loaded.descriptor == recovered.descriptor


def test_descriptor_persistence_is_canonical_no_overwrite_and_digest_bound(
    tmp_path: Path,
) -> None:
    fixture = _launch_fixture(tmp_path)
    prepared = _prepare(fixture)
    path = tmp_path / "launch.json"

    loaded = write_prepared_selection_launch_descriptor(
        path,
        prepared.descriptor,
    )

    assert loaded.descriptor == prepared.descriptor
    assert loaded.source_bytes == prepared.descriptor.canonical_bytes
    assert loaded.source_sha256 == prepared.descriptor.canonical_sha256
    assert loaded.canonical_sha256 == prepared.descriptor.canonical_sha256
    assert (
        PreparedSelectionLaunchDescriptor.from_dict(
            parse_canonical_json(loaded.source_bytes)
        )
        == prepared.descriptor
    )
    with pytest.raises(QualificationContractError, match="already exists"):
        write_prepared_selection_launch_descriptor(path, prepared.descriptor)
    with pytest.raises(QualificationContractError, match="source SHA-256"):
        load_prepared_selection_launch_descriptor(
            path,
            expected_source_sha256="0" * 64,
            expected_canonical_sha256=prepared.descriptor.canonical_sha256,
        )


def test_execution_loader_has_no_store_override_and_never_creates_claim(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _launch_fixture(tmp_path)
    prepared = _prepare(fixture)
    path, loaded_descriptor = _write_and_commit_g(fixture, prepared)

    parameters = inspect.signature(load_prepared_selection_launch).parameters
    assert tuple(parameters) == (
        "descriptor_path",
        "expected_descriptor_source_sha256",
        "expected_descriptor_canonical_sha256",
    )
    assert "attempt_store_path" not in parameters

    def forbidden_claim(*_arguments: object, **_keywords: object) -> object:
        raise AssertionError("execution loader must never create a claim")

    monkeypatch.setattr(
        qualification_launch,
        "claim_selection_attempt",
        forbidden_claim,
    )
    before = {path.name: path.read_bytes() for path in fixture.attempt_store.iterdir()}

    loaded = load_prepared_selection_launch(
        path,
        expected_descriptor_source_sha256=loaded_descriptor.source_sha256,
        expected_descriptor_canonical_sha256=(loaded_descriptor.canonical_sha256),
    )

    after = {path.name: path.read_bytes() for path in fixture.attempt_store.iterdir()}
    assert before == after
    assert loaded.attempt_claim == prepared.attempt_claim
    assert loaded.descriptor.attempt_store_path == str(fixture.attempt_store)
    assert loaded.source_binding_receipt.head_commit == _git(
        fixture.repository,
        "rev-parse",
        "HEAD",
    )
    assert loaded.launch_authorization is not None
    assert loaded.launch_authorization.authorized_head_commit == _git(
        fixture.repository,
        "rev-parse",
        "HEAD",
    )


def test_execution_loader_rejects_uncommitted_g_before_authorization(
    tmp_path: Path,
) -> None:
    fixture = _launch_fixture(tmp_path)
    prepared = _prepare(fixture)
    descriptor_path = fixture.repository / "artifacts" / "launch.json"
    loaded_descriptor = write_prepared_selection_launch_descriptor(
        descriptor_path,
        prepared.descriptor,
    )

    with pytest.raises(QualificationContractError, match="tracked HEAD"):
        load_prepared_selection_launch(
            descriptor_path,
            expected_descriptor_source_sha256=(loaded_descriptor.source_sha256),
            expected_descriptor_canonical_sha256=(loaded_descriptor.canonical_sha256),
        )


@pytest.mark.parametrize(
    "artifact_name",
    ("descriptor", "store-freeze", "launch-intent", "attempt-claim"),
)
@pytest.mark.parametrize("mutation", ("dirty", "missing"))
def test_execution_loader_rejects_each_changed_committed_g_artifact(
    tmp_path: Path,
    artifact_name: str,
    mutation: str,
) -> None:
    fixture = _launch_fixture(tmp_path)
    prepared = _prepare(fixture)
    descriptor_path, loaded_descriptor = _write_and_commit_g(
        fixture,
        prepared,
    )
    artifact_paths = {
        "descriptor": descriptor_path,
        "store-freeze": selection_freeze_store_path(
            fixture.attempt_store,
            fixture.freeze,
        ),
        "launch-intent": Path(prepared.descriptor.launch_intent.path),
        "attempt-claim": Path(prepared.descriptor.attempt_claim_path),
    }
    artifact_path = artifact_paths[artifact_name]
    if mutation == "dirty":
        artifact_path.write_bytes(artifact_path.read_bytes() + b"\n")
    else:
        artifact_path.unlink()

    with pytest.raises(QualificationContractError):
        load_prepared_selection_launch(
            descriptor_path,
            expected_descriptor_source_sha256=loaded_descriptor.source_sha256,
            expected_descriptor_canonical_sha256=(loaded_descriptor.canonical_sha256),
        )
    assert not selection_execution_start_path(
        fixture.attempt_store,
        fixture.freeze,
    ).exists()


@pytest.mark.parametrize(
    "artifact_name",
    ("descriptor", "store-freeze", "launch-intent", "attempt-claim"),
)
def test_official_orchestrator_revalidates_each_g_artifact_before_start(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    artifact_name: str,
) -> None:
    fixture = _launch_fixture(tmp_path)
    prepared = _prepare(fixture)
    descriptor_path, loaded_descriptor = _write_and_commit_g(
        fixture,
        prepared,
    )
    loaded = load_prepared_selection_launch(
        descriptor_path,
        expected_descriptor_source_sha256=loaded_descriptor.source_sha256,
        expected_descriptor_canonical_sha256=(loaded_descriptor.canonical_sha256),
    )
    artifact_paths = {
        "descriptor": descriptor_path,
        "store-freeze": selection_freeze_store_path(
            fixture.attempt_store,
            fixture.freeze,
        ),
        "launch-intent": Path(prepared.descriptor.launch_intent.path),
        "attempt-claim": Path(prepared.descriptor.attempt_claim_path),
    }
    artifact_path = artifact_paths[artifact_name]
    artifact_path.write_bytes(artifact_path.read_bytes() + b"\n")

    def forbidden_run(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("official runner must not start after G drift")

    monkeypatch.setattr(
        qualification_runner,
        "run_calibration_selection",
        forbidden_run,
    )
    with pytest.raises(QualificationContractError):
        qualification_runner.run_and_publish_calibration_selection(
            loaded.loaded_protocol,
            source_binding_receipt=loaded.source_binding_receipt,
            selection_freeze_artifact=loaded.selection_freeze_artifact,
            attempt_claim=loaded.attempt_claim,
            attempt_store_directory=fixture.attempt_store,
            launch_authorization=loaded.launch_authorization,
        )
    assert not selection_execution_start_path(
        fixture.attempt_store,
        fixture.freeze,
    ).exists()


def test_official_orchestrator_rejects_missing_authorization_before_start(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _launch_fixture(tmp_path)
    prepared = _prepare(fixture)

    def forbidden_run(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("official runner must not start without authorization")

    monkeypatch.setattr(
        qualification_runner,
        "run_calibration_selection",
        forbidden_run,
    )
    with pytest.raises(
        QualificationContractError,
        match="committed-G launch authorization",
    ):
        qualification_runner.run_and_publish_calibration_selection(
            prepared.loaded_protocol,
            source_binding_receipt=prepared.source_binding_receipt,
            selection_freeze_artifact=prepared.selection_freeze_artifact,
            attempt_claim=prepared.attempt_claim,
            attempt_store_directory=fixture.attempt_store,
        )

    assert not selection_execution_start_path(
        fixture.attempt_store,
        fixture.freeze,
    ).exists()


def test_official_after_start_failure_preserves_descriptor_authorization_lineage(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _launch_fixture(tmp_path)
    prepared = _prepare(fixture)
    descriptor_path, loaded_descriptor = _write_and_commit_g(
        fixture,
        prepared,
    )
    launch = load_prepared_selection_launch(
        descriptor_path,
        expected_descriptor_source_sha256=loaded_descriptor.source_sha256,
        expected_descriptor_canonical_sha256=loaded_descriptor.canonical_sha256,
    )
    authorization = launch.launch_authorization
    assert authorization is not None

    def fail_after_real_start(
        loaded_protocol: object,
        **kwargs: object,
    ) -> None:
        begin_selection_execution(
            kwargs["attempt_store_directory"],  # type: ignore[arg-type]
            freeze=kwargs["selection_freeze_artifact"],  # type: ignore[arg-type]
            attempt_claim=kwargs["attempt_claim"],  # type: ignore[arg-type]
            loaded_protocol=loaded_protocol,
            launch_authorization=kwargs["launch_authorization"],
        )
        kwargs["_execution_started_callback"]()  # type: ignore[operator]
        raise RuntimeError("official execution failed after start")

    monkeypatch.setattr(
        qualification_runner,
        "run_calibration_selection",
        fail_after_real_start,
    )

    with pytest.raises(
        RuntimeError,
        match="official execution failed after start",
    ) as captured:
        qualification_runner.run_and_publish_calibration_selection(
            launch.loaded_protocol,
            source_binding_receipt=launch.source_binding_receipt,
            selection_freeze_artifact=launch.selection_freeze_artifact,
            attempt_claim=launch.attempt_claim,
            attempt_store_directory=fixture.attempt_store,
            launch_authorization=authorization,
        )

    receipt = getattr(
        captured.value,
        qualification_runner.ORCHESTRATED_TERMINAL_PUBLICATION_RECEIPT_ATTRIBUTE,
    )
    assert isinstance(
        receipt,
        qualification_runner.OrchestratedTerminalPublicationReceipt,
    )
    assert receipt.terminal_artifact_kind is TerminalAttemptArtifactKind.FAILED_ATTEMPT
    _consumption, failed = load_terminal_selection_consumption(
        receipt.terminal_transaction_path,
        expected_manifest_sha256=receipt.manifest_sha256,
        expected_terminal_artifact_sha256=receipt.terminal_artifact_sha256,
        expected_consumption_sha256=receipt.consumption_sha256,
        freeze=launch.selection_freeze_artifact,
        attempt_claim=launch.attempt_claim,
        loaded_protocol=launch.loaded_protocol,
        launch_authorization=authorization,
    )
    assert isinstance(failed, SelectionFailedAttemptArtifact)
    assert (
        failed.selection_launch_authorization_sha256 == authorization.canonical_sha256
    )


def test_official_low_level_runner_rejects_no_authorization_before_start(
    tmp_path: Path,
) -> None:
    fixture = _launch_fixture(tmp_path)
    prepared = _prepare(fixture)

    with pytest.raises(
        QualificationContractError,
        match="low-level.*committed-G launch authorization",
    ):
        qualification_runner.run_calibration_selection(
            prepared.loaded_protocol,
            source_binding_receipt=prepared.source_binding_receipt,
            selection_freeze_artifact=prepared.selection_freeze_artifact,
            attempt_claim=prepared.attempt_claim,
            attempt_store_directory=fixture.attempt_store,
        )

    assert not selection_execution_start_path(
        fixture.attempt_store,
        fixture.freeze,
    ).exists()


def test_raw_claim_and_arbitrary_digest_cannot_start_or_terminalize_official(
    tmp_path: Path,
) -> None:
    fixture = _launch_fixture(tmp_path)
    loaded_protocol = load_qualification_protocol(
        fixture.protocol_path,
        expected_source_sha256=fixture.protocol_identity.source_sha256,
        expected_canonical_sha256=fixture.protocol_identity.canonical_sha256,
    )
    raw_claim, _identity = claim_selection_attempt(
        fixture.attempt_store,
        claim_id="raw-official-claim",
        freeze=fixture.freeze,
    )

    with pytest.raises(
        QualificationContractError,
        match="typed committed-G launch authorization",
    ):
        begin_selection_execution(
            fixture.attempt_store,
            freeze=fixture.freeze,
            attempt_claim=raw_claim,
            loaded_protocol=loaded_protocol,
            launch_authorization="a" * 64,
        )

    forged_failure = SelectionFailedAttemptArtifact.from_freeze(
        failed_attempt_id="forged-official-failure",
        freeze=fixture.freeze,
        failure_stage="forged-lineage",
        failure_evidence_sha256="b" * 64,
        attested_selection_values_observed=False,
        selection_launch_authorization_sha256="c" * 64,
    )
    with pytest.raises(QualificationContractError):
        publish_terminal_selection_consumption(
            fixture.attempt_store,
            consumption_id="forged-official-consumption",
            freeze=fixture.freeze,
            attempt_claim=raw_claim,
            terminal_artifact=forged_failure,
        )

    assert not selection_execution_start_path(
        fixture.attempt_store,
        fixture.freeze,
    ).exists()
    assert not terminal_selection_transaction_path(
        fixture.attempt_store,
        fixture.freeze,
    ).exists()


def test_official_start_terminal_and_loader_reject_lineage_mismatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _launch_fixture(tmp_path)
    prepared = _prepare(fixture)
    descriptor_path, loaded_descriptor = _write_and_commit_g(
        fixture,
        prepared,
    )
    launch = load_prepared_selection_launch(
        descriptor_path,
        expected_descriptor_source_sha256=loaded_descriptor.source_sha256,
        expected_descriptor_canonical_sha256=(loaded_descriptor.canonical_sha256),
    )
    authorization = launch.launch_authorization
    assert authorization is not None
    start, _identity = begin_selection_execution(
        fixture.attempt_store,
        freeze=fixture.freeze,
        attempt_claim=launch.attempt_claim,
        loaded_protocol=launch.loaded_protocol,
        launch_authorization=authorization,
    )
    assert start.selection_launch_authorization_sha256 == authorization.canonical_sha256
    assert start.authorized_head_commit == authorization.authorized_head_commit

    wrong_digest = "f" * 64
    assert wrong_digest != authorization.canonical_sha256
    wrong_failure = SelectionFailedAttemptArtifact.from_freeze(
        failed_attempt_id="wrong-lineage-failure",
        freeze=fixture.freeze,
        failure_stage="wrong-lineage",
        failure_evidence_sha256="e" * 64,
        attested_selection_values_observed=True,
        selection_launch_authorization_sha256=wrong_digest,
    )
    with pytest.raises(QualificationContractError):
        publish_terminal_selection_consumption(
            fixture.attempt_store,
            consumption_id="wrong-lineage-consumption",
            freeze=fixture.freeze,
            attempt_claim=launch.attempt_claim,
            terminal_artifact=wrong_failure,
            loaded_protocol=launch.loaded_protocol,
            launch_authorization=authorization,
        )
    with pytest.raises(
        QualificationContractError,
        match="required for the official",
    ):
        SelectionFailedAttemptArtifact.from_freeze(
            failed_attempt_id="missing-lineage-failure",
            freeze=fixture.freeze,
            failure_stage="missing-lineage",
            failure_evidence_sha256="d" * 64,
            attested_selection_values_observed=True,
        )

    original_validator = (
        qualification_freeze.validate_persisted_selection_execution_start
    )
    original_terminal_lineage = (
        qualification_freeze._terminal_launch_authorization_sha256
    )
    monkeypatch.setattr(
        qualification_freeze,
        "validate_persisted_selection_execution_start",
        lambda *_args, **_kwargs: start,
    )
    monkeypatch.setattr(
        qualification_freeze,
        "_terminal_launch_authorization_sha256",
        lambda _artifact: start.selection_launch_authorization_sha256,
    )
    consumption, terminal_identity = publish_terminal_selection_consumption(
        fixture.attempt_store,
        consumption_id="forced-wrong-lineage-consumption",
        freeze=fixture.freeze,
        attempt_claim=launch.attempt_claim,
        terminal_artifact=wrong_failure,
        loaded_protocol=launch.loaded_protocol,
        launch_authorization=authorization,
    )
    monkeypatch.setattr(
        qualification_freeze,
        "validate_persisted_selection_execution_start",
        original_validator,
    )
    monkeypatch.setattr(
        qualification_freeze,
        "_terminal_launch_authorization_sha256",
        original_terminal_lineage,
    )
    with pytest.raises(
        QualificationContractError,
        match="typed committed-G launch authorization",
    ):
        load_terminal_selection_consumption(
            terminal_identity.path,
            expected_manifest_sha256=terminal_identity.manifest_sha256,
            expected_terminal_artifact_sha256=(
                terminal_identity.terminal_artifact_sha256
            ),
            expected_consumption_sha256=(terminal_identity.consumption_sha256),
            freeze=fixture.freeze,
            attempt_claim=launch.attempt_claim,
            loaded_protocol=launch.loaded_protocol,
        )
    wrong_authorization = replace(
        authorization,
        protocol_canonical_sha256="0" * 64,
    )
    with pytest.raises(QualificationContractError):
        load_terminal_selection_consumption(
            terminal_identity.path,
            expected_manifest_sha256=terminal_identity.manifest_sha256,
            expected_terminal_artifact_sha256=(
                terminal_identity.terminal_artifact_sha256
            ),
            expected_consumption_sha256=(terminal_identity.consumption_sha256),
            freeze=fixture.freeze,
            attempt_claim=launch.attempt_claim,
            loaded_protocol=launch.loaded_protocol,
            launch_authorization=wrong_authorization,
        )
    assert consumption.terminal_artifact_sha256 == wrong_failure.canonical_sha256


def test_terminal_authorization_accepts_unchanged_successor_and_rejects_false_g(
    tmp_path: Path,
) -> None:
    fixture = _launch_fixture(tmp_path)
    prepared = _prepare(fixture)
    descriptor_path, loaded_descriptor = _write_and_commit_g(
        fixture,
        prepared,
    )
    launch = load_prepared_selection_launch(
        descriptor_path,
        expected_descriptor_source_sha256=loaded_descriptor.source_sha256,
        expected_descriptor_canonical_sha256=loaded_descriptor.canonical_sha256,
    )
    authorization = launch.launch_authorization
    assert authorization is not None
    begin_selection_execution(
        fixture.attempt_store,
        freeze=fixture.freeze,
        attempt_claim=launch.attempt_claim,
        loaded_protocol=launch.loaded_protocol,
        launch_authorization=authorization,
    )
    failed = SelectionFailedAttemptArtifact.from_freeze(
        failed_attempt_id="successor-terminal-failure",
        freeze=fixture.freeze,
        failure_stage="successor-terminal-validation",
        failure_evidence_sha256="a" * 64,
        attested_selection_values_observed=True,
        selection_launch_authorization_sha256=authorization.canonical_sha256,
    )
    consumption, terminal_identity = publish_terminal_selection_consumption(
        fixture.attempt_store,
        consumption_id="successor-terminal-consumption",
        freeze=fixture.freeze,
        attempt_claim=launch.attempt_claim,
        terminal_artifact=failed,
        loaded_protocol=launch.loaded_protocol,
        launch_authorization=authorization,
    )

    chronology_paths = (
        selection_execution_start_path(fixture.attempt_store, fixture.freeze),
        terminal_identity.path,
    )
    _git(
        fixture.repository,
        "add",
        *(str(path.relative_to(fixture.repository)) for path in chronology_paths),
    )
    _git(
        fixture.repository,
        "commit",
        "-m",
        "record terminal chronology successor",
    )
    successor_head = _git(fixture.repository, "rev-parse", "HEAD")
    assert successor_head != authorization.authorized_head_commit

    loaded_consumption, loaded_failed = load_terminal_selection_consumption(
        terminal_identity.path,
        expected_manifest_sha256=terminal_identity.manifest_sha256,
        expected_terminal_artifact_sha256=terminal_identity.terminal_artifact_sha256,
        expected_consumption_sha256=terminal_identity.consumption_sha256,
        freeze=fixture.freeze,
        attempt_claim=launch.attempt_claim,
        loaded_protocol=launch.loaded_protocol,
        launch_authorization=authorization,
    )
    assert loaded_consumption == consumption
    assert loaded_failed == failed

    false_g_authorization = replace(
        authorization,
        authorized_head_commit=successor_head,
    )
    with pytest.raises(
        QualificationContractError,
        match="already existed at committed G authorization HEAD",
    ):
        false_g_authorization.validate_terminal_companions(
            loaded_protocol=launch.loaded_protocol,
            freeze=fixture.freeze,
            attempt_claim=launch.attempt_claim,
            attempt_store=fixture.attempt_store,
        )

    _git(
        fixture.repository,
        "checkout",
        "--detach",
        authorization.authorized_head_commit,
    )
    sibling_marker = fixture.repository / "artifacts" / "sibling-marker.txt"
    sibling_marker.write_text("sibling\n", encoding="utf-8")
    _git(fixture.repository, "add", "artifacts/sibling-marker.txt")
    _git(fixture.repository, "commit", "-m", "create sibling of successor")
    sibling_head = _git(fixture.repository, "rev-parse", "HEAD")
    _git(fixture.repository, "checkout", "--detach", successor_head)
    sibling_authorization = replace(
        authorization,
        authorized_head_commit=sibling_head,
    )
    with pytest.raises(
        QualificationContractError,
        match="not an ancestor of current HEAD",
    ):
        sibling_authorization.validate_terminal_companions(
            loaded_protocol=launch.loaded_protocol,
            freeze=fixture.freeze,
            attempt_claim=launch.attempt_claim,
            attempt_store=fixture.attempt_store,
        )

    launch_intent_path = Path(launch.descriptor.launch_intent.path)
    launch_intent_path.write_bytes(launch_intent_path.read_bytes() + b"\n")
    _git(
        fixture.repository,
        "add",
        str(launch_intent_path.relative_to(fixture.repository)),
    )
    _git(fixture.repository, "commit", "-m", "modify one committed G artifact")
    with pytest.raises(
        QualificationContractError,
        match="changed after its committed G authorization",
    ):
        load_terminal_selection_consumption(
            terminal_identity.path,
            expected_manifest_sha256=terminal_identity.manifest_sha256,
            expected_terminal_artifact_sha256=(
                terminal_identity.terminal_artifact_sha256
            ),
            expected_consumption_sha256=terminal_identity.consumption_sha256,
            freeze=fixture.freeze,
            attempt_claim=launch.attempt_claim,
            loaded_protocol=launch.loaded_protocol,
            launch_authorization=authorization,
        )


def test_committed_terminal_loader_reconstructs_read_only_authorization(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _launch_fixture(tmp_path)
    prepared = _prepare(fixture)
    descriptor_path, loaded_descriptor = _write_and_commit_g(
        fixture,
        prepared,
    )
    launch = load_prepared_selection_launch(
        descriptor_path,
        expected_descriptor_source_sha256=loaded_descriptor.source_sha256,
        expected_descriptor_canonical_sha256=loaded_descriptor.canonical_sha256,
    )
    authorization = launch.launch_authorization
    assert authorization is not None
    begin_selection_execution(
        fixture.attempt_store,
        freeze=fixture.freeze,
        attempt_claim=launch.attempt_claim,
        loaded_protocol=launch.loaded_protocol,
        launch_authorization=authorization,
    )

    source_summary = QualificationSourceBindingSummary.from_receipt(
        launch.source_binding_receipt
    )
    validation_receipts: list[object] = []
    validation_capabilities: list[object | None] = []

    class FakeQualificationResult:
        loaded_instance: object

        def __init__(self) -> None:
            self.protocol_id = launch.loaded_protocol.protocol.protocol_id
            self.protocol_source_sha256 = launch.loaded_protocol.source_sha256
            self.protocol_canonical_sha256 = launch.loaded_protocol.canonical_sha256
            self.source_binding = source_summary
            self.selection_freeze_artifact_sha256 = fixture.freeze.canonical_sha256
            self.selection_attempt_claim_sha256 = launch.attempt_claim.canonical_sha256
            self.selection_launch_authorization_sha256 = authorization.canonical_sha256

        def to_dict(self) -> dict[str, object]:
            return {
                "kind": "committed-terminal-loader-result",
                "source_binding": self.source_binding.to_dict(),
            }

        @property
        def canonical_bytes(self) -> bytes:
            return qualification_launch.canonical_json_bytes(self.to_dict())

        @property
        def canonical_sha256(self) -> str:
            return qualification_launch.canonical_json_sha256(self.to_dict())

        def validate_against_protocol(
            self,
            supplied_protocol: object,
            *,
            protocol_source_sha256: str,
            source_binding_receipt: object,
            selection_freeze_artifact: object,
            selection_attempt_claim: object,
            selection_launch_authorization_sha256: str | None,
            _historical_reload_capability: object | None = None,
        ) -> None:
            assert supplied_protocol == launch.loaded_protocol.protocol
            assert protocol_source_sha256 == launch.loaded_protocol.source_sha256
            assert selection_freeze_artifact == fixture.freeze
            assert selection_attempt_claim == launch.attempt_claim
            assert (
                selection_launch_authorization_sha256 == authorization.canonical_sha256
            )
            validation_receipts.append(source_binding_receipt)
            validation_capabilities.append(_historical_reload_capability)

        @classmethod
        def from_dict(cls, value: object) -> object:
            instance = cls.loaded_instance
            assert value == instance.to_dict()  # type: ignore[attr-defined]
            return instance

    result = FakeQualificationResult()
    FakeQualificationResult.loaded_instance = result
    monkeypatch.setattr(
        qualification_contracts,
        "QualificationResult",
        FakeQualificationResult,
    )
    consumption, terminal_identity = publish_terminal_selection_consumption(
        fixture.attempt_store,
        consumption_id="committed-terminal-loader-consumption",
        freeze=fixture.freeze,
        attempt_claim=launch.attempt_claim,
        terminal_artifact=result,
        loaded_protocol=launch.loaded_protocol,
        launch_authorization=authorization,
        repository_root=fixture.repository,
        registry_path=fixture.registry_path,
        referent_path=fixture.referent_path,
    )
    _git(
        fixture.repository,
        "add",
        str(
            selection_execution_start_path(
                fixture.attempt_store,
                fixture.freeze,
            ).relative_to(fixture.repository)
        ),
        str(terminal_identity.path.relative_to(fixture.repository)),
    )
    _git(fixture.repository, "commit", "-m", "record committed H terminal")
    changed_module = (
        fixture.repository / launch.source_binding_receipt.modules[0].repository_path
    )
    changed_module.write_bytes(changed_module.read_bytes() + b"\n# successor change\n")
    _git(
        fixture.repository,
        "add",
        changed_module.relative_to(fixture.repository).as_posix(),
    )
    _git(fixture.repository, "commit", "-m", "change current engine successor")

    loaded = load_committed_selection_terminal(
        descriptor_path,
        expected_descriptor_source_sha256=loaded_descriptor.source_sha256,
        expected_descriptor_canonical_sha256=loaded_descriptor.canonical_sha256,
        expected_terminal_manifest_sha256=terminal_identity.manifest_sha256,
        expected_terminal_artifact_sha256=(terminal_identity.terminal_artifact_sha256),
        expected_consumption_sha256=terminal_identity.consumption_sha256,
    )

    assert isinstance(loaded, LoadedCommittedSelectionTerminal)
    assert loaded.launch_authorization == authorization
    assert loaded.terminal_identity == terminal_identity
    assert loaded.consumption == consumption
    assert loaded.terminal_artifact is result
    assert validation_receipts == [
        launch.source_binding_receipt,
        launch.source_binding_receipt,
    ]
    assert validation_capabilities == [
        None,
        qualification_freeze._HISTORICAL_SOURCE_RELOAD_CAPABILITY,
    ]
    assert loaded.launch_authorization.retry_authorized is False
    assert loaded.consumption.reopen_authorized is False
    assert loaded.consumption.retry_authorized is False
    assert loaded.archival_contract_parser_used is True
    assert loaded.historical_d1_recomputation_performed is False
    assert loaded.current_source_compatibility_verified is False
    assert loaded.historical_engine_reexecution_verified is False
    assert not hasattr(loaded, "loaded_protocol")

    with pytest.raises(
        QualificationContractError,
        match="private archived-reload capability",
    ):
        load_terminal_selection_consumption(
            terminal_identity.path,
            expected_manifest_sha256=terminal_identity.manifest_sha256,
            expected_terminal_artifact_sha256=(
                terminal_identity.terminal_artifact_sha256
            ),
            expected_consumption_sha256=terminal_identity.consumption_sha256,
            freeze=fixture.freeze,
            attempt_claim=launch.attempt_claim,
            loaded_protocol=launch.loaded_protocol,
            launch_authorization=authorization,
            _historical_source_binding_receipt=launch.source_binding_receipt,
        )

    with pytest.raises(
        QualificationContractError,
        match="H terminal manifest",
    ):
        load_committed_selection_terminal(
            descriptor_path,
            expected_descriptor_source_sha256=loaded_descriptor.source_sha256,
            expected_descriptor_canonical_sha256=(loaded_descriptor.canonical_sha256),
            expected_terminal_manifest_sha256="0" * 64,
            expected_terminal_artifact_sha256=(
                terminal_identity.terminal_artifact_sha256
            ),
            expected_consumption_sha256=terminal_identity.consumption_sha256,
        )


def test_execution_loader_preserves_preparation_summary_across_successor_commit(
    tmp_path: Path,
) -> None:
    fixture = _launch_fixture(tmp_path)
    prepared = _prepare(fixture)
    preparation_head = prepared.source_readiness_receipt.head_commit
    descriptor_path, loaded_descriptor = _write_and_commit_g(
        fixture,
        prepared,
    )
    successor_head = _git(fixture.repository, "rev-parse", "HEAD")
    assert successor_head != preparation_head

    loaded = load_prepared_selection_launch(
        descriptor_path,
        expected_descriptor_source_sha256=loaded_descriptor.source_sha256,
        expected_descriptor_canonical_sha256=(loaded_descriptor.canonical_sha256),
    )

    assert loaded.source_readiness_receipt.head_commit == preparation_head
    assert loaded.source_binding_receipt.head_commit == successor_head
    assert loaded.descriptor.source_readiness.head_commit == preparation_head
    loaded.descriptor.source_readiness.verify_receipt(loaded.source_readiness_receipt)


def test_execution_loader_rejects_started_or_terminal_attempt(
    tmp_path: Path,
) -> None:
    fixture = _launch_fixture(tmp_path)
    prepared = _prepare(fixture)
    descriptor_path, loaded_descriptor = _write_and_commit_g(
        fixture,
        prepared,
    )
    start_path = selection_execution_start_path(
        fixture.attempt_store,
        fixture.freeze,
    )
    start_path.write_bytes(b"occupied")

    with pytest.raises(QualificationContractError, match="already started"):
        load_prepared_selection_launch(
            descriptor_path,
            expected_descriptor_source_sha256=(loaded_descriptor.source_sha256),
            expected_descriptor_canonical_sha256=(loaded_descriptor.canonical_sha256),
        )


def test_descriptor_rejects_laundered_claim_and_one_shot_constants(
    tmp_path: Path,
) -> None:
    fixture = _launch_fixture(tmp_path)
    prepared = _prepare(fixture)
    document = prepared.descriptor.to_dict()

    document["global_one_shot_proved"] = True
    with pytest.raises(QualificationContractError, match="global_one_shot"):
        PreparedSelectionLaunchDescriptor.from_dict(document)

    document = prepared.descriptor.to_dict()
    document["attempt_store_override_authorized"] = True
    with pytest.raises(
        QualificationContractError,
        match="attempt_store_override",
    ):
        PreparedSelectionLaunchDescriptor.from_dict(document)

    document = prepared.descriptor.to_dict()
    document["attempt_claim_path"] = str(tmp_path / "different-claim.json")
    with pytest.raises(QualificationContractError, match="claim path"):
        PreparedSelectionLaunchDescriptor.from_dict(document)


def test_descriptor_loader_rejects_symlink(tmp_path: Path) -> None:
    fixture = _launch_fixture(tmp_path)
    prepared = _prepare(fixture)
    descriptor_path = tmp_path / "launch.json"
    loaded = write_prepared_selection_launch_descriptor(
        descriptor_path,
        prepared.descriptor,
    )
    symlink_path = tmp_path / "launch-link.json"
    symlink_path.symlink_to(descriptor_path)

    with pytest.raises(QualificationContractError, match="symbolic link"):
        load_prepared_selection_launch_descriptor(
            symlink_path,
            expected_source_sha256=loaded.source_sha256,
            expected_canonical_sha256=loaded.canonical_sha256,
        )
