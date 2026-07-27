"""Strict closed-world loading for canonical instrument bundles."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass, fields, is_dataclass
import errno
import hashlib
import os
from pathlib import Path, PurePosixPath
import stat
from types import MappingProxyType
from typing import TypeAlias

from spirallens.contexts import (
    CONTEXT_BANK_SCHEMA_VERSION,
    MAX_CONTEXT_BANK_BYTES,
    ContextBank,
    ContextBankIntegrityError,
    ContextContractError,
)
from spirallens.contexts.loader import _load_context_bank_from_bytes

from .artifact_loader import (
    MAX_INSTRUMENT_ARTIFACT_BYTES,
    InstrumentArtifactIntegrityError,
    InstrumentArtifactSchemaError,
    _load_instrument_artifact_from_bytes,
)
from .artifacts import InstrumentArtifactValue
from .bundle import (
    BundleArtifactEntry,
    BundleContextBankEntry,
    InstrumentBundleManifest,
)
from .canonical import CanonicalJsonError, parse_canonical_json
from .common import (
    ArtifactRef,
    ArtifactType,
    ContractValidationError,
    PayloadRef,
    require_mapping,
    require_sha256,
)
from .registry import HypothesisRegistry, HypothesisRegistryPolicyError
from .registry_loader import (
    MAX_HYPOTHESIS_REGISTRY_BYTES,
    HypothesisRegistryIntegrityError,
    HypothesisRegistrySchemaError,
    _load_hypothesis_registry_from_bytes,
)


MAX_INSTRUMENT_BUNDLE_BYTES = 4 * 1024 * 1024
_STREAM_CHUNK_BYTES = 1024 * 1024
_SUPPORTS_SECURE_DIR_FD = (
    hasattr(os, "O_NOFOLLOW")
    and hasattr(os, "O_DIRECTORY")
    and os.open in os.supports_dir_fd
    and os.stat in os.supports_dir_fd
    and os.stat in os.supports_follow_symlinks
)

ArtifactKey: TypeAlias = tuple[ArtifactType, str]
FileIdentity: TypeAlias = tuple[int, int]
ResolvedArtifactValue: TypeAlias = (
    InstrumentArtifactValue | HypothesisRegistry | ContextBank
)


class InstrumentBundleError(ContractValidationError):
    """Base class for stable, fail-closed bundle validation errors."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code


class InstrumentBundleSchemaError(InstrumentBundleError):
    """The canonical bundle index or member schema is malformed."""


class InstrumentBundleIntegrityError(InstrumentBundleError):
    """A declared source or content identity differs from actual bytes."""


class InstrumentBundleResolutionError(InstrumentBundleError):
    """A closed-world artifact or payload reference cannot be resolved."""


class InstrumentBundleConsistencyError(InstrumentBundleError):
    """Resolved manifests disagree on a repeated contract fact."""


@dataclass(frozen=True, slots=True)
class ArtifactReferenceUse:
    """One typed ArtifactRef and its owner-relative field path."""

    owner: ArtifactRef
    path: str
    reference: ArtifactRef


@dataclass(frozen=True, slots=True)
class PayloadReferenceUse:
    """One typed PayloadRef and its owner-relative field path."""

    owner: ArtifactRef
    path: str
    reference: PayloadRef


@dataclass(frozen=True, slots=True)
class LoadedBundleArtifact:
    """One indexed artifact after strict source and canonical validation."""

    reference: ArtifactRef
    value: ResolvedArtifactValue
    source_path: Path
    source_sha256: str

    @property
    def logical_key(self) -> ArtifactKey:
        return (
            self.reference.artifact_type,
            self.reference.artifact_id,
        )


@dataclass(frozen=True, slots=True)
class LoadedBundlePayload:
    """Integrity receipt for opaque bytes, without a reusable path handle."""

    reference: PayloadRef


@dataclass(frozen=True, slots=True)
class _OpenedBundleMember:
    """One no-follow regular file bound to the descriptor being consumed."""

    source_path: Path
    descriptor: int
    root_identity: FileIdentity
    identity: FileIdentity


