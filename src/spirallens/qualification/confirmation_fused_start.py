"""Same-call verification, exclusive start, execution, and terminal mechanics.

The sole operation in this deep-internal module accepts a raw committed launch
descriptor path and one zero-argument scientific producer.  It never accepts
or returns an authorization token, ownership object, lifecycle record, seed,
supplier, preverified receipt, or caller-selected trust root.

Transition checks are derived only inside the call from the descriptor's clean
current-HEAD inventory, a live canonical-origin/main observation, the declared
source/runtime and execution-identity observation surfaces, live physical
identity, and two path-absence observations.  A dedicated no-replace start
transaction is made durable before the producer can be entered.  The private
ownership handoff is consumed before callback invocation and is never returned.

No official descriptor or attempt exists in the repository yet.  Therefore
this module establishes mechanics and failure semantics, not an official D7
execution, result, scientific claim, replay permission, or D8 state.
"""

from __future__ import annotations

import inspect
import marshal
import os
import platform
import re
import stat
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from types import FunctionType
from typing import ClassVar, NoReturn, Self

from spirallens.core.canonical import (
    CanonicalJsonError,
    canonical_json_bytes,
    parse_canonical_json,
    sha256_bytes,
)

from . import confirmation_attempt_authority as a
from . import confirmation_attempt_evidence as e
from . import confirmation_attempt_persistence as p
from . import confirmation_attempt_records as r
from . import confirmation_attempt_terminal_persistence as terminal_persistence
from . import confirmation_authoritative_start_persistence as start_persistence
from . import confirmation_fused_authority as fused_authority
from . import confirmation_runner as runner
from . import confirmation_runtime_observation as runtime_observation
from . import confirmation_terminal_operations as terminal_operations
from .common import QualificationContractError

__all__: tuple[str, ...] = ()

D7_FUSED_START_VERIFICATION_EVIDENCE_SCHEMA_VERSION = (
    "spirallens.d7-fused-start-verification-evidence.v0.1"
)
D7_FUSED_START_SOURCE_TREE_SCHEME = (
    "spirallens.d7-fused-start-source-tree-observation.v0.1"
)
D7_FUSED_START_DEPENDENCY_SET_SCHEME = (
    runtime_observation.D7_RUNTIME_DEPENDENCY_SET_SCHEME
)
D7_FUSED_START_CALLABLE_IDENTITY_SCHEME = (
    "spirallens.d7-fused-start-callable-identity.v0.1"
)
D7_FUSED_START_PROCESS_IDENTITY_SCHEME = (
    "spirallens.d7-fused-start-process-identity.v0.1"
)
D7_RUNTIME_LOCK_REPOSITORY_PATH = "requirements-d7-runtime-lock.txt"
MAX_D7_SOURCE_RUNTIME_MEMBER_BYTES = 16 * 1024 * 1024
MAX_D7_SOURCE_RUNTIME_MEMBER_COUNT = 4096
MAX_D7_SOURCE_RUNTIME_TOTAL_BYTES = 128 * 1024 * 1024
MAX_D7_FUSED_START_VERIFICATION_EVIDENCE_BYTES = 256 * 1024
MAX_D7_PHYSICAL_DIRECTORY_ANCESTRY_DEPTH = 4096

_CANONICAL_ORIGIN_URLS = frozenset(
    {
        "https://github.com/RyoSpiralArchitect/SpiralLens",
        "https://github.com/RyoSpiralArchitect/SpiralLens.git",
        "git@github.com:RyoSpiralArchitect/SpiralLens.git",
        "ssh://git@github.com/RyoSpiralArchitect/SpiralLens.git",
    }
)
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
_VERIFIED_INPUT_FACTORY_TOKEN = object()
_REPOSITORY_ONLY_SOURCE_PATHS = (
    "experiments/qualification/d7_spectral_moment_confirmation_v0_1/"
    "post_d6_code/_post_d6_outputs_01_12.py",
    "experiments/qualification/d7_spectral_moment_confirmation_v0_1/"
    "post_d6_code/_post_d6_outputs_13_27.py",
    "experiments/qualification/d7_spectral_moment_confirmation_v0_1/"
    "post_d6_code/confirmation_post_d6_descriptive.py",
)
_SOURCE_PATHS = (
    "src/spirallens",
    "pyproject.toml",
    D7_RUNTIME_LOCK_REPOSITORY_PATH,
    *_REPOSITORY_ONLY_SOURCE_PATHS,
)


