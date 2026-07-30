from __future__ import annotations

import errno
import hashlib
import os
import shutil
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from spirallens.core.canonical import (
    canonical_json_bytes,
    parse_canonical_json,
    sha256_bytes,
)
from spirallens.qualification import confirmation_attempt_evidence as e
from spirallens.qualification import confirmation_attempt_persistence as p
from spirallens.qualification import confirmation_attempt_records as r
from spirallens.qualification.common import QualificationContractError


def _h(label: str) -> str:
    return hashlib.sha256(label.encode()).hexdigest()


def _prefix(
    directory: Path,
    *,
    output_leaf: str = "primary-output",
    terminal_leaf: str = "primary-terminal",
) -> SimpleNamespace:
    store = Path(os.path.realpath(directory))
    observed_parent = store.stat()
    store_identity = _h("store-identity")
    output_identity = e.d7_path_identity_sha256(
        store_identity_sha256=store_identity,
        resolved_parent_realpath=str(store),
        subject_basename=output_leaf,
    )
    terminal_identity = e.d7_path_identity_sha256(
        store_identity_sha256=store_identity,
        resolved_parent_realpath=str(store),
        subject_basename=terminal_leaf,
    )
    declaration = r.D7AttemptDeclarationRecord(
        replay_target_sha256=_h("target"),
        launch_intent_sha256=_h("intent"),
        role_evidence=r.D7PrimaryRoleEvidence(),
        store_identity_sha256=store_identity,
        output_namespace_identity_sha256=output_identity,
        terminal_path_identity_sha256=terminal_identity,
        authorization_commit="a" * 40,
        execution_identity_receipt_sha256=_h("execution-identity"),
    )

    def authorization_receipt(
        *,
        subject: e.D7AbsentPathSubject,
        identity: str,
        leaf: str,
    ) -> e.D7AuthorizationPathAbsenceReceipt:
        return e.D7AuthorizationPathAbsenceReceipt(
            subject_kind=subject,
            replay_target_sha256=declaration.replay_target_sha256,
            attempt_key_sha256=declaration.attempt_key_sha256,
            attempt_declaration_sha256=declaration.canonical_sha256,
            authorization_commit=declaration.authorization_commit,
            execution_identity_receipt_sha256=(
                declaration.execution_identity_receipt_sha256
            ),
            store_identity_sha256=declaration.store_identity_sha256,
            subject_path_identity_sha256=identity,
            store_root_realpath=str(store),
            resolved_parent_realpath=str(store),
            subject_basename=leaf,
            parent_device=observed_parent.st_dev,
            parent_inode=observed_parent.st_ino,
        )

    authorization_output = authorization_receipt(
        subject=e.D7AbsentPathSubject.OUTPUT_NAMESPACE,
        identity=output_identity,
        leaf=output_leaf,
    )
    authorization_terminal = authorization_receipt(
        subject=e.D7AbsentPathSubject.TERMINAL_PATH,
        identity=terminal_identity,
        leaf=terminal_leaf,
    )
    authorization = r.D7LaunchAuthorizationRecord(
        attempt_declaration_sha256=declaration.canonical_sha256,
        replay_target_sha256=declaration.replay_target_sha256,
        attempt_key_sha256=declaration.attempt_key_sha256,
        authorization_commit=declaration.authorization_commit,
        execution_identity_receipt_sha256=(
            declaration.execution_identity_receipt_sha256
        ),
        execution_source_runtime_receipt_sha256=_h("source-runtime"),
        runtime_specification_sha256=_h("runtime-specification"),
        admission_receipt_sha256=_h("admission"),
        full_design_freeze_receipt_sha256=_h("full-design"),
        store_identity_sha256=declaration.store_identity_sha256,
        output_namespace_identity_sha256=(declaration.output_namespace_identity_sha256),
        terminal_path_identity_sha256=declaration.terminal_path_identity_sha256,
        authorization_output_namespace_absence_receipt_sha256=(
            authorization_output.canonical_sha256
        ),
        authorization_terminal_path_absence_receipt_sha256=(
            authorization_terminal.canonical_sha256
        ),
    )
    claim = r.D7AttemptClaimRecord(
        attempt_declaration_sha256=declaration.canonical_sha256,
        launch_authorization_sha256=authorization.canonical_sha256,
        replay_target_sha256=declaration.replay_target_sha256,
        attempt_key_sha256=declaration.attempt_key_sha256,
        execution_identity_receipt_sha256=(
            declaration.execution_identity_receipt_sha256
        ),
        store_identity_sha256=declaration.store_identity_sha256,
    )

    def pre_start_receipt(
        *,
        subject: e.D7AbsentPathSubject,
        identity: str,
        leaf: str,
    ) -> e.D7PreStartPathAbsenceReceipt:
        return e.D7PreStartPathAbsenceReceipt(
            subject_kind=subject,
            replay_target_sha256=declaration.replay_target_sha256,
            attempt_key_sha256=declaration.attempt_key_sha256,
            attempt_declaration_sha256=declaration.canonical_sha256,
            launch_authorization_sha256=authorization.canonical_sha256,
            attempt_claim_sha256=claim.canonical_sha256,
            authorization_commit=declaration.authorization_commit,
            execution_identity_receipt_sha256=(
                declaration.execution_identity_receipt_sha256
            ),
            store_identity_sha256=declaration.store_identity_sha256,
            subject_path_identity_sha256=identity,
            store_root_realpath=str(store),
            resolved_parent_realpath=str(store),
            subject_basename=leaf,
            parent_device=observed_parent.st_dev,
            parent_inode=observed_parent.st_ino,
        )

    pre_start_output = pre_start_receipt(
        subject=e.D7AbsentPathSubject.OUTPUT_NAMESPACE,
        identity=output_identity,
        leaf=output_leaf,
    )
    pre_start_terminal = pre_start_receipt(
        subject=e.D7AbsentPathSubject.TERMINAL_PATH,
        identity=terminal_identity,
        leaf=terminal_leaf,
    )
    start = r.D7ExecutionStartRecord(
        attempt_declaration_sha256=declaration.canonical_sha256,
        launch_authorization_sha256=authorization.canonical_sha256,
        attempt_claim_sha256=claim.canonical_sha256,
        replay_target_sha256=declaration.replay_target_sha256,
        attempt_key_sha256=declaration.attempt_key_sha256,
        authorization_commit=declaration.authorization_commit,
        execution_identity_receipt_sha256=(
            declaration.execution_identity_receipt_sha256
        ),
        observed_execution_identity_receipt_sha256=(
            declaration.execution_identity_receipt_sha256
        ),
        observed_execution_source_runtime_receipt_sha256=(
            authorization.execution_source_runtime_receipt_sha256
        ),
        observed_runtime_specification_sha256=(
            authorization.runtime_specification_sha256
        ),
        output_namespace_identity_sha256=(declaration.output_namespace_identity_sha256),
        terminal_path_identity_sha256=declaration.terminal_path_identity_sha256,
        pre_start_output_namespace_absence_receipt_sha256=(
            pre_start_output.canonical_sha256
        ),
        pre_start_terminal_path_absence_receipt_sha256=(
            pre_start_terminal.canonical_sha256
        ),
    )
    return SimpleNamespace(
        store=store,
        declaration=declaration,
        authorization=authorization,
        claim=claim,
        start=start,
        authorization_output=authorization_output,
        authorization_terminal=authorization_terminal,
        pre_start_output=pre_start_output,
        pre_start_terminal=pre_start_terminal,
    )


