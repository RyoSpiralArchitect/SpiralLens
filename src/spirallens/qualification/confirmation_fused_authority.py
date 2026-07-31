"""Git-rooted, non-authorizing reopener for future D7 fused execution.

This module closes one narrow provenance gap without issuing authority.  A
canonical descriptor committed at the repository's current ``HEAD`` names a
closed inventory of launch-prerequisite records.  The loader derives the Git
root and ``HEAD`` from the raw descriptor path, reopens every member as a real
regular file, proves exact equality with its current-``HEAD`` blob, and rejoins
the independently persisted records to the structural launch bundle.

The descriptor is a locator and integrity inventory, not an authorization
token.  An arbitrary Git repository remains arbitrary, and the returned
private snapshot deliberately leaves repository trust, launch authority,
execution, and scientific eligibility false.  The sibling same-call fused
operation adds its scoped live checks and start transition without promoting
this loader's return value into a reusable capability.
"""

from __future__ import annotations

import os
import re
import stat
import subprocess
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import ClassVar, NoReturn

from spirallens.core.canonical import (
    CanonicalJsonError,
    canonical_json_bytes,
    parse_canonical_json,
    sha256_bytes,
)

from . import confirmation_attempt_authority as authority
from .common import QualificationContractError

__all__: tuple[str, ...] = ()

D7_FUSED_AUTHORITY_DESCRIPTOR_SCHEMA_VERSION = (
    "spirallens.d7-fused-authority-launch-descriptor.v0.1"
)
MAX_D7_FUSED_AUTHORITY_DESCRIPTOR_BYTES = 256 * 1024
MAX_D7_FUSED_AUTHORITY_MEMBER_BYTES = 2 * 1024 * 1024
MAX_D7_FUSED_AUTHORITY_REPOSITORY_PATH_BYTES = 4096

_DESCRIPTOR_CLAIM_CEILING = "level_0"
_DESCRIPTOR_TRUST_SCOPE = "current-git-head-blob-equality-only"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,191}$")
_PATH_SEGMENT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,191}$")
_SNAPSHOT_FACTORY_TOKEN = object()

_MEMBER_SPECS = (
    (
        "launch-authority-input-bundle",
        authority.D7_LAUNCH_AUTHORITY_INPUT_BUNDLE_SCHEMA_VERSION,
        None,
        authority.D7LaunchAuthorityInputBundle,
    ),
    (
        "replay-target",
        authority.D7_REPLAY_TARGET_INPUT_SCHEMA_VERSION,
        "replay_target",
        authority.D7ReplayTargetInputRecord,
    ),
    (
        "launch-intent",
        authority.D7_LAUNCH_INTENT_INPUT_SCHEMA_VERSION,
        "launch_intent",
        authority.D7LaunchIntentInputRecord,
    ),
    (
        "execution-source-runtime-closure",
        authority.D7_SOURCE_RUNTIME_CLOSURE_INPUT_SCHEMA_VERSION,
        "source_runtime_closure",
        authority.D7SourceRuntimeClosureInputRecord,
    ),
    (
        "runtime-specification",
        authority.D7_RUNTIME_SPECIFICATION_INPUT_SCHEMA_VERSION,
        "runtime_specification",
        authority.D7RuntimeSpecificationInputRecord,
    ),
    (
        "family-admission",
        authority.D7_FAMILY_ADMISSION_INPUT_SCHEMA_VERSION,
        "family_admission",
        authority.D7FamilyAdmissionInputRecord,
    ),
    (
        "execution-identity",
        authority.D7_EXECUTION_IDENTITY_INPUT_SCHEMA_VERSION,
        "execution_identity",
        authority.D7ExecutionIdentityInputRecord,
    ),
    (
        "physical-store-lane-identity",
        authority.D7_PHYSICAL_STORE_LANE_IDENTITY_SCHEMA_VERSION,
        "physical_store_lane_identity",
        authority.D7PhysicalStoreLaneIdentityRecord,
    ),
    (
        "full-design-freeze",
        authority.D7_FULL_DESIGN_FREEZE_INPUT_SCHEMA_VERSION,
        "full_design_freeze",
        authority.D7FullDesignFreezeInputRecord,
    ),
)
_MEMBER_ROLES = tuple(item[0] for item in _MEMBER_SPECS)
_MEMBER_SPEC_BY_ROLE = {item[0]: item for item in _MEMBER_SPECS}


def _mapping(value: object, *, label: str) -> dict[str, object]:
    if not isinstance(value, dict) or any(type(key) is not str for key in value):
        raise QualificationContractError(f"{label} must be a JSON object")
    return dict(value)


def _sequence(value: object, *, label: str) -> list[object]:
    if not isinstance(value, list):
        raise QualificationContractError(f"{label} must be a JSON array")
    return list(value)