def _git(
    root: Path,
    *args: str,
    timeout: float = 30.0,
    check: bool = True,
) -> subprocess.CompletedProcess[bytes]:
    try:
        completed = subprocess.run(
            ["git", "-C", str(root), *args],
            check=False,
            capture_output=True,
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise QualificationContractError(
            f"cannot run Git verification: {' '.join(args)}"
        ) from error
    if check and completed.returncode != 0:
        detail = completed.stderr.decode("utf-8", errors="replace").strip()
        raise QualificationContractError(
            f"Git verification failed: {' '.join(args)}: {detail}"
        )
    return completed


def _sha256(value: object, *, label: str) -> str:
    if type(value) is not str or _SHA256_RE.fullmatch(value) is None:
        raise QualificationContractError(f"{label} must be a lowercase SHA-256")
    return value


def _commit(value: object, *, label: str) -> str:
    if type(value) is not str or _COMMIT_RE.fullmatch(value) is None:
        raise QualificationContractError(f"{label} must be a lowercase Git commit")
    return value


def _read_regular_file(path: Path, *, label: str, maximum_bytes: int) -> bytes:
    anchor = p._open_real_directory(path.parent, label=f"{label} parent")
    try:
        source, _observed = p._read_bounded_file(
            anchor,
            path.name,
            maximum_bytes=maximum_bytes,
            label=label,
        )
        return source
    finally:
        os.close(anchor.descriptor)


def _hash_regular_file(path: Path, *, label: str, maximum_bytes: int) -> str:
    return sha256_bytes(
        _read_regular_file(path, label=label, maximum_bytes=maximum_bytes)
    )


@dataclass(frozen=True, slots=True)
class _CanonicalOriginObservation:
    origin_url: str
    branch_name: str
    local_head_commit: str
    remote_main_commit: str

    def __post_init__(self) -> None:
        if self.origin_url not in _CANONICAL_ORIGIN_URLS:
            raise QualificationContractError("canonical origin URL differs")
        if self.branch_name != "main":
            raise QualificationContractError(
                "fused start requires the canonical main branch"
            )
        local = _commit(self.local_head_commit, label="local_head_commit")
        remote = _commit(self.remote_main_commit, label="remote_main_commit")
        if local != remote:
            raise QualificationContractError(
                "current HEAD differs from the live canonical origin/main"
            )

    @property
    def canonical_sha256(self) -> str:
        return sha256_bytes(
            canonical_json_bytes(
                {
                    "schema_version": (
                        "spirallens.d7-canonical-origin-observation.v0.1"
                    ),
                    "origin_url": self.origin_url,
                    "branch_name": self.branch_name,
                    "local_head_commit": self.local_head_commit,
                    "remote_main_commit": self.remote_main_commit,
                    "working_tree_clean": True,
                    "live_remote_ref_observed": True,
                }
            )
        )


def _observe_canonical_origin(
    snapshot: fused_authority._LoadedD7FusedAuthoritySnapshot,
) -> _CanonicalOriginObservation:
    root = snapshot.repository_root
    status = _git(root, "status", "--porcelain=v1", "-z", "--untracked-files=all")
    if status.stdout:
        raise QualificationContractError(
            "fused start requires an entirely clean current worktree"
        )
    try:
        branch = (
            _git(root, "symbolic-ref", "--quiet", "--short", "HEAD")
            .stdout.decode("utf-8")
            .strip()
        )
        origin_url = (
            _git(root, "remote", "get-url", "origin").stdout.decode("utf-8").strip()
        )
        remote = _git(
            root,
            "ls-remote",
            "--exit-code",
            "origin",
            "refs/heads/main",
            timeout=60.0,
        ).stdout.decode("ascii")
    except UnicodeDecodeError as error:
        raise QualificationContractError(
            "canonical repository observation is not valid text"
        ) from error
    lines = tuple(line.split() for line in remote.splitlines() if line.strip())
    if len(lines) != 1 or len(lines[0]) != 2 or lines[0][1] != "refs/heads/main":
        raise QualificationContractError(
            "canonical origin/main did not resolve to one exact ref"
        )
    return _CanonicalOriginObservation(
        origin_url=origin_url,
        branch_name=branch,
        local_head_commit=snapshot.head_commit,
        remote_main_commit=lines[0][0],
    )


def _source_tree_sha256(root: Path, source_commit: str) -> str:
    commit = _commit(source_commit, label="source_commit")

    def source_tree(commitish: str) -> tuple[bytes, ...]:
        tree = _git(
            root,
            "ls-tree",
            "-r",
            "-z",
            "--full-tree",
            commitish,
            "--",
            *_SOURCE_PATHS,
        ).stdout
        return tuple(raw for raw in tree.split(b"\0") if raw)

    frozen_entries = source_tree(commit)
    if source_tree("HEAD") != frozen_entries:
        raise QualificationContractError(
            "current execution-source inventory differs from the frozen source commit"
        )
    members: list[dict[str, object]] = []
    total_bytes = 0
    for raw in frozen_entries:
        try:
            header, raw_path = raw.split(b"\t", 1)
            mode, object_type, object_id = header.decode("ascii").split()
            repository_path = raw_path.decode("utf-8")
        except (ValueError, UnicodeDecodeError) as error:
            raise QualificationContractError(
                "source/runtime Git tree entry is malformed"
            ) from error
        included = (
            repository_path == "pyproject.toml"
            or repository_path == D7_RUNTIME_LOCK_REPOSITORY_PATH
            or repository_path.startswith("src/spirallens/")
            or repository_path in _REPOSITORY_ONLY_SOURCE_PATHS
        )
        if not included:
            continue
        if len(members) >= MAX_D7_SOURCE_RUNTIME_MEMBER_COUNT:
            raise QualificationContractError(
                "source/runtime tree exceeds its fixed member-count cap"
            )
        if (
            mode not in {"100644", "100755"}
            or object_type != "blob"
            or _COMMIT_RE.fullmatch(object_id) is None
        ):
            raise QualificationContractError(
                "source/runtime tree contains a non-regular member"
            )
        path = root / repository_path
        source = _read_regular_file(
            path,
            label=f"source/runtime member {repository_path}",
            maximum_bytes=MAX_D7_SOURCE_RUNTIME_MEMBER_BYTES,
        )
        try:
            object_size = int(
                _git(root, "cat-file", "-s", object_id).stdout.decode("ascii").strip()
            )
        except (UnicodeDecodeError, ValueError) as error:
            raise QualificationContractError(
                "source/runtime Git blob size is malformed"
            ) from error
        if object_size != len(source):
            raise QualificationContractError(
                "execution source size differs from its frozen Git blob"
            )
        total_bytes += len(source)
        if total_bytes > MAX_D7_SOURCE_RUNTIME_TOTAL_BYTES:
            raise QualificationContractError(
                "source/runtime tree exceeds its fixed total-byte cap"
            )
        blob = _git(root, "cat-file", "blob", object_id).stdout
        if blob != source:
            raise QualificationContractError(
                "execution source differs from its frozen Git blob"
            )
        members.append(
            {
                "repository_path": repository_path,
                "git_mode": mode,
                "byte_count": len(source),
                "sha256": sha256_bytes(source),
            }
        )
    observed_paths = {member["repository_path"] for member in members}
    if (
        "pyproject.toml" not in observed_paths
        or D7_RUNTIME_LOCK_REPOSITORY_PATH not in observed_paths
        or not any(
            isinstance(path, str) and path.startswith("src/spirallens/")
            for path in observed_paths
        )
        or not set(_REPOSITORY_ONLY_SOURCE_PATHS).issubset(observed_paths)
    ):
        raise QualificationContractError(
            "source/runtime tree lacks its fixed code or dependency-lock surface"
        )
    members.sort(key=lambda item: str(item["repository_path"]))
    return sha256_bytes(
        canonical_json_bytes(
            {
                "schema_version": D7_FUSED_START_SOURCE_TREE_SCHEME,
                "source_commit": commit,
                "members": members,
            }
        )
    )


@dataclass(frozen=True, slots=True)
class _RuntimeObservation:
    source_tree_sha256: str
    dependency_lock_sha256: str
    transitive_dependency_set_sha256: str
    native_runtime_sha256: str

    def __post_init__(self) -> None:
        for name in (
            "source_tree_sha256",
            "dependency_lock_sha256",
            "transitive_dependency_set_sha256",
            "native_runtime_sha256",
        ):
            _sha256(getattr(self, name), label=name)


def _observe_runtime(
    snapshot: fused_authority._LoadedD7FusedAuthoritySnapshot,
) -> _RuntimeObservation:
    root = snapshot.repository_root
    runtime = snapshot.runtime_specification
    closure = snapshot.source_runtime_closure
    executable = Path(os.path.realpath(sys.executable))
    dependency_lock_source = _read_regular_file(
        root / D7_RUNTIME_LOCK_REPOSITORY_PATH,
        label="D7 runtime dependency lock",
        maximum_bytes=runtime_observation.MAX_D7_RUNTIME_LOCK_BYTES,
    )
    dependencies = runtime_observation._verify_exact_dependency_lock(
        dependency_lock_source
    )
    observation = _RuntimeObservation(
        source_tree_sha256=_source_tree_sha256(root, closure.source_commit),
        dependency_lock_sha256=dependencies.dependency_lock_sha256,
        transitive_dependency_set_sha256=(
            dependencies.transitive_dependency_set_sha256
        ),
        native_runtime_sha256=_hash_regular_file(
            executable,
            label="Python native runtime executable",
            maximum_bytes=512 * 1024 * 1024,
        ),
    )
    observed_runtime = (
        sys.implementation.name,
        platform.python_version(),
        sys.platform,
        platform.machine().lower(),
        observation.dependency_lock_sha256,
        observation.native_runtime_sha256,
    )
    expected_runtime = (
        runtime.python_implementation,
        runtime.python_version,
        runtime.platform,
        runtime.machine,
        runtime.dependency_lock_sha256,
        runtime.native_runtime_sha256,
    )
    if observed_runtime != expected_runtime:
        raise QualificationContractError(
            "live Python/native runtime differs from the frozen specification"
        )
    if (
        observation.source_tree_sha256 != closure.source_tree_sha256
        or observation.transitive_dependency_set_sha256
        != closure.transitive_dependency_set_sha256
    ):
        raise QualificationContractError(
            "live source or transitive dependency closure differs"
        )
    return observation


@dataclass(frozen=True, slots=True)
class _ExecutionObservation:
    executable_sha256: str
    callable_identity_sha256: str
    process_identity_sha256: str

    def __post_init__(self) -> None:
        for name in (
            "executable_sha256",
            "callable_identity_sha256",
            "process_identity_sha256",
        ):
            _sha256(getattr(self, name), label=name)


def _observe_execution(
    snapshot: fused_authority._LoadedD7FusedAuthoritySnapshot,
    scientific_producer: Callable[[], runner.D7ScientificProducerOutput],
) -> _ExecutionObservation:
    if type(scientific_producer) is not FunctionType:
        raise QualificationContractError(
            "official scientific producer must be one exact Python function"
        )
    source_file_raw = inspect.getsourcefile(scientific_producer)
    if source_file_raw is None:
        raise QualificationContractError(
            "scientific producer source file cannot be resolved"
        )
    source_file = Path(os.path.realpath(source_file_raw))
    try:
        repository_path = source_file.relative_to(snapshot.repository_root).as_posix()
    except ValueError as error:
        raise QualificationContractError(
            "scientific producer must belong to the execution repository"
        ) from error
    if not repository_path.startswith(
        "src/spirallens/"
    ) or not repository_path.endswith(".py"):
        raise QualificationContractError(
            "scientific producer must be a tracked SpiralLens source function"
        )
    source = _read_regular_file(
        source_file,
        label="scientific producer source",
        maximum_bytes=MAX_D7_SOURCE_RUNTIME_MEMBER_BYTES,
    )
    head_source = _git(
        snapshot.repository_root,
        "show",
        f"{snapshot.head_commit}:{repository_path}",
    ).stdout
    if source != head_source:
        raise QualificationContractError(
            "scientific producer source differs from current HEAD"
        )
    executable = Path(os.path.realpath(sys.executable))
    executable_stat = executable.stat()
    executable_sha256 = _hash_regular_file(
        executable,
        label="execution Python executable",
        maximum_bytes=512 * 1024 * 1024,
    )
    callable_identity = sha256_bytes(
        canonical_json_bytes(
            {
                "schema_version": D7_FUSED_START_CALLABLE_IDENTITY_SCHEME,
                "module": scientific_producer.__module__,
                "qualname": scientific_producer.__qualname__,
                "repository_path": repository_path,
                "source_sha256": sha256_bytes(source),
                "code_sha256": sha256_bytes(
                    marshal.dumps(scientific_producer.__code__)
                ),
            }
        )
    )
    process_identity = sha256_bytes(
        canonical_json_bytes(
            {
                "schema_version": D7_FUSED_START_PROCESS_IDENTITY_SCHEME,
                "executable_realpath": str(executable),
                "executable_device": executable_stat.st_dev,
                "executable_inode": executable_stat.st_ino,
                "working_directory_realpath": os.path.realpath(os.getcwd()),
                "argv": list(sys.argv),
                "real_uid": os.getuid(),
                "effective_uid": os.geteuid(),
                "real_gid": os.getgid(),
                "effective_gid": os.getegid(),
            }
        )
    )
    observation = _ExecutionObservation(
        executable_sha256=executable_sha256,
        callable_identity_sha256=callable_identity,
        process_identity_sha256=process_identity,
    )
    expected = snapshot.execution_identity
    if (
        observation.executable_sha256,
        observation.callable_identity_sha256,
        observation.process_identity_sha256,
    ) != (
        expected.executable_sha256,
        expected.callable_identity_sha256,
        expected.process_identity_sha256,
    ):
        raise QualificationContractError(
            "live executable, callable, or process identity differs"
        )
    return observation


def _require_descriptor_bound_official_producer(
    snapshot: fused_authority._LoadedD7FusedAuthoritySnapshot,
    scientific_producer: object,
) -> None:
    """Bind the canonical official descriptor path to its sole producer."""

    repository_root = getattr(snapshot, "repository_root", None)
    descriptor_path = getattr(snapshot, "descriptor_path", None)
    if not isinstance(repository_root, Path) or not isinstance(descriptor_path, Path):
        # Existing isolated generic-runner tests use structural doubles that
        # deliberately omit filesystem coordinates.
        return
    from . import confirmation_official_execution as official

    official_path = (
        repository_root / official.D7_OFFICIAL_FUSED_DESCRIPTOR_REPOSITORY_PATH
    )
    if descriptor_path == official_path:
        official._require_official_producer_identity(scientific_producer)
        official._require_v0_1_chronology_execution_eligible(repository_root)


@dataclass(frozen=True, slots=True)
class _AbsentSubjectObservation:
    subject_kind: e.D7AbsentPathSubject
    resolved_parent_realpath: str
    subject_basename: str
    parent_device: int
    parent_inode: int
    subject_path_identity_sha256: str


def _observe_absent_subject(
    physical: a.D7PhysicalStoreLaneIdentityRecord,
    subject_kind: e.D7AbsentPathSubject,
) -> _AbsentSubjectObservation:
    is_output = subject_kind is e.D7AbsentPathSubject.OUTPUT_NAMESPACE
    subject_path = Path(
        physical.output_namespace_path if is_output else physical.terminal_path
    )
    expected_parent = (
        (physical.output_parent_device, physical.output_parent_inode)
        if is_output
        else (physical.terminal_parent_device, physical.terminal_parent_inode)
    )
    parent = p._open_real_directory(
        subject_path.parent,
        label=f"{subject_kind.value} parent",
    )
    try:
        if (parent.device, parent.inode) != expected_parent:
            raise QualificationContractError(
                f"{subject_kind.value} parent physical identity differs"
            )
        if p._relative_stat(parent, subject_path.name) is not None:
            raise QualificationContractError(
                f"{subject_kind.value} is present at fused-start observation"
            )
        p._verify_anchor(parent, label=f"{subject_kind.value} parent")
        return _AbsentSubjectObservation(
            subject_kind=subject_kind,
            resolved_parent_realpath=str(parent.path),
            subject_basename=subject_path.name,
            parent_device=parent.device,
            parent_inode=parent.inode,
            subject_path_identity_sha256=e.d7_path_identity_sha256(
                store_identity_sha256=physical.store_identity_sha256,
                resolved_parent_realpath=str(parent.path),
                subject_basename=subject_path.name,
            ),
        )
    finally:
        os.close(parent.descriptor)


def _physical_directory_ancestry(
    anchor: p._DirectoryAnchor,
    *,
    label: str,
) -> tuple[tuple[int, int], ...]:
    """Return the descriptor-relative physical ancestry from ``anchor`` to root."""

    try:
        descriptor = os.dup(anchor.descriptor)
    except OSError as error:
        raise QualificationContractError(
            f"cannot duplicate {label} directory descriptor"
        ) from error
    identities: list[tuple[int, int]] = []
    seen: set[tuple[int, int]] = set()
    try:
        for _depth in range(MAX_D7_PHYSICAL_DIRECTORY_ANCESTRY_DEPTH):
            try:
                observed = os.fstat(descriptor)
            except OSError as error:
                raise QualificationContractError(
                    f"cannot inspect {label} physical ancestry"
                ) from error
            if not stat.S_ISDIR(observed.st_mode):
                raise QualificationContractError(
                    f"{label} physical ancestry member is not a directory"
                )
            identity = p._identity(observed)
            if identity in seen:
                raise QualificationContractError(
                    f"{label} physical ancestry contains a cycle"
                )
            identities.append(identity)
            seen.add(identity)

            parent_descriptor: int | None = None
            try:
                parent_descriptor = os.open(
                    "..",
                    p._directory_flags(),
                    dir_fd=descriptor,
                )
                parent_observed = os.fstat(parent_descriptor)
                if not stat.S_ISDIR(parent_observed.st_mode):
                    raise QualificationContractError(
                        f"{label} physical parent is not a directory"
                    )
                parent_identity = p._identity(parent_observed)
                if parent_identity == identity:
                    return tuple(identities)
                os.close(descriptor)
                descriptor = parent_descriptor
                parent_descriptor = None
            except OSError as error:
                raise QualificationContractError(
                    f"cannot traverse {label} physical ancestry"
                ) from error
            finally:
                if parent_descriptor is not None:
                    os.close(parent_descriptor)
        raise QualificationContractError(
            f"{label} physical ancestry exceeds the fixed depth limit"
        )
    finally:
        os.close(descriptor)


def _verify_store_and_lane(
    repository_root: Path,
    physical: a.D7PhysicalStoreLaneIdentityRecord,
) -> None:
    repository = p._open_real_directory(
        repository_root,
        label="fused-start Git repository",
    )
    store: p._DirectoryAnchor | None = None
    lane: p._DirectoryAnchor | None = None
    try:
        store = p._open_real_directory(physical.store_path, label="fused-start store")
        repository_ancestry = _physical_directory_ancestry(
            repository,
            label="fused-start Git repository",
        )
        store_ancestry = _physical_directory_ancestry(
            store,
            label="fused-start store",
        )
        repository_identity = (repository.device, repository.inode)
        store_identity = (store.device, store.inode)
        if repository_identity in store_ancestry:
            raise QualificationContractError(
                "authoritative attempt store must not be inside the Git repository"
            )
        if store_identity in repository_ancestry:
            raise QualificationContractError(
                "authoritative attempt store must not contain the Git repository"
            )
        lane = p._open_child_directory(
            store,
            leaf=a.D7_AUTHORITATIVE_START_LANE_BASENAME,
            label="fused-start authoritative lane",
            create=False,
        )
        if (
            str(store.path),
            store.device,
            store.inode,
            str(lane.path),
            lane.device,
            lane.inode,
        ) != (
            physical.store_path,
            physical.store_device,
            physical.store_inode,
            physical.lane_path,
            physical.lane_device,
            physical.lane_inode,
        ):
            raise QualificationContractError(
                "live store or authoritative-start lane identity differs"
            )
        p._verify_anchor(lane, label="fused-start authoritative lane")
        p._verify_anchor(store, label="fused-start store")
        p._verify_anchor(repository, label="fused-start Git repository")
    finally:
        if lane is not None:
            os.close(lane.descriptor)
        if store is not None:
            os.close(store.descriptor)
        os.close(repository.descriptor)


def _authorization_receipt(
    *,
    snapshot: fused_authority._LoadedD7FusedAuthoritySnapshot,
    declaration: r.D7AttemptDeclarationRecord,
    subject: _AbsentSubjectObservation,
) -> e.D7AuthorizationPathAbsenceReceipt:
    return e.D7AuthorizationPathAbsenceReceipt(
        subject_kind=subject.subject_kind,
        replay_target_sha256=declaration.replay_target_sha256,
        attempt_key_sha256=declaration.attempt_key_sha256,
        attempt_declaration_sha256=declaration.canonical_sha256,
        authorization_commit=snapshot.launch_intent.authorization_commit,
        execution_identity_receipt_sha256=(
            snapshot.execution_identity.canonical_sha256
        ),
        store_identity_sha256=declaration.store_identity_sha256,
        subject_path_identity_sha256=subject.subject_path_identity_sha256,
        store_root_realpath=snapshot.physical_identity.store_path,
        resolved_parent_realpath=subject.resolved_parent_realpath,
        subject_basename=subject.subject_basename,
        parent_device=subject.parent_device,
        parent_inode=subject.parent_inode,
    )


def _pre_start_receipt(
    *,
    snapshot: fused_authority._LoadedD7FusedAuthoritySnapshot,
    declaration: r.D7AttemptDeclarationRecord,
    authorization: r.D7LaunchAuthorizationRecord,
    claim: r.D7AttemptClaimRecord,
    subject: _AbsentSubjectObservation,
) -> e.D7PreStartPathAbsenceReceipt:
    return e.D7PreStartPathAbsenceReceipt(
        subject_kind=subject.subject_kind,
        replay_target_sha256=declaration.replay_target_sha256,
        attempt_key_sha256=declaration.attempt_key_sha256,
        attempt_declaration_sha256=declaration.canonical_sha256,
        launch_authorization_sha256=authorization.canonical_sha256,
        attempt_claim_sha256=claim.canonical_sha256,
        authorization_commit=snapshot.launch_intent.authorization_commit,
        execution_identity_receipt_sha256=(
            snapshot.execution_identity.canonical_sha256
        ),
        store_identity_sha256=declaration.store_identity_sha256,
        subject_path_identity_sha256=subject.subject_path_identity_sha256,
        store_root_realpath=snapshot.physical_identity.store_path,
        resolved_parent_realpath=subject.resolved_parent_realpath,
        subject_basename=subject.subject_basename,
        parent_device=subject.parent_device,
        parent_inode=subject.parent_inode,
    )


@dataclass(frozen=True, slots=True)
class _D7FusedStartVerificationEvidence:
    descriptor_sha256: str
    launch_bundle_sha256: str
    repository_head_commit: str
    canonical_origin_observation_sha256: str
    replay_target_sha256: str
    launch_intent_sha256: str
    source_runtime_closure_sha256: str
    runtime_specification_sha256: str
    family_admission_sha256: str
    execution_identity_sha256: str
    physical_identity_sha256: str
    full_design_freeze_sha256: str
    source_tree_sha256: str
    transitive_dependency_set_sha256: str
    callable_identity_sha256: str
    process_identity_sha256: str
    attempt_key_sha256: str

    schema_version: ClassVar[str] = D7_FUSED_START_VERIFICATION_EVIDENCE_SCHEMA_VERSION
    _SHA256_FIELDS: ClassVar[tuple[str, ...]] = (
        "descriptor_sha256",
        "launch_bundle_sha256",
        "canonical_origin_observation_sha256",
        "replay_target_sha256",
        "launch_intent_sha256",
        "source_runtime_closure_sha256",
        "runtime_specification_sha256",
        "family_admission_sha256",
        "execution_identity_sha256",
        "physical_identity_sha256",
        "full_design_freeze_sha256",
        "source_tree_sha256",
        "transitive_dependency_set_sha256",
        "callable_identity_sha256",
        "process_identity_sha256",
        "attempt_key_sha256",
    )
    _TRUE_FIELDS: ClassVar[tuple[str, ...]] = (
        "descriptor_and_members_reopened",
        "canonical_origin_main_live_reobserved",
        "declared_source_runtime_surface_matched",
        "declared_execution_identity_fields_matched",
        "physical_identity_live_reobserved",
        "authorization_absence_observed",
        "pre_start_absence_observed",
        "canonical_repository_transition_checks_satisfied",
    )
    _FALSE_FIELDS: ClassVar[tuple[str, ...]] = (
        "reusable_authorization_capability_present",
        "caller_authorization_token_accepted",
        "execution_observed",
        "scientific_claim_eligible",
        "d7_result_produced",
        "d8_execution_authorized",
        "persisted_replay_reauthenticates_live_observations",
        "all_live_observation_digests_semantically_rejoined",
    )
    _RECORD_KIND: ClassVar[str] = "same-call-fused-start-verification-evidence"
    _VERIFICATION_SCOPE: ClassVar[str] = (
        "canonical-origin-main-clean-head-declared-runtime-and-physical-v0.1"
    )

    def __post_init__(self) -> None:
        for name in self._SHA256_FIELDS:
            _sha256(getattr(self, name), label=name)
        _commit(self.repository_head_commit, label="repository_head_commit")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "record_kind": self._RECORD_KIND,
            "claim_ceiling": r.D7_RECORD_CLAIM_CEILING,
            "descriptor_sha256": self.descriptor_sha256,
            "launch_bundle_sha256": self.launch_bundle_sha256,
            "repository_head_commit": self.repository_head_commit,
            "canonical_origin_observation_sha256": (
                self.canonical_origin_observation_sha256
            ),
            "replay_target_sha256": self.replay_target_sha256,
            "launch_intent_sha256": self.launch_intent_sha256,
            "source_runtime_closure_sha256": (self.source_runtime_closure_sha256),
            "runtime_specification_sha256": self.runtime_specification_sha256,
            "family_admission_sha256": self.family_admission_sha256,
            "execution_identity_sha256": self.execution_identity_sha256,
            "physical_identity_sha256": self.physical_identity_sha256,
            "full_design_freeze_sha256": self.full_design_freeze_sha256,
            "source_tree_sha256": self.source_tree_sha256,
            "transitive_dependency_set_sha256": (self.transitive_dependency_set_sha256),
            "callable_identity_sha256": self.callable_identity_sha256,
            "process_identity_sha256": self.process_identity_sha256,
            "attempt_key_sha256": self.attempt_key_sha256,
            "verification_scope": self._VERIFICATION_SCOPE,
            "descriptor_and_members_reopened": True,
            "canonical_origin_main_live_reobserved": True,
            "declared_source_runtime_surface_matched": True,
            "declared_execution_identity_fields_matched": True,
            "physical_identity_live_reobserved": True,
            "authorization_absence_observed": True,
            "pre_start_absence_observed": True,
            "canonical_repository_transition_checks_satisfied": True,
            "reusable_authorization_capability_present": False,
            "caller_authorization_token_accepted": False,
            "execution_observed": False,
            "scientific_claim_eligible": False,
            "d7_result_produced": False,
            "d8_execution_authorized": False,
            "persisted_replay_reauthenticates_live_observations": False,
            "all_live_observation_digests_semantically_rejoined": False,
        }

    @classmethod
    def from_dict(cls, value: object) -> Self:
        if type(value) is not dict or any(type(key) is not str for key in value):
            raise QualificationContractError(
                "fused-start verification evidence must be an exact JSON object"
            )
        item = dict(value)
        constants: dict[str, object] = {
            "schema_version": cls.schema_version,
            "record_kind": cls._RECORD_KIND,
            "claim_ceiling": r.D7_RECORD_CLAIM_CEILING,
            "verification_scope": cls._VERIFICATION_SCOPE,
            **dict.fromkeys(cls._TRUE_FIELDS, True),
            **dict.fromkeys(cls._FALSE_FIELDS, False),
        }
        expected = {
            *constants,
            *cls._SHA256_FIELDS,
            "repository_head_commit",
        }
        if set(item) != expected:
            raise QualificationContractError(
                "fused-start verification evidence fields differ"
            )
        for name, expected_value in constants.items():
            if item[name] != expected_value or type(item[name]) is not type(
                expected_value
            ):
                raise QualificationContractError(
                    f"fused-start verification evidence {name} differs"
                )
        fields = {name: _sha256(item[name], label=name) for name in cls._SHA256_FIELDS}
        return cls(
            **fields,
            repository_head_commit=_commit(
                item["repository_head_commit"],
                label="repository_head_commit",
            ),
        )

    @classmethod
    def from_canonical_bytes(
        cls,
        source: bytes,
        *,
        expected_sha256: str,
    ) -> Self:
        expected = _sha256(expected_sha256, label="expected_sha256")
        if (
            type(source) is not bytes
            or not source
            or len(source) > MAX_D7_FUSED_START_VERIFICATION_EVIDENCE_BYTES
        ):
            raise QualificationContractError(
                "fused-start verification evidence bytes exceed the cap"
            )
        if sha256_bytes(source) != expected:
            raise QualificationContractError(
                "fused-start verification evidence SHA-256 differs before parse"
            )
        try:
            parsed = parse_canonical_json(
                source,
                label="fused-start verification evidence",
            )
        except (CanonicalJsonError, RecursionError) as error:
            raise QualificationContractError(
                "fused-start verification evidence is not canonical JSON"
            ) from error
        result = cls.from_dict(parsed)
        if result.canonical_bytes != source:
            raise QualificationContractError(
                "fused-start verification evidence canonical round-trip differs"
            )
        return result

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_dict())

    @property
    def canonical_sha256(self) -> str:
        return sha256_bytes(self.canonical_bytes)


