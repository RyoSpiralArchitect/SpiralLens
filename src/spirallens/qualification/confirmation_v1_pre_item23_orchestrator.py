"""Closed pre-item23 materialization owner for the D7 v1 successor.

The sole high-level operation accepts only a repository and asserted source
commit.  It reconstructs every record and coordinate from that Git tree and
the frozen v1 protocol.  In particular, callers cannot supply paths, bytes,
records, seeds, supplier functions, or persistence callbacks.

The operation owns the non-retryable chronology from the first external
staging-directory creation through the existing private repository publisher:
the exclusive seed claim is durable and reloaded before the fixed supplier is
entered exactly once; the separate pre-start attempt reservation is then made
durable; the exact two-file external tree is promoted without replacement and
reverified; and the chronology receipt is constructed last before the joined
hard gate and exact nine-file repository publication.

There is deliberately no cleanup, resume, retry, Git commit, result
derivation, official execution, model access, or subject access in this
module.  The raw ``source_commit`` argument is an operator assertion, not proof
that source was reviewed or selected.  This callable's presence, and the still
unwired preparation script, grant no invocation authority.  Importing the
module performs no I/O.
"""

from __future__ import annotations

from dataclasses import dataclass
import errno
import os
from pathlib import Path, PurePosixPath
import stat
from types import MappingProxyType
from typing import Mapping, NoReturn

from spirallens._repository_context import RepositoryContext
from spirallens.core.canonical import sha256_bytes

from .common import QualificationContractError
from . import confirmation_v1_deterministic_inputs as deterministic_inputs_module
from . import confirmation_v1_full_design_referents as referents_module
from . import confirmation_v1_materialization as verification
from . import confirmation_v1_private_publication as publication
from . import confirmation_v1_records as records
from . import confirmation_v1_source_closure as source_closure_module
from . import confirmation_v1_source_selected_supplier as supplier_module

__all__: tuple[str, ...] = ()


_MODULE_PATH = "src/spirallens/qualification/confirmation_v1_pre_item23_orchestrator.py"
_RECORD_IDS = MappingProxyType(
    {
        records.D7V1ExclusiveSeedSupplyClaim.artifact_role: (
            "d7-v1-exclusive-seed-supply-claim"
        ),
        records.D7V1OfficialSeedInventory.artifact_role: (
            "d7-v1-official-seed-inventory"
        ),
        records.D7V1ReplayTarget.artifact_role: "d7-v1-replay-target",
        records.D7V1FullDesignFreeze.artifact_role: "d7-v1-full-design-freeze",
        records.D7V1LaunchIntent.artifact_role: "d7-v1-launch-intent",
        records.D7V1OfficialExecutionAttemptReservation.artifact_role: (
            "d7-v1-official-execution-attempt-reservation"
        ),
        records.D7V1PreItem23ChronologyReceipt.artifact_role: (
            "d7-v1-pre-item23-chronology-receipt"
        ),
    }
)
_FULL_DESIGN_ID = "d7-v1-spectral-moment-official-full-design"
_EXTERNAL_FILE_ROLES = (
    records.D7V1ExclusiveSeedSupplyClaim.artifact_role,
    records.D7V1OfficialExecutionAttemptReservation.artifact_role,
)


class _D7V1ExternalChronologyFailure(QualificationContractError):
    """One non-retryable closed chronology failure disposition."""

    __slots__ = (
        "cleanup_authorized",
        "disposition",
        "external_stage",
        "external_store",
        "external_store_verified",
        "repository_destination",
        "repository_disposition",
        "repository_publication_visible",
        "repository_stage_path",
        "repository_stage_retained",
        "resume_authorized",
        "retry_authorized",
        "stage_retained",
        "store_visible",
    )

    def __init__(
        self,
        message: str,
        *,
        disposition: str,
        external_stage: Path,
        external_store: Path,
        stage_retained: bool | None,
        store_visible: bool | None,
        external_store_verified: bool | None = None,
        repository_disposition: str | None = None,
        repository_destination: Path | None = None,
        repository_stage_path: Path | None = None,
        repository_stage_retained: bool | None = None,
        repository_publication_visible: bool | None = None,
    ) -> None:
        super().__init__(f"{disposition}: {message}")
        self.disposition = disposition
        self.external_stage = external_stage
        self.external_store = external_store
        self.stage_retained = stage_retained
        self.store_visible = store_visible
        self.external_store_verified = external_store_verified
        self.repository_disposition = repository_disposition
        self.repository_destination = repository_destination
        self.repository_stage_path = repository_stage_path
        self.repository_stage_retained = repository_stage_retained
        self.repository_publication_visible = repository_publication_visible
        self.retry_authorized = False
        self.cleanup_authorized = False
        self.resume_authorized = False


@dataclass(frozen=True, slots=True)
class _ExternalCoordinates:
    staging: Path
    store: Path
    claim: Path
    attempt: Path
    parent: Path
    staging_leaf: str
    store_leaf: str
    relative_by_role: Mapping[str, str]

    def __post_init__(self) -> None:
        paths = (
            self.staging,
            self.store,
            self.claim,
            self.attempt,
            self.parent,
        )
        if any(not isinstance(path, Path) or not path.is_absolute() for path in paths):
            raise TypeError("external chronology paths must be absolute Paths")
        if self.staging.parent != self.parent or self.store.parent != self.parent:
            raise QualificationContractError(
                "external staging and store must share one parent"
            )
        if self.staging_leaf != self.staging.name or self.store_leaf != self.store.name:
            raise QualificationContractError("external leaf binding differs")
        expected = set(_EXTERNAL_FILE_ROLES)
        if set(self.relative_by_role) != expected:
            raise QualificationContractError("external file-role map is not closed")
        for role, relative in self.relative_by_role.items():
            normalized = verification._relative_path(
                relative, label=f"{role} external relative path"
            )
            if normalized != relative or len(PurePosixPath(relative).parts) != 2:
                raise QualificationContractError(
                    "external evidence files must each have one fixed parent"
                )