def _persist(prefix: SimpleNamespace) -> p.D7LoadedEvidenceOnlyPrefix:
    declaration_identity = p.persist_d7_attempt_declaration_evidence_no_replace(
        prefix.store,
        prefix.declaration,
    )
    authorization_identity = p.persist_d7_launch_authorization_evidence_no_replace(
        prefix.store,
        authorization=prefix.authorization,
        expected_declaration_envelope_sha256=(declaration_identity.canonical_sha256),
        output_namespace_receipt=prefix.authorization_output,
        terminal_path_receipt=prefix.authorization_terminal,
    )
    claim_identity = p.persist_d7_attempt_claim_evidence_no_replace(
        prefix.store,
        claim=prefix.claim,
        expected_declaration_envelope_sha256=(declaration_identity.canonical_sha256),
        expected_authorization_envelope_sha256=(
            authorization_identity.canonical_sha256
        ),
    )
    start_identity = p.persist_d7_execution_start_evidence_no_replace(
        prefix.store,
        start=prefix.start,
        expected_store_identity_sha256=prefix.declaration.store_identity_sha256,
        expected_declaration_envelope_sha256=(declaration_identity.canonical_sha256),
        expected_authorization_envelope_sha256=(
            authorization_identity.canonical_sha256
        ),
        expected_claim_envelope_sha256=claim_identity.canonical_sha256,
        output_namespace_receipt=prefix.pre_start_output,
        terminal_path_receipt=prefix.pre_start_terminal,
    )
    for identity in (
        declaration_identity,
        authorization_identity,
        claim_identity,
        start_identity,
    ):
        assert identity.created_by_call is True
        assert identity.parent_directory_fsync_proved is True
        assert identity.atomic_no_replace is True
        assert identity.authority_granted is False
    return p.load_d7_evidence_only_prefix(
        prefix.store,
        attempt_key_sha256=prefix.declaration.attempt_key_sha256,
        expected_store_identity_sha256=prefix.declaration.store_identity_sha256,
        expected_declaration_sha256=prefix.declaration.canonical_sha256,
        expected_authorization_sha256=prefix.authorization.canonical_sha256,
        expected_claim_sha256=prefix.claim.canonical_sha256,
        expected_start_sha256=prefix.start.canonical_sha256,
        expected_declaration_envelope_sha256=(declaration_identity.canonical_sha256),
        expected_authorization_envelope_sha256=(
            authorization_identity.canonical_sha256
        ),
        expected_claim_envelope_sha256=claim_identity.canonical_sha256,
        expected_start_envelope_sha256=start_identity.canonical_sha256,
    )


