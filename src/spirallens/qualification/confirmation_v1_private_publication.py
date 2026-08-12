"""Private-stage, no-replace repository publication for the D7 v1 successor.

Importing this module performs no I/O.  The one high-level operation accepts
the closed nine-record byte set and, only for the closed orchestration owner, a
publisher-sealed held-descriptor capability.  It derives every path from the
frozen v1 protocol, owns its stage from creation through publication, and never
invokes a supplier, model, subject, result producer, or official runner.

Once a stage directory has been created, every failure is retained in place.
There is deliberately no cleanup, resume, retry, overwrite, or portable rename
fallback.  Success proves one native namespace-atomic publication plus the
completed fsync calls recorded by the returned in-memory receipt; it grants no
execution or scientific authority.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
import ctypes
from dataclasses import dataclass
import errno
import os
from pathlib import Path, PurePosixPath
import stat
import sys
from types import MappingProxyType

from spirallens._repository_context import RepositoryContext
from spirallens.core.canonical import sha256_bytes

from .common import QualificationContractError, require_sha256
from . import confirmation_v1_materialization as verification
from . import confirmation_v1_records as records

__all__: tuple[str, ...] = ()


_MODULE_PATH = "src/spirallens/qualification/confirmation_v1_private_publication.py"
_STAGE_MARKER = ".private-stage."
_NativeRename = Callable[[int, str, str], None]
_StatIdentity = tuple[int, int, int]
_ANCHORED_EXTERNAL_FACTORY_TOKEN = object()


class D7V1PrivatePublicationFailure(QualificationContractError):
    """Typed, non-retryable state after a refused or incomplete publication."""

    __slots__ = (
        "cleanup_authorized",
        "destination",
        "disposition",
        "publication_visible",
        "retry_authorized",
        "stage_path",
        "stage_retained",
    )

    def __init__(
        self,
        message: str,
        *,
        disposition: str,
        destination: Path,
        stage_path: Path | None,
        stage_retained: bool | None,
        publication_visible: bool | None,
    ) -> None:
        super().__init__(f"{disposition}: {message}")
        self.disposition = disposition
        self.destination = destination
        self.stage_path = stage_path
        self.stage_retained = stage_retained
        self.publication_visible = publication_visible
        self.retry_authorized = False
        self.cleanup_authorized = False


@dataclass(frozen=True, slots=True)
class D7V1PrivatePublicationReceipt:
    """In-memory facts from one completed repository namespace publication."""

    destination: Path
    source_commit: str
    receipt_sha256: str
    member_sha256_by_role: tuple[tuple[str, str], ...]
    native_primitive: str
    namespace_atomic: bool = True
    member_fsync_completed: bool = True
    directory_fsync_completed: bool = True
    parent_directory_fsync_completed: bool = True
    structural_only: bool = True
    retry_authorized: bool = False
    cleanup_authorized: bool = False
    authority_granted: bool = False
    materialization_authorized: bool = False
    artifact_commit_a_verified: bool = False
    execution_authorized: bool = False
    scientific_claim_eligible: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.destination, Path) or not self.destination.is_absolute():
            raise TypeError("destination must be an absolute Path")
        verification._full_commit(self.source_commit, label="source_commit")
        require_sha256(self.receipt_sha256, label="receipt_sha256")
        if not self.member_sha256_by_role or any(
            type(item) is not tuple or len(item) != 2
            for item in self.member_sha256_by_role
        ):
            raise QualificationContractError(
                "member_sha256_by_role must contain two-field tuples"
            )
        for role, digest in self.member_sha256_by_role:
            if type(role) is not str or not role:
                raise QualificationContractError("publication member role is invalid")
            require_sha256(digest, label=f"{role} sha256")
        if self.member_sha256_by_role != tuple(sorted(self.member_sha256_by_role)) or {
            role for role, _digest in self.member_sha256_by_role
        } != set(verification._ROLE_CLASSES):
            raise QualificationContractError(
                "member_sha256_by_role must be the sorted exact nine roles"
            )
        if type(self.native_primitive) is not str or not self.native_primitive:
            raise QualificationContractError("native_primitive must be nonempty")
        if (
            self.namespace_atomic is not True
            or self.member_fsync_completed is not True
            or self.directory_fsync_completed is not True
            or self.parent_directory_fsync_completed is not True
            or self.structural_only is not True
            or self.retry_authorized is not False
            or self.cleanup_authorized is not False
            or self.authority_granted is not False
            or self.materialization_authorized is not False
            or self.artifact_commit_a_verified is not False
            or self.execution_authorized is not False
            or self.scientific_claim_eligible is not False
        ):
            raise QualificationContractError(
                "publication receipt facts must retain their closed boundary"
            )


@dataclass(frozen=True, slots=True)
class _D7V1AnchoredExternalEvidence:
    """Sealed held-descriptor evidence for the frozen external two-file tree."""

    parent_fd: int
    root_fd: int
    store_path: Path
    root_stat: tuple[int, int, int]
    source_by_path: Mapping[Path, bytes]
    directory_fd_by_path: Mapping[Path, int]
    directory_identity_by_path: Mapping[Path, _StatIdentity]
    directory_stat_by_path: Mapping[Path, tuple[int, int, int]]
    file_fd_by_path: Mapping[Path, int]
    file_identity_by_path: Mapping[Path, _StatIdentity]
    file_stat_by_path: Mapping[Path, tuple[int, int]]
    _factory_token: object

    def __post_init__(self) -> None:
        if self._factory_token is not _ANCHORED_EXTERNAL_FACTORY_TOKEN:
            raise QualificationContractError(
                "anchored external evidence must be factory-produced"
            )
        if type(self.parent_fd) is not int or type(self.root_fd) is not int:
            raise TypeError("anchored external descriptors must be plain integers")
        if not isinstance(self.store_path, Path) or not self.store_path.is_absolute():
            raise TypeError("anchored external store_path must be absolute")
        sources = dict(self.source_by_path)
        directory_descriptors = dict(self.directory_fd_by_path)
        directory_identities = dict(self.directory_identity_by_path)
        directory_snapshots = dict(self.directory_stat_by_path)
        descriptors = dict(self.file_fd_by_path)
        identities = dict(self.file_identity_by_path)
        snapshots = dict(self.file_stat_by_path)
        if (
            not sources
            or set(sources) != set(descriptors)
            or set(sources) != set(identities)
            or set(sources) != set(snapshots)
            or not directory_descriptors
            or set(directory_descriptors) != set(directory_identities)
            or set(directory_descriptors) != set(directory_snapshots)
            or any(
                not isinstance(path, Path)
                or not path.is_absolute()
                or type(source) is not bytes
                or not source
                or type(descriptors[path]) is not int
                for path, source in sources.items()
            )
        ):
            raise QualificationContractError(
                "anchored external evidence path set is not closed"
            )
        object.__setattr__(self, "source_by_path", MappingProxyType(sources))
        object.__setattr__(
            self,
            "directory_fd_by_path",
            MappingProxyType(directory_descriptors),
        )
        object.__setattr__(
            self,
            "directory_identity_by_path",
            MappingProxyType(directory_identities),
        )
        object.__setattr__(
            self,
            "directory_stat_by_path",
            MappingProxyType(directory_snapshots),
        )
        object.__setattr__(self, "file_fd_by_path", MappingProxyType(descriptors))
        object.__setattr__(self, "file_identity_by_path", MappingProxyType(identities))
        object.__setattr__(self, "file_stat_by_path", MappingProxyType(snapshots))

    def _open_live_parent(self) -> int:
        flags = _directory_open_flags()
        descriptor = os.open("/", flags)
        try:
            for part in self.store_path.parent.parts[1:]:
                leaf = _leaf(part, label="external store parent component")
                child = os.open(leaf, flags, dir_fd=descriptor)
                os.close(descriptor)
                descriptor = child
            return descriptor
        except BaseException:
            _close_quietly(descriptor)
            raise

    def _require_live_store(self) -> None:
        live_parent_fd = self._open_live_parent()
        try:
            if _stat_identity(os.fstat(live_parent_fd)) != _stat_identity(
                os.fstat(self.parent_fd)
            ):
                raise QualificationContractError(
                    "live external parent differs from anchored evidence"
                )
            store_entry = os.stat(
                self.store_path.name,
                dir_fd=live_parent_fd,
                follow_symlinks=False,
            )
            if _stat_identity(store_entry) != _stat_identity(os.fstat(self.root_fd)):
                raise QualificationContractError(
                    "live external store differs from anchored evidence"
                )
            root_stat = os.fstat(self.root_fd)
            if (
                not stat.S_ISDIR(root_stat.st_mode)
                or (
                    stat.S_IMODE(root_stat.st_mode),
                    root_stat.st_nlink,
                    root_stat.st_mtime_ns,
                )
                != self.root_stat
            ):
                raise QualificationContractError(
                    "anchored external store root mode differs"
                )
            expected_directories = {
                path.relative_to(self.store_path).parts[0]
                for path in self.source_by_path
            }
            expected_directory_paths = {
                self.store_path / directory for directory in expected_directories
            }
            if set(self.directory_fd_by_path) != expected_directory_paths:
                raise QualificationContractError(
                    "anchored external directory descriptor set differs"
                )
            if set(os.listdir(self.root_fd)) != expected_directories:
                raise QualificationContractError(
                    "anchored external store root entries differ"
                )
            for path in self.source_by_path:
                relative = path.relative_to(self.store_path)
                if len(relative.parts) != 2:
                    raise QualificationContractError(
                        "anchored external evidence path depth differs"
                    )
                directory_leaf, file_leaf = relative.parts
                directory_fd = os.open(
                    directory_leaf,
                    _directory_open_flags(),
                    dir_fd=self.root_fd,
                )
                try:
                    directory_stat = os.fstat(directory_fd)
                    held_directory_fd = self.directory_fd_by_path[
                        self.store_path / directory_leaf
                    ]
                    held_directory_stat = os.fstat(held_directory_fd)
                    if (
                        stat.S_IMODE(directory_stat.st_mode) != 0o700
                        or _stat_identity(directory_stat)
                        != self.directory_identity_by_path[
                            self.store_path / directory_leaf
                        ]
                        or _stat_identity(held_directory_stat)
                        != self.directory_identity_by_path[
                            self.store_path / directory_leaf
                        ]
                        or (
                            stat.S_IMODE(directory_stat.st_mode),
                            directory_stat.st_nlink,
                            directory_stat.st_mtime_ns,
                        )
                        != self.directory_stat_by_path[self.store_path / directory_leaf]
                        or (
                            stat.S_IMODE(held_directory_stat.st_mode),
                            held_directory_stat.st_nlink,
                            held_directory_stat.st_mtime_ns,
                        )
                        != self.directory_stat_by_path[self.store_path / directory_leaf]
                        or set(os.listdir(directory_fd)) != {file_leaf}
                    ):
                        raise QualificationContractError(
                            "anchored external evidence directory differs"
                        )
                    leaf_stat = os.stat(
                        file_leaf,
                        dir_fd=directory_fd,
                        follow_symlinks=False,
                    )
                    descriptor_stat = os.fstat(self.file_fd_by_path[path])
                    if (
                        _stat_identity(leaf_stat) != self.file_identity_by_path[path]
                        or _stat_identity(descriptor_stat)
                        != self.file_identity_by_path[path]
                        or not stat.S_ISREG(leaf_stat.st_mode)
                        or stat.S_IMODE(leaf_stat.st_mode) != 0o600
                        or leaf_stat.st_nlink != 1
                        or (leaf_stat.st_size, leaf_stat.st_mtime_ns)
                        != self.file_stat_by_path[path]
                        or (descriptor_stat.st_size, descriptor_stat.st_mtime_ns)
                        != self.file_stat_by_path[path]
                    ):
                        raise QualificationContractError(
                            "live external evidence file differs from held descriptor"
                        )
                finally:
                    _close_quietly(directory_fd)
        finally:
            _close_quietly(live_parent_fd)

    def read(self, path: Path, maximum_bytes: int) -> bytes:
        if type(maximum_bytes) is not int or maximum_bytes < 1:
            raise QualificationContractError(
                "anchored external evidence byte cap is invalid"
            )
        try:
            expected = self.source_by_path[path]
            descriptor = self.file_fd_by_path[path]
            identity = self.file_identity_by_path[path]
        except KeyError as error:
            raise QualificationContractError(
                "anchored external evidence received an undeclared path"
            ) from error
        self._require_live_store()
        observed = os.fstat(descriptor)
        if _stat_identity(observed) != identity:
            raise QualificationContractError(
                "anchored external evidence file identity differs"
            )
        source = _read_file_descriptor(
            descriptor,
            maximum_bytes=maximum_bytes,
        )
        if source != expected:
            raise QualificationContractError(
                "anchored external evidence file bytes differ"
            )
        self._require_live_store()
        return source


def _build_d7_v1_anchored_external_evidence(
    repository: RepositoryContext,
    *,
    parent_fd: int,
    root_fd: int,
    directory_fd_by_path: Mapping[Path, int],
    file_fd_by_path: Mapping[Path, int],
    source_by_path: Mapping[Path, bytes],
) -> _D7V1AnchoredExternalEvidence:
    """Seal exact frozen external paths and already-owned file descriptors."""

    if not isinstance(repository, RepositoryContext):
        raise TypeError("repository must be RepositoryContext")
    protocol = verification._load_d7_v1_materialization_protocol(repository)
    claim_path, attempt_path = verification._expected_external_paths(protocol)
    _route_source, route = verification._route_source(repository, protocol)
    store_path, _staging, _runner, _callable = verification._expected_route_coordinates(
        route
    )
    expected_paths = {claim_path, attempt_path}
    sources = dict(source_by_path)
    directory_descriptors = dict(directory_fd_by_path)
    descriptors = dict(file_fd_by_path)
    if set(sources) != expected_paths or set(descriptors) != expected_paths:
        raise QualificationContractError(
            "anchored external evidence differs from exact frozen paths"
        )
    expected_directory_paths = {path.parent for path in expected_paths}
    if set(directory_descriptors) != expected_directory_paths:
        raise QualificationContractError(
            "anchored external directory descriptors differ from frozen paths"
        )
    directory_identities = {
        path: _stat_identity(os.fstat(descriptor))
        for path, descriptor in directory_descriptors.items()
    }
    directory_observed = {
        path: os.fstat(descriptor) for path, descriptor in directory_descriptors.items()
    }
    directory_snapshots = {
        path: (stat.S_IMODE(value.st_mode), value.st_nlink, value.st_mtime_ns)
        for path, value in directory_observed.items()
    }
    root_observed = os.fstat(root_fd)
    observed = {path: os.fstat(descriptors[path]) for path in expected_paths}
    identities = {path: _stat_identity(value) for path, value in observed.items()}
    snapshots = {
        path: (value.st_size, value.st_mtime_ns) for path, value in observed.items()
    }
    result = _D7V1AnchoredExternalEvidence(
        parent_fd=parent_fd,
        root_fd=root_fd,
        store_path=store_path,
        root_stat=(
            stat.S_IMODE(root_observed.st_mode),
            root_observed.st_nlink,
            root_observed.st_mtime_ns,
        ),
        source_by_path=sources,
        directory_fd_by_path=directory_descriptors,
        directory_identity_by_path=directory_identities,
        directory_stat_by_path=directory_snapshots,
        file_fd_by_path=descriptors,
        file_identity_by_path=identities,
        file_stat_by_path=snapshots,
        _factory_token=_ANCHORED_EXTERNAL_FACTORY_TOKEN,
    )
    for path, source in sources.items():
        if result.read(path, records.D7_V1_DEFAULT_MAX_RECORD_BYTES) != source:
            raise QualificationContractError(
                "anchored external evidence factory reload differs"
            )
    return result


@dataclass(slots=True)
class _OwnedStage:
    parent_fd: int
    stage_fd: int
    stage_leaf: str
    destination_leaf: str
    directory_fds: dict[str, int]
    file_fds: dict[str, int]
    file_snapshots: dict[str, os.stat_result]

    def close(self) -> None:
        for descriptor in self.file_fds.values():
            _close_quietly(descriptor)
        for descriptor in reversed(tuple(self.directory_fds.values())):
            _close_quietly(descriptor)
        _close_quietly(self.parent_fd)
        self.file_fds.clear()
        self.directory_fds.clear()


def _close_quietly(descriptor: int) -> None:
    try:
        os.close(descriptor)
    except OSError:
        pass


def _directory_open_flags() -> int:
    required = ("O_DIRECTORY", "O_NOFOLLOW")
    if any(not hasattr(os, name) for name in required):
        raise QualificationContractError(
            "private publication requires O_DIRECTORY and O_NOFOLLOW"
        )
    return os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)


def _file_create_flags() -> int:
    if not hasattr(os, "O_NOFOLLOW"):
        raise QualificationContractError("private publication requires O_NOFOLLOW")
    return (
        os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)
    )


def _leaf(value: str, *, label: str) -> str:
    if (
        type(value) is not str
        or not value
        or value in {".", ".."}
        or "/" in value
        or "\0" in value
    ):
        raise QualificationContractError(f"{label} must be one safe path leaf")
    return value


def _stat_identity(value: os.stat_result) -> _StatIdentity:
    return (value.st_dev, value.st_ino, stat.S_IFMT(value.st_mode))


def _entry_stat(parent_fd: int, leaf: str) -> os.stat_result | None:
    try:
        return os.stat(leaf, dir_fd=parent_fd, follow_symlinks=False)
    except FileNotFoundError:
        return None


def _open_publication_parent(
    repository: RepositoryContext,
    parent_parts: tuple[str, ...],
) -> int:
    flags = _directory_open_flags()
    try:
        descriptor = os.open(repository.root, flags)
    except OSError as error:
        raise QualificationContractError(
            f"cannot anchor repository root: {error}"
        ) from error
    try:
        for part in parent_parts:
            leaf = _leaf(part, label="publication parent component")
            try:
                child = os.open(leaf, flags, dir_fd=descriptor)
            except OSError as error:
                raise QualificationContractError(
                    f"cannot anchor publication parent {leaf}: {error}"
                ) from error
            os.close(descriptor)
            descriptor = child
        return descriptor
    except BaseException:
        _close_quietly(descriptor)
        raise


def _require_live_parent_anchor(
    repository: RepositoryContext,
    parent_parts: tuple[str, ...],
    anchored_parent_fd: int,
) -> None:
    live_descriptor = _open_publication_parent(repository, parent_parts)
    try:
        if _stat_identity(os.fstat(live_descriptor)) != _stat_identity(
            os.fstat(anchored_parent_fd)
        ):
            raise QualificationContractError(
                "live publication parent differs from its anchored directory"
            )
    finally:
        _close_quietly(live_descriptor)


def _native_exclusive_rename() -> tuple[str, _NativeRename]:
    libc = ctypes.CDLL(None, use_errno=True)
    if sys.platform == "darwin":
        try:
            function = libc.renameatx_np
        except AttributeError as error:
            raise QualificationContractError(
                "Darwin renameatx_np is unavailable"
            ) from error
        function.argtypes = (
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_uint,
        )
        function.restype = ctypes.c_int
        flag = 0x00000004  # RENAME_EXCL
        primitive = "darwin.renameatx_np.RENAME_EXCL"
    elif sys.platform.startswith("linux"):
        try:
            function = libc.renameat2
        except AttributeError as error:
            raise QualificationContractError(
                "Linux renameat2 is unavailable"
            ) from error
        function.argtypes = (
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_uint,
        )
        function.restype = ctypes.c_int
        flag = 0x00000001  # RENAME_NOREPLACE
        primitive = "linux.renameat2.RENAME_NOREPLACE"
    else:
        raise QualificationContractError(
            "no reviewed native exclusive directory rename for this platform"
        )

    def invoke(parent_fd: int, source_leaf: str, destination_leaf: str) -> None:
        ctypes.set_errno(0)
        result = function(
            parent_fd,
            os.fsencode(_leaf(source_leaf, label="source leaf")),
            parent_fd,
            os.fsencode(_leaf(destination_leaf, label="destination leaf")),
            flag,
        )
        if result != 0:
            observed_errno = ctypes.get_errno() or errno.EIO
            raise OSError(observed_errno, os.strerror(observed_errno))

    return primitive, invoke


def _publication_coordinates(
    repository: RepositoryContext,
    protocol: verification.D7V1MaterializationProtocol,
    receipt_sha256: str,
) -> tuple[tuple[str, ...], str, str, Path]:
    layout = verification._mapping(
        protocol.document.get("coordinate_and_member_layout"),
        label="coordinate_and_member_layout",
    )
    root_text = verification._relative_path(
        layout.get("repository_root"), label="repository_root"
    )
    root = PurePosixPath(root_text)
    if len(root.parts) < 2:
        raise QualificationContractError("repository_root must have a parent")
    destination_leaf = _leaf(root.name, label="destination leaf")
    stage_leaf = _leaf(
        f".{destination_leaf}{_STAGE_MARKER}{receipt_sha256}",
        label="private stage leaf",
    )
    destination = repository.root.joinpath(*root.parts)
    return tuple(root.parts[:-1]), destination_leaf, stage_leaf, destination


def _observe_d7_v1_pre_item23_publication(
    repository: RepositoryContext,
    *,
    receipt_sha256: str,
) -> str:
    """Observe only the frozen destination and reserved private-stage names."""

    if not isinstance(repository, RepositoryContext):
        raise TypeError("repository must be RepositoryContext")
    digest = require_sha256(receipt_sha256, label="receipt_sha256")
    protocol = verification._load_d7_v1_materialization_protocol(repository)
    parent_parts, destination_leaf, stage_leaf, _destination = _publication_coordinates(
        repository, protocol, digest
    )
    parent_fd = _open_publication_parent(repository, parent_parts)
    try:
        names = set(os.listdir(parent_fd))
        reserved_prefix = f".{destination_leaf}{_STAGE_MARKER}"
        stages = {name for name in names if name.startswith(reserved_prefix)}
        destination_present = destination_leaf in names
        exact_stage_present = stage_leaf in stages
        foreign_stage_present = bool(stages - {stage_leaf})
        if destination_present and stages:
            return "destination-and-private-stage-present"
        if destination_present:
            return "destination-present"
        if exact_stage_present and foreign_stage_present:
            return "multiple-private-stages-present"
        if exact_stage_present:
            return "exact-private-stage-present"
        if foreign_stage_present:
            return "foreign-private-stage-present"
        return "absent"
    finally:
        _close_quietly(parent_fd)


def _require_head_and_clean_status(
    repository: RepositoryContext,
    source_commit: str,
    *,
    allowed_untracked: set[str],
) -> None:
    head = (
        verification._git(repository, "rev-parse", "--verify", "HEAD^{commit}")
        .decode("ascii", errors="strict")
        .strip()
    )
    if head != source_commit:
        raise QualificationContractError("repository HEAD differs from source S")
    status_source = verification._git(
        repository,
        "status",
        "--porcelain=v1",
        "-z",
        "--untracked-files=all",
    )
    observed_untracked: set[str] = set()
    for item in (part for part in status_source.split(b"\0") if part):
        if len(item) < 4 or item[2:3] != b" ":
            raise QualificationContractError("malformed Git status entry")
        status_code = item[:2]
        try:
            path = item[3:].decode("utf-8", errors="strict")
        except UnicodeDecodeError as error:
            raise QualificationContractError("Git status path is not UTF-8") from error
        if status_code != b"??" or path not in allowed_untracked:
            raise QualificationContractError(
                f"repository has an unrelated live change: {path}"
            )
        observed_untracked.add(path)
    if observed_untracked != allowed_untracked:
        raise QualificationContractError(
            "private stage is not the exact allowed untracked file set"
        )


def _require_publisher_source_bound(
    repository: RepositoryContext,
    joined: verification.D7V1JoinedRecords,
) -> None:
    if not repository.matches_imported_file(
        imported_file=__file__, repository_path=_MODULE_PATH
    ):
        raise QualificationContractError(
            "private-publication module import origin differs from repository"
        )
    members = verification._source_members_from_c1(
        joined.record(records.D7V1C1SourceSetRecord.artifact_role)
    )
    by_path = {member.repository_path: member for member in members}
    if _MODULE_PATH not in by_path:
        raise QualificationContractError(
            "C1 source closure omits the private-publication module"
        )
    _mode, committed = verification._git_blob(
        repository,
        joined.source_commit,
        _MODULE_PATH,
        maximum_bytes=verification._MAX_SOURCE_MEMBER_BYTES,
    )
    live = verification._safe_read_file(
        repository.root / _MODULE_PATH,
        verification._MAX_SOURCE_MEMBER_BYTES,
        require_single_link=False,
    )
    member = by_path[_MODULE_PATH]
    if (
        live != committed
        or member.sha256 != sha256_bytes(committed)
        or member.byte_count != len(committed)
    ):
        raise QualificationContractError(
            "executing private-publication source differs from source S"
        )


def _path_parent(relative: str) -> tuple[str, str]:
    path = PurePosixPath(relative)
    parent = "" if str(path.parent) == "." else path.parent.as_posix()
    return parent, _leaf(path.name, label="stage member leaf")


def _required_directories(paths: Mapping[str, str]) -> tuple[str, ...]:
    directories: set[str] = set()
    for relative in paths.values():
        parent = PurePosixPath(relative).parent
        while str(parent) != ".":
            directories.add(parent.as_posix())
            parent = parent.parent
    return tuple(sorted(directories, key=lambda value: (value.count("/"), value)))


def _write_all(descriptor: int, source: bytes) -> None:
    view = memoryview(source)
    written = 0
    while written < len(view):
        count = os.write(descriptor, view[written:])
        if count <= 0:
            raise OSError(errno.EIO, "zero-length write")
        written += count


def _read_file_descriptor(
    descriptor: int,
    *,
    maximum_bytes: int,
) -> bytes:
    observed = os.fstat(descriptor)
    if (
        not stat.S_ISREG(observed.st_mode)
        or observed.st_nlink != 1
        or observed.st_size < 1
        or observed.st_size > maximum_bytes
    ):
        raise QualificationContractError("owned stage file violates its byte cap")
    os.lseek(descriptor, 0, os.SEEK_SET)
    chunks: list[bytes] = []
    remaining = maximum_bytes + 1
    while remaining:
        chunk = os.read(descriptor, min(remaining, 1024 * 1024))
        if not chunk:
            break
        chunks.append(chunk)
        remaining -= len(chunk)
    source = b"".join(chunks)
    if len(source) != observed.st_size or len(source) > maximum_bytes:
        raise QualificationContractError("owned stage file changed while read")
    return source


def _create_owned_stage(
    parent_fd: int,
    *,
    stage_leaf: str,
    destination_leaf: str,
    paths_by_role: Mapping[str, str],
    sources_by_role: Mapping[str, bytes],
) -> _OwnedStage:
    os.mkdir(stage_leaf, 0o700, dir_fd=parent_fd)
    stage_fd = -1
    directory_fds: dict[str, int] = {}
    file_fds: dict[str, int] = {}
    try:
        stage_fd = os.open(stage_leaf, _directory_open_flags(), dir_fd=parent_fd)
        os.fchmod(stage_fd, 0o700)
        stage_entry = os.stat(stage_leaf, dir_fd=parent_fd, follow_symlinks=False)
        if _stat_identity(stage_entry) != _stat_identity(os.fstat(stage_fd)):
            raise QualificationContractError("private stage anchor identity differs")
        directory_fds[""] = stage_fd
        os.fsync(parent_fd)

        for relative in _required_directories(paths_by_role):
            parent, leaf = _path_parent(relative)
            parent_descriptor = directory_fds[parent]
            os.mkdir(leaf, 0o700, dir_fd=parent_descriptor)
            descriptor = os.open(
                leaf, _directory_open_flags(), dir_fd=parent_descriptor
            )
            os.fchmod(descriptor, 0o700)
            directory_fds[relative] = descriptor

        receipt_role = records.D7V1PreItem23ChronologyReceipt.artifact_role
        ordered_roles = tuple(
            sorted(role for role in paths_by_role if role != receipt_role)
        ) + (receipt_role,)
        snapshots: dict[str, os.stat_result] = {}
        for role in ordered_roles:
            relative = paths_by_role[role]
            parent, leaf = _path_parent(relative)
            descriptor = os.open(
                leaf,
                _file_create_flags(),
                0o600,
                dir_fd=directory_fds[parent],
            )
            file_fds[relative] = descriptor
            os.fchmod(descriptor, 0o600)
            _write_all(descriptor, sources_by_role[role])
            os.fsync(descriptor)
            snapshots[relative] = os.fstat(descriptor)

        for relative in sorted(
            directory_fds, key=lambda value: (value.count("/"), value), reverse=True
        ):
            os.fsync(directory_fds[relative])
        return _OwnedStage(
            parent_fd=parent_fd,
            stage_fd=stage_fd,
            stage_leaf=stage_leaf,
            destination_leaf=destination_leaf,
            directory_fds=directory_fds,
            file_fds=file_fds,
            file_snapshots=snapshots,
        )
    except BaseException:
        for descriptor in file_fds.values():
            _close_quietly(descriptor)
        for descriptor in reversed(tuple(directory_fds.values())):
            _close_quietly(descriptor)
        if stage_fd >= 0 and stage_fd not in directory_fds.values():
            _close_quietly(stage_fd)
        raise


def _expected_children(paths_by_role: Mapping[str, str]) -> dict[str, set[str]]:
    result = {
        relative: set() for relative in ("", *_required_directories(paths_by_role))
    }
    for relative in tuple(result):
        if not relative:
            continue
        parent, leaf = _path_parent(relative)
        result[parent].add(leaf)
    for relative in paths_by_role.values():
        parent, leaf = _path_parent(relative)
        result[parent].add(leaf)
    return result


def _revalidate_owned_stage(
    stage: _OwnedStage,
    *,
    paths_by_role: Mapping[str, str],
    sources_by_role: Mapping[str, bytes],
    published: bool,
) -> dict[str, bytes]:
    children = _expected_children(paths_by_role)
    directory_paths = set(stage.directory_fds)
    file_paths = set(stage.file_fds)
    if directory_paths != set(children) or file_paths != set(paths_by_role.values()):
        raise QualificationContractError("owned stage handle set is not closed")

    for relative, descriptor in stage.directory_fds.items():
        directory_stat = os.fstat(descriptor)
        if (
            not stat.S_ISDIR(directory_stat.st_mode)
            or stat.S_IMODE(directory_stat.st_mode) != 0o700
        ):
            raise QualificationContractError(
                f"owned stage directory mode changed: {relative or '.'}"
            )
        observed_names = set(os.listdir(descriptor))
        if observed_names != children[relative]:
            raise QualificationContractError(
                f"owned stage directory entries changed: {relative or '.'}"
            )
        for name in observed_names:
            child_path = name if not relative else f"{relative}/{name}"
            child_fd = (
                stage.directory_fds[child_path]
                if child_path in stage.directory_fds
                else stage.file_fds[child_path]
            )
            entry = os.stat(name, dir_fd=descriptor, follow_symlinks=False)
            if _stat_identity(entry) != _stat_identity(os.fstat(child_fd)):
                raise QualificationContractError(
                    f"owned stage entry identity changed: {child_path}"
                )

    sources: dict[str, bytes] = {}
    for role, relative in paths_by_role.items():
        descriptor = stage.file_fds[relative]
        before = stage.file_snapshots[relative]
        now = os.fstat(descriptor)
        if (
            _stat_identity(now) != _stat_identity(before)
            or stat.S_IMODE(now.st_mode) != 0o600
            or now.st_nlink != before.st_nlink
            or now.st_size != before.st_size
            or now.st_mtime_ns != before.st_mtime_ns
        ):
            raise QualificationContractError(
                f"owned stage member stat changed: {relative}"
            )
        source = _read_file_descriptor(
            descriptor,
            maximum_bytes=verification._ROLE_CLASSES[role].max_record_bytes,
        )
        if source != sources_by_role[role]:
            raise QualificationContractError(
                f"owned stage member bytes changed: {relative}"
            )
        sources[role] = source

    stage_entry = _entry_stat(stage.parent_fd, stage.stage_leaf)
    destination_entry = _entry_stat(stage.parent_fd, stage.destination_leaf)
    expected_identity = _stat_identity(os.fstat(stage.stage_fd))
    reserved_prefix = f".{stage.destination_leaf}{_STAGE_MARKER}"
    observed_stages = {
        name for name in os.listdir(stage.parent_fd) if name.startswith(reserved_prefix)
    }
    if published:
        if (
            stage_entry is not None
            or destination_entry is None
            or _stat_identity(destination_entry) != expected_identity
            or observed_stages
        ):
            raise QualificationContractError(
                "published namespace does not contain the exact owned directory"
            )
    elif (
        stage_entry is None
        or _stat_identity(stage_entry) != expected_identity
        or destination_entry is not None
        or observed_stages != {stage.stage_leaf}
    ):
        if destination_entry is not None:
            raise FileExistsError(errno.EEXIST, "publication destination exists")
        raise QualificationContractError("private stage namespace entry changed")
    return sources


def _rename_outcome(stage: _OwnedStage) -> str:
    expected = _stat_identity(os.fstat(stage.stage_fd))
    stage_entry = _entry_stat(stage.parent_fd, stage.stage_leaf)
    destination_entry = _entry_stat(stage.parent_fd, stage.destination_leaf)
    stage_matches = stage_entry is not None and _stat_identity(stage_entry) == expected
    destination_matches = (
        destination_entry is not None and _stat_identity(destination_entry) == expected
    )
    if stage_entry is None and destination_matches:
        return "published"
    if stage_matches and destination_entry is None:
        return "stage-retained"
    if stage_matches and destination_entry is not None and not destination_matches:
        return "destination-collision"
    return "ambiguous"


def _member_digests(
    sources_by_role: Mapping[str, bytes],
) -> tuple[tuple[str, str], ...]:
    return tuple(
        sorted((role, sha256_bytes(source)) for role, source in sources_by_role.items())
    )


def _publish_d7_v1_pre_item23_records_no_replace(
    repository: RepositoryContext,
    sources_by_role: Mapping[str, bytes],
    *,
    expected_receipt_sha256: str,
    _anchored_external_evidence: _D7V1AnchoredExternalEvidence | None = None,
) -> D7V1PrivatePublicationReceipt:
    """Own, validate, and exclusively publish the exact nine-record v1 tree.

    This function has no caller-controlled stage or destination.  The private
    sealed ``_anchored_external_evidence`` capability lets the closed
    orchestration owner retain and reauthenticate its already-promoted external
    file descriptors through this publisher's repeated joined gates; ordinary
    callers use the default frozen-coordinate reader.  No arbitrary reader is
    accepted.  Any failure after the private stage is created leaves that stage
    in place and rejects retry and cleanup for the same identity.
    """

    if not isinstance(repository, RepositoryContext):
        raise TypeError("repository must be RepositoryContext")
    receipt_sha256 = require_sha256(
        expected_receipt_sha256, label="expected_receipt_sha256"
    )
    try:
        frozen_sources = dict(sources_by_role)
    except (TypeError, ValueError) as error:
        raise TypeError("sources_by_role must be a mapping") from error
    if set(frozen_sources) != set(verification._ROLE_CLASSES) or any(
        type(role) is not str or type(source) is not bytes or not source
        for role, source in frozen_sources.items()
    ):
        raise QualificationContractError(
            "sources_by_role must contain the exact nine nonempty byte records"
        )
    frozen_sources = dict(MappingProxyType(frozen_sources))

    protocol = verification._load_d7_v1_materialization_protocol(repository)
    if (
        _anchored_external_evidence is not None
        and type(_anchored_external_evidence) is not _D7V1AnchoredExternalEvidence
    ):
        raise TypeError("_anchored_external_evidence must be sealed publisher evidence")
    if _anchored_external_evidence is not None:
        claim_path, attempt_path = verification._expected_external_paths(protocol)
        _route_source, route = verification._route_source(repository, protocol)
        store_path, _staging, _runner, _callable = (
            verification._expected_route_coordinates(route)
        )
        if _anchored_external_evidence.store_path != store_path or set(
            _anchored_external_evidence.source_by_path
        ) != {claim_path, attempt_path}:
            raise QualificationContractError(
                "anchored external evidence differs from publisher protocol"
            )
        for path, expected_source in _anchored_external_evidence.source_by_path.items():
            if (
                _anchored_external_evidence.read(
                    path, records.D7_V1_DEFAULT_MAX_RECORD_BYTES
                )
                != expected_source
            ):
                raise QualificationContractError(
                    "initial anchored external evidence reload differs"
                )
    external_reader: verification._ExternalReader = (
        verification._default_external_reader
        if _anchored_external_evidence is None
        else _anchored_external_evidence.read
    )
    parent_parts, destination_leaf, stage_leaf, destination = _publication_coordinates(
        repository, protocol, receipt_sha256
    )
    stage_path = destination.parent / stage_leaf
    stage_created = False
    publication_visible = False
    parent_fsync_completed = False
    parent_fd = -1
    owned: _OwnedStage | None = None

    try:
        verification._require_complete_git_history(repository)
        primitive, native_rename = _native_exclusive_rename()
        joined = verification._load_joined_sources(
            repository,
            protocol,
            frozen_sources,
            expected_receipt_sha256=receipt_sha256,
            stage_root=None,
            external_reader=external_reader,
        )
        _require_publisher_source_bound(repository, joined)

        paths_by_role = verification._expected_stage_files(protocol)
        parent_fd = _open_publication_parent(repository, parent_parts)
        names = set(os.listdir(parent_fd))
        reserved_prefix = f".{destination_leaf}{_STAGE_MARKER}"
        if destination_leaf in names:
            raise D7V1PrivatePublicationFailure(
                "publication destination already exists",
                disposition="destination_collision",
                destination=destination,
                stage_path=None,
                stage_retained=None,
                publication_visible=None,
            )
        partials = sorted(name for name in names if name.startswith(reserved_prefix))
        if partials:
            raise D7V1PrivatePublicationFailure(
                f"private stage namespace already contains {partials}",
                disposition="stage_collision",
                destination=destination,
                stage_path=None,
                stage_retained=None,
                publication_visible=None,
            )
        _require_head_and_clean_status(
            repository, joined.source_commit, allowed_untracked=set()
        )

        # Prove the publication parent accepts directory fsync before creating
        # the non-retryable private-stage namespace entry.
        os.fsync(parent_fd)

        try:
            owned = _create_owned_stage(
                parent_fd,
                stage_leaf=stage_leaf,
                destination_leaf=destination_leaf,
                paths_by_role=paths_by_role,
                sources_by_role=frozen_sources,
            )
            stage_created = True
            parent_fd = -1  # ownership transferred to _OwnedStage
        except FileExistsError as error:
            raise D7V1PrivatePublicationFailure(
                str(error),
                disposition="stage_collision_state_unknown",
                destination=destination,
                stage_path=None,
                stage_retained=None,
                publication_visible=None,
            ) from error
        except BaseException as stage_error:
            try:
                stage_created = _entry_stat(parent_fd, stage_leaf) is not None
            except BaseException as observation_error:
                raise D7V1PrivatePublicationFailure(
                    f"stage creation failed and namespace observation failed: "
                    f"{observation_error}",
                    disposition="stage_creation_state_unknown",
                    destination=destination,
                    stage_path=None,
                    stage_retained=None,
                    publication_visible=None,
                ) from stage_error
            raise

        staged_sources = _revalidate_owned_stage(
            owned,
            paths_by_role=paths_by_role,
            sources_by_role=frozen_sources,
            published=False,
        )
        staged_join = verification._load_joined_sources(
            repository,
            protocol,
            staged_sources,
            expected_receipt_sha256=receipt_sha256,
            stage_root=stage_path,
            external_reader=external_reader,
        )
        if staged_join.source_commit != joined.source_commit:
            raise QualificationContractError(
                "private stage source commit changed after construction"
            )
        expected_untracked = {
            (PurePosixPath(*parent_parts) / stage_leaf / relative).as_posix()
            for relative in paths_by_role.values()
        }
        _require_head_and_clean_status(
            repository,
            joined.source_commit,
            allowed_untracked=expected_untracked,
        )
        final_sources = _revalidate_owned_stage(
            owned,
            paths_by_role=paths_by_role,
            sources_by_role=frozen_sources,
            published=False,
        )
        final_join = verification._load_joined_sources(
            repository,
            protocol,
            final_sources,
            expected_receipt_sha256=receipt_sha256,
            stage_root=stage_path,
            external_reader=external_reader,
        )
        if final_join.source_commit != joined.source_commit:
            raise QualificationContractError(
                "final private stage source commit changed"
            )
        if (
            _revalidate_owned_stage(
                owned,
                paths_by_role=paths_by_role,
                sources_by_role=frozen_sources,
                published=False,
            )
            != final_sources
        ):
            raise QualificationContractError(
                "private stage changed after the final joined-loader gate"
            )
        _require_live_parent_anchor(repository, parent_parts, owned.parent_fd)
        rename_error: OSError | None = None
        try:
            native_rename(owned.parent_fd, stage_leaf, destination_leaf)
        except OSError as error:
            rename_error = error
        outcome = _rename_outcome(owned)
        if outcome == "destination-collision":
            detail = str(rename_error) if rename_error is not None else "collision"
            raise D7V1PrivatePublicationFailure(
                detail,
                disposition="destination_collision_stage_retained",
                destination=destination,
                stage_path=stage_path,
                stage_retained=True,
                publication_visible=False,
            ) from rename_error
        if outcome == "stage-retained":
            if rename_error is None:
                raise D7V1PrivatePublicationFailure(
                    "native rename returned without moving the private stage",
                    disposition="rename_outcome_ambiguous",
                    destination=destination,
                    stage_path=stage_path,
                    stage_retained=True,
                    publication_visible=None,
                )
            if rename_error.errno in {errno.EEXIST, errno.ENOTEMPTY}:
                raise D7V1PrivatePublicationFailure(
                    str(rename_error),
                    disposition="destination_collision_stage_retained",
                    destination=destination,
                    stage_path=stage_path,
                    stage_retained=True,
                    publication_visible=False,
                ) from rename_error
            raise rename_error
        if outcome != "published":
            raise D7V1PrivatePublicationFailure(
                str(rename_error or "native rename namespace is ambiguous"),
                disposition="rename_outcome_ambiguous",
                destination=destination,
                stage_path=None,
                stage_retained=None,
                publication_visible=None,
            ) from rename_error
        publication_visible = True
        os.fsync(owned.parent_fd)
        parent_fsync_completed = True
        _require_live_parent_anchor(repository, parent_parts, owned.parent_fd)
        published_sources = _revalidate_owned_stage(
            owned,
            paths_by_role=paths_by_role,
            sources_by_role=frozen_sources,
            published=True,
        )
        if published_sources != frozen_sources:
            raise QualificationContractError(
                "published held-file bytes differ from the validated source set"
            )
        published_join = verification._load_joined_sources(
            repository,
            protocol,
            published_sources,
            expected_receipt_sha256=receipt_sha256,
            stage_root=destination,
            external_reader=external_reader,
        )
        if published_join.source_commit != joined.source_commit:
            raise QualificationContractError(
                "published held-file joined loader changed source commit"
            )
        expected_published_untracked = {
            (PurePosixPath(*parent_parts) / destination_leaf / relative).as_posix()
            for relative in paths_by_role.values()
        }
        _require_head_and_clean_status(
            repository,
            joined.source_commit,
            allowed_untracked=expected_published_untracked,
        )
        if _anchored_external_evidence is not None:
            for (
                path,
                expected_source,
            ) in _anchored_external_evidence.source_by_path.items():
                if (
                    _anchored_external_evidence.read(
                        path, records.D7_V1_DEFAULT_MAX_RECORD_BYTES
                    )
                    != expected_source
                ):
                    raise QualificationContractError(
                        "final anchored external evidence reload differs"
                    )
        return D7V1PrivatePublicationReceipt(
            destination=destination,
            source_commit=joined.source_commit,
            receipt_sha256=receipt_sha256,
            member_sha256_by_role=_member_digests(frozen_sources),
            native_primitive=primitive,
        )
    except D7V1PrivatePublicationFailure:
        raise
    except BaseException as error:
        reauthenticated_outcome: str | None = None
        live_parent_reauthenticated = False
        reported_stage_path = stage_path if stage_created else None
        if owned is not None:
            try:
                reauthenticated_outcome = _rename_outcome(owned)
                _require_live_parent_anchor(repository, parent_parts, owned.parent_fd)
                live_parent_reauthenticated = True
            except BaseException:
                reauthenticated_outcome = None
                live_parent_reauthenticated = False

        if owned is not None and not live_parent_reauthenticated:
            disposition = "namespace_reauthentication_failed"
            retained: bool | None = None
            visible = None
            reported_stage_path = None
        elif reauthenticated_outcome == "published":
            disposition = (
                "published_verification_unknown"
                if parent_fsync_completed
                else "published_durability_unknown"
            )
            retained = False
            visible = True
            reported_stage_path = None
        elif reauthenticated_outcome == "stage-retained":
            disposition = "stage_partial_retained"
            retained = True
            visible = False
        elif reauthenticated_outcome == "destination-collision":
            disposition = "destination_collision_stage_retained"
            retained = True
            visible = None
        elif owned is not None:
            disposition = "rename_outcome_ambiguous"
            retained = None
            visible = None
            reported_stage_path = None
        elif publication_visible:
            disposition = (
                "published_verification_unknown"
                if parent_fsync_completed
                else "published_durability_unknown"
            )
            retained = None
            visible = None
            reported_stage_path = None
        elif stage_created:
            disposition = "stage_partial_retained"
            retained = True
            visible = False
        else:
            disposition = "preflight_rejected"
            retained = None
            visible = None
        raise D7V1PrivatePublicationFailure(
            str(error),
            disposition=disposition,
            destination=destination,
            stage_path=reported_stage_path,
            stage_retained=retained,
            publication_visible=visible,
        ) from error
    finally:
        if owned is not None:
            owned.close()
        elif parent_fd >= 0:
            _close_quietly(parent_fd)