class _VerifiedD7StartInputs:
    __slots__ = (
        "_authorization",
        "_authorization_output_receipt",
        "_authorization_terminal_receipt",
        "_claim",
        "_declaration",
        "_origin",
        "_pre_start_output_receipt",
        "_pre_start_terminal_receipt",
        "_runtime",
        "_sealed",
        "_snapshot",
        "_start",
        "_verification",
    )

    def __init__(
        self,
        *,
        snapshot: fused_authority._LoadedD7FusedAuthoritySnapshot,
        origin: _CanonicalOriginObservation,
        runtime: _RuntimeObservation,
        declaration: r.D7AttemptDeclarationRecord,
        authorization_output_receipt: e.D7AuthorizationPathAbsenceReceipt,
        authorization_terminal_receipt: e.D7AuthorizationPathAbsenceReceipt,
        authorization: r.D7LaunchAuthorizationRecord,
        claim: r.D7AttemptClaimRecord,
        pre_start_output_receipt: e.D7PreStartPathAbsenceReceipt,
        pre_start_terminal_receipt: e.D7PreStartPathAbsenceReceipt,
        start: r.D7ExecutionStartRecord,
        verification: _D7FusedStartVerificationEvidence,
        _factory_token: object,
    ) -> None:
        if _factory_token is not _VERIFIED_INPUT_FACTORY_TOKEN:
            raise TypeError("verified D7 start inputs require the fused verifier")
        for name, value in locals().copy().items():
            if name in {"self", "_factory_token"}:
                continue
            object.__setattr__(self, f"_{name}", value)
        object.__setattr__(self, "_sealed", True)

    def __setattr__(self, name: str, value: object) -> None:
        if getattr(self, "_sealed", False):
            raise AttributeError("verified D7 start inputs are immutable")
        object.__setattr__(self, name, value)

    def __reduce__(self) -> NoReturn:
        raise TypeError("verified D7 start inputs are an in-process handoff")

    def __reduce_ex__(self, protocol: int) -> NoReturn:
        del protocol
        raise TypeError("verified D7 start inputs are an in-process handoff")

    @property
    def snapshot(self) -> fused_authority._LoadedD7FusedAuthoritySnapshot:
        return self._snapshot

    @property
    def verification(self) -> _D7FusedStartVerificationEvidence:
        return self._verification

    @property
    def declaration(self) -> r.D7AttemptDeclarationRecord:
        return self._declaration

    @property
    def authorization_output_receipt(self) -> e.D7AuthorizationPathAbsenceReceipt:
        return self._authorization_output_receipt

    @property
    def authorization_terminal_receipt(self) -> e.D7AuthorizationPathAbsenceReceipt:
        return self._authorization_terminal_receipt

    @property
    def authorization(self) -> r.D7LaunchAuthorizationRecord:
        return self._authorization

    @property
    def claim(self) -> r.D7AttemptClaimRecord:
        return self._claim

    @property
    def pre_start_output_receipt(self) -> e.D7PreStartPathAbsenceReceipt:
        return self._pre_start_output_receipt

    @property
    def pre_start_terminal_receipt(self) -> e.D7PreStartPathAbsenceReceipt:
        return self._pre_start_terminal_receipt

    @property
    def start(self) -> r.D7ExecutionStartRecord:
        return self._start