def _reload(
    prefix: SimpleNamespace,
    loaded: p.D7LoadedEvidenceOnlyPrefix,
    *,
    store: Path | None = None,
    start_envelope_sha256: str | None = None,
) -> p.D7LoadedEvidenceOnlyPrefix:
    return p.load_d7_evidence_only_prefix(
        prefix.store if store is None else store,
        attempt_key_sha256=prefix.declaration.attempt_key_sha256,
        expected_store_identity_sha256=prefix.declaration.store_identity_sha256,
        expected_declaration_sha256=prefix.declaration.canonical_sha256,
        expected_authorization_sha256=prefix.authorization.canonical_sha256,
        expected_claim_sha256=prefix.claim.canonical_sha256,
        expected_start_sha256=prefix.start.canonical_sha256,
        expected_declaration_envelope_sha256=(
            loaded.declaration_identity.canonical_sha256
        ),
        expected_authorization_envelope_sha256=(
            loaded.authorization_identity.canonical_sha256
        ),
        expected_claim_envelope_sha256=loaded.claim_identity.canonical_sha256,
        expected_start_envelope_sha256=(
            loaded.start_identity.canonical_sha256
            if start_envelope_sha256 is None
            else start_envelope_sha256
        ),
    )


def test_evidence_only_prefix_roundtrips_without_establishing_execution(
    tmp_path: Path,
) -> None:
    prefix = _prefix(tmp_path)
    loaded = _persist(prefix)

    assert loaded.declaration == prefix.declaration
    assert loaded.authorization == prefix.authorization
    assert loaded.claim == prefix.claim
    assert loaded.start == prefix.start
    inspection = p.inspect_d7_evidence_only_prefix(loaded)
    assert (
        inspection.state
        is p.D7EvidenceOnlyPrefixState.CALLER_SUPPLIED_START_RECORD_PRESENT_TERMINAL_ABSENT
    )
    assert inspection.terminal_path == prefix.store / "primary-terminal"
    assert inspection.retry_authorized is False
    assert inspection.replay_authorized is False
    assert inspection.d8_eligible is False
    assert inspection.elapsed_time_used is False
    assert inspection.process_absence_used is False
    assert inspection.caller_assertion_used is False
    assert inspection.terminal_validated is False
    assert inspection.external_abort_finalized is False
    assert inspection.execution_observed is False
    assert inspection.started_unresolved_established is False
    assert loaded.store_scope.authority_granted is False
    assert loaded.store_scope.authoritative_lifecycle_eligible is False
    assert loaded.store_scope.in_place_promotion_allowed is False
    assert loaded.start_envelope.authority_granted is False
    assert loaded.start_envelope.execution_capability_issued is False
    assert loaded.start_envelope.terminal_finalization_capability_issued is False


def test_stage_order_and_every_overwrite_are_rejected(tmp_path: Path) -> None:
    prefix = _prefix(tmp_path)
    with pytest.raises(QualificationContractError, match="prefix lane"):
        p.persist_d7_launch_authorization_evidence_no_replace(
            prefix.store,
            authorization=prefix.authorization,
            expected_declaration_envelope_sha256=_h("missing declaration envelope"),
            output_namespace_receipt=prefix.authorization_output,
            terminal_path_receipt=prefix.authorization_terminal,
        )
    with pytest.raises(QualificationContractError, match="prefix lane"):
        p.persist_d7_attempt_claim_evidence_no_replace(
            prefix.store,
            claim=prefix.claim,
            expected_declaration_envelope_sha256=_h("missing declaration envelope"),
            expected_authorization_envelope_sha256=_h("missing authorization envelope"),
        )

    declaration_identity = p.persist_d7_attempt_declaration_evidence_no_replace(
        prefix.store,
        prefix.declaration,
    )
    declaration_bytes = declaration_identity.path.read_bytes()
    with pytest.raises(QualificationContractError, match="declaration"):
        p.persist_d7_attempt_declaration_evidence_no_replace(
            prefix.store,
            prefix.declaration,
        )
    assert declaration_identity.path.read_bytes() == declaration_bytes

    authorization_identity = p.persist_d7_launch_authorization_evidence_no_replace(
        prefix.store,
        authorization=prefix.authorization,
        expected_declaration_envelope_sha256=(declaration_identity.canonical_sha256),
        output_namespace_receipt=prefix.authorization_output,
        terminal_path_receipt=prefix.authorization_terminal,
    )
    with pytest.raises(QualificationContractError, match="authorization"):
        p.persist_d7_launch_authorization_evidence_no_replace(
            prefix.store,
            authorization=prefix.authorization,
            expected_declaration_envelope_sha256=(
                declaration_identity.canonical_sha256
            ),
            output_namespace_receipt=prefix.authorization_output,
            terminal_path_receipt=prefix.authorization_terminal,
        )
    claim_identity = p.persist_d7_attempt_claim_evidence_no_replace(
        prefix.store,
        claim=prefix.claim,
        expected_declaration_envelope_sha256=(declaration_identity.canonical_sha256),
        expected_authorization_envelope_sha256=(
            authorization_identity.canonical_sha256
        ),
    )
    with pytest.raises(QualificationContractError, match="claim"):
        p.persist_d7_attempt_claim_evidence_no_replace(
            prefix.store,
            claim=prefix.claim,
            expected_declaration_envelope_sha256=(
                declaration_identity.canonical_sha256
            ),
            expected_authorization_envelope_sha256=(
                authorization_identity.canonical_sha256
            ),
        )
    p.persist_d7_execution_start_evidence_no_replace(
        prefix.store,
        start=prefix.start,
        expected_store_identity_sha256=prefix.declaration.store_identity_sha256,
        expected_declaration_envelope_sha256=(declaration_identity.canonical_sha256),
        expected_authorization_envelope_sha256=(
            authorization_identity.canonical_sha256
        ),
        expected_claim_envelope_sha256=claim_identity.canonical_sha256,
        output_namespace_receipt=prefix.pre_start_output,
        terminal_path_receipt=prefix.pre_start_terminal,
    )
    with pytest.raises(QualificationContractError, match="start"):
        p.persist_d7_execution_start_evidence_no_replace(
            prefix.store,
            start=prefix.start,
            expected_store_identity_sha256=(prefix.declaration.store_identity_sha256),
            expected_declaration_envelope_sha256=(
                declaration_identity.canonical_sha256
            ),
            expected_authorization_envelope_sha256=(
                authorization_identity.canonical_sha256
            ),
            expected_claim_envelope_sha256=claim_identity.canonical_sha256,
            output_namespace_receipt=prefix.pre_start_output,
            terminal_path_receipt=prefix.pre_start_terminal,
        )


