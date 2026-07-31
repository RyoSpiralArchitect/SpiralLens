from __future__ import annotations

import copy
import json
import os
import pickle
import subprocess
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Callable

import pytest

import test_d7_confirmation_attempt_authority as authority_fixtures
import spirallens.qualification as qualification
from spirallens.core.canonical import canonical_json_bytes, sha256_bytes
from spirallens.qualification import confirmation_attempt_authority as authority
from spirallens.qualification import confirmation_fused_authority as fused
from spirallens.qualification.common import QualificationContractError


@dataclass(frozen=True, slots=True)
class _AuthorityRepository:
    root: Path
    descriptor_path: Path
    bundle: authority.D7LaunchAuthorityInputBundle
    member_paths: dict[str, Path]
    source_commit: str
    freeze_commit: str
    authorization_commit: str
    head_commit: str


def _git(root: Path, *arguments: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(root), *arguments],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _commit_marker(root: Path, name: str) -> str:
    path = root / "history" / f"{name}.txt"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"{name}\n", encoding="utf-8")
    _git(root, "add", "--", path.relative_to(root).as_posix())
    _git(root, "commit", "-q", "-m", name)
    return _git(root, "rev-parse", "HEAD")


def _binding(
    role: str,
    record: object,
) -> authority.D7AuthorityArtifactBinding:
    return authority.D7AuthorityArtifactBinding.from_record(
        artifact_role=role,
        artifact_contract_id=record.schema_version,  # type: ignore[attr-defined]
        record=record,  # type: ignore[arg-type]
    )


def _bundle_with_git_chronology(
    *,
    source_commit: str,
    freeze_commit: str,
    authorization_commit: str,
) -> authority.D7LaunchAuthorityInputBundle:
    base = authority_fixtures._bundle()
    closure = replace(base.source_runtime_closure, source_commit=source_commit)
    family_admission = replace(
        base.family_admission,
        source_runtime_closure_binding=_binding(
            "execution-source-runtime-closure",
            closure,
        ),
    )
    execution_identity = replace(
        base.execution_identity,
        source_runtime_closure_binding=_binding(
            "execution-source-runtime-closure",
            closure,
        ),
    )
    design_freeze = replace(
        base.full_design_freeze,
        freeze_commit=freeze_commit,
        authorization_commit=authorization_commit,
    )
    launch_intent = replace(
        base.launch_intent,
        full_design_freeze_binding=_binding("full-design-freeze", design_freeze),
        execution_identity_binding=_binding(
            "execution-identity",
            execution_identity,
        ),
        freeze_commit=freeze_commit,
        authorization_commit=authorization_commit,
    )
    chronology = list(base.chronology)
    chronology[7] = replace(
        chronology[7],
        subject_bindings=(_binding("full-design-freeze", design_freeze),),
    )
    chronology[8] = replace(
        chronology[8],
        predecessor_binding=chronology[7].artifact_binding,
        subject_bindings=(_binding("launch-intent", launch_intent),),
    )
    return replace(
        base,
        source_runtime_closure=closure,
        family_admission=family_admission,
        execution_identity=execution_identity,
        full_design_freeze=design_freeze,
        launch_intent=launch_intent,
        chronology=tuple(chronology),
    )


def _member_records(
    bundle: authority.D7LaunchAuthorityInputBundle,
) -> tuple[tuple[str, str, object], ...]:
    return (
        (
            "launch-authority-input-bundle",
            bundle.schema_version,
            bundle,
        ),
        ("replay-target", bundle.replay_target.schema_version, bundle.replay_target),
        ("launch-intent", bundle.launch_intent.schema_version, bundle.launch_intent),
        (
            "execution-source-runtime-closure",
            bundle.source_runtime_closure.schema_version,
            bundle.source_runtime_closure,
        ),
        (
            "runtime-specification",
            bundle.runtime_specification.schema_version,
            bundle.runtime_specification,
        ),
        (
            "family-admission",
            bundle.family_admission.schema_version,
            bundle.family_admission,
        ),
        (
            "execution-identity",
            bundle.execution_identity.schema_version,
            bundle.execution_identity,
        ),
        (
            "physical-store-lane-identity",
            bundle.physical_store_lane_identity.schema_version,
            bundle.physical_store_lane_identity,
        ),
        (
            "full-design-freeze",
            bundle.full_design_freeze.schema_version,
            bundle.full_design_freeze,
        ),
    )


