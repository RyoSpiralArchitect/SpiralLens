"""Private no-replace publication of the D7 v1 descriptive result.

The sole high-level operation accepts only repository and Git coordinates.  It
first reauthenticates exact commit A, derives the result from the six frozen
historical inputs, and then owns the result stage through publication.  A
caller cannot supply result bytes, a path, a stage, or filesystem callbacks.

Importing this module performs no I/O.  Publication creates no Git commit and
grants no materialization, execution, scientific, or retry authority.  Any
failure after stage creation retains the observable evidence without cleanup,
resume, overwrite, or retry.
"""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path, PurePosixPath
import stat

from spirallens._repository_context import RepositoryContext
from spirallens.core.canonical import sha256_bytes

from .common import QualificationContractError, require_sha256
from . import confirmation_v1_materialization as verification
from . import confirmation_v1_post_d6_descriptive as descriptive
from . import confirmation_v1_private_publication as private_publication
from . import confirmation_v1_records as records

__all__: tuple[str, ...] = ()


_MODULE_PATH = "src/spirallens/qualification/confirmation_v1_result_publication.py"
_RESULT_PATH = (
    "experiments/qualification/d7_spectral_moment_confirmation_v1/"
    "post-d6-descriptive-analysis-result.json"
)
_STAGE_MARKER = ".private-stage."


class D7V1ResultPublicationFailure(QualificationContractError):
    """Typed non-retryable result-publication failure state."""

    __slots__ = (
        "cleanup_authorized",
        "destination",
        "disposition",
        "publication_visible",
        "resume_authorized",
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
        self.resume_authorized = False


@dataclass(frozen=True, slots=True)
class D7V1PrivateResultPublicationReceipt:
    """In-memory structural facts from one completed result publication."""

    destination: Path
    source_commit: str
    artifact_commit: str
    result_sha256: str
    result_byte_count: int
    native_primitive: str
    namespace_atomic: bool = True
    result_fsync_completed: bool = True
    parent_directory_fsync_completed: bool = True
    same_inode_reloaded: bool = True
    canonical_bytes_reloaded: bool = True
    artifact_commit_a_verified: bool = True
    result_published: bool = True
    structural_only: bool = True
    retry_authorized: bool = False
    cleanup_authorized: bool = False
    authority_granted: bool = False
    materialization_authorized: bool = False
    result_commit_b_created: bool = False
    result_commit_b_verified: bool = False
    execution_authorized: bool = False
    scientific_claim_eligible: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.destination, Path) or not self.destination.is_absolute():
            raise TypeError("destination must be an absolute Path")
        verification._full_commit(self.source_commit, label="source_commit")
        verification._full_commit(self.artifact_commit, label="artifact_commit")
        require_sha256(self.result_sha256, label="result_sha256")
        if (
            type(self.result_byte_count) is not int
            or self.result_byte_count < 1
            or self.result_byte_count
            > records.D7_V1_POSTSELECTION_RESULT_MAX_RECORD_BYTES
        ):
            raise QualificationContractError("result_byte_count is outside its cap")
        if type(self.native_primitive) is not str or not self.native_primitive:
            raise QualificationContractError("native_primitive must be nonempty")
        if (
            self.namespace_atomic is not True
            or self.result_fsync_completed is not True
            or self.parent_directory_fsync_completed is not True
            or self.same_inode_reloaded is not True
            or self.canonical_bytes_reloaded is not True
            or self.artifact_commit_a_verified is not True
            or self.result_published is not True
            or self.structural_only is not True
            or self.retry_authorized is not False
            or self.cleanup_authorized is not False
            or self.authority_granted is not False
            or self.materialization_authorized is not False
            or self.result_commit_b_created is not False
            or self.result_commit_b_verified is not False
            or self.execution_authorized is not False
            or self.scientific_claim_eligible is not False
        ):
            raise QualificationContractError(
                "result publication receipt facts exceed their structural boundary"
            )


