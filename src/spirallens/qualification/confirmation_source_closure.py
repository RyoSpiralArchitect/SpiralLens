"""Choice-free C2 source closure for the committed D7 C1 candidate.

The issuer derives C1 from a clean current ``HEAD``.  It accepts no commit,
digest, seed, gate, result, policy, or admission choice.  It verifies the
tracked C1 bundle, re-enumerates every ``src/spirallens/**/*.py`` blob plus
``pyproject.toml`` from the C1 Git tree, and writes the fixed receipt path once.

The receipt binds C1 but never embeds the future C2 commit that will contain
the receipt; doing so would be self-referential.  A later read-only loader
derives the unique receipt-introduction commit and proves that its single
parent is C1 and its entire delta is the one added receipt.

This is source-only Level-0 evidence.  It does not execute historical code,
attest Python or native runtime state, prove in-process callable identity,
admit the construction family, freeze a seed, authorize execution, or produce
a D7 result.
"""

from __future__ import annotations

import os
import re
import subprocess
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import ClassVar

from spirallens.core.canonical import (
    CanonicalJsonError,
    canonical_json_bytes,
    parse_canonical_json,
    sha256_bytes,
)

from .common import QualificationContractError, require_sha256
from .confirmation_c1 import (
    D7_C1_BUNDLE_REPOSITORY_PATH,
    D7_C2_RECEIPT_REPOSITORY_PATH,
    MAX_D7_C1_SEED_FREE_SOURCE_SET_BYTES,
    MAX_D7_C1_SOURCE_FILE_COUNT,
    MAX_D7_C1_SOURCE_MEMBER_BYTES,
    MAX_D7_C1_SOURCE_SET_TOTAL_BYTES,
    D7C1SeedFreeSourceSet,
)
from .persistence import PersistedQualificationIdentity, _atomic_write_no_overwrite

D7_C2_SOURCE_CLOSURE_RECEIPT_SCHEMA_VERSION = (
    "spirallens.d7-c2-source-closure-receipt.v0.1"
)
MAX_D7_C2_SOURCE_CLOSURE_RECEIPT_BYTES = 1024 * 1024
MAX_D7_SOURCE_CLOSURE_GIT_METADATA_BYTES = 16 * 1024 * 1024
MAX_D7_SOURCE_CLOSURE_STATUS_BYTES = 1024 * 1024

_RECEIPT_FACTORY_TOKEN = object()
_COMMIT = re.compile(r"^[0-9a-f]{40}$")
_AUTHORITY = {
    "confirmation_family_admitted": False,
    "confirmation_values_accessed": False,
    "d7_execution_authorized": False,
    "d7_result_produced": False,
    "d8_execution_authorized": False,
    "integer_output_authorized": False,
    "localized_core_loop_join_established": False,
    "model_access_authorized": False,
    "p0_winner_selected": False,
    "pythia_access_authorized": False,
    "representation_instrument_advanced": False,
    "scientific_claim_eligible": False,
    "semantic_authority": False,
    "subject_access_authorized": False,
    "synthetic_qualified": False,
    "topology_claim_authorized": False,
}

_C1_SOURCE_ENUMERATION_RULE = {
    "python_root": "src/spirallens",
    "python_glob": "**/*.py",
    "additional_paths": ["pyproject.toml"],
    "excluded_paths": [],
    "enumeration_applied_to": "working-tree-candidate",
    "future_c2_git_tree_reenumeration_required": True,
}


def _c2_chronology_document() -> dict[str, object]:
    return {
        "artifact_knowledge": {
            "c1_commit_contains_receipt": False,
            "c2_commit_identity_embedded": False,
            "receipt_commit_attestation_embedded": False,
            "official_seed_inventory_embedded": False,
            "confirmation_values_embedded": False,
            "launch_or_execution_record_embedded": False,
        },
        "ordering_requirements": {
            "c2_commit_must_be_unique_receipt_only_child_of_c1": True,
            "official_seed_supplier_must_follow_committed_c2": True,
            "launch_must_follow_seed_free_design_freeze": True,
        },
    }


def _commit(value: object, *, label: str) -> str:
    if not isinstance(value, str) or _COMMIT.fullmatch(value) is None:
        raise QualificationContractError(f"{label} must be a full Git commit")
    return value


def _exact_keys(
    value: Mapping[str, object],
    expected: set[str],
    *,
    label: str,
) -> None:
    if set(value) != expected:
        raise QualificationContractError(f"{label} fields differ")


def _require_exact_json_value(
    value: object,
    expected: object,
    *,
    label: str,
) -> None:
    """Require recursive JSON value and type identity, including bool vs int."""

    if isinstance(expected, Mapping):
        if not isinstance(value, Mapping) or set(value) != set(expected):
            raise QualificationContractError(f"{label} fields differ")
        for key, expected_item in expected.items():
            _require_exact_json_value(
                value[key],
                expected_item,
                label=f"{label}.{key}",
            )
        return
    if isinstance(expected, list):
        if not isinstance(value, list) or len(value) != len(expected):
            raise QualificationContractError(f"{label} list differs")
        for index, (item, expected_item) in enumerate(
            zip(value, expected, strict=True)
        ):
            _require_exact_json_value(
                item,
                expected_item,
                label=f"{label}[{index}]",
            )
        return
    if type(value) is not type(expected) or value != expected:
        raise QualificationContractError(f"{label} differs")


def _canonical_repository_path(value: object, *, label: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value.startswith("/")
        or "\\" in value
        or any(ord(character) < 32 or ord(character) == 127 for character in value)
    ):
        raise QualificationContractError(
            f"{label} must be a canonical relative POSIX path"
        )
    path = PurePosixPath(value)
    if (
        path.as_posix() != value
        or not path.parts
        or any(part in {"", ".", ".."} for part in path.parts)
    ):
        raise QualificationContractError(
            f"{label} must be a canonical relative POSIX path"
        )
    return value