def _exact_keys(
    value: dict[str, object],
    expected: set[str],
    *,
    label: str,
) -> None:
    if set(value) != expected:
        raise QualificationContractError(
            f"{label} keys differ: expected {sorted(expected)}, "
            f"observed {sorted(value)}"
        )


def _string(value: object, *, label: str) -> str:
    if type(value) is not str or not value:
        raise QualificationContractError(f"{label} must be a non-empty string")
    return value


def _slug(value: object, *, label: str) -> str:
    result = _string(value, label=label)
    if _SLUG_RE.fullmatch(result) is None:
        raise QualificationContractError(f"{label} must be a portable slug")
    return result


def _sha256(value: object, *, label: str) -> str:
    if type(value) is not str or _SHA256_RE.fullmatch(value) is None:
        raise QualificationContractError(f"{label} must be a lowercase SHA-256")
    return value


def _plain_positive_int(value: object, *, label: str) -> int:
    if type(value) is not int or value <= 0:
        raise QualificationContractError(f"{label} must be a positive integer")
    return value


def _false(value: object, *, label: str) -> None:
    if value is not False:
        raise QualificationContractError(f"{label} must remain false")


def _repository_path(value: object, *, label: str) -> str:
    result = _string(value, label=label)
    try:
        encoded = result.encode("utf-8")
    except UnicodeEncodeError as error:
        raise QualificationContractError(f"{label} must be UTF-8") from error
    if len(encoded) > MAX_D7_FUSED_AUTHORITY_REPOSITORY_PATH_BYTES:
        raise QualificationContractError(f"{label} is overlong")
    path = PurePosixPath(result)
    if (
        path.is_absolute()
        or result != path.as_posix()
        or not path.parts
        or any(part in {"", ".", ".."} for part in path.parts)
        or any(_PATH_SEGMENT_RE.fullmatch(part) is None for part in path.parts)
        or path.parts[0] == ".git"
    ):
        raise QualificationContractError(
            f"{label} must be a normalized in-repository portable path"
        )
    return result


@dataclass(frozen=True, slots=True)
class _D7FusedAuthorityMember:
    artifact_role: str
    artifact_contract_id: str
    repository_path: str
    canonical_sha256: str
    byte_count: int

    def __post_init__(self) -> None:
        role = _slug(self.artifact_role, label="artifact_role")
        if role not in _MEMBER_SPEC_BY_ROLE:
            raise QualificationContractError(
                "fused-authority inventory contains an unknown member role"
            )
        expected_contract = _MEMBER_SPEC_BY_ROLE[role][1]
        if self.artifact_contract_id != expected_contract:
            raise QualificationContractError(
                f"{role} contract differs from the closed inventory"
            )
        _repository_path(self.repository_path, label=f"{role} repository_path")
        _sha256(self.canonical_sha256, label=f"{role} canonical_sha256")
        count = _plain_positive_int(self.byte_count, label=f"{role} byte_count")
        if count > MAX_D7_FUSED_AUTHORITY_MEMBER_BYTES:
            raise QualificationContractError(f"{role} byte_count exceeds its cap")

    @classmethod
    def from_dict(cls, value: object) -> _D7FusedAuthorityMember:
        item = _mapping(value, label="fused-authority inventory member")
        _exact_keys(
            item,
            {
                "artifact_role",
                "artifact_contract_id",
                "repository_path",
                "canonical_sha256",
                "byte_count",
            },
            label="fused-authority inventory member",
        )
        return cls(
            artifact_role=_slug(item["artifact_role"], label="artifact_role"),
            artifact_contract_id=_string(
                item["artifact_contract_id"],
                label="artifact_contract_id",
            ),
            repository_path=_repository_path(
                item["repository_path"],
                label="repository_path",
            ),
            canonical_sha256=_sha256(
                item["canonical_sha256"],
                label="canonical_sha256",
            ),
            byte_count=_plain_positive_int(
                item["byte_count"],
                label="byte_count",
            ),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "artifact_role": self.artifact_role,
            "artifact_contract_id": self.artifact_contract_id,
            "repository_path": self.repository_path,
            "canonical_sha256": self.canonical_sha256,
            "byte_count": self.byte_count,
        }


