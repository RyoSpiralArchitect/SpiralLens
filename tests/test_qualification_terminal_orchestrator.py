from __future__ import annotations

import json
import runpy
from pathlib import Path
from types import SimpleNamespace

import pytest

import spirallens.qualification.freeze as qualification_freeze
import spirallens.qualification.runner as qualification_runner
from spirallens.qualification.common import QualificationContractError
from spirallens.qualification.freeze import (
    SelectionFailedAttemptArtifact,
    SelectionFreezeArtifact,
    TerminalAttemptArtifactKind,
    begin_selection_execution,
    claim_selection_attempt,
    load_terminal_selection_consumption,
    selection_execution_start_path,
    terminal_selection_transaction_path,
)
from spirallens.qualification.persistence import LoadedQualificationProtocol


def _companions(
    tmp_path: Path,
) -> tuple[
    LoadedQualificationProtocol,
    SelectionFreezeArtifact,
    object,
]:
    namespace = runpy.run_path(
        Path(__file__).with_name("test_qualification_protocol_hardening.py")
    )
    loaded = namespace["_loaded_protocol"](tmp_path)
    freeze = SelectionFreezeArtifact.from_loaded_protocol(
        freeze_id="terminal-orchestrator-freeze",
        loaded_protocol=loaded,
        seed_family_id="terminal-orchestrator-family",
    )
    claim, _identity = claim_selection_attempt(
        tmp_path,
        claim_id="terminal-orchestrator-claim",
        freeze=freeze,
    )
    return loaded, freeze, claim


def _source_receipt_stub() -> object:
    return SimpleNamespace(
        hypothesis_registry=SimpleNamespace(
            repository_path="protocols/development-registry.yaml"
        ),
        referent_contracts=SimpleNamespace(
            repository_path="protocols/development-referents.json"
        ),
    )


def _not_run_result_companions(
    tmp_path: Path,
) -> tuple[
    LoadedQualificationProtocol,
    SelectionFreezeArtifact,
    object,
    object,
]:
    """Build a typed result and its exact chronology companions without execution."""

    namespace = runpy.run_path(
        Path(__file__).with_name("test_qualification_contracts.py")
    )
    protocol = namespace["_protocol"]()
    result = namespace["_not_run_result"](protocol)
    loaded = LoadedQualificationProtocol(
        protocol=protocol,
        source_path=tmp_path / "not-run-protocol.json",
        source_bytes=protocol.canonical_bytes,
        source_sha256=protocol.canonical_sha256,
        canonical_sha256=protocol.canonical_sha256,
    )
    freeze = SelectionFreezeArtifact.from_loaded_protocol(
        freeze_id="contract-test-freeze",
        loaded_protocol=loaded,
        seed_family_id="contract-test-seeds",
    )
    claim, _identity = claim_selection_attempt(
        tmp_path,
        claim_id="contract-test-attempt",
        freeze=freeze,
    )
    return loaded, freeze, claim, result


def _start_then(
    *,
    selection_freeze_artifact: SelectionFreezeArtifact,
    attempt_claim: object,
    attempt_store_directory: str | Path,
    _execution_started_callback: object,
) -> None:
    begin_selection_execution(
        attempt_store_directory,
        freeze=selection_freeze_artifact,
        attempt_claim=attempt_claim,  # type: ignore[arg-type]
    )
    _execution_started_callback()  # type: ignore[operator]


