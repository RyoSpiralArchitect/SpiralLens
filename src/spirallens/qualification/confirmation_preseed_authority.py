"""Committed, seed-free positive prerequisites for the future D7 seed claim.

This deep-internal module owns three distinct repository artifacts:

1. an exact execution-source/runtime receipt;
2. seed-free readiness; and
3. a scoped reviewed successor-family admission.

They are intentionally not one bundle.  After all execution-source changes are
committed, each artifact must be the sole addition in one direct-child commit.
The artifacts do not embed their own future introduction commits; strict
loaders derive those commits from Git history.  Existing caller-constructible
``confirmation_attempt_authority`` records remain non-authorizing and are not
promoted here.

The retained v0.1 historical path reconstructs the source tree and runtime lock
from the source commit plus fixed v0.1 pins; it does not invoke whatever
official builders happen to be current later.  The separate current verifier
reobserves the live source/runtime and exact current builder identities.  Its
returned object is point-in-time evidence only, not freshness or authority for
a future seed-supply transition.

The positive claim is deliberately narrow and honest-local.  It does not prove
a signed trust root, an external timestamp, hostile-local mutation resistance,
installed package bytes, loaded native-library bytes, mutable module state,
unrecorded environment state, model/data state, execution, or a scientific
result.  It accepts no seed, supplier, callback, target, full design, freeze,
launch intent, or result.
"""

from __future__ import annotations

import copy
import os
import platform
import re
import stat
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from types import FunctionType
from typing import ClassVar, NoReturn

from spirallens.core.canonical import (
    CanonicalJsonError,
    canonical_json_bytes,
    canonical_json_sha256,
    parse_canonical_json,
    sha256_bytes,
)
from spirallens.synthetic import (
    spectral_moment_confirmation as spectral_generator,
)

from . import confirmation_attempt_authority as authority
from . import confirmation_c1 as c1
from . import confirmation_fused_start as fused_start
from . import confirmation_official_execution as official
from . import confirmation_replay_contracts as replay_contracts
from . import confirmation_runtime_observation as runtime_observation
from .common import QualificationContractError
from .persistence import PersistedQualificationIdentity, _atomic_write_no_overwrite

__all__: tuple[str, ...] = ()

D7_ITEM21_SOURCE_RUNTIME_RECEIPT_SCHEMA_VERSION = (
    "spirallens.d7-exact-current-execution-source-runtime-receipt.v0.1"
)
D7_ITEM21_SEED_FREE_READINESS_SCHEMA_VERSION = "spirallens.d7-seed-free-readiness.v0.1"
D7_ITEM21_REVIEWED_FAMILY_ADMISSION_SCHEMA_VERSION = (
    "spirallens.d7-reviewed-successor-family-admission.v0.1"
)
D7_ITEM21_SUCCESSOR_ADMISSION_SPEC_SCHEMA_VERSION = (
    "spirallens.d7-successor-family-admission-spec.v0.1"
)
D7_ITEM21_FINAL_CODE_REVIEW_SCHEMA_VERSION = (
    "spirallens.d7-final-code-review-attestation.v0.1"
)

D7_ITEM21_DIRECTORY = "experiments/qualification/d7_spectral_moment_confirmation_v0_1"
D7_ITEM21_SOURCE_RUNTIME_RECEIPT_REPOSITORY_PATH = (
    f"{D7_ITEM21_DIRECTORY}/item21-execution-source-runtime-receipt.json"
)
D7_ITEM21_SEED_FREE_READINESS_REPOSITORY_PATH = (
    f"{D7_ITEM21_DIRECTORY}/item21-seed-free-readiness.json"
)
D7_ITEM21_REVIEWED_FAMILY_ADMISSION_REPOSITORY_PATH = (
    f"{D7_ITEM21_DIRECTORY}/item21-reviewed-family-admission.json"
)
D7_ITEM22_SEED_SUPPLY_DIRECTORY_REPOSITORY_PATH = (
    f"{D7_ITEM21_DIRECTORY}/item22-seed-supply"
)
D7_ITEM22_CURRENT_SOURCE_REANCHOR_REPOSITORY_PATH = (
    f"{D7_ITEM21_DIRECTORY}/item22-current-source-runtime-reanchor.json"
)
D7_FUTURE_LAUNCH_DESCRIPTOR_REPOSITORY_PATH = f"{D7_ITEM21_DIRECTORY}/launch.json"

D7_PR26_RUNTIME_CLOSURE_MERGE_COMMIT = "eb3a1439739faf6394e78c225252d60e2e31b312"

MAX_D7_ITEM21_ARTIFACT_BYTES = 2 * 1024 * 1024
MAX_D7_ITEM21_GIT_OUTPUT_BYTES = 128 * 1024 * 1024
MAX_D7_ITEM21_SOURCE_MEMBERS = fused_start.MAX_D7_SOURCE_RUNTIME_MEMBER_COUNT
MAX_D7_ITEM21_SOURCE_TOTAL_BYTES = fused_start.MAX_D7_SOURCE_RUNTIME_TOTAL_BYTES

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
_REPOSITORY_PATH_RE = re.compile(r"^[A-Za-z0-9._/-]+$")

_ARTIFACT_PATHS = (
    D7_ITEM21_SOURCE_RUNTIME_RECEIPT_REPOSITORY_PATH,
    D7_ITEM21_SEED_FREE_READINESS_REPOSITORY_PATH,
    D7_ITEM21_REVIEWED_FAMILY_ADMISSION_REPOSITORY_PATH,
)
_LOADED_CHAIN_FACTORY_TOKEN = object()
_READY_HANDOFF_FACTORY_TOKEN = object()
_OFFICIAL_FULL_INVENTORY_BUILDER = official.build_d7_official_full_inventory_document
_OFFICIAL_AGGREGATION_BUILDER = official.build_d7_official_aggregation_document
_OFFICIAL_FULL_DESIGN_BUILDER = official.build_d7_official_full_design_document
_GENERATOR_SOURCE_PATH = "src/spirallens/synthetic/spectral_moment_confirmation.py"
_GENERATOR_SOURCE_SHA256 = (
    "6fd52c03c35ba8de6227b8583dfa6ff58ad913de7b85f0b38ccb7122f7dcc252"
)
_GENERATOR_IDENTITY = {
    "family_id": "spectral-moment-confirmation-grid-v0.1",
    "construction_family_id": "separable-spectral-moment-grid",
    "implementation_id": "numpy-separable-sine-moment-grid",
    "implementation_version": "v0.2",
}
_FIXED_CODE_SIDE_EXECUTION_INGREDIENTS = {
    "fixed_official_producer": {
        "producer_id": "d7-spectral-moment-official-producer-v0-1",
        "module": "spirallens.qualification.confirmation_official_execution",
        "qualname": "produce_d7_official_result",
        "parameters": [],
    },
    "exact_full_inventory_builder": {
        "module": "spirallens.qualification.confirmation_official_execution",
        "qualname": "build_d7_official_full_inventory_document",
        "keyword_only_parameters": ["design", "official_seed_inventory"],
        "closure_present": False,
    },
    "exact_aggregation_builder": {
        "module": "spirallens.qualification.confirmation_official_execution",
        "qualname": "build_d7_official_aggregation_document",
        "keyword_only_parameters": ["implementation_registry_sha256"],
        "closure_present": False,
    },
    "exact_full_design_builder": {
        "module": "spirallens.qualification.confirmation_official_execution",
        "qualname": "build_d7_official_full_design_document",
        "keyword_only_parameters": [
            "design",
            "official_seed_inventory",
            "full_inventory_sha256",
            "implementation_registry_sha256",
            "aggregation_sha256",
        ],
        "closure_present": False,
    },
    "exact_aggregation": {
        "schema_version": "spirallens.d7-official-exact-aggregation.v0.1",
        "canonical_sha256": (
            "c6d5596de711194c9fc42492642f418af24cb5462e32f7f8dd32e2d0d19fa760"
        ),
        "byte_count": 2_077,
    },
    "result_payload_schema_sha256": (
        "441912187a9ca0ffc2a1a0c9f02dbd5aea0f4fd659d57b0554f375a780ea90a2"
    ),
    "development_seed_exclusion_registry_sha256": (
        "20803b40c5fc6903e1d1a64ae41c0eb3dcbb3c4a859d7a482971088346fcb54a"
    ),
    "parent_selection_seed_exclusion_registry_sha256": (
        "9e11d212c57b04b424c228a554fc3f6eec221e9d7640cc06881bdaf913bf4b31"
    ),
}
_PRESEED_ABSENCE_PATHS = (
    D7_ITEM22_CURRENT_SOURCE_REANCHOR_REPOSITORY_PATH,
    D7_ITEM22_SEED_SUPPLY_DIRECTORY_REPOSITORY_PATH,
    D7_FUTURE_LAUNCH_DESCRIPTOR_REPOSITORY_PATH,
)

