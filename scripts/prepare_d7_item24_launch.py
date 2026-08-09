#!/usr/bin/env python3
"""Publish the non-authorizing D7 item-24 launch inventory exactly once.

The script reopens the frozen item-22 records, observes one fixed local Python
process envelope and one fixed external persistence lane, then publishes seven
new member projections plus the closed nine-member ``launch.json`` descriptor.
It never calls the scientific producer or the fused start operation.
"""

from __future__ import annotations

import argparse
import inspect
import json
import marshal
import os
import stat
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from types import FunctionType


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
_BOOTSTRAP_SYS_PATH = tuple(sys.path)
sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

from spirallens.core.canonical import (  # noqa: E402
    canonical_json_bytes,
    parse_canonical_json,
    sha256_bytes,
)
from spirallens.qualification import confirmation_attempt_authority as authority  # noqa: E402
from spirallens.qualification import confirmation_attempt_persistence as persistence  # noqa: E402
from spirallens.qualification import confirmation_attempt_records as attempt_records  # noqa: E402
from spirallens.qualification import confirmation_fused_authority as fused_authority  # noqa: E402
from spirallens.qualification import confirmation_fused_start as fused_start  # noqa: E402
from spirallens.qualification import confirmation_official_execution as official  # noqa: E402
from spirallens.qualification import confirmation_seed_supply_contracts as item22  # noqa: E402
from spirallens.qualification.common import QualificationContractError  # noqa: E402

sys.path[:] = _BOOTSTRAP_SYS_PATH
if Path(official.__file__).resolve() != (
    REPOSITORY_ROOT / "src/spirallens/qualification/confirmation_official_execution.py"
):
    raise RuntimeError("item-24 official producer import origin differs")


LAUNCH_MEMBER_DIRECTORY_REPOSITORY_PATH = (
    "experiments/qualification/d7_spectral_moment_confirmation_v0_1/launch-members"
)
LAUNCH_DESCRIPTOR_REPOSITORY_PATH = (
    official.D7_OFFICIAL_FUSED_DESCRIPTOR_REPOSITORY_PATH
)
OFFICIAL_LAUNCHER_REPOSITORY_PATH = "scripts/run_d7_item24.py"
OFFICIAL_STORE_PATH = Path(
    "/Users/ryohiga/SpiralReality/spirallens-d7-item24-store-v0-1"
)
OFFICIAL_STORE_STAGING_PATH = OFFICIAL_STORE_PATH.with_name(
    f".{OFFICIAL_STORE_PATH.name}.staging"
)
OFFICIAL_OUTPUT_BASENAME = "d7-official-output-v0-1"
OFFICIAL_TERMINAL_BASENAME = "d7-official-terminal-v0-1"
_STAGING_DIRECTORY_BASENAME = ".launch-members.staging"

_NEW_MEMBER_FILENAMES = {
    "launch-authority-input-bundle": "launch-authority-input-bundle.json",
    "launch-intent": "launch-intent.json",
    "execution-source-runtime-closure": "execution-source-runtime-closure.json",
    "runtime-specification": "runtime-specification.json",
    "family-admission": "family-admission.json",
    "execution-identity": "execution-identity.json",
    "physical-store-lane-identity": "physical-store-lane-identity.json",
}


@dataclass(frozen=True, slots=True)
class _FrozenItem22Inputs:
    development_registry: authority.D7DevelopmentSeedExclusionRegistryRecord
    parent_registry: authority.D7ParentSelectionSeedExclusionRegistryRecord
    official_seed_inventory: authority.D7OfficialSeedInventoryRecord
    runtime_specification: authority.D7RuntimeSpecificationInputRecord
    source_runtime_closure: authority.D7SourceRuntimeClosureInputRecord
    family_admission: authority.D7FamilyAdmissionInputRecord
    exclusive_seed_supply_claim: authority.D7ExclusiveSeedSupplyClaimInputRecord
    single_supplier_invocation: authority.D7SingleSupplierInvocationInputRecord
    replay_target: authority.D7ReplayTargetInputRecord
    full_design_freeze: authority.D7FullDesignFreezeInputRecord
    chronology: tuple[authority.D7ChronologyInputRecord, ...]
    replay_target_source: bytes
    full_design_freeze_source: bytes


@dataclass(frozen=True, slots=True)
class _LaunchMaterial:
    bundle: authority.D7LaunchAuthorityInputBundle
    descriptor: fused_authority._D7FusedAuthorityLaunchDescriptor
    member_sources: tuple[tuple[str, str, bytes], ...]
    new_member_sources: tuple[tuple[str, bytes], ...]


@dataclass(frozen=True, slots=True)
class _StagedPhysicalStore:
    record: authority.D7PhysicalStoreLaneIdentityRecord
    staging_device: int
    staging_inode: int
    lane_device: int
    lane_inode: int


_PROMOTED_STORE_FACTORY_TOKEN = object()


