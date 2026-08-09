"""Private-stage, no-replace repository publication for the D7 v1 successor.

Importing this module performs no I/O.  The one high-level operation accepts
only the closed nine-record byte set, derives every path from the frozen v1
protocol, owns its stage from creation through publication, and never invokes a
supplier, model, subject, result producer, or official runner.

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
) -> D7V1PrivatePublicationReceipt:
    """Own, validate, and exclusively publish the exact nine-record v1 tree.

    This function has no caller-controlled stage or destination.  Any failure
    after the private stage is created leaves that stage in place and rejects
    retry and cleanup for the same identity.
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
            external_reader=verification._default_external_reader,
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
            external_reader=verification._default_external_reader,
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
            external_reader=verification._default_external_reader,
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
            external_reader=verification._default_external_reader,
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
