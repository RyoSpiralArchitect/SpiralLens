from __future__ import annotations

import errno
import os
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

import pytest

import spirallens
import test_d7_confirmation_attempt_evidence as evidence_fixtures
import test_d7_confirmation_attempt_persistence as prefix_fixtures
import test_d7_confirmation_result_components as component_fixtures
from spirallens import qualification
from spirallens.qualification import confirmation_attempt_records as r
from spirallens.qualification import confirmation_attempt_terminal_persistence as tp
from spirallens.qualification import confirmation_attempt_validation as v
from spirallens.qualification.common import QualificationContractError


@dataclass(frozen=True)
class _Transaction:
    prefix_values: SimpleNamespace
    loaded_prefix: object
    sources: dict[str, bytes]
    manifest: r.D7TerminalManifestRecord
    consumption: r.D7TerminalConsumptionRecord
    artifact: r.D7ScientificResultRecord | r.D7FailedAttemptRecord


@pytest.fixture(scope="module")
def component_bundle() -> object:
    return component_fixtures.bundle.__wrapped__()


def _failed_transaction(directory: Path) -> _Transaction:
    prefix = prefix_fixtures._prefix(directory)
    loaded = prefix_fixtures._persist(prefix)
    failure = evidence_fixtures._in_process_failure(prefix)
    manifest = r.D7TerminalManifestRecord(
        replay_target_sha256=prefix.start.replay_target_sha256,
        attempt_key_sha256=prefix.start.attempt_key_sha256,
        attempt_claim_sha256=prefix.claim.canonical_sha256,
        execution_start_sha256=prefix.start.canonical_sha256,
        execution_identity_receipt_sha256=(
            prefix.start.execution_identity_receipt_sha256
        ),
        terminal_artifact_kind=r.D7TerminalArtifactKind.FAILED_ATTEMPT,
        terminal_artifact_sha256=failure.failed.canonical_sha256,
        immutable_members=v._failure_members(
            failure.evidence,
            failure.failed,
            None,
        ),
    )
    consumption = r.D7TerminalConsumptionRecord(
        replay_target_sha256=prefix.start.replay_target_sha256,
        attempt_key_sha256=prefix.start.attempt_key_sha256,
        attempt_claim_sha256=prefix.claim.canonical_sha256,
        execution_start_sha256=prefix.start.canonical_sha256,
        execution_identity_receipt_sha256=(
            prefix.start.execution_identity_receipt_sha256
        ),
        terminal_manifest_sha256=manifest.canonical_sha256,
        terminal_artifact_kind=r.D7TerminalArtifactKind.FAILED_ATTEMPT,
        terminal_artifact_sha256=failure.failed.canonical_sha256,
        confirmation_value_access_state=(
            failure.failed.confirmation_value_access_state
        ),
    )
    return _Transaction(
        prefix_values=prefix,
        loaded_prefix=loaded,
        sources={
            r.D7_FAILED_ATTEMPT_FILENAME: failure.failed.canonical_bytes,
            r.D7_FAILURE_EVIDENCE_FILENAME: failure.evidence.canonical_bytes,
            r.D7_FAILURE_EVIDENCE_PAYLOAD_FILENAME: failure.payload.canonical_bytes,
        },
        manifest=manifest,
        consumption=consumption,
        artifact=failure.failed,
    )