_C1_COMPONENT_BINDINGS = {
    "aggregation_application": (
        "spirallens.d7-confirmation-aggregation-application.v0.1",
        "d616cd063a87103c558fa33ce23514dab70abb59483d3d303ba1f475a6881435",
        5_034,
    ),
    "construction_diversity_review": (
        "spirallens.d7-construction-diversity-review.v0.1",
        "51e12859000ba67bb5ff01cecf6d6fe6a271114eb5aa0b6da9c3def59b8017c0",
        4_766,
    ),
    "implementation_registry": (
        "spirallens.d7-confirmation-implementation-registry.v0.1",
        "f73f0945ad59430ad75bde932acb2822e164140e06cd12428ef8b6167e1dca18",
        5_302,
    ),
    "seed_free_execution_design": (
        "spirallens.d7-stable-seed-free-execution-design.v0.1",
        "936df4835d398ae5f839da4ad4dace097997388a15643de440d7a4a582b13a4e",
        478_461,
    ),
    "source_set_manifest": (
        "spirallens.d7-c1-source-set-manifest.v0.1",
        "93b3b861ed8ec6d39069d070ef80e3ee2dc62720fd06fdec3063fdd6eacb95af",
        30_383,
    ),
    "successor_rebinding_review_contract": (
        "spirallens.d7-successor-rebinding-review-contract.v0.1",
        "9981eab2a962f5de38f728c0b037462448b988e52c52b1d1aac18b82bf944950",
        11_522,
    ),
}

_AUTHORITY_FALSE = {
    key: False
    for key in (
        "confirmation_values_accessed",
        "d7_execution_authorized",
        "d7_result_produced",
        "d8_execution_authorized",
        "integer_output_authorized",
        "localized_core_loop_join_established",
        "model_access_authorized",
        "p0_winner_selected",
        "pythia_access_authorized",
        "representation_instrument_advanced",
        "scientific_claim_eligible",
        "semantic_authority",
        "subject_access_authorized",
        "synthetic_qualified",
        "topology_claim_authorized",
    )
}


def _sha256(value: object, *, label: str) -> str:
    if type(value) is not str or _SHA256_RE.fullmatch(value) is None:
        raise QualificationContractError(f"{label} must be a lowercase SHA-256")
    return value


def _commit(value: object, *, label: str) -> str:
    if type(value) is not str or _COMMIT_RE.fullmatch(value) is None:
        raise QualificationContractError(f"{label} must be one lowercase Git commit")
    return value


def _positive_int(value: object, *, label: str) -> int:
    if type(value) is not int or value <= 0:
        raise QualificationContractError(f"{label} must be a positive integer")
    return value


def _mapping(value: object, *, label: str) -> dict[str, object]:
    if type(value) is not dict or any(type(key) is not str for key in value):
        raise QualificationContractError(f"{label} must be a string-keyed object")
    return value


def _exact_keys(
    value: dict[str, object],
    expected: set[str],
    *,
    label: str,
) -> None:
    if set(value) != expected:
        raise QualificationContractError(
            f"{label} fields differ: expected {sorted(expected)}, "
            f"observed {sorted(value)}"
        )


def _repository_path(value: object, *, label: str) -> str:
    if (
        type(value) is not str
        or not value
        or len(value.encode("utf-8")) > 4096
        or _REPOSITORY_PATH_RE.fullmatch(value) is None
    ):
        raise QualificationContractError(f"{label} must be a bounded repository path")
    path = PurePosixPath(value)
    if path.is_absolute() or "." in path.parts or ".." in path.parts:
        raise QualificationContractError(f"{label} must be canonical and relative")
    if path.as_posix() != value:
        raise QualificationContractError(f"{label} must use canonical POSIX spelling")
    return value