class _PromotedPhysicalStore:
    """One-call, descriptor-bound witness retaining live directory anchors."""

    __slots__ = (
        "record",
        "parent",
        "store",
        "lane",
        "_consumed",
    )

    def __init__(
        self,
        *,
        record: authority.D7PhysicalStoreLaneIdentityRecord,
        parent: persistence._DirectoryAnchor,
        store: persistence._DirectoryAnchor,
        lane: persistence._DirectoryAnchor,
        _factory_token: object,
    ) -> None:
        if _factory_token is not _PROMOTED_STORE_FACTORY_TOKEN:
            raise TypeError("promoted-store witness requires its exclusive promoter")
        self.record = record
        self.parent = parent
        self.store = store
        self.lane = lane
        self._consumed = False


def _git(root: Path, *arguments: str) -> bytes:
    completed = subprocess.run(
        ["git", "-C", str(root), *arguments],
        check=True,
        capture_output=True,
    )
    return completed.stdout


def _read_tracked_canonical(
    root: Path,
    repository_path: str,
) -> tuple[dict[str, object], bytes]:
    source = _require_tracked_current_file(root, repository_path)
    parsed = parse_canonical_json(source, label=repository_path)
    if type(parsed) is not dict or canonical_json_bytes(parsed) != source:
        raise QualificationContractError(
            f"canonical artifact differs: {repository_path}"
        )
    return dict(parsed), source


def _load_record(
    root: Path,
    repository_path: str,
    record_type: type[object],
) -> tuple[object, bytes]:
    document, source = _read_tracked_canonical(root, repository_path)
    try:
        record = record_type.from_dict(document)  # type: ignore[attr-defined]
    except (TypeError, ValueError) as error:
        raise QualificationContractError(
            f"frozen item-22 record is invalid: {repository_path}"
        ) from error
    if record.canonical_bytes != source:  # type: ignore[attr-defined]
        raise QualificationContractError(
            f"frozen item-22 record does not round-trip: {repository_path}"
        )
    return record, source


def _load_frozen_item22_inputs(root: Path) -> _FrozenItem22Inputs:
    state = item22.observe_d7_item22_seed_supply_state(root)
    if state != "full-design-frozen":
        raise QualificationContractError(
            "item-24 preparation requires the exact full-design-frozen state"
        )

    target_root = item22.D7_ITEM22_ATOMIC_TARGET_DIRECTORY_REPOSITORY_PATH
    inventory, _ = _load_record(
        root,
        f"{target_root}/official-seed-inventory.json",
        authority.D7OfficialSeedInventoryRecord,
    )
    invocation, _ = _load_record(
        root,
        f"{target_root}/single-supplier-invocation.json",
        authority.D7SingleSupplierInvocationInputRecord,
    )
    replay_target, replay_source = _load_record(
        root,
        f"{target_root}/replay-target.json",
        authority.D7ReplayTargetInputRecord,
    )
    claim, _ = _load_record(
        root,
        item22.D7_ITEM22_EXCLUSIVE_SEED_SUPPLY_CLAIM_REPOSITORY_PATH,
        authority.D7ExclusiveSeedSupplyClaimInputRecord,
    )
    freeze, freeze_source = _load_record(
        root,
        item22.D7_ITEM22_FULL_DESIGN_FREEZE_REPOSITORY_PATH,
        authority.D7FullDesignFreezeInputRecord,
    )
    manifest, _ = _read_tracked_canonical(
        root,
        f"{target_root}/transaction-manifest.json",
    )
    runtime = authority.D7RuntimeSpecificationInputRecord.from_dict(
        manifest["runtime_specification"]
    )
    closure = authority.D7SourceRuntimeClosureInputRecord.from_dict(
        manifest["source_runtime_closure"]
    )
    family = authority.D7FamilyAdmissionInputRecord.from_dict(
        manifest["family_admission"]
    )
    chronology = tuple(
        authority.D7ChronologyInputRecord.from_dict(item)
        for item in manifest["chronology"]  # type: ignore[union-attr]
    )
    if (
        tuple(record.transition for record in chronology)
        != authority.D7_SEED_SUPPLY_TRANSITION_ORDER[:7]
    ):
        raise QualificationContractError("item-22 chronology prefix differs")
    return _FrozenItem22Inputs(
        development_registry=(
            authority.D7DevelopmentSeedExclusionRegistryRecord.exact()
        ),
        parent_registry=(
            authority.D7ParentSelectionSeedExclusionRegistryRecord.exact()
        ),
        official_seed_inventory=inventory,  # type: ignore[arg-type]
        runtime_specification=runtime,
        source_runtime_closure=closure,
        family_admission=family,
        exclusive_seed_supply_claim=claim,  # type: ignore[arg-type]
        single_supplier_invocation=invocation,  # type: ignore[arg-type]
        replay_target=replay_target,  # type: ignore[arg-type]
        full_design_freeze=freeze,  # type: ignore[arg-type]
        chronology=chronology,
        replay_target_source=replay_source,
        full_design_freeze_source=freeze_source,
    )


