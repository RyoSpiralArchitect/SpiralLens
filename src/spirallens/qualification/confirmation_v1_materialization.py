"""Fail-closed joined loading and Git verification for the D7 v1 successor.

This module implements the source-side machinery frozen by
``d7_v1_pre_item23_materialization_v0_1.json``.  Importing it performs no I/O.
It does not generate seeds, enter a supplier, construct a scientific result,
access a model or subject, or invoke an official runner.  Repository
publication is kept in the separate private-stage primitive; this module
remains read-only.

The record classes validate one canonical document at a time.  This module is
the deliberately separate layer which proves that those documents bind the
same bytes, the same reviewed source commit, the same durable external claim
bytes, and the exact two-commit Git chronology.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
import hashlib
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import subprocess
from types import MappingProxyType
from typing import TypeAlias, cast

from spirallens import _repository_context as repository_context_module
from spirallens._repository_context import RepositoryContext
from spirallens.core import canonical as canonical_module
from spirallens.core.canonical import (
    CanonicalJsonError,
    canonical_json_bytes,
    parse_canonical_json,
    sha256_bytes,
)

from . import common as common_module
from .common import QualificationContractError, require_sha256
from . import confirmation_v1_descriptive_common as descriptive_common
from . import confirmation_v1_descriptive_d1 as descriptive_d1
from . import confirmation_v1_descriptive_d2 as descriptive_d2
from . import confirmation_v1_descriptive_d3 as descriptive_d3
from . import confirmation_v1_descriptive_d4 as descriptive_d4
from . import confirmation_v1_descriptive_d5_inputs as descriptive_d5_inputs
from . import confirmation_v1_descriptive_d5_outputs as descriptive_d5_outputs
from . import confirmation_v1_descriptive_independence as descriptive_independence
from . import confirmation_v1_post_d6_descriptive as descriptive
from . import confirmation_v1_records as records

__all__: tuple[str, ...] = ()


_PROTOCOL_PATH = "protocols/d7_v1_pre_item23_materialization_v0_1.json"
_PROTOCOL_SHA256 = "13d013e007fa30775abb4cd092b264482207dcad23f772aecd966a51cbafbaad"
_PROTOCOL_BYTE_COUNT = 43_288
_PROTOCOL_SCHEMA = "spirallens.d7-v1-pre-item23-materialization-protocol.v0.1"
_PROTOCOL_ID = "d7-v1-pre-item23-materialization-v0-1"
_PROTOCOL_MERGE_COMMIT = "052893036f0562292f869118dbcbc72746df329a"
_REPOSITORY_CONTEXT_MODULE_PATH = "src/spirallens/_repository_context.py"
_CANONICAL_MODULE_PATH = "src/spirallens/core/canonical.py"
_COMMON_MODULE_PATH = "src/spirallens/qualification/common.py"
_MODULE_PATH = "src/spirallens/qualification/confirmation_v1_materialization.py"
_DESCRIPTIVE_MODULE_PATH = (
    "src/spirallens/qualification/confirmation_v1_post_d6_descriptive.py"
)
_SOURCE_CLOSURE_MODULE_PATH = (
    "src/spirallens/qualification/confirmation_v1_source_closure.py"
)
_DESCRIPTIVE_HELPER_MODULES = (
    (
        descriptive_common,
        "src/spirallens/qualification/confirmation_v1_descriptive_common.py",
        "descriptive common module",
    ),
    (
        descriptive_d1,
        "src/spirallens/qualification/confirmation_v1_descriptive_d1.py",
        "descriptive D1 module",
    ),
    (
        descriptive_d2,
        "src/spirallens/qualification/confirmation_v1_descriptive_d2.py",
        "descriptive D2 module",
    ),
    (
        descriptive_d3,
        "src/spirallens/qualification/confirmation_v1_descriptive_d3.py",
        "descriptive D3 module",
    ),
    (
        descriptive_d4,
        "src/spirallens/qualification/confirmation_v1_descriptive_d4.py",
        "descriptive D4 module",
    ),
    (
        descriptive_d5_inputs,
        "src/spirallens/qualification/confirmation_v1_descriptive_d5_inputs.py",
        "descriptive D5 input module",
    ),
    (
        descriptive_d5_outputs,
        "src/spirallens/qualification/confirmation_v1_descriptive_d5_outputs.py",
        "descriptive D5 output module",
    ),
    (
        descriptive_independence,
        "src/spirallens/qualification/confirmation_v1_descriptive_independence.py",
        "descriptive independence module",
    ),
)
_DESCRIPTIVE_HELPER_PATHS = tuple(
    repository_path for _module, repository_path, _label in _DESCRIPTIVE_HELPER_MODULES
)
_RECORDS_MODULE_PATH = "src/spirallens/qualification/confirmation_v1_records.py"
_ROUTE_ROLE = "navigation-route"
_PROTOCOL_ROLE = "v1-materialization-protocol"
_MAX_PROTOCOL_BYTES = 64 * 1024
_MAX_SOURCE_MEMBER_BYTES = 64 * 1024 * 1024
_MAX_SOURCE_TREE_FILE_COUNT = 4_096
_MAX_SOURCE_TREE_METADATA_BYTES = 16 * 1024 * 1024
_MAX_SOURCE_TREE_TOTAL_BYTES = 512 * 1024 * 1024
_COMMIT_LENGTH = 40
_SOURCE_TREE_ROOT = "src/spirallens"
_SOURCE_TREE_FIXED_PATHS = (
    "pyproject.toml",
    "requirements-d7-runtime-lock.txt",
)

_COORDINATE_ROLES = {
    "c1_source_set": records.D7V1C1SourceSetRecord.artifact_role,
    "c2_source_closure_receipt": records.D7V1C2SourceClosureReceipt.artifact_role,
    "exclusive_seed_supply_claim": records.D7V1ExclusiveSeedSupplyClaim.artifact_role,
    "official_seed_inventory": records.D7V1OfficialSeedInventory.artifact_role,
    "replay_target": records.D7V1ReplayTarget.artifact_role,
    "full_design_freeze": records.D7V1FullDesignFreeze.artifact_role,
    "launch_intent": records.D7V1LaunchIntent.artifact_role,
    "official_execution_attempt_envelope": (
        records.D7V1OfficialExecutionAttemptReservation.artifact_role
    ),
    "pre_item23_chronology_receipt": (
        records.D7V1PreItem23ChronologyReceipt.artifact_role
    ),
}
_ROLE_CLASSES = {
    records.D7V1C1SourceSetRecord.artifact_role: records.D7V1C1SourceSetRecord,
    records.D7V1C2SourceClosureReceipt.artifact_role: (
        records.D7V1C2SourceClosureReceipt
    ),
    records.D7V1ExclusiveSeedSupplyClaim.artifact_role: (
        records.D7V1ExclusiveSeedSupplyClaim
    ),
    records.D7V1OfficialSeedInventory.artifact_role: records.D7V1OfficialSeedInventory,
    records.D7V1ReplayTarget.artifact_role: records.D7V1ReplayTarget,
    records.D7V1FullDesignFreeze.artifact_role: records.D7V1FullDesignFreeze,
    records.D7V1LaunchIntent.artifact_role: records.D7V1LaunchIntent,
    records.D7V1OfficialExecutionAttemptReservation.artifact_role: (
        records.D7V1OfficialExecutionAttemptReservation
    ),
    records.D7V1PreItem23ChronologyReceipt.artifact_role: (
        records.D7V1PreItem23ChronologyReceipt
    ),
}
_RESULT_ROLE = records.D7V1PostselectionDescriptiveResult.artifact_role

_Record: TypeAlias = (
    records.D7V1C1SourceSetRecord
    | records.D7V1C2SourceClosureReceipt
    | records.D7V1ExclusiveSeedSupplyClaim
    | records.D7V1OfficialSeedInventory
    | records.D7V1ReplayTarget
    | records.D7V1FullDesignFreeze
    | records.D7V1LaunchIntent
    | records.D7V1OfficialExecutionAttemptReservation
    | records.D7V1PreItem23ChronologyReceipt
)
_ExternalReader: TypeAlias = Callable[[Path, int], bytes]


def _mapping(value: object, *, label: str) -> dict[str, object]:
    if type(value) is not dict or any(type(key) is not str for key in value):
        raise QualificationContractError(f"{label} must be a JSON object")
    return cast(dict[str, object], value)


def _sequence(value: object, *, label: str) -> list[object]:
    if type(value) is not list:
        raise QualificationContractError(f"{label} must be a JSON array")
    return cast(list[object], value)


def _string(value: object, *, label: str) -> str:
    if type(value) is not str or not value or value != value.strip():
        raise QualificationContractError(f"{label} must be a non-empty string")
    return value


def _plain_int(value: object, *, label: str, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise QualificationContractError(f"{label} must be an integer >= {minimum}")
    return value


def _full_commit(value: object, *, label: str) -> str:
    text = _string(value, label=label)
    if len(text) != _COMMIT_LENGTH or any(ch not in "0123456789abcdef" for ch in text):
        raise QualificationContractError(f"{label} must be a full lowercase commit id")
    return text


def _relative_path(value: object, *, label: str) -> str:
    text = _string(value, label=label)
    path = PurePosixPath(text)
    if path.is_absolute() or not path.parts or ".." in path.parts or str(path) != text:
        raise QualificationContractError(f"{label} must be a normalized relative path")
    return text


def _absolute_path(value: object, *, label: str) -> Path:
    text = _string(value, label=label)
    path = PurePosixPath(text)
    if not path.is_absolute() or ".." in path.parts or str(path) != text:
        raise QualificationContractError(f"{label} must be a normalized absolute path")
    return Path(text)


def _record_binding(record: object) -> records.D7V1ArtifactBinding:
    if not isinstance(record, records._D7V1CanonicalRecord):
        raise TypeError("record must be a D7 v1 canonical record")
    return records.D7V1ArtifactBinding.from_record(record)


def _binding(value: object, *, label: str) -> records.D7V1ArtifactBinding:
    try:
        return records.D7V1ArtifactBinding.from_dict(value)
    except (QualificationContractError, TypeError, ValueError) as error:
        raise QualificationContractError(f"{label} is invalid: {error}") from error


def _require_binding(
    value: object,
    expected: records.D7V1ArtifactBinding,
    *,
    label: str,
) -> None:
    if _binding(value, label=label) != expected:
        raise QualificationContractError(f"{label} does not bind the actual bytes")


def _record_document(record: object) -> dict[str, object]:
    if not isinstance(record, records._FactoryCanonicalBytes):
        raise TypeError("record must carry canonical bytes")
    return record.to_dict()


def _record_payload(record: object) -> dict[str, object]:
    return _mapping(_record_document(record).get("payload"), label="record payload")


def _safe_read_file(
    path: Path,
    maximum_bytes: int,
    *,
    require_single_link: bool = True,
) -> bytes:
    """Read one stable, regular, single-link file without following symlinks."""

    if not isinstance(path, Path) or not path.is_absolute():
        raise QualificationContractError("read path must be absolute")
    if maximum_bytes < 1:
        raise QualificationContractError("maximum_bytes must be positive")
    flags = os.O_RDONLY
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags)
    except OSError as error:
        raise QualificationContractError(f"cannot open {path}: {error}") from error
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or (
            require_single_link and before.st_nlink != 1
        ):
            raise QualificationContractError(
                f"{path} must be a single-link regular file"
            )
        if before.st_size < 1 or before.st_size > maximum_bytes:
            raise QualificationContractError(f"{path} exceeds its byte contract")
        chunks: list[bytes] = []
        remaining = maximum_bytes + 1
        while remaining:
            chunk = os.read(descriptor, min(remaining, 1024 * 1024))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        source = b"".join(chunks)
        after = os.fstat(descriptor)
        if (
            before.st_dev,
            before.st_ino,
            before.st_size,
            before.st_mtime_ns,
        ) != (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
        ):
            raise QualificationContractError(f"{path} changed while being read")
        if len(source) != before.st_size or not source or len(source) > maximum_bytes:
            raise QualificationContractError(f"{path} violates its byte contract")
        return source
    finally:
        os.close(descriptor)


def _default_external_reader(path: Path, maximum_bytes: int) -> bytes:
    return _safe_read_file(path, maximum_bytes)


def _git_environment() -> dict[str, str]:
    return {
        "GIT_CONFIG_COUNT": "0",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_ATTR_NOSYSTEM": "1",
        "GIT_LITERAL_PATHSPECS": "1",
        "GIT_NO_LAZY_FETCH": "1",
        "GIT_NO_REPLACE_OBJECTS": "1",
        "GIT_OPTIONAL_LOCKS": "0",
        "GIT_PAGER": "cat",
        "GIT_TERMINAL_PROMPT": "0",
        "LANG": "C",
        "LC_ALL": "C",
        "PAGER": "cat",
        "PATH": os.defpath,
    }


def _git_executable() -> str:
    executable = shutil.which("git", path=os.defpath)
    if executable is None or not Path(executable).is_absolute():
        raise QualificationContractError("cannot resolve system Git executable")
    return executable


def _git(repository: RepositoryContext, *arguments: str) -> bytes:
    completed = subprocess.run(
        (
            _git_executable(),
            "--no-replace-objects",
            "-c",
            "core.fsmonitor=false",
            "-c",
            "core.untrackedCache=false",
            "-c",
            "core.trustctime=true",
            "-c",
            "core.checkStat=default",
            "-c",
            "core.fileMode=true",
            "-c",
            f"core.attributesFile={os.devnull}",
            "-C",
            str(repository.root),
            "--no-optional-locks",
            *arguments,
        ),
        check=False,
        capture_output=True,
        env=_git_environment(),
    )
    if completed.returncode != 0:
        detail = completed.stderr.decode("utf-8", errors="replace").strip()
        raise QualificationContractError(
            f"git {' '.join(arguments)} failed: {detail or completed.returncode}"
        )
    return completed.stdout


def _kill_and_wait(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is None:
        try:
            process.kill()
        except ProcessLookupError:
            pass
    process.wait()


def _git_bounded(
    repository: RepositoryContext,
    maximum_stdout_bytes: int,
    *arguments: str,
) -> bytes:
    """Run one Git read while bounding combined stdout/stderr before EOF."""

    if (
        isinstance(maximum_stdout_bytes, bool)
        or not isinstance(maximum_stdout_bytes, int)
        or maximum_stdout_bytes < 0
    ):
        raise ValueError("maximum_stdout_bytes must be a non-negative integer")
    process = subprocess.Popen(
        (
            _git_executable(),
            "--no-replace-objects",
            "-c",
            "core.fsmonitor=false",
            "-c",
            "core.untrackedCache=false",
            "-c",
            "core.trustctime=true",
            "-c",
            "core.checkStat=default",
            "-c",
            "core.fileMode=true",
            "-c",
            f"core.attributesFile={os.devnull}",
            "-C",
            str(repository.root),
            "--no-optional-locks",
            *arguments,
        ),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        bufsize=0,
        env=_git_environment(),
    )
    try:
        if process.stdout is None:
            raise QualificationContractError("cannot open bounded Git output pipe")
        chunks: list[bytes] = []
        remaining = maximum_stdout_bytes + 1
        while remaining:
            chunk = process.stdout.read(remaining)
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        output = b"".join(chunks)
        if len(output) > maximum_stdout_bytes:
            raise QualificationContractError(
                f"git {' '.join(arguments)} output exceeds its cap"
            )
        returncode = process.wait()
        if returncode != 0:
            detail = output.decode("utf-8", errors="replace").strip()
            raise QualificationContractError(
                f"git {' '.join(arguments)} failed: {detail or returncode}"
            )
        return output
    except BaseException:
        _kill_and_wait(process)
        raise
    finally:
        if process.stdout is not None:
            try:
                process.stdout.close()
            except OSError:
                pass


def _resolve_commit(repository: RepositoryContext, value: str, *, label: str) -> str:
    declared = _full_commit(value, label=label)
    resolved = _git(repository, "rev-parse", "--verify", f"{declared}^{{commit}}")
    text = resolved.decode("ascii", errors="strict").strip()
    if text != declared:
        raise QualificationContractError(f"{label} does not resolve exactly")
    return declared


def _commit_parents(repository: RepositoryContext, commit: str) -> tuple[str, ...]:
    line = _git(repository, "rev-list", "--parents", "-n", "1", commit)
    fields = line.decode("ascii", errors="strict").strip().split()
    if not fields or fields[0] != commit:
        raise QualificationContractError("Git returned a different commit identity")
    return tuple(_full_commit(item, label="parent commit") for item in fields[1:])


def _is_ancestor(
    repository: RepositoryContext,
    ancestor: str,
    descendant: str,
) -> bool:
    completed = subprocess.run(
        (
            _git_executable(),
            "--no-replace-objects",
            "-c",
            "core.fsmonitor=false",
            "-c",
            "core.untrackedCache=false",
            "-c",
            "core.trustctime=true",
            "-c",
            "core.checkStat=default",
            "-c",
            "core.fileMode=true",
            "-c",
            f"core.attributesFile={os.devnull}",
            "-C",
            str(repository.root),
            "--no-optional-locks",
            "merge-base",
            "--is-ancestor",
            ancestor,
            descendant,
        ),
        check=False,
        capture_output=True,
        env=_git_environment(),
    )
    if completed.returncode == 0:
        return True
    if completed.returncode == 1:
        return False
    detail = completed.stderr.decode("utf-8", errors="replace").strip()
    raise QualificationContractError(
        f"cannot evaluate Git ancestry: {detail or completed.returncode}"
    )


def _require_complete_git_history(repository: RepositoryContext) -> None:
    shallow = _git(repository, "rev-parse", "--is-shallow-repository")
    if shallow.decode("ascii", errors="strict").strip() != "false":
        raise QualificationContractError(
            "D7 v1 verification rejects a shallow Git repository"
        )
    common_source = _git(
        repository,
        "rev-parse",
        "--path-format=absolute",
        "--git-common-dir",
    )
    common_text = common_source.decode("utf-8", errors="strict").strip()
    if not common_text or "\n" in common_text:
        raise QualificationContractError("Git returned an invalid common directory")
    common_directory = Path(common_text)
    if not common_directory.is_absolute():
        common_directory = repository.root / common_directory
    try:
        common_directory = common_directory.resolve(strict=True)
    except OSError as error:
        raise QualificationContractError(
            f"cannot resolve Git common directory: {error}"
        ) from error
    if not common_directory.is_dir():
        raise QualificationContractError("Git common directory is not a directory")
    if os.path.lexists(common_directory / "info" / "grafts"):
        raise QualificationContractError(
            "D7 v1 verification rejects a repository-local Git graft file"
        )


def _git_blob(
    repository: RepositoryContext,
    commit: str,
    repository_path: str,
    *,
    maximum_bytes: int,
) -> tuple[str, bytes]:
    if type(maximum_bytes) is not int or maximum_bytes < 0:
        raise QualificationContractError("maximum_bytes must be a nonnegative integer")
    relative = _relative_path(repository_path, label="repository_path")
    listing = _git(repository, "ls-tree", "-z", commit, "--", relative)
    entries = [item for item in listing.split(b"\0") if item]
    if len(entries) != 1:
        raise QualificationContractError(
            f"{relative} must have exactly one Git tree entry at {commit}"
        )
    try:
        metadata, encoded_path = entries[0].split(b"\t", 1)
        mode_b, kind_b, object_b = metadata.split(b" ", 2)
        mode = mode_b.decode("ascii")
        kind = kind_b.decode("ascii")
        object_id = object_b.decode("ascii")
        observed_path = encoded_path.decode("utf-8")
    except (UnicodeDecodeError, ValueError) as error:
        raise QualificationContractError("malformed Git tree entry") from error
    if observed_path != relative or kind != "blob" or mode not in {"100644", "100755"}:
        raise QualificationContractError(
            f"{relative} must be an ordinary 100644/100755 Git blob"
        )
    size_source = _git(repository, "cat-file", "-s", object_id)
    try:
        size = int(size_source.decode("ascii", errors="strict").strip())
    except (UnicodeDecodeError, ValueError) as error:
        raise QualificationContractError("Git returned an invalid blob size") from error
    if size < 0 or size > maximum_bytes:
        raise QualificationContractError(
            f"{relative} Git blob exceeds its pre-read byte cap"
        )
    source = _git(repository, "cat-file", "blob", object_id)
    if len(source) != size:
        raise QualificationContractError(f"{relative} Git blob size changed")
    return mode, source


def _require_import_origins(repository: RepositoryContext) -> None:
    for module, repository_path, label in (
        (
            repository_context_module,
            _REPOSITORY_CONTEXT_MODULE_PATH,
            "repository-context module",
        ),
        (canonical_module, _CANONICAL_MODULE_PATH, "canonical module"),
        (common_module, _COMMON_MODULE_PATH, "qualification common module"),
    ):
        try:
            matches = (repository.root / repository_path).samefile(module.__file__)
        except (OSError, TypeError, ValueError):
            matches = False
        if not matches:
            raise QualificationContractError(
                f"{label} import origin differs from repository"
            )
    if not repository.matches_imported_file(
        imported_file=__file__,
        repository_path=_MODULE_PATH,
    ):
        raise QualificationContractError(
            "materialization module import origin differs from repository"
        )
    if not repository.matches_imported_file(
        imported_file=records.__file__,
        repository_path=_RECORDS_MODULE_PATH,
    ):
        raise QualificationContractError(
            "records module import origin differs from repository"
        )
    if not repository.matches_imported_file(
        imported_file=descriptive.__file__,
        repository_path=_DESCRIPTIVE_MODULE_PATH,
    ):
        raise QualificationContractError(
            "descriptive module import origin differs from repository"
        )
    for module, repository_path, label in _DESCRIPTIVE_HELPER_MODULES:
        if not repository.matches_imported_file(
            imported_file=module.__file__,
            repository_path=repository_path,
        ):
            raise QualificationContractError(
                f"{label} import origin differs from repository"
            )


def _require_executing_sources_match_commit(
    repository: RepositoryContext,
    source_commit: str,
) -> None:
    for repository_path in (
        _REPOSITORY_CONTEXT_MODULE_PATH,
        _CANONICAL_MODULE_PATH,
        _COMMON_MODULE_PATH,
        _MODULE_PATH,
        _RECORDS_MODULE_PATH,
        _DESCRIPTIVE_MODULE_PATH,
        _SOURCE_CLOSURE_MODULE_PATH,
        *_DESCRIPTIVE_HELPER_PATHS,
    ):
        _mode, committed = _git_blob(
            repository,
            source_commit,
            repository_path,
            maximum_bytes=_MAX_SOURCE_MEMBER_BYTES,
        )
        observed = _safe_read_file(
            repository.root / repository_path,
            _MAX_SOURCE_MEMBER_BYTES,
            require_single_link=False,
        )
        if observed != committed:
            raise QualificationContractError(
                f"executing source bytes differ from reviewed source S: {repository_path}"
            )


def _git_path_absent(
    repository: RepositoryContext,
    commit: str,
    repository_path: str,
) -> bool:
    relative = _relative_path(repository_path, label="repository_path")
    return not bool(_git(repository, "ls-tree", "-z", commit, "--", relative))


def _parse_canonical_mapping(source: bytes, *, label: str) -> dict[str, object]:
    try:
        document = parse_canonical_json(source, label=label)
    except CanonicalJsonError as error:
        raise QualificationContractError(str(error)) from error
    mapping = _mapping(document, label=label)
    if canonical_json_bytes(mapping) != source:
        raise QualificationContractError(f"{label} canonical round-trip differs")
    return mapping


@dataclass(frozen=True, slots=True)
class D7V1MaterializationProtocol:
    canonical_bytes: bytes

    def __post_init__(self) -> None:
        if type(self.canonical_bytes) is not bytes:
            raise TypeError("canonical_bytes must be bytes")
        if (
            len(self.canonical_bytes) != _PROTOCOL_BYTE_COUNT
            or sha256_bytes(self.canonical_bytes) != _PROTOCOL_SHA256
        ):
            raise QualificationContractError(
                "materialization protocol identity differs"
            )
        document = _parse_canonical_mapping(
            self.canonical_bytes,
            label="D7 v1 materialization protocol",
        )
        if (
            document.get("schema_version") != _PROTOCOL_SCHEMA
            or document.get("protocol_id") != _PROTOCOL_ID
            or document.get("status") != "frozen_not_run"
        ):
            raise QualificationContractError("materialization protocol header differs")

    @property
    def canonical_sha256(self) -> str:
        return _PROTOCOL_SHA256

    @property
    def document(self) -> dict[str, object]:
        return _parse_canonical_mapping(
            self.canonical_bytes,
            label="D7 v1 materialization protocol",
        )


@dataclass(frozen=True, slots=True)
class D7V1JoinedRecords:
    protocol: D7V1MaterializationProtocol
    source_commit: str
    stage_root: Path | None
    _records: Mapping[str, _Record]
    _sources: Mapping[str, bytes]

    def __post_init__(self) -> None:
        _full_commit(self.source_commit, label="source_commit")
        if set(self._records) != set(_ROLE_CLASSES):
            raise QualificationContractError("joined record roles are not closed")
        if set(self._sources) != set(_ROLE_CLASSES):
            raise QualificationContractError("joined record sources are not closed")
        object.__setattr__(self, "_records", MappingProxyType(dict(self._records)))
        object.__setattr__(self, "_sources", MappingProxyType(dict(self._sources)))

    def record(self, role: str) -> _Record:
        try:
            return self._records[role]
        except KeyError as error:
            raise QualificationContractError(f"unknown joined role: {role}") from error

    def source(self, role: str) -> bytes:
        try:
            return self._sources[role]
        except KeyError as error:
            raise QualificationContractError(f"unknown joined role: {role}") from error

    @property
    def receipt(self) -> records.D7V1PreItem23ChronologyReceipt:
        value = self.record(records.D7V1PreItem23ChronologyReceipt.artifact_role)
        if not isinstance(value, records.D7V1PreItem23ChronologyReceipt):
            raise AssertionError("closed role map returned the wrong receipt type")
        return value


@dataclass(frozen=True, slots=True)
class D7V1CommitVerification:
    source_commit: str
    artifact_commit: str
    result_commit: str | None
    joined: D7V1JoinedRecords
    result: records.D7V1PostselectionDescriptiveResult | None

    def __post_init__(self) -> None:
        _full_commit(self.source_commit, label="source_commit")
        _full_commit(self.artifact_commit, label="artifact_commit")
        if self.result_commit is not None:
            _full_commit(self.result_commit, label="result_commit")
        if (self.result_commit is None) != (self.result is None):
            raise QualificationContractError("result commit and record must co-occur")


def _load_protocol_source(source: bytes) -> D7V1MaterializationProtocol:
    if not source or len(source) > _MAX_PROTOCOL_BYTES:
        raise QualificationContractError("materialization protocol exceeds its cap")
    if sha256_bytes(source) != _PROTOCOL_SHA256:
        raise QualificationContractError("materialization protocol digest differs")
    return D7V1MaterializationProtocol(source)


def _load_d7_v1_materialization_protocol(
    repository: RepositoryContext,
) -> D7V1MaterializationProtocol:
    if not isinstance(repository, RepositoryContext):
        raise TypeError("repository must be RepositoryContext")
    _require_import_origins(repository)
    source = _safe_read_file(repository.root / _PROTOCOL_PATH, _MAX_PROTOCOL_BYTES)
    return _load_protocol_source(source)


def _protocol_at_commit(
    repository: RepositoryContext,
    source_commit: str,
) -> D7V1MaterializationProtocol:
    _mode, source = _git_blob(
        repository,
        source_commit,
        _PROTOCOL_PATH,
        maximum_bytes=_MAX_PROTOCOL_BYTES,
    )
    return _load_protocol_source(source)


def _coordinates(protocol: D7V1MaterializationProtocol) -> dict[str, str]:
    layout = _mapping(
        protocol.document.get("coordinate_and_member_layout"),
        label="coordinate_and_member_layout",
    )
    coordinates = {
        key: _relative_path(layout.get(key), label=f"coordinate {key}")
        for key in (*_COORDINATE_ROLES, "descriptive_result")
    }
    root = _relative_path(layout.get("repository_root"), label="repository_root")
    prefix = root + "/"
    if any(not value.startswith(prefix) for value in coordinates.values()):
        raise QualificationContractError("v1 coordinates must be below repository_root")
    if len(set(coordinates.values())) != len(coordinates):
        raise QualificationContractError("v1 coordinates must be unique")
    return coordinates


def _route_source(
    repository: RepositoryContext,
    protocol: D7V1MaterializationProtocol,
) -> tuple[bytes, dict[str, object]]:
    binding = _mapping(protocol.document.get("route_binding"), label="route_binding")
    commit = _resolve_commit(
        repository,
        _string(binding.get("merge_commit"), label="route merge_commit"),
        label="route merge_commit",
    )
    path = _relative_path(binding.get("repository_path"), label="route path")
    expected_size = _plain_int(
        binding.get("byte_count"), label="route byte_count", minimum=1
    )
    _mode, source = _git_blob(
        repository,
        commit,
        path,
        maximum_bytes=expected_size,
    )
    expected_sha = require_sha256(binding.get("canonical_sha256"), label="route sha256")
    if len(source) != expected_size or sha256_bytes(source) != expected_sha:
        raise QualificationContractError("route bytes differ from the frozen binding")
    return source, _parse_canonical_mapping(source, label="navigation route")


def _expected_external_paths(
    protocol: D7V1MaterializationProtocol,
) -> tuple[Path, Path]:
    external = _mapping(
        protocol.document.get("external_durable_chronology_contract"),
        label="external durable chronology",
    )
    claim = _mapping(external.get("seed_supply_claim"), label="seed_supply_claim")
    attempt = _mapping(external.get("attempt_reservation"), label="attempt_reservation")
    return (
        _absolute_path(claim.get("external_store_path"), label="external claim path"),
        _absolute_path(
            attempt.get("external_store_path"), label="external attempt path"
        ),
    )


def _expected_route_coordinates(
    route: Mapping[str, object],
) -> tuple[Path, Path, str, str]:
    declaration = _mapping(
        route.get("strict_successor_declaration"),
        label="strict successor declaration",
    )
    external = _mapping(
        declaration.get("future_external_coordinates"),
        label="future external coordinates",
    )
    entrypoints = _mapping(
        declaration.get("future_entrypoint_coordinates"),
        label="future entrypoint coordinates",
    )
    return (
        _absolute_path(external.get("external_store_path"), label="route store path"),
        _absolute_path(
            external.get("external_staging_path"), label="route staging path"
        ),
        _relative_path(entrypoints.get("runner_script"), label="route runner script"),
        _string(entrypoints.get("official_callable"), label="route official callable"),
    )


def _load_record(
    role: str,
    source: bytes,
    *,
    expected_sha256: str,
) -> _Record:
    try:
        record_class = _ROLE_CLASSES[role]
    except KeyError as error:
        raise QualificationContractError(
            f"unknown D7 v1 record role: {role}"
        ) from error
    record = record_class.from_canonical_bytes(
        source,
        expected_sha256=require_sha256(
            expected_sha256, label=f"{role} expected sha256"
        ),
    )
    return cast(_Record, record)


def _record_repository_path(record: object) -> str:
    document = _record_document(record)
    if "payload" in document:
        value = _mapping(document["payload"], label="record payload").get(
            "repository_path"
        )
    else:
        value = document.get("repository_path")
    return _relative_path(value, label="record repository_path")


def _source_members_from_c1(
    c1: records.D7V1C1SourceSetRecord,
) -> tuple[records.D7V1SourceMember, ...]:
    payload = _record_payload(c1)
    return tuple(
        records.D7V1SourceMember.from_dict(item)
        for item in _sequence(payload.get("source_members"), label="C1 source_members")
    )


def _enumerate_d7_v1_source_members(
    repository: RepositoryContext,
    source_commit: str,
    repository_paths: Sequence[str],
) -> tuple[records.D7V1SourceMember, ...]:
    commit = _resolve_commit(repository, source_commit, label="source_commit")
    normalized = tuple(
        sorted(
            {
                _relative_path(path, label="source repository_path")
                for path in repository_paths
            }
        )
    )
    if not normalized:
        raise QualificationContractError("source member paths must be non-empty")
    result: list[records.D7V1SourceMember] = []
    for path in normalized:
        mode, source = _git_blob(
            repository,
            commit,
            path,
            maximum_bytes=_MAX_SOURCE_MEMBER_BYTES,
        )
        result.append(
            records.D7V1SourceMember(
                repository_path=path,
                git_mode=mode,
                sha256=sha256_bytes(source),
                byte_count=len(source),
            )
        )
    return tuple(result)


def _choice_free_d7_v1_source_tree_entries(
    repository: RepositoryContext,
    protocol: D7V1MaterializationProtocol,
    source_commit: str,
) -> tuple[tuple[str, str, str, int], ...]:
    """Derive exact ``(path, mode, object, size)`` entries from Git S."""

    commit = _resolve_commit(repository, source_commit, label="source_commit")
    source_contract = _mapping(
        protocol.document.get("source_contract"), label="source_contract"
    )
    required_paths = {
        _relative_path(item, label="required source path")
        for item in _sequence(
            source_contract.get("required_new_source_paths"),
            label="required_new_source_paths",
        )
    }
    route_binding = _mapping(
        protocol.document.get("route_binding"), label="route_binding"
    )
    route_path = _relative_path(
        route_binding.get("repository_path"), label="route path"
    )
    fixed_paths = required_paths | {*_SOURCE_TREE_FIXED_PATHS, route_path}
    pathspecs = (_SOURCE_TREE_ROOT, *sorted(fixed_paths))
    listing = _git_bounded(
        repository,
        _MAX_SOURCE_TREE_METADATA_BYTES,
        "ls-tree",
        "-r",
        "-l",
        "-z",
        "--full-tree",
        commit,
        "--",
        *pathspecs,
    )
    source_prefix = _SOURCE_TREE_ROOT + "/"
    entries: dict[str, tuple[str, str, int]] = {}
    total_bytes = 0
    for entry in (item for item in listing.split(b"\0") if item):
        try:
            metadata, encoded_path = entry.split(b"\t", 1)
            mode_source, kind_source, object_source, size_source = metadata.split()
            mode = mode_source.decode("ascii", errors="strict")
            kind = kind_source.decode("ascii", errors="strict")
            object_id = object_source.decode("ascii", errors="strict")
            size = int(size_source.decode("ascii", errors="strict"))
            repository_path = encoded_path.decode("utf-8", errors="strict")
        except (UnicodeDecodeError, ValueError) as error:
            raise QualificationContractError(
                "Git source-tree metadata is malformed"
            ) from error
        normalized = _relative_path(
            repository_path,
            label="Git source-tree repository_path",
        )
        if not normalized.startswith(source_prefix) and normalized not in fixed_paths:
            raise QualificationContractError(
                "Git source-tree enumeration escaped its exact path policy"
            )
        if kind != "blob" or mode not in {"100644", "100755"}:
            raise QualificationContractError(
                f"{normalized} must be an ordinary 100644/100755 Git blob"
            )
        if (
            len(object_id) != _COMMIT_LENGTH
            or any(character not in "0123456789abcdef" for character in object_id)
            or size < 0
            or size > _MAX_SOURCE_MEMBER_BYTES
        ):
            raise QualificationContractError(
                f"{normalized} has invalid or oversized Git blob metadata"
            )
        if normalized in entries:
            raise QualificationContractError(
                "Git source-tree enumeration contains a duplicate path"
            )
        entries[normalized] = (mode, object_id, size)
        total_bytes += size
        if len(entries) > _MAX_SOURCE_TREE_FILE_COUNT:
            raise QualificationContractError(
                "Git source-tree enumeration exceeds its file-count cap"
            )
        if total_bytes > _MAX_SOURCE_TREE_TOTAL_BYTES:
            raise QualificationContractError(
                "Git source-tree enumeration exceeds its aggregate byte cap"
            )
    if not entries:
        raise QualificationContractError("Git source-tree enumeration is empty")
    if not fixed_paths <= set(entries):
        missing = sorted(fixed_paths - set(entries))
        raise QualificationContractError(
            f"Git source-tree enumeration omits fixed source paths: {missing}"
        )
    return tuple(
        (repository_path, mode, object_id, size)
        for repository_path, (mode, object_id, size) in sorted(entries.items())
    )


def _choice_free_d7_v1_source_paths(
    repository: RepositoryContext,
    protocol: D7V1MaterializationProtocol,
    source_commit: str,
) -> tuple[str, ...]:
    """Derive the exact v1 source inventory only from the Git tree at S."""

    return tuple(
        repository_path
        for repository_path, _mode, _object_id, _size in (
            _choice_free_d7_v1_source_tree_entries(
                repository,
                protocol,
                source_commit,
            )
        )
    )


def _batch_git_source_sha256(
    repository: RepositoryContext,
    entries: Sequence[tuple[str, str, str, int]],
) -> tuple[str, ...]:
    if not entries or len(entries) > _MAX_SOURCE_TREE_FILE_COUNT:
        raise QualificationContractError("Git source batch has invalid cardinality")
    expected_total = sum(size for _path, _mode, _object_id, size in entries)
    if expected_total > _MAX_SOURCE_TREE_TOTAL_BYTES:
        raise QualificationContractError("Git source batch exceeds its aggregate cap")
    process = subprocess.Popen(
        (
            _git_executable(),
            "--no-replace-objects",
            "-c",
            "core.fsmonitor=false",
            "-c",
            "core.untrackedCache=false",
            "-c",
            "core.trustctime=true",
            "-c",
            "core.checkStat=default",
            "-c",
            "core.fileMode=true",
            "-c",
            f"core.attributesFile={os.devnull}",
            "-C",
            str(repository.root),
            "--no-optional-locks",
            "cat-file",
            "--batch",
        ),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        bufsize=0,
        env=_git_environment(),
    )
    result: list[str] = []
    try:
        if process.stdin is None or process.stdout is None:
            raise QualificationContractError("cannot open Git source batch pipes")
        for repository_path, _mode, object_id, expected_size in entries:
            request = object_id.encode("ascii") + b"\n"
            written = 0
            while written < len(request):
                count = process.stdin.write(request[written:])
                if count is None or count <= 0:
                    raise QualificationContractError(
                        "Git source batch request is incomplete"
                    )
                written += count
            header = process.stdout.readline(129)
            expected_header = f"{object_id} blob {expected_size}\n".encode("ascii")
            if len(header) > 128 or header != expected_header:
                raise QualificationContractError(
                    f"Git source batch header differs: {repository_path}"
                )
            digest = hashlib.sha256()
            remaining = expected_size
            while remaining:
                chunk = process.stdout.read(min(64 * 1024, remaining))
                if not chunk:
                    raise QualificationContractError(
                        f"Git source batch body is incomplete: {repository_path}"
                    )
                digest.update(chunk)
                remaining -= len(chunk)
            if process.stdout.read(1) != b"\n":
                raise QualificationContractError(
                    f"Git source batch body is incomplete: {repository_path}"
                )
            result.append(digest.hexdigest())
        process.stdin.close()
        if process.stdout.read(1):
            raise QualificationContractError("Git source batch has trailing output")
        returncode = process.wait()
        if returncode != 0:
            raise QualificationContractError(
                f"git cat-file --batch failed: {returncode}"
            )
        return tuple(result)
    except OSError as error:
        _kill_and_wait(process)
        raise QualificationContractError(
            f"git cat-file --batch pipe failed: {error}"
        ) from error
    except BaseException:
        _kill_and_wait(process)
        raise
    finally:
        if process.stdin is not None and not process.stdin.closed:
            try:
                process.stdin.close()
            except OSError:
                pass
        if process.stdout is not None:
            try:
                process.stdout.close()
            except OSError:
                pass


def _enumerate_choice_free_d7_v1_source_members(
    repository: RepositoryContext,
    protocol: D7V1MaterializationProtocol,
    source_commit: str,
) -> tuple[records.D7V1SourceMember, ...]:
    entries = _choice_free_d7_v1_source_tree_entries(
        repository,
        protocol,
        source_commit,
    )
    digests = _batch_git_source_sha256(repository, entries)
    return tuple(
        records.D7V1SourceMember(
            repository_path=repository_path,
            git_mode=mode,
            sha256=digest,
            byte_count=size,
        )
        for (repository_path, mode, _object_id, size), digest in zip(
            entries,
            digests,
            strict=True,
        )
    )


def _verify_source_join(
    repository: RepositoryContext,
    protocol: D7V1MaterializationProtocol,
    c1: records.D7V1C1SourceSetRecord,
    c2: records.D7V1C2SourceClosureReceipt,
) -> str:
    c1_payload = _record_payload(c1)
    c2_payload = _record_payload(c2)
    derivation = _mapping(
        c2_payload.get("source_tree_derivation"), label="source_tree_derivation"
    )
    source_commit = _resolve_commit(
        repository,
        _string(derivation.get("merged_source_commit"), label="merged_source_commit"),
        label="reviewed source commit S",
    )
    layout = _mapping(
        protocol.document.get("coordinate_and_member_layout"),
        label="coordinate_and_member_layout",
    )
    repository_root = _relative_path(
        layout.get("repository_root"),
        label="repository_root",
    )
    if not _git_path_absent(repository, source_commit, repository_root):
        raise QualificationContractError(
            "D7 v1 materialization repository_root must be entirely absent at source S"
        )
    _require_executing_sources_match_commit(repository, source_commit)
    _require_binding(
        c2_payload.get("c1_binding"), _record_binding(c1), label="C2 C1 binding"
    )
    c1_members = _source_members_from_c1(c1)
    derived_members = tuple(
        records.D7V1SourceMember.from_dict(item)
        for item in _sequence(
            derivation.get("source_members"), label="C2 source_members"
        )
    )
    if derived_members != c1_members:
        raise QualificationContractError("C2 source members differ from C1")
    observed = _enumerate_choice_free_d7_v1_source_members(
        repository,
        protocol,
        source_commit,
    )
    if observed != c1_members:
        raise QualificationContractError(
            "C1 source members differ from the exact choice-free Git tree S inventory"
        )
    source_contract = _mapping(
        protocol.document.get("source_contract"), label="source_contract"
    )
    required = {
        _relative_path(item, label="required source path")
        for item in _sequence(
            source_contract.get("required_new_source_paths"),
            label="required_new_source_paths",
        )
    }
    route_binding = _mapping(
        protocol.document.get("route_binding"), label="route_binding"
    )
    route_path = _relative_path(
        route_binding.get("repository_path"), label="route path"
    )
    member_paths = {member.repository_path for member in c1_members}
    required_members = required | {route_path} | set(_DESCRIPTIVE_HELPER_PATHS)
    if not required_members <= member_paths:
        missing = sorted(required_members - member_paths)
        raise QualificationContractError(f"C1 omits required source paths: {missing}")
    route_source, route_document = _route_source(repository, protocol)
    route_commit = _full_commit(route_binding.get("merge_commit"), label="route commit")
    if not _is_ancestor(repository, route_commit, source_commit):
        raise QualificationContractError("route merge commit is not an ancestor of S")
    if not _is_ancestor(repository, _PROTOCOL_MERGE_COMMIT, source_commit):
        raise QualificationContractError(
            "materialization protocol merge commit is not an ancestor of S"
        )
    expected_route = records.D7V1ArtifactBinding(
        artifact_role=_ROUTE_ROLE,
        artifact_contract_id=_string(
            route_document.get("schema_version"), label="route schema_version"
        ),
        canonical_sha256=sha256_bytes(route_source),
        byte_count=len(route_source),
    )
    _require_binding(
        c1_payload.get("route_binding"), expected_route, label="C1 route binding"
    )
    by_path = {member.repository_path: member for member in c1_members}
    route_member = by_path[route_path]
    if (
        route_member.sha256 != expected_route.canonical_sha256
        or route_member.byte_count != expected_route.byte_count
    ):
        raise QualificationContractError(
            "C1 route member differs from the frozen route"
        )
    protocol_member = by_path[_PROTOCOL_PATH]
    if (
        protocol_member.sha256 != protocol.canonical_sha256
        or protocol_member.byte_count != len(protocol.canonical_bytes)
    ):
        raise QualificationContractError(
            "C1 materialization protocol member differs from the frozen protocol"
        )
    return source_commit


def _historical_sources_and_bindings(
    repository: RepositoryContext,
    protocol: D7V1MaterializationProtocol,
) -> tuple[
    dict[str, bytes],
    dict[str, records.D7V1ArtifactBinding],
]:
    policy = _mapping(
        protocol.document.get("historical_input_policy"),
        label="historical_input_policy",
    )
    entries = [
        _mapping(policy.get("historical_plan_binding"), label="historical plan"),
        *(
            _mapping(item, label="historical parent")
            for item in _sequence(
                policy.get("permitted_historical_scientific_parents"),
                label="historical parents",
            )
        ),
    ]
    sources: dict[str, bytes] = {}
    bindings: dict[str, records.D7V1ArtifactBinding] = {}
    for entry in entries:
        role = _string(entry.get("artifact_binding_role"), label="historical role")
        source_commit = _resolve_commit(
            repository,
            _string(entry.get("source_commit"), label=f"{role} source_commit"),
            label=f"{role} source_commit",
        )
        path = _relative_path(entry.get("repository_path"), label=f"{role} path")
        expected_sha = require_sha256(
            entry.get("canonical_sha256"), label=f"{role} sha256"
        )
        expected_size = _plain_int(
            entry.get("byte_count"), label=f"{role} byte_count", minimum=1
        )
        _mode, source = _git_blob(
            repository,
            source_commit,
            path,
            maximum_bytes=expected_size,
        )
        if sha256_bytes(source) != expected_sha or len(source) != expected_size:
            raise QualificationContractError(f"{role} historical bytes differ")
        document = _parse_canonical_mapping(source, label=f"{role} historical input")
        artifact_contract_id = _string(
            entry.get("artifact_contract_id"), label=f"{role} contract"
        )
        if document.get("schema_version") != artifact_contract_id:
            raise QualificationContractError(f"{role} historical schema differs")
        sources[role] = source
        bindings[role] = records.D7V1ArtifactBinding(
            artifact_role=role,
            artifact_contract_id=artifact_contract_id,
            canonical_sha256=expected_sha,
            byte_count=expected_size,
        )
    if tuple(bindings) != records._DESCRIPTIVE_READ_TRACE_ROLES:
        raise QualificationContractError("historical input binding set is not closed")
    return sources, bindings


def _historical_bindings(
    repository: RepositoryContext,
    protocol: D7V1MaterializationProtocol,
) -> dict[str, records.D7V1ArtifactBinding]:
    _sources, bindings = _historical_sources_and_bindings(repository, protocol)
    return bindings


def _negative_seed_binding(
    repository: RepositoryContext,
    protocol: D7V1MaterializationProtocol,
) -> tuple[records.D7V1ArtifactBinding, tuple[int, ...]]:
    policy = _mapping(
        protocol.document.get("historical_input_policy"),
        label="historical_input_policy",
    )
    negative_items = _sequence(
        policy.get("negative_exclusion_inputs"), label="negative_exclusion_inputs"
    )
    if len(negative_items) != 1:
        raise QualificationContractError("negative seed input set is not closed")
    entry = _mapping(negative_items[0], label="negative seed input")
    role = _string(entry.get("artifact_binding_role"), label="negative seed role")
    commit = _resolve_commit(
        repository,
        _string(entry.get("source_commit"), label="negative seed source_commit"),
        label="negative seed source_commit",
    )
    path = _relative_path(entry.get("repository_path"), label="negative seed path")
    expected_sha = require_sha256(
        entry.get("canonical_sha256"), label="negative seed sha256"
    )
    expected_size = _plain_int(
        entry.get("byte_count"), label="negative seed byte_count", minimum=1
    )
    _mode, source = _git_blob(
        repository,
        commit,
        path,
        maximum_bytes=expected_size,
    )
    if sha256_bytes(source) != expected_sha or len(source) != expected_size:
        raise QualificationContractError("negative seed inventory bytes differ")
    _parse_canonical_mapping(source, label="negative seed inventory")
    values = tuple(
        _plain_int(item, label="predecessor seed", minimum=0)
        for item in _sequence(
            entry.get("pinned_predecessor_seed_values"),
            label="pinned predecessor seeds",
        )
    )
    if len(values) != len(set(values)) or not values:
        raise QualificationContractError("pinned predecessor seeds are invalid")
    return (
        records.D7V1ArtifactBinding(
            artifact_role=role,
            artifact_contract_id=_string(
                entry.get("artifact_contract_id"), label="negative seed contract"
            ),
            canonical_sha256=expected_sha,
            byte_count=expected_size,
        ),
        values,
    )


def _protocol_binding(
    protocol: D7V1MaterializationProtocol,
) -> records.D7V1ArtifactBinding:
    return records.D7V1ArtifactBinding(
        artifact_role=_PROTOCOL_ROLE,
        artifact_contract_id=_PROTOCOL_SCHEMA,
        canonical_sha256=protocol.canonical_sha256,
        byte_count=len(protocol.canonical_bytes),
    )


def _verify_cross_record_joins(
    repository: RepositoryContext,
    protocol: D7V1MaterializationProtocol,
    loaded: Mapping[str, _Record],
    sources: Mapping[str, bytes],
    *,
    external_reader: _ExternalReader,
) -> str:
    c1 = cast(
        records.D7V1C1SourceSetRecord,
        loaded[records.D7V1C1SourceSetRecord.artifact_role],
    )
    c2 = cast(
        records.D7V1C2SourceClosureReceipt,
        loaded[records.D7V1C2SourceClosureReceipt.artifact_role],
    )
    claim = cast(
        records.D7V1ExclusiveSeedSupplyClaim,
        loaded[records.D7V1ExclusiveSeedSupplyClaim.artifact_role],
    )
    inventory = cast(
        records.D7V1OfficialSeedInventory,
        loaded[records.D7V1OfficialSeedInventory.artifact_role],
    )
    replay = cast(
        records.D7V1ReplayTarget, loaded[records.D7V1ReplayTarget.artifact_role]
    )
    freeze = cast(
        records.D7V1FullDesignFreeze, loaded[records.D7V1FullDesignFreeze.artifact_role]
    )
    launch = cast(
        records.D7V1LaunchIntent, loaded[records.D7V1LaunchIntent.artifact_role]
    )
    attempt = cast(
        records.D7V1OfficialExecutionAttemptReservation,
        loaded[records.D7V1OfficialExecutionAttemptReservation.artifact_role],
    )
    receipt = cast(
        records.D7V1PreItem23ChronologyReceipt,
        loaded[records.D7V1PreItem23ChronologyReceipt.artifact_role],
    )

    source_commit = _verify_source_join(repository, protocol, c1, c2)
    coordinates = _coordinates(protocol)
    for key, role in _COORDINATE_ROLES.items():
        if _record_repository_path(loaded[role]) != coordinates[key]:
            raise QualificationContractError(f"{role} repository path differs")

    c2_payload = _record_payload(c2)
    claim_payload = _record_payload(claim)
    inventory_payload = _record_payload(inventory)
    freeze_payload = _record_payload(freeze)
    launch_payload = _record_payload(launch)
    attempt_payload = _record_payload(attempt)
    receipt_payload = _record_payload(receipt)
    replay_document = _record_document(replay)

    _require_binding(
        claim_payload.get("c2_binding"), _record_binding(c2), label="claim C2 binding"
    )
    c2_tree_sha = _string(c2_payload.get("source_tree_sha256"), label="C2 tree sha")
    claim_derivation = _mapping(
        claim_payload.get("claim_key_derivation"), label="claim derivation"
    )
    if claim_derivation.get("source_tree_sha256") != c2_tree_sha:
        raise QualificationContractError("claim source-tree digest differs from C2")

    _require_binding(
        inventory_payload.get("claim_binding"),
        _record_binding(claim),
        label="inventory claim binding",
    )
    supplier = _binding(
        claim_payload.get("supplier_identity_binding"), label="claim supplier identity"
    )
    _require_binding(
        inventory_payload.get("supplier_identity_binding"),
        supplier,
        label="inventory supplier identity",
    )
    if inventory_payload.get("supplier_id") != claim_derivation.get("supplier_id"):
        raise QualificationContractError("inventory supplier id differs from claim")

    negative_binding, negative_values = _negative_seed_binding(repository, protocol)
    _require_binding(
        inventory_payload.get("predecessor_inventory_binding"),
        negative_binding,
        label="predecessor seed inventory binding",
    )
    observed_negative = tuple(
        _plain_int(item, label="predecessor seed", minimum=0)
        for item in _sequence(
            inventory_payload.get("predecessor_seed_values"),
            label="predecessor seed values",
        )
    )
    if observed_negative != negative_values:
        raise QualificationContractError("predecessor seed values differ from the pin")
    new_seeds = tuple(
        _plain_int(item, label="successor seed", minimum=0)
        for item in _sequence(inventory_payload.get("seeds"), label="successor seeds")
    )
    if set(new_seeds) & set(negative_values):
        raise QualificationContractError("successor seeds overlap predecessor seeds")

    inventory_binding = _record_binding(inventory)
    _require_binding(
        replay_document.get("official_seed_inventory_binding"),
        inventory_binding,
        label="replay direct inventory binding",
    )
    full_design = _mapping(
        replay_document.get("full_design"), label="embedded full design"
    )
    design_inventory = _mapping(
        full_design.get("inventory"), label="full design inventory"
    )
    _require_binding(
        design_inventory.get("inventory_binding"),
        inventory_binding,
        label="embedded design inventory binding",
    )
    transitive = _mapping(
        replay_document.get("transitive_bindings"), label="replay transitive bindings"
    )
    actual_transitive = {
        "c1_binding": _record_binding(c1),
        "c2_binding": _record_binding(c2),
        "seed_claim_binding": _record_binding(claim),
        "seed_inventory_binding": inventory_binding,
        "embedded_full_design_binding": _binding(
            replay_document.get("embedded_full_design_binding"),
            label="embedded full design binding",
        ),
    }
    route_source, route_document = _route_source(repository, protocol)
    actual_transitive["route_binding"] = records.D7V1ArtifactBinding(
        artifact_role=_ROUTE_ROLE,
        artifact_contract_id=_string(
            route_document.get("schema_version"), label="route schema"
        ),
        canonical_sha256=sha256_bytes(route_source),
        byte_count=len(route_source),
    )
    actual_transitive["materialization_protocol_binding"] = _protocol_binding(protocol)
    historical = _historical_bindings(repository, protocol)
    historical_keys = {
        "historical_plan_binding": "historical-post-d6-plan",
        "parent_protocol_binding": "parent-protocol",
        "parent_result_binding": "parent-result",
        "parent_manifest_binding": "parent-manifest",
        "parent_consumption_binding": "parent-consumption",
        "parent_d6_decision_binding": "parent-d6-decision",
    }
    actual_transitive.update(
        {key: historical[role] for key, role in historical_keys.items()}
    )
    if set(transitive) != set(actual_transitive):
        raise QualificationContractError("replay transitive binding keyset differs")
    for key, expected in actual_transitive.items():
        _require_binding(transitive.get(key), expected, label=f"replay {key}")

    _require_binding(
        freeze_payload.get("replay_target_binding"),
        _record_binding(replay),
        label="freeze replay binding",
    )
    if freeze_payload.get("full_design_binding") != replay_document.get(
        "full_design_binding"
    ):
        raise QualificationContractError(
            "freeze full-design pointer differs from replay"
        )
    if freeze_payload.get("reviewed_source_commit") != source_commit:
        raise QualificationContractError("freeze reviewed source commit differs")

    _require_binding(
        launch_payload.get("replay_target_binding"),
        _record_binding(replay),
        label="launch replay binding",
    )
    _require_binding(
        launch_payload.get("full_design_freeze_binding"),
        _record_binding(freeze),
        label="launch freeze binding",
    )
    route_store, route_staging, route_runner, route_callable = (
        _expected_route_coordinates(route_document)
    )
    if (
        launch_payload.get("external_store_path") != str(route_store)
        or launch_payload.get("external_staging_path") != str(route_staging)
        or launch_payload.get("runner_script") != route_runner
        or launch_payload.get("official_callable") != route_callable
    ):
        raise QualificationContractError("launch coordinates differ from the route")

    _require_binding(
        attempt_payload.get("launch_intent_binding"),
        _record_binding(launch),
        label="attempt launch binding",
    )
    _require_binding(
        attempt_payload.get("replay_target_binding"),
        _record_binding(replay),
        label="attempt replay binding",
    )
    _require_binding(
        attempt_payload.get("seed_claim_binding"),
        _record_binding(claim),
        label="attempt claim binding",
    )
    attempt_derivation = _mapping(
        attempt_payload.get("attempt_key_derivation"), label="attempt derivation"
    )
    claim_path, attempt_path = _expected_external_paths(protocol)
    if (
        claim_derivation.get("external_claim_path") != str(claim_path)
        or attempt_derivation.get("external_attempt_path") != str(attempt_path)
        or attempt_derivation.get("reviewed_source_commit") != source_commit
        or attempt_payload.get("external_store_path") != str(route_store)
    ):
        raise QualificationContractError("external claim or attempt coordinates differ")

    claim_external = external_reader(claim_path, records.D7_V1_DEFAULT_MAX_RECORD_BYTES)
    attempt_external = external_reader(
        attempt_path, records.D7_V1_DEFAULT_MAX_RECORD_BYTES
    )
    if claim_external != sources[claim.artifact_role]:
        raise QualificationContractError(
            "external seed claim differs from repository projection"
        )
    if attempt_external != sources[attempt.artifact_role]:
        raise QualificationContractError(
            "external attempt differs from repository projection"
        )

    receipt_inventory = _mapping(
        receipt_payload.get("pre_item23_file_inventory"),
        label="receipt file inventory",
    )
    expected_inventory = {
        role: coordinates[key] for key, role in _COORDINATE_ROLES.items()
    }
    if receipt_inventory != expected_inventory:
        raise QualificationContractError("receipt nine-file inventory differs")
    predecessor_files = _mapping(
        receipt_payload.get("predecessor_files"), label="receipt predecessor files"
    )
    for role, record in loaded.items():
        if role == receipt.artifact_role:
            continue
        joined = records.D7V1RepositoryArtifactBinding.from_dict(
            predecessor_files.get(role)
        )
        if joined.repository_path != expected_inventory[role]:
            raise QualificationContractError(f"receipt {role} path differs")
        if joined.artifact_binding != _record_binding(record):
            raise QualificationContractError(f"receipt {role} bytes differ")
    absence = records.D7V1NamespaceAbsenceObservation.from_dict(
        receipt_payload.get("descriptive_result_namespace_absence")
    )
    if (
        absence.repository_path != coordinates["descriptive_result"]
        or absence.observed_at_reviewed_source_commit != source_commit
        or not _git_path_absent(repository, source_commit, absence.repository_path)
    ):
        raise QualificationContractError("descriptive result absence at S differs")
    return source_commit


def _receipt_expectations(
    receipt: records.D7V1PreItem23ChronologyReceipt,
) -> dict[str, str]:
    payload = _record_payload(receipt)
    predecessor = _mapping(payload.get("predecessor_files"), label="predecessor files")
    result: dict[str, str] = {}
    for role, value in predecessor.items():
        joined = records.D7V1RepositoryArtifactBinding.from_dict(value)
        if joined.artifact_binding.artifact_role != role:
            raise QualificationContractError("receipt predecessor role differs")
        result[role] = joined.artifact_binding.canonical_sha256
    return result


def _load_joined_sources(
    repository: RepositoryContext,
    protocol: D7V1MaterializationProtocol,
    sources: Mapping[str, bytes],
    *,
    expected_receipt_sha256: str,
    stage_root: Path | None,
    external_reader: _ExternalReader,
) -> D7V1JoinedRecords:
    if set(sources) != set(_ROLE_CLASSES):
        raise QualificationContractError("joined source roles are not the exact nine")
    receipt_role = records.D7V1PreItem23ChronologyReceipt.artifact_role
    receipt = _load_record(
        receipt_role,
        sources[receipt_role],
        expected_sha256=expected_receipt_sha256,
    )
    if not isinstance(receipt, records.D7V1PreItem23ChronologyReceipt):
        raise AssertionError("receipt loader returned the wrong type")
    expected = _receipt_expectations(receipt)
    if set(expected) != set(_ROLE_CLASSES) - {receipt_role}:
        raise QualificationContractError(
            "receipt does not bind the exact eight predecessors"
        )
    loaded: dict[str, _Record] = {receipt_role: receipt}
    for role in _ROLE_CLASSES:
        if role == receipt_role:
            continue
        loaded[role] = _load_record(
            role,
            sources[role],
            expected_sha256=expected[role],
        )
    source_commit = _verify_cross_record_joins(
        repository,
        protocol,
        loaded,
        sources,
        external_reader=external_reader,
    )
    return D7V1JoinedRecords(
        protocol=protocol,
        source_commit=source_commit,
        stage_root=stage_root,
        _records=loaded,
        _sources=sources,
    )


def _expected_stage_files(
    protocol: D7V1MaterializationProtocol,
) -> dict[str, str]:
    coordinates = _coordinates(protocol)
    root = _relative_path(
        _mapping(
            protocol.document.get("coordinate_and_member_layout"),
            label="coordinate_and_member_layout",
        ).get("repository_root"),
        label="repository_root",
    )
    prefix = root + "/"
    return {
        role: coordinates[key].removeprefix(prefix)
        for key, role in _COORDINATE_ROLES.items()
    }


def _stage_tree_sets(stage_root: Path) -> tuple[set[str], set[str]]:
    if not stage_root.is_absolute():
        raise QualificationContractError("stage_root must be absolute")
    try:
        root_stat = os.lstat(stage_root)
    except OSError as error:
        raise QualificationContractError(
            f"cannot inspect stage_root: {error}"
        ) from error
    if not stat.S_ISDIR(root_stat.st_mode) or stat.S_ISLNK(root_stat.st_mode):
        raise QualificationContractError("stage_root must be a real directory")
    files: set[str] = set()
    observed_directories: set[str] = set()
    for current, directory_names, filenames in os.walk(stage_root, followlinks=False):
        current_path = Path(current)
        for name in directory_names:
            child = current_path / name
            child_stat = os.lstat(child)
            if stat.S_ISLNK(child_stat.st_mode) or not stat.S_ISDIR(child_stat.st_mode):
                raise QualificationContractError(
                    "stage tree contains a non-directory child"
                )
            observed_directories.add(child.relative_to(stage_root).as_posix())
        for name in filenames:
            child = current_path / name
            child_stat = os.lstat(child)
            if not stat.S_ISREG(child_stat.st_mode) or child_stat.st_nlink != 1:
                raise QualificationContractError(
                    "stage tree contains a non-regular file"
                )
            files.add(child.relative_to(stage_root).as_posix())
    return files, observed_directories


def _expected_stage_directories(paths: Mapping[str, str]) -> set[str]:
    result: set[str] = set()
    for relative in paths.values():
        parent = PurePosixPath(relative).parent
        while str(parent) != ".":
            result.add(str(parent))
            parent = parent.parent
    return result


def _require_exact_stage_tree(
    stage_root: Path,
    paths: Mapping[str, str],
) -> None:
    files, directories = _stage_tree_sets(stage_root)
    if files != set(paths.values()) or directories != _expected_stage_directories(
        paths
    ):
        raise QualificationContractError("stage tree is not the exact nine-file tree")


def _load_d7_v1_staged_joined_records(
    repository: RepositoryContext,
    stage_root: Path,
    *,
    expected_receipt_sha256: str,
) -> D7V1JoinedRecords:
    if not isinstance(repository, RepositoryContext):
        raise TypeError("repository must be RepositoryContext")
    if not isinstance(stage_root, Path) or not stage_root.is_absolute():
        raise QualificationContractError("stage_root must be an absolute Path")
    _require_complete_git_history(repository)
    protocol = _load_d7_v1_materialization_protocol(repository)
    paths = _expected_stage_files(protocol)
    _require_exact_stage_tree(stage_root, paths)
    sources: dict[str, bytes] = {}
    for role, relative in paths.items():
        record_class = _ROLE_CLASSES[role]
        sources[role] = _safe_read_file(
            stage_root / relative,
            record_class.max_record_bytes,
        )
    return _load_joined_sources(
        repository,
        protocol,
        sources,
        expected_receipt_sha256=expected_receipt_sha256,
        stage_root=stage_root,
        external_reader=_default_external_reader,
    )


def _commit_delta(
    repository: RepositoryContext,
    parent: str,
    child: str,
) -> dict[str, str]:
    source = _git(
        repository,
        "diff-tree",
        "--no-commit-id",
        "--name-status",
        "-r",
        "--no-renames",
        "-z",
        parent,
        child,
    )
    fields = [item.decode("utf-8") for item in source.split(b"\0") if item]
    if len(fields) % 2:
        raise QualificationContractError("malformed Git diff-tree output")
    result: dict[str, str] = {}
    for index in range(0, len(fields), 2):
        status_code, path = fields[index], fields[index + 1]
        if path in result:
            raise QualificationContractError("Git delta contains duplicate paths")
        result[path] = status_code
    return result


def _require_unique_introduction(
    repository: RepositoryContext,
    commit: str,
    path: str,
) -> None:
    source = _git(
        repository,
        "log",
        "--full-history",
        "--no-renames",
        "--format=%H",
        "--diff-filter=A",
        commit,
        "--",
        path,
    )
    commits = tuple(item for item in source.decode("ascii").splitlines() if item)
    if commits != (commit,):
        raise QualificationContractError(
            f"{path} was not introduced exactly once at {commit}"
        )


def _sources_from_commit(
    repository: RepositoryContext,
    protocol: D7V1MaterializationProtocol,
    commit: str,
) -> dict[str, bytes]:
    coordinates = _coordinates(protocol)
    result: dict[str, bytes] = {}
    for key, role in _COORDINATE_ROLES.items():
        _mode, source = _git_blob(
            repository,
            commit,
            coordinates[key],
            maximum_bytes=_ROLE_CLASSES[role].max_record_bytes,
        )
        result[role] = source
    return result


def _verify_and_load_d7_v1_commit_a(
    repository: RepositoryContext,
    *,
    source_commit: str,
    artifact_commit: str,
) -> D7V1CommitVerification:
    _require_import_origins(repository)
    _require_complete_git_history(repository)
    source = _resolve_commit(repository, source_commit, label="source_commit S")
    artifact = _resolve_commit(repository, artifact_commit, label="artifact_commit A")
    if _commit_parents(repository, artifact) != (source,):
        raise QualificationContractError(
            "artifact commit A must have exactly source S as parent"
        )
    protocol = _protocol_at_commit(repository, source)
    coordinates = _coordinates(protocol)
    exact_paths = {coordinates[key] for key in _COORDINATE_ROLES}
    delta = _commit_delta(repository, source, artifact)
    if set(delta) != exact_paths or any(value != "A" for value in delta.values()):
        raise QualificationContractError(
            "commit A must add only the exact nine-file set"
        )
    for path in sorted(exact_paths):
        _require_unique_introduction(repository, artifact, path)
    if not _git_path_absent(repository, source, coordinates["descriptive_result"]):
        raise QualificationContractError(
            "descriptive result was already present at source S"
        )
    if not _git_path_absent(repository, artifact, coordinates["descriptive_result"]):
        raise QualificationContractError(
            "descriptive result must be absent from commit A"
        )
    sources = _sources_from_commit(repository, protocol, artifact)
    receipt_role = records.D7V1PreItem23ChronologyReceipt.artifact_role
    joined = _load_joined_sources(
        repository,
        protocol,
        sources,
        expected_receipt_sha256=sha256_bytes(sources[receipt_role]),
        stage_root=None,
        external_reader=_default_external_reader,
    )
    if joined.source_commit != source:
        raise QualificationContractError(
            "joined source commit differs from commit A parent"
        )
    return D7V1CommitVerification(source, artifact, None, joined, None)


def _load_result(
    source: bytes,
    *,
    expected_sha256: str,
) -> records.D7V1PostselectionDescriptiveResult:
    return records.D7V1PostselectionDescriptiveResult.from_canonical_bytes(
        source,
        expected_sha256=expected_sha256,
    )


def _verify_result_joins(
    repository: RepositoryContext,
    protocol: D7V1MaterializationProtocol,
    joined: D7V1JoinedRecords,
    result: records.D7V1PostselectionDescriptiveResult,
) -> dict[str, bytes]:
    coordinates = _coordinates(protocol)
    if _record_repository_path(result) != coordinates["descriptive_result"]:
        raise QualificationContractError("result repository path differs")
    payload = _record_payload(result)
    attempt = joined.record(
        records.D7V1OfficialExecutionAttemptReservation.artifact_role
    )
    _require_binding(
        payload.get("parent_binding"),
        _record_binding(attempt),
        label="result attempt parent",
    )
    _require_binding(
        payload.get("chronology_receipt_binding"),
        _record_binding(joined.receipt),
        label="result chronology receipt",
    )
    historical_sources, historical = _historical_sources_and_bindings(
        repository, protocol
    )
    trace = _sequence(payload.get("read_trace"), label="result read_trace")
    observed: list[records.D7V1ArtifactBinding] = []
    for item in trace:
        entry = records.D7V1ReadTraceEntry.from_dict(item)
        observed.append(entry.artifact_binding)
    expected = [historical[role] for role in records._DESCRIPTIVE_READ_TRACE_ROLES]
    if observed != expected[: len(observed)]:
        raise QualificationContractError("result read trace differs from pinned inputs")
    return historical_sources


def _verify_and_load_d7_v1_commit_b(
    repository: RepositoryContext,
    *,
    source_commit: str,
    artifact_commit: str,
    result_commit: str,
) -> D7V1CommitVerification:
    commit_a = _verify_and_load_d7_v1_commit_a(
        repository,
        source_commit=source_commit,
        artifact_commit=artifact_commit,
    )
    result_id = _resolve_commit(repository, result_commit, label="result_commit B")
    if _commit_parents(repository, result_id) != (commit_a.artifact_commit,):
        raise QualificationContractError(
            "result commit B must have exactly commit A as parent"
        )
    coordinates = _coordinates(commit_a.joined.protocol)
    result_path = coordinates["descriptive_result"]
    delta = _commit_delta(repository, commit_a.artifact_commit, result_id)
    if delta != {result_path: "A"}:
        raise QualificationContractError(
            "commit B must add only the descriptive result"
        )
    _require_unique_introduction(repository, result_id, result_path)
    for key in _COORDINATE_ROLES:
        path = coordinates[key]
        role = _COORDINATE_ROLES[key]
        cap = _ROLE_CLASSES[role].max_record_bytes
        mode_a, source_a = _git_blob(
            repository,
            commit_a.artifact_commit,
            path,
            maximum_bytes=cap,
        )
        mode_b, source_b = _git_blob(
            repository,
            result_id,
            path,
            maximum_bytes=cap,
        )
        if mode_a != mode_b or source_a != source_b:
            raise QualificationContractError(f"commit B changed commit A member {path}")
    _mode, result_source = _git_blob(
        repository,
        result_id,
        result_path,
        maximum_bytes=records.D7_V1_POSTSELECTION_RESULT_MAX_RECORD_BYTES,
    )
    result = _load_result(
        result_source,
        expected_sha256=sha256_bytes(result_source),
    )
    historical_sources = _verify_result_joins(
        repository,
        commit_a.joined.protocol,
        commit_a.joined,
        result,
    )
    attempt = commit_a.joined.record(
        records.D7V1OfficialExecutionAttemptReservation.artifact_role
    )
    if not isinstance(attempt, records.D7V1OfficialExecutionAttemptReservation):
        raise QualificationContractError("joined result parent is not an attempt")
    descriptive._verify_d7_v1_post_d6_descriptive_result(
        result,
        historical_plan_source=historical_sources["historical-post-d6-plan"],
        parent_protocol_source=historical_sources["parent-protocol"],
        parent_result_source=historical_sources["parent-result"],
        parent_manifest_source=historical_sources["parent-manifest"],
        parent_consumption_source=historical_sources["parent-consumption"],
        parent_d6_decision_source=historical_sources["parent-d6-decision"],
        parent_attempt=attempt,
        chronology_receipt=commit_a.joined.receipt,
    )
    return D7V1CommitVerification(
        commit_a.source_commit,
        commit_a.artifact_commit,
        result_id,
        commit_a.joined,
        result,
    )