@dataclass(slots=True)
class _OwnedExternalStage:
    coordinates: _ExternalCoordinates
    parent_fd: int
    root_fd: int
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


def _safe_leaf(value: str, *, label: str) -> str:
    if (
        type(value) is not str
        or not value
        or value in {".", ".."}
        or "/" in value
        or "\0" in value
    ):
        raise QualificationContractError(f"{label} must be one safe path leaf")
    return value


def _stat_identity(value: os.stat_result) -> tuple[int, int, int]:
    return (value.st_dev, value.st_ino, stat.S_IFMT(value.st_mode))


def _entry_stat(parent_fd: int, leaf: str) -> os.stat_result | None:
    try:
        return os.stat(leaf, dir_fd=parent_fd, follow_symlinks=False)
    except FileNotFoundError:
        return None


def _write_all(descriptor: int, source: bytes) -> None:
    view = memoryview(source)
    written = 0
    while written < len(view):
        count = os.write(descriptor, view[written:])
        if count <= 0:
            raise OSError(errno.EIO, "zero-length external evidence write")
        written += count


def _read_descriptor(descriptor: int, *, maximum_bytes: int) -> bytes:
    observed = os.fstat(descriptor)
    if (
        not stat.S_ISREG(observed.st_mode)
        or observed.st_nlink != 1
        or observed.st_size < 1
        or observed.st_size > maximum_bytes
    ):
        raise QualificationContractError(
            "external evidence file violates its closed type or byte cap"
        )
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
        raise QualificationContractError("external evidence changed while read")
    return source


def _external_coordinates(
    protocol: verification.D7V1MaterializationProtocol,
    route: Mapping[str, object],
) -> _ExternalCoordinates:
    store, staging, _runner, _callable = verification._expected_route_coordinates(route)
    claim, attempt = verification._expected_external_paths(protocol)
    try:
        claim_relative = claim.relative_to(store).as_posix()
        attempt_relative = attempt.relative_to(store).as_posix()
    except ValueError as error:
        raise QualificationContractError(
            "external evidence coordinates escape the fixed store"
        ) from error
    return _ExternalCoordinates(
        staging=staging,
        store=store,
        claim=claim,
        attempt=attempt,
        parent=store.parent,
        staging_leaf=_safe_leaf(staging.name, label="external staging leaf"),
        store_leaf=_safe_leaf(store.name, label="external store leaf"),
        relative_by_role=MappingProxyType(
            {
                records.D7V1ExclusiveSeedSupplyClaim.artifact_role: claim_relative,
                records.D7V1OfficialExecutionAttemptReservation.artifact_role: (
                    attempt_relative
                ),
            }
        ),
    )


def _require_module_bound_to_s(
    repository: RepositoryContext,
    source_commit: str,
    c1: records.D7V1C1SourceSetRecord,
    *,
    imported_file: str,
    repository_path: str,
    label: str,
) -> None:
    if not repository.matches_imported_file(
        imported_file=imported_file, repository_path=repository_path
    ):
        raise QualificationContractError(
            f"{label} import origin differs from repository"
        )
    members = verification._source_members_from_c1(c1)
    by_path = {member.repository_path: member for member in members}
    if repository_path not in by_path:
        raise QualificationContractError(f"C1 source closure omits the {label}")
    _mode, committed = verification._git_blob(
        repository,
        source_commit,
        repository_path,
        maximum_bytes=verification._MAX_SOURCE_MEMBER_BYTES,
    )
    live = verification._safe_read_file(
        repository.root / repository_path,
        verification._MAX_SOURCE_MEMBER_BYTES,
        require_single_link=False,
    )
    member = by_path[repository_path]
    if (
        live != committed
        or member.sha256 != sha256_bytes(committed)
        or member.byte_count != len(committed)
    ):
        raise QualificationContractError(
            f"executing {label} source differs from source S"
        )


def _require_operation_sources_bound_to_s(
    repository: RepositoryContext,
    source_commit: str,
    c1: records.D7V1C1SourceSetRecord,
) -> None:
    _require_module_bound_to_s(
        repository,
        source_commit,
        c1,
        imported_file=__file__,
        repository_path=_MODULE_PATH,
        label="pre-item23 orchestrator",
    )
    _require_module_bound_to_s(
        repository,
        source_commit,
        c1,
        imported_file=publication.__file__,
        repository_path=publication._MODULE_PATH,
        label="private-publication module",
    )


def _preflight_repository_destination(
    repository: RepositoryContext,
    protocol: verification.D7V1MaterializationProtocol,
) -> None:
    layout = verification._mapping(
        protocol.document.get("coordinate_and_member_layout"),
        label="coordinate_and_member_layout",
    )
    root = PurePosixPath(
        verification._relative_path(
            layout.get("repository_root"), label="repository_root"
        )
    )
    if len(root.parts) < 2:
        raise QualificationContractError("repository root must have a parent")
    parent_fd = publication._open_publication_parent(repository, tuple(root.parts[:-1]))
    try:
        destination_leaf = _safe_leaf(root.name, label="repository destination leaf")
        reserved_prefix = f".{destination_leaf}{publication._STAGE_MARKER}"
        names = set(os.listdir(parent_fd))
        if destination_leaf in names:
            raise QualificationContractError(
                "D7 v1 repository destination already exists"
            )
        if any(name.startswith(reserved_prefix) for name in names):
            raise QualificationContractError(
                "D7 v1 repository private-stage namespace is not empty"
            )
        os.fsync(parent_fd)
    finally:
        _close_quietly(parent_fd)