@dataclass(frozen=True, slots=True)
class LoadedInstrumentBundle:
    """A closed, acyclic bundle with resolved artifacts and payload bytes."""

    manifest: InstrumentBundleManifest
    source_path: Path
    source_sha256: str
    canonical_sha256: str
    artifacts: tuple[LoadedBundleArtifact, ...]
    payloads: tuple[LoadedBundlePayload, ...]
    artifact_reference_count: int
    payload_reference_count: int
    cross_manifest_join_count: int

    @property
    def artifact_index(self) -> Mapping[ArtifactKey, LoadedBundleArtifact]:
        return MappingProxyType(
            {member.logical_key: member for member in self.artifacts}
        )

    def resolve(self, reference: ArtifactRef) -> ResolvedArtifactValue:
        """Resolve one exact content-addressed reference from this bundle."""

        member = self.artifact_index.get(
            (reference.artifact_type, reference.artifact_id)
        )
        if member is None or member.reference != reference:
            raise InstrumentBundleResolutionError(
                "artifact_reference_unresolved",
                "reference is absent or differs from the indexed identity",
            )
        return member.value


def _artifact_ref_for(
    value: ResolvedArtifactValue,
    *,
    canonical_sha256: str,
) -> ArtifactRef:
    if isinstance(value, HypothesisRegistry):
        artifact_type = ArtifactType.HYPOTHESIS_REGISTRY
        schema_version = value.schema_version
        artifact_id = value.registry_id
    elif isinstance(value, ContextBank):
        artifact_type = ArtifactType.CONTEXT_BANK
        schema_version = CONTEXT_BANK_SCHEMA_VERSION
        artifact_id = value.bank_id
    else:
        artifact_type = value.artifact_type
        schema_version = value.schema_version
        artifact_id = value.artifact_id
    return ArtifactRef(
        artifact_type=artifact_type,
        schema_version=schema_version,
        artifact_id=artifact_id,
        canonical_sha256=canonical_sha256,
    )


def _walk_reference_uses(
    value: object,
    *,
    owner: ArtifactRef,
    path: str,
) -> Iterator[ArtifactReferenceUse | PayloadReferenceUse]:
    if isinstance(value, ArtifactRef):
        yield ArtifactReferenceUse(
            owner=owner,
            path=path,
            reference=value,
        )
        return
    if isinstance(value, PayloadRef):
        yield PayloadReferenceUse(
            owner=owner,
            path=path,
            reference=value,
        )
        return
    if isinstance(value, tuple):
        for index, item in enumerate(value):
            yield from _walk_reference_uses(
                item,
                owner=owner,
                path=f"{path}[{index}]",
            )
        return
    if is_dataclass(value):
        for field in fields(value):
            yield from _walk_reference_uses(
                getattr(value, field.name),
                owner=owner,
                path=f"{path}.{field.name}",
            )


def iter_artifact_reference_uses(
    member: LoadedBundleArtifact,
) -> Iterator[ArtifactReferenceUse]:
    """Yield every top-level, nested, optional, and tuple ArtifactRef."""

    if isinstance(member.value, (HypothesisRegistry, ContextBank)):
        return
    for use in _walk_reference_uses(
        member.value,
        owner=member.reference,
        path=member.value.__class__.__name__,
    ):
        if isinstance(use, ArtifactReferenceUse):
            yield use


def iter_payload_reference_uses(
    member: LoadedBundleArtifact,
) -> Iterator[PayloadReferenceUse]:
    """Yield every payload reference without opening the payload."""

    if isinstance(member.value, (HypothesisRegistry, ContextBank)):
        return
    for use in _walk_reference_uses(
        member.value,
        owner=member.reference,
        path=member.value.__class__.__name__,
    ):
        if isinstance(use, PayloadReferenceUse):
            yield use


def _secure_open_flags(*, directory: bool) -> int:
    no_follow = getattr(os, "O_NOFOLLOW", None)
    directory_only = getattr(os, "O_DIRECTORY", None)
    if not _SUPPORTS_SECURE_DIR_FD:
        raise InstrumentBundleResolutionError(
            "secure_member_open_unavailable",
            "this platform cannot enforce descriptor-relative no-follow loading",
        )
    assert no_follow is not None
    assert directory_only is not None
    flags = (
        os.O_RDONLY
        | no_follow
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NONBLOCK", 0)
        | getattr(os, "O_NOCTTY", 0)
    )
    if directory:
        flags |= directory_only
    return flags