@dataclass(frozen=True, slots=True)
class _D7FusedAuthorityLaunchDescriptor:
    descriptor_id: str
    descriptor_repository_path: str
    inventory: tuple[_D7FusedAuthorityMember, ...]

    schema_version: ClassVar[str] = D7_FUSED_AUTHORITY_DESCRIPTOR_SCHEMA_VERSION

    def __post_init__(self) -> None:
        _slug(self.descriptor_id, label="descriptor_id")
        descriptor_path = _repository_path(
            self.descriptor_repository_path,
            label="descriptor_repository_path",
        )
        if type(self.inventory) is not tuple or tuple(
            type(item) for item in self.inventory
        ) != (_D7FusedAuthorityMember,) * len(_MEMBER_SPECS):
            raise QualificationContractError(
                "fused-authority inventory must contain every exact member"
            )
        roles = tuple(item.artifact_role for item in self.inventory)
        if roles != _MEMBER_ROLES:
            raise QualificationContractError(
                "fused-authority inventory roles or order differ"
            )
        paths = tuple(item.repository_path for item in self.inventory)
        if len(set(paths)) != len(paths) or descriptor_path in paths:
            raise QualificationContractError(
                "fused-authority descriptor and member paths must be distinct"
            )

    @classmethod
    def from_dict(cls, value: object) -> _D7FusedAuthorityLaunchDescriptor:
        item = _mapping(value, label="D7 fused-authority launch descriptor")
        _exact_keys(
            item,
            {
                "schema_version",
                "descriptor_id",
                "descriptor_repository_path",
                "claim_ceiling",
                "trust_scope",
                "closed_member_count",
                "unknown_members_allowed",
                "inventory",
                "authority_authenticated",
                "repository_trust_root_authenticated",
                "launch_authorized",
                "execution_authorized",
                "scientific_claim_eligible",
                "reusable_authorization_capability_present",
            },
            label="D7 fused-authority launch descriptor",
        )
        if item["schema_version"] != cls.schema_version:
            raise QualificationContractError(
                "fused-authority descriptor schema differs"
            )
        if item["claim_ceiling"] != _DESCRIPTOR_CLAIM_CEILING:
            raise QualificationContractError(
                "fused-authority descriptor claim ceiling differs"
            )
        if item["trust_scope"] != _DESCRIPTOR_TRUST_SCOPE:
            raise QualificationContractError(
                "fused-authority descriptor trust scope differs"
            )
        if item["closed_member_count"] != len(_MEMBER_SPECS):
            raise QualificationContractError(
                "fused-authority descriptor member count differs"
            )
        _false(item["unknown_members_allowed"], label="unknown_members_allowed")
        for name in (
            "authority_authenticated",
            "repository_trust_root_authenticated",
            "launch_authorized",
            "execution_authorized",
            "scientific_claim_eligible",
            "reusable_authorization_capability_present",
        ):
            _false(item[name], label=name)
        return cls(
            descriptor_id=_slug(item["descriptor_id"], label="descriptor_id"),
            descriptor_repository_path=_repository_path(
                item["descriptor_repository_path"],
                label="descriptor_repository_path",
            ),
            inventory=tuple(
                _D7FusedAuthorityMember.from_dict(member)
                for member in _sequence(item["inventory"], label="inventory")
            ),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "descriptor_id": self.descriptor_id,
            "descriptor_repository_path": self.descriptor_repository_path,
            "claim_ceiling": _DESCRIPTOR_CLAIM_CEILING,
            "trust_scope": _DESCRIPTOR_TRUST_SCOPE,
            "closed_member_count": len(_MEMBER_SPECS),
            "unknown_members_allowed": False,
            "inventory": [member.to_dict() for member in self.inventory],
            "authority_authenticated": False,
            "repository_trust_root_authenticated": False,
            "launch_authorized": False,
            "execution_authorized": False,
            "scientific_claim_eligible": False,
            "reusable_authorization_capability_present": False,
        }

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_dict())

    @property
    def canonical_sha256(self) -> str:
        return sha256_bytes(self.canonical_bytes)


@dataclass(frozen=True, slots=True)
class _StableFileIdentity:
    repository_path: str
    path: Path
    head_mode: str
    head_object_id: str
    device: int
    inode: int
    mode: int
    byte_count: int
    mtime_ns: int
    canonical_sha256: str


@dataclass(frozen=True, slots=True)
class _GitHeadBlob:
    mode: str
    object_id: str
    source: bytes


