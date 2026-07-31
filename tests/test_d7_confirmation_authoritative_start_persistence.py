from __future__ import annotations

import errno
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

import spirallens
from spirallens import qualification
from spirallens.core.canonical import canonical_json_bytes, sha256_bytes
from spirallens.qualification import confirmation_attempt_authority as authority
from spirallens.qualification import confirmation_attempt_persistence as persistence
from spirallens.qualification import (
    confirmation_attempt_terminal_persistence as terminal_persistence,
)
from spirallens.qualification import (
    confirmation_authoritative_start_persistence as start_persistence,
)
from spirallens.qualification import confirmation_fused_authority as fused_authority
from spirallens.qualification import confirmation_fused_start as fused_start
from spirallens.qualification.common import QualificationContractError
from test_d7_confirmation_attempt_persistence import _h, _prefix


def _opaque_binding(
    role: str,
    contract_id: str,
    source: bytes,
) -> authority.D7AuthorityArtifactBinding:
    return authority.D7AuthorityArtifactBinding(
        artifact_role=role,
        artifact_contract_id=contract_id,
        canonical_sha256=sha256_bytes(source),
        byte_count=len(source),
    )


def _launch_material(values: SimpleNamespace) -> SimpleNamespace:
    member_sha256 = {
        "launch-authority-input-bundle": _h("launch-authority-input-bundle"),
        "replay-target": values.declaration.replay_target_sha256,
        "launch-intent": values.declaration.launch_intent_sha256,
        "execution-source-runtime-closure": _h("source-runtime-closure"),
        "runtime-specification": values.authorization.runtime_specification_sha256,
        "family-admission": _h("family-admission"),
        "execution-identity": values.declaration.execution_identity_receipt_sha256,
        "physical-store-lane-identity": _h("physical-identity"),
        "full-design-freeze": (values.authorization.full_design_freeze_receipt_sha256),
    }
    descriptor = fused_authority._D7FusedAuthorityLaunchDescriptor(
        descriptor_id="test-authoritative-start-descriptor",
        descriptor_repository_path="authority/launch-descriptor.json",
        inventory=tuple(
            fused_authority._D7FusedAuthorityMember(
                artifact_role=role,
                artifact_contract_id=contract_id,
                repository_path=f"authority/{index:02d}-{role}.json",
                canonical_sha256=member_sha256[role],
                byte_count=1,
            )
            for index, (role, contract_id, _attribute, _record_type) in enumerate(
                fused_authority._MEMBER_SPECS
            )
        ),
    )
    verification = fused_start._D7FusedStartVerificationEvidence(
        descriptor_sha256=descriptor.canonical_sha256,
        launch_bundle_sha256=member_sha256["launch-authority-input-bundle"],
        repository_head_commit="a" * 40,
        canonical_origin_observation_sha256=_h("origin-observation"),
        replay_target_sha256=member_sha256["replay-target"],
        launch_intent_sha256=member_sha256["launch-intent"],
        source_runtime_closure_sha256=member_sha256["execution-source-runtime-closure"],
        runtime_specification_sha256=member_sha256["runtime-specification"],
        family_admission_sha256=member_sha256["family-admission"],
        execution_identity_sha256=member_sha256["execution-identity"],
        physical_identity_sha256=member_sha256["physical-store-lane-identity"],
        full_design_freeze_sha256=member_sha256["full-design-freeze"],
        source_tree_sha256=_h("source-tree"),
        transitive_dependency_set_sha256=_h("dependency-set"),
        callable_identity_sha256=_h("callable-identity"),
        process_identity_sha256=_h("process-identity"),
        attempt_key_sha256=values.start.attempt_key_sha256,
    )
    return SimpleNamespace(
        descriptor=descriptor,
        descriptor_binding=_opaque_binding(
            "launch-authority-source-envelope",
            descriptor.schema_version,
            descriptor.canonical_bytes,
        ),
        verification=verification,
        verification_binding=_opaque_binding(
            "launch-authority-verification-evidence",
            verification.schema_version,
            verification.canonical_bytes,
        ),
    )