def _binding(
    role: str,
    record: object,
) -> authority.D7AuthorityArtifactBinding:
    return authority.D7AuthorityArtifactBinding.from_record(
        artifact_role=role,
        artifact_contract_id=record.schema_version,  # type: ignore[attr-defined]
        record=record,  # type: ignore[arg-type]
    )


def _require_tracked_current_file(root: Path, repository_path: str) -> bytes:
    path = root / repository_path
    observed = path.read_bytes()
    head = _git(root, "show", f"HEAD:{repository_path}")
    if observed != head:
        raise QualificationContractError(
            f"reviewed launch input differs from current HEAD: {repository_path}"
        )
    return observed


def _execution_identity(
    root: Path,
    frozen: _FrozenItem22Inputs,
) -> authority.D7ExecutionIdentityInputRecord:
    producer = official.produce_d7_official_result
    if type(producer) is not FunctionType:
        raise QualificationContractError("official producer is not one function")
    producer_source_file = Path(os.path.realpath(inspect.getsourcefile(producer) or ""))
    try:
        producer_repository_path = producer_source_file.relative_to(root).as_posix()
    except ValueError as error:
        raise QualificationContractError(
            "official producer source is outside the repository"
        ) from error
    producer_source = _require_tracked_current_file(
        root,
        producer_repository_path,
    )
    _require_tracked_current_file(root, OFFICIAL_LAUNCHER_REPOSITORY_PATH)

    executable = Path(os.path.realpath(sys.executable))
    executable_stat = executable.stat()
    if not stat.S_ISREG(executable_stat.st_mode):
        raise QualificationContractError("execution interpreter is not a real file")
    executable_sha256 = sha256_bytes(executable.read_bytes())
    if executable_sha256 != frozen.runtime_specification.native_runtime_sha256:
        raise QualificationContractError(
            "preparation interpreter differs from the frozen native runtime"
        )
    callable_identity_sha256 = sha256_bytes(
        canonical_json_bytes(
            {
                "schema_version": fused_start.D7_FUSED_START_CALLABLE_IDENTITY_SCHEME,
                "module": producer.__module__,
                "qualname": producer.__qualname__,
                "repository_path": producer_repository_path,
                "source_sha256": sha256_bytes(producer_source),
                "code_sha256": sha256_bytes(marshal.dumps(producer.__code__)),
            }
        )
    )
    launcher = (root / OFFICIAL_LAUNCHER_REPOSITORY_PATH).resolve()
    process_identity_sha256 = sha256_bytes(
        canonical_json_bytes(
            {
                "schema_version": fused_start.D7_FUSED_START_PROCESS_IDENTITY_SCHEME,
                "executable_realpath": str(executable),
                "executable_device": executable_stat.st_dev,
                "executable_inode": executable_stat.st_ino,
                "working_directory_realpath": str(root.resolve()),
                "argv": [str(launcher)],
                "real_uid": os.getuid(),
                "effective_uid": os.geteuid(),
                "real_gid": os.getgid(),
                "effective_gid": os.getegid(),
            }
        )
    )
    return authority.D7ExecutionIdentityInputRecord(
        execution_identity_id="d7-item24-execution-identity-v0-1",
        source_runtime_closure_binding=_binding(
            "execution-source-runtime-closure",
            frozen.source_runtime_closure,
        ),
        runtime_specification_binding=_binding(
            "runtime-specification",
            frozen.runtime_specification,
        ),
        executable_sha256=executable_sha256,
        callable_identity_sha256=callable_identity_sha256,
        process_identity_sha256=process_identity_sha256,
    )


def _path_exists(path: Path) -> bool:
    return os.path.lexists(path)


