"""Prepared, no-seed launch boundary for one frozen D0--D5 selection.

Preparation and execution are deliberately separate capabilities:

* :func:`prepare_selection_launch` verifies the exact protocol, freeze,
  source closure, and terminal-publication primitive before it persists a
  launch intent and then acquires and round-trips the sole store-local attempt
  claim.
* :func:`load_prepared_selection_launch` accepts only one exact descriptor
  identity.  Every repository, source, protocol, freeze, store, and claim path
  comes from that descriptor; the function has no store override, never
  creates a claim, and authorizes execution only when all four G artifacts are
  exact clean tracked blobs at one unchanged HEAD.

The descriptor is Level-0 chronology evidence.  Its one-shot boundary is the
named, trusted local store only.  It does not prove global, cross-store,
multi-host, deletion-resistant, or hostile-operator one-shot execution, and it
does not observe or authorize selection, subject, semantic, or topology data.
"""

from __future__ import annotations

import ctypes
import hashlib
import os
import stat
import subprocess
import sys
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING, ClassVar

from spirallens.core.canonical import (
    CanonicalJsonError,
    canonical_json_bytes,
    canonical_json_sha256,
    parse_canonical_json,
)

from .common import QualificationContractError
from .freeze import (
    _HISTORICAL_SOURCE_RELOAD_CAPABILITY,
    MAX_SELECTION_CHRONOLOGY_ARTIFACT_BYTES,
    MAX_SELECTION_TERMINAL_ARTIFACT_BYTES,
    SELECTION_ATTEMPT_CLAIM_SUFFIX,
    SELECTION_TERMINAL_ARTIFACT_FILENAME,
    SELECTION_TERMINAL_CONSUMPTION_FILENAME,
    SELECTION_TERMINAL_MANIFEST_FILENAME,
    PersistedSelectionIdentity,
    PersistedSelectionTerminalIdentity,
    SelectionAttemptClaimArtifact,
    SelectionConsumptionArtifact,
    SelectionExecutionStartArtifact,
    SelectionFailedAttemptArtifact,
    SelectionFreezeArtifact,
    SelectionLaunchIntentBinding,
    SelectionTerminalManifestArtifact,
    TerminalAttemptArtifactKind,
    claim_selection_attempt,
    load_selection_attempt_claim,
    load_selection_freeze,
    load_terminal_selection_consumption,
    selection_attempt_claim_path,
    selection_attempt_key_sha256,
    selection_execution_start_path,
    selection_freeze_store_path,
    terminal_selection_transaction_path,
    validate_persisted_selection_attempt_claim,
)
from .persistence import LoadedQualificationProtocol, load_qualification_protocol
from .preparation import (
    LoadedClosedD0D5PreseedReadinessArtifact,
    load_protocol_preseed_readiness_artifact,
    validate_closed_d0_d5_selection_protocol,
)
from .protocol import PreseedReadinessBinding
from .source_binding import (
    ModuleSourceReceipt,
    QualificationSourceBindingReceipt,
    QualificationSourceBindingSummary,
    ReferentSourceReceipt,
    RegistrySourceReceipt,
    verify_protocol_source_binding,
    verify_protocol_source_binding_successor,
)

if TYPE_CHECKING:
    from .contracts import QualificationResult

PREPARED_SELECTION_LAUNCH_DESCRIPTOR_SCHEMA_VERSION = (
    "spirallens.prepared-selection-launch-descriptor.v0.3"
)
PREPARED_SELECTION_LAUNCH_INTENT_SCHEMA_VERSION = (
    "spirallens.prepared-selection-launch-intent.v0.1"
)
SELECTION_LAUNCH_AUTHORIZATION_SCHEMA_VERSION = (
    "spirallens.selection-launch-authorization.v0.1"
)
EXCLUSIVE_TERMINAL_PUBLICATION_CAPABILITY_SCHEMA_VERSION = (
    "spirallens.exclusive-terminal-publication-capability.v0.1"
)
MAX_PREPARED_SELECTION_LAUNCH_DESCRIPTOR_BYTES = 256 * 1024
SELECTION_LAUNCH_INTENT_SUFFIX = ".selection-launch-intent.json"

_SHA256_CHARACTERS = frozenset("0123456789abcdef")
_SLUG_CHARACTERS = frozenset("abcdefghijklmnopqrstuvwxyz0123456789._-")


def _mapping(value: object, *, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping) or any(not isinstance(key, str) for key in value):
        raise QualificationContractError(f"{label} must be a string-keyed mapping")
    return value


def _exact_keys(
    value: Mapping[str, object],
    expected: frozenset[str],
    *,
    label: str,
) -> None:
    actual = set(value)
    if actual != set(expected):
        raise QualificationContractError(
            f"{label} fields differ from the contract: "
            f"missing={sorted(set(expected) - actual)}, "
            f"unknown={sorted(actual - set(expected))}"
        )


def _string(value: object, *, label: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise QualificationContractError(f"{label} must be a non-empty trimmed string")
    return value


def _slug(value: object, *, label: str) -> str:
    result = _string(value, label=label)
    if (
        len(result) > 128
        or result[0] not in frozenset("abcdefghijklmnopqrstuvwxyz0123456789")
        or any(character not in _SLUG_CHARACTERS for character in result)
    ):
        raise QualificationContractError(f"{label} must be a lowercase portable slug")
    return result


def _sha256(value: object, *, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in _SHA256_CHARACTERS for character in value)
    ):
        raise QualificationContractError(f"{label} must be a lowercase SHA-256 digest")
    return value


def _plain_int(value: object, *, label: str, minimum: int) -> int:
    if type(value) is not int or value < minimum:
        raise QualificationContractError(
            f"{label} must be an integer of at least {minimum}"
        )
    return value


def _constant(value: object, expected: object, *, label: str) -> None:
    if type(value) is not type(expected) or value != expected:
        raise QualificationContractError(f"{label} must equal {expected!r}")


def _absolute(path: str | Path) -> Path:
    return Path(os.path.abspath(Path(path)))


def _absolute_path_string(value: object, *, label: str) -> str:
    result = _string(value, label=label)
    path = Path(result)
    if not path.is_absolute() or str(_absolute(path)) != result:
        raise QualificationContractError(f"{label} must be a normalized absolute path")
    return result


def _require_real_directory(path: Path, *, label: str) -> Path:
    if not path.is_absolute():
        raise QualificationContractError(f"{label} must be absolute")
    if path.is_symlink():
        raise QualificationContractError(f"{label} must not be a symbolic link")
    try:
        resolved = path.resolve(strict=True)
    except OSError as error:
        raise QualificationContractError(f"{label} does not exist: {path}") from error
    if resolved != path or not path.is_dir():
        raise QualificationContractError(
            f"{label} must be an existing real directory: {path}"
        )
    return path


def _require_real_file(path: Path, *, label: str) -> Path:
    if not path.is_absolute():
        raise QualificationContractError(f"{label} must be absolute")
    if path.is_symlink():
        raise QualificationContractError(f"{label} must not be a symbolic link")
    try:
        resolved = path.resolve(strict=True)
        metadata = path.stat()
    except OSError as error:
        raise QualificationContractError(f"{label} does not exist: {path}") from error
    if resolved != path or not stat.S_ISREG(metadata.st_mode):
        raise QualificationContractError(
            f"{label} must be an existing real regular file: {path}"
        )
    return path


def _require_absent(path: Path, *, label: str) -> None:
    if path.exists() or path.is_symlink():
        raise QualificationContractError(f"{label} already exists: {path}")


def _resolve_repository_head(repository: Path, *, label: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repository), "rev-parse", "--verify", "HEAD^{commit}"],
        check=False,
        capture_output=True,
        text=True,
    )
    head = completed.stdout.strip()
    if (
        completed.returncode != 0
        or len(head) != 40
        or any(character not in _SHA256_CHARACTERS for character in head)
    ):
        raise QualificationContractError(f"cannot resolve {label} HEAD")
    return head


def _require_tracked_clean_head_artifact(
    repository: Path,
    path: Path,
    *,
    expected_sha256: str,
    label: str,
    expected_head_commit: str | None = None,
) -> None:
    """Bind a frozen artifact to one clean tracked current-HEAD blob."""

    try:
        relative = path.relative_to(repository).as_posix()
    except ValueError as error:
        raise QualificationContractError(
            f"{label} must resolve inside repository_root"
        ) from error

    def git(arguments: list[str]) -> bytes:
        completed = subprocess.run(
            ["git", "-C", str(repository), *arguments],
            check=False,
            capture_output=True,
        )
        if completed.returncode != 0:
            raise QualificationContractError(
                f"{label} failed tracked HEAD verification"
            )
        return completed.stdout

    git(["ls-files", "--error-unmatch", "--", relative])
    status = git(
        [
            "status",
            "--porcelain=v1",
            "-z",
            "--untracked-files=all",
            "--",
            relative,
        ]
    )
    if status:
        raise QualificationContractError(
            f"{label} has a tracked or untracked worktree difference"
        )
    if expected_head_commit is not None:
        current_head = git(["rev-parse", "HEAD"]).decode("ascii").strip()
        if current_head != expected_head_commit:
            raise QualificationContractError(
                f"{label} HEAD changed during tracked verification"
            )
    source = path.read_bytes()
    head_ref = "HEAD" if expected_head_commit is None else expected_head_commit
    head_blob = git(["show", f"{head_ref}:{relative}"])
    if (
        hashlib.sha256(source).hexdigest() != expected_sha256
        or hashlib.sha256(head_blob).hexdigest() != expected_sha256
        or source != head_blob
    ):
        raise QualificationContractError(
            f"{label} differs from its exact protocol-bound clean HEAD blob"
        )


def _require_tracked_clean_unchanged_artifact(
    repository: Path,
    path: Path,
    *,
    expected_sha256: str,
    authorized_head_commit: str,
    current_head_commit: str,
    label: str,
) -> None:
    """Require one G blob to be identical at authorization and current HEAD."""

    try:
        relative = path.relative_to(repository).as_posix()
    except ValueError as error:
        raise QualificationContractError(
            f"{label} must resolve inside repository_root"
        ) from error

    def git(arguments: list[str]) -> bytes:
        completed = subprocess.run(
            ["git", "-C", str(repository), *arguments],
            check=False,
            capture_output=True,
        )
        if completed.returncode != 0:
            raise QualificationContractError(
                f"{label} failed terminal tracked-blob verification"
            )
        return completed.stdout

    git(["ls-files", "--error-unmatch", "--", relative])
    status = git(
        [
            "status",
            "--porcelain=v1",
            "-z",
            "--untracked-files=all",
            "--",
            relative,
        ]
    )
    if status:
        raise QualificationContractError(
            f"{label} has a tracked or untracked worktree difference"
        )
    observed_head = (
        git(["rev-parse", "--verify", "HEAD^{commit}"]).decode("ascii").strip()
    )
    if observed_head != current_head_commit:
        raise QualificationContractError(
            f"{label} HEAD changed during terminal tracked verification"
        )
    source = path.read_bytes()
    authorized_blob = git(["show", f"{authorized_head_commit}:{relative}"])
    current_blob = git(["show", f"{current_head_commit}:{relative}"])
    if (
        hashlib.sha256(source).hexdigest() != expected_sha256
        or hashlib.sha256(authorized_blob).hexdigest() != expected_sha256
        or hashlib.sha256(current_blob).hexdigest() != expected_sha256
        or source != authorized_blob
        or source != current_blob
    ):
        raise QualificationContractError(
            f"{label} changed after its committed G authorization"
        )


def _require_path_absent_at_commit(
    repository: Path,
    path: Path,
    *,
    commit: str,
    label: str,
) -> None:
    try:
        relative = path.relative_to(repository).as_posix()
    except ValueError as error:
        raise QualificationContractError(
            f"{label} must resolve inside repository_root"
        ) from error
    completed = subprocess.run(
        [
            "git",
            "-C",
            str(repository),
            "ls-tree",
            "-z",
            "--full-name",
            commit,
            "--",
            relative,
        ],
        check=False,
        capture_output=True,
    )
    if completed.returncode != 0:
        raise QualificationContractError(
            f"{label} failed authorized-commit absence verification"
        )
    if completed.stdout:
        raise QualificationContractError(
            f"{label} already existed at committed G authorization HEAD"
        )


@dataclass(frozen=True, slots=True)
class ExclusiveTerminalPublicationCapability:
    """Read-only resolution receipt for the primitive used by terminal publish.

    Merely resolving a callable libc symbol cannot exercise its filesystem
    semantics without mutation.  The negative fields below keep that
    distinction explicit.
    """

    platform_id: str
    primitive_id: str
    no_replace_flag: int
    schema_version: str = EXCLUSIVE_TERMINAL_PUBLICATION_CAPABILITY_SCHEMA_VERSION
    role: str = "exclusive_terminal_publication_preflight"
    read_only_probe: bool = True
    symbol_resolved: bool = True
    primitive_invoked: bool = False
    filesystem_mutated: bool = False
    selection_execution_started: bool = False
    selection_values_observed: bool = False
    operational_publication_proved: bool = False

    _ROOT_KEYS: ClassVar[frozenset[str]] = frozenset(
        {
            "schema_version",
            "role",
            "platform_id",
            "primitive_id",
            "no_replace_flag",
            "read_only_probe",
            "symbol_resolved",
            "primitive_invoked",
            "filesystem_mutated",
            "selection_execution_started",
            "selection_values_observed",
            "operational_publication_proved",
        }
    )

    def __post_init__(self) -> None:
        _constant(
            self.schema_version,
            EXCLUSIVE_TERMINAL_PUBLICATION_CAPABILITY_SCHEMA_VERSION,
            label="terminal capability schema_version",
        )
        _constant(
            self.role,
            "exclusive_terminal_publication_preflight",
            label="terminal capability role",
        )
        expected = {
            "darwin": ("renameatx_np", 0x00000004),
            "linux": ("renameat2", 0x00000001),
        }
        if self.platform_id not in expected:
            raise QualificationContractError(
                "terminal capability platform_id is unsupported"
            )
        if (self.primitive_id, self.no_replace_flag) != expected[self.platform_id]:
            raise QualificationContractError(
                "terminal capability primitive differs from the platform contract"
            )
        for name in ("read_only_probe", "symbol_resolved"):
            _constant(getattr(self, name), True, label=f"terminal capability {name}")
        for name in (
            "primitive_invoked",
            "filesystem_mutated",
            "selection_execution_started",
            "selection_values_observed",
            "operational_publication_proved",
        ):
            _constant(getattr(self, name), False, label=f"terminal capability {name}")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "role": self.role,
            "platform_id": self.platform_id,
            "primitive_id": self.primitive_id,
            "no_replace_flag": self.no_replace_flag,
            "read_only_probe": self.read_only_probe,
            "symbol_resolved": self.symbol_resolved,
            "primitive_invoked": self.primitive_invoked,
            "filesystem_mutated": self.filesystem_mutated,
            "selection_execution_started": self.selection_execution_started,
            "selection_values_observed": self.selection_values_observed,
            "operational_publication_proved": self.operational_publication_proved,
        }

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_dict())

    @property
    def canonical_sha256(self) -> str:
        return canonical_json_sha256(self.to_dict())

    @classmethod
    def from_dict(cls, value: object) -> ExclusiveTerminalPublicationCapability:
        document = _mapping(value, label="terminal publication capability")
        _exact_keys(
            document,
            cls._ROOT_KEYS,
            label="terminal publication capability",
        )
        for name, expected in (
            (
                "schema_version",
                EXCLUSIVE_TERMINAL_PUBLICATION_CAPABILITY_SCHEMA_VERSION,
            ),
            ("role", "exclusive_terminal_publication_preflight"),
            ("read_only_probe", True),
            ("symbol_resolved", True),
            ("primitive_invoked", False),
            ("filesystem_mutated", False),
            ("selection_execution_started", False),
            ("selection_values_observed", False),
            ("operational_publication_proved", False),
        ):
            _constant(
                document[name],
                expected,
                label=f"terminal capability {name}",
            )
        platform_id = _string(
            document["platform_id"],
            label="terminal capability platform_id",
        )
        primitive_id = _string(
            document["primitive_id"],
            label="terminal capability primitive_id",
        )
        return cls(
            platform_id=platform_id,
            primitive_id=primitive_id,
            no_replace_flag=_plain_int(
                document["no_replace_flag"],
                label="terminal capability no_replace_flag",
                minimum=1,
            ),
        )