def _build_repository(tmp_path: Path) -> _AuthorityRepository:
    root = tmp_path / "authority-repository"
    root.mkdir()
    _git(root, "init", "-q")
    _git(root, "config", "user.name", "SpiralLens Test")
    _git(root, "config", "user.email", "spirallens@example.invalid")

    source_commit = _commit_marker(root, "source")
    freeze_commit = _commit_marker(root, "freeze")
    authorization_commit = _commit_marker(root, "authorization")
    bundle = _bundle_with_git_chronology(
        source_commit=source_commit,
        freeze_commit=freeze_commit,
        authorization_commit=authorization_commit,
    )

    members: list[fused._D7FusedAuthorityMember] = []
    member_paths: dict[str, Path] = {}
    for index, (role, contract_id, record) in enumerate(_member_records(bundle)):
        repository_path = f"authority/members/{index:02d}-{role}.json"
        path = root / repository_path
        path.parent.mkdir(parents=True, exist_ok=True)
        source = record.canonical_bytes  # type: ignore[attr-defined]
        path.write_bytes(source)
        member_paths[role] = path
        members.append(
            fused._D7FusedAuthorityMember(
                artifact_role=role,
                artifact_contract_id=contract_id,
                repository_path=repository_path,
                canonical_sha256=sha256_bytes(source),
                byte_count=len(source),
            )
        )

    descriptor_repository_path = "authority/launch-descriptor.json"
    descriptor_path = root / descriptor_repository_path
    descriptor = fused._D7FusedAuthorityLaunchDescriptor(
        descriptor_id="d7-fused-authority-launch-descriptor-v0-1",
        descriptor_repository_path=descriptor_repository_path,
        inventory=tuple(members),
    )
    descriptor_path.write_bytes(descriptor.canonical_bytes)
    _git(root, "add", "--", "authority")
    _git(root, "commit", "-q", "-m", "persist closed authority inventory")
    head_commit = _git(root, "rev-parse", "HEAD")
    return _AuthorityRepository(
        root=root,
        descriptor_path=descriptor_path,
        bundle=bundle,
        member_paths=member_paths,
        source_commit=source_commit,
        freeze_commit=freeze_commit,
        authorization_commit=authorization_commit,
        head_commit=head_commit,
    )


def _rewrite_descriptor(
    repository: _AuthorityRepository,
    mutate: Callable[[dict[str, object]], None],
) -> None:
    document = repository.descriptor_path.read_text(encoding="utf-8")
    parsed = json.loads(document)
    mutate(parsed)
    repository.descriptor_path.write_bytes(canonical_json_bytes(parsed))
    _git(repository.root, "add", "--", "authority/launch-descriptor.json")
    _git(repository.root, "commit", "-q", "-m", "mutate descriptor")


def test_current_head_closed_inventory_rejoins_without_authorizing(
    tmp_path: Path,
) -> None:
    repository = _build_repository(tmp_path)

    loaded = fused.load_d7_fused_authority_snapshot(repository.descriptor_path)

    assert loaded.descriptor_path == repository.descriptor_path
    assert loaded.repository_root == repository.root
    assert loaded.head_commit == repository.head_commit
    assert loaded.bundle == repository.bundle
    assert loaded.replay_target == repository.bundle.replay_target
    assert loaded.launch_intent == repository.bundle.launch_intent
    assert loaded.source_runtime_closure == repository.bundle.source_runtime_closure
    assert loaded.runtime_specification == repository.bundle.runtime_specification
    assert loaded.family_admission == repository.bundle.family_admission
    assert loaded.execution_identity == repository.bundle.execution_identity
    assert loaded.physical_identity == repository.bundle.physical_store_lane_identity
    assert loaded.full_design_freeze == repository.bundle.full_design_freeze
    assert loaded.member_paths == tuple(repository.member_paths.values())
    assert loaded.same_call_only is True
    assert loaded.git_current_head_blob_equality_verified is True
    assert loaded.closed_inventory_verified is True
    assert loaded.structural_bundle_rejoined is True
    for flag in (
        "authority_granted",
        "authority_authenticated",
        "repository_trust_root_authenticated",
        "target_authoritative",
        "source_runtime_verified",
        "family_admission_verified",
        "seed_free_readiness_verified",
        "official_seed_chronology_verified",
        "seed_supply_claim_verified",
        "supplier_invocation_verified",
        "inventory_output_verified",
        "atomic_publication_verified",
        "execution_identity_verified",
        "physical_identity_reobserved",
        "path_absence_observed",
        "alternate_store_exclusivity_proved",
        "hostile_mutation_resistant",
        "full_design_freeze_verified",
        "launch_intent_verified",
        "launch_authorized",
        "launch_authorization_derived",
        "exclusive_start_authorized",
        "authoritative_lifecycle_eligible",
        "in_place_promotion_allowed",
        "terminal_publication_authorized",
        "finalization_authorized",
        "unresolved_finalization_authorized",
        "isolated_replay_authorized",
        "execution_authorized",
        "execution_observed",
        "d7_result_produced",
        "scientific_claim_eligible",
        "reusable_authorization_capability_present",
        "d7_execution_authorized",
        "d8_execution_authorized",
    ):
        assert getattr(loaded, flag) is False
    assert fused.__all__ == ()
    assert not hasattr(qualification, "load_d7_fused_authority_snapshot")
    with pytest.raises(TypeError, match="in-process handoff"):
        pickle.dumps(loaded)
    with pytest.raises(TypeError, match="cannot be copied"):
        copy.copy(loaded)
    with pytest.raises(AttributeError, match="immutable"):
        loaded._head_commit = "0" * 40