def test_live_absence_is_reobserved_before_authorization_and_start(
    tmp_path: Path,
) -> None:
    authorization_store = tmp_path / "authorization"
    authorization_store.mkdir()
    authorization = _prefix(authorization_store)
    authorization_declaration_identity = (
        p.persist_d7_attempt_declaration_evidence_no_replace(
            authorization.store,
            authorization.declaration,
        )
    )
    (authorization.store / "primary-output").mkdir()
    with pytest.raises(QualificationContractError, match="present"):
        p.persist_d7_launch_authorization_evidence_no_replace(
            authorization.store,
            authorization=authorization.authorization,
            expected_declaration_envelope_sha256=(
                authorization_declaration_identity.canonical_sha256
            ),
            output_namespace_receipt=authorization.authorization_output,
            terminal_path_receipt=authorization.authorization_terminal,
        )

    start_store = tmp_path / "start"
    start_store.mkdir()
    started = _prefix(start_store)
    started_declaration_identity = p.persist_d7_attempt_declaration_evidence_no_replace(
        started.store,
        started.declaration,
    )
    started_authorization_identity = (
        p.persist_d7_launch_authorization_evidence_no_replace(
            started.store,
            authorization=started.authorization,
            expected_declaration_envelope_sha256=(
                started_declaration_identity.canonical_sha256
            ),
            output_namespace_receipt=started.authorization_output,
            terminal_path_receipt=started.authorization_terminal,
        )
    )
    started_claim_identity = p.persist_d7_attempt_claim_evidence_no_replace(
        started.store,
        claim=started.claim,
        expected_declaration_envelope_sha256=(
            started_declaration_identity.canonical_sha256
        ),
        expected_authorization_envelope_sha256=(
            started_authorization_identity.canonical_sha256
        ),
    )
    (started.store / "primary-terminal").write_bytes(b"occupied")
    with pytest.raises(QualificationContractError, match="present"):
        p.persist_d7_execution_start_evidence_no_replace(
            started.store,
            start=started.start,
            expected_store_identity_sha256=(started.declaration.store_identity_sha256),
            expected_declaration_envelope_sha256=(
                started_declaration_identity.canonical_sha256
            ),
            expected_authorization_envelope_sha256=(
                started_authorization_identity.canonical_sha256
            ),
            expected_claim_envelope_sha256=(started_claim_identity.canonical_sha256),
            output_namespace_receipt=started.pre_start_output,
            terminal_path_receipt=started.pre_start_terminal,
        )


@pytest.mark.parametrize("entry_kind", ("file", "directory", "symlink"))
def test_any_terminal_entry_is_presence_not_an_inferred_abort(
    tmp_path: Path,
    entry_kind: str,
) -> None:
    prefix = _prefix(tmp_path)
    loaded = _persist(prefix)
    terminal = prefix.store / "primary-terminal"
    if entry_kind == "file":
        terminal.write_bytes(b"not a terminal transaction")
    elif entry_kind == "directory":
        terminal.mkdir()
    else:
        terminal.symlink_to(prefix.store / "missing-target")

    inspection = p.inspect_d7_evidence_only_prefix(loaded)
    assert (
        inspection.state is p.D7EvidenceOnlyPrefixState.TERMINAL_PATH_PRESENT_UNVERIFIED
    )
    assert inspection.terminal_validated is False
    assert inspection.external_abort_finalized is False