def _git(
    root: Path,
    *arguments: str,
    check: bool = True,
    timeout: float = 30.0,
) -> subprocess.CompletedProcess[bytes]:
    try:
        completed = subprocess.run(
            ["git", "-C", str(root), *arguments],
            check=False,
            capture_output=True,
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise QualificationContractError(
            f"cannot run Git verification: {' '.join(arguments)}"
        ) from error
    if (
        len(completed.stdout) > MAX_D7_ITEM21_GIT_OUTPUT_BYTES
        or len(completed.stderr) > MAX_D7_ITEM21_GIT_OUTPUT_BYTES
    ):
        raise QualificationContractError("Git verification output exceeds its cap")
    if check and completed.returncode != 0:
        detail = completed.stderr.decode("utf-8", errors="replace").strip()
        raise QualificationContractError(
            f"Git verification failed: {' '.join(arguments)}: {detail}"
        )
    return completed


def _repository_root(value: str | Path) -> Path:
    if not isinstance(value, (str, Path)):
        raise TypeError("repository_root must be str or Path")
    root = Path(os.path.abspath(os.fspath(value)))
    if root.is_symlink() or not root.is_dir() or Path(os.path.realpath(root)) != root:
        raise QualificationContractError("repository root must be one real directory")
    try:
        discovered = Path(
            _git(root, "rev-parse", "--show-toplevel").stdout.decode("utf-8").strip()
        )
    except UnicodeDecodeError as error:
        raise QualificationContractError("Git repository root is not UTF-8") from error
    if discovered != root:
        raise QualificationContractError(
            "repository_root must equal the exact Git toplevel"
        )
    return root


def _head(root: Path) -> str:
    try:
        value = (
            _git(root, "rev-parse", "--verify", "HEAD^{commit}")
            .stdout.decode("ascii")
            .strip()
        )
    except UnicodeDecodeError as error:
        raise QualificationContractError("Git HEAD is not ASCII") from error
    return _commit(value, label="Git HEAD")


def _require_clean(root: Path) -> None:
    status = _git(
        root,
        "status",
        "--porcelain=v1",
        "-z",
        "--untracked-files=all",
    ).stdout
    if status:
        raise QualificationContractError(
            "item-21 issuance or reload requires one clean Git worktree"
        )


def _require_ancestor(
    root: Path, ancestor: str, descendant: str, *, label: str
) -> None:
    _commit(ancestor, label=f"{label} ancestor")
    _commit(descendant, label=f"{label} descendant")
    result = _git(
        root,
        "merge-base",
        "--is-ancestor",
        ancestor,
        descendant,
        check=False,
    )
    if result.returncode != 0:
        raise QualificationContractError(f"{label} Git ancestry differs")


def _tree_entry(
    root: Path,
    commit: str,
    repository_path: str,
) -> tuple[str, str, str, int] | None:
    path = _repository_path(repository_path, label="tree repository path")
    result = _git(root, "ls-tree", "-z", commit, "--", path).stdout
    entries = [entry for entry in result.split(b"\0") if entry]
    if not entries:
        return None
    if len(entries) != 1:
        raise QualificationContractError("Git tree path is not one exact entry")
    try:
        header, raw_path = entries[0].split(b"\t", 1)
        mode, object_type, object_id = header.decode("ascii").split()
        observed_path = raw_path.decode("utf-8")
        size = int(
            _git(root, "cat-file", "-s", object_id).stdout.decode("ascii").strip()
        )
    except (ValueError, UnicodeDecodeError) as error:
        raise QualificationContractError("Git tree entry is malformed") from error
    if observed_path != path:
        raise QualificationContractError("Git tree path spelling differs")
    return mode, object_type, _commit(object_id, label="Git blob object"), size


def _blob(root: Path, commit: str, repository_path: str) -> bytes:
    entry = _tree_entry(root, commit, repository_path)
    if entry is None:
        raise QualificationContractError(
            f"required Git blob is absent: {repository_path}"
        )
    mode, object_type, object_id, size = entry
    if mode != "100644" or object_type != "blob" or size <= 0:
        raise QualificationContractError(
            f"required Git artifact is not one regular 100644 blob: {repository_path}"
        )
    source = _git(root, "cat-file", "blob", object_id).stdout
    if len(source) != size:
        raise QualificationContractError("Git blob byte count differs")
    return source


def _require_path_absent_at_commit(
    root: Path,
    commit: str,
    repository_path: str,
) -> None:
    path = _repository_path(repository_path, label="absent repository path")
    if _git(root, "ls-tree", "-r", "-z", commit, "--", path).stdout:
        raise QualificationContractError(
            f"preseed path was present too early: {repository_path}"
        )


def _read_worktree_artifact(
    root: Path,
    repository_path: str,
    *,
    maximum_bytes: int = MAX_D7_ITEM21_ARTIFACT_BYTES,
) -> bytes:
    path = root / _repository_path(repository_path, label="artifact repository path")
    try:
        before = path.lstat()
    except OSError as error:
        raise QualificationContractError(
            "committed item-21 artifact is absent"
        ) from error
    if (
        not stat.S_ISREG(before.st_mode)
        or before.st_nlink != 1
        or before.st_size <= 0
        or before.st_size > maximum_bytes
    ):
        raise QualificationContractError(
            "item-21 artifact must be one bounded non-hardlinked regular file"
        )
    source = path.read_bytes()
    after = path.lstat()
    identity_fields = (
        "st_dev",
        "st_ino",
        "st_mode",
        "st_nlink",
        "st_size",
        "st_mtime_ns",
    )
    if len(source) != before.st_size or tuple(
        getattr(before, name) for name in identity_fields
    ) != tuple(getattr(after, name) for name in identity_fields):
        raise QualificationContractError("item-21 artifact changed during read")
    return source


def _parse_canonical_artifact(source: bytes, *, label: str) -> dict[str, object]:
    if (
        type(source) is not bytes
        or not source
        or len(source) > MAX_D7_ITEM21_ARTIFACT_BYTES
    ):
        raise QualificationContractError(
            f"{label} must be nonempty canonical bytes within its cap"
        )
    try:
        parsed = parse_canonical_json(source, label=label)
    except CanonicalJsonError as error:
        raise QualificationContractError(str(error)) from error
    document = _mapping(parsed, label=label)
    if canonical_json_bytes(document) != source:
        raise QualificationContractError(f"{label} is not one canonical round trip")
    return document


def _introduction_commit(
    root: Path,
    *,
    repository_path: str,
    expected_parent: str,
    expected_source: bytes,
) -> str:
    path = _repository_path(repository_path, label="introduction repository path")
    try:
        history = [
            line
            for line in _git(root, "log", "--format=%H", "--", path)
            .stdout.decode("ascii")
            .splitlines()
            if line
        ]
    except UnicodeDecodeError as error:
        raise QualificationContractError("artifact Git history is not ASCII") from error
    if len(history) != 1:
        raise QualificationContractError(
            "item-21 artifact lacks one unique immutable introduction commit"
        )
    introduction = _commit(history[0], label="artifact introduction commit")
    try:
        parent_line = (
            _git(root, "rev-list", "--parents", "-n", "1", introduction)
            .stdout.decode("ascii")
            .strip()
            .split()
        )
    except UnicodeDecodeError as error:
        raise QualificationContractError(
            "artifact parent history is not ASCII"
        ) from error
    if parent_line != [introduction, expected_parent]:
        raise QualificationContractError(
            "item-21 artifact introduction is not the required direct child"
        )
    delta = _git(
        root,
        "diff-tree",
        "--no-commit-id",
        "--name-status",
        "-r",
        introduction,
    ).stdout
    expected_delta = f"A\t{path}\n".encode()
    if delta != expected_delta:
        raise QualificationContractError(
            "item-21 artifact introduction changed more than its one added file"
        )
    _require_path_absent_at_commit(root, expected_parent, path)
    if _blob(root, introduction, path) != expected_source:
        raise QualificationContractError("item-21 introduction blob differs")
    head = _head(root)
    _require_ancestor(root, introduction, head, label="artifact-to-current-HEAD")
    if _blob(root, head, path) != expected_source:
        raise QualificationContractError(
            "item-21 artifact changed after its introduction"
        )
    return introduction


def _source_inventory(
    root: Path,
    source_commit: str,
    *,
    require_current_equality: bool,
) -> dict[str, object]:
    commit = _commit(source_commit, label="execution source commit")
    # Issuance/live verification delegates to the existing owner so current
    # HEAD inventory and every live byte must equal the anchor.  Historical
    # reload instead reconstructs from the immutable Git tree; a later source
    # change makes the live verifier fail but does not erase the old receipt.
    shared_sha256 = (
        fused_start._source_tree_sha256(root, commit)
        if require_current_equality
        else None
    )
    tree = _git(
        root,
        "ls-tree",
        "-r",
        "-z",
        "--full-tree",
        commit,
        "--",
        *fused_start._SOURCE_PATHS,
    ).stdout
    members: list[dict[str, object]] = []
    total_bytes = 0
    for raw in (entry for entry in tree.split(b"\0") if entry):
        try:
            header, raw_path = raw.split(b"\t", 1)
            mode, object_type, object_id = header.decode("ascii").split()
            repository_path = raw_path.decode("utf-8")
        except (ValueError, UnicodeDecodeError) as error:
            raise QualificationContractError(
                "execution source Git inventory is malformed"
            ) from error
        included = (
            repository_path == "pyproject.toml"
            or repository_path == fused_start.D7_RUNTIME_LOCK_REPOSITORY_PATH
            or repository_path.startswith("src/spirallens/")
        )
        if not included:
            continue
        if (
            len(members) >= MAX_D7_ITEM21_SOURCE_MEMBERS
            or mode not in {"100644", "100755"}
            or object_type != "blob"
        ):
            raise QualificationContractError(
                "execution source inventory exceeds its closed contract"
            )
        object_id = _commit(object_id, label="execution source blob")
        try:
            size = int(
                _git(root, "cat-file", "-s", object_id).stdout.decode("ascii").strip()
            )
        except (ValueError, UnicodeDecodeError) as error:
            raise QualificationContractError(
                "execution source blob size is malformed"
            ) from error
        source = _git(root, "cat-file", "blob", object_id).stdout
        if size <= 0 or len(source) != size:
            raise QualificationContractError("execution source blob size differs")
        total_bytes += size
        if total_bytes > MAX_D7_ITEM21_SOURCE_TOTAL_BYTES:
            raise QualificationContractError(
                "execution source inventory exceeds its total byte cap"
            )
        members.append(
            {
                "repository_path": repository_path,
                "git_mode": mode,
                "byte_count": size,
                "sha256": sha256_bytes(source),
            }
        )
    members.sort(key=lambda item: str(item["repository_path"]))
    members_by_path = {str(member["repository_path"]): member for member in members}
    for required_regular_path in (
        "pyproject.toml",
        fused_start.D7_RUNTIME_LOCK_REPOSITORY_PATH,
    ):
        required_member = members_by_path.get(required_regular_path)
        if required_member is None or required_member.get("git_mode") != "100644":
            raise QualificationContractError(
                f"execution source requires a 100644 {required_regular_path}"
            )
    digest_document = {
        "schema_version": fused_start.D7_FUSED_START_SOURCE_TREE_SCHEME,
        "source_commit": commit,
        "members": members,
    }
    reconstructed_sha256 = canonical_json_sha256(digest_document)
    if shared_sha256 is not None and reconstructed_sha256 != shared_sha256:
        raise QualificationContractError(
            "item-21 source inventory differs from fused-start observation"
        )
    return {
        **digest_document,
        "member_count": len(members),
        "total_byte_count": total_bytes,
        "source_tree_sha256": reconstructed_sha256,
    }


def _native_runtime_observation() -> dict[str, object]:
    executable = Path(os.path.realpath(sys.executable))
    try:
        status = executable.stat()
    except OSError as error:
        raise QualificationContractError("Python executable is unavailable") from error
    if not stat.S_ISREG(status.st_mode) or status.st_size <= 0:
        raise QualificationContractError(
            "Python executable must resolve to one regular file"
        )
    source = fused_start._read_regular_file(
        executable,
        label="item-21 Python executable",
        maximum_bytes=512 * 1024 * 1024,
    )
    return {
        "executable_sha256": sha256_bytes(source),
        "executable_byte_count": len(source),
    }


def _runtime_document(
    root: Path,
    *,
    require_installed_equality: bool,
    source_commit: str | None = None,
    recorded_runtime: dict[str, object] | None = None,
) -> dict[str, object]:
    if require_installed_equality:
        if recorded_runtime is not None or source_commit is not None:
            raise QualificationContractError(
                "live runtime observation cannot accept recorded runtime fields"
            )
        lock_source = fused_start._read_regular_file(
            root / fused_start.D7_RUNTIME_LOCK_REPOSITORY_PATH,
            label="D7 runtime lock",
            maximum_bytes=runtime_observation.MAX_D7_RUNTIME_LOCK_BYTES,
        )
        observed = runtime_observation._verify_exact_dependency_lock(lock_source)
        pins = observed.distributions
        dependency_set_sha256 = observed.transitive_dependency_set_sha256
        native = _native_runtime_observation()
        specification = authority.D7RuntimeSpecificationInputRecord(
            runtime_specification_id="d7-item21-exact-runtime-v0-1",
            python_implementation=sys.implementation.name,
            python_version=platform.python_version(),
            platform=sys.platform,
            machine=platform.machine().lower(),
            dependency_lock_sha256=sha256_bytes(lock_source),
            native_runtime_sha256=str(native["executable_sha256"]),
        )
    else:
        if recorded_runtime is None or source_commit is None:
            raise QualificationContractError(
                "historical runtime reconstruction requires recorded fields and commit"
            )
        lock_source = _blob(
            root,
            _commit(source_commit, label="historical runtime source commit"),
            fused_start.D7_RUNTIME_LOCK_REPOSITORY_PATH,
        )
        if len(lock_source) > runtime_observation.MAX_D7_RUNTIME_LOCK_BYTES:
            raise QualificationContractError(
                "historical D7 runtime lock exceeds its fixed byte cap"
            )
        pins = runtime_observation._parse_exact_dependency_lock(lock_source)
        runtime_specification = _mapping(
            recorded_runtime.get("runtime_specification"),
            label="recorded runtime specification",
        )
        try:
            specification = authority.D7RuntimeSpecificationInputRecord.from_dict(
                runtime_specification
            )
        except (TypeError, ValueError) as error:
            raise QualificationContractError(
                "recorded runtime specification is malformed"
            ) from error
        recorded_native = _mapping(
            recorded_runtime.get("native_runtime"),
            label="recorded native runtime",
        )
        _exact_keys(
            recorded_native,
            {"executable_sha256", "executable_byte_count"},
            label="recorded native runtime",
        )
        native = {
            "executable_sha256": _sha256(
                recorded_native.get("executable_sha256"),
                label="recorded executable_sha256",
            ),
            "executable_byte_count": _positive_int(
                recorded_native.get("executable_byte_count"),
                label="recorded executable_byte_count",
            ),
        }
        if (
            specification.dependency_lock_sha256 != sha256_bytes(lock_source)
            or specification.native_runtime_sha256 != native["executable_sha256"]
        ):
            raise QualificationContractError(
                "recorded runtime specification differs from lock or executable"
            )
        dependency_set_sha256 = sha256_bytes(
            canonical_json_bytes(
                {
                    "schema_version": (
                        runtime_observation.D7_RUNTIME_DEPENDENCY_SET_SCHEME
                    ),
                    "python_implementation": specification.python_implementation,
                    "python_version": specification.python_version,
                    "distributions": [
                        {"name": pin.name, "version": pin.version} for pin in pins
                    ],
                }
            )
        )
    return {
        "runtime_specification": specification.to_dict(),
        "runtime_specification_sha256": specification.canonical_sha256,
        "runtime_specification_byte_count": specification.byte_count,
        "dependency_lock": {
            "repository_path": fused_start.D7_RUNTIME_LOCK_REPOSITORY_PATH,
            "canonical_sha256": sha256_bytes(lock_source),
            "byte_count": len(lock_source),
        },
        "installed_distribution_inventory": [
            {"name": pin.name, "version": pin.version} for pin in pins
        ],
        "installed_distribution_count": len(pins),
        "installed_dependency_set_schema_version": (
            runtime_observation.D7_RUNTIME_DEPENDENCY_SET_SCHEME
        ),
        "installed_dependency_set_sha256": dependency_set_sha256,
        "complete_installed_inventory_equality_observed_at_issuance": True,
        "native_runtime": native,
    }


def _binding(
    *,
    repository_path: str,
    schema_version: str,
    source: bytes,
    introduction_commit: str | None = None,
) -> dict[str, object]:
    result: dict[str, object] = {
        "repository_path": repository_path,
        "schema_version": schema_version,
        "canonical_sha256": sha256_bytes(source),
        "byte_count": len(source),
    }
    if introduction_commit is not None:
        result["introduction_commit"] = introduction_commit
    return result


def _require_exact_official_builder(
    candidate: object,
    expected: FunctionType,
    *,
    qualname: str,
    keyword_only_parameters: tuple[str, ...],
) -> FunctionType:
    if (
        type(candidate) is not FunctionType
        or candidate is not expected
        or candidate.__module__ != official.__name__
        or candidate.__qualname__ != qualname
        or candidate.__code__.co_argcount != 0
        or candidate.__code__.co_posonlyargcount != 0
        or candidate.__code__.co_kwonlyargcount != len(keyword_only_parameters)
        or candidate.__code__.co_varnames[: len(keyword_only_parameters)]
        != keyword_only_parameters
        or candidate.__defaults__ is not None
        or candidate.__kwdefaults__ is not None
        or candidate.__closure__ is not None
    ):
        raise QualificationContractError(f"official {qualname} identity differs")
    return candidate


def _current_code_side_execution_ingredients() -> dict[str, object]:
    producer = official._require_official_producer_identity(
        official.produce_d7_official_result
    )
    full_inventory = _require_exact_official_builder(
        official.build_d7_official_full_inventory_document,
        _OFFICIAL_FULL_INVENTORY_BUILDER,
        qualname="build_d7_official_full_inventory_document",
        keyword_only_parameters=("design", "official_seed_inventory"),
    )
    aggregation = _require_exact_official_builder(
        official.build_d7_official_aggregation_document,
        _OFFICIAL_AGGREGATION_BUILDER,
        qualname="build_d7_official_aggregation_document",
        keyword_only_parameters=("implementation_registry_sha256",),
    )
    full_design = _require_exact_official_builder(
        official.build_d7_official_full_design_document,
        _OFFICIAL_FULL_DESIGN_BUILDER,
        qualname="build_d7_official_full_design_document",
        keyword_only_parameters=(
            "design",
            "official_seed_inventory",
            "full_inventory_sha256",
            "implementation_registry_sha256",
            "aggregation_sha256",
        ),
    )

    def binding(candidate: FunctionType) -> dict[str, object]:
        return {
            "module": candidate.__module__,
            "qualname": candidate.__qualname__,
            "keyword_only_parameters": list(
                candidate.__code__.co_varnames[: candidate.__code__.co_kwonlyargcount]
            ),
            "closure_present": candidate.__closure__ is not None,
        }

    aggregation_document = _OFFICIAL_AGGREGATION_BUILDER(
        implementation_registry_sha256=(
            official.D7_RECORDED_C1_IMPLEMENTATION_REGISTRY_SHA256
        )
    )
    development = authority.D7DevelopmentSeedExclusionRegistryRecord.exact()
    parent = authority.D7ParentSelectionSeedExclusionRegistryRecord.exact()
    result = {
        "fixed_official_producer": {
            "producer_id": official.D7_OFFICIAL_PRODUCER_ID,
            "module": producer.__module__,
            "qualname": producer.__qualname__,
            "parameters": [],
        },
        "exact_full_inventory_builder": binding(full_inventory),
        "exact_aggregation_builder": binding(aggregation),
        "exact_full_design_builder": binding(full_design),
        "exact_aggregation": {
            "schema_version": aggregation_document["schema_version"],
            "canonical_sha256": canonical_json_sha256(aggregation_document),
            "byte_count": len(canonical_json_bytes(aggregation_document)),
        },
        "result_payload_schema_sha256": (
            authority.attempt_records.D7_SCIENTIFIC_RESULT_IMPLEMENTATION_SCHEMA_SHA256
        ),
        "development_seed_exclusion_registry_sha256": development.canonical_sha256,
        "parent_selection_seed_exclusion_registry_sha256": parent.canonical_sha256,
    }
    if result != _FIXED_CODE_SIDE_EXECUTION_INGREDIENTS:
        raise QualificationContractError(
            "current official code-side ingredients differ from item-21 v0.1"
        )
    return result


def _recorded_components(
    root: Path,
    *,
    source_observation: dict[str, object],
    verify_current_implementation: bool,
) -> dict[str, object]:
    head = _head(root)
    c1_source = _blob(root, head, c1.D7_C1_BUNDLE_REPOSITORY_PATH)
    if (
        sha256_bytes(c1_source) != authority.D7_RECORDED_C1_CANONICAL_SHA256
        or len(c1_source) != authority.D7_RECORDED_C1_BYTE_COUNT
    ):
        raise QualificationContractError("recorded C1 binding differs")
    document = _parse_canonical_artifact(c1_source, label="recorded C1")
    components = _mapping(document.get("components"), label="recorded C1 components")
    component_bindings: dict[str, object] = {}
    for name, (schema_version, expected_sha256, expected_bytes) in sorted(
        _C1_COMPONENT_BINDINGS.items()
    ):
        component = _mapping(
            components.get(name),
            label=f"recorded C1 {name}",
        )
        body = _mapping(component.get("body"), label=f"recorded C1 {name} body")
        body_source = canonical_json_bytes(body)
        if (
            body.get("schema_version") != schema_version
            or component.get("canonical_sha256") != expected_sha256
            or sha256_bytes(body_source) != expected_sha256
            or len(body_source) != expected_bytes
        ):
            raise QualificationContractError(f"recorded C1 {name} binding differs")
        component_bindings[name] = {
            "schema_version": schema_version,
            "canonical_sha256": expected_sha256,
            "byte_count": expected_bytes,
        }
    implementation = _mapping(
        _mapping(
            components["implementation_registry"],
            label="recorded implementation component",
        ).get("body"),
        label="recorded implementation body",
    )
    generator = _mapping(
        implementation.get("generator"),
        label="recorded implementation generator",
    )
    family_identity = _mapping(
        generator.get("family_identity"),
        label="recorded generator family identity",
    )
    generator_source_sha256 = _sha256(
        family_identity.get("source_sha256"),
        label="recorded generator source_sha256",
    )
    if any(
        family_identity.get(name) != expected
        for name, expected in _GENERATOR_IDENTITY.items()
    ):
        raise QualificationContractError(
            "recorded confirmation generator identity differs from item-21 v0.1"
        )
    source_members = source_observation.get("members")
    if type(source_members) is not list:
        raise QualificationContractError(
            "execution source observation lacks its member inventory"
        )
    generator_members = [
        _mapping(member, label="execution source member")
        for member in source_members
        if type(member) is dict
        and member.get("repository_path") == _GENERATOR_SOURCE_PATH
    ]
    if len(generator_members) != 1:
        raise QualificationContractError(
            "execution source inventory lacks one unique confirmation generator"
        )
    generator_member = generator_members[0]
    if (
        generator_source_sha256 != _GENERATOR_SOURCE_SHA256
        or generator_member.get("sha256") != generator_source_sha256
        or generator_member.get("git_mode") != "100644"
        or type(generator_member.get("byte_count")) is not int
        or int(generator_member["byte_count"]) <= 0
    ):
        raise QualificationContractError(
            "recorded confirmation generator differs from the source anchor"
        )
    design_component = _mapping(
        components["seed_free_execution_design"],
        label="recorded seed-free design component",
    )
    design_body = _mapping(
        design_component.get("body"),
        label="recorded seed-free design body",
    )
    design_document = _mapping(
        design_body.get("seed_free_execution_design"),
        label="recorded seed-free execution design",
    )
    design_source = canonical_json_bytes(design_document)

    c2_source = _blob(root, head, c1.D7_C2_RECEIPT_REPOSITORY_PATH)
    if (
        sha256_bytes(c2_source) != authority.D7_RECORDED_C2_CANONICAL_SHA256
        or len(c2_source) != authority.D7_RECORDED_C2_BYTE_COUNT
    ):
        raise QualificationContractError("recorded C2 binding differs")
    if verify_current_implementation:
        replay_contracts.load_d7_replay_attempt_contract_foundation(
            repository_root=root
        )
        bundle = c1.D7C1SeedFreeSourceSet.from_canonical_bytes(
            c1_source,
            expected_sha256=authority.D7_RECORDED_C1_CANONICAL_SHA256,
        )
        design = official._recorded_c1_design(root)
        if (
            bundle.to_dict() != document
            or design.canonical_bytes != design_source
            or authority.D7_CONFIRMATION_GENERATOR_FAMILY_ID
            != _GENERATOR_IDENTITY["family_id"]
            or spectral_generator.SPECTRAL_MOMENT_SOURCE_PATH != _GENERATOR_SOURCE_PATH
            or spectral_generator.SPECTRAL_MOMENT_GENERATOR_FAMILY_ID
            != _GENERATOR_IDENTITY["family_id"]
            or spectral_generator.SPECTRAL_MOMENT_CONSTRUCTION_FAMILY_ID
            != _GENERATOR_IDENTITY["construction_family_id"]
            or spectral_generator.SPECTRAL_MOMENT_IMPLEMENTATION_ID
            != _GENERATOR_IDENTITY["implementation_id"]
            or spectral_generator.SPECTRAL_MOMENT_IMPLEMENTATION_VERSION
            != _GENERATOR_IDENTITY["implementation_version"]
        ):
            raise QualificationContractError(
                "current confirmation implementation differs from recorded C1"
            )
    return {
        "recorded_c1": _binding(
            repository_path=c1.D7_C1_BUNDLE_REPOSITORY_PATH,
            schema_version=authority.D7_RECORDED_C1_SCHEMA_VERSION,
            source=c1_source,
        ),
        "recorded_c2": _binding(
            repository_path=c1.D7_C2_RECEIPT_REPOSITORY_PATH,
            schema_version=authority.D7_RECORDED_C2_SCHEMA_VERSION,
            source=c2_source,
        ),
        "components": component_bindings,
        "generator_source": {
            "repository_path": _GENERATOR_SOURCE_PATH,
            "canonical_sha256": generator_source_sha256,
            "byte_count": generator_member["byte_count"],
            "git_mode": generator_member["git_mode"],
            **_GENERATOR_IDENTITY,
        },
        "seed_free_design": {
            "schema_version": design_document.get("schema_version"),
            "canonical_sha256": sha256_bytes(design_source),
            "byte_count": len(design_source),
        },
    }


def _final_code_review(
    source_commit: str, source_tree_sha256: str
) -> dict[str, object]:
    return {
        "schema_version": D7_ITEM21_FINAL_CODE_REVIEW_SCHEMA_VERSION,
        "review_id": "d7-item21-final-code-review-v0-1",
        "reviewed_source_commit": source_commit,
        "reviewed_source_tree_sha256": source_tree_sha256,
        "review_scope": [
            "lifecycle-code",
            "result-code",
            "terminal-code",
            "witness-code",
            "runner-code",
            "fused-start-code",
            "runtime-lock-and-observer-code",
            "fixed-official-producer-and-builders",
            "item21-positive-chain-code",
        ],
        "review_method": (
            "repository-maintainer-plus-bounded-adversarial-agent-review"
        ),
        "remaining_severity_counts": {"p0": 0, "p1": 0, "p2": 0},
        "repository_review_attested": True,
        "reviewer_identity_cryptographically_authenticated": False,
        "signed_external_timestamp_present": False,
        "official_seed_values_accessed": False,
        "confirmation_values_accessed": False,
    }


def _source_receipt_document(
    root: Path,
    *,
    source_commit: str,
    require_current_source_equality: bool,
    require_installed_equality: bool,
    recorded_runtime: dict[str, object] | None = None,
) -> dict[str, object]:
    source = _source_inventory(
        root,
        source_commit,
        require_current_equality=require_current_source_equality,
    )
    runtime = _runtime_document(
        root,
        require_installed_equality=require_installed_equality,
        source_commit=None if require_installed_equality else source_commit,
        recorded_runtime=recorded_runtime,
    )
    recorded = _recorded_components(
        root,
        source_observation=source,
        verify_current_implementation=require_current_source_equality,
    )
    review = _final_code_review(
        source_commit,
        str(source["source_tree_sha256"]),
    )
    return {
        "schema_version": D7_ITEM21_SOURCE_RUNTIME_RECEIPT_SCHEMA_VERSION,
        "receipt_id": "d7-item21-execution-source-runtime-receipt-v0-1",
        "artifact_role": "execution-source-runtime-receipt",
        "repository_path": (D7_ITEM21_SOURCE_RUNTIME_RECEIPT_REPOSITORY_PATH),
        "status": "exact-anchor-source-runtime-observed",
        "claim_ceiling": "level_0",
        "lineage": {
            "pr26_runtime_closure_merge_commit": (D7_PR26_RUNTIME_CLOSURE_MERGE_COMMIT),
            "source_commit": source_commit,
            "receipt_absent_at_source_commit": True,
            "receipt_introduction_commit_embedded": False,
            "source_anchor_clean_head_at_issuance": True,
            "canonical_origin_main_equality_at_issuance_claimed": False,
            "post_merge_current_tree_reverification_required": True,
            "later_execution_source_change_invalidates_live_readiness": True,
            "versioned_current_source_reanchor_required_before_item22_after_change": (
                True
            ),
            "recorded_c1": recorded["recorded_c1"],
            "recorded_c2": recorded["recorded_c2"],
        },
        "final_code_review": review,
        "final_code_review_sha256": canonical_json_sha256(review),
        "source_observation": source,
        "runtime_observation": runtime,
        "state": {
            "source_runtime_observed_at_issuance": True,
            "historical_receipt_remains_reloadable_after_later_source_change": True,
            "current_source_tree_must_still_equal_receipt_before_item22": True,
            "seed_free_readiness_present": False,
            "family_admission_present": False,
            "exclusive_seed_supply_claim_present": False,
            "supplier_invoked": False,
            "official_seed_inventory_present": False,
            "seed_bearing_target_present": False,
            "full_design_freeze_present": False,
            "launch_intent_present": False,
            "launch_descriptor_present": False,
            "execution_observed": False,
            "d7_state": "not_run",
            "d8_state": "not_run",
        },
        "limitations": {
            "official_process_attested_only": True,
            "signed_trust_root_proved": False,
            "external_timestamp_proved": False,
            "hostile_local_operator_resistance_proved": False,
            "installed_package_files_closed": False,
            "loaded_native_libraries_closed": False,
            "mutable_module_state_closed": False,
            "unrecorded_environment_closed": False,
            "model_or_data_state_closed": False,
        },
        "authority": {
            "confirmation_family_admitted": False,
            **_AUTHORITY_FALSE,
        },
    }


def build_d7_item21_source_runtime_receipt(
    repository_root: str | Path,
) -> bytes:
    """Build the first choice-free item-21 artifact from one clean source HEAD."""

    root = _repository_root(repository_root)
    _require_clean(root)
    source_commit = _head(root)
    _require_ancestor(
        root,
        D7_PR26_RUNTIME_CLOSURE_MERGE_COMMIT,
        source_commit,
        label="PR26-to-item21-source",
    )
    for path in _ARTIFACT_PATHS:
        _require_path_absent_at_commit(root, source_commit, path)
        if (root / path).exists() or (root / path).is_symlink():
            raise QualificationContractError("item-21 artifact path already exists")
    for path in _PRESEED_ABSENCE_PATHS:
        _require_path_absent_at_commit(root, source_commit, path)
        if (root / path).exists() or (root / path).is_symlink():
            raise QualificationContractError("future item-22 path already exists")
    return canonical_json_bytes(
        _source_receipt_document(
            root,
            source_commit=source_commit,
            require_current_source_equality=True,
            require_installed_equality=True,
        )
    )


def issue_d7_item21_source_runtime_receipt(
    repository_root: str | Path,
) -> PersistedQualificationIdentity:
    """Publish the first artifact without overwrite; accept no caller choices."""

    root = _repository_root(repository_root)
    source = build_d7_item21_source_runtime_receipt(root)
    return _atomic_write_no_overwrite(
        root / D7_ITEM21_SOURCE_RUNTIME_RECEIPT_REPOSITORY_PATH,
        source,
        maximum_bytes=MAX_D7_ITEM21_ARTIFACT_BYTES,
        label="D7 item-21 source/runtime receipt",
    )


@dataclass(frozen=True, slots=True)
class _LoadedArtifact:
    repository_path: str
    source: bytes
    introduction_commit: str

    @property
    def canonical_sha256(self) -> str:
        return sha256_bytes(self.source)

    @property
    def byte_count(self) -> int:
        return len(self.source)

    @property
    def document(self) -> dict[str, object]:
        return copy.deepcopy(
            _parse_canonical_artifact(
                self.source,
                label=self.repository_path,
            )
        )


def _load_source_receipt(root: Path) -> _LoadedArtifact:
    repository_path = D7_ITEM21_SOURCE_RUNTIME_RECEIPT_REPOSITORY_PATH
    source = _read_worktree_artifact(root, repository_path)
    document = _parse_canonical_artifact(
        source,
        label="D7 item-21 source/runtime receipt",
    )
    _exact_keys(
        document,
        {
            "schema_version",
            "receipt_id",
            "artifact_role",
            "repository_path",
            "status",
            "claim_ceiling",
            "lineage",
            "final_code_review",
            "final_code_review_sha256",
            "source_observation",
            "runtime_observation",
            "state",
            "limitations",
            "authority",
        },
        label="D7 item-21 source/runtime receipt",
    )
    if (
        document["schema_version"] != D7_ITEM21_SOURCE_RUNTIME_RECEIPT_SCHEMA_VERSION
        or document["repository_path"] != repository_path
    ):
        raise QualificationContractError("source/runtime receipt identity differs")
    lineage = _mapping(document["lineage"], label="source/runtime lineage")
    source_commit = _commit(lineage.get("source_commit"), label="receipt source commit")
    _require_ancestor(
        root,
        D7_PR26_RUNTIME_CLOSURE_MERGE_COMMIT,
        source_commit,
        label="PR26-to-receipt-source",
    )
    runtime = _mapping(
        document["runtime_observation"],
        label="recorded runtime observation",
    )
    expected = _source_receipt_document(
        root,
        source_commit=source_commit,
        require_current_source_equality=False,
        require_installed_equality=False,
        recorded_runtime=runtime,
    )
    if document != expected or source != canonical_json_bytes(expected):
        raise QualificationContractError(
            "source/runtime receipt differs from exact reconstruction"
        )
    introduction = _introduction_commit(
        root,
        repository_path=repository_path,
        expected_parent=source_commit,
        expected_source=source,
    )
    return _LoadedArtifact(repository_path, source, introduction)


def _artifact_binding(
    artifact: _LoadedArtifact,
    *,
    schema_version: str,
) -> dict[str, object]:
    return _binding(
        repository_path=artifact.repository_path,
        schema_version=schema_version,
        source=artifact.source,
        introduction_commit=artifact.introduction_commit,
    )


def _absence_observation() -> dict[str, object]:
    return {
        "required_absent_repository_paths": list(_PRESEED_ABSENCE_PATHS),
        "all_required_paths_absent_at_issuance": True,
        "absence_is_point_in_time": True,
        "absence_proves_supplier_not_invoked": False,
    }


def _readiness_document(
    root: Path,
    receipt: _LoadedArtifact,
    *,
    verify_current_implementation: bool,
) -> dict[str, object]:
    receipt_document = receipt.document
    recorded = _recorded_components(
        root,
        source_observation=_mapping(
            receipt_document["source_observation"],
            label="receipt source observation",
        ),
        verify_current_implementation=verify_current_implementation,
    )
    ingredients = (
        _current_code_side_execution_ingredients()
        if verify_current_implementation
        else copy.deepcopy(_FIXED_CODE_SIDE_EXECUTION_INGREDIENTS)
    )
    return {
        "schema_version": D7_ITEM21_SEED_FREE_READINESS_SCHEMA_VERSION,
        "readiness_id": "d7-item21-seed-free-readiness-v0-1",
        "artifact_role": "seed-free-readiness",
        "repository_path": D7_ITEM21_SEED_FREE_READINESS_REPOSITORY_PATH,
        "status": "seed-free-ready-for-reviewed-family-admission",
        "claim_ceiling": "level_0",
        "predecessor": _artifact_binding(
            receipt,
            schema_version=D7_ITEM21_SOURCE_RUNTIME_RECEIPT_SCHEMA_VERSION,
        ),
        "recorded_inputs": recorded,
        "code_side_execution_ingredients": ingredients,
        "preseed_absence": _absence_observation(),
        "readiness": {
            "exact_source_runtime_receipt_committed": True,
            "recorded_c1_c2_reverified": True,
            "seed_free_design_reconstructed": True,
            "fixed_producer_identity_verified": True,
            "implementation_registry_bound": True,
            "aggregation_bound": True,
            "result_schema_bound": True,
            "seed_free_readiness_verified": True,
            "current_source_tree_must_still_equal_receipt_before_item22": True,
            "versioned_current_source_reanchor_required_after_source_change": True,
            "cryptographic_preseed_unseen_proof": False,
            "human_or_external_process_unseen_proof": False,
            "confirmation_values_accessed": False,
            "supplier_invoked": False,
            "official_seed_inventory_present": False,
            "seed_bearing_target_present": False,
            "full_design_freeze_present": False,
            "launch_intent_present": False,
            "launch_descriptor_present": False,
            "d7_state": "not_run",
            "d8_state": "not_run",
        },
        "authority": {
            "confirmation_family_admitted": False,
            **_AUTHORITY_FALSE,
        },
    }


def _require_live_paths_absent(root: Path) -> None:
    head = _head(root)
    for repository_path in _PRESEED_ABSENCE_PATHS:
        _require_path_absent_at_commit(root, head, repository_path)
        path = root / repository_path
        if path.exists() or path.is_symlink():
            raise QualificationContractError(
                f"preseed path is not live-absent: {repository_path}"
            )


def build_d7_item21_seed_free_readiness(
    repository_root: str | Path,
) -> bytes:
    """Build readiness only from the committed first artifact and live absence."""

    root = _repository_root(repository_root)
    _require_clean(root)
    receipt = _load_source_receipt(root)
    if _head(root) != receipt.introduction_commit:
        raise QualificationContractError(
            "readiness must be issued from the receipt-only direct child"
        )
    if (root / D7_ITEM21_SEED_FREE_READINESS_REPOSITORY_PATH).exists():
        raise QualificationContractError("seed-free readiness already exists")
    if (root / D7_ITEM21_REVIEWED_FAMILY_ADMISSION_REPOSITORY_PATH).exists():
        raise QualificationContractError("family admission exists before readiness")
    _verify_live_runtime(root, receipt)
    _require_live_paths_absent(root)
    return canonical_json_bytes(
        _readiness_document(
            root,
            receipt,
            verify_current_implementation=True,
        )
    )


def issue_d7_item21_seed_free_readiness(
    repository_root: str | Path,
) -> PersistedQualificationIdentity:
    root = _repository_root(repository_root)
    source = build_d7_item21_seed_free_readiness(root)
    return _atomic_write_no_overwrite(
        root / D7_ITEM21_SEED_FREE_READINESS_REPOSITORY_PATH,
        source,
        maximum_bytes=MAX_D7_ITEM21_ARTIFACT_BYTES,
        label="D7 item-21 seed-free readiness",
    )


def _load_readiness(root: Path, receipt: _LoadedArtifact) -> _LoadedArtifact:
    repository_path = D7_ITEM21_SEED_FREE_READINESS_REPOSITORY_PATH
    source = _read_worktree_artifact(root, repository_path)
    document = _parse_canonical_artifact(
        source,
        label="D7 item-21 seed-free readiness",
    )
    expected = _readiness_document(
        root,
        receipt,
        verify_current_implementation=False,
    )
    if document != expected or source != canonical_json_bytes(expected):
        raise QualificationContractError(
            "seed-free readiness differs from exact reconstruction"
        )
    introduction = _introduction_commit(
        root,
        repository_path=repository_path,
        expected_parent=receipt.introduction_commit,
        expected_source=source,
    )
    for path in _PRESEED_ABSENCE_PATHS:
        _require_path_absent_at_commit(
            root,
            receipt.introduction_commit,
            path,
        )
        _require_path_absent_at_commit(root, introduction, path)
    return _LoadedArtifact(repository_path, source, introduction)


def _successor_admission_spec(
    recorded: dict[str, object],
) -> dict[str, object]:
    components = _mapping(recorded["components"], label="admission components")
    generator_source = _mapping(
        recorded["generator_source"],
        label="admission generator source",
    )
    generator_family_id = generator_source.get("family_id")
    if generator_family_id != _GENERATOR_IDENTITY["family_id"]:
        raise QualificationContractError(
            "admission generator family differs from item-21 v0.1"
        )
    return {
        "schema_version": D7_ITEM21_SUCCESSOR_ADMISSION_SPEC_SCHEMA_VERSION,
        "admission_spec_id": "d7-spectral-moment-successor-admission-v0-1",
        "claim_ceiling": "level_0",
        "generator_family_id": generator_family_id,
        "historical_d6_admission": {
            "admission_spec_sha256": (
                "2e4aa2a272a38ed68b61f612d8a3a261cc6376f3d9a8097f5dce701a2c3f5aa4"
            ),
            "historical_bytes_mutated": False,
            "historical_d6_exact_admission_satisfied": False,
            "historical_d6_reinterpreted": False,
        },
        "reviewed_successor_bindings": {
            "construction_diversity_review": components[
                "construction_diversity_review"
            ],
            "successor_rebinding_review_contract": components[
                "successor_rebinding_review_contract"
            ],
            "stable_seed_free_execution_design": components[
                "seed_free_execution_design"
            ],
            "implementation_registry": components["implementation_registry"],
            "aggregation_application": components["aggregation_application"],
        },
        "requirements": {
            "construction_family_distinct": True,
            "implementation_distinct": True,
            "source_distinct": True,
            "seed_or_label_only_difference": False,
            "graph_axes_exact_carry_forward": True,
            "thresholds_exact_carry_forward": True,
            "successor_cells_and_stress_use_distinct_identities": True,
            "successor_structural_projection_matches_parent": True,
            "selection_identity_reuse_allowed": False,
            "core_and_loop_separate": True,
            "oracle_truth_is_not_kernel_input": True,
            "policy_override_allowed": False,
            "post_selection_exclusion_allowed": False,
            "full_coverage_required": True,
            "zero_abstention_required": True,
        },
        "admission_scope": {
            "family_only": True,
            "official_seed_values_bound": False,
            "seed_supply_claim_acquired": False,
            "supplier_invoked": False,
            "target_or_full_design_frozen": False,
            "launch_or_execution_authorized": False,
            "scientific_claim_eligible": False,
        },
    }


def _admission_document(
    root: Path,
    receipt: _LoadedArtifact,
    readiness: _LoadedArtifact,
    *,
    verify_current_implementation: bool,
) -> dict[str, object]:
    receipt_document = receipt.document
    recorded = _recorded_components(
        root,
        source_observation=_mapping(
            receipt_document["source_observation"],
            label="receipt source observation",
        ),
        verify_current_implementation=verify_current_implementation,
    )
    if verify_current_implementation:
        _current_code_side_execution_ingredients()
    specification = _successor_admission_spec(recorded)
    return {
        "schema_version": D7_ITEM21_REVIEWED_FAMILY_ADMISSION_SCHEMA_VERSION,
        "admission_id": "d7-item21-reviewed-successor-family-admission-v0-1",
        "artifact_role": "family-admission-receipt",
        "repository_path": (D7_ITEM21_REVIEWED_FAMILY_ADMISSION_REPOSITORY_PATH),
        "status": "scoped-successor-family-admitted-item22-not-started",
        "claim_ceiling": "level_0",
        "source_runtime_predecessor": _artifact_binding(
            receipt,
            schema_version=D7_ITEM21_SOURCE_RUNTIME_RECEIPT_SCHEMA_VERSION,
        ),
        "readiness_predecessor": _artifact_binding(
            readiness,
            schema_version=D7_ITEM21_SEED_FREE_READINESS_SCHEMA_VERSION,
        ),
        "successor_admission_spec": specification,
        "successor_admission_spec_sha256": canonical_json_sha256(specification),
        "decision": {
            "construction_diversity_reviewed": True,
            "successor_fulfillment_rule_reviewed": True,
            "source_runtime_receipt_verified": True,
            "seed_free_readiness_verified": True,
            "implementation_registry_bound": True,
            "aggregation_application_bound": True,
            "result_schema_bound": True,
            "historical_d6_exact_admission_satisfied": False,
            "historical_d6_reinterpreted": False,
            "family_admitted": True,
            "admission_is_scoped_to_named_successor": True,
            "official_seed_inventory_present": False,
            "seed_supply_claim_acquired": False,
            "supplier_invoked": False,
            "target_or_full_design_present": False,
            "freeze_or_launch_intent_present": False,
            "launch_descriptor_present": False,
            "execution_observed": False,
            "d7_state": "not_run",
            "d8_state": "not_run",
        },
        "review_provenance": {
            "repository_process_attested": True,
            "external_reviewer_identity_authenticated": False,
            "signed_external_timestamp_present": False,
            "canonical_bytes_alone_are_authority": False,
            "current_live_reobservation_required_before_item22": True,
            "current_source_tree_must_equal_item21_anchor": True,
            "versioned_current_source_reanchor_required_after_source_change": True,
        },
        "authority": {
            "confirmation_family_admitted": True,
            **_AUTHORITY_FALSE,
        },
    }


def build_d7_item21_reviewed_family_admission(
    repository_root: str | Path,
) -> bytes:
    """Build the scoped admission only from committed receipt and readiness."""

    root = _repository_root(repository_root)
    _require_clean(root)
    receipt = _load_source_receipt(root)
    readiness = _load_readiness(root, receipt)
    if _head(root) != readiness.introduction_commit:
        raise QualificationContractError(
            "admission must be issued from the readiness-only direct child"
        )
    destination = root / D7_ITEM21_REVIEWED_FAMILY_ADMISSION_REPOSITORY_PATH
    if destination.exists() or destination.is_symlink():
        raise QualificationContractError("family admission already exists")
    _verify_live_runtime(root, receipt)
    _require_live_paths_absent(root)
    return canonical_json_bytes(
        _admission_document(
            root,
            receipt,
            readiness,
            verify_current_implementation=True,
        )
    )


def issue_d7_item21_reviewed_family_admission(
    repository_root: str | Path,
) -> PersistedQualificationIdentity:
    root = _repository_root(repository_root)
    source = build_d7_item21_reviewed_family_admission(root)
    return _atomic_write_no_overwrite(
        root / D7_ITEM21_REVIEWED_FAMILY_ADMISSION_REPOSITORY_PATH,
        source,
        maximum_bytes=MAX_D7_ITEM21_ARTIFACT_BYTES,
        label="D7 item-21 reviewed family admission",
    )


def _load_admission(
    root: Path,
    receipt: _LoadedArtifact,
    readiness: _LoadedArtifact,
) -> _LoadedArtifact:
    repository_path = D7_ITEM21_REVIEWED_FAMILY_ADMISSION_REPOSITORY_PATH
    source = _read_worktree_artifact(root, repository_path)
    document = _parse_canonical_artifact(
        source,
        label="D7 item-21 reviewed family admission",
    )
    expected = _admission_document(
        root,
        receipt,
        readiness,
        verify_current_implementation=False,
    )
    if document != expected or source != canonical_json_bytes(expected):
        raise QualificationContractError(
            "reviewed family admission differs from exact reconstruction"
        )
    introduction = _introduction_commit(
        root,
        repository_path=repository_path,
        expected_parent=readiness.introduction_commit,
        expected_source=source,
    )
    for path in _PRESEED_ABSENCE_PATHS:
        _require_path_absent_at_commit(root, readiness.introduction_commit, path)
        _require_path_absent_at_commit(root, introduction, path)
    return _LoadedArtifact(repository_path, source, introduction)


@dataclass(frozen=True, slots=True, init=False)
class _LoadedD7Item21PositiveChain:
    repository_root: Path
    source_runtime_receipt: _LoadedArtifact
    seed_free_readiness: _LoadedArtifact
    reviewed_family_admission: _LoadedArtifact

    git_chronology_verified: ClassVar[bool] = True
    anchor_to_admission_source_tree_continuity_verified: ClassVar[bool] = True
    current_source_tree_verified: ClassVar[bool] = False
    issuance_runtime_attestation_embedded: ClassVar[bool] = True
    current_live_runtime_verified: ClassVar[bool] = False
    current_preseed_absence_verified: ClassVar[bool] = False
    reusable_authorization_capability_present: ClassVar[bool] = False
    seed_supply_claim_acquired: ClassVar[bool] = False
    supplier_invoked: ClassVar[bool] = False
    execution_observed: ClassVar[bool] = False
    scientific_claim_eligible: ClassVar[bool] = False

    def __init__(
        self,
        *,
        repository_root: Path,
        source_runtime_receipt: _LoadedArtifact,
        seed_free_readiness: _LoadedArtifact,
        reviewed_family_admission: _LoadedArtifact,
        _factory_token: object,
    ) -> None:
        if _factory_token is not _LOADED_CHAIN_FACTORY_TOKEN:
            raise QualificationContractError(
                "loaded item-21 chain requires the strict repository loader"
            )
        if (
            not isinstance(repository_root, Path)
            or type(source_runtime_receipt) is not _LoadedArtifact
            or type(seed_free_readiness) is not _LoadedArtifact
            or type(reviewed_family_admission) is not _LoadedArtifact
        ):
            raise TypeError("loaded item-21 chain inputs differ from exact types")
        object.__setattr__(self, "repository_root", repository_root)
        object.__setattr__(self, "source_runtime_receipt", source_runtime_receipt)
        object.__setattr__(self, "seed_free_readiness", seed_free_readiness)
        object.__setattr__(
            self,
            "reviewed_family_admission",
            reviewed_family_admission,
        )

    def __reduce__(self) -> NoReturn:
        raise TypeError("loaded item-21 chain is an in-process evidence snapshot")

    def __reduce_ex__(self, protocol: int) -> NoReturn:
        del protocol
        raise TypeError("loaded item-21 chain is an in-process evidence snapshot")

    def __copy__(self) -> NoReturn:
        raise TypeError("loaded item-21 chain cannot be copied")

    def __deepcopy__(self, memo: object) -> NoReturn:
        del memo
        raise TypeError("loaded item-21 chain cannot be copied")


def load_committed_d7_item21_positive_chain(
    repository_root: str | Path,
) -> _LoadedD7Item21PositiveChain:
    """Strictly load the three immutable commits without claiming live runtime."""

    root = _repository_root(repository_root)
    _require_clean(root)
    receipt = _load_source_receipt(root)
    readiness = _load_readiness(root, receipt)
    admission = _load_admission(root, receipt, readiness)
    head = _head(root)
    _require_ancestor(
        root, admission.introduction_commit, head, label="admission-to-HEAD"
    )
    return _LoadedD7Item21PositiveChain(
        repository_root=root,
        source_runtime_receipt=receipt,
        seed_free_readiness=readiness,
        reviewed_family_admission=admission,
        _factory_token=_LOADED_CHAIN_FACTORY_TOKEN,
    )


def _verify_live_runtime(root: Path, receipt: _LoadedArtifact) -> None:
    document = receipt.document
    lineage = _mapping(document["lineage"], label="source receipt lineage")
    source_commit = _commit(
        lineage["source_commit"],
        label="source receipt source_commit",
    )
    if (
        _source_inventory(
            root,
            source_commit,
            require_current_equality=True,
        )
        != document["source_observation"]
    ):
        raise QualificationContractError(
            "current source tree differs from the item-21 receipt"
        )
    expected_runtime = _runtime_document(
        root,
        require_installed_equality=True,
    )
    if expected_runtime != document["runtime_observation"]:
        raise QualificationContractError(
            "current runtime differs from the item-21 receipt"
        )


class _VerifiedD7Item21ReadyForSeedSupply:
    """Private point-in-time evidence snapshot, never an authorization capability."""

    __slots__ = ("_chain", "_sealed")

    source_runtime_verified: ClassVar[bool] = True
    current_source_tree_verified: ClassVar[bool] = True
    seed_free_readiness_verified: ClassVar[bool] = True
    reviewed_family_admission_verified: ClassVar[bool] = True
    confirmation_family_admitted: ClassVar[bool] = True
    current_preseed_absence_verified: ClassVar[bool] = True
    valid_only_while_source_tree_equals_item21_anchor: ClassVar[bool] = True
    point_in_time_observation_only: ClassVar[bool] = True
    freshness_retained_after_return: ClassVar[bool] = False
    canonical_origin_main_verified: ClassVar[bool] = False
    reusable_authorization_capability_present: ClassVar[bool] = False
    seed_supply_claim_acquired: ClassVar[bool] = False
    supplier_invoked: ClassVar[bool] = False
    official_seed_inventory_present: ClassVar[bool] = False
    execution_observed: ClassVar[bool] = False
    scientific_claim_eligible: ClassVar[bool] = False

    def __init__(
        self,
        chain: _LoadedD7Item21PositiveChain,
        *,
        _factory_token: object,
    ) -> None:
        if _factory_token is not _READY_HANDOFF_FACTORY_TOKEN:
            raise QualificationContractError(
                "verified item-21 snapshot requires current live reobservation"
            )
        if type(chain) is not _LoadedD7Item21PositiveChain:
            raise TypeError("chain must be the exact private loaded item-21 type")
        object.__setattr__(self, "_chain", chain)
        object.__setattr__(self, "_sealed", True)

    def __setattr__(self, name: str, value: object) -> None:
        if getattr(self, "_sealed", False):
            raise AttributeError("verified item-21 snapshot is immutable")
        object.__setattr__(self, name, value)

    @property
    def chain(self) -> _LoadedD7Item21PositiveChain:
        return self._chain

    def __reduce__(self) -> NoReturn:
        raise TypeError("verified item-21 snapshot is not serializable")

    def __reduce_ex__(self, protocol: int) -> NoReturn:
        del protocol
        raise TypeError("verified item-21 snapshot is not serializable")

    def __copy__(self) -> NoReturn:
        raise TypeError("verified item-21 snapshot cannot be copied")

    def __deepcopy__(self, memo: object) -> NoReturn:
        del memo
        raise TypeError("verified item-21 snapshot cannot be copied")


def verify_current_d7_item21_ready_for_seed_supply(
    repository_root: str | Path,
) -> _VerifiedD7Item21ReadyForSeedSupply:
    """Return non-authorizing live evidence; a future item-22 op must reverify."""

    chain = load_committed_d7_item21_positive_chain(repository_root)
    root = chain.repository_root
    _verify_live_runtime(root, chain.source_runtime_receipt)
    receipt_document = chain.source_runtime_receipt.document
    current_recorded = _recorded_components(
        root,
        source_observation=_mapping(
            receipt_document["source_observation"],
            label="receipt source observation",
        ),
        verify_current_implementation=True,
    )
    current_ingredients = _current_code_side_execution_ingredients()
    readiness_document = chain.seed_free_readiness.document
    if (
        current_recorded != readiness_document["recorded_inputs"]
        or current_ingredients != readiness_document["code_side_execution_ingredients"]
    ):
        raise QualificationContractError(
            "current item-21 code bindings differ from committed readiness"
        )
    _require_live_paths_absent(root)
    return _VerifiedD7Item21ReadyForSeedSupply(
        chain,
        _factory_token=_READY_HANDOFF_FACTORY_TOKEN,
    )