def _open_external_parent(coordinates: _ExternalCoordinates) -> int:
    flags = publication._directory_open_flags()
    try:
        descriptor = os.open("/", flags)
    except OSError as error:
        raise QualificationContractError(
            f"cannot anchor filesystem root for external chronology: {error}"
        ) from error
    try:
        for part in coordinates.parent.parts[1:]:
            leaf = _safe_leaf(part, label="external chronology parent component")
            try:
                child = os.open(leaf, flags, dir_fd=descriptor)
            except OSError as error:
                raise QualificationContractError(
                    f"cannot anchor external chronology parent {leaf}: {error}"
                ) from error
            os.close(descriptor)
            descriptor = child
        if not stat.S_ISDIR(os.fstat(descriptor).st_mode):
            raise QualificationContractError(
                "external chronology parent is not a real directory"
            )
        return descriptor
    except BaseException:
        _close_quietly(descriptor)
        raise


def _preflight_external_destination(coordinates: _ExternalCoordinates) -> None:
    parent_fd = _open_external_parent(coordinates)
    try:
        if _entry_stat(parent_fd, coordinates.staging_leaf) is not None:
            raise QualificationContractError("external staging root already exists")
        if _entry_stat(parent_fd, coordinates.store_leaf) is not None:
            raise QualificationContractError("external store already exists")
        publication._native_exclusive_rename()
        os.fsync(parent_fd)
    finally:
        _close_quietly(parent_fd)


def _raise_external_failure(
    coordinates: _ExternalCoordinates,
    error: BaseException,
    *,
    disposition: str,
    stage_retained: bool | None = None,
    store_visible: bool | None = None,
) -> NoReturn:
    raise _D7V1ExternalChronologyFailure(
        str(error),
        disposition=disposition,
        external_stage=coordinates.staging,
        external_store=coordinates.store,
        stage_retained=stage_retained,
        store_visible=store_visible,
    ) from error


def _create_external_stage(
    coordinates: _ExternalCoordinates,
) -> _OwnedExternalStage:
    parent_fd = _open_external_parent(coordinates)
    root_fd = -1
    directory_fds: dict[str, int] = {}
    created = False
    try:
        if (
            _entry_stat(parent_fd, coordinates.staging_leaf) is not None
            or _entry_stat(parent_fd, coordinates.store_leaf) is not None
        ):
            raise FileExistsError(
                errno.EEXIST, "external staging or store destination exists"
            )
        os.mkdir(coordinates.staging_leaf, 0o700, dir_fd=parent_fd)
        created = True
        root_fd = os.open(
            coordinates.staging_leaf,
            publication._directory_open_flags(),
            dir_fd=parent_fd,
        )
        os.fchmod(root_fd, 0o700)
        stage_entry = os.stat(
            coordinates.staging_leaf, dir_fd=parent_fd, follow_symlinks=False
        )
        if _stat_identity(stage_entry) != _stat_identity(os.fstat(root_fd)):
            raise QualificationContractError("external staging anchor identity differs")
        directory_fds[""] = root_fd
        os.fsync(parent_fd)

        directories = sorted(
            {
                PurePosixPath(relative).parent.as_posix()
                for relative in coordinates.relative_by_role.values()
            }
        )
        for relative in directories:
            leaf = _safe_leaf(relative, label="external evidence directory")
            os.mkdir(leaf, 0o700, dir_fd=root_fd)
            descriptor = os.open(
                leaf, publication._directory_open_flags(), dir_fd=root_fd
            )
            os.fchmod(descriptor, 0o700)
            directory_fds[relative] = descriptor
        os.fsync(root_fd)
        return _OwnedExternalStage(
            coordinates=coordinates,
            parent_fd=parent_fd,
            root_fd=root_fd,
            directory_fds=directory_fds,
            file_fds={},
            file_snapshots={},
        )
    except BaseException as error:
        retained_failure: _D7V1ExternalChronologyFailure | None = None
        if created:
            try:
                _require_live_external_parent_anchor(coordinates, parent_fd)
                stage_entry = _entry_stat(parent_fd, coordinates.staging_leaf)
                store_entry = _entry_stat(parent_fd, coordinates.store_leaf)
                stage_matches = (
                    root_fd >= 0
                    and stage_entry is not None
                    and (
                        _stat_identity(stage_entry) == _stat_identity(os.fstat(root_fd))
                    )
                )
                if stage_matches and store_entry is None:
                    disposition = "external_stage_retained"
                    stage_retained: bool | None = True
                    store_visible: bool | None = False
                else:
                    disposition = "external_stage_creation_state_unknown"
                    stage_retained = None
                    store_visible = store_entry is not None
                retained_failure = _D7V1ExternalChronologyFailure(
                    str(error),
                    disposition=disposition,
                    external_stage=coordinates.staging,
                    external_store=coordinates.store,
                    stage_retained=stage_retained,
                    store_visible=store_visible,
                )
            except BaseException as observation_error:
                retained_failure = _D7V1ExternalChronologyFailure(
                    f"stage creation failed ({error}) and exact lexical namespace "
                    f"reauthentication failed: {observation_error}",
                    disposition="external_namespace_reauthentication_failed",
                    external_stage=coordinates.staging,
                    external_store=coordinates.store,
                    stage_retained=None,
                    store_visible=None,
                )
        for relative, descriptor in reversed(tuple(directory_fds.items())):
            if relative:
                _close_quietly(descriptor)
        if root_fd >= 0:
            _close_quietly(root_fd)
        _close_quietly(parent_fd)
        if retained_failure is not None:
            raise retained_failure from error
        raise