def probe_exclusive_terminal_publication_capability(
    *,
    platform_id: str | None = None,
    libc: object | None = None,
) -> ExclusiveTerminalPublicationCapability:
    """Resolve, but never invoke, the terminal no-replace rename primitive.

    ``platform_id`` and ``libc`` exist for deterministic unit tests.  Official
    preparation and execution call this function with neither override.
    """

    observed_platform = sys.platform if platform_id is None else platform_id
    if observed_platform == "darwin":
        normalized_platform = "darwin"
        primitive_id = "renameatx_np"
        no_replace_flag = 0x00000004
    elif observed_platform.startswith("linux"):
        normalized_platform = "linux"
        primitive_id = "renameat2"
        no_replace_flag = 0x00000001
    else:
        raise QualificationContractError(
            "exclusive terminal-directory rename is unsupported on this platform"
        )
    if libc is None:
        try:
            libc = ctypes.CDLL(None, use_errno=True)
        except OSError as error:
            raise QualificationContractError(
                "cannot load the process C library for terminal publication"
            ) from error
    try:
        primitive = getattr(libc, primitive_id)
    except AttributeError as error:
        raise QualificationContractError(
            "exclusive terminal-directory rename is unavailable"
        ) from error
    if not callable(primitive):
        raise QualificationContractError(
            "exclusive terminal-directory rename symbol is not callable"
        )
    return ExclusiveTerminalPublicationCapability(
        platform_id=normalized_platform,
        primitive_id=primitive_id,
        no_replace_flag=no_replace_flag,
    )


@dataclass(frozen=True, slots=True)
class PreparedSelectionLaunchIntentArtifact:
    """Canonical checked launch intent published before the attempt claim."""

    intent_id: str
    repository_root: str
    protocol_path: str
    protocol_source_sha256: str
    protocol_canonical_sha256: str
    freeze_path: str
    freeze_source_sha256: str
    freeze_canonical_sha256: str
    attempt_store_path: str
    attempt_key_sha256: str
    attempt_claim_path: str
    claim_id: str
    engine_commit: str
    preseed_readiness: PreseedReadinessBinding
    source_readiness_summary_sha256: str
    terminal_publication_capability_sha256: str
    schema_version: str = PREPARED_SELECTION_LAUNCH_INTENT_SCHEMA_VERSION
    role: str = "prepared_calibration_selection_launch_intent"
    chronology_claim: str = "official-process-attested"
    launch_preconditions_verified: bool = True
    intent_published_before_attempt_claim: bool = True
    attempt_claim_created: bool = False
    selection_execution_started: bool = False
    selection_values_observed: bool = False
    trusted_store_operator_required: bool = True
    global_one_shot_proved: bool = False
    cross_store_uniqueness_proved: bool = False
    hostile_local_mutation_resistant: bool = False

    _ROOT_KEYS: ClassVar[frozenset[str]] = frozenset(
        {
            "schema_version",
            "intent_id",
            "role",
            "chronology_claim",
            "repository_root",
            "protocol_path",
            "protocol_source_sha256",
            "protocol_canonical_sha256",
            "freeze_path",
            "freeze_source_sha256",
            "freeze_canonical_sha256",
            "attempt_store_path",
            "attempt_key_sha256",
            "attempt_claim_path",
            "claim_id",
            "engine_commit",
            "preseed_readiness",
            "source_readiness_summary_sha256",
            "terminal_publication_capability_sha256",
            "launch_preconditions_verified",
            "intent_published_before_attempt_claim",
            "attempt_claim_created",
            "selection_execution_started",
            "selection_values_observed",
            "trusted_store_operator_required",
            "global_one_shot_proved",
            "cross_store_uniqueness_proved",
            "hostile_local_mutation_resistant",
        }
    )

    def __post_init__(self) -> None:
        _constant(
            self.schema_version,
            PREPARED_SELECTION_LAUNCH_INTENT_SCHEMA_VERSION,
            label="launch intent schema_version",
        )
        _slug(self.intent_id, label="launch intent intent_id")
        _constant(
            self.role,
            "prepared_calibration_selection_launch_intent",
            label="launch intent role",
        )
        _constant(
            self.chronology_claim,
            "official-process-attested",
            label="launch intent chronology_claim",
        )
        for name in (
            "repository_root",
            "protocol_path",
            "freeze_path",
            "attempt_store_path",
            "attempt_claim_path",
        ):
            _absolute_path_string(
                getattr(self, name),
                label=f"launch intent {name}",
            )
        for name in (
            "protocol_source_sha256",
            "protocol_canonical_sha256",
            "freeze_source_sha256",
            "freeze_canonical_sha256",
            "attempt_key_sha256",
            "source_readiness_summary_sha256",
            "terminal_publication_capability_sha256",
        ):
            _sha256(getattr(self, name), label=f"launch intent {name}")
        if (
            not isinstance(self.engine_commit, str)
            or len(self.engine_commit) != 40
            or any(
                character not in _SHA256_CHARACTERS for character in self.engine_commit
            )
        ):
            raise QualificationContractError(
                "launch intent engine_commit must be a lowercase "
                "40-character Git commit"
            )
        _slug(self.claim_id, label="launch intent claim_id")
        if not isinstance(self.preseed_readiness, PreseedReadinessBinding):
            raise TypeError(
                "launch intent preseed_readiness must be a PreseedReadinessBinding"
            )
        if self.preseed_readiness.engine_commit != self.engine_commit:
            raise QualificationContractError(
                "launch intent preseed readiness differs from engine_commit"
            )
        if self.protocol_source_sha256 != self.protocol_canonical_sha256:
            raise QualificationContractError(
                "launch intent must bind exact canonical protocol bytes"
            )
        if self.freeze_source_sha256 != self.freeze_canonical_sha256:
            raise QualificationContractError(
                "launch intent must bind exact canonical freeze bytes"
            )
        expected_claim_path = (
            Path(self.attempt_store_path)
            / f"{self.attempt_key_sha256}{SELECTION_ATTEMPT_CLAIM_SUFFIX}"
        )
        if Path(self.attempt_claim_path) != expected_claim_path:
            raise QualificationContractError(
                "launch intent claim path differs from its fixed store/key"
            )
        for name in (
            "launch_preconditions_verified",
            "intent_published_before_attempt_claim",
            "trusted_store_operator_required",
        ):
            _constant(getattr(self, name), True, label=f"launch intent {name}")
        for name in (
            "attempt_claim_created",
            "selection_execution_started",
            "selection_values_observed",
            "global_one_shot_proved",
            "cross_store_uniqueness_proved",
            "hostile_local_mutation_resistant",
        ):
            _constant(getattr(self, name), False, label=f"launch intent {name}")
        if len(self.canonical_bytes) > MAX_SELECTION_CHRONOLOGY_ARTIFACT_BYTES:
            raise QualificationContractError(
                "launch intent exceeds the fixed chronology byte cap"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "intent_id": self.intent_id,
            "role": self.role,
            "chronology_claim": self.chronology_claim,
            "repository_root": self.repository_root,
            "protocol_path": self.protocol_path,
            "protocol_source_sha256": self.protocol_source_sha256,
            "protocol_canonical_sha256": self.protocol_canonical_sha256,
            "freeze_path": self.freeze_path,
            "freeze_source_sha256": self.freeze_source_sha256,
            "freeze_canonical_sha256": self.freeze_canonical_sha256,
            "attempt_store_path": self.attempt_store_path,
            "attempt_key_sha256": self.attempt_key_sha256,
            "attempt_claim_path": self.attempt_claim_path,
            "claim_id": self.claim_id,
            "engine_commit": self.engine_commit,
            "preseed_readiness": self.preseed_readiness.to_dict(),
            "source_readiness_summary_sha256": (self.source_readiness_summary_sha256),
            "terminal_publication_capability_sha256": (
                self.terminal_publication_capability_sha256
            ),
            "launch_preconditions_verified": self.launch_preconditions_verified,
            "intent_published_before_attempt_claim": (
                self.intent_published_before_attempt_claim
            ),
            "attempt_claim_created": self.attempt_claim_created,
            "selection_execution_started": self.selection_execution_started,
            "selection_values_observed": self.selection_values_observed,
            "trusted_store_operator_required": self.trusted_store_operator_required,
            "global_one_shot_proved": self.global_one_shot_proved,
            "cross_store_uniqueness_proved": self.cross_store_uniqueness_proved,
            "hostile_local_mutation_resistant": (self.hostile_local_mutation_resistant),
        }

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_dict())

    @property
    def canonical_sha256(self) -> str:
        return canonical_json_sha256(self.to_dict())

    @classmethod
    def from_dict(cls, value: object) -> PreparedSelectionLaunchIntentArtifact:
        document = _mapping(value, label="prepared selection launch intent")
        _exact_keys(
            document,
            cls._ROOT_KEYS,
            label="prepared selection launch intent",
        )
        constants = {
            "schema_version": PREPARED_SELECTION_LAUNCH_INTENT_SCHEMA_VERSION,
            "role": "prepared_calibration_selection_launch_intent",
            "chronology_claim": "official-process-attested",
            "launch_preconditions_verified": True,
            "intent_published_before_attempt_claim": True,
            "attempt_claim_created": False,
            "selection_execution_started": False,
            "selection_values_observed": False,
            "trusted_store_operator_required": True,
            "global_one_shot_proved": False,
            "cross_store_uniqueness_proved": False,
            "hostile_local_mutation_resistant": False,
        }
        for name, expected in constants.items():
            _constant(
                document[name],
                expected,
                label=f"launch intent {name}",
            )
        return cls(
            intent_id=_slug(
                document["intent_id"],
                label="launch intent intent_id",
            ),
            repository_root=_absolute_path_string(
                document["repository_root"],
                label="launch intent repository_root",
            ),
            protocol_path=_absolute_path_string(
                document["protocol_path"],
                label="launch intent protocol_path",
            ),
            protocol_source_sha256=_sha256(
                document["protocol_source_sha256"],
                label="launch intent protocol_source_sha256",
            ),
            protocol_canonical_sha256=_sha256(
                document["protocol_canonical_sha256"],
                label="launch intent protocol_canonical_sha256",
            ),
            freeze_path=_absolute_path_string(
                document["freeze_path"],
                label="launch intent freeze_path",
            ),
            freeze_source_sha256=_sha256(
                document["freeze_source_sha256"],
                label="launch intent freeze_source_sha256",
            ),
            freeze_canonical_sha256=_sha256(
                document["freeze_canonical_sha256"],
                label="launch intent freeze_canonical_sha256",
            ),
            attempt_store_path=_absolute_path_string(
                document["attempt_store_path"],
                label="launch intent attempt_store_path",
            ),
            attempt_key_sha256=_sha256(
                document["attempt_key_sha256"],
                label="launch intent attempt_key_sha256",
            ),
            attempt_claim_path=_absolute_path_string(
                document["attempt_claim_path"],
                label="launch intent attempt_claim_path",
            ),
            claim_id=_slug(document["claim_id"], label="launch intent claim_id"),
            engine_commit=_string(
                document["engine_commit"],
                label="launch intent engine_commit",
            ),
            preseed_readiness=PreseedReadinessBinding.from_dict(
                document["preseed_readiness"]
            ),
            source_readiness_summary_sha256=_sha256(
                document["source_readiness_summary_sha256"],
                label="launch intent source_readiness_summary_sha256",
            ),
            terminal_publication_capability_sha256=_sha256(
                document["terminal_publication_capability_sha256"],
                label="launch intent terminal_publication_capability_sha256",
            ),
        )


@dataclass(frozen=True, slots=True)
class LoadedPreparedSelectionLaunchIntent:
    """One exact canonical launch intent loaded from its fixed local store."""

    artifact: PreparedSelectionLaunchIntentArtifact
    binding: SelectionLaunchIntentBinding
    source_bytes: bytes

    def __post_init__(self) -> None:
        if not isinstance(self.artifact, PreparedSelectionLaunchIntentArtifact):
            raise TypeError("artifact must be a PreparedSelectionLaunchIntentArtifact")
        if not isinstance(self.binding, SelectionLaunchIntentBinding):
            raise TypeError("binding must be a SelectionLaunchIntentBinding")
        if (
            self.source_bytes != self.artifact.canonical_bytes
            or self.binding.source_sha256 != self.artifact.canonical_sha256
            or self.binding.canonical_sha256 != self.artifact.canonical_sha256
            or self.binding.byte_count != len(self.source_bytes)
        ):
            raise QualificationContractError(
                "loaded launch intent differs from its exact binding"
            )