def _scientific_transaction(directory: Path, bundle: object) -> _Transaction:
    prefix = prefix_fixtures._prefix(directory)
    loaded = prefix_fixtures._persist(prefix)
    payload = bundle.result
    result = r.D7ScientificResultRecord(
        replay_target_sha256=prefix.start.replay_target_sha256,
        attempt_key_sha256=prefix.start.attempt_key_sha256,
        execution_start_sha256=prefix.start.canonical_sha256,
        execution_identity_receipt_sha256=(
            prefix.start.execution_identity_receipt_sha256
        ),
        result_payload_sha256=payload.canonical_sha256,
        result_payload_byte_count=len(payload.canonical_bytes),
    )
    manifest = r.D7TerminalManifestRecord(
        replay_target_sha256=prefix.start.replay_target_sha256,
        attempt_key_sha256=prefix.start.attempt_key_sha256,
        attempt_claim_sha256=prefix.claim.canonical_sha256,
        execution_start_sha256=prefix.start.canonical_sha256,
        execution_identity_receipt_sha256=(
            prefix.start.execution_identity_receipt_sha256
        ),
        terminal_artifact_kind=r.D7TerminalArtifactKind.SCIENTIFIC_RESULT,
        terminal_artifact_sha256=result.canonical_sha256,
        immutable_members=v._scientific_members(payload, result),
    )
    consumption = r.D7TerminalConsumptionRecord(
        replay_target_sha256=prefix.start.replay_target_sha256,
        attempt_key_sha256=prefix.start.attempt_key_sha256,
        attempt_claim_sha256=prefix.claim.canonical_sha256,
        execution_start_sha256=prefix.start.canonical_sha256,
        execution_identity_receipt_sha256=(
            prefix.start.execution_identity_receipt_sha256
        ),
        terminal_manifest_sha256=manifest.canonical_sha256,
        terminal_artifact_kind=r.D7TerminalArtifactKind.SCIENTIFIC_RESULT,
        terminal_artifact_sha256=result.canonical_sha256,
        confirmation_value_access_state=(r.D7ConfirmationValueAccessState.OBSERVED),
    )
    components = (
        bundle.event,
        bundle.core,
        bundle.loop,
        bundle.primary,
        bundle.strata,
        bundle.gates,
    )
    return _Transaction(
        prefix_values=prefix,
        loaded_prefix=loaded,
        sources={
            r.D7_SCIENTIFIC_RESULT_FILENAME: result.canonical_bytes,
            r.D7_SCIENTIFIC_RESULT_PAYLOAD_FILENAME: payload.canonical_bytes,
            **{
                f"result-{component.component_id.value}.json": (
                    component.canonical_bytes
                )
                for component in components
            },
        },
        manifest=manifest,
        consumption=consumption,
        artifact=result,
    )


def _external_transaction(directory: Path) -> _Transaction:
    prefix = prefix_fixtures._prefix(directory)
    loaded = prefix_fixtures._persist(prefix)
    signed_witness = evidence_fixtures._signed_external_witness(prefix)
    failure = signed_witness.failure
    manifest = r.D7TerminalManifestRecord(
        replay_target_sha256=prefix.start.replay_target_sha256,
        attempt_key_sha256=prefix.start.attempt_key_sha256,
        attempt_claim_sha256=prefix.claim.canonical_sha256,
        execution_start_sha256=prefix.start.canonical_sha256,
        execution_identity_receipt_sha256=(
            prefix.start.execution_identity_receipt_sha256
        ),
        terminal_artifact_kind=r.D7TerminalArtifactKind.FAILED_ATTEMPT,
        terminal_artifact_sha256=failure.failed.canonical_sha256,
        immutable_members=v._failure_members(
            failure.evidence,
            failure.failed,
            failure.finalization,
        ),
    )
    consumption = r.D7TerminalConsumptionRecord(
        replay_target_sha256=prefix.start.replay_target_sha256,
        attempt_key_sha256=prefix.start.attempt_key_sha256,
        attempt_claim_sha256=prefix.claim.canonical_sha256,
        execution_start_sha256=prefix.start.canonical_sha256,
        execution_identity_receipt_sha256=(
            prefix.start.execution_identity_receipt_sha256
        ),
        terminal_manifest_sha256=manifest.canonical_sha256,
        terminal_artifact_kind=r.D7TerminalArtifactKind.FAILED_ATTEMPT,
        terminal_artifact_sha256=failure.failed.canonical_sha256,
        confirmation_value_access_state=(
            failure.failed.confirmation_value_access_state
        ),
    )
    return _Transaction(
        prefix_values=prefix,
        loaded_prefix=loaded,
        sources={
            r.D7_FAILED_ATTEMPT_FILENAME: failure.failed.canonical_bytes,
            r.D7_FAILURE_EVIDENCE_FILENAME: failure.evidence.canonical_bytes,
            r.D7_FAILURE_EVIDENCE_PAYLOAD_FILENAME: failure.payload.canonical_bytes,
            r.D7_EXTERNAL_ABORT_VERIFICATION_RECEIPT_FILENAME: (
                failure.receipt.canonical_bytes
            ),
            r.D7_SIGNED_EXTERNAL_ABORT_WITNESS_ENVELOPE_FILENAME: (
                signed_witness.envelope.canonical_bytes
            ),
            r.D7_STARTED_UNRESOLVED_FINALIZATION_FILENAME: (
                failure.finalization.canonical_bytes
            ),
        },
        manifest=manifest,
        consumption=consumption,
        artifact=failure.failed,
    )