def _create_physical_store(
    replay_target: authority.D7ReplayTargetInputRecord,
) -> _StagedPhysicalStore:
    store = OFFICIAL_STORE_PATH
    stage_path = OFFICIAL_STORE_STAGING_PATH
    lane_basename = authority.D7_AUTHORITATIVE_START_LANE_BASENAME
    final_lane = store / lane_basename
    output = store / OFFICIAL_OUTPUT_BASENAME
    terminal = store / OFFICIAL_TERMINAL_BASENAME
    parent = persistence._open_real_directory(
        store.parent,
        label="D7 item-24 external-store parent",
    )
    stage: persistence._DirectoryAnchor | None = None
    lane: persistence._DirectoryAnchor | None = None
    try:
        for leaf, label in (
            (store.name, "fixed item-24 store"),
            (stage_path.name, "fixed item-24 staged store"),
        ):
            if persistence._relative_stat(parent, leaf) is not None:
                raise QualificationContractError(f"{label} already exists")
        os.mkdir(stage_path.name, 0o700, dir_fd=parent.descriptor)
        os.fsync(parent.descriptor)
        stage = persistence._open_child_directory(
            parent,
            leaf=stage_path.name,
            label="D7 item-24 staged store",
            create=False,
        )
        lane = persistence._open_child_directory(
            stage,
            leaf=lane_basename,
            label="D7 item-24 staged authoritative lane",
            create=True,
        )
        if set(os.listdir(stage.descriptor)) != {lane_basename} or os.listdir(
            lane.descriptor
        ):
            raise QualificationContractError(
                "fixed item-24 staged physical layout differs"
            )
        persistence._verify_anchor(
            lane,
            label="D7 item-24 staged authoritative lane",
        )
        persistence._verify_anchor(stage, label="D7 item-24 staged store")
        persistence._verify_anchor(
            parent,
            label="D7 item-24 external-store parent",
        )
        stage_device, stage_inode = stage.device, stage.inode
        lane_device, lane_inode = lane.device, lane.inode
    finally:
        if lane is not None:
            os.close(lane.descriptor)
        if stage is not None:
            os.close(stage.descriptor)
        os.close(parent.descriptor)
    attempt_key = attempt_records.d7_attempt_key_sha256(
        replay_target_sha256=replay_target.canonical_sha256,
        attempt_role=attempt_records.D7AttemptRole.PRIMARY_CONFIRMATION,
    )
    record = authority.D7PhysicalStoreLaneIdentityRecord(
        physical_identity_id="d7-item24-physical-store-lane-identity-v0-1",
        attempt_key_sha256=attempt_key,
        store_path=str(store),
        store_device=stage_device,
        store_inode=stage_inode,
        lane_path=str(final_lane),
        lane_device=lane_device,
        lane_inode=lane_inode,
        lane_parent_device=stage_device,
        lane_parent_inode=stage_inode,
        output_namespace_path=str(output),
        output_parent_device=stage_device,
        output_parent_inode=stage_inode,
        terminal_path=str(terminal),
        terminal_parent_device=stage_device,
        terminal_parent_inode=stage_inode,
    )
    return _StagedPhysicalStore(
        record=record,
        staging_device=stage_device,
        staging_inode=stage_inode,
        lane_device=lane_device,
        lane_inode=lane_inode,
    )


def _promote_physical_store(staged: _StagedPhysicalStore) -> _PromotedPhysicalStore:
    if type(staged) is not _StagedPhysicalStore:
        raise TypeError("staged must be the exact staged-store type")
    store = OFFICIAL_STORE_PATH
    lane_basename = authority.D7_AUTHORITATIVE_START_LANE_BASENAME
    parent = persistence._open_real_directory(
        store.parent,
        label="D7 item-24 external-store parent",
    )
    stage: persistence._DirectoryAnchor | None = None
    lane: persistence._DirectoryAnchor | None = None
    promoted: persistence._DirectoryAnchor | None = None
    promoted_lane: persistence._DirectoryAnchor | None = None
    witness: _PromotedPhysicalStore | None = None
    try:
        if persistence._relative_stat(parent, store.name) is not None:
            raise QualificationContractError("fixed item-24 store already exists")
        stage = persistence._open_child_directory(
            parent,
            leaf=OFFICIAL_STORE_STAGING_PATH.name,
            label="D7 item-24 staged store",
            create=False,
        )
        lane = persistence._open_child_directory(
            stage,
            leaf=lane_basename,
            label="D7 item-24 staged authoritative lane",
            create=False,
        )
        if (
            (stage.device, stage.inode) != (staged.staging_device, staged.staging_inode)
            or (lane.device, lane.inode) != (staged.lane_device, staged.lane_inode)
            or set(os.listdir(stage.descriptor)) != {lane_basename}
            or os.listdir(lane.descriptor)
        ):
            raise QualificationContractError(
                "D7 item-24 staged store identity or contents changed"
            )
        persistence._verify_anchor(stage, label="D7 item-24 staged store")
        persistence._verify_anchor(
            parent,
            label="D7 item-24 external-store parent",
        )
        persistence._rename_file_no_replace(
            parent,
            OFFICIAL_STORE_STAGING_PATH.name,
            store.name,
        )
        os.fsync(parent.descriptor)
        promoted = persistence._open_child_directory(
            parent,
            leaf=store.name,
            label="D7 item-24 promoted store",
            create=False,
        )
        promoted_lane = persistence._open_child_directory(
            promoted,
            leaf=lane_basename,
            label="D7 item-24 promoted authoritative lane",
            create=False,
        )
        if (
            (promoted.device, promoted.inode)
            != (staged.record.store_device, staged.record.store_inode)
            or (promoted_lane.device, promoted_lane.inode)
            != (staged.record.lane_device, staged.record.lane_inode)
            or set(os.listdir(promoted.descriptor)) != {lane_basename}
            or os.listdir(promoted_lane.descriptor)
            or _path_exists(Path(staged.record.output_namespace_path))
            or _path_exists(Path(staged.record.terminal_path))
        ):
            raise QualificationContractError(
                "D7 item-24 promoted physical layout differs"
            )
        persistence._verify_anchor(
            promoted_lane,
            label="D7 item-24 promoted authoritative lane",
        )
        persistence._verify_anchor(promoted, label="D7 item-24 promoted store")
        persistence._verify_anchor(
            parent,
            label="D7 item-24 external-store parent",
        )
        witness = _PromotedPhysicalStore(
            record=staged.record,
            parent=parent,
            store=promoted,
            lane=promoted_lane,
            _factory_token=_PROMOTED_STORE_FACTORY_TOKEN,
        )
        parent = None  # type: ignore[assignment]
        promoted = None
        promoted_lane = None
        return witness
    finally:
        if promoted_lane is not None:
            os.close(promoted_lane.descriptor)
        if promoted is not None:
            os.close(promoted.descriptor)
        if lane is not None:
            os.close(lane.descriptor)
        if stage is not None:
            os.close(stage.descriptor)
        if parent is not None:
            os.close(parent.descriptor)