def _raise_member_os_error(
    *,
    relative_path: str,
    action: str,
    error: OSError,
) -> None:
    if isinstance(error, FileNotFoundError):
        raise InstrumentBundleResolutionError(
            "bundle_member_missing",
            f"bundle member {relative_path!r} disappeared during {action}",
        ) from error
    if error.errno == errno.ELOOP:
        raise InstrumentBundleResolutionError(
            "symlink_member_forbidden",
            f"bundle member {relative_path!r} traverses a symlink",
        ) from error
    raise InstrumentBundleResolutionError(
        "bundle_member_unreadable",
        f"bundle member {relative_path!r} failed during {action}",
    ) from error


def _relative_component_stat(
    *,
    parent_descriptor: int,
    component: str,
    relative_path: str,
) -> os.stat_result:
    try:
        component_stat = os.stat(
            component,
            dir_fd=parent_descriptor,
            follow_symlinks=False,
        )
    except OSError as error:
        _raise_member_os_error(
            relative_path=relative_path,
            action="path inspection",
            error=error,
        )
    if stat.S_ISLNK(component_stat.st_mode):
        raise InstrumentBundleResolutionError(
            "symlink_member_forbidden",
            f"bundle member {relative_path!r} traverses a symlink",
        )
    return component_stat


def _open_relative_component(
    *,
    parent_descriptor: int,
    component: str,
    relative_path: str,
    directory: bool,
) -> int:
    try:
        return os.open(
            component,
            _secure_open_flags(directory=directory),
            dir_fd=parent_descriptor,
        )
    except OSError as error:
        if directory and error.errno in {errno.ELOOP, errno.ENOTDIR}:
            raise InstrumentBundleResolutionError(
                "bundle_member_unreadable",
                f"bundle member {relative_path!r} changed during traversal",
            ) from error
        _raise_member_os_error(
            relative_path=relative_path,
            action="descriptor open",
            error=error,
        )


def _opened_identity(
    *,
    descriptor: int,
    relative_path: str,
) -> tuple[os.stat_result, FileIdentity]:
    try:
        opened_stat = os.fstat(descriptor)
    except OSError as error:
        _raise_member_os_error(
            relative_path=relative_path,
            action="descriptor inspection",
            error=error,
        )
    return opened_stat, (opened_stat.st_dev, opened_stat.st_ino)


def _close_descriptors(descriptors: list[int]) -> None:
    for descriptor in reversed(descriptors):
        try:
            os.close(descriptor)
        except OSError:
            pass


@contextmanager
def _open_bundle_member(
    *,
    bundle_root: Path,
    relative_path: str,
    expected_root_identity: FileIdentity | None,
    seen_files: dict[FileIdentity, str],
) -> Iterator[_OpenedBundleMember]:
    parts = PurePosixPath(relative_path).parts
    if not parts:
        raise InstrumentBundleResolutionError(
            "bundle_member_unreadable",
            "bundle member path must name a file",
        )
    descriptors: list[int] = []
    try:
        try:
            root_before = bundle_root.stat()
            root_descriptor = os.open(
                bundle_root,
                _secure_open_flags(directory=True),
            )
        except OSError as error:
            _raise_member_os_error(
                relative_path=relative_path,
                action="bundle-root open",
                error=error,
            )
        descriptors.append(root_descriptor)
        root_after, root_identity = _opened_identity(
            descriptor=root_descriptor,
            relative_path=relative_path,
        )
        root_before_identity = (root_before.st_dev, root_before.st_ino)
        if (
            not stat.S_ISDIR(root_after.st_mode)
            or root_before_identity != root_identity
            or (
                expected_root_identity is not None
                and expected_root_identity != root_identity
            )
        ):
            raise InstrumentBundleResolutionError(
                "bundle_member_unreadable",
                f"bundle root changed while opening {relative_path!r}",
            )

        parent_descriptor = root_descriptor
        for component in parts[:-1]:
            before = _relative_component_stat(
                parent_descriptor=parent_descriptor,
                component=component,
                relative_path=relative_path,
            )
            if not stat.S_ISDIR(before.st_mode):
                raise InstrumentBundleResolutionError(
                    "bundle_member_unreadable",
                    f"bundle member {relative_path!r} has a non-directory parent",
                )
            directory_descriptor = _open_relative_component(
                parent_descriptor=parent_descriptor,
                component=component,
                relative_path=relative_path,
                directory=True,
            )
            descriptors.append(directory_descriptor)
            after, after_identity = _opened_identity(
                descriptor=directory_descriptor,
                relative_path=relative_path,
            )
            before_identity = (before.st_dev, before.st_ino)
            if not stat.S_ISDIR(after.st_mode) or before_identity != after_identity:
                raise InstrumentBundleResolutionError(
                    "bundle_member_unreadable",
                    f"bundle member {relative_path!r} changed during traversal",
                )
            parent_descriptor = directory_descriptor

        final_component = parts[-1]
        before = _relative_component_stat(
            parent_descriptor=parent_descriptor,
            component=final_component,
            relative_path=relative_path,
        )
        member_descriptor = _open_relative_component(
            parent_descriptor=parent_descriptor,
            component=final_component,
            relative_path=relative_path,
            directory=False,
        )
        descriptors.append(member_descriptor)
        after, identity = _opened_identity(
            descriptor=member_descriptor,
            relative_path=relative_path,
        )
        before_identity = (before.st_dev, before.st_ino)
        if before_identity != identity:
            raise InstrumentBundleResolutionError(
                "bundle_member_unreadable",
                f"bundle member {relative_path!r} changed while opening",
            )
        if not stat.S_ISREG(after.st_mode):
            raise InstrumentBundleResolutionError(
                "bundle_member_not_regular_file",
                f"bundle member {relative_path!r} is not a regular file",
            )
        if after.st_nlink != 1:
            raise InstrumentBundleResolutionError(
                "bundle_member_alias",
                f"bundle member {relative_path!r} has multiple hard links",
            )
        previous = seen_files.get(identity)
        if previous is not None:
            raise InstrumentBundleResolutionError(
                "bundle_member_alias",
                f"{relative_path!r} aliases already indexed member {previous!r}",
            )
        seen_files[identity] = relative_path
        yield _OpenedBundleMember(
            source_path=bundle_root.joinpath(*parts),
            descriptor=member_descriptor,
            root_identity=root_identity,
            identity=identity,
        )
    finally:
        _close_descriptors(descriptors)