def _repository_root(value: str | Path) -> Path:
    requested = Path(os.path.abspath(value))
    if not requested.is_dir() or requested.is_symlink():
        raise QualificationContractError(
            "repository_root must be one real existing directory"
        )
    completed = subprocess.run(
        ["git", "-C", str(requested), "rev-parse", "--show-toplevel"],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise QualificationContractError("repository_root is not a Git worktree")
    observed = Path(os.path.abspath(completed.stdout.strip()))
    if observed != requested:
        raise QualificationContractError(
            "repository_root must equal the exact Git worktree root"
        )
    return requested


def _git(
    root: Path,
    args: list[str],
    *,
    check: bool = True,
) -> subprocess.CompletedProcess[bytes]:
    completed = subprocess.run(
        ["git", "-C", str(root), *args],
        check=False,
        capture_output=True,
    )
    if check and completed.returncode != 0:
        detail = completed.stderr.decode("utf-8", errors="replace").strip()
        raise QualificationContractError(
            f"Git verification failed: {' '.join(args)}: {detail}"
        )
    return completed


def _git_text(root: Path, args: list[str]) -> str:
    return _git(root, args).stdout.decode("utf-8").strip()


def _git_stdout_bounded(
    root: Path,
    args: list[str],
    *,
    maximum_bytes: int,
    label: str,
) -> bytes:
    process = subprocess.Popen(
        ["git", "-C", str(root), *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    if process.stdout is None:
        process.kill()
        process.wait()
        raise QualificationContractError(f"cannot read {label}")
    try:
        source = process.stdout.read(maximum_bytes + 1)
        if len(source) > maximum_bytes:
            process.kill()
            process.wait()
            raise QualificationContractError(f"{label} exceeds its byte cap")
        returncode = process.wait()
        if returncode != 0:
            raise QualificationContractError(f"{label} Git query failed")
        return source
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()


def _git_text_bounded(
    root: Path,
    args: list[str],
    *,
    maximum_bytes: int,
    label: str,
) -> str:
    try:
        return _git_stdout_bounded(
            root,
            args,
            maximum_bytes=maximum_bytes,
            label=label,
        ).decode("utf-8").strip()
    except UnicodeDecodeError as error:
        raise QualificationContractError(f"{label} is not UTF-8") from error


def _head(root: Path) -> str:
    return _commit(
        _git_text(root, ["rev-parse", "--verify", "HEAD^{commit}"]),
        label="current HEAD",
    )


def _status(root: Path) -> bytes:
    return _git_stdout_bounded(
        root,
        ["status", "--porcelain=v1", "-z", "--untracked-files=all"],
        maximum_bytes=MAX_D7_SOURCE_CLOSURE_STATUS_BYTES,
        label="Git worktree status",
    )


def _read_bounded_regular(
    path: Path,
    *,
    maximum_bytes: int,
    label: str,
) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise QualificationContractError(f"{label} must be one regular file")
    with path.open("rb") as handle:
        source = handle.read(maximum_bytes + 1)
    if not source or len(source) > maximum_bytes:
        raise QualificationContractError(
            f"{label} is empty or exceeds its byte cap"
        )
    return source


def _tree_entry(
    root: Path,
    commit: str,
    repository_path: str,
) -> tuple[str, str, str, int]:
    if (
        not repository_path
        or any(character in repository_path for character in "\0\r\n")
    ):
        raise QualificationContractError("Git tree path is unsafe")
    raw = _git_stdout_bounded(
        root,
        [
            "ls-tree",
            "-l",
            "-z",
            commit,
            "--",
            repository_path,
        ],
        maximum_bytes=64 * 1024,
        label="required Git tree entry",
    )
    records = tuple(record for record in raw.split(b"\0") if record)
    if len(records) != 1:
        raise QualificationContractError(
            f"required Git tree entry is absent or ambiguous: "
            f"{commit}:{repository_path}"
        )
    try:
        metadata, path_bytes = records[0].split(b"\t", 1)
        mode, object_type, object_id, size_text = (
            metadata.decode("ascii").split()
        )
        observed_path = path_bytes.decode("utf-8")
        size = int(size_text)
    except (UnicodeDecodeError, ValueError) as error:
        raise QualificationContractError(
            "required Git tree entry is malformed"
        ) from error
    if observed_path != repository_path or size < 0:
        raise QualificationContractError(
            "required Git tree entry path or size differs"
        )
    return mode, object_type, object_id, size


def _blob(
    root: Path,
    commit: str,
    repository_path: str,
    *,
    maximum_bytes: int,
    label: str,
) -> bytes:
    _mode, object_type, object_id, tree_size = _tree_entry(
        root,
        commit,
        repository_path,
    )
    if object_type != "blob" or tree_size <= 0 or tree_size > maximum_bytes:
        raise QualificationContractError(
            f"{label} is not a nonempty blob within its byte cap"
        )
    size_text = _git_text(root, ["cat-file", "-s", object_id])
    try:
        object_size = int(size_text)
    except ValueError as error:
        raise QualificationContractError(
            f"{label} Git object size is malformed"
        ) from error
    if object_size != tree_size or object_size > maximum_bytes:
        raise QualificationContractError(
            f"{label} Git object size differs or exceeds its cap"
        )
    completed = _git(root, ["cat-file", "blob", object_id])
    if len(completed.stdout) != object_size:
        raise QualificationContractError(f"{label} Git blob size differs")
    return completed.stdout


def _blob_exists(root: Path, commit: str, repository_path: str) -> bool:
    return (
        _git(
            root,
            ["cat-file", "-e", f"{commit}:{repository_path}"],
            check=False,
        ).returncode
        == 0
    )


def _tree_source_entries(
    root: Path,
    commit: str,
) -> dict[str, tuple[str, str, str, int]]:
    raw = _git_stdout_bounded(
        root,
        [
            "ls-tree",
            "-r",
            "-l",
            "-z",
            "--full-tree",
            commit,
            "--",
            "src/spirallens",
            "pyproject.toml",
        ],
        maximum_bytes=MAX_D7_SOURCE_CLOSURE_GIT_METADATA_BYTES,
        label="C1 Git source-tree metadata",
    )
    result: dict[str, tuple[str, str, str, int]] = {}
    for record in raw.split(b"\0"):
        if not record:
            continue
        try:
            metadata, path_bytes = record.split(b"\t", 1)
            mode, object_type, object_id, size_text = (
                metadata.decode("ascii").split()
            )
            size = int(size_text)
            repository_path = path_bytes.decode("utf-8")
        except (UnicodeDecodeError, ValueError) as error:
            raise QualificationContractError(
                "C1 Git tree contains an unsupported source entry"
            ) from error
        if repository_path == "pyproject.toml" or (
            repository_path.startswith("src/spirallens/")
            and repository_path.endswith(".py")
        ):
            if repository_path in result:
                raise QualificationContractError(
                    "C1 Git tree source enumeration is not unique"
                )
            if len(result) >= MAX_D7_C1_SOURCE_FILE_COUNT:
                raise QualificationContractError(
                    "C1 Git tree source enumeration exceeds the file-count cap"
                )
            if size < 0:
                raise QualificationContractError(
                    "C1 Git tree source size is invalid"
                )
            result[repository_path] = (
                mode,
                object_type,
                object_id,
                size,
            )
    return result


def _batch_blobs(
    root: Path,
    repository_paths: tuple[str, ...],
    tree_entries: Mapping[str, tuple[str, str, str, int]],
) -> dict[str, bytes]:
    if not repository_paths:
        return {}
    if len(repository_paths) > MAX_D7_C1_SOURCE_FILE_COUNT:
        raise QualificationContractError(
            "C1 source batch exceeds the file-count cap"
        )
    expected_total = sum(
        tree_entries[repository_path][3]
        for repository_path in repository_paths
    )
    if expected_total <= 0 or expected_total > MAX_D7_C1_SOURCE_SET_TOTAL_BYTES:
        raise QualificationContractError(
            "declared C1 source total is empty or exceeds the hard cap"
        )
    process = subprocess.Popen(
        ["git", "-C", str(root), "cat-file", "--batch"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    if process.stdin is None or process.stdout is None:
        process.kill()
        process.wait()
        raise QualificationContractError("cannot open the C1 source batch")
    try:
        result: dict[str, bytes] = {}
        observed_total = 0
        for repository_path in repository_paths:
            object_id = tree_entries[repository_path][2]
            process.stdin.write(f"{object_id}\n".encode("ascii"))
            process.stdin.flush()
            header_bytes = process.stdout.readline(1024)
            if (
                not header_bytes
                or len(header_bytes) >= 1024
                or not header_bytes.endswith(b"\n")
            ):
                raise QualificationContractError(
                    "C1 source batch response lacks one bounded header"
                )
            try:
                header = header_bytes.decode("ascii").split()
            except UnicodeDecodeError as error:
                raise QualificationContractError(
                    "C1 source batch header is not ASCII"
                ) from error
            expected_mode, expected_type, expected_id, expected_size = (
                tree_entries[repository_path]
            )
            if (
                expected_mode not in {"100644", "100755"}
                or expected_type != "blob"
                or len(header) != 3
                or header[0] != expected_id
                or header[1] != "blob"
            ):
                raise QualificationContractError(
                    f"C1 source batch identity differs: {repository_path}"
                )
            try:
                byte_count = int(header[2])
            except ValueError as error:
                raise QualificationContractError(
                    "C1 source batch response has an invalid byte count"
                ) from error
            if byte_count != expected_size:
                raise QualificationContractError(
                    f"C1 source batch size differs: {repository_path}"
                )
            if byte_count <= 0 or byte_count > MAX_D7_C1_SOURCE_MEMBER_BYTES:
                raise QualificationContractError(
                    f"C1 source batch member exceeds its cap: {repository_path}"
                )
            chunks: list[bytes] = []
            remaining = byte_count
            while remaining:
                chunk = process.stdout.read(min(remaining, 1024 * 1024))
                if not chunk:
                    raise QualificationContractError(
                        "C1 source batch response ended inside a blob"
                    )
                chunks.append(chunk)
                remaining -= len(chunk)
            if process.stdout.read(1) != b"\n":
                raise QualificationContractError(
                    "C1 source batch response lacks a blob terminator"
                )
            source = b"".join(chunks)
            result[repository_path] = source
            observed_total += len(source)
            if observed_total > MAX_D7_C1_SOURCE_SET_TOTAL_BYTES:
                raise QualificationContractError(
                    "C1 source batch crossed the hard total cap"
                )
        process.stdin.close()
        trailing = process.stdout.read(1)
        returncode = process.wait()
        if returncode != 0 or trailing:
            raise QualificationContractError(
                "C1 source batch failed or contains trailing bytes"
            )
        return result
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()


def _source_manifest(bundle: D7C1SeedFreeSourceSet) -> Mapping[str, object]:
    document = bundle.to_dict()
    components = document["components"]
    if not isinstance(components, Mapping):
        raise QualificationContractError("C1 bundle components are malformed")
    component = components["source_set_manifest"]
    if not isinstance(component, Mapping):
        raise QualificationContractError("C1 source-set component is malformed")
    body = component["body"]
    if not isinstance(body, Mapping):
        raise QualificationContractError("C1 source-set body is malformed")
    return body


def _verify_c1_source_tree(
    root: Path,
    c1_commit: str,
    source_manifest: Mapping[str, object],
) -> tuple[int, int]:
    entries = source_manifest.get("entries")
    if not isinstance(entries, list):
        raise QualificationContractError("C1 source entries must be a list")
    if len(entries) > MAX_D7_C1_SOURCE_FILE_COUNT:
        raise QualificationContractError(
            "C1 source entries exceed the file-count cap"
        )
    declared: dict[str, Mapping[str, object]] = {}
    declared_total = 0
    for item in entries:
        if not isinstance(item, Mapping):
            raise QualificationContractError("C1 source entry is malformed")
        if set(item) != {
            "repository_path",
            "role",
            "source_sha256",
            "byte_count",
            "git_mode",
        }:
            raise QualificationContractError("C1 source entry fields differ")
        repository_path = _canonical_repository_path(
            item.get("repository_path"),
            label="C1 declared source path",
        )
        byte_count = item.get("byte_count")
        if (
            repository_path in declared
            or type(byte_count) is not int
            or int(byte_count) <= 0
            or int(byte_count) > MAX_D7_C1_SOURCE_MEMBER_BYTES
        ):
            raise QualificationContractError(
                "C1 source paths and sizes must be unique bounded values"
            )
        declared[repository_path] = item
        declared_total += int(byte_count)
    if tuple(declared) != tuple(sorted(declared)):
        raise QualificationContractError("C1 source paths are not canonical")
    if (
        declared_total > MAX_D7_C1_SOURCE_SET_TOTAL_BYTES
        or source_manifest.get("total_bytes") != declared_total
    ):
        raise QualificationContractError(
            "C1 source manifest total exceeds or differs from the hard cap"
        )
    observed = _tree_source_entries(root, c1_commit)
    if set(observed) != set(declared):
        raise QualificationContractError(
            "C1 source manifest differs from Git-tree re-enumeration"
        )
    observed_total = sum(item[3] for item in observed.values())
    if (
        observed_total != declared_total
        or observed_total > MAX_D7_C1_SOURCE_SET_TOTAL_BYTES
    ):
        raise QualificationContractError(
            "C1 Git source total differs or exceeds the hard cap"
        )
    for repository_path, item in declared.items():
        mode, object_type, _object_id, tree_size = observed[repository_path]
        if (
            object_type != "blob"
            or mode not in {"100644", "100755"}
            or item.get("git_mode") != mode
            or item.get("byte_count") != tree_size
        ):
            raise QualificationContractError(
                f"C1 source tree metadata differs: {repository_path}"
            )
    blobs = _batch_blobs(root, tuple(declared), observed)
    total_bytes = 0
    for repository_path, item in declared.items():
        source = blobs[repository_path]
        digest = sha256_bytes(source)
        if (
            item.get("source_sha256") != digest
            or item.get("byte_count") != len(source)
        ):
            raise QualificationContractError(
                f"C1 source blob identity differs: {repository_path}"
            )
        total_bytes += len(source)
    if (
        source_manifest.get("file_count") != len(declared)
        or source_manifest.get("total_bytes") != total_bytes
    ):
        raise QualificationContractError(
            "C1 source-set aggregate counts differ"
        )
    return len(declared), total_bytes


def _load_c1_blob(
    root: Path,
    c1_commit: str,
) -> tuple[D7C1SeedFreeSourceSet, bytes]:
    mode, object_type, _object_id, _size = _tree_entry(
        root,
        c1_commit,
        D7_C1_BUNDLE_REPOSITORY_PATH,
    )
    if mode != "100644" or object_type != "blob":
        raise QualificationContractError(
            "committed C1 bundle must be one non-executable regular blob"
        )
    source = _blob(
        root,
        c1_commit,
        D7_C1_BUNDLE_REPOSITORY_PATH,
        maximum_bytes=MAX_D7_C1_SEED_FREE_SOURCE_SET_BYTES,
        label="committed C1 bundle",
    )
    bundle = D7C1SeedFreeSourceSet.from_canonical_bytes(
        source,
        expected_sha256=sha256_bytes(source),
    )
    return bundle, source


@dataclass(frozen=True, slots=True, init=False)
class D7C2SourceClosureReceipt:
    """Canonical receipt that binds C1 only, never its own future commit."""

    _canonical_bytes: bytes

    schema_version: ClassVar[str] = (
        D7_C2_SOURCE_CLOSURE_RECEIPT_SCHEMA_VERSION
    )
    receipt_id: ClassVar[str] = "d7-spectral-moment-c2-source-closure-v0-1"

    def __init__(
        self,
        *,
        _factory_token: object = None,
        canonical_bytes: bytes,
    ) -> None:
        if _factory_token is not _RECEIPT_FACTORY_TOKEN:
            raise QualificationContractError(
                "D7C2SourceClosureReceipt must be produced by its issuer or loader"
            )
        if (
            not isinstance(canonical_bytes, bytes)
            or not canonical_bytes
            or len(canonical_bytes) > MAX_D7_C2_SOURCE_CLOSURE_RECEIPT_BYTES
        ):
            raise QualificationContractError(
                "C2 source-closure receipt is empty or exceeds its byte cap"
            )
        try:
            document = parse_canonical_json(
                canonical_bytes,
                label="D7 C2 source-closure receipt",
            )
        except CanonicalJsonError as error:
            raise QualificationContractError(str(error)) from error
        if not isinstance(document, Mapping):
            raise QualificationContractError(
                "D7 C2 source-closure receipt must be an object"
            )
        self._validate_document(document)
        object.__setattr__(self, "_canonical_bytes", canonical_bytes)

    @classmethod
    def _validate_document(cls, document: Mapping[str, object]) -> None:
        expected = {
            "schema_version",
            "receipt_id",
            "status",
            "claim_ceiling",
            "c1_commit",
            "c1_bundle",
            "source_inventory",
            "verification",
            "limitations",
            "chronology",
            "d7_state",
            "d8_state",
            "authority",
        }
        if set(document) != expected:
            raise QualificationContractError(
                "D7 C2 source-closure receipt root fields differ"
            )
        _commit(document["c1_commit"], label="receipt c1_commit")
        if (
            document["schema_version"] != cls.schema_version
            or document["receipt_id"] != cls.receipt_id
            or document["status"] != "c1-source-closure-verified"
            or document["claim_ceiling"] != "level_0"
            or document["d7_state"] != "not_run"
            or document["d8_state"] != "not_run"
        ):
            raise QualificationContractError(
                "D7 C2 source-closure receipt state differs"
            )
        _require_exact_json_value(
            document["authority"],
            dict(sorted(_AUTHORITY.items())),
            label="D7 C2 authority",
        )
        c1_bundle = document["c1_bundle"]
        source_inventory = document["source_inventory"]
        verification = document["verification"]
        limitations = document["limitations"]
        chronology = document["chronology"]
        if not all(
            isinstance(value, Mapping)
            for value in (
                c1_bundle,
                source_inventory,
                verification,
                limitations,
                chronology,
            )
        ):
            raise QualificationContractError(
                "D7 C2 receipt nested records must be objects"
            )
        _exact_keys(
            c1_bundle,
            {
                "repository_path",
                "source_sha256",
                "canonical_sha256",
                "byte_count",
                "component_set_sha256",
            },
            label="D7 C2 C1 bundle",
        )
        _exact_keys(
            source_inventory,
            {
                "source_set_manifest_sha256",
                "file_count",
                "role_counts",
                "total_bytes",
                "enumeration_rule",
            },
            label="D7 C2 source inventory",
        )
        for name in (
            "source_sha256",
            "canonical_sha256",
            "component_set_sha256",
            "source_set_manifest_sha256",
        ):
            container = (
                source_inventory
                if name == "source_set_manifest_sha256"
                else c1_bundle
            )
            require_sha256(container.get(name), label=f"C2 {name}")
        if (
            c1_bundle.get("repository_path") != D7_C1_BUNDLE_REPOSITORY_PATH
            or c1_bundle.get("source_sha256")
            != c1_bundle.get("canonical_sha256")
            or type(c1_bundle.get("byte_count")) is not int
            or int(c1_bundle["byte_count"]) <= 0
            or int(c1_bundle["byte_count"])
            > MAX_D7_C1_SEED_FREE_SOURCE_SET_BYTES
        ):
            raise QualificationContractError("D7 C2 C1-bundle identity differs")
        file_count = source_inventory.get("file_count")
        total_bytes = source_inventory.get("total_bytes")
        role_counts = source_inventory.get("role_counts")
        enumeration_rule = source_inventory.get("enumeration_rule")
        if (
            type(file_count) is not int
            or int(file_count) < 2
            or int(file_count) > MAX_D7_C1_SOURCE_FILE_COUNT
            or type(total_bytes) is not int
            or int(total_bytes) <= 0
            or int(total_bytes) > MAX_D7_C1_SOURCE_SET_TOTAL_BYTES
            or not isinstance(role_counts, Mapping)
            or set(role_counts)
            != {"packaging_contract", "project_python_source"}
            or type(role_counts.get("packaging_contract")) is not int
            or type(role_counts.get("project_python_source")) is not int
            or role_counts.get("packaging_contract") != 1
            or role_counts.get("project_python_source")
            != int(file_count) - 1
        ):
            raise QualificationContractError(
                "D7 C2 source-inventory aggregates or enumeration differ"
            )
        _require_exact_json_value(
            enumeration_rule,
            _C1_SOURCE_ENUMERATION_RULE,
            label="D7 C2 source enumeration",
        )
        expected_verification = {
            "c1_head_derived_not_supplied": True,
            "c1_bundle_tracked_exact_blob": True,
            "git_tree_reenumerated": True,
            "declared_and_observed_source_paths_equal": True,
            "all_source_blob_digests_sizes_and_modes_verified": True,
            "receipt_absent_at_c1": True,
            "worktree_clean_before_issuance": True,
            "head_stable_during_issuance": True,
        }
        _require_exact_json_value(
            verification,
            expected_verification,
            label="D7 C2 verification",
        )
        expected_limitations = {
            "source_only": True,
            "historical_code_executed": False,
            "python_runtime_attested": False,
            "native_runtime_attested": False,
            "in_process_callable_identity_verified": False,
            "hostile_local_mutation_resistant": False,
            "current_source_compatibility_verified": False,
        }
        _require_exact_json_value(
            limitations,
            expected_limitations,
            label="D7 C2 limitations",
        )
        _require_exact_json_value(
            chronology,
            _c2_chronology_document(),
            label="D7 C2 chronology",
        )

    @classmethod
    def from_canonical_bytes(
        cls,
        source: bytes,
        *,
        expected_sha256: str,
    ) -> D7C2SourceClosureReceipt:
        expected = require_sha256(expected_sha256, label="expected_sha256")
        if sha256_bytes(source) != expected:
            raise QualificationContractError(
                "D7 C2 source-closure receipt SHA-256 differs"
            )
        return cls(
            _factory_token=_RECEIPT_FACTORY_TOKEN,
            canonical_bytes=source,
        )

    @property
    def canonical_bytes(self) -> bytes:
        return self._canonical_bytes

    @property
    def canonical_sha256(self) -> str:
        return sha256_bytes(self._canonical_bytes)

    def to_dict(self) -> dict[str, object]:
        document = parse_canonical_json(
            self._canonical_bytes,
            label="D7 C2 source-closure receipt",
        )
        if not isinstance(document, Mapping):
            raise TypeError("validated C2 document must remain a mapping")
        return dict(document)


@dataclass(frozen=True, slots=True)
class PublishedD7C2SourceClosureReceipt:
    """Filesystem receipt after issuance; the C2 commit is still future."""

    receipt: D7C2SourceClosureReceipt
    identity: PersistedQualificationIdentity
    committed_receipt_verified: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.receipt, D7C2SourceClosureReceipt):
            raise TypeError("receipt must be D7C2SourceClosureReceipt")
        if not isinstance(self.identity, PersistedQualificationIdentity):
            raise TypeError("identity must be PersistedQualificationIdentity")
        if (
            self.identity.source_sha256 != self.receipt.canonical_sha256
            or self.identity.canonical_sha256 != self.receipt.canonical_sha256
            or self.identity.byte_count != len(self.receipt.canonical_bytes)
        ):
            raise QualificationContractError(
                "published C2 identity differs from canonical receipt"
            )
        if self.committed_receipt_verified is not False:
            raise QualificationContractError(
                "filesystem C2 publication cannot attest its future commit"
            )


@dataclass(frozen=True, slots=True)
class LoadedCommittedD7SourceClosure:
    """Read-only derived proof of C1 and its receipt-only C2 child."""

    receipt: D7C2SourceClosureReceipt
    c1_commit: str
    c2_commit: str
    current_head: str
    committed_receipt_verified: bool = True
    historical_c1_source_closure_verified: bool = True
    current_source_compatibility_verified: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.receipt, D7C2SourceClosureReceipt):
            raise TypeError("receipt must be D7C2SourceClosureReceipt")
        for name in ("c1_commit", "c2_commit", "current_head"):
            _commit(getattr(self, name), label=name)
        if self.receipt.to_dict()["c1_commit"] != self.c1_commit:
            raise QualificationContractError(
                "loaded C1 commit differs from the canonical receipt"
            )
        if (
            self.committed_receipt_verified is not True
            or self.historical_c1_source_closure_verified is not True
            or self.current_source_compatibility_verified is not False
        ):
            raise QualificationContractError(
                "loaded source-closure verification state differs"
            )


def _receipt_document(
    *,
    c1_commit: str,
    bundle: D7C1SeedFreeSourceSet,
    bundle_source: bytes,
    source_manifest: Mapping[str, object],
    source_file_count: int,
    source_total_bytes: int,
) -> dict[str, object]:
    bundle_document = bundle.to_dict()
    components = bundle_document["components"]
    if not isinstance(components, Mapping):
        raise QualificationContractError("C1 components are malformed")
    source_component = components["source_set_manifest"]
    if not isinstance(source_component, Mapping):
        raise QualificationContractError("C1 source component is malformed")
    return {
        "schema_version": D7_C2_SOURCE_CLOSURE_RECEIPT_SCHEMA_VERSION,
        "receipt_id": D7C2SourceClosureReceipt.receipt_id,
        "status": "c1-source-closure-verified",
        "claim_ceiling": "level_0",
        "c1_commit": c1_commit,
        "c1_bundle": {
            "repository_path": D7_C1_BUNDLE_REPOSITORY_PATH,
            "source_sha256": sha256_bytes(bundle_source),
            "canonical_sha256": bundle.canonical_sha256,
            "byte_count": len(bundle_source),
            "component_set_sha256": bundle_document["component_set_sha256"],
        },
        "source_inventory": {
            "source_set_manifest_sha256": source_component["canonical_sha256"],
            "file_count": source_file_count,
            "role_counts": source_manifest["role_counts"],
            "total_bytes": source_total_bytes,
            "enumeration_rule": source_manifest["enumeration_rule"],
        },
        "verification": {
            "c1_head_derived_not_supplied": True,
            "c1_bundle_tracked_exact_blob": True,
            "git_tree_reenumerated": True,
            "declared_and_observed_source_paths_equal": True,
            "all_source_blob_digests_sizes_and_modes_verified": True,
            "receipt_absent_at_c1": True,
            "worktree_clean_before_issuance": True,
            "head_stable_during_issuance": True,
        },
        "limitations": {
            "source_only": True,
            "historical_code_executed": False,
            "python_runtime_attested": False,
            "native_runtime_attested": False,
            "in_process_callable_identity_verified": False,
            "hostile_local_mutation_resistant": False,
            "current_source_compatibility_verified": False,
        },
        "chronology": _c2_chronology_document(),
        "d7_state": "not_run",
        "d8_state": "not_run",
        "authority": dict(sorted(_AUTHORITY.items())),
    }


def issue_d7_c2_source_closure_receipt(
    *,
    repository_root: str | Path,
) -> PublishedD7C2SourceClosureReceipt:
    """Derive C1 from clean HEAD and publish only the fixed C2 receipt."""

    root = _repository_root(repository_root)
    c1_commit = _head(root)
    if _status(root):
        raise QualificationContractError(
            "C2 issuance requires a completely clean C1 worktree"
        )
    destination = root / D7_C2_RECEIPT_REPOSITORY_PATH
    if destination.exists() or destination.is_symlink():
        raise QualificationContractError(
            "C2 receipt destination already exists"
        )
    if _blob_exists(root, c1_commit, D7_C2_RECEIPT_REPOSITORY_PATH):
        raise QualificationContractError(
            "C2 receipt must be absent from the C1 Git tree"
        )
    bundle_path = root / D7_C1_BUNDLE_REPOSITORY_PATH
    if bundle_path.is_symlink() or not bundle_path.is_file():
        raise QualificationContractError(
            "C1 bundle must be one clean tracked regular file"
        )
    bundle, bundle_source = _load_c1_blob(root, c1_commit)
    if (
        _read_bounded_regular(
            bundle_path,
            maximum_bytes=MAX_D7_C1_SEED_FREE_SOURCE_SET_BYTES,
            label="working C1 bundle",
        )
        != bundle_source
    ):
        raise QualificationContractError(
            "working C1 bundle differs from the C1 Git blob"
        )
    source_manifest = _source_manifest(bundle)
    file_count, total_bytes = _verify_c1_source_tree(
        root,
        c1_commit,
        source_manifest,
    )
    if _head(root) != c1_commit or _status(root):
        raise QualificationContractError(
            "C1 HEAD or worktree changed during source verification"
        )
    receipt = D7C2SourceClosureReceipt(
        _factory_token=_RECEIPT_FACTORY_TOKEN,
        canonical_bytes=canonical_json_bytes(
            _receipt_document(
                c1_commit=c1_commit,
                bundle=bundle,
                bundle_source=bundle_source,
                source_manifest=source_manifest,
                source_file_count=file_count,
                source_total_bytes=total_bytes,
            )
        ),
    )
    identity = _atomic_write_no_overwrite(
        destination,
        receipt.canonical_bytes,
        maximum_bytes=MAX_D7_C2_SOURCE_CLOSURE_RECEIPT_BYTES,
        label="D7 C2 source-closure receipt",
    )
    expected_status = f"?? {D7_C2_RECEIPT_REPOSITORY_PATH}\0".encode()
    if _head(root) != c1_commit or _status(root) != expected_status:
        raise QualificationContractError(
            "post-issuance worktree differs from the sole untracked C2 receipt"
        )
    return PublishedD7C2SourceClosureReceipt(
        receipt=receipt,
        identity=identity,
    )


def _receipt_introduction_commit(
    root: Path,
    *,
    c1_commit: str,
    current_head: str,
) -> str:
    commits = tuple(
        line
        for line in _git_text_bounded(
            root,
            [
                "rev-list",
                "--full-history",
                current_head,
                "--",
                D7_C2_RECEIPT_REPOSITORY_PATH,
            ],
            maximum_bytes=MAX_D7_SOURCE_CLOSURE_GIT_METADATA_BYTES,
            label="C2 receipt path history",
        ).splitlines()
        if line
    )
    candidates: list[str] = []
    for value in commits:
        commit = _commit(value, label="receipt history commit")
        parent_line = _git_text_bounded(
            root,
            ["rev-list", "--parents", "-n", "1", commit],
            maximum_bytes=1024,
            label="C2 receipt introduction parent",
        ).split()
        if len(parent_line) != 2:
            continue
        parent = _commit(parent_line[1], label="receipt introduction parent")
        if (
            parent == c1_commit
            and _blob_exists(root, commit, D7_C2_RECEIPT_REPOSITORY_PATH)
            and not _blob_exists(root, parent, D7_C2_RECEIPT_REPOSITORY_PATH)
        ):
            candidates.append(commit)
    if len(candidates) != 1:
        raise QualificationContractError(
            "receipt history lacks one unique single-parent C1-to-C2 introduction"
        )
    return candidates[0]


def _require_tree_entry_unchanged_on_ancestry(
    root: Path,
    *,
    ancestor: str,
    current_head: str,
    repository_path: str,
    expected_entry: tuple[str, str, str, int],
    label: str,
) -> None:
    descendants = tuple(
        line
        for line in _git_text_bounded(
            root,
            [
                "rev-list",
                "--ancestry-path",
                f"{ancestor}..{current_head}",
            ],
            maximum_bytes=MAX_D7_SOURCE_CLOSURE_GIT_METADATA_BYTES,
            label=f"{label} ancestry history",
        ).splitlines()
        if line
    )
    for value in descendants:
        commit = _commit(value, label=f"{label} descendant commit")
        try:
            observed_entry = _tree_entry(root, commit, repository_path)
        except QualificationContractError as error:
            raise QualificationContractError(
                f"{label} was deleted, replaced, or changed after {ancestor}"
            ) from error
        if observed_entry != expected_entry:
            raise QualificationContractError(
                f"{label} was deleted, replaced, or changed after {ancestor}"
            )


def _require_c2_dominated_history(
    root: Path,
    *,
    c1_commit: str,
    c2_commit: str,
    current_head: str,
) -> None:
    """Reject post-C1 sibling history that reaches HEAD beside C2."""

    records = tuple(
        line.split()
        for line in _git_text_bounded(
            root,
            [
                "rev-list",
                "--ancestry-path",
                "--parents",
                f"{c2_commit}..{current_head}",
            ],
            maximum_bytes=MAX_D7_SOURCE_CLOSURE_GIT_METADATA_BYTES,
            label="C2-dominated ancestry history",
        ).splitlines()
        if line
    )
    for record in records:
        commit = _commit(record[0], label="C2-dominated descendant")
        if len(record) < 2:
            raise QualificationContractError(
                f"C2-dominated descendant lacks a parent: {commit}"
            )
        for parent_value in record[1:]:
            parent = _commit(
                parent_value,
                label="C2-dominated descendant parent",
            )
            if parent == c1_commit:
                continue
            if (
                _git(
                    root,
                    ["merge-base", "--is-ancestor", c2_commit, parent],
                    check=False,
                ).returncode
                != 0
            ):
                raise QualificationContractError(
                    "current history contains a post-C1 branch not dominated "
                    "by the unique C2 receipt commit"
                )


def load_committed_d7_source_closure(
    *,
    repository_root: str | Path,
    expected_source_sha256: str,
    expected_canonical_sha256: str,
) -> LoadedCommittedD7SourceClosure:
    """Verify committed C1/C2 history without executing historical Python."""

    expected_source = require_sha256(
        expected_source_sha256,
        label="expected_source_sha256",
    )
    expected_canonical = require_sha256(
        expected_canonical_sha256,
        label="expected_canonical_sha256",
    )
    root = _repository_root(repository_root)
    current_head = _head(root)
    if _status(root):
        raise QualificationContractError(
            "committed C2 loading requires a completely clean worktree"
        )
    receipt_path = root / D7_C2_RECEIPT_REPOSITORY_PATH
    if receipt_path.is_symlink() or not receipt_path.is_file():
        raise QualificationContractError(
            "committed C2 receipt must be one regular file"
        )
    source = _read_bounded_regular(
        receipt_path,
        maximum_bytes=MAX_D7_C2_SOURCE_CLOSURE_RECEIPT_BYTES,
        label="committed C2 receipt",
    )
    receipt = D7C2SourceClosureReceipt.from_canonical_bytes(
        source,
        expected_sha256=expected_source,
    )
    if receipt.canonical_sha256 != expected_canonical:
        raise QualificationContractError(
            "committed C2 canonical SHA-256 differs"
        )
    document = receipt.to_dict()
    c1_commit = _commit(document["c1_commit"], label="C1 commit")
    resolved_c1 = _git_text(
        root,
        ["rev-parse", "--verify", f"{c1_commit}^{{commit}}"],
    )
    if resolved_c1 != c1_commit:
        raise QualificationContractError(
            "receipt C1 commit does not resolve exactly"
        )
    if (
        _git(
            root,
            ["merge-base", "--is-ancestor", c1_commit, current_head],
            check=False,
        ).returncode
        != 0
    ):
        raise QualificationContractError(
            "receipt C1 commit is not an ancestor of current HEAD"
        )
    if _blob_exists(root, c1_commit, D7_C2_RECEIPT_REPOSITORY_PATH):
        raise QualificationContractError("C2 receipt already existed at C1")
    c2_commit = _receipt_introduction_commit(
        root,
        c1_commit=c1_commit,
        current_head=current_head,
    )
    delta = _git_stdout_bounded(
        root,
        [
            "diff-tree",
            "--no-commit-id",
            "--name-status",
            "-r",
            c1_commit,
            c2_commit,
        ],
        maximum_bytes=64 * 1024,
        label="C1-to-C2 tree delta",
    )
    expected_delta = f"A\t{D7_C2_RECEIPT_REPOSITORY_PATH}\n".encode()
    if delta != expected_delta:
        raise QualificationContractError(
            "C2 introduction changed anything besides the one added receipt"
        )
    if (
        _git(
            root,
            ["merge-base", "--is-ancestor", c2_commit, current_head],
            check=False,
        ).returncode
        != 0
    ):
        raise QualificationContractError(
            "derived C2 commit is not an ancestor of current HEAD"
        )
    _require_c2_dominated_history(
        root,
        c1_commit=c1_commit,
        c2_commit=c2_commit,
        current_head=current_head,
    )
    receipt_entry = _tree_entry(
        root,
        c2_commit,
        D7_C2_RECEIPT_REPOSITORY_PATH,
    )
    if (
        receipt_entry[0] != "100644"
        or receipt_entry[1] != "blob"
        or receipt_entry[3] != len(source)
        or _blob(
            root,
            c2_commit,
            D7_C2_RECEIPT_REPOSITORY_PATH,
            maximum_bytes=MAX_D7_C2_SOURCE_CLOSURE_RECEIPT_BYTES,
            label="C2 receipt introduction blob",
        )
        != source
        or _tree_entry(
            root,
            current_head,
            D7_C2_RECEIPT_REPOSITORY_PATH,
        )
        != receipt_entry
    ):
        raise QualificationContractError(
            "C2 receipt blob changed after its introduction"
        )
    _require_tree_entry_unchanged_on_ancestry(
        root,
        ancestor=c2_commit,
        current_head=current_head,
        repository_path=D7_C2_RECEIPT_REPOSITORY_PATH,
        expected_entry=receipt_entry,
        label="C2 receipt",
    )
    bundle, bundle_source = _load_c1_blob(root, c1_commit)
    bundle_entry = _tree_entry(
        root,
        c1_commit,
        D7_C1_BUNDLE_REPOSITORY_PATH,
    )
    c1_bundle_record = document["c1_bundle"]
    if not isinstance(c1_bundle_record, Mapping):
        raise QualificationContractError("C2 C1-bundle record is malformed")
    if (
        c1_bundle_record.get("source_sha256") != sha256_bytes(bundle_source)
        or c1_bundle_record.get("canonical_sha256") != bundle.canonical_sha256
        or c1_bundle_record.get("byte_count") != len(bundle_source)
        or _tree_entry(
            root,
            current_head,
            D7_C1_BUNDLE_REPOSITORY_PATH,
        )
        != bundle_entry
    ):
        raise QualificationContractError(
            "committed C1 bundle differs from the C2 receipt or current history"
        )
    _require_tree_entry_unchanged_on_ancestry(
        root,
        ancestor=c1_commit,
        current_head=current_head,
        repository_path=D7_C1_BUNDLE_REPOSITORY_PATH,
        expected_entry=bundle_entry,
        label="C1 bundle",
    )
    bundle_document = bundle.to_dict()
    if c1_bundle_record.get("component_set_sha256") != (
        bundle_document["component_set_sha256"]
    ):
        raise QualificationContractError(
            "C2 component-set identity differs from the committed C1 bundle"
        )
    source_manifest = _source_manifest(bundle)
    file_count, total_bytes = _verify_c1_source_tree(
        root,
        c1_commit,
        source_manifest,
    )
    inventory_record = document["source_inventory"]
    components = bundle_document["components"]
    if not isinstance(components, Mapping):
        raise QualificationContractError("committed C1 components are malformed")
    source_component = components["source_set_manifest"]
    if not isinstance(source_component, Mapping):
        raise QualificationContractError(
            "committed C1 source-set component is malformed"
        )
    if not isinstance(inventory_record, Mapping) or any(
        (
            inventory_record.get("source_set_manifest_sha256")
            != source_component["canonical_sha256"],
            inventory_record.get("file_count") != file_count,
            inventory_record.get("role_counts")
            != source_manifest["role_counts"],
            inventory_record.get("total_bytes") != total_bytes,
            inventory_record.get("enumeration_rule")
            != source_manifest["enumeration_rule"],
        )
    ):
        raise QualificationContractError(
            "committed C1 source aggregates differ from the C2 receipt"
        )
    if _head(root) != current_head or _status(root):
        raise QualificationContractError(
            "HEAD or worktree changed during committed C2 verification"
        )
    return LoadedCommittedD7SourceClosure(
        receipt=receipt,
        c1_commit=c1_commit,
        c2_commit=c2_commit,
        current_head=current_head,
    )


__all__ = [
    "D7_C2_SOURCE_CLOSURE_RECEIPT_SCHEMA_VERSION",
    "MAX_D7_C2_SOURCE_CLOSURE_RECEIPT_BYTES",
    "D7C2SourceClosureReceipt",
    "LoadedCommittedD7SourceClosure",
    "PublishedD7C2SourceClosureReceipt",
    "issue_d7_c2_source_closure_receipt",
    "load_committed_d7_source_closure",
]