def _persist(transaction: _Transaction) -> tp.D7PersistedStructuralTerminalIdentity:
    return tp.persist_d7_structural_terminal_transaction_no_replace(
        transaction.loaded_prefix,  # type: ignore[arg-type]
        immutable_member_sources=transaction.sources,
        manifest=transaction.manifest,
        consumption=transaction.consumption,
    )


def _load(transaction: _Transaction) -> tp.D7LoadedStructuralTerminalTransaction:
    return tp.load_d7_structural_terminal_transaction(
        transaction.loaded_prefix,  # type: ignore[arg-type]
        expected_manifest_sha256=transaction.manifest.canonical_sha256,
        expected_consumption_sha256=transaction.consumption.canonical_sha256,
    )


def test_ordinary_failed_terminal_is_atomic_strict_and_non_authorizing(
    tmp_path: Path,
) -> None:
    transaction = _failed_transaction(tmp_path)
    identity = _persist(transaction)
    loaded = _load(transaction)

    assert identity.path == tmp_path / "primary-terminal"
    assert identity.terminal_artifact_sha256 == transaction.artifact.canonical_sha256
    assert identity.parent_directory_fsync_proved is True
    assert identity.atomic_no_replace is True
    assert identity.authority_granted is False
    assert identity.execution_observed is False
    assert identity.scientific_claim_eligible is False
    assert identity.retry_authorized is False
    assert identity.replay_authorized is False
    assert identity.d8_eligible is False
    assert loaded.terminal_artifact == transaction.artifact
    assert loaded.manifest == transaction.manifest
    assert loaded.consumption == transaction.consumption
    assert loaded.terminal_structure_validated is True
    assert loaded.authority_granted is False
    assert loaded.execution_observed is False
    assert loaded.started_unresolved_established is False
    assert loaded.external_abort_authenticated is False
    assert loaded.external_abort_finalized is False
    assert loaded.scientific_claim_eligible is False
    assert set(item.name for item in identity.path.iterdir()) == {
        *transaction.sources,
        r.D7_TERMINAL_MANIFEST_FILENAME,
        r.D7_TERMINAL_CONSUMPTION_FILENAME,
    }
    before = {
        path.name: path.read_bytes()
        for path in identity.path.iterdir()
        if path.is_file()
    }
    with pytest.raises(QualificationContractError, match="replace existing"):
        _persist(transaction)
    assert {
        path.name: path.read_bytes()
        for path in identity.path.iterdir()
        if path.is_file()
    } == before


def test_complete_scientific_component_transaction_round_trips(
    tmp_path: Path,
    component_bundle: object,
) -> None:
    transaction = _scientific_transaction(tmp_path, component_bundle)
    identity = _persist(transaction)
    loaded = _load(transaction)

    assert identity.terminal_artifact_kind is r.D7TerminalArtifactKind.SCIENTIFIC_RESULT
    assert loaded.terminal_artifact == transaction.artifact
    assert len(loaded.immutable_member_sources) == 8
    assert set(loaded.immutable_member_sources) == set(transaction.sources)
    assert (
        loaded.consumption.confirmation_value_access_state
        is r.D7ConfirmationValueAccessState.OBSERVED
    )
    assert len(tuple(identity.path.iterdir())) == 10