class _LoadedD7FusedAuthoritySnapshot:
    """Private same-call structural snapshot; never an authority capability."""

    __slots__ = (
        "_bundle",
        "_descriptor",
        "_descriptor_path",
        "_execution_identity",
        "_family_admission",
        "_full_design_freeze",
        "_head_commit",
        "_launch_intent",
        "_member_paths",
        "_physical_identity",
        "_replay_target",
        "_repository_root",
        "_runtime_specification",
        "_sealed",
        "_source_runtime_closure",
    )

    same_call_only: ClassVar[bool] = True
    git_current_head_blob_equality_verified: ClassVar[bool] = True
    closed_inventory_verified: ClassVar[bool] = True
    structural_bundle_rejoined: ClassVar[bool] = True
    authority_granted: ClassVar[bool] = False
    authority_authenticated: ClassVar[bool] = False
    repository_trust_root_authenticated: ClassVar[bool] = False
    target_authoritative: ClassVar[bool] = False
    source_runtime_verified: ClassVar[bool] = False
    family_admission_verified: ClassVar[bool] = False
    seed_free_readiness_verified: ClassVar[bool] = False
    official_seed_chronology_verified: ClassVar[bool] = False
    seed_supply_claim_verified: ClassVar[bool] = False
    supplier_invocation_verified: ClassVar[bool] = False
    inventory_output_verified: ClassVar[bool] = False
    atomic_publication_verified: ClassVar[bool] = False
    execution_identity_verified: ClassVar[bool] = False
    physical_identity_reobserved: ClassVar[bool] = False
    path_absence_observed: ClassVar[bool] = False
    alternate_store_exclusivity_proved: ClassVar[bool] = False
    hostile_mutation_resistant: ClassVar[bool] = False
    full_design_freeze_verified: ClassVar[bool] = False
    launch_intent_verified: ClassVar[bool] = False
    launch_authorized: ClassVar[bool] = False
    launch_authorization_derived: ClassVar[bool] = False
    exclusive_start_authorized: ClassVar[bool] = False
    authoritative_lifecycle_eligible: ClassVar[bool] = False
    in_place_promotion_allowed: ClassVar[bool] = False
    terminal_publication_authorized: ClassVar[bool] = False
    finalization_authorized: ClassVar[bool] = False
    unresolved_finalization_authorized: ClassVar[bool] = False
    isolated_replay_authorized: ClassVar[bool] = False
    execution_authorized: ClassVar[bool] = False
    execution_observed: ClassVar[bool] = False
    d7_result_produced: ClassVar[bool] = False
    scientific_claim_eligible: ClassVar[bool] = False
    reusable_authorization_capability_present: ClassVar[bool] = False
    d7_execution_authorized: ClassVar[bool] = False
    d8_execution_authorized: ClassVar[bool] = False

    def __init__(
        self,
        *,
        descriptor_path: Path,
        repository_root: Path,
        head_commit: str,
        descriptor: _D7FusedAuthorityLaunchDescriptor,
        bundle: authority.D7LaunchAuthorityInputBundle,
        replay_target: authority.D7ReplayTargetInputRecord,
        launch_intent: authority.D7LaunchIntentInputRecord,
        source_runtime_closure: authority.D7SourceRuntimeClosureInputRecord,
        runtime_specification: authority.D7RuntimeSpecificationInputRecord,
        family_admission: authority.D7FamilyAdmissionInputRecord,
        execution_identity: authority.D7ExecutionIdentityInputRecord,
        physical_identity: authority.D7PhysicalStoreLaneIdentityRecord,
        full_design_freeze: authority.D7FullDesignFreezeInputRecord,
        member_paths: tuple[Path, ...],
        _factory_token: object,
    ) -> None:
        if _factory_token is not _SNAPSHOT_FACTORY_TOKEN:
            raise TypeError(
                "D7 fused-authority snapshot requires its Git-rooted loader"
            )
        values = (
            (bundle, authority.D7LaunchAuthorityInputBundle),
            (replay_target, authority.D7ReplayTargetInputRecord),
            (launch_intent, authority.D7LaunchIntentInputRecord),
            (source_runtime_closure, authority.D7SourceRuntimeClosureInputRecord),
            (runtime_specification, authority.D7RuntimeSpecificationInputRecord),
            (family_admission, authority.D7FamilyAdmissionInputRecord),
            (execution_identity, authority.D7ExecutionIdentityInputRecord),
            (physical_identity, authority.D7PhysicalStoreLaneIdentityRecord),
            (full_design_freeze, authority.D7FullDesignFreezeInputRecord),
        )
        if any(type(value) is not expected for value, expected in values):
            raise TypeError("D7 fused-authority snapshot values have wrong types")
        if (
            not isinstance(descriptor_path, Path)
            or not isinstance(repository_root, Path)
            or not descriptor_path.is_absolute()
            or not repository_root.is_absolute()
            or type(descriptor) is not _D7FusedAuthorityLaunchDescriptor
            or type(member_paths) is not tuple
            or any(
                not isinstance(path, Path) or not path.is_absolute()
                for path in member_paths
            )
        ):
            raise TypeError("D7 fused-authority snapshot paths are invalid")
        if _COMMIT_RE.fullmatch(head_commit) is None:
            raise TypeError("head_commit must be a lowercase Git commit")
        object.__setattr__(self, "_descriptor_path", descriptor_path)
        object.__setattr__(self, "_repository_root", repository_root)
        object.__setattr__(self, "_head_commit", head_commit)
        object.__setattr__(self, "_descriptor", descriptor)
        object.__setattr__(self, "_bundle", bundle)
        object.__setattr__(self, "_replay_target", replay_target)
        object.__setattr__(self, "_launch_intent", launch_intent)
        object.__setattr__(self, "_source_runtime_closure", source_runtime_closure)
        object.__setattr__(self, "_runtime_specification", runtime_specification)
        object.__setattr__(self, "_family_admission", family_admission)
        object.__setattr__(self, "_execution_identity", execution_identity)
        object.__setattr__(self, "_physical_identity", physical_identity)
        object.__setattr__(self, "_full_design_freeze", full_design_freeze)
        object.__setattr__(self, "_member_paths", member_paths)
        object.__setattr__(self, "_sealed", True)

    def __setattr__(self, name: str, value: object) -> None:
        if getattr(self, "_sealed", False):
            raise AttributeError("D7 fused-authority snapshot is immutable")
        object.__setattr__(self, name, value)

    def __reduce__(self) -> NoReturn:
        raise TypeError("D7 fused-authority snapshot is an in-process handoff")

    def __reduce_ex__(self, protocol: int) -> NoReturn:
        del protocol
        raise TypeError("D7 fused-authority snapshot is an in-process handoff")

    def __getstate__(self) -> NoReturn:
        raise TypeError("D7 fused-authority snapshot is an in-process handoff")

    def __copy__(self) -> NoReturn:
        raise TypeError("D7 fused-authority snapshot cannot be copied")

    def __deepcopy__(self, memo: object) -> NoReturn:
        del memo
        raise TypeError("D7 fused-authority snapshot cannot be copied")

    @property
    def descriptor_path(self) -> Path:
        return self._descriptor_path

    @property
    def repository_root(self) -> Path:
        return self._repository_root

    @property
    def head_commit(self) -> str:
        return self._head_commit

    @property
    def descriptor(self) -> _D7FusedAuthorityLaunchDescriptor:
        return self._descriptor

    @property
    def bundle(self) -> authority.D7LaunchAuthorityInputBundle:
        return self._bundle

    @property
    def replay_target(self) -> authority.D7ReplayTargetInputRecord:
        return self._replay_target

    @property
    def launch_intent(self) -> authority.D7LaunchIntentInputRecord:
        return self._launch_intent

    @property
    def source_runtime_closure(self) -> authority.D7SourceRuntimeClosureInputRecord:
        return self._source_runtime_closure

    @property
    def runtime_specification(self) -> authority.D7RuntimeSpecificationInputRecord:
        return self._runtime_specification

    @property
    def family_admission(self) -> authority.D7FamilyAdmissionInputRecord:
        return self._family_admission

    @property
    def execution_identity(self) -> authority.D7ExecutionIdentityInputRecord:
        return self._execution_identity

    @property
    def physical_identity(self) -> authority.D7PhysicalStoreLaneIdentityRecord:
        return self._physical_identity

    @property
    def full_design_freeze(self) -> authority.D7FullDesignFreezeInputRecord:
        return self._full_design_freeze

    @property
    def member_paths(self) -> tuple[Path, ...]:
        return self._member_paths