def _transaction(directory: Path) -> SimpleNamespace:
    directory.mkdir(parents=True, exist_ok=True)
    values = _prefix(directory)
    lane = directory / start_persistence.D7_AUTHORITATIVE_START_LANE_BASENAME
    lane.mkdir(mode=0o700)
    launch = _launch_material(values)
    return SimpleNamespace(
        values=values,
        lane=lane,
        descriptor=launch.descriptor,
        authority_source=launch.descriptor.canonical_bytes,
        authority_source_binding=launch.descriptor_binding,
        verification=launch.verification,
        verification_source=launch.verification.canonical_bytes,
        verification_binding=launch.verification_binding,
    )


def _persist(
    transaction: SimpleNamespace,
) -> start_persistence.D7LoadedAuthoritativeStartTransaction:
    values = transaction.values
    return start_persistence.persist_d7_authoritative_start_transaction_no_replace(
        values.store,
        launch_authority_source_envelope_source=transaction.authority_source,
        launch_authority_source_envelope_binding=(transaction.authority_source_binding),
        verification_evidence_source=transaction.verification_source,
        verification_evidence_binding=transaction.verification_binding,
        declaration=values.declaration,
        authorization_output_receipt=values.authorization_output,
        authorization_terminal_receipt=values.authorization_terminal,
        authorization=values.authorization,
        claim=values.claim,
        pre_start_output_receipt=values.pre_start_output,
        pre_start_terminal_receipt=values.pre_start_terminal,
        start=values.start,
    )


def _load(
    transaction: SimpleNamespace,
    loaded: start_persistence.D7LoadedAuthoritativeStartTransaction,
) -> start_persistence.D7LoadedAuthoritativeStartTransaction:
    return start_persistence.load_d7_authoritative_start_transaction(
        transaction.values.store,
        attempt_key_sha256=transaction.values.start.attempt_key_sha256,
        expected_manifest_sha256=loaded.manifest.canonical_sha256,
    )


def _rewrite_persisted_members_and_manifest(
    loaded: start_persistence.D7LoadedAuthoritativeStartTransaction,
    replacements: dict[str, bytes],
) -> start_persistence.D7AuthoritativeStartManifest:
    for filename, source in replacements.items():
        (loaded.path / filename).write_bytes(source)
    members = tuple(
        replace(
            member,
            member_canonical_sha256=sha256_bytes(replacements[member.filename]),
            byte_count=len(replacements[member.filename]),
        )
        if member.filename in replacements
        else member
        for member in loaded.manifest.immutable_members
    )
    manifest = replace(loaded.manifest, immutable_members=members)
    (
        loaded.path / start_persistence.D7_AUTHORITATIVE_START_MANIFEST_FILENAME
    ).write_bytes(manifest.canonical_bytes)
    return manifest


def test_closed_start_transaction_round_trips_without_issuing_authority(
    tmp_path: Path,
) -> None:
    transaction = _transaction(tmp_path)
    loaded = _persist(transaction)
    reloaded = _load(transaction, loaded)

    assert loaded.declaration == transaction.values.declaration
    assert loaded.authorization == transaction.values.authorization
    assert loaded.claim == transaction.values.claim
    assert loaded.start == transaction.values.start
    assert loaded.created_by_call is True
    assert loaded.atomic_no_replace_performed_by_call is True
    assert loaded.parent_directory_fsync_proved is True
    assert reloaded.created_by_call is False
    assert reloaded.atomic_no_replace_performed_by_call is False
    assert reloaded.parent_directory_fsync_proved is None
    assert reloaded.manifest == loaded.manifest
    assert reloaded.directory_identity_sha256 == loaded.directory_identity_sha256
    assert loaded.path.parent == transaction.lane
    assert loaded.path.name.endswith(".authoritative-start")
    assert loaded.manifest.start_directory_device == loaded.directory_device
    assert loaded.manifest.start_directory_inode == loaded.directory_inode
    assert set(loaded.immutable_member_sources) == {
        filename for _kind, filename in start_persistence._MEMBER_ORDER
    }
    for name in (
        "authority_authenticated",
        "authority_granted",
        "authoritative_lifecycle_eligible",
        "exclusive_start_authorized",
        "ownership_issued",
        "execution_observed",
        "started_unresolved_established",
        "scientific_claim_eligible",
        "retry_authorized",
        "replay_authorized",
        "d8_eligible",
    ):
        assert getattr(loaded, name) is False
    assert loaded.verification_evidence_strictly_parsed is True
    assert loaded.verification_evidence_descriptor_and_start_subset_rejoined is True
    assert loaded.live_observation_digests_reauthenticated is False
    assert loaded.all_live_observation_digests_semantically_rejoined is False