@dataclass(frozen=True, slots=True)
class PreparedSelectionLaunchDescriptor:
    """Canonical launch descriptor binding every mutable launch pathname."""

    descriptor_id: str
    repository_root: str
    registry_path: str
    referent_path: str
    protocol_path: str
    protocol_id: str
    protocol_source_sha256: str
    protocol_canonical_sha256: str
    freeze_path: str
    freeze_id: str
    freeze_source_sha256: str
    freeze_canonical_sha256: str
    attempt_store_path: str
    attempt_key_sha256: str
    attempt_claim_path: str
    claim_id: str
    attempt_claim_source_sha256: str
    attempt_claim_canonical_sha256: str
    attempt_claim_byte_count: int
    launch_intent: SelectionLaunchIntentBinding
    engine_commit: str
    preseed_readiness: PreseedReadinessBinding
    source_readiness: QualificationSourceBindingSummary
    source_readiness_summary_sha256: str
    terminal_publication_capability: ExclusiveTerminalPublicationCapability
    terminal_publication_capability_sha256: str
    schema_version: str = PREPARED_SELECTION_LAUNCH_DESCRIPTOR_SCHEMA_VERSION
    role: str = "prepared_calibration_selection_launch"
    claim_ceiling: str = "level_0"
    uniqueness_scope: str = "descriptor_bound_store_only"
    path_binding_scope: str = "absolute_local_paths"
    attempt_claim_preacquired: bool = True
    execution_may_create_attempt_claim: bool = False
    attempt_store_override_authorized: bool = False
    trusted_store_operator_required: bool = True
    global_one_shot_proved: bool = False
    cross_store_uniqueness_proved: bool = False
    multi_host_uniqueness_proved: bool = False
    cross_worktree_portable: bool = False
    cross_machine_portable: bool = False
    store_deletion_resistant: bool = False
    hostile_local_mutation_resistant: bool = False
    exclusive_terminal_publication_preflight_verified: bool = True
    exclusive_terminal_publication_operationally_proved: bool = False
    selection_execution_started: bool = False
    selection_values_observed: bool = False
    scientific_claim_eligible: bool = False
    subject_access_authorized: bool = False

    _ROOT_KEYS: ClassVar[frozenset[str]] = frozenset(
        {
            "schema_version",
            "descriptor_id",
            "role",
            "claim_ceiling",
            "repository_root",
            "registry_path",
            "referent_path",
            "protocol_path",
            "protocol_id",
            "protocol_source_sha256",
            "protocol_canonical_sha256",
            "freeze_path",
            "freeze_id",
            "freeze_source_sha256",
            "freeze_canonical_sha256",
            "attempt_store_path",
            "attempt_key_sha256",
            "attempt_claim_path",
            "claim_id",
            "attempt_claim_source_sha256",
            "attempt_claim_canonical_sha256",
            "attempt_claim_byte_count",
            "launch_intent",
            "engine_commit",
            "preseed_readiness",
            "source_readiness",
            "source_readiness_summary_sha256",
            "terminal_publication_capability",
            "terminal_publication_capability_sha256",
            "uniqueness_scope",
            "path_binding_scope",
            "attempt_claim_preacquired",
            "execution_may_create_attempt_claim",
            "attempt_store_override_authorized",
            "trusted_store_operator_required",
            "global_one_shot_proved",
            "cross_store_uniqueness_proved",
            "multi_host_uniqueness_proved",
            "cross_worktree_portable",
            "cross_machine_portable",
            "store_deletion_resistant",
            "hostile_local_mutation_resistant",
            "exclusive_terminal_publication_preflight_verified",
            "exclusive_terminal_publication_operationally_proved",
            "selection_execution_started",
            "selection_values_observed",
            "scientific_claim_eligible",
            "subject_access_authorized",
        }
    )

    def __post_init__(self) -> None:
        _constant(
            self.schema_version,
            PREPARED_SELECTION_LAUNCH_DESCRIPTOR_SCHEMA_VERSION,
            label="launch descriptor schema_version",
        )
        _slug(self.descriptor_id, label="launch descriptor descriptor_id")
        _constant(
            self.role,
            "prepared_calibration_selection_launch",
            label="launch descriptor role",
        )
        _constant(
            self.claim_ceiling,
            "level_0",
            label="launch descriptor claim_ceiling",
        )
        for name in (
            "repository_root",
            "registry_path",
            "referent_path",
            "protocol_path",
            "freeze_path",
            "attempt_store_path",
            "attempt_claim_path",
        ):
            _absolute_path_string(
                getattr(self, name),
                label=f"launch descriptor {name}",
            )
        for name in ("protocol_id", "freeze_id", "claim_id"):
            _slug(getattr(self, name), label=f"launch descriptor {name}")
        for name in (
            "protocol_source_sha256",
            "protocol_canonical_sha256",
            "freeze_source_sha256",
            "freeze_canonical_sha256",
            "attempt_key_sha256",
            "attempt_claim_source_sha256",
            "attempt_claim_canonical_sha256",
            "engine_commit",
            "source_readiness_summary_sha256",
            "terminal_publication_capability_sha256",
        ):
            value = getattr(self, name)
            if name == "engine_commit":
                if (
                    not isinstance(value, str)
                    or len(value) != 40
                    or any(character not in _SHA256_CHARACTERS for character in value)
                ):
                    raise QualificationContractError(
                        "launch descriptor engine_commit must be a lowercase "
                        "40-character Git commit"
                    )
            else:
                _sha256(value, label=f"launch descriptor {name}")
        _plain_int(
            self.attempt_claim_byte_count,
            label="launch descriptor attempt_claim_byte_count",
            minimum=1,
        )
        if self.attempt_claim_byte_count > MAX_SELECTION_CHRONOLOGY_ARTIFACT_BYTES:
            raise QualificationContractError(
                "launch descriptor claim byte count exceeds the chronology cap"
            )
        if not isinstance(self.launch_intent, SelectionLaunchIntentBinding):
            raise TypeError("launch_intent must be a SelectionLaunchIntentBinding")
        if not isinstance(
            self.preseed_readiness,
            PreseedReadinessBinding,
        ):
            raise TypeError("preseed_readiness must be a PreseedReadinessBinding")
        if not isinstance(
            self.source_readiness,
            QualificationSourceBindingSummary,
        ):
            raise TypeError(
                "source_readiness must be a QualificationSourceBindingSummary"
            )
        if not isinstance(
            self.terminal_publication_capability,
            ExclusiveTerminalPublicationCapability,
        ):
            raise TypeError(
                "terminal_publication_capability must be an "
                "ExclusiveTerminalPublicationCapability"
            )
        if (
            self.source_readiness_summary_sha256
            != self.source_readiness.canonical_sha256
        ):
            raise QualificationContractError(
                "launch descriptor source-readiness digest differs from its summary"
            )
        if (
            self.terminal_publication_capability_sha256
            != self.terminal_publication_capability.canonical_sha256
        ):
            raise QualificationContractError(
                "launch descriptor capability digest differs from its receipt"
            )
        if self.source_readiness.engine_commit != self.engine_commit:
            raise QualificationContractError(
                "launch descriptor source readiness differs from engine_commit"
            )
        if self.preseed_readiness.engine_commit != self.engine_commit:
            raise QualificationContractError(
                "launch descriptor preseed readiness differs from engine_commit"
            )
        if self.protocol_source_sha256 != self.protocol_canonical_sha256:
            raise QualificationContractError(
                "launch descriptor must bind exact canonical protocol bytes"
            )
        if self.freeze_source_sha256 != self.freeze_canonical_sha256:
            raise QualificationContractError(
                "launch descriptor must bind exact canonical freeze bytes"
            )
        if self.attempt_claim_source_sha256 != self.attempt_claim_canonical_sha256:
            raise QualificationContractError(
                "launch descriptor must bind exact canonical claim bytes"
            )
        store_path = Path(self.attempt_store_path)
        claim_path = Path(self.attempt_claim_path)
        expected_claim_name = (
            f"{self.attempt_key_sha256}{SELECTION_ATTEMPT_CLAIM_SUFFIX}"
        )
        if claim_path.parent != store_path or claim_path.name != expected_claim_name:
            raise QualificationContractError(
                "launch descriptor claim path is not canonical for its fixed store"
            )
        if (
            len(
                {
                    self.registry_path,
                    self.referent_path,
                    self.protocol_path,
                    self.freeze_path,
                    self.attempt_claim_path,
                    self.preseed_readiness.artifact_path,
                    self.launch_intent.path,
                }
            )
            != 7
        ):
            raise QualificationContractError(
                "launch descriptor file paths must be distinct"
            )
        _constant(
            self.uniqueness_scope,
            "descriptor_bound_store_only",
            label="launch descriptor uniqueness_scope",
        )
        _constant(
            self.path_binding_scope,
            "absolute_local_paths",
            label="launch descriptor path_binding_scope",
        )
        for name in (
            "attempt_claim_preacquired",
            "trusted_store_operator_required",
            "exclusive_terminal_publication_preflight_verified",
        ):
            _constant(getattr(self, name), True, label=f"launch descriptor {name}")
        for name in (
            "execution_may_create_attempt_claim",
            "attempt_store_override_authorized",
            "global_one_shot_proved",
            "cross_store_uniqueness_proved",
            "multi_host_uniqueness_proved",
            "cross_worktree_portable",
            "cross_machine_portable",
            "store_deletion_resistant",
            "hostile_local_mutation_resistant",
            "exclusive_terminal_publication_operationally_proved",
            "selection_execution_started",
            "selection_values_observed",
            "scientific_claim_eligible",
            "subject_access_authorized",
        ):
            _constant(getattr(self, name), False, label=f"launch descriptor {name}")
        if len(canonical_json_bytes(self.to_dict())) > (
            MAX_PREPARED_SELECTION_LAUNCH_DESCRIPTOR_BYTES
        ):
            raise QualificationContractError(
                "prepared selection launch descriptor exceeds the fixed byte cap"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "descriptor_id": self.descriptor_id,
            "role": self.role,
            "claim_ceiling": self.claim_ceiling,
            "repository_root": self.repository_root,
            "registry_path": self.registry_path,
            "referent_path": self.referent_path,
            "protocol_path": self.protocol_path,
            "protocol_id": self.protocol_id,
            "protocol_source_sha256": self.protocol_source_sha256,
            "protocol_canonical_sha256": self.protocol_canonical_sha256,
            "freeze_path": self.freeze_path,
            "freeze_id": self.freeze_id,
            "freeze_source_sha256": self.freeze_source_sha256,
            "freeze_canonical_sha256": self.freeze_canonical_sha256,
            "attempt_store_path": self.attempt_store_path,
            "attempt_key_sha256": self.attempt_key_sha256,
            "attempt_claim_path": self.attempt_claim_path,
            "claim_id": self.claim_id,
            "attempt_claim_source_sha256": self.attempt_claim_source_sha256,
            "attempt_claim_canonical_sha256": (self.attempt_claim_canonical_sha256),
            "attempt_claim_byte_count": self.attempt_claim_byte_count,
            "launch_intent": self.launch_intent.to_dict(),
            "engine_commit": self.engine_commit,
            "preseed_readiness": self.preseed_readiness.to_dict(),
            "source_readiness": self.source_readiness.to_dict(),
            "source_readiness_summary_sha256": (self.source_readiness_summary_sha256),
            "terminal_publication_capability": (
                self.terminal_publication_capability.to_dict()
            ),
            "terminal_publication_capability_sha256": (
                self.terminal_publication_capability_sha256
            ),
            "uniqueness_scope": self.uniqueness_scope,
            "path_binding_scope": self.path_binding_scope,
            "attempt_claim_preacquired": self.attempt_claim_preacquired,
            "execution_may_create_attempt_claim": (
                self.execution_may_create_attempt_claim
            ),
            "attempt_store_override_authorized": (
                self.attempt_store_override_authorized
            ),
            "trusted_store_operator_required": self.trusted_store_operator_required,
            "global_one_shot_proved": self.global_one_shot_proved,
            "cross_store_uniqueness_proved": self.cross_store_uniqueness_proved,
            "multi_host_uniqueness_proved": self.multi_host_uniqueness_proved,
            "cross_worktree_portable": self.cross_worktree_portable,
            "cross_machine_portable": self.cross_machine_portable,
            "store_deletion_resistant": self.store_deletion_resistant,
            "hostile_local_mutation_resistant": (self.hostile_local_mutation_resistant),
            "exclusive_terminal_publication_preflight_verified": (
                self.exclusive_terminal_publication_preflight_verified
            ),
            "exclusive_terminal_publication_operationally_proved": (
                self.exclusive_terminal_publication_operationally_proved
            ),
            "selection_execution_started": self.selection_execution_started,
            "selection_values_observed": self.selection_values_observed,
            "scientific_claim_eligible": self.scientific_claim_eligible,
            "subject_access_authorized": self.subject_access_authorized,
        }

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_dict())

    @property
    def canonical_sha256(self) -> str:
        return canonical_json_sha256(self.to_dict())

    @classmethod
    def from_dict(cls, value: object) -> PreparedSelectionLaunchDescriptor:
        document = _mapping(value, label="prepared selection launch descriptor")
        _exact_keys(
            document,
            cls._ROOT_KEYS,
            label="prepared selection launch descriptor",
        )
        constants = {
            "schema_version": PREPARED_SELECTION_LAUNCH_DESCRIPTOR_SCHEMA_VERSION,
            "role": "prepared_calibration_selection_launch",
            "claim_ceiling": "level_0",
            "uniqueness_scope": "descriptor_bound_store_only",
            "path_binding_scope": "absolute_local_paths",
            "attempt_claim_preacquired": True,
            "execution_may_create_attempt_claim": False,
            "attempt_store_override_authorized": False,
            "trusted_store_operator_required": True,
            "global_one_shot_proved": False,
            "cross_store_uniqueness_proved": False,
            "multi_host_uniqueness_proved": False,
            "cross_worktree_portable": False,
            "cross_machine_portable": False,
            "store_deletion_resistant": False,
            "hostile_local_mutation_resistant": False,
            "exclusive_terminal_publication_preflight_verified": True,
            "exclusive_terminal_publication_operationally_proved": False,
            "selection_execution_started": False,
            "selection_values_observed": False,
            "scientific_claim_eligible": False,
            "subject_access_authorized": False,
        }
        for name, expected in constants.items():
            _constant(
                document[name],
                expected,
                label=f"launch descriptor {name}",
            )
        source_readiness = QualificationSourceBindingSummary.from_dict(
            document["source_readiness"]
        )
        preseed_readiness = PreseedReadinessBinding.from_dict(
            document["preseed_readiness"]
        )
        launch_intent = SelectionLaunchIntentBinding.from_dict(
            document["launch_intent"]
        )
        terminal_capability = ExclusiveTerminalPublicationCapability.from_dict(
            document["terminal_publication_capability"]
        )
        return cls(
            descriptor_id=_slug(
                document["descriptor_id"],
                label="launch descriptor descriptor_id",
            ),
            repository_root=_absolute_path_string(
                document["repository_root"],
                label="launch descriptor repository_root",
            ),
            registry_path=_absolute_path_string(
                document["registry_path"],
                label="launch descriptor registry_path",
            ),
            referent_path=_absolute_path_string(
                document["referent_path"],
                label="launch descriptor referent_path",
            ),
            protocol_path=_absolute_path_string(
                document["protocol_path"],
                label="launch descriptor protocol_path",
            ),
            protocol_id=_slug(
                document["protocol_id"],
                label="launch descriptor protocol_id",
            ),
            protocol_source_sha256=_sha256(
                document["protocol_source_sha256"],
                label="launch descriptor protocol_source_sha256",
            ),
            protocol_canonical_sha256=_sha256(
                document["protocol_canonical_sha256"],
                label="launch descriptor protocol_canonical_sha256",
            ),
            freeze_path=_absolute_path_string(
                document["freeze_path"],
                label="launch descriptor freeze_path",
            ),
            freeze_id=_slug(
                document["freeze_id"],
                label="launch descriptor freeze_id",
            ),
            freeze_source_sha256=_sha256(
                document["freeze_source_sha256"],
                label="launch descriptor freeze_source_sha256",
            ),
            freeze_canonical_sha256=_sha256(
                document["freeze_canonical_sha256"],
                label="launch descriptor freeze_canonical_sha256",
            ),
            attempt_store_path=_absolute_path_string(
                document["attempt_store_path"],
                label="launch descriptor attempt_store_path",
            ),
            attempt_key_sha256=_sha256(
                document["attempt_key_sha256"],
                label="launch descriptor attempt_key_sha256",
            ),
            attempt_claim_path=_absolute_path_string(
                document["attempt_claim_path"],
                label="launch descriptor attempt_claim_path",
            ),
            claim_id=_slug(
                document["claim_id"],
                label="launch descriptor claim_id",
            ),
            attempt_claim_source_sha256=_sha256(
                document["attempt_claim_source_sha256"],
                label="launch descriptor attempt_claim_source_sha256",
            ),
            attempt_claim_canonical_sha256=_sha256(
                document["attempt_claim_canonical_sha256"],
                label="launch descriptor attempt_claim_canonical_sha256",
            ),
            attempt_claim_byte_count=_plain_int(
                document["attempt_claim_byte_count"],
                label="launch descriptor attempt_claim_byte_count",
                minimum=1,
            ),
            launch_intent=launch_intent,
            engine_commit=_string(
                document["engine_commit"],
                label="launch descriptor engine_commit",
            ),
            preseed_readiness=preseed_readiness,
            source_readiness=source_readiness,
            source_readiness_summary_sha256=_sha256(
                document["source_readiness_summary_sha256"],
                label="launch descriptor source_readiness_summary_sha256",
            ),
            terminal_publication_capability=terminal_capability,
            terminal_publication_capability_sha256=_sha256(
                document["terminal_publication_capability_sha256"],
                label=("launch descriptor terminal_publication_capability_sha256"),
            ),
        )