def _close_promoted_physical_store(witness: _PromotedPhysicalStore) -> None:
    if type(witness) is not _PromotedPhysicalStore:
        raise TypeError("witness must be the exact promoted-store type")
    if witness._consumed:
        return
    first_error: OSError | None = None
    try:
        for descriptor in (
            witness.lane.descriptor,
            witness.store.descriptor,
            witness.parent.descriptor,
        ):
            try:
                os.close(descriptor)
            except OSError as error:
                if first_error is None:
                    first_error = error
    finally:
        witness._consumed = True
    if first_error is not None:
        raise QualificationContractError(
            "cannot close every D7 item-24 promoted-store anchor"
        ) from first_error


def _verify_promoted_physical_store(
    material: _LaunchMaterial,
    witness: _PromotedPhysicalStore,
) -> None:
    if type(witness) is not _PromotedPhysicalStore or witness._consumed:
        raise QualificationContractError(
            "D7 item-24 promoted-store witness is absent or consumed"
        )
    physical = material.bundle.physical_store_lane_identity
    if witness.record != physical:
        raise QualificationContractError(
            "D7 item-24 promoted-store witness differs from launch material"
        )
    lane_basename = authority.D7_AUTHORITATIVE_START_LANE_BASENAME
    output = Path(physical.output_namespace_path)
    terminal = Path(physical.terminal_path)
    if (
        str(witness.store.path) != physical.store_path
        or (witness.store.device, witness.store.inode)
        != (physical.store_device, physical.store_inode)
        or str(witness.lane.path) != physical.lane_path
        or (witness.lane.device, witness.lane.inode)
        != (physical.lane_device, physical.lane_inode)
        or (witness.store.device, witness.store.inode)
        != (physical.lane_parent_device, physical.lane_parent_inode)
        or (witness.store.device, witness.store.inode)
        != (physical.output_parent_device, physical.output_parent_inode)
        or (witness.store.device, witness.store.inode)
        != (physical.terminal_parent_device, physical.terminal_parent_inode)
        or output.parent != witness.store.path
        or terminal.parent != witness.store.path
        or set(os.listdir(witness.store.descriptor)) != {lane_basename}
        or os.listdir(witness.lane.descriptor)
        or persistence._relative_stat(witness.store, output.name) is not None
        or persistence._relative_stat(witness.store, terminal.name) is not None
    ):
        raise QualificationContractError(
            "D7 item-24 promoted physical layout differs from launch material"
        )
    displayed_store = persistence._relative_stat(
        witness.parent,
        witness.store.path.name,
    )
    if (
        displayed_store is None
        or (displayed_store.st_dev, displayed_store.st_ino)
        != (witness.store.device, witness.store.inode)
        or persistence._relative_stat(
            witness.parent,
            OFFICIAL_STORE_STAGING_PATH.name,
        )
        is not None
    ):
        raise QualificationContractError(
            "D7 item-24 promoted store display identity differs"
        )
    persistence._verify_anchor(
        witness.lane,
        label="D7 item-24 promoted authoritative lane",
    )
    persistence._verify_anchor(witness.store, label="D7 item-24 promoted store")
    persistence._verify_anchor(
        witness.parent,
        label="D7 item-24 external-store parent",
    )