def test_official_orchestrator_owns_success_publication(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    loaded, freeze, claim = _companions(tmp_path)

    class FakeResult:
        canonical_sha256 = "a" * 64

    result = FakeResult()

    def fake_run(_loaded: object, **kwargs: object) -> FakeResult:
        _start_then(
            selection_freeze_artifact=kwargs["selection_freeze_artifact"],  # type: ignore[arg-type]
            attempt_claim=kwargs["attempt_claim"],
            attempt_store_directory=kwargs["attempt_store_directory"],  # type: ignore[arg-type]
            _execution_started_callback=kwargs["_execution_started_callback"],
        )
        return result

    publication_calls: list[dict[str, object]] = []

    def fake_publish(
        _directory: str | Path,
        **kwargs: object,
    ) -> tuple[str, str]:
        publication_calls.append(kwargs)
        return "consumption", "identity"

    monkeypatch.setattr(qualification_runner, "QualificationResult", FakeResult)
    monkeypatch.setattr(qualification_runner, "run_calibration_selection", fake_run)
    monkeypatch.setattr(
        qualification_runner,
        "_expected_terminal_publication",
        lambda **_kwargs: ("consumption", "identity"),
    )
    monkeypatch.setattr(
        qualification_runner,
        "publish_terminal_selection_consumption",
        fake_publish,
    )

    observed = qualification_runner.run_and_publish_calibration_selection(
        loaded,
        source_binding_receipt=_source_receipt_stub(),  # type: ignore[arg-type]
        selection_freeze_artifact=freeze,
        attempt_claim=claim,
        attempt_store_directory=tmp_path,
    )

    assert observed == (result, "consumption", "identity")
    assert len(publication_calls) == 1
    assert publication_calls[0]["terminal_artifact"] is result
    assert publication_calls[0]["consumption_id"] == (
        f"selection-result-{result.canonical_sha256[:24]}"
    )


def test_pre_start_failure_is_correctable_and_not_terminalized(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    loaded, freeze, claim = _companions(tmp_path)

    def fail_before_start(_loaded: object, **_kwargs: object) -> None:
        raise ValueError("pre-start source verification failed")

    def forbidden_publish(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("pre-start failure must not publish a terminal")

    monkeypatch.setattr(
        qualification_runner,
        "run_calibration_selection",
        fail_before_start,
    )
    monkeypatch.setattr(
        qualification_runner,
        "publish_terminal_selection_consumption",
        forbidden_publish,
    )

    with pytest.raises(
        ValueError,
        match="pre-start source verification failed",
    ):
        qualification_runner.run_and_publish_calibration_selection(
            loaded,
            source_binding_receipt=_source_receipt_stub(),  # type: ignore[arg-type]
            selection_freeze_artifact=freeze,
            attempt_claim=claim,
            attempt_store_directory=tmp_path,
        )

    assert not selection_execution_start_path(tmp_path, freeze).exists()
    assert not terminal_selection_transaction_path(tmp_path, freeze).exists()


def test_preexisting_start_only_store_is_read_only_and_not_retried(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    loaded, freeze, claim = _companions(tmp_path)
    begin_selection_execution(
        tmp_path,
        freeze=freeze,
        attempt_claim=claim,  # type: ignore[arg-type]
    )

    def attempted_retry(_loaded: object, **kwargs: object) -> None:
        _start_then(
            selection_freeze_artifact=kwargs["selection_freeze_artifact"],  # type: ignore[arg-type]
            attempt_claim=kwargs["attempt_claim"],
            attempt_store_directory=kwargs["attempt_store_directory"],  # type: ignore[arg-type]
            _execution_started_callback=kwargs["_execution_started_callback"],
        )

    def forbidden_publish(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("start-only state must not be republished by a retry")

    monkeypatch.setattr(
        qualification_runner,
        "run_calibration_selection",
        attempted_retry,
    )
    monkeypatch.setattr(
        qualification_runner,
        "publish_terminal_selection_consumption",
        forbidden_publish,
    )

    with pytest.raises(QualificationContractError, match="overwrite"):
        qualification_runner.run_and_publish_calibration_selection(
            loaded,
            source_binding_receipt=_source_receipt_stub(),  # type: ignore[arg-type]
            selection_freeze_artifact=freeze,
            attempt_claim=claim,
            attempt_store_directory=tmp_path,
        )

    assert selection_execution_start_path(tmp_path, freeze).is_file()
    assert not terminal_selection_transaction_path(tmp_path, freeze).exists()


def test_after_start_exception_publishes_conservative_failure_then_reraises(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    loaded, freeze, claim = _companions(tmp_path)

    def fail_after_start(_loaded: object, **kwargs: object) -> None:
        _start_then(
            selection_freeze_artifact=kwargs["selection_freeze_artifact"],  # type: ignore[arg-type]
            attempt_claim=kwargs["attempt_claim"],
            attempt_store_directory=kwargs["attempt_store_directory"],  # type: ignore[arg-type]
            _execution_started_callback=kwargs["_execution_started_callback"],
        )
        raise RuntimeError("synthetic execution failure")

    monkeypatch.setattr(
        qualification_runner,
        "run_calibration_selection",
        fail_after_start,
    )

    with pytest.raises(
        RuntimeError,
        match="synthetic execution failure",
    ) as captured:
        qualification_runner.run_and_publish_calibration_selection(
            loaded,
            source_binding_receipt=_source_receipt_stub(),  # type: ignore[arg-type]
            selection_freeze_artifact=freeze,
            attempt_claim=claim,
            attempt_store_directory=tmp_path,
        )

    terminal_path = terminal_selection_transaction_path(tmp_path, freeze)
    terminal_document = json.loads(
        terminal_path.joinpath("terminal-artifact.json").read_text("utf-8")
    )
    failed = SelectionFailedAttemptArtifact.from_dict(terminal_document)
    assert failed.attested_selection_values_observed is True
    assert failed.failure_stage == qualification_runner.ORCHESTRATED_FAILURE_STAGE
    assert failed.failure_evidence_sha256 == (
        qualification_runner._orchestrated_failure_evidence_sha256(
            RuntimeError("synthetic execution failure")
        )
    )
    receipt = getattr(
        captured.value,
        qualification_runner.ORCHESTRATED_TERMINAL_PUBLICATION_RECEIPT_ATTRIBUTE,
    )
    assert isinstance(
        receipt,
        qualification_runner.OrchestratedTerminalPublicationReceipt,
    )
    assert receipt.strict_roundtrip_verified is True
    assert receipt.original_exception_preserved is True
    assert receipt.terminal_artifact_kind is TerminalAttemptArtifactKind.FAILED_ATTEMPT
    assert receipt.publication_call_returned is True
    assert receipt.parent_directory_durability_fsync_proved is True
    assert receipt.retry_authorized is False
    reloaded_consumption, reloaded_failed = load_terminal_selection_consumption(
        receipt.terminal_transaction_path,
        expected_manifest_sha256=receipt.manifest_sha256,
        expected_terminal_artifact_sha256=receipt.terminal_artifact_sha256,
        expected_consumption_sha256=receipt.consumption_sha256,
        freeze=freeze,
        attempt_claim=claim,  # type: ignore[arg-type]
    )
    assert reloaded_failed == failed
    assert (
        reloaded_consumption.terminal_artifact_sha256
        == receipt.terminal_artifact_sha256
    )
    assert any(
        note.startswith("spirallens_terminal_publication_receipt=")
        for note in captured.value.__notes__
    )


def test_failed_terminal_rename_then_parent_fsync_error_strictly_recovers(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    loaded, freeze, claim = _companions(tmp_path)

    def fail_after_start(_loaded: object, **kwargs: object) -> None:
        _start_then(
            selection_freeze_artifact=kwargs["selection_freeze_artifact"],  # type: ignore[arg-type]
            attempt_claim=kwargs["attempt_claim"],
            attempt_store_directory=kwargs["attempt_store_directory"],  # type: ignore[arg-type]
            _execution_started_callback=kwargs["_execution_started_callback"],
        )
        raise RuntimeError("failure before terminal recovery")

    original_fsync = qualification_freeze._fsync_directory
    terminal_path = terminal_selection_transaction_path(tmp_path, freeze)

    def fail_parent_fsync_after_rename(path: Path) -> None:
        if path == tmp_path and terminal_path.is_dir():
            raise OSError("injected post-rename parent fsync failure")
        original_fsync(path)

    monkeypatch.setattr(
        qualification_runner,
        "run_calibration_selection",
        fail_after_start,
    )
    monkeypatch.setattr(
        qualification_freeze,
        "_fsync_directory",
        fail_parent_fsync_after_rename,
    )

    with pytest.raises(
        RuntimeError,
        match="failure before terminal recovery",
    ) as captured:
        qualification_runner.run_and_publish_calibration_selection(
            loaded,
            source_binding_receipt=_source_receipt_stub(),  # type: ignore[arg-type]
            selection_freeze_artifact=freeze,
            attempt_claim=claim,
            attempt_store_directory=tmp_path,
        )

    receipt = getattr(
        captured.value,
        qualification_runner.ORCHESTRATED_TERMINAL_PUBLICATION_RECEIPT_ATTRIBUTE,
    )
    assert receipt.strict_roundtrip_verified is True
    assert receipt.terminal_artifact_kind is TerminalAttemptArtifactKind.FAILED_ATTEMPT
    assert receipt.publication_call_returned is False
    assert receipt.parent_directory_durability_fsync_proved is False
    assert receipt.retry_authorized is False
    loaded_consumption, loaded_failed = load_terminal_selection_consumption(
        receipt.terminal_transaction_path,
        expected_manifest_sha256=receipt.manifest_sha256,
        expected_terminal_artifact_sha256=receipt.terminal_artifact_sha256,
        expected_consumption_sha256=receipt.consumption_sha256,
        freeze=freeze,
        attempt_claim=claim,  # type: ignore[arg-type]
    )
    assert loaded_failed.canonical_sha256 == receipt.terminal_artifact_sha256
    assert loaded_consumption.canonical_sha256 == receipt.consumption_sha256
    assert any(
        "parent-directory durability fsync is not proved" in note
        for note in captured.value.__notes__
    )


def test_result_terminal_rename_then_parent_fsync_error_strictly_recovers(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    loaded, freeze, claim, result = _not_run_result_companions(tmp_path)

    def return_result_after_start(_loaded: object, **kwargs: object) -> object:
        _start_then(
            selection_freeze_artifact=kwargs["selection_freeze_artifact"],  # type: ignore[arg-type]
            attempt_claim=kwargs["attempt_claim"],
            attempt_store_directory=kwargs["attempt_store_directory"],  # type: ignore[arg-type]
            _execution_started_callback=kwargs["_execution_started_callback"],
        )
        return result

    original_fsync = qualification_freeze._fsync_directory
    terminal_path = terminal_selection_transaction_path(tmp_path, freeze)

    def fail_parent_fsync_after_rename(path: Path) -> None:
        if path == tmp_path and terminal_path.is_dir():
            raise OSError("injected result post-rename parent fsync failure")
        original_fsync(path)

    monkeypatch.setattr(
        qualification_runner,
        "run_calibration_selection",
        return_result_after_start,
    )
    monkeypatch.setattr(
        qualification_freeze,
        "_validate_terminal_result_against_live_sources",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        qualification_freeze,
        "_fsync_directory",
        fail_parent_fsync_after_rename,
    )

    with pytest.raises(
        OSError,
        match="injected result post-rename parent fsync failure",
    ) as captured:
        qualification_runner.run_and_publish_calibration_selection(
            loaded,
            source_binding_receipt=_source_receipt_stub(),  # type: ignore[arg-type]
            selection_freeze_artifact=freeze,
            attempt_claim=claim,
            attempt_store_directory=tmp_path,
        )

    receipt = getattr(
        captured.value,
        qualification_runner.ORCHESTRATED_TERMINAL_PUBLICATION_RECEIPT_ATTRIBUTE,
    )
    assert receipt.strict_roundtrip_verified is True
    assert receipt.terminal_artifact_kind is TerminalAttemptArtifactKind.RESULT
    assert receipt.terminal_artifact_sha256 == result.canonical_sha256
    assert receipt.publication_call_returned is False
    assert receipt.parent_directory_durability_fsync_proved is False
    assert receipt.retry_authorized is False
    loaded_consumption, loaded_result = load_terminal_selection_consumption(
        receipt.terminal_transaction_path,
        expected_manifest_sha256=receipt.manifest_sha256,
        expected_terminal_artifact_sha256=receipt.terminal_artifact_sha256,
        expected_consumption_sha256=receipt.consumption_sha256,
        freeze=freeze,
        attempt_claim=claim,  # type: ignore[arg-type]
    )
    assert loaded_result == result
    assert (
        loaded_consumption.terminal_artifact_sha256 == receipt.terminal_artifact_sha256
    )
    assert any(
        "parent-directory durability fsync is not proved" in note
        for note in captured.value.__notes__
    )


def test_result_publication_failure_is_closed_as_failure_without_replacement(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    loaded, freeze, claim = _companions(tmp_path)

    class FakeResult:
        canonical_sha256 = "b" * 64

    result = FakeResult()

    def fake_run(_loaded: object, **kwargs: object) -> FakeResult:
        _start_then(
            selection_freeze_artifact=kwargs["selection_freeze_artifact"],  # type: ignore[arg-type]
            attempt_claim=kwargs["attempt_claim"],
            attempt_store_directory=kwargs["attempt_store_directory"],  # type: ignore[arg-type]
            _execution_started_callback=kwargs["_execution_started_callback"],
        )
        return result

    real_publish = qualification_runner.publish_terminal_selection_consumption
    real_expected = qualification_runner._expected_terminal_publication
    publication_artifacts: list[object] = []

    def fail_result_then_publish_failure(
        directory: str | Path,
        **kwargs: object,
    ) -> object:
        terminal_artifact = kwargs["terminal_artifact"]
        publication_artifacts.append(terminal_artifact)
        if terminal_artifact is result:
            raise OSError("synthetic result publication failure")
        return real_publish(directory, **kwargs)

    def fake_result_expected_then_real_failure(**kwargs: object) -> object:
        if kwargs["terminal_artifact"] is result:
            return "expected-result-consumption", "expected-result-identity"
        return real_expected(**kwargs)

    monkeypatch.setattr(qualification_runner, "QualificationResult", FakeResult)
    monkeypatch.setattr(qualification_runner, "run_calibration_selection", fake_run)
    monkeypatch.setattr(
        qualification_runner,
        "_expected_terminal_publication",
        fake_result_expected_then_real_failure,
    )
    monkeypatch.setattr(
        qualification_runner,
        "publish_terminal_selection_consumption",
        fail_result_then_publish_failure,
    )

    with pytest.raises(
        OSError,
        match="synthetic result publication failure",
    ):
        qualification_runner.run_and_publish_calibration_selection(
            loaded,
            source_binding_receipt=_source_receipt_stub(),  # type: ignore[arg-type]
            selection_freeze_artifact=freeze,
            attempt_claim=claim,
            attempt_store_directory=tmp_path,
        )

    assert len(publication_artifacts) == 2
    assert publication_artifacts[0] is result
    assert isinstance(publication_artifacts[1], SelectionFailedAttemptArtifact)
    assert terminal_selection_transaction_path(tmp_path, freeze).is_dir()


def test_completed_publication_error_does_not_attempt_second_terminal(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    loaded, freeze, claim = _companions(tmp_path)

    class FakeResult:
        canonical_sha256 = "c" * 64

    result = FakeResult()

    def fake_run(_loaded: object, **kwargs: object) -> FakeResult:
        _start_then(
            selection_freeze_artifact=kwargs["selection_freeze_artifact"],  # type: ignore[arg-type]
            attempt_claim=kwargs["attempt_claim"],
            attempt_store_directory=kwargs["attempt_store_directory"],  # type: ignore[arg-type]
            _execution_started_callback=kwargs["_execution_started_callback"],
        )
        return result

    publication_count = 0

    def publish_then_raise(
        directory: str | Path,
        **_kwargs: object,
    ) -> None:
        nonlocal publication_count
        publication_count += 1
        terminal_selection_transaction_path(directory, freeze).mkdir()
        raise OSError("post-publication durability failure")

    monkeypatch.setattr(qualification_runner, "QualificationResult", FakeResult)
    monkeypatch.setattr(qualification_runner, "run_calibration_selection", fake_run)
    monkeypatch.setattr(
        qualification_runner,
        "_expected_terminal_publication",
        lambda **_kwargs: ("expected-result-consumption", "expected-result-identity"),
    )
    monkeypatch.setattr(
        qualification_runner,
        "publish_terminal_selection_consumption",
        publish_then_raise,
    )

    with pytest.raises(OSError, match="post-publication durability failure"):
        qualification_runner.run_and_publish_calibration_selection(
            loaded,
            source_binding_receipt=_source_receipt_stub(),  # type: ignore[arg-type]
            selection_freeze_artifact=freeze,
            attempt_claim=claim,
            attempt_store_directory=tmp_path,
        )

    assert publication_count == 1