def _persist_external_record(
    stage: _OwnedExternalStage,
    record: records._D7V1CanonicalRecord,
) -> records._D7V1CanonicalRecord:
    role = record.artifact_role
    try:
        relative = stage.coordinates.relative_by_role[role]
    except KeyError as error:
        raise QualificationContractError(
            f"record role has no external coordinate: {role}"
        ) from error
    parent_relative = PurePosixPath(relative).parent.as_posix()
    leaf = _safe_leaf(PurePosixPath(relative).name, label=f"{role} external leaf")
    parent_fd = stage.directory_fds[parent_relative]
    descriptor = os.open(
        leaf,
        publication._file_create_flags(),
        0o600,
        dir_fd=parent_fd,
    )
    stage.file_fds[relative] = descriptor
    os.fchmod(descriptor, 0o600)
    _write_all(descriptor, record.canonical_bytes)
    os.fsync(descriptor)
    stage.file_snapshots[relative] = os.fstat(descriptor)
    os.fsync(parent_fd)
    os.fsync(stage.root_fd)

    reloaded_fd = os.open(
        leaf,
        os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0),
        dir_fd=parent_fd,
    )
    try:
        if _stat_identity(os.fstat(reloaded_fd)) != _stat_identity(
            os.fstat(descriptor)
        ):
            raise QualificationContractError(
                f"durable external {role} reload identity differs"
            )
        source = _read_descriptor(reloaded_fd, maximum_bytes=record.max_record_bytes)
    finally:
        _close_quietly(reloaded_fd)
    if source != record.canonical_bytes:
        raise QualificationContractError(f"durable external {role} reload bytes differ")
    return type(record).from_canonical_bytes(
        source, expected_sha256=record.canonical_sha256
    )


def _expected_external_children(
    coordinates: _ExternalCoordinates,
) -> dict[str, set[str]]:
    children: dict[str, set[str]] = {"": set()}
    for relative in coordinates.relative_by_role.values():
        parent = PurePosixPath(relative).parent.as_posix()
        leaf = PurePosixPath(relative).name
        children.setdefault(parent, set()).add(leaf)
        children[""].add(parent)
    return children


def _reverify_external_stage(
    stage: _OwnedExternalStage,
    sources_by_role: Mapping[str, bytes],
    *,
    promoted: bool,
) -> None:
    coordinates = stage.coordinates
    if set(sources_by_role) != set(_EXTERNAL_FILE_ROLES):
        raise QualificationContractError("external evidence source set is not closed")
    children = _expected_external_children(coordinates)
    if set(stage.directory_fds) != set(children):
        raise QualificationContractError("external evidence directory set differs")
    if set(stage.file_fds) != set(coordinates.relative_by_role.values()):
        raise QualificationContractError("external evidence file set differs")
    for relative, descriptor in stage.directory_fds.items():
        observed = os.fstat(descriptor)
        observed_names = set(os.listdir(descriptor))
        if (
            not stat.S_ISDIR(observed.st_mode)
            or stat.S_IMODE(observed.st_mode) != 0o700
            or observed_names != children[relative]
        ):
            raise QualificationContractError(
                f"external evidence directory changed: {relative or '.'}"
            )
        for name in observed_names:
            child_relative = name if not relative else f"{relative}/{name}"
            child_fd = (
                stage.directory_fds[child_relative]
                if child_relative in stage.directory_fds
                else stage.file_fds[child_relative]
            )
            entry = os.stat(name, dir_fd=descriptor, follow_symlinks=False)
            if _stat_identity(entry) != _stat_identity(os.fstat(child_fd)):
                raise QualificationContractError(
                    f"external evidence entry identity changed: {child_relative}"
                )
    for role, relative in coordinates.relative_by_role.items():
        descriptor = stage.file_fds[relative]
        before = stage.file_snapshots[relative]
        now = os.fstat(descriptor)
        if (
            _stat_identity(now) != _stat_identity(before)
            or stat.S_IMODE(now.st_mode) != 0o600
            or now.st_nlink != 1
            or now.st_size != before.st_size
            or now.st_mtime_ns != before.st_mtime_ns
        ):
            raise QualificationContractError(
                f"external evidence member changed: {relative}"
            )
        source = _read_descriptor(
            descriptor,
            maximum_bytes=verification._ROLE_CLASSES[role].max_record_bytes,
        )
        if source != sources_by_role[role]:
            raise QualificationContractError(
                f"external evidence member bytes changed: {relative}"
            )

    stage_entry = _entry_stat(stage.parent_fd, coordinates.staging_leaf)
    store_entry = _entry_stat(stage.parent_fd, coordinates.store_leaf)
    expected = _stat_identity(os.fstat(stage.root_fd))
    if promoted:
        if (
            stage_entry is not None
            or store_entry is None
            or _stat_identity(store_entry) != expected
        ):
            raise QualificationContractError("promoted external store identity differs")
    elif (
        stage_entry is None
        or _stat_identity(stage_entry) != expected
        or store_entry is not None
    ):
        raise QualificationContractError("external staging namespace changed")


def _require_live_external_parent_anchor(
    coordinates: _ExternalCoordinates,
    anchored_parent_fd: int,
) -> None:
    live_parent_fd = _open_external_parent(coordinates)
    try:
        if _stat_identity(os.fstat(live_parent_fd)) != _stat_identity(
            os.fstat(anchored_parent_fd)
        ):
            raise QualificationContractError(
                "live external parent differs from its held anchor"
            )
    finally:
        _close_quietly(live_parent_fd)


def _external_promotion_outcome(stage: _OwnedExternalStage) -> str:
    _require_live_external_parent_anchor(stage.coordinates, stage.parent_fd)
    expected = _stat_identity(os.fstat(stage.root_fd))
    stage_entry = _entry_stat(stage.parent_fd, stage.coordinates.staging_leaf)
    store_entry = _entry_stat(stage.parent_fd, stage.coordinates.store_leaf)
    stage_matches = stage_entry is not None and _stat_identity(stage_entry) == expected
    store_matches = store_entry is not None and _stat_identity(store_entry) == expected
    if stage_matches and store_entry is None:
        return "stage-retained"
    if stage_entry is None and store_matches:
        return "published"
    return "ambiguous"