@dataclass(frozen=True, slots=True)
class LoadedPreparedSelectionLaunchDescriptor:
    """One exact canonical launch descriptor loaded from a regular file."""

    descriptor: PreparedSelectionLaunchDescriptor
    source_path: Path
    source_bytes: bytes
    source_sha256: str
    canonical_sha256: str

    def __post_init__(self) -> None:
        if not isinstance(self.descriptor, PreparedSelectionLaunchDescriptor):
            raise TypeError("descriptor must be a PreparedSelectionLaunchDescriptor")
        if not isinstance(self.source_path, Path) or not self.source_path.is_absolute():
            raise TypeError("source_path must be an absolute Path")
        if not isinstance(self.source_bytes, bytes) or not self.source_bytes:
            raise TypeError("source_bytes must be non-empty bytes")
        _sha256(self.source_sha256, label="descriptor source_sha256")
        _sha256(self.canonical_sha256, label="descriptor canonical_sha256")
        if hashlib.sha256(self.source_bytes).hexdigest() != self.source_sha256:
            raise QualificationContractError(
                "loaded launch descriptor bytes differ from source_sha256"
            )
        if (
            self.source_bytes != self.descriptor.canonical_bytes
            or self.canonical_sha256 != self.descriptor.canonical_sha256
        ):
            raise QualificationContractError(
                "loaded launch descriptor differs from its canonical identity"
            )