def _read_descriptor_bytes(
    descriptor: int,
    *,
    maximum_bytes: int,
) -> bytes:
    chunks: list[bytes] = []
    size = 0
    read_limit = maximum_bytes + 1
    while size < read_limit:
        chunk = os.read(
            descriptor,
            min(_STREAM_CHUNK_BYTES, read_limit - size),
        )
        if not chunk:
            break
        chunks.append(chunk)
        size += len(chunk)
    return b"".join(chunks)


def _load_instrument_entry(
    entry: BundleArtifactEntry,
    *,
    bundle_root: Path,
    expected_root_identity: FileIdentity,
    seen_files: dict[FileIdentity, str],
) -> LoadedBundleArtifact:
    try:
        with _open_bundle_member(
            bundle_root=bundle_root,
            relative_path=entry.path,
            expected_root_identity=expected_root_identity,
            seen_files=seen_files,
        ) as opened:
            source = _read_descriptor_bytes(
                opened.descriptor,
                maximum_bytes=MAX_INSTRUMENT_ARTIFACT_BYTES,
            )
            source_path = opened.source_path
    except FileNotFoundError as error:
        raise InstrumentBundleResolutionError(
            "bundle_member_missing",
            f"{entry.path!r} disappeared before it could be read",
        ) from error
    except OSError as error:
        raise InstrumentBundleResolutionError(
            "bundle_member_unreadable",
            f"{entry.path!r} could not be read after path validation",
        ) from error
    try:
        loaded = _load_instrument_artifact_from_bytes(
            source,
            source_path=source_path,
            expected_source_sha256=entry.source_sha256,
        )
    except InstrumentArtifactIntegrityError as error:
        raise InstrumentBundleIntegrityError(
            "instrument_member_integrity_mismatch",
            f"{entry.path!r} differs from its declared content identity",
        ) from error
    except InstrumentArtifactSchemaError as error:
        raise InstrumentBundleSchemaError(
            "instrument_member_invalid",
            f"{entry.path!r} is not the declared canonical instrument artifact",
        ) from error
    actual = _artifact_ref_for(
        loaded.artifact,
        canonical_sha256=loaded.canonical_sha256,
    )
    if actual != entry.reference:
        raise InstrumentBundleIntegrityError(
            "instrument_member_identity_mismatch",
            f"{entry.path!r} does not match its indexed reference",
        )
    return LoadedBundleArtifact(
        reference=actual,
        value=loaded.artifact,
        source_path=loaded.source_path,
        source_sha256=loaded.source_sha256,
    )