def test_preflight_tamper_fails_and_external_abort_stays_structural_only(
    tmp_path: Path,
) -> None:
    tamper_store = tmp_path / "tamper"
    tamper_store.mkdir()
    tampered = _failed_transaction(tamper_store)
    altered = dict(tampered.sources)
    altered[r.D7_FAILURE_EVIDENCE_PAYLOAD_FILENAME] += b" "
    with pytest.raises(QualificationContractError, match="manifest identity"):
        tp.persist_d7_structural_terminal_transaction_no_replace(
            tampered.loaded_prefix,  # type: ignore[arg-type]
            immutable_member_sources=altered,
            manifest=tampered.manifest,
            consumption=tampered.consumption,
        )
    assert not (tamper_store / "primary-terminal").exists()
    assert not tuple(tamper_store.glob(".*.tmp"))

    external_store = tmp_path / "external"
    external_store.mkdir()
    external = _external_transaction(external_store)
    identity = _persist(external)
    loaded = _load(external)
    assert identity.path == external_store / "primary-terminal"
    assert loaded.terminal_artifact == external.artifact
    assert loaded.external_abort_authenticated is False
    assert loaded.external_abort_finalized is False
    assert loaded.authority_granted is False
    assert not tuple(external_store.glob(".*.tmp"))


@pytest.mark.parametrize("entry_kind", ("file", "directory", "symlink"))
def test_existing_terminal_entry_of_any_kind_is_never_replaced(
    tmp_path: Path,
    entry_kind: str,
) -> None:
    transaction = _failed_transaction(tmp_path)
    terminal = tmp_path / "primary-terminal"
    if entry_kind == "file":
        terminal.write_bytes(b"existing")
    elif entry_kind == "directory":
        terminal.mkdir()
        (terminal / "sentinel").write_bytes(b"existing")
    else:
        terminal.symlink_to(tmp_path / "missing")

    with pytest.raises(QualificationContractError, match="replace existing"):
        _persist(transaction)
    if entry_kind == "file":
        assert terminal.read_bytes() == b"existing"
    elif entry_kind == "directory":
        assert (terminal / "sentinel").read_bytes() == b"existing"
    else:
        assert terminal.is_symlink()


def test_attempt_scoped_staging_orphan_blocks_retry_until_offline_recovery(
    tmp_path: Path,
) -> None:
    transaction = _failed_transaction(tmp_path)
    stage = tmp_path / (
        f"{tp._staging_prefix(transaction.prefix_values.start.attempt_key_sha256)}"
        f"crash{tp._TEMPORARY_SUFFIX}"
    )
    stage.mkdir()
    (stage / "partial").write_bytes(b"partial")

    with pytest.raises(QualificationContractError, match="offline recovery"):
        _persist(transaction)
    with pytest.raises(QualificationContractError, match="offline recovery"):
        _load(transaction)
    assert stage.is_dir()
    assert not (tmp_path / "primary-terminal").exists()


@pytest.mark.parametrize(
    "mutation",
    ("extra", "missing", "tamper", "symlink", "hardlink", "fifo"),
)
def test_strict_loader_rejects_closed_inventory_and_alias_violations(
    tmp_path: Path,
    mutation: str,
) -> None:
    transaction = _failed_transaction(tmp_path)
    identity = _persist(transaction)
    payload = identity.path / r.D7_FAILURE_EVIDENCE_PAYLOAD_FILENAME
    if mutation == "extra":
        (identity.path / "extra.json").write_bytes(b"{}")
    elif mutation == "missing":
        payload.unlink()
    elif mutation == "tamper":
        payload.write_bytes(b"{}")
    elif mutation == "symlink":
        payload.unlink()
        payload.symlink_to(identity.path / r.D7_FAILURE_EVIDENCE_FILENAME)
    elif mutation == "hardlink":
        os.link(payload, tmp_path / "outside-hardlink.json")
    else:
        assert tp.p._file_read_flags() & os.O_NONBLOCK
        payload.unlink()
        os.mkfifo(payload)

    with pytest.raises(QualificationContractError):
        _load(transaction)