def _raise_observed_external_failure(
    stage: _OwnedExternalStage,
    error: BaseException,
) -> NoReturn:
    try:
        outcome = _external_promotion_outcome(stage)
    except BaseException as observation_error:
        _raise_external_failure(
            stage.coordinates,
            QualificationContractError(
                f"external operation failed ({error}) and exact lexical namespace "
                f"reauthentication failed: {observation_error}"
            ),
            disposition="external_namespace_reauthentication_failed",
            stage_retained=None,
            store_visible=None,
        )
    disposition = {
        "stage-retained": "external_stage_retained",
        "published": "external_published_verification_unknown",
        "ambiguous": "external_state_unknown",
    }[outcome]
    stage_retained, store_visible = {
        "stage-retained": (True, False),
        "published": (False, True),
        "ambiguous": (None, None),
    }[outcome]
    _raise_external_failure(
        stage.coordinates,
        error,
        disposition=disposition,
        stage_retained=stage_retained,
        store_visible=store_visible,
    )


def _require_anchored_external_store(
    stage: _OwnedExternalStage,
    sources_by_role: Mapping[str, bytes],
    anchored_evidence: publication._D7V1AnchoredExternalEvidence,
) -> None:
    """Reauthenticate the exact promoted tree through both held abstractions."""

    expected_by_path = {
        stage.coordinates.store / stage.coordinates.relative_by_role[role]: source
        for role, source in sources_by_role.items()
    }
    if (
        type(anchored_evidence) is not publication._D7V1AnchoredExternalEvidence
        or anchored_evidence.store_path != stage.coordinates.store
        or dict(anchored_evidence.source_by_path) != expected_by_path
    ):
        raise QualificationContractError(
            "anchored external evidence differs from the promoted source set"
        )

    _require_live_external_parent_anchor(stage.coordinates, stage.parent_fd)
    _reverify_external_stage(stage, sources_by_role, promoted=True)
    for role, relative in stage.coordinates.relative_by_role.items():
        path = stage.coordinates.store / relative
        source = anchored_evidence.read(
            path,
            verification._ROLE_CLASSES[role].max_record_bytes,
        )
        if source != sources_by_role[role]:
            raise QualificationContractError(
                f"anchored external evidence bytes changed: {relative}"
            )
    _require_live_external_parent_anchor(stage.coordinates, stage.parent_fd)
    _reverify_external_stage(stage, sources_by_role, promoted=True)


def _raise_composite_publication_failure(
    stage: _OwnedExternalStage,
    sources_by_role: Mapping[str, bytes],
    anchored_evidence: publication._D7V1AnchoredExternalEvidence,
    error: publication.D7V1PrivatePublicationFailure,
) -> NoReturn:
    """Preserve exact failure facts for both publication namespaces."""

    try:
        _require_anchored_external_store(stage, sources_by_role, anchored_evidence)
    except BaseException as external_error:
        try:
            outcome = _external_promotion_outcome(stage)
        except BaseException as observation_error:
            disposition = (
                "repository_publication_failed_external_namespace_"
                "reauthentication_failed"
            )
            stage_retained = None
            store_visible = None
            external_store_verified = None
            external_detail = (
                f"exact external-store verification failed ({external_error}); "
                f"namespace reauthentication also failed ({observation_error})"
            )
        else:
            disposition = {
                "stage-retained": (
                    "repository_publication_failed_external_stage_retained"
                ),
                "published": (
                    "repository_publication_failed_external_store_unverified"
                ),
                "ambiguous": "repository_publication_failed_external_state_unknown",
            }[outcome]
            stage_retained, store_visible = {
                "stage-retained": (True, False),
                "published": (False, True),
                "ambiguous": (None, None),
            }[outcome]
            external_store_verified = None if outcome == "ambiguous" else False
            external_detail = (
                f"exact external-store verification failed ({external_error})"
            )
    else:
        disposition = "repository_publication_failed_external_store_verified"
        stage_retained = False
        store_visible = True
        external_store_verified = True
        external_detail = "the exact promoted external store remains verified"

    raise _D7V1ExternalChronologyFailure(
        f"repository publication failed with {error.disposition}; {external_detail}",
        disposition=disposition,
        external_stage=stage.coordinates.staging,
        external_store=stage.coordinates.store,
        stage_retained=stage_retained,
        store_visible=store_visible,
        external_store_verified=external_store_verified,
        repository_disposition=error.disposition,
        repository_destination=error.destination,
        repository_stage_path=error.stage_path,
        repository_stage_retained=error.stage_retained,
        repository_publication_visible=error.publication_visible,
    ) from error