def _load_registry_entry(
    entry: BundleArtifactEntry,
    *,
    bundle_root: Path,
    expected_root_identity: FileIdentity,
    seen_files: dict[FileIdentity, str],
) -> LoadedBundleArtifact:
    try:
        with _open_bundle_member(
            bundle_root=bundle_root,
            relative_path=entry.path,
            expected_root_identity=expected_root_identity,
            seen_files=seen_files,
        ) as opened:
            source = _read_descriptor_bytes(
                opened.descriptor,
                maximum_bytes=MAX_HYPOTHESIS_REGISTRY_BYTES,
            )
            source_path = opened.source_path
    except FileNotFoundError as error:
        raise InstrumentBundleResolutionError(
            "bundle_member_missing",
            f"{entry.path!r} disappeared before it could be read",
        ) from error
    except OSError as error:
        raise InstrumentBundleResolutionError(
            "bundle_member_unreadable",
            f"{entry.path!r} could not be read after path validation",
        ) from error
    try:
        loaded = _load_hypothesis_registry_from_bytes(
            source,
            source_path=source_path,
            expected_source_sha256=entry.source_sha256,
        )
    except HypothesisRegistryIntegrityError as error:
        raise InstrumentBundleIntegrityError(
            "registry_member_integrity_mismatch",
            f"{entry.path!r} differs from its declared content identity",
        ) from error
    except (
        HypothesisRegistrySchemaError,
        HypothesisRegistryPolicyError,
    ) as error:
        raise InstrumentBundleSchemaError(
            "registry_member_invalid",
            f"{entry.path!r} is not the declared strict registry",
        ) from error
    actual = _artifact_ref_for(
        loaded.registry,
        canonical_sha256=loaded.canonical_sha256,
    )
    if actual != entry.reference:
        raise InstrumentBundleIntegrityError(
            "registry_member_identity_mismatch",
            f"{entry.path!r} does not match its indexed reference",
        )
    return LoadedBundleArtifact(
        reference=actual,
        value=loaded.registry,
        source_path=loaded.source_path,
        source_sha256=loaded.source_sha256,
    )


def _load_context_entry(
    entry: BundleContextBankEntry,
    *,
    bundle_root: Path,
    expected_root_identity: FileIdentity,
    seen_files: dict[FileIdentity, str],
) -> LoadedBundleArtifact:
    try:
        with _open_bundle_member(
            bundle_root=bundle_root,
            relative_path=entry.path,
            expected_root_identity=expected_root_identity,
            seen_files=seen_files,
        ) as opened:
            source = _read_descriptor_bytes(
                opened.descriptor,
                maximum_bytes=MAX_CONTEXT_BANK_BYTES,
            )
            source_path = opened.source_path
    except FileNotFoundError as error:
        raise InstrumentBundleResolutionError(
            "bundle_member_missing",
            f"{entry.path!r} disappeared before it could be read",
        ) from error
    except OSError as error:
        raise InstrumentBundleResolutionError(
            "bundle_member_unreadable",
            f"{entry.path!r} could not be read after path validation",
        ) from error
    try:
        loaded = _load_context_bank_from_bytes(
            source,
            source_path=source_path,
            allowed_roles={entry.allowed_role},
            expected_source_sha256=entry.source_sha256,
        )
    except ContextBankIntegrityError as error:
        raise InstrumentBundleIntegrityError(
            "context_bank_member_integrity_mismatch",
            f"{entry.path!r} differs from its declared content identity",
        ) from error
    except ContextContractError as error:
        raise InstrumentBundleSchemaError(
            "context_bank_member_invalid",
            f"{entry.path!r} is not the declared role-bound context bank",
        ) from error
    actual = _artifact_ref_for(
        loaded.bank,
        canonical_sha256=loaded.canonical_sha256,
    )
    if actual != entry.reference:
        raise InstrumentBundleIntegrityError(
            "context_bank_member_identity_mismatch",
            f"{entry.path!r} does not match its indexed reference",
        )
    return LoadedBundleArtifact(
        reference=actual,
        value=loaded.bank,
        source_path=loaded.source_path,
        source_sha256=loaded.source_sha256,
    )


