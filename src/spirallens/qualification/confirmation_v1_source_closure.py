"""Choice-free structural C1/C2 candidate construction for D7 v1.

The sole builder accepts an explicit repository and a full commit only as an
assertion of the exact clean current ``HEAD``.  It derives the complete source
inventory from that Git tree, constructs the current C1 and C2 record types,
canonically reloads them, and rejoins them through the materialization
verifier.  It accepts no caller-selected paths, bytes, record identifiers,
runtime facts, publication coordinates, or authority inputs.

Membership in the inventory is bytes-only evidence.  In particular, including
the runtime lock or legacy modules neither authenticates the installed runtime
nor authorizes reuse.  The fixed record identifiers are non-attesting labels;
the C2 payload and canonical digests carry the source-commit binding.

Importing and building perform no writes, publication, supplier access, model
access, official execution, or result derivation.  The returned object remains
a structural candidate: review, source selection, runtime closure,
materialization, authority, execution, and scientific-claim axes are false.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import os
from pathlib import Path
from typing import ClassVar

from spirallens import _repository_context as repository_context_module
from spirallens._repository_context import RepositoryContext

from .common import QualificationContractError
from . import confirmation_v1_materialization as materialization
from . import confirmation_v1_records as records

__all__: tuple[str, ...] = ()


_MODULE_PATH = "src/spirallens/qualification/confirmation_v1_source_closure.py"
_REPOSITORY_CONTEXT_MODULE_PATH = "src/spirallens/_repository_context.py"
_C1_RECORD_ID = "d7-v1-c1-source-set-candidate"
_C2_RECORD_ID = "d7-v1-c2-source-closure-candidate"
_MAX_STATUS_BYTES = 1024 * 1024
_CANDIDATE_FACTORY_TOKEN = object()
_FORBIDDEN_LOCAL_CONFIG_PREFIXES = ("filter.", "include.", "includeif.")
_FORBIDDEN_LOCAL_CONFIG_NAMES = {
    "core.alternaterefscommand",
    "core.attributesfile",
    "core.fsmonitor",
    "core.ignorestat",
    "core.checkstat",
    "core.trustctime",
    "core.untrackedcache",
    "core.worktree",
    "extensions.worktreeconfig",
}


@dataclass(frozen=True, slots=True)
class D7V1SourceClosureCandidate:
    """In-memory source-structure candidate without review or authority."""

    source_commit: str
    c1: records.D7V1C1SourceSetRecord
    c2: records.D7V1C2SourceClosureReceipt
    _factory_token: object = field(default=None, repr=False, compare=False)

    structural_only: ClassVar[bool] = True
    git_source_tree_reenumerated: ClassVar[bool] = True
    c1_c2_rejoined: ClassVar[bool] = True
    source_reviewed: ClassVar[bool] = False
    source_selected: ClassVar[bool] = False
    identity_authenticated: ClassVar[bool] = False
    runtime_environment_authenticated: ClassVar[bool] = False
    runtime_lock_conformity_verified: ClassVar[bool] = False
    runtime_dependency_closure_verified: ClassVar[bool] = False
    legacy_source_reuse_authorized: ClassVar[bool] = False
    source_closure_established: ClassVar[bool] = False
    source_tree_authenticated: ClassVar[bool] = False
    c1_persisted: ClassVar[bool] = False
    c2_persisted: ClassVar[bool] = False
    artifact_chronology_verified: ClassVar[bool] = False
    external_store_observed: ClassVar[bool] = False
    external_namespace_reserved: ClassVar[bool] = False
    seed_claim_persisted: ClassVar[bool] = False
    seed_values_present: ClassVar[bool] = False
    supplier_invoked: ClassVar[bool] = False
    attempt_reserved: ClassVar[bool] = False
    chronology_receipt_persisted: ClassVar[bool] = False
    materialization_authorized: ClassVar[bool] = False
    publication_authorized: ClassVar[bool] = False
    artifact_commit_created: ClassVar[bool] = False
    artifact_commit_verified: ClassVar[bool] = False
    authority_granted: ClassVar[bool] = False
    execution_authorized: ClassVar[bool] = False
    execution_started: ClassVar[bool] = False
    result_produced: ClassVar[bool] = False
    result_commit_created: ClassVar[bool] = False
    result_commit_verified: ClassVar[bool] = False
    scientific_claim_eligible: ClassVar[bool] = False

    def __post_init__(self) -> None:
        if self._factory_token is not _CANDIDATE_FACTORY_TOKEN:
            raise QualificationContractError(
                "source-closure candidate must be produced by its closed builder"
            )
        materialization._full_commit(self.source_commit, label="source_commit")
        if not isinstance(self.c1, records.D7V1C1SourceSetRecord):
            raise TypeError("c1 must be D7V1C1SourceSetRecord")
        if not isinstance(self.c2, records.D7V1C2SourceClosureReceipt):
            raise TypeError("c2 must be D7V1C2SourceClosureReceipt")
        c2_payload = materialization._record_payload(self.c2)
        materialization._require_binding(
            c2_payload.get("c1_binding"),
            materialization._record_binding(self.c1),
            label="candidate C2 C1 binding",
        )
        derivation = materialization._mapping(
            c2_payload.get("source_tree_derivation"),
            label="candidate source_tree_derivation",
        )
        if (
            materialization._full_commit(
                derivation.get("merged_source_commit"),
                label="candidate merged_source_commit",
            )
            != self.source_commit
        ):
            raise QualificationContractError("candidate source commit differs from C2")
        derived_members = tuple(
            records.D7V1SourceMember.from_dict(item)
            for item in materialization._sequence(
                derivation.get("source_members"),
                label="candidate C2 source_members",
            )
        )
        if derived_members != self.source_members:
            raise QualificationContractError(
                "candidate C2 source members differ from C1"
            )

    @property
    def source_members(self) -> tuple[records.D7V1SourceMember, ...]:
        return materialization._source_members_from_c1(self.c1)


def _require_exact_clean_head(
    repository: RepositoryContext,
    source_commit: str,
) -> None:
    _require_unredirected_repository_state(repository)
    head_source = materialization._git(
        repository,
        "rev-parse",
        "--verify",
        "HEAD^{commit}",
    )
    try:
        head = head_source.decode("ascii", errors="strict").strip()
    except UnicodeDecodeError as error:
        raise QualificationContractError("Git HEAD identity is not ASCII") from error
    if materialization._full_commit(head, label="repository HEAD") != source_commit:
        raise QualificationContractError(
            "source_commit must equal the exact current repository HEAD"
        )
    status = materialization._git_bounded(
        repository,
        _MAX_STATUS_BYTES,
        "status",
        "--porcelain=v1",
        "-z",
        "--untracked-files=all",
    )
    if status:
        raise QualificationContractError(
            "source-closure candidate requires a completely clean repository"
        )


def _git_admin_directory(
    repository: RepositoryContext,
    argument: str,
    *,
    label: str,
) -> Path:
    source = materialization._git(
        repository,
        "rev-parse",
        "--path-format=absolute",
        argument,
    )
    try:
        text = source.decode("utf-8", errors="strict").strip()
    except UnicodeDecodeError as error:
        raise QualificationContractError(f"{label} is not UTF-8") from error
    if not text or "\n" in text:
        raise QualificationContractError(f"{label} is invalid")
    path = Path(text)
    if not path.is_absolute():
        path = repository.root / path
    try:
        resolved = path.resolve(strict=True)
    except OSError as error:
        raise QualificationContractError(f"cannot resolve {label}: {error}") from error
    if not resolved.is_dir():
        raise QualificationContractError(f"{label} is not a directory")
    return resolved


def _require_unredirected_repository_state(
    repository: RepositoryContext,
) -> None:
    config_source = materialization._git_bounded(
        repository,
        _MAX_STATUS_BYTES,
        "config",
        "--local",
        "--no-includes",
        "--name-only",
        "--list",
    )
    try:
        config_names = {
            line.lower()
            for line in config_source.decode("utf-8", errors="strict").splitlines()
            if line
        }
    except UnicodeDecodeError as error:
        raise QualificationContractError("local Git config is not UTF-8") from error
    if any(
        name.startswith(_FORBIDDEN_LOCAL_CONFIG_PREFIXES)
        or name in _FORBIDDEN_LOCAL_CONFIG_NAMES
        for name in config_names
    ):
        raise QualificationContractError(
            "source-closure candidate rejects mutable local Git indirection"
        )

    index_source = materialization._git_bounded(
        repository,
        _MAX_STATUS_BYTES,
        "ls-files",
        "-v",
        "-z",
        "--",
        ".",
    )
    index_records = tuple(item for item in index_source.split(b"\0") if item)
    if not index_records or any(not item.startswith(b"H ") for item in index_records):
        raise QualificationContractError(
            "source-closure candidate rejects hidden or sparse Git index entries"
        )
    tracked_paths = tuple(item[2:] for item in index_records)
    if any(
        path == b".gitattributes" or path.endswith(b"/.gitattributes")
        for path in tracked_paths
    ):
        raise QualificationContractError(
            "source-closure candidate rejects tracked Git attribute files"
        )

    untracked_source = materialization._git_bounded(
        repository,
        _MAX_STATUS_BYTES,
        "ls-files",
        "--others",
        "-z",
        "--",
        ".",
    )
    if untracked_source:
        raise QualificationContractError(
            "source-closure candidate requires zero untracked repository files"
        )

    staged_source = materialization._git_bounded(
        repository,
        _MAX_STATUS_BYTES,
        "ls-files",
        "--stage",
        "-z",
        "--",
        ".",
    )
    for item in (entry for entry in staged_source.split(b"\0") if entry):
        try:
            metadata, repository_path = item.split(b"\t", 1)
            mode, _object_id, _stage = metadata.split(b" ", 2)
        except ValueError as error:
            raise QualificationContractError(
                "Git staged-file inventory is malformed"
            ) from error
        if not repository_path:
            raise QualificationContractError(
                "Git staged-file inventory contains an empty path"
            )
        if mode == b"160000":
            raise QualificationContractError(
                "source-closure candidate rejects Git submodule entries"
            )

    git_directory = _git_admin_directory(
        repository,
        "--git-dir",
        label="Git directory",
    )
    common_directory = _git_admin_directory(
        repository,
        "--git-common-dir",
        label="Git common directory",
    )
    forbidden_admin_paths = {
        git_directory / "config.worktree",
        git_directory / "info" / "attributes",
        git_directory / "shallow",
        common_directory / "config.worktree",
        common_directory / "info" / "grafts",
        common_directory / "info" / "attributes",
        common_directory / "objects" / "info" / "alternates",
        common_directory / "shallow",
    }
    if any(os.path.lexists(path) for path in forbidden_admin_paths):
        raise QualificationContractError(
            "source-closure candidate rejects mutable Git admin indirection"
        )
    if materialization._git_bounded(
        repository,
        _MAX_STATUS_BYTES,
        "for-each-ref",
        "--format=%(refname)",
        "refs/replace",
    ):
        raise QualificationContractError(
            "source-closure candidate rejects Git replacement refs"
        )


def _canonical_reload_c1(
    candidate: records.D7V1C1SourceSetRecord,
) -> records.D7V1C1SourceSetRecord:
    return records.D7V1C1SourceSetRecord.from_canonical_bytes(
        candidate.canonical_bytes,
        expected_sha256=candidate.canonical_sha256,
    )


def _canonical_reload_c2(
    candidate: records.D7V1C2SourceClosureReceipt,
) -> records.D7V1C2SourceClosureReceipt:
    return records.D7V1C2SourceClosureReceipt.from_canonical_bytes(
        candidate.canonical_bytes,
        expected_sha256=candidate.canonical_sha256,
    )


def _build_d7_v1_source_closure_candidate(
    repository: RepositoryContext,
    *,
    source_commit: str,
) -> D7V1SourceClosureCandidate:
    """Construct the exact clean-HEAD C1/C2 structural candidate read-only."""

    if not isinstance(repository, RepositoryContext):
        raise TypeError("repository must be RepositoryContext")
    for imported_file, repository_path, label in (
        (__file__, _MODULE_PATH, "source-closure module"),
        (
            repository_context_module.__file__,
            _REPOSITORY_CONTEXT_MODULE_PATH,
            "repository-context module",
        ),
    ):
        try:
            matches = (repository.root / repository_path).samefile(imported_file)
        except (OSError, TypeError, ValueError):
            matches = False
        if not matches:
            raise QualificationContractError(
                f"{label} import origin differs from repository"
            )
    materialization._require_import_origins(repository)
    materialization._require_complete_git_history(repository)
    declared_source = materialization._full_commit(
        source_commit,
        label="source_commit",
    )
    _require_exact_clean_head(repository, declared_source)
    source = materialization._resolve_commit(
        repository,
        declared_source,
        label="source_commit",
    )

    protocol = materialization._protocol_at_commit(repository, source)
    coordinates = materialization._coordinates(protocol)
    source_members = materialization._enumerate_choice_free_d7_v1_source_members(
        repository,
        protocol,
        source,
    )
    route_source, route_document = materialization._route_source(
        repository,
        protocol,
    )
    route_binding = records.D7V1ArtifactBinding(
        artifact_role=materialization._ROUTE_ROLE,
        artifact_contract_id=materialization._string(
            route_document.get("schema_version"),
            label="route schema_version",
        ),
        canonical_sha256=materialization.sha256_bytes(route_source),
        byte_count=len(route_source),
    )
    c1 = _canonical_reload_c1(
        records.D7V1C1SourceSetRecord.create(
            record_id=_C1_RECORD_ID,
            repository_path=coordinates["c1_source_set"],
            route_binding=route_binding,
            source_members=source_members,
        )
    )
    c2 = _canonical_reload_c2(
        records.D7V1C2SourceClosureReceipt.create(
            record_id=_C2_RECORD_ID,
            repository_path=coordinates["c2_source_closure_receipt"],
            c1=c1,
            source_commit=source,
        )
    )
    if (
        materialization._verify_source_join(
            repository,
            protocol,
            c1,
            c2,
        )
        != source
    ):
        raise QualificationContractError(
            "source-closure rejoin returned a different source commit"
        )
    result = D7V1SourceClosureCandidate(
        source_commit=source,
        c1=c1,
        c2=c2,
        _factory_token=_CANDIDATE_FACTORY_TOKEN,
    )
    _require_exact_clean_head(repository, source)
    return result