def _git(
    root: Path,
    *arguments: str,
    check: bool = True,
) -> subprocess.CompletedProcess[bytes]:
    completed = subprocess.run(
        ["git", "-C", str(root), *arguments],
        check=False,
        capture_output=True,
    )
    if check and completed.returncode != 0:
        raise QualificationContractError(
            "Git verification failed for the fused-authority descriptor"
        )
    return completed


def _absolute_lexical_path(value: str | Path) -> Path:
    if not isinstance(value, (str, Path)):
        raise TypeError("descriptor_path must be str or Path")
    try:
        result = Path(os.path.abspath(os.fspath(value)))
    except (TypeError, ValueError, OSError) as error:
        raise QualificationContractError("descriptor path is invalid") from error
    if Path(os.path.realpath(result)) != result:
        raise QualificationContractError(
            "descriptor path or one of its ancestors is a symlink"
        )
    return result


def _discover_repository(descriptor_path: Path) -> tuple[Path, str, str]:
    root_result = _git(descriptor_path.parent, "rev-parse", "--show-toplevel")
    try:
        root = Path(root_result.stdout.decode("utf-8").strip())
    except UnicodeDecodeError as error:
        raise QualificationContractError("Git root is not UTF-8") from error
    if (
        not root.is_absolute()
        or Path(os.path.realpath(root)) != root
        or root.is_symlink()
        or not root.is_dir()
    ):
        raise QualificationContractError("Git root must be one real directory")
    try:
        relative = descriptor_path.relative_to(root).as_posix()
    except ValueError as error:
        raise QualificationContractError(
            "descriptor path lies outside its derived Git root"
        ) from error
    relative = _repository_path(relative, label="descriptor repository path")
    head_result = _git(root, "rev-parse", "--verify", "HEAD^{commit}")
    try:
        head = head_result.stdout.decode("ascii").strip()
    except UnicodeDecodeError as error:
        raise QualificationContractError("Git HEAD is not ASCII") from error
    if _COMMIT_RE.fullmatch(head) is None:
        raise QualificationContractError("Git HEAD is not one exact commit")
    return root, head, relative