def _detect_cycle(
    adjacency: Mapping[ArtifactKey, tuple[ArtifactKey, ...]],
) -> None:
    state: dict[ArtifactKey, int] = {}

    for root in sorted(
        adjacency,
        key=lambda item: (item[0].value, item[1]),
    ):
        if state.get(root, 0) == 2:
            continue
        frames: list[tuple[ArtifactKey, int]] = [(root, 0)]
        path: list[ArtifactKey] = []
        path_positions: dict[ArtifactKey, int] = {}
        while frames:
            key, next_index = frames[-1]
            if state.get(key, 0) == 0:
                state[key] = 1
                path_positions[key] = len(path)
                path.append(key)

            targets = adjacency.get(key, ())
            while next_index < len(targets) and targets[next_index] not in adjacency:
                next_index += 1
            if next_index >= len(targets):
                state[key] = 2
                frames.pop()
                path_positions.pop(key)
                popped = path.pop()
                assert popped == key
                continue

            target = targets[next_index]
            frames[-1] = (key, next_index + 1)
            marker = state.get(target, 0)
            if marker == 0:
                frames.append((target, 0))
                continue
            if marker == 1:
                start = path_positions[target]
                cycle = (*path[start:], target)
                rendered = " -> ".join(
                    f"{artifact_type.value}:{artifact_id}"
                    for artifact_type, artifact_id in cycle
                )
                raise InstrumentBundleResolutionError(
                    "artifact_dependency_cycle",
                    f"logical artifact dependency cycle: {rendered}",
                )


def _reachable_from_roots(
    *,
    roots: tuple[ArtifactRef, ...],
    adjacency: Mapping[ArtifactKey, tuple[ArtifactKey, ...]],
) -> set[ArtifactKey]:
    pending = [(reference.artifact_type, reference.artifact_id) for reference in roots]
    reachable: set[ArtifactKey] = set()
    while pending:
        key = pending.pop()
        if key in reachable:
            continue
        reachable.add(key)
        pending.extend(adjacency.get(key, ()))
    return reachable


def _stream_payload_identity(
    descriptor: int,
    *,
    expected_byte_length: int,
) -> tuple[int, str]:
    digest = hashlib.sha256()
    size = 0
    read_limit = expected_byte_length + 1
    while size < read_limit:
        chunk = os.read(
            descriptor,
            min(_STREAM_CHUNK_BYTES, read_limit - size),
        )
        if not chunk:
            break
        size += len(chunk)
        digest.update(chunk)
    return size, digest.hexdigest()


def _read_bundle_manifest(
    path: str | Path,
    *,
    expected_source_sha256: str | None,
    expected_canonical_sha256: str | None,
    expected_root_identity: FileIdentity | None,
) -> tuple[
    InstrumentBundleManifest,
    Path,
    str,
    str,
    FileIdentity,
    FileIdentity,
]:
    if expected_source_sha256 is not None:
        require_sha256(
            expected_source_sha256,
            label="expected_source_sha256",
        )
    if expected_canonical_sha256 is not None:
        require_sha256(
            expected_canonical_sha256,
            label="expected_canonical_sha256",
        )
    requested = Path(path)
    try:
        is_symlink = requested.is_symlink()
    except OSError as error:
        raise InstrumentBundleSchemaError(
            "bundle_manifest_unreadable",
            "bundle manifest path cannot be inspected",
        ) from error
    if is_symlink:
        raise InstrumentBundleSchemaError(
            "bundle_manifest_symlink",
            "bundle manifest path must not be a symlink",
        )
    try:
        bundle_root = requested.parent.resolve(strict=True)
    except OSError as error:
        raise InstrumentBundleSchemaError(
            "bundle_manifest_unreadable",
            "bundle manifest parent cannot be resolved",
        ) from error
    source_path = bundle_root / requested.name
    manifest_seen_files: dict[FileIdentity, str] = {}
    try:
        with _open_bundle_member(
            bundle_root=bundle_root,
            relative_path=requested.name,
            expected_root_identity=expected_root_identity,
            seen_files=manifest_seen_files,
        ) as opened:
            source = _read_descriptor_bytes(
                opened.descriptor,
                maximum_bytes=MAX_INSTRUMENT_BUNDLE_BYTES,
            )
            source_path = opened.source_path
            root_identity = opened.root_identity
            manifest_identity = opened.identity
    except InstrumentBundleResolutionError as error:
        if error.code == "symlink_member_forbidden":
            raise InstrumentBundleSchemaError(
                "bundle_manifest_symlink",
                "bundle manifest path must not be a symlink",
            ) from error
        if error.code == "secure_member_open_unavailable":
            raise
        raise InstrumentBundleSchemaError(
            "bundle_manifest_unreadable",
            "bundle manifest cannot be opened securely",
        ) from error
    except OSError as error:
        raise InstrumentBundleSchemaError(
            "bundle_manifest_unreadable",
            "bundle manifest cannot be read",
        ) from error
    if len(source) > MAX_INSTRUMENT_BUNDLE_BYTES:
        raise InstrumentBundleSchemaError(
            "bundle_manifest_too_large",
            f"bundle manifest exceeds {MAX_INSTRUMENT_BUNDLE_BYTES} bytes",
        )
    source_sha256 = hashlib.sha256(source).hexdigest()
    if expected_source_sha256 is not None and source_sha256 != expected_source_sha256:
        raise InstrumentBundleIntegrityError(
            "bundle_source_digest_mismatch",
            "bundle manifest source SHA-256 differs",
        )
    try:
        parsed = parse_canonical_json(
            source,
            label="instrument bundle",
        )
        manifest = InstrumentBundleManifest.from_dict(
            require_mapping(parsed, label="instrument bundle")
        )
    except (CanonicalJsonError, ContractValidationError, TypeError) as error:
        raise InstrumentBundleSchemaError(
            "bundle_manifest_invalid",
            str(error),
        ) from error
    if manifest.canonical_bytes != source:
        raise InstrumentBundleIntegrityError(
            "bundle_canonical_reconstruction_mismatch",
            "bundle manifest typed reconstruction differs",
        )
    canonical_sha256 = manifest.canonical_sha256
    if (
        expected_canonical_sha256 is not None
        and canonical_sha256 != expected_canonical_sha256
    ):
        raise InstrumentBundleIntegrityError(
            "bundle_canonical_digest_mismatch",
            "bundle manifest canonical SHA-256 differs",
        )
    return (
        manifest,
        source_path,
        source_sha256,
        canonical_sha256,
        root_identity,
        manifest_identity,
    )