def _build_launch_material(
    frozen: _FrozenItem22Inputs,
    execution_identity: authority.D7ExecutionIdentityInputRecord,
    physical_identity: authority.D7PhysicalStoreLaneIdentityRecord,
) -> _LaunchMaterial:
    freeze_step = authority.D7ChronologyInputRecord(
        transition=authority.D7SeedSupplyTransition.COMMITTED_FULL_DESIGN_FREEZE,
        ordinal=7,
        record_id="d7-item24-committed-full-design-freeze-v0-1",
        predecessor_binding=frozen.chronology[-1].artifact_binding,
        subject_bindings=(_binding("full-design-freeze", frozen.full_design_freeze),),
    )
    launch_intent = authority.D7LaunchIntentInputRecord(
        launch_intent_id="d7-item24-launch-intent-v0-1",
        replay_target_binding=_binding("replay-target", frozen.replay_target),
        full_design_freeze_binding=_binding(
            "full-design-freeze",
            frozen.full_design_freeze,
        ),
        execution_identity_binding=_binding(
            "execution-identity",
            execution_identity,
        ),
        physical_identity_binding=_binding(
            "physical-store-lane-identity",
            physical_identity,
        ),
        freeze_commit=frozen.full_design_freeze.freeze_commit,
        authorization_commit=frozen.full_design_freeze.authorization_commit,
    )
    intent_step = authority.D7ChronologyInputRecord(
        transition=authority.D7SeedSupplyTransition.LAUNCH_INTENT,
        ordinal=8,
        record_id="d7-item24-launch-intent-v0-1",
        predecessor_binding=freeze_step.artifact_binding,
        subject_bindings=(_binding("launch-intent", launch_intent),),
    )
    bundle = authority.D7LaunchAuthorityInputBundle(
        bundle_id="d7-item24-launch-authority-input-bundle-v0-1",
        development_seed_exclusion_registry=frozen.development_registry,
        parent_selection_seed_exclusion_registry=frozen.parent_registry,
        official_seed_inventory=frozen.official_seed_inventory,
        runtime_specification=frozen.runtime_specification,
        source_runtime_closure=frozen.source_runtime_closure,
        family_admission=frozen.family_admission,
        exclusive_seed_supply_claim=frozen.exclusive_seed_supply_claim,
        single_supplier_invocation=frozen.single_supplier_invocation,
        execution_identity=execution_identity,
        physical_store_lane_identity=physical_identity,
        replay_target=frozen.replay_target,
        full_design_freeze=frozen.full_design_freeze,
        launch_intent=launch_intent,
        chronology=(*frozen.chronology, freeze_step, intent_step),
    )
    # Exercise the digest-before-parse structural loader before persistence.
    authority.load_d7_launch_authority_structural_candidate(
        bundle.canonical_bytes,
        expected_sha256=bundle.canonical_sha256,
    )

    new_records: dict[str, object] = {
        "launch-authority-input-bundle": bundle,
        "launch-intent": launch_intent,
        "execution-source-runtime-closure": frozen.source_runtime_closure,
        "runtime-specification": frozen.runtime_specification,
        "family-admission": frozen.family_admission,
        "execution-identity": execution_identity,
        "physical-store-lane-identity": physical_identity,
    }
    role_sources = {
        role: record.canonical_bytes  # type: ignore[attr-defined]
        for role, record in new_records.items()
    }
    role_sources["replay-target"] = frozen.replay_target_source
    role_sources["full-design-freeze"] = frozen.full_design_freeze_source
    role_paths = {
        role: f"{LAUNCH_MEMBER_DIRECTORY_REPOSITORY_PATH}/{filename}"
        for role, filename in _NEW_MEMBER_FILENAMES.items()
    }
    role_paths["replay-target"] = (
        f"{item22.D7_ITEM22_ATOMIC_TARGET_DIRECTORY_REPOSITORY_PATH}/replay-target.json"
    )
    role_paths["full-design-freeze"] = (
        item22.D7_ITEM22_FULL_DESIGN_FREEZE_REPOSITORY_PATH
    )
    inventory = tuple(
        fused_authority._D7FusedAuthorityMember(
            artifact_role=role,
            artifact_contract_id=contract_id,
            repository_path=role_paths[role],
            canonical_sha256=sha256_bytes(role_sources[role]),
            byte_count=len(role_sources[role]),
        )
        for role, contract_id, _attribute, _record_type in (
            fused_authority._MEMBER_SPECS
        )
    )
    descriptor = fused_authority._D7FusedAuthorityLaunchDescriptor(
        descriptor_id="d7-item24-fused-authority-launch-descriptor-v0-1",
        descriptor_repository_path=LAUNCH_DESCRIPTOR_REPOSITORY_PATH,
        inventory=inventory,
    )
    fused_authority._D7FusedAuthorityLaunchDescriptor.from_dict(
        parse_canonical_json(
            descriptor.canonical_bytes,
            label="D7 item-24 launch descriptor",
        )
    )
    new_sources = tuple(
        (_NEW_MEMBER_FILENAMES[role], role_sources[role])
        for role in _NEW_MEMBER_FILENAMES
    )
    member_sources = tuple(
        (
            member.artifact_role,
            member.repository_path,
            role_sources[member.artifact_role],
        )
        for member in descriptor.inventory
    )
    return _LaunchMaterial(
        bundle=bundle,
        descriptor=descriptor,
        member_sources=member_sources,
        new_member_sources=new_sources,
    )