def _require_real_ancestors(root: Path, repository_path: str) -> Path:
    current = root
    if current.is_symlink() or not current.is_dir():
        raise QualificationContractError("Git root changed identity")
    parts = PurePosixPath(repository_path).parts
    for part in parts[:-1]:
        current = current / part
        try:
            status = current.lstat()
        except OSError as error:
            raise QualificationContractError(
                "fused-authority member ancestor is unavailable"
            ) from error
        if stat.S_ISLNK(status.st_mode) or not stat.S_ISDIR(status.st_mode):
            raise QualificationContractError(
                "fused-authority member ancestors must be real directories"
            )
    return root.joinpath(*parts)


def _stable_read(
    path: Path,
    *,
    repository_path: str,
    maximum_bytes: int,
    head_mode: str,
    head_object_id: str,
) -> tuple[bytes, _StableFileIdentity]:
    flags = os.O_RDONLY
    flags |= getattr(os, "O_CLOEXEC", 0)
    flags |= getattr(os, "O_NOFOLLOW", 0)
    flags |= getattr(os, "O_NONBLOCK", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as error:
        raise QualificationContractError(
            "fused-authority source could not be opened without following links"
        ) from error
    try:
        before = os.fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_nlink != 1
            or before.st_size <= 0
            or before.st_size > maximum_bytes
        ):
            raise QualificationContractError(
                "fused-authority source must be one bounded non-hardlinked regular file"
            )
        chunks: list[bytes] = []
        remaining = before.st_size
        while remaining:
            chunk = os.read(descriptor, min(remaining, 1024 * 1024))
            if not chunk:
                raise QualificationContractError(
                    "fused-authority source ended before its observed size"
                )
            chunks.append(chunk)
            remaining -= len(chunk)
        if os.read(descriptor, 1):
            raise QualificationContractError(
                "fused-authority source grew during its stable read"
            )
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    identity_fields = (
        "st_dev",
        "st_ino",
        "st_mode",
        "st_nlink",
        "st_size",
        "st_mtime_ns",
    )
    if tuple(getattr(before, name) for name in identity_fields) != tuple(
        getattr(after, name) for name in identity_fields
    ):
        raise QualificationContractError(
            "fused-authority source changed during its stable read"
        )
    try:
        visible = path.lstat()
    except OSError as error:
        raise QualificationContractError(
            "fused-authority source disappeared after its stable read"
        ) from error
    if tuple(getattr(after, name) for name in identity_fields) != tuple(
        getattr(visible, name) for name in identity_fields
    ):
        raise QualificationContractError(
            "fused-authority source path was replaced during its stable read"
        )
    source = b"".join(chunks)
    return source, _StableFileIdentity(
        repository_path=repository_path,
        path=path,
        head_mode=head_mode,
        head_object_id=head_object_id,
        device=after.st_dev,
        inode=after.st_ino,
        mode=after.st_mode,
        byte_count=after.st_size,
        mtime_ns=after.st_mtime_ns,
        canonical_sha256=sha256_bytes(source),
    )


def _head_blob(
    root: Path,
    *,
    head: str,
    repository_path: str,
    maximum_bytes: int,
) -> _GitHeadBlob:
    result = _git(root, "ls-tree", "-z", head, "--", repository_path)
    entries = [entry for entry in result.stdout.split(b"\0") if entry]
    if len(entries) != 1:
        raise QualificationContractError(
            "fused-authority source is not exactly one current-HEAD entry"
        )
    try:
        header, observed_path = entries[0].split(b"\t", 1)
        mode, object_type, object_id = header.decode("ascii").split(" ")
        decoded_path = observed_path.decode("utf-8")
    except (ValueError, UnicodeDecodeError) as error:
        raise QualificationContractError(
            "current-HEAD tree entry is malformed"
        ) from error
    if (
        decoded_path != repository_path
        or mode not in {"100644", "100755"}
        or object_type != "blob"
        or _COMMIT_RE.fullmatch(object_id) is None
    ):
        raise QualificationContractError(
            "fused-authority source is not a regular current-HEAD blob"
        )
    size_result = _git(root, "cat-file", "-s", object_id)
    try:
        size = int(size_result.stdout.decode("ascii").strip())
    except (ValueError, UnicodeDecodeError) as error:
        raise QualificationContractError("current-HEAD blob size is invalid") from error
    if size <= 0 or size > maximum_bytes:
        raise QualificationContractError("current-HEAD blob exceeds its byte cap")
    source = _git(root, "cat-file", "blob", object_id).stdout
    if len(source) != size:
        raise QualificationContractError("current-HEAD blob size changed")
    return _GitHeadBlob(mode=mode, object_id=object_id, source=source)


def _require_clean_index_entry(
    root: Path,
    *,
    repository_path: str,
    expected_mode: str,
    expected_object_id: str,
) -> None:
    result = _git(root, "ls-files", "--stage", "-z", "--", repository_path)
    entries = [entry for entry in result.stdout.split(b"\0") if entry]
    if len(entries) != 1:
        raise QualificationContractError(
            "fused-authority source is not exactly one tracked index entry"
        )
    try:
        header, observed_path = entries[0].split(b"\t", 1)
        mode, object_id, stage = header.decode("ascii").split(" ")
        decoded_path = observed_path.decode("utf-8")
    except (ValueError, UnicodeDecodeError) as error:
        raise QualificationContractError("Git index entry is malformed") from error
    if (
        decoded_path != repository_path
        or mode != expected_mode
        or object_id != expected_object_id
        or stage != "0"
    ):
        raise QualificationContractError(
            "fused-authority index entry differs from current HEAD"
        )