def _require_artifact_head_and_clean_status(
    repository: RepositoryContext,
    artifact_commit: str,
    *,
    allowed_untracked: set[str],
) -> None:
    try:
        private_publication._require_head_and_clean_status(
            repository, artifact_commit, allowed_untracked=allowed_untracked
        )
    except QualificationContractError as error:
        if str(error) != "repository HEAD differs from source S":
            raise
        raise QualificationContractError(
            "repository HEAD differs from artifact commit A"
        ) from error


def _publication_coordinates(
    repository: RepositoryContext,
    protocol: verification.D7V1MaterializationProtocol,
    result_sha256: str,
) -> tuple[tuple[str, ...], str, str, Path, Path, str]:
    digest = require_sha256(result_sha256, label="result_sha256")
    result_path = verification._coordinates(protocol)["descriptive_result"]
    if result_path != _RESULT_PATH:
        raise QualificationContractError("descriptive result coordinate differs")
    relative = PurePosixPath(result_path)
    if len(relative.parts) < 2:
        raise QualificationContractError("descriptive result must have a parent")
    destination_leaf = private_publication._leaf(
        relative.name, label="result destination leaf"
    )
    stage_leaf = private_publication._leaf(
        f".{destination_leaf}{_STAGE_MARKER}{digest}",
        label="result private-stage leaf",
    )
    parent_parts = tuple(relative.parts[:-1])
    destination = repository.root.joinpath(*relative.parts)
    stage_path = repository.root.joinpath(*parent_parts, stage_leaf)
    return (
        parent_parts,
        destination_leaf,
        stage_leaf,
        destination,
        stage_path,
        result_path,
    )


def _require_result_publisher_source_bound(
    repository: RepositoryContext,
    joined: verification.D7V1JoinedRecords,
) -> None:
    if not repository.matches_imported_file(
        imported_file=__file__, repository_path=_MODULE_PATH
    ):
        raise QualificationContractError(
            "result-publication module import origin differs from repository"
        )
    c1 = joined.record(records.D7V1C1SourceSetRecord.artifact_role)
    if not isinstance(c1, records.D7V1C1SourceSetRecord):
        raise QualificationContractError("joined source closure has the wrong C1 role")
    members = verification._source_members_from_c1(c1)
    by_path = {member.repository_path: member for member in members}
    if _MODULE_PATH not in by_path:
        raise QualificationContractError(
            "C1 source closure omits the result-publication module"
        )
    mode, committed = verification._git_blob(
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
        or member.git_mode != mode
        or member.sha256 != sha256_bytes(committed)
        or member.byte_count != len(committed)
    ):
        raise QualificationContractError(
            "executing result-publication source differs from source S"
        )


def _attempt(
    joined: verification.D7V1JoinedRecords,
) -> records.D7V1OfficialExecutionAttemptReservation:
    value = joined.record(records.D7V1OfficialExecutionAttemptReservation.artifact_role)
    if not isinstance(value, records.D7V1OfficialExecutionAttemptReservation):
        raise QualificationContractError("joined result parent is not an attempt")
    return value


def _strict_result_source(
    source: bytes,
    *,
    expected_sha256: str,
) -> records.D7V1PostselectionDescriptiveResult:
    digest = require_sha256(expected_sha256, label="expected result sha256")
    if (
        type(source) is not bytes
        or not source
        or len(source) > records.D7_V1_POSTSELECTION_RESULT_MAX_RECORD_BYTES
    ):
        raise QualificationContractError("descriptive result violates its byte cap")
    if sha256_bytes(source) != digest:
        raise QualificationContractError("descriptive result digest differs")
    return records.D7V1PostselectionDescriptiveResult.from_canonical_bytes(
        source,
        expected_sha256=digest,
    )