def _promote_external_store_no_replace(
    stage: _OwnedExternalStage,
    sources_by_role: Mapping[str, bytes],
) -> None:
    _reverify_external_stage(stage, sources_by_role, promoted=False)
    _primitive, native_rename = publication._native_exclusive_rename()
    try:
        _require_live_external_parent_anchor(stage.coordinates, stage.parent_fd)
    except BaseException as error:
        _raise_external_failure(
            stage.coordinates,
            error,
            disposition="external_namespace_reauthentication_failed",
            stage_retained=None,
            store_visible=None,
        )
    try:
        native_rename(
            stage.parent_fd,
            stage.coordinates.staging_leaf,
            stage.coordinates.store_leaf,
        )
    except BaseException as error:
        try:
            outcome = _external_promotion_outcome(stage)
        except BaseException as observation_error:
            detail = QualificationContractError(
                f"external rename failed ({error}) and exact anchored outcome "
                f"observation also failed: {observation_error}"
            )
            _raise_external_failure(
                stage.coordinates,
                detail,
                disposition="external_promotion_state_unknown",
            )
        disposition = {
            "stage-retained": "external_stage_retained",
            "published": "external_published_durability_unknown",
            "ambiguous": "external_promotion_state_unknown",
        }[outcome]
        stage_retained, store_visible = {
            "stage-retained": (True, False),
            "published": (False, True),
            "ambiguous": (None, None),
        }[outcome]
        _raise_external_failure(
            stage.coordinates,
            error,
            disposition=disposition,
            stage_retained=stage_retained,
            store_visible=store_visible,
        )
    try:
        outcome = _external_promotion_outcome(stage)
    except BaseException as error:
        _raise_external_failure(
            stage.coordinates,
            error,
            disposition="external_promotion_state_unknown",
        )
    if outcome != "published":
        disposition = (
            "external_stage_retained"
            if outcome == "stage-retained"
            else "external_promotion_state_unknown"
        )
        _raise_external_failure(
            stage.coordinates,
            QualificationContractError(
                "native external rename returned without exact publication"
            ),
            disposition=disposition,
            stage_retained=True if outcome == "stage-retained" else None,
            store_visible=False if outcome == "stage-retained" else None,
        )
    try:
        os.fsync(stage.parent_fd)
    except BaseException as error:
        _raise_external_failure(
            stage.coordinates,
            error,
            disposition="external_published_durability_unknown",
            stage_retained=False,
            store_visible=True,
        )
    try:
        _require_live_external_parent_anchor(stage.coordinates, stage.parent_fd)
    except BaseException as error:
        _raise_external_failure(
            stage.coordinates,
            error,
            disposition="external_namespace_reauthentication_failed",
            stage_retained=None,
            store_visible=None,
        )
    try:
        _reverify_external_stage(stage, sources_by_role, promoted=True)
        reopened = os.open(
            stage.coordinates.store_leaf,
            publication._directory_open_flags(),
            dir_fd=stage.parent_fd,
        )
        try:
            if _stat_identity(os.fstat(reopened)) != _stat_identity(
                os.fstat(stage.root_fd)
            ):
                raise QualificationContractError(
                    "reopened durable external store identity differs"
                )
        finally:
            _close_quietly(reopened)
    except BaseException as error:
        _raise_external_failure(
            stage.coordinates,
            error,
            disposition="external_published_verification_unknown",
            stage_retained=False,
            store_visible=True,
        )
    try:
        _require_live_external_parent_anchor(stage.coordinates, stage.parent_fd)
    except BaseException as error:
        _raise_external_failure(
            stage.coordinates,
            error,
            disposition="external_namespace_reauthentication_failed",
            stage_retained=None,
            store_visible=None,
        )


def _route_binding(
    repository: RepositoryContext,
    protocol: verification.D7V1MaterializationProtocol,
) -> tuple[dict[str, object], records.D7V1ArtifactBinding]:
    source, route = verification._route_source(repository, protocol)
    return route, records.D7V1ArtifactBinding(
        artifact_role=verification._ROUTE_ROLE,
        artifact_contract_id=verification._string(
            route.get("schema_version"), label="route schema_version"
        ),
        canonical_sha256=sha256_bytes(source),
        byte_count=len(source),
    )


def _build_claim(
    protocol: verification.D7V1MaterializationProtocol,
    closure: source_closure_module.D7V1SourceClosureCandidate,
    supplier: supplier_module.D7V1SourceSelectedSeedSupplierCandidate,
    coordinates: _ExternalCoordinates,
) -> records.D7V1ExclusiveSeedSupplyClaim:
    paths = verification._coordinates(protocol)
    return records.D7V1ExclusiveSeedSupplyClaim.create(
        record_id=_RECORD_IDS[records.D7V1ExclusiveSeedSupplyClaim.artifact_role],
        repository_path=paths["exclusive_seed_supply_claim"],
        c2=closure.c2,
        supplier_identity_binding=supplier.supplier_identity_binding,
        supplier_id=supplier.supplier_id,
        external_claim_path=str(coordinates.claim),
    )