def _verify_and_derive_start_inputs(
    snapshot: fused_authority._LoadedD7FusedAuthoritySnapshot,
    scientific_producer: Callable[[], runner.D7ScientificProducerOutput],
) -> _VerifiedD7StartInputs:
    origin = _observe_canonical_origin(snapshot)
    runtime = _observe_runtime(snapshot)
    execution = _observe_execution(snapshot, scientific_producer)
    physical = snapshot.physical_identity
    _verify_store_and_lane(snapshot.repository_root, physical)
    authorization_output = _observe_absent_subject(
        physical,
        e.D7AbsentPathSubject.OUTPUT_NAMESPACE,
    )
    authorization_terminal = _observe_absent_subject(
        physical,
        e.D7AbsentPathSubject.TERMINAL_PATH,
    )
    declaration = r.D7AttemptDeclarationRecord(
        replay_target_sha256=snapshot.replay_target.canonical_sha256,
        launch_intent_sha256=snapshot.launch_intent.canonical_sha256,
        role_evidence=r.D7PrimaryRoleEvidence(),
        store_identity_sha256=physical.store_identity_sha256,
        output_namespace_identity_sha256=(
            authorization_output.subject_path_identity_sha256
        ),
        terminal_path_identity_sha256=(
            authorization_terminal.subject_path_identity_sha256
        ),
        authorization_commit=snapshot.launch_intent.authorization_commit,
        execution_identity_receipt_sha256=(
            snapshot.execution_identity.canonical_sha256
        ),
    )
    authorization_output_receipt = _authorization_receipt(
        snapshot=snapshot,
        declaration=declaration,
        subject=authorization_output,
    )
    authorization_terminal_receipt = _authorization_receipt(
        snapshot=snapshot,
        declaration=declaration,
        subject=authorization_terminal,
    )
    authorization = r.D7LaunchAuthorizationRecord(
        attempt_declaration_sha256=declaration.canonical_sha256,
        replay_target_sha256=declaration.replay_target_sha256,
        attempt_key_sha256=declaration.attempt_key_sha256,
        authorization_commit=declaration.authorization_commit,
        execution_identity_receipt_sha256=(
            declaration.execution_identity_receipt_sha256
        ),
        execution_source_runtime_receipt_sha256=(
            snapshot.source_runtime_closure.receipt_binding.canonical_sha256
        ),
        runtime_specification_sha256=snapshot.runtime_specification.canonical_sha256,
        admission_receipt_sha256=(
            snapshot.family_admission.admission_receipt_binding.canonical_sha256
        ),
        full_design_freeze_receipt_sha256=(
            snapshot.full_design_freeze.canonical_sha256
        ),
        store_identity_sha256=declaration.store_identity_sha256,
        output_namespace_identity_sha256=(declaration.output_namespace_identity_sha256),
        terminal_path_identity_sha256=declaration.terminal_path_identity_sha256,
        authorization_output_namespace_absence_receipt_sha256=(
            authorization_output_receipt.canonical_sha256
        ),
        authorization_terminal_path_absence_receipt_sha256=(
            authorization_terminal_receipt.canonical_sha256
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
    _verify_store_and_lane(snapshot.repository_root, physical)
    pre_start_output = _observe_absent_subject(
        physical,
        e.D7AbsentPathSubject.OUTPUT_NAMESPACE,
    )
    pre_start_terminal = _observe_absent_subject(
        physical,
        e.D7AbsentPathSubject.TERMINAL_PATH,
    )
    pre_start_output_receipt = _pre_start_receipt(
        snapshot=snapshot,
        declaration=declaration,
        authorization=authorization,
        claim=claim,
        subject=pre_start_output,
    )
    pre_start_terminal_receipt = _pre_start_receipt(
        snapshot=snapshot,
        declaration=declaration,
        authorization=authorization,
        claim=claim,
        subject=pre_start_terminal,
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
            snapshot.execution_identity.canonical_sha256
        ),
        observed_execution_source_runtime_receipt_sha256=(
            snapshot.source_runtime_closure.receipt_binding.canonical_sha256
        ),
        observed_runtime_specification_sha256=(
            snapshot.runtime_specification.canonical_sha256
        ),
        output_namespace_identity_sha256=(declaration.output_namespace_identity_sha256),
        terminal_path_identity_sha256=declaration.terminal_path_identity_sha256,
        pre_start_output_namespace_absence_receipt_sha256=(
            pre_start_output_receipt.canonical_sha256
        ),
        pre_start_terminal_path_absence_receipt_sha256=(
            pre_start_terminal_receipt.canonical_sha256
        ),
    )
    verification = _D7FusedStartVerificationEvidence(
        descriptor_sha256=snapshot.descriptor.canonical_sha256,
        launch_bundle_sha256=snapshot.bundle.canonical_sha256,
        repository_head_commit=snapshot.head_commit,
        canonical_origin_observation_sha256=origin.canonical_sha256,
        replay_target_sha256=snapshot.replay_target.canonical_sha256,
        launch_intent_sha256=snapshot.launch_intent.canonical_sha256,
        source_runtime_closure_sha256=(
            snapshot.source_runtime_closure.canonical_sha256
        ),
        runtime_specification_sha256=snapshot.runtime_specification.canonical_sha256,
        family_admission_sha256=snapshot.family_admission.canonical_sha256,
        execution_identity_sha256=snapshot.execution_identity.canonical_sha256,
        physical_identity_sha256=snapshot.physical_identity.canonical_sha256,
        full_design_freeze_sha256=snapshot.full_design_freeze.canonical_sha256,
        source_tree_sha256=runtime.source_tree_sha256,
        transitive_dependency_set_sha256=(runtime.transitive_dependency_set_sha256),
        callable_identity_sha256=execution.callable_identity_sha256,
        process_identity_sha256=execution.process_identity_sha256,
        attempt_key_sha256=start.attempt_key_sha256,
    )
    return _VerifiedD7StartInputs(
        snapshot=snapshot,
        origin=origin,
        runtime=runtime,
        declaration=declaration,
        authorization_output_receipt=authorization_output_receipt,
        authorization_terminal_receipt=authorization_terminal_receipt,
        authorization=authorization,
        claim=claim,
        pre_start_output_receipt=pre_start_output_receipt,
        pre_start_terminal_receipt=pre_start_terminal_receipt,
        start=start,
        verification=verification,
        _factory_token=_VERIFIED_INPUT_FACTORY_TOKEN,
    )


def _same_verified_inputs(
    first: _VerifiedD7StartInputs,
    second: _VerifiedD7StartInputs,
) -> bool:
    return (
        first.snapshot.head_commit,
        first.snapshot.descriptor.canonical_sha256,
        first.snapshot.bundle.canonical_sha256,
        first.verification.canonical_sha256,
        first.declaration,
        first.authorization_output_receipt,
        first.authorization_terminal_receipt,
        first.authorization,
        first.claim,
        first.pre_start_output_receipt,
        first.pre_start_terminal_receipt,
        first.start,
    ) == (
        second.snapshot.head_commit,
        second.snapshot.descriptor.canonical_sha256,
        second.snapshot.bundle.canonical_sha256,
        second.verification.canonical_sha256,
        second.declaration,
        second.authorization_output_receipt,
        second.authorization_terminal_receipt,
        second.authorization,
        second.claim,
        second.pre_start_output_receipt,
        second.pre_start_terminal_receipt,
        second.start,
    )


def _source_envelope_binding(
    verified: _VerifiedD7StartInputs,
) -> a.D7AuthorityArtifactBinding:
    source = verified.snapshot.descriptor.canonical_bytes
    return a.D7AuthorityArtifactBinding(
        artifact_role="launch-authority-source-envelope",
        artifact_contract_id=fused_authority.D7_FUSED_AUTHORITY_DESCRIPTOR_SCHEMA_VERSION,
        canonical_sha256=sha256_bytes(source),
        byte_count=len(source),
    )


def _verification_binding(
    verified: _VerifiedD7StartInputs,
) -> a.D7AuthorityArtifactBinding:
    source = verified.verification.canonical_bytes
    return a.D7AuthorityArtifactBinding(
        artifact_role="launch-authority-verification-evidence",
        artifact_contract_id=verified.verification.schema_version,
        canonical_sha256=sha256_bytes(source),
        byte_count=len(source),
    )


def _persist_failed_terminal_from_exception(
    loaded_start: start_persistence.D7LoadedAuthoritativeStartTransaction,
    ownership: runner._D7PostStartOwnership,
    error: Exception,
) -> None:
    attributes: dict[str, object] | None = None
    try:
        try:
            candidate = object.__getattribute__(error, "__dict__")
            if type(candidate) is dict:
                attributes = candidate
        except BaseException:  # noqa: BLE001
            attributes = None
        prepared = (
            attributes.get(runner.D7_PREPARED_FAILED_TERMINAL_ATTRIBUTE)
            if attributes is not None
            else None
        )
        if (
            type(prepared) is runner.D7PreparedFailedTerminal
            and prepared.ownership is ownership
        ):
            try:
                published = terminal_operations.persist_d7_prepared_terminal_no_replace(
                    loaded_start,
                    prepared,
                )
                if published.parent_directory_fsync_proved is not True:
                    try:
                        error.add_note(
                            "D7 failed-terminal publication is visible but "
                            "parent-directory durability is unproved: "
                            f"path={published.path}; "
                            "terminal_manifest_sha256="
                            f"{published.terminal_manifest_sha256}; "
                            "terminal_consumption_sha256="
                            f"{published.terminal_consumption_sha256}; "
                            f"directory_device={published.directory_device}; "
                            f"directory_inode={published.directory_inode}"
                        )
                    except BaseException:  # noqa: BLE001
                        pass
            except BaseException as terminal_error:  # noqa: BLE001
                try:
                    error.add_note(
                        "D7 failed-terminal publication did not complete: "
                        f"{type(terminal_error).__module__}."
                        f"{type(terminal_error).__qualname__}: {terminal_error}"
                    )
                except BaseException:  # noqa: BLE001
                    pass
    finally:
        ownership._invalidate_all()
        if attributes is not None:
            attributes.pop(
                runner.D7_PREPARED_FAILED_TERMINAL_ATTRIBUTE,
                None,
            )
        else:
            try:
                object.__delattr__(
                    error,
                    runner.D7_PREPARED_FAILED_TERMINAL_ATTRIBUTE,
                )
            except BaseException:  # noqa: BLE001
                pass


def run_d7_fused_verify_start_and_terminal_no_replace(
    descriptor_path: str | Path,
    scientific_producer: Callable[[], runner.D7ScientificProducerOutput],
    /,
) -> terminal_persistence.D7PersistedStructuralTerminalIdentity:
    """Attempt one fused D7 start and at most one terminal publication.

    A visible start is never resumed.  Any exception after its no-replace
    publication leaves the attempt consumed.  An ordinary producer/result
    exception may publish one conservatively prepared failed terminal.  Hard
    process exits and ``BaseException`` outcomes leave structural start bytes
    visible and the terminal absent; this module does not itself establish the
    named ``started_unresolved`` lifecycle state.
    """

    if not callable(scientific_producer):
        raise TypeError("scientific_producer must be callable")
    snapshot = fused_authority.load_d7_fused_authority_snapshot(descriptor_path)
    _require_descriptor_bound_official_producer(snapshot, scientific_producer)
    verified = _verify_and_derive_start_inputs(snapshot, scientific_producer)
    source_envelope = verified.snapshot.descriptor.canonical_bytes
    verification_source = verified.verification.canonical_bytes
    loaded_start = (
        start_persistence.persist_d7_authoritative_start_transaction_no_replace(
            verified.snapshot.physical_identity.store_path,
            launch_authority_source_envelope_source=source_envelope,
            launch_authority_source_envelope_binding=(
                _source_envelope_binding(verified)
            ),
            verification_evidence_source=verification_source,
            verification_evidence_binding=_verification_binding(verified),
            declaration=verified.declaration,
            authorization_output_receipt=(verified.authorization_output_receipt),
            authorization_terminal_receipt=(verified.authorization_terminal_receipt),
            authorization=verified.authorization,
            claim=verified.claim,
            pre_start_output_receipt=verified.pre_start_output_receipt,
            pre_start_terminal_receipt=verified.pre_start_terminal_receipt,
            start=verified.start,
        )
    )
    if loaded_start.parent_directory_fsync_proved is not True:
        raise QualificationContractError(
            "authoritative start is visible but parent-directory durability "
            "is unproved; callback entry is forbidden and retry is not authorized"
        )

    # Reopen and recompute every authority/live input after the start becomes
    # visible.  Any drift consumes the attempt without entering the producer.
    reloaded_snapshot = fused_authority.load_d7_fused_authority_snapshot(
        descriptor_path
    )
    reverified = _verify_and_derive_start_inputs(
        reloaded_snapshot,
        scientific_producer,
    )
    if not _same_verified_inputs(verified, reverified):
        raise QualificationContractError(
            "fused-start authority or live observations changed at transition"
        )
    reloaded_start = start_persistence.load_d7_authoritative_start_transaction(
        loaded_start.store_root,
        attempt_key_sha256=loaded_start.start.attempt_key_sha256,
        expected_manifest_sha256=loaded_start.manifest.canonical_sha256,
    )
    if (
        reloaded_start.directory_identity_sha256
        != loaded_start.directory_identity_sha256
        or reloaded_start.declaration != loaded_start.declaration
        or reloaded_start.authorization != loaded_start.authorization
        or reloaded_start.claim != loaded_start.claim
        or reloaded_start.start != loaded_start.start
        or reloaded_start.launch_authority_source_envelope_binding
        != loaded_start.launch_authority_source_envelope_binding
        or reloaded_start.verification_evidence_binding
        != loaded_start.verification_evidence_binding
        or dict(reloaded_start.immutable_member_sources)
        != dict(loaded_start.immutable_member_sources)
    ):
        raise QualificationContractError(
            "authoritative-start transaction changed before callback entry"
        )

    target = verified.snapshot.replay_target
    ownership: runner._D7PostStartOwnership | None = None
    try:
        ownership = runner._D7PostStartOwnership(
            loaded_start.declaration,
            loaded_start.authorization,
            loaded_start.claim,
            loaded_start.start,
            full_inventory_sha256=target.full_design_binding.inventory_sha256,
            aggregation_sha256=target.aggregation_binding.canonical_sha256,
            result_schema_sha256=(
                target.result_payload_schema_binding.canonical_sha256
            ),
            authoritative_start_manifest_sha256=(
                loaded_start.manifest.canonical_sha256
            ),
            authoritative_start_directory_identity_sha256=(
                loaded_start.directory_identity_sha256
            ),
            requires_authoritative_start=True,
            _factory_token=runner._POST_START_OWNERSHIP_FACTORY_TOKEN,
        )
        try:
            prepared = runner.prepare_d7_post_start_terminal(
                ownership,
                scientific_producer,
            )
        except Exception as error:
            _persist_failed_terminal_from_exception(loaded_start, ownership, error)
            raise
        return terminal_operations.persist_d7_prepared_terminal_no_replace(
            loaded_start,
            prepared,
        )
    finally:
        if ownership is not None:
            ownership._invalidate_all()