def _derive_fresh_result(
    repository: RepositoryContext,
    verified_a: verification.D7V1CommitVerification,
) -> records.D7V1PostselectionDescriptiveResult:
    historical, _bindings = verification._historical_sources_and_bindings(
        repository, verified_a.joined.protocol
    )
    attempt = _attempt(verified_a.joined)
    result = descriptive._derive_d7_v1_post_d6_descriptive_result(
        historical_plan_source=historical["historical-post-d6-plan"],
        parent_protocol_source=historical["parent-protocol"],
        parent_result_source=historical["parent-result"],
        parent_manifest_source=historical["parent-manifest"],
        parent_consumption_source=historical["parent-consumption"],
        parent_d6_decision_source=historical["parent-d6-decision"],
        parent_attempt=attempt,
        chronology_receipt=verified_a.joined.receipt,
    )
    if not isinstance(result, records.D7V1PostselectionDescriptiveResult):
        raise QualificationContractError("fresh derivation returned the wrong record")
    candidate = _strict_result_source(
        result.canonical_bytes,
        expected_sha256=result.canonical_sha256,
    )
    rejoined_historical = verification._verify_result_joins(
        repository,
        verified_a.joined.protocol,
        verified_a.joined,
        candidate,
    )
    descriptive._verify_d7_v1_post_d6_descriptive_result(
        candidate,
        historical_plan_source=rejoined_historical["historical-post-d6-plan"],
        parent_protocol_source=rejoined_historical["parent-protocol"],
        parent_result_source=rejoined_historical["parent-result"],
        parent_manifest_source=rejoined_historical["parent-manifest"],
        parent_consumption_source=rejoined_historical["parent-consumption"],
        parent_d6_decision_source=rejoined_historical["parent-d6-decision"],
        parent_attempt=attempt,
        chronology_receipt=verified_a.joined.receipt,
    )
    expected_path = verification._coordinates(verified_a.joined.protocol)[
        "descriptive_result"
    ]
    if verification._record_repository_path(candidate) != expected_path:
        raise QualificationContractError("fresh result repository path differs")
    return candidate


def _require_owned_result_stat(
    observed: os.stat_result,
    *,
    expected_size: int,
) -> None:
    if (
        not stat.S_ISREG(observed.st_mode)
        or observed.st_nlink != 1
        or stat.S_IMODE(observed.st_mode) != 0o600
        or observed.st_size != expected_size
    ):
        raise QualificationContractError("owned result file identity differs")


def _read_owned_result(
    descriptor: int,
    *,
    expected_source: bytes,
    expected_sha256: str,
    expected_identity: private_publication._StatIdentity,
) -> records.D7V1PostselectionDescriptiveResult:
    observed = os.fstat(descriptor)
    _require_owned_result_stat(observed, expected_size=len(expected_source))
    if private_publication._stat_identity(observed) != expected_identity:
        raise QualificationContractError("owned result inode changed")
    source = private_publication._read_file_descriptor(
        descriptor,
        maximum_bytes=records.D7_V1_POSTSELECTION_RESULT_MAX_RECORD_BYTES,
    )
    if source != expected_source:
        raise QualificationContractError("owned result bytes changed")
    return _strict_result_source(source, expected_sha256=expected_sha256)