@dataclass(frozen=True, slots=True)
class SelectionLaunchAuthorization:
    """Descriptor-derived authorization required by the official orchestrator."""

    descriptor_path: str
    descriptor_source_sha256: str
    descriptor_canonical_sha256: str
    authorized_head_commit: str
    launch_intent_identity_sha256: str
    protocol_canonical_sha256: str
    freeze_canonical_sha256: str
    attempt_claim_canonical_sha256: str
    attempt_store_path: str
    schema_version: str = SELECTION_LAUNCH_AUTHORIZATION_SCHEMA_VERSION
    descriptor_clean_tracked_head_verified: bool = True
    g_artifacts_clean_tracked_head_verified: bool = True
    selection_execution_started: bool = False
    retry_authorized: bool = False

    def __post_init__(self) -> None:
        _absolute_path_string(
            self.descriptor_path,
            label="launch authorization descriptor_path",
        )
        _absolute_path_string(
            self.attempt_store_path,
            label="launch authorization attempt_store_path",
        )
        for name in (
            "descriptor_source_sha256",
            "descriptor_canonical_sha256",
            "launch_intent_identity_sha256",
            "protocol_canonical_sha256",
            "freeze_canonical_sha256",
            "attempt_claim_canonical_sha256",
        ):
            _sha256(getattr(self, name), label=f"launch authorization {name}")
        if (
            not isinstance(self.authorized_head_commit, str)
            or len(self.authorized_head_commit) != 40
            or any(
                character not in _SHA256_CHARACTERS
                for character in self.authorized_head_commit
            )
        ):
            raise QualificationContractError(
                "launch authorization head must be a lowercase Git commit"
            )
        _constant(
            self.schema_version,
            SELECTION_LAUNCH_AUTHORIZATION_SCHEMA_VERSION,
            label="launch authorization schema_version",
        )
        for name in (
            "descriptor_clean_tracked_head_verified",
            "g_artifacts_clean_tracked_head_verified",
        ):
            _constant(
                getattr(self, name),
                True,
                label=f"launch authorization {name}",
            )
        for name in ("selection_execution_started", "retry_authorized"):
            _constant(
                getattr(self, name),
                False,
                label=f"launch authorization {name}",
            )

    @property
    def canonical_sha256(self) -> str:
        return canonical_json_sha256(
            {
                "schema_version": self.schema_version,
                "descriptor_path": self.descriptor_path,
                "descriptor_source_sha256": self.descriptor_source_sha256,
                "descriptor_canonical_sha256": self.descriptor_canonical_sha256,
                "authorized_head_commit": self.authorized_head_commit,
                "launch_intent_identity_sha256": (self.launch_intent_identity_sha256),
                "protocol_canonical_sha256": self.protocol_canonical_sha256,
                "freeze_canonical_sha256": self.freeze_canonical_sha256,
                "attempt_claim_canonical_sha256": (self.attempt_claim_canonical_sha256),
                "attempt_store_path": self.attempt_store_path,
                "descriptor_clean_tracked_head_verified": (
                    self.descriptor_clean_tracked_head_verified
                ),
                "g_artifacts_clean_tracked_head_verified": (
                    self.g_artifacts_clean_tracked_head_verified
                ),
                "selection_execution_started": self.selection_execution_started,
                "retry_authorized": self.retry_authorized,
            }
        )

    def validate_companions(
        self,
        *,
        loaded_protocol: LoadedQualificationProtocol,
        freeze: SelectionFreezeArtifact,
        attempt_claim: SelectionAttemptClaimArtifact,
        attempt_store: str | Path,
    ) -> None:
        """Reload the descriptor and require the same committed G companions."""

        loaded_descriptor = load_prepared_selection_launch_descriptor(
            self.descriptor_path,
            expected_source_sha256=self.descriptor_source_sha256,
            expected_canonical_sha256=self.descriptor_canonical_sha256,
        )
        descriptor = loaded_descriptor.descriptor
        store = _absolute(attempt_store)
        if (
            loaded_protocol.canonical_sha256 != self.protocol_canonical_sha256
            or freeze.canonical_sha256 != self.freeze_canonical_sha256
            or attempt_claim.canonical_sha256 != self.attempt_claim_canonical_sha256
            or str(store) != self.attempt_store_path
            or descriptor.protocol_canonical_sha256 != self.protocol_canonical_sha256
            or descriptor.freeze_canonical_sha256 != self.freeze_canonical_sha256
            or descriptor.attempt_claim_canonical_sha256
            != self.attempt_claim_canonical_sha256
            or descriptor.launch_intent.identity_sha256
            != self.launch_intent_identity_sha256
            or descriptor.attempt_store_path != self.attempt_store_path
        ):
            raise QualificationContractError(
                "launch authorization differs from its descriptor/companions"
            )
        repository = Path(descriptor.repository_root)
        current_head = subprocess.run(
            ["git", "-C", str(repository), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        if current_head != self.authorized_head_commit:
            raise QualificationContractError(
                "launch authorization HEAD changed after descriptor loading"
            )
        verified_head = _require_committed_g_artifacts(
            repository,
            loaded_descriptor=loaded_descriptor,
            descriptor=descriptor,
            freeze=freeze,
            attempt_claim=attempt_claim,
        )
        if verified_head != self.authorized_head_commit:
            raise QualificationContractError(
                "launch authorization HEAD changed during committed-G revalidation"
            )

    def validate_terminal_companions(
        self,
        *,
        loaded_protocol: LoadedQualificationProtocol,
        freeze: SelectionFreezeArtifact,
        attempt_claim: SelectionAttemptClaimArtifact,
        attempt_store: str | Path,
    ) -> None:
        """Revalidate G lineage while allowing unchanged descendant artifacts."""

        if not isinstance(loaded_protocol, LoadedQualificationProtocol):
            raise TypeError("loaded_protocol must be a LoadedQualificationProtocol")
        if not isinstance(freeze, SelectionFreezeArtifact):
            raise TypeError("freeze must be a SelectionFreezeArtifact")
        if not isinstance(attempt_claim, SelectionAttemptClaimArtifact):
            raise TypeError("attempt_claim must be a SelectionAttemptClaimArtifact")
        loaded_descriptor = load_prepared_selection_launch_descriptor(
            self.descriptor_path,
            expected_source_sha256=self.descriptor_source_sha256,
            expected_canonical_sha256=self.descriptor_canonical_sha256,
        )
        descriptor = loaded_descriptor.descriptor
        store = _absolute(attempt_store)
        descriptor_store = _validate_descriptor_join(
            descriptor,
            loaded_protocol=loaded_protocol,
            freeze=freeze,
        )
        freeze.validate_loaded_protocol(loaded_protocol=loaded_protocol)
        attempt_claim.validate_freeze(freeze)
        if (
            descriptor_store != store
            or loaded_protocol.source_path != Path(descriptor.protocol_path)
            or loaded_protocol.source_sha256 != descriptor.protocol_source_sha256
            or loaded_protocol.canonical_sha256 != descriptor.protocol_canonical_sha256
            or loaded_protocol.canonical_sha256 != self.protocol_canonical_sha256
            or descriptor.freeze_source_sha256 != freeze.canonical_sha256
            or freeze.canonical_sha256 != descriptor.freeze_canonical_sha256
            or freeze.canonical_sha256 != self.freeze_canonical_sha256
            or attempt_claim.claim_id != descriptor.claim_id
            or descriptor.attempt_claim_source_sha256 != attempt_claim.canonical_sha256
            or attempt_claim.canonical_sha256
            != descriptor.attempt_claim_canonical_sha256
            or attempt_claim.canonical_sha256 != self.attempt_claim_canonical_sha256
            or descriptor.attempt_claim_byte_count != len(attempt_claim.canonical_bytes)
            or attempt_claim.launch_intent != descriptor.launch_intent
            or descriptor.launch_intent.identity_sha256
            != self.launch_intent_identity_sha256
            or str(store) != self.attempt_store_path
            or descriptor.attempt_store_path != self.attempt_store_path
        ):
            raise QualificationContractError(
                "terminal launch authorization differs from its "
                "descriptor/protocol/freeze/claim/store companions"
            )
        validate_persisted_selection_attempt_claim(
            store,
            freeze=freeze,
            attempt_claim=attempt_claim,
        )
        repository = _require_real_directory(
            Path(descriptor.repository_root),
            label="terminal launch authorization repository",
        )
        _require_committed_g_artifacts_for_terminal(
            repository,
            engine_commit=loaded_protocol.protocol.engine.commit,
            authorized_head_commit=self.authorized_head_commit,
            loaded_descriptor=loaded_descriptor,
            descriptor=descriptor,
            freeze=freeze,
            attempt_claim=attempt_claim,
        )


@dataclass(frozen=True, slots=True)
class LoadedCommittedSelectionTerminal:
    """Read-only archived reload of one already-consumed official attempt.

    The protocol is intentionally not retained because it contains the closed
    selection seeds.  Historical blob verification does not establish current
    engine compatibility or historical runtime reexecution.  This receipt
    carries no execution or retry capability.
    """

    launch_authorization: SelectionLaunchAuthorization
    terminal_identity: PersistedSelectionTerminalIdentity
    consumption: SelectionConsumptionArtifact
    terminal_artifact: QualificationResult | SelectionFailedAttemptArtifact
    archival_contract_parser_used: bool = True
    historical_d1_recomputation_performed: bool = False
    current_source_compatibility_verified: bool = False
    historical_engine_reexecution_verified: bool = False

    def __post_init__(self) -> None:
        from .contracts import QualificationResult

        if not isinstance(self.launch_authorization, SelectionLaunchAuthorization):
            raise TypeError(
                "launch_authorization must be a SelectionLaunchAuthorization"
            )
        if not isinstance(
            self.terminal_identity,
            PersistedSelectionTerminalIdentity,
        ):
            raise TypeError(
                "terminal_identity must be a PersistedSelectionTerminalIdentity"
            )
        if not isinstance(self.consumption, SelectionConsumptionArtifact):
            raise TypeError("consumption must be a SelectionConsumptionArtifact")
        if not isinstance(
            self.terminal_artifact,
            (QualificationResult, SelectionFailedAttemptArtifact),
        ):
            raise TypeError(
                "terminal_artifact must be a QualificationResult or "
                "SelectionFailedAttemptArtifact"
            )
        _constant(
            self.archival_contract_parser_used,
            True,
            label="archived terminal archival_contract_parser_used",
        )
        for name in (
            "historical_d1_recomputation_performed",
            "current_source_compatibility_verified",
            "historical_engine_reexecution_verified",
        ):
            _constant(
                getattr(self, name),
                False,
                label=f"archived terminal {name}",
            )
        if (
            self.launch_authorization.retry_authorized
            or self.consumption.retry_authorized
            or self.consumption.reopen_authorized
        ):
            raise QualificationContractError(
                "a committed terminal reload cannot authorize reopen or retry"
            )
        if (
            self.terminal_identity.terminal_artifact_sha256
            != self.terminal_artifact.canonical_sha256
            or self.terminal_identity.consumption_sha256
            != self.consumption.canonical_sha256
            or self.consumption.terminal_artifact_sha256
            != self.terminal_artifact.canonical_sha256
        ):
            raise QualificationContractError(
                "loaded terminal receipt identities differ"
            )


@dataclass(frozen=True, slots=True)
class PreparedSelectionLaunch:
    """Validated inputs for the official runner, without entering it."""

    descriptor: PreparedSelectionLaunchDescriptor
    loaded_protocol: LoadedQualificationProtocol
    selection_freeze_artifact: SelectionFreezeArtifact
    attempt_claim: SelectionAttemptClaimArtifact
    loaded_preseed_readiness: LoadedClosedD0D5PreseedReadinessArtifact
    loaded_launch_intent: LoadedPreparedSelectionLaunchIntent
    source_readiness_receipt: QualificationSourceBindingReceipt
    source_binding_receipt: QualificationSourceBindingReceipt
    terminal_publication_capability: ExclusiveTerminalPublicationCapability
    launch_authorization: SelectionLaunchAuthorization | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.descriptor, PreparedSelectionLaunchDescriptor):
            raise TypeError("descriptor must be a PreparedSelectionLaunchDescriptor")
        if not isinstance(self.loaded_protocol, LoadedQualificationProtocol):
            raise TypeError("loaded_protocol must be a LoadedQualificationProtocol")
        if not isinstance(
            self.selection_freeze_artifact,
            SelectionFreezeArtifact,
        ):
            raise TypeError(
                "selection_freeze_artifact must be a SelectionFreezeArtifact"
            )
        if not isinstance(self.attempt_claim, SelectionAttemptClaimArtifact):
            raise TypeError("attempt_claim must be a SelectionAttemptClaimArtifact")
        if not isinstance(
            self.loaded_preseed_readiness,
            LoadedClosedD0D5PreseedReadinessArtifact,
        ):
            raise TypeError(
                "loaded_preseed_readiness must be a "
                "LoadedClosedD0D5PreseedReadinessArtifact"
            )
        if not isinstance(
            self.loaded_launch_intent,
            LoadedPreparedSelectionLaunchIntent,
        ):
            raise TypeError(
                "loaded_launch_intent must be a LoadedPreparedSelectionLaunchIntent"
            )
        for name in ("source_readiness_receipt", "source_binding_receipt"):
            if not isinstance(
                getattr(self, name),
                QualificationSourceBindingReceipt,
            ):
                raise TypeError(f"{name} must be a QualificationSourceBindingReceipt")
        if not isinstance(
            self.terminal_publication_capability,
            ExclusiveTerminalPublicationCapability,
        ):
            raise TypeError(
                "terminal_publication_capability must be an "
                "ExclusiveTerminalPublicationCapability"
            )
        descriptor = self.descriptor
        if self.loaded_launch_intent.binding != descriptor.launch_intent:
            raise QualificationContractError(
                "loaded launch intent differs from the launch descriptor"
            )
        if self.loaded_preseed_readiness.binding != descriptor.preseed_readiness:
            raise QualificationContractError(
                "loaded preseed readiness differs from the launch descriptor"
            )
        if self.loaded_protocol.source_path != Path(descriptor.protocol_path):
            raise QualificationContractError(
                "loaded protocol path differs from the launch descriptor"
            )
        if (
            self.loaded_protocol.source_sha256 != descriptor.protocol_source_sha256
            or self.loaded_protocol.canonical_sha256
            != descriptor.protocol_canonical_sha256
            or self.loaded_protocol.protocol.protocol_id != descriptor.protocol_id
        ):
            raise QualificationContractError(
                "loaded protocol identity differs from the launch descriptor"
            )
        if (
            self.selection_freeze_artifact.canonical_sha256
            != descriptor.freeze_canonical_sha256
            or self.selection_freeze_artifact.freeze_id != descriptor.freeze_id
        ):
            raise QualificationContractError(
                "selection freeze differs from the launch descriptor"
            )
        if (
            self.attempt_claim.claim_id != descriptor.claim_id
            or self.attempt_claim.canonical_sha256
            != descriptor.attempt_claim_canonical_sha256
            or len(self.attempt_claim.canonical_bytes)
            != descriptor.attempt_claim_byte_count
            or self.attempt_claim.launch_intent != descriptor.launch_intent
        ):
            raise QualificationContractError(
                "selection attempt claim differs from the launch descriptor"
            )
        descriptor.source_readiness.verify_receipt(self.source_readiness_receipt)
        if (
            self.selection_freeze_artifact.preseed_readiness
            != descriptor.preseed_readiness
            or self.attempt_claim.preseed_readiness != descriptor.preseed_readiness
            or self.loaded_protocol.protocol.preseed_readiness
            != descriptor.preseed_readiness
        ):
            raise QualificationContractError(
                "protocol/freeze/claim/descriptor preseed readiness join differs"
            )
        if (
            self.source_binding_receipt.engine != self.loaded_protocol.protocol.engine
            or self.source_binding_receipt.registry
            != self.loaded_protocol.protocol.registry
        ):
            raise QualificationContractError(
                "fresh source receipt differs from the loaded protocol"
            )
        if (
            self.terminal_publication_capability
            != descriptor.terminal_publication_capability
        ):
            raise QualificationContractError(
                "terminal capability differs from the launch descriptor"
            )
        if self.launch_authorization is not None and not isinstance(
            self.launch_authorization,
            SelectionLaunchAuthorization,
        ):
            raise TypeError(
                "launch_authorization must be a SelectionLaunchAuthorization or None"
            )


def _read_descriptor_source(path: Path) -> bytes:
    _require_real_file(path, label="prepared selection launch descriptor")
    try:
        with path.open("rb") as handle:
            before = os.fstat(handle.fileno())
            source = handle.read(MAX_PREPARED_SELECTION_LAUNCH_DESCRIPTOR_BYTES + 1)
            after = os.fstat(handle.fileno())
    except OSError as error:
        raise QualificationContractError(
            f"cannot read prepared selection launch descriptor: {error}"
        ) from error
    before_identity = (
        before.st_dev,
        before.st_ino,
        before.st_size,
        before.st_mtime_ns,
        before.st_ctime_ns,
        before.st_nlink,
    )
    after_identity = (
        after.st_dev,
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
        after.st_ctime_ns,
        after.st_nlink,
    )
    if before_identity != after_identity or len(source) != after.st_size:
        raise QualificationContractError(
            "prepared selection launch descriptor changed during read"
        )
    if after.st_nlink != 1:
        raise QualificationContractError(
            "prepared selection launch descriptor must have exactly one link"
        )
    if not source or len(source) > MAX_PREPARED_SELECTION_LAUNCH_DESCRIPTOR_BYTES:
        raise QualificationContractError(
            "prepared selection launch descriptor exceeds its fixed byte bound"
        )
    return source


def selection_launch_intent_path(
    store_directory: str | Path,
    freeze: SelectionFreezeArtifact,
) -> Path:
    """Return the sole freeze-keyed launch-intent path in a local store."""

    store = _require_real_directory(
        _absolute(store_directory),
        label="selection launch intent store",
    )
    return store / (
        f"{selection_attempt_key_sha256(freeze)}{SELECTION_LAUNCH_INTENT_SUFFIX}"
    )


def load_prepared_selection_launch_intent(
    binding: SelectionLaunchIntentBinding,
) -> LoadedPreparedSelectionLaunchIntent:
    """Strictly load one exact canonical launch intent from its binding."""

    if not isinstance(binding, SelectionLaunchIntentBinding):
        raise TypeError("binding must be a SelectionLaunchIntentBinding")
    path = _require_real_file(
        Path(binding.path),
        label="prepared selection launch intent",
    )
    try:
        with path.open("rb") as handle:
            before = os.fstat(handle.fileno())
            source = handle.read(MAX_SELECTION_CHRONOLOGY_ARTIFACT_BYTES + 1)
            after = os.fstat(handle.fileno())
    except OSError as error:
        raise QualificationContractError(
            f"cannot read prepared selection launch intent: {error}"
        ) from error
    if (
        (
            before.st_dev,
            before.st_ino,
            before.st_size,
            before.st_mtime_ns,
            before.st_ctime_ns,
            before.st_nlink,
        )
        != (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
            after.st_ctime_ns,
            after.st_nlink,
        )
        or after.st_nlink != 1
        or not source
        or len(source) != after.st_size
        or len(source) > MAX_SELECTION_CHRONOLOGY_ARTIFACT_BYTES
    ):
        raise QualificationContractError(
            "prepared selection launch intent is not one stable bounded file"
        )
    source_sha256 = hashlib.sha256(source).hexdigest()
    if source_sha256 != binding.source_sha256 or len(source) != binding.byte_count:
        raise QualificationContractError(
            "prepared selection launch intent source identity differs"
        )
    try:
        document = parse_canonical_json(
            source,
            label="prepared selection launch intent",
        )
    except CanonicalJsonError as error:
        raise QualificationContractError(str(error)) from error
    artifact = PreparedSelectionLaunchIntentArtifact.from_dict(document)
    if (
        artifact.canonical_bytes != source
        or artifact.canonical_sha256 != binding.canonical_sha256
    ):
        raise QualificationContractError(
            "prepared selection launch intent canonical identity differs"
        )
    return LoadedPreparedSelectionLaunchIntent(
        artifact=artifact,
        binding=binding,
        source_bytes=source,
    )


def write_prepared_selection_launch_intent(
    path: str | Path,
    artifact: PreparedSelectionLaunchIntentArtifact,
) -> LoadedPreparedSelectionLaunchIntent:
    """Publish the checked intent without overwrite and strictly round-trip."""

    if not isinstance(artifact, PreparedSelectionLaunchIntentArtifact):
        raise TypeError("artifact must be a PreparedSelectionLaunchIntentArtifact")
    destination = _absolute(path)
    parent = _require_real_directory(
        destination.parent,
        label="launch intent parent",
    )
    _require_absent(destination, label="prepared selection launch intent")
    payload = artifact.canonical_bytes
    file_descriptor, temporary_name = tempfile.mkstemp(
        dir=parent,
        prefix=f".{destination.name}.",
        suffix=".tmp",
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(file_descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary, destination)
        except FileExistsError as error:
            raise QualificationContractError(
                "prepared selection launch intent already exists; refusing overwrite"
            ) from error
        except OSError as error:
            raise QualificationContractError(
                f"cannot atomically publish launch intent: {error}"
            ) from error
        _fsync_directory(parent)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
    binding = SelectionLaunchIntentBinding(
        path=str(destination),
        source_sha256=artifact.canonical_sha256,
        canonical_sha256=artifact.canonical_sha256,
        byte_count=len(payload),
    )
    return load_prepared_selection_launch_intent(binding)


def load_prepared_selection_launch_descriptor(
    path: str | Path,
    *,
    expected_source_sha256: str,
    expected_canonical_sha256: str,
) -> LoadedPreparedSelectionLaunchDescriptor:
    """Load one exact descriptor without reading or creating a claim."""

    expected_source = _sha256(
        expected_source_sha256,
        label="expected descriptor source_sha256",
    )
    expected_canonical = _sha256(
        expected_canonical_sha256,
        label="expected descriptor canonical_sha256",
    )
    source_path = _absolute(path)
    source = _read_descriptor_source(source_path)
    source_sha256 = hashlib.sha256(source).hexdigest()
    if source_sha256 != expected_source:
        raise QualificationContractError(
            "prepared selection launch descriptor source SHA-256 differs"
        )
    try:
        parsed = parse_canonical_json(
            source,
            label="prepared selection launch descriptor",
        )
    except CanonicalJsonError as error:
        raise QualificationContractError(str(error)) from error
    descriptor = PreparedSelectionLaunchDescriptor.from_dict(parsed)
    if (
        descriptor.canonical_sha256 != expected_canonical
        or descriptor.canonical_bytes != source
    ):
        raise QualificationContractError(
            "prepared selection launch descriptor canonical identity differs"
        )
    return LoadedPreparedSelectionLaunchDescriptor(
        descriptor=descriptor,
        source_path=source_path,
        source_bytes=source,
        source_sha256=source_sha256,
        canonical_sha256=descriptor.canonical_sha256,
    )


def _fsync_directory(path: Path) -> None:
    flags = os.O_RDONLY
    if hasattr(os, "O_DIRECTORY"):
        flags |= os.O_DIRECTORY
    descriptor = os.open(path, flags)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def write_prepared_selection_launch_descriptor(
    path: str | Path,
    descriptor: PreparedSelectionLaunchDescriptor,
) -> LoadedPreparedSelectionLaunchDescriptor:
    """Publish one descriptor atomically without overwrite, then round-trip it."""

    if not isinstance(descriptor, PreparedSelectionLaunchDescriptor):
        raise TypeError("descriptor must be a PreparedSelectionLaunchDescriptor")
    destination = _absolute(path)
    parent = _require_real_directory(
        destination.parent,
        label="launch descriptor parent",
    )
    _require_absent(destination, label="prepared selection launch descriptor")
    payload = descriptor.canonical_bytes
    file_descriptor, temporary_name = tempfile.mkstemp(
        dir=parent,
        prefix=f".{destination.name}.",
        suffix=".tmp",
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(file_descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary, destination)
        except FileExistsError as error:
            raise QualificationContractError(
                "prepared selection launch descriptor already exists; "
                "overwrite is forbidden"
            ) from error
        except OSError as error:
            raise QualificationContractError(
                f"cannot atomically publish launch descriptor: {error}"
            ) from error
        _fsync_directory(parent)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
    digest = descriptor.canonical_sha256
    return load_prepared_selection_launch_descriptor(
        destination,
        expected_source_sha256=digest,
        expected_canonical_sha256=digest,
    )


def _validate_descriptor_join(
    descriptor: PreparedSelectionLaunchDescriptor,
    *,
    loaded_protocol: LoadedQualificationProtocol,
    freeze: SelectionFreezeArtifact,
) -> Path:
    protocol = loaded_protocol.protocol
    if (
        protocol.protocol_id != descriptor.protocol_id
        or protocol.engine.commit != descriptor.engine_commit
    ):
        raise QualificationContractError(
            "launch descriptor protocol identity differs from the loaded protocol"
        )
    if (
        freeze.freeze_id != descriptor.freeze_id
        or freeze.canonical_sha256 != descriptor.freeze_canonical_sha256
    ):
        raise QualificationContractError(
            "launch descriptor freeze identity differs from the loaded freeze"
        )
    attempt_store = Path(descriptor.attempt_store_path)
    expected_key = selection_attempt_key_sha256(freeze)
    expected_claim_path = selection_attempt_claim_path(attempt_store, freeze)
    expected_intent_path = selection_launch_intent_path(attempt_store, freeze)
    if (
        descriptor.attempt_key_sha256 != expected_key
        or Path(descriptor.attempt_claim_path) != expected_claim_path
        or Path(descriptor.launch_intent.path) != expected_intent_path
    ):
        raise QualificationContractError(
            "launch descriptor attempt identity differs from its freeze and store"
        )
    return attempt_store


def _require_unstarted(
    attempt_store: Path,
    *,
    freeze: SelectionFreezeArtifact,
) -> None:
    start_path = selection_execution_start_path(attempt_store, freeze)
    terminal_path = terminal_selection_transaction_path(attempt_store, freeze)
    if start_path.exists() or start_path.is_symlink():
        raise QualificationContractError(
            "selection execution has already started for this prepared launch"
        )
    if terminal_path.exists() or terminal_path.is_symlink():
        raise QualificationContractError(
            "selection attempt is already terminally consumed"
        )


def _expected_launch_intent(
    *,
    intent_id: str,
    repository: Path,
    loaded_protocol: LoadedQualificationProtocol,
    protocol_path: Path,
    freeze: SelectionFreezeArtifact,
    freeze_path: Path,
    freeze_source_sha256: str,
    attempt_store: Path,
    claim_id: str,
    preseed_readiness: PreseedReadinessBinding,
    source_readiness: QualificationSourceBindingSummary,
    terminal_capability: ExclusiveTerminalPublicationCapability,
) -> PreparedSelectionLaunchIntentArtifact:
    attempt_key = selection_attempt_key_sha256(freeze)
    return PreparedSelectionLaunchIntentArtifact(
        intent_id=intent_id,
        repository_root=str(repository),
        protocol_path=str(protocol_path),
        protocol_source_sha256=loaded_protocol.source_sha256,
        protocol_canonical_sha256=loaded_protocol.canonical_sha256,
        freeze_path=str(freeze_path),
        freeze_source_sha256=freeze_source_sha256,
        freeze_canonical_sha256=freeze.canonical_sha256,
        attempt_store_path=str(attempt_store),
        attempt_key_sha256=attempt_key,
        attempt_claim_path=str(selection_attempt_claim_path(attempt_store, freeze)),
        claim_id=claim_id,
        engine_commit=loaded_protocol.protocol.engine.commit,
        preseed_readiness=preseed_readiness,
        source_readiness_summary_sha256=source_readiness.canonical_sha256,
        terminal_publication_capability_sha256=(terminal_capability.canonical_sha256),
    )


def _require_committed_g_artifacts(
    repository: Path,
    *,
    loaded_descriptor: LoadedPreparedSelectionLaunchDescriptor,
    descriptor: PreparedSelectionLaunchDescriptor,
    freeze: SelectionFreezeArtifact,
    attempt_claim: SelectionAttemptClaimArtifact,
) -> str:
    """Require descriptor, store-freeze, intent, and claim as clean HEAD blobs."""

    completed = subprocess.run(
        ["git", "-C", str(repository), "rev-parse", "HEAD"],
        check=False,
        capture_output=True,
        text=True,
    )
    head = completed.stdout.strip()
    if (
        completed.returncode != 0
        or len(head) != 40
        or any(character not in _SHA256_CHARACTERS for character in head)
    ):
        raise QualificationContractError(
            "cannot resolve committed G authorization HEAD"
        )
    attempt_store = Path(descriptor.attempt_store_path)
    artifacts = (
        (
            loaded_descriptor.source_path,
            loaded_descriptor.source_sha256,
            "G launch descriptor",
        ),
        (
            selection_freeze_store_path(attempt_store, freeze),
            freeze.canonical_sha256,
            "G store freeze",
        ),
        (
            Path(descriptor.launch_intent.path),
            descriptor.launch_intent.source_sha256,
            "G launch intent",
        ),
        (
            Path(descriptor.attempt_claim_path),
            attempt_claim.canonical_sha256,
            "G attempt claim",
        ),
    )
    for path, digest, label in artifacts:
        _require_real_file(path, label=label)
        _require_tracked_clean_head_artifact(
            repository,
            path,
            expected_sha256=digest,
            label=label,
            expected_head_commit=head,
        )
    completed_after = subprocess.run(
        ["git", "-C", str(repository), "rev-parse", "HEAD"],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed_after.returncode != 0 or completed_after.stdout.strip() != head:
        raise QualificationContractError(
            "committed G authorization HEAD changed during verification"
        )
    return head


def _require_committed_g_artifacts_for_terminal(
    repository: Path,
    *,
    engine_commit: str,
    authorized_head_commit: str,
    loaded_descriptor: LoadedPreparedSelectionLaunchDescriptor,
    descriptor: PreparedSelectionLaunchDescriptor,
    freeze: SelectionFreezeArtifact,
    attempt_claim: SelectionAttemptClaimArtifact,
) -> str:
    """Revalidate committed G at an unchanged descendant HEAD."""

    current_head = _resolve_repository_head(
        repository,
        label="terminal committed G",
    )
    engine_ancestry = subprocess.run(
        [
            "git",
            "-C",
            str(repository),
            "merge-base",
            "--is-ancestor",
            engine_commit,
            authorized_head_commit,
        ],
        check=False,
        capture_output=True,
    )
    if engine_ancestry.returncode != 0:
        raise QualificationContractError(
            "engine commit is not an ancestor of committed G authorization HEAD"
        )
    ancestry = subprocess.run(
        [
            "git",
            "-C",
            str(repository),
            "merge-base",
            "--is-ancestor",
            authorized_head_commit,
            current_head,
        ],
        check=False,
        capture_output=True,
    )
    if ancestry.returncode != 0:
        raise QualificationContractError(
            "committed G authorization HEAD is not an ancestor of current HEAD"
        )
    attempt_store = Path(descriptor.attempt_store_path)
    for chronology_path, label in (
        (
            selection_execution_start_path(attempt_store, freeze),
            "selection execution-start path",
        ),
        (
            terminal_selection_transaction_path(attempt_store, freeze),
            "selection terminal transaction path",
        ),
    ):
        _require_path_absent_at_commit(
            repository,
            chronology_path,
            commit=authorized_head_commit,
            label=label,
        )
    artifacts = (
        (
            loaded_descriptor.source_path,
            loaded_descriptor.source_sha256,
            "G launch descriptor",
        ),
        (
            selection_freeze_store_path(attempt_store, freeze),
            freeze.canonical_sha256,
            "G store freeze",
        ),
        (
            Path(descriptor.launch_intent.path),
            descriptor.launch_intent.source_sha256,
            "G launch intent",
        ),
        (
            Path(descriptor.attempt_claim_path),
            attempt_claim.canonical_sha256,
            "G attempt claim",
        ),
    )
    for path, digest, label in artifacts:
        _require_real_file(path, label=label)
        _require_tracked_clean_unchanged_artifact(
            repository,
            path,
            expected_sha256=digest,
            authorized_head_commit=authorized_head_commit,
            current_head_commit=current_head,
            label=label,
        )
    if (
        _resolve_repository_head(
            repository,
            label="terminal committed G",
        )
        != current_head
    ):
        raise QualificationContractError(
            "terminal committed G HEAD changed during verification"
        )
    return current_head


def prepare_selection_launch(
    *,
    descriptor_id: str,
    repository_root: str | Path,
    registry_path: str | Path,
    referent_path: str | Path,
    protocol_path: str | Path,
    protocol_source_sha256: str,
    protocol_canonical_sha256: str,
    freeze_path: str | Path,
    freeze_source_sha256: str,
    freeze_canonical_sha256: str,
    attempt_store_path: str | Path,
    claim_id: str,
) -> PreparedSelectionLaunch:
    """Verify all preconditions, then acquire and round-trip one attempt claim.

    This function never begins execution and never reads a selection value.
    The claim is acquired only after both source readiness and the read-only
    terminal-publication capability preflight have succeeded.
    """

    prepared_descriptor_id = _slug(descriptor_id, label="descriptor_id")
    prepared_claim_id = _slug(claim_id, label="claim_id")
    repository = _require_real_directory(
        _absolute(repository_root),
        label="repository_root",
    )
    registry = _require_real_file(
        _absolute(registry_path),
        label="hypothesis registry",
    )
    referent = _require_real_file(
        _absolute(referent_path),
        label="referent contract set",
    )
    protocol_source_path = _require_real_file(
        _absolute(protocol_path),
        label="qualification protocol",
    )
    freeze_source_path = _require_real_file(
        _absolute(freeze_path),
        label="selection freeze",
    )
    attempt_store = _require_real_directory(
        _absolute(attempt_store_path),
        label="selection attempt store",
    )

    loaded_protocol = load_qualification_protocol(
        protocol_source_path,
        expected_source_sha256=protocol_source_sha256,
        expected_canonical_sha256=protocol_canonical_sha256,
    )
    loaded_preseed = load_protocol_preseed_readiness_artifact(loaded_protocol.protocol)
    if (
        loaded_preseed.artifact.repository_root != str(repository)
        or loaded_preseed.artifact.registry_path != str(registry)
        or loaded_preseed.artifact.referent_path != str(referent)
    ):
        raise QualificationContractError(
            "preseed readiness repository/registry/referent paths differ "
            "from launch inputs"
        )
    validate_closed_d0_d5_selection_protocol(
        loaded_protocol.protocol,
        require_persisted_preseed_readiness=True,
    )
    freeze = load_selection_freeze(
        freeze_source_path,
        expected_source_sha256=freeze_source_sha256,
        expected_canonical_sha256=freeze_canonical_sha256,
        loaded_protocol=loaded_protocol,
    )
    for path, digest, label in (
        (
            loaded_preseed.source_path,
            loaded_preseed.source_sha256,
            "preseed readiness artifact",
        ),
        (
            protocol_source_path,
            loaded_protocol.source_sha256,
            "qualification protocol",
        ),
        (
            freeze_source_path,
            freeze.canonical_sha256,
            "selection freeze",
        ),
    ):
        _require_tracked_clean_head_artifact(
            repository,
            path,
            expected_sha256=digest,
            label=label,
        )

    source_receipt = verify_protocol_source_binding(
        loaded_protocol.protocol,
        repository_root=repository,
        registry_path=registry,
        referent_path=referent,
    )
    verify_protocol_source_binding_successor(
        loaded_protocol.protocol,
        source_binding_summary=loaded_preseed.artifact.source_readiness,
        repository_root=repository,
        registry_path=registry,
        referent_path=referent,
    )
    source_summary = QualificationSourceBindingSummary.from_receipt(source_receipt)
    terminal_capability = probe_exclusive_terminal_publication_capability()

    _require_unstarted(attempt_store, freeze=freeze)
    claim_path = selection_attempt_claim_path(attempt_store, freeze)
    intent_path = selection_launch_intent_path(attempt_store, freeze)
    expected_intent = _expected_launch_intent(
        intent_id=prepared_descriptor_id,
        repository=repository,
        loaded_protocol=loaded_protocol,
        protocol_path=protocol_source_path,
        freeze=freeze,
        freeze_path=freeze_source_path,
        freeze_source_sha256=freeze.canonical_sha256,
        attempt_store=attempt_store,
        claim_id=prepared_claim_id,
        preseed_readiness=loaded_preseed.binding,
        source_readiness=source_summary,
        terminal_capability=terminal_capability,
    )
    claim_exists = claim_path.exists() or claim_path.is_symlink()
    intent_exists = intent_path.exists() or intent_path.is_symlink()
    if claim_exists and not intent_exists:
        raise QualificationContractError(
            "raw preexisting attempt claim has no earlier persisted launch intent"
        )
    if intent_exists:
        expected_intent_binding = SelectionLaunchIntentBinding(
            path=str(intent_path),
            source_sha256=expected_intent.canonical_sha256,
            canonical_sha256=expected_intent.canonical_sha256,
            byte_count=len(expected_intent.canonical_bytes),
        )
        loaded_intent = load_prepared_selection_launch_intent(expected_intent_binding)
        if loaded_intent.artifact != expected_intent:
            raise QualificationContractError(
                "persisted launch intent differs from the fully revalidated "
                "launch preconditions"
            )
    else:
        loaded_intent = write_prepared_selection_launch_intent(
            intent_path,
            expected_intent,
        )

    expected_claim = SelectionAttemptClaimArtifact.from_freeze(
        claim_id=prepared_claim_id,
        freeze=freeze,
        launch_intent=loaded_intent.binding,
    )
    if claim_exists:
        # Deterministic crash recovery for the narrow claim->descriptor gap.
        # Only the exact earlier intent, claim label, freeze, protocol,
        # preseed artifact, and canonical claim bytes are reusable.
        loaded_claim = load_selection_attempt_claim(
            claim_path,
            expected_source_sha256=expected_claim.canonical_sha256,
            expected_canonical_sha256=expected_claim.canonical_sha256,
            freeze=freeze,
        )
        claim_identity = PersistedSelectionIdentity(
            path=claim_path,
            source_sha256=expected_claim.canonical_sha256,
            canonical_sha256=expected_claim.canonical_sha256,
            byte_count=len(expected_claim.canonical_bytes),
        )
        attempt_claim = expected_claim
    else:
        attempt_claim, claim_identity = claim_selection_attempt(
            attempt_store,
            claim_id=prepared_claim_id,
            freeze=freeze,
            launch_intent=loaded_intent.binding,
        )
        loaded_claim = load_selection_attempt_claim(
            claim_identity.path,
            expected_source_sha256=claim_identity.source_sha256,
            expected_canonical_sha256=claim_identity.canonical_sha256,
            freeze=freeze,
        )
    validate_persisted_selection_attempt_claim(
        attempt_store,
        freeze=freeze,
        attempt_claim=loaded_claim,
    )
    if loaded_claim != attempt_claim:
        raise QualificationContractError(
            "prepared selection claim differs after canonical round-trip"
        )

    descriptor = PreparedSelectionLaunchDescriptor(
        descriptor_id=prepared_descriptor_id,
        repository_root=str(repository),
        registry_path=str(registry),
        referent_path=str(referent),
        protocol_path=str(protocol_source_path),
        protocol_id=loaded_protocol.protocol.protocol_id,
        protocol_source_sha256=loaded_protocol.source_sha256,
        protocol_canonical_sha256=loaded_protocol.canonical_sha256,
        freeze_path=str(freeze_source_path),
        freeze_id=freeze.freeze_id,
        freeze_source_sha256=_sha256(
            freeze_source_sha256,
            label="freeze_source_sha256",
        ),
        freeze_canonical_sha256=freeze.canonical_sha256,
        attempt_store_path=str(attempt_store),
        attempt_key_sha256=selection_attempt_key_sha256(freeze),
        attempt_claim_path=str(claim_identity.path),
        claim_id=attempt_claim.claim_id,
        attempt_claim_source_sha256=claim_identity.source_sha256,
        attempt_claim_canonical_sha256=claim_identity.canonical_sha256,
        attempt_claim_byte_count=claim_identity.byte_count,
        launch_intent=loaded_intent.binding,
        engine_commit=loaded_protocol.protocol.engine.commit,
        preseed_readiness=loaded_preseed.binding,
        source_readiness=source_summary,
        source_readiness_summary_sha256=source_summary.canonical_sha256,
        terminal_publication_capability=terminal_capability,
        terminal_publication_capability_sha256=(terminal_capability.canonical_sha256),
    )
    return PreparedSelectionLaunch(
        descriptor=descriptor,
        loaded_protocol=loaded_protocol,
        selection_freeze_artifact=freeze,
        attempt_claim=loaded_claim,
        loaded_launch_intent=loaded_intent,
        loaded_preseed_readiness=loaded_preseed,
        source_readiness_receipt=source_receipt,
        source_binding_receipt=source_receipt,
        terminal_publication_capability=terminal_capability,
    )


def load_prepared_selection_launch(
    descriptor_path: str | Path,
    *,
    expected_descriptor_source_sha256: str,
    expected_descriptor_canonical_sha256: str,
) -> PreparedSelectionLaunch:
    """Load an existing prepared claim solely through one exact descriptor.

    There is intentionally no repository, protocol, freeze, claim, or attempt
    store override in this signature.  This path never calls
    :func:`claim_selection_attempt`.
    """

    loaded_descriptor = load_prepared_selection_launch_descriptor(
        descriptor_path,
        expected_source_sha256=expected_descriptor_source_sha256,
        expected_canonical_sha256=expected_descriptor_canonical_sha256,
    )
    descriptor = loaded_descriptor.descriptor
    repository = _require_real_directory(
        Path(descriptor.repository_root),
        label="descriptor repository_root",
    )
    registry = _require_real_file(
        Path(descriptor.registry_path),
        label="descriptor hypothesis registry",
    )
    referent = _require_real_file(
        Path(descriptor.referent_path),
        label="descriptor referent contract set",
    )
    protocol_path = _require_real_file(
        Path(descriptor.protocol_path),
        label="descriptor qualification protocol",
    )
    freeze_path = _require_real_file(
        Path(descriptor.freeze_path),
        label="descriptor selection freeze",
    )
    _require_real_directory(
        Path(descriptor.attempt_store_path),
        label="descriptor selection attempt store",
    )

    loaded_protocol = load_qualification_protocol(
        protocol_path,
        expected_source_sha256=descriptor.protocol_source_sha256,
        expected_canonical_sha256=descriptor.protocol_canonical_sha256,
    )
    loaded_preseed = load_protocol_preseed_readiness_artifact(loaded_protocol.protocol)
    if (
        loaded_preseed.artifact.repository_root != str(repository)
        or loaded_preseed.artifact.registry_path != str(registry)
        or loaded_preseed.artifact.referent_path != str(referent)
    ):
        raise QualificationContractError(
            "historical preseed readiness paths differ from the descriptor"
        )
    if loaded_preseed.binding != descriptor.preseed_readiness:
        raise QualificationContractError(
            "historical preseed readiness differs from the launch descriptor"
        )
    validate_closed_d0_d5_selection_protocol(
        loaded_protocol.protocol,
        require_persisted_preseed_readiness=True,
    )
    freeze = load_selection_freeze(
        freeze_path,
        expected_source_sha256=descriptor.freeze_source_sha256,
        expected_canonical_sha256=descriptor.freeze_canonical_sha256,
        loaded_protocol=loaded_protocol,
    )
    for path, digest, label in (
        (
            loaded_preseed.source_path,
            loaded_preseed.source_sha256,
            "descriptor preseed readiness artifact",
        ),
        (
            protocol_path,
            loaded_protocol.source_sha256,
            "descriptor qualification protocol",
        ),
        (
            freeze_path,
            freeze.canonical_sha256,
            "descriptor selection freeze",
        ),
    ):
        _require_tracked_clean_head_artifact(
            repository,
            path,
            expected_sha256=digest,
            label=label,
        )
    attempt_store = _validate_descriptor_join(
        descriptor,
        loaded_protocol=loaded_protocol,
        freeze=freeze,
    )

    source_readiness_receipt = verify_protocol_source_binding_successor(
        loaded_protocol.protocol,
        source_binding_summary=descriptor.source_readiness,
        repository_root=repository,
        registry_path=registry,
        referent_path=referent,
    )
    verify_protocol_source_binding_successor(
        loaded_protocol.protocol,
        source_binding_summary=loaded_preseed.artifact.source_readiness,
        repository_root=repository,
        registry_path=registry,
        referent_path=referent,
    )
    fresh_source_receipt = verify_protocol_source_binding(
        loaded_protocol.protocol,
        repository_root=repository,
        registry_path=registry,
        referent_path=referent,
    )
    terminal_capability = probe_exclusive_terminal_publication_capability()
    if terminal_capability != descriptor.terminal_publication_capability:
        raise QualificationContractError(
            "current terminal-publication capability differs from the descriptor"
        )
    loaded_intent = load_prepared_selection_launch_intent(descriptor.launch_intent)
    expected_intent = _expected_launch_intent(
        intent_id=descriptor.descriptor_id,
        repository=repository,
        loaded_protocol=loaded_protocol,
        protocol_path=protocol_path,
        freeze=freeze,
        freeze_path=freeze_path,
        freeze_source_sha256=descriptor.freeze_source_sha256,
        attempt_store=attempt_store,
        claim_id=descriptor.claim_id,
        preseed_readiness=descriptor.preseed_readiness,
        source_readiness=descriptor.source_readiness,
        terminal_capability=terminal_capability,
    )
    if loaded_intent.artifact != expected_intent:
        raise QualificationContractError(
            "persisted launch intent differs from the descriptor and "
            "revalidated launch preconditions"
        )

    attempt_claim = load_selection_attempt_claim(
        descriptor.attempt_claim_path,
        expected_source_sha256=descriptor.attempt_claim_source_sha256,
        expected_canonical_sha256=(descriptor.attempt_claim_canonical_sha256),
        freeze=freeze,
    )
    validate_persisted_selection_attempt_claim(
        attempt_store,
        freeze=freeze,
        attempt_claim=attempt_claim,
    )
    if (
        attempt_claim.claim_id != descriptor.claim_id
        or attempt_claim.launch_intent != descriptor.launch_intent
    ):
        raise QualificationContractError(
            "descriptor intent/claim differs from the persisted attempt claim"
        )
    _require_unstarted(attempt_store, freeze=freeze)
    authorized_head = _require_committed_g_artifacts(
        repository,
        loaded_descriptor=loaded_descriptor,
        descriptor=descriptor,
        freeze=freeze,
        attempt_claim=attempt_claim,
    )
    launch_authorization = SelectionLaunchAuthorization(
        descriptor_path=str(loaded_descriptor.source_path),
        descriptor_source_sha256=loaded_descriptor.source_sha256,
        descriptor_canonical_sha256=loaded_descriptor.canonical_sha256,
        authorized_head_commit=authorized_head,
        launch_intent_identity_sha256=descriptor.launch_intent.identity_sha256,
        protocol_canonical_sha256=loaded_protocol.canonical_sha256,
        freeze_canonical_sha256=freeze.canonical_sha256,
        attempt_claim_canonical_sha256=attempt_claim.canonical_sha256,
        attempt_store_path=str(attempt_store),
    )

    return PreparedSelectionLaunch(
        descriptor=descriptor,
        loaded_protocol=loaded_protocol,
        selection_freeze_artifact=freeze,
        attempt_claim=attempt_claim,
        loaded_preseed_readiness=loaded_preseed,
        loaded_launch_intent=loaded_intent,
        source_readiness_receipt=source_readiness_receipt,
        source_binding_receipt=fresh_source_receipt,
        terminal_publication_capability=terminal_capability,
        launch_authorization=launch_authorization,
    )


def _read_stable_bounded_source(
    path: Path,
    *,
    label: str,
    maximum_bytes: int,
) -> bytes:
    """Read one regular file while rejecting replacement and oversize races."""

    _require_real_file(path, label=label)
    try:
        with path.open("rb") as handle:
            before = os.fstat(handle.fileno())
            source = handle.read(maximum_bytes + 1)
            after = os.fstat(handle.fileno())
    except OSError as error:
        raise QualificationContractError(f"cannot read {label}: {error}") from error
    before_identity = (
        before.st_dev,
        before.st_ino,
        before.st_size,
        before.st_mtime_ns,
        before.st_ctime_ns,
        before.st_nlink,
    )
    after_identity = (
        after.st_dev,
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
        after.st_ctime_ns,
        after.st_nlink,
    )
    if before_identity != after_identity or len(source) != after.st_size:
        raise QualificationContractError(f"{label} changed while being read")
    if len(source) > maximum_bytes:
        raise QualificationContractError(f"{label} exceeds the fixed byte cap")
    return source


def _git_blob_at_commit(
    repository: Path,
    *,
    commit: str,
    repository_path: str,
    label: str,
) -> bytes:
    completed = subprocess.run(
        ["git", "-C", str(repository), "show", f"{commit}:{repository_path}"],
        check=False,
        capture_output=True,
    )
    if completed.returncode != 0:
        raise QualificationContractError(
            f"{label} is absent from its historical commit"
        )
    return completed.stdout


def _module_path_at_commit(
    repository: Path,
    *,
    commit: str,
    module: str,
) -> str:
    stem = PurePosixPath("src", *module.split("."))
    candidates = (f"{stem.as_posix()}.py", f"{stem.as_posix()}/__init__.py")
    existing: list[str] = []
    for candidate in candidates:
        completed = subprocess.run(
            [
                "git",
                "-C",
                str(repository),
                "cat-file",
                "-e",
                f"{commit}:{candidate}",
            ],
            check=False,
            capture_output=True,
        )
        if completed.returncode == 0:
            existing.append(candidate)
    if len(existing) != 1:
        raise QualificationContractError(
            f"engine module {module} does not resolve uniquely at execution HEAD"
        )
    return existing[0]


def _historical_source_binding_receipt(
    *,
    repository: Path,
    loaded_protocol: LoadedQualificationProtocol,
    descriptor: PreparedSelectionLaunchDescriptor,
    authorization: SelectionLaunchAuthorization,
    source_binding: QualificationSourceBindingSummary,
) -> QualificationSourceBindingReceipt:
    """Rebuild the exact result-bound receipt from immutable Git blobs."""

    protocol = loaded_protocol.protocol
    execution_head = source_binding.head_commit
    if execution_head != authorization.authorized_head_commit:
        raise QualificationContractError(
            "result execution source HEAD differs from committed G authorization"
        )
    current_head = _resolve_repository_head(
        repository,
        label="historical source receipt",
    )
    for commit, label in (
        (protocol.engine.commit, "engine commit"),
        (execution_head, "execution HEAD"),
        (current_head, "current HEAD"),
    ):
        resolved = subprocess.run(
            [
                "git",
                "-C",
                str(repository),
                "rev-parse",
                "--verify",
                f"{commit}^{{commit}}",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        if resolved.returncode != 0 or resolved.stdout.strip() != commit:
            raise QualificationContractError(
                f"historical source receipt {label} does not resolve exactly"
            )
    for ancestor, descendant, label in (
        (
            protocol.engine.commit,
            execution_head,
            "engine commit is not an ancestor of execution HEAD",
        ),
        (
            execution_head,
            current_head,
            "execution HEAD is not an ancestor of current HEAD",
        ),
    ):
        ancestry = subprocess.run(
            [
                "git",
                "-C",
                str(repository),
                "merge-base",
                "--is-ancestor",
                ancestor,
                descendant,
            ],
            check=False,
            capture_output=True,
        )
        if ancestry.returncode != 0:
            raise QualificationContractError(label)

    module_receipts: list[ModuleSourceReceipt] = []
    for declaration in protocol.engine.modules:
        repository_path = _module_path_at_commit(
            repository,
            commit=protocol.engine.commit,
            module=declaration.module,
        )
        execution_path = _module_path_at_commit(
            repository,
            commit=execution_head,
            module=declaration.module,
        )
        if execution_path != repository_path:
            raise QualificationContractError(
                f"engine module {declaration.module} moved before execution"
            )
        for commit, label in (
            (protocol.engine.commit, "engine commit"),
            (execution_head, "execution HEAD"),
        ):
            source = _git_blob_at_commit(
                repository,
                commit=commit,
                repository_path=repository_path,
                label=f"engine module {declaration.module} at {label}",
            )
            if hashlib.sha256(source).hexdigest() != declaration.sha256:
                raise QualificationContractError(
                    f"engine module {declaration.module} differs at {label}"
                )
        module_receipts.append(
            ModuleSourceReceipt(
                module=declaration.module,
                repository_path=repository_path,
                declared_sha256=declaration.sha256,
                working_sha256=declaration.sha256,
                head_blob_sha256=declaration.sha256,
                bound_blob_sha256=declaration.sha256,
            )
        )

    for declaration in protocol.engine.official_executables:
        for commit, label in (
            (protocol.engine.commit, "engine commit"),
            (execution_head, "execution HEAD"),
        ):
            source = _git_blob_at_commit(
                repository,
                commit=commit,
                repository_path=declaration.repository_path,
                label=f"official executable {declaration.repository_path} at {label}",
            )
            if hashlib.sha256(source).hexdigest() != declaration.sha256:
                raise QualificationContractError(
                    f"official executable {declaration.repository_path} "
                    f"differs at {label}"
                )

    try:
        registry_repository_path = Path(descriptor.registry_path).relative_to(
            repository
        )
        referent_repository_path = Path(descriptor.referent_path).relative_to(
            repository
        )
    except ValueError as error:
        raise QualificationContractError(
            "descriptor registry/referent paths must remain inside repository_root"
        ) from error
    registry_path_text = registry_repository_path.as_posix()
    referent_path_text = referent_repository_path.as_posix()
    registry_source = _git_blob_at_commit(
        repository,
        commit=execution_head,
        repository_path=registry_path_text,
        label="hypothesis registry at execution HEAD",
    )
    referent_source = _git_blob_at_commit(
        repository,
        commit=execution_head,
        repository_path=referent_path_text,
        label="referent contract set at execution HEAD",
    )
    if (
        hashlib.sha256(registry_source).hexdigest()
        != protocol.registry.registry_source_sha256
        or hashlib.sha256(referent_source).hexdigest()
        != protocol.registry.referent_canonical_sha256
    ):
        raise QualificationContractError(
            "registry or referent historical blob differs from the protocol"
        )
    receipt = QualificationSourceBindingReceipt(
        engine=protocol.engine,
        registry=protocol.registry,
        head_commit=execution_head,
        modules=tuple(module_receipts),
        hypothesis_registry=RegistrySourceReceipt(
            repository_path=registry_path_text,
            source_sha256=protocol.registry.registry_source_sha256,
            canonical_sha256=protocol.registry.registry_canonical_sha256,
        ),
        referent_contracts=ReferentSourceReceipt(
            repository_path=referent_path_text,
            source_sha256=protocol.registry.referent_canonical_sha256,
            canonical_sha256=protocol.registry.referent_canonical_sha256,
            hypothesis_registry_canonical_sha256=(
                protocol.registry.registry_canonical_sha256
            ),
        ),
    )
    source_binding.verify_receipt(receipt)
    return receipt


def _terminal_historical_source_binding_receipt(
    *,
    repository: Path,
    loaded_protocol: LoadedQualificationProtocol,
    descriptor: PreparedSelectionLaunchDescriptor,
    authorization: SelectionLaunchAuthorization,
    freeze: SelectionFreezeArtifact,
    attempt_claim: SelectionAttemptClaimArtifact,
    terminal_identity: PersistedSelectionTerminalIdentity,
) -> QualificationSourceBindingReceipt | None:
    """Preload only enough typed terminal data to rebuild result provenance."""

    manifest_source = _read_stable_bounded_source(
        terminal_identity.path / SELECTION_TERMINAL_MANIFEST_FILENAME,
        label="H terminal manifest",
        maximum_bytes=MAX_SELECTION_CHRONOLOGY_ARTIFACT_BYTES,
    )
    try:
        manifest_document = parse_canonical_json(
            manifest_source,
            label="selection terminal manifest",
        )
    except CanonicalJsonError as error:
        raise QualificationContractError(str(error)) from error
    manifest = SelectionTerminalManifestArtifact.from_dict(manifest_document)
    if (
        manifest_source != manifest.canonical_bytes
        or manifest.canonical_sha256 != terminal_identity.manifest_sha256
        or manifest.freeze_artifact_sha256 != freeze.canonical_sha256
        or manifest.attempt_claim_sha256 != attempt_claim.canonical_sha256
        or manifest.terminal_artifact_sha256
        != terminal_identity.terminal_artifact_sha256
        or manifest.consumption_sha256 != terminal_identity.consumption_sha256
    ):
        raise QualificationContractError(
            "preloaded terminal manifest identity or companion join differs"
        )
    if manifest.terminal_artifact_kind is TerminalAttemptArtifactKind.FAILED_ATTEMPT:
        return None

    from .contracts import QualificationResult

    terminal_source = _read_stable_bounded_source(
        terminal_identity.path / SELECTION_TERMINAL_ARTIFACT_FILENAME,
        label="H terminal artifact",
        maximum_bytes=MAX_SELECTION_TERMINAL_ARTIFACT_BYTES,
    )
    try:
        terminal_document = parse_canonical_json(
            terminal_source,
            label="selection terminal artifact",
        )
    except CanonicalJsonError as error:
        raise QualificationContractError(str(error)) from error
    result = QualificationResult.from_dict(terminal_document)
    if (
        terminal_source != result.canonical_bytes
        or result.canonical_sha256 != terminal_identity.terminal_artifact_sha256
        or len(terminal_source) != manifest.terminal_artifact_byte_count
    ):
        raise QualificationContractError(
            "preloaded result identity differs from the terminal manifest"
        )
    return _historical_source_binding_receipt(
        repository=repository,
        loaded_protocol=loaded_protocol,
        descriptor=descriptor,
        authorization=authorization,
        source_binding=result.source_binding,
    )


def _reconstruct_terminal_launch_authorization(
    *,
    loaded_descriptor: LoadedPreparedSelectionLaunchDescriptor,
    loaded_protocol: LoadedQualificationProtocol,
    freeze: SelectionFreezeArtifact,
    attempt_claim: SelectionAttemptClaimArtifact,
    attempt_store: Path,
) -> tuple[SelectionLaunchAuthorization, SelectionExecutionStartArtifact]:
    """Reconstruct G authorization from an exact persisted execution start."""

    descriptor = loaded_descriptor.descriptor
    start_path = selection_execution_start_path(attempt_store, freeze)
    source = _read_stable_bounded_source(
        start_path,
        label="selection execution-start artifact",
        maximum_bytes=MAX_SELECTION_CHRONOLOGY_ARTIFACT_BYTES,
    )
    try:
        document = parse_canonical_json(
            source,
            label="selection execution-start artifact",
        )
    except CanonicalJsonError as error:
        raise QualificationContractError(str(error)) from error
    start = SelectionExecutionStartArtifact.from_dict(document)
    if source != start.canonical_bytes:
        raise QualificationContractError(
            "selection execution-start artifact is not exact canonical bytes"
        )
    if (
        start.authorized_head_commit is None
        or start.selection_launch_authorization_sha256 is None
    ):
        raise QualificationContractError(
            "official terminal start lacks committed-G authorization lineage"
        )
    start.validate_companions(
        freeze=freeze,
        attempt_claim=attempt_claim,
        selection_launch_authorization_sha256=(
            start.selection_launch_authorization_sha256
        ),
        authorized_head_commit=start.authorized_head_commit,
    )
    authorization = SelectionLaunchAuthorization(
        descriptor_path=str(loaded_descriptor.source_path),
        descriptor_source_sha256=loaded_descriptor.source_sha256,
        descriptor_canonical_sha256=loaded_descriptor.canonical_sha256,
        authorized_head_commit=start.authorized_head_commit,
        launch_intent_identity_sha256=descriptor.launch_intent.identity_sha256,
        protocol_canonical_sha256=loaded_protocol.canonical_sha256,
        freeze_canonical_sha256=freeze.canonical_sha256,
        attempt_claim_canonical_sha256=attempt_claim.canonical_sha256,
        attempt_store_path=str(attempt_store),
    )
    if authorization.canonical_sha256 != start.selection_launch_authorization_sha256:
        raise QualificationContractError(
            "execution-start launch authorization differs from its exact "
            "descriptor-derived identity"
        )
    authorization.validate_terminal_companions(
        loaded_protocol=loaded_protocol,
        freeze=freeze,
        attempt_claim=attempt_claim,
        attempt_store=attempt_store,
    )
    return authorization, start


def load_committed_selection_terminal(
    descriptor_path: str | Path,
    *,
    expected_descriptor_source_sha256: str,
    expected_descriptor_canonical_sha256: str,
    expected_terminal_manifest_sha256: str,
    expected_terminal_artifact_sha256: str,
    expected_consumption_sha256: str,
) -> LoadedCommittedSelectionTerminal:
    """Strictly reload one completed official terminal transaction.

    All paths are descriptor-derived.  The historical G authorization is
    reconstructed from the immutable execution-start lineage, then checked as
    ``engine -> G -> current HEAD``.  The four G blobs must be unchanged at G
    and current HEAD, and both the start and terminal paths must have been
    absent at G.  This function only reads an already-consumed attempt; it
    cannot create a claim, begin execution, reopen, or authorize a retry.
    """

    loaded_descriptor = load_prepared_selection_launch_descriptor(
        descriptor_path,
        expected_source_sha256=expected_descriptor_source_sha256,
        expected_canonical_sha256=expected_descriptor_canonical_sha256,
    )
    descriptor = loaded_descriptor.descriptor
    repository = _require_real_directory(
        Path(descriptor.repository_root),
        label="terminal descriptor repository_root",
    )
    _require_real_file(
        Path(descriptor.registry_path),
        label="terminal descriptor hypothesis registry",
    )
    _require_real_file(
        Path(descriptor.referent_path),
        label="terminal descriptor referent contract set",
    )
    protocol_path = _require_real_file(
        Path(descriptor.protocol_path),
        label="terminal descriptor qualification protocol",
    )
    freeze_path = _require_real_file(
        Path(descriptor.freeze_path),
        label="terminal descriptor selection freeze",
    )
    attempt_store = _require_real_directory(
        Path(descriptor.attempt_store_path),
        label="terminal descriptor selection attempt store",
    )

    loaded_protocol = load_qualification_protocol(
        protocol_path,
        expected_source_sha256=descriptor.protocol_source_sha256,
        expected_canonical_sha256=descriptor.protocol_canonical_sha256,
    )
    validate_closed_d0_d5_selection_protocol(
        loaded_protocol.protocol,
        require_persisted_preseed_readiness=True,
    )
    freeze = load_selection_freeze(
        freeze_path,
        expected_source_sha256=descriptor.freeze_source_sha256,
        expected_canonical_sha256=descriptor.freeze_canonical_sha256,
        loaded_protocol=loaded_protocol,
    )
    if (
        _validate_descriptor_join(
            descriptor,
            loaded_protocol=loaded_protocol,
            freeze=freeze,
        )
        != attempt_store
    ):
        raise QualificationContractError(
            "terminal descriptor attempt store differs from its companions"
        )
    loaded_intent = load_prepared_selection_launch_intent(descriptor.launch_intent)
    if loaded_intent.binding != descriptor.launch_intent:
        raise QualificationContractError(
            "terminal launch intent differs from the descriptor"
        )
    attempt_claim = load_selection_attempt_claim(
        descriptor.attempt_claim_path,
        expected_source_sha256=descriptor.attempt_claim_source_sha256,
        expected_canonical_sha256=descriptor.attempt_claim_canonical_sha256,
        freeze=freeze,
    )
    validate_persisted_selection_attempt_claim(
        attempt_store,
        freeze=freeze,
        attempt_claim=attempt_claim,
    )
    if (
        attempt_claim.claim_id != descriptor.claim_id
        or attempt_claim.launch_intent != descriptor.launch_intent
        or attempt_claim.canonical_sha256 != descriptor.attempt_claim_canonical_sha256
    ):
        raise QualificationContractError(
            "terminal descriptor intent/claim identity differs"
        )

    authorization, start = _reconstruct_terminal_launch_authorization(
        loaded_descriptor=loaded_descriptor,
        loaded_protocol=loaded_protocol,
        freeze=freeze,
        attempt_claim=attempt_claim,
        attempt_store=attempt_store,
    )
    terminal_path = terminal_selection_transaction_path(attempt_store, freeze)
    terminal_identity = PersistedSelectionTerminalIdentity(
        path=terminal_path,
        manifest_sha256=_sha256(
            expected_terminal_manifest_sha256,
            label="expected terminal manifest_sha256",
        ),
        terminal_artifact_sha256=_sha256(
            expected_terminal_artifact_sha256,
            label="expected terminal artifact_sha256",
        ),
        consumption_sha256=_sha256(
            expected_consumption_sha256,
            label="expected terminal consumption_sha256",
        ),
    )
    current_head = _resolve_repository_head(
        repository,
        label="committed terminal reload",
    )
    for path, digest, label in (
        (
            selection_execution_start_path(attempt_store, freeze),
            start.canonical_sha256,
            "H selection execution start",
        ),
        (
            terminal_path / SELECTION_TERMINAL_MANIFEST_FILENAME,
            terminal_identity.manifest_sha256,
            "H terminal manifest",
        ),
        (
            terminal_path / SELECTION_TERMINAL_ARTIFACT_FILENAME,
            terminal_identity.terminal_artifact_sha256,
            "H terminal artifact",
        ),
        (
            terminal_path / SELECTION_TERMINAL_CONSUMPTION_FILENAME,
            terminal_identity.consumption_sha256,
            "H terminal consumption",
        ),
    ):
        _require_real_file(path, label=label)
        _require_tracked_clean_head_artifact(
            repository,
            path,
            expected_sha256=digest,
            label=label,
            expected_head_commit=current_head,
        )
    if (
        _resolve_repository_head(
            repository,
            label="committed terminal reload",
        )
        != current_head
    ):
        raise QualificationContractError(
            "committed terminal HEAD changed during verification"
        )
    historical_source_receipt = _terminal_historical_source_binding_receipt(
        repository=repository,
        loaded_protocol=loaded_protocol,
        descriptor=descriptor,
        authorization=authorization,
        freeze=freeze,
        attempt_claim=attempt_claim,
        terminal_identity=terminal_identity,
    )
    consumption, terminal_artifact = load_terminal_selection_consumption(
        terminal_identity.path,
        expected_manifest_sha256=terminal_identity.manifest_sha256,
        expected_terminal_artifact_sha256=(terminal_identity.terminal_artifact_sha256),
        expected_consumption_sha256=terminal_identity.consumption_sha256,
        freeze=freeze,
        attempt_claim=attempt_claim,
        loaded_protocol=loaded_protocol,
        launch_authorization=authorization,
        _historical_source_binding_receipt=historical_source_receipt,
        _historical_reload_capability=(
            _HISTORICAL_SOURCE_RELOAD_CAPABILITY
            if historical_source_receipt is not None
            else None
        ),
    )
    return LoadedCommittedSelectionTerminal(
        launch_authorization=authorization,
        terminal_identity=terminal_identity,
        consumption=consumption,
        terminal_artifact=terminal_artifact,  # type: ignore[arg-type]
    )


__all__ = [
    "EXCLUSIVE_TERMINAL_PUBLICATION_CAPABILITY_SCHEMA_VERSION",
    "MAX_PREPARED_SELECTION_LAUNCH_DESCRIPTOR_BYTES",
    "PREPARED_SELECTION_LAUNCH_DESCRIPTOR_SCHEMA_VERSION",
    "PREPARED_SELECTION_LAUNCH_INTENT_SCHEMA_VERSION",
    "SELECTION_LAUNCH_AUTHORIZATION_SCHEMA_VERSION",
    "ExclusiveTerminalPublicationCapability",
    "LoadedCommittedSelectionTerminal",
    "LoadedPreparedSelectionLaunchDescriptor",
    "LoadedPreparedSelectionLaunchIntent",
    "PreparedSelectionLaunch",
    "PreparedSelectionLaunchDescriptor",
    "PreparedSelectionLaunchIntentArtifact",
    "SelectionLaunchAuthorization",
    "load_committed_selection_terminal",
    "load_prepared_selection_launch",
    "load_prepared_selection_launch_descriptor",
    "load_prepared_selection_launch_intent",
    "prepare_selection_launch",
    "probe_exclusive_terminal_publication_capability",
    "selection_launch_intent_path",
    "write_prepared_selection_launch_descriptor",
    "write_prepared_selection_launch_intent",
]