def load_instrument_bundle(
    path: str | Path,
    *,
    expected_source_sha256: str | None = None,
    expected_canonical_sha256: str | None = None,
    expected_root_identity: FileIdentity | None = None,
) -> LoadedInstrumentBundle:
    """Validate a canonical closed bundle without decoding payload values.

    ``expected_root_identity`` lets a publisher bind validation to an already
    opened bundle-directory inode instead of trusting a display path alone.
    """

    if expected_root_identity is not None and (
        not isinstance(expected_root_identity, tuple)
        or len(expected_root_identity) != 2
        or any(
            isinstance(value, bool) or not isinstance(value, int)
            for value in expected_root_identity
        )
    ):
        raise TypeError(
            "expected_root_identity must be a (device, inode) integer tuple"
        )

    (
        manifest,
        source_path,
        source_sha256,
        canonical_sha256,
        root_identity,
        manifest_identity,
    ) = _read_bundle_manifest(
        path,
        expected_source_sha256=expected_source_sha256,
        expected_canonical_sha256=expected_canonical_sha256,
        expected_root_identity=expected_root_identity,
    )
    bundle_root = source_path.parent
    seen_files: dict[FileIdentity, str] = {manifest_identity: source_path.name}

    members: list[LoadedBundleArtifact] = []
    for entry in manifest.instrument_artifacts:
        members.append(
            _load_instrument_entry(
                entry,
                bundle_root=bundle_root,
                expected_root_identity=root_identity,
                seen_files=seen_files,
            )
        )
    for entry in manifest.hypothesis_registries:
        members.append(
            _load_registry_entry(
                entry,
                bundle_root=bundle_root,
                expected_root_identity=root_identity,
                seen_files=seen_files,
            )
        )
    for entry in manifest.context_banks:
        members.append(
            _load_context_entry(
                entry,
                bundle_root=bundle_root,
                expected_root_identity=root_identity,
                seen_files=seen_files,
            )
        )

    index = {member.logical_key: member for member in members}
    if len(index) != len(members):
        raise InstrumentBundleResolutionError(
            "duplicate_artifact_identity",
            "multiple loaded artifacts share one type/id identity",
        )

    artifact_uses = tuple(
        use for member in members for use in iter_artifact_reference_uses(member)
    )
    adjacency: dict[ArtifactKey, tuple[ArtifactKey, ...]] = {}
    for member in members:
        targets = tuple(
            sorted(
                {
                    (
                        use.reference.artifact_type,
                        use.reference.artifact_id,
                    )
                    for use in artifact_uses
                    if use.owner == member.reference
                },
                key=lambda item: (item[0].value, item[1]),
            )
        )
        adjacency[member.logical_key] = targets

    for use in artifact_uses:
        key = (
            use.reference.artifact_type,
            use.reference.artifact_id,
        )
        if key not in index:
            raise InstrumentBundleResolutionError(
                "artifact_reference_missing",
                f"{use.path} points outside the closed bundle",
            )
    _detect_cycle(adjacency)
    for use in artifact_uses:
        target = index[
            (
                use.reference.artifact_type,
                use.reference.artifact_id,
            )
        ]
        if target.reference != use.reference:
            raise InstrumentBundleResolutionError(
                "artifact_reference_identity_mismatch",
                f"{use.path} differs from the resolved artifact identity",
            )

    reachable = _reachable_from_roots(
        roots=manifest.roots,
        adjacency=adjacency,
    )
    unreachable = set(index) - reachable
    if unreachable:
        rendered = sorted(
            f"{artifact_type.value}:{artifact_id}"
            for artifact_type, artifact_id in unreachable
        )
        raise InstrumentBundleResolutionError(
            "unreferenced_artifact_entry",
            f"artifact entries are unreachable from roots: {rendered}",
        )

    payload_uses = tuple(
        use for member in members for use in iter_payload_reference_uses(member)
    )
    payload_refs_by_sha: dict[str, set[PayloadRef]] = {}
    for use in payload_uses:
        payload_refs_by_sha.setdefault(
            use.reference.sha256,
            set(),
        ).add(use.reference)
    reclassified = [
        digest
        for digest, references in payload_refs_by_sha.items()
        if len(references) != 1
    ]
    if reclassified:
        raise InstrumentBundleResolutionError(
            "payload_digest_reclassified",
            "one payload digest is used with conflicting metadata",
        )
    referenced_payloads = {use.reference for use in payload_uses}
    indexed_payloads = {entry.reference for entry in manifest.payloads}
    missing_payloads = referenced_payloads - indexed_payloads
    if missing_payloads:
        raise InstrumentBundleResolutionError(
            "payload_reference_missing",
            f"{len(missing_payloads)} payload references are not indexed",
        )
    extra_payloads = indexed_payloads - referenced_payloads
    if extra_payloads:
        raise InstrumentBundleResolutionError(
            "unreferenced_payload_entry",
            f"{len(extra_payloads)} payload entries are not referenced",
        )

    from .bundle_validation import validate_bundle_cross_manifest

    cross_manifest_join_count = validate_bundle_cross_manifest(
        members=tuple(members),
        index=MappingProxyType(index),
    )

    loaded_payloads: list[LoadedBundlePayload] = []
    for entry in manifest.payloads:
        try:
            with _open_bundle_member(
                bundle_root=bundle_root,
                relative_path=entry.path,
                expected_root_identity=root_identity,
                seen_files=seen_files,
            ) as opened:
                size, digest = _stream_payload_identity(
                    opened.descriptor,
                    expected_byte_length=entry.reference.byte_length,
                )
        except FileNotFoundError as error:
            raise InstrumentBundleResolutionError(
                "bundle_member_missing",
                f"{entry.path!r} disappeared before it could be read",
            ) from error
        except OSError as error:
            raise InstrumentBundleResolutionError(
                "bundle_member_unreadable",
                f"{entry.path!r} could not be read after path validation",
            ) from error
        if size != entry.reference.byte_length:
            raise InstrumentBundleIntegrityError(
                "payload_byte_length_mismatch",
                f"payload {entry.path!r} byte length differs",
            )
        if digest != entry.reference.sha256:
            raise InstrumentBundleIntegrityError(
                "payload_digest_mismatch",
                f"payload {entry.path!r} SHA-256 differs",
            )
        loaded_payloads.append(
            LoadedBundlePayload(
                reference=entry.reference,
            )
        )

    return LoadedInstrumentBundle(
        manifest=manifest,
        source_path=source_path,
        source_sha256=source_sha256,
        canonical_sha256=canonical_sha256,
        artifacts=tuple(
            sorted(
                members,
                key=lambda member: (
                    member.reference.artifact_type.value,
                    member.reference.artifact_id,
                ),
            )
        ),
        payloads=tuple(
            sorted(
                loaded_payloads,
                key=lambda payload: (
                    payload.reference.sha256,
                    payload.reference.identity_sha256,
                ),
            )
        ),
        artifact_reference_count=len(artifact_uses),
        payload_reference_count=len(payload_uses),
        cross_manifest_join_count=cross_manifest_join_count,
    )