def test_orphan_content_addressed_receipts_do_not_create_authorization(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    prefix = _prefix(tmp_path)
    declaration_identity = p.persist_d7_attempt_declaration_evidence_no_replace(
        prefix.store,
        prefix.declaration,
    )
    real_writer = p._write_canonical_file_no_replace

    def fail_authorization(
        anchor: object,
        leaf: str,
        payload: bytes,
        **kwargs: object,
    ) -> p.D7PersistedRecordIdentity:
        if kwargs["label"] == "D7 evidence-only launch-authorization envelope":
            raise OSError("injected authorization marker failure")
        return real_writer(anchor, leaf, payload, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(p, "_write_canonical_file_no_replace", fail_authorization)
    with pytest.raises(OSError, match="injected"):
        p.persist_d7_launch_authorization_evidence_no_replace(
            prefix.store,
            authorization=prefix.authorization,
            expected_declaration_envelope_sha256=(
                declaration_identity.canonical_sha256
            ),
            output_namespace_receipt=prefix.authorization_output,
            terminal_path_receipt=prefix.authorization_terminal,
        )
    authorization_path = (
        prefix.store
        / "d7-prefix-evidence-only-v0"
        / (
            f"{prefix.declaration.attempt_key_sha256}"
            ".launch-authorization.envelope.json"
        )
    )
    assert not authorization_path.exists()
    evidence_files = tuple((prefix.store / "d7-attempt-evidence").iterdir())
    assert len(evidence_files) == 2

    monkeypatch.setattr(p, "_write_canonical_file_no_replace", real_writer)
    p.persist_d7_launch_authorization_evidence_no_replace(
        prefix.store,
        authorization=prefix.authorization,
        expected_declaration_envelope_sha256=(declaration_identity.canonical_sha256),
        output_namespace_receipt=prefix.authorization_output,
        terminal_path_receipt=prefix.authorization_terminal,
    )
    assert authorization_path.is_file()


def test_loader_rejects_tamper_symlink_and_hardlink_aliases(tmp_path: Path) -> None:
    tamper_store = tmp_path / "tamper"
    tamper_store.mkdir()
    tampered = _prefix(tamper_store)
    loaded = _persist(tampered)
    loaded.start_identity.path.write_bytes(b"{}")
    with pytest.raises(QualificationContractError, match="SHA-256"):
        _reload(tampered, loaded)

    symlink_store = tmp_path / "symlink"
    symlink_store.mkdir()
    symlinked = _prefix(symlink_store)
    symlink_loaded = _persist(symlinked)
    start_path = symlink_loaded.start_identity.path
    start_path.unlink()
    start_path.symlink_to(symlink_loaded.claim_identity.path)
    with pytest.raises(QualificationContractError, match="open D7 evidence-only"):
        _reload(symlinked, symlink_loaded)

    hardlink_store = tmp_path / "hardlink"
    hardlink_store.mkdir()
    hardlinked = _prefix(hardlink_store)
    hardlink_loaded = _persist(hardlinked)
    os.link(
        hardlink_loaded.start_identity.path,
        hardlink_store / "start-alias.json",
    )
    with pytest.raises(QualificationContractError, match="unaliased"):
        _reload(hardlinked, hardlink_loaded)


@pytest.mark.parametrize(
    "namespace",
    ("d7-prefix-evidence-only-v0", "d7-attempt-evidence"),
)
def test_unpublished_staging_entry_blocks_retry_and_reload(
    tmp_path: Path,
    namespace: str,
) -> None:
    prefix = _prefix(tmp_path)
    loaded = _persist(prefix)
    staged = prefix.store / namespace / ".crash-orphan.tmp"
    staged.write_bytes(b"unpublished staged bytes")

    with pytest.raises(QualificationContractError, match="offline recovery"):
        _reload(prefix, loaded)

    retry_store = tmp_path / f"retry-{namespace}"
    retry_store.mkdir()
    retry_prefix = _prefix(retry_store)
    retry_lane = retry_store / "d7-prefix-evidence-only-v0"
    retry_lane.mkdir()
    (retry_lane / ".crash-orphan.tmp").write_bytes(b"unpublished staged bytes")
    with pytest.raises(QualificationContractError, match="offline recovery"):
        p.persist_d7_attempt_declaration_evidence_no_replace(
            retry_prefix.store,
            retry_prefix.declaration,
        )
    assert not (retry_lane / "store-scope.json").exists()


def test_post_rename_parent_fsync_failure_is_visible_but_not_durable(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    prefix = _prefix(tmp_path)
    real_fsync = p.os.fsync
    calls = 0

    def fail_first_parent_fsync(descriptor: int) -> None:
        nonlocal calls
        calls += 1
        if calls == 5:
            raise OSError("injected parent fsync failure")
        real_fsync(descriptor)

    monkeypatch.setattr(p.os, "fsync", fail_first_parent_fsync)
    identity = p.persist_d7_attempt_declaration_evidence_no_replace(
        prefix.store,
        prefix.declaration,
    )
    assert b'"authority_granted":false' in identity.path.read_bytes()
    assert prefix.declaration.canonical_sha256.encode() in identity.path.read_bytes()
    assert identity.created_by_call is True
    assert identity.parent_directory_fsync_proved is False
    with pytest.raises(QualificationContractError, match="declaration"):
        p.persist_d7_attempt_declaration_evidence_no_replace(
            prefix.store,
            prefix.declaration,
        )


def test_failed_temporary_file_fsync_leaves_no_visible_or_staged_record(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    prefix = _prefix(tmp_path)
    real_fsync = p.os.fsync
    calls = 0

    def fail_file_fsync_once(descriptor: int) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("injected temporary file fsync failure")
        real_fsync(descriptor)

    monkeypatch.setattr(p.os, "fsync", fail_file_fsync_once)
    with pytest.raises(OSError, match="temporary file fsync"):
        p.persist_d7_attempt_declaration_evidence_no_replace(
            prefix.store,
            prefix.declaration,
        )

    lane = prefix.store / "d7-prefix-evidence-only-v0"
    declaration = lane / (
        f"{prefix.declaration.attempt_key_sha256}.attempt-declaration.envelope.json"
    )
    assert not declaration.exists()
    assert not tuple(prefix.store.rglob("*.tmp"))


@pytest.mark.parametrize(
    ("failure_mode", "expected_error"),
    (
        ("cleanup", "temporary cleanup is unproved"),
        ("cleanup_fsync", "temporary cleanup durability is unproved"),
    ),
)
def test_identical_collision_cannot_succeed_without_durable_temporary_cleanup(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    failure_mode: str,
    expected_error: str,
) -> None:
    payload = canonical_json_bytes({"schema": "collision-test.v0.1"})
    expected_sha256 = sha256_bytes(payload)
    anchor = p._open_real_directory(tmp_path, label="collision test")
    real_cleanup = p._cleanup_temporary
    real_fsync = p.os.fsync
    cleanup_finished = False

    def publish_identical_winner_then_report_collision(
        directory: object,
        source_leaf: str,
        destination_leaf: str,
    ) -> None:
        shutil.copyfile(
            anchor.path / source_leaf,
            anchor.path / destination_leaf,
        )
        raise OSError(errno.EEXIST, "injected identical collision")

    def controlled_cleanup(
        directory: object,
        leaf: str,
        *,
        expected_identity: tuple[int, int],
    ) -> bool:
        nonlocal cleanup_finished
        if failure_mode == "cleanup":
            return False
        cleaned = real_cleanup(
            directory,  # type: ignore[arg-type]
            leaf,
            expected_identity=expected_identity,
        )
        cleanup_finished = True
        return cleaned

    def controlled_fsync(descriptor: int) -> None:
        if failure_mode == "cleanup_fsync" and cleanup_finished:
            raise OSError("injected cleanup directory fsync failure")
        real_fsync(descriptor)

    monkeypatch.setattr(
        p,
        "_rename_file_no_replace",
        publish_identical_winner_then_report_collision,
    )
    monkeypatch.setattr(p, "_cleanup_temporary", controlled_cleanup)
    monkeypatch.setattr(p.os, "fsync", controlled_fsync)
    try:
        with pytest.raises(QualificationContractError, match=expected_error):
            p._write_canonical_file_no_replace(
                anchor,
                "winner.json",
                payload,
                expected_sha256=expected_sha256,
                maximum_bytes=1024,
                label="collision test",
                allow_identical_existing=True,
            )
    finally:
        os.close(anchor.descriptor)

    assert (tmp_path / "winner.json").read_bytes() == payload
    if failure_mode == "cleanup":
        assert tuple(tmp_path.glob(".*.tmp"))
    else:
        assert not tuple(tmp_path.glob(".*.tmp"))


def test_success_followed_by_ambiguous_rename_error_recovers_exact_identity(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    prefix = _prefix(tmp_path)
    real_rename = p._rename_file_no_replace

    def rename_then_report_error(
        anchor: object,
        source_leaf: str,
        destination_leaf: str,
    ) -> None:
        real_rename(anchor, source_leaf, destination_leaf)  # type: ignore[arg-type]
        raise OSError(errno.EIO, "injected ambiguous rename result")

    monkeypatch.setattr(p, "_rename_file_no_replace", rename_then_report_error)
    identity = p.persist_d7_attempt_declaration_evidence_no_replace(
        prefix.store,
        prefix.declaration,
    )

    assert b'"authority_granted":false' in identity.path.read_bytes()
    assert prefix.declaration.canonical_sha256.encode() in identity.path.read_bytes()
    assert identity.path.stat().st_nlink == 1
    assert not tuple(prefix.store.rglob("*.tmp"))


def test_concurrent_declaration_publish_has_one_complete_winner(
    tmp_path: Path,
) -> None:
    prefix = _prefix(tmp_path)

    def publish() -> object:
        try:
            return p.persist_d7_attempt_declaration_evidence_no_replace(
                prefix.store,
                prefix.declaration,
            )
        except QualificationContractError as error:
            return error

    with ThreadPoolExecutor(max_workers=8) as executor:
        outcomes = tuple(executor.map(lambda _index: publish(), range(8)))
    winners = tuple(
        value for value in outcomes if type(value) is p.D7PersistedRecordIdentity
    )
    losers = tuple(
        value for value in outcomes if type(value) is QualificationContractError
    )
    assert len(winners) == 1
    assert len(losers) == 7
    assert b'"authority_granted":false' in winners[0].path.read_bytes()
    assert prefix.declaration.canonical_sha256.encode() in winners[0].path.read_bytes()
    assert tuple(
        item
        for item in (prefix.store / "d7-prefix-evidence-only-v0").iterdir()
        if item.name.endswith(".attempt-declaration.envelope.json")
    ) == (winners[0].path,)


def test_loaded_prefix_is_bound_to_its_original_store_root(tmp_path: Path) -> None:
    original_store = tmp_path / "original"
    copied_store = tmp_path / "copied"
    original_store.mkdir()
    prefix = _prefix(original_store)
    loaded = _persist(prefix)
    shutil.copytree(original_store, copied_store)

    with pytest.raises(QualificationContractError, match="scope"):
        _reload(prefix, loaded, store=copied_store)


def test_reserved_paths_and_wrong_parent_identity_fail_closed(
    tmp_path: Path,
) -> None:
    reserved = _prefix(tmp_path, output_leaf="d7-attempt-evidence")
    reserved_declaration_identity = (
        p.persist_d7_attempt_declaration_evidence_no_replace(
            reserved.store,
            reserved.declaration,
        )
    )
    with pytest.raises(QualificationContractError, match="reserved"):
        p.persist_d7_launch_authorization_evidence_no_replace(
            reserved.store,
            authorization=reserved.authorization,
            expected_declaration_envelope_sha256=(
                reserved_declaration_identity.canonical_sha256
            ),
            output_namespace_receipt=reserved.authorization_output,
            terminal_path_receipt=reserved.authorization_terminal,
        )

    other_attempt_store = tmp_path / "other-attempt"
    other_attempt_store.mkdir()
    other_attempt_key = _h("another attempt")
    other_attempt = _prefix(
        other_attempt_store,
        output_leaf=f"{other_attempt_key}.attempt-claim.json",
    )
    other_declaration_identity = p.persist_d7_attempt_declaration_evidence_no_replace(
        other_attempt.store,
        other_attempt.declaration,
    )
    with pytest.raises(QualificationContractError, match="reserved"):
        p.persist_d7_launch_authorization_evidence_no_replace(
            other_attempt.store,
            authorization=other_attempt.authorization,
            expected_declaration_envelope_sha256=(
                other_declaration_identity.canonical_sha256
            ),
            output_namespace_receipt=other_attempt.authorization_output,
            terminal_path_receipt=other_attempt.authorization_terminal,
        )

    wrong_store = tmp_path / "wrong-parent"
    wrong_store.mkdir()
    wrong = _prefix(wrong_store)
    wrong_declaration_identity = p.persist_d7_attempt_declaration_evidence_no_replace(
        wrong.store,
        wrong.declaration,
    )
    changed = replace(
        wrong.authorization_output,
        parent_inode=wrong.authorization_output.parent_inode + 1,
    )
    changed_authorization = replace(
        wrong.authorization,
        authorization_output_namespace_absence_receipt_sha256=(
            changed.canonical_sha256
        ),
    )
    with pytest.raises(QualificationContractError, match="device/inode"):
        p.persist_d7_launch_authorization_evidence_no_replace(
            wrong.store,
            authorization=changed_authorization,
            expected_declaration_envelope_sha256=(
                wrong_declaration_identity.canonical_sha256
            ),
            output_namespace_receipt=changed,
            terminal_path_receipt=wrong.authorization_terminal,
        )


def test_persisted_scope_and_envelope_carry_exact_false_authority(
    tmp_path: Path,
) -> None:
    prefix = _prefix(tmp_path)
    loaded = _persist(prefix)
    scope_document = parse_canonical_json(
        loaded.store_scope_identity.path.read_bytes(),
        label="test scope",
    )
    envelope_document = parse_canonical_json(
        loaded.start_identity.path.read_bytes(),
        label="test envelope",
    )
    assert type(scope_document) is dict
    assert type(envelope_document) is dict
    assert loaded.start_identity.canonical_sha256 != prefix.start.canonical_sha256
    assert loaded.start_identity.path.read_bytes() != prefix.start.canonical_bytes
    assert (
        envelope_document["schema_version"]
        == "spirallens.d7-prefix-persistence-envelope.v0.1"
    )
    for document, fields in (
        (
            scope_document,
            (
                "authority_granted",
                "authoritative_lifecycle_eligible",
                "in_place_promotion_allowed",
                "d7_execution_authorized",
                "terminal_publication_authorized",
                "unresolved_finalization_authorized",
            ),
        ),
        (
            envelope_document,
            (
                "authority_granted",
                "authoritative_lifecycle_eligible",
                "execution_capability_issued",
                "terminal_finalization_capability_issued",
            ),
        ),
    ):
        for field in fields:
            assert document[field] is False

    invalid_scope = dict(scope_document)
    invalid_scope["authority_granted"] = 0
    invalid_scope_bytes = canonical_json_bytes(invalid_scope)
    with pytest.raises(QualificationContractError, match="authority constants"):
        p._D7PrefixStoreScope.from_canonical_bytes(
            invalid_scope_bytes,
            expected_sha256=sha256_bytes(invalid_scope_bytes),
        )

    invalid_envelope = dict(envelope_document)
    invalid_envelope["execution_capability_issued"] = 0
    invalid_envelope_bytes = canonical_json_bytes(invalid_envelope)
    with pytest.raises(QualificationContractError, match="authority constants"):
        p._D7PrefixPersistenceEnvelope.from_canonical_bytes(
            invalid_envelope_bytes,
            expected_sha256=sha256_bytes(invalid_envelope_bytes),
        )


def test_raw_start_record_cannot_parse_as_persisted_stage(
    tmp_path: Path,
) -> None:
    prefix = _prefix(tmp_path)
    loaded = _persist(prefix)
    loaded.start_identity.path.write_bytes(prefix.start.canonical_bytes)

    with pytest.raises(QualificationContractError, match="envelope fields"):
        _reload(
            prefix,
            loaded,
            start_envelope_sha256=prefix.start.canonical_sha256,
        )


def test_envelope_predecessor_splice_is_rejected(
    tmp_path: Path,
) -> None:
    prefix = _prefix(tmp_path)
    loaded = _persist(prefix)
    document = parse_canonical_json(
        loaded.start_identity.path.read_bytes(),
        label="test start envelope",
    )
    assert type(document) is dict
    document["previous_envelope_sha256"] = loaded.declaration_envelope.canonical_sha256
    spliced = canonical_json_bytes(document)
    loaded.start_identity.path.write_bytes(spliced)

    with pytest.raises(QualificationContractError, match="binding differs"):
        _reload(
            prefix,
            loaded,
            start_envelope_sha256=sha256_bytes(spliced),
        )


def test_envelope_scope_and_embedded_record_splices_are_rejected(
    tmp_path: Path,
) -> None:
    scope_store = tmp_path / "scope-splice"
    scope_store.mkdir()
    scope_prefix = _prefix(scope_store)
    scope_loaded = _persist(scope_prefix)
    scope_document = parse_canonical_json(
        scope_loaded.start_identity.path.read_bytes(),
        label="test scope-spliced envelope",
    )
    assert type(scope_document) is dict
    scope_document["store_scope_sha256"] = _h("foreign store scope")
    scope_splice = canonical_json_bytes(scope_document)
    scope_loaded.start_identity.path.write_bytes(scope_splice)
    with pytest.raises(QualificationContractError, match="binding differs"):
        _reload(
            scope_prefix,
            scope_loaded,
            start_envelope_sha256=sha256_bytes(scope_splice),
        )

    record_store = tmp_path / "record-splice"
    record_store.mkdir()
    record_prefix = _prefix(record_store)
    record_loaded = _persist(record_prefix)
    record_document = parse_canonical_json(
        record_loaded.start_identity.path.read_bytes(),
        label="test record-spliced envelope",
    )
    assert type(record_document) is dict
    embedded = record_document["embedded_record"]
    assert type(embedded) is dict
    embedded["observed_runtime_specification_sha256"] = _h("different observed runtime")
    embedded_bytes = canonical_json_bytes(embedded)
    record_document["embedded_record_sha256"] = sha256_bytes(embedded_bytes)
    record_document["embedded_record_byte_count"] = len(embedded_bytes)
    record_splice = canonical_json_bytes(record_document)
    record_loaded.start_identity.path.write_bytes(record_splice)
    with pytest.raises(QualificationContractError, match="binding differs"):
        _reload(
            record_prefix,
            record_loaded,
            start_envelope_sha256=sha256_bytes(record_splice),
        )


def test_missing_scope_and_mixed_store_identity_fail_closed(tmp_path: Path) -> None:
    missing_store = tmp_path / "missing-scope"
    missing_store.mkdir()
    missing_prefix = _prefix(missing_store)
    missing_loaded = _persist(missing_prefix)
    missing_loaded.store_scope_identity.path.unlink()
    with pytest.raises(QualificationContractError, match="store scope"):
        _reload(missing_prefix, missing_loaded)

    mixed_store = tmp_path / "mixed-store"
    mixed_store.mkdir()
    mixed_prefix = _prefix(mixed_store)
    p.persist_d7_attempt_declaration_evidence_no_replace(
        mixed_prefix.store,
        mixed_prefix.declaration,
    )
    changed_declaration = replace(
        mixed_prefix.declaration,
        replay_target_sha256=_h("second target"),
        store_identity_sha256=_h("different declared store identity"),
    )
    with pytest.raises(QualificationContractError, match="store scope"):
        p.persist_d7_attempt_declaration_evidence_no_replace(
            mixed_prefix.store,
            changed_declaration,
        )


def test_isolated_replay_is_rejected_before_any_persistence(tmp_path: Path) -> None:
    prefix = _prefix(tmp_path)
    primary_key = r.d7_attempt_key_sha256(
        replay_target_sha256=prefix.declaration.replay_target_sha256,
        attempt_role=r.D7AttemptRole.PRIMARY_CONFIRMATION,
    )
    isolated_evidence = r.D7IsolatedReplayRoleEvidence(
        primary_replay_target_sha256=prefix.declaration.replay_target_sha256,
        primary_attempt_key_sha256=primary_key,
        primary_attempt_declaration_sha256=_h("primary declaration"),
        primary_launch_authorization_sha256=_h("primary authorization"),
        primary_attempt_claim_sha256=_h("primary claim"),
        primary_execution_start_sha256=_h("primary start"),
        primary_result_payload_sha256=_h("primary payload"),
        primary_scientific_result_sha256=_h("primary result"),
        primary_terminal_manifest_sha256=_h("primary terminal"),
        primary_terminal_consumption_sha256=_h("primary consumption"),
    )
    isolated = replace(prefix.declaration, role_evidence=isolated_evidence)

    with pytest.raises(QualificationContractError, match="isolated-replay authority"):
        p.persist_d7_attempt_declaration_evidence_no_replace(
            prefix.store,
            isolated,
        )
    assert tuple(prefix.store.iterdir()) == ()


def test_loaded_prefix_rejects_detached_store_root(tmp_path: Path) -> None:
    prefix = _prefix(tmp_path)
    loaded = _persist(prefix)
    with pytest.raises(QualificationContractError, match="store scope"):
        replace(
            loaded,
            store_root=tmp_path / "not-the-store",
        )


def test_persistence_module_cannot_finalize_a_constructible_external_receipt() -> None:
    assert not hasattr(p, "finalize_d7_started_unresolved")
    assert not hasattr(p, "publish_d7_failed_terminal")
    assert not hasattr(p, "publish_d7_scientific_terminal")
    assert not hasattr(p, "write_d7_execution_start_no_replace")
    assert not hasattr(p, "promote_d7_evidence_only_prefix")
    assert all(
        "started_unresolved" not in state.value for state in p.D7EvidenceOnlyPrefixState
    )
    assert p.__all__ == ()