def _load_clean_head_source(
    root: Path,
    *,
    head: str,
    repository_path: str,
    maximum_bytes: int,
) -> tuple[bytes, _StableFileIdentity]:
    path = _require_real_ancestors(root, repository_path)
    head_blob = _head_blob(
        root,
        head=head,
        repository_path=repository_path,
        maximum_bytes=maximum_bytes,
    )
    _require_clean_index_entry(
        root,
        repository_path=repository_path,
        expected_mode=head_blob.mode,
        expected_object_id=head_blob.object_id,
    )
    source, identity = _stable_read(
        path,
        repository_path=repository_path,
        maximum_bytes=maximum_bytes,
        head_mode=head_blob.mode,
        head_object_id=head_blob.object_id,
    )
    # Compare digest and byte count before any canonical parser is invoked.
    if (
        identity.canonical_sha256 != sha256_bytes(head_blob.source)
        or identity.byte_count != len(head_blob.source)
        or source != head_blob.source
    ):
        raise QualificationContractError(
            "fused-authority source differs from its current-HEAD blob"
        )
    expected_executable = head_blob.mode == "100755"
    if bool(identity.mode & 0o111) is not expected_executable:
        raise QualificationContractError(
            "fused-authority source mode differs from current HEAD"
        )
    return source, identity


def _parse_canonical(source: bytes, *, label: str) -> object:
    try:
        return parse_canonical_json(source, label=label)
    except (CanonicalJsonError, RecursionError) as error:
        raise QualificationContractError(f"{label} is not canonical JSON") from error


def _parse_member(
    source: bytes,
    *,
    member: _D7FusedAuthorityMember,
) -> object:
    # The caller-independent descriptor binding and HEAD blob were checked
    # before this parser boundary.
    if (
        len(source) != member.byte_count
        or sha256_bytes(source) != member.canonical_sha256
    ):
        raise QualificationContractError(
            f"{member.artifact_role} differs from the descriptor inventory"
        )
    parsed = _parse_canonical(source, label=member.artifact_role)
    record_type = _MEMBER_SPEC_BY_ROLE[member.artifact_role][3]
    try:
        record = record_type.from_dict(parsed)
    except (TypeError, ValueError, RecursionError) as error:
        raise QualificationContractError(
            f"{member.artifact_role} does not satisfy its exact record contract"
        ) from error
    if record.canonical_bytes != source:
        raise QualificationContractError(
            f"{member.artifact_role} differs from reconstructed canonical bytes"
        )
    return record


def _commit_exists(root: Path, commit: str, *, label: str) -> str:
    if _COMMIT_RE.fullmatch(commit) is None:
        raise QualificationContractError(f"{label} is not one Git commit")
    result = _git(root, "rev-parse", "--verify", f"{commit}^{{commit}}")
    try:
        observed = result.stdout.decode("ascii").strip()
    except UnicodeDecodeError as error:
        raise QualificationContractError(f"{label} is not ASCII") from error
    if observed != commit:
        raise QualificationContractError(f"{label} does not resolve exactly")
    return observed


def _require_strict_ancestor(
    root: Path,
    ancestor: str,
    descendant: str,
    *,
    label: str,
) -> None:
    if ancestor == descendant:
        raise QualificationContractError(f"{label} must be a strict chronology")
    result = _git(
        root,
        "merge-base",
        "--is-ancestor",
        ancestor,
        descendant,
        check=False,
    )
    if result.returncode != 0:
        raise QualificationContractError(f"{label} ancestry differs")


def _verify_commit_chronology(
    root: Path,
    *,
    head: str,
    bundle: authority.D7LaunchAuthorityInputBundle,
) -> None:
    source_commit = _commit_exists(
        root,
        bundle.source_runtime_closure.source_commit,
        label="source/runtime closure commit",
    )
    freeze_commit = _commit_exists(
        root,
        bundle.full_design_freeze.freeze_commit,
        label="full-design freeze commit",
    )
    authorization_commit = _commit_exists(
        root,
        bundle.full_design_freeze.authorization_commit,
        label="launch authorization commit",
    )
    if (
        bundle.launch_intent.freeze_commit != freeze_commit
        or bundle.launch_intent.authorization_commit != authorization_commit
    ):
        raise QualificationContractError(
            "launch intent commit chronology differs from the full-design freeze"
        )
    _require_strict_ancestor(
        root,
        source_commit,
        freeze_commit,
        label="source-to-freeze",
    )
    _require_strict_ancestor(
        root,
        freeze_commit,
        authorization_commit,
        label="freeze-to-authorization",
    )
    _require_strict_ancestor(
        root,
        authorization_commit,
        head,
        label="authorization-to-current-HEAD",
    )