def _build_post_supplier_records(
    repository: RepositoryContext,
    protocol: verification.D7V1MaterializationProtocol,
    route: Mapping[str, object],
    route_binding: records.D7V1ArtifactBinding,
    closure: source_closure_module.D7V1SourceClosureCandidate,
    supplier: supplier_module.D7V1SourceSelectedSeedSupplierCandidate,
    referents: referents_module.D7V1FullDesignReferentSetCandidate,
    coordinates: _ExternalCoordinates,
    claim: records.D7V1ExclusiveSeedSupplyClaim,
    seeds: tuple[int, int],
) -> tuple[
    records.D7V1OfficialSeedInventory,
    records.D7V1ReplayTarget,
    records.D7V1FullDesignFreeze,
    records.D7V1LaunchIntent,
    records.D7V1OfficialExecutionAttemptReservation,
]:
    paths = verification._coordinates(protocol)
    predecessor_binding, predecessor_values = verification._negative_seed_binding(
        repository, protocol
    )
    inventory = records.D7V1OfficialSeedInventory.create(
        record_id=_RECORD_IDS[records.D7V1OfficialSeedInventory.artifact_role],
        repository_path=paths["official_seed_inventory"],
        claim=claim,
        supplier_identity_binding=supplier.supplier_identity_binding,
        supplier_id=supplier.supplier_id,
        seeds=seeds,
        predecessor_inventory_binding=predecessor_binding,
        predecessor_seed_values=predecessor_values,
    )
    bindings = referents.bindings_by_inventory_field
    full_design = records.D7V1EmbeddedFullDesign.create(
        design_id=_FULL_DESIGN_ID,
        family_binding=bindings["family_binding"],
        admission_binding=bindings["admission_binding"],
        protocol_binding=bindings["protocol_binding"],
        source_graph_binding=bindings["source_graph_binding"],
        inventory_binding=records.D7V1ArtifactBinding.from_record(inventory),
        graph_case_stress_aggregation_binding=bindings[
            "graph_case_stress_aggregation_binding"
        ],
        lifecycle_binding=bindings["lifecycle_binding"],
    )
    historical = verification._historical_bindings(repository, protocol)
    transitive_by_role = {
        records.D7V1C1SourceSetRecord.artifact_role: (
            records.D7V1ArtifactBinding.from_record(closure.c1)
        ),
        records.D7V1C2SourceClosureReceipt.artifact_role: (
            records.D7V1ArtifactBinding.from_record(closure.c2)
        ),
        records.D7V1ExclusiveSeedSupplyClaim.artifact_role: (
            records.D7V1ArtifactBinding.from_record(claim)
        ),
        records.D7V1OfficialSeedInventory.artifact_role: (
            records.D7V1ArtifactBinding.from_record(inventory)
        ),
        "embedded-full-design": records.D7V1ArtifactBinding(
            artifact_role="embedded-full-design",
            artifact_contract_id=full_design.schema_version,
            canonical_sha256=full_design.canonical_sha256,
            byte_count=full_design.byte_count,
        ),
        verification._ROUTE_ROLE: route_binding,
        verification._PROTOCOL_ROLE: verification._protocol_binding(protocol),
        **historical,
    }
    transitive = {
        key: transitive_by_role[role]
        for key, role in records._REPLAY_TRANSITIVE_ROLES.items()
        if key != "embedded_full_design_binding"
    }
    replay = records.D7V1ReplayTarget.create(
        record_id=_RECORD_IDS[records.D7V1ReplayTarget.artifact_role],
        repository_path=paths["replay_target"],
        official_seed_inventory_binding=(
            records.D7V1ArtifactBinding.from_record(inventory)
        ),
        full_design=full_design,
        transitive_bindings=transitive,
    )
    replay_document = replay.to_dict()
    freeze = records.D7V1FullDesignFreeze.create(
        record_id=_RECORD_IDS[records.D7V1FullDesignFreeze.artifact_role],
        repository_path=paths["full_design_freeze"],
        replay_target_binding=records.D7V1ArtifactBinding.from_record(replay),
        full_design_binding=records.D7V1JsonPointerBinding.from_dict(
            replay_document["full_design_binding"]
        ),
        reviewed_source_commit=closure.source_commit,
    )
    store, staging, runner, official_callable = (
        verification._expected_route_coordinates(route)
    )
    if store != coordinates.store or staging != coordinates.staging:
        raise QualificationContractError("external route coordinates changed")
    launch = records.D7V1LaunchIntent.create(
        record_id=_RECORD_IDS[records.D7V1LaunchIntent.artifact_role],
        repository_path=paths["launch_intent"],
        replay_target_binding=records.D7V1ArtifactBinding.from_record(replay),
        full_design_freeze_binding=records.D7V1ArtifactBinding.from_record(freeze),
        external_store_path=str(store),
        external_staging_path=str(staging),
        runner_script=runner,
        official_callable=official_callable,
    )
    attempt = records.D7V1OfficialExecutionAttemptReservation.create(
        record_id=_RECORD_IDS[
            records.D7V1OfficialExecutionAttemptReservation.artifact_role
        ],
        repository_path=paths["official_execution_attempt_envelope"],
        launch_intent=launch,
        replay_target=replay,
        seed_claim=claim,
        external_attempt_path=str(coordinates.attempt),
        external_store_path=str(store),
        reviewed_source_commit=closure.source_commit,
    )
    return inventory, replay, freeze, launch, attempt


def _build_receipt_last(
    protocol: verification.D7V1MaterializationProtocol,
    source_commit: str,
    predecessors: tuple[records._D7V1CanonicalRecord, ...],
) -> records.D7V1PreItem23ChronologyReceipt:
    paths = verification._coordinates(protocol)
    inventory = {
        role: paths[key] for key, role in verification._COORDINATE_ROLES.items()
    }
    absence = records.D7V1NamespaceAbsenceObservation(
        repository_path=paths["descriptive_result"],
        observed_at_reviewed_source_commit=source_commit,
    )
    return records.D7V1PreItem23ChronologyReceipt.create(
        record_id=_RECORD_IDS[records.D7V1PreItem23ChronologyReceipt.artifact_role],
        repository_path=paths["pre_item23_chronology_receipt"],
        predecessor_bindings={
            record.artifact_role: records.D7V1ArtifactBinding.from_record(record)
            for record in predecessors
        },
        pre_item23_file_inventory=inventory,
        descriptive_result_namespace_absence=absence,
    )