def test_loader_rejects_same_name_replacement_during_validation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    transaction = _failed_transaction(tmp_path)
    identity = _persist(transaction)
    target = identity.path / r.D7_FAILURE_EVIDENCE_PAYLOAD_FILENAME
    original = target.read_bytes()
    real_validate = tp._validate_transaction_sources
    replaced = False

    def validate_then_replace(*args: object, **kwargs: object) -> object:
        nonlocal replaced
        result = real_validate(*args, **kwargs)
        if not replaced:
            replaced = True
            target.unlink()
            target.write_bytes(original)
        return result

    monkeypatch.setattr(tp, "_validate_transaction_sources", validate_then_replace)
    with pytest.raises(QualificationContractError, match="changed during"):
        _load(transaction)


def test_stage_mutation_is_rejected_before_publication(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    transaction = _failed_transaction(tmp_path)
    real_revalidate = tp._revalidate_file_set
    mutated = False

    def mutate_stage_then_revalidate(
        directory: object,
        expected: object,
    ) -> None:
        nonlocal mutated
        path = directory.path  # type: ignore[attr-defined]
        if not mutated and ".d7-terminal-transaction." in path.name:
            mutated = True
            target = path / r.D7_FAILURE_EVIDENCE_PAYLOAD_FILENAME
            target.write_bytes(b"{}")
        real_revalidate(directory, expected)  # type: ignore[arg-type]

    monkeypatch.setattr(tp, "_revalidate_file_set", mutate_stage_then_revalidate)
    with pytest.raises(QualificationContractError):
        _persist(transaction)
    assert mutated is True
    assert not (tmp_path / "primary-terminal").exists()
    assert not tuple(tmp_path.glob(".*.tmp"))


def test_concurrent_writers_have_one_complete_no_replace_winner(
    tmp_path: Path,
) -> None:
    transaction = _failed_transaction(tmp_path)

    def publish() -> object:
        try:
            return _persist(transaction)
        except QualificationContractError as error:
            return error

    with ThreadPoolExecutor(max_workers=8) as executor:
        outcomes = tuple(executor.map(lambda _index: publish(), range(8)))
    winners = tuple(
        value
        for value in outcomes
        if type(value) is tp.D7PersistedStructuralTerminalIdentity
    )
    losers = tuple(
        value for value in outcomes if type(value) is QualificationContractError
    )
    assert len(winners) == 1
    assert len(losers) == 7
    assert _load(transaction).terminal_artifact == transaction.artifact
    assert not tuple(tmp_path.glob(".*.tmp"))


def test_rename_success_followed_by_error_recovers_the_owned_directory(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    transaction = _failed_transaction(tmp_path)
    real_rename = tp._rename_stage_no_replace

    def rename_then_error(
        parent: object,
        stage_leaf: str,
        terminal_leaf: str,
    ) -> None:
        real_rename(parent, stage_leaf, terminal_leaf)  # type: ignore[arg-type]
        raise OSError(errno.EIO, "injected ambiguous rename result")

    monkeypatch.setattr(tp, "_rename_stage_no_replace", rename_then_error)
    identity = _persist(transaction)

    assert identity.path.is_dir()
    assert identity.parent_directory_fsync_proved is True
    assert _load(transaction).terminal_artifact == transaction.artifact
    assert not tuple(tmp_path.glob(".*.tmp"))


def test_post_rename_parent_fsync_failure_is_visible_reloadable_and_not_durable(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    transaction = _failed_transaction(tmp_path)
    real_rename = tp._rename_stage_no_replace
    real_fsync = tp.os.fsync
    renamed = False
    failed = False

    def mark_rename(
        parent: object,
        stage_leaf: str,
        terminal_leaf: str,
    ) -> None:
        nonlocal renamed
        real_rename(parent, stage_leaf, terminal_leaf)  # type: ignore[arg-type]
        renamed = True

    def fail_after_rename(descriptor: int) -> None:
        nonlocal failed
        if renamed and not failed:
            failed = True
            raise OSError("injected terminal parent fsync failure")
        real_fsync(descriptor)

    monkeypatch.setattr(tp, "_rename_stage_no_replace", mark_rename)
    monkeypatch.setattr(tp.os, "fsync", fail_after_rename)
    identity = _persist(transaction)

    assert identity.path.is_dir()
    assert identity.parent_directory_fsync_proved is False
    assert _load(transaction).terminal_artifact == transaction.artifact
    with pytest.raises(QualificationContractError, match="replace existing"):
        _persist(transaction)


def test_uncertain_staging_cleanup_is_retained_and_blocks_retry(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    transaction = _failed_transaction(tmp_path)
    real_write = tp._write_stage_file
    failed = False

    def write_then_crash(
        stage: object,
        filename: str,
        source: bytes,
        **kwargs: object,
    ) -> tuple[int, int]:
        nonlocal failed
        identity = real_write(
            stage,  # type: ignore[arg-type]
            filename,
            source,
            **kwargs,  # type: ignore[arg-type]
        )
        if not failed:
            failed = True
            raise OSError("injected interruption after durable member staging")
        return identity

    monkeypatch.setattr(tp, "_write_stage_file", write_then_crash)
    with pytest.raises(QualificationContractError, match="offline recovery"):
        _persist(transaction)

    staged = tuple(tmp_path.glob(".*.tmp"))
    assert len(staged) == 1
    assert not (tmp_path / "primary-terminal").exists()
    monkeypatch.setattr(tp, "_write_stage_file", real_write)
    with pytest.raises(QualificationContractError, match="offline recovery"):
        _persist(transaction)


def test_cleanup_exception_still_closes_terminal_parent_descriptor(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    transaction = _failed_transaction(tmp_path)
    real_open_parent = tp._open_terminal_parent
    real_write = tp._write_stage_file
    captured_descriptor: int | None = None
    failed = False

    def capture_parent(*args: object, **kwargs: object) -> object:
        nonlocal captured_descriptor
        result = real_open_parent(*args, **kwargs)
        captured_descriptor = result[0].descriptor
        return result

    def write_then_fail(
        *args: object,
        **kwargs: object,
    ) -> tuple[int, int]:
        nonlocal failed
        identity = real_write(*args, **kwargs)
        if not failed:
            failed = True
            raise OSError("injected write-tail failure")
        return identity

    def cleanup_crash(*args: object, **kwargs: object) -> bool:
        raise OSError("injected cleanup-stat failure")

    monkeypatch.setattr(tp, "_open_terminal_parent", capture_parent)
    monkeypatch.setattr(tp, "_write_stage_file", write_then_fail)
    monkeypatch.setattr(tp, "_cleanup_stage", cleanup_crash)
    with pytest.raises(QualificationContractError, match="offline recovery"):
        _persist(transaction)

    assert captured_descriptor is not None
    with pytest.raises(OSError):
        os.fstat(captured_descriptor)


def test_module_remains_deep_internal_and_emits_no_capability() -> None:
    assert tp.__all__ == ()
    assert not hasattr(spirallens, "D7LoadedStructuralTerminalTransaction")
    assert not hasattr(qualification, "D7LoadedStructuralTerminalTransaction")
    assert not hasattr(tp, "run_d7_confirmation")
    assert not hasattr(tp, "invoke_d7_seed_supplier")
    assert not hasattr(tp, "authorize_d7_fused_start")
    assert not hasattr(tp, "finalize_d7_started_unresolved")