def test_start_persistence_and_fused_start_are_independently_importable() -> None:
    repository_root = Path(__file__).resolve().parents[1]
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(repository_root / "src")
    modules = (
        "spirallens.qualification.confirmation_authoritative_start_persistence",
        "spirallens.qualification.confirmation_fused_start",
    )
    for order in (modules, tuple(reversed(modules))):
        script = (
            "import importlib; "
            f"first = importlib.import_module({order[0]!r}); "
            f"second = importlib.import_module({order[1]!r}); "
            "assert first.__all__ == (); assert second.__all__ == ()"
        )
        completed = subprocess.run(
            [sys.executable, "-c", script],
            cwd=repository_root,
            env=environment,
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert completed.returncode == 0, completed.stderr


@pytest.mark.parametrize("mutation", ("unknown-field", "missing-field"))
def test_loader_strictly_replays_persisted_verification_evidence_fields(
    tmp_path: Path,
    mutation: str,
) -> None:
    transaction = _transaction(tmp_path)
    loaded = _persist(transaction)
    document = transaction.verification.to_dict()
    if mutation == "unknown-field":
        document["unreviewed_extension"] = False
    else:
        document.pop("canonical_origin_observation_sha256")
    source = canonical_json_bytes(document)
    manifest = _rewrite_persisted_members_and_manifest(
        loaded,
        {
            start_persistence.D7_AUTHORITY_VERIFICATION_EVIDENCE_FILENAME: source,
        },
    )

    with pytest.raises(QualificationContractError, match="fields differ"):
        start_persistence.load_d7_authoritative_start_transaction(
            transaction.values.store,
            attempt_key_sha256=transaction.values.start.attempt_key_sha256,
            expected_manifest_sha256=manifest.canonical_sha256,
        )


@pytest.mark.parametrize("mutation", ("unknown-field", "missing-field"))
def test_loader_strictly_replays_persisted_source_descriptor_fields(
    tmp_path: Path,
    mutation: str,
) -> None:
    transaction = _transaction(tmp_path)
    loaded = _persist(transaction)
    document = transaction.descriptor.to_dict()
    if mutation == "unknown-field":
        document["unreviewed_extension"] = False
    else:
        document.pop("trust_scope")
    source = canonical_json_bytes(document)
    manifest = _rewrite_persisted_members_and_manifest(
        loaded,
        {
            start_persistence.D7_LAUNCH_AUTHORITY_SOURCE_ENVELOPE_FILENAME: source,
        },
    )

    with pytest.raises(QualificationContractError, match="keys differ"):
        start_persistence.load_d7_authoritative_start_transaction(
            transaction.values.store,
            attempt_key_sha256=transaction.values.start.attempt_key_sha256,
            expected_manifest_sha256=manifest.canonical_sha256,
        )


@pytest.mark.parametrize(
    "field",
    (
        "launch_bundle_sha256",
        "source_runtime_closure_sha256",
        "family_admission_sha256",
        "physical_identity_sha256",
    ),
)
def test_loader_rejects_evidence_digest_splice_against_descriptor_inventory(
    tmp_path: Path,
    field: str,
) -> None:
    transaction = _transaction(tmp_path)
    loaded = _persist(transaction)
    verification = replace(
        transaction.verification,
        **{field: _h(f"spliced-{field}")},
    )
    manifest = _rewrite_persisted_members_and_manifest(
        loaded,
        {
            start_persistence.D7_AUTHORITY_VERIFICATION_EVIDENCE_FILENAME: (
                verification.canonical_bytes
            ),
        },
    )

    with pytest.raises(QualificationContractError, match="descriptor inventory"):
        start_persistence.load_d7_authoritative_start_transaction(
            transaction.values.store,
            attempt_key_sha256=transaction.values.start.attempt_key_sha256,
            expected_manifest_sha256=manifest.canonical_sha256,
        )


@pytest.mark.parametrize(
    ("field", "descriptor_role", "error_fragment"),
    (
        ("descriptor_sha256", None, "descriptor source digest"),
        ("attempt_key_sha256", None, "attempt binding"),
        ("replay_target_sha256", "replay-target", "replay-target binding"),
        ("launch_intent_sha256", "launch-intent", "launch-intent binding"),
        (
            "execution_identity_sha256",
            "execution-identity",
            "execution-identity binding",
        ),
        (
            "runtime_specification_sha256",
            "runtime-specification",
            "runtime-specification binding",
        ),
        (
            "full_design_freeze_sha256",
            "full-design-freeze",
            "full-design-freeze binding",
        ),
    ),
)
def test_loader_rejects_semantic_splice_after_coherent_manifest_and_descriptor_rewrite(
    tmp_path: Path,
    field: str,
    descriptor_role: str | None,
    error_fragment: str,
) -> None:
    transaction = _transaction(tmp_path)
    loaded = _persist(transaction)
    spliced_sha256 = _h(f"spliced-{field}")
    replacements: dict[str, bytes] = {}
    if descriptor_role is None:
        verification = replace(
            transaction.verification,
            **{field: spliced_sha256},
        )
    else:
        descriptor = replace(
            transaction.descriptor,
            inventory=tuple(
                replace(member, canonical_sha256=spliced_sha256)
                if member.artifact_role == descriptor_role
                else member
                for member in transaction.descriptor.inventory
            ),
        )
        verification = replace(
            transaction.verification,
            **{
                field: spliced_sha256,
                "descriptor_sha256": descriptor.canonical_sha256,
            },
        )
        replacements[start_persistence.D7_LAUNCH_AUTHORITY_SOURCE_ENVELOPE_FILENAME] = (
            descriptor.canonical_bytes
        )
    replacements[start_persistence.D7_AUTHORITY_VERIFICATION_EVIDENCE_FILENAME] = (
        verification.canonical_bytes
    )
    manifest = _rewrite_persisted_members_and_manifest(
        loaded,
        replacements,
    )

    with pytest.raises(QualificationContractError, match=error_fragment):
        start_persistence.load_d7_authoritative_start_transaction(
            transaction.values.store,
            attempt_key_sha256=transaction.values.start.attempt_key_sha256,
            expected_manifest_sha256=manifest.canonical_sha256,
        )


def test_loader_preserves_but_does_not_reauthenticate_live_observation_digests(
    tmp_path: Path,
) -> None:
    transaction = _transaction(tmp_path)
    loaded = _persist(transaction)
    preserved_only = replace(
        transaction.verification,
        repository_head_commit="b" * 40,
        canonical_origin_observation_sha256=_h("different-origin-observation"),
        source_tree_sha256=_h("different-source-tree"),
        transitive_dependency_set_sha256=_h("different-dependency-set"),
        callable_identity_sha256=_h("different-callable"),
        process_identity_sha256=_h("different-process"),
    )
    manifest = _rewrite_persisted_members_and_manifest(
        loaded,
        {
            start_persistence.D7_AUTHORITY_VERIFICATION_EVIDENCE_FILENAME: (
                preserved_only.canonical_bytes
            ),
        },
    )

    reloaded = start_persistence.load_d7_authoritative_start_transaction(
        transaction.values.store,
        attempt_key_sha256=transaction.values.start.attempt_key_sha256,
        expected_manifest_sha256=manifest.canonical_sha256,
    )

    assert reloaded.verification_evidence_binding.canonical_sha256 == (
        preserved_only.canonical_sha256
    )
    assert reloaded.verification_evidence_strictly_parsed is True
    assert reloaded.verification_evidence_descriptor_and_start_subset_rejoined is True
    assert reloaded.live_observation_digests_reauthenticated is False
    assert reloaded.all_live_observation_digests_semantically_rejoined is False
    assert reloaded.authority_authenticated is False
    assert reloaded.authority_granted is False


def test_lane_must_preexist_and_authority_binding_roles_are_exact(
    tmp_path: Path,
) -> None:
    missing_lane_store = tmp_path / "missing-lane"
    missing_lane_store.mkdir()
    missing = _prefix(missing_lane_store)
    launch = _launch_material(missing)
    with pytest.raises(QualificationContractError, match="lane"):
        start_persistence.persist_d7_authoritative_start_transaction_no_replace(
            missing.store,
            launch_authority_source_envelope_source=launch.descriptor.canonical_bytes,
            launch_authority_source_envelope_binding=launch.descriptor_binding,
            verification_evidence_source=launch.verification.canonical_bytes,
            verification_evidence_binding=launch.verification_binding,
            declaration=missing.declaration,
            authorization_output_receipt=missing.authorization_output,
            authorization_terminal_receipt=missing.authorization_terminal,
            authorization=missing.authorization,
            claim=missing.claim,
            pre_start_output_receipt=missing.pre_start_output,
            pre_start_terminal_receipt=missing.pre_start_terminal,
            start=missing.start,
        )

    transaction = _transaction(tmp_path / "bad-binding")
    wrong_role = _opaque_binding(
        "untrusted-caller-token",
        transaction.authority_source_binding.artifact_contract_id,
        transaction.authority_source,
    )
    transaction.authority_source_binding = wrong_role
    with pytest.raises(QualificationContractError, match="binding role"):
        _persist(transaction)
    assert not tuple(transaction.lane.glob("*.authoritative-start"))


def test_byte_identical_existing_destination_is_always_a_conflict(
    tmp_path: Path,
) -> None:
    transaction = _transaction(tmp_path)
    first = _persist(transaction)
    manifest_bytes = (first.path / "start-manifest.json").read_bytes()

    with pytest.raises(QualificationContractError, match="replace existing"):
        _persist(transaction)

    assert (first.path / "start-manifest.json").read_bytes() == manifest_bytes
    assert _load(transaction, first).directory_identity_sha256 == (
        first.directory_identity_sha256
    )


def test_concurrent_writers_have_one_complete_no_replace_winner(
    tmp_path: Path,
) -> None:
    transaction = _transaction(tmp_path)

    def publish() -> object:
        try:
            return _persist(transaction)
        except QualificationContractError as error:
            return error

    with ThreadPoolExecutor(max_workers=8) as executor:
        outcomes = tuple(executor.map(lambda _index: publish(), range(8)))
    winners = tuple(
        outcome
        for outcome in outcomes
        if type(outcome) is start_persistence.D7LoadedAuthoritativeStartTransaction
    )
    losers = tuple(
        outcome for outcome in outcomes if type(outcome) is QualificationContractError
    )

    assert len(winners) == 1
    assert len(losers) == 7
    assert _load(transaction, winners[0]).start == transaction.values.start
    assert not tuple(transaction.lane.glob(".*.tmp"))


def test_attempt_scoped_staging_orphan_blocks_publish_and_load(
    tmp_path: Path,
) -> None:
    transaction = _transaction(tmp_path)
    prefix = start_persistence._staging_prefix(
        transaction.values.start.attempt_key_sha256
    )
    orphan = transaction.lane / f"{prefix}crash.tmp"
    orphan.mkdir()
    (orphan / "partial.json").write_bytes(b"{}")

    with pytest.raises(QualificationContractError, match="offline recovery"):
        _persist(transaction)
    with pytest.raises(QualificationContractError, match="offline recovery"):
        start_persistence.load_d7_authoritative_start_transaction(
            transaction.values.store,
            attempt_key_sha256=transaction.values.start.attempt_key_sha256,
            expected_manifest_sha256="0" * 64,
        )
    assert orphan.is_dir()


@pytest.mark.parametrize(
    "mutation",
    ("extra", "missing", "tamper", "symlink", "hardlink", "fifo"),
)
def test_strict_loader_rejects_inventory_alias_and_type_violations(
    tmp_path: Path,
    mutation: str,
) -> None:
    transaction = _transaction(tmp_path)
    loaded = _persist(transaction)
    target = loaded.path / start_persistence.D7_AUTHORITY_VERIFICATION_EVIDENCE_FILENAME
    if mutation == "extra":
        (loaded.path / "unknown.json").write_bytes(b"{}")
    elif mutation == "missing":
        target.unlink()
    elif mutation == "tamper":
        target.write_bytes(b"{}")
    elif mutation == "symlink":
        target.unlink()
        target.symlink_to(
            loaded.path / start_persistence.D7_LAUNCH_AUTHORITY_SOURCE_ENVELOPE_FILENAME
        )
    elif mutation == "hardlink":
        os.link(target, tmp_path / "outside-hardlink.json")
    else:
        assert persistence._file_read_flags() & os.O_NONBLOCK
        target.unlink()
        os.mkfifo(target)

    with pytest.raises(QualificationContractError):
        _load(transaction, loaded)


def test_loader_rejects_same_name_member_replacement_during_reload(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    transaction = _transaction(tmp_path)
    loaded = _persist(transaction)
    target = loaded.path / start_persistence.D7_AUTHORITY_VERIFICATION_EVIDENCE_FILENAME
    original = target.read_bytes()
    real_revalidate = terminal_persistence._revalidate_file_set
    replaced = False

    def replace_then_revalidate(directory: object, expected: object) -> None:
        nonlocal replaced
        if not replaced:
            replaced = True
            target.unlink()
            target.write_bytes(original)
        real_revalidate(directory, expected)  # type: ignore[arg-type]

    monkeypatch.setattr(
        terminal_persistence,
        "_revalidate_file_set",
        replace_then_revalidate,
    )
    with pytest.raises(QualificationContractError, match="changed during"):
        _load(transaction, loaded)


def test_stage_mutation_is_rejected_before_publication(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    transaction = _transaction(tmp_path)
    real_revalidate = terminal_persistence._revalidate_file_set
    mutated = False

    def mutate_stage_then_revalidate(directory: object, expected: object) -> None:
        nonlocal mutated
        path = directory.path  # type: ignore[attr-defined]
        if not mutated and ".d7-authoritative-start-transaction." in path.name:
            mutated = True
            target = (
                path / start_persistence.D7_AUTHORITY_VERIFICATION_EVIDENCE_FILENAME
            )
            target.write_bytes(b"{}")
        real_revalidate(directory, expected)  # type: ignore[arg-type]

    monkeypatch.setattr(
        terminal_persistence,
        "_revalidate_file_set",
        mutate_stage_then_revalidate,
    )
    with pytest.raises(QualificationContractError):
        _persist(transaction)
    assert mutated is True
    assert not tuple(transaction.lane.glob("*.authoritative-start"))
    assert not tuple(transaction.lane.glob(".*.tmp"))


def test_rename_success_followed_by_error_recovers_owned_directory(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    transaction = _transaction(tmp_path)
    real_rename = persistence._rename_file_no_replace

    def rename_then_error(
        anchor: object,
        source_leaf: str,
        destination_leaf: str,
    ) -> None:
        real_rename(anchor, source_leaf, destination_leaf)  # type: ignore[arg-type]
        raise OSError(errno.EIO, "injected ambiguous rename result")

    monkeypatch.setattr(
        persistence,
        "_rename_file_no_replace",
        rename_then_error,
    )
    loaded = _persist(transaction)

    assert loaded.path.is_dir()
    assert loaded.parent_directory_fsync_proved is True
    assert _load(transaction, loaded).start == transaction.values.start
    assert not tuple(transaction.lane.glob(".*.tmp"))


def test_post_rename_parent_fsync_failure_is_visible_but_not_durable(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    transaction = _transaction(tmp_path)
    monkeypatch.setattr(
        start_persistence,
        "_fsync_published_parent",
        lambda _lane: False,
    )

    loaded = _persist(transaction)

    assert loaded.path.is_dir()
    assert loaded.created_by_call is True
    assert loaded.parent_directory_fsync_proved is False
    reloaded = _load(transaction, loaded)
    assert reloaded.parent_directory_fsync_proved is None
    with pytest.raises(QualificationContractError, match="replace existing"):
        _persist(transaction)


def test_live_path_occupation_before_publication_leaves_no_start(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    transaction = _transaction(tmp_path)
    real_reobserve = persistence._reobserve_absence
    observations = 0

    def occupy_after_initial_observations(
        store: Path,
        receipt: object,
    ) -> None:
        nonlocal observations
        real_reobserve(store, receipt)  # type: ignore[arg-type]
        observations += 1
        if observations == 2:
            (transaction.values.store / "primary-terminal").write_bytes(b"occupied")

    monkeypatch.setattr(
        persistence, "_reobserve_absence", occupy_after_initial_observations
    )
    with pytest.raises(QualificationContractError, match="present"):
        _persist(transaction)

    assert not tuple(transaction.lane.glob("*.authoritative-start"))
    assert not tuple(transaction.lane.glob(".*.tmp"))


def test_module_is_deep_internal_and_cannot_issue_runner_ownership() -> None:
    assert start_persistence.__all__ == ()
    assert not hasattr(spirallens, "D7LoadedAuthoritativeStartTransaction")
    assert not hasattr(qualification, "D7LoadedAuthoritativeStartTransaction")
    assert not hasattr(start_persistence, "issue_d7_post_start_ownership")
    assert not hasattr(start_persistence, "run_d7_confirmation")
    assert not hasattr(start_persistence, "authenticate_d7_authority")
    assert not hasattr(start_persistence, "authorize_d7_fused_start")