def _reload_published_result(
    repository: RepositoryContext,
    *,
    parent_parts: tuple[str, ...],
    parent_fd: int,
    destination_leaf: str,
    held_fd: int,
    held_identity: private_publication._StatIdentity,
    expected_source: bytes,
    expected_sha256: str,
    verified_a: verification.D7V1CommitVerification,
) -> records.D7V1PostselectionDescriptiveResult:
    private_publication._require_live_parent_anchor(repository, parent_parts, parent_fd)
    entry = private_publication._entry_stat(parent_fd, destination_leaf)
    if entry is None or private_publication._stat_identity(entry) != held_identity:
        raise QualificationContractError(
            "published result path differs from the held inode"
        )
    _require_owned_result_stat(entry, expected_size=len(expected_source))
    if not hasattr(os, "O_NOFOLLOW"):
        raise QualificationContractError("result reload requires O_NOFOLLOW")
    flags = os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)
    reloaded_fd = -1
    try:
        reloaded_fd = os.open(destination_leaf, flags, dir_fd=parent_fd)
        reloaded = os.fstat(reloaded_fd)
        if private_publication._stat_identity(reloaded) != held_identity:
            raise QualificationContractError(
                "separately opened result differs from the held inode"
            )
        candidate = _read_owned_result(
            reloaded_fd,
            expected_source=expected_source,
            expected_sha256=expected_sha256,
            expected_identity=held_identity,
        )
    finally:
        private_publication._close_quietly(reloaded_fd)
    verification._verify_result_joins(
        repository,
        verified_a.joined.protocol,
        verified_a.joined,
        candidate,
    )
    held_candidate = _read_owned_result(
        held_fd,
        expected_source=expected_source,
        expected_sha256=expected_sha256,
        expected_identity=held_identity,
    )
    if held_candidate.canonical_bytes != candidate.canonical_bytes:
        raise QualificationContractError("held and reloaded result records differ")
    return candidate


def _publication_outcome(
    parent_fd: int,
    *,
    stage_leaf: str,
    destination_leaf: str,
    held_fd: int,
    held_identity: private_publication._StatIdentity | None,
) -> str:
    stage = private_publication._entry_stat(parent_fd, stage_leaf)
    destination = private_publication._entry_stat(parent_fd, destination_leaf)
    if held_fd < 0 or held_identity is None:
        if stage is not None and destination is not None:
            return "foreign-stage-and-destination"
        if stage is not None:
            return "foreign-stage"
        if destination is not None:
            return "foreign-destination"
        return "absent"
    try:
        held = os.fstat(held_fd)
    except OSError:
        return "identity-unknown"
    if private_publication._stat_identity(held) != held_identity:
        return "identity-unknown"
    stage_owned = (
        stage is not None and private_publication._stat_identity(stage) == held_identity
    )
    destination_owned = (
        destination is not None
        and private_publication._stat_identity(destination) == held_identity
    )
    if destination_owned and stage is None:
        return "published"
    if stage_owned and destination is None:
        return "stage-retained"
    if stage_owned and destination is not None and not destination_owned:
        return "destination-collision-stage-retained"
    return "ambiguous"


def _failure_facts(
    *,
    outcome: str | None,
    creation_attempted: bool,
    stage_created: bool,
    parent_fsync_completed: bool,
    stage_path: Path | None,
) -> tuple[str, Path | None, bool | None, bool | None]:
    if outcome == "published":
        return (
            "published_verification_unknown"
            if parent_fsync_completed
            else "published_durability_unknown",
            None,
            False,
            True,
        )
    if outcome == "stage-retained":
        return "stage_partial_retained", stage_path, True, False
    if outcome == "destination-collision-stage-retained":
        return "destination_collision_stage_retained", stage_path, True, None
    if stage_created:
        return "rename_outcome_ambiguous", None, None, None
    if creation_attempted:
        return "stage_creation_state_unknown", None, None, None
    return "preflight_rejected", None, None, None