def _revalidate_identity(identity: _StableFileIdentity) -> None:
    try:
        observed = identity.path.lstat()
    except OSError as error:
        raise QualificationContractError(
            "fused-authority source disappeared before snapshot return"
        ) from error
    if (
        not stat.S_ISREG(observed.st_mode)
        or observed.st_nlink != 1
        or (
            observed.st_dev,
            observed.st_ino,
            observed.st_mode,
            observed.st_size,
            observed.st_mtime_ns,
        )
        != (
            identity.device,
            identity.inode,
            identity.mode,
            identity.byte_count,
            identity.mtime_ns,
        )
    ):
        raise QualificationContractError(
            "fused-authority source was replaced before snapshot return"
        )


def load_d7_fused_authority_snapshot(
    descriptor_path: str | Path,
    /,
) -> _LoadedD7FusedAuthoritySnapshot:
    """Reopen one closed current-HEAD inventory without granting authority.

    No expected digest, preverified record, capability, or caller token is
    accepted.  Git blob equality is derived from the descriptor's own current
    worktree and is still not proof that the repository or its operator is an
    official SpiralLens authority.
    """

    path = _absolute_lexical_path(descriptor_path)
    root, head, descriptor_repository_path = _discover_repository(path)
    descriptor_source, descriptor_identity = _load_clean_head_source(
        root,
        head=head,
        repository_path=descriptor_repository_path,
        maximum_bytes=MAX_D7_FUSED_AUTHORITY_DESCRIPTOR_BYTES,
    )
    descriptor_parsed = _parse_canonical(
        descriptor_source,
        label="D7 fused-authority launch descriptor",
    )
    try:
        descriptor = _D7FusedAuthorityLaunchDescriptor.from_dict(descriptor_parsed)
    except QualificationContractError:
        raise
    except (TypeError, ValueError, RecursionError) as error:
        raise QualificationContractError(
            "D7 fused-authority launch descriptor is invalid"
        ) from error
    if (
        descriptor.canonical_bytes != descriptor_source
        or descriptor.descriptor_repository_path != descriptor_repository_path
    ):
        raise QualificationContractError(
            "descriptor bytes or repository location differ"
        )

    records: dict[str, object] = {}
    member_identities: list[_StableFileIdentity] = []
    member_paths: list[Path] = []
    for member in descriptor.inventory:
        source, identity = _load_clean_head_source(
            root,
            head=head,
            repository_path=member.repository_path,
            maximum_bytes=min(
                member.byte_count,
                MAX_D7_FUSED_AUTHORITY_MEMBER_BYTES,
            ),
        )
        records[member.artifact_role] = _parse_member(source, member=member)
        member_identities.append(identity)
        member_paths.append(identity.path)

    bundle = records["launch-authority-input-bundle"]
    if type(bundle) is not authority.D7LaunchAuthorityInputBundle:
        raise QualificationContractError(
            "closed inventory did not produce one exact launch bundle"
        )
    for role, _contract, attribute, record_type in _MEMBER_SPECS[1:]:
        record = records[role]
        if type(record) is not record_type or record != getattr(bundle, attribute):
            raise QualificationContractError(
                f"{role} does not exactly rejoin the structural launch bundle"
            )

    _verify_commit_chronology(root, head=head, bundle=bundle)
    head_after = _git(root, "rev-parse", "--verify", "HEAD^{commit}").stdout
    try:
        decoded_head_after = head_after.decode("ascii").strip()
    except UnicodeDecodeError as error:
        raise QualificationContractError("Git HEAD changed encoding") from error
    if decoded_head_after != head:
        raise QualificationContractError(
            "Git HEAD changed during fused-authority reopening"
        )
    for identity in (descriptor_identity, *member_identities):
        _revalidate_identity(identity)
        _require_clean_index_entry(
            root,
            repository_path=identity.repository_path,
            expected_mode=identity.head_mode,
            expected_object_id=identity.head_object_id,
        )

    return _LoadedD7FusedAuthoritySnapshot(
        descriptor_path=path,
        repository_root=root,
        head_commit=head,
        descriptor=descriptor,
        bundle=bundle,
        replay_target=records["replay-target"],
        launch_intent=records["launch-intent"],
        source_runtime_closure=records["execution-source-runtime-closure"],
        runtime_specification=records["runtime-specification"],
        family_admission=records["family-admission"],
        execution_identity=records["execution-identity"],
        physical_identity=records["physical-store-lane-identity"],
        full_design_freeze=records["full-design-freeze"],
        member_paths=tuple(member_paths),
        _factory_token=_SNAPSHOT_FACTORY_TOKEN,
    )