def _require_absent_launch_outputs(root: Path) -> None:
    paths = (
        root / LAUNCH_MEMBER_DIRECTORY_REPOSITORY_PATH,
        root / LAUNCH_DESCRIPTOR_REPOSITORY_PATH,
        root
        / Path(LAUNCH_MEMBER_DIRECTORY_REPOSITORY_PATH).parent
        / _STAGING_DIRECTORY_BASENAME,
    )
    if any(_path_exists(path) for path in paths):
        raise QualificationContractError(
            "launch output or an unresolved staging directory already exists"
        )
    if _descriptor_temporary_present(root):
        raise QualificationContractError(
            "an unresolved launch-descriptor temporary file already exists"
        )
    if _path_exists(OFFICIAL_STORE_PATH) or _path_exists(OFFICIAL_STORE_STAGING_PATH):
        raise QualificationContractError(
            "fixed item-24 store or staged store already exists"
        )


def _descriptor_temporary_present(root: Path) -> bool:
    descriptor = Path(LAUNCH_DESCRIPTOR_REPOSITORY_PATH)
    experiment_path = root / descriptor.parent
    if not experiment_path.is_dir():
        return False
    experiment = persistence._open_real_directory(
        experiment_path,
        label="D7 item-24 experiment directory",
    )
    try:
        prefix = f".{descriptor.name}."
        return any(
            name.startswith(prefix) and name.endswith(".tmp")
            for name in os.listdir(experiment.descriptor)
        )
    finally:
        os.close(experiment.descriptor)


def classify_d7_item24_preparation_state(root: Path) -> str:
    """Classify presence only; never infer authority or recover a partial state."""

    experiment = root / Path(LAUNCH_DESCRIPTOR_REPOSITORY_PATH).parent
    present = (
        _descriptor_temporary_present(root),
        _path_exists(experiment / _STAGING_DIRECTORY_BASENAME),
        _path_exists(root / LAUNCH_MEMBER_DIRECTORY_REPOSITORY_PATH),
        _path_exists(OFFICIAL_STORE_STAGING_PATH),
        _path_exists(OFFICIAL_STORE_PATH),
        _path_exists(root / LAUNCH_DESCRIPTOR_REPOSITORY_PATH),
    )
    states = {
        (False, False, False, False, False, False): "pristine",
        (False, False, False, True, False, False): "external-store-staged",
        (False, True, False, True, False, False): "members-and-store-staged",
        (False, False, True, True, False, False): ("members-published-store-staged"),
        (False, False, True, False, True, False): ("members-and-store-published"),
        (False, False, True, False, True, True): "descriptor-present",
    }
    return states.get(present, "invalid-partial-state")


def _publish_launch_members(root: Path, material: _LaunchMaterial) -> None:
    experiment_path = root / Path(LAUNCH_DESCRIPTOR_REPOSITORY_PATH).parent
    experiment = persistence._open_real_directory(
        experiment_path,
        label="D7 item-24 experiment directory",
    )
    stage: persistence._DirectoryAnchor | None = None
    try:
        for leaf, label in (
            (_STAGING_DIRECTORY_BASENAME, "member staging directory"),
            (
                Path(LAUNCH_MEMBER_DIRECTORY_REPOSITORY_PATH).name,
                "member directory",
            ),
            (Path(LAUNCH_DESCRIPTOR_REPOSITORY_PATH).name, "launch descriptor"),
        ):
            if persistence._relative_stat(experiment, leaf) is not None:
                raise QualificationContractError(f"D7 item-24 {label} already exists")
        os.mkdir(_STAGING_DIRECTORY_BASENAME, 0o700, dir_fd=experiment.descriptor)
        os.fsync(experiment.descriptor)
        stage = persistence._open_child_directory(
            experiment,
            leaf=_STAGING_DIRECTORY_BASENAME,
            label="D7 item-24 member staging directory",
            create=False,
        )
        for filename, source in material.new_member_sources:
            persistence._write_canonical_file_no_replace(
                stage,
                filename,
                source,
                expected_sha256=sha256_bytes(source),
                maximum_bytes=fused_authority.MAX_D7_FUSED_AUTHORITY_MEMBER_BYTES,
                label=f"D7 item-24 {filename}",
                allow_identical_existing=False,
            )
        if set(os.listdir(stage.descriptor)) != {
            filename for filename, _source in material.new_member_sources
        }:
            raise QualificationContractError(
                "D7 item-24 staged member inventory differs"
            )
        os.fsync(stage.descriptor)
        persistence._verify_anchor(
            experiment,
            label="D7 item-24 experiment directory",
        )
        persistence._rename_file_no_replace(
            experiment,
            _STAGING_DIRECTORY_BASENAME,
            Path(LAUNCH_MEMBER_DIRECTORY_REPOSITORY_PATH).name,
        )
        os.fsync(experiment.descriptor)
        persistence._verify_anchor(
            experiment,
            label="D7 item-24 experiment directory",
        )
    finally:
        if stage is not None:
            os.close(stage.descriptor)
        os.close(experiment.descriptor)