def _materialize_d7_v1_pre_item23_no_replace(
    repository: RepositoryContext,
    *,
    source_commit: str,
) -> publication.D7V1PrivatePublicationReceipt:
    """Materialize from asserted S; this source alone grants no call authority.

    The operation authenticates the assertion against clean ``HEAD`` and C1,
    but it does not attest that S was reviewed or selected.  The preparation
    script remains intentionally unwired from this private callable.
    """

    if not isinstance(repository, RepositoryContext):
        raise TypeError("repository must be RepositoryContext")

    # Everything through both namespace preflights is read-only.  This also
    # proves that the executing orchestrator bytes are an exact member of S.
    closure = source_closure_module._build_d7_v1_source_closure_candidate(
        repository,
        source_commit=source_commit,
    )
    _require_operation_sources_bound_to_s(repository, closure.source_commit, closure.c1)
    deterministic = (
        deterministic_inputs_module._build_d7_v1_deterministic_input_contract_candidate(
            repository,
            source_closure=closure,
        )
    )
    supplier = supplier_module._build_d7_v1_source_selected_seed_supplier_candidate(
        repository,
        deterministic_inputs=deterministic,
    )
    supplier_module._fixed_callable_contract()
    fixed_supplier = supplier_module._FIXED_SUPPLIER
    if fixed_supplier is not supplier_module._supply_d7_v1_official_seed_values:
        raise QualificationContractError("captured fixed supplier identity differs")
    referents = referents_module._build_d7_v1_full_design_referent_set_candidate(
        repository,
        deterministic_inputs=deterministic,
    )
    protocol = verification._protocol_at_commit(repository, closure.source_commit)
    route, route_binding = _route_binding(repository, protocol)
    coordinates = _external_coordinates(protocol, route)
    _preflight_repository_destination(repository, protocol)
    _preflight_external_destination(coordinates)
    source_closure_module._require_exact_clean_head(repository, closure.source_commit)
    _require_operation_sources_bound_to_s(repository, closure.source_commit, closure.c1)

    stage = _create_external_stage(coordinates)
    try:
        try:
            claim = _build_claim(protocol, closure, supplier, coordinates)
            durable_claim = _persist_external_record(stage, claim)
            if not isinstance(durable_claim, records.D7V1ExclusiveSeedSupplyClaim):
                raise AssertionError("durable claim reload returned the wrong type")

            # This is the sole supplier entry in the complete operation.  The
            # durable canonical claim reload above necessarily precedes it.
            supplied_values = fixed_supplier()
            if (
                type(supplied_values) is not tuple
                or len(supplied_values) != supplier.required_seed_count
                or any(type(value) is not int for value in supplied_values)
                or any(value < 0 or value > (2**63 - 1) for value in supplied_values)
                or tuple(sorted(supplied_values)) != supplied_values
            ):
                raise QualificationContractError(
                    "fixed supplier returned an invalid seed tuple"
                )
            seeds = supplied_values
            if len(set(seeds)) != supplier.required_seed_count or set(seeds) & set(
                supplier.excluded_seed_values
            ):
                raise QualificationContractError(
                    "fixed supplier returned excluded or duplicate seeds"
                )

            inventory, replay, freeze, launch, attempt = _build_post_supplier_records(
                repository,
                protocol,
                route,
                route_binding,
                closure,
                supplier,
                referents,
                coordinates,
                durable_claim,
                seeds,
            )
            durable_attempt = _persist_external_record(stage, attempt)
            if not isinstance(
                durable_attempt, records.D7V1OfficialExecutionAttemptReservation
            ):
                raise AssertionError("durable attempt reload returned the wrong type")
            source_closure_module._require_exact_clean_head(
                repository, closure.source_commit
            )
            if (
                verification._verify_source_join(
                    repository,
                    protocol,
                    closure.c1,
                    closure.c2,
                )
                != closure.source_commit
            ):
                raise QualificationContractError(
                    "pre-promotion source join differs from source S"
                )
            _require_operation_sources_bound_to_s(
                repository, closure.source_commit, closure.c1
            )
            external_sources = {
                durable_claim.artifact_role: durable_claim.canonical_bytes,
                durable_attempt.artifact_role: durable_attempt.canonical_bytes,
            }
            _promote_external_store_no_replace(stage, external_sources)
            anchored_external_evidence = (
                publication._build_d7_v1_anchored_external_evidence(
                    repository,
                    parent_fd=stage.parent_fd,
                    root_fd=stage.root_fd,
                    directory_fd_by_path={
                        coordinates.store / relative: descriptor
                        for relative, descriptor in stage.directory_fds.items()
                        if relative
                    },
                    file_fd_by_path={
                        coordinates.store / relative: descriptor
                        for relative, descriptor in stage.file_fds.items()
                    },
                    source_by_path={
                        coordinates.store / coordinates.relative_by_role[role]: source
                        for role, source in external_sources.items()
                    },
                )
            )
        except _D7V1ExternalChronologyFailure:
            raise
        except BaseException as error:
            _raise_observed_external_failure(stage, error)

        try:
            predecessors: tuple[records._D7V1CanonicalRecord, ...] = (
                closure.c1,
                closure.c2,
                durable_claim,
                inventory,
                replay,
                freeze,
                launch,
                durable_attempt,
            )
            receipt = _build_receipt_last(protocol, closure.source_commit, predecessors)
            all_records = (*predecessors, receipt)
            sources_by_role = {
                record.artifact_role: record.canonical_bytes for record in all_records
            }

            joined = verification._load_joined_sources(
                repository,
                protocol,
                sources_by_role,
                expected_receipt_sha256=receipt.canonical_sha256,
                stage_root=None,
                external_reader=anchored_external_evidence.read,
            )
            if (
                joined.source_commit != closure.source_commit
                or joined.receipt.canonical_bytes != receipt.canonical_bytes
            ):
                raise QualificationContractError("pre-item23 joined hard gate differs")
            _require_operation_sources_bound_to_s(
                repository, closure.source_commit, closure.c1
            )
            return publication._publish_d7_v1_pre_item23_records_no_replace(
                repository,
                sources_by_role,
                expected_receipt_sha256=receipt.canonical_sha256,
                _anchored_external_evidence=anchored_external_evidence,
            )
        except _D7V1ExternalChronologyFailure:
            raise
        except publication.D7V1PrivatePublicationFailure as error:
            _raise_composite_publication_failure(
                stage,
                external_sources,
                anchored_external_evidence,
                error,
            )
        except BaseException as error:
            _raise_observed_external_failure(stage, error)
    finally:
        stage.close()
