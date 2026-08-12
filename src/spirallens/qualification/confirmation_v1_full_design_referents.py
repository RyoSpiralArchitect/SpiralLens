"""Private, source-derived D7 v1 full-design referent candidates.

The materialization protocol names seven fields in the embedded full design.
The official inventory is a persisted record, but the other six fields had no
source-authenticated referents.  This module closes only that structural gap:
it reads the five permitted historical scientific parents from their pinned
Git objects, reconstructs the existing seed-free execution design, and emits
six canonical *virtual* referents in memory.

No historical plan, predecessor D7 artifact, seed supplier, launch artifact,
model, subject, official callable, entropy source, or filesystem writer is
used here.  A resolved virtual binding is not authentication, admission,
freeze, review, application, instantiation, persistence, or authority.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import hashlib
import importlib.machinery
import importlib.util
import inspect
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import subprocess
import sys
from types import FunctionType, MappingProxyType, ModuleType
from typing import TYPE_CHECKING, cast

from spirallens import _repository_context as repository_context_module
from spirallens._repository_context import RepositoryContext
from spirallens.core import canonical as canonical_module
from spirallens.core.canonical import (
    canonical_json_bytes,
    parse_canonical_json,
    sha256_bytes,
)
from spirallens.synthetic import (
    spectral_moment_confirmation as spectral_moment_confirmation,
)

from . import advancement
from . import confirmation_execution_design as execution_design
from . import confirmation_protocol
from . import confirmation_v1_records as records
from . import contracts
from . import freeze
from . import persistence
from . import protocol as qualification_protocol
from . import common as common_module
from .common import QualificationContractError, require_sha256

if TYPE_CHECKING:
    from .confirmation_v1_design_referent_documents import (
        D7V1FullDesignReferentSetCandidate,
        D7V1TypedScientificParentAdapter,
    )
    from .confirmation_v1_deterministic_inputs import (
        D7V1DeterministicInputContractCandidate,
    )
    from .confirmation_v1_materialization import D7V1MaterializationProtocol


__all__: tuple[str, ...] = ()


_MODULE_PATH = "src/spirallens/qualification/confirmation_v1_full_design_referents.py"
_MATERIALIZATION_PATH = (
    "src/spirallens/qualification/confirmation_v1_materialization.py"
)
_REPOSITORY_CONTEXT_PATH = "src/spirallens/_repository_context.py"
_CANONICAL_PATH = "src/spirallens/core/canonical.py"
_COMMON_PATH = "src/spirallens/qualification/common.py"
_RECORDS_PATH = "src/spirallens/qualification/confirmation_v1_records.py"
_DESIGN_REFERENT_DOCUMENTS_PATH = (
    "src/spirallens/qualification/confirmation_v1_design_referent_documents.py"
)
_DESIGN_REFERENT_DOCUMENTS_MODULE_NAME = (
    "spirallens.qualification.confirmation_v1_design_referent_documents"
)
_DETERMINISTIC_INPUTS_PATH = (
    "src/spirallens/qualification/confirmation_v1_deterministic_inputs.py"
)
_SOURCE_CLOSURE_PATH = "src/spirallens/qualification/confirmation_v1_source_closure.py"
_EXECUTION_DESIGN_PATH = "src/spirallens/qualification/confirmation_execution_design.py"
_BOOTSTRAP_MAX_SOURCE_BYTES = 64 * 1024 * 1024
_CRITICAL_RUNTIME_MODULES = (
    (
        advancement,
        "src/spirallens/qualification/advancement.py",
        "advancement module",
    ),
    (
        contracts,
        "src/spirallens/qualification/contracts.py",
        "qualification-result contracts module",
    ),
    (
        freeze,
        "src/spirallens/qualification/freeze.py",
        "selection terminal contracts module",
    ),
    (
        persistence,
        "src/spirallens/qualification/persistence.py",
        "qualification persistence module",
    ),
    (
        qualification_protocol,
        "src/spirallens/qualification/protocol.py",
        "qualification protocol module",
    ),
    (
        confirmation_protocol,
        "src/spirallens/qualification/confirmation_protocol.py",
        "D7 parent-binding module",
    ),
    (
        spectral_moment_confirmation,
        "src/spirallens/synthetic/spectral_moment_confirmation.py",
        "spectral-moment scientific projection module",
    ),
    (execution_design, _EXECUTION_DESIGN_PATH, "approved execution-design module"),
)
_SUCCESSOR_LINEAGE_ID = "d7-spectral-moment-confirmation-v1"
_PARENT_ROLES = (
    "parent-protocol",
    "parent-result",
    "parent-manifest",
    "parent-consumption",
    "parent-d6-decision",
)
_AUTHENTICATED_REFERENT_DOCUMENTS_MODULE: ModuleType | None = None
_AUTHENTICATED_REFERENT_DOCUMENTS_CACHE: (
    tuple[
        ModuleType,
        str,
        importlib.machinery.ModuleSpec,
        Mapping[str, str],
    ]
    | None
) = None


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


def _boolean(value: object, *, label: str) -> bool:
    if type(value) is not bool:
        raise QualificationContractError(f"{label} must be boolean")
    return value


def _plain_int(value: object, *, label: str, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise QualificationContractError(f"{label} must be an integer >= {minimum}")
    return value


def _binding_document(binding: records.D7V1ArtifactBinding) -> dict[str, object]:
    if not isinstance(binding, records.D7V1ArtifactBinding):
        raise TypeError("binding must be D7V1ArtifactBinding")
    return binding.to_dict()


def _record_binding(
    record: records.D7V1C1SourceSetRecord | records.D7V1C2SourceClosureReceipt,
) -> records.D7V1ArtifactBinding:
    return records.D7V1ArtifactBinding.from_record(record)


def _parse_exact_canonical(source: bytes, *, label: str) -> dict[str, object]:
    if type(source) is not bytes or not source:
        raise QualificationContractError(f"{label} must be nonempty bytes")
    value = parse_canonical_json(source, label=label)
    document = _mapping(value, label=label)
    if canonical_json_bytes(document) != source:
        raise QualificationContractError(f"{label} canonical round-trip differs")
    return document


def _bootstrap_read_source(path: Path) -> bytes:
    """Read one fixed source without relying on materialization helpers."""

    flags = os.O_RDONLY
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags)
    except OSError as error:
        raise QualificationContractError(
            f"cannot bootstrap-read {path}: {error}"
        ) from error
    try:
        before = os.fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_size < 1
            or before.st_size > _BOOTSTRAP_MAX_SOURCE_BYTES
        ):
            raise QualificationContractError(
                f"bootstrap source violates its byte contract: {path}"
            )
        chunks: list[bytes] = []
        remaining = _BOOTSTRAP_MAX_SOURCE_BYTES + 1
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
            raise QualificationContractError(
                f"bootstrap source changed while read: {path}"
            )
        if len(source) != before.st_size or not source or remaining == 0:
            raise QualificationContractError(
                f"bootstrap source violates its byte contract: {path}"
            )
        return source
    finally:
        os.close(descriptor)


def _bootstrap_git_source(
    repository_root: Path,
    *,
    source_commit: str,
    repository_path: str,
) -> tuple[str, bytes]:
    """Read one Git-S blob with only stdlib and a sanitized system Git."""

    executable = shutil.which("git", path=os.defpath)
    if executable is None or not Path(executable).is_absolute():
        raise QualificationContractError("cannot resolve bootstrap system Git")
    environment = {
        "GIT_ATTR_NOSYSTEM": "1",
        "GIT_CONFIG_COUNT": "0",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_NOSYSTEM": "1",
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
    prefix = (
        executable,
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
        str(repository_root),
        "--no-optional-locks",
    )
    if (
        type(source_commit) is not str
        or len(source_commit) != 40
        or any(character not in "0123456789abcdef" for character in source_commit)
    ):
        raise QualificationContractError(
            "bootstrap source_commit must be exact lowercase full Git identity"
        )
    resolved = subprocess.run(
        (*prefix, "rev-parse", "--verify", f"{source_commit}^{{commit}}"),
        stdin=subprocess.DEVNULL,
        check=False,
        capture_output=True,
        env=environment,
    )
    if resolved.returncode != 0 or resolved.stdout != f"{source_commit}\n".encode(
        "ascii"
    ):
        raise QualificationContractError(
            "bootstrap source_commit does not resolve exactly"
        )
    listing = subprocess.run(
        (*prefix, "ls-tree", "-z", source_commit, "--", repository_path),
        stdin=subprocess.DEVNULL,
        check=False,
        capture_output=True,
        env=environment,
    )
    expected_suffix = f"\t{repository_path}\0".encode("utf-8")
    if (
        listing.returncode != 0
        or listing.stdout.count(b"\0") != 1
        or not listing.stdout.endswith(expected_suffix)
    ):
        raise QualificationContractError("bootstrap Git tree entry differs")
    metadata = listing.stdout[: -len(expected_suffix)].decode("ascii").split()
    if (
        len(metadata) != 3
        or metadata[0] not in {"100644", "100755"}
        or metadata[1] != "blob"
        or len(metadata[2]) != 40
        or any(character not in "0123456789abcdef" for character in metadata[2])
    ):
        raise QualificationContractError(
            "bootstrap Git tree mode, kind, or object identity differs"
        )
    process = subprocess.Popen(
        (
            *prefix,
            "cat-file",
            "blob",
            metadata[2],
        ),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        bufsize=0,
        env=environment,
    )
    try:
        if process.stdout is None:
            raise QualificationContractError("cannot open bootstrap Git output")
        chunks: list[bytes] = []
        remaining = _BOOTSTRAP_MAX_SOURCE_BYTES + 1
        while remaining:
            chunk = process.stdout.read(remaining)
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        output = b"".join(chunks)
        if remaining == 0:
            raise QualificationContractError(
                "bootstrap materialization Git blob exceeds its cap"
            )
        returncode = process.wait()
        if returncode != 0:
            detail = output.decode("utf-8", errors="replace").strip()
            raise QualificationContractError(
                "bootstrap materialization Git blob read failed: "
                f"{detail or returncode}"
            )
        if not output:
            raise QualificationContractError(
                "bootstrap materialization Git blob is empty"
            )
        return metadata[0], output
    except BaseException:
        if process.poll() is None:
            process.kill()
        process.wait()
        raise
    finally:
        if process.stdout is not None:
            process.stdout.close()


def _bootstrap_object_pairs(
    pairs: list[tuple[str, object]],
) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if type(key) is not str or key in result:
            raise ValueError("bootstrap C1 contains duplicate or non-string keys")
        result[key] = value
    return result


def _bootstrap_c1_members(c1: object) -> dict[str, tuple[str, int, str]]:
    """Parse only the source-member identities before records.py is trusted."""

    try:
        source = object.__getattribute__(c1, "_canonical_source")
    except (AttributeError, TypeError) as error:
        raise QualificationContractError(
            "bootstrap C1 does not expose immutable canonical source bytes"
        ) from error
    if (
        type(source) is not bytes
        or not source
        or len(source) > _BOOTSTRAP_MAX_SOURCE_BYTES
    ):
        raise QualificationContractError("bootstrap C1 violates its byte contract")
    try:
        document = json.loads(
            source.decode("utf-8", errors="strict"),
            object_pairs_hook=_bootstrap_object_pairs,
            parse_constant=lambda value: (_ for _ in ()).throw(
                ValueError(f"invalid JSON constant: {value}")
            ),
        )
    except (UnicodeDecodeError, ValueError, TypeError) as error:
        raise QualificationContractError("bootstrap C1 is not strict JSON") from error
    if type(document) is not dict or set(document) != {
        "schema_version",
        "record_id",
        "artifact_role",
        "successor_lineage_id",
        "payload",
        "typestate",
        "claim_boundary",
    }:
        raise QualificationContractError("bootstrap C1 root shape differs")
    if (
        document.get("schema_version")
        != "spirallens.d7-v1-c1-seed-free-source-set.v0.1"
        or document.get("artifact_role") != "c1-seed-free-source-set"
        or document.get("successor_lineage_id") != _SUCCESSOR_LINEAGE_ID
    ):
        raise QualificationContractError("bootstrap C1 identity differs")
    payload = document.get("payload")
    if type(payload) is not dict or set(payload) != {
        "repository_path",
        "route_binding",
        "source_members",
        "source_manifest_sha256",
        "source_member_count",
    }:
        raise QualificationContractError("bootstrap C1 payload shape differs")
    source_members = payload.get("source_members")
    if type(source_members) is not list or not source_members:
        raise QualificationContractError("bootstrap C1 source members differ")
    members: dict[str, tuple[str, int, str]] = {}
    for item in source_members:
        if type(item) is not dict or set(item) != {
            "schema_version",
            "repository_path",
            "git_mode",
            "sha256",
            "byte_count",
        }:
            raise QualificationContractError("bootstrap C1 source member shape differs")
        repository_path = item.get("repository_path")
        git_mode = item.get("git_mode")
        digest = item.get("sha256")
        byte_count = item.get("byte_count")
        if (
            item.get("schema_version") != "spirallens.d7-v1-source-member.v0.1"
            or type(repository_path) is not str
            or not repository_path
            or repository_path != str(PurePosixPath(repository_path))
            or PurePosixPath(repository_path).is_absolute()
            or ".." in PurePosixPath(repository_path).parts
            or git_mode not in {"100644", "100755"}
            or type(byte_count) is not int
            or byte_count < 0
            or type(digest) is not str
            or len(digest) != 64
            or any(character not in "0123456789abcdef" for character in digest)
        ):
            raise QualificationContractError("bootstrap C1 source member differs")
        if repository_path in members:
            raise QualificationContractError(
                "bootstrap C1 source member paths are not unique"
            )
        members[repository_path] = (git_mode, byte_count, digest)
    if payload.get("source_member_count") != len(members):
        raise QualificationContractError("bootstrap C1 source member count differs")
    return members


def _bootstrap_referent_documents_source(
    repository_root: Path,
    *,
    source_commit: str,
    c1: object,
) -> tuple[Path, bytes]:
    """Verify the fixed leaf bytes without importing or executing the leaf."""

    members = _bootstrap_c1_members(c1)
    member = members.get(_DESIGN_REFERENT_DOCUMENTS_PATH)
    if member is None:
        raise QualificationContractError(
            "bootstrap C1 omits D7 v1 design-referent document module"
        )
    target = repository_root.joinpath(
        *PurePosixPath(_DESIGN_REFERENT_DOCUMENTS_PATH).parts
    )
    mode, committed = _bootstrap_git_source(
        repository_root,
        source_commit=source_commit,
        repository_path=_DESIGN_REFERENT_DOCUMENTS_PATH,
    )
    live = _bootstrap_read_source(target)
    if (
        mode != member[0]
        or len(committed) != member[1]
        or hashlib.sha256(committed).hexdigest() != member[2]
        or live != committed
    ):
        raise QualificationContractError(
            "bootstrap design-referent document module differs from Git S and C1"
        )
    return target, committed


def _authenticated_referent_documents_module(
    repository: object,
    *,
    source_commit: str,
    c1: object,
) -> ModuleType:
    """Execute the canonical leaf only after its raw trust-root verification."""

    global _AUTHENTICATED_REFERENT_DOCUMENTS_CACHE
    global _AUTHENTICATED_REFERENT_DOCUMENTS_MODULE

    try:
        repository_root = object.__getattribute__(repository, "root")
    except (AttributeError, TypeError) as error:
        raise QualificationContractError(
            "bootstrap repository does not expose an exact root"
        ) from error
    if (
        not isinstance(repository_root, Path)
        or not repository_root.is_absolute()
        or ".." in repository_root.parts
    ):
        raise QualificationContractError(
            "bootstrap repository root must be an absolute normalized Path"
        )
    target, committed = _bootstrap_referent_documents_source(
        repository_root,
        source_commit=source_commit,
        c1=c1,
    )
    committed_sha256 = hashlib.sha256(committed).hexdigest()
    package_name, _, child_name = _DESIGN_REFERENT_DOCUMENTS_MODULE_NAME.rpartition(".")
    package = sys.modules.get(package_name)
    if not isinstance(package, ModuleType):
        raise QualificationContractError(
            "design-referent document parent package is not loaded exactly"
        )
    existing = sys.modules.get(_DESIGN_REFERENT_DOCUMENTS_MODULE_NAME)
    cache = _AUTHENTICATED_REFERENT_DOCUMENTS_CACHE
    if cache is None:
        cached = None
        cached_sha256 = None
        cached_specification = None
        cached_marker = None
    elif type(cache) is tuple and len(cache) == 4:
        cached, cached_sha256, cached_specification, cached_marker = cache
    else:
        raise QualificationContractError(
            "authenticated design-referent document cache shape differs"
        )
    if _AUTHENTICATED_REFERENT_DOCUMENTS_MODULE is not cached:
        raise QualificationContractError(
            "authenticated design-referent document cache binding differs"
        )
    if existing is not None:
        if cached is None or existing is not cached:
            raise QualificationContractError(
                "design-referent document module was preloaded outside its "
                "authenticated facade"
            )
        if committed_sha256 != cached_sha256:
            raise QualificationContractError(
                "cached design-referent document compiled source differs from "
                "current Git S/C1/live source"
            )
        try:
            origin_matches = target.samefile(existing.__file__)
            specification_origin_matches = target.samefile(existing.__spec__.origin)
        except (AttributeError, OSError, TypeError, ValueError):
            origin_matches = False
            specification_origin_matches = False
        if (
            not origin_matches
            or not specification_origin_matches
            or getattr(existing, "__name__", None)
            != _DESIGN_REFERENT_DOCUMENTS_MODULE_NAME
            or getattr(existing, "__package__", None) != package_name
            or getattr(existing, "__loader__", object()) is not None
            or getattr(getattr(existing, "__spec__", None), "name", None)
            != _DESIGN_REFERENT_DOCUMENTS_MODULE_NAME
            or getattr(getattr(existing, "__spec__", None), "loader", object())
            is not None
            or getattr(existing, "__cached__", object()) is not None
            or getattr(existing, "__spec__", None) is not cached_specification
            or getattr(cached_specification, "loader_state", None) is not cached_marker
            or getattr(cached_marker, "get", lambda _key: None)("schema_version")
            != "spirallens.authenticated-source-module.v0.1"
            or getattr(cached_marker, "get", lambda _key: None)("source_sha256")
            != cached_sha256
        ):
            raise QualificationContractError(
                "authenticated design-referent document module identity differs"
            )
        if vars(package).get(child_name) is not existing:
            raise QualificationContractError(
                "authenticated design-referent document package binding differs"
            )
        rechecked_target, rechecked_committed = _bootstrap_referent_documents_source(
            repository_root,
            source_commit=source_commit,
            c1=c1,
        )
        try:
            rechecked_target_matches = target.samefile(rechecked_target)
        except (OSError, TypeError, ValueError):
            rechecked_target_matches = False
        if (
            not rechecked_target_matches
            or hashlib.sha256(rechecked_committed).hexdigest() != cached_sha256
        ):
            raise QualificationContractError(
                "cached design-referent document source changed during reauthentication"
            )
        return existing
    if cached is not None:
        raise QualificationContractError(
            "authenticated design-referent document module was removed from runtime"
        )
    if child_name in vars(package):
        raise QualificationContractError(
            "design-referent document package attribute was preloaded outside its "
            "authenticated facade"
        )
    try:
        specification = importlib.util.find_spec(_DESIGN_REFERENT_DOCUMENTS_MODULE_NAME)
        specification_origin = None if specification is None else specification.origin
        specification_matches = target.samefile(specification_origin)
    except (ImportError, OSError, TypeError, ValueError):
        specification_matches = False
    if not specification_matches:
        raise QualificationContractError(
            "design-referent document module import specification differs"
        )
    specification = importlib.machinery.ModuleSpec(
        _DESIGN_REFERENT_DOCUMENTS_MODULE_NAME,
        loader=None,
        origin=str(target),
    )
    specification.has_location = True
    imported = ModuleType(_DESIGN_REFERENT_DOCUMENTS_MODULE_NAME)
    imported.__file__ = str(target)
    imported.__package__ = _DESIGN_REFERENT_DOCUMENTS_MODULE_NAME.rpartition(".")[0]
    imported.__loader__ = None
    imported.__spec__ = specification
    imported.__cached__ = None
    try:
        code = compile(
            committed,
            str(target),
            "exec",
            dont_inherit=True,
            optimize=0,
        )
        sys.modules[_DESIGN_REFERENT_DOCUMENTS_MODULE_NAME] = imported
        exec(code, imported.__dict__)
        if sys.modules.get(_DESIGN_REFERENT_DOCUMENTS_MODULE_NAME) is not imported:
            raise QualificationContractError(
                "design-referent document execution replaced its module identity"
            )
        try:
            imported_origin_matches = target.samefile(imported.__file__)
            imported_specification_origin_matches = target.samefile(
                imported.__spec__.origin
            )
        except (AttributeError, OSError, TypeError, ValueError):
            imported_origin_matches = False
            imported_specification_origin_matches = False
        if (
            not imported_origin_matches
            or not imported_specification_origin_matches
            or getattr(imported, "__name__", None)
            != _DESIGN_REFERENT_DOCUMENTS_MODULE_NAME
            or getattr(imported, "__package__", None) != package_name
            or getattr(imported, "__loader__", object()) is not None
            or getattr(getattr(imported, "__spec__", None), "name", None)
            != _DESIGN_REFERENT_DOCUMENTS_MODULE_NAME
            or getattr(getattr(imported, "__spec__", None), "loader", object())
            is not None
            or getattr(imported, "__cached__", object()) is not None
        ):
            raise QualificationContractError(
                "design-referent document module execution identity differs"
            )
        rechecked_target, rechecked_committed = _bootstrap_referent_documents_source(
            repository_root,
            source_commit=source_commit,
            c1=c1,
        )
        try:
            rechecked_target_matches = target.samefile(rechecked_target)
        except (OSError, TypeError, ValueError):
            rechecked_target_matches = False
        if (
            not rechecked_target_matches
            or hashlib.sha256(rechecked_committed).hexdigest() != committed_sha256
        ):
            raise QualificationContractError(
                "design-referent document source changed during authenticated execution"
            )
        marker = MappingProxyType(
            {
                "schema_version": "spirallens.authenticated-source-module.v0.1",
                "source_sha256": committed_sha256,
            }
        )
        specification.loader_state = marker
        setattr(package, child_name, imported)
    except BaseException:
        if vars(package).get(child_name) is imported:
            delattr(package, child_name)
        if sys.modules.get(_DESIGN_REFERENT_DOCUMENTS_MODULE_NAME) is imported:
            del sys.modules[_DESIGN_REFERENT_DOCUMENTS_MODULE_NAME]
        raise
    _AUTHENTICATED_REFERENT_DOCUMENTS_MODULE = imported
    _AUTHENTICATED_REFERENT_DOCUMENTS_CACHE = (
        imported,
        committed_sha256,
        specification,
        marker,
    )
    return imported


def _runtime_source_modules(
    materialization: object,
) -> tuple[tuple[object, str, str], ...]:
    return (
        *_CRITICAL_RUNTIME_MODULES,
        (materialization, _MATERIALIZATION_PATH, "materialization module"),
        (
            repository_context_module,
            _REPOSITORY_CONTEXT_PATH,
            "repository-context module",
        ),
        (canonical_module, _CANONICAL_PATH, "canonical module"),
        (common_module, _COMMON_PATH, "qualification common module"),
        (records, _RECORDS_PATH, "D7 v1 records module"),
    )


def _bootstrap_runtime_trust(
    repository: object,
    *,
    source_commit: str,
    c1: object,
    materialization: object,
    extra_modules: tuple[tuple[object, str, str], ...] = (),
) -> None:
    """Close the verifier trust root without invoking repository helpers."""

    try:
        repository_root = object.__getattribute__(repository, "root")
    except (AttributeError, TypeError) as error:
        raise QualificationContractError(
            "bootstrap repository does not expose an exact root"
        ) from error
    if (
        not isinstance(repository_root, Path)
        or not repository_root.is_absolute()
        or ".." in repository_root.parts
    ):
        raise QualificationContractError(
            "bootstrap repository root must be an absolute normalized Path"
        )
    members = _bootstrap_c1_members(c1)
    module_specs = (
        *_runtime_source_modules(materialization),
        *extra_modules,
        (None, _MODULE_PATH, "full-design referent module"),
    )
    paths = tuple(repository_path for _module, repository_path, _label in module_specs)
    if len(set(paths)) != len(paths):
        raise QualificationContractError(
            "bootstrap runtime source paths are not unique"
        )
    for module, repository_path, label in module_specs:
        imported_file = (
            __file__ if module is None else getattr(module, "__file__", None)
        )
        target = repository_root.joinpath(*PurePosixPath(repository_path).parts)
        try:
            origin_matches = target.samefile(imported_file)
        except (OSError, TypeError, ValueError):
            origin_matches = False
        if not origin_matches:
            raise QualificationContractError(
                f"bootstrap {label} import origin differs from repository"
            )
        member = members.get(repository_path)
        if member is None:
            raise QualificationContractError(f"bootstrap C1 omits executed {label}")
        mode, committed = _bootstrap_git_source(
            repository_root,
            source_commit=source_commit,
            repository_path=repository_path,
        )
        live = _bootstrap_read_source(target)
        if (
            mode != member[0]
            or len(committed) != member[1]
            or hashlib.sha256(committed).hexdigest() != member[2]
            or live != committed
        ):
            raise QualificationContractError(
                f"bootstrap executed {label} differs from Git S and C1 bytes"
            )


@dataclass(frozen=True, slots=True)
class _PinnedScientificParent:
    role: str
    repository_path: str
    source_commit: str
    binding: records.D7V1ArtifactBinding
    source: bytes
    document: Mapping[str, object]

    def __post_init__(self) -> None:
        if self.role not in _PARENT_ROLES:
            raise QualificationContractError("scientific parent role differs")
        if self.binding.artifact_role != self.role:
            raise QualificationContractError("scientific parent binding role differs")
        if (
            len(self.source) != self.binding.byte_count
            or sha256_bytes(self.source) != self.binding.canonical_sha256
            or self.document.get("schema_version") != self.binding.artifact_contract_id
        ):
            raise QualificationContractError(
                f"{self.role} source identity differs from its binding"
            )


def _require_runtime_origins(
    repository: RepositoryContext,
    *,
    protocol: D7V1MaterializationProtocol,
    source_commit: str,
    c1: records.D7V1C1SourceSetRecord,
) -> None:
    """Bind every executed critical module to its imported inode, Git S, and C1."""

    from . import confirmation_v1_materialization as materialization

    _bootstrap_runtime_trust(
        repository,
        source_commit=source_commit,
        c1=c1,
        materialization=materialization,
    )
    if not isinstance(repository, RepositoryContext):
        raise TypeError("repository must be RepositoryContext")
    if not isinstance(protocol, materialization.D7V1MaterializationProtocol):
        raise TypeError("protocol must be D7V1MaterializationProtocol")
    if not isinstance(c1, records.D7V1C1SourceSetRecord):
        raise TypeError("c1 must be D7V1C1SourceSetRecord")
    runtime_modules = _runtime_source_modules(materialization)
    c1_payload = _mapping(c1.to_dict().get("payload"), label="C1 payload")
    members = tuple(
        records.D7V1SourceMember.from_dict(item)
        for item in _sequence(
            c1_payload.get("source_members"),
            label="C1 source members",
        )
    )
    by_path = {member.repository_path: member for member in members}
    if len(by_path) != len(members):
        raise QualificationContractError("C1 source member paths are not unique")
    for module, repository_path, label in runtime_modules:
        if not repository.matches_imported_file(
            imported_file=module.__file__,
            repository_path=repository_path,
        ):
            raise QualificationContractError(f"{label} import origin differs")
    if not repository.matches_imported_file(
        imported_file=__file__,
        repository_path=_MODULE_PATH,
    ):
        raise QualificationContractError(
            "full-design referent module import origin differs"
        )
    for module, repository_path, label in (
        *runtime_modules,
        (
            None,
            _MODULE_PATH,
            "full-design referent module",
        ),
    ):
        member = by_path.get(repository_path)
        if member is None:
            raise QualificationContractError(f"C1 omits executed {label}")
        mode, committed = materialization._git_blob(
            repository,
            source_commit,
            repository_path,
            maximum_bytes=materialization._MAX_SOURCE_MEMBER_BYTES,
        )
        live = materialization._safe_read_file(
            repository.root / repository_path,
            materialization._MAX_SOURCE_MEMBER_BYTES,
            require_single_link=False,
        )
        if (
            mode != member.git_mode
            or len(committed) != member.byte_count
            or sha256_bytes(committed) != member.sha256
            or live != committed
        ):
            raise QualificationContractError(
                f"executed {label} differs from imported Git S and C1 bytes"
            )
    approved = execution_design.build_seed_free_d7_confirmation_execution_design
    signature = inspect.signature(approved)
    if (
        not isinstance(approved, FunctionType)
        or approved.__module__ != execution_design.__name__
        or approved.__qualname__ != "build_seed_free_d7_confirmation_execution_design"
        or tuple(signature.parameters) != ("loaded_d6", "parent_protocol")
        or any(
            parameter.kind is not inspect.Parameter.KEYWORD_ONLY
            for parameter in signature.parameters.values()
        )
    ):
        raise QualificationContractError(
            "approved seed-free execution-design callable identity differs"
        )
    source_contract = _mapping(
        protocol.document.get("source_contract"),
        label="source_contract",
    )
    approved_entries = tuple(
        _mapping(item, label="approved exact runtime reuse")
        for item in _sequence(
            source_contract.get("approved_exact_function_runtime_reuse"),
            label="approved_exact_function_runtime_reuse",
        )
        if isinstance(item, Mapping)
        and item.get("allowed_symbol")
        == "build_seed_free_d7_confirmation_execution_design"
    )
    if approved_entries != (
        {
            "allowed_symbol": "build_seed_free_d7_confirmation_execution_design",
            "authority_transfer_allowed": False,
            "future_c1_must_bind_transitive_dependency_closure": True,
            "persistence_transfer_allowed": False,
            "repository_path": _EXECUTION_DESIGN_PATH,
            "reuse_scope": "runtime_function_only",
            "runtime_purpose": (
                "fresh_five_parent_seed_free_scientific_projection_only"
            ),
            "schema_transfer_allowed": False,
            "source_commit": "2645ab360598c9ff4f1d9e628b9a9fe1857aedf6",
            "source_sha256": (
                "824553e20b29e74f29959755079d9b0d87b4f244d95d6988a97e94dc52889d13"
            ),
        },
    ):
        raise QualificationContractError(
            "approved seed-free execution-design reuse contract differs"
        )
    approved_entry = approved_entries[0]
    approved_commit = materialization._resolve_commit(
        repository,
        _string(
            approved_entry.get("source_commit"),
            label="approved execution-design source_commit",
        ),
        label="approved execution-design source_commit",
    )
    if not materialization._is_ancestor(
        repository,
        approved_commit,
        source_commit,
    ):
        raise QualificationContractError(
            "approved execution-design source commit is not an ancestor of S"
        )
    expected_approved_sha = require_sha256(
        approved_entry.get("source_sha256"),
        label="approved execution-design source_sha256",
    )
    _mode, approved_source = materialization._git_blob(
        repository,
        approved_commit,
        _EXECUTION_DESIGN_PATH,
        maximum_bytes=materialization._MAX_SOURCE_MEMBER_BYTES,
    )
    current_member = by_path[_EXECUTION_DESIGN_PATH]
    if (
        sha256_bytes(approved_source) != expected_approved_sha
        or current_member.sha256 != expected_approved_sha
    ):
        raise QualificationContractError(
            "execution-design source differs from its approved historical digest"
        )


def _load_scientific_parents(
    repository: RepositoryContext,
    protocol: D7V1MaterializationProtocol,
    *,
    source_commit: str,
) -> tuple[_PinnedScientificParent, ...]:
    from . import confirmation_v1_materialization as materialization

    policy = _mapping(
        protocol.document.get("historical_input_policy"),
        label="historical_input_policy",
    )
    entries = tuple(
        _mapping(item, label="permitted historical scientific parent")
        for item in _sequence(
            policy.get("permitted_historical_scientific_parents"),
            label="permitted historical scientific parents",
        )
    )
    roles = tuple(
        _string(entry.get("artifact_binding_role"), label="scientific parent role")
        for entry in entries
    )
    if roles != _PARENT_ROLES:
        raise QualificationContractError(
            "permitted historical scientific parents differ from exact five roles"
        )
    result: list[_PinnedScientificParent] = []
    for entry, role in zip(entries, roles, strict=True):
        if set(entry) != {
            "artifact_binding_role",
            "artifact_contract_id",
            "authority_for_v1",
            "byte_count",
            "canonical_sha256",
            "descriptive_input_allowed",
            "repository_path",
            "role",
            "source_commit",
        }:
            raise QualificationContractError(
                f"{role} scientific parent metadata keyset differs"
            )
        if (
            entry.get("authority_for_v1") is not False
            or entry.get("descriptive_input_allowed") is not True
            or entry.get("role") != role
        ):
            raise QualificationContractError(
                f"{role} scientific parent permission boundary differs"
            )
        parent_commit = materialization._resolve_commit(
            repository,
            _string(entry.get("source_commit"), label=f"{role} source_commit"),
            label=f"{role} source_commit",
        )
        if not materialization._is_ancestor(
            repository,
            parent_commit,
            source_commit,
        ):
            raise QualificationContractError(
                f"{role} source commit is not an ancestor of source S"
            )
        repository_path = materialization._relative_path(
            entry.get("repository_path"),
            label=f"{role} repository_path",
        )
        expected_size = _plain_int(
            entry.get("byte_count"),
            label=f"{role} byte_count",
            minimum=1,
        )
        expected_sha = require_sha256(
            entry.get("canonical_sha256"),
            label=f"{role} canonical_sha256",
        )
        _mode, source = materialization._git_blob(
            repository,
            parent_commit,
            repository_path,
            maximum_bytes=expected_size,
        )
        if len(source) != expected_size or sha256_bytes(source) != expected_sha:
            raise QualificationContractError(f"{role} historical bytes differ")
        document = _parse_exact_canonical(source, label=f"{role} historical parent")
        contract = _string(
            entry.get("artifact_contract_id"),
            label=f"{role} artifact_contract_id",
        )
        if document.get("schema_version") != contract:
            raise QualificationContractError(f"{role} historical schema differs")
        result.append(
            _PinnedScientificParent(
                role=role,
                repository_path=repository_path,
                source_commit=parent_commit,
                binding=records.D7V1ArtifactBinding(
                    artifact_role=role,
                    artifact_contract_id=contract,
                    canonical_sha256=expected_sha,
                    byte_count=expected_size,
                ),
                source=source,
                document=MappingProxyType(document),
            )
        )
    return tuple(result)


def _require_parent_joins(parents: Sequence[_PinnedScientificParent]) -> None:
    if tuple(parent.role for parent in parents) != _PARENT_ROLES:
        raise QualificationContractError(
            "scientific parent adapter input differs from ordered exact five"
        )
    protocol, result, manifest, consumption, d6 = (
        parent.document for parent in parents
    )
    bindings = {parent.role: parent.binding for parent in parents}
    protocol_sha = bindings["parent-protocol"].canonical_sha256
    result_sha = bindings["parent-result"].canonical_sha256
    manifest_sha = bindings["parent-manifest"].canonical_sha256
    consumption_sha = bindings["parent-consumption"].canonical_sha256
    joins = (
        (result.get("protocol_canonical_sha256"), protocol_sha),
        (result.get("protocol_source_sha256"), protocol_sha),
        (manifest.get("terminal_artifact_sha256"), result_sha),
        (manifest.get("consumption_sha256"), consumption_sha),
        (consumption.get("terminal_artifact_sha256"), result_sha),
        (consumption.get("protocol_canonical_sha256"), protocol_sha),
        (consumption.get("protocol_source_sha256"), protocol_sha),
    )
    if any(observed != expected for observed, expected in joins):
        raise QualificationContractError("five-parent identity join differs")
    terminal = _mapping(d6.get("selection_terminal"), label="D6 selection terminal")
    d6_joins = (
        (terminal.get("result_sha256"), result_sha),
        (terminal.get("terminal_manifest_sha256"), manifest_sha),
        (terminal.get("consumption_sha256"), consumption_sha),
        (terminal.get("protocol_canonical_sha256"), protocol_sha),
        (terminal.get("protocol_source_sha256"), protocol_sha),
    )
    if any(observed != expected for observed, expected in d6_joins):
        raise QualificationContractError("D6 scientific parent join differs")
    protocol_ids = (
        protocol.get("protocol_id"),
        result.get("protocol_id"),
        consumption.get("protocol_id"),
        terminal.get("protocol_id"),
    )
    if len(set(protocol_ids)) != 1:
        raise QualificationContractError("scientific parent protocol ids differ")
    for name in (
        "selection_execution_started",
        "terminally_consumed",
    ):
        _boolean(consumption.get(name), label=f"parent consumption {name}")
    if consumption.get("terminally_consumed") is not True:
        raise QualificationContractError("parent consumption is not terminal")


def _advancement_source_surface_at_commit(
    repository: RepositoryContext,
    source_commit: str,
) -> tuple[tuple[tuple[str, str, bytes], ...], str]:
    """Reconstruct one source-only advancement binding with sanitized Git."""

    from . import confirmation_v1_materialization as materialization

    source_commit = materialization._resolve_commit(
        repository,
        source_commit,
        label="advancement source commit",
    )
    listing = materialization._git_bounded(
        repository,
        materialization._MAX_SOURCE_TREE_METADATA_BYTES,
        "ls-tree",
        "-r",
        "--name-only",
        "-z",
        source_commit,
        "--",
        "src/spirallens",
        "scripts/seal_d6_surrogate_advancement.py",
    )
    try:
        entries = tuple(item.decode("utf-8") for item in listing.split(b"\0") if item)
    except UnicodeDecodeError as error:
        raise QualificationContractError(
            "advancement source paths are not UTF-8"
        ) from error
    paths = tuple(
        sorted(
            path
            for path in entries
            if path == "scripts/seal_d6_surrogate_advancement.py"
            or (path.startswith("src/spirallens/") and path.endswith(".py"))
        )
    )
    if (
        not paths
        or len(paths) != len(set(paths))
        or len(paths) > materialization._MAX_SOURCE_TREE_FILE_COUNT
        or "scripts/seal_d6_surrogate_advancement.py" not in paths
    ):
        raise QualificationContractError(
            "independent advancement source surface is incomplete"
        )
    surface: list[tuple[str, str, bytes]] = []
    files: list[dict[str, str]] = []
    total_bytes = 0
    for repository_path in paths:
        mode, source = materialization._git_blob(
            repository,
            source_commit,
            repository_path,
            maximum_bytes=materialization._MAX_SOURCE_MEMBER_BYTES,
        )
        total_bytes += len(source)
        if total_bytes > materialization._MAX_SOURCE_TREE_TOTAL_BYTES:
            raise QualificationContractError(
                "advancement source surface exceeds its aggregate byte cap"
            )
        digest = sha256_bytes(source)
        surface.append((repository_path, mode, source))
        files.append(
            {
                "repository_path": repository_path,
                "sha256": digest,
            }
        )
    binding = sha256_bytes(
        canonical_json_bytes(
            {
                "schema_version": advancement.ADVANCEMENT_SOURCE_BINDING_SCHEMA_VERSION,
                "commit": source_commit,
                "files": files,
                "source_only": True,
                "runtime_attested": False,
                "hostile_process_attested": False,
            }
        )
    )
    return tuple(surface), binding


def _advancement_source_binding_at_s(
    repository: RepositoryContext,
    source_commit: str,
    c1: records.D7V1C1SourceSetRecord,
) -> str:
    """Independently reconstruct the source-only advancement binding at S."""

    from . import confirmation_v1_materialization as materialization

    surface, independent = _advancement_source_surface_at_commit(
        repository,
        source_commit,
    )
    paths = tuple(repository_path for repository_path, _mode, _source in surface)
    c1_payload = _mapping(c1.to_dict().get("payload"), label="C1 payload")
    members = tuple(
        records.D7V1SourceMember.from_dict(item)
        for item in _sequence(
            c1_payload.get("source_members"),
            label="C1 source members",
        )
    )
    by_path = {member.repository_path: member for member in members}
    if len(by_path) != len(members):
        raise QualificationContractError("C1 source member paths are not unique")
    expected_python_paths = tuple(
        path for path in paths if path.startswith("src/spirallens/")
    )
    c1_python_paths = tuple(
        sorted(
            path
            for path in by_path
            if path.startswith("src/spirallens/") and path.endswith(".py")
        )
    )
    if c1_python_paths != expected_python_paths:
        raise QualificationContractError(
            "C1 Python surface differs from advancement Git S paths"
        )
    filesystem_entries = tuple((repository.root / "src/spirallens").rglob("*.py"))
    if any(path.is_symlink() or not path.is_file() for path in filesystem_entries):
        raise QualificationContractError(
            "live advancement Python surface contains a non-regular path"
        )
    filesystem_paths = tuple(
        sorted(
            path.relative_to(repository.root).as_posix() for path in filesystem_entries
        )
    )
    if filesystem_paths != expected_python_paths:
        raise QualificationContractError(
            "live advancement Python path set differs from Git S"
        )
    sealer_path = "scripts/seal_d6_surrogate_advancement.py"
    for repository_path, mode, committed in surface:
        live = materialization._safe_read_file(
            repository.root / repository_path,
            materialization._MAX_SOURCE_MEMBER_BYTES,
            require_single_link=False,
        )
        if repository_path == sealer_path:
            if live != committed:
                raise QualificationContractError(
                    "live advancement sealer differs from Git S"
                )
            continue
        member = by_path.get(repository_path)
        if member is None:
            raise QualificationContractError(
                f"C1 omits advancement source: {repository_path}"
            )
        digest = sha256_bytes(committed)
        if (
            mode != member.git_mode
            or len(committed) != member.byte_count
            or digest != member.sha256
            or live != committed
        ):
            raise QualificationContractError(
                f"live advancement source differs from Git S/C1: {repository_path}"
            )
    return independent


def _typed_adapter(
    repository: RepositoryContext,
    *,
    source_commit: str,
    c1: records.D7V1C1SourceSetRecord,
    parents: Sequence[_PinnedScientificParent],
    referent_documents: ModuleType,
) -> D7V1TypedScientificParentAdapter:
    """Rebuild every typed historical companion before creating ephemeral D6."""

    from . import confirmation_v1_materialization as materialization

    _require_parent_joins(parents)
    by_role = {parent.role: parent for parent in parents}
    parent_protocol = by_role["parent-protocol"]
    protocol_object = qualification_protocol.QualificationProtocol.from_dict(
        parent_protocol.document
    )
    if protocol_object.canonical_bytes != parent_protocol.source:
        raise QualificationContractError(
            "typed parent protocol differs from its exact historical bytes"
        )
    loaded_protocol = persistence.LoadedQualificationProtocol(
        protocol=protocol_object,
        source_path=(repository.root / parent_protocol.repository_path).resolve(),
        source_bytes=parent_protocol.source,
        source_sha256=parent_protocol.binding.canonical_sha256,
        canonical_sha256=parent_protocol.binding.canonical_sha256,
    )

    parent_result = by_role["parent-result"]
    typed_result = contracts.QualificationResult.from_dict(parent_result.document)
    if typed_result.canonical_bytes != parent_result.source:
        raise QualificationContractError(
            "typed parent result differs from its exact historical bytes"
        )
    if (
        typed_result.source_binding.engine_commit != protocol_object.engine.commit
        or typed_result.source_binding.module_count
        != len(protocol_object.engine.modules)
        or typed_result.source_binding.registry_source_sha256
        != protocol_object.registry.registry_source_sha256
        or typed_result.source_binding.registry_canonical_sha256
        != protocol_object.registry.registry_canonical_sha256
        or typed_result.source_binding.referent_canonical_sha256
        != protocol_object.registry.referent_canonical_sha256
    ):
        raise QualificationContractError(
            "typed parent result source binding differs from parent protocol"
        )
    parent_manifest = by_role["parent-manifest"]
    typed_manifest = freeze.SelectionTerminalManifestArtifact.from_dict(
        parent_manifest.document
    )
    if typed_manifest.canonical_bytes != parent_manifest.source:
        raise QualificationContractError(
            "typed parent manifest differs from its exact historical bytes"
        )
    parent_consumption = by_role["parent-consumption"]
    typed_consumption = freeze.SelectionConsumptionArtifact.from_dict(
        parent_consumption.document
    )
    if typed_consumption.canonical_bytes != parent_consumption.source:
        raise QualificationContractError(
            "typed parent consumption differs from its exact historical bytes"
        )
    if (
        typed_consumption.engine_commit != protocol_object.engine.commit
        or typed_consumption.seed_family_commitment_sha256
        != freeze.seed_family_commitment_sha256(
            seed_family_id=typed_consumption.seed_family_id,
            seeds=protocol_object.selection.seeds,
        )
    ):
        raise QualificationContractError(
            "typed parent consumption engine or seed family differs from protocol"
        )
    if (
        typed_manifest.terminal_artifact_kind
        is not freeze.TerminalAttemptArtifactKind.RESULT
        or typed_consumption.terminal_artifact_kind
        is not freeze.TerminalAttemptArtifactKind.RESULT
        or typed_manifest.terminal_artifact_kind
        is not typed_consumption.terminal_artifact_kind
        or typed_manifest.terminal_artifact_sha256
        != parent_result.binding.canonical_sha256
        or typed_manifest.terminal_artifact_byte_count != len(parent_result.source)
        or typed_manifest.consumption_sha256
        != parent_consumption.binding.canonical_sha256
        or typed_manifest.consumption_byte_count != len(parent_consumption.source)
        or typed_consumption.terminal_artifact_sha256
        != parent_result.binding.canonical_sha256
        or typed_manifest.freeze_artifact_sha256
        != typed_result.selection_freeze_artifact_sha256
        or typed_manifest.freeze_artifact_sha256
        != typed_consumption.freeze_artifact_sha256
        or typed_manifest.attempt_claim_sha256
        != typed_result.selection_attempt_claim_sha256
        or typed_manifest.attempt_claim_sha256 != typed_consumption.attempt_claim_sha256
    ):
        raise QualificationContractError(
            "typed terminal manifest byte counts or companion identities differ"
        )
    terminal_identity = freeze.PersistedSelectionTerminalIdentity(
        path=(
            repository.root / ".git" / "d7-v1-virtual-parent-terminal-identity"
        ).resolve(),
        manifest_sha256=parent_manifest.binding.canonical_sha256,
        terminal_artifact_sha256=parent_result.binding.canonical_sha256,
        consumption_sha256=parent_consumption.binding.canonical_sha256,
    )
    rebuilt_terminal = advancement.build_selection_terminal_binding(
        result=typed_result,
        protocol=protocol_object,
        terminal_identity=terminal_identity,
        consumption=typed_consumption,
    )

    parent_d6 = by_role["parent-d6-decision"]
    parsed_decision = advancement.SurrogateAdvancementDecision.from_dict(
        parent_d6.document
    )
    if parsed_decision.canonical_bytes != parent_d6.source:
        raise QualificationContractError(
            "typed D6 decision differs from its exact historical bytes"
        )
    if not materialization._is_ancestor(
        repository,
        parsed_decision.decision_source_commit,
        parent_d6.source_commit,
    ):
        raise QualificationContractError(
            "D6 decision source commit is not an ancestor of its artifact commit"
        )
    if not materialization._git_path_absent(
        repository,
        parsed_decision.decision_source_commit,
        parent_d6.repository_path,
    ):
        raise QualificationContractError(
            "D6 decision artifact already existed at its decision source commit"
        )
    if rebuilt_terminal != parsed_decision.selection_terminal:
        raise QualificationContractError(
            "rebuilt selection terminal binding differs from persisted D6"
        )
    rebuilt_admission = advancement.IndependentConfirmationAdmissionSpec.from_selection(
        rebuilt_terminal,
        admission_spec_id=(
            parsed_decision.confirmation_admission_spec.admission_spec_id
        ),
    )
    if rebuilt_admission != parsed_decision.confirmation_admission_spec:
        raise QualificationContractError(
            "rebuilt confirmation admission spec differs from persisted D6"
        )
    resealed_decision = advancement.SurrogateAdvancementDecision.seal(
        decision_id=parsed_decision.decision_id,
        decision_source_commit=parsed_decision.decision_source_commit,
        decision_source_binding_sha256=(parsed_decision.decision_source_binding_sha256),
        selection_terminal=rebuilt_terminal,
        admission_spec=rebuilt_admission,
    )
    if resealed_decision.canonical_bytes != parent_d6.source:
        raise QualificationContractError(
            "freshly resealed D6 decision differs from persisted canonical bytes"
        )
    if not materialization._is_ancestor(
        repository,
        parsed_decision.decision_source_commit,
        source_commit,
    ):
        raise QualificationContractError(
            "D6 decision source commit is not an ancestor of source S"
        )
    _decision_surface, decision_source_binding = _advancement_source_surface_at_commit(
        repository,
        parsed_decision.decision_source_commit,
    )
    if decision_source_binding != parsed_decision.decision_source_binding_sha256:
        raise QualificationContractError(
            "D6 decision source binding differs from its historical Git blobs"
        )
    identity = advancement.PersistedAdvancementIdentity(
        path=(repository.root / parent_d6.repository_path).resolve(),
        source_sha256=parent_d6.binding.canonical_sha256,
        canonical_sha256=parent_d6.binding.canonical_sha256,
        byte_count=parent_d6.binding.byte_count,
        parent_directory_fsync_verified=False,
    )
    loaded_artifact = advancement.LoadedAdvancementArtifact(
        artifact=resealed_decision,
        identity=identity,
        source_bytes=parent_d6.source,
    )
    current_loader_source_binding_sha256 = _advancement_source_binding_at_s(
        repository,
        source_commit,
        c1,
    )
    loaded_d6 = advancement._build_authoritative_loaded_d6_decision(
        loaded_artifact,
        current_loader_source_commit=source_commit,
        current_loader_source_binding_sha256=(current_loader_source_binding_sha256),
    )
    design = execution_design.build_seed_free_d7_confirmation_execution_design(
        loaded_d6=loaded_d6,
        parent_protocol=loaded_protocol,
    )
    bindings = {parent.role: parent.binding for parent in parents}
    join_sha = sha256_bytes(
        canonical_json_bytes(
            {
                "schema_version": "spirallens.d7-v1-five-parent-join.v0.1",
                "parent_bindings": [
                    _binding_document(bindings[role]) for role in _PARENT_ROLES
                ],
                "confirmation_admission_sha256": rebuilt_admission.canonical_sha256,
                "execution_design_sha256": design.canonical_sha256,
            }
        )
    )
    (
        validated_parent_bindings,
        validated_confirmation_admission,
        validated_execution_design,
        validated_parent_join_sha256,
    ) = referent_documents._validated_parent_adapter_fields(
        parent_bindings=bindings,
        confirmation_admission=rebuilt_admission.to_dict(),
        execution_design=design,
        parent_join_sha256=join_sha,
    )
    adapter = object.__new__(referent_documents.D7V1TypedScientificParentAdapter)
    object.__setattr__(adapter, "parent_bindings", validated_parent_bindings)
    object.__setattr__(
        adapter,
        "confirmation_admission",
        validated_confirmation_admission,
    )
    object.__setattr__(adapter, "execution_design", validated_execution_design)
    object.__setattr__(
        adapter,
        "parent_join_sha256",
        validated_parent_join_sha256,
    )
    return adapter


def _derive_d7_v1_full_design_referent_set_candidate(
    repository: RepositoryContext,
    *,
    protocol: D7V1MaterializationProtocol,
    source_commit: str,
    c1: records.D7V1C1SourceSetRecord,
    c2: records.D7V1C2SourceClosureReceipt,
) -> D7V1FullDesignReferentSetCandidate:
    """Derive six virtual referents from the exact verified S/C1/C2 join."""

    from . import confirmation_v1_materialization as materialization

    _require_runtime_origins(
        repository,
        protocol=protocol,
        source_commit=source_commit,
        c1=c1,
    )
    if not isinstance(repository, RepositoryContext):
        raise TypeError("repository must be RepositoryContext")
    if not isinstance(protocol, materialization.D7V1MaterializationProtocol):
        raise TypeError("protocol must be D7V1MaterializationProtocol")
    if not isinstance(c1, records.D7V1C1SourceSetRecord):
        raise TypeError("c1 must be D7V1C1SourceSetRecord")
    if not isinstance(c2, records.D7V1C2SourceClosureReceipt):
        raise TypeError("c2 must be D7V1C2SourceClosureReceipt")
    joined_source = materialization._verify_source_join(
        repository,
        protocol,
        c1,
        c2,
    )
    if joined_source != source_commit:
        raise QualificationContractError(
            "full-design referent source_commit differs from exact S/C1/C2 join"
        )
    referent_documents = _authenticated_referent_documents_module(
        repository,
        source_commit=source_commit,
        c1=c1,
    )
    parents = _load_scientific_parents(
        repository,
        protocol,
        source_commit=source_commit,
    )
    adapter = _typed_adapter(
        repository,
        source_commit=source_commit,
        c1=c1,
        parents=parents,
        referent_documents=referent_documents,
    )
    derivation = referent_documents._derivation_document(
        source_commit=source_commit,
        c1=c1,
        c2=c2,
        adapter=adapter,
    )
    payloads = referent_documents._referent_payloads(
        protocol=protocol,
        source_commit=source_commit,
        c1=c1,
        adapter=adapter,
    )
    referents: dict[str, object] = {}
    for role in referent_documents._ROLE_SPECS:
        (
            validated_role,
            validated_contract_id,
            validated_canonical_bytes,
            validated_canonical_sha256,
            validated_byte_count,
        ) = referent_documents._validated_canonical_referent_fields(
            artifact_role=role,
            document=referent_documents._document(
                role,
                derivation=derivation,
                payload=payloads[role],
            ),
        )
        referent = object.__new__(referent_documents.D7V1CanonicalDesignReferent)
        object.__setattr__(referent, "artifact_role", validated_role)
        object.__setattr__(referent, "artifact_contract_id", validated_contract_id)
        object.__setattr__(referent, "canonical_bytes", validated_canonical_bytes)
        object.__setattr__(referent, "canonical_sha256", validated_canonical_sha256)
        object.__setattr__(referent, "byte_count", validated_byte_count)
        referents[role] = referent
    (
        validated_source_commit,
        validated_parent_adapter,
        validated_referents_by_role,
        validated_bindings_by_inventory_field,
    ) = referent_documents._validated_referent_set_fields(
        source_commit=source_commit,
        parent_adapter=adapter,
        referents_by_role=referents,
    )
    candidate = object.__new__(referent_documents.D7V1FullDesignReferentSetCandidate)
    object.__setattr__(candidate, "source_commit", validated_source_commit)
    object.__setattr__(candidate, "parent_adapter", validated_parent_adapter)
    object.__setattr__(candidate, "referents_by_role", validated_referents_by_role)
    object.__setattr__(
        candidate,
        "bindings_by_inventory_field",
        validated_bindings_by_inventory_field,
    )
    return candidate


def _build_d7_v1_full_design_referent_set_candidate(
    repository: RepositoryContext,
    *,
    deterministic_inputs: D7V1DeterministicInputContractCandidate,
) -> D7V1FullDesignReferentSetCandidate:
    """Build the candidate from a clean repository whose HEAD is source S."""

    from . import confirmation_v1_deterministic_inputs as deterministic_module
    from . import confirmation_v1_materialization as materialization
    from . import confirmation_v1_source_closure as source_closure_module

    try:
        closure = object.__getattribute__(deterministic_inputs, "source_closure")
        source_commit = object.__getattribute__(closure, "source_commit")
        c1 = object.__getattribute__(closure, "c1")
        c2 = object.__getattribute__(closure, "c2")
    except (AttributeError, TypeError) as error:
        raise QualificationContractError(
            "deterministic inputs do not expose their exact source closure"
        ) from error
    _bootstrap_runtime_trust(
        repository,
        source_commit=source_commit,
        c1=c1,
        materialization=materialization,
        extra_modules=(
            (
                deterministic_module,
                _DETERMINISTIC_INPUTS_PATH,
                "deterministic-input module",
            ),
            (
                source_closure_module,
                _SOURCE_CLOSURE_PATH,
                "source-closure module",
            ),
        ),
    )
    if not isinstance(
        deterministic_inputs,
        deterministic_module.D7V1DeterministicInputContractCandidate,
    ):
        raise TypeError(
            "deterministic_inputs must be D7V1DeterministicInputContractCandidate"
        )
    if not isinstance(closure, source_closure_module.D7V1SourceClosureCandidate):
        raise TypeError("deterministic_inputs.source_closure has the wrong type")
    protocol = materialization._protocol_at_commit(repository, source_commit)
    if (
        materialization._verify_source_join(repository, protocol, c1, c2)
        != source_commit
    ):
        raise QualificationContractError(
            "deterministic-input source closure rejoins a different source commit"
        )
    supplier_role, seed_slots, full_design_roles = (
        deterministic_module._declared_contract(protocol)
    )
    if (
        deterministic_inputs.source_commit != source_commit
        or deterministic_inputs.source_closure is not closure
        or deterministic_inputs.supplier_identity_role != supplier_role
        or deterministic_inputs.required_seed_count != len(seed_slots)
        or deterministic_inputs.seed_slot_ids != seed_slots
        or dict(deterministic_inputs.full_design_field_roles) != full_design_roles
    ):
        raise QualificationContractError(
            "supplied deterministic inputs differ from the fresh clean-S rejoin"
        )
    result = _derive_d7_v1_full_design_referent_set_candidate(
        repository,
        protocol=protocol,
        source_commit=source_commit,
        c1=c1,
        c2=c2,
    )
    source_closure_module._require_exact_clean_head(
        repository,
        source_commit,
    )
    return result