def _verify_launch_members(root: Path, material: _LaunchMaterial) -> None:
    if len(material.member_sources) != len(material.descriptor.inventory):
        raise QualificationContractError("D7 item-24 member inventory length differs")
    expected_new_names = {filename for filename, _source in material.new_member_sources}
    member_directory = persistence._open_real_directory(
        root / LAUNCH_MEMBER_DIRECTORY_REPOSITORY_PATH,
        label="D7 item-24 launch-member directory",
    )
    try:
        if set(os.listdir(member_directory.descriptor)) != expected_new_names:
            raise QualificationContractError(
                "D7 item-24 published member-directory inventory differs"
            )
        persistence._verify_anchor(
            member_directory,
            label="D7 item-24 launch-member directory",
        )
    finally:
        os.close(member_directory.descriptor)

    for member, expected in zip(
        material.descriptor.inventory,
        material.member_sources,
        strict=True,
    ):
        role, repository_path, expected_source = expected
        if (
            role != member.artifact_role
            or repository_path != member.repository_path
            or len(expected_source) != member.byte_count
            or sha256_bytes(expected_source) != member.canonical_sha256
        ):
            raise QualificationContractError(
                f"D7 item-24 material projection differs: {member.artifact_role}"
            )
        path = root / repository_path
        parent = persistence._open_real_directory(
            path.parent,
            label=f"D7 item-24 {role} parent",
        )
        try:
            source, observed = persistence._read_exact_file(
                parent,
                path.name,
                expected_sha256=member.canonical_sha256,
                maximum_bytes=fused_authority.MAX_D7_FUSED_AUTHORITY_MEMBER_BYTES,
                label=f"D7 item-24 {role}",
            )
            if source != expected_source or observed.st_size != member.byte_count:
                raise QualificationContractError(
                    f"D7 item-24 published member bytes differ: {role}"
                )
            persistence._verify_anchor(
                parent,
                label=f"D7 item-24 {role} parent",
            )
        finally:
            os.close(parent.descriptor)


def _publish_launch_descriptor(
    root: Path,
    material: _LaunchMaterial,
    promoted_store: _PromotedPhysicalStore,
) -> None:
    experiment_path = root / Path(LAUNCH_DESCRIPTOR_REPOSITORY_PATH).parent
    experiment = persistence._open_real_directory(
        experiment_path,
        label="D7 item-24 experiment directory",
    )
    try:
        if classify_d7_item24_preparation_state(root) != (
            "members-and-store-published"
        ):
            raise QualificationContractError(
                "D7 item-24 descriptor requires published members and store"
            )
        _verify_launch_members(root, material)
        _verify_promoted_physical_store(material, promoted_store)
        persistence._write_canonical_file_no_replace(
            experiment,
            Path(LAUNCH_DESCRIPTOR_REPOSITORY_PATH).name,
            material.descriptor.canonical_bytes,
            expected_sha256=material.descriptor.canonical_sha256,
            maximum_bytes=fused_authority.MAX_D7_FUSED_AUTHORITY_DESCRIPTOR_BYTES,
            label="D7 item-24 launch descriptor",
            allow_identical_existing=False,
        )
        os.fsync(experiment.descriptor)
        persistence._verify_anchor(
            experiment,
            label="D7 item-24 experiment directory",
        )
        _verify_launch_members(root, material)
        _verify_promoted_physical_store(material, promoted_store)
        if classify_d7_item24_preparation_state(root) != "descriptor-present":
            raise QualificationContractError(
                "D7 item-24 descriptor publication state differs"
            )
    finally:
        try:
            _close_promoted_physical_store(promoted_store)
        finally:
            os.close(experiment.descriptor)


def _parser() -> argparse.ArgumentParser:
    return argparse.ArgumentParser(
        description=(
            "Create the fixed local D7 item-24 store and publish its "
            "all-false closed launch descriptor without starting execution."
        )
    )


def main(argv: list[str] | None = None) -> int:
    _parser().parse_args(argv)
    root = REPOSITORY_ROOT
    if Path(os.path.realpath(os.getcwd())) != root:
        raise QualificationContractError(
            "item-24 preparation requires the exact repository cwd"
        )
    item22.item21._require_clean(root)
    _require_absent_launch_outputs(root)
    frozen = _load_frozen_item22_inputs(root)
    execution_identity = _execution_identity(root, frozen)
    staged_store = _create_physical_store(frozen.replay_target)
    material = _build_launch_material(
        frozen,
        execution_identity,
        staged_store.record,
    )
    _publish_launch_members(root, material)
    promoted_store = _promote_physical_store(staged_store)
    try:
        _publish_launch_descriptor(root, material, promoted_store)
    finally:
        _close_promoted_physical_store(promoted_store)
    print(
        json.dumps(
            {
                "authority_authenticated": False,
                "bundle_sha256": material.bundle.canonical_sha256,
                "descriptor_path": str(root / LAUNCH_DESCRIPTOR_REPOSITORY_PATH),
                "descriptor_sha256": material.descriptor.canonical_sha256,
                "execution_authorized": False,
                "execution_started": False,
                "launch_authorized": False,
                "member_count": len(material.descriptor.inventory),
                "scientific_claim_eligible": False,
                "store_path": str(OFFICIAL_STORE_PATH),
                "strict_git_rejoin_requires_artifact_commit": True,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