def _publish_d7_v1_descriptive_result_no_replace(
    repository: RepositoryContext,
    *,
    source_commit: str,
    artifact_commit: str,
) -> D7V1PrivateResultPublicationReceipt:
    """Freshly derive and exclusively publish the fixed v1 result file."""

    if not isinstance(repository, RepositoryContext):
        raise TypeError("repository must be RepositoryContext")
    fixed_relative = PurePosixPath(_RESULT_PATH)
    destination = repository.root.joinpath(*fixed_relative.parts)
    parent_parts = tuple(fixed_relative.parts[:-1])
    destination_leaf = fixed_relative.name
    stage_leaf = ""
    stage_path: Path | None = None
    parent_fd = -1
    held_fd = -1
    held_identity: private_publication._StatIdentity | None = None
    creation_attempted = False
    stage_created = False
    parent_fsync_completed = False
    try:
        verification._require_complete_git_history(repository)
        source = verification._resolve_commit(
            repository, source_commit, label="source_commit S"
        )
        artifact = verification._resolve_commit(
            repository, artifact_commit, label="artifact_commit A"
        )
        _require_artifact_head_and_clean_status(
            repository, artifact, allowed_untracked=set()
        )
        verified_a = verification._verify_and_load_d7_v1_commit_a(
            repository,
            source_commit=source,
            artifact_commit=artifact,
        )
        if (
            verified_a.source_commit != source
            or verified_a.artifact_commit != artifact
            or verified_a.result_commit is not None
            or verified_a.result is not None
        ):
            raise QualificationContractError("commit A verification facts differ")
        private_publication._require_publisher_source_bound(
            repository, verified_a.joined
        )
        _require_result_publisher_source_bound(repository, verified_a.joined)

        result = _derive_fresh_result(repository, verified_a)
        result_source = result.canonical_bytes
        result_sha256 = result.canonical_sha256
        (
            parent_parts,
            destination_leaf,
            stage_leaf,
            destination,
            stage_path,
            result_path,
        ) = _publication_coordinates(
            repository, verified_a.joined.protocol, result_sha256
        )
        stage_repository_path = PurePosixPath(*parent_parts, stage_leaf).as_posix()

        primitive, native_rename = private_publication._native_exclusive_rename()
        parent_fd = private_publication._open_publication_parent(
            repository, parent_parts
        )
        names = set(os.listdir(parent_fd))
        reserved_prefix = f".{destination_leaf}{_STAGE_MARKER}"
        if destination_leaf in names:
            raise D7V1ResultPublicationFailure(
                "result destination already exists",
                disposition="destination_collision",
                destination=destination,
                stage_path=None,
                stage_retained=None,
                publication_visible=None,
            )
        stages = sorted(name for name in names if name.startswith(reserved_prefix))
        if stages:
            raise D7V1ResultPublicationFailure(
                f"result private-stage namespace already contains {stages}",
                disposition="stage_collision_state_unknown",
                destination=destination,
                stage_path=stage_path if stage_leaf in stages else None,
                stage_retained=None,
                publication_visible=None,
            )
        private_publication._require_live_parent_anchor(
            repository, parent_parts, parent_fd
        )
        os.fsync(parent_fd)

        creation_attempted = True
        held_fd = os.open(
            stage_leaf,
            private_publication._file_create_flags(),
            0o600,
            dir_fd=parent_fd,
        )
        stage_created = True
        os.fchmod(held_fd, 0o600)
        held_identity = private_publication._stat_identity(os.fstat(held_fd))
        os.fsync(parent_fd)
        private_publication._write_all(held_fd, result_source)
        os.fsync(held_fd)
        staged = _read_owned_result(
            held_fd,
            expected_source=result_source,
            expected_sha256=result_sha256,
            expected_identity=held_identity,
        )
        if staged.canonical_bytes != result_source:
            raise QualificationContractError("staged result record differs")
        verification._verify_result_joins(
            repository,
            verified_a.joined.protocol,
            verified_a.joined,
            staged,
        )
        stage_entry = private_publication._entry_stat(parent_fd, stage_leaf)
        if (
            stage_entry is None
            or private_publication._stat_identity(stage_entry) != held_identity
        ):
            raise QualificationContractError("private result stage identity differs")
        _require_owned_result_stat(stage_entry, expected_size=len(result_source))
        if private_publication._entry_stat(parent_fd, destination_leaf) is not None:
            raise QualificationContractError(
                "result destination appeared before rename"
            )
        private_publication._require_live_parent_anchor(
            repository, parent_parts, parent_fd
        )
        _require_artifact_head_and_clean_status(
            repository, artifact, allowed_untracked={stage_repository_path}
        )

        rename_error: OSError | None = None
        try:
            native_rename(parent_fd, stage_leaf, destination_leaf)
        except OSError as error:
            rename_error = error
        rename_outcome = _publication_outcome(
            parent_fd,
            stage_leaf=stage_leaf,
            destination_leaf=destination_leaf,
            held_fd=held_fd,
            held_identity=held_identity,
        )
        if rename_error is not None:
            raise rename_error
        if rename_outcome == "destination-collision-stage-retained":
            raise QualificationContractError("result destination collision")
        if rename_outcome == "stage-retained":
            raise QualificationContractError(
                "native rename returned without moving the result stage",
            )
        if rename_outcome != "published":
            raise D7V1ResultPublicationFailure(
                str(rename_error or "native rename namespace is ambiguous"),
                disposition="rename_outcome_ambiguous",
                destination=destination,
                stage_path=None,
                stage_retained=None,
                publication_visible=None,
            ) from rename_error
        _reload_published_result(
            repository,
            parent_parts=parent_parts,
            parent_fd=parent_fd,
            destination_leaf=destination_leaf,
            held_fd=held_fd,
            held_identity=held_identity,
            expected_source=result_source,
            expected_sha256=result_sha256,
            verified_a=verified_a,
        )
        os.fsync(parent_fd)
        parent_fsync_completed = True
        _reload_published_result(
            repository,
            parent_parts=parent_parts,
            parent_fd=parent_fd,
            destination_leaf=destination_leaf,
            held_fd=held_fd,
            held_identity=held_identity,
            expected_source=result_source,
            expected_sha256=result_sha256,
            verified_a=verified_a,
        )
        _require_artifact_head_and_clean_status(
            repository, artifact, allowed_untracked={result_path}
        )
        _reload_published_result(
            repository,
            parent_parts=parent_parts,
            parent_fd=parent_fd,
            destination_leaf=destination_leaf,
            held_fd=held_fd,
            held_identity=held_identity,
            expected_source=result_source,
            expected_sha256=result_sha256,
            verified_a=verified_a,
        )
        return D7V1PrivateResultPublicationReceipt(
            destination=destination,
            source_commit=source,
            artifact_commit=artifact,
            result_sha256=result_sha256,
            result_byte_count=len(result_source),
            native_primitive=primitive,
        )
    except D7V1ResultPublicationFailure:
        raise
    except BaseException as error:
        outcome: str | None = None
        namespace_reauthenticated = False
        if parent_fd >= 0:
            try:
                if stage_leaf:
                    outcome = _publication_outcome(
                        parent_fd,
                        stage_leaf=stage_leaf,
                        destination_leaf=destination_leaf,
                        held_fd=held_fd,
                        held_identity=held_identity,
                    )
                private_publication._require_live_parent_anchor(
                    repository, parent_parts, parent_fd
                )
                namespace_reauthenticated = True
            except BaseException:
                namespace_reauthenticated = False
                outcome = None
        if parent_fd >= 0 and not namespace_reauthenticated:
            disposition = "namespace_reauthentication_failed"
            reported_stage = None
            stage_retained: bool | None = None
            publication_visible: bool | None = None
        else:
            (
                disposition,
                reported_stage,
                stage_retained,
                publication_visible,
            ) = _failure_facts(
                outcome=outcome,
                creation_attempted=creation_attempted,
                stage_created=stage_created,
                parent_fsync_completed=parent_fsync_completed,
                stage_path=stage_path,
            )
        raise D7V1ResultPublicationFailure(
            str(error),
            disposition=disposition,
            destination=destination,
            stage_path=reported_stage,
            stage_retained=stage_retained,
            publication_visible=publication_visible,
        ) from error
    finally:
        private_publication._close_quietly(held_fd)
        private_publication._close_quietly(parent_fd)