def test_dirty_member_is_rejected_against_current_head(tmp_path: Path) -> None:
    repository = _build_repository(tmp_path)
    repository.member_paths["runtime-specification"].write_bytes(b"{}\n")

    with pytest.raises(
        QualificationContractError,
        match="differs from its current-HEAD blob",
    ):
        fused.load_d7_fused_authority_snapshot(repository.descriptor_path)


def test_staged_index_divergence_is_rejected_even_when_worktree_matches_head(
    tmp_path: Path,
) -> None:
    repository = _build_repository(tmp_path)
    member = repository.member_paths["runtime-specification"]
    head_source = member.read_bytes()
    member.write_bytes(b"{}\n")
    _git(
        repository.root,
        "add",
        "--",
        member.relative_to(repository.root).as_posix(),
    )
    member.write_bytes(head_source)

    with pytest.raises(
        QualificationContractError,
        match="index entry differs from current HEAD",
    ):
        fused.load_d7_fused_authority_snapshot(repository.descriptor_path)


def test_descriptor_member_digest_is_checked_before_member_parse(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = _build_repository(tmp_path)
    role = "launch-authority-input-bundle"

    def mutate(document: dict[str, object]) -> None:
        inventory = document["inventory"]
        assert isinstance(inventory, list)
        member = inventory[0]
        assert isinstance(member, dict)
        assert member["artifact_role"] == role
        member["canonical_sha256"] = "f" * 64

    _rewrite_descriptor(repository, mutate)
    original_parse = fused.parse_canonical_json

    def guarded_parse(source: bytes, *, label: str) -> object:
        if label == role:
            raise AssertionError("wrong-digest member reached canonical parser")
        return original_parse(source, label=label)

    monkeypatch.setattr(fused, "parse_canonical_json", guarded_parse)
    with pytest.raises(
        QualificationContractError,
        match="differs from the descriptor inventory",
    ):
        fused.load_d7_fused_authority_snapshot(repository.descriptor_path)


def test_untracked_member_cannot_be_named_by_a_committed_descriptor(
    tmp_path: Path,
) -> None:
    repository = _build_repository(tmp_path)
    role = "runtime-specification"
    untracked = repository.root / "authority" / "untracked-runtime.json"
    untracked.write_bytes(repository.member_paths[role].read_bytes())

    def mutate(document: dict[str, object]) -> None:
        inventory = document["inventory"]
        assert isinstance(inventory, list)
        member = next(
            item
            for item in inventory
            if isinstance(item, dict) and item["artifact_role"] == role
        )
        member["repository_path"] = "authority/untracked-runtime.json"

    _rewrite_descriptor(repository, mutate)
    with pytest.raises(
        QualificationContractError,
        match="not exactly one current-HEAD entry",
    ):
        fused.load_d7_fused_authority_snapshot(repository.descriptor_path)


def test_sibling_escape_is_rejected_before_member_open(tmp_path: Path) -> None:
    repository = _build_repository(tmp_path)

    def mutate(document: dict[str, object]) -> None:
        inventory = document["inventory"]
        assert isinstance(inventory, list)
        member = inventory[0]
        assert isinstance(member, dict)
        member["repository_path"] = "../sibling/bundle.json"

    _rewrite_descriptor(repository, mutate)
    with pytest.raises(
        QualificationContractError,
        match="normalized in-repository portable path",
    ):
        fused.load_d7_fused_authority_snapshot(repository.descriptor_path)


def test_separately_valid_member_must_exactly_rejoin_bundle(tmp_path: Path) -> None:
    repository = _build_repository(tmp_path)
    role = "physical-store-lane-identity"
    replacement = replace(
        repository.bundle.physical_store_lane_identity,
        physical_identity_id="different-physical-store-lane-identity-v0-1",
    )
    source = replacement.canonical_bytes
    repository.member_paths[role].write_bytes(source)

    def mutate(document: dict[str, object]) -> None:
        inventory = document["inventory"]
        assert isinstance(inventory, list)
        member = next(
            item
            for item in inventory
            if isinstance(item, dict) and item["artifact_role"] == role
        )
        member["canonical_sha256"] = sha256_bytes(source)
        member["byte_count"] = len(source)

    _rewrite_descriptor(repository, mutate)
    _git(
        repository.root,
        "add",
        "--",
        repository.member_paths[role].relative_to(repository.root).as_posix(),
    )
    _git(repository.root, "commit", "-q", "-m", "persist mismatched member")

    with pytest.raises(
        QualificationContractError,
        match="does not exactly rejoin",
    ):
        fused.load_d7_fused_authority_snapshot(repository.descriptor_path)


@pytest.mark.parametrize("mutation", ["unknown", "missing", "laundered"])
def test_descriptor_cannot_expand_omit_or_launder_authority(
    tmp_path: Path,
    mutation: str,
) -> None:
    repository = _build_repository(tmp_path)

    def mutate(document: dict[str, object]) -> None:
        inventory = document["inventory"]
        assert isinstance(inventory, list)
        if mutation == "unknown":
            member = inventory[-1]
            assert isinstance(member, dict)
            member["artifact_role"] = "unknown-authority-input"
        elif mutation == "missing":
            inventory.pop()
        else:
            document["authority_authenticated"] = True

    _rewrite_descriptor(repository, mutate)
    with pytest.raises(QualificationContractError):
        fused.load_d7_fused_authority_snapshot(repository.descriptor_path)


@pytest.mark.parametrize("replacement_kind", ["symlink", "hardlink", "fifo"])
def test_member_must_remain_one_real_non_hardlinked_regular_file(
    tmp_path: Path,
    replacement_kind: str,
) -> None:
    repository = _build_repository(tmp_path)
    member = repository.member_paths["family-admission"]
    source = member.read_bytes()
    if replacement_kind == "hardlink":
        os.link(member, repository.root / "untracked-hardlink")
    else:
        member.unlink()
        if replacement_kind == "symlink":
            target = repository.root / "untracked-symlink-target"
            target.write_bytes(source)
            member.symlink_to(target)
        else:
            os.mkfifo(member)

    with pytest.raises(QualificationContractError):
        fused.load_d7_fused_authority_snapshot(repository.descriptor_path)


def test_member_replacement_before_snapshot_return_is_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = _build_repository(tmp_path)
    member = repository.member_paths["execution-identity"]
    replacement = repository.root / "untracked-replacement"
    replacement.write_bytes(member.read_bytes())
    original_revalidate = fused._revalidate_identity
    replaced = False

    def replace_before_revalidation(identity: fused._StableFileIdentity) -> None:
        nonlocal replaced
        if identity.path == member and not replaced:
            os.replace(replacement, member)
            replaced = True
        original_revalidate(identity)

    monkeypatch.setattr(fused, "_revalidate_identity", replace_before_revalidation)
    with pytest.raises(
        QualificationContractError,
        match="replaced before snapshot return",
    ):
        fused.load_d7_fused_authority_snapshot(repository.descriptor_path)
    assert replaced is True


def test_source_freeze_authorization_and_head_must_be_strictly_ordered(
    tmp_path: Path,
) -> None:
    repository = _build_repository(tmp_path)
    collapsed = _bundle_with_git_chronology(
        source_commit=repository.source_commit,
        freeze_commit=repository.freeze_commit,
        authorization_commit=repository.source_commit,
    )
    descriptor_document = json.loads(
        repository.descriptor_path.read_text(encoding="utf-8")
    )
    inventory = descriptor_document["inventory"]
    assert isinstance(inventory, list)
    member_by_role = {
        member["artifact_role"]: member
        for member in inventory
        if isinstance(member, dict)
    }
    for role, _contract_id, record in _member_records(collapsed):
        source = record.canonical_bytes  # type: ignore[attr-defined]
        repository.member_paths[role].write_bytes(source)
        member_by_role[role]["canonical_sha256"] = sha256_bytes(source)
        member_by_role[role]["byte_count"] = len(source)
    repository.descriptor_path.write_bytes(canonical_json_bytes(descriptor_document))
    _git(repository.root, "add", "--", "authority")
    _git(repository.root, "commit", "-q", "-m", "collapse chronology")

    with pytest.raises(
        QualificationContractError,
        match="freeze-to-authorization ancestry differs",
    ):
        fused.load_d7_fused_authority_snapshot(repository.descriptor_path)
